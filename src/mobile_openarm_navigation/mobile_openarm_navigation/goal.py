"""Send one map-frame Nav2 goal and wait for its actual action result."""

import argparse
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("x", type=float)
    parser.add_argument("y", type=float)
    parser.add_argument("yaw", type=float, nargs="?", default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--use-sim-time", choices=["true", "false"], default=None)
    options = parser.parse_args(args)
    use_sim_time = True
    rclpy.init()
    node = Node(
        "mobile_openarm_goal",
        parameter_overrides=[
            rclpy.parameter.Parameter("use_sim_time", value=use_sim_time)
        ],
    )
    client = ActionClient(node, NavigateToPose, "/navigate_to_pose")
    code = 1
    try:
        if not client.wait_for_server(timeout_sec=30.0):
            raise RuntimeError(
                "Nav2 action server did not become available in 30 seconds"
            )
        deadline = time.monotonic() + 5
        while (
            use_sim_time
            and node.get_clock().now().nanoseconds == 0
            and time.monotonic() < deadline
        ):
            rclpy.spin_once(node, timeout_sec=0.1)
        if use_sim_time and node.get_clock().now().nanoseconds == 0:
            raise RuntimeError("Simulation selected but /clock is not available")
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = node.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = options.x, options.y
        goal.pose.pose.orientation.z = math.sin(options.yaw / 2)
        goal.pose.pose.orientation.w = math.cos(options.yaw / 2)
        future = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10)
        if not future.done() or not future.result().accepted:
            raise RuntimeError("Goal was not accepted")
        handle = future.result()
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(node, result, timeout_sec=options.timeout)
        if not result.done():
            cancel = handle.cancel_goal_async()
            rclpy.spin_until_future_complete(node, cancel, timeout_sec=5)
            raise RuntimeError("Goal timed out and cancellation was requested")
        status = result.result().status
        print(
            f"NavigateToPose result: status={status} (SUCCEEDED={GoalStatus.STATUS_SUCCEEDED})"
        )
        code = 0 if status == GoalStatus.STATUS_SUCCEEDED else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
