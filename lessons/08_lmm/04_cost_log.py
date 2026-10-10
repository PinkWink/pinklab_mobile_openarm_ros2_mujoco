#!/usr/bin/env python3
"""Lesson 08-4: read the cost log (logs/openai_usage.jsonl) - calls, tokens and estimated USD per purpose.

    ./scripts/mobile_openarm exec python lessons/08_lmm/04_cost_log.py            # today
    ./scripts/mobile_openarm exec python lessons/08_lmm/04_cost_log.py --all

The prices in src/warehouse_lecture/config/llm.yaml make this an estimate; the OpenAI usage page is the bill.
"""
import argparse
import datetime as dt
import json
from collections import defaultdict

from warehouse_lecture.llm.client import _find_workspace, load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="whole log instead of today")
    a = ap.parse_args()
    log = _find_workspace() / load_config().get("usage_log", "logs/openai_usage.jsonl")
    rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    if not a.all:
        today = dt.date.today().isoformat()
        rows = [r for r in rows if r["time"].startswith(today)]
    groups = defaultdict(lambda: [0, 0, 0, 0.0])
    for r in rows:
        g = groups[(r["purpose"], r["model"])]
        g[0] += 1
        g[1] += r["input_tokens"]
        g[2] += r["output_tokens"]
        g[3] += r["cost_usd"]
    print(f"{log}  ({'all' if a.all else 'today'}: {len(rows)} calls)")
    print(f"   {'purpose':16s} {'model':14s} {'calls':>5s} {'in tok':>8s} {'out tok':>8s} {'USD':>9s} {'USD/call':>9s}")
    for (purpose, model), (n, i, o, c) in sorted(groups.items(), key=lambda kv: -kv[1][3]):
        print(f"   {purpose:16s} {model:14s} {n:5d} {i:8d} {o:8d} {c:9.5f} {c / n:9.6f}")
    total = sum(g[3] for g in groups.values())
    print(f"   {'total':31s} {len(rows):5d} {sum(g[1] for g in groups.values()):8d} {sum(g[2] for g in groups.values()):8d} {total:9.5f}")


if __name__ == "__main__":
    main()
