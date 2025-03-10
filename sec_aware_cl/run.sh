#!/bin/bash

#SBATCH --job-name=security_cl
#SBATCH --mem=20G

#SBATCH --gres=shard:6
#SBATCH --time=10:00:00
#SBATCH --mail-type=all
#SBATCH --mail-user=rufimelo99@gmail.com
#SBATCH --output=/home/u021521/SecurityAwareCL/lurm-%x-%j.out
#SBATCH --error=/home/u021521/SecurityAwareCL/slurm-%x-%j.err

# Prepare Environment
source activate /home/u021521/anaconda3/envs/cl/
echo "Submitting job"

python run.py \
   --model openai-community/gpt2 \
   --dataset rufimelo/gbug-java