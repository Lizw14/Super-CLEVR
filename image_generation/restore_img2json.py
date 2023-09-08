import cv2
import sys
import os
import json
import pdb
import numpy as np


def srgb_to_linear(x, mod=0.1):
    if x <=0.04045 :
        y = x / 12.92
    else:
        y = ((x + 0.055) / 1.055) ** 2.4
    if mod is not None:
        y = round(y / mod) * mod
    return y


def to_str(img):
    pre = 0
    has = 0
    lis = []
    for _x in img:
        if _x == pre:
            has += 1
        else:    
            lis.append(has)
            pre = 1-pre
            has = 1
    if has != 0:
        lis.append(has)
    return ','.join([str(it) for it in lis])


def get_mask(path, mat_indices):
    #mat_indices{mat_idx(1-num_mat):(obj_idx(0-num_obj-1), part_idx(0-num_part-1), obj.name+'.'+part_name)}
    
    obj_masks = {}
    mask_array = {'masks': [], 'info': []}
    bgr_img = cv2.imread(path)
    vf = np.vectorize(srgb_to_linear)
    img_2 = vf(bgr_img[:,:,0]/255., 0.1)
    img_1 = vf(bgr_img[:,:,1]/255., 0.1)
    img_0 = vf(bgr_img[:,:,2]/255., 0.05)
    
    mask_r, mask_g, mask_b = {}, {}, {}
    for i in range(5):
        mask_b[i] = (img_2 == 0.1*(i+1))
    
    for _i in range(len(mat_indices)):
        obj_idx, mat_idx, mat_name = mat_indices[str(_i+1)]
        obj_name = mat_name.split('.')[0]
        if obj_idx not in obj_masks:
            obj_masks[obj_idx] = {'info': obj_name}
        
        if obj_idx not in mask_r:
            mask_r[obj_idx] = (img_0==0.05*(obj_idx+1))
        mask_0 = mask_r[obj_idx]
        
        if mat_idx == -1:
            mask = mask_0
            part_name = 'obj'
        else:
            if mat_idx//5 not in mask_g:
                mask_g[mat_idx//5] = (img_1 == 0.1*(mat_idx//5 + 1))
            mask_1 = mask_g[mat_idx//5]
            mask_2 = mask_b[mat_idx%5]
            mask = mask_0 & mask_1 & mask_2
            part_name = mat_name.split('.')[1]
        mask_array['masks'].append(mask)
        mask_array['info'].append((obj_idx, obj_name, part_name))
        mask = mask.astype(int).flatten().tolist()
        obj_masks[obj_idx][part_name] = to_str(mask)
    
    mask_array['masks'] = np.stack(mask_array['masks'], axis=-1)
    
    return obj_masks, mask_array


def extract_bboxes(mask):
    ## Copied from https://github.com/multimodallearning/pytorch-mask-rcnn/blob/master/utils.py
    """Compute bounding boxes from masks.
    mask: [height, width, num_instances]. Mask pixels are either 1 or 0.
    Returns: bbox array [num_instances, (y1, x1, y2, x2)]. --> [x, y, w, h]
    """
    boxes = np.zeros([mask.shape[-1], 4], dtype=np.int32)
    for i in range(mask.shape[-1]):
        m = mask[:, :, i]
        # Bounding box.
        horizontal_indicies = np.where(np.any(m, axis=0))[0]
        vertical_indicies = np.where(np.any(m, axis=1))[0]
        if horizontal_indicies.shape[0]:
            x1, x2 = horizontal_indicies[[0, -1]]
            y1, y2 = vertical_indicies[[0, -1]]
            # x2 and y2 should not be part of the box. Increment by 1.
            x2 += 1
            y2 += 1
        else:
            # No mask for this instance. Might happen due to
            # resizing or cropping. Set bbox to zeros
            x1, x2, y1, y2 = 0, 0, 0, 0
        # boxes[i] = np.array([y1, x1, y2, x2])
        boxes[i] = np.array([x1, y1, x2-x1, y2-y1])
    return boxes.astype(np.int32)

## functions for decode masks and draw masks and boxes
def str_to_biimg(imgstr):
    img=[]
    cur = 0
    for num in imgstr.strip().split(','):
        num = int(num)
        img += [cur] * num
        cur = 1 - cur
    return np.array(img)
        

def decode_mask(obj_mask, height=480, width=640):
    mask_pixel_num = height*width
    gt_mask  = np.array([0]*mask_pixel_num)
    for obj_idx in obj_mask:
        # key = list(obj_mask[obj_idx].keys())[-1] 
        key ='obj'
        gt_mask |= str_to_biimg(obj_mask[obj_idx][key][1])
    return gt_mask.reshape(height, width)


def draw_img_with_box(img, obj_box):
    for obj_idx in obj_box:
        key = 'obj'
        # key = list(obj_box[obj_idx].keys())[-1]
        box = obj_box[obj_idx][key][0]
        cv2.rectangle(img,(box[0], box[1]),(box[0] + box[2], box[1] + box[3]),(0,139,69),2)
    return img 


def write_img_box_mask(idx):
    json_pth = '../output/ver_mask/scenes/superCLEVR_new_%06d.json' % idx
    obj_res = json.load(open(json_pth, 'r'))['obj_mask_box']
    mask = decode_mask(obj_res)
    img_path = '../output/ver_mask/images/superCLEVR_new_%06d.png' % idx
    im = cv2.imread(img_path)
    im_seg = im / 2 
    for ci in range(im.shape[0]):
        for cj in range(im.shape[1]):
            if mask[ci][cj] :
                im_seg[ci, cj, :] = (0, 0, 180)
    img_box = draw_img_with_box(im_seg, obj_res)
    cv2.imwrite('../output/tmp/im_seg_{}.png'.format(idx), img_box)
    
    
def main(idx): 
    
    # test
    # write_img_box_mask(idx)
    
    img_path = '../output/tmp/mask_all_{}_0001.png'.format(idx)
    json_pth = '../output/tmp/mat_indices_{}.json'.format(idx)
    mat_indices = json.load(open(json_pth, 'r'))
    
    obj_masks, masks_array = get_mask(img_path, mat_indices)
    
    obj_res = obj_masks
    obj_boxes = extract_bboxes(masks_array['masks'].astype(int))
    
    for i, (obj_idx, obj_name, part_name) in enumerate(masks_array['info']):
        box = obj_boxes[i].tolist() #x, y, w, h
        obj_res[obj_idx][part_name] = [box, obj_masks[obj_idx][part_name]]

    out_pth = '/tmp/obj_mask_{}.json'.format(idx)
    json.dump(obj_res, open(out_pth, 'w'))
    
    os.system('rm {} {}'.format(img_path, json_pth))

main(int(sys.argv[1]))
