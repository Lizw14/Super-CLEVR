# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from __future__ import print_function
import math, sys, random, argparse, json, os, tempfile
from datetime import datetime as dt
from collections import Counter
import pdb
# random.seed(10)

import numpy as np
import subprocess

"""
Renders random scenes using Blender, each with with a random number of objects;
each object has a random size, position, color, and shape. Objects will be
nonintersecting but may partially occlude each other. Output images will be
written to disk as PNGs, and we will also write a JSON file for each image with
ground-truth scene information.

This file expects to be run from Blender like this:

blender --background --python render_images.py -- [arguments to this script]
"""

INSIDE_BLENDER = True
try:
    import bpy, bpy_extras
    from mathutils import Vector
except ImportError as e:
    INSIDE_BLENDER = False
if INSIDE_BLENDER:
    try:
        import utils
    except ImportError as e:
        print("\nERROR")
        print("Running render_images.py from Blender and cannot import utils.py.") 
        print("You may need to add a .pth file to the site-packages of Blender's")
        print("bundled python with a command like this:\n")
        print("echo $PWD >> $BLENDER/$VERSION/python/lib/python3.5/site-packages/clevr.pth")
        print("\nWhere $BLENDER is the directory where Blender is installed, and")
        print("$VERSION is your Blender version (such as 2.78).")
        sys.exit(1)

parser = argparse.ArgumentParser()

# Input options
parser.add_argument('--base_scene_blendfile', default='data/base_scene.blend',
        help="Base blender file on which all scenes are based; includes " +
                    "ground plane, lights, and camera.")
parser.add_argument('--properties_json', default='data/properties.json',
        help="JSON file defining objects, materials, sizes, and colors. " +
                 "The \"colors\" field maps from CLEVR color names to RGB values; " +
                 "The \"sizes\" field maps from CLEVR size names to scalars used to " +
                 "rescale object models; the \"materials\" and \"shapes\" fields map " +
                 "from CLEVR material and shape names to .blend files in the " +
                 "--object_material_dir and --shape_dir directories respectively.")
parser.add_argument('--shape_dir', default='data/shapes',
        help="Directory where .obj files for object models are stored")
parser.add_argument('--model_dir', default='data/save_models_1/',
        help="Directory where .blend files for object models are stored")
parser.add_argument('--material_dir', default='data/materials',
    help="Directory where .blend files for materials are stored")

# Settings for objects
parser.add_argument('--min_objects', default=3, type=int,
        help="The minimum number of objects to place in each scene")
parser.add_argument('--max_objects', default=10, type=int,
        help="The maximum number of objects to place in each scene")
parser.add_argument('--min_dist', default=0.25, type=float,
        help="The minimum allowed distance between object centers")
parser.add_argument('--margin', default=0.4, type=float,
        help="Along all cardinal directions (left, right, front, back), all " +
                 "objects will be at least this distance apart. This makes resolving " +
                 "spatial relationships slightly less ambiguous.")
parser.add_argument('--min_pixels_per_object', default=200, type=int,
        help="All objects will have at least this many visible pixels in the " +
                 "final rendered images; this ensures that no objects are fully " +
                 "occluded by other objects.")
parser.add_argument('--min_pixels_per_part', default=20, type=int,
        help="All modified parts will have at least this many visible pixels in the " +
                 "final rendered images; this ensures that no objects are fully " +
                 "occluded by other objects.")
parser.add_argument('--max_retries', default=50, type=int,
        help="The number of times to try placing an object before giving up and " +
                 "re-placing all objects in the scene.")

# Output settings
parser.add_argument('--start_idx', default=0, type=int,
        help="The index at which to start for numbering rendered images. Setting " +
                 "this to non-zero values allows you to distribute rendering across " +
                 "multiple machines and recombine the results later.")
parser.add_argument('--num_images', default=5, type=int,
        help="The number of images to render")
parser.add_argument('--filename_prefix', default='superCLEVR',
        help="This prefix will be prepended to the rendered images and JSON scenes")
parser.add_argument('--split', default='new',
        help="Name of the split for which we are rendering. This will be added to " +
                 "the names of rendered images, and will also be stored in the JSON " +
                 "scene structure for each image.")
parser.add_argument('--output_image_dir', default='../output/images/',
        help="The directory where output images will be stored. It will be " +
                 "created if it does not exist.")
parser.add_argument('--output_scene_dir', default='../output/scenes/',
        help="The directory where output JSON scene structures will be stored. " +
                 "It will be created if it does not exist.")
parser.add_argument('--output_scene_file', default='../output/CLEVR_scenes.json',
        help="Path to write a single JSON file containing all scene information")
parser.add_argument('--output_blend_dir', default='../output/blendfiles',
        help="The directory where blender scene files will be stored, if the " +
                 "user requested that these files be saved using the " +
                 "--save_blendfiles flag; in this case it will be created if it does " +
                 "not already exist.")
parser.add_argument('--save_blendfiles', type=int, default=0,
        help="Setting --save_blendfiles 1 will cause the blender scene file for " +
                 "each generated image to be stored in the directory specified by " +
                 "the --output_blend_dir flag. These files are not saved by default " +
                 "because they take up ~5-10MB each.")
parser.add_argument('--version', default='1.0',
        help="String to store in the \"version\" field of the generated JSON file")
parser.add_argument('--license',
        default="Creative Commons Attribution (CC-BY 4.0)",
        help="String to store in the \"license\" field of the generated JSON file")
parser.add_argument('--date', default=dt.today().strftime("%m/%d/%Y"),
        help="String to store in the \"date\" field of the generated JSON file; " +
                 "defaults to today's date")

# Rendering options
parser.add_argument('--use_gpu', default=0, type=int,
        help="Setting --use_gpu 1 enables GPU-accelerated rendering using CUDA. " +
                 "You must have an NVIDIA GPU with the CUDA toolkit installed for " +
                 "to work.")
parser.add_argument('--width', default=320, type=int,
        help="The width (in pixels) for the rendered images")
parser.add_argument('--height', default=240, type=int,
        help="The height (in pixels) for the rendered images")
parser.add_argument('--key_light_jitter', default=1.0, type=float,
        help="The magnitude of random jitter to add to the key light position.")
parser.add_argument('--fill_light_jitter', default=1.0, type=float,
        help="The magnitude of random jitter to add to the fill light position.")
parser.add_argument('--back_light_jitter', default=1.0, type=float,
        help="The magnitude of random jitter to add to the back light position.")
parser.add_argument('--camera_jitter', default=0.5, type=float,
        help="The magnitude of random jitter to add to the camera position")
parser.add_argument('--render_num_samples', default=512, type=int,
        help="The number of samples to use when rendering. Larger values will " +
                 "result in nicer images but will cause rendering to take longer.")
parser.add_argument('--render_min_bounces', default=8, type=int,
        help="The minimum number of bounces to use for rendering.")
parser.add_argument('--render_max_bounces', default=8, type=int,
        help="The maximum number of bounces to use for rendering.")
parser.add_argument('--render_tile_size', default=256, type=int,
        help="The tile size to use for rendering. This should not affect the " +
                 "quality of the rendered image but may affect the speed; CPU-based " +
                 "rendering may achieve better performance using smaller tile sizes " +
                 "while larger tile sizes may be optimal for GPU-based rendering.")
parser.add_argument('--clevr_scene_path', default=None,
        help="the path of CLEVR's scene file")

# dist files
parser.add_argument('--color_dist_pth', default=None,
        help="the dir to distribution files")
parser.add_argument('--mat_dist_pth', default=None,
        help="the dir to distribution files")
parser.add_argument('--shape_dist_pth', default=None,
        help="the dir to distribution files")
parser.add_argument('--shape_color_co_dist_pth', default=None,
        help="the dir to distribution files")
parser.add_argument('--is_part', default=1, type=int,
        help="need part or not")
parser.add_argument('--load_scene', default=1, type=int,
        help="when sclevr_scene_path is provided, 0 to only load xyz size, 1 to load the scene")



argv = utils.extract_args()
args = parser.parse_args(argv)
clevr_scene_path = args.clevr_scene_path
if clevr_scene_path is not None:
    print('Loading scenes from ', clevr_scene_path)
    clevr_scene = json.load(open(clevr_scene_path))
    clevr_scene = clevr_scene['scenes']
    

def main(args):
    global color_name_to_rgba, size_mapping, material_mapping, textures_mapping, obj_info
    # Load the property file
    color_name_to_rgba, size_mapping, material_mapping, textures_mapping, obj_info = utils.load_properties_json(args.properties_json, os.path.join(args.shape_dir, 'labels'))

    global shape_dist, mat_dist, color_dist, shape_color_co_dist
    shape_dist, mat_dist, color_dist, shape_color_co_dist = utils.load_dist(args.color_dist_pth, args.mat_dist_pth, args.shape_dist_pth, args.shape_color_co_dist_pth)

    num_digits = 6
    prefix = '%s_%s_' % (args.filename_prefix, args.split)
    img_template = '%s%%0%dd.png' % (prefix, num_digits)
    scene_template = '%s%%0%dd.json' % (prefix, num_digits)
    blend_template = '%s%%0%dd.blend' % (prefix, num_digits)
    img_template = os.path.join(args.output_image_dir, img_template)
    scene_template = os.path.join(args.output_scene_dir, scene_template)
    blend_template = os.path.join(args.output_blend_dir, blend_template)

    if not os.path.isdir(args.output_image_dir):
        os.makedirs(args.output_image_dir)
    if not os.path.isdir(args.output_scene_dir):
        os.makedirs(args.output_scene_dir)
    if args.save_blendfiles == 1 and not os.path.isdir(args.output_blend_dir):
        os.makedirs(args.output_blend_dir)
    
    all_scene_paths = []
    # for i in range(args.num_images):
    
    # for i in range(21):
    #     for t in range(12):
    #         # positive to render normally, else load the scene and only render the mask
    #         scene_idx = i + args.start_idx if args.clevr_scene_path is not None else -1
    #         image_idx = clevr_scene[scene_idx]['image_index'] if (scene_idx >= 0 and args.load_scene) else i+args.start_idx
            
    #         img_path = img_template % (image_idx)
            
    #         scene_path = scene_template % (image_idx)
    #         all_scene_paths.append(scene_path)
    #         blend_path = None
    #         if args.save_blendfiles == 1:
    #             blend_path = blend_template % (image_idx)
    #         num_objects = random.randint(args.min_objects, args.max_objects)
            
    #         obj_idx = i
    #         theta = 30*t
    #         img_path = img_path[:-4]+'_'+str(theta)+'.png'
    #         render_scene(args,
    #             num_objects=num_objects,
    #             output_index=(image_idx),
    #             output_split=args.split,
    #             output_image=img_path,
    #             output_scene=scene_path,
    #             output_blendfile=blend_path,
    #             idx=scene_idx,
    #             obj_idx=obj_idx,
    #             theta=theta
    #         )
    
    for i in range(8):
        for t in range(2):
            # positive to render normally, else load the scene and only render the mask
            scene_idx = i + args.start_idx if args.clevr_scene_path is not None else -1
            image_idx = clevr_scene[scene_idx]['image_index'] if (scene_idx >= 0 and args.load_scene) else i+args.start_idx
            
            img_path = img_template % (image_idx)
            
            scene_path = scene_template % (image_idx)
            all_scene_paths.append(scene_path)
            blend_path = None
            if args.save_blendfiles == 1:
                blend_path = blend_template % (image_idx)
            num_objects = random.randint(args.min_objects, args.max_objects)
            
            obj_idx = 0
            theta = 0
            color_idx = i
            mat_idx = t
            img_path = img_path[:-4]+'_'+str(t)+'.png'
            render_scene(args,
                num_objects=num_objects,
                output_index=(image_idx),
                output_split=args.split,
                output_image=img_path,
                output_scene=scene_path,
                output_blendfile=blend_path,
                idx=scene_idx,
                obj_idx=obj_idx,
                theta=theta,
                mat_idx=mat_idx,
                color_idx=color_idx
            )

    # After rendering all images, combine the JSON files for each scene into a
    # single JSON file.
    # all_scenes = []
    # for scene_path in all_scene_paths:
    #     with open(scene_path, 'r') as f:
    #         all_scenes.append(json.load(f))
    # output = {
    #     'info': {
    #         'date': args.date,
    #         'version': args.version,
    #         'split': args.split,
    #         'license': args.license,
    #     },
    #     'scenes': all_scenes
    # }
    # with open(args.output_scene_file, 'w') as f:
    #     json.dump(output, f)



def render_scene(args,
        num_objects=5,
        output_index=0,
        output_split='none',
        output_image='render.png',
        output_scene='render_json',
        output_blendfile=None,
        idx=-1,
        obj_idx=0,
        color_idx=0,
        mat_idx=0,
        theta=0
    ):

    # Load the main blendfile
    bpy.ops.wm.open_mainfile(filepath=args.base_scene_blendfile)
    bpy.data.objects['Camera'].location = [10,0,6]
    bpy.data.objects['Camera'].rotation_euler=[0,0,0]

    # Load materials
    utils.load_materials(args.material_dir)

    # Set render arguments so we can get pixel coordinates later.
    # We use functionality specific to the CYCLES renderer so BLENDER_RENDER
    # cannot be used.
    render_args = bpy.context.scene.render
    render_args.engine = "CYCLES" #BLENDER_RENDER, CYCLES
    render_args.filepath = output_image
    render_args.resolution_x = args.width
    render_args.resolution_y = args.height
    render_args.resolution_percentage = 100
    render_args.tile_x = args.render_tile_size
    render_args.tile_y = args.render_tile_size
    if args.use_gpu == 1:
        # Blender changed the API for enabling CUDA at some point
        if bpy.app.version < (2, 78, 0):
            bpy.context.user_preferences.system.compute_device_type = 'CUDA'
            bpy.context.user_preferences.system.compute_device = 'CUDA_0'
        else:
            cycles_prefs = bpy.context.user_preferences.addons['cycles'].preferences
            cycles_prefs.compute_device_type = 'CUDA'

    # Some CYCLES-specific stuff
    bpy.data.worlds['World'].cycles.sample_as_light = True
    bpy.context.scene.cycles.blur_glossy = 2.0
    bpy.context.scene.cycles.samples = args.render_num_samples
    bpy.context.scene.cycles.transparent_min_bounces = args.render_min_bounces
    bpy.context.scene.cycles.transparent_max_bounces = args.render_max_bounces
    if args.use_gpu == 1:
        bpy.context.scene.cycles.device = 'GPU'

    # This will give ground-truth information about the scene and its objects
    scene_struct = {
            'split': output_split,
            'image_index': output_index,
            'image_filename': os.path.basename(output_image),
            'objects': [],
            'directions': {},
    }
    

    # Put a plane on the ground so we can compute cardinal directions
    bpy.ops.mesh.primitive_plane_add(radius=5)
    plane = bpy.context.object

    def rand(L):
        return 2.0 * L * (random.random() - 0.5)

    # # Add random jitter to camera position
    # if args.camera_jitter > 0:
    #     for i in range(3):
    #         bpy.data.objects['Camera'].location[i] += rand(args.camera_jitter)

    # Figure out the left, up, and behind directions along the plane and record
    # them in the scene structure
    camera = bpy.data.objects['Camera']
    plane_normal = plane.data.vertices[0].normal
    cam_behind = camera.matrix_world.to_quaternion() * Vector((0, 0, -1))
    cam_left = camera.matrix_world.to_quaternion() * Vector((-1, 0, 0))
    cam_up = camera.matrix_world.to_quaternion() * Vector((0, 1, 0))
    plane_behind = (cam_behind - cam_behind.project(plane_normal)).normalized()
    plane_left = (cam_left - cam_left.project(plane_normal)).normalized()
    plane_up = cam_up.project(plane_normal).normalized()

    # Delete the plane; we only used it for normals anyway. The base scene file
    # contains the actual ground plane.
    utils.delete_object(plane)

    # Save all six axis-aligned directions in the scene struct
    scene_struct['directions']['behind'] = tuple(plane_behind)
    scene_struct['directions']['front'] = tuple(-plane_behind)
    scene_struct['directions']['left'] = tuple(plane_left)
    scene_struct['directions']['right'] = tuple(-plane_left)
    scene_struct['directions']['above'] = tuple(plane_up)
    scene_struct['directions']['below'] = tuple(-plane_up)

    # # Add random jitter to lamp positions
    # if args.key_light_jitter > 0:
    #     for i in range(3):
    #         bpy.data.objects['Lamp_Key'].location[i] += rand(args.key_light_jitter)
    # if args.back_light_jitter > 0:
    #     for i in range(3):
    #         bpy.data.objects['Lamp_Back'].location[i] += rand(args.back_light_jitter)
    # if args.fill_light_jitter > 0:
    #     for i in range(3):
    #         bpy.data.objects['Lamp_Fill'].location[i] += rand(args.fill_light_jitter)

    # Now make some random objects
    objects, blender_objects = add_object(scene_struct, num_objects, args, camera, obj_idx=obj_idx, theta=theta, color_idx=color_idx, mat_idx=mat_idx, idx=idx)


    # def get_mat_pass_index():
    #     mat_indices = {}
    #     mm_idx = 1
    #     for i, obj in enumerate(blender_objects):   
    #         obj_name = obj.name.split('_')[0]
    #         mat_indices[obj.name] = (i, -1, mm_idx)
    #         mm_idx += 1
    #         obj.pass_index = i+1
    #         if args.is_part:
    #             for pi, part_name in enumerate(obj_info['info_part'][obj_name]):
    #                 mat_indices[obj.name+'.'+part_name] = (i, pi, mm_idx)
    #                 mm_idx += 1
                    
    #         for mi in range(len(obj.data.materials)):
    #             mat = obj.data.materials[mi]
    #             if not mat.name.startswith(obj_name): # original materials
    #                 mat.pass_index = mat_indices[obj.name][2]
    #             elif args.is_part:
    #                 part_name = mat.name.split('.')[1]
    #                 mat.pass_index = mat_indices[obj.name+'.'+part_name][2]
    #     mat_indices = {v[2]:(v[0], v[1], k) for k,v in mat_indices.items()}
    #     return mat_indices

    
    # def build_rendermask_graph(mat_indices):
    #     # switch on nodes
    #     bpy.context.scene.use_nodes = True
    #     tree = bpy.context.scene.node_tree
    #     links = tree.links
        
    #     # clear default nodes
    #     for n in tree.nodes:
    #         tree.nodes.remove(n)
            
    #     # create input render layer node
    #     rl = tree.nodes.new('CompositorNodeRLayers')      
    #     rl.location = 185,285

    #     scene = bpy.context.scene
    #     nodes = scene.node_tree.nodes

    #     render_layers = nodes['Render Layers']

    #     num_mat = len(mat_indices)
    #     num_obj = len(blender_objects)
        
    #     ofile_node = nodes.new("CompositorNodeOutputFile")
    #     path = '../output/tmp'
    #     ofile_node.base_path = path
    #     ofile_node.file_slots.remove(ofile_node.inputs[0])
        
    #     idmask_nodes = [nodes.new("CompositorNodeIDMask") for _ in range(num_mat)]
    #     for _i, o_node in enumerate(idmask_nodes):    
    #         o_node.index = _i + 1
            
    #     idmask_obj_nodes = [nodes.new("CompositorNodeIDMask") for _ in range(num_obj)]
    #     for _i, o_node in enumerate(idmask_obj_nodes):    
    #         o_node.index = _i + 1
            
    #     part_colors = {}
    #     rgb_nodes = [nodes.new("CompositorNodeRGB") for _ in range(num_mat)]
    #     for _i, rgb_node in enumerate(rgb_nodes):
    #         obj_idx, mat_idx, mat_name = mat_indices[_i+1]
    #         r, g, b = 0.05*(obj_idx+1), 0.1*(mat_idx//5 + 1), 0.1*(mat_idx%5 + 1)
    #         part_colors[mat_name] = (r, g, b)
    #         rgb_node.outputs[0].default_value[:3] = (r, g, b)
        
    #     mix_nodes = [nodes.new("CompositorNodeMixRGB") for _ in range(num_mat)]
    #     for _i, o_node in enumerate(mix_nodes):    
    #         o_node.blend_type = "MULTIPLY"
            
    #     add_nodes = [nodes.new("CompositorNodeMixRGB") for _ in range(num_mat-1)]
    #     for _i, o_node in enumerate(add_nodes):    
    #         o_node.blend_type = "ADD"
        
    #     bpy.data.scenes['Scene'].render.layers['RenderLayer'].use_pass_material_index = True
    #     bpy.data.scenes['Scene'].render.layers['RenderLayer'].use_pass_object_index = True

    #     for mat_idx in range(num_mat):
    #         scene.node_tree.links.new(
    #             render_layers.outputs['IndexMA'],
    #             idmask_nodes[mat_idx].inputs[0]
    #             )
    #         scene.node_tree.links.new(
    #             idmask_nodes[mat_idx].outputs[0],
    #             mix_nodes[mat_idx].inputs[1]
    #             )
    #         scene.node_tree.links.new(
    #             rgb_nodes[mat_idx].outputs[0],
    #             mix_nodes[mat_idx].inputs[2]
    #             )
    #         # ofile_node.file_slots.new("part_" + mat_indices[mat_idx+1] + '_')
    #         # scene.node_tree.links.new(
    #         #     idmask_nodes[mat_idx].outputs[0],
    #         #     ofile_node.inputs[mat_idx]
    #         #     )
            
    #     # for obj_idx in range(num_obj):
    #     #     scene.node_tree.links.new(
    #     #         render_layers.outputs['IndexOB'],
    #     #         idmask_obj_nodes[obj_idx].inputs[0]
    #     #         )
    #     #     ofile_node.file_slots.new("obj_" + str(blender_objects[obj_idx].name) + '_')
    #     #     scene.node_tree.links.new(
    #     #         idmask_obj_nodes[obj_idx].outputs[0],
    #     #         ofile_node.inputs[num_mat+obj_idx]
    #     #         )
            
    #     mat_idx = 0
    #     scene.node_tree.links.new(
    #         mix_nodes[mat_idx+1].outputs[0],
    #         add_nodes[mat_idx].inputs[1]
    #         )
    #     scene.node_tree.links.new(
    #         mix_nodes[mat_idx].outputs[0],
    #         add_nodes[mat_idx].inputs[2]
    #         )
    #     for mat_idx in range(1, num_mat-1):
    #         scene.node_tree.links.new(
    #             mix_nodes[mat_idx+1].outputs[0],
    #             add_nodes[mat_idx].inputs[1]
    #             )
    #         scene.node_tree.links.new(
    #             add_nodes[mat_idx-1].outputs[0],
    #             add_nodes[mat_idx].inputs[2]
    #             )
        
    #     ofile_node.file_slots.new("mask_all_{}_".format(output_index))
    #     scene.node_tree.links.new(
    #         add_nodes[-1].outputs[0],
    #         ofile_node.inputs[0]
    #         )
        
    #     return part_colors
            
    # mat_indices = get_mat_pass_index()
    # json_pth = '../output/tmp/mat_indices_{}.json'.format(output_index)
    # json.dump(mat_indices, open(json_pth, 'w'))
    # part_colors = build_rendermask_graph(mat_indices)




    # Render the scene and dump the scene data structure
    # scene_struct['objects'] = objects
    # scene_struct['relationships'] = compute_all_relationships(scene_struct)
    while True:
        try:
            bpy.ops.render.render(write_still=True)
            break
        except Exception as e:
            print(e)
            
    
    #save_as_json
    # cmd = ['python','./restore_img2json.py', str(output_index)]
    # res = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    # res.wait()
    # if res.returncode != 0:
    #     print("  os.wait:exit status != 0\n")
    #     result = res.stdout.read()
    #     print ("after read: {}".format(result))
    #     raise Exception('error in img2json')

    # obj_mask_box = json.load(open('/tmp/obj_mask_{}.json'.format(output_index)))
    # _path = '/tmp/obj_mask_{}.json'.format(output_index)
    # os.system('rm ' + _path)
    
    # scene_struct['obj_mask_box'] = obj_mask_box
    

    # with open(output_scene, 'w') as f:
    #     # json.dump(scene_struct, f, indent=2)
    #     json.dump(scene_struct, f)

    if output_blendfile is not None:
        bpy.ops.wm.save_as_mainfile(filepath=output_blendfile)

def add_object(scene_struct, num_objects, args, camera, obj_idx=0, theta=0, color_idx=0, mat_idx=0, idx=-1):
    """
    Add random objects to the current blender scene
    """

    num_objects = 1
    
    positions = []
    objects = []
    blender_objects = []
    obj_pointer = []
    
    print('adding', num_objects, 'objects.')
    
    # Choose a random size
    size_name, r = random.choice(size_mapping)
    size_name, r = 'large', 6.0

    # Choose random shape
    # obj_name, obj_pth = random.choice(list(obj_info['info_pth'].items()))
    obj_name, obj_pth = "suv", "car/473dd606c5ef340638805e546aa28d99"
    # obj_name, obj_pth = sorted(obj_info['info_pth'].items(), key=lambda b: b[1])[obj_idx]
            

    # # Actually add the object to the scene
    # x = random.uniform(-3, 3)
    # y = random.uniform(-3, 3)
    # # Choose random orientation for the object.
    # theta = 360.0 * random.random()
    x, y = 0, 0
    theta = theta
    
    loc = (x, y, -r*obj_info['info_z'][obj_name])
    current_obj = utils.add_object(args.model_dir, obj_name, obj_pth, r, loc, theta=theta)
    obj = bpy.context.object
    blender_objects.append(obj)
    positions.append((obj_name, x, y, r, theta))

    # Attach a random color
    # rgba=(1,0,0,1)
    # mat_name, mat_name_out = random.choice(material_mapping)
    mat_name, mat_name_out = sorted(list(material_mapping))[mat_idx]
    # mat_name, mat_name_out = 'Rubber', 'rubber'

    # color_name, rgba = random.choice(list(color_name_to_rgba.items()))
    color_name, rgba = sorted(list(color_name_to_rgba.items()))[color_idx]
    # color_name  = 'gray'
    # rgba = color_name_to_rgba[color_name]
    
    # texture = random.choice(textures_mapping)
    texture = None
    mat_freq = {"large":60, "small":30}[size_name]
    # if texture=='checkered':
    #     mat_freq = mat_freq / 2
    utils.modify_color(current_obj, material_name=mat_name, mat_list=obj_info['info_material'][obj_name], 
                        color=rgba,
                        texture=texture, mat_freq=mat_freq)

    # part_pth = '../output/human_study/masks/' + str(obj_idx) + '_' + str(theta) + '.png'
    part_pth = 'output/tmp.png'
    object_colors, part_colors = render_shadeless(blender_objects, path=part_pth, is_part=True, obj_info=obj_info)
    
    # Check that all objects are at least partially visible in the rendered image
    # all_visible, visible_parts = check_visibility(blender_objects, args.min_pixels_per_object, args.min_pixels_per_part, is_part=True, obj_info=obj_info)

    # if args.is_part:
    #     for i in range(num_objects):
    #         # randomize part material
            
    #         current_obj = obj_pointer[i]
    #         obj_name = current_obj.name.split('_')[0]
    #         color_name = objects[i]['color']
    #         size_name = objects[i]['size']
    #         part_list = visible_parts[current_obj.name]
    #         part_names = random.sample(part_list, min(3, len(part_list)))
    #         # part_name = random.choice(obj_info['info_part'][obj_name])
    #         part_record = {}
    #         for part_name in part_names:
    #             while True:
    #                 part_color_name, part_rgba = random.choice(list(color_name_to_rgba.items()))
    #                 if part_color_name != color_name:
    #                     break
    #             part_name = part_name.split('.')[0]
    #             # if part_name not in obj_info['info_part_labels'][obj_name]:
    #             #     print(part_name, obj_name, '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    #             #     continue
    #             part_verts_idxs = obj_info['info_part_labels'][obj_name][part_name]
    #             mat_name, mat_name_out = random.choice(material_mapping)
    #             texture = random.choice(textures_mapping)
    #             mat_freq = {"large":60, "small":30}[size_name]
    #             if texture=='checkered':
    #                 mat_freq = mat_freq / 2
    #             utils.modify_part_color(current_obj, part_name, part_verts_idxs, mat_list=obj_info['info_material'][obj_name], 
    #                                     material_name=mat_name, color_name=part_color_name, color=part_rgba,
    #                                     texture=texture, mat_freq=mat_freq)
    #             part_record[part_name] = {
    #                     "color": part_color_name,
    #                     "material": mat_name_out,
    #                     "size": objects[i]['size'],
    #                     "texture": texture
    #                     }
                
    #     objects[i]['parts'] = part_record

    return objects, blender_objects



def check_visibility(blender_objects, min_pixels_per_object, min_pixels_per_part=None, is_part=False, obj_info=None):
    """
    Check whether all objects in the scene have some minimum number of visible
    pixels; to accomplish this we assign random (but distinct) colors to all
    objects, and render using no lighting or shading or antialiasing; this
    ensures that each object is just a solid uniform color. We can then count
    the number of pixels of each color in the output image to check the visibility
    of each object.

    Returns True if all objects are visible and False otherwise.
    """
    f, path = tempfile.mkstemp(suffix='.png')
    path = 'output/tmp.png'
    object_colors, part_colors = render_shadeless(blender_objects, path=path, is_part=is_part, obj_info=obj_info)
    img = bpy.data.images.load(path)
    
    def srgb_to_linear(x, mod=0.1):
        if x <=0.04045 :
            y = x / 12.92
        else:
            y = ((x + 0.055) / 1.055) ** 2.4
        if mod is not None:
            y = round(y / mod) * mod
        return y
    
    p = list(img.pixels)
    color_count_raw = Counter((p[i], p[i+1], p[i+2], p[i+3]) for i in range(0, len(p), 4))
    color_count_raw.pop(color_count_raw.most_common(1)[0][0])
    color_count_part = {(srgb_to_linear(k[0]), srgb_to_linear(k[1]), srgb_to_linear(k[2])):v for k,v in color_count_raw.items()}
    color_count_part = Counter(color_count_part)
    color_count_obj = Counter()
    for k,v in color_count_part.items():
        color_count_obj[k[0]] += v
    # os.remove(path)
    all_visible = True
    visible_parts = {obj.name:[] for obj in blender_objects}
    if len(color_count_obj) != len(blender_objects):
        all_visible = False
        # return False, visible_parts
    for _, count in color_count_obj.most_common():
        if count < min_pixels_per_object:
            all_visible = False
            # return False, visible_parts
    if is_part:
        for p_name, p_color in part_colors.items():
            try:
                obj_name, part_name = p_name.split('..')
            except:
                print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                print(p_name)
                pdb.set_trace()
            if color_count_part[p_color] > min_pixels_per_part:
                visible_parts[obj_name].append(part_name)
    return all_visible, visible_parts



def render_shadeless(blender_objects, path='flat.png', is_part=False, obj_info=None):
    """
    Render a version of the scene with shading disabled and unique materials
    assigned to all objects, and return a set of all colors that should be in the
    rendered image. The image itself is written to path. This is used to ensure
    that all objects will be visible in the final rendered scene.
    """
    render_args = bpy.context.scene.render

    # Cache the render args we are about to clobber
    old_filepath = render_args.filepath
    old_engine = render_args.engine
    old_use_antialiasing = render_args.use_antialiasing

    # Override some render settings to have flat shading
    render_args.filepath = path
    render_args.engine = 'BLENDER_RENDER'
    render_args.use_antialiasing = False
    
    render_args.resolution_x = 640
    render_args.resolution_y = args.height

    # Move the lights and ground to layer 2 so they don't render
    utils.set_layer(bpy.data.objects['Lamp_Key'], 2)
    utils.set_layer(bpy.data.objects['Lamp_Fill'], 2)
    utils.set_layer(bpy.data.objects['Lamp_Back'], 2)
    utils.set_layer(bpy.data.objects['Ground'], 2)

    # Add random shadeless materials to all objects
    object_colors = set()
    part_colors = {}
    old_materials = []
    
    random.seed(1000)
    # color_json = json.load(open('data/colors.json', 'r'))
    # cssr_colors = color_json['CSS4_COLORS']
    # random.shuffle(cssr_colors)
    # color_list = color_json['TABLEAU_COLORS'] + cssr_colors
    
    color_list = np.load('data/pascal_seg_colormap.npy').tolist()[2:]
    
    for i, obj in enumerate(blender_objects):
        # need to use iteration to copy by value, otherwise just a pointer is copied
        old_materials.append([])
        for mi in range(len(obj.data.materials)):
            old_materials[i].append(obj.data.materials[mi])
        bpy.ops.material.new()
        mat = bpy.data.materials['Material']
        mat.name = 'Material_%d' % i
        # r,g,b = 0.1 * i, 0, 0
        # r,g,b = random.random(), random.random(), random.random()
        r, g, b = color_list[0]
        mat.diffuse_color = [r, g, b]
        object_colors.add((r, g, b))
        mat.use_shadeless = True
        if not is_part:
            for mi in range(len(obj.data.materials)):
                obj.data.materials[mi] = mat
        else:
            assert obj_info is not None
            obj_name = obj.name.split('_')[0]
            for pi, part_name in enumerate(obj_info['info_part'][obj_name]):
                bpy.ops.material.new()
                new_mat = bpy.data.materials['Material']
                new_mat.name =  obj.name + '..' + part_name
                # pcolor = obj_info['colors'][pi][1]
                # new_mat.diffuse_color = (r/2.+pcolor[0]/2., g/2.+pcolor[1]/2., b/2.+pcolor[2]/2.)
                # r, g, b = 0.3*pi, 0.16*(pi//5 + 1), 1 - 0.16*(pi%5 + 1)
                # r, g, b = random.random(), random.random(), random.random()
                r, g, b = color_list[pi+1]
                new_mat.diffuse_color = (r, g, b)
                pc = new_mat.diffuse_color
                part_colors[new_mat.name] = (r, g, b)
                new_mat.use_shadeless = True
            for mi in range(len(obj.data.materials)):
                orig_mat = obj.data.materials[mi]
                if not orig_mat.name.startswith(obj_name): # original materials
                    obj.data.materials[mi] = mat
                else:
                    part_name = orig_mat.name.split('.')[1]
                    obj.data.materials[mi] = bpy.data.materials[obj.name + '..' + part_name]
            
    # Render the scene
    bpy.ops.render.render(write_still=True)
    print('render still done 1')
    
    # Undo the above; first restore the materials to objects
    for mat, obj in zip(old_materials, blender_objects):
        for mi in range(len(obj.data.materials)):
            obj.data.materials[mi] = mat[mi]
        # obj.data.materials = mat
    
    print('render still done 2')

    # Move the lights and ground back to layer 0
    utils.set_layer(bpy.data.objects['Lamp_Key'], 0)
    utils.set_layer(bpy.data.objects['Lamp_Fill'], 0)
    utils.set_layer(bpy.data.objects['Lamp_Back'], 0)
    utils.set_layer(bpy.data.objects['Ground'], 0)

    # Set the render settings back to what they were
    render_args.filepath = old_filepath
    render_args.engine = old_engine
    render_args.use_antialiasing = old_use_antialiasing

    print('render still done 3')
    return object_colors, part_colors
                            



if __name__ == '__main__':
    if INSIDE_BLENDER:
        # Run normally
        argv = utils.extract_args()
        args = parser.parse_args(argv)
        main(args)
    elif '--help' in sys.argv or '-h' in sys.argv:
        parser.print_help()
    else:
        print('This script is intended to be called from blender like this:')
        print()
        print('blender --background --python render_images.py -- [args]')
        print()
        print('You can also run as a standalone python script to view all')
        print('arguments like this:')
        print()
        print('python render_images.py --help')
