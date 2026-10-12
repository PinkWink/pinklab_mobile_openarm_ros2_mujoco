"""Figures for the lesson-14 Confluence page (⑬ MuJoCo Web Dashboard). Output: docs/camp/lesson14_*.png

    python3 docs/camp/draw_lesson14_figures.py
Data (2026-10-12, gpt-4.1-mini, lessons/09_web_dashboard/server.py + task_manager):
  artifacts/dev/l13dash/final/f*.png   headless Chrome screenshots every 2 s (docs/camp/cdp_capture.py, 1600 x 1250)
  artifacts/dev/l13dash/tm.log         Task Manager log of the same run (step timeline)
  artifacts/dev/l13dash/final_*.log    the user turns sent by the test driver and what the dashboard showed
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = Path("docs/camp")
DATA = Path("artifacts/dev/l13dash")
RED, BLUE, GREEN, GREY, ORANGE, PURPLE = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100", "#6a1b9a"
FONT = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.15, "⑫ 는 터미널에서 문장을 쳤다. ⑬ 은 같은 대화 관리자를 브라우저에 붙인다.", bold=True, fs=12)
    tiles(ax, [("⑫ 08_text_mission.py", ["터미널에 문장 입력 · print 로 대답", "단계 진행은 로그 줄로만", "로봇 · 지도 · 카메라는 다른 창"], C["grey"]),
               ("⑬ 웹 대시보드", ["입력창 · 빠른 지령 버튼 · [실행 취소]", "단계 목록 · 진행 막대 · 피드백 한 줄", "지도 · 카메라 · 로봇 상태를 한 화면에"], C["blue"]),
               ("그대로 쓰는 것", ["PlanDialogManager (되묻기 · 확인)", "Task Manager (/execute_plan)", "04 대시보드 (지도 · 카메라 · SSE)"], C["green"])],
          cols=3, y_top=3.7, gap=0.3, h=2.2, tfs=11, fs=9)
    note(ax, 0.3, 1.05, "예제: lessons/09_web_dashboard/  server.py · static/index.html · desk.js · desk.css   (04 의 server.py · app.js 를 불러 쓴다)", fs=9.8)
    save(fig, "lesson14_why.png")


def arch():
    fig, ax = fig_ax(14, 6.8)
    note(ax, 0.3, 6.5, "통신 구조: 브라우저는 HTTP 만, 서버 안의 세 스레드가 웹 · LLM · ROS 2 를 잇는다", bold=True, fs=12)
    rbox(ax, 0.3, 1.6, 3.0, 4.2, "브라우저", ["index.html", "app.js (04): 지도 · 카메라", "desk.js: 대화 · 단계", "", "fetch POST → 문장", "EventSource ← SSE", "<img> ← MJPEG"], fc=C["purple"], tfs=11, fs=8.8)
    ax.add_patch(Rectangle((4.0, 0.3), 5.0, 5.8, fc="#F7F9FC", ec="#90A4AE", lw=1.2, zorder=1)); note(ax, 4.15, 5.85, "터미널 3: server.py (한 프로세스)", bold=True, fs=9.8, color=BLUE)
    rbox(ax, 4.2, 3.9, 4.6, 1.7, "Flask 스레드", ["POST /api/say · /api/task_cancel", "/api/stream (SSE 5 Hz, task 포함)", "/camera/<cam>.mjpg · /api/map.png"], fc=C["yellow"], tfs=10, fs=8.4)
    rbox(ax, 4.2, 2.0, 4.6, 1.5, "대화 스레드 (queue)", ["PlanDialogManager.handle(문장)", "LLM 계획 → 되묻기 · 확인 · 실행"], fc=C["orange"], tfs=10, fs=8.4)
    rbox(ax, 4.2, 0.5, 4.6, 1.2, "ROS 스레드 (rclpy)", ["구독 9 개 + /execute_plan 클라이언트"], fc=C["blue"], tfs=10, fs=8.4)
    arrow(ax, (6.5, 3.9), (6.5, 3.5)); arrow(ax, (6.5, 2.0), (6.5, 1.7))
    rbox(ax, 9.8, 3.6, 3.9, 2.0, "터미널 2: task_manager", ["ExecutePlan 액션 서버", "Nav2 · PickPlace · 카메라 · LLM 보고"], fc=C["green"], tfs=10, fs=8.4)
    rbox(ax, 9.8, 0.5, 3.9, 2.4, "터미널 1: 시뮬레이터", ["MuJoCo · Nav2 · MoveIt · PickPlace", "frame_tap → /dev/shm/…/<cam>.jpg", "/odom · /scan · /map · /vision/*"], fc=C["teal"], tfs=10, fs=8.4)
    arrow(ax, (3.3, 4.9), (4.2, 4.9)); label(ax, 3.65, 5.2, "문장", fs=8.4)
    arrow(ax, (4.2, 4.3), (3.3, 4.3)); label(ax, 3.65, 4.0, "상태", fs=8.4)
    ax.plot([8.8, 9.25, 9.25], [1.35, 1.35, 4.9], color=GREEN, lw=1.4, zorder=4); arrow(ax, (9.25, 4.9), (9.8, 4.9), color=GREEN)
    ax.plot([9.8, 9.55, 9.55], [4.2, 4.2, 1.05], color=GREEN, lw=1.4, zorder=4); arrow(ax, (9.55, 1.05), (8.8, 1.05), color=GREEN)
    label(ax, 9.4, 5.25, "goal · cancel", color=GREEN, fs=8.2); label(ax, 9.4, 3.2, "feedback\nresult", color=GREEN, fs=8.2)
    arrow(ax, (9.8, 0.8), (8.8, 0.8)); label(ax, 9.3, 0.45, "토픽", fs=8.2)
    arrow(ax, (11.75, 2.9), (11.75, 3.6)); label(ax, 12.3, 3.25, "액션", fs=8.2)
    note(ax, 0.3, 0.9, "http://localhost:8080", bold=True, fs=10, color=BLUE)
    save(fig, "lesson14_arch.png")


def sequence():
    fig, ax = fig_ax(14, 6.4)
    note(ax, 0.3, 6.15, "지령 한 건: \"빨간 상자 적재대로 옮겨\" → 확인 → \"응\" → 5 단계 실행", bold=True, fs=12)
    cols = [("브라우저", 1.3), ("Flask", 4.0), ("대화 스레드", 6.7), ("OpenAI", 9.2), ("Task Manager", 12.0)]
    for name, x in cols:
        rbox(ax, x - 1.0, 5.25, 2.0, 0.55, name, fc=C["blue"] if name != "OpenAI" else C["grey"], tfs=10)
        ax.plot([x, x], [0.3, 5.25], color="#B0BEC5", lw=1.0, ls="--", zorder=1)
    rows = [
        (1.3, 4.0, 4.85, "POST /api/say  (200 즉시 응답)", INK),
        (4.0, 6.7, 4.45, "inbox.put(문장)", INK),
        (6.7, 9.2, 4.05, "계획 요청 (Structured Outputs)", INK),
        (9.2, 6.7, 3.65, "RobotPlan 5 단계 · 약 1.5 s", INK),
        (6.7, 1.3, 3.25, "SSE: 확인 문장 + 단계 목록 (phase=confirm)", PURPLE),
        (1.3, 6.7, 2.75, "POST \"응\" → inbox", INK),
        (6.7, 12.0, 2.3, "ExecutePlan goal", GREEN),
        (12.0, 6.7, 1.85, "feedback (단계 · 단계 안 진행)", GREEN),
        (6.7, 1.3, 1.45, "SSE: active / done · 진행 막대", PURPLE),
        (12.0, 6.7, 1.0, "result: 5/5 · \"빨간 상자를 적재 작업대에 놓았습니다.\"", GREEN),
        (6.7, 1.3, 0.55, "SSE: 결과 문장 (phase=idle)", PURPLE),
    ]
    for x0, x1, y, text, color in rows:
        arrow(ax, (x0, y), (x1, y), color=color, lw=1.4)
        label(ax, (x0 + x1) / 2, y + 0.17, text, color=color, fs=8.4)
    save(fig, "lesson14_sequence.png")


def phases():
    fig, ax = fig_ax(14, 3.2)
    note(ax, 0.3, 2.95, "작업 지령 패널의 상태 (SSE 의 task.phase)", bold=True, fs=12)
    chain(ax, [("대기 idle", ["입력 가능"]), ("LLM 계획 중 thinking", ["입력 막힘 · 1 ~ 2 s"]), ("확인 대기 confirm", ["단계 목록 표시", "응 / 아니 / 다른 문장"]),
               ("실행 중 running", ["[실행 취소] 켜짐", "단계 active → done"]), ("대기 idle", ["결과 문장 · 이벤트 로그"])],
          y=0.5, h=1.85, colors=[C["grey"], C["orange"], C["yellow"], C["blue"], C["green"]], tfs=10, fs=8.6)
    save(fig, "lesson14_phases.png")


def cancel_chain():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "[실행 취소] 가 바퀴까지 가는 길: 액션마다 cancel 을 다음 액션으로 넘긴다", bold=True, fs=12)
    chain(ax, [("브라우저", ["POST /api/task_cancel"]), ("server.py", ["goal.cancel_goal_async()"]), ("Task Manager", ["on_cancel → cancel_flag", "call() 이 PickPlace 취소"]),
               ("PickPlace", ["on_cancel →", "nav.cancel_requested"]), ("nav_client", ["turn · drive · dock 루프", "stop() 후 예외"])],
          y=2.2, h=1.9, colors=[C["purple"], C["yellow"], C["green"], C["teal"], C["blue"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 1.55, "고치기 전: cancel 요청을 받아도 cancel_flag 를 세우지 않음 → 피드백 콜백 안의 예외는 ROS executor 로 사라지고 계획은 계속 (side-step 중 15 s 지연)", fs=9.4, color=RED)
    note(ax, 0.3, 1.0, "고친 뒤 (2026-10-12): 취소 요청 → PickPlace 정지 0.4 s, 결과 문장 \"2단계까지 마치고 취소했습니다.\"", fs=9.4, color=GREEN)
    note(ax, 0.3, 0.45, "팔(MoveIt) 동작 중이면 그 동작이 끝난 뒤 멈춘다 (실측 약 7 s)", fs=9.4)
    save(fig, "lesson14_cancel.png")


# ================================================================ 2. 실행 결과 (실제 화면)
def frame(i):
    return Image.open(DATA / "final" / f"f{i:03d}.png").convert("RGB")


def shot(i, name, crop=None):
    im = frame(i)
    im = im.crop(crop or (0, 0, im.width, max(b for _, b in card_spans(im, 982) + card_spans(im, 18)) + 12))
    im.save(OUT / name)
    print("saved", name)


def card_spans(im, x):
    """(top, bottom) of the dashboard cards crossing column x: cards are separated by >= 10 px of page background."""
    bg = lambda p: abs(p[0] - 15) < 4 and abs(p[1] - 20) < 4 and abs(p[2] - 25) < 4
    spans, top, run = [], None, 0
    for y in range(40, im.height):
        if bg(im.getpixel((x, y))):
            run += 1
            if run == 10 and top is not None:
                spans.append((top, y - 10)); top = None
        else:
            if top is None and run >= 10:
                top = y
            run = 0
    if top is not None:
        spans.append((top, im.height - 1))
    return spans


def layout(i):
    im = frame(i)
    first = card_spans(im, 18)[0]                        # card padding columns: no inputs or images there
    side = card_spans(im, 982)
    im = im.crop((0, 0, 1600, side[-1][1] + 12))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 22)
    boxes = [((12, first[0], 962, first[1]), "① 지도 · 계획의 장소")] + [
        ((975, a, 1588, b), t) for (a, b), t in zip(side, ["② 작업 지령", "③ 로봇", "④ 카메라", "⑤ 이벤트"])]
    for (x0, y0, x1, y1), text in boxes:
        d.rectangle((x0, y0, x1, y1), outline="#ffd43b", width=4)
        tw = d.textlength(text, font=f)
        d.rectangle((x0 + 8, y0 + 8, x0 + 20 + tw, y0 + 40), fill="#ffd43b")
        d.text((x0 + 14, y0 + 11), text, font=f, fill="#111111")
    im.save(OUT / "lesson14_layout.png")
    print("saved lesson14_layout.png")


def timeline():
    """Step bars of the red run from the Task Manager log: '[k/5 action/phase] detail' lines with ROS wall stamps."""
    rows = []
    for line in open(DATA / "tm.log"):
        m = re.search(r"\[INFO\] \[(\d+\.\d+)\] \[task_manager\]: \[(\d)/(\d) (\w+)/(\w+)\]", line)
        if m:
            rows.append((float(m.group(1)), int(m.group(2)), m.group(4)))
    first_run = []
    for t, k, a in rows:
        if first_run and k < first_run[-1][1]:
            break
        first_run.append((t, k, a))
    t0 = first_run[0][0]
    t_end = None
    for line in open(DATA / "tm.log"):
        m = re.search(r"\[(\d+\.\d+)\] \[task_manager\]: \[5/5 place/pick_place\] retreat", line)
        if m:
            t_end = float(m.group(1)) + 1.0
            break
    starts = {}
    for t, k, a in first_run:
        starts.setdefault(k, (t - t0, a))
    names = {1: "1. 픽업 작업대로 이동", 2: "2. 빨간 상자 확인", 3: "3. 빨간 상자 집기", 4: "4. 적재 작업대로 이동", 5: "5. 적재 작업대에 놓기"}
    colors = {"navigate": "#1f77b4", "detect": "#9467bd", "pick": "#2ca02c", "place": "#ff7f0e"}
    end = (t_end or first_run[-1][0]) - t0
    fig, ax = plt.subplots(figsize=(14, 3.6), dpi=150)
    ks = sorted(starts)
    for j, k in enumerate(ks):
        s, a = starts[k]
        e = starts[ks[j + 1]][0] if j + 1 < len(ks) else end
        ax.barh(6 - k, e - s, left=s, color=colors.get(a, GREY), height=0.6)
        if e - s >= 5:
            ax.text(s + (e - s) / 2, 6 - k, f"{e - s:.0f} s", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
        else:                                            # detect: the camera already saw it, under a second
            ax.text(e + 1.5, 6 - k, f"{e - s:.0f} s" if e - s >= 1 else "< 1 s", ha="left", va="center", color=colors.get(a, GREY), fontsize=10, fontweight="bold")
    ax.set_yticks([6 - k for k in ks]); ax.set_yticklabels([names[k] for k in ks], fontsize=10)
    ax.set_xlabel("확인 \"응\" 뒤 경과 시간 (s, 벽시계)"); ax.set_xlim(0, end * 1.02)
    ax.set_title(f"빨간 상자 운반 5 단계 · 합계 {end:.0f} s (Task Manager 로그)", fontsize=12, loc="left")
    ax.grid(axis="x", alpha=0.3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "lesson14_timeline.png", facecolor="white")
    plt.close(fig)
    print("saved lesson14_timeline.png")


if __name__ == "__main__":
    why(); arch(); sequence(); phases(); cancel_chain()
    if len(sys.argv) > 1 and sys.argv[1] == "--shots":
        layout(int(sys.argv[2]))
        timeline()
