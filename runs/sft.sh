#!/bin/bash

GIT_LFS_SKIP_SMUDGE=1 pip install -e ".[dev]"
source ~/.bashrc

# custom
export TIMESTAMP=$(date +"%m-%d-%y-%T")

export CONFIG_GRPO="configs/config_demo_code_sft.yaml" 

export MODEL_NAME_OR_PATH="./models/Qwen2.5-Coder-7B-Instruct"
export DATASET_NAME="./web/data/sft"

export OUTPUT_DIR="./saves/sft"
export LOG_FILE="$OUTPUT_DIR/train.log"

mkdir -p $OUTPUT_DIR

ACCELERATE_LOG_LEVEL=info \
    accelerate launch --config_file configs/accelerate_configs/zero2.yaml \
    src/open_r1/sft.py --config $CONFIG_GRPO \
    --model_name_or_path $MODEL_NAME_OR_PATH \
    --dataset_name $DATASET_NAME \
    --output_dir $OUTPUT_DIR 2>&1 | tee $LOG_FILE