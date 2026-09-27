#!/usr/bin/env python3
"""M4 예제 2: 한국어 60문장 테스트셋으로 자연어 -> RobotCommand 변환 정확도를 잰다 (Structured Outputs).

실행:
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/02_nl_to_command.py [--test commands_test.yaml]
출력: artifacts/m4/nl_to_command.json

배우는 점:
- 파서는 warehouse_lecture.commands.parser.CommandParser (M3-06 승격). system prompt + few-shot 4개 + 스키마.
- 채점은 의도 + 명시된 슬롯만 본다. 기본값(source=pick_table)은 validate_world() 가 채우므로 파서가 비워도 정답.
- 모호(ambiguous)·위험(refuse) 문장은 answer 가 정답이고 reply 에 되묻기·거부가 있어야 한다.
- 틀린 문장을 보고 프롬프트의 어느 규칙이 부족한지 찾는 것이 프롬프트 엔지니어링이다. 검증 기준: ≥ 90 %.
"""

import argparse
import json
from pathlib import Path

import yaml
from warehouse_lecture.commands.parser import CommandParser


def score(q, cmd):
    if cmd.intent.value != q["intent"]:
        return False
    for key in ("target", "source", "destination"):
        if q.get(key):
            got = getattr(cmd, key)
            if (got.value if hasattr(got, "value") else got) != q[key]:
                return False
    for k, v in (q.get("attributes") or {}).items():
        if str(cmd.attribute_dict().get(k, "")).lower() != str(v).lower():
            return False
    if (q.get("ambiguous") or q.get("refuse")) and not cmd.reply.strip():
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default=str(Path(__file__).with_name("commands_test.yaml")))
    a = ap.parse_args()
    tests = yaml.safe_load(Path(a.test).read_text())
    parser = CommandParser()
    rows, ok = [], 0
    by_intent = {}
    for q in tests:
        try:
            cmd = parser.parse(q["text"])
        except ValueError as error:
            print(f"  거부/실패 {q['text']!r}: {error}")
            rows.append({"text": q["text"], "expected": q["intent"], "error": str(error), "ok": False})
            continue
        cmd.validate_world()
        good = score(q, cmd)
        ok += good
        by_intent.setdefault(q["intent"], [0, 0])
        by_intent[q["intent"]][0] += good; by_intent[q["intent"]][1] += 1
        rows.append({"text": q["text"], "expected": q["intent"], "cmd": json.loads(cmd.model_dump_json()), "ok": good})
        if not good:
            print(f"  X {q['text']!r} -> {cmd.intent.value} target={cmd.target} src={cmd.source.value} dst={cmd.destination.value} attrs={cmd.attribute_dict()} | {cmd.reply}")
    print(f"\n정확도 {ok}/{len(tests)} = {ok / len(tests) * 100:.1f} %  (기준 90 %)  비용 ${parser.llm.session_cost:.4f}")
    for intent, (g, n) in by_intent.items():
        print(f"  {intent:12s} {g}/{n}")
    out = Path("artifacts/m4"); out.mkdir(parents=True, exist_ok=True)
    (out / "nl_to_command.json").write_text(json.dumps({"accuracy": ok / len(tests), "by_intent": by_intent, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
