#!/usr/bin/env python3
"""Lesson 08-5 (LMM -> ROS 2 Task Pipeline): one instruction -> RobotPlan (ordered steps), without the simulator.

    ./scripts/mobile_openarm exec python lessons/08_lmm/05_plan.py
    ./scripts/mobile_openarm exec python lessons/08_lmm/05_plan.py "파란 상자 옮기고 노란 상자도 적재대로"

RobotCommand (lesson 08-2) is one action per sentence. RobotPlan is a list of steps the Task Manager runs in order:
navigate / detect / pick / place / arm_pose / gripper / report / answer. The LMM still never outputs joints or speeds.
RobotPlan.validate_world() checks the order against the world: it inserts a missing navigate before pick/place, fills
the table, and rejects a place with nothing held, a second pick while holding, or a plan that ends holding a parcel.
"""
import sys
import time

from warehouse_lecture.commands.plan import PlanStep, RobotPlan
from warehouse_lecture.commands.plan_parser import PlanParser

DEFAULT = ["테이블 A 에서 파란 물체 집어서 테이블 B 로 옮겨",   # 별명 (테이블 A = pick_table), '물체' = 상자
           "노란 상자 적재대로",                            # 짧은 지령: 다섯 단계로 펼쳐진다
           "동쪽 벽으로 가서 지게차 있는지 확인해",         # 이동 + 확인 (pick/place 없음 → 확인 없이 실행)
           "옮겨 줘"]                                       # 무엇을? → steps 비움, 되묻기
# (parser.py 의 예시 4 개와 겹치지 않는 문장들)


def show(plan, problems):
    for i, st in enumerate(plan.steps, 1):
        key = " ".join(x for x in (st.action.value, st.target, f"@{st.location.value}" if st.location.value else "") if x)
        print(f"   {i}. {key:34s} {st.note or st.describe()}")
    if problems:
        print(f"   validate_world: {'; '.join(problems)}")
    elif plan.steps:
        print(f"   validate_world: ok   (confirm first: {plan.needs_confirmation()})")
    if plan.reply:
        print(f"   reply: {plan.reply}")


def main():
    print("1) validate_world() without the LLM")
    hand = RobotPlan(steps=[PlanStep(action="pick", target="parcel_red"), PlanStep(action="place", location="place_table")])
    print(">> [pick parcel_red, place @place_table]   (no navigate written)")
    show(hand, hand.validate_world())
    bad = RobotPlan(steps=[PlanStep(action="navigate", location="place_table"), PlanStep(action="place", location="place_table")])
    print(">> [navigate place_table, place @place_table]   (nothing picked)")
    show(bad, bad.validate_world())
    parser = PlanParser()
    print("\n2) LLM -> RobotPlan -> validate_world()")
    for text in sys.argv[1:] or DEFAULT:
        t0 = time.monotonic()
        plan = parser.parse(text)
        print(f"\n>> {text}   ({time.monotonic() - t0:.2f} s, {len(plan.steps)} steps)")
        show(plan, plan.validate_world())
    print(f"\ncost this run ${parser.llm.session_cost:.5f}")


if __name__ == "__main__":
    main()
