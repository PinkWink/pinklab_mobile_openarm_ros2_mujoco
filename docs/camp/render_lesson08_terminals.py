"""Terminal captures for the lesson-08 (MoveIt + MuJoCo) page. Text below is copied from real runs on 2026-10-02
(moveit mode: ./scripts/mobile_openarm moveit viewer:=true rviz:=true). Output: docs/camp/lesson08_cli_*.png / lesson08_t1_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
MG = "[move_group-3] [INFO] [move_group.moveit"
TEH = "[move_group-3] [INFO] [...controller_handle]:"

render([(P, "source /opt/ros/jazzy/setup.bash"), (P, "source scripts/env.sh"),
        (P, "./scripts/mobile_openarm moveit viewer:=true rviz:=true"),
        (O, "[INFO] [mobile_openarm_mujoco-1]: process started with pid [41377]"),
        (O, "[INFO] [robot_state_publisher-2]: process started with pid [41378]"),
        (O, "[INFO] [move_group-3]: process started with pid [41379]"),
        (O, "[INFO] [warehouse_scene-4]: process started with pid [41380]"),
        (O, "[INFO] [rviz2-5]: process started with pid [41381]"),
        (O, f"{MG}.moveit.core.robot_model]: Loading robot model 'mobile_openarm'..."),
        (O, "[move_group-3] Loading 'move_group/MoveGroupMoveAction'..."),
        (O, "[move_group-3] Loading 'move_group/MoveGroupKinematicsService'..."),
        (O, "[move_group-3] Loading 'move_group/MoveGroupCartesianPathService'..."),
        (O, "[move_group-3] You can start planning now!"),
        (O, "[mobile_openarm_mujoco-1] [INFO] [mobile_openarm_mujoco]: Vic Pinky + OpenArm ready: ... 4 action servers; actors=9"),
        (O, "[rviz2-5] [INFO] [moveit_...motion_planning_frame]: Ready to take commands for planning group left_arm.")],
       OUT + "lesson08_t1_moveit.png",
       highlight=("move_group-3]: process", "warehouse_scene-4]: process", "You can start planning now", "4 action servers", "Ready to take commands"))

render([(P, "ros2 node list"),
        (O, "/interactive_marker_display_99447051075024"), (O, "/mobile_openarm_mujoco"), (O, "/move_group"), (O, "/move_group/moveit"),
        (O, "/move_group_private_96620631403104"), (O, "/moveit_2408324476"), (O, "/moveit_2760340243"), (O, "/moveit_simple_controller_manager"),
        (O, "/robot_state_publisher"), (O, "/rviz"), (O, "/rviz_private_137679412751504"), (O, "/transform_listener_impl_57e03ea24300"),
        (O, "/warehouse_planning_scene"),
        (P, "ros2 action list"),
        (O, "/execute_trajectory"), (O, "/left_gripper_controller/gripper_cmd"), (O, "/left_joint_trajectory_controller/follow_joint_trajectory"),
        (O, "/move_action"), (O, "/right_gripper_controller/gripper_cmd"), (O, "/right_joint_trajectory_controller/follow_joint_trajectory")],
       OUT + "lesson08_cli_nodes.png",
       highlight=("/mobile_openarm_mujoco", "/move_group", "/moveit_simple_controller_manager", "/warehouse_planning_scene", "_controller/", "/move_action"))

render([(P, "ros2 action info /left_joint_trajectory_controller/follow_joint_trajectory"),
        (O, "Action: /left_joint_trajectory_controller/follow_joint_trajectory"), (O, "Action clients: 1"),
        (O, "    /moveit_simple_controller_manager"), (O, "Action servers: 1"), (O, "    /mobile_openarm_mujoco"),
        (P, "ros2 service list | grep -E 'ik|cartesian|plan|scene' | grep -v warehouse_planning_scene/"),
        (O, "/apply_planning_scene"), (O, "/compute_cartesian_path"), (O, "/compute_ik"), (O, "/get_planner_params"),
        (O, "/get_planning_scene"), (O, "/plan_kinematic_path"), (O, "/query_planner_interface"), (O, "/set_planner_params")],
       OUT + "lesson08_cli_actions.png",
       highlight=("/moveit_simple_controller_manager", "/mobile_openarm_mujoco", "/apply_planning_scene", "/compute_cartesian_path", "/compute_ik"))

render([(P, "time ./scripts/mobile_openarm arm both ready"),
        (O, "MoveIt both_arms/ready: status=4, error_code=1"),
        (O, ""), (O, "real\t0m3.955s"), (O, "user\t0m0.910s"), (O, "sys\t0m0.890s"),
        (P, "./scripts/mobile_openarm arm both hands_up"),
        (O, "MoveIt both_arms/hands_up: status=4, error_code=1"),
        (P, "./scripts/mobile_openarm arm both transport"),
        (O, "MoveIt both_arms/transport: status=4, error_code=1")],
       OUT + "lesson08_cli_arm.png", highlight=("status=4, error_code=1", "real"))

render([(O, f"{MG}.ros.move_group.move_action]: MoveGroupMoveAction: Received request"),
        (O, "[move_group-3] [INFO] [move_group]: Calling PlanningRequestAdapter 'CheckStartStateCollision'"),
        (O, f"[move_group-3] [INFO] [...model_based_planning_context]: Planner configuration 'both_arms' will use planner 'geometric::RRTConnect'."),
        (O, "[move_group-3] [INFO] [move_group]: Calling Planner 'OMPL'"),
        (O, "[move_group-3] [INFO] [move_group]: Calling PlanningResponseAdapter 'AddTimeOptimalParameterization'"),
        (O, "[move_group-3] [INFO] [move_group]: Calling PlanningResponseAdapter 'ValidateSolution'"),
        (O, f"{MG}.ros.trajectory_execution_manager]: Starting trajectory execution ..."),
        (O, f"{TEH} sending trajectory to left_joint_trajectory_controller"),
        (O, f"{TEH} sending trajectory to right_joint_trajectory_controller"),
        (O, f"{TEH} Controller 'left_joint_trajectory_controller' successfully finished"),
        (O, f"{TEH} Controller 'right_joint_trajectory_controller' successfully finished"),
        (O, f"{MG}.ros.trajectory_execution_manager]: Completed trajectory execution with status SUCCEEDED ..."),
        (O, f"{MG}.ros.move_group.move_action]: Solution was found and executed.")],
       OUT + "lesson08_t1_arm_log.png", title="터미널 1 — moveit (move_group 로그, 발췌)",
       highlight=("RRTConnect", "Calling Planner 'OMPL'", "AddTimeOptimalParameterization", "sending trajectory", "SUCCEEDED", "Solution was found"))

W = "[move_group-3] [WARN] [...controller_handle]:"
render([(P, "./scripts/mobile_openarm arm both home"),
        (O, "MoveIt both_arms/home: status=6, error_code=-4"),
        (O, "[ros2run]: Process exited with failure 1"),
        (O, ""),
        (O, "--- 터미널 1 (move_group 로그) ---"),
        (O, f"{TEH} sending trajectory to left_joint_trajectory_controller"),
        (O, f"{W} Controller 'left_joint_trajectory_controller' failed with error GOAL_TOLERANCE_VIOLATED:"),
        (O, "    Measured joints did not reach the goal"),
        (O, f"{W} Controller 'right_joint_trajectory_controller' failed with error GOAL_TOLERANCE_VIOLATED:"),
        (O, "    Measured joints did not reach the goal"),
        (O, f"{MG}.ros.trajectory_execution_manager]: Completed trajectory execution with status ABORTED ..."),
        (O, f"{MG}.ros.move_group.move_action]: CONTROL_FAILED")],
       OUT + "lesson08_cli_home.png", highlight=("status=6, error_code=-4", "GOAL_TOLERANCE_VIOLATED", "ABORTED", "CONTROL_FAILED"))
