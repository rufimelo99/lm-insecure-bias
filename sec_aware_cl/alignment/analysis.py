#!/usr/bin/env python
# coding: utf-8
"""
analysis.py — reproduce all figures and tables from the paper.

Usage (from repo root):
    python sec_aware_cl/alignment/analysis.py
    python sec_aware_cl/alignment/analysis.py --artifacts path/to/artifacts

All figures are saved as PDFs under <artifacts>/plots/.
No display is required; matplotlib runs in headless (Agg) mode.

NOTE: The "Length Sensitivity" section (Section 9) downloads tokenizers from
Hugging Face and requires network access + significant memory. It is skipped
by default. Pass --length-sensitivity to enable it.
"""

import argparse
import itertools
import json
import os
import warnings

import matplotlib

matplotlib.use("Agg")  # headless — no display needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from scipy.stats import wilcoxon

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reproduce all paper figures from pre-computed artifacts."
    )
    parser.add_argument(
        "--artifacts",
        type=str,
        default=None,
        help="Path to the artifacts/ directory. Defaults to <repo_root>/artifacts/.",
    )
    parser.add_argument(
        "--length-sensitivity",
        action="store_true",
        default=False,
        help="Run the length-sensitivity analysis (requires HF tokenizers + network access).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

paul_tol_palette = [
    "#332288",
    "#117733",
    "#44AA99",
    "#88CCEE",
    "#DDCC77",
    "#CC6677",
    "#AA4499",
    "#882255",
]

paul_tol_palette_alt = [
    "#88CCEE",
    "#44AA99",
    "#332288",
    "#117733",
    "#DDCC77",
    "#CC6677",
    "#AA4499",
    "#882255",
]

prettier_names = {
    "openai-community/gpt2": "GPT-2",
    "microsoft/codebert-base": "CodeBERT",
    "WizardLMTeam/WizardCoder-15B-V1.0": "WizardCoder 15B",
    "Salesforce/codegen-6B-multi": "Codegen 6B",
    "lmsys/vicuna-7b-v1.5": "Vicuna 7B",
    "lmsys/vicuna-13b-v1.5": "Vicuna 13B",
    "Qwen/Qwen2.5-Coder-0.5B-Instruct": "Qwen 0.5B",
    "deepseek-ai/deepseek-coder-6.7b-base": "Deepseek 6.7B",
    "meta-llama/CodeLlama-7b-hf": "CodeLlama 7B",
    "meta-llama/CodeLlama-13b-hf": "CodeLlama 13B",
    "meta-llama/Llama-3.2-3B-Instruct": "Llama 3.2B",
    "yulan-team/YuLan-Mini": "YuLan Mini",
    "JetBrains/Mellum-4b-base": "Mellum 4B",
    "bigcode/starcoder2-3b": "StarCoder2 3B",
    "bigcode/starcoder2-7b": "StarCoder2 7B",
}

MODEL_LABELS = {
    "meta-llama/CodeLlama-7b-hf": "CodeLlama 7B",
    "meta-llama/CodeLlama-13b-hf": "CodeLlama 13B",
    "bigcode/starcoder2-3b": "StarCoder2 3B",
    "bigcode/starcoder2-7b": "StarCoder2 7B",
    "JetBrains/Mellum-4b-base": "Mellum 4B",
    "deepseek-ai/deepseek-coder-6.7b-base": "DeepSeek 6.7B",
}


def extract_cwe_number(cwe_str):
    try:
        return int(cwe_str.split("-")[1])
    except Exception:
        return 9999


def get_cwe_number(x: str) -> int:
    number = x.split("-")[-1]
    try:
        return int(number)
    except ValueError:
        return -1


def save(fig_path):
    os.makedirs(os.path.dirname(fig_path), exist_ok=True)
    plt.savefig(fig_path, dpi=500, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {fig_path}")


# ---------------------------------------------------------------------------
# Section 1 — Load dataset (chosen/rejected pairs)
# ---------------------------------------------------------------------------


def load_dataset(data_dir):
    print("\n[1] Loading alignment dataset...")
    original_df = pd.DataFrame(
        columns=[
            "cwe",
            "additions",
            "deletions",
            "vuln_id",
            "vuln_code",
            "patched_code",
        ]
    )
    for file in os.listdir(data_dir):
        if not file.endswith(".jsonl"):
            continue
        with open(os.path.join(data_dir, file)) as f:
            for line in f:
                data = json.loads(line)
                row = pd.DataFrame(
                    {
                        "cwe": data["cwe"],
                        "additions": [data["additions"]],
                        "deletions": [data["deletions"]],
                        "vuln_id": [data["vuln_id"]],
                        "vuln_code": [data["rejected"]],
                        "patched_code": [data["chosen"]],
                    }
                )
                original_df = pd.concat([original_df, row], ignore_index=True)
    original_df["additions"] = original_df["additions"].astype(int)
    original_df["deletions"] = original_df["deletions"].astype(int)
    print(f"  {len(original_df)} samples across {original_df['cwe'].nunique()} CWEs")
    return original_df


# ---------------------------------------------------------------------------
# Section 2 — Dataset distribution plot
# ---------------------------------------------------------------------------


def plot_dataset_distribution(original_df, plots_dir):
    print("\n[2] Dataset distribution plot...")
    ordered_cwe = original_df["cwe"].value_counts().index
    sns.set(style="whitegrid", font_scale=1.2)
    plt.figure(figsize=(14, 6))
    ax = sns.countplot(
        data=original_df,
        x="cwe",
        order=ordered_cwe,
        palette=paul_tol_palette * (len(ordered_cwe) // len(paul_tol_palette) + 1),
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=10)
    ax.set_title("Distribution of CWE Categories", fontsize=16, weight="bold")
    ax.set_xlabel("Common Weakness Enumeration (CWE)", fontsize=13)
    ax.set_ylabel("Frequency", fontsize=13)
    for container in ax.containers:
        ax.bar_label(container, fmt="%d", label_type="edge", fontsize=9, padding=2)
    plt.tight_layout()
    save(os.path.join(plots_dir, "dataset_distribution.pdf"))


# ---------------------------------------------------------------------------
# Section 3 — Load model results
# ---------------------------------------------------------------------------


def load_results(results_dir):
    print("\n[3] Loading model results...")
    df = pd.DataFrame(
        columns=[
            "model",
            "cwe",
            "dpo_loss",
            "Aligned",
            "ppl_diff",
            "uncertainty_diff",
            "vuln_ids",
            "rejected_code",
            "patched_code",
        ]
    )
    for file in os.listdir(results_dir):
        if not file.endswith(".jsonl") or file in [
            "NVD-CWE-Other.jsonl",
            "alignment_stats.jsonl",
        ]:
            continue
        with open(os.path.join(results_dir, file)) as f:
            seen_models = set()
            for line in f:
                data = json.loads(line)
                model = data["model"]
                if model in seen_models:
                    continue
                seen_models.add(model)
                cwe = data["cwe"]
                dpo_losses, ppl_diffs, aligned, uncertainty_diffs = [], [], [], []
                vuln_ids, rejected_code, patched_code = [], [], []
                for snippet in data["snippets"]:
                    dpo_losses.append(snippet["dpo_loss"])
                    ppl_diffs.append(snippet["ppl_diff"])
                    aligned.append(snippet["aligned"])
                    uncertainty_diffs.append(snippet["uncertainty_diff"])
                    vuln_ids.append(snippet["vuln_id"])
                    rejected_code.append(snippet["rejected"])
                    patched_code.append(snippet["chosen"])
                row = pd.DataFrame(
                    {
                        "model": [model],
                        "cwe": [cwe],
                        "dpo_loss": [dpo_losses],
                        "Aligned": [aligned],
                        "ppl_diff": [ppl_diffs],
                        "uncertainty_diff": [uncertainty_diffs],
                        "vuln_ids": [vuln_ids],
                        "rejected_code": [rejected_code],
                        "patched_code": [patched_code],
                    }
                )
                df = pd.concat([df, row], ignore_index=True)
    df["cwe_number"] = df["cwe"].apply(get_cwe_number)
    df["base_cwe"] = df["cwe"]
    print(f"  {len(df)} model×CWE entries across {df['model'].nunique()} models")
    return df


# ---------------------------------------------------------------------------
# Section 4 — PPL diff bar chart
# ---------------------------------------------------------------------------


def plot_ppl_diff(df, plots_dir):
    print("\n[4] PPL difference plot...")
    all_models_df = []
    for model_name in df["model"].unique():
        model_df = df[df["model"] == model_name].copy()
        model_df["ppl_diff_avg"] = model_df["ppl_diff"].apply(
            lambda d: sum(d) / len(d) if isinstance(d, list) and d else 0
        )
        summary = model_df[["base_cwe", "cwe_number", "ppl_diff_avg"]].copy()
        summary["model"] = model_name
        summary.rename(columns={"ppl_diff_avg": "diff"}, inplace=True)
        all_models_df.append(summary)
    combined = pd.concat(all_models_df).sort_values("cwe_number")
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        data=combined, x="base_cwe", y="diff", hue="model", palette=paul_tol_palette_alt
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title("Average PPL Difference (Vulnerable − Patched) by CWE Across Models")
    plt.xlabel("CWE")
    plt.ylabel("PPL Difference")
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "ppl_diff_all.pdf"))


# ---------------------------------------------------------------------------
# Section 5 — Uncertainty diff bar chart
# ---------------------------------------------------------------------------


def plot_uncertainty_diff(df, plots_dir):
    print("\n[5] Uncertainty difference plot...")
    all_models_df = []
    for model_name in df["model"].unique():
        model_df = df[df["model"] == model_name].copy()
        model_df["unc_diff_avg"] = model_df["uncertainty_diff"].apply(
            lambda d: sum(d) / len(d) if isinstance(d, list) and d else 0
        )
        summary = model_df[["base_cwe", "cwe_number", "unc_diff_avg"]].copy()
        summary["model"] = model_name
        summary.rename(columns={"unc_diff_avg": "diff"}, inplace=True)
        all_models_df.append(summary)
    combined = pd.concat(all_models_df).sort_values("cwe_number")
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        data=combined, x="base_cwe", y="diff", hue="model", palette=paul_tol_palette_alt
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title(
        "Average Uncertainty Difference (Vulnerable − Patched) by CWE Across Models"
    )
    plt.xlabel("CWE")
    plt.ylabel("Uncertainty Difference")
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "rebuttal", "uncertainty_diff_all.pdf"))


# ---------------------------------------------------------------------------
# Section 6 — DPO loss diff bar chart
# ---------------------------------------------------------------------------


def plot_dpo_loss_diff(df, plots_dir):
    print("\n[6] DPO loss difference plot...")
    all_models_df = []
    for model_name in df["model"].unique():
        model_df = df[df["model"] == model_name].copy()
        model_df["dpo_avg"] = model_df["dpo_loss"].apply(
            lambda d: sum(d) / len(d) if isinstance(d, list) and d else 0
        )
        summary = model_df[["base_cwe", "cwe_number", "dpo_avg"]].copy()
        summary["model"] = model_name
        summary.rename(columns={"dpo_avg": "diff"}, inplace=True)
        all_models_df.append(summary)
    combined = pd.concat(all_models_df).sort_values("cwe_number")
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        data=combined, x="base_cwe", y="diff", hue="model", palette=paul_tol_palette_alt
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title("Average DPO Loss by CWE Across Models")
    plt.xlabel("CWE")
    plt.ylabel("DPO Loss")
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "rebuttal", "dpo_loss_diff_all.pdf"))


# ---------------------------------------------------------------------------
# Section 7 — Preferred alignment bar chart
# ---------------------------------------------------------------------------


def plot_preferred_avg(df, plots_dir):
    print("\n[7] Preferred alignment average plot...")
    all_models_df = []
    for model_name in df["model"].unique():
        model_df = df[df["model"] == model_name].copy()
        model_df["aligned_avg"] = model_df["Aligned"].apply(
            lambda d: (
                sum(1 if a else -1 for a in d) / len(d)
                if isinstance(d, list) and d
                else 0
            )
        )
        summary = model_df[["base_cwe", "cwe_number", "aligned_avg"]].copy()
        summary["model"] = model_name
        summary.rename(columns={"aligned_avg": "diff"}, inplace=True)
        all_models_df.append(summary)
    combined = pd.concat(all_models_df).sort_values("cwe_number")
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        data=combined, x="base_cwe", y="diff", hue="model", palette=paul_tol_palette_alt
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title("Average Alignment Signal by CWE Across Models")
    plt.xlabel("CWE")
    plt.ylabel('Preferred "Average"')
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "rebuttal", "aligned_avg_all.pdf"))


# ---------------------------------------------------------------------------
# Section 8 — DPO loss heatmap + per-model bar chart
# ---------------------------------------------------------------------------

import torch
import torch.nn.functional as F


def dpo_loss_fn(chosen_logprob, rejected_logprob, beta=1.0):
    delta = beta * (chosen_logprob - rejected_logprob)
    return F.softplus(-delta)


def softplus_inverse(y):
    return torch.log(torch.expm1(y))


def invert_dpo_delta_from_loss(loss):
    delta = -softplus_inverse(loss).item()
    return 0.0 if delta == float("-inf") else delta


def plot_dpo_heatmap(df, plots_dir):
    print("\n[8] DPO loss heatmap and per-model bar chart...")
    top_cwes = df.explode(["dpo_loss"])["cwe"].value_counts().nlargest(12).index

    # Build summary table
    list_columns = ["dpo_loss", "Aligned", "ppl_diff", "uncertainty_diff", "vuln_ids"]
    df_t = df.explode(list_columns, ignore_index=True)
    df_t["dpo_loss"] = df_t["dpo_loss"].astype(float)
    df_top = df_t[df_t["cwe"].isin(top_cwes)]

    summary_table = (
        df_top.groupby(["cwe", "model"])["dpo_loss"]
        .agg(count="count", mean="mean", std="std")
        .reset_index()
    )
    summary_table["cwe_numeric"] = summary_table["cwe"].apply(get_cwe_number)
    summary_table = summary_table.sort_values(["cwe_numeric", "model"]).drop(
        columns="cwe_numeric"
    )
    summary_table["model"] = summary_table["model"].map(
        lambda x: prettier_names.get(x, x)
    )
    pivot_table = summary_table.pivot(
        index="cwe", columns="model", values="mean"
    ).round(1)

    # Heatmap
    tol_cmap = LinearSegmentedColormap.from_list("paul_tol", paul_tol_palette, N=256)
    plt.figure(figsize=(12, 7))
    ax = sns.heatmap(
        pivot_table,
        annot=True,
        fmt=".1f",
        cmap="Greens",
        linewidths=0.5,
        linecolor="gray",
        cbar_kws={"label": "Mean DPO Loss"},
        annot_kws={"fontsize": 10},
        center=np.nanmean(pivot_table.values),
    )
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right", fontsize=12)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=12)
    plt.title("Mean Preference Loss per CWE and Model", fontsize=14, pad=15)
    plt.xlabel("Model", fontsize=15)
    plt.ylabel("CWE", fontsize=15)
    plt.tight_layout()
    save(os.path.join(plots_dir, "figure5_replacement_dpo_heatmap.pdf"))

    # Per-model average bar chart
    avg_dpo_per_model = summary_table.groupby("model")["mean"].mean().sort_values()
    plt.figure(figsize=(12, 7))
    ax = sns.barplot(
        x=avg_dpo_per_model.values, y=avg_dpo_per_model.index, palette=paul_tol_palette
    )
    ax.set_xlabel("Average Preference Loss", fontsize=16)
    ax.set_ylabel("Model", fontsize=16)
    ax.set_xlim(40, 70)
    ax.tick_params(axis="x", labelsize=12)
    ax.tick_params(axis="y", labelsize=12)
    ax.set_title(
        "Model-Level Preference with Secure Code (Average Preference Loss)",
        fontsize=14,
        pad=12,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "figure5b_avg_dpo_per_model.pdf"))

    return df_t, summary_table


# ---------------------------------------------------------------------------
# Section 9 — Log-prob diff (inverted from DPO loss)
# ---------------------------------------------------------------------------


def plot_logprob_diff(df, plots_dir):
    print("\n[9] Log-prob diff (inverted DPO) plot...")
    all_models_df = []
    for model_name in df["model"].unique():
        model_df = df[df["model"] == model_name].copy()
        model_df["log_prob_diff_avg"] = model_df["dpo_loss"].apply(
            lambda x: (
                sum(
                    invert_dpo_delta_from_loss(torch.tensor(a))
                    for a in x
                    if float(a) != 0
                )
                / len(x)
                if isinstance(x, list) and x
                else 0
            )
        )
        summary = model_df[["base_cwe", "cwe_number", "log_prob_diff_avg"]].copy()
        summary["model"] = model_name
        summary.rename(columns={"log_prob_diff_avg": "diff"}, inplace=True)
        all_models_df.append(summary)
    combined = pd.concat(all_models_df).sort_values("cwe_number")
    plt.figure(figsize=(14, 7))
    ax = sns.barplot(
        data=combined, x="base_cwe", y="diff", hue="model", palette=paul_tol_palette_alt
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title("Average Log-Prob Diff (Inverted from DPO Loss) by CWE Across Models")
    plt.xlabel("CWE")
    plt.ylabel("Log Prob Diff Average")
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "rebuttal", "log_prob_diff_avg_all.pdf"))


# ---------------------------------------------------------------------------
# Section 10 — Wilcoxon tests
# ---------------------------------------------------------------------------


def run_wilcoxon_tests(df, plots_dir):
    print("\n[10] Wilcoxon signed-rank tests...")

    # DPO loss vs PPL diff
    results_dpo = []
    for _, row in df.iterrows():
        try:
            stat, p = wilcoxon(row["dpo_loss"], row["ppl_diff"])
        except Exception:
            stat, p = None, None
        results_dpo.append(
            {
                "model": row["model"],
                "cwe": row["cwe"],
                "wilcoxon_statistic": stat,
                "p_value": p,
                "n_samples": len(row["dpo_loss"]),
            }
        )
    wilcoxon_df = pd.DataFrame(results_dpo)
    wilcoxon_df["significant"] = wilcoxon_df["p_value"] < 0.05
    pivot = wilcoxon_df.pivot(index="cwe", columns="model", values="p_value")
    mask = (pivot > 0.05).fillna(True)
    plt.figure(figsize=(20, 10))
    ax = sns.heatmap(
        pivot,
        mask=mask,
        annot=True,
        fmt=".2e",
        cmap="Greens",
        cbar_kws={"label": "p-value"},
    )
    for y in range(pivot.shape[0]):
        for x in range(pivot.shape[1]):
            p_val = pivot.iloc[y, x]
            if pd.notnull(p_val) and p_val > 0.05:
                ax.text(
                    x + 0.5,
                    y + 0.5,
                    "*",
                    color="black",
                    ha="center",
                    va="center",
                    fontsize=20,
                    fontweight="bold",
                )
    plt.title("Wilcoxon p-values (DPO Loss vs PPL Diff) by CWE and Model")
    plt.ylabel("CWE")
    plt.xlabel("Model")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    save(os.path.join(plots_dir, "Wilcoxon_dpo_loss.pdf"))
    print(
        f"  DPO Wilcoxon — significant: {wilcoxon_df['significant'].value_counts().to_dict()}"
    )

    # Uncertainty diff
    results_unc = []
    for _, row in df.iterrows():
        try:
            stat, p = wilcoxon(row["uncertainty_diff"])
        except Exception:
            stat, p = None, None
        results_unc.append(
            {
                "model": row["model"],
                "cwe": row["cwe"],
                "wilcoxon_statistic": stat,
                "p_value": p,
                "n_samples": len(row["uncertainty_diff"]),
            }
        )
    wilcoxon_unc_df = pd.DataFrame(results_unc)
    wilcoxon_unc_df["significant"] = wilcoxon_unc_df["p_value"] < 0.05
    pivot_unc = wilcoxon_unc_df.pivot(index="cwe", columns="model", values="p_value")
    plt.figure(figsize=(20, 10))
    sns.heatmap(
        pivot_unc,
        annot=True,
        fmt=".2e",
        cmap="Purples",
        cbar_kws={"label": "p-value", "ticks": [0.00, 0.05], "format": "%.2f"},
        vmin=0,
        vmax=0.05,
    )
    plt.title("Wilcoxon p-values (Uncertainty Diff) by CWE and Model")
    plt.ylabel("CWE")
    plt.xlabel("Model")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    save(os.path.join(plots_dir, "Wilcoxon_uncert.pdf"))
    print(
        f"  Uncertainty Wilcoxon — significant: {wilcoxon_unc_df['significant'].value_counts().to_dict()}"
    )

    # BT loss only
    results_bt = []
    for _, row in df.iterrows():
        try:
            stat, p = wilcoxon(row["dpo_loss"])
        except Exception:
            stat, p = None, None
        results_bt.append(
            {
                "model": row["model"],
                "cwe": row["cwe"],
                "wilcoxon_statistic": stat,
                "p_value": p,
                "n_samples": len(row["dpo_loss"]),
            }
        )
    wilcoxon_bt_df = pd.DataFrame(results_bt)
    wilcoxon_bt_df["significant"] = wilcoxon_bt_df["p_value"] < 0.05
    pivot_bt = wilcoxon_bt_df.pivot(index="cwe", columns="model", values="p_value")
    plt.figure(figsize=(20, 10))
    sns.heatmap(
        pivot_bt,
        annot=True,
        fmt=".2e",
        cmap="Blues",
        cbar_kws={"label": "p-value", "ticks": [0.00, 0.05], "format": "%.2f"},
    )
    plt.title("Wilcoxon p-values (BT Loss) by CWE and Model")
    plt.ylabel("CWE")
    plt.xlabel("Model")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    save(os.path.join(plots_dir, "Wilcoxon_bt_loss.pdf"))
    print(
        f"  BT Loss Wilcoxon — significant: {wilcoxon_bt_df['significant'].value_counts().to_dict()}"
    )


# ---------------------------------------------------------------------------
# Section 11 — Transversal (exploded) analysis and alignment graphs
# ---------------------------------------------------------------------------


def build_transversal(df):
    print("\n[11] Building transversal (per-sample) dataframe...")
    list_columns = ["dpo_loss", "Aligned", "ppl_diff", "uncertainty_diff", "vuln_ids"]
    df_t = df.explode(list_columns, ignore_index=True)
    df_t["dpo_loss"] = df_t["dpo_loss"].astype(float)
    df_t["ppl_diff"] = df_t["ppl_diff"].astype(float)
    df_t["uncertainty_diff"] = df_t["uncertainty_diff"].astype(float)
    return df_t


def print_alignment_stats(df_t):
    print("\n[12] Alignment statistics:")
    print("  -- DPO alignment (logprob) --")
    df_aligned = df_t[df_t["Aligned"] == True]
    for model in df_t["model"].unique():
        m = df_t[df_t["model"] == model]
        ma = df_aligned[df_aligned["model"] == model]
        print(
            f"    {prettier_names.get(model, model):20s}  {len(ma)/len(m)*100:.1f}%  ({len(ma)}/{len(m)})"
        )

    print("  -- Fluency (ppl_diff > 0) --")
    df_fluent = df_t[df_t["ppl_diff"] > 0]
    for model in df_t["model"].unique():
        m = df_t[df_t["model"] == model]
        mf = df_fluent[df_fluent["model"] == model]
        print(
            f"    {prettier_names.get(model, model):20s}  {len(mf)/len(m)*100:.1f}%  ({len(mf)}/{len(m)})"
        )

    print("  -- Certainty (uncertainty_diff > 0) --")
    df_cert = df_t[df_t["uncertainty_diff"] > 0]
    for model in df_t["model"].unique():
        m = df_t[df_t["model"] == model]
        mc = df_cert[df_cert["model"] == model]
        print(
            f"    {prettier_names.get(model, model):20s}  {len(mc)/len(m)*100:.1f}%  ({len(mc)}/{len(m)})"
        )

    print("  -- Full alignment (Aligned + ppl>0 + uncertainty>0) --")
    df_full = df_t[
        (df_t["Aligned"] == True)
        & (df_t["ppl_diff"] > 0)
        & (df_t["uncertainty_diff"] > 0)
    ]
    for model in df_t["model"].unique():
        m = df_t[df_t["model"] == model]
        mf = df_full[df_full["model"] == model]
        print(
            f"    {prettier_names.get(model, model):20s}  {len(mf)/len(m)*100:.1f}%  ({len(mf)}/{len(m)})"
        )


def plot_alignment_graph(df_t, plots_dir):
    print("\n[13] Alignment by CWE graph...")
    df_t = df_t.copy()
    df_t["cwe_number"] = df_t["cwe"].apply(get_cwe_number)
    df_filtered = df_t[
        (df_t["Aligned"] == True)
        & (df_t["ppl_diff"] > 0)
        & (df_t["uncertainty_diff"] > 0)
    ]
    df_filtered = df_filtered.copy()
    df_filtered["cwe_number"] = df_filtered["cwe"].apply(get_cwe_number)
    df_filtered["base_cwe"] = df_filtered["cwe"]
    count_df = (
        df_filtered.groupby(["model", "base_cwe", "cwe_number"])
        .size()
        .reset_index(name="count")
    )
    count_all_df = (
        df_t.groupby(["model", "base_cwe", "cwe_number"])
        .size()
        .reset_index(name="count_all")
    )
    count_df = count_df.merge(count_all_df, on=["model", "base_cwe", "cwe_number"])
    count_df["count"] = (count_df["count"] / count_df["count_all"]) * 100
    count_df = count_df.drop(columns=["count_all"]).sort_values("cwe_number")

    plt.figure(figsize=(14, 5))
    ax = sns.barplot(
        data=count_df,
        x="base_cwe",
        y="count",
        hue="model",
        palette=paul_tol_palette_alt,
    )
    plt.axhline(0, color="gray", linestyle="--")
    plt.title("Alignment by CWE Across Models")
    plt.xlabel("CWE")
    plt.ylabel("Alignment (%)")
    plt.xticks(rotation=45)
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles=handles,
        labels=[prettier_names.get(l, l) for l in labels],
        title="Model",
        title_fontsize=12,
        fontsize=10,
    )
    plt.tight_layout()
    save(os.path.join(plots_dir, "alignemnt_graph_shorter.pdf"))


def plot_ppl_uncertainty_scatter(df_t, plots_dir):
    print("\n[14] PPL vs uncertainty scatter plots...")
    df_t = df_t.copy()
    df_t["Preferred"] = df_t["Aligned"]
    models = df_t["model"].unique()
    alignment_palette = {True: "#117733", False: "#CC6677"}

    # Per-model grid
    n_cols = 3
    n_rows = (len(models) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(8 * n_cols, 6 * n_rows), sharex=True, sharey=True
    )
    axes = axes.flatten()
    for i, model in enumerate(models):
        ax = axes[i]
        df_model = df_t[df_t["model"] == model]
        sns.scatterplot(
            data=df_model,
            x="ppl_diff",
            y="uncertainty_diff",
            hue="Preferred",
            style="Preferred",
            s=40,
            palette=alignment_palette,
            ax=ax,
        )
        ax.axhline(0, color="grey", linestyle="--")
        ax.axvline(0, color="grey", linestyle="--")
        ax.set_title(prettier_names.get(model, model))
        ax.set_xlabel("PPL Difference (\u2192 Better Fluency)")
        ax.set_ylabel("Uncertainty Difference (\u2192 More Confident in Secure Code)")
        ax.set_xscale("symlog")
    for j in range(i + 1, len(axes)):
        fig.delaxes(axes[j])
    plt.suptitle("PPL vs. Uncertainty Difference per Model", fontsize=16)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    save(os.path.join(plots_dir, "ppl_diff_uncertainty_all.pdf"))

    # All models combined
    plt.figure(figsize=(10, 8))
    sns.scatterplot(
        data=df_t,
        x="ppl_diff",
        y="uncertainty_diff",
        hue="Preferred",
        palette=alignment_palette,
        s=60,
        facecolors="none",
        edgecolors="black",
        linewidth=0.8,
        legend=False,
        alpha=0.5,
    )
    plt.axhline(0, color="grey", linestyle="--")
    plt.axvline(0, color="grey", linestyle="--")
    plt.xlabel("PPL Difference (\u2192 Better Fluency)")
    plt.ylabel("Uncertainty Difference (\u2192 More Confident in Secure Code)")
    plt.xscale("symlog")
    plt.title("PPL vs. Uncertainty Difference (All Models Combined)")
    legend_elements = [
        Patch(facecolor=alignment_palette[True], edgecolor="black", label="Preferred"),
        Patch(
            facecolor=alignment_palette[False], edgecolor="black", label="Not Preferred"
        ),
    ]
    plt.legend(handles=legend_elements, title="Preferred", frameon=True)
    plt.tight_layout()
    save(os.path.join(plots_dir, "ppl_diff_uncertainty_all_together.pdf"))


# ---------------------------------------------------------------------------
# Section 12 — Condition counts table
# ---------------------------------------------------------------------------


def compute_condition_counts(df_t, plots_dir):
    print("\n[15] Condition counts table...")
    df_t = df_t.copy()
    df_t["cond_aligned"] = df_t["Aligned"]
    df_t["cond_ppl_pos"] = df_t["ppl_diff"] > 0
    df_t["cond_unc_pos"] = df_t["uncertainty_diff"] > 0
    condition_labels = ["Aligned", "ppl_diff>0", "uncertainty_diff>0"]
    conditions = list(itertools.product([False, True], repeat=3))
    rows = []
    for model in df_t["model"].unique():
        df_m = df_t[df_t["model"] == model]
        total = len(df_m)
        for combo in conditions:
            df_subset = df_m[
                (df_m["cond_aligned"] == combo[0])
                & (df_m["cond_ppl_pos"] == combo[1])
                & (df_m["cond_unc_pos"] == combo[2])
            ]
            count = len(df_subset)
            rows.append(
                {
                    "model": model,
                    **{label: val for label, val in zip(condition_labels, combo)},
                    "percentage": round(count / total * 100, 2) if total > 0 else 0,
                }
            )
    df_conditions = pd.DataFrame(rows)
    out_csv = os.path.join(plots_dir, "rebuttal", "condition_counts.csv")
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df_conditions.to_csv(out_csv, index=False)
    print(f"  Saved: {out_csv}")

    out_tex = os.path.join(plots_dir, "rebuttal", "condition_counts.tex")
    with open(out_tex, "w") as f:
        f.write(df_conditions.to_latex(index=False))
    print(f"  Saved: {out_tex}")

    grouped = df_conditions.groupby(["Aligned", "ppl_diff>0", "uncertainty_diff>0"])[
        "percentage"
    ].agg(["mean", "std"])
    print("  Condition statistics (mean ± std across models):")
    print(grouped.to_string())


# ---------------------------------------------------------------------------
# Section 13 — Macro-averaging (alignment rate per model)
# ---------------------------------------------------------------------------


def compute_macro_alignment(df_t):
    print("\n[16] Macro-averaging alignment rates...")
    MIN_SAMPLES = 30
    df = df_t.copy()
    df["aligned"] = (
        (df["Aligned"] == True) & (df["ppl_diff"] > 0) & (df["uncertainty_diff"] > 0)
    )
    df["model_short"] = df["model"].map(MODEL_LABELS).fillna(df["model"])
    cwe_model_stats = (
        df.groupby(["model_short", "base_cwe"])
        .agg(n=("aligned", "count"), align_rate=("aligned", "mean"))
        .reset_index()
    )
    cwe_model_stats = cwe_model_stats[cwe_model_stats["n"] >= MIN_SAMPLES]
    print(f"  {'Model':20s}  {'Micro':>7}  {'Macro':>7}")
    for model in df["model_short"].unique():
        df_m = df[df["model_short"] == model]
        cwe_m = cwe_model_stats[cwe_model_stats["model_short"] == model]
        micro = df_m["aligned"].mean()
        macro = cwe_m["align_rate"].mean() if len(cwe_m) else float("nan")
        print(f"  {model:20s}  {micro:.2%}  {macro:.2%}")


# ---------------------------------------------------------------------------
# Section 14 — Length sensitivity (optional, requires HF tokenizers)
# ---------------------------------------------------------------------------


def run_length_sensitivity(df_t):
    print("\n[17] Length sensitivity analysis (requires HF tokenizers + network)...")
    try:
        import statsmodels.api as sm
        from scipy import stats
        from tqdm import tqdm
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"  Skipped: missing dependency ({e})")
        return

    tqdm.pandas()
    MODELS = list(MODEL_LABELS.keys())
    results = []
    for model_id in MODELS:
        label = MODEL_LABELS[model_id]
        print(f"  {label}")
        df_model = df_t[df_t["model"] == model_id].copy()
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        df_model["rejected_token_count"] = df_model["rejected_code"].progress_apply(
            lambda x: len(tokenizer.encode(x[0]))
        )
        df_model["patched_token_count"] = df_model["patched_code"].progress_apply(
            lambda x: len(tokenizer.encode(x[0]))
        )
        df_model["token_diff"] = (
            df_model["patched_token_count"] - df_model["rejected_token_count"]
        )
        df_model["token_diff_signal"] = (df_model["token_diff"] > 0).astype(int)
        df_model["Aligned_int"] = df_model["Aligned"].astype(int)
        r = (
            df_model[["token_diff_signal", "Aligned_int"]]
            .corr()
            .loc["token_diff_signal", "Aligned_int"]
        )
        contingency = pd.crosstab(
            df_model["token_diff_signal"], df_model["Aligned_int"]
        )
        chi2_val, p_chi2, _, _ = stats.chi2_contingency(contingency)
        X = sm.add_constant(df_model["token_diff"])
        y = df_model["Aligned_int"]
        logit_model = sm.Logit(y, X).fit(disp=0)
        coef = logit_model.params["token_diff"]
        pval = logit_model.pvalues["token_diff"]
        results.append(
            {
                "model": label,
                "r": r,
                "r2": r**2,
                "chi2": chi2_val,
                "p_chi2": p_chi2,
                "logit_coef": coef,
                "logit_p": pval,
            }
        )
    summary = pd.DataFrame(results).set_index("model")
    print("\n  Length sensitivity summary:")
    print(summary.to_string(float_format=lambda x: f"{x:.4f}"))


# ---------------------------------------------------------------------------
# Section 15 — Mean preference per CWE and model
# ---------------------------------------------------------------------------


def plot_mean_pref_cwe_model(df_t, plots_dir):
    print("\n[18] Mean preference per CWE and model heatmap...")
    df = df_t.copy()
    df["model_short"] = df["model"].map(MODEL_LABELS).fillna(df["model"])
    df["Aligned_int"] = df["Aligned"].astype(int)

    pivot = df.groupby(["base_cwe", "model_short"])["Aligned_int"].mean().unstack()
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        pivot * 100,
        annot=True,
        fmt=".1f",
        cmap="Greens",
        linewidths=0.5,
        cbar_kws={"label": "% Aligned"},
        vmin=0,
        vmax=100,
        annot_kws={"fontsize": 9},
    )
    plt.title("Alignment Rate (%) per CWE and Model", fontsize=14)
    plt.xlabel("Model", fontsize=13)
    plt.ylabel("CWE", fontsize=13)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    save(os.path.join(plots_dir, "mean_pref_cwe_model.pdf"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    args = parse_args()

    # Resolve artifacts directory
    if args.artifacts:
        artifacts_dir = os.path.abspath(args.artifacts)
    else:
        # Default: <repo_root>/artifacts/
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        artifacts_dir = os.path.join(repo_root, "artifacts")

    data_dir = os.path.join(artifacts_dir, "security_alignment", "data")
    results_dir = os.path.join(
        artifacts_dir, "security_alignment", "all_models_results"
    )
    plots_dir = os.path.join(artifacts_dir, "plots")

    print(f"Artifacts: {artifacts_dir}")
    print(f"Plots output: {plots_dir}")
    os.makedirs(plots_dir, exist_ok=True)
    os.makedirs(os.path.join(plots_dir, "rebuttal"), exist_ok=True)

    # --- Load data ---
    original_df = load_dataset(data_dir)
    df = load_results(results_dir)

    # --- Figures ---
    plot_dataset_distribution(original_df, plots_dir)
    plot_ppl_diff(df, plots_dir)
    plot_uncertainty_diff(df, plots_dir)
    plot_dpo_loss_diff(df, plots_dir)
    plot_preferred_avg(df, plots_dir)
    df_t, summary_table = plot_dpo_heatmap(df, plots_dir)
    plot_logprob_diff(df, plots_dir)
    run_wilcoxon_tests(df, plots_dir)
    df_t = build_transversal(df)
    print_alignment_stats(df_t)
    plot_alignment_graph(df_t, plots_dir)
    plot_ppl_uncertainty_scatter(df_t, plots_dir)
    compute_condition_counts(df_t, plots_dir)
    compute_macro_alignment(df_t)
    plot_mean_pref_cwe_model(df_t, plots_dir)

    if args.length_sensitivity:
        run_length_sensitivity(df_t)

    print(f"\nDone. All figures saved to {plots_dir}/")


if __name__ == "__main__":
    main()
