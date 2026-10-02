"""Figures for the lesson-08 Confluence page (MoveIt + MuJoCo). Output: docs/camp/lesson08_*.png

Run from the workspace root with the workspace venv (needs mujoco):
    .venv-mobile-openarm/bin/python docs/camp/draw_lesson08_figures.py
Screen captures come from artifacts/dev/lesson08_shots/ (MuJoCo viewer + RViz, 2026-10-02, moveit mode).
The trajectory graph reads artifacts/dev/arm_ready.pkl (docs/camp/arm_record.py during `arm both ready`).
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

SHOTS = Path("artifacts/dev/lesson08_shots")
OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e"
FONT = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"


# ================================================================ 1. MoveIt 이란
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "⑥ 까지는 바퀴를 움직였다 → ⑦ 부터는 팔을 움직인다", bold=True, fs=12)
    chain(ax, [("목표", ["이름 자세 · 손 위치"]), ("IK", ["손 위치 → 관절 7 개"]), ("경로 계획", ["OMPL: 부딪히지 않는 길"]),
               ("시간 붙이기", ["속도 · 가속 한계 안에서"]), ("실행", ["컨트롤러가 관절을 따라 움직임"])],
          y=1.4, h=1.7, gap=0.3, colors=[C["purple"], C["orange"], C["yellow"], C["blue"], C["green"]], tfs=11, fs=8.8)
    note(ax, 0.3, 0.6, "MoveIt = 이 과정을 move_group 노드 하나가 맡는 ROS 2 표준 팔 계획 스택.  실행만 MuJoCo 브리지가 한다.", fs=9.8)
    save(fig, "lesson08_why.png")


def architecture():
    fig, ax = fig_ax(14, 6.6)
    note(ax, 0.3, 6.3, "MoveIt 구성: move_group 이 계획하고, 브리지가 MuJoCo 에서 실행한다", bold=True, fs=12)
    # inputs
    ax.add_patch(Rectangle((0.3, 0.5), 3.2, 5.3, fc="#F7F4FB", ec="#9C89C9", lw=1.1, zorder=1))
    note(ax, 0.45, 5.55, "설정 (config/)", bold=True, fs=10, color="#5E35B1")
    for k, (t, s) in enumerate([("URDF", "링크 · 관절 · 충돌 메시"), ("SRDF", "그룹 · 이름 자세"), ("kinematics.yaml", "KDL IK"),
                                ("joint_limits.yaml", "속도 · 가속 한계"), ("ompl_planning.yaml", "RRTConnect")]):
        rbox(ax, 0.45, 4.5 - k * 0.96, 2.9, 0.88, t, [s], fc=C["purple"], tfs=9.4, fs=7.8)
    arrow(ax, (3.5, 3.3), (4.2, 3.3))
    rbox(ax, 4.2, 1.9, 3.3, 2.8, "move_group", ["MoveGroup 액션 /move_action", "IK 서비스 /compute_ik", "직선 경로 /compute_cartesian_path",
                                                "Planning Scene 유지"], fc=C["yellow"], tfs=11.5, fs=8.4, dy=0.36)
    rbox(ax, 4.2, 0.5, 3.3, 1.05, "warehouse_scene", ["선반 · 작업대 · 상자 → 장애물"], fc=C["grey"], tfs=9.6, fs=8)
    arrow(ax, (5.85, 1.55), (5.85, 1.9))
    rbox(ax, 4.2, 5.05, 3.3, 0.95, "요청하는 쪽", ["arm 명령 · RViz 패널 · ee_control.py"], fc=C["orange"], tfs=9.6, fs=8)
    arrow(ax, (5.85, 5.05), (5.85, 4.7))
    arrow(ax, (7.5, 3.3), (8.4, 3.3))
    label(ax, 7.95, 3.6, "궤적", fs=8.4)
    ax.add_patch(Rectangle((8.4, 0.9), 5.3, 4.9, fc="#EEF8F7", ec="#5AA9A0", lw=1.1, zorder=1))
    note(ax, 8.55, 5.55, "MuJoCo 브리지 (mobile_openarm_mujoco)", bold=True, fs=10, color="#00695C")
    for k, t in enumerate(["/left_joint_trajectory_controller/follow_joint_trajectory", "/right_joint_trajectory_controller/follow_joint_trajectory",
                           "/left_gripper_controller/gripper_cmd", "/right_gripper_controller/gripper_cmd"]):
        rbox(ax, 8.55, 4.6 - k * 0.72, 5.0, 0.6, t, fc=C["teal"], tfs=7.9)
    rbox(ax, 8.55, 1.05, 5.0, 0.95, "MuJoCo position 액추에이터", ["관절 목표값 → 물리 계산 → /joint_states"], fc=C["green"], tfs=9.6, fs=8)
    arrow(ax, (11.05, 2.45), (11.05, 2.0))
    ax.plot([11.05, 11.05, 6.6], [1.05, 0.25, 0.25], color=GREEN, lw=1.4)
    arrow(ax, (6.6, 0.25), (6.6, 0.5), color=GREEN, lw=1.4)
    label(ax, 9.3, 0.25, "/joint_states (현재 관절)", color=GREEN, fs=8.4)
    save(fig, "lesson08_architecture.png")


def groups():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "Planning Group: MoveIt 이 한 번에 계획하는 관절 묶음 (SRDF)", bold=True, fs=12)
    tiles(ax, [("left_arm", ["openarm_left_joint1 ~ 7", "관절 7 개 (7 자유도)", "IK: KDL"], C["blue"]),
               ("right_arm", ["openarm_right_joint1 ~ 7", "관절 7 개", "왼팔과 거울 대칭"], C["orange"]),
               ("both_arms", ["left_arm + right_arm", "관절 14 개를 한 번에", "두 팔이 같이 움직임"], C["green"]),
               ("left · right_gripper", ["finger_joint1 1 개", "finger_joint2 는 따라 움직임", "(passive · mimic)"], C["purple"])],
          cols=4, y_top=4.1, gap=0.25, h=2.2, tfs=11, fs=8.7)
    note(ax, 0.3, 1.2, "end_effector: left_ee · right_ee (부모 링크 openarm_*_hand).  손끝 기준점(TCP) = openarm_*_hand_tcp", fs=9.5)
    note(ax, 0.3, 0.6, "virtual_joint odom_joint (planar): 베이스는 MoveIt 이 움직이지 않는다.  주행은 Nav2, 팔은 MoveIt.", fs=9.5)
    save(fig, "lesson08_groups.png")


def crop_robot(path, box=(300, 60, 820, 700)):
    return Image.open(path).convert("RGB").crop(box)


def caption(img, text, sub=""):
    w, h = img.size
    out = Image.new("RGB", (w, h + 78), "white")
    out.paste(img, (0, 78))
    d = ImageDraw.Draw(out)
    d.text((w // 2, 24), text, fill=INK, font=ImageFont.truetype(FONT, 28), anchor="mm")
    if sub:
        d.text((w // 2, 58), sub, fill="#555555", font=ImageFont.truetype(FONT.replace("Bold", ""), 20), anchor="mm")
    return out


def hstack(images, gap=16, bg="white"):
    h = max(i.height for i in images)
    out = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), h), bg)
    x = 0
    for i in images:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def named_poses():
    items = [("transport", "주행 자세 · joint4 = 1.2", "mj_transport.png"), ("ready", "작업 준비 · joint4 = 1.65", "mj_ready.png"),
             ("hands_up", "joint4 = 2.0", "mj_hands_up.png"), ("home", "모든 관절 0", "mj_home.png")]
    hstack([caption(crop_robot(SHOTS / f), t, s) for t, s, f in items]).save(OUT / "lesson08_named_poses.png")
    print("saved lesson08_named_poses.png")


def scene():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "Planning Scene: MoveIt 이 아는 장애물 = MuJoCo 창고를 옮겨 놓은 것", bold=True, fs=12)
    chain(ax, [("창고 정의", ["warehouse.yaml: 선반 · 작업대", "상자 크기 · 위치"]), ("MuJoCo 상자 위치", ["/warehouse/object_poses", "(움직인 상자도 따라감)"]),
               ("warehouse_scene", ["0.5 s 마다 BOX 장애물 생성", "odom 기준, 오도메트리 오차 보정"]), ("/apply_planning_scene", ["move_group 의 Planning Scene"]),
               ("계획 · RViz", ["부딪히는 경로는 버린다", "RViz 의 초록 상자"])],
          y=1.3, h=1.9, gap=0.25, colors=[C["purple"], C["teal"], C["grey"], C["yellow"], C["green"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.6, "집은 상자는 /warehouse_scene/attached 로 알려 주면 장애물에서 빠지고 손에 붙는다 (⑨ Pick & Place).", fs=9.5)
    save(fig, "lesson08_scene.png")


def exec_flow():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "계획에서 실행까지: MoveGroup 요청 하나가 MuJoCo 관절 움직임이 되기까지", bold=True, fs=12)
    items = [("MoveGroup 요청", "group · 목표 관절값"), ("OMPL", "RRTConnect: 충돌 없는 경로"), ("시간 붙이기", "TOTG: 속도 · 가속 한계"),
             ("실행 관리자", "컨트롤러 이름으로 분배"), ("FollowJointTrajectory", "왼팔 · 오른팔 액션"), ("브리지 goal()", "관절 이름 · 한계 · 정지 검사"),
             ("브리지 update()", "매 스텝 궤적 보간"), ("position 액추에이터", "kp 500 · kv 35"), ("결과", "목표 ± 0.035 rad → 성공")]
    from draw_intro_figures import flow_rows
    flow_rows(ax, [(t, s) for t, s in items], per_row=5, y_top=4.2, h=1.35, gap=0.25, row_gap=0.6,
              colors=[C["orange"], C["yellow"], C["yellow"], C["yellow"], C["teal"], C["teal"], C["teal"], C["green"], C["green"]], tfs=10, fs=8.2)
    note(ax, 0.3, 0.35, "노란색 = move_group 안,  청록 · 초록 = MuJoCo 브리지 안 (같은 프로세스의 물리 스레드).", fs=9.4)
    save(fig, "lesson08_exec_flow.png")


# ================================================================ 2. 실행
def moveit_tree():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "./scripts/mobile_openarm moveit  =  warehouse.launch.py mode:=drive moveit:=true", bold=True, fs=12)
    rbox(ax, 0.3, 1.8, 2.8, 1.4, "warehouse.launch.py", ["mode:=drive"], fc=C["purple"], tfs=10.2, fs=8.6)
    items = [("브리지", "MuJoCo + 액션 4 개", C["teal"]), ("RSP", "로봇 TF", C["blue"]), ("move_group", "계획 · 실행", C["yellow"]),
             ("warehouse_scene", "장애물", C["grey"]), ("RViz2", "MotionPlanning", C["grey"])]
    for k, (t, l, fc) in enumerate(items):
        x = 3.7 + k * 2.0
        rbox(ax, x, 1.8, 1.85, 1.4, t, [l], fc=fc, tfs=9.6, fs=7.8)
        arrow(ax, (x + 0.92, 3.6), (x + 0.92, 3.2))
    ax.plot([3.1, 3.4], [2.5, 2.5], color=INK, lw=1.6); ax.plot([3.4, 3.4], [2.5, 3.6], color=INK, lw=1.6)
    ax.plot([3.4, 3.7 + 4 * 2.0 + 0.92], [3.6, 3.6], color=INK, lw=1.6)
    ax.add_patch(Rectangle((3.7 + 2 * 2.0 - 0.08, 1.7), 2.0 * 3 - 0.0, 1.6, fc="none", ec=RED, lw=1.5, ls="--"))
    label(ax, 3.7 + 3 * 2.0 + 0.85, 1.4, "moveit.launch.py 가 붙이는 것 (moveit:=true)", color=RED, fs=9)
    note(ax, 0.3, 0.7, "지도 · AMCL · Nav2 는 없다 (mode:=drive).  팔만 볼 때 가볍게 띄우는 조합.", fs=9.4)
    note(ax, 0.3, 0.25, "start (= nav) 도 moveit:=true 가 기본 → Nav2 + MoveIt 이 함께 뜬다 (Day 2 후반).", fs=9.4)
    save(fig, "lesson08_moveit_tree.png")


def screen(mj, rv, out, rv_crop=None):
    a = Image.open(SHOTS / mj).convert("RGB")
    b = Image.open(SHOTS / rv).convert("RGB")
    if rv_crop:
        b = b.crop(rv_crop)
    b = b.resize((int(b.width * a.height / b.height), a.height))
    hstack([a, b], gap=12).save(OUT / out)
    print("saved", out)


def before_after(left, right, out, t1, t2, box=(250, 40, 870, 760)):
    hstack([caption(crop_robot(SHOTS / left, box), t1), caption(crop_robot(SHOTS / right, box), t2)], gap=24).save(OUT / out)
    print("saved", out)


def traj():
    d = pickle.load(open("artifacts/dev/arm_ready.pkl", "rb"))
    plan = d["plans"][0]
    states = d["states"]
    names = states[0]["names"]
    t = np.array([s["t"] for s in states])
    pt = np.array(plan["times"])
    pq = np.array(plan["positions"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
    for ax, side in zip(axes, ["left", "right"]):
        n = f"openarm_{side}_joint4"
        q = np.array([s["positions"][names.index(n)] for s in states])
        qp = pq[:, plan["names"].index(n)]
        moving = np.nonzero(np.abs(q - q[0]) > 0.002)[0][0]
        # MoveIt 의 계획 시각 0 = 실제로 움직이기 시작한 순간 근처: 계획 곡선에 가장 잘 맞는 시작 시각을 찾는다
        best = min(np.arange(t[moving] - 0.5, t[moving] + 0.2, 0.002),
                   key=lambda t0: np.sum((np.interp(t[(t > t0) & (t < t0 + pt[-1])] - t0, pt, qp) - q[(t > t0) & (t < t0 + pt[-1])]) ** 2))
        sel = (t > best - 0.5) & (t < best + pt[-1] + 1.0)
        ax.plot(t[sel] - best, q[sel], color=BLUE, lw=2.2, label="MuJoCo 실제 관절 (/joint_states)")
        ax.plot(pt, qp, "o--", color=RED, ms=5, lw=1.2, label=f"MoveIt 계획 (점 {len(pt)} 개)")
        err = np.abs(np.interp(pt, t - best, q) - qp).max()
        ax.set_title(f"{side}_arm joint4 : 1.2 → 1.65 rad  (계획 {pt[-1]:.2f} s, 최대 차이 {err:.3f} rad)", fontsize=11)
        ax.set_xlabel("계획 시작부터 시간 [s]")
        ax.set_ylabel("관절 각도 [rad]")
        ax.grid(alpha=0.3)
        ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    save(fig, "lesson08_traj.png")


def rviz_steps():
    a = Image.open(SHOTS / "drop_c.png").convert("RGB").crop((0, 40, 880, 500))
    b = Image.open(SHOTS / "rv_plan.png").convert("RGB").crop((0, 270, 870, 680))
    hstack([caption(a, "① Goal State 고르기", "이름 자세 = SRDF group_state"),
            caption(b.resize((int(b.width * a.height / b.height), a.height)), "② Plan → ③ Execute", "Time: 0.030 s 계획 · Executed")],
           gap=24).save(OUT / "lesson08_rviz_panel.png")
    print("saved lesson08_rviz_panel.png")


# ================================================================ 3. 계획은 됐는데 실행 실패
def home_hull():
    import mujoco
    from scipy.spatial import ConvexHull
    m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
    d = mujoco.MjData(m)
    for s in ["left", "right"]:
        for i in range(1, 8):
            d.qpos[m.joint(f"openarm_{s}_joint{i}").qposadr[0]] = 0.0
    mujoco.mj_forward(m, d)

    def world(g):
        mid = m.geom_dataid[g]
        a, n = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        v = m.mesh_vert[a:a + n]
        return v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]

    def tris(g):
        mid = m.geom_dataid[g]
        a, n = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        return world(g)[m.mesh_face[a:a + n]]

    def collision_geom(body):
        return [g for g in range(m.ngeom) if m.body(m.geom_bodyid[g]).name == body and m.geom_contype[g]][0]

    body = collision_geom("openarm_body_link0")
    hands = [collision_geom(f"openarm_{s}_hand") for s in ["left", "right"]]
    contacts = [c for c in d.contact[:d.ncon] if {c.geom1, c.geom2} & {body} and {c.geom1, c.geom2} & set(hands)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.0), dpi=150)
    for ax, title, hull in zip(axes, ["MoveIt (FCL): 메시 그대로", "MuJoCo: 메시마다 볼록 껍질(convex hull)"], [False, True]):
        for g, col in [(body, GREY)] + [(h, BLUE) for h in hands]:
            if hull:
                p = world(g)[:, 1:]
                hp = ConvexHull(p)
                ax.add_patch(Polygon(p[hp.vertices], closed=True, fc=col, ec=INK, alpha=0.45, lw=1))
            else:
                for tri in tris(g):
                    ax.add_patch(Polygon(tri[:, 1:], closed=True, fc=col, ec="none", alpha=0.35))
        if hull:
            for c in contacts:
                ax.plot(c.pos[1], c.pos[2], "o", ms=14, mfc="none", mec=RED, mew=2.5)
            label(ax, 0.0, 0.30, f"닿음: 겹침 {abs(contacts[0].dist) * 100:.1f} cm", color=RED, fs=10)
        ax.set_title(title, fontsize=12)
        ax.set_xlim(0.3, -0.3)
        ax.set_ylim(0.2, 0.85)
        ax.set_aspect("equal")
        ax.set_xlabel("y [m]  (로봇 정면에서 본 모습)")
        ax.set_ylabel("z [m]")
        ax.grid(alpha=0.3)
    fig.suptitle("home 자세(관절 0)에서 몸통(회색)과 두 손(파랑): 같은 STL 인데 충돌 모양이 다르다", fontsize=12.5, fontweight="bold")
    fig.tight_layout()
    save(fig, "lesson08_home_hull.png")


def home_why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "home: MoveIt 은 성공, MuJoCo 는 실패 (CONTROL_FAILED, error_code -4)", bold=True, fs=12)
    chain(ax, [("MoveIt 계획", ["실제 몸통 기둥은 폭 6 cm", "손과 안 닿음 → 충돌 아님"]), ("브리지 실행", ["궤적대로 관절 목표를 보낸다"]),
               ("MuJoCo 물리", ["몸통 = 어깨까지 감싼 볼록 껍질", "손이 껍질에 걸려 멈춤"]), ("목표 판정", ["3 s 안에 ± 0.035 rad 못 옴", "GOAL_TOLERANCE_VIOLATED"]),
               ("MoveIt 결과", ["ABORTED → CONTROL_FAILED", "팔은 그 자리에서 멈춤"])],
          y=1.3, h=1.8, gap=0.25, colors=[C["yellow"], C["teal"], C["green"], C["red"], C["red"]], tfs=10.4, fs=8.4)
    note(ax, 0.3, 0.6, "교훈: 계획용 모델과 물리 모델은 다르다 → 쓰는 자세는 실제 시뮬레이터에서 한 번씩 실행해 확인한다.", fs=9.8)
    save(fig, "lesson08_home_why.png")


# ================================================================ 4. 코드
def joint_goal_flow():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "arm 명령 (joint_goal.py): SRDF 이름 자세 → MoveGroup 액션", bold=True, fs=12)
    chain(ax, [("SRDF 읽기", ["group_state 의 관절값"]), ("ActionClient", ["/move_action (MoveGroup)"]), ("Goal 만들기", ["group_name", "JointConstraint ± 0.01"]),
               ("옵션", ["속도 · 가속 배율 0.3", "plan_only = False"]), ("결과", ["status 4 · error_code 1", "= SUCCEEDED · SUCCESS"])],
          y=1.2, h=1.8, gap=0.25, colors=[C["purple"], C["grey"], C["orange"], C["yellow"], C["green"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.5, "실행 파일 이름 joint_goal: mobile_openarm_moveit_config 의 setup.py.  wrapper 의 arm 이 ros2 run 으로 부른다.", fs=9.4)
    save(fig, "lesson08_joint_goal_flow.png")


def controllers():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "moveit_controllers.yaml: 컨트롤러 이름 + action_ns = 브리지 액션 이름", bold=True, fs=12)
    rows = [("left_joint_trajectory_controller", "follow_joint_trajectory", "FollowJointTrajectory · 관절 7"),
            ("left_gripper_controller", "gripper_cmd", "GripperCommand · finger_joint1")]
    for k, (n, ns, typ) in enumerate(rows):
        y = 2.7 - k * 1.3
        rbox(ax, 0.3, y, 4.3, 0.95, n, [typ], fc=C["yellow"], tfs=9.6, fs=8)
        rbox(ax, 5.2, y, 2.4, 0.95, ns, ["action_ns"], fc=C["grey"], tfs=9.6, fs=8)
        arrow(ax, (7.6, y + 0.47), (8.3, y + 0.47))
        rbox(ax, 8.3, y, 5.4, 0.95, f"/{n}/{ns}", ["브리지 Controllers 가 만든 액션 서버"], fc=C["teal"], tfs=8.6, fs=8)
        note(ax, 4.75, y + 0.47, "+", bold=True, fs=13)
    note(ax, 0.3, 0.75, "오른쪽도 같다 (right_*).  이름이 하나라도 다르면 MoveIt 은 실행할 컨트롤러를 못 찾는다.", fs=9.5)
    note(ax, 0.3, 0.3, "moveit_manage_controllers: False → MoveIt 은 컨트롤러를 켜고 끄지 않고, 있는 액션에 보내기만 한다.", fs=9.5)
    save(fig, "lesson08_controllers.png")


def bridge_goal():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "브리지 액션 서버: 받기 전에 검사 (goal) → 매 물리 스텝 따라가기 (update)", bold=True, fs=12)
    chain(ax, [("거부 조건", ["이미 실행 중 · 베이스가 움직이는 중"]), ("궤적 검사", ["관절 이름이 정확히 같은가", "시간 증가 · 한계 ± 0.02"]),
               ("수락", ["베이스 정지 명령", "reserved 에 등록"]), ("update()", ["궤적 보간 → set_targets", "0.05 s 마다 feedback"]),
               ("끝", ["목표 ± 0.035 rad → succeed", "+3 s 넘으면 abort"])],
          y=1.2, h=1.8, gap=0.25, colors=[C["red"], C["yellow"], C["green"], C["teal"], C["blue"]], tfs=10.2, fs=8.2)
    note(ax, 0.3, 0.5, "goal() 은 ROS 실행기 스레드, update() 는 물리 루프가 매 스텝 부른다 → MuJoCo 데이터는 물리 스레드만 만진다.", fs=9.4)
    save(fig, "lesson08_bridge_goal.png")


def hermite():
    fig, ax = plt.subplots(figsize=(14, 4.4), dpi=150)
    # 개념도: 궤적 점 4 개 (MoveIt 궤적은 0.1 s 간격 점 21 개라 직선과 곡선이 거의 겹친다)
    pt = np.array([0.0, 1.0, 2.0, 3.0])
    qp = np.array([0.0, 0.6, 1.6, 2.0])
    v = np.array([0.0, 0.8, 0.7, 0.0])
    tt = np.linspace(0, pt[-1], 600)
    i = np.clip(np.searchsorted(pt, tt, side="right") - 1, 0, len(pt) - 2)
    dt = pt[i + 1] - pt[i]
    u = (tt - pt[i]) / dt
    h = ((2 * u**3 - 3 * u**2 + 1) * qp[i] + (u**3 - 2 * u**2 + u) * dt * v[i] + (-2 * u**3 + 3 * u**2) * qp[i + 1] + (u**3 - u**2) * dt * v[i + 1])
    ax.plot(pt, qp, "-", color=GREY, lw=1.6, label="velocities 가 없을 때: 점과 점을 직선으로 (꺾임)")
    ax.plot(tt, h, color=BLUE, lw=2.4, label="velocities 가 있을 때: Hermite 3 차 곡선 (위치 + 속도가 이어짐)")
    for t0, q0, v0 in zip(pt, qp, v):
        ax.plot([t0 - 0.25, t0 + 0.25], [q0 - 0.25 * v0, q0 + 0.25 * v0], color=GREEN, lw=2.2)
    ax.plot(pt, qp, "o", color=RED, ms=8, label="궤적 점 (time_from_start, positions)")
    ax.plot([], [], color=GREEN, lw=2.2, label="점의 속도 (velocities) = 기울기")
    ax.set_xlabel("time_from_start [s]")
    ax.set_ylabel("관절 목표 [rad]")
    ax.set_title("Trajectory.sample(t) 개념도: 물리 스텝(2 ms)마다 두 궤적 점 사이를 보간해 관절 목표값을 만든다", fontsize=11.5)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    save(fig, "lesson08_hermite.png")


def interlock():
    fig, ax = fig_ax(14, 3.9)
    note(ax, 0.3, 3.6, "인터록: 팔이 움직이는 동안 바퀴는 멈춘다", bold=True, fs=12)
    tiles(ax, [("팔 액션 실행 중", ["controllers.reserved 가 비어 있지 않음", "→ /cmd_vel 을 0 으로 바꿈"], C["red"]),
               ("팔이 주행 자세가 아님", ["transport_ready() = False", "→ /cmd_vel 무시 (ready · transport 만 허용)"], C["orange"]),
               ("베이스가 움직이는 중", ["바퀴 속도 > 0.04", "→ 팔 액션 goal 을 거부"], C["blue"])],
          cols=3, y_top=3.2, gap=0.3, h=1.75, tfs=11, fs=8.8)
    note(ax, 0.3, 0.75, "Nav2 와 MoveIt 이 같은 로봇을 동시에 움직이지 않게 브리지가 막는다 (Day 2 이동 → 집기 → 이동).", fs=9.6)
    save(fig, "lesson08_interlock.png")


if __name__ == "__main__":
    why(); architecture(); groups(); named_poses(); scene(); exec_flow()
    moveit_tree()
    screen("mj_start.png", "rv_start.png", "lesson08_run_result.png", rv_crop=(895, 62, 2150, 862))
    before_after("mj_transport.png", "mj_ready.png", "lesson08_arm_motion.png", "보내기 전: transport", "arm both ready 뒤")
    traj(); rviz_steps()
    screen("mj_exec.png", "rv_exec.png", "lesson08_rviz_exec.png", rv_crop=(895, 62, 2150, 862))
    Image.open(SHOTS / "rv_scene.png").convert("RGB").crop((0, 255, 2150, 862)).save(OUT / "lesson08_rviz_scene.png")
    before_after("mj_transport.png", "mj_home.png", "lesson08_home_mujoco.png", "보내기 전: transport", "arm both home 뒤 (멈춤)")
    home_hull(); home_why()
    joint_goal_flow(); controllers(); bridge_goal(); hermite(); interlock()
