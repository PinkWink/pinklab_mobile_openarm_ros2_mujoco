#!/usr/bin/env python3
"""Lesson 08-6: plan accuracy on 20 Korean instructions (the whole step sequence must match).

    ./scripts/mobile_openarm exec python lessons/08_lmm/06_plan_accuracy.py

Scoring: the action sequence must be identical, with the target of pick/detect/arm_pose/gripper and the location of
navigate/pick/place. Clarifications and refusals must leave steps empty. Writes artifacts/lessons/08_plan_accuracy.json.
"""
import argparse
import json
import time
from pathlib import Path

import yaml
from warehouse_lecture.commands.plan_parser import PlanParser

TEST = Path("examples/m5_task_plan/plans_test.yaml")


def expected(spec):
    out = []
    for item in spec:                                  # "pick:parcel_red@pick_table", "navigate:rack_c", "report"
        action, _, rest = str(item).partition(":")
        target, _, location = rest.partition("@")
        if action == "navigate" and target and not location:
            target, location = "", target
        out.append((action, target, location))
    return out


def actual(plan):
    return [(s.action.value,
             s.target if s.action.value in ("pick", "detect", "arm_pose", "gripper") else "",
             s.location.value if s.action.value in ("navigate", "pick", "place") else "") for s in plan.steps]


def fmt(steps):
    return " > ".join(f"{a}:{t}@{l}".replace(":@", "@").rstrip("@:") for a, t, l in steps) or "(none)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default=str(TEST))
    a = ap.parse_args()
    cases = yaml.safe_load(Path(a.test).read_text())
    parser = PlanParser()
    rows = []
    for i, case in enumerate(cases, 1):
        t0 = time.monotonic()
        plan = parser.parse(case["text"])
        seconds = time.monotonic() - t0
        problems = plan.validate_world()
        want, got = expected(case["steps"]), actual(plan)
        ok = want == got and not (got and problems)
        rows.append({"text": case["text"], "ok": ok, "want": fmt(want), "got": fmt(got), "steps": len(got), "seconds": seconds, "reply": plan.reply})
        print(f"{i:2d} {'ok' if ok else 'XX'} {seconds:4.1f}s {len(got):2d} steps  {case['text']}", flush=True)
        if not ok:
            print(f"      want: {fmt(want)}\n      got : {fmt(got)}  {problems or ''}")
    n = sum(r["ok"] for r in rows)
    print(f"\naccuracy {n}/{len(rows)} = {n / len(rows) * 100:.1f} %   cost ${parser.llm.session_cost:.4f}   "
          f"latency mean {sum(r['seconds'] for r in rows) / len(rows):.2f} s")
    out = Path("artifacts/lessons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "08_plan_accuracy.json").write_text(json.dumps({"cost": parser.llm.session_cost, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
