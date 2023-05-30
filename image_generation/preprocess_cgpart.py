
import bpy
import bmesh
import json
import os
import random
import pdb
import sys
import re

from material_cycles_converter import AutoNode
# import matplotlib.colors as mcolors

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
                
    return color_name_to_rgba, size_mapping, obj_info



def modify_part_color(current_obj, part_name, part_verts_idxs, mat_list, color_name, color):
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(current_obj.data)
    bpy.ops.mesh.select_all(action='DESELECT')
    for face in bm.faces:
        flag = True
        for v in face.verts:
            if v.index not in part_verts_idxs:
                flag = False
                break
        if flag:
            # if material for this part already exist, assign
            face.select = True
            mat_name = current_obj.data.materials[face.material_index].name
            mat = current_obj.data.materials[face.material_index]
            for midx in range(len(current_obj.data.materials)):
                if current_obj.data.materials[midx].name.startswith(current_obj.name+'.'+part_name) and mat.node_tree.nodes[1].name == current_obj.data.materials[midx].node_tree.nodes[1].name:
                    face.material_index = midx
                    flag = False
                    break
        if flag:
            # if not, create new
            # there are problems with suv door material assignment, fix it here
            if current_obj.name == 'suv' and mat_name.split('.')[0] in ['material_1_24'] and part_name in ['back_left_door', 'back_right_door']:
                #, 'material_2_24', 'material_3_16', 'material_0_16'
                face.normal_flip() ## TODO: temp fix, not sure what to do here (see git issue of CGPart)
                for tmp_m in current_obj.data.materials.keys():
                    if tmp_m.split('.')[0] == 'material_3_24':
                        break
                face.material_index = current_obj.data.materials.keys().index(tmp_m)
                mat_name = tmp_m
            elif current_obj.name == 'articulated' and mat_name.split('.')[0] == 'material_1_1_8' and part_name in ['frame_right']:
                for tmp_m in current_obj.data.materials.keys():
                    if tmp_m.split('.')[0] == 'material_11_24':
                        break
                face.material_index = current_obj.data.materials.keys().index(tmp_m)
                mat_name = tmp_m
            elif current_obj.name == 'dirtbike' and mat_name.split('.')[0] == 'material_14_1_8' and part_name in ['wheel_front']:
                for tmp_m in current_obj.data.materials.keys():
                    if tmp_m.split('.')[0] == 'material_7_24':
                        break
                face.material_index = current_obj.data.materials.keys().index(tmp_m)
                mat_name = tmp_m
            elif current_obj.name == 'dirtbike' and mat_name.split('.')[0] == 'material_14_1_8' and part_name in ['exhaust_right_1']:
                for tmp_m in current_obj.data.materials.keys():
                    if tmp_m.split('.')[0] == 'material_5_24':
                        break
                face.material_index = current_obj.data.materials.keys().index(tmp_m)
                mat_name = tmp_m
            elif current_obj.name == 'chopper' and mat_name.split('.')[0] == 'material_14_4_8' and part_name in ['wheel_front', 'wheel_back']:
                for tmp_m in current_obj.data.materials.keys():
                    if tmp_m.split('.')[0] == 'material_17_24':
                        break
                face.material_index = current_obj.data.materials.keys().index(tmp_m)
                mat_name = tmp_m
            # if mat_name.split('.')[0] not in mat_list:
            #     continue
            new_mat_name = current_obj.name+'.'+part_name+'.'+mat_name+'.'+color_name
            # if the face has already been assigned to a part (with a new mat), then skipping assigning for second time (mat name has length limit)
            if len(new_mat_name.split('.')) >= 6:
                continue
            # if the new material does not exist, create it
            if new_mat_name not in bpy.data.materials.keys():
                # new_mat = bpy.data.materials.new(new_mat_name)
                new_mat = bpy.data.materials[mat_name].copy()
                assert new_mat.node_tree.nodes[1].name in ['Diffuse BSDF', 'Transparent BSDF']
                new_mat.name = new_mat_name
                if len(new_mat.node_tree.nodes) > 2: #texture materials
                    assert len(new_mat.node_tree.nodes)==3
                    node_to_rm = new_mat.node_tree.nodes[2]
                    new_mat.node_tree.nodes.remove(node_to_rm)
                # new_mat.node_tree.nodes[1].inputs[0].default_value[0:3] = color[0:3]
                current_obj.data.materials.append(new_mat)
            face.material_index = len(current_obj.data.materials) - 1

    bpy.ops.object.mode_set(mode='OBJECT')

objs = bpy.data.objects
objs.remove(objs["Cube"], do_unlink=True)
objs.remove(objs["Camera"], do_unlink=True)
objs.remove(objs["Lamp"], do_unlink=True)


# colors = [(k.split(':')[1],v) for k,v in mcolors.CSS4_COLORS.items()] 
#BASE_COLORS, TABLEAU_COLORS, CSS4_COLORS
## Save color json
# https://matplotlib.org/stable/gallery/color/named_colors.html
# res = {'BASE_COLORS':mcolors.BASE_COLORS, 'TABLEAU_COLORS':mcolors.TABLEAU_COLORS, 'CSS4_COLORS':mcolors.CSS4_COLORS}
# for k in res:
#     res[k] = [(kk.split(':')[-1], mcolors.hex2color(vv)) for kk,vv in res[k].items()]
color_pth = 'data/colors.json'
# with open(color_pth,'w') as f:
#     json.dump(res, f, indent=2)

colors = json.load(open(color_pth, 'r'))['CSS4_COLORS']
random.seed(2022)
random.shuffle(colors)

properties_json = 'data/properties_cgpart.json'
label_dir = '/home/zhuowan/zhuowan/SuperClevr/render-3d-segmentation/CGPart/labels'
color_name_to_rgba, size_mapping, obj_info = load_properties_json(properties_json, label_dir)

part_dict = {}
for si, obj_name in enumerate(obj_info['info_pth']):
    model_dir = '/home/zhuowan/zhuowan/SuperClevr/render-3d-segmentation/CGPart/'
    model_id = obj_info['info_pth'][obj_name]
    shape_file = os.path.join(model_dir, 'models', model_id, 'models', 'model_normalized.obj')
    # if obj_name!='suv':
    #     continue
    # cat_name = 'car'
    # if not obj_info['info_pth'][obj_name].startswith('car'):
    #     continue
    cat_name = obj_info['info_pth'][obj_name].split('/')[0]

    sys.stdout = open(os.devnull, 'w')
    existings = list(bpy.data.objects)
    bpy.ops.import_scene.obj(filepath=shape_file,use_split_groups=False,use_split_objects=False)
    added_name = list(set(bpy.data.objects) - set(existings))[0].name

    obj_car = bpy.data.objects[added_name]
    obj_car.name = obj_name
    bpy.context.scene.objects.active = obj_car
    AutoNode()
    sys.stdout = sys.__stdout__
    # loc = (si, 0, 0)
    # bpy.ops.transform.translate(value=loc)


    print('shape', obj_name)

    part_dict[obj_name] = []
    for i, part_name in enumerate(obj_info['info_part'][obj_name]):
        # part_color_name, part_rgba = random.choice(list(color_name_to_rgba.items()))
        part_color_name, part_rgba = colors[i]
        if part_name in obj_info['info_part_labels'][obj_name]:
            flag = True
            # window for car
            # misc for bicycle 
            # bus: (frame)
            # cockpit, bomb,landing_gear, door(s) for plane (body)
            # motorcycle: seat & seat_back; footrest(s); exhaust_left/right(s) (cover_body, cover_back)
            part_filter_list = ['window', 'windshield', 'misc', 'cockpit', 'bomb', 'landing_gear', 'seat_back', 'frame', 'body']
            for p in part_filter_list:
                if p in part_name:
                    flag = False
                    break
            if flag:
                part_verts_idxs = obj_info['info_part_labels'][obj_name][part_name]
                mat_list=obj_info['info_material'][obj_name]
                modify_part_color(obj_car, part_name, part_verts_idxs, mat_list, part_color_name, part_rgba)
                part_dict[obj_name].append(part_name)

    filepath = 'data/save_models_1/'+cat_name+'_'+obj_name+'.blend'
    bpy.ops.wm.save_as_mainfile(filepath=filepath)


    objs = bpy.data.objects
    objs.remove(objs[obj_name], do_unlink=True)

# load parts
    # filepath = '/Users/lizw/Downloads/save_models/'+cat_name+'_'+obj_name+'.blend'
    # inner_path = 'Object'
    # bpy.ops.wm.append(
    #     filepath=os.path.join(filepath, inner_path, obj_name),
    #     directory=os.path.join(filepath, inner_path),
    #     filename=obj_name
    #     )

filepath = 'data/save_models_1/part_dict.json'
with open(filepath, 'w') as f:
    json.dump(part_dict, f, indent=2)

