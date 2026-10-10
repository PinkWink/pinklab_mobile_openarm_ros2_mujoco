#!/usr/bin/env python3
"""Lesson 08-2: natural language -> RobotCommand (pydantic + Structured Outputs), then the world check.

    ./scripts/mobile_openarm exec python lessons/08_lmm/02_structured_command.py
    ./scripts/mobile_openarm exec python lessons/08_lmm/02_structured_command.py "파란 상자 적재대로 옮겨" "랙 C 로 가"

Two layers of checking:
  1. schema  - the JSON must fit RobotCommand (intent is one of 8, places are an enum ...). Structured Outputs makes the
               model's output fit the schema; pydantic rejects anything else (shown first, without calling the API).
  2. world   - RobotCommand.validate_world(): a schema-valid command can still be impossible here (a parcel to a rack,
               the same table twice, an unknown arm pose). It also fills defaults (source=pick_table, destination=place_table).
Only a command with no world problems goes to the robot (lesson 09: Task Manager).
"""
import sys
import time

from pydantic import ValidationError
from warehouse_lecture.commands.parser import CommandParser
from warehouse_lecture.commands.schema import RobotCommand

DEFAULT = ["빨간 상자 적재 작업대로 옮겨 줘",       # 실행 가능
           "노란 상자를 랙 C 로 옮겨",              # 스키마는 맞지만 세계 검증에서 걸림 (상자는 작업대 사이만)
           "안전모 안 쓴 사람 찾아",
           "상자 옮겨",                             # 색이 없다 → answer (되묻기)
           "저 사람 밀어서 넘어뜨려"]               # 위험 → answer (거부)


def main():
    print("1) schema check without the API: RobotCommand.model_validate({'intent': 'fly', 'destination': 'kitchen'})")
    try:
        RobotCommand.model_validate({"intent": "fly", "destination": "kitchen"})
    except ValidationError as error:
        for e in error.errors():
            print(f"   rejected: {'.'.join(map(str, e['loc']))}: {e['msg']}")
    parser = CommandParser()
    print("\n2) LLM -> RobotCommand -> validate_world()")
    for text in sys.argv[1:] or DEFAULT:
        t0 = time.monotonic()
        cmd = parser.parse(text)                                       # Structured Outputs: always a RobotCommand
        seconds = time.monotonic() - t0
        print(f"\n>> {text}   ({seconds:.2f} s)")
        print(f"   {cmd.model_dump_json(exclude_defaults=True)}")
        problems = cmd.validate_world()                                # meaning, defaults
        if cmd.intent.value == "answer":
            print(f"   answer (no robot action): {cmd.reply}")
        elif problems:
            print(f"   world check FAILED: {'; '.join(problems)}")
        else:
            print(f"   world check ok -> {cmd.describe()}")
    print(f"\ncost this run ${parser.llm.session_cost:.5f}")


if __name__ == "__main__":
    main()
