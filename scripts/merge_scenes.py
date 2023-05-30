import os
import json
from tqdm import tqdm

def main():
    all_scene_paths = []
    output_scene_dir = 'output/scenes'
    
    # prefix = 'superCLEVR_new_'
    # num_digits = 6
    # scene_template = '%s%%0%dd.json' % (prefix, num_digits)
    # scene_template = os.path.join(output_scene_dir, scene_template)
    # start_idx = 0
    # for i in range(10):
    #     scene_path = scene_template % (i + start_idx)
    #     all_scene_paths.append(scene_path)
        
    for scene_name in os.listdir(output_scene_dir):
        if not scene_name.endswith('.json'):
            continue
        all_scene_paths.append(os.path.join(output_scene_dir, scene_name))
    print('All %d scenes.' % len(all_scene_paths))
        
    all_scenes = []
    for scene_path in tqdm(all_scene_paths):
        with open(scene_path, 'r') as f:
            all_scenes.append(json.load(f))
    
    all_scenes = sorted(all_scenes, key=lambda k: int(k['image_filename'].split('_')[-1].split('.')[0]))
    output = {
        'info': {
            'date': "01/04/2022",
            'version': "1.0",
            'split': "new",
            'license': "Creative Commons Attribution (CC-BY 4.0)",
        },
        'scenes': all_scenes
    }
    output_scene_file = 'output/superCLEVR_scenes.json'
    with open(output_scene_file, 'w') as f:
        json.dump(output, f)
        
if __name__ == '__main__':
    main()