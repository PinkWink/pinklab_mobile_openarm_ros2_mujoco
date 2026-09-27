"""Korean utterance -> RobotCommand with OpenAI Structured Outputs (promoted from M3 example 06)."""

from ..llm.client import LLM
from .schema import RobotCommand

SYSTEM = """너는 창고 이동 로봇의 명령 해석기다. 사용자의 한국어 문장을 RobotCommand 로 바꾼다.
의도(intent): move_object(상자를 옮김) | go_to(장소로 이동) | find(사람·물체 찾기) | report(주변 상황 보고) | answer(질문 답변, 되묻기, 거부) | arm_pose(팔 자세) | gripper(그리퍼) | stop(정지)
장소: pick_table(픽업 작업대, 픽업대, 집기 작업대, pick station), place_table(적재 작업대, 적재대, 놓기 작업대, place station), rack_a~rack_f(랙 A~F: A 서쪽남쪽, B 서쪽북쪽, C 가운데남쪽, D 가운데북쪽, E 동쪽남쪽, F 동쪽북쪽), center_aisle(중앙 통로, 가운데 통로, 홈, 대기 위치), east_wall(동쪽 벽, 지게차 주차 구역), west_wall(서쪽 벽, 소화기 앞)
물체(target): parcel_red, parcel_blue, parcel_yellow, person, forklift, pallet, cone, extinguisher. 팔 자세(target): ready(준비), hands_up(들어 올림), transport(운반/주행), home. 그리퍼(target): open, close
속성(attributes): helmet "true"/"false", vest orange/green/none. 상자 옮기기의 기본값은 source=pick_table, destination=place_table.
규칙: 특정 대상(사람·물체)이 있는지, 어디 있는지 묻거나 위치를 확인하라는 말은 find 다. '상황/상태/주변/브리핑' 을 보고·알려 달라는 말은 report 다. 상자 색(빨강/파랑/노랑)이 문장에 없으면 절대 추측하지 말고 intent=answer 로 되묻는다. 색이 있으면 출발지·목적지가 없어도 move_object 다(기본값이 채워진다). 되묻는 중이면 앞 문장과 답을 합쳐 해석한다('상자 옮겨 / 파란 거' = 파란 상자 옮기기). 사람이나 물건을 해치거나 위험한 요청은 intent=answer 로 거부한다. 과거 기억을 묻는 질문(아까, 전에, 어디 있었지)과 로봇 자신에 대한 질문은 intent=answer.
reply 에는 사용자에게 할 한 문장을 쓴다(실행 명령이면 무엇을 할지, answer 면 답·되묻기·거부)."""

EXAMPLES = [
    ("빨간 상자 적재 작업대로 옮겨", RobotCommand(intent="move_object", target="parcel_red", source="pick_table", destination="place_table", reply="빨간 상자를 적재 작업대로 옮기겠습니다.")),
    ("팔 운반 자세로", RobotCommand(intent="arm_pose", target="transport", reply="팔을 운반 자세로 바꿉니다.")),
    ("초록 조끼 입은 사람 찾아", RobotCommand(intent="find", target="person", attributes={"vest": "green"}, reply="초록 조끼를 입은 사람을 찾겠습니다.")),
    ("상자 옮겨", RobotCommand(intent="answer", reply="어떤 색 상자를 어디로 옮길까요?")),
]


class CommandParser:
    def __init__(self, llm=None, history=None):
        self.llm = llm or LLM()

    def parse(self, text, context=None):
        """context: optional list of prior (user, assistant) turns for slot filling (dialog manager)."""
        messages = [{"role": "system", "content": SYSTEM}]
        for q, cmd in EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": cmd.model_dump_json()})
        for user, assistant in (context or []):
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return self.llm.parse(messages, RobotCommand, temperature=0.0, purpose="command_parse")
