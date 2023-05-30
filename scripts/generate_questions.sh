# cd /home/zhuowan/zhuowan/SuperClevr/clevr-dataset-gen/question_generation
cd question_generation

## (for debug purpose) generate questions based on orinal CLEVR scenes
# python generate_questions.py \
#     --input_scene_file /home/zhuowan/zhuowan/SuperClevr/CLEVR_v1.0/scenes/CLEVR_train_scenes.json \
#     --output_questions_file output/sample_questions.json \
#     --scene_start_idx 0 \
#     --num_scenes 10

# Generate questions with part template for super-CLEVR
python generate_questions.py \
    --input_scene_file ../output/superCLEVR_scenes.json \
    --scene_start_idx 0 \
    --num_scenes 5 \
    --instances_per_template 5 \
    --templates_per_image 10 \
    --metadata_file metadata_part.json \
    --template_dir super_clevr_templates \
    --output_questions_file ../output/superCLEVR_questions_part.json

#@ Generate questions with original CLEVR template for super-CLEVR
# python generate_questions.py \
#     --input_scene_file ../output/superCLEVR_scenes.json \
#     --scene_start_idx 25000 \
#     --num_scenes 5000 \
#     --instances_per_template 1 \
#     --templates_per_image 10 \
#     --metadata_file metadata_part.json \
#     --output_questions_file ../output/superCLEVR_questions_30000.json \
#     --template_dir CLEVR_1.0_templates

cd -

# CLEVR_1.0_templates
    # --input_scene_file ../output/CLEVR_scenes.json \
