#!/usr/bin/env python3
"""Lesson 10-1: the same sentence, planned with and without the parcel table (no simulator).

    ./scripts/mobile_openarm exec python lessons/10_final_project/01_world_plan.py
    ./scripts/mobile_openarm exec python lessons/10_final_project/01_world_plan.py --only world

Each case gives a belief (where each parcel is) and a sentence. The planner runs twice:
  - "none":  PlanParser.parse(text)               -> always assumes the parcels are on pick_table
  - "world": PlanParser.parse(text, world=world)  -> the table is in the system prompt
A case passes when the pick/place locations match and WorldState.check(plan) finds nothing. For a parcel
that is already at the destination nothing may run: empty steps, or check() says "이미 ... 에 있다". Writes artifacts/lessons/10_world_plan.json.
"""
import argparse
import json
import time
from pathlib import Path

from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.commands.world import WorldState

A, B = "pick_table", "place_table"
START = {"parcel_red": A, "parcel_blue": A, "parcel_yellow": A}
RED_MOVED = {"parcel_red": B, "parcel_blue": A, "parcel_yellow": A}
TWO_MOVED = {"parcel_red": B, "parcel_blue": B, "parcel_yellow": A}
CASES = [  # (belief, sentence, expected [(action, target, location)] for pick/place only; [] = no steps)
    (START, "빨간 상자 적재대로 옮겨", [("pick", "parcel_red", A), ("place", "", B)]),
    (RED_MOVED, "파란 상자도 적재대로 옮겨", [("pick", "parcel_blue", A), ("place", "", B)]),
    (RED_MOVED, "빨간 상자 다시 픽업대로 가져와", [("pick", "parcel_red", B), ("place", "", A)]),
    (RED_MOVED, "빨간 상자 옮겨", [("pick", "parcel_red", B), ("place", "", A)]),
    (RED_MOVED, "빨간 상자 적재대로 옮겨", []),
    (TWO_MOVED, "파란 상자 원래 자리로 돌려놔", [("pick", "parcel_blue", B), ("place", "", A)]),
    (TWO_MOVED, "노란 상자도 같은 데로 옮겨", [("pick", "parcel_yellow", A), ("place", "", B)]),
    (TWO_MOVED, "빨간 상자랑 파란 상자 픽업대로 돌려놔",
     [("pick", "parcel_red", B), ("place", "", A), ("pick", "parcel_blue", B), ("place", "", A)]),
]


def picks_places(plan):
    return [(s.action.value, s.target if s.action.value == "pick" else "", s.location.value)
            for s in plan.steps if s.action.value in ("pick", "place")]


def fmt(pp):
    return " > ".join(f"{a}:{t}@{l}" if t else f"{a}@{l}" for a, t, l in pp) or "(steps 없음)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["none", "world"], help="한쪽만 실행")
    a = ap.parse_args()
    parser = PlanParser()
    modes = [a.only] if a.only else ["none", "world"]
    rows = []
    for mode in modes:
        print(f"\n== {mode}: {'상자 위치표 없이' if mode == 'none' else '상자 위치표를 프롬프트에'}")
        for i, (belief, text, want) in enumerate(CASES, 1):
            world = WorldState(belief)
            t0 = time.monotonic()
            plan = parser.parse(text, world=world if mode == "world" else None)
            dt = time.monotonic() - t0
            problems = plan.validate_world() + (world.check(plan) if plan.steps else [])
            got = picks_places(plan)
            if want:
                ok = got == want and not problems
            else:                       # "already there": nothing may run (empty steps, or the code check refuses)
                ok = not got or any("이미" in p for p in problems)
            rows.append({"mode": mode, "world": world.describe(), "text": text, "ok": ok, "want": fmt(want),
                         "got": fmt(got), "problems": problems, "reply": plan.reply, "seconds": round(dt, 2)})
            print(f"{i} {'ok' if ok else 'XX'} {dt:4.1f}s  [{world.describe()}]  {text}", flush=True)
            if not ok:
                print(f"      want: {fmt(want)}\n      got : {fmt(got)}  {problems or ''}")
            elif not want:
                print(f"      {'; '.join(problems) or plan.reply}")
    for mode in modes:
        n = sum(r["ok"] for r in rows if r["mode"] == mode)
        print(f"{mode:5s}: {n}/{len(CASES)}")
    print(f"cost ${parser.llm.session_cost:.4f}")
    out = Path("artifacts/lessons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "10_world_plan.json").write_text(json.dumps({"cost": parser.llm.session_cost, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
