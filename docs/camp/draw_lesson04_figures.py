"""Figures for the lesson-04 Confluence page (SLAM Toolbox로 창고 지도 만들기). Output: docs/camp/lesson04_*.png

Run from the workspace root.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson03_figures import tiles_at  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402

RED, BLUE, GREEN, BROWN, GREY = "#C62828", "#1f4e79", "#2e7d32", "#7a4b00", "#9e9e9e"


# ================================================================ 1. SLAM 이란
def why_slam():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "Odom 만으로는 부족하다 (④ 에서 본 것)", bold=True, fs=12)
    tiles(ax, [("오차가 쌓인다", ["바퀴 각도를 적분한 추정값", "시뮬레이터에서도 8 m 에 0.5 cm", "실제 로봇은 수십 cm"], C["red"]),
               ("지도가 없다", ["odom 은 '얼마나 움직였나' 만 안다", "벽 · 선반이 어디 있는지 모른다", "목적지를 좌표로 줄 수 없다"], C["red"]),
               ("시작점만 안다", ["켤 때마다 (0, 0) 에서 시작", "창고 안 어디인지 모른다", "다시 켜면 좌표가 바뀐다"], C["red"])],
          cols=3, y_top=3.9, gap=0.3, h=2.0, tfs=11.5, fs=9.0)
    arrow(ax, (7.0, 1.75), (7.0, 1.2))
    rbox(ax, 2.5, 0.3, 9.0, 0.85, "SLAM: 라이다로 지도를 만들면서, 그 지도 위에서 내 위치를 바로잡는다", fc=C["green"], tfs=10.8)
    save(fig, "lesson04_why_slam.png")


def slam_loop():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.9, "SLAM = Simultaneous Localization And Mapping", bold=True, fs=12)
    rbox(ax, 0.3, 2.9, 2.6, 1.3, "/scan", ["라이다 360점"], fc=C["blue"], tfs=10.5, fs=8.8)
    rbox(ax, 0.3, 0.9, 2.6, 1.3, "odom", ["바퀴로 추정한 이동"], fc=C["blue"], tfs=10.5, fs=8.8)
    rbox(ax, 4.0, 1.6, 3.0, 1.9, "위치 추정", ["odom 으로 대략 옮긴 뒤", "스캔을 지도에 맞춰 보정", "(Localization)"], fc=C["orange"], tfs=11, fs=8.8)
    rbox(ax, 9.0, 1.6, 3.0, 1.9, "지도 작성", ["보정된 위치에서", "스캔을 격자에 그린다", "(Mapping)"], fc=C["green"], tfs=11, fs=8.8)
    arrow(ax, (2.9, 3.55), (3.45, 3.55)); ax.plot([3.45, 3.45], [3.55, 2.8], color=INK, lw=1.6); arrow(ax, (3.45, 2.8), (4.0, 2.8))
    arrow(ax, (2.9, 1.55), (3.45, 1.55)); ax.plot([3.45, 3.45], [1.55, 2.3], color=INK, lw=1.6); arrow(ax, (3.45, 2.3), (4.0, 2.3))
    arrow(ax, (7.0, 2.8), (9.0, 2.8)); label(ax, 8.0, 3.1, "내 위치", fs=9)
    ax.plot([10.5, 10.5], [1.6, 0.6], color=BROWN, lw=1.6); ax.plot([10.5, 5.5], [0.6, 0.6], color=BROWN, lw=1.6)
    arrow(ax, (5.5, 0.6), (5.5, 1.6), color=BROWN); label(ax, 8.0, 0.6, "지금까지의 지도 (다음 스캔을 맞출 기준)", color=BROWN, fs=9)
    arrow(ax, (12.0, 2.55), (12.5, 2.55))
    rbox(ax, 12.5, 1.6, 1.2, 1.9, "/map", ["TF", "map→odom"], fc=C["purple"], tfs=10.5, fs=8.4)
    note(ax, 0.3, 4.4, "지도가 있어야 위치를 알고, 위치를 알아야 지도를 그린다 → 둘을 같이 푼다.", fs=9.8)
    save(fig, "lesson04_slam_loop.png")


def occupancy():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "점유 격자 지도 (Occupancy Grid): 바닥을 5 cm 칸으로 나눠 칸마다 상태를 적는다", bold=True, fs=12)
    ax.set_aspect("equal")
    n, s, x0, y0 = 12, 0.33, 0.6, 0.45
    grid = np.full((n, n), -1)
    ox, oy = 2, 5
    for i in range(n):
        for j in range(ox, 10):
            if abs(np.arctan2(i - oy, j - ox)) < 0.62:
                grid[i, j] = 100 if j == 9 else 0
    grid[oy, ox] = 0
    col = {-1: "#9aa5a8", 0: "#f2f2f2", 100: "#202020"}
    for i in range(n):
        for j in range(n):
            ax.add_patch(Rectangle((x0 + j * s, y0 + i * s), s, s, fc=col[grid[i, j]], ec="#c8c8c8", lw=0.4))
    cx, cy = x0 + (ox + 0.5) * s, y0 + (oy + 0.5) * s
    ax.add_patch(Circle((cx, cy), 0.16, fc=RED, ec=INK, zorder=4))
    for a in (-0.5, -0.2, 0.1, 0.4):
        ax.plot([cx, x0 + 9.5 * s], [cy, cy + np.tan(a) * (x0 + 9.5 * s - cx)], color=RED, lw=0.8, alpha=0.7)
    label(ax, cx, cy - 0.45, "라이다", color=RED, fs=8.6)
    label(ax, x0 + n * s / 2, y0 + n * s + 0.2, "레이가 지나간 칸 = 비어 있음 · 레이가 멈춘 칸 = 막힘", fs=8.6)
    tiles_at(ax, [("비어 있음 (free)", ["값 0 · 흰색", "레이가 통과한 칸"], C["grey"]),
                  ("막힘 (occupied)", ["값 100 · 검은색", "레이가 부딪힌 칸"], "#D6D6D6"),
                  ("모름 (unknown)", ["값 -1 · 회색", "아직 레이가 닿지 않은 칸"], "#DCE3E5")],
             cols=1, x0=6.2, x1=10.0, y_top=4.6, gap=0.2, h=1.25, tfs=10.5, fs=8.8)
    tiles_at(ax, [("nav_msgs/OccupancyGrid", ["info.resolution 0.05 m", "info.width × height (칸 수)", "info.origin = 왼쪽 아래 칸의 좌표", "data[] = 칸 값 (행 순서)"], C["purple"])],
             cols=1, x0=10.3, x1=13.7, y_top=4.6, gap=0.2, h=2.2, tfs=10.2, fs=8.8)
    save(fig, "lesson04_occupancy.png")


def tf_chain():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "TF 가 한 단계 늘어난다: map → odom → base_footprint", bold=True, fs=12)
    xs = [0.4, 3.9, 7.4, 10.9]
    names = [("map", "지도 좌표 (SLAM 원점)"), ("odom", "odom 원점 (출발점)"), ("base_footprint", "로봇 바닥 중심"), ("laser_link", "라이다")]
    for x, (t, l) in zip(xs, names):
        rbox(ax, x, 2.3, 2.7, 1.2, t, [l], fc=C["purple"] if t == "map" else C["blue"], tfs=11, fs=8.6)
    for x, (who, col) in zip(xs[:3], [("slam_toolbox", RED), ("브리지 (odom 적분)", BLUE), ("robot_state_publisher", GREEN)]):
        arrow(ax, (x + 2.7, 2.9), (x + 3.5, 2.9), color=col, lw=2)
        label(ax, x + 3.1, 1.95, who, color=col, fs=8.6)
    tiles_at(ax, [("map → odom = 보정값", ["odom 이 틀린 만큼을 SLAM 이 채운다", "drift 가 없으면 (0, 0, 0) 에 머문다"], C["red"]),
                  ("odom → base_footprint", ["④ 와 같다: 50 Hz, 연속적", "짧은 구간은 여전히 odom 이 담당"], C["blue"])],
             cols=2, x0=0.4, x1=13.6, y_top=1.55, gap=0.3, h=1.2, tfs=10.2, fs=8.6)
    save(fig, "lesson04_tf_chain.png")


def toolbox_intro():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "SLAM Toolbox: ROS 2 기본 2D SLAM 패키지 (Nav2 공식 문서가 쓰는 것)", bold=True, fs=12)
    tiles(ax, [("스캔 매칭", ["새 스캔을 이전 스캔 · 지도에 겹쳐", "odom 이 틀린 만큼 위치를 고친다", "(Karto 계열 상관 매칭)"], C["orange"]),
               ("포즈 그래프", ["스캔을 찍은 자리 = 노드", "노드 사이 상대 이동 = 엣지", "Ceres 로 최적화"], C["yellow"]),
               ("루프 클로징", ["왔던 곳을 다시 알아보면", "처음과 끝을 잇는 엣지 추가", "쌓인 오차를 한 번에 편다"], C["green"]),
               ("모드", ["mapping: 지도 만들기 (이 페이지)", "localization: 저장한 지도에서 위치만", "online async: 실시간 · 스캔 건너뛰기 허용"], C["blue"])],
          cols=4, y_top=3.9, gap=0.25, h=2.2, tfs=11, fs=8.4)
    note(ax, 0.3, 1.2, "설치: ros-jazzy-slam-toolbox (설치 스크립트에 포함).  실행 파일: async_slam_toolbox_node", fs=9.6)
    note(ax, 0.3, 0.6, "입력: /scan + TF(odom → base_footprint → laser_link).  출력: /map + TF(map → odom).", fs=9.6)
    save(fig, "lesson04_toolbox.png")


def scan_matching():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "스캔 매칭: odom 이 준 위치를 출발점으로, 스캔이 지도와 가장 잘 겹치는 위치를 찾는다", bold=True, fs=12)
    ax.set_aspect("equal")

    def room(ax, dx, dy, da, col, x0):
        pts = []
        for t in np.linspace(0, 1, 18):
            pts += [(t * 3.2, 0), (t * 3.2, 2.4), (0, t * 2.4)]
        pts += [(1.6 + 0.5 * np.cos(a), 1.2 + 0.3 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 10)]
        p = np.array(pts)
        c, s = np.cos(da), np.sin(da)
        p = p @ np.array([[c, s], [-s, c]]) + [dx, dy]
        ax.scatter(p[:, 0] + x0, p[:, 1] + 1.0, s=6, color=col, zorder=3)

    for x0, title, shift in ((0.4, "① odom 위치로 놓은 스캔", (0.35, -0.25, 0.12)), (5.0, "② 겹치도록 옮겨 본다", (0.15, -0.1, 0.05)), (9.6, "③ 가장 잘 겹치는 위치", (0, 0, 0))):
        room(ax, 0, 0, 0, "#9e9e9e", x0)
        room(ax, *shift, RED, x0)
        note(ax, x0, 4.1, title, bold=True, fs=10.5, color=INK)
    for x in (4.2, 8.8):
        arrow(ax, (x, 2.2), (x + 0.6, 2.2))
    note(ax, 0.4, 0.45, "회색 = 지금까지의 지도,  빨강 = 새 스캔.  ③ 에서 찾은 위치와 odom 위치의 차이가 곧 보정량이다.", fs=9.6)
    save(fig, "lesson04_scan_matching.png")


def pose_graph():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.9, "포즈 그래프와 루프 클로징", bold=True, fs=12)
    ax.set_aspect("equal")
    t = np.linspace(0, 2 * np.pi, 13)[:-1]
    for x0, closed, title in ((0.6, False, "① 한 바퀴 돌며 노드를 쌓는다 (오차 누적)"), (7.4, True, "② 출발점을 다시 알아보면 → 엣지 추가 → 전체를 편다")):
        drift = 0.0 if closed else 1.0
        xs = x0 + 2.8 + 2.2 * np.cos(t - np.pi / 2) + drift * np.linspace(0, 0.9, len(t))
        ys = 2.3 + 1.6 * np.sin(t - np.pi / 2) + drift * np.linspace(0, 0.55, len(t))
        ax.plot(xs, ys, color=BLUE, lw=1.4, zorder=2)
        ax.scatter(xs, ys, s=70, color="#BBDEFB", edgecolor=BLUE, zorder=3)
        ax.scatter(xs[:1], ys[:1], s=110, color=GREEN, edgecolor=INK, zorder=4)
        if closed:
            ax.plot([xs[-1], xs[0]], [ys[-1], ys[0]], color=RED, lw=2.4, zorder=2)
            label(ax, (xs[-1] + xs[0]) / 2 - 0.9, (ys[-1] + ys[0]) / 2 - 0.1, "루프 엣지", color=RED, fs=9)
        else:
            ax.plot([xs[-1], xs[0]], [ys[-1], ys[0]], color=RED, lw=1.2, ls=":", zorder=2)
            label(ax, xs[-1] + 0.3, ys[-1] + 0.45, "같은 곳인데 어긋남", color=RED, fs=9)
        note(ax, x0, 4.35, title, bold=True, fs=10.2, color=INK)
    note(ax, 0.6, 0.25, "노드 = 스캔을 찍은 자세,  엣지 = 스캔 매칭으로 구한 상대 이동.  초록 = 출발 노드.", fs=9.4)
    save(fig, "lesson04_pose_graph.png")


# ================================================================ 2. 실행
def slam_tree():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "./scripts/mobile_openarm slam  =  warehouse.launch.py mode:=slam moveit:=false", bold=True, fs=12)
    rbox(ax, 0.3, 1.4, 3.0, 1.5, "warehouse.launch.py", ["mode:=slam"], fc=C["purple"], tfs=10.5, fs=8.8)
    items = [("브리지 (MuJoCo)", "/scan · /odom · TF", C["teal"]), ("robot_state_publisher", "로봇 TF", C["blue"]),
             ("slam_toolbox", "/map · map→odom", C["orange"]), ("RViz2", "Fixed Frame map", C["grey"])]
    for k, (t, l, fc) in enumerate(items):
        x = 4.2 + k * 2.4
        rbox(ax, x, 1.4, 2.2, 1.5, t, [l], fc=fc, tfs=9.8, fs=8.2)
    ax.plot([3.3, 3.75], [2.15, 2.15], color=INK, lw=1.6); ax.plot([3.75, 3.75], [2.15, 3.3], color=INK, lw=1.6)
    ax.plot([3.75, 4.2 + 3 * 2.4 + 1.1], [3.3, 3.3], color=INK, lw=1.6)
    for k in range(4):
        arrow(ax, (4.2 + k * 2.4 + 1.1, 3.3), (4.2 + k * 2.4 + 1.1, 2.9))
    label(ax, 10.15, 1.05, "drive 와 달라진 것", color=RED, fs=9)
    ax.add_patch(Rectangle((8.95, 1.3), 2.4, 1.7, fc="none", ec=RED, lw=1.6, ls="--", zorder=5))
    note(ax, 0.3, 0.55, "navigation.launch.py 가 slam_toolbox 의 online_async_launch.py 를 slam.yaml 과 함께 불러 온다.  Nav2 는 띄우지 않는다.", fs=9.4)
    save(fig, "lesson04_slam_tree.png")


def teleop_keys():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "teleop_twist_keyboard: 키보드 → /cmd_vel", bold=True, fs=12)
    keys = [["u", "i", "o"], ["j", "k", "l"], ["m", ",", "."]]
    desc = {"i": "전진", ",": "후진", "j": "좌회전", "l": "우회전", "k": "정지", "u": "좌전진", "o": "우전진", "m": "좌후진", ".": "우후진"}
    for r, row in enumerate(keys):
        for c, k in enumerate(row):
            x, y = 0.6 + c * 1.35, 3.1 - r * 1.3
            rbox(ax, x, y, 1.15, 0.9, k, fc=C["yellow"] if k == "k" else C["grey"], tfs=14)
            label(ax, x + 0.58, y - 0.2, desc[k], fs=8.2)
    tiles_at(ax, [("속도 조절", ["q / z : 둘 다 ±10 %", "w / x : 직진만 · e / c : 회전만", "wrapper 기본값 0.25 m/s · 0.5 rad/s"], C["blue"]),
                  ("지도를 잘 만드는 운전", ["천천히 · 회전은 더 천천히", "벽을 따라 한 바퀴 → 출발점으로 돌아오기", "터미널 창을 클릭해 둬야 키가 먹는다"], C["green"])],
             cols=2, x0=5.2, x1=13.7, y_top=4.0, gap=0.3, h=2.1, tfs=10.5, fs=8.8)
    save(fig, "lesson04_teleop_keys.png")


# ================================================================ 3. 저장
def map_files():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "map_saver_cli: /map 한 장을 파일 두 개로", bold=True, fs=12)
    rbox(ax, 0.3, 1.3, 2.6, 1.6, "/map", ["OccupancyGrid", "transient local"], fc=C["purple"], tfs=11, fs=8.6)
    rbox(ax, 3.6, 1.3, 3.0, 1.6, "map_saver_cli", ["-f artifacts/maps/my_warehouse"], fc=C["orange"], tfs=10.5, fs=8.2)
    rbox(ax, 7.4, 2.25, 6.3, 1.15, "my_warehouse.pgm", ["칸 하나 = 픽셀 하나 (흰 0 · 검 100 · 회색 -1)"], fc=C["grey"], tfs=10.2, fs=8.6)
    rbox(ax, 7.4, 0.8, 6.3, 1.15, "my_warehouse.yaml", ["image · resolution · origin · 임계값 (pgm 을 읽는 법)"], fc=C["yellow"], tfs=10.2, fs=8.6)
    arrow(ax, (2.9, 2.1), (3.6, 2.1)); ax.plot([6.6, 7.0], [2.1, 2.1], color=INK, lw=1.6); ax.plot([7.0, 7.0], [1.37, 2.82], color=INK, lw=1.6)
    arrow(ax, (7.0, 2.82), (7.4, 2.82)); arrow(ax, (7.0, 1.37), (7.4, 1.37))
    note(ax, 0.3, 0.35, "Nav2 의 map_server 가 이 yaml 을 읽어 다시 /map 으로 낸다 (⑥ 에서 사용).", fs=9.4)
    save(fig, "lesson04_map_files.png")


def yaml_fields():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "yaml 의 뜻: 픽셀 (i, j) → 지도 좌표 (x, y)", bold=True, fs=12)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0.6, 0.7), 4.4, 3.2, fc="#f2f2f2", ec=INK, lw=1.2))
    ax.add_patch(Circle((0.6, 0.7), 0.1, fc=RED, zorder=5)); label(ax, 1.25, 0.4, "origin (x, y)", color=RED, fs=9)
    for k in range(1, 6):
        ax.plot([0.6 + k * 0.4, 0.6 + k * 0.4], [0.7, 0.9], color=GREY, lw=0.8)
    label(ax, 1.7, 1.15, "칸 한 변 = resolution", fs=8.6)
    ax.add_patch(Circle((3.1, 2.4), 0.09, fc=BLUE, zorder=5))
    ax.plot([0.6, 3.1], [2.4, 2.4], color=BLUE, lw=1, ls="--"); ax.plot([3.1, 3.1], [0.7, 2.4], color=BLUE, lw=1, ls="--")
    label(ax, 3.1, 2.75, "x = origin_x + (열 + 0.5) × resolution", color=BLUE, fs=8.4)
    note(ax, 0.6, 4.2, "pgm 의 맨 아래 줄이 origin 쪽 (이미지는 위에서부터 저장)", fs=8.8)
    tiles_at(ax, [("image · mode", ["pgm 파일 이름 · trinary (0 / 100 / -1 세 값)"], C["grey"]),
                  ("resolution", ["칸 한 변의 길이 [m] · 0.05 = 5 cm"], C["blue"]),
                  ("origin: [x, y, yaw]", ["pgm 왼쪽 아래 칸의 map 좌표"], C["purple"]),
                  ("occupied_thresh · free_thresh", ["밝기 → 점유 확률 경계 (0.65 · 0.25)"], C["yellow"]),
                  ("negate", ["0 = 흰색이 빈칸 (보통 그대로)"], C["grey"])],
             cols=1, x0=6.4, x1=13.7, y_top=5.0, gap=0.1, h=0.88, tfs=9.8, fs=8.4)
    save(fig, "lesson04_yaml_fields.png")


# ================================================================ 4. 코드
def launch_branch():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "navigation.launch.py 의 분기: mode 에 따라 무엇을 붙이나", bold=True, fs=12)
    rbox(ax, 0.3, 1.4, 2.6, 1.5, "mode", ["warehouse.launch 가", "넘겨 준 값"], fc=C["purple"], tfs=11, fs=8.6)
    rows = [("slam", "slam_toolbox (online_async_launch.py + slam.yaml)", C["orange"]),
            ("nav + map", "map_server + amcl + Nav2 서버 5개", C["blue"]),
            ("nav (map 없음)", "slam_toolbox + Nav2 서버 5개  (지도 만들며 주행)", C["yellow"]),
            ("drive", "아무것도 붙이지 않음 (warehouse.launch 가 include 안 함)", C["grey"])]
    for k, (a, b, fc) in enumerate(rows):
        y = 3.05 - k * 0.8
        rbox(ax, 3.6, y - 0.3, 2.3, 0.62, a, fc=fc, tfs=10); arrow(ax, (5.9, y), (6.4, y)); rbox(ax, 6.4, y - 0.3, 7.3, 0.62, b, fc=C["grey"], tfs=9.4)
    ax.plot([2.9, 3.25], [2.15, 2.15], color=INK, lw=1.6); ax.plot([3.25, 3.25], [0.65, 3.05], color=INK, lw=1.6)
    for k in range(4):
        arrow(ax, (3.25, 3.05 - k * 0.8), (3.6, 3.05 - k * 0.8))
    save(fig, "lesson04_launch_branch.png")


def params():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "slam.yaml 에서 볼 파라미터", bold=True, fs=12)
    tiles(ax, [("프레임 · 토픽", ["map_frame: map", "odom_frame: odom", "base_frame: base_footprint", "scan_topic: /scan"], C["purple"]),
               ("지도", ["resolution: 0.05 (5 cm 칸)", "max_laser_range: 20.0", "map_update_interval: 1.0 s", "mode: mapping"], C["green"]),
               ("언제 스캔을 쓰나", ["minimum_travel_distance: 0.05 m", "minimum_travel_heading: 0.05 rad", "minimum_time_interval: 0.1 s", "→ 움직여야 지도가 자란다"], C["orange"]),
               ("보정", ["use_scan_matching: true", "do_loop_closing: true", "solver: CeresSolver", "transform_publish_period: 0.02 s"], C["blue"])],
          cols=4, y_top=4.2, gap=0.25, h=2.55, tfs=11, fs=8.6)
    note(ax, 0.3, 1.05, "use_sim_time: true  →  /clock 기준으로 동작 (시뮬레이터 시각).", fs=9.6)
    note(ax, 0.3, 0.5, "파일: src/mobile_openarm_navigation/config/slam.yaml  (symlink 설치: 고치면 다시 빌드하지 않아도 다음 실행에 반영)", fs=9.6)
    save(fig, "lesson04_params.png")


# ================================================================ data figures (recorded /map, saved maps)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from PIL import Image  # noqa: E402

MAPCMAP = ListedColormap(["#8a9a9c", "#f4f4f4", "#1a1a1a"])   # unknown · free · occupied


def show_grid(ax, data, res, origin):
    """OccupancyGrid values (-1 / 0 / 100, row 0 = bottom) drawn in world coordinates."""
    code = np.where(data < 0, 0, np.where(data >= 65, 2, 1))
    h, w = data.shape
    ax.imshow(code, cmap=MAPCMAP, vmin=0, vmax=2, origin="lower", interpolation="nearest",
              extent=[origin[0], origin[0] + w * res, origin[1], origin[1] + h * res])
    ax.set_xlim(-7.9, 7.9); ax.set_ylim(-5.9, 5.9); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])


def load_pgm(yaml_path):
    import yaml
    y = yaml.safe_load(Path(yaml_path).read_text())
    img = np.array(Image.open(Path(yaml_path).parent / y["image"]))[::-1]
    data = np.where(img < 50, 100, np.where(img > 230, 0, -1))
    return data, y["resolution"], y["origin"][:2]


def map_growth():
    shots = [np.load(f"artifacts/dev/slam_maps/wp{i}.npz") for i in range(8)]
    route = [(0.0, 0.0), (6.4, 0.0), (6.4, 4.8), (-6.6, 4.8), (-6.6, -4.8), (6.4, -4.8), (6.4, 0.0), (0.0, 0.0)]
    pick = [0, 1, 3, 4, 5, 7]
    t0 = float(shots[0]["stamp"])
    fig, axs = plt.subplots(2, 3, figsize=(14, 7.2), dpi=150)
    for ax, i in zip(axs.flat, pick):
        s = shots[i]
        show_grid(ax, s["data"], float(s["resolution"]), s["origin"])
        path = np.array(route[: i + 1])
        ax.plot(path[:, 0], path[:, 1], color="#1976D2", lw=1.6, alpha=0.8)
        x, y, a = s["pose"]
        ax.add_patch(Circle((x, y), 0.3, fc=RED, ec="white", lw=1.2, zorder=5))
        ax.plot([x, x + 0.6 * np.cos(a)], [y, y + 0.6 * np.sin(a)], color="white", lw=1.8, zorder=6)
        known = (s["data"] >= 0).mean() * 100
        ax.set_title(f"{'출발' if i == 0 else f'웨이포인트 {i}'}  ·  시뮬레이션 {float(s['stamp']) - t0:.0f} s  ·  아는 칸 {known:.0f} %", fontsize=10.5)
    fig.suptitle("지도가 자라는 모습 (한 바퀴 58 m, 실제 /map 기록): 회색 = 모름 · 흰색 = 비어 있음 · 검정 = 막힘 · 파랑 = 지나온 길",
                 fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout()
    save(fig, "lesson04_map_growth.png")


def map_compare():
    mine = load_pgm("artifacts/maps/my_warehouse.yaml")
    pkg = load_pgm("src/mobile_openarm_navigation/maps/warehouse.yaml")
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4), dpi=150)
    show_grid(axs[0], *mine); axs[0].set_title("내가 만든 지도 (SLAM, artifacts/maps/my_warehouse)", fontsize=11)
    show_grid(axs[1], *pkg); axs[1].set_title("패키지 지도 (maps/warehouse, 모델에서 그린 것)", fontsize=11)
    for ax in axs:
        ax.annotate("작업대: 다리 4개만", (2.6, 3.6), xytext=(0.2, 1.4), fontsize=9.5, color=RED, arrowprops=dict(arrowstyle="-|>", color=RED))
        ax.annotate("선반: 기둥 + 아래 칸 상자", (-2.6, -2.7), xytext=(-6.8, -0.6), fontsize=9.5, color=BLUE, arrowprops=dict(arrowstyle="-|>", color=BLUE))
    axs[1].texts[-2].set_text("작업대: 상판까지 막힘"); axs[1].texts[-1].set_text("선반: 통째로 막힘")
    fig.suptitle("같은 창고, 다른 지도: SLAM 은 라이다 높이(0.24 m)에서 보이는 것만 그린다", fontsize=12, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, "lesson04_map_compare.png")


def lidar_height():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.9, "라이다는 높이 0.24 m 의 수평면 하나만 본다", bold=True, fs=12)
    k, fl = 3.4, 0.7                                       # 1 m = 3.4 units (same scale both axes)
    ax.plot([0.3, 13.7], [fl, fl], color="#8d7b5a", lw=2)
    zl = fl + 0.239 * k
    # robot (Vic Pinky body ~0.3 m tall, lidar on top of the base)
    ax.add_patch(Rectangle((0.6, fl + 0.03 * k), 1.9, 0.2 * k, fc="#ECEFF1", ec=INK, zorder=3))
    ax.add_patch(Rectangle((1.9, zl - 0.07), 0.3, 0.14, fc="#333333", zorder=4))
    label(ax, 1.55, fl + 0.23 * k + 0.35, "로봇 · 라이다", fs=9)
    # rack: posts, shelves at 0.18 / 0.90 m, box on the bottom shelf 0.215 ~ 0.595 m
    rx, rw = 3.6, 3.6
    for zz in (0.18, 0.90):
        ax.add_patch(Rectangle((rx, fl + (zz - 0.035) * k), rw, 0.07 * k, fc="#8D6E63", ec=INK, lw=0.8, zorder=2))
    for px in (rx, rx + rw - 0.27):
        ax.add_patch(Rectangle((px, fl), 0.27, 1.05 * k, fc="#37474F", zorder=3))
    ax.add_patch(Rectangle((rx + 0.7, fl + 0.215 * k), 2.2, 0.38 * k, fc="#FFE082", ec=INK, lw=0.8, zorder=2))
    label(ax, rx + rw / 2, fl + 1.05 * k + 0.25, "선반: 기둥 · 아래 칸 상자에 맞는다", color=BLUE, fs=9.2)
    # table: top 0.70 ~ 0.78 m, legs
    tx, tw = 8.9, 3.3
    ax.add_patch(Rectangle((tx, fl + 0.70 * k), tw, 0.08 * k, fc="#B0BEC5", ec=INK, zorder=2))
    for px in (tx + 0.15, tx + tw - 0.4):
        ax.add_patch(Rectangle((px, fl), 0.24, 0.70 * k, fc="#546E7A", zorder=2))
    label(ax, tx + tw / 2, fl + 0.78 * k + 0.3, "작업대: 상판(0.70 m)은 안 보인다 · 다리만 맞는다", color=RED, fs=9.2)
    ax.plot([2.2, 13.7], [zl, zl], color=RED, lw=1.6, ls="--", zorder=5)
    label(ax, 12.9, zl + 0.25, "라이다 평면 0.24 m", color=RED, fs=8.8)
    for xx in (rx, rx + 0.7, tx + 0.15):
        ax.add_patch(Circle((xx, zl), 0.08, fc=RED, zorder=6))
    note(ax, 0.3, 0.3, "지도에 없는 것은 Nav2 도 모른다 → 그래서 ⑥ 에서 쓰는 패키지 지도는 작업대를 통째로 막힘으로 그려 두었다.", fs=9.4)
    save(fig, "lesson04_lidar_height.png")


def pose_graph_real():
    """slam_toolbox /slam_toolbox/graph_visualization captured after the loop (artifacts/dev/slam_graph.pkl)."""
    import pickle
    g = pickle.load(open("artifacts/dev/slam_graph.pkl", "rb"))
    nodes = np.array([o[4] for o in g if o[0] == "slam_toolbox"])
    pairs = np.array([o[3] for o in g if o[0] == "slam_toolbox_edges" and o[3]][0]).reshape(-1, 2, 2)
    idx = np.array([[np.argmin(np.hypot(*(nodes - a).T)) for a in pr] for pr in pairs])
    loop = np.abs(idx[:, 0] - idx[:, 1]) > 20
    fig, ax = plt.subplots(figsize=(14, 7.0), dpi=150)
    show_grid(ax, *load_pgm("artifacts/maps/my_warehouse.yaml"))
    for a, b in pairs[~loop]:
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#1976D2", lw=0.8, zorder=3)
    ax.scatter(nodes[:, 0], nodes[:, 1], s=4, color="#0D47A1", zorder=5)
    for a, b in pairs[loop]:
        ax.plot([a[0], b[0]], [a[1], b[1]], color=RED, lw=1.2, alpha=0.8, zorder=7)
    ax.scatter(nodes[:1, 0], nodes[:1, 1], s=80, color=GREEN, edgecolor="white", zorder=8)
    ax.add_patch(Rectangle((-0.4, -1.9), 7.4, 3.1, fc="none", ec=RED, lw=1.2, ls="--", zorder=9))
    ax.text(3.3, -2.2, "빨강이 모인 곳: 돌아오는 길에 출발 구간을 다시 본 가운데 통로", ha="center", fontsize=9.5, color=RED,
            bbox=dict(fc="white", ec="none", alpha=0.85), zorder=10)
    ax.set_title(f"실제 포즈 그래프 (/slam_toolbox/graph_visualization): 노드 {len(nodes)}개 · 이웃 엣지 {int((~loop).sum())}개 · "
                 f"멀리 떨어진 노드를 잇는 엣지(빨강) {int(loop.sum())}개", fontsize=11.5)
    ax.text(-7.6, -5.75, "파랑 점 = 스캔을 쓴 자세 (5 cm 또는 0.05 rad 움직일 때마다) · 초록 = 첫 노드 · 빨강 = 다시 본 곳을 이어 준 제약", fontsize=9.5, color="#333333",
            bbox=dict(fc="white", ec="none", alpha=0.85))
    fig.tight_layout()
    save(fig, "lesson04_pose_graph_real.png")


if __name__ == "__main__":
    for f in (why_slam, slam_loop, occupancy, tf_chain, toolbox_intro, scan_matching, pose_graph, slam_tree, teleop_keys, map_files, yaml_fields,
              launch_branch, params, map_growth, map_compare, lidar_height, pose_graph_real):
        f()
