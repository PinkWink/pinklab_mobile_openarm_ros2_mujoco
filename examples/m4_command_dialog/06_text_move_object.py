#!/usr/bin/env python3
"""M4 예제 6: 텍스트 "픽업대에서 적재대로 빨간 상자 옮겨" -> 명령 -> 확인 -> 실행 -> 결과 문장. 단계별 지연 측정.

실행 (시뮬레이터 + 실행기가 떠 있어야 한다. 03번 참고):
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/06_text_move_object.py                 # 키보드 대화
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/06_text_move_object.py --lines "파란 상자 적재대로" "응"   # 자동 시험
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/06_text_move_object.py --ros           # 04번 콘솔 토픽으로 입출력
출력: artifacts/m4/dialog_timings.json

배우는 점:
- 한 턴 = 읽기 → 이해(LLM 파서, 약 1 초) → 행동(실행기, 수십 초~수 분) → 답 문장. 지연은 단계별로 재야 어디를 줄일지 안다.
- 행동이 오래 걸리면 "시작합니다" 를 먼저 보내고, 끝나면 결과를 보낸다. 사용자는 기다리는 이유를 알아야 한다.
- 운반처럼 되돌리기 어려운 행동은 확인(진행할까요?)을 거친다. --ros 모드에서는 콘솔(04)과 토픽으로 대화한다.
"""

import argparse
import json
import time
from pathlib import Path

from warehouse_lecture.commands.dialog import DialogManager
from warehouse_lecture.commands.parser import CommandParser
from warehouse_lecture.llm.client import LLM


class ListInput:
    def __init__(self, lines):
        self.lines = list(lines)

    def read(self):
        if not self.lines:
            return ""
        t = self.lines.pop(0); print(f"[user] {t}"); return t


class KeyboardInput:
    def read(self):
        try:
            return input("[user] ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", nargs="*", help="자동 시험 문장들")
    ap.add_argument("--ros", action="store_true", help="/warehouse/utterance 로 읽고 /warehouse/narration 으로 답한다 (04번 콘솔)")
    ap.add_argument("--no-execute", action="store_true")
    a = ap.parse_args()
    import rclpy, importlib.util
    from warehouse_interfaces.msg import Utterance
    spec = importlib.util.spec_from_file_location("client03", Path(__file__).with_name("03_command_executor.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    rclpy.init(); node = mod.CommandClient()
    reply_pub = node.create_publisher(Utterance, "/warehouse/narration", 10)

    def speak(text):
        print(f"[robot] {text}", flush=True)
        msg = Utterance(); msg.header.stamp = node.get_clock().now().to_msg()
        msg.speaker, msg.text, msg.language = "robot", text, "ko"
        reply_pub.publish(msg)

    executor = None
    if not a.no_execute:
        def executor(cmd, text):
            speak("시작합니다.")
            return node.run(cmd, utterance=text)

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
    dm = DialogManager(CommandParser(llm), executor=executor, speak=speak)
    timings = []
    while True:
        t0 = time.perf_counter()
        text = reader.read()
        if not text:
            break
        t1 = time.perf_counter()
        action, reply, cmd = dm.handle(text)
        t_handle = time.perf_counter() - t1
        timings.append({"text": text, "action": action, "handle_s": round(t_handle, 2)})
        print(f"    ({action}; 이해+행동+답 {t_handle:.1f}s)")
    Path("artifacts/m4").mkdir(parents=True, exist_ok=True)
    Path("artifacts/m4/dialog_timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=1))
    print(f"턴 {len(timings)}개, 실행 {sum(t['action'] == 'result' for t in timings)}회, 비용 ${llm.session_cost:.4f}")
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
