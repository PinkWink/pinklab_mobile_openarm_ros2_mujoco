"""Figures for the lesson-01 page section "two_link_arm.xml" (URDF vs MJCF, then the file element by element).
Output: docs/camp/lesson01_xml_*.png. Helpers come from draw_intro_figures.py (orthogonal arrows only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, cross, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle, Circle  # noqa: E402
import numpy as np  # noqa: E402


def tiles_at(ax, items, cols, x0, x1, y_top, gap=0.25, h=1.6, tfs=10.5, fs=8.6):
    """Grid of cards inside [x0, x1] (the shared tiles() helper only takes a symmetric margin)."""
    w = (x1 - x0 - gap * (cols - 1)) / cols
    for i, (title, lines, fc) in enumerate(items):
        r, c = divmod(i, cols)
        rbox(ax, x0 + c * (w + gap), y_top - (r + 1) * h - r * gap, w, h, title, lines, fc=fc, tfs=tfs, fs=fs, align="left", dy=0.3)


# ---------------------------------------------------------------- A. URDF vs MJCF
def formats():
    fig, ax = fig_ax(14, 3.2)
    tiles(ax, [("URDF (Unified Robot Description Format)", ["ROS 의 로봇 기술 형식 · XML", "RViz · MoveIt · robot_state_publisher 가 읽는다", "링크 · 관절 · 형상 · 관성을 적는다", "물리 · 액추에이터 · 센서는 파일 밖에 있다"], C["blue"]),
               ("MJCF (MuJoCo XML)", ["MuJoCo 의 모델 형식 · XML", "mujoco 라이브러리가 직접 읽는다", "링크 · 관절 · 형상에 더해", "물리 옵션 · 액추에이터 · 카메라 · 조명까지 한 파일"], C["green"])],
          cols=2, y_top=3.0, h=2.5, gap=0.4, tfs=12, fs=9.4)
    note(ax, 0.3, 0.25, "창고 로봇: URDF(xacro) 로 적고 MJCF 로 바꿔 쓴다      이 예제: two_link_arm.xml (MJCF) 하나만 쓴다", fs=9.5)
    save(fig, "lesson01_xml_formats.png")


def tree():
    fig, ax = fig_ax(14, 5.2)
    # URDF: flat list + parent/child references
    ax.add_patch(Rectangle((0.3, 0.3), 6.4, 4.5, fc="#F4F8FF", ec="#8FA9D6", lw=1.2, zorder=1))
    note(ax, 0.5, 4.55, "URDF: <link> 와 <joint> 를 나란히 나열", bold=True, fs=12, color="#1f4e79")
    rbox(ax, 0.6, 3.35, 2.6, 0.75, "<link name=base_link>", fc=C["blue"], tfs=9.5)
    rbox(ax, 0.6, 2.35, 2.6, 0.75, "<link name=link1>", fc=C["blue"], tfs=9.5)
    rbox(ax, 0.6, 1.35, 2.6, 0.75, "<link name=link2>", fc=C["blue"], tfs=9.5)
    rbox(ax, 3.7, 2.85, 2.8, 1.0, "<joint name=joint1>", ["parent base_link · child link1"], fc=C["yellow"], tfs=9.5, fs=8.4)
    rbox(ax, 3.7, 1.35, 2.8, 1.0, "<joint name=joint2>", ["parent link1 · child link2"], fc=C["yellow"], tfs=9.5, fs=8.4)
    arrow(ax, (3.7, 3.55), (3.2, 3.55), color="#7a4b00", lw=1.2); arrow(ax, (3.7, 3.05), (3.2, 3.05), color="#7a4b00", lw=1.2)
    arrow(ax, (3.7, 2.05), (3.2, 2.05), color="#7a4b00", lw=1.2); arrow(ax, (3.7, 1.55), (3.2, 1.55), color="#7a4b00", lw=1.2)
    note(ax, 0.5, 0.6, "joint 의 parent · child 이름이 트리를 만든다", fs=9.5)
    # MJCF: nested bodies
    ax.add_patch(Rectangle((7.3, 0.3), 6.4, 4.5, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 7.5, 4.55, "MJCF: <body> 안에 <body> 를 넣어 중첩", bold=True, fs=12, color="#2e7d32")
    for k, (name, extra) in enumerate((("<body name=base_link>", ""), ("<body name=link1 pos=…>", "<joint name=joint1/>"),
                                       ("<body name=link2 pos=…>", "<joint name=joint2/>"), ("<body name=camera_link pos=…>", "<camera name=tip_camera/>"))):
        x0, y0 = 7.6 + 0.45 * k, 0.6 + 0.2 * k
        w, h = 5.8 - 0.9 * k, 3.7 - 0.85 * k
        ax.add_patch(Rectangle((x0, y0), w, h, fc=[C["green"], C["teal"], C["yellow"], C["orange"]][k], ec=INK, lw=1.0, zorder=2 + k, alpha=0.95))
        ax.text(x0 + 0.12, y0 + h - 0.12, name, ha="left", va="top", fontsize=9.2, fontweight="bold", color=INK, zorder=10)
        if extra:
            ax.text(x0 + 0.12, y0 + h - 0.42, extra, ha="left", va="top", fontsize=8.4, color="#444444", zorder=10)
    note(ax, 7.5, 0.42, "안쪽 body 의 pos 는 바깥 body 기준 · 관절은 자식 body 안에", fs=9.0)
    save(fig, "lesson01_xml_tree.png")


def contents():
    fig, ax = fig_ax(14, 4.8)
    ax.add_patch(Rectangle((0.3, 0.3), 6.4, 4.2, fc="#F4F8FF", ec="#8FA9D6", lw=1.2, zorder=1))
    note(ax, 0.5, 4.25, "URDF: 파일 안 · 파일 밖", bold=True, fs=12, color="#1f4e79")
    rbox(ax, 0.6, 2.3, 2.7, 1.7, "URDF 파일 안", ["링크 형상 · 관성", "관절 종류 · 한계", "collision 형상"], fc=C["blue"], tfs=10.5, fs=8.8, align="left")
    rbox(ax, 3.6, 2.3, 2.9, 1.7, "파일 밖 (별도 파일)", ["ros2_control 컨트롤러 YAML", "Gazebo 센서 플러그인 태그", "물리 옵션은 시뮬레이터 설정"], fc=C["grey"], tfs=10.5, fs=8.4, align="left")
    note(ax, 0.5, 1.6, "URDF 만으로는 시뮬레이션이 돌지 않는다", fs=9.5)
    note(ax, 0.5, 1.15, "→ 시뮬레이터 · 컨트롤러 설정을 따로 붙인다", fs=9.5)
    ax.add_patch(Rectangle((7.3, 0.3), 6.4, 4.2, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 7.5, 4.25, "MJCF: 전부 파일 안", bold=True, fs=12, color="#2e7d32")
    tiles_at(ax, [("<worldbody>", ["body · joint · geom", "camera · light"], C["green"]), ("<actuator>", ["position · motor …", "kp · ctrlrange"], C["yellow"]),
               ("<option>", ["timestep · gravity", "적분기 · 접촉 옵션"], C["teal"]), ("<asset> <default>", ["텍스처 · 재질", "공통 속성"], C["orange"])],
          cols=2, x0=7.6, x1=13.4, y_top=4.0, gap=0.25, h=1.25, tfs=10, fs=8.4)
    note(ax, 7.5, 1.05, "MJCF 파일 하나로 시뮬레이션이 바로 돈다", fs=9.5)
    note(ax, 7.5, 0.6, "→ python -m mujoco.viewer --mjcf=two_link_arm.xml", fs=9.5)
    save(fig, "lesson01_xml_contents.png")


def units():
    fig, ax = fig_ax(14, 3.3)
    tiles(ax, [("각도 단위", ["URDF: 항상 rad", "MJCF: 기본이 도(degree)", "→ compiler angle=\"radian\" 으로 맞춘다"], C["yellow"]),
               ("관성", ["URDF: <inertial> 을 직접 적는다", "MJCF: geom 크기 · 밀도로 자동 계산", "→ 링크마다 질량을 안 적어도 된다"], C["green"]),
               ("시각 · 충돌 형상", ["URDF: <visual> 과 <collision> 이 따로", "MJCF: geom 하나가 둘을 겸한다", "→ 충돌만 끄려면 contype=0"], C["blue"])],
          cols=3, y_top=3.0, h=2.3, gap=0.3, tfs=11.5, fs=9.0)
    note(ax, 0.3, 0.3, "세 가지가 URDF 에 익숙한 사람이 MJCF 에서 가장 자주 틀리는 곳이다", fs=9.5)
    save(fig, "lesson01_xml_units.png")


# ---------------------------------------------------------------- B. the file element by element
def structure():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "two_link_arm.xml: 최상위 요소 7개 (46줄)", bold=True, fs=12)
    tiles(ax, [("<compiler>", ["각도 단위 rad"], C["grey"]), ("<option>", ["timestep 2 ms · 중력"], C["grey"]),
               ("<visual>", ["오프스크린 렌더 크기"], C["grey"]), ("<asset>", ["바닥 텍스처 · 재질"], C["grey"]),
               ("<default>", ["팔 링크 공통 속성 (class=arm)"], C["grey"]), ("<worldbody>", ["빛 · 바닥 · 상자", "body 트리 · joint · geom · camera"], C["green"]),
               ("<actuator>", ["관절 2개의 위치 액추에이터"], C["yellow"]), ("브리지가 찾는 이름", ["joint1 joint2 · body 4개", "tip_camera · 액추에이터 수"], C["blue"])],
          cols=4, y_top=4.2, gap=0.3, h=1.7, tfs=11, fs=8.8)
    note(ax, 0.3, 0.3, "앞의 다섯은 설정이다.  <worldbody> 가 로봇과 세계, <actuator> 가 관절을 움직이는 힘이다.", fs=9.5)
    save(fig, "lesson01_xml_structure.png")


def compiler_option():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "<compiler> · <option>: 단위와 물리 스텝", bold=True, fs=12)
    chain(ax, [("<compiler angle=\"radian\"/>", ["각도를 rad 로 읽는다"]), ("joint range · ctrlrange", ["-1.57 ~ 1.57 rad"]), ("/cmd [q1, q2]", ["rad 그대로 넣는다"])],
          y=2.2, h=1.35, colors=[C["grey"], C["yellow"], C["orange"]], tfs=10.5, fs=8.8)
    chain(ax, [("<option timestep=\"0.002\"/>", ["gravity 0 0 -9.81"]), ("mj_step 한 번", ["시뮬레이션 2 ms 진행"]), ("브리지 루프 한 바퀴", ["data.time += 0.002"])],
          y=0.45, h=1.35, colors=[C["grey"], C["green"], C["purple"]], tfs=10.5, fs=8.8)
    save(fig, "lesson01_xml_compiler.png")


def visual_asset():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "<visual> · <asset>: 렌더 크기와 바닥 무늬", bold=True, fs=12)
    chain(ax, [("<texture builtin=\"checker\">", ["회색 두 톤 바둑판", "256 × 256"]), ("<material name=\"floor\">", ["texture 를 입힌다", "texrepeat 6 × 6"]),
               ("<geom material=\"floor\">", ["바닥 평면 2 × 2 m", "name=\"floor\""]), ("카메라 영상", ["무늬가 있어 움직임이 보인다"])],
          y=1.3, h=1.8, colors=[C["grey"], C["grey"], C["green"], C["blue"]], tfs=10, fs=8.6)
    rbox(ax, 0.3, 0.2, 13.4, 0.75, "<visual><global offwidth=\"640\" offheight=\"480\"/></visual>   오프스크린 렌더의 최대 크기 · 브리지의 320 × 240 이 이 안에 들어간다", fc=C["yellow"], tfs=9.5)
    save(fig, "lesson01_xml_asset.png")


def default_class():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "<default class=\"arm\">: 팔 링크끼리는 충돌하지 않는다", bold=True, fs=12)
    for k, (x0, title, sub, col, bad) in enumerate(((0.3, "충돌 켬 (기본)", "관절에서 겹친 캡슐이 서로 밀어낸다 → 팔이 튄다", "#FFF5F5", True),
                                                   (7.3, "class=\"arm\"  contype=0 conaffinity=0", "겹쳐도 무시한다 → 팔이 조용히 선다", "#F3FAF3", False))):
        ax.add_patch(Rectangle((x0, 0.3), 6.4, 3.3, fc=col, ec="#B0B7C3", lw=1.0, zorder=1))
        note(ax, x0 + 0.2, 3.35, title, bold=True, fs=11)
        cx, cy = x0 + 2.4, 1.7
        ax.plot([cx - 1.4, cx], [cy, cy], color="#3380E6", lw=16, solid_capstyle="round", zorder=3)
        ax.plot([cx, cx + 1.3 * np.cos(0.9), ], [cy, cy + 1.3 * np.sin(0.9)], color="#E69A33", lw=14, solid_capstyle="round", zorder=4, alpha=0.9)
        ax.add_patch(Circle((cx, cy), 0.12, fc="white", ec=INK, lw=1.3, zorder=6))
        if bad:
            cross(ax, cx, cy + 0.35, s=0.2)
            label(ax, cx + 2.2, cy + 0.9, "겹침 = 접촉력 발생", color="#C62828", fs=9.5)
        else:
            label(ax, cx + 2.2, cy + 0.9, "겹침 무시", color="#2e7d32", fs=9.5)
        note(ax, x0 + 0.2, 0.55, sub, fs=9.2)
    save(fig, "lesson01_xml_default.png")


def world():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "<worldbody> 의 고정물: 빛 · 바닥 · 상자 (위에서 본 배치, 단위 m)", bold=True, fs=12)
    # top view: x to the right, y up. scale 8 units per metre, origin at (2.2, 2.2)
    S, ox, oy = 8.0, 1.8, 2.15
    ax.add_patch(Rectangle((ox - 0.25 * S, oy - 0.2 * S), 1.1 * S, 0.4 * S, fc="#EDEDED", ec="#999999", lw=1.0, zorder=1))
    ax.plot([ox - 0.25 * S, ox + 0.85 * S], [oy, oy], color="#BBBBBB", lw=0.8, ls="--", zorder=2)
    ax.add_patch(Circle((ox, oy), 0.05 * S, fc="#555555", ec=INK, zorder=4)); label(ax, ox, oy - 0.65, "base_link (0, 0)", fs=9)
    ax.add_patch(Rectangle((ox + 0.55 * S - 0.04 * S, oy + 0.08 * S - 0.04 * S), 0.08 * S, 0.08 * S, fc="#E53935", ec=INK, zorder=4))
    label(ax, ox + 0.55 * S, oy + 0.08 * S + 0.6, "red_box (0.55, 0.08) · 한 변 8 cm", fs=9)
    ax.add_patch(Rectangle((ox + 0.62 * S - 0.03 * S, oy - 0.10 * S - 0.03 * S), 0.06 * S, 0.06 * S, fc="#3949AB", ec=INK, zorder=4))
    label(ax, ox + 0.62 * S, oy - 0.10 * S - 0.55, "blue_box (0.62, -0.10) · 한 변 6 cm", fs=9)
    ax.text(ox + 0.85 * S - 0.1, oy + 0.08, "x →", fontsize=9, color="#555555", ha="right")
    ax.text(ox + 0.1, oy + 0.2 * S - 0.35, "y ↑", fontsize=9, color="#555555")
    rbox(ax, 10.2, 0.4, 3.5, 3.4, "worldbody 에 바로 둔 geom", ["<light>: 위에서 비추는 조명", "  없으면 카메라 영상이 어둡다", "<geom type=plane>: 바닥 2 × 2 m", "<geom type=box> × 2: 상자", "  body 가 없으니 고정물이다", "  팔을 [0.6, 1.5] 로 굽히면", "  카메라가 이 자리를 본다"], fc=C["yellow"], tfs=10.5, fs=8.6, align="left", dy=0.33)
    save(fig, "lesson01_xml_world.png")


def bodies():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "<body> 트리: 중첩 순서가 곧 TF 트리", bold=True, fs=12)
    items = (("<body name=\"base_link\" pos=\"0 0 0\">", ""), ("<body name=\"link1\" pos=\"0 0 0.06\">", "base 위 6 cm"),
             ("<body name=\"link2\" pos=\"0 0 0.30\">", "link1 끝 30 cm"), ("<body name=\"camera_link\" pos=\"0 0 0.26\">", "link2 끝 26 cm"))
    for k, (name, sub) in enumerate(items):
        x0, y0 = 0.3 + 0.4 * k, 0.4 + 0.2 * k
        w, h = 7.6 - 0.8 * k, 3.8 - 0.85 * k
        ax.add_patch(Rectangle((x0, y0), w, h, fc=[C["green"], C["teal"], C["yellow"], C["orange"]][k], ec=INK, lw=1.0, zorder=2 + k))
        ax.text(x0 + 0.12, y0 + h - 0.12, name, ha="left", va="top", fontsize=9.4, fontweight="bold", color=INK, zorder=10)
        if sub:
            ax.text(x0 + w - 0.12, y0 + h - 0.12, sub, ha="right", va="top", fontsize=8.6, color="#444444", zorder=10)
    ys = [3.8, 2.75, 1.7, 0.65]
    for k, name in enumerate(("base_link", "link1", "link2", "camera_link")):
        rbox(ax, 9.3, ys[k] - 0.3, 2.6, 0.6, name, fc=C["blue"], tfs=10)
        if k < 3:
            arrow(ax, (10.6, ys[k] - 0.3), (10.6, ys[k + 1] + 0.3))
    note(ax, 12.1, 3.8, "TF 부모 → 자식", fs=9.5, bold=True); note(ax, 12.1, 3.4, "= 브리지의 bodies 목록", fs=9)
    note(ax, 12.1, 2.2, "pos 는 부모 기준", fs=9.5, bold=True); note(ax, 12.1, 1.8, "= URDF joint origin", fs=9)
    save(fig, "lesson01_xml_bodies.png")


def joint():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "<joint>: hinge 관절 두 개", bold=True, fs=12)
    chain(ax, [("자식 body 안에 적는다", ["그 body 와 부모 사이의", "자유도가 된다"]), ("type=\"hinge\"", ["회전 관절", "URDF 의 revolute"]),
               ("axis=\"0 1 0\"", ["y축 회전", "팔이 x-z 평면에서 굽는다"]), ("range", ["관절 한계 (rad)", "joint1 ±1.57 · joint2 ±2.0"]), ("damping=\"0.5\"", ["속도에 비례한 저항", "없으면 오래 흔들린다"])],
          y=1.35, h=2.1, gap=0.25, colors=[C["grey"], C["yellow"], C["yellow"], C["orange"], C["orange"]], tfs=10.5, fs=8.6)
    # tiny side-view: hinge axis into the page
    ax.plot([0.8, 3.0], [0.7, 0.7], color="#3380E6", lw=8, solid_capstyle="round"); ax.add_patch(Circle((3.0, 0.7), 0.13, fc="white", ec=INK, lw=1.3, zorder=6))
    ax.plot([3.0, 4.6], [0.7, 0.7 + 1.6 * np.tan(0.0) + 0.0], color="#E69A33", lw=7, solid_capstyle="round", alpha=0.0)
    ax.plot([3.0, 4.4], [0.7, 1.1], color="#E69A33", lw=7, solid_capstyle="round", zorder=5)
    label(ax, 6.2, 0.7, "y축(지면 안쪽)을 축으로 회전 → 옆에서 보면 x-z 평면에서 굽는다", fs=9)
    save(fig, "lesson01_xml_joint.png")


def geom():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "<geom>: capsule 로 그린 링크", bold=True, fs=12)
    # capsule drawing
    ax.plot([0.9, 4.9], [3.0, 3.0], color="#3380E6", lw=26, solid_capstyle="round", zorder=3)
    for x, t in ((0.9, "fromto 시작 (0 0 0)"), (4.9, "fromto 끝 (0 0 0.30)")):
        ax.add_patch(Circle((x, 3.0), 0.08, fc="white", ec=INK, zorder=6)); label(ax, x, 2.35, t, fs=8.8)
    ax.plot([2.9, 2.9], [3.0, 3.36], color=INK, lw=1.2, zorder=6); label(ax, 2.9, 3.62, "size = 반지름 0.02", fs=8.8)
    note(ax, 0.5, 1.5, "관성은 여기서 자동 계산된다 (부피 × 기본 밀도)", fs=9.5)
    note(ax, 0.5, 1.05, "rgba 로 색을 준다: link1 파랑 · link2 주황", fs=9.5)
    note(ax, 0.5, 0.6, "class=\"arm\" 이라 서로 충돌하지 않는다", fs=9.5)
    tiles_at(ax, [("base (cylinder)", ["반지름 5 cm · 높이 6 cm", "base_link 에 붙은 받침"], C["grey"]), ("link1_geom (capsule)", ["fromto 0 → 0.30 m", "반지름 2 cm · 파랑"], C["blue"]),
               ("link2_geom (capsule)", ["fromto 0 → 0.25 m", "반지름 1.8 cm · 주황"], C["orange"]), ("camera_body (box)", ["3 × 4 × 2 cm 검정", "카메라 자리 표시"], C["yellow"])],
          cols=2, x0=7.0, x1=13.7, y_top=4.0, gap=0.25, h=1.6, tfs=10.5, fs=8.6)
    save(fig, "lesson01_xml_geom.png")


def camera():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "<camera name=\"tip_camera\">: 팔 끝 카메라가 링크 방향을 보게 하기", bold=True, fs=12)
    # link2 drawn vertical (body +z up), camera box at top, view direction up
    ax.plot([2.5, 2.5], [0.6, 2.6], color="#E69A33", lw=12, solid_capstyle="round", zorder=3)
    ax.add_patch(Rectangle((2.25, 2.7), 0.5, 0.3, fc="#222222", ec=INK, zorder=5))
    arrow(ax, (2.5, 3.05), (2.5, 3.95), color="#8a6d00", lw=2); label(ax, 3.6, 3.7, "본다 = body +z (링크 방향)", color="#8a6d00", fs=9)
    arrow(ax, (2.9, 1.2), (4.0, 1.2), color="#555555", lw=1.4); label(ax, 4.6, 1.2, "body x", fs=8.8)
    arrow(ax, (2.9, 1.2), (2.9, 2.2), color="#555555", lw=1.4); label(ax, 3.45, 2.05, "body z", fs=8.8)
    tiles_at(ax, [("MuJoCo 카메라 규칙", ["카메라는 자기 -z 축을 본다", "xyaxes = (영상 오른쪽, 영상 위)", "두 벡터로 자세를 정한다"], C["grey"]),
               ("xyaxes=\"0 -1 0  -1 0 0\"", ["오른쪽 = body -y", "위 = body -x", "→ 보는 방향 = body +z"], C["yellow"]),
               ("fovy=\"60\"", ["세로 화각 60°", "가로는 영상 비율에서 나온다", "크기 320 × 240 은 브리지 Renderer"], C["green"]),
               ("브리지에서", ["update_scene(camera=\"tip_camera\")", "이름으로 찾는다", "frame_id 는 camera_link"], C["blue"])],
          cols=2, x0=6.2, x1=13.7, y_top=4.0, gap=0.25, h=1.7, tfs=10.5, fs=8.5)
    note(ax, 0.5, 0.25, "xyaxes 를 빼면 카메라가 링크 뒤쪽(-z)을 본다", fs=9.5)
    save(fig, "lesson01_xml_camera.png")


def actuator():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "<actuator>: 관절을 목표 각도로 잡는 위치 액추에이터", bold=True, fs=12)
    chain(ax, [("/cmd [q1, q2]", ["브리지 on_cmd", "→ data.ctrl[0:2]"]), ("ctrlrange", ["명령 범위", "밖이면 브리지가 자른다"]),
               ("<position kp=…>", ["토크 = kp · (ctrl - q)", "joint1 kp 30 · joint2 kp 20"]), ("joint=\"joint1\" · joint2", ["관절이 목표로 간다", "damping 이 진동을 죽인다"])],
          y=1.1, h=2.0, colors=[C["orange"], C["grey"], C["yellow"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.45, "액추에이터를 적은 순서가 data.ctrl 의 순서다.  Gazebo 라면 ros2_control 컨트롤러 YAML 이 하던 일이다.", fs=9.5)
    save(fig, "lesson01_xml_actuator.png")


def names():
    fig, ax = fig_ax(14, 4.7)
    note(ax, 0.3, 4.4, "브리지가 이 파일에서 이름으로 찾는 것", bold=True, fs=12)
    rows = (("joint1 · joint2", "model.joint(j).qposadr · dofadr → /joint_states"),
            ("base_link · link1 · link2 · camera_link", "model.body(name) → xpos · xquat → /tf"),
            ("tip_camera", "renderer.update_scene(camera=\"tip_camera\") → /tip_camera/image_raw"),
            ("액추에이터 2개 (model.nu)", "len(/cmd.data) == nu 확인 → data.ctrl"))
    for k, (a, b) in enumerate(rows):
        y = 3.6 - k * 0.85
        rbox(ax, 0.3, y - 0.3, 4.6, 0.65, a, fc=C["green"], tfs=10)
        arrow(ax, (4.9, y + 0.025), (5.6, y + 0.025))
        rbox(ax, 5.6, y - 0.3, 8.1, 0.65, b, fc=C["blue"], tfs=9.6)
    note(ax, 0.3, 0.3, "XML 의 이름을 바꾸면 브리지의 joints · bodies 목록도 같이 바꾼다", fs=9.5)
    save(fig, "lesson01_xml_names.png")


# ---------------------------------------------------------------- C. summary: everything exchanged between MuJoCo and ROS 2
def exchange():
    fig, ax = fig_ax(14, 7.0)
    note(ax, 0.3, 6.7, "MuJoCo <-> ROS 2: 브리지가 주고받는 것 (lessons/01_mujoco_ros2)", bold=True, fs=12.5)
    ys, h, yc = (4.95, 3.9, 2.85, 1.8), 0.9, 0.55           # four outgoing rows, box height, the /cmd row
    cols = ((0.3, 3.4, "#F3FAF3", "#7CB07C", "MuJoCo", "#2e7d32"), (5.0, 4.0, "#F6F2FB", "#9C8AC6", "minimal_bridge.py", "#5E4B8B"),
            (10.3, 3.4, "#F4F8FF", "#8FA9D6", "ROS 2", "#1f4e79"))
    for x0, w, fc, ec, name, tc in cols:
        ax.add_patch(Rectangle((x0, 0.35), w, 6.0, fc=fc, ec=ec, lw=1.4, zorder=1))
        note(ax, x0 + 0.2, 6.1, name, bold=True, fs=12, color=tc)
    mj = (("data.time", ""), ("data.qpos · data.qvel", ""), ("data.xpos · data.xquat", ""), ("renderer.render()", ""))
    br = (("stamp(t) → /clock", "매 스텝 (2 ms)"), ("publish_joints (앞)", "50 Hz"), ("publish_joints (뒤)", "50 Hz · 부모 → 자식 변환"), ("publish_camera", "5 Hz · rgb8"))
    ros = (("/clock", "rosgraph_msgs/Clock"), ("/joint_states", "sensor_msgs/JointState"), ("/tf", "base_link → link1 → link2 → camera_link"), ("/tip_camera/image_raw", "sensor_msgs/Image 320 × 240"))
    for y, a, b, c in zip(ys, mj, br, ros):
        rbox(ax, 0.5, y, 3.0, h, a[0], fc=C["green"], tfs=10)
        rbox(ax, 5.2, y, 3.6, h, b[0], [b[1]], fc=C["purple"], tfs=9.8, fs=8.2)
        rbox(ax, 10.5, y, 3.0, h, c[0], [c[1]], fc=C["blue"], tfs=10, fs=7.6 if c[0] == "/tf" else 8.2)
        arrow(ax, (3.5, y + h / 2), (5.2, y + h / 2), color="#2e7d32", lw=1.8)
        arrow(ax, (8.8, y + h / 2), (10.5, y + h / 2), color="#1f4e79", lw=1.8)
    rbox(ax, 0.5, yc, 3.0, h, "data.ctrl[0:2]", fc=C["orange"], tfs=10)
    rbox(ax, 5.2, yc, 3.6, h, "on_cmd", ["길이 확인 · ctrlrange clip"], fc=C["purple"], tfs=9.8, fs=8.2)
    rbox(ax, 10.5, yc, 3.0, h, "/cmd", ["std_msgs/Float64MultiArray [q1, q2]"], fc=C["orange"], tfs=10, fs=7.8)
    arrow(ax, (10.5, yc + h / 2), (8.8, yc + h / 2), color="#7a4b00", lw=1.8)
    arrow(ax, (5.2, yc + h / 2), (3.5, yc + h / 2), color="#7a4b00", lw=1.8)
    label(ax, 4.35, 5.75, "읽는다", color="#2e7d32", fs=9); label(ax, 9.65, 5.75, "발행한다", color="#1f4e79", fs=9)
    label(ax, 9.65, 1.35, "구독한다", color="#7a4b00", fs=9); label(ax, 4.35, 1.35, "쓴다", color="#7a4b00", fs=9)
    ax.plot([0.3, 13.7], [1.62, 1.62], color="#999999", lw=0.8, ls="--", zorder=1)
    note(ax, 0.3, 0.1, "위 네 줄: MuJoCo → ROS 2 (시각 · 관절 · TF · 영상)      아래 한 줄: ROS 2 → MuJoCo (관절 목표)", fs=9.5)
    save(fig, "lesson01_exchange.png")

if __name__ == "__main__":
    for f in (formats, tree, contents, units, structure, compiler_option, visual_asset, default_class, world, bodies, joint, geom, camera, actuator, names, exchange):
        f()
