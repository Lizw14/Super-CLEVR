import json
import pdb

def main():
    pth = 'output/ver_mask/questions/superCLEVR_questions_merged.json'
    with open(pth, 'r') as f:
        questions = json.load(f)
    res = {'info': questions['info'], 'questions': []}
        
    for i,q in enumerate(questions['questions']):
        if i%50000 == 0:
            print(i)
        try:
            program = q['program']
            used_idxs = []
            for step in program:
                used_idxs.extend(step['inputs'])
            # print(used_idxs)
            used_idxs = set(used_idxs)
            for p_idx in range(len(program)-1):
                if p_idx not in used_idxs:
                    program[-1]['inputs'].append(p_idx)
            assert(len(program[-1]['inputs']) <= 2)
            # print(len(program), program[-1]['inputs'])
            res['questions'].append(q)
        except:
            pdb.set_trace()
        
    output_pth = pth[:-5] + '_fixed.json'
    with open(output_pth, 'w') as f:
        json.dump(questions, f)
                
if __name__ == '__main__':
    main()