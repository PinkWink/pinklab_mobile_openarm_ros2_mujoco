"""Measure how fast this PC renders the warehouse and suggest launch options.

    ./scripts/mobile_openarm exec python3 scripts/check_gpu.py
    __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./scripts/mobile_openarm exec python3 scripts/check_gpu.py

Needs the generated model: run ./scripts/mobile_openarm start once first.
"""

import os
import shutil
import sys
import time
from pathlib import Path

import mujoco

model_dir = Path(os.environ.get("MOBILE_OPENARM_MODEL_DIR", "artifacts/mobile_generated"))
xml = model_dir / "warehouse.xml"
if not xml.exists():
    sys.exit(f"{xml} 없음: ./scripts/mobile_openarm start 를 한 번 실행한 뒤 다시 시도하세요.")

model = mujoco.MjModel.from_xml_path(str(xml))
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
option = mujoco.MjvOption()
option.geomgroup[1] = 0  # visual meshes only, as in the viewer and cameras


# minimal profile: the viewer draws collision hulls, the cameras keep the visual meshes.
simple = mujoco.MjvOption()
simple.geomgroup[2] = 0
model.geom_rgba[model.geom_group == 1, 3] = 1.0


def fps(width, height, shadows, camera=None, seconds=3.0, scene_option=option):
    renderer = mujoco.Renderer(model, height, width)
    view = camera
    if view is None:  # the viewer's start view
        view = mujoco.MjvCamera()
        view.lookat[:] = [0, 0, 0.5]
        view.distance, view.azimuth, view.elevation = 14, 130, -50
    def draw():
        renderer.update_scene(data, view, scene_option)
        renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = shadows
        renderer.render()

    for _ in range(3):  # warm-up frames
        draw()
    frames, start = 0, time.perf_counter()
    while time.perf_counter() - start < seconds:
        draw()
        frames += 1
    renderer.close()
    return frames / (time.perf_counter() - start)


from OpenGL import GL  # noqa: E402  (valid once a Renderer has made a context)

probe = mujoco.Renderer(model, 64, 64)
renderer_name = GL.glGetString(GL.GL_RENDERER).decode()
probe.close()
nvidia_present = shutil.which("nvidia-smi") is not None or Path("/proc/driver/nvidia").exists()
on_nvidia = "NVIDIA" in renderer_name.upper()

print(f"OpenGL 렌더러      : {renderer_name}")
if nvidia_present and not on_nvidia:
    print("NVIDIA GPU         : 있음, 하지만 렌더링에 쓰이지 않음")
print("측정 중 (약 15초) ...")
full = fps(1280, 720, shadows=True)
lite = fps(1280, 720, shadows=False)
minimal = fps(1280, 720, shadows=False, scene_option=simple)
cam = 1000 / fps(320, 240, shadows=True, camera="head_camera")
cam_flat = 1000 / fps(320, 240, shadows=False, camera="head_camera")
print(f"뷰어 1280x720 full    (그림자 켬)       : {full:6.1f} FPS")
print(f"뷰어 1280x720 lite    (그림자 끔)       : {lite:6.1f} FPS")
print(f"뷰어 1280x720 minimal (단순 형상)       : {minimal:6.1f} FPS")
print(f"카메라 320x240 한 장 (그림자 켬 / 끔)   : {cam:6.1f} / {cam_flat:.1f} ms")

if lite >= 30:
    advice = "sim_config.yaml 의 profile: lite (기본값)로 충분합니다."
elif minimal >= 30:
    advice = "sim_config.yaml 에서 profile: minimal 로 바꾸세요."
else:
    advice = "sim_config.yaml 에서 profile: minimal, viewer: false 로 MuJoCo 창 없이 RViz 만 쓰세요."
print(f"권장               : {advice}")
if nvidia_present and not on_nvidia:
    print("NVIDIA 로 렌더링   : __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./scripts/mobile_openarm start")
