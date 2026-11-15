"""Captioned GIF for the section "그대로 읽은 모델을 1 초 돌리면": the plain URDF model collapses, the converted one holds.

  MUJOCO_GL=egl python docs/camp/make_lesson01c_gif.py        # run from the workspace root (venv python)
Output: docs/camp/lesson01c_plain.gif
"""
import re
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LESSON = Path("lessons/01_mujoco_ros2")
sys.path.insert(0, str(LESSON))
from urdf_to_mjcf import URDF, build  # noqa: E402

W, H, BAR, FPS = 800, 450, 64, 15
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
F_CAP, F_HEAD, F_HUD = (ImageFont.truetype(BOLD, s) for s in (25, 22, 20))


def camera():
    cam = mujoco.MjvCamera()
    cam.lookat[:], cam.distance, cam.azimuth, cam.elevation = [0.2, 0.0, 0.2], 1.25, 90, -12
    return cam


def frame(renderer, data, cam, head, head_color, caption, speed):
    renderer.update_scene(data, cam)
    img = Image.new("RGB", (W, H + BAR), "#111111")
    img.paste(Image.fromarray(renderer.render()), (0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((12, 12, 24 + d.textlength(head, font=F_HEAD), 48), 8, fill=head_color)
    d.text((18, 17), head, fill="white", font=F_HEAD)
    hud = [f"t = {data.time:4.2f} s   ({speed})", f"joint1  {data.qpos[0]:6.3f} rad", f"joint2  {data.qpos[1]:6.3f} rad"]
    for i, line in enumerate(hud):
        d.text((W - 250, 14 + 26 * i), line, fill="#FFD75F" if i else "#DDDDDD", font=F_HUD)
    d.text(((W - d.textlength(caption, font=F_CAP)) / 2, H + 18), caption, fill="white", font=F_CAP)   # subtitle bar
    return img


def play(frames, model, data, renderer, cam, head, color, caption, t_end, video_s, speed):
    """Advance the simulation to t_end while emitting video_s seconds of frames."""
    n, t0 = int(video_s * FPS), data.time
    for k in range(1, n + 1):
        target = t0 + (t_end - t0) * k / n
        while data.time < target - 1e-9:
            mujoco.mj_step(model, data)
        frames.append(frame(renderer, data, cam, head, color, caption, speed))


def hold(frames, renderer, data, cam, head, color, caption, video_s):
    frames += [frame(renderer, data, cam, head, color, caption, "정지")] * int(video_s * FPS)


def main():
    frames, cam = [], camera()
    # ---- part 1: the URDF exactly as a ROS user has it (no <mujoco> tag, nothing added)
    plain = re.sub(r"<mujoco>.*?</mujoco>", "", URDF.read_text(), flags=re.S)
    model = mujoco.MjModel.from_xml_string(plain)
    model.vis.headlight.ambient[:] = 0.45                    # the model has no light: brighten the default headlight
    data = mujoco.MjData(model)
    data.qpos[:] = [0.6, 1.5]
    mujoco.mj_forward(model, data)
    model.vis.global_.offwidth, model.vis.global_.offheight = W, H    # offscreen buffer defaults to 640 x 480
    r = mujoco.Renderer(model, H, W)
    head, red = "URDF 를 그대로 읽은 모델", "#B3261E"
    hold(frames, r, data, cam, head, red, "관절 [0.6, 1.5] 자세에서 시작 · 바닥도 빛도 없다", 2.5)
    play(frames, model, data, r, cam, head, red, "① link1 이 base 원기둥과 충돌 → 밀려난다 (0.6 → 0.01 rad)", 0.2, 4.0, "0.05 배속")
    hold(frames, r, data, cam, head, red, "① link1 이 base 원기둥과 충돌 → 밀려난다 (0.6 → 0.01 rad)", 1.0)
    play(frames, model, data, r, cam, head, red, "② 액추에이터 0 개 → link2 가 중력에 처진다", 0.9, 4.0, "0.18 배속")
    play(frames, model, data, r, cam, head, red, "③ 관절 한계 2.0 rad 에 걸려서야 멈춘다", 1.2, 1.5, "0.2 배속")
    hold(frames, r, data, cam, head, red, "③ 관절 한계 2.0 rad 에 걸려서야 멈춘다", 1.5)
    r.close()
    # ---- part 2: the same URDF through urdf_to_mjcf.build()
    _, model = build()
    data = mujoco.MjData(model)
    data.qpos[:] = [0.6, 1.5]
    data.ctrl[:] = [0.6, 1.5]
    mujoco.mj_forward(model, data)
    model.vis.global_.offwidth, model.vis.global_.offheight = W, H    # offscreen buffer defaults to 640 x 480
    r = mujoco.Renderer(model, H, W)
    head, green = "urdf_to_mjcf.py 로 변환한 모델", "#2E7D32"
    hold(frames, r, data, cam, head, green, "같은 자세에서 다시 시작 · 바닥 · 빛 · 카메라 상자가 생겼다", 2.5)
    play(frames, model, data, r, cam, head, green, "충돌 제외 + 위치 액추에이터 → 자세를 버틴다", 1.2, 3.0, "0.4 배속")
    hold(frames, r, data, cam, head, green, "중력만큼 조금 처진 0.64 rad 에서 정지 (kp 30)", 2.5)
    r.close()

    out = Path("docs/camp/lesson01c_plain.gif")
    pal = frames[len(frames) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=round(1000 / FPS), loop=0, optimize=False)
    print("saved", out, len(frames), "frames", f"{out.stat().st_size / 1e6:.1f} MB")
    for i in (0, 60, 140, 200, 270, len(frames) - 1):         # stills for checking
        frames[min(i, len(frames) - 1)].save(f"artifacts/dev/l01c/gif_{i}.png")


if __name__ == "__main__":
    main()
