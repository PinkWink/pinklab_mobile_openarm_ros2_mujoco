#!/usr/bin/env bash
# 강좌용 설치: Ubuntu 24.04 + ROS 2 Jazzy native. GPU 불필요, OpenAI API 사용.
# ROS 2 Jazzy(/opt/ros/jazzy)만 설치되어 있으면 나머지는 이 스크립트가 처리한다.
#   ./scripts/install_lecture.sh
# 빠진 apt 패키지 설치, rosdep 초기화, venv, pip, 빌드, 단위 테스트까지 한 번에 진행하며
# 여러 번 실행해도 안전하다. 끝나면 ./scripts/mobile_openarm doctor 로 점검한다.
set -eo pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WS"
fail() { echo "❌ $*" >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || fail 'This installer targets Ubuntu 24.04; use install_mobile_openarm.sh on macOS'
SUDO=""; [[ $EUID -eq 0 ]] || SUDO=sudo
# conda base 가 자동 활성화된 PC가 많다. venv는 반드시 Ubuntu 시스템 Python(rclpy와 같은 3.12)으로 만든다.
SYS_PY=/usr/bin/python3
[[ -n "${CONDA_PREFIX:-}" ]] && echo "  ⚠️ conda 환경($CONDA_PREFIX)이 켜져 있습니다. 설치는 시스템 Python($SYS_PY)으로 진행합니다."
unset PYTHONPATH PYTHONHOME

echo "== ROS 2 Jazzy"
if [[ "${ROS_DISTRO:-}" != jazzy ]]; then
  [[ -f /opt/ros/jazzy/setup.bash ]] || fail 'ROS 2 Jazzy가 없습니다. https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html 대로 ros-jazzy-desktop을 먼저 설치하세요.'
  set +e; source /opt/ros/jazzy/setup.bash; set -e
fi
# PATH 에서 conda 경로를 빼서 rosdep·colcon·python 이 conda 쪽으로 잡히지 않게 한다.
[[ -n "${CONDA_PREFIX:-}" ]] && PATH="$(tr ':' '\n' <<<"$PATH" | grep -v "^${CONDA_PREFIX%/envs/*}" | paste -sd: -)"

echo "== apt packages (scripts/apt_packages.txt)"
MISSING=""
while read -r pkg; do
  pkg="${pkg%%#*}"; pkg="${pkg//[[:space:]]/}"
  [[ -z "$pkg" ]] && continue
  dpkg -s "$pkg" >/dev/null 2>&1 || MISSING="$MISSING $pkg"
done < scripts/apt_packages.txt
if [[ -n "$MISSING" ]]; then
  echo "  설치합니다:$MISSING  (sudo 비밀번호를 물을 수 있습니다)"
  $SUDO apt-get update
  # 강의실 와이파이에서 미러 연결이 끊기는 일이 잦다. 재시도하고, 그래도 실패하면 받은 데까지 두고 한 번 더 시도한다.
  # shellcheck disable=SC2086
  $SUDO apt-get install -y -o Acquire::Retries=5 $MISSING \
    || { echo "  ⚠️ 다운로드 실패, 한 번 더 시도합니다."; $SUDO apt-get update && $SUDO apt-get install -y -o Acquire::Retries=5 --fix-missing $MISSING; } \
    || fail "apt 설치 실패(네트워크). 받은 패키지는 보존되므로 ./scripts/install_lecture.sh 를 다시 실행하면 이어서 설치합니다."
fi

echo "== rosdep"
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  $SUDO rosdep init || fail 'rosdep init 실패'
fi
[[ -d "$HOME/.ros/rosdep/sources.cache" ]] || rosdep update --rosdistro jazzy || fail 'rosdep update 실패 (네트워크 확인)'
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy \
  --skip-keys "ament_python warehouse_interfaces" \
  || echo "  ⚠️ rosdep 일부 실패. 필수 패키지는 위 apt 단계에서 설치했으므로 계속 진행합니다."

echo "== Python venv (system site packages for rclpy)"
VENV=.venv-mobile-openarm
# 예전에 conda Python 등 다른 인터프리터로 만든 venv면 다시 만든다.
if [[ -f $VENV/pyvenv.cfg ]] && ! grep -qE '^home = /usr/bin/?$' $VENV/pyvenv.cfg; then
  echo "  기존 venv가 시스템 Python으로 만들어지지 않아 다시 만듭니다."; rm -rf $VENV
fi
[[ -n "${VIRTUAL_ENV:-}" ]] && { PATH="${PATH//$VIRTUAL_ENV\/bin:/}"; unset VIRTUAL_ENV; }
$SYS_PY -m venv --system-site-packages $VENV
source .venv-mobile-openarm/bin/activate
export PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_RETRIES=10 PIP_DEFAULT_TIMEOUT=60   # torch 등 큰 휠이 느린 망에서 끊기지 않게
python -m pip install -q --upgrade "pip<26"
python -m pip install -q -r requirements-mobile-openarm.txt
python -m pip install -q -r requirements-lecture.txt
# pip check는 시스템 apt 패키지끼리의 충돌(예: apt yt-dlp ↔ websockets)까지 보고하므로
# 강의 의존 트리와 venv에 걸린 충돌만 오류로 판정한다.
python scripts/check_pip_deps.py requirements-mobile-openarm.txt requirements-lecture.txt \
  || fail 'pip 의존성 충돌이 있습니다. 위 ERROR 줄과 requirements-lecture.txt의 고정 버전을 확인하세요.'

echo "== .env"
[[ -f .env ]] || { cp .env.example .env; echo "  .env 를 만들었습니다. OPENAI_API_KEY 를 채우세요."; }

echo "== build"
export MOBILE_ENV_MODE=native
python -m colcon build --symlink-install --base-paths src \
  --packages-up-to mobile_openarm_bringup warehouse_lecture warehouse_skills \
  --event-handlers desktop_notification-

echo "== quick test (no simulator)"
source install/local_setup.bash
export MOBILE_OPENARM_MODEL_DIR="$WS/artifacts/mobile_generated"
python -m pytest tests -q -x

cat <<EOF

✅ 설치 완료. 어느 터미널에서든 source 없이 바로 실행하면 됩니다:
  ./scripts/mobile_openarm doctor         # 환경 점검 (결과를 강사에게 보내 주세요)
  ./scripts/mobile_openarm start          # lite 프로파일 (카메라 2대, 320x240, 2 FPS)
EOF
