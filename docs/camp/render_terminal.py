"""Render real terminal output as a terminal-styled PNG (dark window, green prompt).

    from render_terminal import render
    render([("prompt", "ros2 topic list"), ("out", "/clock"), ...], "docs/camp/x.png")
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

MONO = "NanumGothicCoding" if any(f.name == "NanumGothicCoding" for f in font_manager.fontManager.ttflist) else "DejaVu Sans Mono"
SANS = "NanumGothic" if any(f.name == "NanumGothic" for f in font_manager.fontManager.ttflist) else "DejaVu Sans"
from matplotlib.patches import FancyBboxPatch

PROMPT = "pw@laptop:~/mujoco_ros2/mobile_openarm_ws$ "


def render(lines, out, title="pw@laptop: ~/mujoco_ros2/mobile_openarm_ws — bash", highlight=()):
    W, LH = 14.0, 0.36
    H = LH * len(lines) + 1.0
    fig, ax = plt.subplots(figsize=(W, H), dpi=150); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.1, 0.1), W - 0.2, H - 0.2, boxstyle="round,pad=0,rounding_size=0.15", fc="#1E1E1E", ec="#444444", lw=1))
    ax.add_patch(FancyBboxPatch((0.1, H - 0.55), W - 0.2, 0.45, boxstyle="round,pad=0,rounding_size=0.15", fc="#2D2D2D", ec="none"))
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        ax.add_patch(plt.Circle((0.4 + i * 0.28, H - 0.32), 0.08, fc=c, ec="none"))
    ax.text(W / 2, H - 0.32, title, ha="center", va="center", fontsize=9, color="#BBBBBB", family=SANS)
    y = H - 0.95
    for kind, text in lines:
        if kind == "prompt":
            t = ax.text(0.35, y, PROMPT, va="center", fontsize=9.6, color="#5FD75F", family=MONO)
            fig.canvas.draw()
            x1 = ax.transData.inverted().transform((t.get_window_extent().x1, 0))[0]
            ax.text(x1, y, text, va="center", fontsize=9.6, color="#FFFFFF", family=MONO)
        else:
            col = "#FFD75F" if any(h in text for h in highlight) else "#E0E0E0"
            ax.text(0.35, y, text, va="center", fontsize=9.6, color=col, family=MONO)
        y -= LH
    fig.savefig(out, bbox_inches="tight", facecolor="white", pad_inches=0.05)
    plt.close(fig)
