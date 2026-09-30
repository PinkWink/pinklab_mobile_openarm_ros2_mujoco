"""Figures for the lesson-05 Confluence page (ROS2 Navigation). Output: docs/camp/lesson05_*.png

Run from the workspace root. Data figures read artifacts/dev/nav_run.pkl and nav_amcl.pkl (docs/camp/nav_record.py).
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson03_figures import tiles_at  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

RED, BLUE, GREEN, BROWN, GREY = "#C62828", "#1f4e79", "#2e7d32", "#7a4b00", "#9e9e9e"
FOOT = np.array([[0.38, 0.32], [0.38, -0.32], [-0.38, -0.32], [-0.38, 0.32]])


# ================================================================ 1. Nav2 란
def why_nav():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "⑤ 에서 지도를 만들었다 → ⑥ 에서는 그 지도 위에서 목표까지 간다", bold=True, fs=12)
    chain(ax, [("지도", ["⑤ SLAM · maps/warehouse"]), ("내 위치", ["AMCL: 지도 위 어디?"]), ("경로", ["Planner: 어디로 갈까"]),
               ("속도 명령", ["Controller: 어떻게 따라갈까"]), ("도착", ["목표 자세 · 허용 오차"])],
          y=1.4, h=1.7, gap=0.3, colors=[C["purple"], C["orange"], C["yellow"], C["blue"], C["green"]], tfs=11, fs=8.8)
    note(ax, 0.3, 0.6, "Nav2 = 이 다섯 단계를 서버 여러 개로 나눠 맡고, Behavior Tree 가 순서를 정하는 ROS 2 표준 주행 스택.", fs=9.8)
    save(fig, "lesson05_why_nav.png")


def architecture():
    fig, ax = fig_ax(14, 6.4)
    note(ax, 0.3, 6.1, "Nav2 구성: 목표 하나가 /cmd_vel 이 되기까지", bold=True, fs=12)
    rbox(ax, 0.3, 4.0, 2.4, 1.3, "목표", ["goal 명령 · RViz", "NavigateToPose"], fc=C["purple"], tfs=10.5, fs=8.4)
    rbox(ax, 3.4, 4.0, 2.9, 1.3, "bt_navigator", ["Behavior Tree 실행"], fc=C["yellow"], tfs=10.5, fs=8.6)
    rbox(ax, 7.0, 4.6, 3.0, 1.1, "planner_server", ["NavFn (A*) → /plan"], fc=C["orange"], tfs=10, fs=8.4)
    rbox(ax, 7.0, 3.2, 3.0, 1.1, "controller_server", ["DWB → /cmd_vel"], fc=C["blue"], tfs=10, fs=8.4)
    rbox(ax, 7.0, 1.8, 3.0, 1.1, "behavior_server", ["spin · backup · wait"], fc=C["red"], tfs=10, fs=8.4)
    rbox(ax, 10.8, 4.6, 2.9, 1.1, "global_costmap", ["map 기준 · 창고 전체"], fc=C["grey"], tfs=10, fs=8.4)
    rbox(ax, 10.8, 3.2, 2.9, 1.1, "local_costmap", ["odom 기준 · 5 m × 5 m"], fc=C["grey"], tfs=10, fs=8.4)
    rbox(ax, 10.8, 1.8, 2.9, 1.1, "브리지 (MuJoCo)", ["/cmd_vel → 바퀴"], fc=C["teal"], tfs=10, fs=8.4)
    arrow(ax, (2.7, 4.65), (3.4, 4.65))
    ax.plot([6.3, 6.65], [4.65, 4.65], color=INK, lw=1.6); ax.plot([6.65, 6.65], [2.35, 5.15], color=INK, lw=1.6)
    for y in (5.15, 3.75, 2.35):
        arrow(ax, (6.65, y), (7.0, y))
    for y in (5.15, 3.75):
        ax.plot([10.0, 10.8], [y, y], color=GREY, lw=1.4, ls="--")
    ax.plot([10.0, 10.4], [3.55, 3.55], color=BLUE, lw=1.6); ax.plot([10.4, 10.4], [3.55, 2.35], color=BLUE, lw=1.6); arrow(ax, (10.4, 2.35), (10.8, 2.35), color=BLUE)
    rbox(ax, 0.3, 1.8, 2.8, 1.5, "map_server", ["yaml + pgm → /map"], fc=C["purple"], tfs=10, fs=8.4)
    rbox(ax, 3.4, 1.8, 2.9, 1.5, "amcl", ["/scan + /map", "→ TF map→odom"], fc=C["green"], tfs=10, fs=8.4)
    arrow(ax, (3.1, 2.55), (3.4, 2.55))
    rbox(ax, 0.3, 0.3, 13.4, 0.9, "mobile_lifecycle_manager: map_server → amcl → controller → planner → smoother → behavior → bt_navigator 순서로 켜고 지켜본다", fc=C["grey"], tfs=9.6)
    save(fig, "lesson05_architecture.png")


def lifecycle():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "Lifecycle 노드: 켜는 순서를 정할 수 있는 노드", bold=True, fs=12)
    chain(ax, [("unconfigured", ["막 만들어진 상태"]), ("inactive", ["configure: 파라미터 · 구독 준비"]), ("active", ["activate: 발행 · 서버 동작"]), ("finalized", ["shutdown"])],
          y=1.5, h=1.5, gap=0.45, colors=[C["grey"], C["yellow"], C["green"], C["grey"]], tfs=11, fs=8.6)
    note(ax, 0.3, 0.8, "lifecycle_manager 가 모든 Nav2 노드를 configure → activate 한다 (autostart: true).  하나라도 실패하면 나머지도 켜지 않는다.", fs=9.4)
    note(ax, 0.3, 0.35, "확인: ros2 lifecycle get /amcl  →  active [3]", fs=9.4)
    save(fig, "lesson05_lifecycle.png")


def amcl():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "AMCL: 파티클 수백 개가 '내가 여기 있다면?' 을 동시에 검사한다", bold=True, fs=12)
    chain(ax, [("① 예측", ["odom 만큼 모든 파티클을 옮긴다", "+ 잡음 (alpha1~5)"]), ("② 가중치", ["파티클 자리에서 스캔을 지도에 겹쳐", "잘 맞을수록 무겁게"]),
               ("③ 재추출", ["무거운 파티클을 더 많이 복제", "가벼운 것은 버린다"]), ("④ 추정", ["평균 자세 → /amcl_pose", "TF map → odom 발행"])],
          y=1.5, h=2.1, gap=0.35, colors=[C["blue"], C["orange"], C["yellow"], C["green"]], tfs=11, fs=8.6)
    note(ax, 0.3, 0.9, "움직일 때만 갱신 (update_min_d 0.05 m · update_min_a 0.05 rad).  파티클 500 ~ 2000 개, 퍼져 있으면 많이 · 모이면 적게.", fs=9.4)
    note(ax, 0.3, 0.4, "SLAM 과 달리 지도는 고정 (map_server).  위치만 추정한다.", fs=9.4)
    save(fig, "lesson05_amcl.png")


def costmap_layers():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "Costmap: 지도 + 라이다 + 부풀리기 = 로봇 중심이 들어가면 안 되는 곳", bold=True, fs=12)
    tiles(ax, [("static_layer", ["/map 의 벽 · 선반 (global 만)", "지도에 있는 것"], C["purple"]),
               ("obstacle_layer", ["/scan 으로 지금 보이는 것", "사람 · 지게차 · 지도에 없는 것"], C["orange"]),
               ("inflation_layer", ["장애물 둘레를 0.55 m 부풀림", "가까울수록 비싸다 (scaling 3.0)"], C["yellow"])],
          cols=3, y_top=4.2, gap=0.3, h=1.7, tfs=11, fs=8.8)
    x0, y0, s = 0.6, 0.35, 0.16
    vals = np.clip(1 - (np.abs(np.arange(-8, 9)) - 1) / 7, 0, 1)
    for k, v in enumerate(vals):
        col = "#1a1a1a" if abs(k - 8) <= 1 else plt.cm.RdPu(0.2 + 0.7 * v) if v > 0 else "#f4f4f4"
        ax.add_patch(Rectangle((x0 + k * s * 2.2, y0 + 0.2), s * 2.2, 0.8, fc=col, ec="white", lw=0.5))
    label(ax, x0 + 8.5 * s * 2.2, 1.3, "장애물 (lethal)", fs=8.6)
    label(ax, x0 + 1.0 * s * 2.2, 1.3, "빈칸 (0)", fs=8.6)
    label(ax, x0 + 4.5 * s * 2.2, 0.28, "← 0.55 m 안에서 가까울수록 비싸다", fs=8.4)
    tiles_at(ax, [("footprint", ["0.76 m × 0.64 m 사각형 + 0.03 m", "로봇 모양으로 충돌 검사"], C["blue"]),
                  ("global vs local", ["global: map 기준 창고 전체 → Planner", "local: odom 기준 5 m 창 → Controller"], C["grey"])],
             cols=2, x0=6.8, x1=13.7, y_top=2.2, gap=0.3, h=1.8, tfs=10.2, fs=8.6)
    save(fig, "lesson05_costmap_layers.png")


def planner():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "Planner (NavFn, A*): global costmap 위에서 싸고 짧은 길", bold=True, fs=12)
    ax.set_aspect("equal")
    n, s, x0, y0 = 14, 0.26, 0.6, 0.35
    rng = np.random.default_rng(2)
    wall = {(r, 6) for r in range(3, 14)} | {(r, 10) for r in range(0, 10)}
    for r in range(n):
        for c in range(n):
            col = "#1a1a1a" if (r, c) in wall else "#f4d7e8" if any(abs(r - a) + abs(c - b) == 1 for a, b in wall) else "#f7f7f7"
            ax.add_patch(Rectangle((x0 + c * s, y0 + r * s), s, s, fc=col, ec="#dddddd", lw=0.4))
    path = [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8), (8, 8), (9, 8), (10, 8), (11, 8), (11, 9), (11, 10), (11, 11), (11, 12)]
    xy = np.array([(x0 + (c + 0.5) * s, y0 + (r + 0.5) * s) for r, c in path])
    ax.plot(xy[:, 0], xy[:, 1], color=GREEN, lw=2.4)
    ax.add_patch(Circle(xy[0], 0.1, fc=RED, zorder=5)); ax.add_patch(Circle(xy[-1], 0.1, fc=BLUE, zorder=5))
    tiles_at(ax, [("입력", ["global costmap · 로봇 위치 (map) · 목표"], C["grey"]), ("탐색", ["칸마다 비용 = 거리 + costmap 값", "use_astar: true · allow_unknown: true"], C["orange"]),
                  ("출력", ["/plan (nav_msgs/Path) · 약 1 초마다 다시 계산", "tolerance 0.15 m: 목표 칸이 막혀 있으면 근처로"], C["green"])],
             cols=1, x0=5.2, x1=13.7, y_top=4.2, gap=0.15, h=1.25, tfs=10.2, fs=8.6)
    save(fig, "lesson05_planner.png")


def dwb():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "Controller (DWB): 속도 후보를 굴려 보고 점수가 가장 좋은 것을 낸다", bold=True, fs=12)
    ax.set_aspect("equal")
    cx, cy = 1.4, 1.0
    for w in np.linspace(-0.65, 0.65, 9):
        t = np.linspace(0, 1.7, 30); v = 0.3
        th = w * t; x = cx + (v * np.cos(th)).cumsum() * (1.7 / 30) * 4; y = cy + (v * np.sin(th)).cumsum() * (1.7 / 30) * 4
        best = abs(w - 0.16) < 0.1
        ax.plot(x, y, color=GREEN if best else "#bdbdbd", lw=2.4 if best else 1.1, zorder=3 if best else 2)
    ax.add_patch(Rectangle((cx - 0.35, cy - 0.3), 0.7, 0.6, fc="#ECEFF1", ec=INK, zorder=4))
    ax.plot([cx, 4.4], [cy + 0.05, cy + 1.5], color=BLUE, lw=1.6, ls="--"); label(ax, 4.0, cy + 1.75, "/plan", color=BLUE, fs=9)
    ax.add_patch(Rectangle((3.7, 0.2), 0.3, 0.6, fc="#1a1a1a"))
    tiles_at(ax, [("① 후보", ["vx 15 개 × wz 30 개", "vx ≤ 0.3 m/s · wz ≤ 0.65 rad/s"], C["blue"]), ("② 굴려 보기", ["각 후보로 1.7 s 앞을 시뮬레이션", "가속 한계 0.4 m/s² · 1.0 rad/s²"], C["grey"]),
                  ("③ 점수", ["PathAlign · PathDist · GoalAlign · GoalDist", "ObstacleFootprint · Oscillation · RotateToGoal"], C["orange"]), ("④ 출력", ["가장 싼 후보 → /cmd_vel (15 Hz)"], C["green"])],
             cols=2, x0=5.4, x1=13.7, y_top=4.1, gap=0.25, h=1.6, tfs=10.2, fs=8.4)
    note(ax, 0.6, 0.0, "회색 = 버린 후보,  초록 = 고른 후보", fs=9)
    save(fig, "lesson05_dwb.png")


def bt():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "Behavior Tree (navigate_to_pose 기본 트리): 계획 → 추종, 막히면 복구", bold=True, fs=12)
    rbox(ax, 5.3, 3.3, 3.4, 0.8, "RecoveryNode (재시도 6 번)", fc=C["yellow"], tfs=10)
    rbox(ax, 1.0, 1.8, 5.4, 0.9, "PipelineSequence: 계획 + 추종", fc=C["blue"], tfs=10)
    rbox(ax, 7.6, 1.8, 5.4, 0.9, "복구: costmap 지우기 → spin → wait → backup", fc=C["red"], tfs=9.6)
    rbox(ax, 0.6, 0.4, 3.0, 0.9, "ComputePathToPose", ["1 Hz 로 다시 계획"], fc=C["orange"], tfs=9.6, fs=8.2)
    rbox(ax, 3.9, 0.4, 2.8, 0.9, "FollowPath", ["controller 에 전달"], fc=C["blue"], tfs=9.6, fs=8.2)
    ax.plot([7.0, 7.0], [3.3, 3.0], color=INK, lw=1.6); ax.plot([3.7, 10.3], [3.0, 3.0], color=INK, lw=1.6)
    arrow(ax, (3.7, 3.0), (3.7, 2.7)); arrow(ax, (10.3, 3.0), (10.3, 2.7))
    ax.plot([3.7, 3.7], [1.8, 1.55], color=INK, lw=1.6); ax.plot([2.1, 5.3], [1.55, 1.55], color=INK, lw=1.6)
    arrow(ax, (2.1, 1.55), (2.1, 1.3)); arrow(ax, (5.3, 1.55), (5.3, 1.3))
    note(ax, 7.6, 1.0, "왼쪽이 실패하면 오른쪽(복구)을 한 번 하고 왼쪽을 다시 시도한다.", fs=9.2)
    note(ax, 7.6, 0.55, "이 페이지의 주행에서는 복구 없이 한 번에 성공했다.", fs=9.2)
    save(fig, "lesson05_bt.png")


# ================================================================ 2. 실행
def nav_tree():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "./scripts/mobile_openarm nav moveit:=false  =  warehouse.launch.py mode:=nav moveit:=false", bold=True, fs=12)
    rbox(ax, 0.3, 1.9, 2.7, 1.4, "warehouse.launch.py", ["mode:=nav"], fc=C["purple"], tfs=10.2, fs=8.6)
    items = [("브리지", "/scan · /odom", C["teal"]), ("RSP", "로봇 TF", C["blue"]), ("map_server", "maps/warehouse", C["purple"]), ("amcl", "map→odom", C["green"]),
             ("Nav2 서버", "5 개", C["orange"]), ("lifecycle_manager", "켜는 순서", C["grey"]), ("RViz2", "Fixed Frame map", C["grey"])]
    for k, (t, l, fc) in enumerate(items):
        x = 3.6 + k * 1.44
        rbox(ax, x, 1.9, 1.34, 1.4, t, [l], fc=fc, tfs=8.6, fs=7.2)
        arrow(ax, (x + 0.67, 3.7), (x + 0.67, 3.3))
    ax.plot([3.0, 3.3], [2.6, 2.6], color=INK, lw=1.6); ax.plot([3.3, 3.3], [2.6, 3.7], color=INK, lw=1.6); ax.plot([3.3, 3.6 + 6 * 1.44 + 0.67], [3.7, 3.7], color=INK, lw=1.6)
    ax.add_patch(Rectangle((3.6 + 2 * 1.44 - 0.07, 1.8), 1.44 * 4 - 0.02, 1.6, fc="none", ec=RED, lw=1.5, ls="--"))
    label(ax, 3.6 + 4 * 1.44 - 0.1, 1.5, "navigation.launch.py 가 붙이는 것 (map:= 이 있을 때)", color=RED, fs=9)
    note(ax, 0.3, 0.7, "map 인자 기본값 = maps/warehouse.yaml (패키지 지도).  ⑤ 에서 만든 지도: map:=$PWD/artifacts/maps/my_warehouse.yaml", fs=9.4)
    note(ax, 0.3, 0.25, "start (= nav) 는 moveit:=true 가 기본 → MoveIt 까지 뜬다. 이 페이지는 주행만 보려고 moveit:=false.", fs=9.4)
    save(fig, "lesson05_nav_tree.png")


def goal_ways():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "목표를 보내는 세 가지 방법 (모두 map 좌표)", bold=True, fs=12)
    tiles(ax, [("goal 명령", ["./scripts/mobile_openarm goal X Y YAW", "NavigateToPose 액션 클라이언트", "결과(SUCCEEDED)까지 기다린다"], C["orange"]),
               ("RViz: 2D Goal Pose", ["버튼 → 지도 위를 누르고 끌어 방향", "/goal_pose 토픽 → bt_navigator", "결과는 터미널 1 로그로 본다"], C["blue"]),
               ("코드 (Day 2)", ["warehouse_skills 가 같은 액션을 부른다", "pick & place · LMM 작업 순서", "locations.yaml 의 이름 → 좌표"], C["green"])],
          cols=3, y_top=3.6, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 0.9, "장소 좌표: warehouse_lecture/worlds/locations.yaml  (pick_table 의 base_goal = [1.2, -3.6, 0.0])", fs=9.4)
    save(fig, "lesson05_goal_ways.png")


def initialpose_ways():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "AMCL 에게 첫 위치를 알려 주는 방법", bold=True, fs=12)
    tiles(ax, [("nav2.yaml", ["set_initial_pose: true", "initial_pose (0, 0, 0) = 창고 원점", "로봇이 원점에서 시작하면 그대로"], C["purple"]),
               ("launch 인자 spawn", ["spawn:=pick_table 또는 X,Y,YAW", "MuJoCo 로봇 위치 + AMCL 초기값", "둘을 같이 맞춘다"], C["orange"]),
               ("RViz: 2D Pose Estimate", ["버튼 → 지도 위를 끌어 위치 · 방향", "/initialpose 토픽", "틀어졌을 때 손으로 다시 알려 주기"], C["blue"])],
          cols=3, y_top=3.4, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 0.65, "실습: /initialpose 로 일부러 0.72 m · 23° 틀린 위치를 주고, 달리면서 AMCL 이 바로잡는지 본다.", fs=9.6)
    save(fig, "lesson05_initialpose_ways.png")


# ================================================================ 4. 코드
def goal_flow():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "goal.py: NavigateToPose 액션을 보내고 결과를 기다린다", bold=True, fs=12)
    chain(ax, [("ActionClient", ["/navigate_to_pose"]), ("서버 대기", ["wait_for_server 30 s", "/clock 대기 (sim time)"]), ("Goal 만들기", ["frame_id: map", "yaw → 쿼터니언 (z, w)"]),
               ("send_goal_async", ["accepted 확인"]), ("get_result_async", ["status 4 = SUCCEEDED", "시간 초과면 cancel"])],
          y=1.2, h=1.8, gap=0.25, colors=[C["purple"], C["grey"], C["orange"], C["blue"], C["green"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.5, "실행 파일 이름 goal: mobile_openarm_navigation 의 setup.py console_scripts.  wrapper 가 ros2 run 으로 부른다.", fs=9.4)
    save(fig, "lesson05_goal_flow.png")


def nav_branch():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "navigation.launch.py: mode:=nav 이고 map 이 있으면", bold=True, fs=12)
    chain(ax, [("map 파일 확인", ["없으면 RuntimeError"]), ("map_server", ["yaml_filename = map"]), ("amcl", ["initial_pose = spawn 값"]),
               ("Nav2 서버 5개", ["controller · planner · smoother", "behavior · bt_navigator"]), ("lifecycle_manager", ["node_names = 위 7 개", "autostart · bond_timeout 10 s"])],
          y=1.2, h=1.8, gap=0.25, colors=[C["grey"], C["purple"], C["green"], C["orange"], C["yellow"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.5, "파라미터는 전부 config/nav2.yaml 한 파일에서 읽는다 (노드 이름이 yaml 의 최상위 키).", fs=9.4)
    save(fig, "lesson05_nav_branch.png")


def params():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "nav2.yaml 에서 볼 파라미터", bold=True, fs=12)
    tiles(ax, [("amcl", ["min/max_particles: 500 / 2000", "laser_model: likelihood_field", "max_beams: 90", "initial_pose: (0, 0, 0)"], C["green"]),
               ("controller (DWB)", ["max_vel_x: 0.3 · max_vel_theta: 0.65", "acc_lim_x: 0.4", "sim_time: 1.7", "xy_goal_tolerance: 0.08"], C["blue"]),
               ("costmap", ["inflation_radius: 0.55", "footprint: 0.76 × 0.64 m", "local: 5 × 5 m, odom", "global: map, static layer"], C["grey"]),
               ("planner · bt", ["NavfnPlanner · use_astar: true", "tolerance: 0.15", "default_server_timeout: 200 ms", "yaw_goal_tolerance: 0.15"], C["orange"])],
          cols=4, y_top=4.2, gap=0.25, h=2.55, tfs=11, fs=8.5)
    note(ax, 0.3, 1.05, "파일: src/mobile_openarm_navigation/config/nav2.yaml  (symlink 설치: 고치면 다시 빌드하지 않아도 다음 실행에 반영)", fs=9.6)
    note(ax, 0.3, 0.5, "default_server_timeout 을 20 ms 로 두면 부하가 큰 PC 에서 경로 요청이 ABORTED 된다 → 200 ms 로 늘려 둠.", fs=9.6)
    save(fig, "lesson05_params.png")


# ================================================================ data figures
COSTCMAP = ListedColormap(["#f4f4f4"] + [plt.cm.RdPu(v) for v in np.linspace(0.15, 0.75, 97)] + ["#6a1b9a", "#1a1a1a", "#8a9a9c"])


def show_cost(ax, g):
    d = g["data"].copy().astype(float)
    code = np.where(d < 0, 100, d)                         # 0 free .. 99 inscribed, 100 lethal, unknown drawn grey
    code = np.where(g["data"] < 0, 101, code)
    h, w = d.shape
    ax.imshow(code, cmap=COSTCMAP, vmin=0, vmax=101, origin="lower", interpolation="nearest",
              extent=[g["origin"][0], g["origin"][0] + w * g["res"], g["origin"][1], g["origin"][1] + h * g["res"]])
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])


def footprint(ax, x, y, a, **kw):
    c, s = np.cos(a), np.sin(a)
    ax.add_patch(Polygon(FOOT @ np.array([[c, s], [-s, c]]) + [x, y], closed=True, **kw))


def segments(d):
    """Split plans into the two goals (a new goal = the plan's start jumps back to the robot far from the last goal)."""
    ends = [p["xy"][-1] for p in d["plans"]]
    cut = [0] + [i for i in range(1, len(ends)) if np.hypot(*(ends[i] - ends[i - 1])) > 0.5]
    return [d["plans"][a:b] for a, b in zip(cut, cut[1:] + [len(ends)])]


def global_plan():
    d = pickle.load(open("artifacts/dev/nav_run.pkl", "rb"))
    tr = np.array(d["truth"])
    segs = segments(d)
    fig, axs = plt.subplots(1, 2, figsize=(12, 6.4), dpi=150)
    for ax, seg, title in zip(axs, segs, ("goal 명령: (0, 0) → 픽업 작업대 앞 (1.2, -3.6)", "RViz 2D Goal Pose: → 가운데 (0.02, 0.02)")):
        show_cost(ax, d["global_costmap"])
        for k, p in enumerate(seg[::3]):
            ax.plot(p["xy"][:, 0], p["xy"][:, 1], color="#43A047", lw=0.9, alpha=0.35)
        ax.plot(seg[0]["xy"][:, 0], seg[0]["xy"][:, 1], color="#1B5E20", lw=2.0, label="첫 /plan")
        t0, t1 = seg[0]["t"], seg[-1]["t"] + 3
        m = (tr[:, 0] >= t0) & (tr[:, 0] <= t1)
        ax.plot(tr[m, 1], tr[m, 2], color="#1565C0", lw=1.8, ls="--", label="실제로 간 길 (/ground_truth)")
        s, e = tr[m][0], tr[m][-1]
        footprint(ax, s[1], s[2], s[3], fc="none", ec=RED, lw=1.5); footprint(ax, e[1], e[2], e[3], fc="none", ec="#0D47A1", lw=1.5)
        ax.set_xlim(-2.6, 4.2); ax.set_ylim(-5.2, 1.4)
        ax.set_title(f"{title}  ·  /plan {len(seg)} 번 갱신", fontsize=10.5)
        ax.legend(loc="upper left", fontsize=8.5)
    fig.suptitle("global costmap (분홍 = 부풀린 비용, 검정 = 장애물) 위의 경로: 연초록 = 다시 계산한 /plan 들", fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "lesson05_global_plan.png")


def local_costmap():
    d = pickle.load(open("artifacts/dev/nav_run.pkl", "rb"))
    tr = np.array(d["truth"]); od = np.array(d["odom"])
    t0 = segments(d)[0][0]["t"]
    L = [g for g in d["local"] if g["t"] >= t0]
    pick = [L[2], L[10], L[20]]
    fig, axs = plt.subplots(1, 3, figsize=(14, 5.0), dpi=150)
    for ax, g in zip(axs, pick):
        show_cost(ax, g)
        i = np.argmin(abs(od[:, 0] - g["t"]))
        footprint(ax, od[i, 1], od[i, 2], od[i, 3], fc="none", ec=RED, lw=1.8)
        ax.set_title(f"시뮬레이션 {g['t'] - t0:.0f} s  ·  v {od[i, 4]:.2f} m/s", fontsize=10.5)
    fig.suptitle("local costmap (odom 기준 5 m × 5 m, 로봇을 따라 움직이는 창): /scan 으로 보이는 것만 · 빨강 = footprint", fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "lesson05_local_costmap.png")


def speed():
    d = pickle.load(open("artifacts/dev/nav_run.pkl", "rb"))
    od = np.array(d["odom"]); segs = segments(d)
    t0 = segs[0][0]["t"] - 1
    m = (od[:, 0] >= t0) & (od[:, 0] <= segs[-1][-1]["t"] + 5)
    fig, ax = plt.subplots(figsize=(14, 3.8), dpi=150)
    ax.plot(od[m, 0] - t0, od[m, 4], color=BLUE, lw=1.6, label="v  (/odom linear.x) [m/s]")
    ax.plot(od[m, 0] - t0, od[m, 5], color=BROWN, lw=1.2, alpha=0.8, label="w  (/odom angular.z) [rad/s]")
    ax.axhline(0.3, color=BLUE, ls=":", lw=1); ax.axhline(0.65, color=BROWN, ls=":", lw=1); ax.axhline(-0.65, color=BROWN, ls=":", lw=1)
    ax.text(0.5, 0.32, "max_vel_x 0.3", color=BLUE, fontsize=9); ax.text(0.5, 0.55, "max_vel_theta 0.65", color=BROWN, fontsize=9)
    for s in segs:
        ax.axvline(s[0]["t"] - t0, color=GREEN, lw=1.2, ls="--")
    ax.set_xlabel("시뮬레이션 시각 [s]"); ax.grid(alpha=0.3); ax.legend(loc="lower right", fontsize=9)
    ax.set_title("Controller 가 낸 속도: 돌면서 출발 → 0.3 m/s 순항 → 감속 → 멈춰서 목표 방향으로 회전  (초록 점선 = 새 목표)", fontsize=11)
    fig.tight_layout()
    save(fig, "lesson05_speed.png")


def amcl_particles():
    d = pickle.load(open("artifacts/dev/nav_amcl.pkl", "rb"))
    tr = np.array(d["truth"])
    P = d["particles"]
    pick = [P[0], P[3], P[6], P[-1]]
    fig, axs = plt.subplots(1, 4, figsize=(14, 3.6), dpi=150)
    for ax, p in zip(axs, pick):
        show_cost(ax, d["global_costmap"])
        xyt = p["xyt"]
        ax.quiver(xyt[:, 0], xyt[:, 1], np.cos(xyt[:, 2]), np.sin(xyt[:, 2]), color="#E53935", scale=40, width=0.004, alpha=0.5)
        i = np.argmin(abs(tr[:, 0] - p["t"]))
        ax.add_patch(Circle((tr[i, 1], tr[i, 2]), 0.12, fc="#1565C0", ec="white", zorder=6))
        ax.add_patch(Circle((0.6, 0.4), 0.1, fc="none", ec=BROWN, lw=1.5, zorder=6))
        m = xyt[:, :2].mean(0); e = np.hypot(*(m - tr[i, 1:3]))
        ax.set_xlim(-1.2, 4.0); ax.set_ylim(-1.6, 1.8)
        ax.set_title(f"{p['t'] - P[0]['t']:.1f} s · 파티클 {len(xyt)} · 퍼짐 {xyt[:, 0].std():.2f} m\n평균 - 실제 = {e * 100:.0f} cm", fontsize=9.5)
    fig.suptitle("AMCL 파티클 (빨강 화살표): 틀린 초기 위치(갈색 원 0.6, 0.4, 23°)에서 출발 → 달리면서 실제 위치(파랑)로 모인다", fontsize=11.5, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    save(fig, "lesson05_amcl_particles.png")


def amcl_compare():
    S = Path("/tmp/claude-1000/-home-pw-mujoco-ros2/1beb48be-36fd-4f55-82d9-6f1896714b3d/scratchpad")
    a = Image.open(S / "amcl_wrong.png").crop((1470, 130, 2230, 866))
    b = Image.open(S / "amcl_after.png").crop((1470, 130, 2230, 866))
    fig, axs = plt.subplots(1, 2, figsize=(14, 7.0), dpi=150)
    for ax, im, t in zip(axs, (a, b), ("/initialpose 로 틀린 위치를 준 직후: 라이다 점이 벽과 어긋난다", "3.5 m 달린 뒤: AMCL 이 바로잡아 라이다 점이 벽에 겹친다")):
        ax.imshow(im); ax.axis("off"); ax.set_title(t, fontsize=10.5)
    fig.tight_layout()
    save(fig, "lesson05_amcl_compare.png")


if __name__ == "__main__":
    for f in (why_nav, architecture, lifecycle, amcl, costmap_layers, planner, dwb, bt, nav_tree, goal_ways, initialpose_ways, goal_flow, nav_branch, params,
              global_plan, local_costmap, speed, amcl_particles, amcl_compare):
        f()
