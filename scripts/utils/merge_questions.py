import json
import copy

def main():
    res = None
    paths = ['output/dist_texture_a1/questions/superCLEVR_questions_'+str(i*2500)+'.json' for i in range(12)]
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
    with open('output/dist_texture_a1/questions/superCLEVR_questions_merged.json', 'w') as f:
        json.dump(_res, f)

if __name__ == '__main__':
    main()