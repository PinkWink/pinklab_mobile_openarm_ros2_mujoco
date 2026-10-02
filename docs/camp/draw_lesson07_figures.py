"""Figures for the lesson-07 Confluence page (Day-1 integrated demo: patrol + web dashboard). Output: docs/camp/lesson07_*.png

Run from the workspace root. Data (2026-10-02 runs):
  artifacts/dev/patrol_run.pkl          nav_record.py during `patrol.py` on my_warehouse map (148 s, 5 stops)
  artifacts/dev/patrol_frames/          MuJoCo + RViz screenshots every 4 s, patrol_run.log
  artifacts/dev/dash_frames/            dashboard screenshots (headless Chrome via DevTools) every 3.3 s + done.png
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson03_figures import tiles_at  # noqa: E402
from draw_lesson05_figures import footprint, segments, show_cost  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = Path("docs/camp")
RED, BLUE, GREEN, BROWN, GREY, ORANGE = "#C62828", "#1f4e79", "#2e7d32", "#7a4b00", "#9e9e9e", "#EF6C00"
LEG_COL = ["#1565C0", "#2E7D32", "#EF6C00", "#6A1B9A", "#C62828"]
PF, DF = Path("artifacts/dev/patrol_frames"), Path("artifacts/dev/dash_frames")
ROUTE = ["pick_table", "rack_a", "rack_b", "place_table", "center_aisle"]
LOC = yaml.safe_load(open("src/warehouse_lecture/worlds/locations.yaml"))["locations"]
NAMES = {n: LOC[n]["aliases"][0] for n in ROUTE}
# patrol.py output of the recorded run (artifacts/dev/patrol_frames/patrol_run.log)
RUN = {"time": [20.0, 38.0, 31.0, 33.9, 21.6], "amcl": [0.036, 0.031, 0.004, 0.028, 0.036], "odom": [0.002, 0.011, 0.012, 0.015, 0.008]}


def load_map():
    m = yaml.safe_load(open("artifacts/maps/my_warehouse.yaml"))
    img = np.array(Image.open("artifacts/maps/" + m["image"]))
    h, w = img.shape
    ext = [m["origin"][0], m["origin"][0] + w * m["resolution"], m["origin"][1], m["origin"][1] + h * m["resolution"]]
    return img, ext


def show_map(ax, alpha=1.0):
    img, ext = load_map()
    ax.imshow(img, cmap="gray", extent=ext, vmin=0, vmax=255, alpha=alpha, interpolation="nearest")
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def stop_marker(ax, k, x, y, yaw, color):
    ax.add_patch(Circle((x, y), 0.32, fc=color, ec="white", lw=1.5, zorder=6))
    ax.text(x, y, str(k), ha="center", va="center", color="white", fontsize=11, fontweight="bold", zorder=7)
    ax.add_patch(FancyArrowPatch((x, y), (x + 0.75 * np.cos(yaw), y + 0.75 * np.sin(yaw)), arrowstyle="-|>", mutation_scale=14, color=color, lw=2, zorder=5))


# ================================================================ 1. 순찰 Demo
def why():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "전반부(Day 1) 에서 만든 것을 한 번에 돌린다", bold=True, fs=12)
    chain(ax, [("① 브리지", ["MuJoCo ↔ ROS 2", "/clock · /tf · /scan"]), ("③ 로봇 모델", ["URDF → MJCF", "robot_state_publisher"]),
               ("④ 센서 · Odom", ["/scan · /odom", "바퀴로 위치 적분"]), ("⑤ SLAM", ["내 지도", "my_warehouse.yaml"]),
               ("⑥ Nav2", ["AMCL · Planner", "Controller · BT"]), ("순찰", ["5 곳을 차례로", "patrol.py"])],
          y=1.6, h=1.5, gap=0.28, colors=[C["teal"], C["purple"], C["grey"], C["orange"], C["blue"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.75, "새로 만드는 코드는 순찰 노드 하나 (patrol.py) · 나머지는 지금까지의 패키지와 ⑤ 에서 저장한 지도를 그대로 쓴다.", fs=9.8)
    save(fig, "lesson07_why.png")


def route():
    fig, ax = plt.subplots(figsize=(12, 8.0), dpi=150)
    show_map(ax)
    pts = [(0.0, 0.0)] + [tuple(LOC[n]["base_goal"][:2]) for n in ROUTE]
    for k in range(5):
        a, b = pts[k], pts[k + 1]
        ax.annotate("", b, a, arrowprops=dict(arrowstyle="-|>", color=LEG_COL[k], lw=2.2, ls="--", shrinkA=14, shrinkB=14), zorder=4)
    ax.add_patch(Rectangle((-0.38, -0.32), 0.76, 0.64, fc="#90CAF9", ec=BLUE, lw=1.5, zorder=5))
    ax.text(-0.6, -0.55, "출발 (0, 0)\n= 5 번 자리", ha="right", fontsize=10, color=BLUE, fontweight="bold")
    off = {"pick_table": (0.3, -0.7), "rack_a": (0.4, -0.75), "rack_b": (0.4, 0.55), "place_table": (0.3, 0.55), "center_aisle": (0.45, 0.4)}
    for k, n in enumerate(ROUTE):
        x, y, yaw = LOC[n]["base_goal"]
        stop_marker(ax, k + 1, x, y, yaw, LEG_COL[k])
        dx, dy = off[n]
        ax.text(x + dx, y + dy, f"{NAMES[n]} ({n})\n({x:g}, {y:g}, {np.degrees(yaw):.0f}°)", fontsize=9.5, color=LEG_COL[k], fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=LEG_COL[k], alpha=0.92), zorder=8)
    ax.set_title("순찰 경로: ⑤ 에서 만든 지도 위의 5 곳 (locations.yaml 의 base_goal · 화살표 = 도착 방향)", fontsize=11.5)
    fig.tight_layout()
    save(fig, "lesson07_route.png")


def patrol_node():
    fig, ax = fig_ax(14, 5.8)
    note(ax, 0.3, 5.5, "patrol.py: Nav2 에 목표를 하나씩 보내고, 상태를 알린다", bold=True, fs=12)
    rbox(ax, 5.0, 1.6, 4.0, 2.6, "patrol (노드)", ["정지 목록 (locations.yaml)", "go(): 목표 1 개 → 결과", "errors(): 정지마다 오차", "publish(): 0.5 s 마다 상태"],
         fc=C["green"], tfs=11.5, fs=9)
    ins = [("/ground_truth", "실제 위치 (MuJoCo)"), ("/amcl_pose", "AMCL 추정"), ("/odom", "바퀴 적분"), ("/patrol/command", "start · cancel")]
    for i, (t, s) in enumerate(ins):
        y = 4.1 - i * 1.08
        rbox(ax, 0.3, y, 3.6, 0.92, t, [s], fc=C["grey"], tfs=9.8, fs=8.2, dy=0.25)
        arrow(ax, (3.9, y + 0.46), (5.0, min(max(y + 0.46, 1.8), 4.0)))
    rbox(ax, 10.1, 3.1, 3.6, 1.1, "/navigate_to_pose", ["NavigateToPose 액션 → Nav2"], fc=C["blue"], tfs=10, fs=8.4)
    rbox(ax, 10.1, 1.6, 3.6, 1.1, "/patrol/status", ["JSON 문자열 · latched"], fc=C["yellow"], tfs=10, fs=8.4)
    arrow(ax, (9.0, 3.65), (10.1, 3.65)); arrow(ax, (9.0, 2.15), (10.1, 2.15))
    note(ax, 0.3, 0.45, "구독 4 개 · 액션 클라이언트 1 개 · 발행 1 개. 대시보드도 이 /patrol/status 와 /patrol/command 로만 순찰과 이야기한다.", fs=9.6)
    save(fig, "lesson07_patrol_node.png")


def stop_flow():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "정지 하나를 처리하는 순서 (5 번 반복)", bold=True, fs=12)
    chain(ax, [("목표 보내기", ["base_goal (x, y, yaw)", "frame_id: map"]), ("주행", ["Nav2 가 경로 · 속도", "feedback 받기"]),
               ("결과", ["SUCCEEDED → 다음", "실패 → 순찰 중단"]), ("1 s 기다림", ["AMCL 이 자리 잡게"]), ("오차 기록", ["AMCL - 실제", "odom - 실제"])],
          y=1.3, h=1.8, gap=0.3, colors=[C["purple"], C["blue"], C["yellow"], C["grey"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.6, "목표 근처(0.25 m)에서 8 s 동안 멈춰 있으면 취소하고 '근처 도착'으로 넘어가는 워치독이 있다 (4장).", fs=9.6)
    save(fig, "lesson07_stop_flow.png")


def errors_concept():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "정지마다 재는 것: 같은 순간, 세 가지 '로봇 위치'", bold=True, fs=12)
    tiles(ax, [("실제 (/ground_truth)", ["MuJoCo 가 아는 진짜 위치", "실제 로봇에는 없다", "비교 기준으로만 쓴다"], C["blue"]),
               ("AMCL (/amcl_pose)", ["라이다 + 지도로 추정", "Nav2 가 쓰는 위치", "오차가 쌓이지 않는다"], C["green"]),
               ("odom (/odom)", ["바퀴 회전을 적분", "부드럽지만", "오차가 계속 쌓인다"], C["orange"])], cols=3, y_top=4.1, h=2.0, tfs=11, fs=9.2)
    note(ax, 0.3, 1.25, "오차 = 실제 위치와의 거리 (x, y 만).  지도 원점 = 출발점 (0, 0, 0) 이라 실제 좌표와 map 좌표가 같다.", fs=9.8)
    note(ax, 0.3, 0.6, "odom 오차는 달린 거리만큼 쌓일 수 있고 (④ 실험), AMCL 오차는 지도에 맞춰 몇 cm 안에서 오르내린다.", fs=9.8)
    save(fig, "lesson07_errors.png")


# ================================================================ 2. 실행 (captures + data)
def crop_run(src, dst):
    im = Image.open(PF / src)
    im.crop((12, 8, 2272, 955)).save(OUT / dst)
    print("saved", dst)


def crop_dash(src, dst, box=None):
    im = Image.open(DF / src)
    (im.crop(box) if box else im).save(OUT / dst)
    print("saved", dst)


def run_data():
    d = pickle.load(open("artifacts/dev/patrol_run.pkl", "rb"))
    segs = segments(d)
    starts = [s[0]["t"] for s in segs]
    return d, np.array(d["truth"]), np.array(d["odom"]), starts


def traj():
    d, tr, od, starts = run_data()
    ends = starts[1:] + [starts[-1] + 26]
    fig, ax = plt.subplots(figsize=(12, 8.0), dpi=150)
    show_map(ax)
    for k, (a, b) in enumerate(zip(starts, ends)):
        m = (tr[:, 0] >= a) & (tr[:, 0] < b)
        ax.plot(tr[m, 1], tr[m, 2], color=LEG_COL[k], lw=2.6, label=f"{k + 1}. → {NAMES[ROUTE[k]]}  ({RUN['time'][k]:.1f} s)")
    for k, n in enumerate(ROUTE):
        x, y, yaw = LOC[n]["base_goal"]
        stop_marker(ax, k + 1, x, y, yaw, LEG_COL[k])
    ax.legend(loc="upper center", fontsize=9.5, ncol=3, framealpha=0.95)
    ax.set_title("실측: 로봇이 실제로 간 길 (/ground_truth) · 배경 = ⑤ 에서 만든 지도 · 순찰 148 s, 복구 동작 0 번", fontsize=11.5)
    fig.tight_layout()
    save(fig, "lesson07_traj.png")


def legs():
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
    x = np.arange(5); names = [f"{k + 1}. {NAMES[n]}" for k, n in enumerate(ROUTE)]
    b = axs[0].bar(x, RUN["time"], color=LEG_COL)
    axs[0].bar_label(b, fmt="%.1f s", fontsize=9)
    axs[0].set_xticks(x, names, fontsize=9); axs[0].set_ylabel("구간 시간 [s] (시뮬레이션)"); axs[0].set_title("구간별 시간 (합 144.5 s · 정지마다 1 s 대기를 더하면 순찰 148 s)", fontsize=11)
    w = 0.38
    b1 = axs[1].bar(x - w / 2, np.array(RUN["amcl"]) * 100, w, color="#43A047", label="AMCL - 실제")
    b2 = axs[1].bar(x + w / 2, np.array(RUN["odom"]) * 100, w, color="#FB8C00", label="odom - 실제")
    axs[1].bar_label(b1, fmt="%.1f", fontsize=8.5); axs[1].bar_label(b2, fmt="%.1f", fontsize=8.5)
    axs[1].set_xticks(x, names, fontsize=9); axs[1].set_ylabel("오차 [cm]"); axs[1].legend(fontsize=9)
    axs[1].set_title("정지마다 잰 위치 오차: AMCL 0.4 ~ 3.6 cm · odom 0.2 ~ 1.5 cm", fontsize=11)
    for ax in axs:
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save(fig, "lesson07_legs.png")


def speed():
    d, tr, od, starts = run_data()
    t0, t1 = starts[0] - 1, starts[-1] + 26
    m = (od[:, 0] >= t0) & (od[:, 0] <= t1)
    fig, axs = plt.subplots(2, 1, figsize=(14, 5.6), dpi=150, sharex=True)
    for ax in axs:
        for k, (a, b) in enumerate(zip(starts, starts[1:] + [t1])):
            ax.axvspan(a - starts[0], b - starts[0], color=LEG_COL[k], alpha=0.08, lw=0)
        ax.grid(alpha=0.3)
    for k, a in enumerate(starts):
        axs[0].text(a - starts[0] + 0.5, 0.34, f"{k + 1}. {NAMES[ROUTE[k]]}", fontsize=9, color=LEG_COL[k], fontweight="bold")
    t = od[m, 0] - starts[0]
    axs[0].plot(t, od[m, 4], color=BLUE, lw=1.6); axs[0].set_ylabel("v [m/s]"); axs[0].set_ylim(-0.05, 0.38)
    axs[0].axhline(0.3, color=GREY, ls=":", lw=1); axs[0].text(t[-1] - 14, 0.31, "max_vel_x 0.3", fontsize=8.5, color="#666")
    axs[1].plot(t, od[m, 5], color=BROWN, lw=1.4); axs[1].set_ylabel("w [rad/s]")
    for yv in (0.6, -0.6):
        axs[1].axhline(yv, color=RED, ls=":", lw=1)
    axs[1].text(1.0, 0.68, "구간 시작 · 끝: 제자리 회전 (RotationShim 명령 ±0.6 rad/s, /odom 실측 약 0.56)", fontsize=9, color=RED)
    axs[1].set_xlabel("첫 목표를 보낸 뒤 시뮬레이션 시각 [s]")
    fig.suptitle("실측: /odom 의 속도 · 구간마다 먼저 제자리에서 돌고(w), 그다음 0.3 m/s 로 달린다(v)", fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "lesson07_speed.png")


# ================================================================ 3. 막혔던 곳
def rotate_problem():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "원인: 출발할 때 제자리 회전이 너무 느리다", bold=True, fs=12)
    chain(ax, [("목표가 뒤쪽", ["랙 통로 끝에서", "방향을 크게 바꿔야 함"]), ("DWB 의 회전 명령", ["0.02 ~ 0.07 rad/s", "작은 회전만 고른다"]),
               ("바퀴 정지마찰", ["약 0.1 rad/s 이상", "이어야 돌기 시작"]), ("결과", ["로봇이 안 움직임", "Failed to make progress"])],
          y=1.4, h=1.8, gap=0.35, colors=[C["grey"], C["blue"], C["orange"], C["red"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.7, "수동 /cmd_vel 로는 잘 돈다 → 브리지 · 물리 문제가 아니라 컨트롤러가 고르는 속도 문제.", fs=9.8)
    save(fig, "lesson07_rotate_problem.png")


def shim():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "해결: RotationShim 컨트롤러가 DWB 를 감싼다", bold=True, fs=12)
    rbox(ax, 0.3, 2.0, 2.8, 1.5, "/plan", ["Planner 가 준 경로"], fc=C["orange"], tfs=10.5, fs=8.6)
    rbox(ax, 4.0, 1.6, 3.6, 2.3, "RotationShim", ["경로 방향과의 각도 차이", "> 0.6 rad 이면", "제자리에서 0.6 rad/s 로 회전"], fc=C["purple"], tfs=11, fs=8.8)
    rbox(ax, 8.6, 3.0, 2.6, 1.2, "직접 회전", ["w = ±0.6 rad/s"], fc=C["red"], tfs=10, fs=8.6)
    rbox(ax, 8.6, 1.3, 2.6, 1.2, "DWB", ["각도가 맞으면 넘김"], fc=C["blue"], tfs=10, fs=8.6)
    rbox(ax, 12.0, 2.0, 1.7, 1.5, "/cmd_vel", ["브리지"], fc=C["teal"], tfs=10, fs=8.6)
    arrow(ax, (3.1, 2.75), (4.0, 2.75))
    arrow(ax, (7.6, 3.2), (8.6, 3.6)); arrow(ax, (7.6, 2.3), (8.6, 1.9))
    arrow(ax, (11.2, 3.6), (12.0, 3.0)); arrow(ax, (11.2, 1.9), (12.0, 2.5))
    label(ax, 8.1, 3.75, "각도 차 큼"); label(ax, 8.1, 1.55, "각도 차 작음")
    note(ax, 0.3, 0.75, "도착할 때도 같다 (rotate_to_goal_heading: true): 목표 위치에 닿은 뒤 목표 방향으로 0.6 rad/s 로 돈다.", fs=9.8)
    save(fig, "lesson07_shim.png")


def code_flow():
    fig, ax = fig_ax(14, 4.3)
    note(ax, 0.3, 4.0, "patrol.py 의 흐름", bold=True, fs=12)
    chain(ax, [("main", ["--route · --loops · --wait"]), ("Patrol.__init__", ["정지 목록 · 구독 · 발행", "액션 클라이언트"]),
               ("run", ["서버 · /clock 기다림", "(--wait) start 기다림"]), ("go × 5", ["목표 → 결과", "워치독 · cancel"]), ("errors", ["AMCL · odom 오차", "→ 출력 · 상태"])],
          y=1.3, h=1.8, gap=0.3, colors=[C["grey"], C["purple"], C["yellow"], C["blue"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.6, "타이머 publish() 가 0.5 s 마다 /patrol/status 를 낸다 · 메인 루프는 spin_once 로 콜백을 돌리며 기다린다.", fs=9.6)
    save(fig, "lesson07_code_flow.png")


def watchdog():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "목표 근처 워치독: 다 와서 못 맞추고 서 있으면 넘어간다", bold=True, fs=12)
    tiles(ax, [("근처", ["AMCL 위치 ↔ 목표", "0.25 m 안"], C["blue"]), ("멈춤", ["실제 위치가 8 s 동안", "1 cm · 0.02 rad 이상 안 변함"], C["orange"]),
               ("처리", ["goal cancel", "'근처 도착' 으로 기록"], C["green"])], cols=3, y_top=3.9, h=1.6, tfs=11, fs=9.2)
    note(ax, 0.3, 1.45, "Nav2 의 허용 오차(xy 0.08 m) 바로 밖에서 서는 경우를 위한 안전장치. 이번 실측에서는 한 번도 쓰이지 않았다.", fs=9.8)
    note(ax, 0.3, 0.8, "거리는 Nav2 feedback 의 distance_remaining 대신 직접 계산한다 (feedback 값이 0 근처로 오는 순간이 있다).", fs=9.8)
    save(fig, "lesson07_watchdog.png")


# ================================================================ 5. 웹 대시보드
def dash_layout():
    im = Image.open(DF / "d035.png").convert("RGB")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 22)
    boxes = [((12, 58, 1022, 968), "① 지도"), ((1036, 60, 1688, 416), "② 미션"), ((1036, 428, 1688, 570), "③ 로봇"),
             ((1036, 582, 1688, 860), "④ 카메라"), ((1036, 872, 1688, 1000), "⑤ 이벤트"), ((1380, 6, 1694, 42), "⑥ 연결 · 시간")]
    for (x0, y0, x1, y1), t in boxes:
        d.rectangle((x0, y0, x1, y1), outline="#FFB300", width=4)
        tw = d.textlength(t, font=f)
        tx, ty = (x0 + 10, y0 + 8) if t[0] != "⑥" else (x0 - tw - 24, y0 + 4)
        d.rectangle((tx - 6, ty - 4, tx + tw + 6, ty + 28), fill="#FFB300")
        d.text((tx, ty), t, fill="black", font=f)
    im.save(OUT / "lesson07_dash_layout.png"); print("saved lesson07_dash_layout.png")


def dash_parts():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "화면의 여섯 영역과 데이터 출처", bold=True, fs=12)
    tiles(ax, [("① 지도", ["/map (PNG) 위에 실제 · AMCL · odom", "/plan · 궤적 · /scan · 사람 · 정지"], C["grey"]),
               ("② 미션", ["/patrol/status (JSON)", "진행바 · 정지표 · 시작/취소"], C["green"]),
               ("③ 로봇", ["/odom 속도 · 위치 오차", "AMCL 표준편차 · 보이는 사람"], C["blue"]),
               ("④ 카메라", ["frame_tap 의 JPEG (MJPEG)", "+ /vision/detections 박스"], C["orange"]),
               ("⑤ 이벤트", ["상태가 바뀔 때만 한 줄", "도착 · 출발 · 안전모 미착용"], C["yellow"]),
               ("⑥ 연결 · 시간", ["SSE 연결 상태 · sim 시각", "실시간 비율 (sim ÷ 벽시계)"], C["purple"])], cols=3, y_top=4.3, h=1.75, tfs=11, fs=9)
    save(fig, "lesson07_dash_parts.png")


def dash_arch():
    fig, ax = fig_ax(14, 6.6)
    note(ax, 0.3, 6.3, "대시보드 구성: 프로세스 셋, 브라우저는 ROS 를 모른다", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 3.2), 4.4, 2.7, fc="#F7F9FC", ec="#90A4AE", lw=1.2, zorder=1)); note(ax, 0.45, 5.65, "터미널 1: 시뮬레이터", bold=True, fs=9.8, color=BLUE)
    rbox(ax, 0.5, 4.3, 4.0, 1.0, "MuJoCo 브리지", ["카메라 렌더 · /odom · /scan …"], fc=C["teal"], tfs=10, fs=8.4)
    rbox(ax, 0.5, 3.35, 4.0, 0.8, "frame_tap.py (camera_handler)", fc=C["orange"], tfs=9.6)
    rbox(ax, 0.3, 1.3, 4.4, 1.3, "/dev/shm/…/<cam>.jpg", ["최신 프레임 1 장 · meta.json"], fc=C["grey"], tfs=10, fs=8.4)
    arrow(ax, (2.5, 3.35), (2.5, 2.6))
    rbox(ax, 0.3, 0.2, 4.4, 0.8, "터미널 3: patrol.py --wait", fc=C["green"], tfs=9.8)
    ax.add_patch(Rectangle((5.4, 0.2), 4.2, 5.7, fc="#F7F9FC", ec="#90A4AE", lw=1.2, zorder=1)); note(ax, 5.55, 5.65, "터미널 2: server.py", bold=True, fs=9.8, color=BLUE)
    rbox(ax, 5.6, 3.9, 3.8, 1.4, "ROS 스레드", ["rclpy 노드: 구독 9 개", "최신값만 dict 에 (lock)"], fc=C["blue"], tfs=10, fs=8.4)
    rbox(ax, 5.6, 1.5, 3.8, 1.9, "Flask 스레드", ["/api/stream (SSE 5 Hz)", "/camera/<cam>.mjpg", "/api/map.png · POST /api/command"], fc=C["yellow"], tfs=10, fs=8.4)
    arrow(ax, (7.5, 3.9), (7.5, 3.4))
    arrow(ax, (4.7, 1.95), (5.6, 1.95))
    rbox(ax, 10.4, 1.5, 3.3, 3.8, "브라우저", ["index.html · app.js", "EventSource ← SSE", "<img> ← MJPEG", "fetch POST → 명령", "canvas 에 지도 그리기"], fc=C["purple"], tfs=10.5, fs=8.6)
    arrow(ax, (9.4, 2.9), (10.4, 2.9)); arrow(ax, (10.4, 2.1), (9.4, 2.1))
    ax.plot([4.7, 5.15, 5.15], [0.6, 0.6, 4.6], color=GREEN, lw=1.4); arrow(ax, (5.15, 4.6), (5.6, 4.6), color=GREEN)
    label(ax, 3.0, 0.6 + 0.55, "/patrol/status ↔ /patrol/command", color=GREEN, fs=8.4)
    ax.plot([4.5, 5.0, 5.0], [4.8, 4.8, 5.05], color=INK, lw=1.2); arrow(ax, (5.0, 5.05), (5.6, 5.05))
    note(ax, 10.4, 0.7, "http://localhost:8080", bold=True, fs=10, color=BLUE)
    save(fig, "lesson07_dash_arch.png")


def sse():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "SSE (Server-Sent Events): 응답 하나를 끊지 않고 계속 이어 쓴다", bold=True, fs=12)
    rbox(ax, 0.3, 1.4, 3.0, 2.4, "브라우저", ["new EventSource(", "'/api/stream')", "onmessage = 그리기"], fc=C["purple"], tfs=10.5, fs=8.8)
    rbox(ax, 10.7, 1.4, 3.0, 2.4, "Flask", ["while True:", "yield 'data: {json}' + 빈 줄", "sleep(0.2)"], fc=C["yellow"], tfs=10.5, fs=8.8)
    arrow(ax, (3.3, 3.3), (10.7, 3.3)); label(ax, 7.0, 3.55, "GET /api/stream  (한 번)")
    for i in range(4):
        x = 9.6 - i * 1.6
        rbox(ax, x - 0.65, 1.75, 1.3, 0.9, f"data {i + 1}", ["{truth, amcl …}"], fc="white", tfs=8.6, fs=7.4, dy=0.22)
    arrow(ax, (10.7, 2.2), (3.3, 2.2), color=BLUE)
    label(ax, 7.0, 1.35, "0.2 s 마다 한 줄씩 (text/event-stream)", color=BLUE)
    note(ax, 0.3, 0.6, "웹소켓보다 단순하다 (서버 → 브라우저 한 방향). 끊기면 브라우저가 알아서 다시 연결한다. 명령은 따로 POST.", fs=9.8)
    save(fig, "lesson07_sse.png")


def mjpeg():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "MJPEG: JPEG 를 이어 붙인 응답 하나 = 움직이는 그림", bold=True, fs=12)
    rbox(ax, 0.3, 1.4, 3.0, 2.4, "<img>", ["src = /camera/", "base_camera.mjpg", "브라우저가 알아서 교체"], fc=C["purple"], tfs=10.5, fs=8.8)
    rbox(ax, 10.7, 1.4, 3.0, 2.4, "Flask", ["파일 mtime 이 바뀌면", "--frame + JPEG 한 장", "0.05 s 마다 확인"], fc=C["yellow"], tfs=10.5, fs=8.8)
    for i in range(4):
        x = 9.6 - i * 1.6
        rbox(ax, x - 0.65, 1.75, 1.3, 0.9, "--frame", ["JPEG"], fc="#FFF8E1", tfs=8.6, fs=7.6, dy=0.22)
    arrow(ax, (10.7, 2.2), (3.3, 2.2), color=ORANGE)
    label(ax, 7.0, 3.3, "Content-Type: multipart/x-mixed-replace; boundary=frame")
    label(ax, 7.0, 1.35, "카메라 5 Hz (camera_fps:=5) · 320 × 240 · 품질 80", color=ORANGE)
    note(ax, 0.3, 0.6, "자바스크립트 없이 <img> 태그 하나로 영상이 나온다. 검출 박스는 그 위에 겹친 canvas 에 app.js 가 그린다.", fs=9.8)
    save(fig, "lesson07_mjpeg.png")


def frametap():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "frame_tap.py: 카메라 영상은 토픽이 없다 → 시뮬레이터 안에서 꺼낸다", bold=True, fs=12)
    chain(ax, [("MuJoCo 렌더", ["시뮬레이터 프로세스 안", "카메라 2 대 · 5 Hz"]), ("camera_handler", ["LecturePipeline", "ArUco · 검출 → /vision/*"]),
               ("DashboardPipeline", ["+ JPEG 인코딩", "(320 × 240 ≈ 1 ms)"]), ("임시 파일 → 교체", ["os.replace: 원자적", "반쯤 쓴 파일 없음"]), ("/dev/shm", ["메모리 위 파일", "server.py 가 읽음"])],
          y=1.3, h=1.8, gap=0.3, colors=[C["teal"], C["blue"], C["orange"], C["grey"], C["yellow"]], tfs=10.2, fs=8.5)
    note(ax, 0.3, 0.6, "launch 인자 camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline 으로 끼워 넣는다.", fs=9.6)
    save(fig, "lesson07_frametap.png")


def threads():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "server.py: ROS 스레드와 Flask 스레드가 dict 하나를 나눠 쓴다", bold=True, fs=12)
    rbox(ax, 0.3, 1.3, 4.0, 2.7, "ROS 스레드", ["SingleThreadedExecutor.spin", "콜백: on_truth · on_amcl …", "self.s 에 최신값 쓰기"], fc=C["blue"], tfs=10.5, fs=8.8)
    rbox(ax, 5.2, 1.6, 3.6, 2.1, "self.s + lock", ["truth · amcl · odom · plan", "scan · actors · detections", "patrol · trail"], fc=C["grey"], tfs=10.5, fs=8.6)
    rbox(ax, 9.7, 1.3, 4.0, 2.7, "Flask 스레드", ["요청마다 스레드 (threaded)", "snapshot(): lock 안에서 복사", "→ JSON 으로 내보냄"], fc=C["yellow"], tfs=10.5, fs=8.8)
    arrow(ax, (4.3, 2.65), (5.2, 2.65)); arrow(ax, (8.8, 2.65), (9.7, 2.65))
    note(ax, 0.3, 0.6, "rclpy.init(SignalHandlerOptions.NO): Ctrl+C 를 Flask 가 받고, finally 에서 executor 를 멈춘 뒤 끝낸다.", fs=9.8)
    save(fig, "lesson07_threads.png")


if __name__ == "__main__":
    for f in (why, route, patrol_node, stop_flow, errors_concept, traj, legs, speed, rotate_problem, shim,
              code_flow, watchdog, dash_layout, dash_parts, dash_arch, sse, mjpeg, frametap, threads):
        f()
    crop_run("s000.png", "lesson07_run_start.png")
    crop_run("s017.png", "lesson07_run_rack_a.png")
    crop_run("s040.png", "lesson07_run_place.png")
    crop_run("s066.png", "lesson07_run_done.png")
    crop_dash("d000.png", "lesson07_dash_waiting.png")
    crop_dash("d015.png", "lesson07_dash_running.png")
    crop_dash("d035.png", "lesson07_dash_helmet.png")
    crop_dash("done.png", "lesson07_dash_done.png")
