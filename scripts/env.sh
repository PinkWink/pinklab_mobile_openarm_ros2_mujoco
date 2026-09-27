# source 해서 쓰는 환경 설정. wrapper(scripts/mobile_openarm)와 같은 환경을 현재 셸에 만든다.
#   source /opt/ros/jazzy/setup.bash    (zsh: setup.zsh)
#   source scripts/env.sh
# 이후 ros2 launch / ros2 run / ros2 topic ... 을 직접 실행할 수 있다.
_WS="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
if [[ "${ROS_DISTRO:-}" != jazzy ]]; then echo "source /opt/ros/jazzy/setup.{bash,zsh} first" >&2; return 1 2>/dev/null || exit 1; fi
[[ -n "${VIRTUAL_ENV:-}" ]] || source "$_WS/.venv-mobile-openarm/bin/activate"
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
# ros2 launch 는 자식(MuJoCo bridge)을 launch 프로세스의 인터프리터로 띄우므로 venv python으로 실행해야 한다.
ros2launch() { python "$(command -v ros2)" launch "$@"; }
echo "mobile_openarm env: domain $ROS_DOMAIN_ID, rmw ${RMW_IMPLEMENTATION:-default}, venv $(python -c 'import sys;print(sys.prefix)')"
