#!/usr/bin/env bash
# 개발용: 운반 스킬을 한 번 실행하고 상자 높이·손가락 타임라인을 함께 출력한다. 사용: scripts/dev/run_pick.sh [red|blue|yellow] [from] [to]
# Run one pick-and-place and summarise. Usage: run_pick.sh [object] [from] [to]
S=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/artifacts/dev; mkdir -p "$S"
cd /home/pw/mujoco_ros2/mobile_openarm_ws
source /opt/ros/jazzy/setup.bash
source scripts/env.sh >/dev/null   # venv + install + domain 43 + CycloneDDS (same RMW as the simulator)
mon="monitor_""parcel.py"; pkill -f "$mon" 2>/dev/null
setsid nohup python "$(dirname "${BASH_SOURCE[0]}")/monitor_parcel.py" "$S/parcel_monitor.log" > /dev/null 2>&1 < /dev/null &
MON=$!
sleep 2
timeout 900 python "$(command -v ros2)" run warehouse_skills pick_place "${1:-red}" "${2:-pick_table}" "${3:-place_table}" 2>&1 | grep -v "^\[WARN\]" | grep -vE "visual dock"
kill $MON 2>/dev/null
echo "--- parcel/finger timeline (changes only):"
awk '{split($2,a,"="); z=a[2]; split($4,f,"="); if (z!=prevz || f[2]!=prevf || $0 ~ /\[/) print; prevz=z; prevf=f[2]}' "$S/parcel_monitor.log" | grep -vE "tick$|visual dock|Nav2 to|looking for|pre-dock aligned|visual servo" | tail -45
echo "--- object poses now:"
timeout 5 ros2 topic echo /warehouse/object_poses --once 2>/dev/null | grep -E "^    (x|y|z):" | paste - - - | head -3
echo "--- server errors:"
grep -E "ERROR|Traceback" "$S"/*.log 2>/dev/null | grep pick_place_server | tail -5
