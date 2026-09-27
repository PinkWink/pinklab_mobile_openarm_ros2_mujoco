#!/usr/bin/env python3
"""M3 예제 6: Structured Outputs(pydantic 스키마)와 tool calling 으로 명령 JSON 을 강제 생성한다. 실패 케이스 관찰.

실행:
    ./scripts/mobile_openarm exec python examples/m3_llm/06_structured_output.py
출력: artifacts/m3/structured_output.json

배우는 점:
- Structured Outputs: 응답이 스키마(JSON Schema)를 반드시 만족한다. 파싱 실패 0. enum 으로 의도·장소를 제한하면 오타도 사라진다.
- tool calling: "함수 목록"을 주면 모델이 함수와 인자를 고른다. 의도마다 함수를 두면 인자 검증이 자연스럽다(M5 에이전트의 기초).
- 스키마가 강제하는 것은 형식이지 정답이 아니다. 모호·위험 요청은 여전히 프롬프트 규칙(되묻기·거부)으로 다룬다.
- refusal: 모델이 안전상 답을 거부하면 parsed 대신 refusal 이 온다. 예외로 처리한다.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from warehouse_lecture.llm.client import LLM, tool_schema

SYSTEM = Path(__file__).with_name("05_prompt_patterns.py").read_text().split('ROLE = """')[1].split('"""')[0]


class Intent(str, Enum):
    move_object = "move_object"; go_to = "go_to"; find = "find"; report = "report"
    answer = "answer"; arm_pose = "arm_pose"; gripper = "gripper"; stop = "stop"


class Place(str, Enum):
    none = ""; pick_table = "pick_table"; place_table = "place_table"; rack_a = "rack_a"; rack_b = "rack_b"; rack_c = "rack_c"
    rack_d = "rack_d"; rack_e = "rack_e"; rack_f = "rack_f"; center_aisle = "center_aisle"; east_wall = "east_wall"; west_wall = "west_wall"


class Attributes(BaseModel):
    helmet: Optional[str] = Field(None, description='"true" 또는 "false"')
    vest: Optional[str] = Field(None, description="orange | green | none")


class RobotCommand(BaseModel):
    """RobotCommand.msg 와 같은 필드. Structured Outputs 가 이 스키마를 강제한다."""
    intent: Intent
    target: str = Field("", description="물체(parcel_red 등)·person·자세(ready, hands_up, transport)·그리퍼(open, close)")
    source: Place = Place.none
    destination: Place = Place.none
    attributes: Attributes
    reply: str = Field(description="사용자에게 할 한 문장 (되묻기·거부 포함)")


TOOLS = [
    tool_schema("move_object", "상자를 한 작업대에서 다른 작업대로 옮긴다", {
        "target": {"type": "string", "enum": ["parcel_red", "parcel_blue", "parcel_yellow"]},
        "source": {"type": "string", "enum": [p.value for p in Place]},
        "destination": {"type": "string", "enum": [p.value for p in Place]}}),
    tool_schema("go_to", "장소로 이동한다", {"destination": {"type": "string", "enum": [p.value for p in Place if p.value]}}),
    tool_schema("find", "사람이나 물체를 찾는다", {
        "target": {"type": "string"}, "helmet": {"type": "string", "enum": ["", "true", "false"]}, "vest": {"type": "string", "enum": ["", "orange", "green", "none"]}}),
    tool_schema("report", "주변 상황을 보고한다", {}),
    tool_schema("arm_pose", "팔 자세를 바꾼다", {"target": {"type": "string", "enum": ["ready", "hands_up", "transport"]}}),
    tool_schema("gripper", "그리퍼를 열거나 닫는다", {"target": {"type": "string", "enum": ["open", "close"]}}),
    tool_schema("stop", "즉시 정지한다", {}),
    tool_schema("answer", "질문에 답하거나 되묻거나 거부한다 (실행 없음)", {"reply": {"type": "string"}}),
]


def score(q, intent, target, source, destination, attrs):
    if intent != q["intent"]:
        return False
    for key, val in (("target", target), ("source", source), ("destination", destination)):
        if q.get(key) and val != q[key]:
            return False
    for k, v in (q.get("attributes") or {}).items():
        if str(attrs.get(k) or "").lower() != str(v).lower():
            return False
    return True


def main():
    questions = yaml.safe_load(Path(__file__).with_name("questions.yaml").read_text())
    llm = LLM()
    out = {"structured": [], "tools": []}
    # 1) Structured Outputs
    ok = fails = 0
    c0 = llm.session_cost
    for q in questions:
        try:
            cmd = llm.parse([{"role": "system", "content": SYSTEM}, {"role": "user", "content": q["text"]}], RobotCommand, temperature=0.0, purpose="structured")
        except ValueError as error:                       # 모델 거부(refusal)
            fails += 1; print(f"  [structured] 거부: {q['text']!r}: {error}"); continue
        attrs = {k: v for k, v in cmd.attributes.model_dump().items() if v}
        good = score(q, cmd.intent.value, cmd.target, cmd.source.value, cmd.destination.value, attrs)
        ok += good
        out["structured"].append({"text": q["text"], "cmd": json.loads(cmd.model_dump_json()), "ok": good})
        if not good:
            print(f"  [structured] X {q['text']!r} -> {cmd.intent.value} {cmd.target} {cmd.destination.value} {attrs} | {cmd.reply}")
    print(f"[structured] 정확도 {ok}/{len(questions)}, 스키마 위반 0 (보장), 거부 {fails}, 비용 ${llm.session_cost - c0:.4f}")

    # 2) tool calling
    ok = none = 0
    c0 = llm.session_cost
    for q in questions:
        message, calls = llm.tools([{"role": "system", "content": SYSTEM + "\n반드시 함수 하나를 호출한다."}, {"role": "user", "content": q["text"]}],
                                   TOOLS, temperature=0.0, purpose="tools", tool_choice="required")
        if not calls:
            none += 1; print(f"  [tools] 호출 없음: {q['text']!r}: {message.content}"); continue
        name, args, _ = calls[0]
        attrs = {k: args[k] for k in ("helmet", "vest") if args.get(k)}
        good = score(q, name, args.get("target", ""), args.get("source", ""), args.get("destination", ""), attrs)
        ok += good
        out["tools"].append({"text": q["text"], "call": name, "args": args, "ok": good})
        if not good:
            print(f"  [tools] X {q['text']!r} -> {name}({args})")
    print(f"[tools] 정확도 {ok}/{len(questions)}, 호출 없음 {none}, 비용 ${llm.session_cost - c0:.4f}")
    Path("artifacts/m3").mkdir(parents=True, exist_ok=True)
    Path("artifacts/m3/structured_output.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"저장: artifacts/m3/structured_output.json, 세션 비용 ${llm.session_cost:.4f}")


if __name__ == "__main__":
    main()
