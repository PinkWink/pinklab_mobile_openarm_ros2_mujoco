"""Korean utterance -> RobotPlan (ordered steps) with OpenAI Structured Outputs.

Compare with parser.py (one RobotCommand per utterance): here the model decomposes a task into
navigate / detect / pick / navigate / place steps. It still never outputs joint values.
"""

from ..llm.client import LLM
from .plan import PlanStep, RobotPlan

SYSTEM = """너는 창고 이동형 양팔 로봇의 작업 계획기다. 사용자의 한국어 지령을 실행 단계 목록(RobotPlan.steps)으로 바꾼다.
단계(action): navigate(장소로 이동) | detect(카메라로 대상 확인) | pick(작업대에서 상자 집기) | place(든 상자를 작업대에 놓기) | arm_pose(팔 자세) | gripper(그리퍼) | report(주변 상황 보고) | answer(답변·되묻기·거부, steps 는 비운다)
장소(location): pick_table(픽업 작업대, 픽업대, 집기 작업대, 테이블 A, A 테이블), place_table(적재 작업대, 적재대, 놓기 작업대, 테이블 B, B 테이블), rack_a~rack_f(랙 A~F), center_aisle(중앙 통로, 홈), east_wall(동쪽 벽, 지게차 구역), west_wall(서쪽 벽, 소화기 앞)
물체(target): parcel_red(빨간 상자), parcel_blue(파란 상자), parcel_yellow(노란 상자), person, forklift, pallet, cone, extinguisher. 팔 자세: ready, hands_up, transport, home. 그리퍼: open, close.
규칙:
- 상자·박스·소포·물체·물건·거(것)는 모두 상자(parcel)다. 색(빨강/파랑/노랑)이 붙어 있으면 그 색의 상자로 확정한다: '파란 물체' = parcel_blue, '빨간 거' = parcel_red.
- 상자를 옮기는 지령은 항상 다섯 단계다: navigate(출발 작업대) → detect(상자) → pick(상자, location=출발 작업대) → navigate(도착 작업대) → place(location=도착 작업대). 출발지가 없으면 pick_table, 도착지가 없으면 place_table.
- 상자를 여러 개 옮기면 상자마다 다섯 단계를 반복한다. 로봇은 한 번에 상자 하나만 든다.
- "가서 ~ 알려줘/보고해/확인해" 는 navigate 뒤에 report 또는 detect 를 붙인다. 장소 없이 '주변에 뭐 보여?', '상황 알려줘' 처럼 지금 보이는 것을 물으면 report 한 단계만 만든다(되묻지 않는다).
- 상자 색(빨강/파랑/노랑)이 문장에 없으면 절대 추측하지 말고 steps 를 비우고 reply 로 되묻는다.
- 사람이나 물건을 해치거나 위험한 요청, 로봇이 할 수 없는 일(계단, 건물 밖)은 steps 를 비우고 reply 로 거부한다.
- 로봇 자신이나 과거에 대한 질문, 잡담은 steps 를 비우고 reply 로 답한다.
- note 에는 각 단계를 한국어 한 구절로 쓴다. summary 는 계획 전체 한 문장, reply 는 사용자에게 할 한 문장이다."""

EXAMPLES = [
    ("픽업 작업대로 가서 빨간 상자를 집고 적재 작업대로 옮겨",
     RobotPlan(summary="빨간 상자를 픽업 작업대에서 적재 작업대로 옮긴다.", reply="픽업 작업대에서 빨간 상자를 집어 적재 작업대로 옮기겠습니다.", steps=[
         PlanStep(action="navigate", location="pick_table", note="픽업 작업대로 이동"),
         PlanStep(action="detect", target="parcel_red", note="빨간 상자 확인"),
         PlanStep(action="pick", target="parcel_red", location="pick_table", note="빨간 상자 집기"),
         PlanStep(action="navigate", location="place_table", note="적재 작업대로 이동"),
         PlanStep(action="place", location="place_table", note="적재 작업대에 놓기")])),
    ("랙 C 앞에 가서 사람 있는지 알려줘",
     RobotPlan(summary="랙 C로 이동해 주변을 보고한다.", reply="랙 C로 이동해서 주변 상황을 알려 드리겠습니다.", steps=[
         PlanStep(action="navigate", location="rack_c", note="랙 C로 이동"),
         PlanStep(action="report", note="주변 상황 보고")])),
    ("상자 옮겨 줘",
     RobotPlan(summary="", reply="어떤 색 상자를 어디로 옮길까요?", steps=[])),
    ("파란 상자 옮기고 노란 상자도 적재대로",
     RobotPlan(summary="파란 상자와 노란 상자를 차례로 적재 작업대로 옮긴다.", reply="파란 상자와 노란 상자를 차례로 적재 작업대로 옮기겠습니다.", steps=[
         PlanStep(action="navigate", location="pick_table", note="픽업 작업대로 이동"),
         PlanStep(action="detect", target="parcel_blue", note="파란 상자 확인"),
         PlanStep(action="pick", target="parcel_blue", location="pick_table", note="파란 상자 집기"),
         PlanStep(action="navigate", location="place_table", note="적재 작업대로 이동"),
         PlanStep(action="place", location="place_table", note="적재 작업대에 놓기"),
         PlanStep(action="navigate", location="pick_table", note="픽업 작업대로 이동"),
         PlanStep(action="detect", target="parcel_yellow", note="노란 상자 확인"),
         PlanStep(action="pick", target="parcel_yellow", location="pick_table", note="노란 상자 집기"),
         PlanStep(action="navigate", location="place_table", note="적재 작업대로 이동"),
         PlanStep(action="place", location="place_table", note="적재 작업대에 놓기")])),
]


class PlanParser:
    def __init__(self, llm=None):
        self.llm = llm or LLM()

    def parse(self, text, context=None):
        """context: optional list of prior (user, assistant_json) turns for slot filling (dialog manager)."""
        messages = [{"role": "system", "content": SYSTEM}]
        for q, plan in EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": plan.model_dump_json()})
        for user, assistant in (context or []):
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return self.llm.parse(messages, RobotPlan, temperature=0.0, purpose="plan_parse")
