"""Block diagram of the package architecture for the Confluence intro page (matplotlib, no ROS).

Four horizontal layers (command / execution / bridge / physics) drawn as shaded bands; boxes are aligned on
columns and every arrow is vertical or horizontal so that nothing crosses or overlaps.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib import font_manager

KO = None
for name in ("NanumGothic", "Noto Sans CJK KR", "Noto Sans KR", "NanumBarunGothic"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        KO = name
        break
if KO:
    plt.rcParams["font.family"] = KO
plt.rcParams["axes.unicode_minus"] = False

W, H = 14.0, 9.6
fig, ax = plt.subplots(figsize=(W, H), dpi=150)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

INK = "#2b2b2b"
BAND = {"cmd": "#FBF4E4", "exe": "#E9F1FB", "bridge": "#EFEAF7", "phys": "#E9F5EA"}
BOX = {"user": "#FFE9B8", "llm": "#FFD6D6", "tm": "#CFE0F7", "ros": "#D7E6FA", "skill": "#D5F0D8", "bridge": "#E4DBF3", "cam": "#FFF2B3", "world": "#DCEFDD"}

# --- layer bands ---------------------------------------------------------------------------------
LAYERS = [  # (key, y0, y1, title, subtitle)
    ("cmd", 7.05, 9.35, "지령 층", "무엇을 · 어떤 순서로"),
    ("exe", 4.45, 6.85, "실행 층", "어디로 · 어떻게 움직일지"),
    ("bridge", 2.05, 4.25, "브리지 층", "ROS 2 인터페이스"),
    ("phys", 0.25, 1.85, "물리 층", "MuJoCo"),
]
for key, y0, y1, title, sub in LAYERS:
    ax.add_patch(Rectangle((0.15, y0), W - 0.3, y1 - y0, fc=BAND[key], ec="none", zorder=0))
    ax.text(0.45, (y0 + y1) / 2 + 0.16, title, ha="left", va="center", fontsize=12.5, fontweight="bold", color=INK)
    ax.text(0.45, (y0 + y1) / 2 - 0.22, sub, ha="left", va="center", fontsize=9, color="#666666")


def box(x0, x1, y0, y1, title, lines=(), color="#EEEEEE", tfs=12, fs=9.8, lw=1.2):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.14",
                                fc=color, ec=INK, lw=lw, zorder=2))
    n = len(lines)
    top = y1 - 0.24
    ax.text((x0 + x1) / 2, top, title, ha="center", va="top", fontsize=tfs, fontweight="bold", color=INK, zorder=3)
    for i, line in enumerate(lines):
        ax.text((x0 + x1) / 2, top - 0.42 - 0.31 * i, line, ha="center", va="top", fontsize=fs, color="#333333", zorder=3)


def arrow(p, q, style="-|>", color=INK, lw=1.5):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=15, lw=lw, color=color, zorder=4,
                                 shrinkA=0, shrinkB=0))


def label(x, y, text, color=INK, fs=9, ha="center", va="center", bg=True):
    ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color, zorder=5,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9) if bg else None)


def path(points, color=INK, lw=1.5, style="-|>"):
    """Orthogonal polyline; arrow head on the last segment."""
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=lw, zorder=4, solid_capstyle="round")
    arrow(points[-2], points[-1], style=style, color=color, lw=lw)


# --- layer 1: command --------------------------------------------------------------------------
box(2.2, 5.0, 7.45, 8.95, "사용자", ["텍스트 콘솔 · 웹 대시보드", "/warehouse/utterance"], BOX["user"])
box(5.7, 9.1, 7.45, 8.95, "LMM (OpenAI API)", ["자연어 → 작업 단계 목록", "Structured Outputs (RobotPlan)"], BOX["llm"])
box(9.8, 13.7, 7.45, 8.95, "ROS 2 Task Manager", ["단계 순차 실행 · 확인 · 실패 보고", "/execute_plan"], BOX["tm"])
arrow((5.0, 8.2), (5.7, 8.2))
label(5.35, 8.42, "지령", fs=9)
arrow((9.1, 8.2), (9.8, 8.2))
label(9.45, 8.42, "단계 목록", fs=9)
# reply back to the user along the top
path([(11.75, 8.95), (11.75, 9.2), (3.6, 9.2), (3.6, 8.95)], color="#7a4b00", lw=1.3)
label(7.6, 9.2, "결과 문장  /warehouse/narration", color="#7a4b00", fs=8.8)

# --- layer 2: execution ------------------------------------------------------------------------
box(2.2, 5.6, 4.85, 6.4, "Nav2", ["AMCL · costmap · planner", "/navigate_to_pose"], BOX["ros"])
box(6.3, 9.6, 4.85, 6.4, "PickPlace 스킬 서버", ["ArUco 도킹 → 위치 확인 → 파지 → 놓기", "/pick_place  (phase = pick | place)"], BOX["skill"], fs=9.4)
box(10.3, 13.7, 4.85, 6.4, "MoveIt 2", ["planning group · planning scene", "양팔 IK · 경로 계획  /move_action"], BOX["ros"])
# Task Manager -> bus -> Nav2 / PickPlace
path([(11.75, 7.45), (11.75, 6.95), (3.9, 6.95), (3.9, 6.4)], color="#1f4e79")
path([(7.95, 6.95), (7.95, 6.4)], color="#2e7d32")
ax.plot([7.95, 7.95], [6.95, 6.95], color="#2e7d32")  # junction marker (no-op line keeps zorder order simple)
label(3.9, 6.68, "navigate", color="#1f4e79", fs=9)
label(7.95, 6.68, "pick · place", color="#2e7d32", fs=9)
label(11.75, 7.2, "단계마다 액션 호출", color="#1f4e79", fs=8.5, ha="left")
# skill <-> Nav2, skill <-> MoveIt
arrow((6.3, 5.62), (5.6, 5.62), style="<|-|>", color="#1f4e79", lw=1.3)
label(5.95, 5.9, "사전 도킹 주행", color="#1f4e79", fs=8.5)
arrow((9.6, 5.62), (10.3, 5.62), style="<|-|>", color="#1f4e79", lw=1.3)
label(9.95, 5.9, "팔 계획 · 실행", color="#1f4e79", fs=8.5)

# --- layer 3: bridge (camera handler lives inside the same process) ------------------------------
box(2.2, 13.7, 2.15, 4.12, "MuJoCo ↔ ROS 2 브리지 (Python 프로세스)",
    ["스텝 루프에서 /clock · /joint_states · TF · /odom · /scan 발행,  /cmd_vel · 관절 궤적 액션 수신"], BOX["bridge"], fs=9.6)
box(6.3, 9.6, 2.24, 3.2, "카메라 핸들러", ["영상 토픽 없음 → 검출 결과만 발행"], BOX["cam"], tfs=10.5, fs=8.8)
# Nav2 <-> bridge, MoveIt <-> bridge
arrow((3.9, 4.85), (3.9, 4.12), style="<|-|>", color="#555555")
label(3.9, 4.45, "/cmd_vel  ↓      ↑  /scan  /odom  TF", color="#444444", fs=8.5)
arrow((12.0, 4.85), (12.0, 4.12), style="<|-|>", color="#555555")
label(12.0, 4.45, "관절 궤적 액션  ↓      ↑  /joint_states", color="#444444", fs=8.5)
# camera handler -> skill
arrow((7.95, 3.2), (7.95, 4.85), color="#8a6d00")
label(7.95, 4.45, "/vision/detections · /vision/markers", color="#8a6d00", fs=8.5)

# --- layer 4: physics --------------------------------------------------------------------------
box(2.2, 13.7, 0.45, 1.65, "MuJoCo 물리 세계",
    ["Vic Pinky 베이스 + OpenARM 양팔(7관절 × 2 + 그리퍼) · 창고 15 × 11 m · 작업대 2 · 상자 3 · ArUco 마커 · 사람·지게차 배우 · 라이다 · 카메라 4"],
    BOX["world"], fs=9.4)
arrow((3.9, 2.15), (3.9, 1.65), style="<|-|>", color="#555555")
label(3.9, 1.92, "물리 스텝 · 관절/바퀴 상태 · 라이다", color="#444444", fs=8.5)
arrow((7.95, 1.65), (7.95, 2.24), color="#8a6d00")
label(7.95, 1.92, "카메라 렌더 (프레임)", color="#8a6d00", fs=8.5)
arrow((12.0, 2.15), (12.0, 1.65), style="<|-|>", color="#555555")
label(12.0, 1.92, "관절 목표 · 실제 관절값", color="#444444", fs=8.5)

fig.savefig("docs/camp/architecture.png", bbox_inches="tight", facecolor="white")
print("font:", KO or "(no Korean font)")
