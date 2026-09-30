"""Terminal captures for the lesson-04 page. Text below is copied from real runs on 2026-09-30
(slam mode, actors:=none, after one slam_tour.py loop). Output: docs/camp/lesson04_cli_*.png / lesson04_t*_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"

render([(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
        (O, "mobile_openarm env: domain 43, rmw rmw_cyclonedds_cpp, venv .../.venv-mobile-openarm"),
        (P, "./scripts/mobile_openarm slam actors:=none"),
        (O, "[INFO] [mobile_openarm_mujoco-1]: process started with pid [30206]"),
        (O, "[INFO] [robot_state_publisher-2]: process started with pid [30207]"),
        (O, "[INFO] [async_slam_toolbox_node-3]: process started with pid [30208]"),
        (O, "[INFO] [rviz2-4]: process started with pid [30209]"),
        (O, "[async_slam_toolbox_node-3] [INFO] [slam_toolbox]: Configuring"),
        (O, "[async_slam_toolbox_node-3] [INFO] [slam_toolbox]: Using solver plugin solver_plugins::CeresSolver"),
        (O, "[INFO] [launch.user]: [LifecycleLaunch] Slamtoolbox node is activating."),
        (O, "[async_slam_toolbox_node-3] [INFO] [slam_toolbox]: Activating"),
        (O, "[mobile_openarm_mujoco-1] [INFO] [mobile_openarm_mujoco]: Vic Pinky + OpenArm ready: radius=0.0825, track=0.4288; ... actors=0"),
        (O, "[async_slam_toolbox_node-3] Registering sensor: [Custom Described Lidar]"),
        (O, "[rviz2-4] [INFO] [rviz2]: Trying to create a map of size 300 x 220 using 1 swatches")],
       OUT + "lesson04_t1_slam.png", highlight=("async_slam_toolbox_node-3]: process", "Registering sensor", "300 x 220"))

render([(P, "ros2 node list"),
        (O, "/launch_ros_30148"), (O, "/mobile_openarm_mujoco"), (O, "/robot_state_publisher"), (O, "/rviz"), (O, "/slam_toolbox"),
        (O, "/transform_listener_impl_60ceeb20e880"), (O, "/transform_listener_impl_64c155952500"),
        (P, "ros2 topic list | grep -E 'map|slam|pose'"),
        (O, "/initialpose"), (O, "/map"), (O, "/map_metadata"), (O, "/map_updates"), (O, "/pose"),
        (O, "/slam_toolbox/feedback"), (O, "/slam_toolbox/graph_visualization"), (O, "/slam_toolbox/scan_visualization"),
        (O, "/slam_toolbox/transition_event"), (O, "/slam_toolbox/update"), (O, "/warehouse/object_poses")],
       OUT + "lesson04_cli_nodes.png", highlight=("/slam_toolbox", "/map"))

render([(P, "ros2 run tf2_ros tf2_echo map odom"),
        (O, "At time 267.300000001"),
        (O, "- Translation: [-0.023, 0.013, 0.000]"),
        (O, "- Rotation: in Quaternion (xyzw) [0.000, 0.000, -0.003, 1.000]"),
        (O, "- Rotation: in RPY (radian) [0.000, 0.000, -0.006]"),
        (O, "- Rotation: in RPY (degree) [0.000, 0.000, -0.367]"),
        (O, "^C")],
       OUT + "lesson04_cli_tf_map_odom.png", highlight=("Translation", "degree"))

render([(P, "ros2 topic echo --once /map --field info"),
        (O, "map_load_time:"), (O, "  sec: 0"), (O, "  nanosec: 0"),
        (O, "resolution: 0.05000000074505806"), (O, "width: 301"), (O, "height: 222"),
        (O, "origin:"), (O, "  position:"), (O, "    x: -7.535456012965424"), (O, "    y: -5.524474073370678"), (O, "    z: 0.0"),
        (O, "  orientation:"), (O, "    x: 0.0"), (O, "    y: 0.0"), (O, "    z: 0.0"), (O, "    w: 1.0"), (O, "---"),
        (P, "ros2 topic hz /map"),
        (O, "average rate: 0.999"), (O, "\tmin: 0.993s max: 1.008s std dev: 0.00764s window: 2"),
        (O, "average rate: 1.000"), (O, "\tmin: 0.993s max: 1.008s std dev: 0.00563s window: 4"), (O, "^C")],
       OUT + "lesson04_cli_map_info.png", highlight=("resolution", "width", "height", "x: -7.5", "y: -5.5", "average rate"))

render([(P, "./scripts/mobile_openarm teleop"),
        (O, "This node takes keypresses from the keyboard and publishes them"),
        (O, "as Twist/TwistStamped messages. It works best with a US keyboard layout."),
        (O, "---------------------------"), (O, "Moving around:"),
        (O, "   u    i    o"), (O, "   j    k    l"), (O, "   m    ,    ."), (O, ""),
        (O, "q/z : increase/decrease max speeds by 10%"),
        (O, "w/x : increase/decrease only linear speed by 10%"),
        (O, "e/c : increase/decrease only angular speed by 10%"), (O, ""),
        (O, "CTRL-C to quit"), (O, ""), (O, "currently:\tspeed 0.25\tturn 0.50")],
       OUT + "lesson04_t3_teleop.png", highlight=("u    i    o", "j    k    l", "m    ,    .", "currently"))

render([(P, "ros2 run nav2_map_server map_saver_cli -f artifacts/maps/my_warehouse"),
        (O, "[INFO] [map_saver]: Saving map from 'map' topic to 'artifacts/maps/my_warehouse' file"),
        (O, "[WARN] [map_saver]: Free threshold unspecified. Setting it to default value: 0.250000"),
        (O, "[WARN] [map_saver]: Occupied threshold unspecified. Setting it to default value: 0.650000"),
        (O, "[WARN] [map_io]: Image format unspecified. Setting it to: pgm"),
        (O, "[INFO] [map_io]: Received a 301 X 222 map @ 0.05 m/pix"),
        (O, "[INFO] [map_io]: Writing map occupancy data to artifacts/maps/my_warehouse.pgm"),
        (O, "[INFO] [map_io]: Writing map metadata to artifacts/maps/my_warehouse.yaml"),
        (O, "[INFO] [map_saver]: Map saved successfully"),
        (P, "ls artifacts/maps"), (O, "my_warehouse.pgm  my_warehouse.yaml"),
        (P, "cat artifacts/maps/my_warehouse.yaml"),
        (O, "image: my_warehouse.pgm"), (O, "mode: trinary"), (O, "resolution: 0.050"), (O, "origin: [-7.535, -5.524, 0]"),
        (O, "negate: 0"), (O, "occupied_thresh: 0.65"), (O, "free_thresh: 0.196")],
       OUT + "lesson04_cli_map_saver.png", highlight=("Received", "saved successfully", "my_warehouse.pgm  my", "origin", "resolution: 0.050"))

TOUR = Path("artifacts/dev/slam_tour.log")
if TOUR.exists():
    lines = [l for l in TOUR.read_text().splitlines() if l.startswith("waypoint") or "blocked" in l]
    render([(P, "python docs/camp/slam_tour.py")] + [(O, l) for l in lines], OUT + "lesson04_cli_tour.png", highlight=("7/7",))
