import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pdb
from collections import Counter

def long_tail_dist(total, a=2):
    '''
    total: total lengths
    a: controller
    '''
    # dist = [(t+1) ** a for t in range(total)]
    dist = [a ** (-t-1) for t in range(total)]
    dist = np.array(dist)
    # dist = dist / dist.sum()
    return dist

def generate_dist(name_list, output_pth=None, a=2):
    '''
    name_list: a list containing color/shape/mat names
    output_pth: pth to npz file
    a: distribution controller
    '''
    value_dist = long_tail_dist(len(name_list), a=a)
    value_dist = value_dist / value_dist.sum()
    if output_pth is not None:
        print('Saving to ', output_pth, value_dist.shape, value_dist)
        np.savez(output_pth, names=np.array(name_list), dist=value_dist)
        plot_bar(name_list, value_dist.tolist(), output_pth+'.png')
    return value_dist

def generate_shape_dist(shape_dict, output_pth=None, a1=2, a2=2):
    shape_list = []
    shape_super_list = list(shape_dict.keys())
    for k in shape_super_list:
        shape_list.extend(shape_dict[k])
    super_dist = long_tail_dist(5, a=a1)
    dist = []
    for super_idx, name in enumerate(shape_super_list): # 5
        tmp_dist = long_tail_dist(len(shape_dict[name]), a=a2)
        dist.append(super_dist[super_idx] * tmp_dist)
    dist = np.concatenate(dist, axis=0)
    dist = dist / dist.sum()
    if output_pth is not None:
        print('Saving to ', output_pth, dist.shape)
        np.savez(output_pth, names=np.array(shape_list), dist=dist)
        print(shape_list, len(shape_list), dist)
        plot_bar(shape_list, dist.tolist(), output_pth+'.png')
    return dist
    
def generate_co_dist(shape_dict, color_list, output_pth=None, mode='super', a=2):
    shape_list = []
    shape_super_list = list(shape_dict.keys())
    for k in shape_super_list:
        shape_list.extend(shape_dict[k])
    value_dist = np.zeros((len(shape_list), len(color_list))) # each row sum up to 1
    rotate_map = [[0,1,2,3,4,5,6,7], [1,2,3,4,5,6,7,0], [2,3,4,5,6,7,0,1], 
                  [3,4,5,6,7,0,1,2], [4,5,6,7,0,1,2,3], [5,6,7,0,1,2,3,4]]
    rotate_map = np.array(rotate_map)
    color_dist = long_tail_dist(len(color_list), a=a)
    color_dist = color_dist / color_dist.sum()
    
    if mode == 'super':
        idx = 0
        for super_idx, name in enumerate(shape_super_list): # 5
            value_dist[idx:idx+len(shape_dict[name]), :] = color_dist[rotate_map[super_idx]]
            idx += len(shape_dict[name])
    elif mode == 'sub':
        idx = 0    
        for super_idx, name in enumerate(shape_super_list):
            for sub_idx, shape_name in enumerate(shape_dict[name]):
                value_dist[idx, :] = color_dist[rotate_map[sub_idx]]
                idx += 1
            
    if output_pth is not None:
        print('Saving to ', output_pth, value_dist.shape)
        np.savez(output_pth, names=np.array(shape_list+color_list), dist=value_dist)
        plot_array(value_dist, color_list, shape_list, output_pth+'.png')
    return value_dist

def plot_bar(keys, dist, save_pth, y_min=None, y_max=None):
    # plt.plot(dist)
    plt.clf()
    if len(dist)>7:
        plt.xticks(rotation='vertical')
    if y_min is not None:
        plt.ylim(y_min, y_max)
    plt.bar(keys, dist)
    plt.tight_layout()
    plt.savefig(save_pth)

import matplotlib.pylab as pylab
params = {'axes.labelsize': 'xx-large',
         'axes.titlesize':'xx-large',
         'xtick.labelsize':'xx-large',
         'ytick.labelsize':'xx-large'}
pylab.rcParams.update(params)
    
def plot_array(dist, x_list, y_list, save_pth):
    plt.clf()
    ax = sns.heatmap(dist, xticklabels=x_list, yticklabels=y_list, linewidth=0.5, vmin=0.0, vmax=0.6)
    plt.tight_layout()
    plt.savefig(save_pth)

def main():
    prop_pth = 'properties_cgpart.json'
    properties = json.load(open(prop_pth, 'r'))
    properties['shapes'].pop('addi')
    properties['info_hier']['car'].pop(-1) #addi
    color_list = list(properties['colors'].keys())
    mat_list = list(properties['materials'].keys())
    # mat_list = ['metal', 'rubber']
    size_list = list(properties['sizes'].keys()) 
    shape_dict = properties['info_hier']
    def output_dist(output_dir='tmp', a=0):
        generate_dist(color_list, output_pth=output_dir+'/color_dist.npz', a=a)
        generate_dist(mat_list, output_pth=output_dir+'/mat_dist.npz', a=a)
        generate_shape_dist(shape_dict, output_pth=output_dir+'/shape_dist.npz', a1=a, a2=a)
        # generate_co_dist(shape_dict, color_list, output_pth=output_dir+'/shape_color_co_sub.npz', mode='sub', a=a)
        # generate_co_dist(shape_dict, color_list, output_pth=output_dir+'/shape_color_co_super.npz', mode='super', a=a)
    # output_dist(output_dir='dist', a=2)
    output_dist(output_dir='dist/dist_a1', a=1.3)

def main_for_test():
    def reverse_dist(inp_pth, output_pth, mode=None):
        input_npy = np.load(inp_pth)
        dist, names = input_npy['dist'], input_npy['names']
        sort_idx = dist.argsort()[::-1]
        names = names[sort_idx]
        dist = dist[sort_idx]
        for i in range((len(dist)+1)//2):
            if mode == 'reverse':
                dist[i], dist[-i-1] = dist[-i-1], dist[i]
            elif mode == 'head':
                dist[-i-1] = 0
                dist[i] = 1
            elif mode == 'tail':
                dist[i] = 0
                dist[-i-1] = 1
            elif mode == 'orig':
                pass
        dist = dist / dist.sum()
        print('Saving to ', output_pth, dist.shape)
        np.savez(output_pth, names=names, dist=dist)
        plot_bar(names, dist.tolist(), output_pth+'.png')
        
    reverse_dist(inp_pth='dist/color_dist.npz', output_pth='dist/test/color_dist_oppo.npz', mode='reverse')
    reverse_dist(inp_pth='dist/mat_dist.npz', output_pth='dist/test/mat_dist_oppo.npz', mode='reverse')
    reverse_dist(inp_pth='dist/shape_dist.npz', output_pth='dist/test/shape_dist_oppo.npz', mode='reverse')
    
    reverse_dist(inp_pth='dist/color_dist.npz', output_pth='dist/test/color_dist_head.npz', mode='head')
    reverse_dist(inp_pth='dist/mat_dist.npz', output_pth='dist/test/mat_dist_head.npz', mode='head')
    reverse_dist(inp_pth='dist/shape_dist.npz', output_pth='dist/test/shape_dist_head.npz', mode='head')
    
    reverse_dist(inp_pth='dist/color_dist.npz', output_pth='dist/test/color_dist_tail.npz', mode='tail')
    reverse_dist(inp_pth='dist/mat_dist.npz', output_pth='dist/test/mat_dist_tail.npz', mode='tail')
    reverse_dist(inp_pth='dist/shape_dist.npz', output_pth='dist/test/shape_dist_tail.npz', mode='tail')
    
    reverse_dist(inp_pth='dist/color_dist.npz', output_pth='dist/test/color_dist_orig.npz', mode='orig')
    reverse_dist(inp_pth='dist/mat_dist.npz', output_pth='dist/test/mat_dist_orig.npz', mode='orig')
    reverse_dist(inp_pth='dist/shape_dist.npz', output_pth='dist/test/shape_dist_orig.npz', mode='orig')
            
def main_for_visualize():
    for pre_key in ['color', 'mat', 'shape']:
        for post_key in ['orig']:#, 'head', 'tail', 'oppo']:
            # inp_pth = 'dist/test/'+pre_key+'_dist_'+post_key+'.npz'
            inp_pth = 'dist/dist_a1/'+pre_key+'_dist.npz'
            # output_pth = 'dist/output1/'+pre_key+'_dist_'+post_key+'.png'
            # output_pth = 'dist/output1/'+pre_key+'_dist_flat.png'
            output_pth = 'dist/output1/'+pre_key+'_dist_a1.png'
            input_npy = np.load(inp_pth)
            input_npy = np.load(inp_pth)
            dist, names = input_npy['dist'], input_npy['names']    
            
            sort_idx = dist.argsort()[::-1]
            # names = names[sort_idx]
            # dist = dist[sort_idx]
            # dist = np.array([1.0/len(dist) for  d in dist])
            y_max_dict = {'color':0.52, 'shape':0.3, 'mat':1.0}
            plot_bar(names, dist.tolist(), output_pth, y_min=0, y_max=y_max_dict[pre_key]) #color 0.52, shape0.3
            # plot_array(dist, names[-8:].tolist(), names[:-8].tolist(), output_pth)

def count_dist(scenes, attr):
    res = Counter()
    for scene in scenes:
        for obj in scene['objects']:
            res[obj[attr]] += 1
    key_list = [a[0] for a in res.most_common()]
    dist_array = np.array([res[k] for k in key_list])
    dist_array = dist_array / dist_array.sum()
    return res, key_list, dist_array
        
def count_co_dist(scenes, shape_list=None, color_list=None):   
    res = Counter()
    for scene in scenes:
        for obj in scene['objects']:
            res[(obj['shape'], obj['color'])] += 1
    dist = np.zeros((len(shape_list), len(color_list)))
    if type(shape_list) == list:
        for i_s, shape in enumerate(shape_list):
            for i_c, color in enumerate(color_list):
                dist[i_s, i_c] = res[(shape, color)]
    elif type(shape_list) == dict: #hier
        for i_s, super_shape in enumerate(shape_list.keys()):
            for shape in shape_list[super_shape]:
                for i_c, color in enumerate(color_list):
                    dist[i_s, i_c] += res[(shape, color)]
    dist = dist / dist.sum(1, keepdims=True)
    return dist

def main_validate():
    scene_json = '/data/c/zhuowan/SuperClevr/super-clevr/output/dist_texture_a1/superCLEVR_scenes.json'
    output_dir = '/data/c/zhuowan/SuperClevr/super-clevr/output/dist_texture_a1/analysis/'
    scenes = json.load(open(scene_json, 'r'))['scenes']
    for attr in ['color', 'size', 'material', 'shape']:
        dist, key_list, dist_array = count_dist(scenes, attr)
        plot_bar(key_list, dist_array.tolist(), output_dir+attr+'.png')
    
    
    prop_pth = 'properties_cgpart.json'
    properties = json.load(open(prop_pth, 'r'))
    properties['shapes'].pop('addi')
    properties['info_hier']['car'].pop(-1) #addi
    color_list = list(properties['colors'].keys())
    mat_list = list(properties['materials'].keys())
    # mat_list = ['metal', 'rubber']
    size_list = list(properties['sizes'].keys()) 
    shape_dict = properties['info_hier']
    shape_list = []
    shape_super_list = list(shape_dict.keys())
    for k in shape_super_list:
        shape_list.extend(shape_dict[k])
        
    dist = count_co_dist(scenes, shape_list=shape_list, color_list=color_list)
    plot_array(dist, color_list, shape_list, output_dir+'codist.png')
    
    super_dist = count_co_dist(scenes, shape_list=shape_dict, color_list=color_list)
    plot_array(super_dist, color_list, shape_super_list, output_dir+'super_codist.png')
    


if __name__ == '__main__':
    # main()
    # main_validate()
    # main_for_test()
    main_for_visualize()
    
