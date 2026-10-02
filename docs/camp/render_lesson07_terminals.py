"""Terminal captures for the lesson-07 (patrol demo + web dashboard) page. Text below is copied from real runs on 2026-10-02
(nav mode, moveit:=false, my_warehouse map; logs in artifacts/dev/patrol_frames/ and artifacts/dev/dash_frames/).
Output: docs/camp/lesson07_cli_*.png / lesson07_t*_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"

render([(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
        (P, "./scripts/mobile_openarm nav moveit:=false map:=$PWD/artifacts/maps/my_warehouse.yaml"),
        (O, "[INFO] [mobile_openarm_mujoco-1]: process started with pid [16371]"),
        (O, "[INFO] [map_server-3]: process started with pid [16373]"),
        (O, "[INFO] [amcl-4]: process started with pid [16374]"),
        (O, "[INFO] [controller_server-5]: process started with pid [16375]"),
        (O, "  ..."),
        (O, "[map_server-3] [INFO] [map_io]: Loading yaml file: /home/pw/mujoco_ros2/mobile_openarm_ws/artifacts/maps/my_warehouse.yaml"),
        (O, "[controller_server-5] [INFO] [controller_server]: Created controller : FollowPath of type nav2_rotation_shim_controller::RotationShimController"),
        (O, "[amcl-4] [INFO] [amcl]: Setting pose (0.000000): 0.000 0.000 0.000"),
        (O, "[mobile_openarm_mujoco-1] [INFO] [mobile_openarm_mujoco]: Vic Pinky + OpenArm ready: radius=0.0825, track=0.4288; 4 action servers; actors=9"),
        (O, "[lifecycle_manager-10] [INFO] [mobile_lifecycle_manager]: Managed nodes are active")],
       OUT + "lesson07_t1_nav.png", highlight=("my_warehouse.yaml", "RotationShimController", "Managed nodes are active"))

render([(P, "python lessons/04_navigation/patrol.py"),
        (O, "patrol: 5 stops: pick_table → rack_a → rack_b → place_table → center_aisle"),
        (O, "  1/5 pick_table     20.0 s   AMCL 오차 0.036 m   odom 오차 0.002 m"),
        (O, "  2/5 rack_a         38.0 s   AMCL 오차 0.031 m   odom 오차 0.011 m"),
        (O, "  3/5 rack_b         31.0 s   AMCL 오차 0.004 m   odom 오차 0.012 m"),
        (O, "  4/5 place_table    33.9 s   AMCL 오차 0.028 m   odom 오차 0.015 m"),
        (O, "  5/5 center_aisle   21.6 s   AMCL 오차 0.036 m   odom 오차 0.008 m"),
        (O, "patrol: done (순찰 완료: 5 곳, 148 s)")],
       OUT + "lesson07_cli_patrol.png", highlight=("patrol: done",))

render([(O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (0.00, -0.00) to (1.20, -3.60)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (1.15, -3.56) to (-4.00, -2.70)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (-3.97, -2.63) to (-4.00, 2.70)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (-4.00, 2.62) to (1.20, 3.60)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (1.17, 3.53) to (0.00, 0.00)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded")],
       OUT + "lesson07_t1_goal_log.png", title="터미널 1 (nav) — 순찰 중 로그", highlight=("Begin navigating",))

render([(P, "ros2 topic echo --once /patrol/status"),
        (O, "data: '{\"state\": \"running\", \"index\": 1, \"message\": \"랙 A(rack_a) 로 이동 중\", \"stops\": [{\"name\": \"pick_table\","),
        (O, "  \"label\": \"픽업 작업대\", \"goal\": [1...'"),
        (O, "---")],
       OUT + "lesson07_cli_status.png", highlight=("running", "rack_a"))

# 3. troubleshooting: robot stuck leaving rack A (log of the 2026-10-02 run before the fix)
render([(O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (-4.03, -2.64) to (-4.00, 2.70)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Received a goal, begin computing control effort."),
        (O, "[controller_server-5] [ERROR] [controller_server]: Failed to make progress"),
        (O, "[controller_server-5] [WARN] [controller_server]: [follow_path] [ActionServer] Aborting handle."),
        (O, "[controller_server-5] [INFO] [local_costmap.local_costmap]: Received request to clear entirely the local_costmap"),
        (O, "[controller_server-5] [ERROR] [controller_server]: Failed to make progress"),
        (O, "[planner_server-6] [INFO] [global_costmap.global_costmap]: Received request to clear entirely the global_costmap"),
        (O, "[controller_server-5] [ERROR] [controller_server]: Failed to make progress"),
        (O, "[controller_server-5] [ERROR] [controller_server]: Failed to make progress"),
        (O, "[behavior_server-8] [INFO] [behavior_server]: Running spin"),
        (O, "[behavior_server-8] [INFO] [behavior_server]: spin completed successfully"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!")],
       OUT + "lesson07_t1_stuck.png", title="터미널 1 (nav) — 랙 A → 랙 B 에서 멈출 때", highlight=("Failed to make progress", "Running spin"))

# 5. dashboard
render([(P, "python lessons/04_navigation/dashboard/server.py"),
        (O, "dashboard: http://localhost:8080   (camera frames: /dev/shm/mobile_openarm_dashboard)"),
        (O, " * Serving Flask app 'server'"),
        (O, " * Debug mode: off"),
        (O, " * Running on http://127.0.0.1:8080"),
        (O, "Press CTRL+C to quit"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:21] \"GET /api/stream HTTP/1.1\" 200 -"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:21] \"GET /api/map HTTP/1.1\" 200 -"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:21] \"GET /camera/base_camera.mjpg?t=1790904261966 HTTP/1.1\" 200 -"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:21] \"GET /camera/head_camera.mjpg?t=1790904261966 HTTP/1.1\" 200 -"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:21] \"GET /api/map.png?v=1790904260.0476718 HTTP/1.1\" 200 -"),
        (O, "127.0.0.1 - - [02/Oct/2026 10:24:37] \"POST /api/command HTTP/1.1\" 200 -")],
       OUT + "lesson07_t2_server.png", title="터미널 2 — 대시보드 서버", highlight=("dashboard: http", "POST /api/command"))

render([(P, "python lessons/04_navigation/patrol.py --wait"),
        (O, "(대시보드의 [순찰 시작] 을 누를 때까지 아무것도 출력하지 않고 기다린다)"),
        (O, "patrol: 5 stops: pick_table → rack_a → rack_b → place_table → center_aisle"),
        (O, "  1/5 pick_table     19.0 s   AMCL 오차 0.042 m   odom 오차 0.013 m"),
        (O, "  2/5 rack_a         37.5 s   AMCL 오차 0.042 m   odom 오차 0.017 m"),
        (O, "  3/5 rack_b         31.1 s   AMCL 오차 0.019 m   odom 오차 0.023 m"),
        (O, "  4/5 place_table    34.1 s   AMCL 오차 0.008 m   odom 오차 0.033 m"),
        (O, "  5/5 center_aisle   22.5 s   AMCL 오차 0.029 m   odom 오차 0.016 m"),
        (O, "patrol: done (순찰 완료: 5 곳, 148 s)")],
       OUT + "lesson07_t3_patrol_wait.png", title="터미널 3 — 순찰 (시작 버튼 대기)", highlight=("patrol: done",))

render([(P, "curl -s localhost:8080/api/cameras"),
        (O, "{\"base_camera\":{\"height\":240,\"sim_time\":467.6400000015048,\"width\":320},\"head_camera\":{\"height\":240,\"sim_time\":467.6400000015048,\"width\":320}}"),
        (P, "curl -s -X POST -H \"Content-Type: application/json\" -d '{\"cmd\":\"start\"}' localhost:8080/api/command"),
        (O, "{\"cmd\":\"start\",\"ok\":true}"),
        (P, "curl -s -N localhost:8080/api/stream | head -c 600"),
        (O, "data: {\"truth\": [1.172, -3.547, 1.597], \"amcl\": [1.149, -3.546, 1.566], \"amcl_cov\": [0.037, 0.051, 2.2],"),
        (O, "\"odom\": [1.18, -3.538, 1.599], \"twist\": [0.146, 0.292], \"plan\": [[1.12, -3.57], [1.11, -3.45], [1.1, -3.35], [1.07, -3.26], ... (줄임)")],
       OUT + "lesson07_cli_curl.png", title="터미널 4 — 브라우저 없이 API 보기", highlight=("\"ok\":true", "data: {"))
