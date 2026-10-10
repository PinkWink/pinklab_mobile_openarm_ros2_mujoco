"""Figures for the lesson-10 Confluence page (Pick & Place). Output: docs/camp/lesson10_*.png

Run from the workspace root with the workspace venv (needs mujoco, offscreen EGL):
    MUJOCO_GL=egl .venv-mobile-openarm/bin/python docs/camp/draw_lesson10_figures.py
Data (2026-10-10, `start spawn:=pick_table camera_depth:=true locate:=vision`, ArucoDetector + YoloDetector3D):
  artifacts/dev/pick_red.pkl  docs/camp/pick_record.py during `pick_then_place.py red` (joint states, /ground_truth,
                              parcel poses, /cmd_vel, PickPlace feedback, TCP from TF, /vision/detections, /vision/markers)
  artifacts/dev/lesson10_shots/start.png  MuJoCo viewer at start
Robot close-ups are offscreen MuJoCo renders of the recorded state (base pose, parcels, joints).
"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from draw_lesson08_figures import caption, hstack  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

SHOTS = Path("artifacts/dev/lesson10_shots")
OUT = Path("docs/camp")
RED, BLUE, GREEN, GREY, ORANGE, YELLOW = "#C62828", "#1f4e79", "#2e7d32", "#9e9e9e", "#E65100", "#E0A800"
FONT = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
RUN = pickle.load(open("artifacts/dev/pick_red.pkl", "rb"))
FB = RUN["feedback"]


def event(prefix, after=0.0):
    """Sim time of the first feedback whose detail starts with prefix (after a given time)."""
    return next(f["t"] for f in FB if f["detail"].startswith(prefix) and f["t"] >= after)


T_START = event("parcel_1 sits")
T_PREDOCK = event("visual servo")
T_BLIND = event("blind segment")
T_DOCKED = event("docked:")
T_LOCATE = event("parcel_1 at")
T_PRE = event("at pre-grasp")
T_HOLD = event("holding at")
T_LIFTED = event("retreated")
T_CARRY = event("hands_up pose")
T_PLACE0 = event("placing the held")
T_PREDOCK2 = event("visual servo", T_PLACE0)
T_DOCKED2 = event("docked:", T_PLACE0)
T_LOWER = event("lowering")
T_RELEASED = event("released")
T_RETREAT = event("back to transport")
T_END = RUN["cmd"][-1]["t"]


def near(rows, t):
    return min(rows, key=lambda r: abs(r["t"] - t))


# ================================================================ offscreen renders of the recorded state
class Render:
    def __init__(self, w=800, h=600):
        import mujoco
        self.mj = mujoco
        self.m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
        self.d = mujoco.MjData(self.m)
        self.size = (w, h)
        self.r = mujoco.Renderer(self.m, h, w)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0
        self.cam = mujoco.MjvCamera()

    def set(self, t):
        m, d = self.m, self.d
        s = near(RUN["states"], t)
        for n, q in zip(s["names"], s["positions"]):
            try:
                d.qpos[m.joint(n).qposadr[0]] = q
            except KeyError:
                pass
        a = m.joint("floating_base").qposadr[0]
        p = near(RUN["base"], t)["pose"]
        d.qpos[a:a + 2] = p[:2]
        d.qpos[a + 3:a + 7] = [p[6], p[3], p[4], p[5]]
        for i, q in enumerate(near(RUN["objects"], t)["poses"]):
            b = m.joint(f"parcel_{i + 1}_free").qposadr[0]
            d.qpos[b:b + 3] = q[:3]
            d.qpos[b + 3:b + 7] = [q[6], q[3], q[4], q[5]]
        self.mj.mj_forward(m, d)

    def image(self, t, lookat, distance, azimuth, elevation, camera=None):
        self.set(t)
        if camera:
            self.r.update_scene(self.d, camera)
        else:
            self.cam.lookat[:] = lookat
            self.cam.distance, self.cam.azimuth, self.cam.elevation = distance, azimuth, elevation
            self.r.update_scene(self.d, self.cam, self.opt)
        return Image.fromarray(self.r.render())


R = None


def renderer():
    global R
    if R is None:
        R = Render()
    return R


REAR = dict(lookat=[2.05, -3.75, 0.8], distance=1.5, azimuth=35, elevation=-28)       # 오른쪽 뒤에서 작업대 쪽으로
WIDE = dict(lookat=[1.85, -3.65, 0.6], distance=2.7, azimuth=35, elevation=-26)
SIDE = dict(lookat=[2.0, -3.85, 0.85], distance=1.0, azimuth=90, elevation=-12)      # 오른쪽 옆


def shot(t, view=REAR):
    return renderer().image(t, **view)


def panel_row(items, out, view=REAR):
    """items: (t, title, subtitle)."""
    hstack([caption(shot(t, view), title, sub) for t, title, sub in items]).save(OUT / out)
    print("saved", out)


# ================================================================ 1. 개념
def why():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "⑧ 은 손끝 하나를 움직였다 → ⑨ 는 도킹 · 인식 · 팔 동작을 하나의 '스킬' 로 묶는다", bold=True, fs=12)
    tiles(ax, [("이동 + 도킹", ["Nav2 는 작업대 앞 (사전 도킹 지점) 까지", "마지막 1 m 는 ArUco 마커 쌍으로 정밀 접근", "잔차 1 cm 이내"], C["blue"]),
               ("인식", ["카메라 (YOLO + 깊이) 가 상자 위치를 준다", "map 좌표 → base_footprint 로 되돌림", "상자 dx · dy · z (m)"], C["yellow"]),
               ("팔 + 그리퍼", ["⑧ 의 pose · cartesian · gripper 를 순서대로", "pre-grasp → 접근 → 잡기 → 들기", "놓기는 그 반대"], C["green"])],
          cols=3, y_top=3.6, gap=0.3, h=2.1, tfs=11, fs=8.8)
    note(ax, 0.3, 0.9, "예제: lessons/06_pick_place/pick_then_place.py  →  액션 /pick_place  (warehouse_skills/pick_place_server.py)", fs=9.8)
    save(fig, "lesson10_why.png")


def action_def():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.75, "warehouse_interfaces/action/PickPlace.action  —  goal · result · feedback", bold=True, fs=12)
    rbox(ax, 0.3, 0.4, 4.3, 3.9, "Goal (보내는 것)", ["object: red | parcel_1", "from_station: pick_table", "to_station: pick_table",
                                                     "arm: '' = 자동 (상자 쪽 팔)", "phase: all | pick | place"], fc=C["blue"], align="left", dy=0.48, fs=9.6)
    rbox(ax, 4.85, 0.4, 4.3, 3.9, "Feedback (진행 중)", ["phase: dock, locate, grasp ...", "progress: 0 ~ 1", "detail: 사람이 읽는 한 줄",
                                                       "→ pick_then_place.py 가", "   [시각 phase] detail 로 출력"], fc=C["yellow"], align="left", dy=0.48, fs=9.6)
    rbox(ax, 9.4, 0.4, 4.3, 3.9, "Result (끝나면)", ["success: True / False", "message: 몇 cm 위 · 슬롯에서 몇 cm", "phase_reached: done | 실패한 단계",
                                                   "duration_s: 걸린 시간 (s)"], fc=C["green"], align="left", dy=0.48, fs=9.6)
    save(fig, "lesson10_action.png")


def phases():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.35, "phase=pick  (물체를 든 채 끝난다 · 서버가 held 로 기억)", bold=True, fs=11)
    chain(ax, [("navigate_pick", ["Nav2", "사전 도킹 지점"]), ("dock", ["ArUco 마커 쌍", "시각 서보"]), ("locate", ["카메라 검출", "dx · dy · z"]),
               ("pre_grasp", ["IK + 계획", "10 cm 뒤"]), ("grasp", ["직선 접근", "그리퍼 닫기"]), ("lift", ["4 cm 위", "14 cm 뒤로"]), ("carry", ["hands_up", "0.75 m 후진"])],
          y=3.4, h=1.55, tfs=9.6, fs=8.4, gap=0.22, colors=[C["blue"], C["blue"], C["yellow"], C["green"], C["green"], C["green"], C["purple"]])
    note(ax, 0.3, 2.75, "phase=place  (held 가 없으면 바로 실패)", bold=True, fs=11)
    chain(ax, [("navigate_place", ["Nav2", "사전 도킹 지점"]), ("dock", ["ArUco 마커 쌍", "시각 서보"]), ("place", ["빈 슬롯 위", "12 cm 뒤 → 내리기"]),
               ("release", ["그리퍼 열기", "detach"]), ("retreat", ["14 cm 뒤로", "transport · 후진"])],
          y=0.8, h=1.55, tfs=9.6, fs=8.4, gap=0.22, x1=10.0, colors=[C["blue"], C["blue"], C["green"], C["green"], C["purple"]])
    rbox(ax, 10.3, 0.8, 3.4, 1.55, "phase=all (기본값)", ["pick + place 를 한 goal 로", "pick_then_place.py 는 둘로 나눠 보냄"], fc=C["grey"], tfs=9.6, fs=8.4)
    save(fig, "lesson10_phases.png")


def layout():
    """Top view of the pick table from the world file, with the recorded base poses."""
    from mobile_openarm_mujoco.model import load_world
    w = load_world()
    fig, ax = plt.subplots(figsize=(14, 6.4), dpi=150)
    for b in w["boxes"]:
        if b["name"].startswith("pick_table"):
            (cx, cy, _), (sx, sy, _) = b["center"], b["size"]
            leg = "leg" in b["name"]
            ax.add_patch(Rectangle((cx - sx / 2, cy - sy / 2), sx, sy, fc="#455a64" if leg else "#cfe3ec", ec="#455a64", lw=1, zorder=1 if not leg else 2))
    ax.text(2.6, -2.95, "pick_table (상판 높이 0.78 m)", fontsize=10, color="#37474f", ha="center")
    for mk in w["markers"]:
        if mk["station"] == "pick":
            x, y = mk["center"][:2]
            ax.add_patch(Rectangle((x - 0.03, y - 0.1), 0.03, 0.2, fc="black", zorder=3))
            ax.text(x + 0.05, y + (0.13 if mk["id"] else -0.13), f"마커 {mk['id']} (앞면 아래, 높이 0.3 m)", ha="left", va="center", fontsize=9)
    colors = {"parcel_1": RED, "parcel_2": "#1E88E5", "parcel_3": YELLOW}
    for o in w["objects"]:
        x, y = o["center"][:2]
        ax.add_patch(Rectangle((x - 0.0225, y - 0.0225), 0.045, 0.045, fc=colors[o["name"]], ec="k", lw=0.6, zorder=4))
    for s in (-0.25, 0.0, 0.25):
        ax.add_patch(Circle((2.18, -3.6 + s), 0.05, fill=False, ls="--", ec=GREEN, lw=1.2, zorder=5))
    ax.text(2.42, -3.6, "초록 점선 = 놓는 슬롯\n(축 기준 -0.25 · 0 · +0.25 m)", color=GREEN, fontsize=9, ha="left", va="center")
    ax.plot([0.7, 3.1], [-3.6, -3.6], ls=":", color=GREY, lw=1)
    ax.text(0.72, -3.57, "작업대 축 (y = -3.60)", fontsize=9, color="#666")

    def base(t, col, text):
        p = near(RUN["base"], t)["pose"]
        yaw = 2 * np.arctan2(p[5], p[6])
        ax.add_patch(Rectangle((p[0] - 0.38, p[1] - 0.32), 0.76, 0.64, fill=False, ec=col, lw=1.6, zorder=6,
                               angle=np.degrees(yaw), rotation_point=(p[0], p[1])))
        ax.add_patch(FancyArrowPatch((p[0], p[1]), (p[0] + 0.25 * np.cos(yaw), p[1] + 0.25 * np.sin(yaw)), arrowstyle="-|>", mutation_scale=12, color=col, lw=1.6))
        ax.text(p[0], p[1] - 0.36, f"{text}\nx={p[0]:.2f}", color=col, ha="center", va="top", fontsize=9)

    base(T_PREDOCK, BLUE, "사전 도킹 지점 (Nav2)")
    base(T_DOCKED, ORANGE, "도킹 끝")
    ax.annotate("", xy=(2.125, -4.05), xytext=(1.66, -4.05), arrowprops=dict(arrowstyle="<->", color=INK))
    ax.text(1.89, -4.1, "0.56 m (target_dx: 마커면까지)", ha="center", va="top", fontsize=9)
    ax.set_aspect("equal")
    ax.set_xlim(0.6, 3.15)
    ax.set_ylim(-4.35, -2.85)
    ax.set_xlabel("world x (m)  →  로봇 앞")
    ax.set_ylabel("world y (m)")
    ax.set_title("픽업 작업대 위에서 본 모습 (world 파일 · /ground_truth 실측, 사각형 = Nav2 footprint)", fontsize=12)
    ax.grid(alpha=0.25)
    save(fig, "lesson10_layout.png")


def dock_concept():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.35, "마커 두 개 → 마커면까지 거리 (along) · 옆 오차 (side) · 방향 오차 (turn)", bold=True, fs=12)
    ax.add_patch(Rectangle((0.6, 1.9), 1.4, 1.2, fc=C["blue"], ec=INK, lw=1.2))
    ax.text(1.3, 2.5, "로봇\nbase_footprint", ha="center", va="center", fontsize=9.5)
    px, scale = 8.0, (8.0 - 2.0) / 1.05            # 마커면 x, 1 m 당 길이
    for y, k in ((4.0, "마커 1 (+0.22 m)"), (1.0, "마커 0 (-0.22 m)")):
        ax.add_patch(Rectangle((px, y - 0.3), 0.15, 0.6, fc="black"))
        ax.text(px + 0.3, y, k, va="center", fontsize=9.5)
    ax.plot([px, px], [0.5, 4.6], color=GREY, lw=1, ls="--")
    ax.text(px, 4.8, "마커면 (작업대 앞면 아래)", ha="center", fontsize=9)
    arrow(ax, (2.0, 2.5), (px, 2.5), color=ORANGE)
    label(ax, 6.6, 2.75, "along (처음 약 1.04 m)", color=ORANGE)
    for d, txt, col, ha in ((0.80, "0.80 m: blind 시작\n(바깥 마커가 화면 밖 → 오도메트리 직진)", RED, "right"),
                            (0.56, "0.56 m: 도킹 끝\n(target_dx)", GREEN, "left")):
        x = px - d * scale
        ax.plot([x, x], [1.2, 2.3], color=col, lw=2.2)
        ax.text(x + (0.12 if ha == "left" else -0.12), 1.3, txt, color=col, fontsize=9, ha=ha, va="bottom")
    rbox(ax, 9.9, 1.0, 3.8, 3.4, "속도 명령 (0.1 s 마다)", ["v = 0.6 × (along - 0.56)", "   (0.03 ~ 0.10 m/s)", "w = 1.2 × side / along",
                                                        "   + 0.4 × turn", "새 마커 쌍이 없으면 정지", "timeout_s 180 (벽시계)"], fc=C["yellow"], align="left", dy=0.42, fs=9.2)
    save(fig, "lesson10_dock_concept.png")


def locate_concept():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.35, "카메라가 본 상자 → 팔이 쓸 base_footprint 좌표", bold=True, fs=12)
    chain(ax, [("head_camera", ["320×240, 깊이 포함", "약 0.4 장/s (이 PC)"]), ("YoloDetector3D", ["parcel_red 상자 박스", "깊이 → 3D 점"]),
               ("/vision/detections", ["좌표계 map", "(AMCL TF 로 변환)"]), ("VisionLocator", ["같은 TF 로 되돌림", "→ base_footprint"]), ("grasp()", ["dx 0.510", "dy -0.246 · z 0.815"])],
          y=0.9, h=1.7, tfs=10, fs=8.8, colors=[C["blue"], C["yellow"], C["yellow"], C["green"], C["green"]])
    note(ax, 0.3, 0.45, "AMCL 오차는 갔다가 돌아오면서 상쇄 → 남는 것은 카메라 오차 (수 cm).  도킹 직후에는 '부른 뒤에 찍힌' 프레임을 최대 10 s 기다린다.", fs=9.4)
    save(fig, "lesson10_locate_concept.png")


def grasp_concept():
    """Side view (x-z in base_footprint) of the right TCP during pre-grasp → lift, from TF."""
    tc = [r for r in RUN["tcp"] if T_LOCATE - 1 <= r["t"] <= T_CARRY + 0.5]
    x = np.array([r["right"][0] for r in tc])
    z = np.array([r["right"][2] for r in tc])
    t = np.array([r["t"] for r in tc])
    fig, ax = plt.subplots(figsize=(14, 6.2), dpi=150)
    edge = 2.125 - near(RUN["base"], T_LOCATE)["pose"][0]           # 작업대 앞 가장자리 (base_footprint x)
    ax.add_patch(Rectangle((edge, 0.70), 0.30, 0.08, fc="#cfe3ec", ec="#455a64"))
    ax.text(0.65, 0.74, "작업대 상판 (0.78 m)", ha="center", va="center", fontsize=9)
    ax.add_patch(Rectangle((0.510 - 0.0225, 0.78), 0.045, 0.06, fc=RED, ec="k", alpha=0.85))
    segs = [(T_LOCATE - 1, T_PRE, BLUE, "pre_grasp: IK + 계획 (관절 공간 → 곡선)"), (T_PRE, T_HOLD, ORANGE, "grasp: 직선 접근 10 cm → 닫기"),
            (T_HOLD, T_LIFTED, GREEN, "lift: 4 cm 위 → 14 cm 뒤 (직선)")]
    for a, b, col, txt in segs:
        k = (t >= a) & (t <= b)
        ax.plot(x[k], z[k], color=col, lw=2.4, label=txt)
    pts = [(T_PRE, "pre-grasp\n(물체 10 cm 뒤,\nz = 물체 중심 + 2 cm)", (-55, -6)), (T_HOLD, "잡음 (손가락 24.5 mm)", (40, -6)), (T_LIFTED, "들고 물러남", (-10, 20))]
    for tt, txt, off in pts:
        i = int(np.argmin(abs(t - tt)))
        ax.plot(x[i], z[i], "o", color=INK, ms=6)
        ax.annotate(txt, (x[i], z[i]), xytext=off, textcoords="offset points", fontsize=9.5, ha="right" if off[0] < 0 else "left",
                    arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))
    ax.set_xlim(0.2, 0.7)
    ax.set_ylim(0.68, 0.95)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m, base_footprint 앞)")
    ax.set_ylabel("z (m)")
    ax.set_title("오른손 TCP 가 지나간 길 (옆에서 본 x-z, TF 실측)", fontsize=12)
    ax.legend(loc="upper left", fontsize=9.5)
    ax.grid(alpha=0.3)
    save(fig, "lesson10_grasp_concept.png")


# ================================================================ 2. 실행
def start_screen():
    img = Image.open(SHOTS / "start.png").convert("RGB")
    img.crop((275, 0, 2025, 960)).save(OUT / "lesson10_run_result.png")
    print("saved lesson10_run_result.png")


def run_dock():
    panel_row([(T_PREDOCK, "사전 도킹 지점 (Nav2 도착)", f"sim {T_PREDOCK:.1f} s"),
               (T_BLIND, "blind 시작 (마커면 0.80 m 안)", f"sim {T_BLIND:.1f} s"),
               (T_DOCKED, "도킹 끝 (마커면 0.56 m)", f"sim {T_DOCKED:.1f} s")], "lesson10_run_dock.png", WIDE)


def camera_view():
    """What the head camera saw when `locate` ran: offscreen render of head_camera + the recorded YOLO boxes."""
    r = Render(320, 240)
    det = near(RUN["detections"], T_LOCATE)
    img = r.image(det["t"], None, 0, 0, 0, camera="head_camera").resize((960, 720), Image.NEAREST)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 22)
    cols = {"parcel_red": (220, 30, 30), "parcel_blue": (30, 110, 230), "parcel_yellow": (230, 170, 0)}
    for it in det["items"]:
        if it["camera"] != "head_camera":
            continue
        x1, y1, x2, y2 = (v * 3 for v in it["bbox"])
        col = cols.get(it["label"], (160, 160, 160))
        d.rectangle((x1, y1, x2, y2), outline=col, width=4 if it["label"] in cols else 2)
        if it["label"] not in cols:
            continue
        d.text((x1 + 4, max(0, y1 - 26)), f"{it['label']} {it['score']:.2f}", fill=col, font=font)
    caption(img, "locate 때 head_camera 가 본 것", f"sim {det['t']:.1f} s · 320×240 (3 배 확대) · 상자 = /vision/detections 실측 (회색 = 사람 · 안전모 · 조끼 · 지게차)").save(OUT / "lesson10_camera.png")
    print("saved lesson10_camera.png")


def run_grasp():
    panel_row([(T_PRE, "pre-grasp", "물체 10 cm 뒤"), (T_HOLD, "grasp", "직선 접근 후 닫기 (24.5 mm)"),
               (T_LIFTED, "lift", "4 cm 위로, 14 cm 뒤로"), (T_CARRY + 6, "carry", "hands_up 자세")], "lesson10_run_grasp.png")


def run_place():
    panel_row([(T_LOWER, "pre-place", "슬롯 12 cm 뒤 · 4 cm 위"), (T_RELEASED, "release", "내린 뒤 그리퍼 열기"),
               (T_RETREAT + 3, "retreat", "14 cm 뒤로, transport 자세")], "lesson10_run_place.png")


def dock_graph():
    fig, axes = plt.subplots(2, 1, figsize=(14, 6.4), dpi=150, sharex=True)
    b = [r for r in RUN["base"] if T_PREDOCK - 1 <= r["t"] <= T_LOCATE]
    t = np.array([r["t"] for r in b]) - T_START
    x = np.array([r["pose"][0] for r in b])
    marker_x = 2.22
    ax = axes[0]
    ax.plot(t, marker_x - x, color=BLUE, lw=2, label="마커면까지 거리 (실측, /ground_truth)")
    ax.axhline(0.80, color=RED, ls="--", lw=1)
    ax.text(t[0] + 0.2, 0.81, "visual_end_dx 0.80", color=RED, fontsize=9, va="bottom")
    ax.axhline(0.56, color=GREEN, ls="--", lw=1)
    ax.text(t[0] + 0.2, 0.565, "target_dx 0.56", color=GREEN, fontsize=9, va="bottom")
    fixes = [f for f in FB if f["detail"].startswith("visual dock") and T_PREDOCK <= f["t"] < T_BLIND]
    seen = []
    for f in fixes:
        if f["detail"] not in seen:
            seen.append(f["detail"])
            along = float(f["detail"].split("along=")[1].split()[0])
            ax.plot(f["t"] - T_START, along, "o", color=ORANGE, ms=7)
    ax.plot([], [], "o", color=ORANGE, label="마커 쌍 측정값 (feedback along)")
    ax.set_ylabel("거리 (m)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_title("도킹: 마커면까지 거리와 속도 명령 (pick 시작 기준 sim 시각)", fontsize=12)
    ax = axes[1]
    c = [r for r in RUN["cmd"] if T_PREDOCK - 1 <= r["t"] <= T_LOCATE]
    ax.step([r["t"] - T_START for r in c], [r["vx"] for r in c], where="post", color=INK, lw=1.6, label="/cmd_vel linear.x")
    for a in axes:
        a.axvspan(T_BLIND - T_START, T_DOCKED - T_START, color="#FFE0B2", alpha=0.6)
    axes[0].text((T_BLIND + T_DOCKED) / 2 - T_START, 0.95, "blind 구간\n(오도메트리 직진)", ha="center", fontsize=9)
    ax.set_ylabel("m/s")
    ax.set_xlabel("s")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    save(fig, "lesson10_dock_graph.png")


def timeline():
    stages = [("pick", [("navigate", T_START, T_PREDOCK), ("dock", T_PREDOCK, T_DOCKED), ("locate", T_DOCKED, T_LOCATE),
                        ("pre_grasp", T_LOCATE, T_PRE), ("grasp", T_PRE, T_HOLD), ("lift", T_HOLD, T_LIFTED), ("carry + 후진", T_LIFTED, T_PLACE0)]),
              ("place", [("navigate", T_PLACE0, T_PREDOCK2), ("dock", T_PREDOCK2, T_DOCKED2), ("pre-place", T_DOCKED2, T_LOWER),
                         ("release", T_LOWER, T_RELEASED), ("retreat + 후진", T_RELEASED, T_END)])]
    cols = {"navigate": C["blue"], "dock": "#BBDEFB", "locate": C["yellow"], "pre_grasp": C["green"], "pre-place": C["green"],
            "grasp": "#C8E6C9", "release": "#C8E6C9", "lift": "#A5D6A7", "carry + 후진": C["purple"], "retreat + 후진": C["purple"]}
    fig, ax = plt.subplots(figsize=(14, 3.8), dpi=150)
    for row, (name, items) in enumerate(stages):
        y = 1 - row
        t0 = items[0][1]
        for lab, a, b in items:
            ax.barh(y, b - a, left=a - t0, color=cols[lab], ec=INK, lw=0.8, height=0.6)
            if b - a > 2.2:
                ax.text((a + b) / 2 - t0, y, f"{lab}\n{b - a:.1f}", ha="center", va="center", fontsize=8.6)
        ax.text(items[-1][2] - t0 + 0.5, y, f"합 {items[-1][2] - t0:.0f} s", va="center", fontsize=10, fontweight="bold")
    ax.set_yticks([1, 0], ["pick", "place"])
    ax.set_xlabel("sim 시각 (s, 각 goal 시작 기준)")
    ax.set_xlim(0, 58)
    ax.set_title("단계별 시간 (feedback 실측, sim 시각)", fontsize=12)
    ax.grid(axis="x", alpha=0.3)
    save(fig, "lesson10_timeline.png")


def hold_graph():
    """Finger gap, right TCP height and parcel height across the pick."""
    s = [r for r in RUN["states"] if T_LOCATE - 1 <= r["t"] <= T_PLACE0]
    f = s[0]["names"].index("openarm_right_finger_joint1")
    t = np.array([r["t"] for r in s]) - T_START
    gap = np.array([r["positions"][f] for r in s]) * 1000
    o = [r for r in RUN["objects"] if T_LOCATE - 1 <= r["t"] <= T_PLACE0]
    to = np.array([r["t"] for r in o]) - T_START
    pz = np.array([r["poses"][0][2] for r in o])
    tc = [r for r in RUN["tcp"] if T_LOCATE - 1 <= r["t"] <= T_PLACE0]
    tt = np.array([r["t"] for r in tc]) - T_START
    tz = np.array([r["right"][2] for r in tc])
    fig, axes = plt.subplots(2, 1, figsize=(14, 6.4), dpi=150, sharex=True)
    ax = axes[0]
    ax.plot(t, gap, color=BLUE, lw=2, label="오른손 손가락 (finger_joint1, mm)")
    ax.axhspan(16, 28, color=GREEN, alpha=0.12)
    ax.text(t[0] + 0.3, 27, "close_min 16 ~ close_max 28 mm: 이 안에서 멈추면 '잡음'", color=GREEN, fontsize=9, va="top")
    ax.set_ylabel("mm")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_title("pick 동안 손가락 · 손끝 높이 · 상자 높이 (실측)", fontsize=12, pad=10)
    ax = axes[1]
    ax.plot(tt, tz, color=ORANGE, lw=2, label="오른손 TCP z (TF, base_footprint)")
    ax.plot(to, pz, color=RED, lw=2, ls="--", label="빨간 상자 중심 z (/warehouse/object_poses)")
    ax.set_ylabel("m")
    ax.set_xlabel("s (pick 시작 기준 sim 시각)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    events = ((T_PRE, "pre-grasp"), (T_HOLD, "잡음"), (T_LIFTED, "들기 끝 → carry"))
    for a in axes:
        for tt_, lab in events:
            a.axvline(tt_ - T_START, color=GREY, ls=":", lw=1)
    for tt_, lab in events:
        axes[0].text(tt_ - T_START + 0.15, 40, lab, fontsize=9, ha="left", va="center",
                     bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.9))
    save(fig, "lesson10_hold_graph.png")


# ================================================================ 3. 코드
def code_flow():
    fig, ax = fig_ax(14, 5.9)
    note(ax, 0.3, 5.65, "pick_place_server.py: execute() → 절반씩 → 단계 함수 → ⑧ 의 MoveItClient · NavClient", bold=True, fs=12)
    rbox(ax, 0.3, 2.0, 2.6, 1.6, "execute()", ["phase 고르기", "held 기억", "실패 → recover()"], fc=C["grey"], tfs=10.5, fs=8.8)
    rbox(ax, 3.5, 3.4, 2.6, 1.4, "do_pick()", ["팔 고르기", "dock_side_for"], fc=C["blue"], tfs=10.5, fs=8.8)
    rbox(ax, 3.5, 0.6, 2.6, 1.4, "do_place()", ["free_slot_offset", "슬롯 dx · dy"], fc=C["blue"], tfs=10.5, fs=8.8)
    arrow(ax, (2.9, 2.9), (3.5, 4.1))
    arrow(ax, (2.9, 2.7), (3.5, 1.3))
    items = [(4.25, "locate_object()", "VisionLocator.relative", C["yellow"]), (3.25, "grasp()", "move_pose · move_cartesian · gripper · attach", C["green"]),
             (2.25, "navigate_and_dock()", "nav.go_to · wait_markers · nav.dock", C["yellow"]), (1.25, "move_named · nav.drive", "hands_up / transport · 0.75 m 후진", C["purple"]),
             (0.25, "place()", "move_pose · move_cartesian · gripper · detach", C["green"])]
    for y, t, sub, fc in items:
        rbox(ax, 6.9, y, 6.8, 0.8, f"{t}   —   {sub}", fc=fc, tfs=9.6)
    for y in (4.65, 3.65, 2.65, 1.65):
        arrow(ax, (6.1, 4.1), (6.9, y), color=BLUE)
    for y in (2.65, 1.65, 0.65):
        arrow(ax, (6.1, 1.3), (6.9, y), color=ORANGE)
    note(ax, 3.5, 5.15, "파랑 = pick 절반,  주황 = place 절반", fs=9.5)
    save(fig, "lesson10_code_flow.png")


def params():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.35, "skills.yaml: 이 페이지에서 쓰는 값", bold=True, fs=12)
    tiles(ax, [("dock", ["target_dx 0.56 · visual_end_dx 0.80", "max_speed 0.10 · blind_speed 0.06", "gain 0.6 · lateral 1.2 · heading 0.4", "timeout_s 180 (벽시계)"], C["blue"]),
               ("grasp", ["pre_offset_x -0.10 · z_offset 0.02", "lift_z 0.04 · retreat_x -0.14", "open 0.044 · close 0.012", "close_min 0.016 ~ close_max 0.028"], C["green"]),
               ("place", ["pre_offset_x -0.12 · drop_z 0.004", "slot_offsets_y [-0.25, 0, 0.25]", "x_from_edge 0.055", "carry_pose hands_up"], C["yellow"])],
          cols=3, y_top=3.9, gap=0.3, h=2.6, tfs=11, fs=9)
    save(fig, "lesson10_params.png")


if __name__ == "__main__":
    for f in (why, action_def, phases, layout, dock_concept, locate_concept, grasp_concept, start_screen, run_dock, camera_view,
              run_grasp, run_place, dock_graph, timeline, hold_graph, code_flow, params):
        f()
