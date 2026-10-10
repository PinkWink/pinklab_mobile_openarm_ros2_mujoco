#!/usr/bin/env python3
"""Lesson 08-3: conversion accuracy on 60 Korean commands (intent + the slots the sentence states).

    ./scripts/mobile_openarm exec python lessons/08_lmm/03_accuracy.py
    ./scripts/mobile_openarm exec python lessons/08_lmm/03_accuracy.py --test my_tests.yaml --model gpt-4.1

Scoring: the intent must match, and every target/source/destination/attribute written in the test must match.
Defaults filled by validate_world() count as correct; ambiguous/dangerous sentences must be intent=answer with a reply.
Writes artifacts/lessons/08_accuracy.json (every sentence, the command, ok, latency) for the figures.
"""
import argparse
import json
import time
from pathlib import Path

import yaml
from warehouse_lecture.commands.parser import CommandParser
from warehouse_lecture.llm.client import LLM

TEST = Path("examples/m4_command_dialog/commands_test.yaml")


def score(q, cmd):
    if cmd.intent.value != q["intent"]:
        return False
    for key in ("target", "source", "destination"):
        if q.get(key):
            got = getattr(cmd, key)
            if (got.value if hasattr(got, "value") else got) != q[key]:
                return False
    for k, v in (q.get("attributes") or {}).items():
        if str(cmd.attribute_dict().get(k, "")).lower() != str(v).lower():
            return False
    if (q.get("ambiguous") or q.get("refuse")) and not cmd.reply.strip():
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default=str(TEST))
    ap.add_argument("--model", help="override models.chat in llm.yaml for this run")
    a = ap.parse_args()
    tests = yaml.safe_load(Path(a.test).read_text())
    llm = LLM()
    if a.model:
        llm.models["chat"] = a.model
    parser = CommandParser(llm)
    rows, by_intent = [], {}
    for i, q in enumerate(tests, 1):
        t0 = time.monotonic()
        cmd = parser.parse(q["text"])
        seconds = time.monotonic() - t0
        cmd.validate_world()
        ok = score(q, cmd)
        g = by_intent.setdefault(q["intent"], [0, 0])
        g[0] += ok
        g[1] += 1
        rows.append({"text": q["text"], "expected": q, "cmd": json.loads(cmd.model_dump_json()), "ok": ok, "seconds": seconds})
        mark = "ok" if ok else "XX"
        print(f"{i:2d} {mark} {seconds:4.1f}s {q['text']}  ->  {cmd.intent.value} {cmd.target} {cmd.source.value} {cmd.destination.value} "
              f"{cmd.attribute_dict() or ''}".rstrip(), flush=True)
    n_ok = sum(r["ok"] for r in rows)
    print(f"\naccuracy {n_ok}/{len(rows)} = {n_ok / len(rows) * 100:.1f} %   model {llm.models['chat']}   cost ${llm.session_cost:.4f}   "
          f"latency mean {sum(r['seconds'] for r in rows) / len(rows):.2f} s")
    for intent, (g, n) in by_intent.items():
        print(f"   {intent:12s} {g}/{n}")
    out = Path("artifacts/lessons")
    out.mkdir(parents=True, exist_ok=True)
    (out / "08_accuracy.json").write_text(json.dumps({"model": llm.models["chat"], "cost": llm.session_cost, "rows": rows},
                                                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
