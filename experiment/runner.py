"""Experiment runner: sweep conditions × tasks × seeds and log JSONL."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from experiment.conditions import CONDITIONS, Condition, build_messages
from experiment.tasks import TASKS, Task

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=True)


def run_one(client, model: str, task: Task, condition: Condition, seed: int) -> dict:
    messages = build_messages(condition, task.prompt)
    kwargs = dict(
        model=model,
        max_tokens=condition.max_tokens,
        messages=messages,
    )
    if condition.system:
        kwargs["system"] = condition.system

    t0 = time.time()
    resp = client.messages.create(**kwargs)
    elapsed = time.time() - t0

    text = "".join(b.text for b in resp.content if b.type == "text")
    return {
        "task_id": task.id,
        "condition": condition.id,
        "seed": seed,
        "model": model,
        "max_tokens": condition.max_tokens,
        "stop_reason": resp.stop_reason,
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "elapsed_sec": round(elapsed, 2),
        "response_text": text,
        "task_meta": task.meta,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-5-20250929")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--seed-start", type=int, default=0, help="starting seed index (for extending a prior run without re-running existing seeds)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tasks", nargs="*", default=None, help="subset of task ids")
    ap.add_argument("--conditions", nargs="*", default=None)
    args = ap.parse_args()

    tasks = [t for t in TASKS if not args.tasks or t.id in args.tasks]
    conds = [c for c in CONDITIONS if not args.conditions or c.id in args.conditions]

    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    total = len(tasks) * len(conds) * args.seeds
    print(f"Matrix: {len(tasks)} tasks × {len(conds)} conditions × {args.seeds} seeds = {total} runs")
    for t in tasks:
        print(f"  task: {t.id}")
    for c in conds:
        print(f"  cond: {c.id} (max_tokens={c.max_tokens}, pad={c.pad_tokens}, burn={c.burndown_turns})")

    if args.dry_run:
        print("DRY RUN — no API calls.")
        return

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Copy .env.example to .env.", file=sys.stderr)
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic()

    out_path = results_dir / f"run_{int(time.time())}.jsonl"
    print(f"Writing to {out_path}")
    done = 0
    with out_path.open("w") as f:
        for task in tasks:
            for cond in conds:
                for seed in range(args.seed_start, args.seed_start + args.seeds):
                    try:
                        rec = run_one(client, args.model, task, cond, seed)
                    except Exception as e:
                        rec = {
                            "task_id": task.id, "condition": cond.id, "seed": seed,
                            "error": str(e),
                        }
                    f.write(json.dumps(rec) + "\n")
                    f.flush()
                    done += 1
                    print(f"  [{done}/{total}] {task.id}/{cond.id}/seed{seed}")
    print(f"Done. Results: {out_path}")


if __name__ == "__main__":
    main()
