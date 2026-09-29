"""Figures for the lesson-02 Confluence page (robot description: packages, URDF/Xacro -> MJCF, robot_state_publisher).
Output: docs/camp/lesson02_*.png. Helpers from draw_intro_figures.py; orthogonal arrows only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def tiles_at(ax, items, cols, x0, x1, y_top, gap=0.25, h=1.6, tfs=10.5, fs=8.6):
    w = (x1 - x0 - gap * (cols - 1)) / cols
    for i, (title, lines, fc) in enumerate(items):
        r, c = divmod(i, cols)
        rbox(ax, x0 + c * (w + gap), y_top - (r + 1) * h - r * gap, w, h, title, lines, fc=fc, tfs=tfs, fs=fs, align="left", dy=0.3)


def vchain(ax, items, x, w, y_top, h=0.62, gap=0.32, colors=None, tfs=9.8, fs=8.2):
    """Top-to-bottom chain of boxes at column x. Returns centre y of each box."""
    ys = []
    for i, it in enumerate(items):
        title, lines = (it[0], it[1]) if isinstance(it, tuple) else (it, ())
        y = y_top - i * (h + gap) - h
        rbox(ax, x, y, w, h, title, lines, fc=(colors[i % len(colors)] if colors else C["blue"]), tfs=tfs, fs=fs)
        if i:
            arrow(ax, (x + w / 2, y + h + gap), (x + w / 2, y + h))
        ys.append(y + h / 2)
    return ys


# ================================================================ 1. packages
def pkg_kinds():
    fig, ax = fig_ax(14, 5.8)
    ax.add_patch(Rectangle((0.3, 0.4), 6.2, 5.1, fc="#FFFBF0", ec="#D9C48A", lw=1.2, zorder=1))
    note(ax, 0.5, 5.2, "가져온 패키지 (상류 · 그대로 복사)", bold=True, fs=12, color="#7a4b00")
    tiles_at(ax, [("openarm_description", ["OpenARM 양팔 · 몸통 · 그리퍼", "xacro · 메시 · YAML (enactic)"], C["yellow"]),
                  ("vicpinky_description", ["Vic Pinky 모바일 베이스", "robot_core.xacro · 메시 (pinklab)"], C["yellow"]),
                  ("mobile_openarm_moveit_config", ["SRDF · kinematics 는 openarm_ros2 에서", "launch 는 우리가 씀"], C["orange"])],
             cols=1, x0=0.5, x1=6.3, y_top=4.9, gap=0.15, h=1.35, tfs=10.5, fs=8.4)
    ax.add_patch(Rectangle((7.5, 0.4), 6.2, 5.1, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 7.7, 5.2, "우리가 만든 패키지", bold=True, fs=12, color="#2e7d32")
    tiles_at(ax, [("mobile_openarm_description", ["베이스 + 양팔 + 카메라를 한 로봇으로 조립", "expand_urdf() · display.launch.py"], C["green"]),
                  ("mobile_openarm_mujoco", ["URDF → MJCF 생성 (model.py)", "브리지 (bridge.py) · 창고 · 물리"], C["green"]),
                  ("mobile_openarm_bringup", ["warehouse.launch.py: 전부 띄우는 launch 하나"], C["green"])],
             cols=1, x0=7.7, x1=13.5, y_top=4.9, gap=0.15, h=1.35, tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.12, "그 밖의 우리 패키지: mobile_openarm_navigation (Nav2 · SLAM 설정) · warehouse_interfaces / skills / lecture (수업 코드)", fs=9)
    save(fig, "lesson02_pkg_kinds.png")


def pkg_assembly():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "로봇 한 대 = 베이스(vicpinky) + 마운트(우리) + 양팔 · 그리퍼(openarm) + 카메라(우리)", bold=True, fs=12)
    # stacked layers left
    layers = (("카메라 4대  (mobile_openarm_description/urdf/cameras.xacro)", C["green"], "우리"),
              ("OpenARM 몸통 + 양팔 7관절 × 2 + 그리퍼  (openarm_description)", C["yellow"], "상류"),
              ("openarm_mount · arm_adapter_plate  (mobile_openarm.urdf.xacro)", C["green"], "우리"),
              ("Vic Pinky 베이스: base_footprint · base_link · 바퀴 2 · 캐스터 4 · laser_link  (vicpinky_description)", C["yellow"], "상류"))
    for i, (t, fc, who) in enumerate(layers):
        y = 3.4 - i * 0.95
        rbox(ax, 0.3, y, 11.4, 0.8, t, fc=fc, tfs=10)
        label(ax, 12.6, y + 0.4, who, fs=9.5, color="#7a4b00" if who == "상류" else "#2e7d32")
    for i in range(3):
        y = 3.4 - i * 0.95
        arrow(ax, (6.0, y - 0.15), (6.0, y), lw=1.2)
    note(ax, 0.3, 0.25, "상류 파일은 손대지 않는다.  붙이는 위치(mount_x · mount_z · arm_base_xyz)와 카메라만 우리 xacro 가 정한다.", fs=9.5)
    save(fig, "lesson02_pkg_assembly.png")


# ================================================================ 2. relations
def rel_flow():
    fig, ax = fig_ax(14, 6.2)
    note(ax, 0.3, 5.9, "URDF 하나를 펼쳐 세 곳에 준다", bold=True, fs=12)
    rbox(ax, 0.3, 3.9, 3.0, 1.3, "mobile_openarm.urdf.xacro", ["+ vicpinky · openarm · cameras"], fc=C["green"], tfs=10, fs=8.4)
    rbox(ax, 4.1, 3.9, 2.8, 1.3, "expand_urdf()", ["xacro.process_file()", "→ URDF 문자열"], fc=C["yellow"], tfs=10.5, fs=8.4)
    arrow(ax, (3.3, 4.55), (4.1, 4.55))
    # three consumers
    rbox(ax, 7.9, 4.5, 5.8, 1.0, "robot_state_publisher", ["robot_description 파라미터 → /robot_description · /tf · /tf_static"], fc=C["blue"], tfs=10, fs=8.2)
    rbox(ax, 7.9, 2.6, 5.8, 1.5, "브리지 (mobile_openarm_mujoco.bridge)", ["--urdf-file robot.urdf → build_model() → warehouse.xml (MJCF)", "→ MuJoCo 가 돈다 → /joint_states · /odom · /scan · /clock"], fc=C["teal"], tfs=10, fs=8.2)
    rbox(ax, 7.9, 0.9, 5.8, 1.0, "MoveIt (move_group)", ["같은 URDF + SRDF → 경로 계획"], fc=C["purple"], tfs=10, fs=8.2)
    ax.plot([6.9, 7.4], [4.55, 4.55], color=INK, lw=1.6); ax.plot([7.4, 7.4], [1.4, 5.0], color=INK, lw=1.6)
    for y in (5.0, 3.35, 1.4):
        arrow(ax, (7.4, y), (7.9, y))
    # joint_states feedback
    ax.plot([13.7, 13.95], [3.35, 3.35], color="#1f4e79", lw=1.4); ax.plot([13.95, 13.95], [3.35, 5.0], color="#1f4e79", lw=1.4); arrow(ax, (13.95, 5.0), (13.7, 5.0), color="#1f4e79", lw=1.4)
    label(ax, 13.9, 4.2, "/joint_states", color="#1f4e79", fs=8.5)
    note(ax, 0.3, 2.9, "세 소비자가 같은 문자열을 받는다.", fs=9.5, bold=True)
    note(ax, 0.3, 2.45, "그래서 링크 · 관절 이름이 어디서나 같다:", fs=9.5)
    note(ax, 0.3, 2.0, "MuJoCo 가 낸 /joint_states 를", fs=9.5)
    note(ax, 0.3, 1.55, "robot_state_publisher 가 그대로 받아 TF 를 만든다.", fs=9.5)
    note(ax, 0.3, 0.3, "펼친 URDF 는 artifacts/mobile_generated/robot.urdf 로 저장돼 브리지에 파일로 전달된다", fs=9)
    save(fig, "lesson02_rel_flow.png")


def rel_xacro():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "mobile_openarm.urdf.xacro 의 조립 순서 (위에서 아래로 include)", bold=True, fs=12)
    ys = vchain(ax, [("① include vicpinky robot_core.xacro", ["base_footprint · base_link · 바퀴 · 캐스터 · laser_link"]),
                     ("② joint base_to_openarm_mount + link arm_adapter_plate", ["base_link → openarm_mount, xyz = (mount_x, 0, mount_z)"]),
                     ("③ include openarm_robot.xacro + xacro:openarm_robot 호출", ["body_connected_to = openarm_mount · bimanual · left/right_arm_base_xyz"]),
                     ("④ include cameras.xacro", ["base · head · left_wrist · right_wrist 카메라 (cameras.yaml)"])],
                x=0.3, w=8.6, y_top=4.85, h=0.85, gap=0.28, colors=[C["yellow"], C["green"], C["yellow"], C["green"]], tfs=10, fs=8.4)
    rbox(ax, 9.4, 1.5, 4.3, 3.35, "xacro:arg (기본값)", ["mount_x = 0.0 · mount_z = 0.13", "arm_type = body_type = v10", "bimanual = true", "ros2_control = false", "left_arm_base_xyz = 0 0.031 0.698", "right_arm_base_xyz = 0 -0.031 0.698", "ee_type = parallel_link"], fc=C["grey"], tfs=10.5, fs=8.4, align="left", dy=0.33)
    note(ax, 0.3, 0.3, "노랑 = 상류 파일을 그대로 include · 초록 = 우리가 쓴 부분.  결과 URDF: 링크 46 · 관절 49 (그중 fixed 25)", fs=9.5)
    save(fig, "lesson02_rel_xacro.png")


def rel_added():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "URDF → MJCF: 그대로 가는 것과 더해지는 것", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 0.5), 5.4, 4.5, fc="#F4F8FF", ec="#8FA9D6", lw=1.2, zorder=1))
    note(ax, 0.5, 4.75, "URDF 에서 그대로 옮기는 것", bold=True, fs=11, color="#1f4e79")
    tiles_at(ax, [("link → body", ["이름 · 부모 기준 위치 · 관성"], C["blue"]), ("joint → joint", ["revolute·continuous → hinge", "prismatic → slide · range"], C["blue"]),
                  ("visual · collision → geom", ["메시는 .obj 로 변환", "group 2 (보기) · group 1 (충돌)"], C["blue"]), ("mimic → equality", ["finger_joint2 = finger_joint1"], C["blue"])],
             cols=2, x0=0.5, x1=5.5, y_top=4.5, gap=0.2, h=1.75, tfs=9.8, fs=8.0)
    ax.add_patch(Rectangle((6.0, 0.5), 7.7, 4.5, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 6.2, 4.75, "MJCF 에서 새로 더하는 것 (URDF 에는 없음)", bold=True, fs=11, color="#2e7d32")
    tiles_at(ax, [("freejoint floating_base", ["base_footprint 가 세계에서 자유롭게"], C["green"]), ("actuator 18개", ["바퀴 velocity 2 · 관절 position 16"], C["green"]),
                  ("site lidar · camera 4", ["laser_link 에 레이 원점", "*_optical_frame 에 카메라"], C["green"]), ("option · default", ["timestep 2 ms · noslip · 마찰"], C["green"]),
                  ("창고 · 상자 · 배우 · 마커", ["worlds/warehouse.yaml · actors.yaml", "ArUco 텍스처 평면"], C["orange"]), ("contact exclude 110", ["이웃 링크끼리 충돌 무시"], C["orange"])],
             cols=3, x0=6.2, x1=13.5, y_top=4.5, gap=0.2, h=1.75, tfs=9.8, fs=8.0)
    note(ax, 0.3, 0.2, "실행할 때마다 다시 생성한다 (artifacts/mobile_generated/warehouse.xml).  MJCF 를 손으로 고치지 않는다.", fs=9.5)
    save(fig, "lesson02_rel_added.png")


def rel_names():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "이름이 그대로라서 맞물린다", bold=True, fs=12)
    rows = (("URDF <link name=\"openarm_left_link3\">", "MJCF <body name=\"openarm_left_link3\">", "TF 프레임 openarm_left_link3"),
            ("URDF <joint name=\"openarm_left_joint3\">", "MJCF <joint name=\"openarm_left_joint3\">", "/joint_states name[i]"),
            ("URDF <link name=\"laser_link\">", "MJCF body + site \"lidar\"", "/scan frame_id = laser_link"))
    for k, (a, b, c) in enumerate(rows):
        y = 3.2 - k * 0.95
        rbox(ax, 0.3, y - 0.3, 4.2, 0.65, a, fc=C["blue"], tfs=9.2)
        arrow(ax, (4.5, y + 0.025), (5.0, y + 0.025)); rbox(ax, 5.0, y - 0.3, 4.2, 0.65, b, fc=C["green"], tfs=9.2)
        arrow(ax, (9.2, y + 0.025), (9.7, y + 0.025)); rbox(ax, 9.7, y - 0.3, 4.0, 0.65, c, fc=C["yellow"], tfs=9.2)
    note(ax, 0.3, 0.35, "브리지가 /joint_states 에 넣는 name 은 MJCF 관절 이름 = URDF 관절 이름.  robot_state_publisher 는 이 이름으로 URDF 관절을 찾아 TF 를 계산한다.", fs=9.2)
    save(fig, "lesson02_rel_names.png")


def rel_tf():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "TF 는 누가 내나: 브리지 · robot_state_publisher · AMCL", bold=True, fs=12)
    rbox(ax, 0.3, 3.4, 3.6, 1.5, "브리지 (MuJoCo)", ["바퀴 오도메트리 →", "odom → base_footprint  (50 Hz)"], fc=C["teal"], tfs=10.5, fs=8.4)
    rbox(ax, 0.3, 1.3, 3.6, 1.5, "브리지 (MuJoCo)", ["/joint_states  (50 Hz)", "관절 20개 위치 · 속도"], fc=C["teal"], tfs=10.5, fs=8.4)
    rbox(ax, 5.2, 1.3, 3.6, 1.5, "robot_state_publisher", ["URDF + /joint_states →", "움직이는 관절: /tf", "고정 관절: /tf_static"], fc=C["blue"], tfs=10.5, fs=8.4)
    rbox(ax, 5.2, 3.4, 3.6, 1.5, "AMCL 또는 SLAM", ["map → odom"], fc=C["purple"], tfs=10.5, fs=8.4)
    arrow(ax, (3.9, 2.05), (5.2, 2.05)); label(ax, 4.55, 2.3, "/joint_states", fs=8.5)
    # resulting tree
    ax.add_patch(Rectangle((10.0, 0.5), 3.7, 4.4, fc="#FAFAFA", ec="#B0B7C3", lw=1.0, zorder=1))
    note(ax, 10.2, 4.65, "TF 트리", bold=True, fs=11)
    ys = vchain(ax, [("map", []), ("odom", []), ("base_footprint", []), ("base_link", []), ("… openarm_*_link7 · laser_link · camera", [])],
                x=10.2, w=3.3, y_top=4.4, h=0.55, gap=0.3, colors=[C["purple"], C["teal"], C["teal"], C["blue"], C["blue"]], tfs=9.2)
    note(ax, 0.3, 0.6, "브리지는 팔 · 바퀴 · 센서 링크의 TF 를 내지 않는다.  URDF 의 모든 링크 프레임은 robot_state_publisher 가 만든다.", fs=9.5)
    save(fig, "lesson02_rel_tf.png")


def rel_display():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "시뮬레이터 없이 보기: display.launch.py 는 /joint_states 공급자만 바꾼다", bold=True, fs=12)
    rbox(ax, 0.3, 2.4, 3.6, 1.4, "joint_state_publisher_gui", ["슬라이더 → /joint_states", "(gui:=false 면 0 으로 고정)"], fc=C["orange"], tfs=10.5, fs=8.4)
    rbox(ax, 0.3, 0.5, 3.6, 1.4, "브리지 (시뮬레이터 실행 시)", ["MuJoCo → /joint_states"], fc=C["teal"], tfs=10.5, fs=8.4)
    rbox(ax, 5.2, 1.4, 3.6, 1.5, "robot_state_publisher", ["같은 URDF", "/robot_description · /tf · /tf_static"], fc=C["blue"], tfs=10.5, fs=8.4)
    rbox(ax, 10.1, 1.4, 3.6, 1.5, "RViz2 (display.rviz)", ["RobotModel ← /robot_description", "TF 표시 · Fixed Frame base_footprint"], fc=C["grey"], tfs=10.5, fs=8.4)
    ax.plot([3.9, 4.55], [3.1, 3.1], color=INK, lw=1.6); ax.plot([3.9, 4.55], [1.2, 1.2], color=INK, lw=1.6); ax.plot([4.55, 4.55], [1.2, 3.1], color=INK, lw=1.6); arrow(ax, (4.55, 2.15), (5.2, 2.15))
    label(ax, 4.55, 3.4, "둘 중 하나만", color="#C62828", fs=8.5)
    arrow(ax, (8.8, 2.15), (10.1, 2.15))
    note(ax, 0.3, 0.15, "둘 다 띄우면 /joint_states 와 /tf 가 두 군데서 나와 로봇이 떨린다.  display 는 시뮬레이터를 끄고 쓴다.", fs=9.5)
    save(fig, "lesson02_rel_display.png")


# ================================================================ 3. code
def code_expand():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "expand_urdf: xacro 파일 → URDF 문자열 (Python API)", bold=True, fs=12)
    chain(ax, [("get_package_share_directory", ["설치된 패키지 경로", "share/mobile_openarm_description"]), ("mappings → options", ["mount_x 등 xacro:arg", "ros2_control 은 항상 false"]),
               ("xacro.process_file()", ["include 와 macro 를 모두 펼친다"]), (".toxml()", ["URDF 문자열 하나", "파일로 안 거친다"])],
          y=0.6, h=2.1, colors=[C["grey"], C["grey"], C["yellow"], C["green"]], tfs=10.5, fs=8.6)
    save(fig, "lesson02_code_expand.png")


def code_launch():
    fig, ax = fig_ax(14, 6.0)
    note(ax, 0.3, 5.7, "warehouse.launch.py setup(): 한 번 펼쳐 세 곳에", bold=True, fs=12)
    rbox(ax, 0.3, 3.4, 3.4, 1.5, "urdf = expand_urdf()", ["OpaqueFunction 안에서", "launch 시작 때 한 번"], fc=C["yellow"], tfs=10.5, fs=8.4)
    rbox(ax, 0.3, 0.5, 3.4, 1.4, "path.write_text(urdf)", ["artifacts/mobile_generated/robot.urdf"], fc=C["grey"], tfs=10.5, fs=8.4)
    arrow(ax, (2.0, 3.4), (2.0, 1.9))
    tiles_at(ax, [("ExecuteProcess 브리지", ["python -m mobile_openarm_mujoco.bridge", "--urdf-file robot.urdf --output-dir …", "→ build_model() 로 MJCF 생성"], C["teal"]),
                  ("Node robot_state_publisher", ["parameters = {robot_description: urdf,", "              use_sim_time: True}"], C["blue"]),
                  ("IncludeLaunchDescription MoveIt", ["urdf_file 로 같은 파일 전달", "moveit:=true 일 때"], C["purple"])],
             cols=1, x0=5.2, x1=13.7, y_top=5.3, gap=0.2, h=1.5, tfs=10, fs=8.3)
    for y in (4.55, 2.85, 1.15):
        arrow(ax, (3.7, y), (5.2, y))
    save(fig, "lesson02_code_launch.png")


def code_build():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "build_model: URDF 트리를 읽고 MJCF 뼈대를 세운다", bold=True, fs=12)
    flow_rows(ax, [("URDF 파싱", "ET.fromstring(urdf)"), ("links · children 사전", "이름 → 요소 · 부모 → 자식 joint"), ("<compiler> <option>", "radian · eulerseq XYZ · timestep"),
                   ("창고 · 상자 · 배우 · 마커", "worlds/*.yaml → worldbody"), ("link(world, \"base_footprint\")", "재귀로 로봇 body 트리"), ("contact · equality · actuator", "제외 쌍 · mimic · 액추에이터")],
              per_row=3, y_top=3.9, h=1.3, gap=0.3, row_gap=0.55, colors=[C["grey"], C["grey"], C["yellow"], C["orange"], C["green"], C["green"]], tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.3, "ElementTree 로 XML 을 만들고 warehouse.xml 로 쓴다.  MuJoCo 의 URDF 로더는 쓰지 않는다 (제어 · 센서 · 창고를 함께 넣기 위해).", fs=9.2)
    save(fig, "lesson02_code_build.png")


def code_link():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "link(): URDF 링크 하나 → MJCF body 하나, 자식으로 재귀", bold=True, fs=12)
    chain(ax, [("<body name=…>", ["pos · euler ← joint origin", "루트는 spawn 위치"]), ("joint (있으면)", ["다음 그림"]),
               ("<inertial>", ["관성 텐서를 body 축으로", "회전 → fullinertia"]), ("geom ×N", ["visual · collision", "→ geometry()"]),
               ("site · camera", ["laser_link 와", "*_optical_frame 만"]), ("자식 링크 재귀", ["자식 joint 마다", "link(body, child, joint)"])],
          y=1.4, h=2.1, gap=0.22, colors=[C["green"], C["yellow"], C["grey"], C["blue"], C["orange"], C["green"]], tfs=9.8, fs=8.0)
    note(ax, 0.3, 0.6, "URDF: joint 가 부모 · 자식을 잇는다  →  MJCF: 자식 body 가 부모 body 안에 들어가고 joint 는 자식 body 안에 놓인다 (lesson 01 의 트리 규칙)", fs=9.2)
    save(fig, "lesson02_code_link.png")


def code_joint():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "관절 변환 규칙", bold=True, fs=12)
    tiles(ax, [("joint 없음 (루트)", ["<freejoint name=\"floating_base\"/>", "base_footprint 가 세계에서 6자유도", "spawn 위치가 초기 pos"], C["orange"]),
               ("fixed", ["joint 를 만들지 않는다", "body 만 부모 안에 pos · euler 로 고정", "fusestatic=false 라 body 는 남는다 (TF 이름 유지)"], C["grey"]),
               ("revolute · continuous", ["type=\"hinge\" axis=xyz", "revolute 만 range=lower upper", "damping 0.1 · armature 0.01"], C["yellow"]),
               ("prismatic", ["type=\"slide\" axis=xyz", "range=lower upper", "armature 0.001 (그리퍼 손가락)"], C["yellow"])],
          cols=4, y_top=3.5, gap=0.25, h=2.4, tfs=10.5, fs=8.2)
    note(ax, 0.3, 0.35, "관절 이름은 URDF 그대로 → /joint_states 의 name 이 된다", fs=9.5)
    save(fig, "lesson02_code_joint.png")


def code_geom():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "geometry(): visual · collision → geom", bold=True, fs=12)
    tiles(ax, [("visual → geom", ["group 2 · contype 0 (보기만)", "rgba 는 URDF material 색"], C["blue"]), ("collision → geom", ["group 1 · contype 2 · conaffinity 3", "rgba 투명"], C["green"]),
               ("mesh", ["package:// 경로 → resolve_mesh", "trimesh 로 scale 을 굽고 .obj 저장", "같은 메시는 한 번만 (sha 이름)"], C["yellow"]),
               ("box · sphere · cylinder", ["URDF size 는 전체 길이", "MJCF size 는 절반 → /2"], C["grey"])],
          cols=4, y_top=3.9, gap=0.25, h=2.3, tfs=10.5, fs=8.2)
    note(ax, 0.3, 0.9, "바퀴 · 캐스터만 예외: 마찰을 따로 주고, 바퀴 충돌 원통은 타원체로 바꾼다 (mujoco.yaml motors.contact_shape)", fs=9.2)
    note(ax, 0.3, 0.45, "결과: geom 255개 · 변환된 메시 41개", fs=9.2)
    save(fig, "lesson02_code_geom.png")


def code_sensor():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "센서 자리: URDF 링크 이름을 보고 site 와 camera 를 붙인다", bold=True, fs=12)
    chain(ax, [("name == \"laser_link\"", ["<site name=\"lidar\"/>", "레이캐스트 원점"]), ("Physics.scan()", ["mj_multiRay 360줄", "group 0 만 맞춘다"]), ("/scan", ["frame_id laser_link", "10 Hz"])],
          y=2.1, h=1.5, colors=[C["blue"], C["teal"], C["yellow"]], tfs=10.5, fs=8.4)
    chain(ax, [("name in *_optical_frame", ["<camera name=base_camera …/>", "quat 0 1 0 0 · fovy (cameras.yaml)"]), ("카메라 핸들러", ["Renderer 로 렌더", "같은 프로세스에서 검출"]), ("/vision/*", ["영상 토픽은 없음"])],
          y=0.4, h=1.5, colors=[C["blue"], C["teal"], C["yellow"]], tfs=10.5, fs=8.4)
    save(fig, "lesson02_code_sensor.png")


def code_act():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "액추에이터: URDF 에 없는 것을 mujoco.yaml 값으로 만든다", bold=True, fs=12)
    tiles(ax, [("바퀴 2개 → <velocity>", ["left_motor · right_motor", "joint = *_wheel_joint", "kv 10 · ctrlrange ±8 rad/s · force ±18 N·m", "브리지 /cmd_vel → 좌우 바퀴 속도"], C["orange"]),
               ("팔 관절 14개 → <position>", ["이름 = 관절이름_position", "kp 500 · kv 35", "ctrlrange = URDF limit lower~upper", "forcerange = URDF effort"], C["yellow"]),
               ("그리퍼 finger_joint1 × 2 → <position>", ["prismatic 이라 gripper 게인", "kp 1800 · kv 15 · max 30 N", "finger_joint2 는 mimic 이라 제외"], C["yellow"])],
          cols=3, y_top=3.7, gap=0.3, h=2.6, tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.35, "Gazebo 라면 ros2_control 컨트롤러 YAML 이 하던 일.  ctrl 에 목표 각도를 쓰면 관절이 따라간다 → FollowJointTrajectory 액션이 이 위에 있다.", fs=9.2)
    save(fig, "lesson02_code_act.png")


def code_mimic():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "mimic → equality: 그리퍼 손가락 둘을 한 값으로", bold=True, fs=12)
    chain(ax, [("URDF <mimic joint=…/>", ["finger_joint2 안에 있음", "multiplier 1 · offset 0"]), ("<equality><joint …/>", ["joint1 = finger_joint2", "joint2 = finger_joint1", "polycoef = offset multiplier 0 0 0"]),
               ("MuJoCo 제약", ["두 관절 값을 같게 유지", "solref 0.004 1"]), ("액추에이터는 하나", ["finger_joint1 에만", "joint2 는 따라간다"])],
          y=0.5, h=2.2, colors=[C["blue"], C["green"], C["teal"], C["yellow"]], tfs=10, fs=8.2)
    save(fig, "lesson02_code_mimic.png")


def code_physics():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "Physics.__init__: MJCF 를 읽고 이름으로 번호를 잡아 둔다", bold=True, fs=12)
    chain(ax, [("MjModel.from_xml_path", ["warehouse.xml", "MjData(model)"]), ("바퀴", ["바퀴 geom 크기 → 반지름", "좌우 body pos 차 → 윤거"]),
               ("joint_names", ["jnt_type 2·3 (slide · hinge)", "= 관절 20개 · freejoint 제외"]), ("q_indices · v_indices", ["qposadr · dofadr", "/joint_states 순서"]), ("initial_positions.yaml", ["qpos · ctrl 초기값", "joint4 = 1.2 · finger 0.025"])],
          y=1.2, h=2.2, gap=0.22, colors=[C["green"], C["grey"], C["yellow"], C["yellow"], C["orange"]], tfs=10, fs=8.0)
    note(ax, 0.3, 0.45, "lesson 01 의 model.joint(name).qposadr 와 같은 방법.  이름이 URDF 와 같아서 그대로 /joint_states 의 name 이 된다.", fs=9.2)
    save(fig, "lesson02_code_physics.png")


def code_state():
    fig, ax = fig_ax(14, 6.0)
    note(ax, 0.3, 5.7, "bridge.publish_state (50 Hz): MuJoCo 상태 → /odom · TF · /joint_states", bold=True, fs=12)
    rbox(ax, 0.3, 0.9, 3.0, 4.4, "MuJoCo", ["p.odom (바퀴 적분)", "p.twist", "data.qpos[q_indices]", "data.qvel[v_indices]"], fc=C["green"], tfs=10.5, fs=8.6, align="left", dy=0.42)
    tiles_at(ax, [("/odom (Odometry)", ["frame odom → child base_footprint", "pose · twist · 공분산"], C["blue"]),
                  ("TF odom → base_footprint", ["odom 과 같은 값 · 같은 stamp", "TransformBroadcaster"], C["blue"]),
                  ("/joint_states (JointState)", ["name = p.joint_names (20개)", "position · velocity"], C["yellow"])],
             cols=1, x0=5.0, x1=9.6, y_top=5.3, gap=0.2, h=1.4, tfs=10, fs=8.2)
    for y in (4.6, 3.0, 1.4):
        arrow(ax, (3.3, y), (5.0, y))
    rbox(ax, 10.6, 3.95, 3.1, 1.3, "AMCL · Nav2", ["odom 사용"], fc=C["purple"], tfs=10, fs=8.4)
    rbox(ax, 10.6, 0.75, 3.1, 1.3, "robot_state_publisher", ["→ /tf 링크 46개"], fc=C["blue"], tfs=10, fs=8.4)
    arrow(ax, (9.6, 4.6), (10.6, 4.6))
    arrow(ax, (9.6, 1.4), (10.6, 1.4))
    note(ax, 0.3, 0.3, "stamp 는 시뮬레이션 시각(/clock).  같은 함수 안에서 나가므로 odom · TF · joint_states 시각이 같다.", fs=9.2)
    save(fig, "lesson02_code_state.png")


def code_display():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "display.launch.py: 노드 셋, 인자 둘", bold=True, fs=12)
    chain(ax, [("urdf = expand_urdf()", ["같은 함수"]), ("robot_state_publisher", ["robot_description = urdf"]), ("joint_state_publisher_gui", ["gui:=false 면 joint_state_publisher", "robot_description = urdf"]), ("rviz2 -d display.rviz", ["rviz:=false 면 생략"])],
          y=1.0, h=2.0, colors=[C["yellow"], C["blue"], C["orange"], C["grey"]], tfs=10, fs=8.4)
    note(ax, 0.3, 0.4, "OpaqueFunction(setup) 이라 LaunchConfiguration 값을 Python 에서 바로 읽는다.  브리지 · Nav2 · MoveIt 은 없다.", fs=9.2)
    save(fig, "lesson02_code_display.png")

# ================================================================ 1b. features of the two upstream robots (from the official sites)
def feat_openarm():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "OpenARM 특징 (docs.openarm.dev 요약)", bold=True, fs=12)
    tiles(ax, [("오픈소스 7자유도 휴머노이드 팔", ["Enactic 공개 · Apache-2.0", "접촉 많은 환경의 physical AI 연구용", "CAD · 펌웨어 · 제어 코드 전부 공개"], C["yellow"]),
               ("사람 크기", ["키 160~165 cm 비율", "리치 606 mm · 팔 무게 5.5 kg", "몸통 하나에 팔 둘 (bimanual)"], C["yellow"]),
               ("가반하중", ["공칭 4.1 kg (1분 유지)", "최대 6.0 kg (들었다 놓기)", "그리퍼 무게 포함"], C["green"]),
               ("QDD 백드라이버블 모터", ["사람과 부딪혀도 안전", "양방향 힘 피드백 텔레오퍼레이션", "→ 데이터 수집 · 모방학습"], C["green"]),
               ("제어 · 구조", ["CAN-FD 1 kHz", "알루미늄 · 스테인리스", "부품 원가(BOM) 약 6,500달러"], C["grey"]),
               ("생태계", ["OpenArm Cell: 평가용 표준 셀", "KER: 모터 없는 리더 팔", "(같은 기구학 · 텔레옵 · 교시)"], C["grey"]),
               ("버전", ["사이트 = OpenArm 2.0", "우리 패키지 = v1.0 자산 (openarm_v1.0)", "관절 범위 같음 (J1 -80° ~ +200°)"], C["orange"]),
               ("우리가 쓰는 방식", ["xacro:openarm_robot 매크로 호출만", "ros2_control · CAN 은 끈다", "그리퍼 parallel_link · mimic"], C["blue"])],
          cols=4, y_top=4.25, gap=0.25, h=1.75, tfs=10.5, fs=8.4)
    save(fig, "lesson02_feat_openarm.png")


def feat_vicpinky():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "Vic Pinky 특징 (pinklab.art/vic-pinky 요약)", bold=True, fs=12)
    tiles(ax, [("모빌리티 플랫폼", ["\"Move the Body of Intelligence\"", "로봇 · 장비를 싣고 공간을 이동", "PinkLAB (핑크랩)"], C["yellow"]),
               ("양팔 로봇과 결합", ["주행 + 조작 = 반주반인 로봇", "이 과정의 로봇이 그 구성", "상판에 OpenARM 을 얹는다"], C["yellow"]),
               ("크기 · 탑재", ["539(W) × 600(D) × 215(H) mm", "최대 탑재 중량 70 kg", "상판에 장비를 올리는 구조"], C["green"]),
               ("구동", ["150 W DC 기어드 모터 × 2", "6.5인치 바퀴 × 2 + 캐스터", "차동 구동 → 제자리 회전"], C["green"]),
               ("전원 · 포트", ["배터리 12 V 7 Ah × 2", "외부 USB · 5 V 전원"], C["grey"]),
               ("용도", ["작업 영역 확장 (고정형 로봇 보완)", "라이다 자율주행: 공정 간 이동 · 자재 운반", "교육 · 데모 · 전시"], C["grey"]),
               ("robot_core.xacro 와 대응", ["차체 0.6 × 0.5 m · 높이 0.128 m", "윤거 0.4288 m · 바퀴 반지름 0.0825 m", "= 6.5인치 바퀴"], C["orange"]),
               ("우리가 쓰는 방식", ["robot_core.xacro 만 include", "Gazebo · 센서 xacro 는 안 씀", "바퀴 → MJCF velocity 액추에이터"], C["blue"])],
          cols=4, y_top=4.25, gap=0.25, h=1.75, tfs=10.5, fs=8.4)
    save(fig, "lesson02_feat_vicpinky.png")


# ================================================================ 3-0. who imports model.py, what comes out, who uses it
def code_derived():
    fig, ax = fig_ax(14, 8.9)
    note(ax, 0.3, 8.6, "model.py 를 누가 import 하고, 어떤 파생물이 나와 누가 쓰나", bold=True, fs=12)
    T = 2.7  # everything above the derived-files row is shifted up by T
    rbox(ax, 0.3, 2.9 + T, 3.2, 2.3, "원본 (src/)", ["mobile_openarm.urdf.xacro", "cameras.yaml · gripper_inertials.yaml", "collision_exclusions.json · 메시 dae · stl"], fc=C["yellow"], tfs=10.5, fs=8.2)
    rbox(ax, 0.3, 0.6 + T, 3.2, 1.6, "mobile_openarm_description/", ["model.py", "def expand_urdf()"], fc=C["green"], tfs=10, fs=9)
    arrow(ax, (1.9, 2.9 + T), (1.9, 2.2 + T)); label(ax, 1.9, 2.55 + T, "xacro.process_file", fs=8.4)
    ax.add_patch(Rectangle((4.4, 0.4 + T), 4.6, 4.8, fc="#F6F2FB", ec="#9C8AC6", lw=1.2, zorder=1))
    note(ax, 4.6, 4.95 + T, "import 하는 곳 (launch 시점에 호출)", bold=True, fs=10.5, color="#5E4B8B")
    rbox(ax, 4.6, 3.6 + T, 4.2, 1.0, "warehouse.launch.py", ["시뮬레이터 실행 · 주 경로"], fc=C["purple"], tfs=10, fs=8.4)
    rbox(ax, 4.6, 2.4 + T, 4.2, 1.0, "display.launch.py", ["URDF 만 보기"], fc=C["purple"], tfs=10, fs=8.4)
    rbox(ax, 4.6, 1.2 + T, 4.2, 1.0, "moveit_config/config.py · mujoco/model.py", ["URDF 를 안 받았을 때만 (대체 경로)"], fc=C["grey"], tfs=9.4, fs=8.2)
    ax.plot([3.5, 3.95], [1.4 + T, 1.4 + T], color=INK, lw=1.6); ax.plot([3.95, 3.95], [1.4 + T, 4.1 + T], color=INK, lw=1.6)
    for y in (4.1, 2.9, 1.7):
        arrow(ax, (3.95, y + T), (4.6, y + T))
    rbox(ax, 9.9, 4.2 + T, 3.8, 0.9, "URDF 문자열 (메모리)", fc=C["orange"], tfs=10)
    rbox(ax, 9.9, 2.9 + T, 3.8, 0.9, "robot.urdf (파일)", ["artifacts/mobile_generated/"], fc=C["orange"], tfs=10, fs=8.2)
    ax.plot([8.8, 9.35], [4.1 + T, 4.1 + T], color=INK, lw=1.6); ax.plot([9.35, 9.35], [3.35 + T, 4.65 + T], color=INK, lw=1.6)
    arrow(ax, (9.35, 4.65 + T), (9.9, 4.65 + T)); arrow(ax, (9.35, 3.35 + T), (9.9, 3.35 + T))
    label(ax, 9.35, 3.75 + T, "write_text", fs=8.2)
    rbox(ax, 9.9, 1.5 + T, 3.8, 0.9, "robot_state_publisher", ["robot_description 파라미터 → /robot_description"], fc=C["blue"], tfs=10, fs=7.8)
    rbox(ax, 9.9, 0.4 + T, 3.8, 0.9, "브리지 --urdf-file", ["build_model(urdf) 호출"], fc=C["teal"], tfs=10, fs=8.2)
    ax.plot([13.85, 14.0], [4.65 + T, 4.65 + T], color="#1f4e79", lw=1.4); ax.plot([14.0, 14.0], [1.95 + T, 4.65 + T], color="#1f4e79", lw=1.4); arrow(ax, (14.0, 1.95 + T), (13.7, 1.95 + T), color="#1f4e79", lw=1.4)
    ax.plot([13.85, 13.98], [3.35 + T, 3.35 + T], color="#2a6f68", lw=1.4); ax.plot([13.98, 13.98], [0.85 + T, 3.35 + T], color="#2a6f68", lw=1.4); arrow(ax, (13.98, 0.85 + T), (13.7, 0.85 + T), color="#2a6f68", lw=1.4)
    # ---- derived files produced by build_model (bottom row) ----
    ax.add_patch(Rectangle((0.3, 0.55), 13.4, 2.4, fc="#EEF8F7", ec="#5FA8A0", lw=1.2, zorder=1))
    note(ax, 0.5, 2.72, "build_model() 이 robot.urdf 에서 만드는 파생물 (artifacts/mobile_generated/)", bold=True, fs=10.5, color="#2a6f68")
    arrow(ax, (11.8, 0.4 + T), (11.8, 2.3), color="#2a6f68", lw=1.6)
    rbox(ax, 0.5, 0.7, 3.0, 1.3, "mobile_openarm.urdf", ["파싱한 URDF 를 다시 쓴 기록"], fc=C["orange"], tfs=9.8, fs=8.0)
    rbox(ax, 3.8, 0.7, 3.4, 1.3, "*_<sha>.obj  (41개)", ["dae · stl → obj · 스케일 굽기", "원본이 바뀔 때만 다시 변환"], fc=C["orange"], tfs=9.8, fs=8.0)
    rbox(ax, 7.5, 0.7, 3.0, 1.3, "warehouse.xml  (MJCF)", ["로봇 + 액추에이터 · 센서 · 창고"], fc=C["orange"], tfs=9.8, fs=8.0)
    rbox(ax, 10.9, 0.7, 2.6, 1.3, "MuJoCo", ["MjModel.from_xml_path", "obj 는 <asset> 으로 참조"], fc=C["green"], tfs=9.8, fs=8.0)
    arrow(ax, (10.5, 1.35), (10.9, 1.35))
    ax.plot([2.0, 11.8], [2.3, 2.3], color="#2a6f68", lw=1.2)
    for x in (2.0, 5.5, 9.0):
        arrow(ax, (x, 2.3), (x, 2.0), color="#2a6f68", lw=1.2)
    note(ax, 0.3, 0.15, "파생물은 매 실행마다 다시 만든다 (xacro 약 0.1 s · MJCF 약 0.3 s).  원본 xacro · YAML · launch 인자가 바뀌면 결과도 바뀌기 때문이다.  obj 만 캐시된다.", fs=9.2)
    save(fig, "lesson02_code_derived.png")

if __name__ == "__main__":
    for f in (pkg_kinds, feat_openarm, feat_vicpinky, pkg_assembly, rel_flow, rel_xacro, rel_added, rel_names, rel_tf, rel_display,
              code_derived, code_expand, code_launch, code_build, code_link, code_joint, code_geom, code_sensor, code_act, code_mimic, code_physics, code_state, code_display):
        f()
