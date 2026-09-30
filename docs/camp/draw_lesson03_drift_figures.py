"""Lesson-03 figures: why odometry drifts even inside MuJoCo. Output: docs/camp/lesson03_drift_*.png

Run from the workspace root after odom_experiment.py wrote artifacts/dev/odom_square1.csv.
Numbers in the figures: wheel penetration from the compiled model at rest (contact dist -0.0285 mm),
straight / turn ratios and error curves from the square-1 CSV.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, fig_ax, label, note, rbox, save  # noqa: E402
from draw_lesson03_figures import tiles_at  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402
import numpy as np  # noqa: E402

RED, BLUE, GREEN, BROWN = "#C62828", "#1f4e79", "#2e7d32", "#7a4b00"
CSV = Path("artifacts/dev/odom_square1.csv")


def load():
    """Rows are recorded on each /odom; /ground_truth of the same tick arrives just after it, so pair odom[i] with truth[i+1]."""
    d = np.genfromtxt(CSV, delimiter=",", names=True)
    o = np.c_[d["odom_x"], d["odom_y"], np.unwrap(d["odom_yaw"])]
    t = np.c_[d["true_x"], d["true_y"], np.unwrap(d["true_yaw"])]
    return o, t


def travelled(p):
    return np.r_[0, np.cumsum(np.hypot(*np.diff(p[:, :2], axis=0).T))]


# ---------------------------------------------------------------- A. overview
def drift_overview():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "odom 은 위치를 재지 않는다: 바퀴가 돈 각도로 '계산'한다", bold=True, fs=12)
    rbox(ax, 0.3, 1.75, 2.2, 1.7, "바퀴 모터가 돈다", ["/cmd_vel → 목표 속도"], fc=C["purple"], tfs=10.5, fs=8.6)
    # truth path
    ax.add_patch(Rectangle((3.0, 2.95), 8.4, 1.85, fc="#F3FAF3", ec="#7CB07C", lw=1.2, zorder=1))
    note(ax, 3.15, 4.55, "MuJoCo 가 계산하는 실제 움직임", bold=True, fs=10, color=GREEN)
    xs = [3.2, 5.95, 8.7]
    for x, (t, l) in zip(xs, [("바퀴-바닥 접촉 힘", "soft contact · 마찰"), ("몸체가 실제로 이동", "파고듦 · 끌림 포함"), ("/ground_truth", "world 기준 정답")]):
        rbox(ax, x, 3.1, 2.45, 1.2, t, [l], fc=C["green"], tfs=9.8, fs=8.4)
    for x in xs[:2]:
        arrow(ax, (x + 2.45, 3.7), (x + 2.75, 3.7))
    # odom path
    ax.add_patch(Rectangle((3.0, 0.35), 8.4, 1.85, fc="#F4F8FF", ec="#8FA9D6", lw=1.2, zorder=1))
    note(ax, 3.15, 1.95, "odom 이 계산하는 추정 움직임", bold=True, fs=10, color=BLUE)
    for x, (t, l) in zip(xs, [("바퀴 관절 각도 qpos", "엔코더 값"), ("가정 3개로 환산", "반지름 r · 윤거 track · 미끄러짐 0"), ("/odom", "시작점 기준 추정")]):
        rbox(ax, x, 0.5, 2.45, 1.2, t, [l], fc=C["blue"], tfs=9.8, fs=8.0)
    for x in xs[:2]:
        arrow(ax, (x + 2.45, 1.1), (x + 2.75, 1.1))
    ax.plot([2.5, 2.75], [2.6, 2.6], color=INK, lw=1.6); ax.plot([2.75, 2.75], [1.1, 3.7], color=INK, lw=1.6)
    arrow(ax, (2.75, 3.7), (3.2, 3.7)); arrow(ax, (2.75, 1.1), (3.2, 1.1))
    # compare
    ax.plot([11.15, 11.75], [3.7, 3.7], color=INK, lw=1.6); ax.plot([11.15, 11.75], [1.1, 1.1], color=INK, lw=1.6)
    ax.plot([11.75, 11.75], [1.1, 3.7], color=INK, lw=1.6); arrow(ax, (11.75, 2.4), (12.1, 2.4))
    rbox(ax, 12.1, 1.55, 1.6, 1.7, "차이", ["= odom 오차"], fc=C["red"], tfs=11, fs=8.8)
    note(ax, 0.3, 0.05, "시뮬레이터도 접촉을 '물리'로 푼다. 가정이 아주 조금 어긋나고, 그 차이가 적분되며 쌓인다.", fs=9.4)
    save(fig, "lesson03_drift_overview.png")


# ---------------------------------------------------------------- B. soft contact
def drift_contact():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "원인 1: 바퀴가 바닥에 살짝 파고든다 (soft contact)", bold=True, fs=12)
    ax.set_aspect("equal")
    cx, r, pen = 3.1, 1.75, 0.32                      # drawn radius, exaggerated penetration
    floor = 0.9
    cy = floor + r - pen
    ax.add_patch(Rectangle((0.4, 0.35), 5.4, floor - 0.35, fc="#E9E4DA", ec="none", zorder=1))
    ax.plot([0.4, 5.8], [floor, floor], color="#8d7b5a", lw=2, zorder=2)
    ax.add_patch(Circle((cx, cy), r, fc="#3a3a3a", ec=INK, lw=1.2, alpha=0.9, zorder=3))
    ax.add_patch(Circle((cx, cy), r * 0.35, fc="#9e9e9e", ec=INK, lw=1, zorder=4))
    a = np.arccos((cy - floor) / r)
    th = np.linspace(-np.pi / 2 - a, -np.pi / 2 + a, 40)
    ax.add_patch(Polygon(np.c_[cx + r * np.cos(th), cy + r * np.sin(th)], closed=True, fc=RED, ec=RED, alpha=0.75, zorder=5))
    # radii
    arrow(ax, (cx, cy), (cx - r * 0.72, cy + r * 0.69), color="#FFD54F", lw=1.8)
    ax.text(cx - 1.75, cy + 1.55, "r = 82.5 mm", color="#B8860B", fontsize=9.5, fontweight="bold", zorder=6, ha="center")
    arrow(ax, (cx + 0.12, cy), (cx + 0.12, floor), color="#80DEEA", lw=1.8)
    ax.text(cx + 0.28, cy - 0.62, "실제로 구르는\n반지름 < r", color="#80DEEA", fontsize=8.8, fontweight="bold", zorder=6)
    label(ax, cx + 1.95, floor - 0.25, "파고든 깊이 (과장해서 그림)", color=RED, fs=8.6)
    arrow(ax, (cx + 0.55, 0.72), (cx + 0.3, floor - 0.08), color=RED, lw=1.2)
    tiles_at(ax, [("모델에서 잰 값 (정지 상태)", ["접촉 깊이 0.03 mm (바퀴마다)", "바퀴 중심 높이 82.47 mm", "solref 0.008 · solimp 0.95~0.99"], C["yellow"]),
                  ("직진 8 m 실측 (멈춘 뒤 남는 오차)", ["odom 8.031 m · 실제 8.030 m", "바퀴가 돈 만큼 다 가지 못함", "odom 이 0.017 % 길다 (1 m 에 0.17 mm)"], C["green"])],
             cols=1, x0=7.0, x1=13.7, y_top=4.6, gap=0.3, h=1.75, tfs=10.5, fs=9.0)
    note(ax, 7.0, 0.55, "odom 은 r 로 굴러간다고 보고 계산 → 실제보다 조금 더 간 것으로 적분한다.", fs=9.4, bold=True)
    save(fig, "lesson03_drift_contact.png")


# ---------------------------------------------------------------- C. turning scrub
def drift_turn():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "원인 2: 제자리 회전에서 바퀴와 캐스터가 바닥에 끌린다", bold=True, fs=12)
    ax.set_aspect("equal")
    cx, cy, half = 3.4, 2.55, 1.35                    # half track (drawn)
    ax.add_patch(Circle((cx, cy), half, fc="none", ec="#9e9e9e", lw=1.2, ls="--", zorder=1))
    ax.add_patch(Rectangle((cx - 1.1, cy - 1.0), 2.2, 2.0, fc="#ECEFF1", ec=INK, lw=1.2, zorder=2))
    for s in (1, -1):
        ax.add_patch(Rectangle((cx - 0.45, cy + s * half - 0.14), 0.9, 0.28, fc="#333333", ec=INK, zorder=3))
    for dx, dy in ((0.8, 0.7), (0.8, -0.7), (-0.8, 0.7), (-0.8, -0.7)):
        ax.add_patch(Circle((cx + dx, cy + dy), 0.11, fc="#bdbdbd", ec=INK, lw=1, zorder=3))
    # wheel travel directions (turning left: left wheel back, right wheel forward)
    arrow(ax, (cx + 0.1, cy + half + 0.3), (cx - 0.9, cy + half + 0.3), color=BLUE, lw=2)
    arrow(ax, (cx - 0.1, cy - half - 0.3), (cx + 0.9, cy - half - 0.3), color=BLUE, lw=2)
    label(ax, cx - 1.55, cy + half + 0.3, "왼쪽 뒤로", color=BLUE, fs=8.6); label(ax, cx + 1.6, cy - half - 0.3, "오른쪽 앞으로", color=BLUE, fs=8.6)
    ax.add_patch(FancyArrowPatch((cx + 0.55, cy - 0.35), (cx + 0.55, cy + 0.35), connectionstyle="arc3,rad=0.6", arrowstyle="-|>", mutation_scale=14, color=BROWN, lw=1.8, zorder=5))
    label(ax, cx + 0.05, cy, "회전", color=BROWN, fs=9)
    # scrub marks at wheel contacts and caster drag
    for s in (1, -1):
        ax.add_patch(Arc((cx, cy + s * half), 0.62, 0.62, theta1=200, theta2=340, color=RED, lw=1.6, zorder=6))
    label(ax, cx + 2.35, cy + half, "접지점이 비틀림", color=RED, fs=8.6)
    for dx, dy in ((0.8, 0.7), (0.8, -0.7), (-0.8, 0.7), (-0.8, -0.7)):
        v = np.array([-dy, dx]) / np.hypot(dx, dy) * 0.42
        arrow(ax, (cx + dx, cy + dy), (cx + dx + v[0], cy + dy + v[1]), color=RED, lw=1.4)
    label(ax, cx - 1.9, cy, "캐스터 4개\n옆으로 끌림", color=RED, fs=8.6)
    label(ax, cx, cy - half - 0.85, "점선 원 = track 0.4288 m 의 바퀴 궤적", fs=8.4)
    tiles_at(ax, [("odom 의 가정", ["두 바퀴가 track 끝에서 미끄러짐 없이 구른다", "da = (dr - dl) / track"], C["blue"]),
                  ("실제 (MuJoCo 접촉)", ["바퀴는 접지점에서 제자리 비틀림 (torsional friction)", "캐스터 4개도 옆으로 끌려온다 → 바퀴가 조금 헛돈다"], C["red"]),
                  ("90° 회전 4번 실측 (멈춘 뒤 남는 오차)", ["odom 351.56° · 실제 351.37° → 0.19° 더 돈 것으로 계산", "한 번에 0.047° (0.054 %) · track 이 0.2 mm 넓은 셈"], C["yellow"])],
             cols=1, x0=7.0, x1=13.7, y_top=4.85, gap=0.22, h=1.35, tfs=10.2, fs=8.7)
    save(fig, "lesson03_drift_turn.png")


# ---------------------------------------------------------------- D'. elastic lag (MuJoCo only, no ROS)
def drift_elastic():
    d = np.genfromtxt("artifacts/dev/odom_offline.csv", delimiter=",", names=True, dtype=None, encoding=None)
    ph = d["phase"]
    cut = [0] + [k for k in range(1, len(ph)) if ph[k] != ph[k - 1]]
    t = d["t"]
    ex = (d["odom_x"] - d["true_x"]) * 1000
    ey = np.degrees(np.unwrap(d["odom_yaw"]) - np.unwrap(d["true_yaw"]))
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), dpi=150)
    for a, (i0, i1, i2), y, unit, speed, pred in ((axs[0], cut[0:3], ex, "mm", "0.3 m/s", "0.3 m/s × 8 ms ≈ 2.4 mm"),
                                                  (axs[1], cut[2:5], ey, "°", "0.5 rad/s", "0.5 rad/s × 8 ms ≈ 0.23°")):
        a.axvspan(t[i0], t[i1 - 1], color="#BBDEFB", alpha=0.45); a.axvspan(t[i1], t[i2 - 1], color="#E0E0E0", alpha=0.6)
        a.plot(t[i0:i2], y[i0:i2], color=RED, lw=2.2); a.axhline(0, color=INK, lw=0.8)
        a.grid(alpha=0.3); a.set_xlabel("시뮬레이션 시각 [s]"); a.set_ylabel(f"odom - 실제 [{unit}]")
        mid = (i0 + i1) // 2
        a.annotate(f"움직이는 동안 {y[mid]:+.2f} {unit}\n({speed} · 스프링처럼 눌려 있음)", (t[mid], y[mid]), xytext=(0, 30), textcoords="offset points", ha="center", fontsize=9.5, color=RED,
                   arrowprops=dict(arrowstyle="-|>", color=RED))
        a.annotate(f"멈추면 되돌아옴\n남는 오차 {y[i2 - 1]:+.2f} {unit}", (t[i2 - 1], y[i2 - 1]), xytext=(-150, 30), textcoords="offset points", ha="center", fontsize=9.5, color=GREEN,
                   arrowprops=dict(arrowstyle="-|>", color=GREEN))
        a.text(0.02, 0.04, f"예상: {pred}", transform=a.transAxes, fontsize=9, color="#555555")
    axs[0].set_title("직진 (파랑) → 정지 (회색): 위치 오차", fontsize=11)
    axs[1].set_title("제자리 회전 (파랑) → 정지 (회색): yaw 오차", fontsize=11)
    for a in axs:
        lo, hi = a.get_ylim(); a.set_ylim(lo - 0.25 * (hi - lo), hi + 0.35 * (hi - lo))
    fig.suptitle("원인 3: 접촉은 스프링이다 (solref 8 ms): 움직이는 동안만 어긋나고, 멈추면 대부분 되돌아온다   (ROS 없이 MuJoCo 만 · 같은 스텝 비교)",
                 fontsize=11.5, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    save(fig, "lesson03_drift_elastic.png")


# ---------------------------------------------------------------- D. yaw -> lateral
def drift_yaw():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "yaw 오차는 다음 직진에서 옆으로 벌어진다", bold=True, fs=12)
    x0, y0, L, d = 0.8, 1.3, 7.2, np.radians(14)       # exaggerated angle
    ax.plot([x0, x0 + L], [y0, y0], color=BLUE, lw=2.2, ls="--")
    ax.plot([x0, x0 + L * np.cos(d)], [y0, y0 + L * np.sin(d)], color=GREEN, lw=2.6)
    ax.add_patch(Circle((x0, y0), 0.09, fc=INK, zorder=5))
    label(ax, x0 + 4.2, y0 - 0.35, "odom 이 믿는 경로 (yaw 오차 없음)", color=BLUE, fs=9)
    label(ax, x0 + 3.2, y0 + 1.25, "실제 경로", color=GREEN, fs=9)
    ax.add_patch(Arc((x0, y0), 2.6, 2.6, theta1=0, theta2=np.degrees(d), color=RED, lw=1.8))
    label(ax, x0 + 1.65, y0 + 0.2, "δ", color=RED, fs=11)
    xe = x0 + L * np.cos(d)
    ax.plot([xe, xe], [y0, y0 + L * np.sin(d)], color=RED, lw=1.8)
    label(ax, xe + 0.85, y0 + L * np.sin(d) / 2, "L · sin δ", color=RED, fs=10)
    label(ax, x0 + L / 2, y0 - 0.85, "L = 직진 거리  (각도는 과장해서 그림)", fs=8.6)
    tiles_at(ax, [("회전 한 번 뒤 (실측)", ["δ = 0.047° , L = 2 m", "→ 옆으로 1.6 mm"], C["yellow"]),
                  ("회전이 쌓이면", ["δ 는 회전마다 더해진다 (4번 → 0.19°)", "뒤 변일수록 더 크게 벌어진다"], C["orange"]),
                  ("실제 로봇 규모", ["δ = 1° , L = 10 m", "→ 17 cm"], C["red"])],
             cols=1, x0=10.0, x1=13.7, y_top=4.3, gap=0.2, h=1.2, tfs=10.2, fs=8.7)
    save(fig, "lesson03_drift_yaw.png")


# ---------------------------------------------------------------- E. measured
def drift_measured():
    o, t = load()
    o, t = o[:-1], t[1:]
    s = travelled(t)
    e_pos = np.hypot(*(o[:, :2] - t[:, :2]).T) * 100
    e_yaw = np.degrees(o[:, 2] - t[:, 2])
    turning = np.r_[False, np.abs(np.diff(t[:, 2])) > 1e-3]
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
    for a in axs:
        for k in np.flatnonzero(np.diff(turning.astype(int)) == 1):
            a.axvline(s[k], color="#FFB74D", lw=6, alpha=0.35)
        a.grid(alpha=0.3); a.set_xlabel("실제 주행 거리 [m]")
    axs[0].plot(s, e_yaw, color=BROWN, lw=2)
    axs[0].set_ylabel("yaw 오차 [°]"); axs[0].set_title("yaw 오차: 회전(주황 띠)마다 계단처럼 한 칸씩", fontsize=11)
    axs[1].plot(s, e_pos, color=RED, lw=2)
    axs[1].set_ylabel("위치 오차 [cm]"); axs[1].set_title("위치 오차: 회전 뒤 직진에서 기울기가 커진다", fontsize=11)
    for a, v, u in ((axs[0], e_yaw[-1], "°"), (axs[1], e_pos[-1], " cm")):
        a.annotate(f"끝: {v:.2f}{u}", (s[-1], v), xytext=(-95, -4), textcoords="offset points", color=INK, fontsize=10, fontweight="bold")
    fig.suptitle("실측 (사각형 1바퀴, 한 변 2 m, 같은 틱끼리 비교): 뾰족한 곳 = 움직이는 동안의 탄성 어긋남", fontsize=12, fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    save(fig, "lesson03_drift_measured.png")


# ---------------------------------------------------------------- F. compare at the same time
def drift_timing():
    o, t = load()
    s = travelled(t)
    raw = np.hypot(*(o[:, :2] - t[:, :2]).T) * 100
    fixed = np.r_[np.hypot(*(o[:-1, :2] - t[1:, :2]).T) * 100, np.nan]
    fig = plt.figure(figsize=(14, 4.8), dpi=150)
    ax = fig.add_axes([0.05, 0.13, 0.52, 0.72])
    ax.plot(s, raw, color="#9e9e9e", lw=1.8, label="20 ms 이전 정답과 비교 (가짜 오차 포함)")
    ax.plot(s, fixed, color=RED, lw=2.2, label="같은 틱의 정답과 비교")
    ax.set_xlabel("실제 주행 거리 [m]"); ax.set_ylabel("위치 오차 [cm]"); ax.grid(alpha=0.3); ax.legend(loc="upper left", fontsize=9)
    ax.set_title("비교 시각이 한 틱 어긋나면 달리는 동안 오차가 부풀어 보인다", fontsize=11)
    bx = fig.add_axes([0.6, 0.05, 0.39, 0.85]); bx.set_xlim(0, 5.6); bx.set_ylim(0, 4.8); bx.axis("off")
    rbox(bx, 0.1, 3.05, 5.4, 1.45, "브리지는 같은 틱에 두 토픽을 낸다", ["/odom 다음에 /ground_truth (stamp 같음)", "/odom 을 받는 순간 손에 든 정답은 한 틱 전 것"], fc=C["grey"], tfs=10, fs=8.6, align="left")
    rbox(bx, 0.1, 1.45, 5.4, 1.35, "가짜 오차 크기", ["0.3 m/s × 20 ms = 6 mm (달릴 때만)", "앞 결과 그래프의 높은 턱은 대부분 이것"], fc=C["yellow"], tfs=10, fs=8.6, align="left")
    rbox(bx, 0.1, 0.0, 5.4, 1.2, "규칙", ["두 값을 비교할 땐 header.stamp 가 같은 것끼리", "남는 0.2 cm 턱은 진짜 탄성 어긋남 (앞 그림)"], fc=C["green"], tfs=10, fs=8.6, align="left")
    save(fig, "lesson03_drift_timing.png")


if __name__ == "__main__":
    for f in (drift_overview, drift_contact, drift_turn, drift_elastic, drift_yaw, drift_timing, drift_measured):
        f()
