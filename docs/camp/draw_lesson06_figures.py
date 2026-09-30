"""Figures for the lesson-06 Confluence page (Nav2 collision avoidance with a walking worker). Output: docs/camp/lesson06_*.png

Run from the workspace root. Data: artifacts/dev/nav_crossing.pkl (close-up crossing run), nav_crossing_wide.pkl,
nav_headon.pkl (docs/camp/nav_record.py) and screenshots in artifacts/dev/avoid_frames/.
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson03_figures import tiles_at  # noqa: E402
from draw_lesson05_figures import FOOT, footprint, show_cost  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

RED, BLUE, GREEN, BROWN, GREY, ORANGE = "#C62828", "#1f4e79", "#2e7d32", "#7a4b00", "#9e9e9e", "#EF6C00"
FR = Path("artifacts/dev/avoid_frames")
PHASES = [(0.0, 6.0, "① 접근", "#E3F2FD"), (6.0, 8.8, "② 감지 · 우회", "#FFF3E0"), (8.8, 10.3, "③ 멈춤 · 대기", "#FFEBEE"), (10.3, 16.0, "④ 재개", "#E8F5E9")]


def load(name):
    d = pickle.load(open(f"artifacts/dev/{name}.pkl", "rb"))
    d["t0"] = d["plans"][0]["t"]
    d["tr"] = np.array(d["truth"]); d["od"] = np.array(d["odom"])
    d["at"] = np.array([t for t, _ in d["actors"]]); d["ap"] = np.array([a["worker_helmet_orange"] for _, a in d["actors"]])
    return d


def at(d, key, t):
    arr = d[key]
    return arr[np.argmin(abs(arr[:, 0] - t))]


def worker(d, t):
    return d["ap"][np.argmin(abs(d["at"] - t))]


# ================================================================ 1. 개념
def scenario():
    d = load("nav_crossing_wide")
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.2), dpi=150)
    for ax, (title, route) in zip(axs, (("crossing (기본): 근로자가 통로를 가로지른다", [(3.4, 3.0), (3.4, -3.0)]),
                                         ("headon: 근로자가 통로를 따라 마주 온다", [(5.5, 0.0), (-5.5, 0.0)]))):
        show_cost(ax, min(d["global_series"], key=lambda g: abs(g["t"] - d["plans"][0]["t"])))
        ax.annotate("", xy=(6.2, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=2.4))
        footprint(ax, 0, 0, 0, fc="#90CAF9", ec=BLUE, lw=1.5)
        ax.add_patch(Circle((6.2, 0), 0.12, fc=BLUE, zorder=6)); ax.text(6.2, 0.35, "목표 (6.2, 0, 0)", color=BLUE, fontsize=9, ha="center")
        (x0, y0), (x1, y1) = route
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="<|-|>", color=ORANGE, lw=2.2, ls="--"))
        ax.add_patch(Circle((x0, y0), 0.22, fc=ORANGE, ec="white", zorder=6))
        ax.text(x0 - 0.3, y0 - 0.6, "근로자 출발\n0.4 m/s 왕복", color=ORANGE, fontsize=9, ha="right", bbox=dict(fc="white", ec="none", alpha=0.85))
        ax.set_xlim(-1.2, 7.4); ax.set_ylim(-3.6, 3.6); ax.set_title(title, fontsize=11)
    fig.suptitle("시나리오 (avoid_scenario.py): 로봇은 원점에서 동쪽 목표로, 근로자는 /warehouse/set_actor 로 경로를 받아 걷는다",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "lesson06_scenario.png")


def flow():
    fig, ax = fig_ax(14, 6.2)
    note(ax, 0.3, 5.9, "움직이는 근로자를 피하는 흐름: 보고 → 칠하고 → 다시 계획하고 → 속도를 고른다", bold=True, fs=12)
    row1 = [("① /scan", ["라이다 360점 · 10 Hz"], C["teal"]), ("② obstacle_layer", ["맞은 칸 = 막힘 (marking)", "지나간 칸 = 비움 (clearing)"], C["orange"]),
            ("③ inflation_layer", ["막힌 칸 둘레 0.55 m", "가까울수록 비쌈"], C["yellow"])]
    for k, (tt, l, fc) in enumerate(row1):
        rbox(ax, 0.3 + k * 3.4, 4.0, 3.0, 1.4, tt, l, fc=fc, tfs=10.5, fs=8.4)
        if k < 2:
            arrow(ax, (3.3 + k * 3.4, 4.7), (3.7 + k * 3.4, 4.7))
    rbox(ax, 3.7, 2.4, 3.6, 0.95, "global costmap", ["map 기준 · 창고 전체 · 2 Hz"], fc=C["grey"], tfs=10, fs=8.2)
    rbox(ax, 8.1, 2.4, 3.6, 0.95, "local costmap", ["odom 기준 · 5 m 창 · 10 Hz"], fc=C["grey"], tfs=10, fs=8.2)
    ax.plot([8.3, 8.3], [4.0, 3.7], color=INK, lw=1.6); ax.plot([5.5, 9.9], [3.7, 3.7], color=INK, lw=1.6)
    arrow(ax, (5.5, 3.7), (5.5, 3.35)); arrow(ax, (9.9, 3.7), (9.9, 3.35))
    rbox(ax, 3.7, 0.7, 3.6, 1.25, "④ Planner (약 1 초마다)", ["새 /plan: 근로자의 지금 자리를 돌아감"], fc=C["purple"], tfs=10, fs=8.2)
    rbox(ax, 8.1, 0.7, 3.6, 1.25, "⑤ Controller DWB (15 Hz)", ["부딪히는 속도 후보는 버림"], fc=C["blue"], tfs=10, fs=8.2)
    rbox(ax, 12.2, 0.7, 1.5, 1.25, "브리지", ["바퀴"], fc=C["teal"], tfs=10, fs=8.2)
    arrow(ax, (5.5, 2.4), (5.5, 1.95)); arrow(ax, (9.9, 2.4), (9.9, 1.95))
    arrow(ax, (7.3, 1.32), (8.1, 1.32)); label(ax, 7.7, 1.62, "/plan", fs=8.4)
    arrow(ax, (11.7, 1.32), (12.2, 1.32)); label(ax, 11.95, 1.62, "/cmd_vel", fs=8.4)
    note(ax, 0.3, 2.9, "매 주기 반복", fs=9.4, color=BROWN, bold=True)
    note(ax, 0.3, 2.45, "근로자의 '속도' 는", fs=9.2)
    note(ax, 0.3, 2.05, "어디에도 없다.", fs=9.2)
    note(ax, 0.3, 1.65, "지금 막힌 칸만 본다.", fs=9.2)
    note(ax, 0.3, 0.3, "Planner 는 global costmap, Controller 는 local costmap 을 본다. 둘 다 같은 /scan 으로 근로자를 칠한다.", fs=9.6)
    save(fig, "lesson06_flow.png")


def mark_clear():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "obstacle_layer: 레이가 멈춘 칸은 칠하고(marking), 레이가 지나간 칸은 지운다(clearing)", bold=True, fs=12)
    ax.set_aspect("equal")
    for k, (title, px) in enumerate((("t: 근로자가 여기 있다", 6), ("t + 1 s: 근로자가 옆으로 갔다", None))):
        x0 = 0.5 + k * 6.9
        n, s = 11, 0.33
        for r in range(n):
            for c in range(n):
                ax.add_patch(Rectangle((x0 + c * s, 0.5 + r * s), s, s, fc="#f4f4f4", ec="#d0d0d0", lw=0.4))
        ox, oy = x0 + 0.5 * s, 0.5 + 5.5 * s
        ax.add_patch(Circle((ox, oy), 0.14, fc=BLUE, zorder=5))
        if px is not None:
            for r in (4, 5, 6):
                ax.add_patch(Rectangle((x0 + px * s, 0.5 + r * s), s, s, fc="#1a1a1a", zorder=3))
            for r, c in ((3, 6), (7, 6), (4, 5), (5, 5), (6, 5), (4, 7), (5, 7), (6, 7)):
                ax.add_patch(Rectangle((x0 + c * s, 0.5 + r * s), s, s, fc="#F48FB1", zorder=2))
            ax.plot([ox, x0 + px * s], [oy, oy], color=RED, lw=1.6, zorder=4)
            label(ax, x0 + px * s + 0.2, 0.5 + 8.4 * s, "marking", color=RED, fs=9)
        else:
            ax.plot([ox, x0 + n * s], [oy, oy], color=GREEN, lw=1.6, zorder=4)
            label(ax, x0 + 7 * s, 0.5 + 6.6 * s, "clearing (raytrace)", color=GREEN, fs=9)
            ax.add_patch(Circle((x0 + 8.5 * s, 0.5 + 1.5 * s), 0.14, fc=ORANGE, zorder=5)); label(ax, x0 + 8.5 * s, 0.5 + 0.4 * s, "근로자", color=ORANGE, fs=8.6)
        note(ax, x0, 4.1, title, bold=True, fs=10.2, color=INK)
    note(ax, 4.6, 1.6, "→", fs=20)
    save(fig, "lesson06_mark_clear.png")


def rviz_displays():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "RViz2 에서 '장애물로 인지했다' 를 보는 법 (navigation.rviz 에 추가한 표시)", bold=True, fs=12)
    tiles(ax, [("Local Costmap", ["/local_costmap/costmap · 로봇 둘레 5 m", "분홍 점 = 장애물 칸 · 하늘색 = 중심이 들어가면 닿는 칸", "빨강→보라 = 부풀린 비용 · 근로자가 보이면 '인지'"], C["teal"]),
               ("Global Costmap", ["/global_costmap/costmap · 창고 전체", "Planner 가 쓰는 지도 · 근로자도 칠해짐", "지나간 자리는 clearing 되기 전까지 남음"], C["grey"]),
               ("Footprint", ["/local_costmap/published_footprint", "빨간 사각형 = 충돌 검사 모양", "이 사각형이 장애물 칸에 닿으면 충돌"], C["red"]),
               ("Global Plan · Local Plan", ["/plan (초록) · /local_plan (노랑)", "근로자를 돌아가는 새 경로", "Controller 가 따라가는 앞부분"], C["green"]),
               ("DWB Trajectories", ["/marker · 컨트롤러가 굴려 본 후보", "로봇 앞의 짧은 화살 다발", "색 = DWB 가 매긴 점수"], C["orange"]),
               ("Lidar", ["/scan · 흰 점", "근로자의 다리 · 몸통에 맞은 점", "costmap 의 원재료"], C["blue"])],
          cols=3, y_top=4.6, gap=0.25, h=2.0, tfs=10.8, fs=8.5)
    save(fig, "lesson06_rviz_displays.png")


# ================================================================ 2. 실측
def rviz_sequence():
    frames = [("crossing_s09.png", "① 접근: 앞에 근로자(오른쪽 위 블롭) · 콘"), ("crossing_s13.png", "② 감지 · 우회: /plan 이 남쪽으로 휘고 로봇이 튼다"),
              ("crossing_s15.png", "③ 멈춤 · 대기: 근로자가 막 앞을 지나간다"), ("crossing_s19.png", "④ 재개: 근로자 뒤로 지나 목표로")]
    fig, axs = plt.subplots(2, 2, figsize=(14, 13.6), dpi=150)
    for ax, (f, t) in zip(axs.flat, frames):
        ax.imshow(Image.open(FR / f).crop((1470, 130, 2230, 866))); ax.axis("off"); ax.set_title(t, fontsize=12)
    fig.suptitle("RViz2 (Global Costmap 끔): Local Costmap · Footprint · Global/Local Plan · DWB Trajectories · Lidar", fontsize=13, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, "lesson06_rviz_sequence.png")


def mujoco_sequence():
    frames = [("crossing_s09.png", "① 접근"), ("crossing_s13.png", "② 감지 · 우회"), ("crossing_s15.png", "③ 멈춤 · 대기"), ("crossing_s19.png", "④ 재개")]
    fig, axs = plt.subplots(1, 4, figsize=(14, 4.4), dpi=150)
    for ax, (f, t) in zip(axs, frames):
        ax.imshow(Image.open(FR / f).crop((380, 330, 1000, 866))); ax.axis("off"); ax.set_title(t, fontsize=11)
    fig.suptitle("같은 순간의 MuJoCo 창 (근로자가 오른쪽에서 통로를 가로지른다)", fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "lesson06_mujoco_sequence.png")


def wide_view():
    fig, ax = plt.subplots(figsize=(14, 7.2), dpi=150)
    ax.imshow(Image.open(FR / "wide_s10.png").crop((1470, 130, 2230, 866))); ax.axis("off")
    ax.set_title("Global Costmap 을 켠 넓은 화면: 근로자 · 콘 · 선반 다리가 모두 막힘으로 칠해지고, 지나간 자리는 옅어진다", fontsize=11.5)
    fig.tight_layout()
    save(fig, "lesson06_rviz_wide.png")


def local_snapshots():
    d = load("nav_crossing")
    picks = [4.5, 7.5, 9.0, 11.5]
    fig, axs = plt.subplots(1, 4, figsize=(14, 4.4), dpi=150)
    for ax, ts, (a, b, name, _) in zip(axs, picks, [PHASES[0], PHASES[1], PHASES[2], PHASES[3]]):
        t = d["t0"] + ts
        g = min(d["local"], key=lambda g: abs(g["t"] - t))
        show_cost(ax, g)
        r = at(d, "tr", g["t"]); w = worker(d, g["t"])
        footprint(ax, r[1], r[2], r[3], fc="none", ec=RED, lw=1.8)
        ax.add_patch(Circle(w, 0.22, fc="none", ec=ORANGE, lw=2.0, ls="--", zorder=6))
        pl = min(d["plans"], key=lambda p: abs(p["t"] - g["t"]))
        ax.plot(pl["xy"][:, 0], pl["xy"][:, 1], color="#2E7D32", lw=1.8)
        lp = min(d["local_plans"], key=lambda p: abs(p["t"] - g["t"]))
        if len(lp["xy"]):
            ax.plot(lp["xy"][:, 0], lp["xy"][:, 1], color="#F9A825", lw=2.4)
        ox, oy = g["origin"]; n = g["data"].shape[0] * g["res"]
        ax.set_xlim(ox, ox + n); ax.set_ylim(oy, oy + n)
        ax.set_title(f"{name}  ({ts:.1f} s)", fontsize=10.5)
    fig.suptitle("실측 local costmap (5 m 창): 빨강 = footprint · 주황 점선 = 근로자 실제 위치 · 초록 = /plan · 노랑 = /local_plan",
                 fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "lesson06_local_snapshots.png")


def timeline():
    d = load("nav_crossing")
    t0 = d["t0"]
    tr, od = d["tr"], d["od"]
    m = (tr[:, 0] >= t0 + 0.1) & (tr[:, 0] <= t0 + 16)
    t = tr[m, 0] - t0
    dist = np.array([np.hypot(*(r[1:3] - worker(d, r[0]))) for r in tr[m]])
    mo = (od[:, 0] >= t0 - 0.5) & (od[:, 0] <= t0 + 16)
    dev = np.array([[p["t"] - t0, p["xy"][:, 1].min()] for p in d["plans"] if p["t"] - t0 <= 16])
    fig, axs = plt.subplots(3, 1, figsize=(14, 7.6), dpi=150, sharex=True)
    for ax in axs:
        for a, b, name, col in PHASES:
            ax.axvspan(a, b, color=col, alpha=0.9, lw=0)
        ax.grid(alpha=0.3)
    for a, b, name, col in PHASES:
        axs[0].text((a + b) / 2, 4.3, name, ha="center", fontsize=10, fontweight="bold")
    axs[0].plot(t, dist, color=ORANGE, lw=2); axs[0].set_ylabel("로봇-근로자 거리 [m]"); axs[0].set_ylim(0, 4.8)
    axs[0].axhline(0.57, color=RED, ls=":", lw=1.2); axs[0].text(0.2, 0.7, "닿는 거리 ≈ 0.57 m (반폭 0.32 + 사람 0.25)", color=RED, fontsize=9)
    i = np.argmin(dist); axs[0].annotate(f"최소 {dist[i]:.2f} m", (t[i], dist[i]), xytext=(t[i] + 1.2, dist[i] + 0.9), fontsize=9.5, arrowprops=dict(arrowstyle="-|>"))
    axs[1].plot(od[mo, 0] - t0, od[mo, 4], color=BLUE, lw=1.8, label="v [m/s]"); axs[1].plot(od[mo, 0] - t0, od[mo, 5], color=BROWN, lw=1.4, label="w [rad/s]")
    axs[1].set_ylabel("/odom 속도"); axs[1].legend(loc="lower left", fontsize=9)
    axs[2].step(dev[:, 0], dev[:, 1], where="post", color=GREEN, lw=2); axs[2].set_ylabel("/plan 의 최소 y [m]")
    axs[2].set_xlabel("목표를 보낸 뒤 시뮬레이션 시각 [s]")
    axs[2].text(6.8, -0.85, "근로자를 남쪽으로 돌아가려다", fontsize=9); axs[2].text(9.0, -0.35, "근로자도 남쪽으로 → 길이 막혀 대기", fontsize=9)
    fig.suptitle("실측 타임라인 (crossing): 거리 · 속도 · 경로가 휘는 정도", fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save(fig, "lesson06_timeline.png")


def paths():
    d = load("nav_crossing")
    t0 = d["t0"]
    fig, ax = plt.subplots(figsize=(14, 6.6), dpi=150)
    show_cost(ax, min(d["global_series"], key=lambda g: abs(g["t"] - t0)))     # before the worker reaches the aisle
    cm = plt.cm.viridis
    for p in d["plans"]:
        s = p["t"] - t0
        if 5.5 <= s <= 12:
            ax.plot(p["xy"][:, 0], p["xy"][:, 1], color=cm((s - 5.5) / 6.5), lw=1.2, alpha=0.9)
    tr = d["tr"]; m = (tr[:, 0] >= t0) & (tr[:, 0] <= t0 + 30)
    ax.plot(tr[m, 1], tr[m, 2], color=RED, lw=2.4, label="로봇이 실제로 간 길")
    ma = (d["at"] >= t0) & (d["at"] <= t0 + 14)
    ax.plot(d["ap"][ma, 0], d["ap"][ma, 1], color=ORANGE, lw=2.4, ls="--", label="근로자 (0 ~ 14 s)")
    for k, s in enumerate((4.5, 7.5, 9.0, 11.5)):
        r = at(d, "tr", t0 + s); w = worker(d, t0 + s); tag = "①②③④"[k]
        footprint(ax, r[1], r[2], r[3], fc="none", ec=RED, lw=1.0)
        ax.add_patch(Circle(w, 0.13, fc=ORANGE, ec="white", alpha=0.9, zorder=6)); ax.text(w[0] + 0.2, w[1] - 0.08, f"{tag} {s:.1f} s", fontsize=9, color=BROWN, zorder=7)
    ax.set_xlim(-0.8, 6.8); ax.set_ylim(-3.2, 3.2)
    sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(5.5, 12)); cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01); cb.set_label("/plan 시각 [s]")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("위에서 본 궤적: /plan 은 근로자의 '지금' 자리를 피해 매번 새로 그려진다 (색 = 시각, 빨간 사각형 = ①~④ 시각의 로봇)", fontsize=11)
    fig.tight_layout()
    save(fig, "lesson06_paths.png")


def headon():
    d = load("nav_headon")
    t0 = d["t0"]
    tr = d["tr"]
    m = (tr[:, 0] >= t0 - 0.5) & (tr[:, 0] <= t0 + 14)
    t = tr[m, 0] - t0
    dist = np.array([np.hypot(*(r[1:3] - worker(d, r[0]))) for r in tr[m]])
    fig = plt.figure(figsize=(14, 5.2), dpi=150)
    ax = fig.add_axes([0.04, 0.12, 0.44, 0.78])
    show_cost(ax, d["global_costmap"])
    ax.plot(tr[m, 1], tr[m, 2], color=RED, lw=2.4, label="로봇")
    ma = (d["at"] >= t0) & (d["at"] <= t0 + 14)
    ax.plot(d["ap"][ma, 0], d["ap"][ma, 1] + 0.03, color=ORANGE, lw=2.4, ls="--", label="근로자")
    i = np.argmin(dist); r = tr[m][i]; w = worker(d, r[0])
    footprint(ax, r[1], r[2], r[3], fc="none", ec=RED, lw=1.8); ax.add_patch(Circle(w, 0.22, fc=ORANGE, ec="white", zorder=6))
    ax.set_xlim(-0.5, 6.8); ax.set_ylim(-2.2, 2.2); ax.legend(loc="upper left", fontsize=9)
    ax.set_title(f"가장 가까울 때 ({t[i]:.1f} s): 중심 거리 {dist[i]:.2f} m → footprint 와 겹친다", fontsize=10.5)
    bx = fig.add_axes([0.52, 0.12, 0.46, 0.78])
    bx.plot(t, dist, color=ORANGE, lw=2); bx.axhline(0.57, color=RED, ls=":", lw=1.2); bx.grid(alpha=0.3)
    bx.set_xlabel("목표를 보낸 뒤 시각 [s]"); bx.set_ylabel("로봇-근로자 거리 [m]")
    bx.text(0.3, 0.7, "닿는 거리 ≈ 0.57 m", color=RED, fontsize=9)
    bx.set_title("다가오는 속도 = 0.3 + 0.4 = 0.7 m/s: 방향을 튼 것이 너무 늦었다", fontsize=10.5)
    fig.suptitle("headon: 마주 오는 근로자는 제때 피하지 못했다 (근로자는 모형이라 로봇을 통과해 지나감)", fontsize=12, fontweight="bold", x=0.01, ha="left")
    save(fig, "lesson06_headon.png")


def headon_mujoco():
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), dpi=150)
    for ax, f, t in zip(axs, ("headon_s08.png", "headon_s09.png", "headon_s10.png"), ("다가온다", "겹친다 (충돌)", "지나간 뒤 비켜 선 로봇")):
        ax.imshow(Image.open(FR / f).crop((380, 330, 1000, 866))); ax.axis("off"); ax.set_title(t, fontsize=11)
    fig.suptitle("같은 순간의 MuJoCo 창 (headon)", fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "lesson06_headon_mujoco.png")


def why_late():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "왜 마주 오는 사람은 늦게 피하나: Nav2 기본 구성은 '지금 막힌 칸' 만 본다", bold=True, fs=12)
    tiles(ax, [("속도 예측 없음", ["costmap 에는 위치만 있고 속도가 없다", "Planner 는 사람이 '지금' 있는 자리를 피한다", "사람이 다가오면 그 자리가 계속 다가온다"], C["red"]),
               ("가까워져야 반응", ["DWB 는 1.7 s 앞만 굴려 본다 (0.5 m 남짓)", "inflation 0.55 m 안에 들어와야 비싸진다", "마주 오면 1.5 m 에서 반응 → 이미 늦음"], C["orange"]),
               ("가로지르면 괜찮았다", ["사람이 옆으로 빠져 나가 자리가 비워진다", "로봇은 멈춰 기다렸다가 뒤로 지나감", "최소 거리 1.16 m"], C["green"])],
          cols=3, y_top=3.9, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 1.2, "보완: 속도 낮추기 · inflation 키우기 · Collision Monitor (가까우면 강제 감속/정지) · 사람 추적 + 예측 레이어 · MPPI 컨트롤러.", fs=9.6)
    note(ax, 0.3, 0.6, "실제 현장 로봇은 여기에 안전 인증 센서(안전 스캐너)의 보호 영역을 따로 둔다.", fs=9.6)
    save(fig, "lesson06_why_late.png")


# ================================================================ 3. 설정
def params():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "회피에 관여하는 파라미터 (nav2.yaml)", bold=True, fs=12)
    tiles(ax, [("obstacle_layer.scan", ["marking · clearing: true", "obstacle_max_range: 19.5", "raytrace_max_range: 20.0", "max_obstacle_height: 2.5"], C["orange"]),
               ("inflation_layer", ["inflation_radius: 0.55", "cost_scaling_factor: 3.0", "footprint 0.76 × 0.64 m", "footprint_padding: 0.03"], C["yellow"]),
               ("local_costmap", ["update_frequency: 10.0", "publish_frequency: 5.0", "5 m × 5 m · rolling_window", "global_frame: odom"], C["grey"]),
               ("controller (DWB)", ["controller_frequency: 15.0", "sim_time: 1.7", "ObstacleFootprint critic", "max_vel_x: 0.3"], C["blue"])],
          cols=4, y_top=4.1, gap=0.25, h=2.55, tfs=10.8, fs=8.5)
    note(ax, 0.3, 0.9, "global_costmap 도 같은 obstacle_layer 를 가진다 → Planner 가 근로자를 돌아가는 경로를 그릴 수 있다.", fs=9.6)
    note(ax, 0.3, 0.4, "파일: src/mobile_openarm_navigation/config/nav2.yaml · 표시: config/navigation.rviz", fs=9.6)
    save(fig, "lesson06_params.png")


if __name__ == "__main__":
    for f in (scenario, flow, mark_clear, rviz_displays, rviz_sequence, mujoco_sequence, wide_view, local_snapshots, timeline, paths, headon, headon_mujoco, why_late, params):
        f()
