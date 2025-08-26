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
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir starcoder7b_results --model bigcode/starcoder2-7b
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir starcoder3b_results --model bigcode/starcoder2-3b
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir mellum_results --model JetBrains/Mellum-4b-base
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir deepseek_results --model deepseek-ai/deepseek-coder-6.7b-base
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir codellama7b_results --model meta-llama/CodeLlama-7b-hf
python sec_aware_cl/alignment/dpo.py --directory alignment/datasets/ --output_dir codellama13b_results --model meta-llama/CodeLlama-13b-hf

zip -r starcoder7b_results.zip starcoder7b_results
zip -r starcoder3b_results.zip starcoder3b_results
zip -r codellama13b_results.zip codellama13b_results
zip -r codellama7b_results.zip codellama7b_results
zip -r deepseek_results.zip deepseek_results
zip -r mellum_results.zip mellum_results
```