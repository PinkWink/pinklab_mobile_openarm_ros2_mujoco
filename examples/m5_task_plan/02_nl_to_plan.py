#!/usr/bin/env python3
"""M5 예제 2: 한국어 지령 20문장 -> RobotPlan(단계 목록) 변환 정확도 (Structured Outputs). 시뮬레이터 불필요, OPENAI_API_KEY 필요.

실행:
    ./scripts/mobile_openarm exec python examples/m5_task_plan/02_nl_to_plan.py [--test plans_test.yaml] [--show]
출력: artifacts/m5/nl_to_plan.json

배우는 점:
- 파서는 warehouse_lecture.commands.plan_parser.PlanParser: system prompt(규칙) + few-shot 4개 + RobotPlan 스키마.
- 채점은 단계 열(action 순서)과 pick/detect 의 대상, navigate/pick/place 의 장소만 본다. note/summary/reply 는 자유 문장이다.
- 되묻기·거부·잡담은 steps 가 비어야 정답이다. 색이 없는 상자를 추측해 계획을 만들면 오답이다.
- 틀린 문장을 보고 프롬프트의 규칙·예시를 고치는 것이 프롬프트 엔지니어링이다. 검증 기준: >= 90 %.
"""

import argparse
import json
from pathlib import Path

import yaml

from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.llm.client import LLM


def expected_steps(spec):
    """'pick:parcel_red@pick_table' -> (action, target, location); 'navigate:rack_c' -> location; 'report' -> bare."""
    out = []
    for item in spec:
        action, _, rest = str(item).partition(":")
        target, _, location = rest.partition("@")
        if action == "navigate" and target and not location:
            target, location = "", target
        out.append((action, target, location))
    return out


def actual_steps(plan):
    out = []
    for s in plan.steps:
        a = s.action.value
        target = s.target if a in ("pick", "detect", "arm_pose", "gripper") else ""
        location = s.location.value if a in ("navigate", "pick", "place") else ""
        out.append((a, target, location))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", default=str(Path(__file__).with_name("plans_test.yaml")))
    ap.add_argument("--show", action="store_true", help="모든 문장의 계획을 출력")
    a = ap.parse_args()
    cases = yaml.safe_load(Path(a.test).read_text())
    llm = LLM()
    parser = PlanParser(llm)
    rows, correct = [], 0
    for case in cases:
        plan = parser.parse(case["text"])
        problems = plan.validate_world()
        want, got = expected_steps(case["steps"]), actual_steps(plan)
        ok = want == got and not (got and problems)
        correct += ok
        rows.append({"text": case["text"], "ok": ok, "want": [":".join(w) for w in want], "got": [":".join(g) for g in got], "problems": problems, "reply": plan.reply})
        mark = "OK " if ok else "XX "
        print(f"{mark}{case['text']}")
        if a.show or not ok:
            print(f"      기대: {' > '.join(f'{w[0]}:{w[1]}@{w[2]}'.rstrip('@:') for w in want) or '(없음)'}")
            print(f"      결과: {' > '.join(f'{g[0]}:{g[1]}@{g[2]}'.rstrip('@:') for g in got) or '(없음)'}  reply={plan.reply!r}")
            if problems:
                print(f"      검증: {problems}")
    acc = correct / len(cases)
    print(f"\n정확도 {correct}/{len(cases)} = {acc * 100:.1f} %  (기준 90 %)  비용 ${llm.session_cost:.4f}")
    Path("artifacts/m5").mkdir(parents=True, exist_ok=True)
    Path("artifacts/m5/nl_to_plan.json").write_text(json.dumps({"accuracy": acc, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
