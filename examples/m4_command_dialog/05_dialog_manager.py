#!/usr/bin/env python3
"""M4 예제 5: 대화 관리자. 되묻기("어느 상자요?"), 확인("진행할까요?"), 컨텍스트 기억("그거 적재대로").

실행 (실행기 없이 dry-run, 스크립트된 대화):
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/05_dialog_manager.py --script
    대화형(키보드):  ... 05_dialog_manager.py            # 실행기가 떠 있으면 --execute 로 실제 실행
본체: warehouse_lecture/commands/dialog.py (DialogManager)

배우는 점:
- 대화 상태는 세 가지면 충분하다: 되묻는 중(clarifying), 확인 대기(pending), 최근 문맥(context). LLM 에 문맥을 다시 주면
  "그거", "거기" 가 채워진다. 되묻는 중이면 이전 문장과 답을 붙여 다시 파싱한다("상자 옮겨 / 파란 거").
- 확인은 비싼 행동(운반)에만 건다. 이동·팔 자세는 바로 한다. 사용자가 "아니"라고 하면 취소.
- 실행 결과의 spoken 문장(사용자에게 보여 줄 텍스트)을 그대로 출력한다. 실패도 문장으로 설명한다.
- 검증: 모호 명령 5개가 모두 되묻기로 끝나는지 확인한다.
"""

import argparse

from warehouse_lecture.commands.dialog import DialogManager
from warehouse_lecture.commands.parser import CommandParser

SCRIPT = [
    ("상자 옮겨", "clarify"), ("파란 거", "confirm"), ("응", "execute(dry)"),
    ("저기로 가", "clarify"), ("랙 B", "execute(dry)"),
    ("그거 집어", "clarify"),
    ("옮겨 줘", "clarify"), ("노란 상자 적재대로", "confirm"), ("아니", "cancel"),
    ("찾아봐", "clarify"), ("안전모 안 쓴 사람", "execute(dry)"),
    ("빨간 상자 픽업 작업대에서 적재 작업대로 옮겨", "confirm"), ("진행", "execute(dry)"),
    ("팔 준비 자세로", "execute(dry)"),
    ("저 사람 밀어 버려", "answer"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", action="store_true")
    ap.add_argument("--execute", action="store_true", help="ExecuteCommand 서버로 실제 실행")
    a = ap.parse_args()
    executor = None
    if a.execute:
        import rclpy
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("client03", Path(__file__).with_name("03_command_executor.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        rclpy.init(); node = mod.CommandClient()
        executor = lambda cmd, text: node.run(cmd, utterance=text)
    dm = DialogManager(CommandParser(), executor=executor, speak=lambda t: print(f"  [robot] {t}"))
    if a.script:
        ok = 0
        for text, expected in SCRIPT:
            print(f"[user] {text}")
            action, reply, cmd = dm.handle(text)
            good = action == expected
            ok += good
            print(f"        -> {action}{'' if good else f'  (기대 {expected})'}  {cmd.intent.value} {cmd.target} {cmd.destination.value}")
        clarified = sum(1 for (act, _) in dm.log if act == "clarify")
        print(f"\n동작 일치 {ok}/{len(SCRIPT)}, 되묻기 {clarified}회, 비용 ${dm.parser.llm.session_cost:.4f}")
        return
    print("대화를 시작합니다 (빈 줄로 종료).")
    while True:
        try:
            text = input("[user] ")
        except (EOFError, KeyboardInterrupt):
            break
        if not text.strip():
            break
        dm.handle(text)


if __name__ == "__main__":
    main()
