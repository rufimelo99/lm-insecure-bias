# Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment


## Installation
```
conda create -n cl python=3.10
cd SecurityAwareCL
git submodule update --init --recursive
pip install -e .
export GITHUB_BEARER_TOKEN=your_very_cool_token
python sec_aware_cl/secommits/process_json.py --json_path sec_aware_cl/secommits/secommits-raw.json
python alignment/dataset_builder.py --directory alignment/datasets/ --seccommit_osv <PATH_TO_SEC_COMMIT_OSV> --models <HF_MODEL_NAMES>
```