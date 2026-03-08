# Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment

This repository contains the artifact for the paper *"Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment"*, accepted at the **IEEE International Conference on Software Testing, Verification and Validation (ICST) 2026**.

We frame security alignment as a preference problem inspired by Direct Preference Optimization (DPO): for each vulnerable/safe code pair from real-world security commits, we measure whether the model assigns higher log-probability to the safe version (`chosen`) than to the vulnerable version (`rejected`). We additionally report perplexity differences and token-level entropy (uncertainty).

**Dataset**: The final alignment dataset is publicly available on Hugging Face: [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits)

---

## Purpose

This artifact enables **reproducible measurement of security alignment in code-focused LLMs** by analyzing the probabilities that models assign to **secure vs. vulnerable code variants**.

### 1. Scripts for creating DeltaSecommits
The artifact includes scripts to process the raw SeCommits dataset (sourced from OSV) and produce a dataset of vulnerable/safe code pairs derived from real-world security commits, filtered by CWE and patch size.
The dataset is also available directly on Hugging Face at [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits).


### 2. Measuring Security Alignment with Probabilistic Signals

The framework evaluates whether a model **probabilistically prefers secure code** by comparing token-level likelihoods between vulnerable code and its patched counterpart, using three complementary signals:

- **Preference** (Log-probability) — which variant the model is more likely to generate
- **Fluency** (Perplexity) — how natural each code variant appears to the model
- **Confidence** (Entropy) — how certain the model is about its token predictions



All data, pre-computed model results, and analysis scripts are included to reproduce every figure and statistical test in the paper **without requiring GPU access or model re-inference**. The full pipeline is also provided for those with GPU access who wish to validate the entire process.

**Artifact badges claimed**:

- **Artifact Available**: The artifact is permanently and openly hosted on [GitHub](https://github.com/rufimelo99/lm-insecure-bias) and [Docker Hub](https://hub.docker.com/r/rufimelo/lm-insecure-bias), and the dataset is publicly available on [Hugging Face](https://huggingface.co/datasets/rufimelo/DeltaSecommits). Long-term archival is ensured via [Software Heritage](https://archive.softwareheritage.org/browse/origin/directory/?origin_url=https://github.com/rufimelo99/lm-insecure-bias&visit_type=git). All components are accessible without restrictions.
- **Artifact Reviewed**: The artifact is functional, documented, and reproducible. A smoke-test script (`validate.py`) verifies imports, artifact integrity, and pipeline logic. All paper figures can be reproduced from pre-computed results with a single command and no GPU access. A Docker image provides a fully configured, self-contained environment. The full inference pipeline is also included for end-to-end validation by reviewers with GPU access.

---

## Provenance

- **Paper**: *Do Code LLMs Prefer Insecure Code? A Probabilistic Study of Security Misalignment* — Melo, Rui and Reis, Sofia and Catarino, Andre and Abreu, Rui. ICST 2026, IEEE.
- **GitHub repository**: [https://github.com/rufimelo99/lm-insecure-bias](https://github.com/rufimelo99/lm-insecure-bias)
- **Docker image**: [`rufimelo/lm-insecure-bias:latest`](https://hub.docker.com/r/rufimelo/lm-insecure-bias)
- **Dataset**: [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits) on Hugging Face
- **Software Heritage**: [archive.softwareheritage.org](https://archive.softwareheritage.org/browse/origin/directory/?origin_url=https://github.com/rufimelo99/lm-insecure-bias&visit_type=git)


---

## Data

| File / Directory | Description | Size (approx.) |
|---|---|---|
| `artifacts/secommits-raw.json` | Raw SeCommits dataset (OSV-sourced) | ~50 MB |
| `artifacts/secommits_filtered_final.jsonl` | Cleaned dataset with vulnerable/safe code pairs | ~15 MB |
| `artifacts/security_alignment/data/CWE-*.jsonl` | Per-CWE DPO-style alignment datasets | ~5 MB |
| `artifacts/security_alignment/raw_data.csv` | Flat CSV of all per-sample model scores | ~10 MB |
| `artifacts/security_alignment/*_results/` | Per-model result JSONL files (6 models) | ~30 MB total |
| `artifacts/security_alignment/all_models_results/` | Merged results across all models | ~5 MB |
| `artifacts/plots/` | Pre-generated PDF figures from the paper | ~10 MB |

**Total disk space required**: ~130 MB (all artifacts are already included in the repository).

**Ethical and legal considerations**: All data is derived exclusively from publicly available sources (OSV vulnerability database, public GitHub repositories) under open licenses. No private, personal, or proprietary data is included. The dataset contains only code snippets from security patches — no credentials, PII, or sensitive user data.

---

## Setup

### Hardware Requirements

| Task | CPU | GPU | Disk |
|------|-----|-----|------|
| Reproducing figures (Steps 4 + Analysis) | Any modern CPU | Not required | ~130 MB |
| Re-running model inference (Step 3) | Any modern CPU | CUDA-capable, **≥ 16 GB VRAM** | ~130 MB + model weights |

The models are loaded in 4-bit NF4 quantization via `bitsandbytes`. CPU-only inference is not supported for Step 3. All other steps (data processing, analysis, figure generation) run on CPU.

### Software Requirements

- **Operating system**: Linux (recommended); macOS and Windows supported for analysis-only steps. Docker is recommended on all platforms.
- **Docker** (**recommended** for artifact evaluators) — a pre-configured image [`rufimelo/lm-insecure-bias:latest`](https://hub.docker.com/r/rufimelo/lm-insecure-bias) is provided with all dependencies and artifacts pre-installed. No local Python setup is needed.
- **Python 3.10+** with **Conda** (for local installation without Docker)
- **GitHub Personal Access Token** — required for Step 1 only (fetching commit diffs from the GitHub API). Set as `GITHUB_BEARER_TOKEN`.
  - As of March 2026, obtain a token at `https://github.com/settings/personal-access-tokens/new` with `Public repositories` access.
- **Hugging Face account** with access to gated models (`meta-llama/CodeLlama-*`). Run `huggingface-cli login` before Step 3.

> **Note for artifact evaluators**: Steps 1–3 produce the data in `artifacts/`. These artifacts are already included in the repository, so you can skip directly to [Reproducing Figures from Pre-computed Results](#reproducing-figures-from-pre-computed-results) to validate the analysis without running model inference. We recommend using the provided Docker image for the simplest setup.

---

## Docker Image Usage

```bash
# 1. Clone the repository
git clone --recurse-submodules https://github.com/rufimelo99/lm-insecure-bias.git
cd lm-insecure-bias

# 2. Download the pre-configured Docker image (all artifacts included):
docker pull rufimelo/lm-insecure-bias:latest

# 3. Set your GitHub token (needed for Step 1 only)
export GITHUB_BEARER_TOKEN=your_github_token_here

# 4. (Optional) Log in to Hugging Face (needed for CodeLlama models in Step 3)
huggingface-cli login
# or:
export HF_TOKEN=your_huggingface_token_here

# 5. Run the container with an interactive shell, mounting artifacts/ for output persistence:
docker run -it --rm --gpus all \
  -v $(pwd)/artifacts:/workspace/artifacts \
  -e GITHUB_BEARER_TOKEN=$GITHUB_BEARER_TOKEN \
  -e HF_TOKEN=$HF_TOKEN \
  rufimelo/lm-insecure-bias:latest \
  bash
```

Once inside the container, you can run any of the steps below normally. The `-v` flag ensures outputs written to `artifacts/` persist to your host machine. For analysis only (no GPU needed), omit `--gpus all`.

## Local Installation

```bash
# 1. Clone the repository
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
# or:
export HF_TOKEN=your_huggingface_token_here
```

---

## Recommended Workflow for Artifact Evaluators

1. **Skip Steps 1–3** since all intermediate and final artifacts are already included in the repository under `artifacts/`. These steps require GPU and internet access.
2. **Run the analysis script** to reproduce all figures from the paper using the pre-computed results:
   ```bash
   python sec_aware_cl/alignment/analysis.py
   ```
   Figures are saved to `artifacts/plots/`. See [Reproducing Figures from Pre-computed Results](#reproducing-figures-from-pre-computed-results) for details.

**Basic installation test** (no GPU or internet required):

```bash
python validate.py
```

This smoke-test verifies imports, artifact file presence, and the correctness of Step 2 and Step 4 logic. All checks print `[OK]` on success.

---

## Usage

The pipeline has four steps. **Steps 1–3 require a GPU and internet access.** All intermediate and final artifacts are already included in `artifacts/`, so evaluators can skip ahead.

### Step 1 — Process the Raw Secommits Dataset (data already present in `artifacts/`)

Fetches commit diffs from the GitHub API and produces a filtered JSONL with `prior_version` (vulnerable) and `after_version` (safe) code snippets.

> The final dataset produced by this step is also available directly on Hugging Face at [rufimelo/DeltaSecommits](https://huggingface.co/datasets/rufimelo/DeltaSecommits), so you can skip Steps 1–2 and load it from there.

#### Run through Docker (recommended for artifact evaluators)

First, start an interactive shell in the Docker container with the `artifacts/` directory mounted so you can read/write files. Then run:

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

All model results are already included under `artifacts/security_alignment/`. Two equivalent ways to reproduce all paper figures without running model inference:

### Option A — Python script (recommended, headless)

```bash
conda activate cl
python sec_aware_cl/alignment/analysis.py
# or with a custom artifacts path:
python sec_aware_cl/alignment/analysis.py --artifacts path/to/artifacts
```

### Option B — Jupyter notebook (interactive)

```bash
conda activate cl
jupyter notebook sec_aware_cl/alignment/analysis.ipynb
```

Both options read from `artifacts/security_alignment/` and `artifacts/security_alignment/raw_data.csv` and generate all publication-ready figures saved to `artifacts/plots/`.

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

## Repository Structure

```
lm-insecure-bias/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── setup.py                           # Package installation script
├── Dockerfile                         # Docker image for reproducibility
├── .dockerignore                      # Files excluded from Docker build context
├── validate.py                        # Smoke-test: verifies imports, artifact files,
│                                      #   and Step 2/4 logic (no GPU or internet needed)
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
│       ├── analysis.py                # Headless Python script (equivalent to analysis.ipynb):
│       │                              #   reads pre-computed results, runs statistical tests,
│       │                              #   and saves all paper figures to artifacts/plots/
│       └── analysis.ipynb             # Jupyter notebook for interactive analysis and
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
