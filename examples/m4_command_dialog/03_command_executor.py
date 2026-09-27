#!/usr/bin/env python3
"""M4 예제 3: ExecuteCommand 액션 서버(실행기)와 그 클라이언트. 실행기 본체는 warehouse_lecture/commands/executor.py.

실행:
    # 터미널 1: 시뮬레이터 (find/report 는 카메라 검출기가 필요)
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start viewer:=false camera_depth:=true locate:=vision
    # 터미널 2: 실행기
    ./scripts/mobile_openarm exec ros2 run warehouse_lecture command_executor
    # 터미널 3: 이 스크립트로 명령을 보낸다
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/03_command_executor.py go_to rack_c
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/03_command_executor.py find person helmet=false
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/03_command_executor.py move_object parcel_red
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/03_command_executor.py --nl "랙 C 앞으로 가"   # LLM 파서 경유
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/03_command_executor.py demo             # 여러 명령 연속

배우는 점 (실행기의 상태 기계):
- 의도마다 하위 액션이 다르다: move_object→PickPlace, go_to→Nav2, arm_pose→MoveGroup, gripper→GripperCommand, find→순찰+검출 구독,
  report/answer→상태 JSON+LLM. 실행기는 이들을 순서대로 부르고 피드백(phase/detail)을 위로 올린다.
- 인터록: 베이스는 양팔이 주행 자세(transport 등)일 때만 /cmd_vel 을 받는다. 그래서 go_to/move_object 는 먼저 팔을 transport 로 보낸다.
- 한 번에 한 명령. 실행 중 새 명령은 거부(REJECT)하고 stop 만 받는다. stop 은 진행 중인 하위 goal 을 취소하고 /cmd_vel 0 을 보낸다.
- 실패 복구: 하위 액션의 상태·에러 코드를 CommandError 로 바꿔 result.message/spoken 에 담는다. 상위(대화 관리자)가 사용자에게 말한다.
"""

import argparse
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from warehouse_interfaces.action import ExecuteCommand
from warehouse_lecture.commands.schema import RobotCommand

DEMO = [("arm_pose", "ready"), ("gripper", "open"), ("gripper", "close"), ("go_to", "rack_c"), ("report", ""), ("find", "person helmet=false"), ("go_to", "center_aisle")]


class CommandClient(Node):
    def __init__(self):
        super().__init__("m4_command_client", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.client = ActionClient(self, ExecuteCommand, "/execute_command")

    def run(self, cmd, utterance="", timeout=900.0):
        if not self.client.wait_for_server(timeout_sec=15.0):
            raise SystemExit("/execute_command 서버가 없다: ros2 run warehouse_lecture command_executor")
        goal = ExecuteCommand.Goal(command=cmd.to_msg(utterance=utterance))
        print(f">> {cmd.describe()}")
        t0 = time.monotonic()
        last = [""]

        def on_fb(m):
            t = f"   [{m.feedback.phase}] {m.feedback.detail}"
            if t != last[0]:
                last[0] = t; print(t, flush=True)

        future = self.client.send_goal_async(goal, feedback_callback=on_fb)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        gh = future.result()
        if gh is None or not gh.accepted:
            print("   거부됨 (다른 명령 실행 중?)"); return None
        rf = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rf, timeout_sec=timeout)
        if not rf.done():
            gh.cancel_goal_async(); print("   시간 초과"); return None
        r = rf.result().result
        status = {v: k[7:] for k, v in vars(GoalStatus).items() if k.startswith("STATUS_")}[rf.result().status]
        print(f"<< {status} success={r.success} ({time.monotonic() - t0:.0f}s) 말하기: {r.spoken}")
        return r


def build(intent, arg):
    parts = arg.split()
    cmd = {"intent": intent, "attributes": {}}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1); cmd["attributes"][k] = v
        elif intent == "go_to":
            cmd["destination"] = p
        elif intent == "move_object" and p.startswith("parcel_"):
            cmd["target"] = p
        elif intent == "move_object" and "->" in p:
            cmd["source"], cmd["destination"] = p.split("->")
        else:
            cmd["target"] = p
    return RobotCommand(**cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("intent", nargs="?", default="demo")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--nl", help="자연어 문장을 LLM 파서로 변환해 실행")
    a = ap.parse_args()
    rclpy.init()
    node = CommandClient()
    try:
        if a.nl:
            from warehouse_lecture.commands.parser import CommandParser
            cmd = CommandParser().parse(a.nl)
            print(f"파서: {cmd.model_dump_json(exclude_none=True)}")
            problems = cmd.validate_world()
            if problems:
                print("실행 불가:", problems); sys.exit(1)
            node.run(cmd, utterance=a.nl)
        elif a.intent == "demo":
            for intent, arg in DEMO:
                cmd = build(intent, arg); cmd.validate_world(); node.run(cmd)
        else:
            cmd = build(a.intent, " ".join(a.args))
            problems = cmd.validate_world()
            if problems:
                print("실행 불가:", problems); sys.exit(1)
            node.run(cmd)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
