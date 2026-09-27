#!/usr/bin/env python3
"""Integration checks against an already running warehouse launch.

Moves the simulated robot. Run in a fresh headless session, with MoveIt and Nav2.
"""

import argparse
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import JointState, LaserScan
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from moveit_msgs.srv import GetPlanningScene
from moveit_msgs.msg import PlanningSceneComponents
from tf2_ros import Buffer, TransformListener
from mobile_openarm_mujoco.model import initial_positions, load_world


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nav", action="store_true")
    parser.add_argument("--output", default="artifacts/mobile_openarm_integration.json")
    args = parser.parse_args()
    rclpy.init()
    node = Node(
        "mobile_openarm_checks",
        parameter_overrides=[Parameter("use_sim_time", value=True)],
    )
    latest = {}
    report = {}
    buffer = Buffer()
    _listener = TransformListener(buffer, node)
    for topic, kind, key in [
        ("/joint_states", JointState, "joints"),
        ("/odom", Odometry, "odom"),
        ("/ground_truth", PoseStamped, "truth"),
        ("/scan", LaserScan, "scan"),
    ]:
        node.create_subscription(
            kind,
            topic,
            lambda m, k=key: latest.update({k: m}),
            qos_profile_sensor_data if key == "scan" else 10,
        )
    pub = node.create_publisher(Twist, "/cmd_vel", 10)

    def spin(seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.02)

    def wait_future(future, timeout=30):
        rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
        assert future.done(), "ROS request timeout"
        return future.result()

    def client(kind, name):
        c = ActionClient(node, kind, name)
        assert c.wait_for_server(timeout_sec=40), name
        return c

    def run(c, goal):
        h = wait_future(c.send_goal_async(goal))
        assert h.accepted, "Action rejected"
        try:
            return wait_future(h.get_result_async(), 40)
        except Exception:
            wait_future(h.cancel_goal_async(), 5)
            raise

    def positions():
        return dict(zip(latest["joints"].name, latest["joints"].position))

    def armgoal(names, target, duration):
        g = FollowJointTrajectory.Goal()
        g.trajectory.joint_names = names
        g.trajectory.points = [
            JointTrajectoryPoint(
                positions=target, time_from_start=Duration(sec=duration)
            )
        ]
        return g

    try:
        deadline = time.monotonic() + 45
        while len(latest) < 4 and time.monotonic() < deadline:
            spin(0.1)
        assert len(latest) == 4, latest.keys()
        spin(1)
        assert len(latest["joints"].name) == 20 and len(latest["scan"].ranges) == 360
        for target in ["laser_link", "openarm_left_hand_tcp", "openarm_right_hand_tcp"]:
            assert buffer.can_transform("odom", target, rclpy.time.Time()), target
        report["ros_graph"] = {"joint_states": 20, "scan_rays": 360, "tf_chains": 3}
        scene = node.create_client(GetPlanningScene, "/get_planning_scene")
        assert scene.wait_for_service(timeout_sec=20)
        request = GetPlanningScene.Request(
            components=PlanningSceneComponents(
                components=PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
            )
        )
        response = wait_future(scene.call_async(request))
        ids = {o.id for o in response.scene.world.collision_objects}
        assert {
            "parcel_1",
            "parcel_2",
            "parcel_3",
            "pick_table",
            "place_table",
            "warehouse_floor",
        } <= ids
        assert len(ids) == len(load_world()["boxes"]) + 4
        report["planning_scene_objects"] = len(ids)
        for side in ["left", "right"]:
            c = client(GripperCommand, f"/{side}_gripper_controller/gripper_cmd")
            for q in [0.005, 0.035, 0.025]:
                g = GripperCommand.Goal()
                g.command.position = q
                g.command.max_effort = 15.0
                result = run(c, g)
                assert result.status == 4 and result.result.reached_goal
                assert abs(result.result.position - q) < 0.002
            report[side + "_gripper"] = "open/close with measured feedback passed"
        names = [f"openarm_left_joint{i}" for i in range(1, 8)]
        c = client(
            FollowJointTrajectory,
            "/left_joint_trajectory_controller/follow_joint_trajectory",
        )
        # Malformed names must be rejected without moving any joint.
        invalid = armgoal(["not_a_joint"], [0.0], 1)
        assert not wait_future(c.send_goal_async(invalid)).accepted
        target = [positions()[n] for n in names]
        target[3] = 1.65
        goal = armgoal(names, target, 5)
        h = wait_future(c.send_goal_async(goal))
        assert h.accepted
        assert not wait_future(c.send_goal_async(goal)).accepted, (
            "Concurrent goal must be rejected"
        )
        before = latest["truth"].pose.position
        before = (before.x, before.y)
        command = Twist()
        command.linear.x = 0.25
        for _ in range(10):
            pub.publish(command)
            spin(0.05)
        after = latest["truth"].pose.position
        assert math.hypot(after.x - before[0], after.y - before[1]) < 0.025, (
            "Base moved during arm motion"
        )
        cancel = wait_future(h.cancel_goal_async())
        assert cancel.goals_canceling
        result = wait_future(h.get_result_async())
        assert result.status == 5
        spin(0.2)
        held = positions()[names[3]]
        spin(0.5)
        assert abs(positions()[names[3]] - held) < 0.02
        report["trajectory_validation"] = (
            "malformed goal, concurrent goal, cancellation/hold, base interlock passed"
        )
        initial = initial_positions()
        result = run(c, armgoal(names, [initial[n] for n in names], 2))
        assert result.status == 4 and result.result.error_code == 0
        # Watchdog stops motion when cmd_vel stops arriving.
        spin(0.5)
        before = latest["truth"].pose.position
        before = (before.x, before.y)
        for _ in range(15):
            pub.publish(command)
            spin(0.1)
        spin(1.5)
        after = latest["truth"].pose.position
        distance = math.hypot(after.x - before[0], after.y - before[1])
        assert 0.2 < distance < 0.65, distance
        assert abs(latest["odom"].twist.twist.linear.x) < 0.015
        report["drive_watchdog"] = {
            "distance_m": distance,
            "stopped_velocity_mps": latest["odom"].twist.twist.linear.x,
        }
        if args.nav:
            c = client(NavigateToPose, "/navigate_to_pose")
            g = NavigateToPose.Goal()
            g.pose.header.frame_id = "map"
            g.pose.header.stamp = node.get_clock().now().to_msg()
            g.pose.pose.position.x = 1.0
            g.pose.pose.position.y = 0.6
            g.pose.pose.orientation.w = 1.0
            h = wait_future(c.send_goal_async(g))
            assert h.accepted
            try:
                result = wait_future(h.get_result_async(), 100)
            except Exception:
                wait_future(h.cancel_goal_async(), 5)
                raise
            assert result.status == 4, result
            spin(0.2)
            p = latest["truth"].pose.position
            error = math.hypot(p.x - 1.0, p.y - 0.6)
            assert error < 0.2, error
            report["nav2"] = {
                "status": result.status,
                "ground_truth_goal_error_m": error,
            }
        report["passed"] = True
    finally:
        pub.publish(Twist())
        spin(0.1)
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
