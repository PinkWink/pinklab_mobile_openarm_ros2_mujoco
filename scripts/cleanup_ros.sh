#!/usr/bin/env bash
# 사용법: ./scripts/cleanup_ros.sh  — 이전 세션의 Nav2/MoveIt/시뮬레이터 잔여 프로세스를 모두 종료한다 (중복 노드로 액션이 거부될 때).
# Kill every process left over from earlier simulator sessions (launch children survive SIGKILL of the launch).
for pat in "[r]os2 launch mobile_openarm_bringup" "[m]obile_openarm_mujoco.bridge" "[p]ick_place_server" "[m]onitor_parcel.py" \
           "[w]arehouse_scene" "[r]obot_state_publisher" "[l]ifecycle_manager" "[n]av2_" "[a]mcl" "[m]ap_server" "[m]ove_group" \
           "[c]ontroller_server" "[p]lanner_server" "[s]moother_server" "[b]ehavior_server" "[b]t_navigator" "[r]viz2" "[s]lam_toolbox" \
           "[c]heck_actors_live" "[w]arehouse_skills pick_place"; do
  pkill -INT -f "$pat" 2>/dev/null
done
sleep 4
for pat in "[r]os2 launch mobile_openarm_bringup" "[m]obile_openarm_mujoco.bridge" "[p]ick_place_server" "[m]onitor_parcel.py" \
           "[w]arehouse_scene" "[r]obot_state_publisher" "[l]ifecycle_manager" "[n]av2_" "[a]mcl" "[m]ap_server" "[m]ove_group" \
           "[c]ontroller_server" "[p]lanner_server" "[s]moother_server" "[b]ehavior_server" "[b]t_navigator" "[r]viz2" "[s]lam_toolbox" \
           "[c]heck_actors_live" "[w]arehouse_skills pick_place"; do
  pkill -9 -f "$pat" 2>/dev/null
done
sleep 1
echo "leftover ROS processes: $(pgrep -fc '[/]opt/ros/jazzy')"
