import os
import json
from tqdm import tqdm
import pdb

def main():
    all_scene_paths = []
    scene_paths_1, scene_paths_2 = [], []
    output_scene_dir_1 = 'output/dist_texture_test/head/scenes'
    output_scene_dir_2 = 'output/dist_texture_test/tail/scenes'
    
    # prefix = 'superCLEVR_new_'
    # num_digits = 6
    # scene_template = '%s%%0%dd.json' % (prefix, num_digits)
    # scene_template = os.path.join(output_scene_dir, scene_template)
    # start_idx = 0
    # for i in range(10):
    #     scene_path = scene_template % (i + start_idx)
    #     all_scene_paths.append(scene_path)
        
    for scene_name in os.listdir(output_scene_dir_1):
        if not scene_name.endswith('.json'):
            continue
        scene_paths_1.append(os.path.join(output_scene_dir_1, scene_name))
        
    for scene_name in os.listdir(output_scene_dir_2):
        if not scene_name.endswith('.json'):
            continue
        scene_paths_2.append(os.path.join(output_scene_dir_2, scene_name))
        
    scene_paths_1 = sorted(scene_paths_1, key=lambda k: int(k.split('_')[-1].split('.')[0]))
    scene_paths_2 = sorted(scene_paths_2, key=lambda k: int(k.split('_')[-1].split('.')[0]))
    
    for s1, s2 in zip(scene_paths_1, scene_paths_2):
        all_scene_paths.append(s1)
        all_scene_paths.append(s2)
    print('All %d scenes.' % len(all_scene_paths))
        
    all_scenes = []
    for scene_path in tqdm(all_scene_paths):
        with open(scene_path, 'r') as f:
            try:
                all_scenes.append(json.load(f))
            except:
                print(scene_path)
                pdb.set_trace()
    
    # all_scenes = sorted(all_scenes, key=lambda k: int(k['image_filename'].split('_')[-1].split('.')[0]))
    output = {
        'info': {
            'date': "01/04/2022",
            'version': "1.0",
            'split': "new",
            'license': "Creative Commons Attribution (CC-BY 4.0)",
        },
        'scenes': all_scenes
    }
    output_scene_file = 'output/dist_texture_test/head_tail/superCLEVR_scenes.json'
    with open(output_scene_file, 'w') as f:
        json.dump(output, f)

def merge_question():
    res = None
    paths = ['output/dist_texture_test/head_tail/questions/superCLEVR_questions_'+str(i*500)+'.json' for i in range(4)]
    for pth in paths:
        print(pth)
        with open(pth, 'r') as f:
            if res is None:
                res = json.load(f)
            else:
                res['questions'].extend(json.load(f)['questions'])
    
    _res = res
    
    # if there are error images that we want to remove
    # rm_list = [1752,2968,5067,7639,8532,14504,20425,20819,22229,22933,25342,25795,25809,26055]
    # _res = {'info': res['info'], 'questions': []}
    # for q in res['questions']:
    #     if q['image_index'] not in rm_list:
    #         _res['questions'].append(q)
    
    print('Num of questions: ', len(_res['questions']))        
    with open('output/dist_texture_test/head_tail/questions/superCLEVR_questions_merged.json', 'w') as f:
        json.dump(_res, f)

def split_question():
    questions = json.load(open('output/dist_texture_test/head_tail/questions/superCLEVR_questions_merged.json', 'r'))
    q_head, q_tail = [], []
    for q in questions['questions']:
        if q['image_filename'][-8] == '1':
            q_head.append(q)
        elif q['image_filename'][-8] == '0':
            q_tail.append(q)
        else:
            pdb.set_trace()
    
    q_head = {'info': questions['info'], 'questions': q_head}
    with open('output/dist_texture_test/head/questions/superCLEVR_questions_merged.json', 'w') as f:
        json.dump(q_head, f)
    q_tail = {'info': questions['info'], 'questions': q_tail}
    with open('output/dist_texture_test/tail/questions/superCLEVR_questions_merged.json', 'w') as f:
        json.dump(q_tail, f)
    
        
if __name__ == '__main__':
    # main()
    # merge_question()
    split_question()