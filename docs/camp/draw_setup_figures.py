"""Figures for the setup & usage page: install flow, run structure, warehouse map, pick & place flow."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle

for name in ("NanumGothic", "Noto Sans CJK KR", "NanumBarunGothic"):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False
OUT = Path("docs/camp")
INK = "#2b2b2b"


def rbox(ax, x0, y0, w, h, title, lines=(), fc="#EEF3FA", ec=INK, tfs=11.5, fs=9.2, lw=1.2, title_dy=0.22):
    ax.add_patch(FancyBboxPatch((x0, y0), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x0 + w / 2, y0 + h - title_dy, title, ha="center", va="top", fontsize=tfs, fontweight="bold", color=INK, zorder=3)
    for i, t in enumerate(lines):
        ax.text(x0 + 0.18, y0 + h - title_dy - 0.42 - 0.3 * i, t, ha="left", va="top", fontsize=fs, color="#333333", zorder=3)


def arrow(ax, p, q, color=INK, lw=1.6, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=15, lw=lw, color=color, zorder=4, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- 1. install flow
def install_flow():
    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=150)
    ax.set_xlim(0, 14); ax.set_ylim(0, 4.2); ax.axis("off")
    steps = [
        ("1  ROS 2 Jazzy", ["ros-jazzy-desktop", "Nav2 · SLAM Toolbox", "MoveIt · RViz · xacro", "rosdep init / update"], "#E3EEFF"),
        ("2  저장소 받기", ["git clone <GitHub 저장소>", "cd pinklab_mobile_…", "source /opt/ros/jazzy/", "        setup.bash"], "#FFF3D6"),
        ("3  install_lecture.sh", ["rosdep 확인", "venv (.venv-mobile-openarm)", "pip: torch CPU · ultralytics", "colcon build · pytest"], "#E6F7E6"),
        ("4  .env", ["cp .env.example .env", "OPENAI_API_KEY=…", "LMM 모듈에서만 필요", "키는 강사가 배포"], "#FFE0E0"),
        ("5  확인", ["pytest 41개 PASS", "start → 준비 완료 3줄", "goal 1.0 0.6 0", "pick red (약 3분)"], "#EDE7F6"),
    ]
    w, gap, x = 2.45, 0.35, 0.3
    for i, (title, lines, fc) in enumerate(steps):
        rbox(ax, x, 0.8, w, 2.7, title, lines, fc=fc, tfs=12, fs=9.4)
        if i < len(steps) - 1:
            arrow(ax, (x + w, 2.15), (x + w + gap, 2.15))
        x += w + gap
    ax.text(0.3, 4.0, "설치 흐름 (처음 한 번, 10~20분)", fontsize=12, fontweight="bold", color=INK, va="top")
    ax.text(0.3, 0.45, "매 터미널:  source /opt/ros/jazzy/setup.bash  →  source scripts/env.sh", fontsize=10, color="#444444", va="top")
    fig.savefig(OUT / "setup_flow.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 2. run structure
def run_structure():
    fig, ax = plt.subplots(figsize=(14, 6.4), dpi=150)
    ax.set_xlim(0, 14); ax.set_ylim(0, 6.4); ax.axis("off")
    # terminal 1
    ax.add_patch(Rectangle((0.3, 0.4), 8.2, 5.6, fc="#F7F8FA", ec="#B0B7C3", lw=1.2, zorder=1))
    ax.text(0.55, 5.75, "터미널 1   ./scripts/mobile_openarm start", fontsize=12.5, fontweight="bold", color=INK, va="top")
    ax.text(0.55, 5.35, "launch 하나가 아래 프로세스를 모두 띄운다  (한 번에 하나만)", fontsize=9.5, color="#555555", va="top")
    rbox(ax, 0.55, 3.3, 3.7, 1.7, "MuJoCo 브리지 (Python)", ["MuJoCo 물리 + 창고 + 배우", "/clock /joint_states TF /odom /scan", "카메라 핸들러 (검출 · 마커)"], fc="#EDE7F6")
    rbox(ax, 4.5, 3.3, 3.8, 1.7, "Nav2 + AMCL", ["map_server · amcl · planner", "controller · bt_navigator", "/navigate_to_pose"], fc="#E3EEFF")
    rbox(ax, 0.55, 1.2, 3.7, 1.7, "MoveIt 2 (move_group)", ["planning scene · IK", "/move_action · /compute_ik", "RViz (rviz:=false 로 끌 수 있음)"], fc="#E3EEFF")
    rbox(ax, 4.5, 1.2, 3.8, 1.7, "PickPlace 스킬 서버", ["/pick_place 액션", "도킹 → 파지 → 놓기", "phase = all | pick | place"], fc="#E6F7E6")
    ax.text(0.55, 0.85, "준비 완료 신호:  Managed nodes are active  ·  You can start planning now!  ·  PickPlace server ready",
            fontsize=9, color="#2e7d32", va="top")
    # terminal 2
    ax.add_patch(Rectangle((9.0, 0.4), 4.7, 5.6, fc="#FFFBF0", ec="#D9C48A", lw=1.2, zorder=1))
    ax.text(9.25, 5.75, "터미널 2   명령 · 예제", fontsize=12.5, fontweight="bold", color=INK, va="top")
    ax.text(9.25, 5.35, "source scripts/env.sh 후 실행", fontsize=9.5, color="#555555", va="top")
    rows = [("goal 1.0 0.6 0", "Nav2 목표"), ("arm both ready", "MoveIt 이름 자세"), ("pick red", "운반 스킬 (약 3분)"),
            ("pick red --phase pick", "집기까지만"), ("exec ros2 topic list", "ROS 2 CLI"), ("exec python examples/…", "모듈 예제"),
            ("ros2 run warehouse_lecture task_manager", ""), ("scripts/cleanup_ros.sh", "잔여 프로세스 정리")]
    for i, (cmd, what) in enumerate(rows):
        y = 4.75 - i * 0.5
        ax.add_patch(FancyBboxPatch((9.25, y - 0.18), 4.2, 0.4, boxstyle="round,pad=0,rounding_size=0.06", fc="white", ec="#D9C48A", lw=0.8, zorder=2))
        ax.text(9.35, y + 0.02, cmd, fontsize=8.6, family="monospace", color=INK, va="center", zorder=3)
        ax.text(13.35, y + 0.02, what, fontsize=8.2, color="#666666", va="center", ha="right", zorder=3)
    arrow(ax, (9.0, 3.1), (8.5, 3.1), color="#7a4b00", style="<|-|>")
    ax.text(8.75, 3.22, "ROS 2", fontsize=8, color="#7a4b00", ha="center", va="bottom")
    ax.text(9.25, 0.95, "통신은 이 PC 안 (localhost, ROS_DOMAIN_ID 43)", fontsize=8.2, color="#7a4b00", va="top")
    ax.text(9.25, 0.68, "강의실의 다른 노트북과 토픽이 섞이지 않음", fontsize=8.2, color="#7a4b00", va="top")
    fig.savefig(OUT / "run_structure.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 3. warehouse map
def warehouse_map():
    w = yaml.safe_load(Path("src/mobile_openarm_mujoco/worlds/warehouse.yaml").read_text())
    loc = yaml.safe_load(Path("src/warehouse_lecture/worlds/locations.yaml").read_text())["locations"]
    actors = yaml.safe_load(Path("src/mobile_openarm_mujoco/worlds/actors.yaml").read_text())["actors"]
    fig, ax = plt.subplots(figsize=(13, 9.6), dpi=150)
    ax.set_aspect("equal")
    ax.set_xlim(-8.3, 8.3); ax.set_ylim(-6.3, 6.3)
    ax.set_xlabel("x [m]  (map / world)"); ax.set_ylabel("y [m]")
    ax.grid(True, color="#E5E5E5", lw=0.6, zorder=0)
    for b in w["boxes"]:
        cx, cy, cz = b["center"]; sx, sy, sz = b["size"]
        n = b["name"]
        if n.startswith("wall"):
            fc, ec, z = "#9E9E9E", "#616161", 3
        elif "_post_" in n or "_shelf_" in n:
            fc, ec, z = "#CFD8DC", "#90A4AE", 2
        elif "_stock_" in n:
            fc, ec, z = "#FFE0B2", "#FB8C00", 2
        elif "table" in n:
            fc, ec, z = "#C8E6C9", "#2E7D32", 3
        else:
            fc, ec, z = "#E0E0E0", "#9E9E9E", 2
        ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy, fc=fc, ec=ec, lw=0.6, zorder=z))
    for o in w["objects"]:
        cx, cy, _ = o["center"]
        ax.add_patch(Circle((cx, cy), 0.12, fc=o["rgba"][:3], ec="black", lw=0.6, zorder=6))
    for m in w["markers"]:
        cx, cy, _ = m["center"]
        ax.add_patch(Rectangle((cx - 0.05, cy - 0.13), 0.1, 0.26, fc="white", ec="black", lw=1.0, zorder=6))
        ax.text(cx + 0.18, cy, f"id {m['id']}", fontsize=7.5, va="center", zorder=7)
    for name, d in loc.items():
        x, y, yaw = d["base_goal"]
        ax.plot(x, y, marker=(3, 0, __import__("math").degrees(yaw) - 90), ms=13, color="#1565C0", zorder=7, linestyle="none")
        label = d["aliases"][0] if d.get("aliases") else name
        ax.text(x, y + 0.42, f"{name}\n{label}", fontsize=8, ha="center", va="bottom", color="#0D47A1", zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    icon = {"worker": ("o", "#E53935"), "visitor": ("o", "#E53935"), "forklift": ("s", "#FDD835"), "pallet": ("s", "#8D6E63"),
            "cone": ("^", "#FB8C00"), "extinguisher": ("D", "#D32F2F")}
    for a in actors:
        kind = a["name"].split("_")[0]
        mk, col = icon.get(kind, ("x", "black"))
        p = a.get("pose", a.get("position"))
        ax.plot(p[0], p[1], marker=mk, ms=9 if kind in ("worker", "visitor") else 11, color=col, mec="black", mew=0.5, linestyle="none", zorder=7)
        ax.text(p[0] + 0.22, p[1] - 0.05, a["name"], fontsize=6.8, color="#444444", va="center", zorder=8)
    sx, sy, _ = w["spawn"]
    ax.plot(sx, sy, marker="*", ms=16, color="#00897B", mec="black", mew=0.5, linestyle="none", zorder=8)
    ax.text(sx + 0.25, sy - 0.35, "spawn (기본 시작)", fontsize=8, color="#00695C", zorder=8)
    handles = [
        plt.Line2D([], [], marker="s", color="#C8E6C9", mec="#2E7D32", ms=10, ls="none", label="작업대 (상판 0.78 m)"),
        plt.Line2D([], [], marker="s", color="#FFE0B2", mec="#FB8C00", ms=10, ls="none", label="랙 재고 상자"),
        plt.Line2D([], [], marker="o", color="#E53935", mec="black", ms=8, ls="none", label="상자 parcel 1~3 (빨강·파랑·노랑)"),
        plt.Line2D([], [], marker="s", color="white", mec="black", ms=8, ls="none", label="ArUco 마커 (작업대 다리)"),
        plt.Line2D([], [], marker="^", color="#1565C0", ms=10, ls="none", label="이름 있는 장소 base_goal (방향 = 진행 방향)"),
        plt.Line2D([], [], marker="o", color="#E53935", mec="black", ms=8, ls="none", label="사람 배우 (2명 통로 왕복)"),
        plt.Line2D([], [], marker="s", color="#FDD835", mec="black", ms=9, ls="none", label="지게차 · 팔레트 · 콘 · 소화기"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, fontsize=8, frameon=False)
    ax.set_title("창고 배치도 15 × 11 m  (warehouse.yaml · locations.yaml · actors.yaml)", fontsize=12, fontweight="bold")
    fig.savefig(OUT / "warehouse_map.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- 4. pick & place flow
def pick_place_flow():
    fig, ax = plt.subplots(figsize=(14, 4.6), dpi=150)
    ax.set_xlim(0, 14); ax.set_ylim(0, 4.6); ax.axis("off")
    phases = [
        ("navigate_pick", ["Nav2 로 사전 도킹", "지점 (작업대 앞 1.2 m)", "팔은 transport 자세"], "#E3EEFF"),
        ("dock", ["ArUco 마커 쌍 시각 서보", "마지막 0.2 m 오도메트리", "잔차 1~3 cm"], "#E3EEFF"),
        ("locate · grasp", ["카메라 검출 → 상자 위치", "물체 쪽 팔 자동 선택", "IK → 직선 접근 → 파지 판정"], "#E6F7E6"),
        ("lift · carry", ["4 cm 들고 후퇴", "hands_up 자세", "0.75 m 후진"], "#E6F7E6"),
        ("navigate_place · dock", ["Nav2 로 적재 작업대", "마커 도킹", ""], "#E3EEFF"),
        ("place", ["빈 슬롯에 내려놓기", "그리퍼 열고 detach", "transport 복귀 · 후진"], "#FFF3D6"),
    ]
    w, gap, x = 2.05, 0.25, 0.25
    for i, (title, lines, fc) in enumerate(phases):
        rbox(ax, x, 1.1, w, 2.4, title, lines, fc=fc, tfs=10.5, fs=8.6)
        if i < len(phases) - 1:
            arrow(ax, (x + w, 2.3), (x + w + gap, 2.3))
        x += w + gap
    ax.plot([0.25, 4.85], [0.85, 0.85], color="#2e7d32", lw=2.5)
    ax.text(2.55, 0.55, "phase = pick  (상자를 든 채 끝남)", ha="center", va="top", fontsize=9.5, color="#2e7d32", fontweight="bold")
    ax.plot([9.45, 13.75], [0.85, 0.85], color="#7a4b00", lw=2.5)
    ax.text(11.6, 0.55, "phase = place  (든 상자를 to_station 에)", ha="center", va="top", fontsize=9.5, color="#7a4b00", fontweight="bold")
    ax.text(0.25, 4.3, "운반 스킬 /pick_place 의 단계  (phase 를 비우면 pick → place 를 한 번에, 회당 약 2.5~3분)", fontsize=11.5, fontweight="bold", color=INK, va="top")
    ax.text(0.25, 3.85, "피드백 topic 의 phase 이름이 그대로 상자 제목이다. 실패하면 phase_reached 에 멈춘 단계가 남는다.", fontsize=9, color="#555555", va="top")
    fig.savefig(OUT / "pick_place_flow.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    install_flow(); run_structure(); warehouse_map(); pick_place_flow()
    print("ok")
