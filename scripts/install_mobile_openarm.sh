#!/usr/bin/env bash
set -eo pipefail
MOBILE_WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$MOBILE_WORKSPACE"
if [[ "$(uname -s)" == Darwin ]]; then
  unset PYTHONPATH
  source "${PINKY_CONDA:-/opt/miniconda3}/etc/profile.d/conda.sh"
  # The project environment includes navigation and MoveIt; no system Python changes.
  if conda env list --json | python -c 'import json,sys; sys.exit(not any(p.endswith("/pinky-jazzy") for p in json.load(sys.stdin)["envs"]))'; then
    conda env update -n pinky-jazzy --file environment.yml
  else
    conda env create --file environment.yml
  fi
  exec ./scripts/mobile_openarm build
fi
[[ "${ROS_DISTRO:-}" == jazzy ]] || { echo 'source /opt/ros/jazzy/setup.bash first';exit 1; }
rosdep install --from-paths src/openarm_description src/vicpinky_description \
 src/mobile_openarm_description src/mobile_openarm_mujoco src/mobile_openarm_navigation \
 src/mobile_openarm_moveit_config src/mobile_openarm_bringup --ignore-src -r -y --rosdistro jazzy
# Activate this venv again in each terminal before using the wrapper.
python3 -m venv --system-site-packages .venv-mobile-openarm
source .venv-mobile-openarm/bin/activate
python -m pip install -r requirements-mobile-openarm.txt
export MOBILE_ENV_MODE=native
# Ensure ament Python executables are built with this venv interpreter.
python -m colcon build --symlink-install --base-paths src --packages-up-to mobile_openarm_bringup
