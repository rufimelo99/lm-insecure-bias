# Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment


## Installation
```
conda create -n cl python=3.10 -y
source activate cl
cd SecurityAwareCL
git submodule update --init --recursive
pip install -e .
export GITHUB_BEARER_TOKEN=your_very_cool_token
python sec_aware_cl/secommits/process_json.py --json_path sec_aware_cl/secommits/secommits-raw.json
python alignment/dataset_builder.py --directory alignment/datasets/ --seccommit_osv <PATH_TO_SEC_COMMIT_OSV>


# Run security alignment
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/starcoder7b_results --model bigcode/starcoder2-7b
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/starcoder3b_results --model bigcode/starcoder2-3b
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/mellum_results --model JetBrains/Mellum-4b-base
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/deepseek_results --model deepseek-ai/deepseek-coder-6.7b-base
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/codellama7b_results --model meta-llama/CodeLlama-7b-hf
python sec_aware_cl/alignment/security_alignment.py --directory alignment/datasets/ --output_dir artifacts/security_alignment/codellama13b_results --model meta-llama/CodeLlama-13b-hf


# Join results
python sec_aware_cl/alignment/join_results.py \
  --directories \
  artifacts/security_alignment/codellama7b_results \
  artifacts/security_alignment/codellama13b_results \
  artifacts/security_alignment/starcoder7b_results \
  artifacts/security_alignment/starcoder3b_results \
  artifacts/security_alignment/mellum_results \
  artifacts/security_alignment/deepseek_results \
  --output_dir artifacts/security_alignment/all_models_results

```