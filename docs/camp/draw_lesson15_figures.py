"""Figures for the lesson-15 Confluence page (⑭ Final Mission). Output: docs/camp/lesson15_*.png

Run from the workspace root (ros env sourced, workspace venv, offscreen EGL):
    MUJOCO_GL=egl ./scripts/mobile_openarm exec python docs/camp/draw_lesson15_figures.py
Data (2026-11-12, gpt-4.1-mini, `start camera_depth:=true locate:=vision viewer:=false rviz:=false`, Task Manager):
  artifacts/dev/l14/final_run2.log      02_final_mission.py, scenarios 1-3 (wall-clock step times)
  artifacts/dev/l14/final_mission.pkl   docs/camp/pick_record.py during that run (sim time)
  artifacts/dev/l14/01_run*.log, 01_final.log   01_world_plan.py runs while the prompt was being changed
Robot views are offscreen MuJoCo renders of the recorded state (base pose, parcels, joints).
"""
import math
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson08_figures import caption, hstack  # noqa: E402
import draw_lesson10_figures as L10  # noqa: E402
from draw_lesson11_figures import show_map, yaw_of  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402
from PIL import Image  # noqa: E402
import yaml  # noqa: E402

D = Path("artifacts/dev/l14")
OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE, PURPLE, YELLOW = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100", "#6A1B9A", "#F9A825"
RUN = pickle.load(open(D / "final_mission.pkl", "rb"))
FB = RUN["feedback"]
L10.RUN = RUN                       # Render.set() reads the module-level RUN


def events(prefix):
    return [f["t"] for f in FB if f["detail"].startswith(prefix)]


PICK_T = [f["t"] for f in FB if f["phase"] == "start" and " sits " in f["detail"]]     # PickPlace pick start, one per scenario
HOLD_T, RELEASE_T, END_T = events("holding at"), events("released"), events("back to transport")
assert len(PICK_T) == len(HOLD_T) == len(RELEASE_T) == len(END_T) == 3, (PICK_T, HOLD_T, RELEASE_T, END_T)
SCEN_T = [(0.0, END_T[0] + 1.0), (END_T[0] + 1.0, END_T[1] + 1.0), (END_T[1] + 1.0, END_T[2] + 1.0)]
SCEN = [("① 빨강: 픽업 → 적재", RED), ("② 파랑: 픽업 → 적재", BLUE), ("③ 빨강: 적재 → 픽업", ORANGE)]


def run_log():
    """Per scenario: [(step, action, start_s)], total_s from final_run2.log (wall clock)."""
    out, cur = [], None
    for line in open(D / "final_run2.log"):
        if line.startswith("===== 시나리오"):
            cur = {"steps": [], "total": None}
            out.append(cur)
        m = re.search(r"\[\s*([\d.]+)s (\d)/5 (\w+)/start\] (.*)", line)
        if m and cur is not None:
            cur["steps"].append((int(m.group(2)), m.group(3), float(m.group(1)), m.group(4).strip()))
        m = re.search(r"<< SUCCEEDED .*\((\d+) s\)", line)
        if m and cur is not None:
            cur["total"] = float(m.group(1))
    return out


def plan_runs(path):
    """{'none': [bool]*8, 'world': [bool]*8} from a 01_world_plan.py log."""
    res, mode = {}, None
    for line in open(path):
        m = re.match(r"== (none|world)", line)
        if m:
            mode = m.group(1)
            res[mode] = []
        m = re.match(r"^(\d) (ok|XX) ", line)
        if m and mode:
            res[mode].append(m.group(2) == "ok")
    return res


# ================================================================ 1. 개념
def pipeline():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "Final Mission: 문장 하나 → LLM 계획 → Task Manager → Nav2 · MoveIt → MuJoCo, 결과가 다음 계획의 입력이 된다", bold=True, fs=12)
    chain(ax, [("사용자", ["한국어 한 줄", "되묻기 · 확인 답"]), ("PlanParser (LLM)", ["문장 + 상자 위치표", "→ 단계 목록"]),
               ("검증 (코드)", ["validate_world()", "world.check()"]), ("Task Manager", ["/execute_plan", "단계 순차 실행"]),
               ("Nav2 · PickPlace", ["주행 · 도킹", "MoveIt 집기 · 놓기"]), ("MuJoCo", ["물리 · 카메라", "상자가 실제로 움직임"])],
          y=2.3, h=1.8, tfs=10, fs=8.6, gap=0.25, colors=[C["grey"], C["yellow"], C["green"], C["blue"], C["teal"], C["purple"]])
    arrow(ax, (12.6, 2.2), (12.6, 1.45))
    arrow(ax, (12.6, 1.45), (3.4, 1.45))
    arrow(ax, (3.4, 1.45), (3.4, 2.2))
    label(ax, 8.0, 1.45, "결과 (steps_done, success) → world.apply() → 상자 위치표 갱신", fs=9.6)
    note(ax, 0.3, 0.6, "⑫ 와 같은 파이프라인 + 상자 위치표(WorldState) 하나. 코드: lessons/10_final_project/, commands/world.py", fs=9.6)
    save(fig, "lesson15_pipeline.png")


def why_table():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.65, "LLM 은 창고를 못 본다: 이미 옮긴 상자도 '픽업 작업대에서 집기' 로 계획한다", bold=True, fs=12)
    rbox(ax, 0.3, 0.5, 6.5, 3.7, "⑫ 표 없음 (2026-10-10 실측)", ["빨간 상자는 이미 적재 작업대에 있다", "", "\"빨간 상자 적재대로 옮겨\"",
                                                          "→ navigate(pick_table) → detect(빨강) ...", "",
                                                          "2단계 detect 실패: 카메라에 안 보인다", "52 s 주행만 하고 끝"], fc=C["red"], fs=9.8, dy=0.38)
    rbox(ax, 7.2, 0.5, 6.5, 3.7, "⑭ 표를 프롬프트에", ["parcel_red: place_table (적재 작업대)", "",
                                                    "\"빨간 상자 다시 픽업대로 가져와\"", "→ navigate(place_table) → pick @place_table", "→ place @pick_table", "",
                                                    "5/5 단계, 140 s (오늘 실측)"], fc=C["green"], fs=9.8, dy=0.38)
    arrow(ax, (6.8, 2.35), (7.2, 2.35))
    save(fig, "lesson15_why.png")


def world_state():
    fig, ax = fig_ax(14, 4.7)
    ax.set_ylim(0.7, 4.7)
    note(ax, 0.3, 4.45, "WorldState (commands/world.py): 상자마다 한 줄 — pick_table · place_table · held · unknown", bold=True, fs=12)
    tiles(ax, [("① prompt(): 계획 전", ["표 3 줄 + 규칙 4 줄", "system 프롬프트 끝에 붙인다", "출발 작업대 = 표에 적힌 곳"], C["yellow"]),
               ("② check(plan): 실행 전", ["집으려는 상자가 다른 작업대에 있다", "상자가 이미 도착지에 있다", "→ 실행하지 않고 다시 묻는다"], C["green"]),
               ("③ apply(): 실행 뒤", ["끝난 단계(steps_done)만 반영", "pick 끝 → held, place 끝 → 작업대", "실패한 pick · place → unknown"], C["blue"])],
          cols=3, y_top=4.0, gap=0.3, h=1.9, tfs=11, fs=9.4)
    note(ax, 0.3, 1.5, "처음 값: 세 상자 모두 pick_table. 시뮬레이터를 다시 띄우면 상자도 처음 자리로 돌아가므로 표도 처음부터.", fs=9.6)
    note(ax, 0.3, 1.05, "표는 '로봇이 마지막으로 확인한 것' 이다. 진짜 위치는 detect 단계가 카메라로 다시 확인한다.", fs=9.6)
    save(fig, "lesson15_world.png")


def roles():
    runs = {"표 없음": [plan_runs(D / f"01_run{k}.log")["none"] for k in (3, 4, 5)] + [plan_runs(D / "01_final.log")["none"]],
            "표 + '이미 있으면\n비워라' 를 LLM 에": [plan_runs(D / f"01_run{k}.log")["world"] for k in (1, 2)],
            "표, '이미 있다'\n판정은 코드": [plan_runs(D / f"01_run{k}.log")["world"] for k in (3, 4, 5)],
            "+ '말한 도착지는\n그대로' (최종)": [plan_runs(D / f"01_run{k}.log")["world"] for k in (6, 7, 8)] + [plan_runs(D / "01_final.log")["world"]]}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.0), dpi=150, gridspec_kw={"width_ratios": [1.15, 1]})
    a1.set_xlim(0, 7)
    a1.set_ylim(0, 5)
    a1.axis("off")
    a1.text(0.1, 4.75, "누가 무엇을 정하나", fontsize=12, fontweight="bold", color=INK)
    rbox(a1, 0.1, 2.35, 3.25, 2.1, "LLM: 의도", ["무엇을 · 어디로", "\"다시\", \"원래 자리\" 해석", "되묻기 · 거부 문장"], fc=C["yellow"], fs=9.4, dy=0.38)
    rbox(a1, 3.6, 2.35, 3.25, 2.1, "코드: 사실", ["상자가 지금 어디 있나", "이미 도착지에 있나", "든 것 · 장소 (validate_world)"], fc=C["green"], fs=9.4, dy=0.38)
    a1.text(0.1, 1.75, "'이미 거기 있으면 steps 를 비워라' 를 프롬프트에 넣자", fontsize=9.6, color="#444")
    a1.text(0.1, 1.35, "LLM 이 멀쩡한 지령까지 비웠다 (8 개 중 3 · 4 개만 맞음).", fontsize=9.6, color="#444")
    a1.text(0.1, 0.85, "그 판정을 check() 로 옮기고, '문장이 말한 도착지는", fontsize=9.6, color="#444")
    a1.text(0.1, 0.45, "그대로 쓴다' 를 넣은 뒤 8/8 (4 회 연속).", fontsize=9.6, color="#444")
    names = list(runs)
    for i, n in enumerate(names):
        vals = [sum(r) for r in runs[n]]
        col = [GREY, RED, YELLOW, GREEN][i]
        a2.bar(i, sum(vals) / len(vals), color=col, alpha=0.85, width=0.62)
        for j, v in enumerate(vals):
            a2.plot(i - 0.18 + 0.36 * j / max(1, len(vals) - 1), v, "o", color="k", ms=5, zorder=4)
        a2.text(i, max(vals) + 0.35, " · ".join(str(v) for v in vals), ha="center", fontsize=9.2)
    a2.set_xticks(range(len(names)))
    a2.set_xticklabels(names, fontsize=8.8)
    a2.set_ylim(0, 9)
    a2.set_ylabel("맞은 문장 수 / 8")
    a2.set_title("01_world_plan.py 8 문장, 프롬프트를 바꿔 가며 (점 = 1 회)", fontsize=10.5)
    a2.grid(axis="y", alpha=0.3)
    save(fig, "lesson15_roles.png")


def scenarios():
    fig, ax = fig_ax(14, 5.0)
    ax.set_ylim(1.3, 5.0)
    note(ax, 0.3, 4.75, "시나리오 3 개 (02_final_mission.py, 이어서 실행 — 표가 다음 시나리오로 넘어간다)", bold=True, fs=12)
    items = [("① 빨간 상자", ["\"픽업 작업대로 가서 빨간 상자를", " 집고 적재 작업대로 옮겨\" → \"응\"", "", "표 뒤: 빨강 = 적재 작업대"], C["red"]),
             ("② 파란 상자 (되묻기)", ["\"상자 하나 적재대로 옮겨 줘\"", "→ 어떤 색? → \"파란 거\" → \"응\"", "", "표 뒤: 파랑 = 적재 작업대"], C["blue"]),
             ("③ 빨간 상자 되돌리기", ["\"빨간 상자 다시 픽업대로 가져와\"", "→ 표를 보고 pick @place_table", "", "표 뒤: 빨강 = 픽업 작업대"], C["yellow"])]
    tiles(ax, items, cols=3, y_top=4.3, gap=0.3, h=2.0, tfs=11, fs=9.4)
    note(ax, 0.3, 1.75, "모두 5 단계: navigate(출발) → detect → pick → navigate(도착) → place. 확인 \"진행할까요?\" 에 \"응\" 이면 실행.", fs=9.6)
    save(fig, "lesson15_scenarios.png")


# ================================================================ 2. 실행
def start_screen():
    r = L10.renderer()
    p = RUN["base"][5]["pose"]
    img = r.image(RUN["base"][5]["t"], lookat=[p[0] + 0.8, p[1], 0.4], distance=7.5, azimuth=200, elevation=-38)
    img = img.resize((1000, int(1000 * img.height / img.width)))
    img.save(OUT / "lesson15_start.png")
    print("saved lesson15_start.png")


def routes():
    fig, ax = plt.subplots(figsize=(14, 9.0), dpi=150)
    show_map(ax)
    for (lab, col), (a, z) in zip(SCEN, SCEN_T):
        seg = [r["pose"] for r in RUN["base"] if a <= r["t"] <= z]
        off = {RED: 0.0, BLUE: 0.04, ORANGE: -0.04}[col]
        ax.plot([q[0] + off for q in seg], [q[1] + off for q in seg], color=col, lw=2.4, label=f"{lab}  (sim {z - a:.0f} s)", zorder=4)
    LOC = yaml.safe_load(open("src/warehouse_lecture/worlds/locations.yaml"))["locations"]
    for key in ("pick_table", "place_table"):
        x, y, yaw = LOC[key]["base_goal"]
        ax.add_patch(FancyArrowPatch((x, y), (x + 0.6 * math.cos(yaw), y + 0.6 * math.sin(yaw)), arrowstyle="-|>", mutation_scale=16, color="k", lw=2, zorder=6))
        ax.text(x - 0.2, y + (0.45 if y > 0 else -0.55), f"{LOC[key]['aliases'][0]}", ha="right", fontsize=10,
                bbox=dict(fc="white", ec="none", alpha=0.85), zorder=7)
    p0 = RUN["base"][0]["pose"]
    ax.plot(p0[0], p0[1], "*", color="k", ms=14, zorder=6)
    ax.text(p0[0] + 0.2, p0[1] + 0.2, "출발", fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85))
    ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
    ax.set_title("세 시나리오의 실제 경로 (/ground_truth, 겹치지 않게 4 cm 씩 비켜 그림)", fontsize=12)
    ax.set_xlabel("map x (m)")
    ax.set_ylabel("map y (m)")
    save(fig, "lesson15_routes.png")


def scenes():
    r = L10.renderer()
    pick_view = L10.REAR
    place_view = dict(L10.REAR, lookat=[2.05, 3.45, 0.8])
    items = [(HOLD_T[0] + 0.5, "① 빨강 집기", "픽업 작업대", pick_view), (RELEASE_T[0], "① 빨강 놓기", "적재 작업대", place_view),
             (HOLD_T[1] + 0.5, "② 파랑 집기", "픽업 작업대", pick_view), (RELEASE_T[1], "② 파랑 놓기", "적재 작업대 (빨강 옆)", place_view),
             (HOLD_T[2] + 0.5, "③ 빨강 다시 집기", "적재 작업대", place_view), (RELEASE_T[2], "③ 빨강 되돌림", "픽업 작업대", pick_view)]
    imgs = [caption(r.image(t, **v), a, s) for t, a, s, v in items]
    rows = [hstack(imgs[:3]), hstack(imgs[3:])]
    out = Image.new("RGB", (rows[0].width, rows[0].height * 2 + 16), "white")
    out.paste(rows[0], (0, 0))
    out.paste(rows[1], (0, rows[0].height + 16))
    out.save(OUT / "lesson15_scenes.png")
    print("saved lesson15_scenes.png")


def timeline():
    log = run_log()
    tables = ["빨강·파랑·노랑 = 픽업", "빨강 = 적재", "빨강·파랑 = 적재", "빨강 = 픽업 · 파랑 = 적재"]
    cols = {"navigate": BLUE, "detect": YELLOW, "pick": GREEN, "place": PURPLE}
    fig, ax = plt.subplots(figsize=(14, 4.8), dpi=150)
    for i, sc in enumerate(log):
        y = 2 - i
        bounds = [s[2] for s in sc["steps"]] + [sc["total"]]
        for (n, act, t0, txt), t1 in zip(sc["steps"], bounds[1:]):
            ax.barh(y, t1 - t0, left=t0, color=cols[act], alpha=0.85, edgecolor="white", height=0.55)
            if t1 - t0 > 9:
                ax.text((t0 + t1) / 2, y, f"{n} {act}\n{t1 - t0:.0f} s", ha="center", va="center", fontsize=8.4, color="white", fontweight="bold")
        ax.text(sc["total"] + 3, y, f"{sc['total']:.0f} s", va="center", fontsize=10, fontweight="bold")
        ax.text(-4, y, SCEN[i][0], ha="right", va="center", fontsize=10, color=SCEN[i][1], fontweight="bold")
        ax.text(sc["total"] + 26, y, f"표 → {tables[i + 1]}", va="center", fontsize=9.2, color="#444")
    ax.set_xlim(0, 270)
    ax.set_ylim(-0.6, 2.7)
    ax.set_yticks([])
    ax.set_xlabel("실행 시작부터 (s, 벽시계)")
    ax.set_title(f"단계별 시간 (오늘 실측, 처음 표: {tables[0]})", fontsize=11)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c, alpha=0.85, label=k) for k, c in cols.items()], loc="lower right", ncol=4, fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    save(fig, "lesson15_timeline.png")


if __name__ == "__main__":
    for f in (pipeline, why_table, world_state, roles, scenarios, start_screen, routes, scenes, timeline):
        f()
