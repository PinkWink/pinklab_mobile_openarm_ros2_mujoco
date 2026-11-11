# source 해서 쓰는 환경 설정. wrapper(scripts/mobile_openarm)와 같은 환경을 현재 셸에 만든다.
#   source scripts/env.sh      (ROS 2 Jazzy와 venv가 꺼져 있으면 자동으로 켠다)
# 이후 ros2 launch / ros2 run / ros2 topic ... 을 직접 실행할 수 있다.
_WS="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
if [[ "${ROS_DISTRO:-}" != jazzy ]]; then
  if [[ -n "${ZSH_VERSION:-}" && -f /opt/ros/jazzy/setup.zsh ]]; then source /opt/ros/jazzy/setup.zsh
  elif [[ -f /opt/ros/jazzy/setup.bash ]]; then source /opt/ros/jazzy/setup.bash
  else echo "ROS 2 Jazzy(/opt/ros/jazzy)가 없습니다." >&2; return 1 2>/dev/null || exit 1; fi
fi
[[ "${VIRTUAL_ENV:-}" == "$_WS/.venv-mobile-openarm" ]] || source "$_WS/.venv-mobile-openarm/bin/activate"
if [[ -f "$_WS/install/local_setup.bash" ]]; then
  if [[ -n "${ZSH_VERSION:-}" ]]; then source "$_WS/install/local_setup.zsh"; else source "$_WS/install/local_setup.bash"; fi
fi
export ROS_DOMAIN_ID="${MOBILE_ROS_DOMAIN_ID:-43}" ROS_LOCALHOST_ONLY=1 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST ROS_STATIC_PEERS=''
if [[ -d /opt/ros/jazzy/share/rmw_cyclonedds_cpp ]]; then
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI="$(cat "$_WS/src/mobile_openarm_bringup/config/cyclonedds.xml")"
fi
export ROS_HOME="$_WS/.ros/mobile_openarm" ROS_LOG_DIR="$_WS/.ros/mobile_openarm/log"
export MOBILE_OPENARM_MODEL_DIR="$_WS/artifacts/mobile_generated" PYTHONNOUSERSITE=1
mkdir -p "$ROS_LOG_DIR" "$MOBILE_OPENARM_MODEL_DIR"
# warehouse.launch.py 는 활성 venv python 으로 시뮬레이터를 띄우므로 ros2 launch 를 그대로 써도 된다.
# ros2launch 는 launch 프로세스까지 venv python 으로 실행한다 (다른 launch 파일용).
ros2launch() { python "$(command -v ros2)" launch "$@"; }
echo "mobile_openarm env: domain $ROS_DOMAIN_ID, rmw ${RMW_IMPLEMENTATION:-default}, venv $(python -c 'import sys;print(sys.prefix)')"
