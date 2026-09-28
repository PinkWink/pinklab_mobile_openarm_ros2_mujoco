"""Figures for the lesson-01 Confluence page (Gazebo vs MuJoCo, minimal bridge). Output: docs/camp/lesson01_*.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, cross, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch  # noqa: E402
import numpy as np  # noqa: E402


# ================================================================ 1-1. where each simulator comes from
def gz_mj_profile():
    fig, ax = fig_ax(14, 3.0)
    tiles(ax, [("Gazebo (gz-sim)", ["Open Robotics → OSRF · Apache 2.0", "ROS의 기본 시뮬레이터 · C++ 플러그인 구조", "물리 엔진 교체형: DART · Bullet · ODE", "센서 · 월드 · GUI가 한 프레임워크"], C["yellow"]),
               ("MuJoCo", ["DeepMind · Apache 2.0 (2022 공개)", "연구 · 강화학습 · 로봇 제어에서 표준", "물리 엔진 자체 · Python 바인딩 공식", "GUI · ROS 연동은 사용자가 붙인다"], C["green"])],
          cols=2, y_top=2.8, h=2.5, gap=0.4, tfs=12.5, fs=9.4)
    save(fig, "lesson01_profile.png")


# ================================================================ 1-2. architecture comparison
def gz_mj_arch():
    fig, ax = fig_ax(14, 5.6)
    # Gazebo column
    ax.add_patch(Rectangle((0.3, 0.3), 6.5, 5.0, fc="#FFFBF0", ec="#D9C48A", lw=1.2, zorder=1))
    note(ax, 0.5, 5.05, "Gazebo: 서버 + 플러그인 + 브리지", bold=True, fs=12, color="#7a4b00")
    rbox(ax, 0.6, 3.5, 5.9, 1.2, "gz-sim 서버 (C++)", ["ECS 세계 · 물리 엔진(DART …) · 렌더링"], fc=C["yellow"], tfs=11, fs=9)
    rbox(ax, 0.6, 2.0, 2.8, 1.2, "센서 플러그인", ["LiDAR · 카메라 · IMU", "gz-transport 로 발행"], fc=C["orange"], tfs=10.5, fs=8.8)
    rbox(ax, 3.7, 2.0, 2.8, 1.2, "gz_ros2_control", ["ros2_control 하드웨어 IF", "관절 명령 · 상태"], fc=C["orange"], tfs=10.5, fs=8.8)
    rbox(ax, 0.6, 0.5, 5.9, 1.2, "ros_gz_bridge → ROS 2", ["gz 토픽 ↔ ROS 2 토픽 이름 · 타입 매핑"], fc=C["blue"], tfs=11, fs=9)
    arrow(ax, (2.0, 3.5), (2.0, 3.2)); arrow(ax, (5.1, 3.5), (5.1, 3.2)); arrow(ax, (2.0, 2.0), (2.0, 1.7)); arrow(ax, (5.1, 2.0), (5.1, 1.7))
    # MuJoCo column
    ax.add_patch(Rectangle((7.2, 0.3), 6.5, 5.0, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 7.4, 5.05, "MuJoCo: Python 프로세스 하나", bold=True, fs=12, color="#2e7d32")
    rbox(ax, 7.5, 3.5, 5.9, 1.2, "mujoco (C 라이브러리 + Python 바인딩)", ["mj_step · 센서 값 · 카메라 렌더가 함수 호출"], fc=C["green"], tfs=11, fs=9)
    rbox(ax, 7.5, 2.0, 5.9, 1.2, "브리지 루프 (우리가 쓰는 Python)", ["스텝 → 읽기 → ROS 발행 → 명령 적용 → 반복"], fc=C["purple"], tfs=11, fs=9)
    rbox(ax, 7.5, 0.5, 5.9, 1.2, "rclpy → ROS 2", ["같은 프로세스에서 토픽 · TF · 액션"], fc=C["blue"], tfs=11, fs=9)
    arrow(ax, (10.45, 3.5), (10.45, 3.2)); arrow(ax, (10.45, 2.0), (10.45, 1.7))
    save(fig, "lesson01_arch.png")


# ================================================================ 1-3. physics
def gz_mj_physics():
    fig, ax = fig_ax(14, 3.4)
    tiles(ax, [("접촉 모델", ["Gazebo: 강체 접촉 · LCP 풀이 (DART/ODE)", "MuJoCo: 부드러운 접촉 · 볼록 최적화", "→ 파지 · 다접촉에서 MuJoCo가 안정적"], C["blue"]),
               ("시간 스텝", ["Gazebo: 1 ms 기본 · 엔진마다 다름", "MuJoCo: 2 ms 로도 안정 (이 예제)", "→ 같은 실시간 비율에 계산량 적음"], C["yellow"]),
               ("모델 · 액추에이터", ["Gazebo: SDF + ros2_control 컨트롤러", "MuJoCo: MJCF + 내장 액추에이터", "→ 컨트롤러 스택 없이 관절을 잡는다"], C["green"]),
               ("센서", ["Gazebo: 플러그인이 별도 프로세스에서 발행", "MuJoCo: 레이캐스트 · 카메라 렌더가 함수", "→ 결과를 파이썬 배열로 바로 받는다"], C["purple"])],
          cols=4, y_top=3.1, h=2.0, gap=0.25, tfs=11, fs=8.0)
    note(ax, 0.3, 0.5, "둘 다 실제 로봇을 대신하는 데 충분하다. 차이는 정확도보다 '무엇을 어디서 계산하고 어떻게 꺼내 쓰는가'에 있다.", fs=9.5)
    save(fig, "lesson01_physics.png")


# ================================================================ 1-4. ROS 2 integration paths
def gz_mj_ros():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "Gazebo: 정해진 길", bold=True, fs=12, color="#7a4b00")
    chain(ax, [("SDF/URDF + 플러그인 태그", ["센서 · ros2_control"]), ("gz-sim", ["서버 프로세스"]), ("ros_gz_bridge", ["토픽 매핑 YAML"]), ("ROS 2", ["Nav2 · MoveIt"])],
          y=2.7, h=1.3, colors=[C["yellow"], C["yellow"], C["orange"], C["blue"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 2.2, "MuJoCo: 직접 쓰는 길 (이 과정)", bold=True, fs=12, color="#2e7d32")
    chain(ax, [("MJCF", ["모델 · 카메라 · 액추에이터"]), ("Python 브리지", ["mj_step + rclpy"]), ("표준 ROS 2 토픽 · TF · 액션", ["/clock /joint_states …"]), ("ROS 2", ["Nav2 · MoveIt"])],
          y=0.6, h=1.3, colors=[C["green"], C["purple"], C["teal"], C["blue"]], tfs=10.5, fs=8.6)
    save(fig, "lesson01_ros_path.png")


# ================================================================ 1-5. pros / cons
def gz_mj_proscons():
    fig, ax = fig_ax(14, 5.0)
    tiles(ax, [("Gazebo 장점", ["ROS 2 공식 · 예제 · 튜토리얼 많음", "센서 · 플러그인 · 월드 생태계", "ros2_control 과 그대로 연결", "대규모 월드 · 다중 로봇 경험 축적"], C["yellow"]),
               ("Gazebo 단점", ["무겁다: 별도 서버 · GUI · 렌더 프로세스", "저사양 노트북에서 느리다", "플러그인 · 브리지 설정이 여러 층", "파지 같은 다접촉이 불안정할 때가 있다"], C["red"]),
               ("MuJoCo 장점", ["가볍고 빠르다 · 내장 그래픽으로 충분", "접촉이 안정적 (파지 · 양팔)", "Python 한 프로세스에 모든 것이 보인다", "카메라 · 센서 값을 배열로 바로 쓴다"], C["green"]),
               ("MuJoCo 단점", ["ROS 2 연동을 직접 써야 한다", "SDF 월드 · 플러그인 생태계 없음", "GUI 편집기 없음 (XML 직접)", "URDF → MJCF 변환 단계가 필요"], C["orange"])],
          cols=2, y_top=4.7, h=2.1, gap=0.3, tfs=12, fs=9.2)
    save(fig, "lesson01_proscons.png")


# ================================================================ 1-6. why MuJoCo here
def why_mujoco():
    fig, ax = fig_ax(14, 3.6)
    tiles(ax, [("① 저사양 노트북", ["4코어 · 내장 그래픽에서 실시간", "창고 + 양팔 + 카메라 4대"], C["green"]),
               ("② 코드가 다 보인다", ["브리지 한 파일이 시뮬레이터 ↔ ROS 2", "플러그인 뒤에 숨는 것이 없다"], C["purple"]),
               ("③ 파지가 안정적", ["Pick & Place 를 반복해도", "상자가 튀지 않는다"], C["yellow"]),
               ("④ 카메라를 직접 받는다", ["영상 토픽 없이 검출만 발행", "저사양에서 실시간 유지"], C["blue"])],
          cols=4, y_top=3.3, h=1.8, gap=0.25, tfs=11.5, fs=9)
    ax.plot([0.3, 3.4], [0.75, 0.75], color="#999999", lw=1.4, ls="--", zorder=3); cross(ax, 1.85, 0.75)
    note(ax, 3.6, 0.75, "Gazebo 는 설치하지 않는다. 비교 설명 이후 모든 실습은 MuJoCo 로만 진행한다.", fs=9.5, color="#C62828")
    save(fig, "lesson01_why.png")


# ================================================================ 2-1. the example robot (side view)
def arm_schematic():
    fig, ax = fig_ax(14, 5.2)
    ax.set_aspect("equal")
    note(ax, 0.3, 4.9, "예제 로봇: 2링크 팔 + 팔 끝 카메라 (two_link_arm.xml, 옆에서 본 모습)", bold=True, fs=12)
    S, x0, z0 = 6.0, 2.5, 0.6  # scale units per metre, base origin
    ax.plot([0.6, 9.5], [z0, z0], color=INK, lw=1.5); note(ax, 9.6, z0, "바닥", fs=9)
    ax.add_patch(Rectangle((x0 - 0.3, z0), 0.6, 0.06 * S, fc="#555555", ec=INK, zorder=3)); label(ax, x0 - 0.9, z0 + 0.2, "base_link", fs=9)
    q1, q2 = 0.6, 1.5
    p1 = np.array([x0, z0 + 0.06 * S]); d1 = np.array([np.sin(q1), np.cos(q1)]); p2 = p1 + 0.30 * S * d1
    d2 = np.array([np.sin(q1 + q2), np.cos(q1 + q2)]); p3 = p2 + 0.26 * S * d2
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#3380E6", lw=9, solid_capstyle="round", zorder=4)
    ax.plot([p2[0], p3[0]], [p2[1], p3[1]], color="#E69A33", lw=8, solid_capstyle="round", zorder=4)
    for p, name in ((p1, "joint1 (hinge, y축)"), (p2, "joint2 (hinge, y축)")):
        ax.add_patch(Circle(p, 0.11, fc="white", ec=INK, lw=1.5, zorder=6)); label(ax, p[0] - 1.35, p[1] + 0.05, name, fs=9)
    ax.add_patch(Rectangle((p3[0] - 0.12, p3[1] - 0.12), 0.24, 0.24, fc="#222222", ec=INK, zorder=6)); label(ax, p3[0] + 0.05, p3[1] + 0.42, "camera_link · tip_camera", fs=9)
    # field of view
    for s in (-1, 1):
        ang = np.arctan2(d2[0], d2[1]) + s * np.deg2rad(30)
        e = p3 + 2.2 * np.array([np.sin(ang), np.cos(ang)])
        ax.plot([p3[0], e[0]], [p3[1], e[1]], color="#8a6d00", lw=1.2, ls="--", zorder=5)
    label(ax, p3[0] + 1.6, p3[1] - 0.05, "fovy 60° · 320×240 · 5 Hz", color="#8a6d00", fs=9)
    ax.add_patch(Rectangle((x0 + 0.55 * S - 0.24, z0), 0.48, 0.48, fc="#E53935", ec=INK, zorder=4)); ax.add_patch(Rectangle((x0 + 0.62 * S - 0.18, z0), 0.36, 0.36, fc="#3949AB", ec=INK, zorder=4))
    label(ax, x0 + 0.58 * S, z0 - 0.3, "빨강 · 파랑 상자 (카메라가 볼 것)", fs=9)
    label(ax, p1[0] + 1.3, p1[1] - 0.05, "link1 0.30 m", color="#1f4e79", fs=9); label(ax, p2[0] + 0.9, p2[1] + 0.45, "link2 0.25 m", color="#8a5a00", fs=9)
    rbox(ax, 10.3, 2.4, 3.4, 2.1, "액추에이터", ["position: kp=30 (joint1)", "position: kp=20 (joint2)", "목표 각도 = data.ctrl[0:2]", "단위: rad (compiler angle=radian)"], fc=C["yellow"], tfs=10.5, fs=8.8, align="left")
    rbox(ax, 10.3, 0.5, 3.4, 1.6, "자기 충돌 끔", ["링크 지오메트리 contype=0", "관절에서 캡슐이 겹치므로"], fc=C["grey"], tfs=10.5, fs=8.8, align="left")
    save(fig, "lesson01_arm.png")


# ================================================================ 2-2. what the bridge exchanges
def bridge_io():
    fig, ax = fig_ax(14, 4.6)
    rbox(ax, 5.0, 0.75, 4.0, 3.4, "minimal_bridge.py", ["MuJoCo 모델 + 데이터", "mj_step 루프", "rclpy 노드 (use_sim_time)"], fc=C["purple"], tfs=12, fs=9.4)
    outs = [("/clock", "rosgraph_msgs/Clock · 매 스텝"), ("/joint_states", "sensor_msgs/JointState · 50 Hz"), ("/tf", "base_link → link1 → link2 → camera_link · 50 Hz"), ("/tip_camera/image_raw", "sensor_msgs/Image rgb8 320×240 · 5 Hz")]
    for i, (t, d) in enumerate(outs):
        y = 3.65 - i * 0.98
        rbox(ax, 10.0, y - 0.45, 3.7, 0.9, t, [d], fc=C["blue"], tfs=10, fs=7.8, dy=0.26)
        arrow(ax, (9.0, y), (10.0, y), color="#1f4e79", lw=1.6)
    rbox(ax, 0.3, 2.0, 3.7, 0.95, "/cmd", ["std_msgs/Float64MultiArray [q1, q2] rad"], fc=C["orange"], tfs=10, fs=8.2, dy=0.26)
    arrow(ax, (4.0, 2.45), (5.0, 2.45), color="#7a4b00", lw=1.6)
    label(ax, 4.5, 2.75, "→ data.ctrl", color="#7a4b00", fs=8.8)
    note(ax, 0.3, 0.35, "ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray \"{data: [0.6, 1.5]}\"", fs=9.5)
    note(ax, 0.3, 4.3, "브리지가 주고받는 것: 나가는 4개, 들어오는 1개", bold=True, fs=12)
    save(fig, "lesson01_io.png")


# ================================================================ 2-3. the step loop
def step_loop():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "spin(): 스텝 루프 한 바퀴 = 2 ms", bold=True, fs=12)
    spans = chain(ax, [("1  mj_step", ["물리 한 스텝"]), ("2  /clock", ["data.time 발행"]), ("3  joints · TF", ["50 Hz 마다"]),
                       ("4  camera", ["5 Hz 마다 렌더"]), ("5  spin_once", ["/cmd 콜백 → ctrl"]), ("6  sleep", ["벽시계와 맞춤"])],
                  y=0.9, h=1.6, gap=0.25, colors=[C["green"], C["blue"], C["blue"], C["yellow"], C["orange"], C["grey"]], tfs=10.5, fs=8.8)
    xr = (spans[5][0] + spans[5][1]) / 2; xl = (spans[0][0] + spans[0][1]) / 2
    ax.plot([xr, xr], [0.9, 0.5], color="#7a4b00", lw=1.3); ax.plot([xr, xl], [0.5, 0.5], color="#7a4b00", lw=1.3); arrow(ax, (xl, 0.5), (xl, 0.9), color="#7a4b00", lw=1.3)
    label(ax, (xl + xr) / 2, 0.5, "반복", color="#7a4b00", fs=9)
    save(fig, "lesson01_loop.png")


# ================================================================ 2-4. run: two terminals
def run_terminals():
    fig, ax = fig_ax(14, 2.6)
    tiles(ax, [("터미널 1: 브리지", ["source /opt/ros/jazzy/setup.bash", "source scripts/env.sh", "python lessons/01_mujoco_ros2/minimal_bridge.py --viewer"], C["purple"]),
               ("터미널 2: 보기 · 명령", ["ros2 topic list · hz /joint_states", "ros2 run rqt_image_view rqt_image_view /tip_camera/image_raw", "ros2 topic pub -1 /cmd … \"{data: [0.6, 1.5]}\""], C["blue"])],
          cols=2, y_top=2.4, h=2.1, gap=0.4, tfs=12, fs=9.2)
    save(fig, "lesson01_run.png")


# ================================================================ 2-5. TF tree
def tf_tree():
    fig, ax = fig_ax(14, 3.4)
    note(ax, 0.3, 3.1, "TF 트리: MuJoCo 의 xpos · xquat(월드 기준) → 부모 기준 상대 자세", bold=True, fs=12)
    chain(ax, [("base_link", ["부모 없음 (루트)"]), ("link1", ["joint1 회전"]), ("link2", ["joint2 회전"]), ("camera_link", ["image frame_id"])],
          y=1.2, h=1.3, colors=[C["grey"], C["blue"], C["blue"], C["yellow"]], tfs=11, fs=8.8)
    note(ax, 0.3, 0.55, "q_rel = conj(q_parent) · q_child      p_rel = rot(conj(q_parent), p_child - p_parent)      → TransformStamped(parent → child)", fs=9.5)
    save(fig, "lesson01_tf.png")


# ================================================================ 2-6. minimal -> warehouse bridge
def to_warehouse():
    fig, ax = fig_ax(14, 4.4)
    rbox(ax, 0.3, 1.4, 3.6, 2.2, "최소 브리지 (이 예제)", ["mj_step 루프", "/clock /joint_states /tf", "카메라 렌더 → Image", "/cmd → ctrl"], fc=C["purple"], tfs=11.5, fs=9)
    arrow(ax, (3.9, 2.5), (4.7, 2.5), lw=2)
    label(ax, 4.3, 2.8, "+", fs=14)
    items = [("라이다", ["레이캐스트 → /scan"], C["yellow"]), ("바퀴 · 오도메트리", ["/cmd_vel → 바퀴 · /odom + TF"], C["yellow"]),
             ("궤적 액션", ["FollowJointTrajectory → 양팔"], C["blue"]), ("카메라 핸들러", ["렌더 → 검출 → /vision/* 만 발행"], C["green"])]
    for i, (t, lines, fc) in enumerate(items):
        r, c = divmod(i, 2)
        rbox(ax, 4.8 + c * 4.55, 2.7 - r * 1.45, 4.3, 1.2, t, lines, fc=fc, tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.6, "= src/mobile_openarm_mujoco/mobile_openarm_mujoco/bridge.py (창고 브리지, 약 400줄).  같은 루프에 항목이 늘어난 것이다.", fs=9.5)
    save(fig, "lesson01_to_warehouse.png")


# ================================================================ 2-7. try it
def try_it():
    fig, ax = fig_ax(14, 2.4)
    tiles(ax, [("--camera-hz 20", ["영상 토픽의 비용을 본다", "창고 브리지가 영상을 안 흘리는 이유"], C["blue"]),
               ("kp 를 5 로", ["팔이 늘어진다", "위치 액추에이터의 강성"], C["yellow"]),
               ("link3 추가", ["MJCF body 하나 + joints/bodies 목록", "TF 가 한 단 늘어난다"], C["green"])],
          cols=3, y_top=2.1, h=1.7, gap=0.3, tfs=11, fs=9)
    save(fig, "lesson01_try.png")


# ================================================================ 3. code structure diagrams (one per function)
def fn_init():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "__init__: 모델을 읽고 ROS 2 입출력을 만든다", bold=True, fs=12)
    rbox(ax, 0.3, 1.6, 3.4, 2.3, "MuJoCo", ["MjModel.from_xml_path(XML)", "MjData(model)", "Renderer(240 × 320)"], fc=C["green"], tfs=11, fs=8.8, align="left")
    rbox(ax, 4.2, 1.6, 4.9, 2.3, "발행기 4개", ["/clock            Clock", "/joint_states     JointState", "/tf               TransformBroadcaster", "/tip_camera/image_raw   Image"], fc=C["blue"], tfs=11, fs=8.8, align="left")
    rbox(ax, 9.6, 1.6, 4.1, 2.3, "구독 1개 · 주기", ["/cmd  Float64MultiArray → on_cmd", "joint_period = 1 / 50 Hz", "camera_period = 1 / 5 Hz", "use_sim_time = True"], fc=C["orange"], tfs=11, fs=8.8, align="left")
    note(ax, 0.3, 0.8, "이름 목록이 곧 트리다:  joints = [joint1, joint2]      bodies = [base_link, link1, link2, camera_link]", fs=9.5)
    save(fig, "lesson01_fn_init.png")


def fn_joints():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "publish_joints (앞부분): MuJoCo 상태 → JointState", bold=True, fs=12)
    chain(ax, [("data.qpos · data.qvel", ["MuJoCo 전체 상태 배열"]), ("관절 인덱스", ["model.joint(j).qposadr", "model.joint(j).dofadr"]),
               ("JointState", ["name · position · velocity", "stamp = 시뮬레이션 시각 t"]), ("/joint_states", ["50 Hz"])],
          y=0.7, h=1.9, colors=[C["green"], C["grey"], C["yellow"], C["blue"]], tfs=10.5, fs=8.8)
    save(fig, "lesson01_fn_joints.png")


def fn_tf():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "publish_joints (뒷부분): body 자세(월드) → 부모 기준 변환 → /tf", bold=True, fs=12)
    spans = chain(ax, [("(parent, child) 쌍", ["base_link→link1", "link1→link2 · link2→camera_link"]), ("xpos · xquat", ["두 body 의 월드 자세"]),
                       ("상대 변환", ["mju_negQuat · mju_mulQuat", "mju_rotVecQuat"]), ("TransformStamped", ["frame_id = parent", "child_frame_id = child"]),
                       ("sendTransform", ["3개를 한 번에 → /tf"])],
                  y=1.4, h=2.1, gap=0.25, colors=[C["grey"], C["green"], C["purple"], C["yellow"], C["blue"]], tfs=10.5, fs=8.6)
    xr = (spans[3][0] + spans[3][1]) / 2; xl = (spans[0][0] + spans[0][1]) / 2
    ax.plot([xr, xr], [1.4, 0.9], color="#7a4b00", lw=1.3); ax.plot([xr, xl], [0.9, 0.9], color="#7a4b00", lw=1.3); arrow(ax, (xl, 0.9), (xl, 1.4), color="#7a4b00", lw=1.3)
    label(ax, (xl + xr) / 2, 0.9, "쌍마다 반복 (3회) → tfs 리스트", color="#7a4b00", fs=9)
    note(ax, 0.3, 0.35, "q_rel = conj(q_parent) · q_child        p_rel = rot(conj(q_parent), p_child - p_parent)", fs=9.5)
    save(fig, "lesson01_fn_tf.png")


def fn_camera():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "publish_camera: MuJoCo 렌더 → sensor_msgs/Image", bold=True, fs=12)
    chain(ax, [("update_scene", ["camera=\"tip_camera\"", "현재 data 로 장면 갱신"]), ("render()", ["numpy (240, 320, 3) uint8", "오프스크린 · GPU 불필요"]),
               ("Image 메시지", ["encoding rgb8 · step 960", "frame_id camera_link · data = bytes"]), ("/tip_camera/image_raw", ["5 Hz"])],
          y=0.7, h=1.9, colors=[C["green"], C["green"], C["yellow"], C["blue"]], tfs=10.5, fs=8.6)
    save(fig, "lesson01_fn_camera.png")


def fn_cmd():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "on_cmd: ROS 2 명령 → MuJoCo 액추에이터", bold=True, fs=12)
    chain(ax, [("/cmd", ["Float64MultiArray", "[q1, q2] rad"]), ("길이 확인", ["len(data) == model.nu", "아니면 무시"]),
               ("np.clip", ["actuator_ctrlrange 안으로"]), ("data.ctrl[:]", ["다음 mj_step 부터 적용"]), ("위치 액추에이터", ["토크 = kp · (ctrl - q)", "관절이 목표로 간다"])],
          y=0.7, h=1.9, gap=0.25, colors=[C["orange"], C["grey"], C["grey"], C["purple"], C["green"]], tfs=10.5, fs=8.6)
    save(fig, "lesson01_fn_cmd.png")


def fn_clock():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "stamp · /clock: 시뮬레이션 시각이 ROS 시간이 된다", bold=True, fs=12)
    chain(ax, [("data.time", ["float 초", "mj_step 마다 +0.002"]), ("stamp(t)", ["sec = int(t)", "nanosec = 소수부 × 1e9"]),
               ("Clock 메시지", ["매 스텝 발행"]), ("/clock", ["use_sim_time 노드가 따른다", "메시지 stamp 도 같은 t"])],
          y=0.7, h=1.9, colors=[C["green"], C["grey"], C["yellow"], C["blue"]], tfs=10.5, fs=8.6)
    save(fig, "lesson01_fn_clock.png")


if __name__ == "__main__":
    for f in (gz_mj_profile, gz_mj_arch, gz_mj_physics, gz_mj_ros, gz_mj_proscons, why_mujoco, arm_schematic, bridge_io, step_loop,
              run_terminals, tf_tree, to_warehouse, try_it, fn_init, fn_joints, fn_tf, fn_camera, fn_cmd, fn_clock):
        f()
