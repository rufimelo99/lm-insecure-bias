# Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment

This repository contains the artifact for the paper *"Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment"*. The paper investigates whether code-focused Large Language Models (LLMs) are probabilistically aligned with secure coding practices.

We frame security alignment as a preference problem inspired by Direct Preference Optimization (DPO): for each vulnerable/safe code pair from real-world security commits, we measure whether the model assigns higher log-probability to the safe version (`chosen`) than to the vulnerable version (`rejected`). We additionally report perplexity differences and token-level entropy (uncertainty).

**Dataset**: The final alignment dataset (DeltaSeCommits) is publicly available on Hugging Face: [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits)

---

## Repository Structure

```
lm-insecure-bias/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package installation script
├── Dockerfile                         # Docker image for reproducibility
├── fmt.sh                             # Code formatting script (black + isort)
│
├── sec_aware_cl/                      # Main source package
│   ├── __init__.py
│   ├── logger.py                      # Structured logger (structlog-based)
│   ├── schemas.py                     # Enum definitions for models and datasets
│   │
│   ├── secommits/
│   │   └── process_json.py            # Step 1 — Processes the raw SeCommits dataset:
│   │                                  #   fetches commit diffs from GitHub API,
│   │                                  #   filters by language/CWE/patch size, and
│   │                                  #   produces secommits_filtered_final.jsonl
│   │
│   └── alignment/
│       ├── dataset_builder.py         # Step 2 — Converts the filtered SeCommits JSONL
│       │                              #   into per-CWE DPO-style datasets (chosen/rejected pairs)
│       │                              #   stored under artifacts/security_alignment/data/
│       ├── security_alignment.py      # Step 3 — Core analysis script:
│       │                              #   loads each model, runs forward passes on
│       │                              #   chosen/rejected pairs, computes log-probability,
│       │                              #   perplexity, uncertainty, and DPO loss,
│       │                              #   and saves per-CWE JSONL results
│       ├── security_alignment_config.yaml  # YAML configuration listing models and output dirs
│       ├── join_results.py            # Step 4 — Merges per-model result directories into
│       │                              #   a single all_models_results/ directory
│       └── analysis.ipynb             # Jupyter notebook for statistical analysis and
│                                      #   generating all paper figures
│
├── artifacts/
│   ├── secommits-raw.json             # Raw SeCommits dataset (OSV-sourced security commits)
│   ├── secommits_filtered.jsonl       # Intermediate: after fetching GitHub diffs
│   ├── secommits_filtered_final.jsonl # Final cleaned dataset with prior/after code versions
│   │
│   ├── defects4j.csv                  # Defects4J dataset reference (used in analysis)
│   ├── gbug-java.csv                  # GBug-Java dataset reference (used in analysis)
│   │
│   ├── security_alignment/
│   │   ├── data/                      # Per-CWE alignment datasets (chosen/rejected pairs)
│   │   │   └── CWE-*.jsonl            # One file per CWE; each line has:
│   │   │                              #   cwe, chosen (safe code), rejected (vuln code),
│   │   │                              #   vuln_id, score, commit_href, etc.
│   │   │
│   │   ├── raw_data.csv               # Flat CSV with all per-sample model scores
│   │   │                              #   (model, cwe, vuln_id, logprob, ppl, uncertainty)
│   │   │
│   │   ├── codellama7b_results/       # Results for CodeLlama-7B
│   │   ├── codellama13b_results/      # Results for CodeLlama-13B
│   │   ├── starcoder7b_results/       # Results for StarCoder2-7B
│   │   ├── starcoder3b_results/       # Results for StarCoder2-3B
│   │   ├── mellum_results/            # Results for JetBrains Mellum-4B
│   │   ├── deepseek_results/          # Results for DeepSeek-Coder-6.7B
│   │   │
│   │   │   # Each model results directory contains:
│   │   │   #   CWE-*.jsonl            — per-CWE results with per-sample scores,
│   │   │   #                            dpo_loss, alignment flag, ppl_diff,
│   │   │   #                            uncertainty_diff, and raw logprobs/ppl
│   │   │   #   alignment_stats.jsonl  — summary: aligned_count and total_count per CWE
│   │   │
│   │   └── all_models_results/        # Merged results from all 6 models
│   │       └── CWE-*.jsonl            # One entry per model per CWE
│   │
│   └── plots/                         # Publication-ready PDF figures
│       ├── alignemnt_graph_shorter.pdf        # Main alignment results figure
│       ├── dataset_distribution.pdf           # Dataset statistics
│       ├── ppl_diff_all.pdf                   # Perplexity differences across models/CWEs
│       ├── ppl_diff_uncertainty_all.pdf       # Uncertainty (entropy) differences
│       ├── figure5_replacement_dpo_heatmap.pdf # DPO loss heatmap
│       ├── figure5b_avg_dpo_per_model.pdf     # Average DPO loss per model
│       ├── mean_pref_cwe_model.pdf            # Mean preference per CWE and model
│       ├── Wilcoxon_*.pdf                     # Wilcoxon signed-rank test results
│       └── rebuttal/                          # Additional figures from author rebuttal
```

---

## Prerequisites

- **Python 3.10+**
- **CUDA-capable GPU** with ≥16 GB VRAM (for running model inference in Step 3). The models are loaded in 4-bit quantization (NF4) via `bitsandbytes`. CPU-only runs are not supported for Step 3.
- **GitHub Personal Access Token** — required for Step 1 (fetching commit diffs from the GitHub API). Set as `GITHUB_BEARER_TOKEN`.
- **Hugging Face account** with access to gated models (`meta-llama/CodeLlama-*`). Run `huggingface-cli login` before Step 3.

> **Note for artifact evaluators**: Steps 1–3 produce the data in `artifacts/`. These artifacts are already included in the repository, so you can skip directly to [Reproducing Figures from Pre-computed Results](#reproducing-figures-from-pre-computed-results) or [Step 4](#step-4-merge-results) to validate the analysis without running model inference.

---

## Installation

```bash
# 1. Clone the repository with submodules
git clone --recurse-submodules https://github.com/rufimelo99/lm-insecure-bias.git
cd lm-insecure-bias

# 2. Create and activate a conda environment
conda create -n cl python=3.10 -y
conda activate cl

# 3. Install the package and its dependencies
pip install -e .

# 4. Set your GitHub token (needed for Step 1 only)
export GITHUB_BEARER_TOKEN=your_github_token_here

# 5. (Optional) Log in to Hugging Face (needed for CodeLlama models in Step 3)
huggingface-cli login
```

---

## Smoke Test (no GPU required)

After installation, run the validation script to verify that the environment is correctly set up, all artifact files are present and parseable, and the CPU-only steps (dataset building and result merging) reproduce the committed outputs:

```bash
python validate.py
```

Expected output: every check prints `[OK]` and the script exits 0. This does **not** require a GPU, a GitHub token, or downloading any models.

---

## Usage

The pipeline has four steps. **Steps 1–3 require a GPU and internet access.** All intermediate and final artifacts are already included in `artifacts/`, so evaluators can skip ahead.

### Step 1 — Process the Raw SeCommits Dataset

Fetches commit diffs from the GitHub API and produces a filtered JSONL with `prior_version` (vulnerable) and `after_version` (safe) code snippets.

> The final dataset produced by this step is also available directly on Hugging Face at [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits), so you can skip Steps 1–2 and load it from there.

```bash
python sec_aware_cl/secommits/process_json.py \
    --json_path artifacts/secommits-raw.json \
    --output_path artifacts/secommits_filtered.jsonl \
    --final_output_path artifacts/secommits_filtered_final.jsonl
```

**Output**: `artifacts/secommits_filtered.jsonl` and `artifacts/secommits_filtered_final.jsonl`

Filtering applied:
- Only single-commit, single-file patches
- Only source code file extensions (`.java`, `.py`, `.c`, `.cpp`, `.js`, `.ts`, `.go`, etc.)
- Only CWEs with ≥ 30 samples
- Deduplication by `vuln_id`

### Step 2 — Build the Alignment Dataset

Converts the filtered JSONL into per-CWE DPO-style datasets (`chosen` = safe, `rejected` = vulnerable).

```bash
python sec_aware_cl/alignment/dataset_builder.py \
    --directory artifacts/security_alignment \
    --seccommit_osv artifacts/secommits_filtered_final.jsonl
```

**Output**: `artifacts/security_alignment/data/CWE-*.jsonl`

Each line in the output files contains:
```json
{
  "cwe": ["CWE-89"],
  "chosen": "<safe code snippet>",
  "rejected": "<vulnerable code snippet>",
  "vuln_id": "GHSA-xxxx",
  "score": 7.5,
  "additions": 3,
  "deletions": 1,
  "total": 4,
  "published_date": "2021-07-27",
  "commit_href": "https://github.com/..."
}
```

### Step 3 — Run Security Alignment Analysis

Loads each model (4-bit quantized) and runs forward passes on every code pair in each CWE file. Computes log-probability, perplexity, Shannon entropy, and DPO loss.

```bash
python sec_aware_cl/alignment/security_alignment.py \
    --config sec_aware_cl/alignment/security_alignment_config.yaml
```

The config file (`security_alignment_config.yaml`) specifies which models to evaluate and where to write results. The default configuration evaluates:

| Name | Model ID |
|------|----------|
| `starcoder7b` | `bigcode/starcoder2-7b` |
| `starcoder3b` | `bigcode/starcoder2-3b` |
| `mellum` | `JetBrains/Mellum-4b-base` |
| `deepseek` | `deepseek-ai/deepseek-coder-6.7b-base` |
| `codellama7b` | `meta-llama/CodeLlama-7b-hf` |
| `codellama13b` | `meta-llama/CodeLlama-13b-hf` |

**Output** (per model): `artifacts/security_alignment/<model>_results/`
- `CWE-*.jsonl` — per-sample scores including `dpo_loss`, `aligned` (bool), `ppl_diff`, `uncertainty_diff`
- `alignment_stats.jsonl` — summary counts per CWE

**Output** (flat CSV): `artifacts/security_alignment/raw_data.csv`

### Step 4 — Merge Results

Combines all per-model result directories into a single directory for analysis.

```bash
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

**Output**: `artifacts/security_alignment/all_models_results/CWE-*.jsonl`

---

## Reproducing Figures from Pre-computed Results

All model results are already included under `artifacts/security_alignment/`. To reproduce the paper's figures without running model inference, open and run the analysis notebook:

```bash
conda activate cl
pip install jupyter
jupyter notebook sec_aware_cl/alignment/analysis.ipynb
```

The notebook reads from `artifacts/security_alignment/` and `artifacts/security_alignment/raw_data.csv` and generates all figures saved to `artifacts/plots/`.

---

## Running with Docker

A `Dockerfile` is provided for a self-contained execution environment.

### Build

```bash
docker build -t security-aware-cl .
```

### Run the analysis notebook (CPU, no GPU required)

```bash
docker run --rm -p 8888:8888 \
  -v $(pwd)/artifacts:/workspace/artifacts \
  security-aware-cl \
  jupyter notebook --ip=0.0.0.0 --no-browser --allow-root \
    sec_aware_cl/alignment/analysis.ipynb
```

### Run model inference (requires NVIDIA GPU + nvidia-container-toolkit)

```bash
docker run --rm --gpus all \
  -e GITHUB_BEARER_TOKEN=$GITHUB_BEARER_TOKEN \
  -e HF_TOKEN=$HF_TOKEN \
  -v $(pwd)/artifacts:/workspace/artifacts \
  security-aware-cl \
  python sec_aware_cl/alignment/security_alignment.py \
    --config sec_aware_cl/alignment/security_alignment_config.yaml
```

---

## Metrics

| Metric | Description |
|--------|-------------|
| **Log-probability** | Sum of token log-probs for the full code snippet; higher = model prefers this snippet |
| **Aligned** | `True` if `logprob(safe) > logprob(vulnerable)` for a given pair |
| **Perplexity (PPL)** | Exponentiated average negative log-likelihood; lower = more fluent |
| **PPL diff** | `ppl(vulnerable) − ppl(safe)`; positive = model finds vulnerable code more surprising |
| **Uncertainty** | Mean Shannon entropy over token distributions; lower = more confident |
| **DPO loss** | `softplus(−β · (logprob(safe) − logprob(vulnerable)))`; lower = better alignment |

---

## Citation

If you use this artifact, please cite:

```bibtex
@inproceedings{melo2026vulnerable,
  title     = {Do Language Models Prefer Vulnerable Code? A Probabilistic Study of Insecure Code Preference},
  author    = {Melo, Rui and Reis, Sofia and Catarino, Andre and Abreu, Rui},
  booktitle = {Proceedings of the IEEE International Conference on Software Testing, Verification and Validation (ICST)},
  year      = {2026},
  publisher = {IEEE}
}
```
