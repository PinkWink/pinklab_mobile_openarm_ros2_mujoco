"""Figures for the low-spec PC section of the setup & usage page. Output: docs/camp/setup_lowspec_*.png

setup_lowspec_profile.png  real offscreen renders of the viewer start view: full / lite / minimal
setup_lowspec_check.png    real scripts/check_gpu.py output on a Ryzen 7 9700X integrated GPU
setup_lowspec_nvidia.png   real scripts/check_gpu.py output with PRIME render offload to the RTX 5060 Ti
setup_lowspec_config.png   real launch output: sim_config.yaml read by the wrapper and by ros2 launch
setup_lowspec_config_file.png  `cat sim_config.yaml` of the repository file
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
from mobile_openarm_mujoco.bridge import show_simple_meshes  # noqa: E402

XML = HERE.parents[1] / "artifacts/mobile_generated/warehouse.xml"


def profile():
    m = mujoco.MjModel.from_xml_path(str(XML))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    r = mujoco.Renderer(m, 720, 1280)
    cam = mujoco.MjvCamera()  # the viewer's start view
    cam.lookat[:] = [0, 0, 0.5]
    cam.distance, cam.azimuth, cam.elevation = 14, 130, -50
    close = mujoco.MjvCamera()  # the robot up close
    close.lookat[:] = [0, 0, 0.7]
    close.distance, close.azimuth, close.elevation = 2.6, 200, -20
    opt = mujoco.MjvOption()
    opt.geomgroup[1] = 0

    def shot(view, option, shadows):
        r.update_scene(d, view, option)
        r.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = shadows
        return r.render().copy()

    rows = [[shot(v, opt, True) for v in (cam, close)], [shot(v, opt, False) for v in (cam, close)]]
    show_simple_meshes(m)  # what --viewer-simple-meshes does in the bridge
    rows.append([shot(v, mujoco.MjvOption(), False) for v in (cam, close)])
    r.close()
    # FPS measured by scripts/check_gpu.py on a Ryzen 7 9700X integrated GPU (1280x720).
    titles = ["full  ·  그림자 켬  ·  19 FPS", "lite (기본)  ·  그림자 끔  ·  121 FPS", "minimal  ·  단순 형상  ·  301 FPS"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 6.9), dpi=150)
    for col, (pair, title) in enumerate(zip(rows, titles)):
        for row, img in enumerate(pair):
            axes[row, col].imshow(img[:, 160:1120] if row else img)
            axes[row, col].axis("off")
        axes[0, col].set_title(title, fontsize=13, family=SANS, fontweight="bold")
    fig.text(0.5, 0.02, "Ryzen 7 9700X 내장 그래픽 · 1280×720 · scripts/check_gpu.py 측정 · 카메라 영상은 세 프로파일 모두 실제 메시",
             ha="center", fontsize=10, family=SANS, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(HERE / "setup_lowspec_profile.png", facecolor="white")
    plt.close(fig)


CHECK = "./scripts/mobile_openarm exec python3 scripts/check_gpu.py"


def check():
    render([("prompt", CHECK),
            ("out", "OpenGL 렌더러      : AMD Ryzen 7 9700X 8-Core Processor (radeonsi, raphael_mendocino, LLVM 20.1.2, ...)"),
            ("out", "NVIDIA GPU         : 있음, 하지만 렌더링에 쓰이지 않음"),
            ("out", "측정 중 (약 15초) ..."),
            ("out", "뷰어 1280x720 full    (그림자 켬)       :   19.1 FPS"),
            ("out", "뷰어 1280x720 lite    (그림자 끔)       :  120.5 FPS"),
            ("out", "뷰어 1280x720 minimal (단순 형상)       :  301.3 FPS"),
            ("out", "카메라 320x240 한 장 (그림자 켬 / 끔)   :   46.4 / 5.9 ms"),
            ("out", "권장               : sim_config.yaml 의 profile: lite (기본값)로 충분합니다."),
            ("out", "NVIDIA 로 렌더링   : __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia ./scripts/mobile_openarm start")],
           HERE / "setup_lowspec_check.png", highlight=("권장", "뷰어 1280x720 minimal"))


def nvidia():
    render([("prompt", "__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia " + CHECK),
            ("out", "OpenGL 렌더러      : NVIDIA GeForce RTX 5060 Ti/PCIe/SSE2"),
            ("out", "측정 중 (약 15초) ..."),
            ("out", "뷰어 1280x720 full    (그림자 켬)       :  207.6 FPS"),
            ("out", "뷰어 1280x720 lite    (그림자 끔)       :  868.6 FPS"),
            ("out", "뷰어 1280x720 minimal (단순 형상)       : 1660.1 FPS"),
            ("out", "카메라 320x240 한 장 (그림자 켬 / 끔)   :    2.1 / 0.1 ms"),
            ("out", "권장               : sim_config.yaml 의 profile: lite (기본값)로 충분합니다.")],
           HERE / "setup_lowspec_nvidia.png", highlight=("OpenGL 렌더러",), width=16.0)


def config():
    path = "[sim_config] /home/pw/mujoco_ros2/mobile_openarm_ws/sim_config.yaml"
    cams = "camera_names=base_camera,head_camera camera_size=320x240 camera_fps=2 rviz_fps=10"
    render([("prompt", "sed -i 's/^profile: lite/profile: minimal/' sim_config.yaml     # 편집기로 고쳐도 같음"),
            ("prompt", "./scripts/mobile_openarm drive"),
            ("out", path),
            ("out", "[sim_config] profile=minimal viewer=true rviz=true viewer_shadows=false viewer_meshes=simple camera_shadows=false"),
            ("out", "             " + cams),
            ("out", ""),
            ("prompt", "ros2 launch mobile_openarm_bringup warehouse.launch.py mode:=drive moveit:=false rviz:=false"),
            ("out", path),
            ("out", "[sim_config] profile=minimal viewer=true rviz=false viewer_shadows=false viewer_meshes=simple camera_shadows=false"),
            ("out", "             " + cams)],
           HERE / "setup_lowspec_config.png", highlight=("[sim_config] profile",), width=16.0)


def config_file():
    text = (HERE.parents[1] / "sim_config.yaml").read_text().splitlines()
    render([("prompt", "cat sim_config.yaml")] + [("out", line) for line in text],
           HERE / "setup_lowspec_config_file.png", highlight=("profile: lite",), width=16.0)


if __name__ == "__main__":
    profile()
    check()
    nvidia()
    config()
    config_file()
