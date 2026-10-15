"""Figures for the lesson-12 Confluence page (LLM + OpenAI API). Output: docs/camp/lesson12_*.png

    python3 docs/camp/draw_lesson12_figures.py
Data (2026-10-10, gpt-4.1-mini, lessons/08_lmm):
  artifacts/dev/l12/acc_run{1,2,3}.json  03_accuracy.py, three runs of the 60-sentence test (temperature 0)
  artifacts/dev/l12/tokens.log           input tokens of one parse request measured by adding its parts one by one
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100"
RUNS = [json.loads(Path(f"artifacts/dev/l12/acc_run{k}.json").read_text()) for k in (1, 2, 3)]
TOK = json.loads(Path("artifacts/dev/l12/tokens.log").read_text().splitlines()[0])
INTENTS = ["move_object", "go_to", "find", "report", "answer", "arm_pose", "gripper", "stop"]


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "LLM 은 '무엇을 할지' 만 정한다. '어떻게 움직일지' 는 ROS 2 가 정한다.", bold=True, fs=12)
    tiles(ax, [("LLM 이 하는 일", ["한국어 문장 → 의도 + 대상 + 장소", "모호하면 되묻기, 위험하면 거부", "결과를 사람 말로 보고"], C["green"]),
               ("LLM 이 하지 않는 일", ["관절 각도 · 속도 · 좌표 계산", "경로 계획 · 충돌 판단", "실행 중 실시간 제어 (호출 ~1 s)"], C["red"]),
               ("그래서 필요한 것", ["정해진 모양의 출력 (스키마)", "실행 전 세계 검증", "정확도 · 비용 측정"], C["blue"])],
          cols=3, y_top=3.9, gap=0.3, h=2.2, tfs=11, fs=9)
    note(ax, 0.3, 1.25, "예제: lessons/08_lmm/  01_hello · 02_structured_command · 03_accuracy · 04_cost_log   (시뮬레이터 없이 돈다)", fs=9.8)
    save(fig, "lesson12_why.png")


def pipeline():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.95, "자연어 → RobotCommand → 두 번의 검증 → 실행 (⑫)", bold=True, fs=12)
    chain(ax, [("사용자 문장", ["\"빨간 상자", "적재대로 옮겨\""]), ("LLM 호출", ["system 규칙", "+ 예시 4 개 + 문장"]),
               ("Structured Outputs", ["응답이 RobotCommand", "JSON 스키마를 따름"]), ("① 스키마 검증", ["pydantic", "intent · 장소 enum"]),
               ("② 세계 검증", ["validate_world()", "가능한가 · 기본값"]), ("실행 (⑫)", ["Task Manager", "Nav2 · PickPlace"])],
          y=1.3, h=1.9, tfs=10, fs=8.6, gap=0.25, colors=[C["grey"], C["yellow"], C["yellow"], C["blue"], C["green"], C["purple"]])
    note(ax, 0.3, 0.75, "① 은 모양 (형식), ② 는 뜻 (이 창고에서 할 수 있나). 둘 다 통과해야 로봇이 움직인다. intent=answer 는 실행 없이 reply 만 보여 준다.", fs=9.6)
    save(fig, "lesson12_pipeline.png")


def schema():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.35, "RobotCommand (warehouse_lecture/commands/schema.py) — 필드와 허용 값", bold=True, fs=12)
    rows = [("intent", "move_object · go_to · find · report · answer · arm_pose · gripper · stop  (8 개 중 하나)", C["blue"]),
            ("target", "parcel_red/blue/yellow · person · forklift · pallet · cone · extinguisher · 자세 · open/close", C["yellow"]),
            ("source", "'' · pick_table · place_table · rack_a ~ rack_f · center_aisle · east_wall · west_wall", C["green"]),
            ("destination", "source 와 같은 enum (12 개)", C["green"]),
            ("attributes", "helmet: \"true\"/\"false\" · vest: orange/green/none", C["purple"]),
            ("reply", "사용자에게 할 한 문장 (실행 안내 · 되묻기 · 거부)", C["grey"])]
    for i, (k, v, fc) in enumerate(rows):
        y = 4.55 - i * 0.75
        rbox(ax, 0.3, y, 2.4, 0.6, k, fc=fc, tfs=10.5)
        ax.text(2.95, y + 0.3, v, va="center", fontsize=9.8, color=INK)
    save(fig, "lesson12_schema.png")


def two_checks():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.55, "같은 '틀림' 이 아니다: 스키마 검증과 세계 검증 (02_structured_command.py 실측)", bold=True, fs=12)
    rbox(ax, 0.3, 1.0, 4.3, 3.1, "① 스키마에서 걸림", ["{'intent': 'fly',", " 'destination': 'kitchen'}", "→ pydantic ValidationError", "intent · destination 이 enum 밖",
                                                   "Structured Outputs 를 쓰면", "LLM 은 이런 출력을 못 낸다"], fc=C["red"], align="left", dy=0.4, fs=9.2)
    rbox(ax, 4.85, 1.0, 4.3, 3.1, "② 세계에서 걸림", ["\"노란 상자를 랙 C 로 옮겨\"", "→ move_object · parcel_yellow", "   · destination rack_c (모양은 OK)",
                                                  "validate_world():", "상자는 작업대 사이에서만", "→ 실행하지 않고 사용자에게 알림"], fc=C["yellow"], align="left", dy=0.4, fs=9.2)
    rbox(ax, 9.4, 1.0, 4.3, 3.1, "둘 다 통과", ["\"빨간 상자 적재 작업대로 옮겨 줘\"", "→ move_object · parcel_red", "   · pick_table → place_table",
                                            "validate_world(): 문제 없음", "(source 가 비면 pick_table 로 채움)", "→ ⑫ Task Manager 로"], fc=C["green"], align="left", dy=0.4, fs=9.2)
    note(ax, 0.3, 0.5, "세계 검증은 창고가 바뀌면 같이 바뀐다 (장소 · 물체 사전). 스키마에 다 넣으면 프롬프트가 길어지고, LLM 이 지켜도 '가능한가' 는 모른다.", fs=9.4)
    save(fig, "lesson12_two_checks.png")


def tokens():
    full_in, full_out = TOK["full_parse"]
    parts = [("system 규칙", TOK["system_user"][0] - TOK["user_only"][0], C["yellow"]),
             ("예시 4 개 (few-shot)", TOK["system_fewshot_user"][0] - TOK["system_user"][0], C["green"]),
             ("JSON 스키마 (response_format)", full_in - TOK["system_fewshot_user"][0], C["blue"]),
             ("사용자 문장 + 형식", TOK["user_only"][0], C["red"])]
    fig, ax = plt.subplots(figsize=(14, 3.6), dpi=150)
    x = 0
    for name, n, col in parts:
        ax.barh(0, n, left=x, color=col, ec=INK, lw=0.8, height=0.5)
        ax.text(x + n / 2, 0, f"{name}\n{n}" if n > 80 else f"{n}", ha="center", va="center", fontsize=9.5)
        x += n
    ax.barh(-0.75, full_out, color=C["purple"], ec=INK, lw=0.8, height=0.4)
    ax.text(full_out + 10, -0.75, f"출력 (RobotCommand JSON) {full_out} 토큰", va="center", fontsize=9.5)
    ax.text(x + 10, 0, f"입력 {full_in} 토큰", va="center", fontsize=10, fontweight="bold")
    ax.set_yticks([])
    ax.set_xlim(0, full_in * 1.2)
    ax.set_xlabel("토큰 (\"빨간 상자 적재 작업대로 옮겨 줘\" 한 번, 부분을 하나씩 더해 가며 실측)")
    ax.set_title("명령 한 번의 토큰: 사용자 문장은 2 % 도 안 된다", fontsize=12)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    save(fig, "lesson12_tokens.png")


# ================================================================ 2. 실행
def accuracy():
    fig, ax = plt.subplots(figsize=(14, 4.8), dpi=150)
    width = 0.26
    for k, run in enumerate(RUNS):
        good = {i: [0, 0] for i in INTENTS}
        for r in run["rows"]:
            g = good[r["expected"]["intent"]]
            g[0] += r["ok"]
            g[1] += 1
        xs = np.arange(len(INTENTS)) + (k - 1) * width
        ax.bar(xs, [good[i][0] / good[i][1] * 100 for i in INTENTS], width, color=[BLUE, GREEN, ORANGE][k],
               label=f"{k + 1} 회차: {sum(r['ok'] for r in run['rows'])}/60", ec="white")
    ns = {i: sum(1 for r in RUNS[0]["rows"] if r["expected"]["intent"] == i) for i in INTENTS}
    ax.set_xticks(range(len(INTENTS)), [f"{i}\n({ns[i]} 문장)" for i in INTENTS])
    ax.axhline(90, color=RED, ls="--", lw=1)
    ax.text(-0.45, 91, "기준 90 %", color=RED, fontsize=9, ha="left")
    ax.set_ylim(60, 104)
    ax.set_ylabel("정확도 (%)")
    ax.set_title("60 문장 변환 정확도: 같은 설정 (temperature 0) 으로 3 번 (gpt-4.1-mini, 실측)", fontsize=12)
    ax.legend(loc="lower left", fontsize=9.5)
    ax.grid(axis="y", alpha=0.3)
    save(fig, "lesson12_accuracy.png")


def misses():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.15, "틀린 문장 (3 회 중)", bold=True, fs=12)
    seen = {}
    for k, run in enumerate(RUNS):
        for r in run["rows"]:
            if not r["ok"]:
                seen.setdefault(r["text"], [r, []])[1].append(k + 1)
    for j, (text, (r, ks)) in enumerate(seen.items()):
        e, c = r["expected"], r["cmd"]
        exp = f"{e['intent']} {e.get('target', '')}".strip()
        got = f"{c['intent']} {c['target']}".strip()
        y = 2.3 - j * 1.75
        rbox(ax, 0.3, y, 13.4, 1.5, f"\"{text}\"   ({', '.join(map(str, ks))} 회차에서 틀림)",
             [f"정답 {exp}   →   모델 {got}", "규칙에 없는 경계: " + ("'누가 있어?' 는 상황 보고(report) 인가, 사람 찾기(find) 인가" if e["intent"] == "report"
                                                      else "'내려서' 가 home 자세로 읽힘. 주행 = transport 를 규칙에 적어야")],
             fc=C["red"], align="left", fs=9.6, dy=0.42)
    save(fig, "lesson12_misses.png")


def latency():
    fig, ax = plt.subplots(figsize=(14, 3.8), dpi=150)
    for k, run in enumerate(RUNS):
        s = [r["seconds"] for r in run["rows"]]
        ax.hist(s, bins=np.arange(0.4, 2.6, 0.1), histtype="step", lw=2, color=[BLUE, GREEN, ORANGE][k],
                label=f"{k + 1} 회차: 평균 {np.mean(s):.2f} s · 최대 {max(s):.2f} s")
    ax.set_xlabel("문장 하나 변환 시간 (s, 벽시계)")
    ax.set_ylabel("문장 수")
    ax.set_title("LLM 호출 지연 (실측): 실시간 제어에는 못 쓰고, 명령 해석에는 충분하다", fontsize=12)
    ax.legend(fontsize=9.5)
    ax.grid(alpha=0.3)
    save(fig, "lesson12_latency.png")


def cost():
    n = len(RUNS[0]["rows"])
    per = RUNS[0]["cost"] / n
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.95, "비용 = (입력 토큰 × 입력 단가 + 출력 토큰 × 출력 단가)  —  llm.yaml 의 단가로 추정", bold=True, fs=12)
    tiles(ax, [("명령 한 번", [f"입력 {TOK['full_parse'][0]} + 출력 {TOK['full_parse'][1]} 토큰", f"≈ \\${per:.5f}", "(gpt-4.1-mini \\$0.40 / \\$1.60 per 1M)"], C["blue"]),
               ("60 문장 시험 한 번", [f"\\${RUNS[0]['cost']:.4f}", f"3 회 합계 \\${sum(r['cost'] for r in RUNS):.3f}", "입력이 비용의 대부분"], C["green"]),
               ("어디에 남나", ["logs/openai_usage.jsonl (호출마다 한 줄)", "04_cost_log.py 로 목적별 합계", "실제 청구는 OpenAI 사용량 페이지"], C["grey"])],
          cols=3, y_top=3.5, gap=0.3, h=2.2, tfs=11, fs=9.2)
    note(ax, 0.3, 0.75, "줄이는 법: system 규칙을 짧게, 예시를 꼭 필요한 것만, 같은 문장은 다시 묻지 않기 (캐시). 키는 .env 에만 두고 git 에 올리지 않는다.", fs=9.4)
    save(fig, "lesson12_cost.png")


if __name__ == "__main__":
    for f in (why, pipeline, schema, two_checks, tokens, accuracy, misses, latency, cost):
        f()
