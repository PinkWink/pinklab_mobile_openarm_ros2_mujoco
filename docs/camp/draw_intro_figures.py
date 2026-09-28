"""Figures for the intro & curriculum Confluence page: one representative picture per h3 section.

All arrows are vertical or horizontal; Korean text uses NanumGothic. Output: docs/camp/intro_*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

for name in ("NanumGothic", "Noto Sans CJK KR", "Noto Sans CJK JP", "NanumBarunGothic"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        print("font:", name)
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path("docs/camp")
INK = "#2b2b2b"
C = {"blue": "#E3EEFF", "yellow": "#FFF3D6", "green": "#E6F7E6", "red": "#FFE0E0", "purple": "#EDE7F6",
     "grey": "#F1F2F4", "orange": "#FFE9B8", "teal": "#DDF3F0"}


def fig_ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def rbox(ax, x0, y0, w, h, title, lines=(), fc="#EEF3FA", ec=INK, tfs=11.5, fs=9.2, lw=1.2, align="center", dy=0.3):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=lw, zorder=2))
    if lines:
        ax.text(x0 + w / 2, y0 + h - 0.22, title, ha="center", va="top", fontsize=tfs, fontweight="bold", color=INK, zorder=3)
        for i, t in enumerate(lines):
            if align == "left":
                ax.text(x0 + 0.18, y0 + h - 0.22 - 0.42 - dy * i, t, ha="left", va="top", fontsize=fs, color="#333333", zorder=3)
            else:
                ax.text(x0 + w / 2, y0 + h - 0.22 - 0.42 - dy * i, t, ha="center", va="top", fontsize=fs, color="#333333", zorder=3)
    else:
        ax.text(x0 + w / 2, y0 + h / 2, title, ha="center", va="center", fontsize=tfs, fontweight="bold", color=INK, zorder=3)


def arrow(ax, p, q, color=INK, lw=1.6, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=15, lw=lw, color=color, zorder=4, shrinkA=0, shrinkB=0))


def label(ax, x, y, text, color="#444444", fs=8.8, ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color, zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))


def note(ax, x, y, text, color="#555555", fs=9.5, ha="left", bold=False):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs, color=color, fontweight="bold" if bold else "normal")


def cross(ax, x, y, s=0.16, color="#C62828", lw=2.2):
    ax.plot([x - s, x + s], [y - s, y + s], color=color, lw=lw, zorder=6)
    ax.plot([x - s, x + s], [y + s, y - s], color=color, lw=lw, zorder=6)


def chain(ax, items, y, h, x0=0.3, x1=None, gap=0.35, tfs=11, fs=9, colors=None, arrows=True):
    """Horizontal flow of boxes. items: (title, [lines]) tuples. Returns list of (x0, x1) per box."""
    x1 = x1 if x1 is not None else ax.get_xlim()[1] - 0.3
    n = len(items)
    w = (x1 - x0 - gap * (n - 1)) / n
    spans, x = [], x0
    for i, it in enumerate(items):
        title, lines = (it[0], it[1]) if isinstance(it, tuple) else (it, ())
        fc = (colors[i % len(colors)] if colors else C["blue"])
        rbox(ax, x, y, w, h, title, lines, fc=fc, tfs=tfs, fs=fs)
        spans.append((x, x + w))
        if arrows and i < n - 1:
            arrow(ax, (x + w, y + h / 2), (x + w + gap, y + h / 2))
        x += w + gap
    return spans


def flow_rows(ax, items, per_row, y_top=None, h=1.35, gap=0.3, row_gap=0.75, colors=None, tfs=10.5, fs=8.8, x0=0.3):
    """Left-to-right flow split into rows; an orthogonal return path links the end of one row to the start of the next."""
    W = ax.get_xlim()[1]
    y_top = y_top or ax.get_ylim()[1] - 0.3
    w = (W - 2 * x0 - gap * (per_row - 1)) / per_row
    rows = [items[i:i + per_row] for i in range(0, len(items), per_row)]
    for r, row in enumerate(rows):
        y = y_top - (r + 1) * h - r * row_gap
        for c, (title, sub) in enumerate(row):
            i = r * per_row + c
            x = x0 + c * (w + gap)
            fc = colors[i % len(colors)] if colors else C["blue"]
            rbox(ax, x, y, w, h, title, [sub] if sub else (), fc=fc, tfs=tfs, fs=fs)
            if c < len(row) - 1:
                arrow(ax, (x + w, y + h / 2), (x + w + gap, y + h / 2))
        if r < len(rows) - 1:
            xr = x0 + (len(row) - 1) * (w + gap) + w / 2
            xl = x0 + w / 2
            ym = y - row_gap / 2
            ax.plot([xr, xr], [y, ym], color="#7a4b00", lw=1.3, zorder=4)
            ax.plot([xr, xl], [ym, ym], color="#7a4b00", lw=1.3, zorder=4)
            arrow(ax, (xl, ym), (xl, y - row_gap), color="#7a4b00", lw=1.3)


def tiles(ax, items, cols, x0=0.3, y_top=None, gap=0.3, h=1.9, tfs=11.5, fs=9):
    """Grid of cards. items: (title, [lines], color)."""
    W = ax.get_xlim()[1]
    y_top = y_top or ax.get_ylim()[1] - 0.3
    w = (W - 2 * x0 - gap * (cols - 1)) / cols
    for i, (title, lines, fc) in enumerate(items):
        r, c = divmod(i, cols)
        x = x0 + c * (w + gap)
        y = y_top - (r + 1) * h - r * gap
        rbox(ax, x, y, w, h, title, lines, fc=fc, tfs=tfs, fs=fs, align="left", dy=0.3)


def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", name)


# ================================================================ 1. package overview
def overview():
    fig, ax = fig_ax(14, 4.6)
    # robot stack (left)
    ax.add_patch(Rectangle((0.3, 0.4), 4.3, 3.9, fc="#FAFAFA", ec="#B0B7C3", lw=1.0, zorder=1))
    note(ax, 0.5, 4.05, "주행형 양팔 로봇", bold=True, fs=12)
    rbox(ax, 0.6, 2.95, 3.7, 0.8, "센서: 라이다 1 · 카메라 4", fc=C["yellow"], tfs=10.5)
    rbox(ax, 0.6, 1.85, 3.7, 0.95, "OpenARM 양팔", ["7관절 + 그리퍼 × 2"], fc=C["green"], tfs=10.5, fs=9)
    rbox(ax, 0.6, 0.65, 3.7, 1.05, "Vic Pinky 모바일 베이스", ["바퀴 오도메트리 · /cmd_vel"], fc=C["blue"], tfs=10.5, fs=9)
    # warehouse (right)
    ax.add_patch(Rectangle((5.6, 0.4), 8.1, 3.9, fc="#F3F7F3", ec="#7CB07C", lw=1.4, zorder=1))
    note(ax, 5.8, 4.05, "창고 15 × 11 m  (MuJoCo 한 모델)", bold=True, fs=12)
    rbox(ax, 5.9, 2.5, 2.2, 1.1, "픽업 작업대", ["상자 3 · ArUco 마커"], fc=C["orange"], tfs=10.5, fs=9)
    rbox(ax, 11.2, 2.5, 2.2, 1.1, "적재 작업대", ["ArUco 마커"], fc=C["orange"], tfs=10.5, fs=9)
    rbox(ax, 8.4, 0.7, 2.5, 1.0, "배우 · 소품", ["걸어 다니는 사람 · 지게차 · 팔레트"], fc=C["grey"], tfs=10.5, fs=8.6)
    arrow(ax, (8.1, 3.05), (11.2, 3.05), color="#1f4e79", lw=2)
    label(ax, 9.65, 3.3, "집기 → 운반 → 놓기", color="#1f4e79", fs=9.5)
    arrow(ax, (4.6, 2.3), (5.6, 2.3), color="#1f4e79", lw=2)
    label(ax, 5.1, 2.55, "주행", color="#1f4e79", fs=9)
    # bottom bands
    note(ax, 0.3, 0.12, "물리: MuJoCo      로봇 소프트웨어: ROS 2 Jazzy      Gazebo는 설치하지 않음", fs=10, color="#333333")
    save(fig, "intro_overview.png")


# ================================================================ 2. MuJoCo <-> ROS 2 bridge interface
def bridge_iface():
    fig, ax = fig_ax(14, 4.0)
    rbox(ax, 0.3, 0.9, 3.6, 2.4, "MuJoCo", ["물리 엔진", "로봇 · 창고 · 센서 모델"], fc=C["green"])
    rbox(ax, 5.2, 0.9, 3.6, 2.4, "Python 브리지", ["MuJoCo 스텝 루프", "프로세스 하나 · Gazebo 플러그인 없음"], fc=C["purple"], fs=8.8)
    rbox(ax, 10.1, 0.9, 3.6, 2.4, "ROS 2 Jazzy", ["Nav2 · MoveIt · RViz", "실제 로봇과 같은 인터페이스"], fc=C["blue"])
    arrow(ax, (3.9, 2.55), (5.2, 2.55), color="#555555")
    label(ax, 4.55, 2.8, "관절 · 바퀴 · 센서 상태", fs=8.5)
    arrow(ax, (5.2, 1.5), (3.9, 1.5), color="#555555")
    label(ax, 4.55, 1.25, "관절 목표 · 바퀴 속도", fs=8.5)
    arrow(ax, (8.8, 2.55), (10.1, 2.55), color="#1f4e79", lw=2)
    label(ax, 9.45, 2.85, "/clock  /joint_states  TF", color="#1f4e79", fs=8.5)
    label(ax, 9.45, 2.28, "/odom  /scan", color="#1f4e79", fs=8.5)
    arrow(ax, (10.1, 1.5), (8.8, 1.5), color="#7a4b00", lw=2)
    label(ax, 9.45, 1.2, "/cmd_vel · 관절 궤적 액션", color="#7a4b00", fs=8.5)
    note(ax, 0.3, 3.7, "물리 엔진은 MuJoCo, 로봇 소프트웨어는 ROS 2", bold=True, fs=12)
    save(fig, "intro_bridge.png")


# ================================================================ 3. navigation stack
def nav_stack():
    fig, ax = fig_ax(14, 3.9)
    note(ax, 0.3, 3.6, "주행: 라이다 · 오도메트리 → SLAM → Nav2", bold=True, fs=12)
    spans = chain(ax, [("라이다 · 바퀴", ["/scan", "/odom + TF"]), ("SLAM Toolbox", ["지도 생성 · 저장", "map → odom"]),
                       ("Nav2", ["AMCL · costmap", "planner · controller"]), ("로봇 주행", ["/cmd_vel", "Goal Pose 도착"])],
                  y=1.1, h=1.9, colors=[C["yellow"], C["blue"], C["blue"], C["green"]])
    rbox(ax, spans[2][0], 0.2, spans[2][1] - spans[2][0], 0.6, "사람 · 지게차 · 팔레트 회피", fc=C["red"], tfs=9.5)
    arrow(ax, ((spans[2][0] + spans[2][1]) / 2, 0.8), ((spans[2][0] + spans[2][1]) / 2, 1.1), color="#C62828")
    save(fig, "intro_nav.png")


# ================================================================ 4. dual-arm manipulation
def manip():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "양팔 Manipulation: MoveIt + Pick & Place 스킬", bold=True, fs=12)
    rbox(ax, 0.3, 1.9, 3.4, 2.0, "MoveIt 2", ["planning group · scene", "IK · 경로 계획"], fc=C["blue"])
    rbox(ax, 4.6, 3.0, 2.6, 0.9, "왼팔 7관절 + 그리퍼", fc=C["green"], tfs=10)
    rbox(ax, 4.6, 1.9, 2.6, 0.9, "오른팔 7관절 + 그리퍼", fc=C["green"], tfs=10)
    arrow(ax, (3.7, 3.45), (4.6, 3.45)); arrow(ax, (3.7, 2.35), (4.6, 2.35))
    label(ax, 4.15, 2.9, "궤적", fs=8.5)
    chain(ax, [("ArUco 도킹", ["카메라가 본 마커 쌍"]), ("상자 위치", ["카메라 검출"]), ("집기", ["작업대 A"]), ("놓기", ["작업대 B"])],
          y=0.3, h=1.25, x0=0.3, x1=13.7, colors=[C["yellow"], C["yellow"], C["orange"], C["orange"]], tfs=10.5, fs=8.6)
    rbox(ax, 8.2, 1.9, 5.5, 2.0, "Pick & Place 스킬 (액션 하나)", ["도킹 → 위치 확인 → 파지 → 운반 → 놓기", "Nav2와 MoveIt을 함께 부른다"], fc=C["teal"])
    arrow(ax, (7.2, 2.9), (8.2, 2.9), color="#555555")
    save(fig, "intro_manip.png")


# ================================================================ 5. camera path (no image topic)
def camera_path():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "카메라: 영상 토픽 없이 Python이 직접 받는다", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 0.9), 8.9, 2.7, fc="#F6F2FB", ec="#9C8AC6", lw=1.2, zorder=1))
    note(ax, 0.5, 3.35, "시뮬레이터 프로세스 (Python)", fs=10, color="#5E4B8B", bold=True)
    spans = chain(ax, [("MuJoCo 카메라 렌더", ["320 × 240 · 2 FPS"]), ("Python 콜백", ["같은 프로세스 · 복사 없음"]),
                       ("검출", ["YOLO (OpenVINO, CPU)", "ArUco 자세 추정"])],
                  y=1.15, h=1.8, x0=0.5, x1=9.0, colors=[C["green"], C["purple"], C["yellow"]], tfs=10.5, fs=8.6)
    rbox(ax, 10.3, 1.15, 3.4, 1.8, "ROS 2", ["/vision/detections (물체 3D 위치)", "/vision/markers (마커)"], fc=C["blue"], fs=8.6)
    arrow(ax, (9.2, 2.05), (10.3, 2.05), color="#8a6d00", lw=2)
    label(ax, 9.75, 2.35, "검출 결과만", color="#8a6d00", fs=9)
    # crossed-out image topic
    ax.plot([9.2, 10.3], [0.55, 0.55], color="#999999", lw=1.4, ls="--", zorder=3)
    cross(ax, 9.75, 0.55)
    note(ax, 10.45, 0.55, "/image_raw 같은 영상 토픽 없음 → 저사양 노트북에서도 실시간", fs=9.2, color="#C62828")
    save(fig, "intro_camera.png")


# ================================================================ 6. LMM role
def lmm_role():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "LMM은 순서를 정하고, 움직임은 ROS 2가 맡는다", bold=True, fs=12)
    chain(ax, [("자연어 지령", ["\"빨간 상자를 적재 작업대로\""]), ("LMM (OpenAI API)", ["Structured Outputs", "RobotPlan"]),
               ("작업 단계 목록", ["이동 → 확인 → 집기", "→ 이동 → 놓기"]), ("ROS 2 Task Manager", ["단계 순차 실행", "확인 · 실패 보고"]),
               ("Nav2 / MoveIt", ["실제 주행 · 팔 동작"])],
          y=1.3, h=2.1, colors=[C["orange"], C["red"], C["yellow"], C["blue"], C["blue"]], tfs=10.5, fs=8.6)
    ax.plot([3.3, 11.4], [0.55, 0.55], color="#999999", lw=1.4, ls="--", zorder=3)
    cross(ax, 7.35, 0.55)
    note(ax, 7.35, 0.2, "LMM → 관절 · 속도 직접 제어는 없다", fs=9.5, color="#C62828", ha="center")
    save(fig, "intro_lmm.png")


# ================================================================ 7. four layers summary
def layers_roles():
    fig, ax = fig_ax(14, 4.4)
    rows = [("지령 층", "사용자 · LMM · Task Manager", "무엇을 · 어떤 순서로  (좌표 · 관절 값 없음)", "#FBF4E4"),
            ("실행 층", "Nav2 · PickPlace 스킬 · MoveIt", "어디로 · 어떻게 움직일지", "#E9F1FB"),
            ("브리지 층", "MuJoCo ↔ ROS 2 브리지 · 카메라 핸들러", "표준 ROS 2 인터페이스 · 검출 결과만 발행", "#EFEAF7"),
            ("물리 층", "MuJoCo 세계", "로봇 · 창고 · 작업대 · 상자 · 배우 · 센서", "#E9F5EA")]
    for i, (t, who, role, fc) in enumerate(rows):
        y = 3.45 - i * 1.05
        ax.add_patch(Rectangle((0.3, y), 13.4, 0.9, fc=fc, ec="none", zorder=1))
        ax.text(0.55, y + 0.45, t, ha="left", va="center", fontsize=12, fontweight="bold", color=INK)
        ax.text(2.6, y + 0.45, who, ha="left", va="center", fontsize=10.5, color=INK)
        ax.text(8.2, y + 0.45, role, ha="left", va="center", fontsize=9.8, color="#555555")
    save(fig, "intro_layers.png")


# ================================================================ 8. one-line pipeline
def pipeline():
    fig, ax = fig_ax(14, 3.0)
    note(ax, 0.3, 2.75, "한 줄 요약: 하나의 워크스페이스에 파이프라인 전체가 들어 있다", bold=True, fs=12)
    chain(ax, ["자연어 지령", "LMM", "Task Planning", "ROS 2", "Nav2 / MoveIt", "MuJoCo", "로봇 행동"], y=0.9, h=1.2, gap=0.3,
          colors=[C["orange"], C["red"], C["yellow"], C["blue"], C["blue"], C["green"], C["teal"]], tfs=10.5)
    note(ax, 0.3, 0.45, "검증 환경: Ubuntu 24.04 · ROS 2 Jazzy · 4코어 노트북 · 외장 GPU 없음", fs=9.5)
    save(fig, "intro_pipeline.png")


# ================================================================ 9. course format
def course_format():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "단기 집중 수업: 완성 코드를 실행하며 구조를 이해한다", bold=True, fs=12)
    chain(ax, [("GitHub 완성 코드", ["clone · 설치 스크립트"]), ("단계별 실행", ["모듈마다 명령 하나"]),
               ("핵심 코드 읽기", ["ROS 2 ↔ MuJoCo 연결"]), ("전체 시스템 연결", ["Final Mission"])],
          y=0.9, h=1.7, colors=[C["grey"], C["blue"], C["yellow"], C["green"]], tfs=10.5, fs=8.8)
    ax.plot([0.3, 4.5], [0.45, 0.45], color="#999999", lw=1.4, ls="--", zorder=3); cross(ax, 2.4, 0.45)
    note(ax, 4.7, 0.45, "처음부터 코드를 짜는 수업이 아니다", fs=9.5, color="#C62828")
    save(fig, "intro_format.png")


# ================================================================ 10. audience & environment
def env_spec():
    fig, ax = fig_ax(14, 2.3)
    tiles(ax, [("대상", ["ROS 2 기초를 아는 학부 · 대학원생", "60~80명 · 본인 노트북"], C["orange"]),
               ("노트북", ["Ubuntu 24.04 native · 4코어 · 16 GB 이상", "내장 그래픽 (외장 GPU 불필요)"], C["blue"]),
               ("사전 준비", ["캠프 전에 설치 완료", "수업 중 설치 작업 없음 · Gazebo 불필요"], C["green"])],
          cols=3, y_top=2.0, h=1.7, tfs=12, fs=9.4)
    save(fig, "intro_env.png")


# ================================================================ 11. module cycle
def module_cycle():
    fig, ax = fig_ax(14, 3.3)
    note(ax, 0.3, 3.0, "모듈 진행: 네 단계를 반복한다", bold=True, fs=12)
    spans = chain(ax, [("① 개념 설명", ["왜 이렇게 만드는가"]), ("② 핵심 코드", ["브리지 · launch · 노드"]),
                       ("③ 따라 실행", ["ros2 launch 또는 스크립트 하나"]), ("④ 결과 확인", ["RViz · 토픽 · 문제 해결"])],
                  y=0.9, h=1.6, colors=[C["yellow"], C["purple"], C["blue"], C["green"]], tfs=10.5, fs=8.8)
    # return path to next module
    xr = (spans[3][0] + spans[3][1]) / 2; xl = (spans[0][0] + spans[0][1]) / 2
    ax.plot([xr, xr], [0.9, 0.5], color="#7a4b00", lw=1.3); ax.plot([xr, xl], [0.5, 0.5], color="#7a4b00", lw=1.3)
    arrow(ax, (xl, 0.5), (xl, 0.9), color="#7a4b00", lw=1.3)
    label(ax, (xl + xr) / 2, 0.5, "다음 모듈", color="#7a4b00", fs=9)
    save(fig, "intro_cycle.png")


# ================================================================ 12. goals of the two halves
def goals():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "전반부 목표: 창고 자율주행", bold=True, fs=12, color="#1f4e79")
    chain(ax, ["ROS 2 Launch", "MuJoCo", "LiDAR", "SLAM", "Nav2", "자율주행"], y=2.6, h=1.1, colors=[C["blue"]], tfs=10.5)
    note(ax, 0.3, 2.1, "후반부 목표: 자연어 → 로봇 행동 파이프라인 완성", bold=True, fs=12, color="#2e7d32")
    chain(ax, ["자연어", "LMM", "Task Planning", "ROS 2", "Nav2 / MoveIt", "MuJoCo", "로봇 행동"], y=0.6, h=1.1, gap=0.28,
          colors=[C["green"]], tfs=10.5)
    save(fig, "intro_goals.png")


# ================================================================ 13/14. curriculum staircases
def curriculum_front():
    fig, ax = fig_ax(14, 4.0)
    flow_rows(ax, [("① Gazebo vs MuJoCo", "전체 Architecture"), ("② MuJoCo + ROS 2", "브리지 · 최소 예제"),
                   ("③ Launch · Description", "URDF/Xacro → MJCF"), ("④ Sensor · TF · Odom", "LaserScan · /odom"),
                   ("⑤ SLAM", "SLAM Toolbox · 지도"), ("⑥ Nav2", "AMCL · costmap · 회피"), ("전반부 통합 Demo", "Launch → MuJoCo → SLAM → Nav2")],
              per_row=4, colors=[C["blue"], C["blue"], C["blue"], C["yellow"], C["yellow"], C["yellow"], C["green"]])
    save(fig, "intro_curriculum_front.png")


def curriculum_back():
    fig, ax = fig_ax(14, 4.0)
    flow_rows(ax, [("⑦ MoveIt + MuJoCo", "planning group · scene"), ("⑧ Arm · End-Effector", "IK · Cartesian · 그리퍼"),
                   ("⑨ Pick & Place", "확인 → 파지 → 놓기"), ("⑩ Nav + Pick & Place", "ArUco 도킹 · 상태 기계"),
                   ("⑪ LMM + OpenAI API", "Structured Command"), ("⑫ LMM → ROS 2", "Task Manager 파이프라인"),
                   ("⑬ Web Dashboard", "상태 · 지령 입력"), ("⑭ Final Mission", "End-to-End 운반")],
              per_row=4, colors=[C["blue"], C["blue"], C["yellow"], C["yellow"], C["red"], C["red"], C["purple"], C["green"]])
    save(fig, "intro_curriculum_back.png")


# ================================================================ 15. pipeline with example
def pipeline_example():
    fig, ax = fig_ax(14, 4.8)
    note(ax, 0.3, 4.5, "핵심 파이프라인과 예시 지령", bold=True, fs=12)
    chain(ax, ["자연어 명령", "LMM (OpenAI API)", "Task Planning", "Task Manager", "Nav2 / MoveIt", "MuJoCo", "로봇 행동"],
          y=3.0, h=1.1, gap=0.28, colors=[C["orange"], C["red"], C["yellow"], C["blue"], C["blue"], C["green"], C["teal"]], tfs=9.8)
    rbox(ax, 0.3, 1.2, 4.0, 1.4, "\"픽업 작업대로 이동해서", ["빨간 상자를 집고", "적재 작업대로 옮겨.\""], fc=C["orange"], tfs=10.5, fs=10)
    arrow(ax, (4.3, 1.9), (5.0, 1.9))
    chain(ax, ["Navigate\n(pick_table)", "Detect\n(red parcel)", "Pick", "Navigate\n(place_table)", "Place"], y=1.2, h=1.4, x0=5.0, gap=0.25,
          colors=[C["blue"], C["yellow"], C["green"], C["blue"], C["green"]], tfs=10)
    note(ax, 0.3, 0.6, "LMM 출력은 단계 목록(RobotPlan)이다.  좌표 · 관절 값은 ROS 2 쪽이 정한다.", fs=9.5)
    save(fig, "intro_pipeline_example.png")


# ================================================================ 16-18. tech stack groups
def stack_group(name, title, items):
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.65, title, bold=True, fs=12)
    tiles(ax, items, cols=2, y_top=4.35, h=1.85, gap=0.3, tfs=11.5, fs=9)
    save(fig, name)


def stack_sim():
    stack_group("intro_stack_sim.png", "기술 스택 A: 시뮬레이션 · ROS 2 · 모델 · 센서  (모듈 ①~④)", [
        ("물리 시뮬레이션  ①②", ["MuJoCo · MJCF · Python 바인딩", "스텝 루프 · 액추에이터 · 센서 코드 읽기", "Gazebo와 구조 비교"], C["green"]),
        ("ROS 2 Jazzy  ②③④", ["Topic · Service · Action · TF2 · launch", "use_sim_time · lifecycle · colcon", "ros2 topic / action / tf2_tools 로 점검"], C["blue"]),
        ("로봇 모델링  ③", ["URDF / Xacro · Joint · Link · TF 트리", "URDF → MJCF 변환 · robot_state_publisher", "RViz 에서 관절 움직여 보기"], C["yellow"]),
        ("센서와 위치 추정  ④", ["LaserScan · Odometry", "TF: odom → base, map → odom", "어디서 만들어져 어느 프레임에 실리는지 확인"], C["orange"]),
    ])


def stack_motion():
    stack_group("intro_stack_motion.png", "기술 스택 B: 주행 · Manipulation · 인지 · Pick & Place  (모듈 ⑤~⑩)", [
        ("SLAM · 자율주행  ⑤⑥", ["SLAM Toolbox · Nav2 (AMCL, costmap, BT)", "지도 생성 · 저장 → Goal Pose 주행", "사람 · 장애물 회피 · 파라미터 효과"], C["blue"]),
        ("Manipulation  ⑦⑧", ["MoveIt 2 · IK /compute_ik · Cartesian path", "그리퍼 액션 · FollowJointTrajectory", "Python 호출 → 궤적이 시뮬레이터로 가는 길"], C["green"]),
        ("인지  ⑨⑩", ["ArUco 자세 추정 · YOLO (OpenVINO, CPU)", "깊이 → 3D 위치 · TF 좌표 변환", "영상을 토픽으로 흘리지 않는 이유"], C["yellow"]),
        ("Pick & Place · Mobile Manipulation  ⑨⑩", ["스킬 서버(액션) 상태 기계", "도킹 → 파지 → 운반 → 놓기 · attach/detach", "단계별 피드백 · 실패 복구"], C["teal"]),
    ])


def stack_lmm():
    stack_group("intro_stack_lmm.png", "기술 스택 C: LMM · Task Planning · UI · 개발 도구  (모듈 ⑪~⑭)", [
        ("LMM · 프롬프트 엔지니어링  ⑪⑫", ["OpenAI API · Structured Outputs (pydantic)", "few-shot · 스키마 검증 / 세계 검증 분리", "테스트셋 정확도 · 비용 로그"], C["red"]),
        ("Task Planning · 시스템 통합  ⑫⑭", ["ROS 2 Task Manager (액션 서버)", "단계 순차 실행 · 확인 · 되묻기 · 인터록", "Nav2 / MoveIt / 스킬 액션으로 실행"], C["blue"]),
        ("운영 · UI  ⑬", ["텍스트 콘솔 (Utterance 토픽)", "웹 대시보드 (websocket ↔ ROS 2)", "RViz · MuJoCo viewer"], C["purple"]),
        ("개발 도구  전체", ["Ubuntu 24.04 · Python 3.12 venv · colcon · git", "설치 · 점검 스크립트", "저사양 설정: 카메라 2대 320×240 2 FPS · CPU 추론"], C["grey"]),
    ])


# ================================================================ 19. stack order
def stack_order():
    fig, ax = fig_ax(14, 3.0)
    note(ax, 0.3, 2.75, "쌓이는 순서", bold=True, fs=12)
    chain(ax, [("시뮬레이션", ["MuJoCo"]), ("ROS 2", ["브리지 · 모델"]), ("주행", ["SLAM · Nav2"]), ("Manipulation", ["MoveIt"]),
               ("인지", ["ArUco · YOLO"]), ("LMM", ["OpenAI API"]), ("통합", ["Task Manager"])], y=0.9, h=1.3, gap=0.28,
          colors=[C["green"], C["blue"], C["yellow"], C["blue"], C["orange"], C["red"], C["teal"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.45, "각 층의 코드는 블록선도의 상자 하나에 대응한다", fs=9.5)
    save(fig, "intro_stack_order.png")


# ================================================================ 20. repository layout
def repo_tree():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco", bold=True, fs=12)
    tiles(ax, [("src/", ["ROS 2 패키지 10개", "description · bridge · bringup", "navigation · moveit_config", "warehouse_interfaces · skills · lecture"], C["blue"]),
               ("lessons/", ["모듈별 실습 안내"], C["yellow"]),
               ("examples/", ["단계별 예제 코드"], C["yellow"]),
               ("weights/", ["배포용 검출 가중치 (OpenVINO 320)"], C["green"]),
               ("scripts/", ["실행 · 설치 · 점검 스크립트"], C["purple"]),
               ("docs/", ["사용 설명서 · 검증 기록"], C["grey"]),
               ("tests/", ["단위 테스트"], C["grey"])],
          cols=4, y_top=3.55, h=1.7, gap=0.25, tfs=12, fs=8.8)
    save(fig, "intro_repo.png")


# ================================================================ 21. install & contact
def install_note():
    fig, ax = fig_ax(14, 3.4)
    chain(ax, [("README", ["저장소 첫 화면"]), ("docs/lecture/00_setup.md", ["설치 절차"]), ("Ubuntu 24.04 + ROS 2 Jazzy", ["native 설치"]),
               ("설치 점검", ["스크립트 · pytest"])],
          y=1.3, h=1.7, colors=[C["grey"], C["yellow"], C["blue"], C["green"]], tfs=10.5, fs=9)
    ax.plot([0.3, 3.5], [0.7, 0.7], color="#999999", lw=1.4, ls="--", zorder=3); cross(ax, 1.9, 0.7)
    note(ax, 3.7, 0.7, "도커 · VM 미지원", fs=9.5, color="#C62828")
    note(ax, 13.7, 0.7, "문의: contact@pinklab.art  ·  https://pinklab.art", fs=9.5, ha="right")
    save(fig, "intro_install.png")


if __name__ == "__main__":
    for f in (overview, bridge_iface, nav_stack, manip, camera_path, lmm_role, layers_roles, pipeline, course_format, env_spec,
              module_cycle, goals, curriculum_front, curriculum_back, pipeline_example, stack_sim, stack_motion, stack_lmm,
              stack_order, repo_tree, install_note):
        f()
