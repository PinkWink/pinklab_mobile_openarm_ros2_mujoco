"""Lesson 01 joint-command figures: bridge start (initial pose), terminal 2 /cmd, result after /cmd.

  python3 docs/camp/draw_lesson01_cmd_figures.py <capture dir>
  <capture dir> holds window grabs (import -window) of the real run:
    mj_before.png / rq_before.png   MuJoCo viewer + rqt_image_view right after the bridge starts
    mj_after.png  / rq_after.png    the same windows 4 s after ros2 topic pub /cmd [0.6, 1.5]
    pub.out                         stdout of that ros2 topic pub -1 command
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
MONO = "/usr/share/fonts/truetype/nanum/NanumGothicCoding.ttf"
SANS = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
PROMPT = "pw@laptop:~/mujoco_ros2/mobile_openarm_ws$ "


def side_by_side(left, right, out, width=2200, gap=0):
    """MuJoCo window (left) and rqt window (right) scaled to one height."""
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    h = a.height
    b = b.resize((round(b.width * h / b.height), h), Image.LANCZOS)
    canvas = Image.new("RGB", (a.width + gap + b.width, h), "white")
    canvas.paste(a, (0, 0)); canvas.paste(b, (a.width + gap, 0))
    canvas = canvas.resize((width, round(h * width / canvas.width)), Image.LANCZOS)
    canvas.save(out)


def terminal(title, lines, out, width=1642):
    """Terminal-styled PNG (same look as the other lesson01 terminal figures)."""
    mono, sans = ImageFont.truetype(MONO, 19), ImageFont.truetype(SANS, 18)
    lh, top = 42, 96
    h = top + lh * len(lines) + 24
    img = Image.new("RGB", (width, h), "white")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((18, 16, width - 18, h - 16), 20, fill="#1E1E1E", outline="#444444", width=2)
    d.rounded_rectangle((20, 18, width - 20, 70), 18, fill="#2D2D2D")
    d.rectangle((20, 50, width - 20, 70), fill="#2D2D2D")
    for i, c in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        x = 54 + i * 32
        d.ellipse((x - 9, 34, x + 9, 52), fill=c)
    d.text((width / 2, 44), title, font=sans, fill="#BBBBBB", anchor="mm")
    y = top + lh / 2
    for kind, text in lines:
        x = 48
        if kind == "prompt":
            d.text((x, y), PROMPT, font=mono, fill="#5FD75F", anchor="lm")
            x += d.textlength(PROMPT, font=mono)
        d.text((x, y), text, font=mono, fill="#DDDDDD", anchor="lm")
        y += lh
    img.save(out)


def main():
    cap = Path(sys.argv[1])
    side_by_side(cap / "mj_before.png", cap / "rq_before.png", HERE / "lesson01_run_result.png")
    side_by_side(cap / "mj_after.png", cap / "rq_after.png", HERE / "lesson01_cmd_result.png")
    pub = [l for l in (cap / "pub.out").read_text().splitlines() if l.strip() and "[WARN]" not in l]
    terminal("터미널 2 — 관절 명령 [0.6, 1.5]", [
        ("prompt", "source /opt/ros/jazzy/setup.bash"),
        ("prompt", "source scripts/env.sh"),
        ("out", "mobile_openarm env: domain 43, rmw rmw_cyclonedds_cpp, venv /home/pw/mujoco_ros2/mobile_openarm_ws/.venv-mobile-openarm"),
        ("prompt", 'ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"'),
        *[("out", l) for l in pub],
        ("prompt", ""),
    ], HERE / "lesson01_t2_cmd.png")


if __name__ == "__main__":
    main()
