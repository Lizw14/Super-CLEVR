cd image_generation

CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6 \
~/packages/blender-2.79b-linux-glibc219-x86_64/blender --background \
    --python super_render_images.py -- \
    --start_idx 45841 \
    --num_images 4000 \
    --use_gpu 1 \
    --shape_dir /home/zhuowan/zhuowan/SuperClevr/render-3d-segmentation/CGPart \
    --model_dir data/save_models_1/ \
    --properties_json data/properties_cgpart.json \
    --margin 0.1 \
    --save_blendfiles 0 \
    --max_retries 150 \
    --width 640 \
    --height 480

cd ..
