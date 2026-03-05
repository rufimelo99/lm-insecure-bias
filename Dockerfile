FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

LABEL description="Do Code LLMs Prefer Insecure Code?"

# ---- System dependencies -------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        git-lfs \
        curl \
        ca-certificates \
    && git lfs install \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- Working directory ---------------------------------------------------
WORKDIR /workspace

# ---- Copy source ---------------------------------------------------------
COPY . /workspace/


# ---- Python dependencies ------------------------------------------------
# All deps (including matplotlib, seaborn, scipy, jupyter) are in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# ---- Environment variables -----------------------------------------------
# Pass your tokens at runtime via --env or -e flags; do not bake them in.
# Example:
#   docker run --rm -e GITHUB_BEARER_TOKEN=ghp_... -e HF_TOKEN=hf_... ...
ENV PYTHONUNBUFFERED=1

# ---- Default command: run smoke test then show usage ---------------------
CMD ["bash", "-c", "python validate.py && python -c \"\
print('Image ready.'); \
print(''); \
print('Available entry points:'); \
print('  Step 1 — process raw SeCommits dataset:'); \
print('    python sec_aware_cl/secommits/process_json.py --json_path artifacts/secommits-raw.json'); \
print(''); \
print('  Step 2 — build alignment dataset:'); \
print('    python sec_aware_cl/alignment/dataset_builder.py --directory artifacts/security_alignment --seccommit_osv artifacts/secommits_filtered_final.jsonl'); \
print(''); \
print('  Step 3 — run security alignment (GPU required):'); \
print('    python sec_aware_cl/alignment/security_alignment.py --config sec_aware_cl/alignment/security_alignment_config.yaml'); \
print(''); \
print('  Step 4 — merge results:'); \
print('    python sec_aware_cl/alignment/join_results.py --directories artifacts/security_alignment/codellama7b_results ... --output_dir artifacts/security_alignment/all_models_results'); \
print(''); \
print('  Analysis notebook (CPU only):'); \
print('    jupyter notebook --ip=0.0.0.0 --no-browser --allow-root sec_aware_cl/alignment/analysis.ipynb'); \
\""]
