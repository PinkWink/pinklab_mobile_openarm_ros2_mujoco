#!/usr/bin/env python3
"""M5 예제 3: Task Manager(ExecutePlan 액션 서버) 클라이언트. 단계 목록을 보내고 단계별 피드백을 본다.

실행:
    # 터미널 1: 시뮬레이터 (카메라 검출기 + 카메라 기반 위치)
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start viewer:=false camera_depth:=true locate:=vision
    # 터미널 2: Task Manager (command_executor 대신. 둘을 같이 띄우면 /execute_command 가 겹친다)
    ./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
    # 터미널 3: 이 스크립트
    ./scripts/mobile_openarm exec python examples/m5_task_plan/03_task_manager.py navigate:rack_c report
    ./scripts/mobile_openarm exec python examples/m5_task_plan/03_task_manager.py navigate:pick_table detect:parcel_red pick:parcel_red@pick_table navigate:place_table place:@place_table
    ./scripts/mobile_openarm exec python examples/m5_task_plan/03_task_manager.py --nl "픽업 작업대로 가서 빨간 상자 집고 적재 작업대로 옮겨"   # LLM 계획기 경유
    ./scripts/mobile_openarm exec python examples/m5_task_plan/03_task_manager.py mission                      # 위 다섯 단계

배우는 점:
- Task Manager 는 단계를 순서대로 실행하고 (단계 번호, action, phase, detail) 피드백을 올린다. 한 단계가 실패하면 거기서 멈추고
  몇 단계까지 했는지, 무엇을 들고 있는지 문장으로 알린다.
- pick 은 PickPlace 스킬의 phase=pick(도킹·파지·운반 자세), place 는 phase=place(도킹·놓기)다. 스킬 서버가 든 물체를 기억한다.
- 물체를 든 채 이동할 때는 팔을 transport 로 바꾸지 않는다(운반 자세도 주행 허용 자세). 실행기의 인터록과 같은 규칙이다.
"""

import argparse
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from warehouse_interfaces.action import ExecutePlan
from warehouse_lecture.commands.plan import PlanStep, RobotPlan

MISSION = ["navigate:pick_table", "detect:parcel_red", "pick:parcel_red@pick_table", "navigate:place_table", "place:@place_table"]


def build(items):
    steps = []
    for item in items:
        action, _, rest = item.partition(":")
        target, _, location = rest.partition("@")
        if action == "navigate" and target and not location:
            target, location = "", target
        steps.append(PlanStep(action=action, target=target, location=location))
    return RobotPlan(summary=" > ".join(items), steps=steps)


class PlanClient(Node):
    def __init__(self):
        super().__init__("m5_plan_client", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.client = ActionClient(self, ExecutePlan, "/execute_plan")

    def run(self, plan, utterance="", timeout=1800.0):
        if not self.client.wait_for_server(timeout_sec=15.0):
            raise SystemExit("/execute_plan 서버가 없다: ros2 run warehouse_lecture task_manager")
        goal = plan.to_msg(utterance=utterance)
        print(">> 계획:\n   " + plan.describe().replace("\n", "\n   "))
        t0 = time.monotonic()
        last = [""]

        def on_fb(m):
            f = m.feedback
            t = f"   [{f.step + 1}/{f.total} {f.action}/{f.phase}] {f.detail}"
            if t != last[0]:
                last[0] = t
                print(t, flush=True)

        future = self.client.send_goal_async(goal, feedback_callback=on_fb)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        gh = future.result()
        if gh is None or not gh.accepted:
            print("   거부됨 (다른 명령 실행 중?)")
            return None
        rf = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rf, timeout_sec=timeout)
        if not rf.done():
            gh.cancel_goal_async()
            print("   시간 초과")
            return None
        r = rf.result().result
        status = {v: k[7:] for k, v in vars(GoalStatus).items() if k.startswith("STATUS_")}[rf.result().status]
        print(f"<< {status} success={r.success} steps_done={r.steps_done}/{len(plan.steps)} failed_step={r.failed_step} ({time.monotonic() - t0:.0f}s)")
        print(f"   말하기: {r.spoken}")
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("steps", nargs="*", help="action[:target][@location] ... 또는 mission")
    ap.add_argument("--nl", help="자연어 지령을 LLM 계획기로 변환해 실행")
    a = ap.parse_args()
    rclpy.init()
    node = PlanClient()
    try:
        if a.nl:
            from warehouse_lecture.commands.plan_parser import PlanParser
            plan = PlanParser().parse(a.nl)
            print(f"계획기: {plan.model_dump_json(exclude_none=True)}")
        else:
            items = MISSION if (not a.steps or a.steps == ["mission"]) else a.steps
            plan = build(items)
        problems = plan.validate_world()
        if problems:
            print("실행 불가:", problems)
            sys.exit(1)
        if not plan.steps:
            print("단계 없음:", plan.reply)
            sys.exit(0)
        r = node.run(plan, utterance=a.nl or "")
        sys.exit(0 if r is not None and r.success else 1)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
