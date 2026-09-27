#!/usr/bin/env bash
# 개발용: 시뮬레이터를 headless로 재시작하고 준비될 때까지 기다린다. 로그는 artifacts/dev/<이름>.log. 사용: scripts/dev/restart_sim.sh [로그이름]
# Restart the headless simulator (Nav2 + MoveIt + skills + lecture camera pipeline) and wait for readiness.
S=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/artifacts/dev; mkdir -p "$S"
LOG="$S/${1:-sim}.log"
cd /home/pw/mujoco_ros2/mobile_openarm_ws
bash "$(dirname "${BASH_SOURCE[0]}")/../cleanup_ros.sh"
# The ros2 daemon keeps the RMW of the shell that started it; reset it so the CLI sees the CycloneDDS simulator.
bash -c 'source /opt/ros/jazzy/setup.bash && source scripts/env.sh >/dev/null && ros2 daemon stop' >/dev/null 2>&1
setsid nohup bash -c 'source /opt/ros/jazzy/setup.bash && source scripts/env.sh >/dev/null && exec python "$(command -v ros2)" launch mobile_openarm_bringup warehouse.launch.py mode:=nav viewer:=false rviz:=false '"${LAUNCH_ARGS:-}" > "$LOG" 2>&1 < /dev/null &
disown
sleep 15
for i in $(seq 1 150); do
  if grep -q "Managed nodes are active" "$LOG" 2>/dev/null && grep -q "You can start planning now" "$LOG" && (grep -q "PickPlace server ready" "$LOG" || [[ -n "$LAUNCH_ARGS" ]]); then echo READY; break; fi
  if grep -q "process has died" "$LOG"; then echo CRASH; grep "process has died" "$LOG" | head -2; break; fi
  sleep 1
done
grep -E "Direct Python cameras|actors=" "$LOG" | head -2
sleep 4
