"""Animated GIFs for the lesson 03 - 06 pages, built from data recorded during real runs (no simulator needed).

  python3 docs/camp/make_nav_gifs.py [name ...]        # run from the workspace root; no name = all
Sources (artifacts/dev): odom_square1.csv, slam_maps/wp*.npz, nav_run_bt2.pkl, nav_amcl.pkl, avoid_frames_v2/*.png
Outputs (docs/camp): lesson03_square.gif, lesson04_map_growth.gif, lesson05_goal_run.gif, lesson05_amcl.gif,
                     lesson06_crossing.gif, lesson06_headon.gif
"""
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import matplotlib.pyplot as plt  # noqa: E402
from draw_lesson04_figures import show_grid  # noqa: E402
from draw_lesson05_figures import footprint, show_cost  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT, DEV = Path("docs/camp"), Path("artifacts/dev")
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
RED, BLUE, GREEN = "#C62828", "#1565C0", "#1B5E20"


def grab(fig):
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3].copy())


def write(frames, durations, name, colors=96):
    pal = frames[len(frames) // 2].quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    out = OUT / name
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=False)
    print("saved", out, len(frames), "frames", f"{sum(durations) / 1000:.1f} s", f"{out.stat().st_size / 1e6:.1f} MB", frames[0].size)


def captioned(img, text, badge=None, bar=50, size=22):
    """Paste img on a dark canvas with a subtitle bar under it."""
    font = ImageFont.truetype(BOLD, size)
    canvas = Image.new("RGB", (img.width, img.height + bar), "#111111")
    canvas.paste(img, (0, 0))
    d = ImageDraw.Draw(canvas)
    if badge:
        d.rounded_rectangle((10, img.height + 10, 22 + d.textlength(badge, font=font), img.height + bar - 8), 7, fill="#FFD400")
        d.text((16, img.height + 13), badge, fill="#111111", font=font)
    d.text(((img.width - d.textlength(text, font=font)) / 2, img.height + 13), text, fill="white", font=font)
    return canvas


# ---------------------------------------------------------------- lesson 03: odom vs ground truth on a square
def square():
    a = np.genfromtxt(DEV / "odom_square1.csv", delimiter=",", names=True)
    t = a["t"] - a["t"][0]
    err = np.hypot(a["odom_x"] - a["true_x"], a["odom_y"] - a["true_y"]) * 100
    yaw = np.degrees(np.abs((a["odom_yaw"] - a["true_yaw"] + np.pi) % (2 * np.pi) - np.pi))
    frames = []
    idx = list(range(0, len(t), 30)) + [len(t) - 1]
    for i in idx:
        fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4.6), dpi=100, gridspec_kw={"width_ratios": [1, 1.15]})
        ax.plot(a["true_x"][: i + 1], a["true_y"][: i + 1], color=BLUE, lw=2.4, label="/ground_truth (실제)")
        ax.plot(a["odom_x"][: i + 1], a["odom_y"][: i + 1], color=RED, lw=1.4, ls="--", label="/odom (바퀴로 계산)")
        ax.add_patch(Circle((a["true_x"][i], a["true_y"][i]), 0.09, fc=BLUE, ec="white", zorder=5))
        ax.set_xlim(-0.5, 2.6); ax.set_ylim(-0.5, 2.6); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.legend(loc="upper center", fontsize=8.5, ncol=1)
        ax.set_title(f"한 변 2 m 사각형 · t = {t[i]:4.1f} s", fontsize=11)
        bx.plot(t[: i + 1], err[: i + 1], color=RED, lw=1.8)
        bx.set_xlim(0, t[-1]); bx.set_ylim(0, max(err) * 1.25); bx.grid(alpha=0.3)
        bx.set_xlabel("시간 [s]"); bx.set_ylabel("위치 오차 [cm]")
        bx.set_title(f"/odom 과 /ground_truth 의 차이: {err[i]:.2f} cm · yaw {yaw[i]:.2f}°", fontsize=11)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
    dur = [120] * len(frames); dur[0], dur[-1] = 1200, 3000
    cap = ["두 경로가 거의 겹친다 · 오차는 회전할 때 올라간다"] * len(frames)
    cap[-1] = f"한 바퀴 뒤 위치 오차 {err[-1]:.1f} cm · yaw {yaw[-1]:.1f}° → 줄지 않고 쌓인다"
    write([captioned(f, c) for f, c in zip(frames, cap)], dur, "lesson03_square.gif", colors=64)


# ---------------------------------------------------------------- lesson 04: the map growing during one lap
def map_growth():
    shots = [np.load(DEV / f"slam_maps/wp{i}.npz") for i in range(8)]
    route = [(0.0, 0.0), (6.4, 0.0), (6.4, 4.8), (-6.6, 4.8), (-6.6, -4.8), (6.4, -4.8), (6.4, 0.0), (0.0, 0.0)]
    t0, frames, caps = float(shots[0]["stamp"]), [], []
    for i, s in enumerate(shots):
        fig, ax = plt.subplots(figsize=(9.0, 6.9), dpi=100)
        show_grid(ax, s["data"], float(s["resolution"]), s["origin"])
        path = np.array(route[: i + 1])
        ax.plot(path[:, 0], path[:, 1], color="#1976D2", lw=2.2, alpha=0.85)
        x, y, yaw = s["pose"]
        ax.add_patch(Circle((x, y), 0.3, fc=RED, ec="white", lw=1.2, zorder=5))
        ax.plot([x, x + 0.6 * np.cos(yaw)], [y, y + 0.6 * np.sin(yaw)], color="white", lw=2.0, zorder=6)
        known = (s["data"] >= 0).mean() * 100
        ax.set_title(f"시뮬레이션 {float(s['stamp']) - t0:3.0f} s  ·  아는 칸 {known:2.0f} %   (회색 = 모름 · 흰색 = 비어 있음 · 검정 = 막힘)", fontsize=11)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        caps.append("출발 자리에서 라이다로 보이는 곳만 지도가 된다" if i == 0 else
                    "한 바퀴 끝: 출발점으로 돌아와 지도가 닫힌다" if i == 7 else f"웨이포인트 {i}: 지나가며 본 곳이 채워진다 (파랑 = 지나온 길)")
    dur = [1500] * len(frames); dur[0], dur[-1] = 2200, 3500
    write([captioned(f, c, f"{i + 1}/8") for i, (f, c) in enumerate(zip(frames, caps))], dur, "lesson04_map_growth.gif", colors=48)


# ---------------------------------------------------------------- lesson 05: a goal run on the global costmap
def goal_run():
    d = pickle.load(open(DEV / "nav_run_bt2.pkl", "rb"))
    tr, od, plans = np.array(d["truth"]), np.array(d["odom"]), d["plans"]
    t_start, t_second = plans[0]["t"] - 1.5, plans[1]["t"]
    moving = np.where(np.abs(od[:, 4]) + np.abs(od[:, 5]) > 0.01)[0]
    t_end = od[moving[-1], 0] + 2.0
    frames, caps = [], []
    for t in np.arange(t_start, t_end, 0.8):
        i = int(np.argmin(np.abs(tr[:, 0] - t))); j = int(np.argmin(np.abs(od[:, 0] - t)))
        fig, ax = plt.subplots(figsize=(7.4, 7.2), dpi=100)
        show_cost(ax, d["global_costmap"])
        for k, p in enumerate(plans):
            if p["t"] <= t:
                ax.plot(p["xy"][:, 0], p["xy"][:, 1], color=GREEN, lw=2.2, alpha=1.0 if (k == 1) == (t >= t_second) else 0.25)
        m = (tr[:, 0] >= t_start) & (tr[:, 0] <= t)
        ax.plot(tr[m, 1], tr[m, 2], color=BLUE, lw=2.0, ls="--")
        footprint(ax, tr[i, 1], tr[i, 2], tr[i, 3], fc="none", ec=RED, lw=2.0)
        ax.set_xlim(-2.6, 4.2); ax.set_ylim(-5.2, 1.4)
        ax.set_title(f"t = {t - plans[0]['t']:5.1f} s   v = {od[j, 4]:5.2f} m/s   w = {od[j, 5]:5.2f} rad/s\n"
                     "초록 = /plan · 파랑 점선 = 실제로 간 길 · 빨강 = 로봇", fontsize=10.5)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        v, w = od[j, 4], od[j, 5]
        if t < plans[0]["t"]:
            caps.append("goal 1.2 -3.6 0 을 보내기 직전")
        elif t < t_second:
            caps.append("제자리에서 경로 방향으로 돈다" if abs(v) < 0.03 and abs(w) > 0.1 else
                        "첫 목표: 픽업 작업대 앞 (1.2, -3.6) · /plan 을 따라간다")
        else:
            caps.append("제자리에서 경로 방향으로 돈다" if abs(v) < 0.03 and abs(w) > 0.1 else
                        "둘째 목표: RViz 2D Goal Pose 로 준 가운데 (0, 0)")
    dur = [130] * len(frames); dur[0], dur[-1] = 1200, 3000
    write([captioned(f, c) for f, c in zip(frames, caps)], dur, "lesson05_goal_run.gif", colors=64)


# ---------------------------------------------------------------- lesson 05: AMCL particles converging
def amcl():
    d = pickle.load(open(DEV / "nav_amcl.pkl", "rb"))
    tr, P = np.array(d["truth"]), d["particles"]
    frames, caps = [], []
    for n, p in enumerate(P):
        xyt = p["xyt"]
        i = int(np.argmin(np.abs(tr[:, 0] - p["t"])))
        e = np.hypot(*(xyt[:, :2].mean(0) - tr[i, 1:3])) * 100
        fig, ax = plt.subplots(figsize=(8.6, 5.9), dpi=100)
        show_cost(ax, d["global_costmap"])
        ax.quiver(xyt[:, 0], xyt[:, 1], np.cos(xyt[:, 2]), np.sin(xyt[:, 2]), color="#E53935", scale=34, width=0.004, alpha=0.5)
        ax.add_patch(Circle((tr[i, 1], tr[i, 2]), 0.11, fc=BLUE, ec="white", zorder=6))
        ax.add_patch(Circle((0.6, 0.4), 0.1, fc="none", ec="#7a4b00", lw=1.8, zorder=6))
        ax.set_xlim(-1.2, 4.0); ax.set_ylim(-1.6, 1.8)
        ax.set_title(f"{p['t'] - P[0]['t']:4.1f} s · 파티클 {len(xyt):4d} 개 · 퍼짐 {xyt[:, 0].std():.2f} m · 평균과 실제의 차이 {e:3.0f} cm\n"
                     "빨강 화살표 = 파티클 · 파랑 = 실제 위치 · 갈색 원 = 틀리게 알려 준 위치", fontsize=10.5)
        fig.tight_layout()
        frames.append(grab(fig)); plt.close(fig)
        caps.append("틀린 초기 위치 (0.6, 0.4, 23°) 주변에 파티클이 퍼져 있다" if n == 0 else
                    "라이다와 지도가 맞는 파티클만 남아 실제 위치로 모였다" if n == len(P) - 1 else
                    "달리면서 라이다와 맞지 않는 파티클이 사라진다")
    dur = [550] * len(frames); dur[0], dur[-1] = 2200, 3500
    write([captioned(f, c) for f, c in zip(frames, caps)], dur, "lesson05_amcl.gif", colors=64)


# ---------------------------------------------------------------- lesson 06: screen recordings, one frame per sim second
MJ, RV = (345, 200, 1195, 1000), (1830, 130, 2430, 1040)        # crop boxes in the 3440 x 1440 screenshots


def avoid(mode, stages, name):
    fr = DEV / "avoid_frames_v2"
    files = sorted(fr.glob(f"{mode}_s*.png"))
    head = ImageFont.truetype(BOLD, 20)
    frames, durs = [], []
    for k, f in enumerate(files):
        text = next((s for a, b, s in stages if a <= k < b), None)
        if text is None:
            continue
        shot = Image.open(f).convert("RGB")
        a, b = shot.crop(MJ), shot.crop(RV)
        h = 560
        a, b = a.resize((round(a.width * h / a.height), h), Image.LANCZOS), b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
        canvas = Image.new("RGB", (a.width + b.width + 6, h + 36), "#111111")
        canvas.paste(a, (0, 36)); canvas.paste(b, (a.width + 6, 36))
        d = ImageDraw.Draw(canvas)
        d.text((10, 7), "MuJoCo", fill="#9FD3A2", font=head)
        d.text((a.width + 16, 7), "RViz: local costmap · footprint · /plan", fill="#9DBBF0", font=head)
        clock = f"시뮬레이션 {k:2d} s"
        d.text((a.width - 10 - d.textlength(clock, font=head), 7), clock, fill="#FFD75F", font=head)
        frames.append(captioned(canvas, text)); durs.append(650)
    durs[0], durs[-1] = 1500, 3000
    write(frames, durs, name, colors=128)


def crossing():
    avoid("crossing", [(0, 7, "① 접근: 근로자가 통로를 가로질러 온다 (/plan 은 처음 그대로)"), (7, 9, "② 감지 · 우회: 길이 막혀 /plan 이 다시 그려진다"),
                       (9, 12, "③ 근로자가 지나간 쪽으로 새 경로 · 제자리 회전"), (12, 23, "④ 재개: 비워진 통로로 목표까지")], "lesson06_crossing.gif")


def headon():
    avoid("headon", [(0, 7, "근로자가 정면에서 걸어온다 (0.4 m/s)"), (7, 8, "다가온다: costmap 에는 '지금 있는 자리' 만 있다"),
                     (8, 9, "겹친다: 최소 거리 0.15 m (충돌)"), (9, 23, "지나간 뒤에야 길이 열려 다시 출발")], "lesson06_headon.gif")


ALL = {f.__name__: f for f in (square, map_growth, goal_run, amcl, crossing, headon)}

if __name__ == "__main__":
    for n in sys.argv[1:] or ALL:
        ALL[n]()
