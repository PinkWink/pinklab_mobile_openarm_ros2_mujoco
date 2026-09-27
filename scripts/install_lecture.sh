#!/usr/bin/env bash
# 강좌용 설치: Ubuntu 24.04 + ROS 2 Jazzy native. GPU 불필요, OpenAI API 사용.
#   sudo apt install python3-venv python3-colcon-common-extensions python3-rosdep portaudio19-dev
#   source /opt/ros/jazzy/setup.bash
#   ./scripts/install_lecture.sh
set -eo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WS"
[[ "${ROS_DISTRO:-}" == jazzy ]] || { echo 'source /opt/ros/jazzy/setup.bash first' >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo 'This installer targets Ubuntu 24.04; use install_mobile_openarm.sh on macOS' >&2; exit 1; }

echo "== ROS dependencies (rosdep)"
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy \
  --skip-keys "ament_python warehouse_interfaces" || true
for pkg in ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-geometry-msgs; do
  dpkg -s "$pkg" >/dev/null 2>&1 || MISSING="$MISSING $pkg"
done
if [[ -n "${MISSING:-}" ]]; then
  echo "설치가 필요한 apt 패키지:$MISSING"
  echo "  sudo apt install$MISSING"
  exit 1
fi

echo "== Python venv (system site packages for rclpy)"
python3 -m venv --system-site-packages .venv-mobile-openarm
source .venv-mobile-openarm/bin/activate
python -m pip install -q --upgrade "pip<26"
python -m pip install -q -r requirements-mobile-openarm.txt
python -m pip install -q -r requirements-lecture.txt
python -m pip check || { echo 'pip 의존성 충돌이 있습니다. requirements-lecture.txt의 고정 버전을 확인하세요.' >&2; exit 1; }

echo "== .env"
[[ -f .env ]] || { cp .env.example .env; echo "  .env 를 만들었습니다. OPENAI_API_KEY 를 채우세요."; }

echo "== build"
export MOBILE_ENV_MODE=native
python -m colcon build --symlink-install --base-paths src \
  --packages-up-to mobile_openarm_bringup warehouse_lecture

echo "== quick test (no simulator)"
source install/local_setup.bash
export MOBILE_OPENARM_MODEL_DIR="$WS/artifacts/mobile_generated"
python -m pytest tests -q -x

cat <<EOF

설치 완료. 새 터미널마다:
  source /opt/ros/jazzy/setup.bash
  source .venv-mobile-openarm/bin/activate
  ./scripts/mobile_openarm start          # lite 프로파일 (카메라 2대, 320x240, 2 FPS)
EOF
