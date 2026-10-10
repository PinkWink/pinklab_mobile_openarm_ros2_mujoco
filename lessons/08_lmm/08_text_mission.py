#!/usr/bin/env python3
"""Lesson 08-8: text instruction -> plan -> clarify / confirm -> Task Manager -> result sentence.

    (simulator + task_manager running, see 07_run_plan.py)
    ./scripts/mobile_openarm exec python lessons/08_lmm/08_text_mission.py                     # type, empty line ends
    ./scripts/mobile_openarm exec python lessons/08_lmm/08_text_mission.py --lines "상자 옮겨" "빨간 거" "응"

PlanDialogManager (warehouse_lecture/commands/dialog.py):
  - steps empty (missing colour, refusal, question) -> say the reply; a question keeps the sentence for the next answer
  - steps with pick/place -> show the numbered steps and ask "진행할까요?"; yes runs it, no cancels, anything else is new
  - other plans (go somewhere and report) run at once
  - the Task Manager's result sentence (or its failure report) is said back
"""
import argparse
import importlib.util
import time
from pathlib import Path

import rclpy
from warehouse_lecture.commands.dialog import PlanDialogManager
from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.llm.client import LLM

spec = importlib.util.spec_from_file_location("run_plan", Path(__file__).with_name("07_run_plan.py"))
run_plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_plan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", nargs="*", help="scripted user turns instead of the keyboard")
    a = ap.parse_args()
    rclpy.init()
    node = run_plan.PlanClient()
    llm = LLM()
    t0 = time.monotonic()

    def speak(text):
        print(f"[{time.monotonic() - t0:6.1f}s robot] {text}", flush=True)

    dm = PlanDialogManager(PlanParser(llm), executor=lambda plan, text: node.run(plan, utterance=text), speak=speak)
    lines = list(a.lines or [])
    while True:
        if a.lines is not None:
            if not lines:
                break
            text = lines.pop(0)
            print(f"[{time.monotonic() - t0:6.1f}s user ] {text}", flush=True)
        else:
            try:
                text = input("[user] ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                break
        dm.handle(text)
    print(f"LLM cost ${llm.session_cost:.4f}")
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
