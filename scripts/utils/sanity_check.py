import json
import pdb
import tqdm

scene_pth = 'output/dist_texture_a1/superCLEVR_scenes.json'

print('Loading ', scene_pth)
scenes = json.load(open(scene_pth, 'r'))
for idx in range(len(scenes['scenes'])):
    scene = scenes['scenes'][idx]
    for obj_id, obj in scene['obj_mask_box'].items():
        if obj['obj'][0]==[0,0,0,0]:
            print(idx, obj_id)

pdb.set_trace()    
print('Done')