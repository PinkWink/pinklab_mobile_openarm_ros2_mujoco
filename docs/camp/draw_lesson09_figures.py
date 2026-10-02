"""Figures for the lesson-09 Confluence page (Arm / End-Effector Control). Output: docs/camp/lesson09_*.png

Run from the workspace root with the workspace venv (needs mujoco, offscreen EGL):
    MUJOCO_GL=egl .venv-mobile-openarm/bin/python docs/camp/draw_lesson09_figures.py
Data (2026-10-02, moveit mode):
  artifacts/dev/ee_demo.pkl  docs/camp/arm_record.py during `ee_control.py demo` (joint states + TCP from TF)
  artifacts/dev/ik_probe.pkl docs/camp/ik_probe.py (reach grid, distinct IK solutions)
  artifacts/dev/lesson09_shots/ MuJoCo viewer + RViz captures
Robot close-ups are offscreen MuJoCo renders of the recorded /joint_states (same model the bridge runs).
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson08_figures import caption, hstack  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

SHOTS = Path("artifacts/dev/lesson09_shots")
OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100"
DEMO = pickle.load(open("artifacts/dev/ee_demo.pkl", "rb"))
PROBE = pickle.load(open("artifacts/dev/ik_probe.pkl", "rb"))


# ================================================================ offscreen renders of recorded states
class Render:
    def __init__(self, w=640, h=560):
        import mujoco
        self.mj = mujoco
        self.m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
        self.d = mujoco.MjData(self.m)
        self.r = mujoco.Renderer(self.m, h, w)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0
        self.cam = mujoco.MjvCamera()

    def view(self, lookat, distance, azimuth, elevation):
        self.cam.lookat[:] = lookat
        self.cam.distance, self.cam.azimuth, self.cam.elevation = distance, azimuth, elevation

    def set(self, joints):
        for n, v in joints.items():
            self.d.qpos[self.m.joint(n).qposadr[0]] = v
        self.mj.mj_forward(self.m, self.d)

    def image(self, marks=()):
        self.r.update_scene(self.d, self.cam, self.opt)
        for p, rgba in marks:
            s = self.r.scene
            g = s.geoms[s.ngeom]
            self.mj.mjv_initGeom(g, self.mj.mjtGeom.mjGEOM_SPHERE, np.array([0.018, 0, 0]), np.array(p, float),
                                 np.eye(3).flatten(), np.array(rgba, np.float32))
            s.ngeom += 1
        return Image.fromarray(self.r.render())


def state_at(t, data=DEMO):
    s = data["states"]
    k = min(range(len(s)), key=lambda i: abs(s[i]["t"] - t))
    return {n: q for n, q in zip(s[k]["names"], s[k]["positions"]) if "openarm" in n}


def tcp_at(t, side="left"):
    tc = DEMO["tcp"]
    return min(tc, key=lambda r: abs(r["t"] - t))[side]


def finger_min_time():
    s = DEMO["states"]
    f = s[0]["names"].index("openarm_left_finger_joint1")
    return min(s, key=lambda x: x["positions"][f])["t"]


R = None


def renderer():
    global R
    if R is None:
        R = Render()
    return R


FRONT = dict(lookat=[0.22, 0.1, 0.78], distance=1.25, azimuth=270, elevation=-6)


def shot(t, marks=(), view=FRONT):
    r = renderer()
    r.view(**view)
    r.set(state_at(t))
    return r.image(marks)


# sim 시각 (ee_demo.pkl, JointConstraint ±0.001 rad 로 다시 기록): ready 52-55.4, pose 55.6-63.0, 아래 63.0-64.1, 그리퍼 64.1, 위 64.3-65.4
T_TRANSPORT, T_READY, T_POSE_MID, T_POSE, T_DOWN = 51.0, 55.4, 59.0, 63.0, 64.1
T_CLOSED = None


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "⑦ 은 이름 자세(관절값)로 움직였다 → ⑧ 은 손끝(TCP) 위치로 움직인다", bold=True, fs=12)
    tiles(ax, [("관절 공간 (⑦)", ["관절 7 개의 각도를 직접 정한다", "SRDF 이름 자세 · arm 명령", "손이 어디로 갈지는 결과를 봐야 안다"], C["blue"]),
               ("작업 공간 (⑧)", ["손끝 위치 (x, y, z) 를 정한다", "IK 가 관절 7 개로 바꿔 준다", "상자 · 작업대 좌표와 바로 맞물린다"], C["green"]),
               ("그리퍼", ["손가락 간격 하나 (0 ~ 44 mm)", "GripperCommand 액션", "닫힘 · 막힘(stalled) 판정"], C["purple"])],
          cols=3, y_top=3.6, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 0.9, "예제: lessons/05_moveit/ee_control.py  —  where · ik · pose · cartesian · gripper · demo", fs=9.8)
    save(fig, "lesson09_why.png")


def frames():
    """Side (x-z) and top (x-y) views with the real TCP numbers from `where` and the table height."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), dpi=150)
    ax = axes[0]
    ax.add_patch(Rectangle((-0.38, 0.02), 0.76, 0.2, fc="#555555", ec=INK))
    ax.add_patch(Rectangle((-0.04, 0.22), 0.08, 0.82, fc="#9e9e9e", ec=INK))
    ax.add_patch(Rectangle((0.55, 0.0), 0.6, 0.78, fc="#E3F2FD", ec=BLUE, alpha=0.7))
    ax.text(0.85, 0.40, "작업대\n상판 z = 0.78 m", ha="center", fontsize=9.5, color=BLUE)
    for t, name, col in [(T_TRANSPORT, "transport", GREY), (T_READY, "ready", GREEN), (T_POSE, "pose (0.45, 0.20, 0.95)", RED)]:
        p = tcp_at(t)
        ax.plot(p[0], p[2], "o", ms=9, color=col)
        ax.text(p[0] + 0.03, p[2], f"{name}\nx={p[0]:.2f}, z={p[2]:.2f}", fontsize=9, va="center", color=col)
    ax.add_patch(FancyArrowPatch((0, 0), (0.3, 0), arrowstyle="-|>", mutation_scale=15, lw=2, color=RED))
    ax.add_patch(FancyArrowPatch((0, 0), (0, 0.3), arrowstyle="-|>", mutation_scale=15, lw=2, color=BLUE))
    ax.text(0.31, 0.03, "x (앞)", color=RED, fontsize=10)
    ax.text(0.02, 0.31, "z (위)", color=BLUE, fontsize=10)
    ax.set_title("옆에서 본 모습 (x-z) · base_footprint 기준", fontsize=11.5)
    ax.set_xlim(-0.45, 1.2); ax.set_ylim(-0.05, 1.15); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("x [m]"); ax.set_ylabel("z [m]")
    ax = axes[1]
    ax.add_patch(Rectangle((-0.38, -0.32), 0.76, 0.64, fc="#555555", ec=INK, alpha=0.8))
    for side, col in [("left", GREEN), ("right", ORANGE)]:
        sy = 0.093 if side == "left" else -0.093
        ax.plot(0, sy, "s", ms=9, color=col)
        p = tcp_at(T_TRANSPORT, side)
        ax.plot(p[0], p[1], "o", ms=9, color=col)
        ax.text(p[0] + 0.03, p[1], f"{side} TCP\ny={p[1]:+.3f}", fontsize=9, va="center", color=col)
        ax.text(-0.02, sy, f"어깨 y={sy:+.3f}", fontsize=8.5, ha="right", va="center", color="white")
    ax.add_patch(FancyArrowPatch((0, 0), (0.3, 0), arrowstyle="-|>", mutation_scale=15, lw=2, color=RED))
    ax.add_patch(FancyArrowPatch((0, 0), (0, 0.3), arrowstyle="-|>", mutation_scale=15, lw=2, color=GREEN))
    ax.text(0.31, 0.02, "x (앞)", color=RED, fontsize=10)
    ax.text(0.02, 0.31, "y (왼쪽)", color=GREEN, fontsize=10)
    ax.set_title("위에서 본 모습 (x-y) · transport 자세의 두 TCP", fontsize=11.5)
    ax.set_xlim(-0.45, 0.75); ax.set_ylim(-0.45, 0.45); ax.set_aspect("equal"); ax.grid(alpha=0.3)
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    fig.tight_layout()
    save(fig, "lesson09_frames.png")


def grasp():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "자세는 하나로 고정: GRASP_FORWARD (손을 앞으로 뻗어 수평으로 잡기)", bold=True, fs=12)
    tiles(ax, [("손 z 축 (다가가는 방향)", ["→ 로봇 앞 (+x)", "상자 쪽으로 똑바로 들어간다"], C["red"]),
               ("손 y 축 (손가락이 닫히는 방향)", ["→ 로봇 왼쪽 (+y)", "상자 양옆을 집는다"], C["green"]),
               ("손 x 축", ["→ 아래 (-z)", "손등이 위를 향한다"], C["blue"])],
          cols=3, y_top=3.4, gap=0.3, h=1.7, tfs=11, fs=9)
    note(ax, 0.3, 1.1, "그래서 이 페이지의 pose 는 숫자 3 개 (x, y, z) 만 받는다.  쿼터니언은 quat_from_axes() 가 세 축으로 만든다.", fs=9.6)
    note(ax, 0.3, 0.5, "위치 3 + 자세 3 = 6 개 조건,  팔 관절 7 개 → 해가 하나가 아니다 (1 자유도 남음).", fs=9.6)
    save(fig, "lesson09_grasp.png")


def ik_concept():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "IK (/compute_ik): 손끝 자세 → 관절 7 개.  solve_ik() 는 여러 번 풀어 가장 가까운 해를 고른다", bold=True, fs=12)
    chain(ax, [("목표 자세", ["TCP (x, y, z)", "+ GRASP_FORWARD"]), ("seed", ["현재 관절값에서 시작"]), ("KDL 수치 풀이", ["0.2 s 제한", "충돌하는 해는 버림"]),
               ("12 번 반복", ["ik_attempts: 12", "성공한 해 모으기"]), ("가장 가까운 해", ["|해 - 현재| 최소", "→ 팔이 덜 휘두른다"])],
          y=1.2, h=1.8, gap=0.25, colors=[C["purple"], C["grey"], C["yellow"], C["orange"], C["green"]], tfs=10.4, fs=8.4)
    note(ax, 0.3, 0.5, "해가 하나도 없으면 SkillError: No IK solution  (손이 닿지 않거나, 닿아도 부딪히는 자리).", fs=9.5)
    save(fig, "lesson09_ik_concept.png")


def ik_multi():
    r = renderer()
    r.view(lookat=[0.25, 0.1, 0.85], distance=1.05, azimuth=250, elevation=-10)
    base = state_at(T_TRANSPORT)
    imgs = []
    for k, q in enumerate(PROBE["multi"][:4]):
        j = dict(base)
        j.update({f"openarm_left_joint{i + 1}": v for i, v in enumerate(q)})
        r.set(j)
        img = r.image([((0.45, 0.20, 0.95), (1, 0.1, 0.1, 1))])
        imgs.append(caption(img, f"해 {k + 1}", f"joint1 {q[0]:+.2f} · joint3 {q[2]:+.2f} · joint7 {q[6]:+.2f} rad"))
    hstack(imgs).save(OUT / "lesson09_ik_multi.png")
    print("saved lesson09_ik_multi.png")


def reach():
    fig, ax = plt.subplots(figsize=(14, 6.0), dpi=150)
    xs, zs, ok = PROBE["xs"], PROBE["zs"], PROBE["reach"]
    st = PROBE["xs"][1] - PROBE["xs"][0]
    ax.imshow(ok, origin="lower", extent=[xs[0] - st / 2, xs[-1] + st / 2, zs[0] - st / 2, zs[-1] + st / 2],
              cmap=ListedColormap(["#FFE0E0", "#C8E6C9"]), aspect="equal", alpha=0.95)
    ax.axhline(0.78, color=BLUE, lw=1.5, ls="--")
    ax.text(0.16, 0.795, "작업대 상판 0.78 m", color=BLUE, fontsize=9.5)
    ax.plot(0.45, 0.95, "o", ms=12, color=GREEN, mec=INK)
    ax.text(0.44, 1.01, "0.45 → 성공", fontsize=10, color=GREEN, fontweight="bold", ha="right")
    ax.plot(0.65, 0.95, "X", ms=13, color=RED, mec=INK)
    ax.text(0.66, 0.89, "0.65 → No IK solution", fontsize=10, color=RED, fontweight="bold")
    ax.set_xlabel("x [m] (앞)")
    ax.set_ylabel("z [m] (위)")
    ax.set_title(f"왼팔 도달 범위: y = {PROBE['y']:.2f} m, GRASP_FORWARD, 충돌 검사 포함 (초록 = IK 해 있음, {st * 100:.0f} cm 격자, /compute_ik 실측)", fontsize=11)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save(fig, "lesson09_reach.png")


def pose_vs_cart():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "손을 옮기는 두 가지 방법", bold=True, fs=12)
    tiles(ax, [("pose goal = IK + 관절 공간 계획", ["move_pose(): solve_ik → move_joints", "OMPL 이 관절 공간에서 길을 찾는다", "손끝 경로는 곡선 (멀리 돌 수 있음)", "먼 이동 · 장애물 피하기에 알맞다"], C["blue"]),
               ("Cartesian path = 손끝 직선", ["move_cartesian(): /compute_cartesian_path", "1 cm (cartesian_step) 마다 IK 를 이어 붙인다", "손끝이 직선을 따른다", "fraction < 90 % 면 실행하지 않는다"], C["green"])],
          cols=2, y_top=3.6, gap=0.4, h=2.6, tfs=11.5, fs=9.2)
    note(ax, 0.3, 0.55, "pick & place: 작업대 앞까지는 pose goal, 상자에 내려가고 올라오는 마지막 몇 cm 는 Cartesian.", fs=9.8)
    save(fig, "lesson09_pose_vs_cart.png")


def tcp_path():
    tc = DEMO["tcp"]
    t = np.array([r["t"] for r in tc])
    p = np.array([r["left"] for r in tc])
    segs = [("named ready", 51.5, 55.5, GREY), ("pose (관절 공간 계획)", 55.5, 63.05, BLUE),
            ("cartesian 0 0 -0.05", 63.05, 64.12, GREEN), ("cartesian 0 0 +0.05", 64.3, 65.5, ORANGE)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4), dpi=150)
    for ax, (i, j, xl, yl, title) in zip(axes, [(1, 2, "y [m] (왼쪽)", "z [m]", "앞에서 본 손끝 경로 (y-z)"), (0, 1, "x [m] (앞)", "y [m]", "위에서 본 손끝 경로 (x-y)")]):
        for name, a, b, col in segs:
            m = (t >= a) & (t <= b)
            ax.plot(p[m, i], p[m, j], "-", color=col, lw=2.6, label=name)
            ax.plot(p[m, i][-1], p[m, j][-1], "o", color=col, ms=6)
        ax.plot(0.20 if i == 1 else 0.45, 0.95 if j == 2 else 0.20, "*", ms=16, color=RED, mec=INK, label="pose 목표")
        ax.set_title(title, fontsize=11.5)
        ax.set_xlabel(xl); ax.set_ylabel(yl)
        ax.set_aspect("equal"); ax.grid(alpha=0.3)
        if i == 1:
            ax.invert_xaxis()
    axes[0].legend(loc="lower left", fontsize=9)
    ymax = p[(t > 55.5) & (t < 63.05), 1].max()
    fig.suptitle(f"demo 왼손 TCP 실측 (TF): pose 는 y 가 {ymax:.2f} m 까지 돌아서 가고, cartesian 은 x · y 가 그대로인 직선", fontsize=12, fontweight="bold")
    fig.tight_layout()
    save(fig, "lesson09_tcp_path.png")


# pose left 0.45 0.20 0.95 를 ready 에서 반복한 실측 TCP 오차 [mm] (2026-10-02, ee_control.py 출력)
ERR_001 = [12.2, 3.5, 2.3, 3.3, 5.6, 6.3, 9.1]      # JointConstraint ±0.01 rad (이전 설정)
ERR_0001 = [0.8, 1.1, 0.8, 1.0, 1.5, 1.3, 1.3]      # ±0.001 rad (지금 설정)


def pose_error():
    fig, ax = plt.subplots(figsize=(14, 4.6), dpi=150)
    k = np.arange(1, len(ERR_001) + 1)
    ax.bar(k - 0.2, ERR_001, 0.38, color="#EF9A9A", ec=INK, label="tolerance ± 0.01 rad (이전)")
    ax.bar(k + 0.2, ERR_0001, 0.38, color="#81C784", ec=INK, label="tolerance ± 0.001 rad (지금)")
    for x, v in zip(k, ERR_001):
        ax.text(x - 0.2, v + 0.2, f"{v:.1f}", ha="center", fontsize=9)
    for x, v in zip(k, ERR_0001):
        ax.text(x + 0.2, v + 0.2, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(k, [f"{i} 회" for i in k])
    ax.set_ylabel("TCP 오차 [mm]")
    ax.set_title(f"pose left 0.45 0.20 0.95 반복 실측: ± 0.01 rad 평균 {np.mean(ERR_001):.1f} mm → ± 0.001 rad 평균 {np.mean(ERR_0001):.1f} mm  (MuJoCo 추종은 둘 다 0.005 rad 안)", fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=9.5)
    fig.tight_layout()
    save(fig, "lesson09_pose_error.png")


def gripper_plot():
    s = DEMO["states"]
    n = s[0]["names"]
    f = n.index("openarm_left_finger_joint1")
    t = np.array([x["t"] for x in s])
    q = np.array([x["positions"][f] for x in s]) * 1000
    t0 = t[np.nonzero(np.abs(np.diff(q)) > 0.05)[0][0]]
    m = (t > t0 - 0.06) & (t < t0 + 0.2)
    fig, ax = plt.subplots(figsize=(14, 4.2), dpi=150)
    ax.plot((t[m] - t0) * 1000, q[m], "o-", color=BLUE, lw=2, ms=4, label="openarm_left_finger_joint1 (/joint_states, 50 Hz)")
    ax.axhline(44, color=GREEN, ls="--", lw=1.2); ax.text(150, 45.5, "open 목표 0.044 m", color=GREEN, fontsize=9.5)
    ax.axhline(12, color=RED, ls="--", lw=1.2); ax.text(150, 13.5, "close 목표 0.012 m", color=RED, fontsize=9.5)
    ax.set_xlabel("닫기 시작부터 시간 [ms] (sim time)")
    ax.set_ylabel("손가락 간격 [mm]")
    ax.set_title(f"gripper close → open (물건 없음): {q[m][0]:.0f} mm 에서 닫기 → 최저 {q[m].min():.1f} mm 에서 reached → 열기 {q[m][-1]:.1f} mm.  kp 1800, 힘 25 N", fontsize=11.5)
    ax.set_ylim(0, 50); ax.grid(alpha=0.3); ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    save(fig, "lesson09_gripper.png")


def gripper_concept():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "그리퍼 액션 (GripperCommand): 언제 끝나나", bold=True, fs=12)
    tiles(ax, [("reached", ["|간격 - 목표| < 2 mm", "물건이 없을 때 (close 12 mm)"], C["green"]),
               ("stalled", ["1 s 동안 0.1 mm 도 안 움직임", "물건을 쥐었을 때 → 성공으로 끝냄"], C["orange"]),
               ("abort", ["6 s 지나도 둘 다 아님"], C["red"])],
          cols=3, y_top=3.2, gap=0.3, h=1.6, tfs=11, fs=9)
    note(ax, 0.3, 1.0, "ee_control.py: OPEN 0.044 · CLOSE 0.012 · EFFORT 25 N.  브리지가 액추에이터 forcerange 를 effort 로 바꾼다 (최대 30 N).", fs=9.5)
    note(ax, 0.3, 0.45, "⑨ 에서 상자(폭 45 mm)를 쥐면 간격이 상자 폭에서 멈추고 stalled = True 가 된다.", fs=9.5)
    save(fig, "lesson09_gripper_concept.png")


# ================================================================ 2. 실행 화면
def screen(mj, rv, out, rv_crop=(895, 62, 2150, 862)):
    a = Image.open(SHOTS / mj).convert("RGB")
    b = Image.open(SHOTS / rv).convert("RGB").crop(rv_crop)
    b = b.resize((int(b.width * a.height / b.height), a.height))
    hstack([a, b], gap=12).save(OUT / out)
    print("saved", out)


def pair(t1, t2, out, c1, c2, marks2=(), view=FRONT, marks1=()):
    hstack([caption(shot(t1, marks1, view=view), c1), caption(shot(t2, marks2, view=view), c2)], gap=24).save(OUT / out)
    print("saved", out)


def finger(t):
    return state_at(t)["openarm_left_finger_joint1"] * 1000


def gripper_pair():
    t_closed = finger_min_time()
    s = [x for x in DEMO["states"] if x["t"] > t_closed]
    f = s[0]["names"].index("openarm_left_finger_joint1")
    t_open = next(x["t"] for x in s if x["positions"][f] > 0.0435)        # close 다음 open 이 끝난 순간 (팔은 아직 아래)
    view = dict(lookat=list(tcp_at(T_DOWN)), distance=0.38, azimuth=180, elevation=-35)
    pair(t_closed, t_open, "lesson09_run_gripper.png", f"close: {finger(t_closed):.1f} mm", f"open: {finger(t_open):.1f} mm", view=view)


def ee_flow():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "ee_control.py 명령 → MoveItClient 함수 → MoveIt / 브리지 인터페이스", bold=True, fs=12)
    rows = [("where", "tf.lookup_transform", "TF base_footprint → *_hand_tcp"), ("ik", "solve_ik", "서비스 /compute_ik"),
            ("pose", "move_pose = solve_ik + move_joints", "액션 /move_action (MoveGroup)"), ("cartesian", "move_cartesian", "/compute_cartesian_path + /execute_trajectory"),
            ("gripper", "gripper", "액션 /left_gripper_controller/gripper_cmd")]
    for k, (c, fn, it) in enumerate(rows):
        y = 3.45 - k * 0.68
        rbox(ax, 0.3, y, 2.0, 0.55, c, fc=C["orange"], tfs=10)
        arrow(ax, (2.3, y + 0.27), (2.8, y + 0.27))
        rbox(ax, 2.8, y, 4.9, 0.55, fn, fc=C["yellow"], tfs=9.6)
        arrow(ax, (7.7, y + 0.27), (8.2, y + 0.27))
        rbox(ax, 8.2, y, 5.5, 0.55, it, fc=C["teal"], tfs=9.2)
    note(ax, 0.3, 0.25, "MoveItClient = warehouse_skills/moveit_client.py.  ⑨ 의 pick & place 스킬도 같은 함수를 쓴다.", fs=9.5)
    save(fig, "lesson09_ee_flow.png")


def params():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "skills.yaml 의 moveit: 블록 (MoveItClient 가 읽는 값)", bold=True, fs=12)
    tiles(ax, [("계획", ["planning_time: 5.0 s", "attempts: 4"], C["yellow"]),
               ("속도 · 가속 배율", ["velocity_scaling: 0.35", "acceleration_scaling: 0.35"], C["blue"]),
               ("IK", ["ik_attempts: 12", "(한 번 0.2 s 제한)"], C["orange"]),
               ("Cartesian", ["cartesian_step: 0.01 m", "cartesian_min_fraction: 0.9"], C["green"])],
          cols=4, y_top=3.6, gap=0.25, h=1.7, tfs=11, fs=9)
    note(ax, 0.3, 1.2, "파일: src/warehouse_skills/config/skills.yaml  (arms: 블록 = 팔마다 group · tcp_link · gripper 이름)", fs=9.5)
    note(ax, 0.3, 0.6, "arm 명령(⑦ joint_goal.py) 은 배율 0.3 고정,  ee_control.py · pick & place 는 이 파일의 0.35.", fs=9.5)
    save(fig, "lesson09_params.png")


if __name__ == "__main__":
    why(); frames(); grasp(); ik_concept(); ik_multi(); reach(); pose_vs_cart(); tcp_path(); pose_error(); gripper_plot(); gripper_concept()
    screen("mj_start.png", "rv_start.png", "lesson09_run_result.png")
    pair(T_TRANSPORT, T_READY, "lesson09_run_ready.png", "보내기 전: transport", "named both ready 뒤")
    pair(T_READY, T_POSE, "lesson09_run_pose.png", "보내기 전: ready", "pose left 0.45 0.20 0.95 뒤 (빨간 점 = 목표)",
         marks2=[((0.45, 0.20, 0.95), (1, 0.1, 0.1, 1))])
    pair(T_POSE, T_DOWN, "lesson09_run_cart.png", "보내기 전 (빨간 점 = 시작 TCP)", "cartesian left 0 0 -0.05 뒤 (손이 빨간 점 5 cm 아래)",
         marks1=[(tcp_at(T_POSE), (1, 0.1, 0.1, 1))], marks2=[(tcp_at(T_POSE), (1, 0.1, 0.1, 1))])
    gripper_pair()
    ee_flow(); params()
