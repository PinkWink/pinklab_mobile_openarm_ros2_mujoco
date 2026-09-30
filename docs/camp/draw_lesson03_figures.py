"""Figures for the lesson-03 Confluence page (bringup, sensors, TF, odometry). Output: docs/camp/lesson03_*.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, cross, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch  # noqa: E402
import numpy as np  # noqa: E402


def tiles_at(ax, items, cols, x0, x1, y_top, gap=0.25, h=1.6, tfs=10.5, fs=8.6):
    w = (x1 - x0 - gap * (cols - 1)) / cols
    for i, (title, lines, fc) in enumerate(items):
        r, c = divmod(i, cols)
        rbox(ax, x0 + c * (w + gap), y_top - (r + 1) * h - r * gap, w, h, title, lines, fc=fc, tfs=tfs, fs=fs, align="left", dy=0.3)


# ================================================================ 1. bringup
def bringup_tree():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "warehouse.launch.py 가 띄우는 것", bold=True, fs=12)
    rbox(ax, 0.3, 1.4, 3.0, 1.5, "warehouse.launch.py", ["ros2 launch 하나"], fc=C["purple"], tfs=10.5, fs=8.8)
    # always
    ax.add_patch(Rectangle((4.2, 2.3), 4.3, 1.5, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 4.35, 3.55, "항상", bold=True, fs=10, color="#2e7d32")
    rbox(ax, 4.35, 2.45, 1.95, 0.85, "브리지(MuJoCo)", fc=C["teal"], tfs=9.6)
    rbox(ax, 6.45, 2.45, 1.9, 0.85, "robot_state_\npublisher", fc=C["blue"], tfs=9.2)
    # optional
    ax.add_patch(Rectangle((4.2, 0.4), 9.5, 1.5, fc="#FFFBF0", ec="#D9C48A", lw=1.2, zorder=1))
    note(ax, 4.35, 1.65, "인자로 켜고 끔", bold=True, fs=10, color="#7a4b00")
    rbox(ax, 4.35, 0.55, 2.9, 0.85, "Nav2  (mode≠drive)", fc=C["yellow"], tfs=9.8)
    rbox(ax, 7.4, 0.55, 2.9, 0.85, "MoveIt  (moveit:=true)", fc=C["orange"], tfs=9.8)
    rbox(ax, 10.45, 0.55, 3.1, 0.85, "RViz2  (rviz:=true)", fc=C["grey"], tfs=9.8)
    ax.plot([3.3, 3.75], [2.15, 2.15], color=INK, lw=1.6); ax.plot([3.75, 3.75], [1.15, 3.05], color=INK, lw=1.6)
    arrow(ax, (3.75, 3.05), (4.2, 3.05)); arrow(ax, (3.75, 1.15), (4.2, 1.15))
    note(ax, 9.0, 3.05, "이 페이지: drive 모드 = 항상 + RViz2", fs=9.5)
    save(fig, "lesson03_bringup_tree.png")


def bringup_modes():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "mode 인자: 무엇을 더 띄우나", bold=True, fs=12)
    tiles(ax, [("drive", ["브리지 + RSP (+ RViz2)", "Nav2 없음 · TF 는 odom 까지", "이 페이지 · 센서와 odom 을 그대로 본다"], C["green"]),
               ("slam", ["+ slam_toolbox + Nav2", "map → odom 을 SLAM 이 만든다", "지도 작성 (다음 페이지)"], C["yellow"]),
               ("nav (기본)", ["+ map_server + AMCL + Nav2", "map → odom 을 AMCL 이 만든다", "저장된 지도로 자율주행"], C["blue"])],
          cols=3, y_top=3.5, gap=0.3, h=2.3, tfs=11.5, fs=8.6)
    note(ax, 0.3, 0.6, "공통 인자: viewer · rviz · moveit · spawn · profile(lite/full) · camera_handler · actors", fs=9.5)
    save(fig, "lesson03_bringup_modes.png")


def bringup_cmd():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "wrapper 명령 → launch 인자", bold=True, fs=12)
    rows = (("./scripts/mobile_openarm drive", "mode:=drive moveit:=false", C["green"]), ("./scripts/mobile_openarm slam", "mode:=slam moveit:=false", C["yellow"]),
            ("./scripts/mobile_openarm start  (= nav)", "mode:=nav", C["blue"]), ("./scripts/mobile_openarm moveit", "mode:=drive moveit:=true", C["orange"]))
    for k, (a, b, fc) in enumerate(rows):
        y = 2.95 - k * 0.72
        rbox(ax, 0.3, y - 0.28, 5.2, 0.6, a, fc=fc, tfs=9.8); arrow(ax, (5.5, y + 0.02), (6.1, y + 0.02)); rbox(ax, 6.1, y - 0.28, 7.6, 0.6, "ros2 launch mobile_openarm_bringup warehouse.launch.py " + b, fc=C["grey"], tfs=9.2)
    note(ax, 0.3, 0.25, "wrapper 는 ROS_DOMAIN_ID 43 · CycloneDDS · MOBILE_OPENARM_MODEL_DIR 을 맞춘 뒤 launch 를 부른다.  뒤에 인자:=값 을 더 붙일 수 있다.", fs=9.2)
    save(fig, "lesson03_bringup_cmd.png")


# ================================================================ 2. sensors
def sensors_overview():
    fig, ax = fig_ax(14, 6.4)
    note(ax, 0.3, 6.1, "브리지가 재는 것과 내는 것", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 0.5), 4.2, 5.3, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 0.5, 5.55, "MuJoCo 안에서 재는 것", bold=True, fs=10.5, color="#2e7d32")
    tiles_at(ax, [("라이다", ["site lidar 에서 360줄 레이캐스트"], C["green"]), ("바퀴 엔코더", ["바퀴 관절 qpos 의 변화량"], C["green"]),
                  ("관절 각도", ["팔 · 그리퍼 qpos · qvel"], C["green"]), ("카메라 4대", ["Renderer 로 픽셀 렌더"], C["green"]), ("시뮬레이션 시각", ["data.time"], C["green"])],
             cols=1, x0=0.5, x1=4.3, y_top=5.3, gap=0.1, h=0.86, tfs=9.6, fs=7.8)
    ax.add_patch(Rectangle((9.5, 0.5), 4.2, 5.3, fc="#F4F8FF", ec="#8FA9D6", lw=1.2, zorder=1))
    note(ax, 9.7, 5.55, "ROS 2 로 내는 것", bold=True, fs=10.5, color="#1f4e79")
    tiles_at(ax, [("/scan  LaserScan", ["frame laser_link · 10 Hz"], C["blue"]), ("/odom + TF odom→base_footprint", ["50 Hz"], C["blue"]),
                  ("/joint_states", ["50 Hz → RSP 가 /tf"], C["blue"]), ("/vision/*  (영상 토픽 없음)", ["같은 프로세스의 핸들러가 검출"], C["blue"]), ("/clock", ["매 틱 100 Hz"], C["blue"])],
             cols=1, x0=9.7, x1=13.5, y_top=5.3, gap=0.1, h=0.86, tfs=9.6, fs=7.8)
    rbox(ax, 5.2, 0.6, 3.6, 4.7, "브리지 루프 100 Hz", ["mj_step × 5 (10 ms)", "→ 오도메트리 적분", "→ 주기마다 발행", "← /cmd_vel 수신"], fc=C["purple"], tfs=10.5, fs=8.6)
    for k in range(5):
        y = 5.3 - 0.43 - k * 0.96
        arrow(ax, (4.3, y), (5.2, y), color="#2e7d32", lw=1.2)
        arrow(ax, (8.8, y), (9.7, y), color="#1f4e79", lw=1.2)
    note(ax, 0.3, 0.15, "센서 값은 전부 MuJoCo 상태에서 계산한 값이다. 노이즈는 넣지 않았다 (이상적인 센서).", fs=9.2)
    save(fig, "lesson03_sensors_overview.png")


def bridge_process():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "warehouse.launch.py → 브리지 프로세스 하나 = bridge.py + model.py", bold=True, fs=12)
    rbox(ax, 0.3, 1.5, 2.9, 1.9, "warehouse.launch.py", ["ExecuteProcess", "python -m", "mobile_openarm_mujoco.bridge"], fc=C["purple"], tfs=10.5, fs=8.8)
    ax.add_patch(Rectangle((3.8, 0.5), 6.9, 3.85, fc="#F7F7F9", ec="#9A9AA6", lw=1.2, ls="--", zorder=1))
    note(ax, 3.95, 4.1, "프로세스 1개 · 노드 이름 mobile_openarm_mujoco", bold=True, fs=10, color="#444444")
    rbox(ax, 4.0, 0.7, 3.2, 3.1, "bridge.py  (Bridge 노드)", ["main(): Physics(...) 생성", "while 루프 100 Hz", "  → advance()", "  → publish_state()", "ROS 2 발행 · /cmd_vel 수신"], fc=C["teal"], tfs=10.2, fs=8.6, align="left")
    rbox(ax, 7.8, 0.7, 2.7, 3.1, "model.py  (Physics)", ["MuJoCo model · data", "step(): mj_step × 5", "  + odom 적분", "scan(): mj_multiRay", "pose() · 관절 상태"], fc=C["green"], tfs=10.2, fs=8.6, align="left")
    arrow(ax, (7.2, 2.75), (7.8, 2.75)); label(ax, 7.5, 3.05, "호출", fs=8.4)
    arrow(ax, (7.8, 1.6), (7.2, 1.6)); label(ax, 7.5, 1.3, "결과", fs=8.4)
    arrow(ax, (3.2, 2.45), (3.8, 2.45))
    rbox(ax, 11.3, 0.7, 2.4, 3.1, "ROS 2 토픽", ["/scan", "/odom · TF", "/joint_states", "/clock"], fc=C["blue"], tfs=10.2, fs=8.8, align="left")
    arrow(ax, (10.7, 2.25), (11.3, 2.25))
    note(ax, 0.3, 0.15, "robot_state_publisher · RViz2 는 같은 launch 가 띄우는 별도 프로세스다.", fs=9.2)
    save(fig, "lesson03_bridge_process.png")


def lidar_ray():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "라이다: laser_link 의 site 에서 360줄을 쏜다", bold=True, fs=12)
    ax.set_aspect("equal")
    cx, cy = 3.0, 2.3
    ax.add_patch(Rectangle((cx - 0.5, cy - 0.35), 1.0, 0.7, fc="#555555", ec=INK, zorder=3)); ax.add_patch(Circle((cx, cy), 0.1, fc="#E53935", ec=INK, zorder=5))
    label(ax, cx, cy - 0.7, "site \"lidar\" (laser_link)", fs=8.8)
    for k in range(24):
        a = 2 * np.pi * k / 24
        L = 1.9 if k % 6 else 1.2
        ax.plot([cx, cx + L * np.cos(a)], [cy, cy + L * np.sin(a)], color="#C62828", lw=0.8, alpha=0.7, zorder=2)
    ax.add_patch(Rectangle((cx + 1.0, cy + 0.6), 0.5, 0.9, fc="#B0BEC5", ec=INK, zorder=4)); label(ax, cx + 1.25, cy + 1.75, "geom group 0 (충돌)", fs=8.2)
    label(ax, cx, cy - 1.1, "각도 -180° ~ 179° · 1° 간격", fs=8.8)
    tiles_at(ax, [("mj_multiRay", ["360개 방향을 한 번에", "site 자세(site_xmat)로 회전"], C["green"]), ("맞추는 것", ["geom group 0 만 (ray_group)", "마커 · 시각용 geom 은 무시"], C["yellow"]),
                  ("거리 정리", ["range_min 0.05 · range_max 20 m", "밖이면 inf"], C["grey"]), ("→ LaserScan", ["frame_id laser_link", "10 Hz (scan_hz)"], C["blue"])],
             cols=2, x0=6.5, x1=13.7, y_top=4.6, gap=0.25, h=1.55, tfs=10.5, fs=8.4)
    note(ax, 6.5, 0.8, "laser_link 는 base_link 기준 yaw 180° 다. 스캔 각도는 laser_link 기준이라 TF 가 이를 풀어 준다.", fs=9.0)
    save(fig, "lesson03_lidar_ray.png")


def lidar_msg():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "sensor_msgs/LaserScan 한 장", bold=True, fs=12)
    tiles(ax, [("header", ["stamp = 시뮬레이션 시각", "frame_id = laser_link"], C["grey"]), ("각도", ["angle_min -π · angle_max +π-1°", "angle_increment 1° (0.01745 rad)"], C["yellow"]),
               ("거리", ["range_min 0.05 · range_max 20 m", "ranges[360] (m) · 밖이면 inf"], C["green"]), ("시간", ["scan_time 0.1 s (10 Hz)", "time_increment 0 (동시 측정)"], C["blue"])],
          cols=4, y_top=3.5, gap=0.25, h=1.9, tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.9, "ranges[i] 의 각도 = angle_min + i × angle_increment.  i = 180 이 정면(0°).", fs=9.5)
    note(ax, 0.3, 0.45, "실측: 정면 7.69 m · 좌 5.50 m · 후 7.32 m · 우 5.50 m (시작 위치, 창고 벽까지)", fs=9.5)
    save(fig, "lesson03_lidar_msg.png")


def wheel_encoder():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "바퀴 엔코더 = 바퀴 관절 각도 qpos", bold=True, fs=12)
    chain(ax, [("left/right_wheel_joint", ["continuous hinge", "MJCF joint · velocity 액추에이터"]), ("data.qpos[wheel_q]", ["누적 회전각 (rad)", "실제 로봇의 엔코더 카운트"]),
               ("스텝 전후 차이 × 반지름", ["dl · dr (m)", "radius 0.0825 m (모델에서 읽음)"]), ("오도메트리", ["ds = (dl + dr) / 2", "da = (dr - dl) / track"])],
          y=1.3, h=2.1, colors=[C["grey"], C["green"], C["yellow"], C["orange"]], tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.6, "/joint_states 에도 같은 값이 나간다 (left_wheel_joint · right_wheel_joint 의 position · velocity).", fs=9.5)
    save(fig, "lesson03_wheel_encoder.png")


def cameras():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "카메라 4대: 영상 토픽 없이 같은 프로세스에서 처리", bold=True, fs=12)
    chain(ax, [("MJCF <camera> × 4", ["base · head · left/right_wrist", "cameras.yaml 의 위치 · fovy"]), ("CameraRig · Renderer", ["320×240 (lite) · 2 FPS", "depth · segmentation 선택"]),
               ("CameraPump → 핸들러", ["--camera-handler module:Class", "handler(frames) 호출"]), ("/vision/*", ["detections · markers · stats", "영상은 안 보낸다"])],
          y=1.3, h=2.1, colors=[C["green"], C["green"], C["purple"], C["blue"]], tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.6, "이유: 640×480 영상 4장을 토픽으로 보내면 저사양 노트북이 버티지 못한다. 카메라 활용은 뒤 모듈(비전 · ArUco 도킹)에서 다룬다.", fs=9.2)
    save(fig, "lesson03_cameras.png")


def clock_tf():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "/clock 과 TF: 시간과 프레임의 출처", bold=True, fs=12)
    rbox(ax, 0.3, 2.4, 4.0, 1.5, "/clock (브리지, 매 틱)", ["data.time → rosgraph_msgs/Clock", "use_sim_time 노드가 이 시각을 쓴다"], fc=C["green"], tfs=10.5, fs=8.4)
    rbox(ax, 0.3, 0.5, 4.0, 1.5, "모든 메시지의 stamp", ["/scan · /odom · /joint_states · TF", "전부 같은 시뮬레이션 시각"], fc=C["grey"], tfs=10.5, fs=8.4)
    rbox(ax, 5.0, 2.4, 4.0, 1.5, "브리지가 내는 TF", ["odom → base_footprint", "(바퀴 오도메트리, 50 Hz)"], fc=C["teal"], tfs=10.5, fs=8.4)
    rbox(ax, 5.0, 0.5, 4.0, 1.5, "robot_state_publisher 가 내는 TF", ["base_footprint 아래 링크 46개", "/tf (관절) · /tf_static (고정)"], fc=C["blue"], tfs=10.5, fs=8.4)
    rbox(ax, 9.7, 1.4, 4.0, 1.6, "drive 모드의 TF 뿌리", ["odom 이 최상위", "map → odom 은 SLAM · AMCL 이 붙인다", "(다음 페이지)"], fc=C["yellow"], tfs=10.5, fs=8.4)
    arrow(ax, (9.0, 3.15), (9.7, 2.6)) if False else None
    ax.plot([9.0, 9.35], [3.15, 3.15], color=INK, lw=1.4); ax.plot([9.35, 9.35], [1.25, 3.15], color=INK, lw=1.4); ax.plot([9.0, 9.35], [1.25, 1.25], color=INK, lw=1.4); arrow(ax, (9.35, 2.2), (9.7, 2.2))
    save(fig, "lesson03_clock_tf.png")


def rates():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "발행 주기: 설정값(mujoco.yaml rates) 과 ros2 topic hz 실측", bold=True, fs=12)
    tiles(ax, [("/clock", ["설정 100 Hz (bridge_hz)", "실측 81.9 Hz"], C["grey"]), ("/odom · TF", ["설정 50 Hz (state_hz)", "실측 40.9 Hz"], C["teal"]),
               ("/joint_states", ["설정 50 Hz (state_hz)", "실측 42.4 Hz"], C["blue"]), ("/scan", ["설정 10 Hz (scan_hz)", "실측 6.75 Hz"], C["yellow"])],
          cols=4, y_top=3.5, gap=0.25, h=1.7, tfs=10.5, fs=8.6)
    note(ax, 0.3, 1.1, "실측이 설정보다 낮은 이유: hz 는 벽시계 기준이고, 뷰어 · RViz2 · 카메라 2대를 켠 이 PC 에서 시뮬레이션이 실시간의 약 0.82배로 돌기 때문이다.", fs=9.2)
    note(ax, 0.3, 0.65, "시뮬레이션 시각 기준으로는 설정값 그대로다.  headless(viewer:=false rviz:=false) 로 띄우면 실시간에 가깝다.", fs=9.2)
    save(fig, "lesson03_rates.png")


# ================================================================ 3. odometry
def diffdrive():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "차동 구동 기구학: (v, w) ↔ 좌우 바퀴", bold=True, fs=12)
    ax.set_aspect("equal")
    cx, cy = 3.0, 2.2
    ax.add_patch(Rectangle((cx - 1.0, cy - 0.7), 2.0, 1.4, fc="#ECEFF1", ec=INK, lw=1.2, zorder=2))
    ax.add_patch(Rectangle((cx - 1.15, cy + 0.55), 0.35, 0.5, fc="#333333", ec=INK, zorder=3)); ax.add_patch(Rectangle((cx - 1.15, cy - 1.05), 0.35, 0.5, fc="#333333", ec=INK, zorder=3))
    label(ax, cx - 0.97, cy + 1.35, "왼쪽 바퀴 ωL", fs=8.6); label(ax, cx - 0.97, cy - 1.35, "오른쪽 바퀴 ωR", fs=8.6)
    arrow(ax, (cx, cy), (cx + 1.6, cy), color="#1f4e79", lw=2); label(ax, cx + 1.9, cy + 0.25, "v", color="#1f4e79", fs=10)
    ax.add_patch(FancyArrowPatch((cx + 0.6, cy - 0.5), (cx + 0.6, cy + 0.5), connectionstyle="arc3,rad=0.5", arrowstyle="-|>", mutation_scale=14, color="#7a4b00", lw=1.6))
    label(ax, cx + 1.0, cy + 0.7, "w", color="#7a4b00", fs=10)
    ax.plot([cx - 0.97, cx - 0.97], [cy - 0.8, cy + 0.8], color="#C62828", lw=1, ls="--"); label(ax, cx - 0.55, cy, "track 0.4288 m", color="#C62828", fs=8.2)
    tiles_at(ax, [("명령 → 바퀴 (step 앞부분)", ["ωL = (v - w·track/2) / r", "ωR = (v + w·track/2) / r", "r = 0.0825 m"], C["orange"]),
                  ("바퀴 → 이동 (step 뒷부분)", ["dl = ΔqL · r ,  dr = ΔqR · r", "ds = (dl + dr) / 2", "da = (dr - dl) / track"], C["green"])],
             cols=2, x0=6.2, x1=13.7, y_top=4.0, gap=0.3, h=1.9, tfs=10.5, fs=8.6)
    note(ax, 6.2, 1.5, "같은 두 식을 앞으로 쓰면 제어, 거꾸로 쓰면 오도메트리다.", fs=9.5, bold=True)
    note(ax, 6.2, 1.05, "track 과 r 은 MJCF 에서 읽는다 (Physics.__init__). 실제 로봇에서는 이 두 값의 오차가 곧 오도메트리 오차다.", fs=9.0)
    save(fig, "lesson03_diffdrive.png")


def step_cmd():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "step() 앞부분: /cmd_vel → 바퀴 목표 속도", bold=True, fs=12)
    chain(ax, [("(linear, angular)", ["receive_command 가 저장", "max 0.35 m/s · 0.7 rad/s"]), ("가속 제한", ["0.45 m/s² · 1.0 rad/s²", "dt = 10 ms 마다 조금씩"]),
               ("바퀴 각속도", ["[v - w·t/2, v + w·t/2] / r"]), ("data.ctrl[wheel]", ["velocity 액추에이터 목표", "±8 rad/s 로 clip"]), ("mj_step × 5", ["10 ms 진행"])],
          y=1.1, h=2.1, gap=0.22, colors=[C["orange"], C["grey"], C["yellow"], C["green"], C["green"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.45, "명령이 0.5 s 안 오면 (0, 0).  팔이 주행 자세가 아니면 (0, 0).  → 시뮬레이터가 스스로 멈춘다.", fs=9.2)
    save(fig, "lesson03_step_cmd.png")


def step_odom():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "step() 뒷부분: 바퀴가 돈 만큼 자세를 적분", bold=True, fs=12)
    chain(ax, [("before = qpos[wheel]", ["스텝 전 바퀴 각도"]), ("mj_step × 5", ["10 ms"]), ("dl, dr = Δq × r", ["바퀴가 굴러간 호 길이"]),
               ("ds, da", ["(dl+dr)/2 · (dr-dl)/track"]), ("odom += …", ["θ' = θ + da/2 (중점)", "x += ds·cosθ' · y += ds·sinθ'", "θ += da"])],
          y=1.5, h=2.1, gap=0.22, colors=[C["grey"], C["green"], C["yellow"], C["yellow"], C["orange"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.85, "twist = [ds/dt, da/dt] 가 /odom 의 속도.  odom 은 시작 때 (0, 0, 0) 이고 되돌리지 않는다 (spawn 을 바꿔도 0 에서 시작).", fs=9.2)
    note(ax, 0.3, 0.4, "10 ms 마다 한 번 적분한다. 회전 중에는 θ 의 중점을 써서 호를 직선으로 근사하는 오차를 줄인다.", fs=9.2)
    save(fig, "lesson03_step_odom.png")


def odom_msg():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "publish_state: 같은 odom 값이 /odom 메시지와 TF 로", bold=True, fs=12)
    rbox(ax, 0.3, 1.2, 3.0, 2.6, "p.odom · p.twist", ["(x, y, θ)", "(v, w)"], fc=C["orange"], tfs=10.5, fs=9)
    tiles_at(ax, [("nav_msgs/Odometry  /odom", ["header.frame_id odom · child base_footprint", "pose: x y · quaternion(θ) / twist: v w", "covariance 대각: 0.0025 (xy) · 0.01 (yaw) · 1e6 (z rp)"], C["blue"]),
                  ("TF odom → base_footprint", ["같은 값 · 같은 stamp", "TransformBroadcaster.sendTransform"], C["teal"])],
             cols=1, x0=4.4, x1=10.2, y_top=4.0, gap=0.25, h=1.45, tfs=10, fs=8.0)
    arrow(ax, (3.3, 3.3), (4.4, 3.3)); arrow(ax, (3.3, 1.7), (4.4, 1.7))
    rbox(ax, 11.0, 2.55, 2.7, 1.45, "Nav2 · SLAM", ["odom 토픽 + TF 사용"], fc=C["purple"], tfs=10, fs=8.4)
    rbox(ax, 11.0, 0.85, 2.7, 1.45, "RViz2 · tf2_echo", ["odom 프레임에서 로봇 표시"], fc=C["grey"], tfs=10, fs=8.4)
    arrow(ax, (10.2, 3.3), (11.0, 3.3)); arrow(ax, (10.2, 1.7), (11.0, 1.7))
    note(ax, 0.3, 0.4, "공분산은 상수다. '이 값을 얼마나 믿을지'를 EKF · AMCL 에 알려 주는 자리이며, 시뮬레이터에서는 형식만 채운다.", fs=9.2)
    save(fig, "lesson03_odom_msg.png")


# ================================================================ 4. frames and experiment
def frames():
    fig, ax = fig_ax(14, 6.2)
    note(ax, 0.3, 5.9, "프레임 셋: world(정답) · odom(적분) · base_footprint(로봇)", bold=True, fs=12)
    ax.set_aspect("equal")
    ox, oy = 1.2, 1.0
    for (x, y, name, col) in ((ox, oy, "world = odom 원점 (시작 자세)", "#555555"),):
        arrow(ax, (x, y), (x + 1.2, y), color=col, lw=2); arrow(ax, (x, y), (x, y + 1.2), color=col, lw=2); label(ax, x + 0.2, y - 0.35, name, fs=8.6, color=col)
    tx, ty = 5.0, 2.6
    arrow(ax, (tx, ty), (tx + 0.9, ty + 0.5), color="#2e7d32", lw=2); label(ax, tx + 0.1, ty + 0.9, "ground truth (MuJoCo 의 실제 자세)", fs=8.6, color="#2e7d32")
    ax.add_patch(Rectangle((tx - 0.35, ty - 0.25), 0.7, 0.5, fc="#ECEFF1", ec="#2e7d32", lw=1.4, zorder=3, angle=29))
    dx, dy = tx + 0.25, ty - 0.3
    arrow(ax, (dx, dy), (dx + 0.9, dy + 0.55), color="#1f4e79", lw=1.6, style="-|>"); label(ax, dx + 0.9, dy - 0.35, "odom → base_footprint (적분 추정)", fs=8.6, color="#1f4e79")
    ax.plot([ox, tx], [oy, ty], color="#2e7d32", lw=1, ls=":"); ax.plot([ox, dx], [oy, dy], color="#1f4e79", lw=1, ls=":")
    label(ax, 3.1, 2.1, "차이 = 오도메트리 오차", color="#C62828", fs=8.8)
    tiles_at(ax, [("world", ["MuJoCo 의 절대 좌표", "/ground_truth (frame world) 로만 볼 수 있다", "실제 로봇에는 없다"], C["green"]),
                  ("odom", ["시작 자세를 원점으로 하는 적분 좌표", "odom → base_footprint 를 브리지가 낸다", "연속적이지만 오차가 쌓인다"], C["teal"]),
                  ("base_footprint", ["로봇 바닥 중심 · 바퀴 축 위", "/scan · 관절 TF 가 이 아래 붙는다"], C["blue"])],
             cols=1, x0=8.3, x1=13.7, y_top=5.5, gap=0.12, h=1.6, tfs=10, fs=8.0)
    note(ax, 0.3, 0.2, "이 실험은 spawn 을 기본(원점)으로 두어 world 와 odom 원점이 같다. 그래서 두 값을 바로 뺄 수 있다.", fs=9.2)
    save(fig, "lesson03_frames.png")


def exp_design():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "실험: /cmd_vel 로 사각형을 돌며 /odom 과 /ground_truth 를 기록", bold=True, fs=12)
    chain(ax, [("odom_experiment.py", ["rclpy 노드 · use_sim_time", "/odom · /ground_truth 구독"]), ("직진 2 m", ["v = 0.3 m/s", "odom 거리로 종료"]), ("좌회전 90°", ["w = 0.5 rad/s", "odom yaw 로 종료"]),
               ("× 4 (× 3바퀴)", ["멈출 때 감속 램프 고려"]), ("CSV → 그래프", ["경로 겹쳐 보기", "오차 |odom - truth|"])],
          y=1.1, h=2.1, gap=0.22, colors=[C["purple"], C["orange"], C["orange"], C["grey"], C["blue"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.45, "python docs/camp/odom_experiment.py --side 2.0 --laps 3 --out artifacts/dev/odom_square3", fs=9.5)
    save(fig, "lesson03_exp_design.png")


def why_drift():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "오차가 쌓이는 이유 (실제 로봇에서 더 크다)", bold=True, fs=12)
    tiles(ax, [("바퀴 미끄러짐", ["가속 · 급회전 · 미끄러운 바닥", "돌았지만 안 간 만큼 오차", "MuJoCo 는 noslip 으로 거의 없음"], C["red"]),
               ("반지름 · 윤거 오차", ["공기압 · 마모 · 하중", "거리 · 각도에 비례해 누적", "시뮬은 모델 값을 그대로 씀"], C["orange"]),
               ("적분 근사", ["10 ms 마다 직선 근사", "회전 중 미세 오차", "중점법으로 줄임"], C["yellow"]),
               ("절대 기준 없음", ["시작점이 원점 · 되돌릴 수 없음", "kidnap · 재시작이면 무효", "→ 지도 · 외부 센서가 필요"], C["grey"])],
          cols=4, y_top=3.9, gap=0.25, h=2.3, tfs=10.5, fs=8.2)
    note(ax, 0.3, 0.9, "실측: 사각형 3바퀴(약 19 m) 뒤 위치 오차 약 2 cm · yaw 약 0.8°.  시뮬레이터라서 작다. 실제 로봇은 수십 cm · 수 도가 흔하다.", fs=9.2)
    note(ax, 0.3, 0.45, "yaw 오차가 위험하다: 1° 틀린 채 10 m 가면 17 cm 옆으로 벗어난다.", fs=9.2)
    save(fig, "lesson03_why_drift.png")


def odom_role():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "Odom 의 의미: 짧은 시간엔 정확하고 매끄럽다 · 길게는 못 믿는다", bold=True, fs=12)
    tiles_at(ax, [("잘하는 것", ["50 Hz · 지연 없음 · 항상 연속", "짧은 구간의 상대 이동은 정확", "경로 추종 · 장애물 회피의 기준 프레임"], C["green"]),
                  ("못하는 것", ["내가 지도 어디에 있는지", "누적 오차를 스스로 고치기", "재시작 · 납치 후 복구"], C["red"])],
             cols=2, x0=0.3, x1=8.4, y_top=4.0, gap=0.3, h=2.2, tfs=11, fs=8.6)
    rbox(ax, 9.0, 1.8, 4.7, 2.2, "그래서 두 층으로 나눈다", ["map → odom: SLAM · AMCL 이 가끔 '점프' 시켜 고친다", "odom → base_footprint: 바퀴가 매끄럽게 잇는다", "Nav2 의 local costmap 은 odom, global 은 map"], fc=C["yellow"], tfs=10.5, fs=8.4, align="left", dy=0.42)
    note(ax, 0.3, 1.1, "다음 페이지(SLAM)에서 map → odom 이 붙으면서 이 단점이 어떻게 메워지는지 본다.", fs=9.5, bold=True)
    save(fig, "lesson03_odom_role.png")


def wrapper_why():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "wrapper(scripts/mobile_openarm)가 launch 전에 맞춰 주는 것", bold=True, fs=12)
    rbox(ax, 0.3, 1.9, 2.6, 1.5, "wrapper", ["./scripts/mobile_openarm", "drive · slam · start …"], fc=C["purple"], tfs=10.5, fs=8.4)
    tiles_at(ax, [("① ROS 환경 확인", ["ROS_DISTRO = jazzy 인지 검사", "install/ 없으면 build 안내"], C["grey"]),
                  ("② 통신 격리", ["ROS_DOMAIN_ID 43 · localhost 전용", "옆자리 PC 와 토픽이 안 섞임"], C["yellow"]),
                  ("③ DDS 고정", ["CycloneDDS + 설정 xml", "없으면 기본 RMW 로 대체"], C["yellow"]),
                  ("④ 경로 고정", ["로그 → .ros/mobile_openarm/", "생성물 → artifacts/mobile_generated/"], C["green"]),
                  ("⑤ 같은 Python", ["venv 의 python 으로 ros2 실행", "mujoco 를 찾지 못하는 문제 방지"], C["green"]),
                  ("⑥ 짧은 명령", ["drive · slam · start · moveit …", "launch 인자 조합을 이름 하나로"], C["blue"])],
             cols=3, x0=3.6, x1=13.7, y_top=4.3, gap=0.25, h=1.6, tfs=10.5, fs=8.4)
    ax.plot([2.9, 3.25], [2.65, 2.65], color=INK, lw=1.6); ax.plot([3.25, 3.25], [1.4, 3.5], color=INK, lw=1.6)
    arrow(ax, (3.25, 3.5), (3.6, 3.5)); arrow(ax, (3.25, 1.4), (3.6, 1.4))
    note(ax, 0.3, 0.3, "60~80명이 같은 네트워크에서 실습해도 서로 간섭하지 않고, 누구의 PC 에서나 같은 명령이 같은 결과를 낸다.", fs=9.5)
    save(fig, "lesson03_wrapper_why.png")


if __name__ == "__main__":
    for f in (bringup_tree, bringup_modes, wrapper_why, bringup_cmd, sensors_overview, bridge_process, lidar_ray, lidar_msg, wheel_encoder, cameras, clock_tf, rates,
              diffdrive, step_cmd, step_odom, odom_msg, frames, exp_design, why_drift, odom_role):
        f()
