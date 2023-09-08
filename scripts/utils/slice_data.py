import json

from black import out

def main():
    pth = 'output/ver_mask/questions/superCLEVR_questions_part_partquery.json'
    questions = json.load(open(pth, 'r'))
    questions['questions'] = questions['questions'][-50000:]
    output_pth = 'output/ver_mask/sliced/superCLEVR_questions_test_part_50k.json'
    # output_pth = '/home/zhuowan/zhuowan/Clevr/NSCL-PyTorch-Release/data/superclevr/val/questions.json'
    with open(output_pth, 'w') as f:
        json.dump(questions, f)
        
    # pth = 'output/ver_mask/superCLEVR_scenes.json'
    # scenes = json.load(open(pth, 'r'))
    # scenes['scenes'] = scenes['scenes'][500:600]
    # output_pth = 'output/ver_mask/superCLEVR_scenes_5_tiny.json'
    # output_pth = '/home/zhuowan/zhuowan/Clevr/NSCL-PyTorch-Release/data/superclevr/val/scenes.json'
    # with open(output_pth, 'w') as f:
    #     json.dump(scenes, f)
    
if __name__ == '__main__':
    main()