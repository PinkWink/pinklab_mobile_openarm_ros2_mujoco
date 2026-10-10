"""Figures for the lesson-11 Confluence page (Navigation + Pick & Place). Output: docs/camp/lesson11_*.png

Run from the workspace root (ros env sourced, workspace venv, offscreen EGL):
    MUJOCO_GL=egl python docs/camp/draw_lesson11_figures.py
Data (2026-10-10, `start camera_depth:=true locate:=vision`, ArucoDetector + YoloDetector3D, spawn at the centre):
  artifacts/dev/transport_red.pkl        docs/camp/pick_record.py during `transport.py red` (then part of `transport.py blue`)
  artifacts/dev/transport_red_fail1.pkl  same, first attempt: place dock stalled (stale marker frame after the side-step)
  artifacts/dev/l11_transport_*.log      transport.py output (red, blue, yellow)
  artifacts/dev/lesson11_shots/start_mj.png  MuJoCo viewer at start
Robot views are offscreen MuJoCo renders of the recorded state (base pose, parcels, joints).
"""
import math
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson08_figures import caption, hstack  # noqa: E402
from draw_lesson10_figures import Render  # noqa: E402
import draw_lesson10_figures as L10  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image  # noqa: E402

SHOTS = Path("artifacts/dev/lesson11_shots")
OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE, PURPLE = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100", "#6A1B9A"
RUN = pickle.load(open("artifacts/dev/transport_red.pkl", "rb"))
FAIL = pickle.load(open("artifacts/dev/transport_red_fail1.pkl", "rb"))
FB = RUN["feedback"]
L10.RUN = RUN                       # Render.set() reads the module-level RUN


def event(prefix, after=0.0, fb=FB):
    return next(f["t"] for f in fb if f["detail"].startswith(prefix) and f["t"] >= after)


T_START = event("parcel_1 sits")
T_ARRIVE1 = event("arrived at pre-dock")
T_DOCK1 = event("visual servo")
T_DOCKED1 = event("docked:")
T_HOLD = event("holding at")
T_CARRY = event("hands_up pose")
T_NAV2 = event("Nav2 to place_table")
T_ARRIVE2 = event("arrived at pre-dock", T_NAV2)
T_DOCK2 = event("visual servo", T_NAV2)
T_DOCKED2 = event("docked:", T_NAV2)
T_RELEASED = event("released")
T_RETREAT = event("back to transport")
T_NEXT = [f["t"] for f in FB if f["phase"] == "start"][1]          # transport.py blue starts here
T_END = max(r["t"] for r in RUN["cmd"] if r["t"] < T_NEXT and abs(r["vx"]) > 1e-3) + 1.0
LOC = yaml.safe_load(open("src/warehouse_lecture/worlds/locations.yaml"))["locations"]


def near(rows, t):
    return min(rows, key=lambda r: abs(r["t"] - t))


def window(rows, a, b):
    return [r for r in rows if a <= r["t"] <= b]


def yaw_of(p):
    return math.atan2(2 * (p[6] * p[5] + p[3] * p[4]), 1 - 2 * (p[4] ** 2 + p[5] ** 2))


def load_map():
    m = yaml.safe_load(open("src/mobile_openarm_navigation/maps/warehouse.yaml"))
    img = np.array(Image.open("src/mobile_openarm_navigation/maps/" + m["image"]))
    h, w = img.shape
    ext = [m["origin"][0], m["origin"][0] + w * m["resolution"], m["origin"][1], m["origin"][1] + h * m["resolution"]]
    return img, ext


def show_map(ax):
    img, ext = load_map()
    ax.imshow(img, cmap="gray", extent=ext, vmin=0, vmax=255, interpolation="nearest")
    ax.set_aspect("equal")


SEGMENTS = [("navigate_pick (Nav2)", T_START, T_DOCK1, BLUE), ("dock · 잡기", T_DOCK1, T_CARRY, ORANGE),
            ("carry · 후진", T_CARRY, T_NAV2, PURPLE), ("navigate_place (Nav2)", T_NAV2, T_DOCK2, GREEN),
            ("dock · 놓기 · retreat", T_DOCK2, T_END, RED)]


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "⑨ 는 한 작업대 앞에서 집고 놓았다 → ⑩ 은 창고를 가로질러 다른 작업대에 놓는다", bold=True, fs=12)
    tiles(ax, [("⑨ Pick & Place", ["spawn:=pick_table (작업대 앞에서 시작)", "pick 절반 + place 절반 = 같은 작업대", "주행 0.8 m (도킹 · 후진만)"], C["grey"]),
               ("⑩ Navigation + Pick & Place", ["창고 가운데 (0, 0) 에서 시작", "pick_table → place_table (y 7.2 m 차이)", "한 goal (phase=all) · 주행 약 15 m"], C["blue"]),
               ("새로 보는 것", ["Nav2 는 사전 도킹 지점까지만", "상자를 든 채 주행 (hands_up)", "역할 분담: Nav2 · 마커 · 카메라 · MoveIt"], C["green"])],
          cols=3, y_top=3.6, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 0.9, "예제: lessons/07_nav_pick_place/transport.py  →  액션 /pick_place (phase=all, from pick_table, to place_table)", fs=9.8)
    save(fig, "lesson11_why.png")


def state_machine():
    fig, ax = fig_ax(14, 6.0)
    note(ax, 0.3, 5.75, "한 goal 안의 상태 기계  (색 = 그 단계를 맡는 것)", bold=True, fs=12)
    pal = {"Nav2": C["blue"], "마커": C["teal"], "카메라": C["yellow"], "MoveIt": C["green"]}
    chain(ax, [("navigate_pick", ["Nav2", "(1.20, -3.60)"]), ("dock", ["ArUco 0 · 1", "시각 서보"]), ("locate", ["카메라", "parcel_red"]),
               ("pre_grasp · grasp", ["MoveIt", "+ 그리퍼"]), ("lift · carry", ["MoveIt hands_up", "0.75 m 후진"])],
          y=3.5, h=1.6, tfs=10, fs=8.6, colors=[pal["Nav2"], pal["마커"], pal["카메라"], pal["MoveIt"], pal["MoveIt"]])
    arrow(ax, (13.4, 3.5), (13.4, 2.75))
    spans = chain(ax, [("retreat", ["14 cm 뒤", "transport · 후진"]), ("place", ["빈 슬롯", "내리기 · 열기"]), ("dock", ["ArUco 2 · 3", "시각 서보"]),
                       ("navigate_place", ["Nav2", "(1.20, +3.60)"])],
                  y=1.1, h=1.6, tfs=10, fs=8.6, x0=2.95, colors=[pal["MoveIt"], pal["MoveIt"], pal["마커"], pal["Nav2"]], arrows=False)
    for i in range(3):
        arrow(ax, (spans[i + 1][0], 1.9), (spans[i][1], 1.9))
    for i, (k, fc) in enumerate(pal.items()):
        ax.add_patch(Rectangle((0.3 + i * 1.6, 0.25), 0.35, 0.35, fc=fc, ec=INK, lw=0.8))
        ax.text(0.75 + i * 1.6, 0.42, k, va="center", fontsize=9.5)
    note(ax, 0.3, 2.3, "실패하면 그 단계에서 멈추고\nrecover() 가 든 상자를 놓는다", fs=9.2)
    save(fig, "lesson11_states.png")


def roles():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "정밀도는 누가 책임지나", bold=True, fs=12)
    tiles(ax, [("Nav2 (창고 전체)", ["AMCL 위치로 경로 · 속도", "목표 허용 오차 xy 0.08 m · yaw 0.15 rad", "→ 사전 도킹 지점까지만"], C["blue"]),
               ("ArUco 도킹 (마지막 0.5 m)", ["작업대 마커를 직접 본다", "옆 오차가 크면 side-step", "→ 잔차 1 cm 안팎"], C["teal"]),
               ("카메라 + MoveIt (손)", ["도킹 뒤 상자 위치를 다시 잰다", "같은 TF 로 되돌려 AMCL 오차 상쇄", "→ 놓은 위치 오차 1 ~ 5 cm (실측 3 회)"], C["green"])],
          cols=3, y_top=3.9, gap=0.3, h=2.2, tfs=11, fs=9)
    note(ax, 0.3, 1.2, "Nav2 의 8 cm 를 그대로 믿고 팔을 뻗지 않는다: 위치를 '가까이 갈수록 더 정확한 센서' 로 다시 잰다.", fs=9.8)
    save(fig, "lesson11_roles.png")


def latency():
    """First attempt: place-side side-step ended at -25 deg, but a pair fix captured mid-turn said -0.6 deg."""
    fb = FAIL["feedback"]
    t_step = event("side-step", event("Nav2 to place_table", fb=fb), fb=fb)
    t_dock = event("visual servo", t_step, fb=fb)
    b = window(FAIL["base"], t_step - 3, t_dock + 25)
    t = np.array([r["t"] for r in b]) - t_step
    yaw = np.degrees([yaw_of(r["pose"]) for r in b])
    fig, axes = plt.subplots(2, 1, figsize=(14, 6.2), dpi=150, sharex=True, gridspec_kw=dict(height_ratios=[3, 1.3]))
    ax = axes[0]
    ax.plot(t, yaw, color=BLUE, lw=2, label="실제 heading (/ground_truth)")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.plot(t_dock - t_step, -0.6, "o", color=ORANGE, ms=9, label="서버가 받은 마커 쌍: turn -0.6° (정렬됐다고 판단)")
    ax.annotate("실제는 -25° → 마커 3 이 화면 밖", (t_dock - t_step, -25), xytext=(t_dock - t_step + 6, -12), fontsize=10, color=RED,
                arrowprops=dict(arrowstyle="->", color=RED))
    k = int(np.argmax(yaw))
    turned = yaw[k] - min(yaw[:k])
    ax.annotate(f"side-step 의 90° 회전이 {turned:.0f}° 에서 끝남\n(turn() 이 벽시계 9.3 s 제한에 걸림: sim 이 실시간의 0.72 배)", (t[k], yaw[k]), xytext=(13, 40),
                fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="->", color=GREY))
    ax.set_ylabel("heading (deg)")
    ax.set_title("첫 시도: side-step 직후 도킹이 180 s 동안 멈춘 이유 (실측)", fontsize=12)
    ax.legend(loc="upper right", fontsize=9.5)
    ax.grid(alpha=0.3)
    ax = axes[1]
    for r in window(FAIL["markers"], t_step - 3, t_dock + 25):
        ids = sorted(i["id"] for i in r["items"] if i["id"] in (2, 3))
        if ids:
            ax.plot(r["t"] - t_step, 0, "s", color=GREEN if len(ids) == 2 else ORANGE, ms=8)
            ax.text(r["t"] - t_step, 0.35, "2·3" if len(ids) == 2 else str(ids[0]), ha="center", fontsize=8.5)
    ax.set_ylim(-0.6, 0.9)
    ax.set_yticks([])
    ax.set_xlabel("s (side-step 시작 기준 sim 시각)  ·  아래 점 = 카메라가 찍은 시각에 보인 마커")
    ax.grid(alpha=0.3)
    save(fig, "lesson11_latency.png")


def latency_fix():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 0.35, "또 하나: turn() · drive() 의 제한 시간을 벽시계 → sim 시간으로.  고친 뒤 (sim 0.74 배): 90° 명령 → 실제 91.3° · 오도메트리 91.4°", fs=9.8, color=INK)
    note(ax, 0.3, 4.15, "고친 것: '받은 시각' 이 아니라 '찍힌 시각' 으로 새 영상인지 판단", bold=True, fs=12)
    rbox(ax, 0.3, 1.2, 4.2, 2.4, "전 (nav_client.marker)", ["0.7 s 안에 '도착' 한 메시지면 사용", "이 PC: 찍고 나서 ~2.6 s 뒤 도착", "→ 회전 중 영상을 정지 뒤 값으로 착각"], fc=C["red"], align="left", fs=9.2, dy=0.45)
    rbox(ax, 4.9, 1.2, 4.2, 2.4, "후 (wait_markers)", ["멈춘 시각 since 를 기억", "header.stamp ≥ since 인 영상만", "회전 중 찾았으면 멈추고 다시 잰다"], fc=C["green"], align="left", fs=9.2, dy=0.45)
    rbox(ax, 9.5, 1.2, 4.2, 2.4, "같은 원리 (⑨)", ["VisionLocator.relative 도", "부른 뒤 찍힌 검출만 사용", "→ 도킹 직후 locate 실패 해결"], fc=C["yellow"], align="left", fs=9.2, dy=0.45)
    arrow(ax, (4.5, 2.4), (4.9, 2.4))
    save(fig, "lesson11_latency_fix.png")


# ================================================================ 2. 실행
def start_screen():
    Image.open(SHOTS / "start_mj.png").convert("RGB").crop((275, 0, 2025, 960)).save(OUT / "lesson11_run_result.png")
    print("saved lesson11_run_result.png")


def route_map():
    fig, ax = plt.subplots(figsize=(14, 9.5), dpi=150)
    show_map(ax)
    b = window(RUN["base"], T_START - 1, T_END)
    for lab, a, z, col in SEGMENTS:
        seg = [r["pose"] for r in b if a <= r["t"] <= z]
        ax.plot([p[0] for p in seg], [p[1] for p in seg], color=col, lw=2.6, label=lab, zorder=4)
    for t0 in (T_START, T_NAV2):
        plan = next(p for p in RUN["plans"] if p["t"] >= t0)
        ax.plot([q[0] for q in plan["xy"]], [q[1] for q in plan["xy"]], ls="--", color="#555", lw=1.2, zorder=3)
    ax.plot([], [], ls="--", color="#555", label="Nav2 첫 /plan")
    for key in ("pick_table", "place_table"):
        x, y, yaw = LOC[key]["base_goal"]
        ax.add_patch(FancyArrowPatch((x, y), (x + 0.6 * math.cos(yaw), y + 0.6 * math.sin(yaw)), arrowstyle="-|>", mutation_scale=16, color="k", lw=2, zorder=6))
        ax.plot(x, y, "o", color="k", ms=6, zorder=6)
        ax.text(x - 0.2, y + (0.45 if y > 0 else -0.55), f"{LOC[key]['aliases'][0]}\n사전 도킹 ({x:.1f}, {y:+.1f})", ha="right", fontsize=9.5,
                bbox=dict(fc="white", ec="none", alpha=0.85), zorder=7)
    ax.plot(0, 0, "*", color="k", ms=14, zorder=6)
    ax.text(0.2, 0.2, "출발 (0, 0)", fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85))
    ax.legend(loc="upper left", fontsize=9.5, framealpha=0.95)
    ax.set_title("빨간 상자 운반: 실제 경로 (/ground_truth) 와 Nav2 계획 (/plan)", fontsize=12)
    ax.set_xlabel("map x (m)")
    ax.set_ylabel("map y (m)")
    save(fig, "lesson11_route.png")


def arrival_zoom():
    """Place table: Nav2 arrival vs goal tolerance, side-step, docked pose (truth)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), dpi=150)
    for ax, (key, t_arr, t_dock, t_docked, title) in zip(axes, (("pick_table", T_ARRIVE1, T_DOCK1, T_DOCKED1, "픽업 작업대"),
                                                                 ("place_table", T_ARRIVE2, T_DOCK2, T_DOCKED2, "적재 작업대"))):
        gx, gy, _ = LOC[key]["base_goal"]
        ax.add_patch(Circle((gx, gy), 0.08, fill=False, ec=BLUE, ls="--", lw=1.5))
        ax.plot(gx, gy, "+", color=BLUE, ms=12, mew=2)
        seg = window(RUN["base"], t_arr - 4, t_docked + 0.5)
        ax.plot([r["pose"][0] for r in seg], [r["pose"][1] for r in seg], color=GREY, lw=1.5)
        for t, col, txt in ((t_arr, BLUE, "Nav2 도착"), (t_dock, ORANGE, "side-step 뒤 (도킹 시작)"), (t_docked, GREEN, "도킹 끝")):
            p = near(RUN["base"], t)["pose"]
            yw = yaw_of(p)
            ax.add_patch(FancyArrowPatch((p[0], p[1]), (p[0] + 0.06 * math.cos(yw), p[1] + 0.06 * math.sin(yw)), arrowstyle="-|>", mutation_scale=12, color=col, lw=2))
            ax.plot(p[0], p[1], "o", color=col, ms=7, label=f"{txt}: ({p[0]:.3f}, {p[1]:+.3f}) {math.degrees(yw):+.1f}°")
        ax.axhline(gy, color=GREY, ls=":", lw=1)
        ax.set_xlim(gx - 0.15, gx + 0.6)
        ax.set_ylim(gy - 0.2, gy + 0.2)
        ax.set_aspect("equal")
        pa = near(RUN["base"], t_arr)["pose"]
        ax.set_title(f"{title}: Nav2 도착 때 실제 거리 {math.hypot(pa[0] - gx, pa[1] - gy) * 100:.0f} cm (원 = 허용 8 cm, AMCL 기준)", fontsize=10.5)
        ax.legend(loc="lower right", fontsize=8.6)
        ax.grid(alpha=0.3)
        ax.set_xlabel("map x (m)")
    axes[0].set_ylabel("map y (m)")
    save(fig, "lesson11_arrival.png")


def scenes():
    r = Render(560, 420)

    def chase(t, dist=2.4, el=-24, side=25):
        p = near(RUN["base"], t)["pose"]
        return dict(lookat=[p[0] + 0.4 * math.cos(yaw_of(p)), p[1] + 0.4 * math.sin(yaw_of(p)), 0.6], distance=dist,
                    azimuth=math.degrees(yaw_of(p)) + side, elevation=el)

    items = [(T_START + 1, "① 출발 (0, 0)", "transport 자세", chase(T_START + 1, 3.2, -30)),
             (T_HOLD + 0.5, "② 픽업 작업대: 잡기", f"sim {T_HOLD - T_START:.0f} s", L10.REAR),
             ((T_NAV2 + T_ARRIVE2) / 2, "③ 상자를 든 채 주행", "hands_up 자세", chase((T_NAV2 + T_ARRIVE2) / 2, 2.6, -22, 35)),
             (T_DOCKED2, "④ 적재 작업대: 도킹 끝", f"sim {T_DOCKED2 - T_START:.0f} s", chase(T_DOCKED2, 2.2, -26, 30)),
             (T_RELEASED, "⑤ 놓기", "그리퍼 열기", dict(L10.REAR, lookat=[2.05, 3.45, 0.8])),
             (T_END, "⑥ 끝", f"sim {T_END - T_START:.0f} s", chase(T_END, 2.6, -26, 30))]
    imgs = [caption(r.image(t, **v), a, s) for t, a, s, v in items]
    rows = [hstack(imgs[:3]), hstack(imgs[3:])]
    out = Image.new("RGB", (rows[0].width, rows[0].height * 2 + 16), "white")
    out.paste(rows[0], (0, 0))
    out.paste(rows[1], (0, rows[0].height + 16))
    out.save(OUT / "lesson11_scenes.png")
    print("saved lesson11_scenes.png")


def speed():
    b = window(RUN["base"], T_START - 1, T_END)
    t = np.array([r["t"] for r in b])
    xy = np.array([r["pose"][:2] for r in b])
    k = 25                                            # 0.5 s at 50 Hz
    v = np.hypot(*(xy[k:] - xy[:-k]).T) / (t[k:] - t[:-k])
    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=150)
    for lab, a, z, col in SEGMENTS:
        ax.axvspan(a - T_START, z - T_START, color=col, alpha=0.13)
        ax.text((a + z) / 2 - T_START, 0.335, lab.split(" (")[0], ha="center", fontsize=8.8, color=col)
    ax.plot(t[k // 2:-k // 2] - T_START, v, color=INK, lw=1.4)
    ax.axhline(0.3, color=GREY, ls=":", lw=1)
    ax.text(1, 0.305, "max_vel_x 0.3", fontsize=8.5, color="#666")
    ax.set_ylim(0, 0.36)
    ax.set_xlim(0, T_END - T_START)
    ax.set_xlabel("s (goal 시작 기준 sim 시각)")
    ax.set_ylabel("base 속도 (m/s)")
    ax.set_title("주행 속도 (/ground_truth 미분, 실측)", fontsize=12)
    ax.grid(alpha=0.3)
    save(fig, "lesson11_speed.png")


def timeline():
    rows = {"빨강 (오른팔)": [("navigate_pick", 57.8), ("dock", 24.0), ("locate", 0.1), ("pre_grasp", 9.1), ("grasp", 5.1), ("lift", 5.3), ("carry", 22.3),
                          ("navigate_place", 76.1), ("dock", 16.2), ("place", 17.7), ("retreat", 22.4)],
            "파랑 (왼팔)": [("navigate_pick", 97.5), ("dock", 16.0), ("locate", 0.1), ("pre_grasp", 11.9), ("grasp", 5.2), ("lift", 5.1), ("carry", 25.5),
                         ("navigate_place", 80.7), ("dock", 16.4), ("place", 17.5), ("retreat", 22.4)],
            "노랑 (왼팔)": [("navigate_pick", 46.3), ("dock", 21.2), ("locate", 0.0), ("pre_grasp", 8.1), ("grasp", 4.8), ("lift", 9.5), ("carry", 20.7),
                         ("navigate_place", 84.9), ("dock", 13.0), ("place", 22.3), ("retreat", 27.0)]}
    result = {"빨강 (오른팔)": "256 s · 슬롯 1.1 cm", "파랑 (왼팔)": "298 s · 슬롯 4.6 cm", "노랑 (왼팔)": "258 s · 슬롯 1.8 cm"}
    start = {"빨강 (오른팔)": "출발 (0, 0)", "파랑 (왼팔)": "출발: 적재대 앞", "노랑 (왼팔)": "출발: 적재대 앞"}
    cols = {"navigate_pick": C["blue"], "navigate_place": C["blue"], "dock": C["teal"], "locate": C["yellow"], "pre_grasp": C["green"],
            "grasp": "#C8E6C9", "lift": "#A5D6A7", "carry": C["purple"], "place": C["green"], "retreat": C["purple"]}
    fig, ax = plt.subplots(figsize=(14, 4.6), dpi=150)
    for i, (name, items) in enumerate(rows.items()):
        y, x = 2 - i, 0.0
        for lab, d in items:
            ax.barh(y, d, left=x, color=cols[lab], ec=INK, lw=0.7, height=0.6)
            if d > 14:
                ax.text(x + d / 2, y, f"{lab}\n{d:.0f}", ha="center", va="center", fontsize=8.2)
            x += d
        ax.text(x + 3, y, f"{result[name]}\n{start[name]}", va="center", fontsize=9.2)
    ax.set_yticks([2, 1, 0], list(rows))
    ax.set_xlim(0, 380)
    ax.set_xlabel("벽시계 s (transport.py 출력)")
    ax.set_title("세 색 운반: 단계별 시간 (실측)", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    save(fig, "lesson11_timeline.png")


# ================================================================ 3. 코드
def params():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "이 페이지에서 쓰는 설정", bold=True, fs=12)
    tiles(ax, [("locations.yaml", ["pick_table base_goal [1.2, -3.6, 0.0]", "place_table base_goal [1.2, 3.6, 0.0]", "aliases: 픽업 작업대 · 적재 작업대"], C["blue"]),
               ("nav2.yaml", ["xy_goal_tolerance 0.08", "yaw_goal_tolerance 0.15", "max_vel_x 0.3 · inflation 0.55"], C["grey"]),
               ("skills.yaml", ["dock.max_lateral_error 0.05", "dock.timeout_s 180 · undock 0.75", "carry_pose hands_up"], C["green"])],
          cols=3, y_top=3.9, gap=0.3, h=2.4, tfs=11, fs=9)
    save(fig, "lesson11_params.png")


if __name__ == "__main__":
    for f in (why, state_machine, roles, latency, latency_fix, start_screen, route_map, arrival_zoom, scenes, speed, timeline, params):
        f()
