"""Quick analysis script — prints breakdowns and saves a plot.

Usage: python -m experiment.analyze results/scored.csv
"""
import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    args = ap.parse_args()
    df = pd.read_csv(args.csv)

    print("\n=== Per-condition means ===")
    cols = ["correctness", "reward_hack", "stress_language", "silent_degradation", "output_tokens"]
    if "truncated" in df.columns:
        cols.append("truncated")
    print(df.groupby("condition")[cols].mean().round(3))

    print("\n=== Per-task × condition correctness ===")
    print(df.pivot_table(index="task_id", columns="condition", values="correctness").round(3))

    print("\n=== Silent degradation rate (incorrect/hacked WITHOUT stress language) ===")
    print(df.groupby("condition")["silent_degradation"].mean().round(3))

    print("\n=== T4 plan:execute ratio ===")
    t4 = df[df.task_id == "T4_plan"]
    if len(t4):
        print(t4.groupby("condition")["plan_execute_ratio"].mean().round(3))


if __name__ == "__main__":
    main()
