#!/usr/bin/env python3
"""강좌 환경 점검. 수업 전에 한 번 실행하고 결과(artifacts/doctor_report.txt)를 강사에게 보낸다.

    ./scripts/mobile_openarm doctor           # 기본 점검 (약 10초)
    ./scripts/mobile_openarm doctor --api     # + OpenAI API 실제 호출 (키·네트워크 확인)

✅ 통과  ⚠️ 경고(수업은 가능하지만 확인 필요)  ❌ 실패(수업 전에 해결해야 함)
종료 코드: ❌ 가 하나라도 있으면 1.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
OK, WARN, FAIL = "✅", "⚠️ ", "❌"
results = []  # (status, name, detail)


def add(status, name, detail=""):
    results.append((status, name, detail))
    print(f"{status} {name:<26} {detail}", flush=True)


def section(title):
    print(f"\n== {title}", flush=True)


def check_system():
    section("PC / OS")
    osr = {}
    if Path("/etc/os-release").exists():
        for line in Path("/etc/os-release").read_text().splitlines():
            k, _, v = line.partition("=")
            osr[k] = v.strip('"')
    name = osr.get("PRETTY_NAME", platform.platform())
    add(OK if osr.get("VERSION_ID") == "24.04" else FAIL, "Ubuntu 24.04", name)
    add(OK if platform.machine() == "x86_64" else WARN, "CPU 아키텍처", platform.machine())
    cores = os.cpu_count() or 0
    add(OK if cores >= 4 else WARN, "CPU 코어 (4+)", f"{cores}개")
    try:
        kb = int(next(l for l in open("/proc/meminfo") if l.startswith("MemTotal")).split()[1])
        gb = kb / 1024 / 1024
        add(OK if gb >= 15 else WARN, "RAM (16GB+)", f"{gb:.1f} GB")
    except Exception as e:  # noqa: BLE001
        add(WARN, "RAM (16GB+)", f"확인 불가: {e}")
    free = shutil.disk_usage(WS).free / 1e9
    add(OK if free >= 10 else WARN, "디스크 여유 (10GB+)", f"{free:.0f} GB")
    try:
        flags = open("/proc/cpuinfo").read()
        add(OK if " avx2" in flags else WARN, "AVX2", "있음" if " avx2" in flags else "없음 (YOLO 추론이 느릴 수 있음)")
    except OSError:
        pass
    disp = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    add(OK if disp else WARN, "디스플레이", disp or "없음 (원격/SSH 셸이면 viewer·RViz 창이 뜨지 않음)")


def check_ros():
    section("ROS 2")
    distro = os.environ.get("ROS_DISTRO")
    add(OK if distro == "jazzy" else FAIL, "ROS_DISTRO=jazzy", distro or "없음")
    pkgs = []
    for line in (WS / "scripts/apt_packages.txt").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            pkgs.append(line)
    missing = [p for p in pkgs if subprocess.run(["dpkg", "-s", p], capture_output=True).returncode != 0]
    add(OK if not missing else FAIL, f"apt 패키지 {len(pkgs)}개",
        "모두 설치됨" if not missing else "없음: " + " ".join(missing) + "  → ./scripts/install_lecture.sh")
    rmw = os.environ.get("RMW_IMPLEMENTATION", "기본(FastDDS)")
    add(OK if rmw == "rmw_cyclonedds_cpp" else WARN, "RMW", rmw)
    add(OK if os.environ.get("ROS_DOMAIN_ID") == "43" else WARN, "ROS_DOMAIN_ID", os.environ.get("ROS_DOMAIN_ID", "없음"))


def check_python():
    section("Python / venv")
    venv = WS / ".venv-mobile-openarm"
    add(OK if Path(sys.prefix) == venv else FAIL, "강좌 venv 사용", sys.prefix)
    add(OK if sys.version_info[:2] == (3, 12) else FAIL, "Python 3.12", platform.python_version())
    cfg = venv / "pyvenv.cfg"
    if cfg.exists():
        home = next((l.split("=", 1)[1].strip() for l in cfg.read_text().splitlines() if l.startswith("home")), "")
        add(OK if home.rstrip("/") == "/usr/bin" else FAIL, "venv 기반 Python", home + ("" if home.rstrip("/") == "/usr/bin" else "  → conda 등으로 만들어짐, install_lecture.sh 재실행"))
    mods = [  # (import 이름, 표시 이름, 버전 조건 설명, 조건 함수)
        ("rclpy", "rclpy (ROS)", None, None),
        ("mujoco", "mujoco", "3.6.0", lambda v: v == "3.6.0"),
        ("numpy", "numpy", "<2", lambda v: int(v.split(".")[0]) < 2),
        ("cv2", "opencv-python", "<4.11", lambda v: tuple(map(int, v.split(".")[:2])) < (4, 11)),
        ("torch", "torch (CPU)", None, None),
        ("ultralytics", "ultralytics", None, None),
        ("openvino", "openvino", None, None),
        ("onnxruntime", "onnxruntime", None, None),
        ("openai", "openai", None, None),
        ("flask", "flask", None, None),
        ("scipy", "scipy (apt)", None, None),
    ]
    for mod, label, want, ok in mods:
        r = subprocess.run([sys.executable, "-c", f"import {mod}; print(getattr({mod}, '__version__', '-'))"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            err = (r.stderr.strip().splitlines() or ["import 실패"])[-1]
            add(FAIL, label, err[:110])
            continue
        v = (r.stdout.strip().splitlines() or ["-"])[-1].strip()  # 첫 import 안내문(ultralytics 등)은 버린다
        good = ok is None or v == "-" or ok(v)
        add(OK if good else FAIL, label, v + ("" if good else f"  (필요: {want})"))
    sys.path.insert(0, str(WS / "scripts"))
    try:
        from check_pip_deps import check
        errors, warnings = check([WS / "requirements-mobile-openarm.txt", WS / "requirements-lecture.txt"], out=lambda *a: None)
        if errors:
            add(FAIL, "pip 의존성", errors[0][:110])
        elif warnings:
            add(OK, "pip 의존성", f"강의 무관 apt 충돌 {len(warnings)}건 무시 (예: {warnings[0][:60]})")
        else:
            add(OK, "pip 의존성", "충돌 없음")
    except Exception as e:  # noqa: BLE001
        add(WARN, "pip 의존성", f"확인 불가: {e}")


def check_build():
    section("빌드")
    weights = WS / "weights/warehouse_yolo11n_s320_320_openvino_model"
    add(OK if weights.exists() else FAIL, "YOLO 가중치", weights.name if weights.exists() else "없음 (git clone 이 불완전)")
    setup = WS / "install/local_setup.bash"
    add(OK if setup.exists() else FAIL, "colcon 빌드", "install/ 있음" if setup.exists() else "없음 → ./scripts/mobile_openarm build")
    if not setup.exists():
        return
    for pkg in ["mobile_openarm_bringup", "warehouse_lecture", "warehouse_skills", "warehouse_interfaces"]:
        d = WS / "install" / pkg
        if not d.exists():
            add(FAIL, pkg, "빌드 안 됨 → ./scripts/mobile_openarm build")
    r = subprocess.run([sys.executable, "-c", "import warehouse_interfaces.msg, warehouse_lecture"],
                       capture_output=True, text=True, timeout=60)
    add(OK if r.returncode == 0 else FAIL, "강좌 패키지 import",
        "warehouse_interfaces, warehouse_lecture" if r.returncode == 0 else (r.stderr.strip().splitlines() or ["?"])[-1][:110])


RENDER = r"""
import time, mujoco
m = mujoco.MjModel.from_xml_string('<mujoco><worldbody><light pos="0 0 3"/><geom type="plane" size="2 2 .1"/>'
                                   '<body pos="0 0 .5"><freejoint/><geom type="box" size=".1 .1 .1"/></body></worldbody></mujoco>')
d = mujoco.MjData(m); mujoco.mj_forward(m, d)
r = mujoco.Renderer(m, 240, 320)
t = time.perf_counter(); n = 0
while time.perf_counter() - t < 1.0:
    r.update_scene(d); r.render(); n += 1
print(n)
"""


def check_render():
    section("MuJoCo 렌더링 (OpenGL)")
    try:
        r = subprocess.run([sys.executable, "-c", RENDER], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        add(FAIL, "오프스크린 렌더링", "60초 안에 끝나지 않음")
        return
    if r.returncode != 0:
        add(FAIL, "오프스크린 렌더링", (r.stderr.strip().splitlines() or ["실패"])[-1][:110])
    else:
        fps = int(r.stdout.strip() or 0)
        add(OK if fps >= 30 else WARN, "오프스크린 렌더링", f"320x240 {fps} FPS"
            + ("" if fps >= 30 else "  (느림: 저사양 모드 권장, scripts/check_gpu.py 참고)"))


def check_openai(online):
    section("OpenAI")
    key = ""
    env = WS / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENAI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
    key = key or os.environ.get("OPENAI_API_KEY", "")
    if not env.exists():
        add(WARN, ".env", "없음 → cp .env.example .env 후 키 입력 (LLM 모듈에서 필요)")
    elif not key or key in ("sk-...", "sk-"):
        add(WARN, "OPENAI_API_KEY", "비어 있음 (LLM 모듈 전에 입력)")
    else:
        add(OK, "OPENAI_API_KEY", f"{key[:7]}…{key[-4:]}")
    if online and key and key not in ("sk-...", "sk-"):
        try:
            from openai import OpenAI
            t = time.perf_counter()
            OpenAI(api_key=key, timeout=20).models.list()
            add(OK, "OpenAI API 호출", f"{(time.perf_counter() - t) * 1000:.0f} ms")
        except Exception as e:  # noqa: BLE001
            add(FAIL, "OpenAI API 호출", f"{type(e).__name__}: {str(e)[:90]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", action="store_true", help="OpenAI API 를 실제로 호출해 키·네트워크를 확인")
    args = ap.parse_args()
    git = subprocess.run(["git", "-C", str(WS), "describe", "--tags", "--always", "--dirty"], capture_output=True, text=True)
    print(f"mobile_openarm doctor  ({time.strftime('%Y-%m-%d %H:%M')}, 코드 버전 {git.stdout.strip() or '?'})")
    for step in (check_system, check_ros, check_python, check_build, check_render):
        try:
            step()
        except Exception as e:  # noqa: BLE001 - 점검 하나가 죽어도 나머지는 계속
            add(FAIL, step.__name__, f"점검 중 오류: {e}")
    check_openai(args.api)

    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    print("\n" + "=" * 60)
    if fails:
        print(f"{FAIL} 실패 {len(fails)}건, 경고 {len(warns)}건: 아래를 해결한 뒤 다시 실행하세요.")
        for _, n, d in fails:
            print(f"   - {n}: {d}")
    else:
        print(f"{OK} 수업 준비 완료 (경고 {len(warns)}건)")
    report = WS / "artifacts/doctor_report.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(f"{s} {n}: {d}" for s, n, d in results) + "\n", encoding="utf-8")
    print(f"결과 저장: {report.relative_to(WS)}  (이 파일이나 화면 캡처를 강사에게 보내 주세요)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
