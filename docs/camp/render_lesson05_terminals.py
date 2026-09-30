"""Terminal captures for the lesson-05 (Nav2) page. Text below is copied from real runs on 2026-09-30
(nav mode, moveit:=false, packaged warehouse map). Output: docs/camp/lesson05_cli_*.png / lesson05_t*_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"

render([(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
        (P, "./scripts/mobile_openarm nav moveit:=false"),
        (O, "[INFO] [mobile_openarm_mujoco-1]: process started with pid [35531]"),
        (O, "[INFO] [robot_state_publisher-2]: process started with pid [35532]"),
        (O, "[INFO] [map_server-3]: process started with pid [35533]"),
        (O, "[INFO] [amcl-4]: process started with pid [35534]"),
        (O, "[INFO] [controller_server-5]: process started with pid [35535]"),
        (O, "[INFO] [planner_server-6]: process started with pid [35536]"),
        (O, "[INFO] [smoother_server-7]: process started with pid [35537]"),
        (O, "[INFO] [behavior_server-8]: process started with pid [35538]"),
        (O, "[INFO] [bt_navigator-9]: process started with pid [35539]"),
        (O, "[INFO] [lifecycle_manager-10]: process started with pid [35540]"),
        (O, "[INFO] [rviz2-11]: process started with pid [35541]"),
        (O, "[map_server-3] [INFO] [map_io]: Loading yaml file: .../mobile_openarm_navigation/maps/warehouse.yaml"),
        (O, "[amcl-4] [INFO] [amcl]: Setting pose (0.000000): 0.000 0.000 0.000"),
        (O, "[mobile_openarm_mujoco-1] [INFO] [mobile_openarm_mujoco]: Vic Pinky + OpenArm ready: ... actors=9"),
        (O, "[lifecycle_manager-10] [INFO] [mobile_lifecycle_manager]: Managed nodes are active")],
       OUT + "lesson05_t1_nav.png", highlight=("map_server-3]: process", "amcl-4]: process", "Loading yaml", "Setting pose", "Managed nodes are active"))

render([(P, "ros2 node list"),
        (O, "/amcl"), (O, "/behavior_server"), (O, "/bt_navigator"), (O, "/bt_navigator_navigate_through_poses_rclcpp_node"),
        (O, "/bt_navigator_navigate_to_pose_rclcpp_node"), (O, "/controller_server"), (O, "/global_costmap/global_costmap"),
        (O, "/local_costmap/local_costmap"), (O, "/map_server"), (O, "/mobile_lifecycle_manager"), (O, "/mobile_openarm_mujoco"),
        (O, "/planner_server"), (O, "/robot_state_publisher"), (O, "/rviz"), (O, "/smoother_server"),
        (O, "/transform_listener_impl_55a3aa459ce0"), (O, "/transform_listener_impl_57a0331ed000"), (O, "/transform_listener_impl_73bacc00b080")],
       OUT + "lesson05_cli_nodes.png",
       highlight=("/amcl", "/behavior_server", "/bt_navigator", "/controller_server", "costmap", "/map_server", "lifecycle", "/planner_server", "/smoother_server"))

render([(P, "ros2 action list"),
        (O, "/backup"), (O, "/compute_path_through_poses"), (O, "/compute_path_to_pose"), (O, "/drive_on_heading"), (O, "/follow_path"),
        (O, "/left_gripper_controller/gripper_cmd"), (O, "/left_joint_trajectory_controller/follow_joint_trajectory"),
        (O, "/navigate_through_poses"), (O, "/navigate_to_pose"),
        (O, "/right_gripper_controller/gripper_cmd"), (O, "/right_joint_trajectory_controller/follow_joint_trajectory"),
        (O, "/smooth_path"), (O, "/spin"), (O, "/wait"),
        (P, "for n in map_server amcl controller_server planner_server smoother_server behavior_server bt_navigator; do \\"),
        (O, ">   echo \"/$n: $(ros2 lifecycle get /$n)\"; done"),
        (O, "/map_server: active [3]"), (O, "/amcl: active [3]"), (O, "/controller_server: active [3]"), (O, "/planner_server: active [3]"),
        (O, "/smoother_server: active [3]"), (O, "/behavior_server: active [3]"), (O, "/bt_navigator: active [3]")],
       OUT + "lesson05_cli_actions.png", highlight=("/navigate_to_pose", "/compute_path_to_pose", "/follow_path", "active [3]"))

render([(P, "time ./scripts/mobile_openarm goal 1.2 -3.6 0        # 픽업 작업대 앞 (locations.yaml: pick_table)"),
        (O, "NavigateToPose result: status=4 (SUCCEEDED=4)"), (O, ""),
        (O, "real\t0m27.422s"), (O, "user\t0m2.386s"), (O, "sys\t0m1.184s")],
       OUT + "lesson05_cli_goal.png", highlight=("SUCCEEDED", "real"))

render([(O, "(터미널 1 의 로그)"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (0.00, -0.00) to (1.20, -3.60)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Begin navigating from current location (1.15, -3.54) to (0.02, 0.02)"),
        (O, "[controller_server-5] [INFO] [controller_server]: Reached the goal!"),
        (O, "[bt_navigator-9] [INFO] [bt_navigator]: Goal succeeded")],
       OUT + "lesson05_t1_goal_log.png", highlight=("Begin navigating", "Goal succeeded"))

render([(P, "ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \\"),
        (O, ">   \"{header: {frame_id: map}, pose: {pose: {position: {x: 0.6, y: 0.4}, orientation: {z: 0.1987, w: 0.9801}},"),
        (O, ">     covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.0685]}}\""),
        (O, "publisher: beginning loop"),
        (O, "publishing #1: geometry_msgs.msg.PoseWithCovarianceStamped(header=... frame_id='map'), pose=...)"),
        (O, ""),
        (O, "(터미널 1 의 로그)"),
        (O, "[amcl-4] [INFO] [amcl]: Setting pose (140.700000): 0.600 0.400 0.400"),
        (P, "./scripts/mobile_openarm goal 3.5 0.0 0"),
        (O, "NavigateToPose result: status=4 (SUCCEEDED=4)")],
       OUT + "lesson05_cli_initialpose.png", highlight=("Setting pose", "SUCCEEDED"))
