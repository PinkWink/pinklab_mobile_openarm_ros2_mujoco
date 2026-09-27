#!/usr/bin/env python3
"""M4 예제 1: 명령 문법(pydantic RobotCommand)과 세계 사전(장소·물체·자세) 검증.

실행:
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/01_command_schema.py

배우는 점:
- 스키마(형식)와 검증(의미)은 다른 층이다. Structured Outputs 는 형식만 보장한다. "빨간 상자를 랙 A 로" 는 형식상 맞지만
  상자는 작업대 사이에서만 옮길 수 있으므로 validate_world() 가 잡는다.
- 기본값 채우기(source=pick_table)도 검증 층의 일이다. 모델이 매번 맞추게 하지 말고 규칙으로 채운다.
- RobotCommand 는 ROS 메시지(warehouse_interfaces/RobotCommand)와 1:1 로 오간다(to_msg/from_msg). 실행기는 메시지만 본다.
"""

from pydantic import ValidationError
from warehouse_lecture.commands.schema import ARM_POSES, PARCELS, Intent, Place, RobotCommand

CASES = [
    {"intent": "move_object", "target": "parcel_red"},                                             # 기본값으로 채워져 실행 가능
    {"intent": "move_object", "target": "parcel_red", "source": "pick_table", "destination": "pick_table"},  # 같은 작업대
    {"intent": "move_object", "target": "parcel_red", "destination": "rack_a"},                    # 랙으로는 못 옮긴다
    {"intent": "move_object", "target": "box"},                                                    # 모르는 물체
    {"intent": "go_to", "destination": "rack_c"},
    {"intent": "go_to"},                                                                           # 목적지 없음
    {"intent": "find", "target": "person", "attributes": {"helmet": "false"}},
    {"intent": "arm_pose", "target": "banzai"},                                                    # 모르는 자세
    {"intent": "gripper", "target": "open"},
    {"intent": "stop"},
    {"intent": "fly"},                                                                             # 스키마 위반 (enum)
    {"intent": "go_to", "destination": "kitchen"},                                                 # 스키마 위반 (enum)
]


def main():
    print(f"의도 {[i.value for i in Intent]}\n장소 {[p.value for p in Place if p.value]}\n상자 {PARCELS}, 팔 자세 {ARM_POSES}\n")
    for case in CASES:
        try:
            cmd = RobotCommand(**case)
        except ValidationError as error:
            print(f"스키마 위반  {case} -> {error.errors()[0]['msg']}")
            continue
        problems = cmd.validate_world()
        status = "실행 가능" if not problems else "의미 오류"
        print(f"{status:5s}  {case} -> {cmd.describe()}" + (f"  [{'; '.join(problems)}]" if problems else ""))
    # ROS 메시지 왕복
    cmd = RobotCommand(intent="move_object", target="parcel_blue", reply="파란 상자를 옮기겠습니다.")
    cmd.validate_world()
    msg = cmd.to_msg(utterance="파란 상자 옮겨", request_id="r1")
    back = RobotCommand.from_msg(msg)
    print(f"\nROS 왕복: {msg.intent} {msg.target} {msg.source}->{msg.destination} params={[(k.key, k.value) for k in msg.params]} -> {back.describe()} (같음: {back == cmd})")


if __name__ == "__main__":
    main()
