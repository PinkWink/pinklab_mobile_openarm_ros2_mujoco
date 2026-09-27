"""Exercise OMPL planning and actual trajectory execution for a named arm pose."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from ament_index_python.packages import get_package_share_directory
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("side", choices=["left", "right", "both"])
    parser.add_argument("pose", choices=["transport", "ready", "home", "hands_up"])
    parser.add_argument("--plan-only", action="store_true")
    options = parser.parse_args(args)
    srdf = ET.parse(
        Path(get_package_share_directory("mobile_openarm_moveit_config"))
        / "config/mobile_openarm.srdf"
    )
    rclpy.init()
    node = Node(
        "mobile_openarm_joint_goal",
        parameter_overrides=[Parameter("use_sim_time", value=True)],
    )
    client = ActionClient(node, MoveGroup, "/move_action")
    try:
        if not client.wait_for_server(timeout_sec=30):
            raise RuntimeError("MoveIt move_action not available")
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = (
            "both_arms" if options.side == "both" else options.side + "_arm"
        )
        req.allowed_planning_time = 8.0
        req.num_planning_attempts = 5
        req.max_velocity_scaling_factor = 0.3
        req.max_acceleration_scaling_factor = 0.3
        req.start_state.is_diff = True
        constraint = Constraints(name=options.pose)
        for side in ["left", "right"] if options.side == "both" else [options.side]:
            state = srdf.find(
                f"group_state[@group='{side}_arm'][@name='{options.pose}']"
            )
            if state is None:
                raise RuntimeError("Named pose missing from SRDF")
            for j in state.findall("joint"):
                constraint.joint_constraints.append(
                    JointConstraint(
                        joint_name=j.get("name"),
                        position=float(j.get("value")),
                        tolerance_above=0.01,
                        tolerance_below=0.01,
                        weight=1.0,
                    )
                )
        req.goal_constraints = [constraint]
        goal.planning_options.plan_only = options.plan_only
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        future = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10)
        if not future.done() or not future.result().accepted:
            raise RuntimeError("MoveIt rejected the request")
        handle = future.result()
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(node, result, timeout_sec=90)
        if not result.done():
            cancel = handle.cancel_goal_async()
            rclpy.spin_until_future_complete(node, cancel, timeout_sec=5)
            raise RuntimeError("MoveIt timed out; cancellation requested")
        code = result.result().result.error_code.val
        print(
            f"MoveIt {req.group_name}/{options.pose}: status={result.result().status}, error_code={code}"
        )
        if result.result().status != 4 or code != MoveItErrorCodes.SUCCESS:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
