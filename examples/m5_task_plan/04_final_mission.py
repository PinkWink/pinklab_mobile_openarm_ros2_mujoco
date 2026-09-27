#!/usr/bin/env python3
"""M5 예제 4 (Final Mission): 텍스트 지령 -> LMM 계획(단계 목록) -> 확인 -> Task Manager 실행 -> 결과 문장.

실행 (시뮬레이터 + task_manager 가 떠 있어야 한다. 03번 참고):
    ./scripts/mobile_openarm exec python examples/m5_task_plan/04_final_mission.py                                  # 키보드 대화
    ./scripts/mobile_openarm exec python examples/m5_task_plan/04_final_mission.py --lines "픽업 작업대로 가서 빨간 상자 집고 적재 작업대로 옮겨" "응"
    ./scripts/mobile_openarm exec python examples/m5_task_plan/04_final_mission.py --ros                            # 04_text_console 토픽으로 입출력
출력: artifacts/m5/mission_timings.json

배우는 점:
- 전체 파이프라인: 자연어 -> LMM(계획) -> 확인 -> ROS 2 Task Manager -> Nav2 / PickPlace(MoveIt) -> MuJoCo.
- 확인 문장에 단계 목록을 보여 준다. 사용자는 로봇이 무엇을 할지 실행 전에 안다.
- 실패하면 몇 단계까지 했는지, 무엇을 들고 있는지를 문장으로 듣는다. 그 다음 지령은 그 상태에서 이어진다.
"""

import argparse
import importlib.util
import json
import time
from pathlib import Path

from warehouse_lecture.commands.dialog import PlanDialogManager
from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.llm.client import LLM


class ListInput:
    def __init__(self, lines):
        self.lines = list(lines)

    def read(self):
        if not self.lines:
            return ""
        t = self.lines.pop(0)
        print(f"[user] {t}")
        return t


class KeyboardInput:
    def read(self):
        try:
            return input("[user] ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", nargs="*", help="자동 시험 문장들")
    ap.add_argument("--ros", action="store_true", help="/warehouse/utterance 로 읽고 /warehouse/narration 으로 답한다")
    ap.add_argument("--no-execute", action="store_true", help="계획만 세우고 실행하지 않는다")
    a = ap.parse_args()
    import rclpy
    from warehouse_interfaces.msg import Utterance
    spec = importlib.util.spec_from_file_location("client03", Path(__file__).with_name("03_task_manager.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rclpy.init()
    node = mod.PlanClient()
    reply_pub = node.create_publisher(Utterance, "/warehouse/narration", 10)

    def speak(text):
        print(f"[robot] {text}", flush=True)
        msg = Utterance()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.speaker, msg.text, msg.language = "robot", text, "ko"
        reply_pub.publish(msg)

    executor = None
    if not a.no_execute:
        def executor(plan, text):
            speak("시작합니다.")
            return node.run(plan, utterance=text)

    if a.ros:
        inbox = []
        node.create_subscription(Utterance, "/warehouse/utterance", lambda m: inbox.append(m.text) if m.speaker == "user" else None, 10)

        class RosInput:
            def read(self):
                print("[user 입력 대기: 04_text_console.py]", flush=True)
                while rclpy.ok() and not inbox:
                    rclpy.spin_once(node, timeout_sec=0.1)
                return inbox.pop(0) if inbox else ""
        reader = RosInput()
    else:
        reader = ListInput(a.lines) if a.lines else KeyboardInput()

    llm = LLM()
    dm = PlanDialogManager(PlanParser(llm), executor=executor, speak=speak)
    timings = []
    while True:
        text = reader.read()
        if not text:
            break
        t1 = time.perf_counter()
        action, reply, plan = dm.handle(text)
        dt = time.perf_counter() - t1
        timings.append({"text": text, "action": action, "handle_s": round(dt, 2), "steps": len(plan.steps)})
        print(f"    ({action}; {dt:.1f}s)")
    Path("artifacts/m5").mkdir(parents=True, exist_ok=True)
    Path("artifacts/m5/mission_timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=1))
    print(f"턴 {len(timings)}개, 실행 {sum(t['action'] == 'result' for t in timings)}회, 비용 ${llm.session_cost:.4f}")
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
