#!/bin/bash

GIT_LFS_SKIP_SMUDGE=1 pip install -e ".[dev]"
source ~/.bashrc
npm install -g pm2
npm install -g vite
npm -v
node -v
pm2 -v
vite -v
pm2 list
pm2 delete all
export NODE_TLS_REJECT_UNAUTHORIZED=0

export TIMESTAMP=$(date +"%m-%d-%y-%T")

export CONFIG_GRPO="configs/config_qwen2.5_coder_7b_instruct.yaml" # configs/config_qwen3.yaml
export PROJECT_ROOT="./projects"

export CHROME="./chrome/chrome-linux64/chrome"
export CHROME_DRIVER="./chrome/chromedriver-linux64/chromedriver"

export MODEL_NAME_OR_PATH="./models/Qwen2.5-Coder-7B-Instruct"
export DATASET_NAME="./web/data/parquet"

export OUTPUT_DIR="./saves/qwen2.5_coder_7b_instruct/$TIMESTAMP"
export ROLLOUT_FILE="$OUTPUT_DIR/web_rollout.jsonl"
export LOG_FILE="$OUTPUT_DIR/train.log"

export OPENAI_API_KEY="sk-xxxxxx"

mkdir -p $OUTPUT_DIR


ACCELERATE_LOG_LEVEL=info \
    accelerate launch --config_file configs/accelerate_configs/zero2.yaml \
    src/open_r1/grpo.py --config $CONFIG_GRPO \
    --model_name_or_path $MODEL_NAME_OR_PATH \
    --dataset_name $DATASET_NAME \
    --output_dir $OUTPUT_DIR \
    --vllm_mode colocate 2>&1 | tee $LOG_FILE