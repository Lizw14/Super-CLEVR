import json
import argparse
from collections import defaultdict
import random
import pdb 
import copy 
random.seed(120) 


EMPTY_EXAMPLE = {"split": "new",
                 "image_filename": "EMPTY",
                 "image_index": -1,
                 "image": "EMPTY",
                 "question": "EMPTY",
                 "answer": "EMPTY",
                 "template_filename": "EMPTY",
                 "question_family_index": -1,
                 "question_hash": None,
                 "question_index": -1}

def get_candidates(lookup, key, used): 
    all_candidates = lookup[key]
    not_used = [x for x in all_candidates if x[1] not in used]
    if len(not_used) == 0:
        return [("empty", -1)]

    return not_used 

def sanity_check(d, candidates):
    for c, i in candidates:
        for k in ["question_hash", "answer", "image"]:
            try:
                assert(c[k] == d[k])
            except AssertionError:
                pdb.set_trace()

def align(old_data, new_data): 
    empty = 0
    new_lookup = defaultdict(list)
    for i, d in enumerate(new_data):
        new_lookup[d['question_hash']].append((d,i))
    aligned_data = []
    used = []
    for od in old_data: 
        candidates = get_candidates(new_lookup, od['question_hash'], used)
        if len(candidates) == 1 and candidates[0][1] == -1: 
            chosen_q = copy.deepcopy(EMPTY_EXAMPLE)
            chosen_q['question_hash'] = od['question_hash']
            empty += 1
        else:
            sanity_check(od, candidates)
            chosen_q, chosen_idx = random.choice(candidates)
            used.append(chosen_idx)

        for k in ['image_filename', 'image_index', 'image', 'question_family_index', 'question_index']:
            chosen_q[k] = od[k]

        #assert(chosen_q['question_hash'] == od['question_hash'])
        aligned_data.append(chosen_q)

    print(f"empty: {empty}: {empty/len(aligned_data) * 100:.2f}%")
    return aligned_data

if __name__ == "__main__": 
    parser = argparse.ArgumentParser()
    parser.add_argument("--kept-file", type=str, help="path to file with original annotations", required=True)
    parser.add_argument("--new-file", type=str, help="path to file with removed annotations", required=True)
    parser.add_argument("--out-file", type=str, help="path to output file with aligned annotations", required=True)
    args = parser.parse_args() 

    with open(args.kept_file) as f1, open(args.new_file) as f2:
        old_data = json.load(f1) 
        new_data = json.load(f2)
    
    new_questions = new_data['questions']
    old_questions = old_data['questions']
    to_write = {}
    to_write['info'] = old_data['info']

    aligned_new_questions = align(old_questions, new_questions) 
    to_write['questions'] = aligned_new_questions

    with open(args.out_file, "w") as f1:
        json.dump(to_write, f1, indent=4)