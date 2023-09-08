cd image_generation

CUDA_VISIBLE_DEVICES=5 \
~/packages/blender-2.79b-linux-glibc219-x86_64/blender --background \
    --python super_restore_render_images.py -- \
    --start_idx 0 \
    --num_images 2 \
    --use_gpu 1 \
    --shape_dir ../../render-3d-segmentation/CGPart \
    --model_dir data/save_models_1/ \
    --properties_json data/properties_cgpart.json \
    --margin 0.1 \
    --save_blendfiles 0 \
    --max_retries 150 \
    --width 640 \
    --height 480 \


    #--output_image_dir ../output/ver_texture_same/images/ \
    #--output_scene_dir ../output/ver_texture_same/scenes/ \
    #--output_blend_dir ../output/ver_texture_same/blendfiles \
    #--output_scene_file ../output/ver_texture_same/superCLEVR_scenes.json \
    #--is_part 1 \
    #--load_scene 1 \
    #--clevr_scene_path ../output/ver_mask/superCLEVR_scenes.json 

    # --shape_color_co_dist_pth data/dist/shape_color_co_super.npz \

    # --clevr_scene_path ../output/superCLEVR_scenes_5.json

    # --color_dist_pth data/dist/color_dist.npz \
    # --mat_dist_pth data/dist/mat_dist.npz \
    # --shape_dist_pth data/dist/shape_dist.npz \


cd ..

