#!/usr/bin/env python3
"""M5 예제 1: 작업 계획 문법(RobotPlan)과 세계 검증. LLM·시뮬레이터 없이 돈다.

실행:
    ./scripts/mobile_openarm exec python examples/m5_task_plan/01_plan_schema.py

배우는 점:
- 계획은 단계(PlanStep)의 목록이다. LMM 은 이 목록만 만든다. 관절·속도는 Nav2/MoveIt/스킬 서버의 일이다.
- validate_world() 는 형식이 아니라 의미를 본다: 든 것이 없는데 place, 상자를 랙에서 pick, 계획이 상자를 든 채 끝남.
  빠진 navigate 는 자동으로 끼워 넣고(자동 추가), pick/place 의 작업대 기본값을 채운다.
- RobotPlan 은 ROS 액션 goal(warehouse_interfaces/ExecutePlan)과 1:1 로 오간다(to_msg/from_msg). Task Manager 는 goal 만 본다.
"""

from warehouse_lecture.commands.plan import PlanStep, RobotPlan, StepAction

CASES = {
    "정상: 다섯 단계": RobotPlan(summary="빨간 상자 운반", reply="옮기겠습니다.", steps=[
        PlanStep(action="navigate", location="pick_table"), PlanStep(action="detect", target="parcel_red"),
        PlanStep(action="pick", target="parcel_red", location="pick_table"),
        PlanStep(action="navigate", location="place_table"), PlanStep(action="place", location="place_table")]),
    "navigate 가 빠짐 (자동 추가)": RobotPlan(steps=[
        PlanStep(action="pick", target="parcel_blue"), PlanStep(action="place")]),
    "든 것이 없는데 place": RobotPlan(steps=[PlanStep(action="navigate", location="place_table"), PlanStep(action="place", location="place_table")]),
    "상자를 든 채로 끝남": RobotPlan(steps=[PlanStep(action="pick", target="parcel_red", location="pick_table")]),
    "랙에서 집기": RobotPlan(steps=[PlanStep(action="pick", target="parcel_red", location="rack_c"), PlanStep(action="place", location="place_table")]),
    "색이 없는 상자": RobotPlan(steps=[PlanStep(action="pick", target="parcel"), PlanStep(action="place")]),
    "이동 + 보고": RobotPlan(steps=[PlanStep(action="navigate", location="rack_c"), PlanStep(action="report")]),
    "되묻기 (단계 없음)": RobotPlan(reply="어떤 색 상자를 옮길까요?"),
}


def main():
    for title, plan in CASES.items():
        before = [s.action.value for s in plan.steps]
        problems = plan.validate_world()
        print(f"\n## {title}")
        print(f"   입력 : {before}")
        print(f"   결과 : {[s.action.value for s in plan.steps]}")
        if plan.steps:
            print("   설명 :\n      " + plan.describe().replace("\n", "\n      "))
        print("   판정 : " + ("실행 가능" if not problems else "실행 불가 -> " + "; ".join(problems)))
    plan = CASES["정상: 다섯 단계"]
    goal = plan.to_msg(utterance="빨간 상자 옮겨")
    back = RobotPlan.from_msg(goal)
    print(f"\nROS goal: steps={len(goal.steps)} first={goal.steps[0].action}/{goal.steps[0].location} note={goal.steps[0].note!r}")
    print("round trip:", "OK" if [s.action for s in back.steps] == [s.action for s in plan.steps] else "MISMATCH")
    print("확인 필요(pick/place 포함):", plan.needs_confirmation(), "| 이동+보고:", CASES["이동 + 보고"].needs_confirmation())
    assert StepAction.pick.value == "pick"


if __name__ == "__main__":
    main()
