"""Figures for the low-spec PC section of the setup & usage page. Output: docs/camp/setup_lowspec_*.png

setup_lowspec_profile.png  real offscreen renders of the viewer start view, shadows on (full) vs off (lite)
setup_lowspec_check.png    real scripts/check_gpu.py output on a Ryzen 7 9700X integrated GPU
setup_lowspec_nvidia.png   real scripts/check_gpu.py output with PRIME render offload to the RTX 5060 Ti
(setup_lowspec_noviewer.png is a screen capture of `start viewer:=false`, taken by hand with `import -window`.)
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mujoco  # noqa: E402

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from render_terminal import SANS, render  # noqa: E402

XML = HERE.parents[1] / "artifacts/mobile_generated/warehouse.xml"


def profile():
    m = mujoco.MjModel.from_xml_path(str(XML))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 720, 1280)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = [0, 0, 0.5]
    cam.distance, cam.azimuth, cam.elevation = 14, 130, -50
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0
    images = []
    for shadows in (True, False):
        r.update_scene(d, cam, opt)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = shadows
        images.append(r.render().copy())
    r.close()
    # FPS measured by scripts/check_gpu.py on a Ryzen 7 9700X integrated GPU (1280x720).
    titles = ["profile:=full  ·  그림자 켬  ·  19 FPS", "profile:=lite (기본)  ·  그림자 끔  ·  120 FPS"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.6), dpi=150)
    for ax, img, title in zip(axes, images, titles):
        ax.imshow(img)
        ax.set_title(title, fontsize=13, family=SANS, fontweight="bold")
        ax.axis("off")
    fig.text(0.5, 0.02, "Ryzen 7 9700X 내장 그래픽 · 1280×720 · scripts/check_gpu.py 측정 · 카메라 영상은 두 프로파일 모두 그림자 유지",
             ha="center", fontsize=10, family=SANS, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(HERE / "setup_lowspec_profile.png", facecolor="white")
    plt.close(fig)


CHECK = "./scripts/mobile_openarm exec python3 scripts/check_gpu.py"


def check():
    render([("prompt", CHECK),
            ("out", "OpenGL 렌더러      : AMD Ryzen 7 9700X 8-Core Processor (radeonsi, raphael_mendocino, LLVM 20.1.2, ...)"),
            ("out", "NVIDIA GPU         : 있음, 하지만 렌더링에 쓰이지 않음"),
            ("out", "측정 중 (약 10초) ..."),
            ("out", "뷰어 1280x720 그림자 켬 (profile:=full) :   19.1 FPS"),
            ("out", "뷰어 1280x720 그림자 끔 (profile:=lite) :  119.9 FPS"),
            ("out", "카메라 320x240 한 장                    :   46.9 ms"),
            ("out", "권장               : 기본 실행(profile:=lite)으로 충분합니다."),
            ("out", "NVIDIA 로 렌더링   : __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./scripts/mobile_openarm start")],
           HERE / "setup_lowspec_check.png", highlight=("권장", "그림자 끔"))


def nvidia():
    render([("prompt", "__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia " + CHECK),
            ("out", "OpenGL 렌더러      : NVIDIA GeForce RTX 5060 Ti/PCIe/SSE2"),
            ("out", "측정 중 (약 10초) ..."),
            ("out", "뷰어 1280x720 그림자 켬 (profile:=full) :  207.6 FPS"),
            ("out", "뷰어 1280x720 그림자 끔 (profile:=lite) :  869.2 FPS"),
            ("out", "카메라 320x240 한 장                    :    2.1 ms"),
            ("out", "권장               : 기본 실행(profile:=lite)으로 충분합니다.")],
           HERE / "setup_lowspec_nvidia.png", highlight=("OpenGL 렌더러",), width=16.0)


if __name__ == "__main__":
    profile()
    check()
    nvidia()
