"""Captioned GIF of MuJoCo and RViz moving together, from the screenshots of record_lesson01c_motion.py.

  python3 docs/camp/make_lesson01c_motion_gif.py artifacts/dev/l01c/motion     # run from the workspace root
Output: docs/camp/lesson01c_run_motion.gif
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
F_CAP, F_HEAD, F_HUD = (ImageFont.truetype(BOLD, s) for s in (25, 20, 17))
H, WM, WR, TOP, BAR = 450, 550, 650, 40, 64          # panel height, MuJoCo / RViz widths, header, subtitle bar


def caption(i, n_up):
    if i < 2:
        return "처음: 팔이 수직 · 팔 끝 카메라는 하늘을 본다 (영상이 검다)", 1300
    if i < 2 + n_up // 3:
        return "/cmd 목표를 조금씩 올린다 → MuJoCo 의 팔이 움직인다", 220
    if i < 2 + 2 * n_up // 3:
        return "RViz 는 /joint_states 만 받아서 같은 자세를 그린다", 220
    if i < 2 + n_up:
        return "팔 끝 카메라에 상자가 들어온다 (MuJoCo 가 렌더 → RViz 에 표시)", 260
    if i < 4 + n_up:
        return "목표 [0.6, 1.5] 도착 · 두 화면이 같은 자세", 1500
    return "다시 [0.0, 0.0] 으로 돌아간다", 160


def main():
    src = Path(sys.argv[1])
    steps = json.loads((src / "steps.json").read_text())
    n_up = 24
    frames, durations = [], []
    for i, st in enumerate(steps):
        img = Image.new("RGB", (WM + WR, TOP + H + BAR), "#111111")
        img.paste(Image.open(src / f"mj_{i:03d}.png").convert("RGB").resize((WM, H), Image.LANCZOS), (0, TOP))
        img.paste(Image.open(src / f"rviz_{i:03d}.png").convert("RGB").resize((WR, H), Image.LANCZOS), (WM, TOP))
        d = ImageDraw.Draw(img)
        d.text((12, 9), "MuJoCo (물리)", fill="#9FD3A2", font=F_HEAD)
        d.text((WM + 12, 9), "RViz (URDF + /joint_states → TF)", fill="#9DBBF0", font=F_HEAD)
        hud = f"/cmd [{st['cmd'][0]:.2f}, {st['cmd'][1]:.2f}]   /joint_states [{st['q'][0]:.2f}, {st['q'][1]:.2f}]"
        d.text((WM - 12 - d.textlength(hud, font=F_HUD), 10), hud, fill="#FFD75F", font=F_HUD)
        text, ms = caption(i, n_up)
        d.text(((WM + WR - d.textlength(text, font=F_CAP)) / 2, TOP + H + 18), text, fill="white", font=F_CAP)
        frames.append(img); durations.append(ms)
    out = Path("docs/camp/lesson01c_run_motion.gif")
    pal = frames[2 + n_up].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=durations, loop=0, optimize=False)
    print("saved", out, len(frames), "frames", f"{sum(durations) / 1000:.1f} s", f"{out.stat().st_size / 1e6:.1f} MB")
    frames[20].save(src.parent / "motion_gif_20.png"); frames[27].save(src.parent / "motion_gif_27.png")


if __name__ == "__main__":
    main()
