# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import sys, random, os
from tokenize import group
import bpy, bpy_extras, bmesh
import json
import pdb
import math
import re
from material_cycles_converter import AutoNode
from mathutils import Vector
import numpy as np


"""
Some utility functions for interacting with Blender
"""


def extract_args(input_argv=None):
    """
    Pull out command-line arguments after "--". Blender ignores command-line flags
    after --, so this lets us forward command line arguments from the blender
    invocation to our own script.
    """
    if input_argv is None:
        input_argv = sys.argv
    output_argv = []
    if '--' in input_argv:
        idx = input_argv.index('--')
        output_argv = input_argv[(idx + 1):]
    return output_argv


def parse_args(parser, argv=None):
    return parser.parse_args(extract_args(argv))


# I wonder if there's a better way to do this?
def delete_object(obj):
    """ Delete a specified blender object """
    for o in bpy.data.objects:
        o.select = False
    obj.select = True
    bpy.ops.object.delete()


def get_camera_coords(cam, pos):
    """
    For a specified point, get both the 3D coordinates and 2D pixel-space
    coordinates of the point from the perspective of the camera.

    Inputs:
    - cam: Camera object
    - pos: Vector giving 3D world-space position

    Returns a tuple of:
    - (px, py, pz): px and py give 2D image-space coordinates; pz gives depth
        in the range [-1, 1]
    """
    scene = bpy.context.scene
    x, y, z = bpy_extras.object_utils.world_to_camera_view(scene, cam, pos)
    scale = scene.render.resolution_percentage / 100.0
    w = int(scale * scene.render.resolution_x)
    h = int(scale * scene.render.resolution_y)
    px = int(round(x * w))
    py = int(round(h - y * h))
    return (px, py, z), (w, h)


def set_layer(obj, layer_idx):
    """ Move an object to a particular layer """
    # Set the target layer to True first because an object must always be on
    # at least one layer.
    obj.layers[layer_idx] = True
    for i in range(len(obj.layers)):
        obj.layers[i] = (i == layer_idx)


def add_object(object_dir, name, obj_pth, scale, loc, theta=0):
    """
    Load an object from a file. We assume that in the directory object_dir, there
    is a file named "$name.blend" which contains a single object named "$name"
    that has unit size and is centered at the origin.

    - scale: scalar giving the size that the object should be in the scene
    - loc: tuple (x, y) giving the coordinates on the ground plane where the
        object should be placed.
    """
    # First figure out how many of this object are already in the scene so we can
    # give the new object a unique name
    count = 0
    for obj in bpy.data.objects:
        if obj.name.startswith(name):
            count += 1

    # Add the obj, and tet the name of the added object
    existings = list(bpy.data.objects)
    # filename = os.path.join(object_dir, obj_pth, 'models/model_normalized.obj')
    # filename = '/home/zhuowan/zhuowan/SuperClevr/render-3d-segmentation/CGPart/models/car/d4251f9cf7f1e0a7cac1226cb3e860ca/models/model_normalized.obj'
    # bpy.ops.import_scene.obj(filepath=filename,use_split_groups=False,use_split_objects=False)
    filepath = os.path.join(object_dir, obj_pth.split('/')[0]+'_'+name+'.blend')
    inner_path = 'Object'
    bpy.ops.wm.append(
        filepath=os.path.join(filepath, inner_path, name),
        directory=os.path.join(filepath, inner_path),
        filename=name
        )
    added_name = list(set(bpy.data.objects) - set(existings))[0].name

    # Give it a new name to avoid conflicts
    new_name = '%s_%d' % (name, count)
    bpy.data.objects[added_name].name = new_name

    # Set the new object as active, then rotate, scale, and translate it
    bpy.context.scene.objects.active = bpy.data.objects[new_name]
    bpy.context.object.rotation_euler[2] = theta / 180. * math.pi
    bpy.ops.transform.resize(value=(scale, scale, scale))
    
    ## Get the min z, and move the obj to the ground
    # # find the min z of the obj
    # zverts = []
    current_obj = bpy.context.scene.objects.active
    # # get all z coordinates of the vertices
    # for face in current_obj.data.polygons:
    #     verts_in_face = face.vertices[:]
    #     for vert in verts_in_face:
    #         local_point = current_obj.data.vertices[vert].co
    #         world_point = current_obj.matrix_world * local_point
    #         zverts.append(world_point[2])
    # # move the obj
    # x, y = loc
    # bpy.ops.transform.translate(value=(x, y, -min(zverts)))
    
    # Move the obj to loc
    current_obj.location += Vector(loc)
    # bpy.ops.transform.translate(value=loc)
    return current_obj

# # old version (without converting to CYCLES ENGINE)
# # modify the color of current_obj. mat_list: list of mats
# def modify_color(current_obj, mat_list, color):
#     # When different objects has same mat names, the names will be automatically renamed to 'XXX.002', 'XXX.003' etc
#     for mat_name in current_obj.data.materials.keys():
#         if mat_name.split('.')[0] in mat_list:
#             print(current_obj.name, mat_name)
#             # current_obj.data.materials[mat_name].diffuse_color=color #cannot use this in CYCLES nodes
#             for node in current_obj.data.materials[mat_name].node_tree.nodes:
#                 if node.name.startswith('Diffuse BSDF'):
#                     assert(node.name == 'Diffuse BSDF')
#                     assert(len(node.inputs['Color'].links) == 1)
#                     assert(node.inputs['Color'].links[0].from_node.name.startswith('Mix'))
#                     node.inputs['Color'].links[0].from_node.inputs['Color1'].default_value[0:3] = color[0:3]
                    
# # modify the color of current_obj. mat_list: list of mats
# def modify_color(current_obj, mat_list, color):
#     # AutoNode(True) # convert the materials of current obj
#     # When different objects has same mat names, the names will be automatically renamed to 'XXX.002', 'XXX.003' etc
#     for mat_name in current_obj.data.materials.keys():
#         # if mat_name.split('.')[0] not in mat_list:
#         #     continue
#         ## current_obj.data.materials[mat_name].diffuse_color=color #cannot use this in CYCLES nodes
#         # for node in current_obj.data.materials[mat_name].node_tree.nodes:
#         #     if node.name.startswith('Diffuse BSDF'):
#         #         assert(node.name == 'Diffuse BSDF')
#         #         assert(node.inputs[0].name == 'Color')
#         #         node.inputs[0].default_value[0:3] = color[0:3]
#         mat = current_obj.data.materials[mat_name]
#         assert mat.node_tree.nodes[1].name in ['Diffuse BSDF', 'Transparent BSDF']
#         mat.node_tree.nodes[1].inputs[0].default_value[0:3] = color[0:3]

# modify the color of current_obj. mat_list: list of mats, with choice of material
# modified from the original add_material function
def modify_color(current_obj, material_name, mat_list, color, texture, mat_freq):
    # AutoNode(True) # convert the materials of current obj
    # When different objects has same mat names, the names will be automatically renamed to 'XXX.002', 'XXX.003' etc
    for i, mat in enumerate(current_obj.data.materials):
        mat_name = mat.name
        # if mat_name.split('.')[0] not in mat_list:
        #     continue
        ## current_obj.data.materials[mat_name].diffuse_color=color #cannot use this in CYCLES nodes
        # for node in current_obj.data.materials[mat_name].node_tree.nodes:
        #     if node.name.startswith('Diffuse BSDF'):
        #         assert(node.name == 'Diffuse BSDF')
        #         assert(node.inputs[0].name == 'Color')
        #         node.inputs[0].default_value[0:3] = color[0:3]
        assert mat.node_tree.nodes[1].name in ['Diffuse BSDF', 'Transparent BSDF']
        if mat.node_tree.nodes[1].name == 'Transparent BSDF':
            mat.node_tree.nodes[1].inputs[0].default_value[0:3] = color[0:3]
        else:
            new_mat = add_new_mat(mat_name, material_name, color, texture, mat_freq)
            current_obj.data.materials[i] = new_mat

def modify_mat(mat, color, mat_freq):
    group_node = mat.node_tree.nodes['Group']
    group_node.inputs['Color'].default_value = color
    if 'texture' in mat.node_tree.nodes:
        texture_node = mat.node_tree.nodes['texture']
        texture_node.inputs['Color'].default_value = color
        if 'Color2' in texture_node.inputs:
            texture_node.inputs['Color2'].default_value = [c/2 for c in color[:3]] + [1.0]
        if "Checker Texture" in texture_node.node_tree.nodes:
            texture_node.node_tree.nodes["Checker Texture"].inputs[3].default_value = mat_freq


def add_new_mat(mat_name, material_name, color, texture=None, mat_freq=20):
    """
    Create a new material and assign it to the active object. "name" should be the
    name of a material that has been previously loaded using load_materials.
    """
    # Create a new material; it is not attached to anything and
    # it will be called "Material"
    bpy.ops.material.new()

    # Get a reference to the material we just created and rename it;
    # then the next time we make a new material it will still be called
    # "Material" and we will still be able to look it up by name
    new_mat = bpy.data.materials['Material']
    new_mat.name = mat_name+'.'+str(texture)+'_'+material_name

    # Find the output node of the new material
    output_node = new_mat.node_tree.nodes['Material Output']

    # Add a new GroupNode to the node tree of the active material,
    # and copy the node tree from the preloaded node group to the
    # new group node. This copying seems to happen by-value, so
    # we can create multiple materials of the same type without them
    # clobbering each other
    group_node = new_mat.node_tree.nodes.new('ShaderNodeGroup')
    group_node.node_tree = bpy.data.node_groups[material_name]
    
    
    # # texture node
    if texture is not None:
        texture_node = new_mat.node_tree.nodes.new('ShaderNodeGroup')
        texture_node.name = 'texture'
        # texture_name = random.choice(['stripped', 'checkered'])
        texture_name = texture
        texture_node.node_tree = bpy.data.node_groups[texture_name]
        new_mat.node_tree.links.new(
                group_node.outputs['Shader'], 
                texture_node.inputs['Shader'], 
        )          
    else:
        texture_node = group_node
        
    modify_mat(new_mat, color, mat_freq)

    # Wire the output of the new group node to the input of
    # the MaterialOutput node
    new_mat.node_tree.links.new(
            texture_node.outputs['Shader'],
            output_node.inputs['Surface'], 
    )
    return new_mat



# # modify the color of specific part
# # based on part labels (iteration to select mesh and modify color)
# def _modify_part_color(current_obj, part_name, part_verts_idxs, mat_list, color_name, color):
#     bpy.ops.object.mode_set(mode='EDIT')
#     bm = bmesh.from_edit_mesh(current_obj.data)
#     bpy.ops.mesh.select_all(action='DESELECT')
#     for face in bm.faces:
#         flag = True
#         for v in face.verts:
#             if v.index not in part_verts_idxs:
#                 flag = False
#                 break
#         if flag:
#             face.select = True
#             mat_name = current_obj.data.materials[face.material_index].name
#             if mat_name.split('.')[0] not in mat_list:
#                 continue
#             new_mat_name = mat_name+'.'+color_name
#             # if the new material does not exist, create it
#             if new_mat_name not in bpy.data.materials.keys():
#                 # new_mat = bpy.data.materials.new(new_mat_name)
#                 new_mat = bpy.data.materials[mat_name].copy()
#                 new_mat.name = new_mat_name
#                 assert new_mat.node_tree.nodes[1].name in ['Diffuse BSDF', 'Transparent BSDF']
#                 new_mat.node_tree.nodes[1].inputs[0].default_value[0:3] = color[0:3]
#                 current_obj.data.materials.append(new_mat)
#             face.material_index = current_obj.data.materials.keys().index(new_mat_name)
#     bpy.ops.object.mode_set(mode='OBJECT')
    
# modify the color of specific part
# after preprocessing, by modify part materials
def modify_part_color(current_obj, part_name, part_verts_idxs, mat_list, material_name, color_name, color, texture, mat_freq):
    for i, mat in enumerate(current_obj.data.materials):
        split_mat_name = mat.name.split('.')
        if len(split_mat_name) < 2:
            continue
        if split_mat_name[1] == part_name:
            assert mat.node_tree.nodes[1].name in ['Diffuse BSDF', 'Transparent BSDF']
            if mat.node_tree.nodes[1].name == 'Transparent BSDF':
                mat.node_tree.nodes[1].inputs[0].default_value[0:3] = color[0:3]
            elif split_mat_name[-1] == str(texture)+'_'+material_name:
                modify_mat(mat, color, mat_freq)
            else:
                new_mat = add_new_mat('.'.join(split_mat_name[:-1]), material_name, color, texture, mat_freq)
                current_obj.data.materials[i] = new_mat

# load properties json
def load_properties_json(properties_json, label_dir):
    with open(properties_json, 'r') as f:
        properties = json.load(f)
    # remove the car addi from the loaded json file
    properties['shapes'].pop('addi')
    properties['info_material'].pop('addi')
    
    # properties['shapes'].pop('wagon') #TODO
    # properties['info_material'].pop('wagon')
    color_name_to_rgba = {}
    for name, rgb in properties['colors'].items():
        rgba = [float(c) / 255.0 for c in rgb] + [1.0]
        color_name_to_rgba[name] = rgba
        
    material_mapping = [(v, k) for k, v in properties['materials'].items()]
    
    textures = properties['textures']
    textures = [None if t=='None' else t for t in textures]
    
    size_mapping = list(properties['sizes'].items())
    obj_info = {}
    obj_info['info_pth'] = properties['shapes']
    obj_info['info_z'] = properties['info_z']
    obj_info['info_box'] = properties['info_box']
    obj_info['info_material'] = {k:v.split(',') for k,v in properties['info_material'].items()}
    hier_map = {v:k for k,vs in properties['info_hier'].items() for v in vs }
    obj_info['orig_info_part'] = {k:properties['orig_info_part'][v] for k,v in hier_map.items()}
    obj_info['orig_info_part_labels'] = {}
    for k,v in properties['shapes'].items():
        label_file_pth = os.path.join(label_dir, v.replace('aeroplane', 'airplane')+'.json')          
        obj_info['orig_info_part_labels'][k] = json.load(open(label_file_pth, 'r'))

    def merge_parts():
        obj_info['info_part'] = {}
        for obj_name in obj_info['orig_info_part']:
            obj_info['info_part'][obj_name] = set()
            for i, part_name in enumerate(obj_info['orig_info_part'][obj_name]):
                new_part_name = re.sub('_\d','_s', part_name)
                if '_s' in new_part_name and new_part_name[:-2] in obj_info['info_part'][obj_name]:
                    new_part_name = new_part_name + '_s'
                obj_info['info_part'][obj_name].add(new_part_name)
            to_remove = []
            for part_name in obj_info['info_part'][obj_name]:
                if part_name + '_s' in obj_info['info_part'][obj_name]:
                    to_remove.append(part_name)
            for part_name in to_remove:
                obj_info['info_part'][obj_name].pop(part_name)
            obj_info['info_part'][obj_name] = list(obj_info['info_part'][obj_name])

        obj_info['info_part_labels'] = {}
        for obj_name in obj_info['orig_info_part_labels']:
            obj_info['info_part_labels'][obj_name] = {}
            for part_name, part_verts in obj_info['orig_info_part_labels'][obj_name].items():
                new_part_name = re.sub('_\d','_s', part_name)
                if new_part_name not in obj_info['info_part_labels'][obj_name]:
                    obj_info['info_part_labels'][obj_name][new_part_name] = []
                obj_info['info_part_labels'][obj_name][new_part_name].extend(part_verts)
            to_remove = []
            for part_name, part_verts in obj_info['info_part_labels'][obj_name].items():
                if part_name + '_s' in obj_info['info_part_labels'][obj_name]:
                    obj_info['info_part_labels'][obj_name][part_name + '_s'].extend(part_verts)
                    to_remove.append(part_name)
            for part_name in to_remove:
                obj_info['info_part_labels'][obj_name].pop(part_name)
    merge_parts()
    
    obj_info['info_part'] = json.load(open('data/save_models_1/part_dict.json', 'r'))
    obj_info['colors'] = json.load(open('data/colors.json', 'r'))['CSS4_COLORS']
    
    # limited_objs = ['sedan']
    # objs = list(obj_info['info_pth'].keys())
    # for k in obj_info:
    #     for name in objs:
    #         if name not in limited_objs:
    #             obj_info[k].pop(name)
    return color_name_to_rgba, size_mapping, material_mapping, textures, obj_info


def load_dist(color_dist_pth, mat_dist_pth, shape_dist_pth, shape_color_co_dist_pth):
    shape_dist, mat_dist, color_dist, shape_color_co_dist = None, None, None, None
    if color_dist_pth is not None:
        color_dist = dict(np.load(color_dist_pth))
    if mat_dist_pth is not None:
        mat_dist = dict(np.load(mat_dist_pth))
    if shape_dist_pth is not None:
        shape_dist = dict(np.load(shape_dist_pth))
    if shape_color_co_dist_pth is not None:
        shape_color_co_dist = dict(np.load(shape_color_co_dist_pth))
        num_shape, num_color = shape_color_co_dist['dist'].shape
        shape_color_co_dist['shape_idx_map'] = {name:i for i,name in enumerate(shape_color_co_dist['names'][:num_shape])}
        shape_color_co_dist['colors'] = shape_color_co_dist['names'][-num_color:]
    return shape_dist, mat_dist, color_dist, shape_color_co_dist

        
def load_materials(material_dir):
    """
    Load materials from a directory. We assume that the directory contains .blend
    files with one material each. The file X.blend has a single NodeTree item named
    X; this NodeTree item must have a "Color" input that accepts an RGBA value.
    """
    for fn in os.listdir(material_dir):
        if not fn.endswith('.blend'): continue
        name = os.path.splitext(fn)[0]
        filepath = os.path.join(material_dir, fn, 'NodeTree', name)
        bpy.ops.wm.append(filename=filepath)


def add_material(name, **properties):
    """
    Create a new material and assign it to the active object. "name" should be the
    name of a material that has been previously loaded using load_materials.
    """
    # Figure out how many materials are already in the scene
    mat_count = len(bpy.data.materials)

    # Create a new material; it is not attached to anything and
    # it will be called "Material"
    bpy.ops.material.new()

    # Get a reference to the material we just created and rename it;
    # then the next time we make a new material it will still be called
    # "Material" and we will still be able to look it up by name
    mat = bpy.data.materials['Material']
    mat.name = 'Material_%d' % mat_count

    # Attach the new material to the active object
    # Make sure it doesn't already have materials
    obj = bpy.context.active_object
    assert len(obj.data.materials) == 0
    obj.data.materials.append(mat)

    # Find the output node of the new material
    output_node = None
    for n in mat.node_tree.nodes:
        if n.name == 'Material Output':
            output_node = n
            break

    # Add a new GroupNode to the node tree of the active material,
    # and copy the node tree from the preloaded node group to the
    # new group node. This copying seems to happen by-value, so
    # we can create multiple materials of the same type without them
    # clobbering each other
    group_node = mat.node_tree.nodes.new('ShaderNodeGroup')
    group_node.node_tree = bpy.data.node_groups[name]

    # Find and set the "Color" input of the new group node
    for inp in group_node.inputs:
        if inp.name in properties:
            inp.default_value = properties[inp.name]

    # Wire the output of the new group node to the input of
    # the MaterialOutput node
    mat.node_tree.links.new(
            group_node.outputs['Shader'],
            output_node.inputs['Surface'], 
    )

