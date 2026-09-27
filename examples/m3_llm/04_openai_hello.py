#!/usr/bin/env python3
"""M3 예제 4: 첫 OpenAI API 호출. system prompt, 온도, 토큰 한도, 비용 로그.

실행:
    ./scripts/mobile_openarm exec python examples/m3_llm/04_openai_hello.py
  준비: .env 에 OPENAI_API_KEY (.env.example 참고). 모델·가격은 src/warehouse_lecture/config/llm.yaml.

배우는 점 (트랜스포머 한 줄 요약: 입력 토큰열을 보고 다음 토큰의 확률분포를 내는 함수를 반복 호출하는 것이 생성이다):
- 토큰: 모델이 세는 단위. 한국어는 글자당 1~2 토큰. 입력·출력 토큰 수에 비례해 과금된다 (llm.yaml 의 pricing 으로 추정).
- system prompt: 역할·규칙·출력 형식. 매 요청에 함께 보내므로 길이가 비용이다.
- temperature: 0 이면 거의 결정적(같은 답), 1 이면 다양. 로봇 명령 해석은 0~0.2, 설명문 생성은 0.5~0.8.
- max_tokens: 출력 상한. 부족하면 문장이 잘린다(finish_reason=length). JSON 을 받을 땐 넉넉히.
- 모든 호출은 warehouse_lecture.llm.client.LLM 을 거친다. 모델 이름·재시도·타임아웃·비용 로그(logs/openai_usage.jsonl)가 한곳에 있다.
"""

import json
from pathlib import Path

from warehouse_lecture.llm.client import LLM

SYSTEM = ("너는 창고 이동 로봇 '핑키'의 두뇌다. 로봇에는 카메라 2대, 라이다, 양팔이 있고 상자를 집어 옮길 수 있다. "
          "답은 한국어로, 두 문장 이내로 간결하게 한다.")


def main():
    llm = LLM()
    print(f"모델: chat={llm.models['chat']} vision={llm.models['vision']}  비용 로그: {llm.log_path}")

    # 1) 기본 호출: system + user
    answer = llm.chat([{"role": "system", "content": SYSTEM},
                       {"role": "user", "content": "안전모를 안 쓴 사람을 보면 어떻게 해야 해?"}], purpose="hello")
    print("\n[1] 기본 호출:", answer)

    # 2) 온도: 같은 질문을 temperature 0 과 1.0 으로 각 3번
    q = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "창고에서 네가 할 수 있는 일을 한 문장으로 말해 줘."}]
    for t in (0.0, 1.0):
        print(f"\n[2] temperature={t}")
        for i in range(3):
            print("   ", llm.chat(q, temperature=t, max_tokens=80, purpose=f"temp_{t}"))

    # 3) 토큰 한도: 너무 작으면 잘린다
    print("\n[3] max_tokens=12:", llm.chat(q, max_tokens=12, purpose="truncate"), "...(잘림)")

    # 4) 비용 로그 읽기: 이 스크립트가 쓴 토큰과 추정 비용
    rows = [json.loads(l) for l in Path(llm.log_path).read_text().splitlines()]
    mine = rows[-8:]
    tokens_in, tokens_out = sum(r["input_tokens"] for r in mine), sum(r["output_tokens"] for r in mine)
    print(f"\n[4] 이번 실행 {len(mine)}회 호출: 입력 {tokens_in} + 출력 {tokens_out} 토큰, 추정 ${sum(r['cost_usd'] for r in mine):.5f} "
          f"(누적 로그 {len(rows)}회, ${sum(r['cost_usd'] for r in rows):.4f})")


if __name__ == "__main__":
    main()
