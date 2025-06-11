#!/bin/bash

#SBATCH --job-name=purple_llama
#SBATCH --mem=30G

#SBATCH --gres=shard:4
#SBATCH --time=300:00:00
#SBATCH --mincpus=1
#SBATCH --mail-type=all
#SBATCH --mail-user=rufimelo99@gmail.com
#SBATCH --output=/cfs/home/u021521/SecurityAwareCL/logs/slurm-%x-%j.out
#SBATCH --error=/cfs/home/u021521/SecurityAwareCL/logs/slurm-%x-%j.err

# Prepare Environment
source activate /cfs/home/u021521/anaconda3/envs/cl/
echo "Submitting job"

BASE_DIR=/cfs/home/u021521/SecurityAwareCL

export DATASETS=/cfs/home/u021521/SecurityAwareCL/PurpleLlama/CybersecurityBenchmarks/datasets/

cd PurpleLlama

python3 -m CybersecurityBenchmarks.benchmark.run \
   --benchmark=instruct \
   --prompt-path="$DATASETS/instruct/instruct.json" \
   --response-path="$DATASETS/instruct_responses.json" \
   --stat-path="$DATASETS/instruct_stat.json" \
   --llm-under-test="SELFHOSTED::openai-community/gpt2::something"