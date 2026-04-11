"""Generate publication-ready charts from scored data.

Usage: python -m experiment.plots results/scored.csv
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "figure.dpi": 140,
})

COND_ORDER = [
    "control",
    "framed_explicit",
    "padded_150k",
    "cap_soft",
    "burndown_coding",
    "burndown_long",
    "cap_hard",
]
LABELS = {
    "control": "Control",
    "framed_explicit": "Framed\n(explicit)",
    "padded_150k": "Padded\n(150k)",
    "cap_soft": "Cap soft\n(800)",
    "burndown_coding": "Burndown\n(15 turns)",
    "burndown_long": "Burndown\n(25 turns)",
    "cap_hard": "Cap hard\n(250)",
}
BLUE = "#2b6cb0"
ORANGE = "#c05621"
GREY = "#718096"
RED = "#c53030"


def _order(df: pd.DataFrame, col: str) -> pd.Series:
    grouped = df.groupby("condition")[col].mean()
    return grouped.reindex(COND_ORDER)


def chart_silent_degradation(df: pd.DataFrame, outdir: Path):
    correct = _order(df, "correctness")
    silent = _order(df, "silent_degradation")
    x = range(len(COND_ORDER))
    fig, ax = plt.subplots(figsize=(9, 4.8))
    w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], correct.values, w, label="Correctness", color=BLUE)
    b2 = ax.bar([i + w / 2 for i in x], silent.values, w, label="Silent degradation", color=ORANGE)
    ax.set_xticks(list(x))
    ax.set_xticklabels([LABELS[c] for c in COND_ORDER])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("Claude Sonnet 4.5 under token pressure:\ncorrectness drops while stress language stays absent",
                 loc="left", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", frameon=False)
    for bar, v in list(zip(b1, correct.values)) + list(zip(b2, silent.values)):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{v:.2f}", ha="center", fontsize=9, color="#2d3748")
    fig.text(0.01, 0.01,
             "Silent degradation = incorrect or shortcut output with no stress/apology language. "
             "n=10 per cell for control, framed_explicit, burndown_coding, cap_hard; n=5 elsewhere.",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = outdir / "chart_1_silent_degradation.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def chart_plan_compression(df: pd.DataFrame, outdir: Path):
    t4 = df[df.task_id == "T4_plan"].copy()
    ratios = t4.groupby("condition")["plan_execute_ratio"].mean().reindex(COND_ORDER)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    colors = [BLUE if c != "framed_explicit" else ORANGE for c in COND_ORDER]
    bars = ax.bar(range(len(COND_ORDER)), ratios.values, color=colors)
    control_val = ratios["control"]
    ax.axhline(control_val, color=RED, linestyle="--", linewidth=1, alpha=0.6, label=f"Control baseline ({control_val:.2f})")
    ax.set_xticks(range(len(COND_ORDER)))
    ax.set_xticklabels([LABELS[c] for c in COND_ORDER])
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Plan : execute character ratio")
    ax.set_title("Pressure compresses deliberation — but only when Claude 'feels' it\n(T4 plan-then-execute task)",
                 loc="left", fontsize=13, fontweight="bold")
    ax.legend(loc="upper right", frameon=False)
    for bar, v in zip(bars, ratios.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.015,
                f"{v:.2f}", ha="center", fontsize=9, color="#2d3748")
    fig.text(0.01, 0.01,
             "Cap conditions don't compress planning — the cap hits mid-execution, after Claude has already planned normally. "
             "Framed_explicit shows the largest compression (-35%) yet holds 100% correctness.",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    path = outdir / "chart_2_plan_compression.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def chart_dose_response(df: pd.DataFrame, outdir: Path):
    subset = df[df.condition.isin(["control", "cap_soft", "cap_hard"])]
    metrics = ["correctness", "silent_degradation", "truncated"]
    labels = ["Correctness", "Silent degradation", "Truncated"]
    conds = ["control", "cap_soft", "cap_hard"]
    cond_labels = ["Control\n(8000 tok)", "Cap soft\n(800 tok)", "Cap hard\n(250 tok)"]
    means = subset.groupby("condition")[metrics].mean().reindex(conds)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    x = range(len(metrics))
    w = 0.26
    colors = [GREY, BLUE, ORANGE]
    for i, cond in enumerate(conds):
        offset = (i - 1) * w
        vals = means.loc[cond].values
        bars = ax.bar([xi + offset for xi in x], vals, w, label=cond_labels[i], color=colors[i])
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                    f"{v:.2f}", ha="center", fontsize=9, color="#2d3748")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("Hard max_tokens caps: dose-response on silent failure",
                 loc="left", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", frameon=False, ncol=3)
    fig.text(0.01, 0.01,
             "Tighter output caps cause Claude to plow ahead and get truncated mid-sentence rather than replan a shorter answer. "
             "Silent-failure rate rises in lockstep.",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    path = outdir / "chart_3_dose_response.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--outdir", default="results/plots")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    chart_silent_degradation(df, outdir)
    chart_plan_compression(df, outdir)
    chart_dose_response(df, outdir)


if __name__ == "__main__":
    main()
