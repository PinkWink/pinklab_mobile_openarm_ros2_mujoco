"""Figures for the page "URDF 에서 MuJoCo 로, MuJoCo 에서 ROS 2 로" (lessons/01_mujoco_ros2: two_link_arm.urdf,
urdf_to_mjcf.py, urdf_bridge.py, view_urdf.launch.py). Output: docs/camp/lesson01c_*.png

  python docs/camp/draw_lesson01c_figures.py [capture folder]     # run from the workspace root

The capture folder (window screenshots + command logs taken while running the lesson) is only needed for the
composite pictures and terminal renders; without it only the diagrams are drawn.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, OUT, arrow, chain, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BLUE, GREEN, PURPLE, BROWN = "#1f4e79", "#2e7d32", "#5e4b8b", "#7a4b00"


def band(ax, x, y, w, h, title, fc, ec, color):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.3, zorder=1))
    note(ax, x + 0.2, y + h - 0.28, title, bold=True, fs=11, color=color)


# ------------------------------------------------------------------ 1. big picture
def steps():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "ROS 2 사용자가 MuJoCo 를 붙이는 세 단계", bold=True, fs=12)
    band(ax, 0.3, 0.9, 5.6, 3.5, "① 모델: URDF → MJCF", "#F3F7FF", "#8FAADC", BLUE)
    band(ax, 6.2, 0.9, 3.4, 3.5, "② 연결: 브리지", "#F5F1FB", "#9C8BC9", PURPLE)
    band(ax, 9.9, 0.9, 3.8, 3.5, "③ 확인: ROS 2 도구", "#F1F8F1", "#7CB07C", GREEN)
    rbox(ax, 0.55, 2.35, 1.55, 1.4, "URDF", ["로봇만", "링크 · 관절"], fc=C["blue"], tfs=10.5, fs=8.6)
    rbox(ax, 2.4, 2.35, 1.6, 1.4, "변환", ["MuJoCo 가 읽고", "빠진 것 추가"], fc=C["yellow"], tfs=10.5, fs=8.6)
    rbox(ax, 4.3, 2.35, 1.4, 1.4, "MjModel", ["바닥 · 액추에이터", "카메라 포함"], fc=C["green"], tfs=10.5, fs=8.2)
    arrow(ax, (2.1, 3.05), (2.4, 3.05)); arrow(ax, (4.0, 3.05), (4.3, 3.05)); arrow(ax, (5.7, 3.05), (6.45, 3.05))
    rbox(ax, 6.45, 2.35, 2.9, 1.4, "mj_step 루프", ["상태 → 토픽 발행", "명령 토픽 → data.ctrl"], fc=C["purple"], tfs=10.5, fs=8.6)
    rbox(ax, 10.15, 2.35, 3.3, 1.4, "robot_state_publisher · RViz", ["같은 URDF 로 TF 계산", "ros2 topic · tf2_echo"], fc=C["green"], tfs=10, fs=8.6)
    arrow(ax, (9.35, 3.3), (10.15, 3.3), color=BLUE); arrow(ax, (10.15, 2.8), (9.35, 2.8), color=BROWN)
    note(ax, 0.55, 1.75, "two_link_arm.urdf", fs=9, color=BLUE)
    note(ax, 0.55, 1.35, "urdf_to_mjcf.py", fs=9, color=BLUE)
    note(ax, 6.45, 1.75, "urdf_bridge.py", fs=9, color=PURPLE)
    note(ax, 6.45, 1.35, "/clock · /joint_states · 영상 · /cmd", fs=8.6, color=PURPLE)
    note(ax, 10.15, 1.75, "view_urdf.launch.py", fs=9, color=GREEN)
    note(ax, 10.15, 1.35, "MuJoCo 와 RViz 가 같은 자세인지", fs=8.6, color=GREEN)
    note(ax, 0.3, 0.45, "URDF 는 그대로 원본으로 둔다.  ROS 2 쪽 도구는 URDF 를, MuJoCo 는 URDF 에서 만든 모델을 쓴다.", fs=9.5)
    save(fig, "lesson01c_steps.png")


def files():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "이 글에서 쓰는 파일 넷 (lessons/01_mujoco_ros2/)", bold=True, fs=12)
    tiles(ax, [("two_link_arm.urdf", ["로봇 기술 · 106 줄", "링크 5 · 관절 4", "ROS 2 와 MuJoCo 의 공통 원본"], C["blue"]),
               ("urdf_to_mjcf.py", ["변환 · 80 줄", "URDF 읽기 + 빠진 것 추가", "build() 를 브리지가 import"], C["yellow"]),
               ("urdf_bridge.py", ["브리지 노드 · 147 줄", "발행 4 · 구독 1", "TF 는 내지 않음"], C["purple"]),
               ("view_urdf.launch.py", ["RViz 로 보기 · 32 줄", "robot_state_publisher", "sim:=true 면 MuJoCo 와 함께"], C["green"])],
          cols=4, y_top=2.9, gap=0.25, h=1.75, tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.6, "앞 글의 two_link_arm.xml · minimal_bridge.py 와 같은 팔이다.  이번에는 URDF 에서 출발한다.", fs=9.5)
    save(fig, "lesson01c_files.png")


def swap():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "/joint_states 를 누가 내는가만 바뀐다", bold=True, fs=12)
    for y, src, sub, fc, tag in ((2.75, "joint_state_publisher_gui", ["슬라이더 값"], C["grey"], "시뮬레이터 없음"),
                                 (0.95, "urdf_bridge.py (MuJoCo)", ["물리가 계산한 qpos"], C["purple"], "sim:=true")):
        note(ax, 0.3, y + 1.3, tag, bold=True, fs=10, color=BROWN)
        rbox(ax, 0.3, y, 3.4, 1.05, src, sub, fc=fc, tfs=10.5, fs=8.8)
        rbox(ax, 4.5, y, 2.3, 1.05, "/joint_states", ["sensor_msgs/JointState"], fc=C["blue"], tfs=10.5, fs=8.4)
        rbox(ax, 7.6, y, 3.0, 1.05, "robot_state_publisher", ["URDF 로 순기구학 → /tf"], fc=C["green"], tfs=10.5, fs=8.6)
        rbox(ax, 11.4, y, 2.3, 1.05, "RViz", ["로봇 모델 · TF"], fc=C["green"], tfs=10.5, fs=8.8)
        for a, b in ((3.7, 4.5), (6.8, 7.6), (10.6, 11.4)):
            arrow(ax, (a, y + 0.52), (b, y + 0.52))
    note(ax, 0.3, 0.4, "오른쪽 세 칸은 두 경우 모두 같은 노드 · 같은 URDF 다.  시뮬레이터를 붙여도 ROS 2 쪽은 손대지 않는다.", fs=9.5)
    save(fig, "lesson01c_swap.png")


# ------------------------------------------------------------------ 2. URDF
def urdf_tree():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "two_link_arm.urdf: 링크 다섯을 관절 넷이 잇는다", bold=True, fs=12)
    links = ["base_link", "link1", "link2", "camera_link", "camera_optical_frame"]
    joints = [("joint1", "revolute", "xyz 0 0 0.06", "axis 0 1 0"), ("joint2", "revolute", "xyz 0 0 0.30", "axis 0 1 0"),
              ("camera_joint", "fixed", "xyz 0 0 0.26", ""), ("camera_optical_joint", "fixed", "xyz 0 0 0.01", "rpy 0 0 -1.57")]
    w, gap, x = 1.92, 0.95, 0.3
    for i, name in enumerate(links):
        rbox(ax, x, 2.9, w, 0.95, name, fc=C["blue"], tfs=10 if len(name) < 14 else 8.4)
        if i < len(joints):
            jn, jt, o, a = joints[i]
            arrow(ax, (x + w, 3.37), (x + w + gap, 3.37))
            jx = x + w + gap / 2
            rbox(ax, jx - 1.25, 0.95, 2.5, 1.55, jn, [jt, o, a] if a else [jt, o], fc=C["yellow"] if jt == "revolute" else C["grey"], tfs=9.6 if len(jn) < 14 else 8.8, fs=8.6)
            ax.plot([jx, jx], [2.5, 3.37], color=BROWN, lw=1.3, zorder=4)
        x += w + gap
    note(ax, 0.3, 4.15, "<link>  부품 하나 (강체)", fs=9.5, color=BLUE)
    note(ax, 4.2, 4.15, "<joint>  parent 링크 → child 링크 · origin = 부모 기준 child 위치", fs=9.5, color=BROWN)
    note(ax, 0.3, 0.45, "노랑 = 움직이는 관절 (/joint_states 에 나옴).  회색 = fixed, 움직이지 않지만 프레임 이름은 남는다.", fs=9.5)
    save(fig, "lesson01c_urdf_tree.png")


def link_parts():
    fig, ax = fig_ax(14, 3.9)
    note(ax, 0.3, 3.6, "<link> 안의 세 가지: 보이는 것 · 부딪히는 것 · 무게", bold=True, fs=12)
    tiles(ax, [("<visual>", ["화면에 그리는 모양 · 색", "RViz · 렌더가 사용", "정밀한 mesh 여도 됨"], C["blue"]),
               ("<collision>", ["충돌 계산용 모양", "물리 엔진 · MoveIt 이 사용", "단순한 도형이 유리"], C["orange"]),
               ("<inertial>", ["질량 · 무게중심 · 관성", "동역학이 사용", "CAD 값을 적음"], C["green"])],
          cols=3, y_top=3.2, gap=0.3, h=1.75, tfs=11.5, fs=9.2)
    note(ax, 0.3, 0.85, "셋 다 <origin> 으로 링크 좌표계 안에서의 위치를 준다.  이 팔: visual = collision = 같은 원기둥.", fs=9.5)
    note(ax, 0.3, 0.42, "camera_optical_frame 처럼 셋 다 없는 링크도 된다 → 좌표계 이름만 필요한 경우.", fs=9.5)
    save(fig, "lesson01c_link.png")


def joint_parts():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "<joint>: 두 링크의 관계 한 줄씩", bold=True, fs=12)
    tiles(ax, [("parent · child", ["트리의 위 · 아래", "이름으로 링크를 가리킴"], C["blue"]),
               ("origin", ["부모 좌표계에서 본", "child 좌표계의 위치 · rpy"], C["blue"]),
               ("axis", ["회전 · 이동 축", "child 좌표계 기준"], C["yellow"]),
               ("limit", ["lower · upper [rad]", "effort [N·m] · velocity"], C["yellow"]),
               ("dynamics", ["damping · friction", "관절의 저항"], C["yellow"])],
          cols=5, y_top=4.2, gap=0.22, h=1.45, tfs=10.5, fs=8.6)
    note(ax, 0.3, 2.35, "type", bold=True, fs=10.5, color=BROWN)
    chain(ax, [("revolute", ["한계 있는 회전"]), ("continuous", ["끝없는 회전 (바퀴)"]), ("prismatic", ["직선 이동"]), ("fixed", ["고정 · 좌표계만"])],
          y=0.95, h=1.1, colors=[C["yellow"], C["yellow"], C["yellow"], C["grey"]], tfs=10.5, fs=8.8, arrows=False)
    note(ax, 0.3, 0.45, "각도는 항상 rad, 길이는 m.  관절 각 0 일 때 child 좌표계 = origin 그대로.", fs=9.5)
    save(fig, "lesson01c_joint.png")


def triad(ax, cx, cy, right, up, fwd, s=0.75):
    """A camera drawn from behind: `right`/`up` are labels on the image-right / image-up arrows, `fwd` on the view direction."""
    ax.add_patch(Rectangle((cx - 0.55, cy - 0.4), 1.1, 0.8, fc="#FFFFFF", ec="#888888", lw=1.0, zorder=2))
    arrow(ax, (cx, cy), (cx + s + 0.35, cy), color="#C62828", lw=2.0); label(ax, cx + s + 0.75, cy, right, color="#C62828", fs=9.5)
    arrow(ax, (cx, cy), (cx, cy + (s + 0.2) * (1 if up[0] != "-" else -1)), color=GREEN, lw=2.0)
    label(ax, cx, cy + (s + 0.45) * (1 if up[0] != "-" else -1), up.lstrip("-"), color=GREEN, fs=9.5)
    ax.plot([cx], [cy], marker="o", ms=9, mfc="white", mec=BLUE, mew=2, zorder=6)
    ax.plot([cx], [cy], marker="x" if fwd.startswith("+") else ".", ms=6, color=BLUE, mew=2, zorder=7)
    label(ax, cx + 0.2, cy + (0.75 if up[0] == "-" else -0.75), fwd[1:], color=BLUE, fs=9.5)


def optical():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "카메라 좌표계: ROS 의 optical frame 과 MuJoCo 카메라는 축이 다르다", bold=True, fs=12)
    band(ax, 0.3, 0.95, 6.3, 3.4, "ROS optical frame (REP 103)", "#F3F7FF", "#8FAADC", BLUE)
    band(ax, 7.4, 0.95, 6.3, 3.4, "MuJoCo <camera>", "#F1F8F1", "#7CB07C", GREEN)
    triad(ax, 2.2, 2.75, "x", "-y", "+z 보는 방향 (화면 안쪽)")
    triad(ax, 9.3, 2.35, "x", "y", "--z 보는 방향 (화면 안쪽)")
    note(ax, 3.9, 3.4, "x = 영상 오른쪽", fs=9.5); note(ax, 3.9, 3.0, "y = 영상 아래", fs=9.5); note(ax, 3.9, 2.6, "z = 보는 방향", fs=9.5)
    note(ax, 11.0, 3.4, "x = 영상 오른쪽", fs=9.5); note(ax, 11.0, 3.0, "y = 영상 위", fs=9.5); note(ax, 11.0, 2.6, "-z = 보는 방향", fs=9.5)
    arrow(ax, (6.6, 2.6), (7.4, 2.6), color=BROWN, lw=2)
    label(ax, 7.0, 2.95, "x 축 180°", color=BROWN, fs=9)
    note(ax, 0.3, 0.5, "영상의 frame_id = camera_optical_frame.  MuJoCo 카메라는 그 body 에 quat [0, 1, 0, 0] (x 축으로 180°) 로 단다.", fs=9.5)
    save(fig, "lesson01c_optical.png")


def missing():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "URDF 에 없어서 시뮬레이터 쪽에서 채워야 하는 것", bold=True, fs=12)
    tiles(ax, [("물리 옵션", ["timestep · 중력 · 적분기", "MJCF <option>"], C["yellow"]),
               ("세계", ["바닥 · 빛 · 주변 물체", "MJCF <worldbody>"], C["grey"]),
               ("액추에이터", ["관절을 움직이는 힘", "MJCF <actuator>"], C["orange"]),
               ("센서", ["카메라 · 라이다", "MJCF <camera> · <site>"], C["purple"]),
               ("충돌 규칙", ["어느 쌍을 계산할지", "contype · <exclude>"], C["red"]),
               ("시간", ["시뮬레이션 시각", "브리지가 /clock 발행"], C["teal"])],
          cols=3, y_top=4.2, gap=0.3, h=1.45, tfs=11, fs=9)
    note(ax, 0.3, 0.45, "Gazebo 에서는 <gazebo> 태그 · ros2_control YAML · world 파일이 이 자리를 채운다.  MuJoCo 에서는 MJCF 가 채운다.", fs=9.5)
    save(fig, "lesson01c_missing.png")


# ------------------------------------------------------------------ 3. URDF -> MJCF
def problems():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "URDF 를 그대로 읽으면 생기는 문제 넷과 해결", bold=True, fs=12)
    items = [("고정 링크가 사라짐", ["base_link · camera_link 가 부모에 합쳐짐", "body 6 → 3, 이름으로 못 찾음"], "fusestatic=\"false\""),
             ("<visual> 이 버려짐", ["<collision> 모양만 남음", "카메라 상자가 안 보임"], "discardvisual=\"false\""),
             ("움직일 수단이 없음", ["actuator 0 · camera 0", "팔이 중력에 처짐"], "actuator · camera 추가"),
             ("세계가 없음", ["바닥 · 빛 · 물체 없음", "base 와 link1 이 충돌"], "floor · light · exclude 추가")]
    w, gap = (14 - 0.6 - 0.3 * 3) / 4, 0.3
    for i, (t, lines, fix) in enumerate(items):
        x = 0.3 + i * (w + gap)
        rbox(ax, x, 2.35, w, 1.75, t, lines, fc=C["red"], tfs=10.5, fs=8.4)
        arrow(ax, (x + w / 2, 2.35), (x + w / 2, 1.85), color=GREEN)
        rbox(ax, x, 1.0, w, 0.85, fix, fc=C["green"], tfs=9.6)
    note(ax, 0.3, 0.45, "앞의 둘 = URDF 안의 <mujoco> 태그 한 줄.  뒤의 둘 = urdf_to_mjcf.py 가 MjSpec 으로 추가.", fs=9.5)
    save(fig, "lesson01c_problems.png")


def mapping():
    fig, ax = fig_ax(14, 6.4)
    note(ax, 0.3, 6.1, "URDF → MJCF: MuJoCo 가 알아서 바꾸는 것", bold=True, fs=12)
    rows = [("<link name=…>", "<body name=…>", "이름 그대로 · 트리는 중첩으로"),
            ("<joint type=\"revolute\">", "<joint> (hinge) · child body 안", "continuous → range 없는 hinge"),
            ("<joint type=\"prismatic\">", "<joint type=\"slide\">", ""),
            ("<joint type=\"fixed\">", "joint 없는 body", "fusestatic 이면 부모에 합침"),
            ("<origin xyz rpy>", "pos · quat", "rpy → 쿼터니언 [w x y z]"),
            ("<limit lower upper effort>", "range · actuatorfrcrange", "velocity 는 옮겨지지 않음"),
            ("<dynamics damping>", "damping", ""),
            ("<inertial>", "<inertial>", "없으면 geom × 밀도 1000 으로 계산"),
            ("<visual> · <collision>", "<geom> 둘", "visual: group 1 · 충돌 끔"),
            ("<mimic>", "(없음)", "<equality> 를 직접 추가")]
    y = 5.45
    for a, b, c in rows:
        rbox(ax, 0.3, y, 3.9, 0.46, a, fc=C["blue"], tfs=9.4, lw=1.0)
        arrow(ax, (4.2, y + 0.23), (4.8, y + 0.23))
        rbox(ax, 4.8, y, 4.3, 0.46, b, fc=C["green"] if b != "(없음)" else C["red"], tfs=9.4, lw=1.0)
        note(ax, 9.35, y + 0.23, c, fs=9.2)
        y -= 0.54
    save(fig, "lesson01c_map.png")


def mimic():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.9, "<mimic>: 한 관절이 다른 관절을 따라간다 (모터 하나, 관절 둘)", bold=True, fs=12)
    rbox(ax, 0.3, 1.9, 3.3, 2.1, "URDF <mimic>", ["right = multiplier × left + offset", "예: 평행 그리퍼의 두 손가락", "기준 관절: left_finger_joint"], fc=C["blue"], tfs=10.5, fs=8.6)
    ax.plot([3.6, 4.1], [2.95, 2.95], color=INK, lw=1.6); ax.plot([4.1, 4.1], [1.75, 3.85], color=INK, lw=1.6)
    arrow(ax, (4.1, 3.85), (4.6, 3.85)); arrow(ax, (4.1, 1.75), (4.6, 1.75))
    rbox(ax, 4.6, 3.2, 3.9, 1.3, "ROS 2 쪽: 읽는다", ["joint_state_publisher · MoveIt", "따라가는 관절 값을 계산"], fc=C["green"], tfs=10.5, fs=8.6)
    rbox(ax, 4.6, 1.1, 3.9, 1.3, "MuJoCo 쪽: 옮기지 않는다", ["두 관절이 서로 독립", "left 0.030 m · right 0.000 m"], fc=C["red"], tfs=10.5, fs=8.6)
    arrow(ax, (8.5, 1.75), (9.3, 1.75), color=GREEN)
    rbox(ax, 9.3, 1.1, 4.4, 1.3, "<equality> <joint> 추가", ["두 관절을 구속으로 묶음", "left 0.030 m · right 0.030 m"], fc=C["green"], tfs=10.5, fs=8.6)
    note(ax, 9.3, 3.85, "따라가는 관절에는 액추에이터를 달지 않는다.", fs=9.2)
    note(ax, 0.3, 0.5, "숫자 = 손가락 관절 둘짜리 URDF 에 left 목표 0.03 m 를 주고 3 초 돌린 결과.  이 글의 2링크 팔에는 mimic 이 없다.", fs=9.5)
    save(fig, "lesson01c_mimic.png")


def convert_flow():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "urdf_to_mjcf.py 의 build(): 여섯 단계", bold=True, fs=12)
    flow_rows(ax, [("1  URDF 읽기", "MjSpec.from_file"), ("2  물리 · 충돌", "timestep · group · exclude"), ("3  세계", "빛 · 바닥 · 상자"),
                   ("4  카메라", "optical frame 에 add_camera"), ("5  액추에이터", "관절마다 position"), ("6  컴파일", "spec.compile() → MjModel")],
              per_row=3, y_top=3.9, h=1.3, gap=0.3, row_gap=0.55,
              colors=[C["blue"], C["yellow"], C["grey"], C["purple"], C["orange"], C["green"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.3, "MjSpec = 모델을 코드로 고치는 API.  XML 문자열을 직접 이어 붙이지 않는다.  to_xml() 로 MJCF 저장.", fs=9.5)
    save(fig, "lesson01c_convert.png")


def one_source():
    fig, ax = fig_ax(14, 4.3)
    note(ax, 0.3, 4.0, "원본은 URDF 하나: 이름이 같아서 양쪽이 맞물린다", bold=True, fs=12)
    rbox(ax, 0.3, 1.55, 2.9, 1.5, "two_link_arm.urdf", ["joint1 · joint2", "base_link … camera_optical_frame"], fc=C["blue"], tfs=10.5, fs=8.2)
    rbox(ax, 4.3, 2.55, 3.6, 1.1, "robot_state_publisher", ["URDF 그대로 읽음"], fc=C["green"], tfs=10.5, fs=8.8)
    rbox(ax, 4.3, 0.95, 3.6, 1.1, "urdf_to_mjcf.build()", ["MjModel 로 변환"], fc=C["yellow"], tfs=10.5, fs=8.8)
    rbox(ax, 9.0, 2.55, 4.7, 1.1, "/tf", ["frame 이름 = URDF link 이름"], fc=C["green"], tfs=10.5, fs=8.8)
    rbox(ax, 9.0, 0.95, 4.7, 1.1, "/joint_states", ["name = MJCF joint 이름 = URDF joint 이름"], fc=C["purple"], tfs=10.5, fs=8.6)
    ax.plot([3.2, 3.75], [2.3, 2.3], color=INK, lw=1.6); ax.plot([3.75, 3.75], [1.5, 3.1], color=INK, lw=1.6)
    arrow(ax, (3.75, 3.1), (4.3, 3.1)); arrow(ax, (3.75, 1.5), (4.3, 1.5))
    arrow(ax, (7.9, 3.1), (9.0, 3.1)); arrow(ax, (7.9, 1.5), (9.0, 1.5))
    arrow(ax, (11.35, 2.05), (11.35, 2.55), color=BROWN)
    label(ax, 12.45, 2.3, "이름으로 짝지음", color=BROWN, fs=9)
    note(ax, 0.3, 0.45, "관절 이름을 어느 한쪽에서만 바꾸면 robot_state_publisher 가 그 관절을 무시한다 → URDF 에서만 고친다.", fs=9.5)
    save(fig, "lesson01c_one_source.png")


# ------------------------------------------------------------------ 4. bridge
def exchange():
    fig, ax = fig_ax(14, 7.6)
    note(ax, 0.3, 7.3, "MuJoCo ↔ ROS 2: 무엇을, 어디서 읽어, 무엇으로 보내나", bold=True, fs=12)
    band(ax, 0.3, 0.9, 3.5, 6.1, "MuJoCo (MjData)", "#F1F8F1", "#7CB07C", GREEN)
    band(ax, 4.5, 0.9, 4.2, 6.1, "urdf_bridge.py", "#F5F1FB", "#9C8BC9", PURPLE)
    band(ax, 9.4, 0.9, 4.3, 6.1, "ROS 2 토픽", "#F3F7FF", "#8FAADC", BLUE)
    rows = [("data.time", "시뮬레이션 시각", "spin() 안에서", "매 스텝", "/clock", "rosgraph_msgs/Clock · 500 Hz"),
            ("qpos · qvel · qfrc_actuator", "관절 각 · 속도 · 토크", "publish_joints", "이름 → 배열 번호", "/joint_states", "sensor_msgs/JointState · 50 Hz"),
            ("xpos · xquat", "월드 기준 body 자세", "publish_tip_pose", "base_link 기준으로 변환", "/tip_pose", "geometry_msgs/PoseStamped · 50 Hz"),
            ("Renderer.render()", "카메라가 본 장면", "publish_camera", "numpy → bytes", "/tip_camera/image_raw", "sensor_msgs/Image rgb8 · 5 Hz")]
    y = 5.6
    for a, a2, b, b2, c, d in rows:
        rbox(ax, 0.5, y, 3.1, 0.95, a, [a2], fc=C["green"], tfs=9.4, fs=8.2)
        rbox(ax, 4.7, y, 3.8, 0.95, b, [b2], fc=C["purple"], tfs=9.8, fs=8.2)
        rbox(ax, 9.6, y, 3.9, 0.95, c, [d], fc=C["blue"], tfs=9.8, fs=8.0)
        arrow(ax, (3.6, y + 0.47), (4.7, y + 0.47), color=GREEN); arrow(ax, (8.5, y + 0.47), (9.6, y + 0.47), color=BLUE)
        y -= 1.1
    ax.plot([0.3, 13.7], [2.18, 2.18], color="#999999", lw=0.8, ls="--", zorder=2)
    rbox(ax, 0.5, 1.08, 3.1, 0.95, "data.ctrl", ["액추에이터 목표"], fc=C["orange"], tfs=9.8, fs=8.2)
    rbox(ax, 4.7, 1.08, 3.8, 0.95, "on_cmd", ["길이 · 유한값 검사 후 clip"], fc=C["purple"], tfs=9.8, fs=8.2)
    rbox(ax, 9.6, 1.08, 3.9, 0.95, "/cmd", ["std_msgs/Float64MultiArray [rad]"], fc=C["orange"], tfs=9.8, fs=8.0)
    arrow(ax, (4.7, 1.55), (3.6, 1.55), color=BROWN); arrow(ax, (9.6, 1.55), (8.5, 1.55), color=BROWN)
    note(ax, 0.3, 0.45, "위 넷 = MuJoCo → ROS 2 (읽어서 발행).  아래 하나 = ROS 2 → MuJoCo (구독해서 쓰기).  /tf 는 이 그림에 없다.", fs=9.5)
    save(fig, "lesson01c_exchange.png")


def tf_paths():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "자세를 ROS 2 로 보내는 두 길", bold=True, fs=12)
    note(ax, 0.3, 4.2, "관절 공간으로: URDF 가 있는 로봇 링크", bold=True, fs=10, color=GREEN)
    chain(ax, [("qpos", ["관절 각"]), ("/joint_states", ["브리지가 발행"]), ("robot_state_publisher", ["URDF 로 순기구학"]), ("/tf", ["모든 링크 프레임"])],
          y=2.85, h=1.05, colors=[C["green"], C["purple"], C["green"], C["blue"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 2.4, "직교 공간으로: URDF 만으로는 알 수 없는 것", bold=True, fs=10, color=BROWN)
    chain(ax, [("xpos · xquat", ["월드 기준 body 자세"]), ("기준 프레임으로 변환", ["conj(q_base) · q"]), ("브리지가 직접 발행", ["PoseStamped · Odometry · TF"]), ("/tip_pose · /odom …", ["떠다니는 base · 물체"])],
          y=1.05, h=1.05, colors=[C["green"], C["yellow"], C["purple"], C["blue"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.5, "이 글: 링크는 위 길.  아래 길은 /tip_pose 하나로 연습하고, 두 길의 결과가 같은지 비교한다.", fs=9.5)
    save(fig, "lesson01c_tf_paths.png")


def codemap():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "urdf_bridge.py 147 줄: 함수 일곱", bold=True, fs=12)
    tiles(ax, [("stamp()", ["36 – 38", "초 → Time"], C["teal"]),
               ("__init__", ["42 – 65", "모델 · 발행자 · 구독자"], C["blue"]),
               ("on_cmd()", ["68 – 74", "/cmd → data.ctrl"], C["orange"]),
               ("publish_joints()", ["77 – 84", "qpos → /joint_states"], C["green"]),
               ("publish_tip_pose()", ["86 – 98", "xpos → /tip_pose"], C["green"]),
               ("publish_camera()", ["100 – 107", "렌더 → 영상"], C["green"]),
               ("spin()", ["110 – 125", "스텝 루프"], C["yellow"])],
          cols=7, y_top=3.7, gap=0.15, h=1.45, tfs=9.2, fs=8.2)
    note(ax, 0.3, 1.75, "주황 = ROS 2 → MuJoCo  ·  초록 = MuJoCo → ROS 2  ·  노랑 = 이 모두를 순서대로 부르는 루프", fs=9.5)
    note(ax, 0.3, 1.3, "아래 절 순서: 준비 (__init__) → 시간 → 관절 상태 → 끝점 자세 → 영상 → 명령 → 루프", fs=9.5)
    note(ax, 0.3, 0.85, "TF 코드가 없다.  minimal_bridge.py 에서 가장 길던 부분을 robot_state_publisher 가 대신한다.", fs=9.5)
    save(fig, "lesson01c_codemap.png")


def loop():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "spin(): 한 바퀴 = 시뮬레이션 2 ms", bold=True, fs=12)
    spans = chain(ax, [("1  mj_step", ["물리 한 스텝"]), ("2  /clock", ["data.time 발행"]), ("3  상태", ["50 Hz 마다"]), ("4  영상", ["5 Hz 마다"]),
                       ("5  spin_once", ["/cmd 콜백"]), ("6  sleep", ["벽시계에 맞춤"])],
                  y=1.35, h=1.25, gap=0.3, colors=[C["green"], C["teal"], C["green"], C["green"], C["orange"], C["grey"]], tfs=10.5, fs=8.8)
    xl, xr = (spans[0][0] + spans[0][1]) / 2, (spans[-1][0] + spans[-1][1]) / 2
    ax.plot([xr, xr], [1.35, 0.9], color=BROWN, lw=1.3); ax.plot([xr, xl], [0.9, 0.9], color=BROWN, lw=1.3)
    arrow(ax, (xl, 0.9), (xl, 1.35), color=BROWN, lw=1.3)
    label(ax, 7.0, 0.9, "반복", color=BROWN, fs=9)
    note(ax, 0.3, 0.4, "콜백은 5 에서만 돈다 → mj_step 도중에 data.ctrl 이 바뀌지 않는다.  스레드 · 잠금이 필요 없다.", fs=9.5)
    save(fig, "lesson01c_loop.png")


# ------------------------------------------------------------------ 6. your own robot
def checklist():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "내 로봇 URDF 를 붙일 때의 순서", bold=True, fs=12)
    flow_rows(ax, [("1  URDF 확인", "check_urdf · RViz 로 보기"), ("2  <mujoco> 태그", "fusestatic · discardvisual · meshdir"), ("3  그대로 읽기", "--raw 처럼 body · joint 수 확인"),
                   ("4  빠진 것 추가", "바닥 · 액추에이터 · 센서 · exclude"), ("5  브리지", "토픽 이름 · 타입은 실물과 같게"), ("6  두 길 비교", "tf2_echo = 시뮬레이터 값")],
              per_row=3, y_top=3.9, h=1.3, gap=0.3, row_gap=0.55,
              colors=[C["blue"], C["blue"], C["yellow"], C["yellow"], C["purple"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.3, "토픽 이름 · 타입을 실제 로봇 드라이버와 맞추면 그 위의 노드 (MoveIt · Nav2 · 내 코드) 는 그대로 쓴다.", fs=9.5)
    save(fig, "lesson01c_checklist.png")


def pitfalls():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "URDF 를 MuJoCo 에 올릴 때 자주 막히는 곳", bold=True, fs=12)
    tiles(ax, [("고정 링크가 없어짐", ["fusestatic 기본값이 URDF 는 true", "센서 프레임 · base_link 를 못 찾음"], C["red"]),
               ("mesh 를 못 읽음", ["package:// 경로는 파일 이름만 남음", "meshdir 지정 · STL / OBJ 로 변환"], C["red"]),
               ("base 와 첫 링크 충돌", ["세계에 고정된 body 는", "부모-자식 충돌 제외가 안 됨"], C["orange"]),
               ("쿼터니언 순서", ["MuJoCo [w, x, y, z]", "ROS 메시지 x · y · z · w"], C["yellow"]),
               ("카메라가 엉뚱한 곳을 봄", ["MuJoCo 카메라는 -z 를 봄", "optical frame 에서 x 축 180°"], C["yellow"]),
               ("시간이 어긋남", ["다른 노드에 use_sim_time", "stamp 는 data.time 으로"], C["teal"])],
          cols=3, y_top=4.2, gap=0.3, h=1.45, tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.45, "빨강 = 모델이 안 읽히거나 이름이 사라짐.  주황 = 움직임이 이상함.  노랑 = 값은 나오는데 뜻이 다름.", fs=9.5)
    save(fig, "lesson01c_pitfalls.png")


def pitfalls_model():
    fig, ax = fig_ax(14, 3.4)
    note(ax, 0.3, 3.1, "URDF 를 MuJoCo 에 올릴 때 자주 막히는 곳", bold=True, fs=12)
    tiles(ax, [("고정 링크가 없어짐", ["fusestatic 기본값이 URDF 는 true", "센서 프레임 · base_link 를 못 찾음"], C["red"]),
               ("mesh 를 못 읽음", ["package:// 경로는 파일 이름만 남음", "meshdir 지정 · STL / OBJ 로 변환"], C["red"]),
               ("base 와 첫 링크 충돌", ["세계에 고정된 body 는", "부모-자식 충돌 제외가 안 됨"], C["orange"])],
          cols=3, y_top=2.7, gap=0.3, h=1.45, tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.5, "빨강 = 모델이 안 읽히거나 이름이 사라짐.  주황 = 읽히지만 움직임이 이상함.", fs=9.5)
    save(fig, "lesson01c_pitfalls_model.png")


def pitfalls_bridge():
    fig, ax = fig_ax(14, 3.4)
    note(ax, 0.3, 3.1, "브리지를 쓸 때 자주 틀리는 곳", bold=True, fs=12)
    tiles(ax, [("쿼터니언 순서", ["MuJoCo [w, x, y, z]", "ROS 메시지 x · y · z · w"], C["yellow"]),
               ("카메라가 엉뚱한 곳을 봄", ["MuJoCo 카메라는 -z 를 봄", "optical frame 에서 x 축 180°"], C["yellow"]),
               ("시간이 어긋남", ["다른 노드에 use_sim_time", "stamp 는 data.time 으로"], C["teal"])],
          cols=3, y_top=2.7, gap=0.3, h=1.45, tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.5, "셋 다 오류 없이 값은 나온다.  뜻이 달라서 RViz · TF 에서 어긋나 보인다.", fs=9.5)
    save(fig, "lesson01c_pitfalls_bridge.png")


# ------------------------------------------------------------------ captures and terminals
def model_data():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "MuJoCo Python 의 세 가지: model · data · mj_step", bold=True, fs=12)
    rbox(ax, 0.3, 1.0, 4.6, 3.8, "MjModel  (model)", ["설계도: 실행 중 변하지 않음", "", "njnt · nu     관절 · 액추에이터 수",
         "opt.timestep     한 스텝의 시간", "joint(i).name     이름", "actuator_ctrlrange     명령 범위"], fc=C["blue"], tfs=12, fs=9.4, align="left", dy=0.42)
    rbox(ax, 9.1, 1.0, 4.6, 3.8, "MjData  (data)", ["상태: 스텝마다 변함", "", "time     시뮬레이션 시각", "ctrl     액추에이터 명령  ← 쓰는 값",
         "qpos · qvel     관절 각 · 속도  → 읽는 값", "xpos · xquat     body 의 월드 자세  → 읽는 값"], fc=C["green"], tfs=12, fs=9.4, align="left", dy=0.42)
    rbox(ax, 5.6, 2.3, 2.8, 1.2, "mj_step(model, data)", ["시간을 timestep 만큼 진행"], fc=C["yellow"], tfs=10.5, fs=8.8)
    arrow(ax, (4.9, 2.9), (5.6, 2.9)); arrow(ax, (8.4, 3.15), (9.1, 3.15)); arrow(ax, (9.1, 2.65), (8.4, 2.65))
    label(ax, 5.25, 3.25, "읽기만"); label(ax, 8.75, 3.5, "갱신"); label(ax, 8.75, 2.3, "읽기")
    note(ax, 0.3, 0.5, "model 은 XML(URDF · MJCF)에서 한 번 만들고, data 는 model 에서 만든다.  mj_step 을 부를 때마다 data 만 바뀐다.", fs=9.5)
    save(fig, "lesson01e_model_data.png")


def basics_bridge():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "기초 루프에 ROS 2 를 끼우면 브리지", bold=True, fs=12)
    note(ax, 0.3, 4.55, "mujoco_basics.py: MuJoCo 만", bold=True, fs=10, color=GREEN)
    chain(ax, [("data.ctrl 에 쓰기", ["코드에 적은 값 [0.6, 1.5]"]), ("mj_step", ["시간 진행"]), ("data.qpos 읽기", ["print 로 출력"])],
          y=3.25, h=1.0, colors=[C["orange"], C["yellow"], C["green"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 2.7, "urdf_bridge.py: 같은 루프 + ROS 2", bold=True, fs=10, color=PURPLE)
    chain(ax, [("data.ctrl 에 쓰기", ["/cmd 구독으로 받은 값"]), ("mj_step", ["시간 진행 · /clock 발행"]), ("data.qpos 읽기", ["/joint_states 로 발행"])],
          y=1.4, h=1.0, colors=[C["orange"], C["yellow"], C["green"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.75, "바뀌는 것은 값이 오고 가는 곳뿐: 코드에 적은 값 → 토픽으로 받은 값,  print → 토픽 발행.", fs=9.5)
    note(ax, 0.3, 0.35, "xpos · xquat → /tip_pose,  Renderer → 카메라 영상도 같은 방식 (다음 절).", fs=9.5)
    save(fig, "lesson01e_basics_bridge.png")


def captures(cap):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", 30)

    def side(names, out, h=820, gap=14, labels=None, bg="white"):
        ims = [Image.open(cap / n).convert("RGB") for n in names]
        ims = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in ims]
        top = 54 if labels else 0
        canvas = Image.new("RGB", (sum(im.width for im in ims) + gap * (len(ims) - 1), h + top), bg)
        x, draw = 0, None
        for i, im in enumerate(ims):
            canvas.paste(im, (x, top))
            if labels:
                draw = draw or ImageDraw.Draw(canvas)
                draw.text((x + 8, 10), labels[i], fill="#2b2b2b", font=font)
            x += im.width + gap
        canvas.save(OUT / out); print("saved", out)

    # RViz preview: RViz window + the slider window pasted at the same scale on a white strip
    rviz, jsp = Image.open(cap / "rviz_preview.png").convert("RGB"), Image.open(cap / "jsp.png").convert("RGB")
    canvas = Image.new("RGB", (rviz.width + jsp.width + 40, rviz.height), "white")
    canvas.paste(rviz, (0, 0)); canvas.paste(jsp, (rviz.width + 20, 40))
    canvas.save(OUT / "lesson01c_rviz_preview.png"); print("saved lesson01c_rviz_preview.png")
    side(["plain_0.png", "plain_500.png"], "lesson01c_plain.png", h=480, labels=["t = 0 s   관절 [0.6, 1.5] 에서 시작", "t = 1 s   [0.01, 2.00] · 처지고 밀려남"])
    Image.open(cap / "viewer_mjcf.png").convert("RGB").save(OUT / "lesson01c_viewer.png"); print("saved lesson01c_viewer.png")
    side(["mj_before.png", "rviz_before.png"], "lesson01c_run_before.png", labels=["MuJoCo (물리)", "RViz (URDF + /joint_states → TF)"])
    side(["mj_after.png", "rviz_after.png"], "lesson01c_run_after.png", labels=["MuJoCo (물리)", "RViz (URDF + /joint_states → TF)"])


def terminals(cap):
    from render_terminal import render
    ros = "source scripts/env.sh"

    def log(name, drop=("LOCALHOST", "localhost_only"), keep=None):
        lines = [l.rstrip() for l in (cap / name).read_text().splitlines()]
        lines = [l for l in lines if not any(d in l for d in drop)]
        lines = [re.sub(r"\[(INFO|WARN)\] \[\d+\.\d+\]", r"[\1]", l) for l in lines]
        return [("out", l) for l in (lines[:keep] if keep else lines)]

    def out(name, cmds, body, highlight=()):
        render([("prompt", c) for c in cmds] + body, str(OUT / name), highlight=highlight); print("saved", name)

    out("lesson01c_t_check.png", ["check_urdf lessons/01_mujoco_ros2/two_link_arm.urdf"], log("check_urdf.log"), highlight=("Successfully",))
    out("lesson01c_t_view.png", ["ros2 launch lessons/01_mujoco_ros2/view_urdf.launch.py"],
        [l for l in log("view_launch.log") if "process started" in l[1] or "Robot initialized" in l[1] or "Got description" in l[1]], highlight=("Robot initialized",))
    out("lesson01c_t_raw.png", ["python lessons/01_mujoco_ros2/urdf_to_mjcf.py --raw"], log("raw.log"), highlight=("body", "actuator", "camera"))
    out("lesson01c_t_conv.png", ["python lessons/01_mujoco_ros2/urdf_to_mjcf.py"], log("conv.log"), highlight=("body", "actuator", "camera"))
    out("lesson01e_t_basics.png", ["python lessons/01_mujoco_ros2/mujoco_basics.py"], log("basics.log"), highlight=("qpos",))
    out("lesson01c_t_bridge.png", ["python lessons/01_mujoco_ros2/urdf_bridge.py --viewer"], log("bridge.log", keep=1), highlight=("bridge up",))
    out("lesson01c_t_sim.png", ["ros2 launch lessons/01_mujoco_ros2/view_urdf.launch.py sim:=true"],
        [l for l in log("sim_launch.log") if "process started" in l[1] or "Robot initialized" in l[1]], highlight=("Robot initialized",))
    out("lesson01c_t_topics.png", ["ros2 topic list"], log("topic_list.log") + [("prompt", "ros2 node list")] + log("node_list.log"),
        highlight=("/clock", "/cmd", "/joint_states", "/tip_", "/urdf_bridge"))
    out("lesson01c_t_info.png", ["ros2 topic info /joint_states -v | grep -E 'Node name|Endpoint type'"],
        [l for l in log("js_info.log") if "Node name" in l[1] or "Endpoint" in l[1]], highlight=("urdf_bridge", "robot_state_publisher"))
    out("lesson01c_t_hz.png", ["ros2 topic hz /joint_states"], log("hz_js.log")[-2:] + [("prompt", "ros2 topic hz /tip_camera/image_raw")] + log("hz_img.log")[-2:]
        + [("prompt", "ros2 topic echo --once /clock")] + log("clock.log"), highlight=("average rate",))
    out("lesson01c_t_cmd.png", ['ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"'],
        [("out", "publisher: beginning loop"), ("out", "publishing #1: std_msgs.msg.Float64MultiArray(layout=..., data=[0.6, 1.5])")])
    out("lesson01c_t_js.png", ["ros2 topic echo --once /joint_states"], log("js_after.log"), highlight=("- 0.64", "- 1.51", "- -1.2", "- -0.32"))
    tip = [l for l in log("tip_pose.log") if l[1].strip() not in ("---",)]
    out("lesson01c_t_tip.png", ["ros2 topic echo --once /tip_pose"], tip, highlight=("x: 0.40", "z: 0.15", "frame_id"))
    tf = log("tf_echo.log")
    start = next(i for i, l in enumerate(tf) if l[1].startswith("At time"))
    out("lesson01c_t_tf.png", ["ros2 run tf2_ros tf2_echo base_link camera_optical_frame"], tf[start:start + 9], highlight=("Translation", "Quaternion"))
    out("lesson01c_t_bad.png", ['ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5, 0.1]}"'],
        [("out", "publisher: beginning loop"), ("out", "publishing #1: std_msgs.msg.Float64MultiArray(layout=..., data=[0.6, 1.5, 0.1])"),
         ("out", ""), ("out", "# 터미널 1 (브리지) 에 찍힌 줄")] + [l for l in log("bridge.log") if "ignored" in l[1]], highlight=("ignored",))


if __name__ == "__main__":
    for f in (steps, files, swap, urdf_tree, link_parts, joint_parts, optical, missing, problems, mapping, convert_flow, one_source,
              exchange, tf_paths, codemap, loop, checklist, pitfalls, pitfalls_model, pitfalls_bridge, mimic, model_data, basics_bridge):
        f()
    if len(sys.argv) > 1:
        captures(Path(sys.argv[1])); terminals(Path(sys.argv[1]))
