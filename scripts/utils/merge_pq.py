import json
import random
import pdb

def main():
    pth = 'output/ver_mask/no_redundant/superCLEVR_questions_merged.json'
    print('Loading questions from: "{}".'.format(pth))
    questions = json.load(open(pth, 'r'))
    questions['questions'] = questions['questions'][:210000]
    
    # pth = 'output/ver_mask/questions/superCLEVR_questions_part_partquery.json'
    # print('Loading questions from: "{}".'.format(pth))
    # # part_questions = json.load(open(pth, 'r'))
    # # questions['questions'].extend(part_questions['questions'][:50000])
    # questions = json.load(open(pth, 'r'))
    # questions['questions'] = questions['questions'][-1000:]
    
    # random.seed(10)
    # random.shuffle(questions['questions'])
        
    pth = 'output/ver_mask/superCLEVR_scenes.json'
    print('Loading scenes from: "{}".'.format(pth))
    _scenes = json.load(open(pth, 'r'))
    scenes = [[]] * (_scenes['scenes'][-1]['image_index']+1)
    for s in _scenes['scenes']:
        scenes[int(s['image_index'])] = s
        
    # pdb.set_trace()
    output_scenes = []
    img_idxes = set([q['image_index'] for q in questions['questions']])
    for img_id in img_idxes:
        output_scenes.append(scenes[img_id])
    output_scenes = {'info': _scenes['info'], 'scenes': output_scenes}
    
    # pth = 'output/ver_mask/sliced/superCLEVR_questions_200k50k.json'
    # train_questions = json.load(open(pth, 'r'))
    # train_idxes = set([q['image_index'] for q in train_questions['questions']])
    # for q in questions['questions']:
    #     assert(q['image_index'] not in train_idxes)
    
    output_pth = 'output/ver_mask/no_redundant/sliced/superCLEVR_scenes_210k0k.json'
    print('Dumping to ', output_pth)
    with open(output_pth, 'w') as f:
        json.dump(output_scenes, f)
    
    output_pth = 'output/ver_mask/no_redundant/sliced/superCLEVR_questions_210k.json'
    print('Dumping to ', output_pth)
    with open(output_pth, 'w') as f:
        json.dump(questions, f)
        
    
if __name__ == '__main__':
    main()