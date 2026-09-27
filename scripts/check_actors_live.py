#!/usr/bin/env python3
"""Live Phase 0 check: actors, SetActor service, truth detections in map, Nav2 near people.

Start first (headless is fine):
  ./scripts/mobile_openarm start viewer:=false rviz:=false \
      camera_handler:=warehouse_lecture.vision.truth_detector:TruthDetector \
      camera_depth:=true camera_segmentation:=true
"""

import argparse
import json
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Pose, PoseStamped
from nav2_msgs.action import NavigateToPose
from warehouse_interfaces.msg import ActorStateArray, Detection3DArray, KeyValue, VisionStats
from warehouse_interfaces.srv import SetActor


class Check(Node):
    def __init__(self):
        super().__init__("check_actors_live", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.actors = None
        self.detections = []
        self.stats = None
        self.truth = None
        self.create_subscription(PoseStamped, "/ground_truth", lambda m: setattr(self, "truth", m.pose), 10)
        self.create_subscription(ActorStateArray, "/warehouse/actor_states", lambda m: setattr(self, "actors", m), 10)
        self.create_subscription(Detection3DArray, "/vision/detections", self.detections.append, 10)
        self.create_subscription(VisionStats, "/vision/stats", lambda m: setattr(self, "stats", m), 10)
        self.set_actor = self.create_client(SetActor, "/warehouse/set_actor")
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def call(self, request):
        future = self.set_actor.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5)
        return future.result()

    def robot_pose(self):
        p = self.truth
        yaw = 2 * math.atan2(p.orientation.z, p.orientation.w)
        return p.position.x, p.position.y, yaw

    def navigate(self, x, y, yaw, timeout):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        future = self.nav.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        handle = future.result()
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result, timeout_sec=timeout)
        if not result.done():
            handle.cancel_goal_async()
            return None
        return result.result().status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nav", action="store_true", help="also drive a goal past a person")
    parser.add_argument("--output", default="artifacts/actors_live.json")
    options = parser.parse_args()
    rclpy.init()
    node = Check()
    report = {"passed": False}
    try:
        node.spin_for(3.0)
        assert node.actors is not None, "no /warehouse/actor_states"
        names = [a.name for a in node.actors.actors]
        people = {a.name: {kv.key: kv.value for kv in a.attributes} for a in node.actors.actors if a.kind == "person"}
        report["actors"] = names
        report["people_attributes"] = people
        assert node.set_actor.wait_for_service(timeout_sec=5), "/warehouse/set_actor unavailable"
        # Reset the target person's attributes (a previous run may have changed them),
        # then put them 3 m in front of the robot, facing it.
        target = "worker_no_helmet_red"
        reset = SetActor.Request(name=target, operation="set_attributes")
        reset.attributes = [KeyValue(key="helmet", value="false"), KeyValue(key="vest", value="orange")]
        assert node.call(reset).success, "attribute reset failed"
        node.spin_for(1.0)
        people = {a.name: {kv.key: kv.value for kv in a.attributes} for a in node.actors.actors if a.kind == "person"}
        report["people_attributes"] = people
        assert {v["helmet"] for v in people.values()} == {"true", "false"}, "expected both helmet states"
        assert node.truth is not None, "no /ground_truth"
        if options.nav:
            # Previous runs leave the robot elsewhere; start from the origin so the
            # person stands on the straight line to the goal.
            assert node.nav.wait_for_server(timeout_sec=20), "Nav2 unavailable"
            rx, ry, _ = node.robot_pose()
            if math.hypot(rx, ry) > 0.3:
                assert node.navigate(0.0, 0.0, 0.0, timeout=150) == GoalStatus.STATUS_SUCCEEDED, "could not return home"
                node.spin_for(1.0)
        rx, ry, ryaw = node.robot_pose()
        px = rx + 3.0 * math.cos(ryaw) - 0.3 * math.sin(ryaw)
        py = ry + 3.0 * math.sin(ryaw) + 0.3 * math.cos(ryaw)
        req = SetActor.Request(name=target, operation="teleport", pose=Pose())
        req.pose.position.x, req.pose.position.y = px, py
        req.pose.orientation.z, req.pose.orientation.w = math.sin((ryaw + math.pi) / 2), math.cos((ryaw + math.pi) / 2)
        res = node.call(req)
        assert res.success, res.message
        report["person_placed_at"] = [round(px, 2), round(py, 2)]
        node.detections.clear()
        node.spin_for(4.0)
        assert node.detections, "no /vision/detections (is the TruthDetector handler running?)"
        latest = node.detections[-1]
        persons = [d for d in latest.detections if d.label == "person" and d.has_position]
        assert persons, "person not detected with a map position"
        best = min(persons, key=lambda d: math.hypot(d.position.point.x - px, d.position.point.y - py))
        error = math.hypot(best.position.point.x - px, best.position.point.y - py)
        attrs = {kv.key: kv.value for kv in best.attributes}
        report["person_map_error_m"] = error
        report["person_attributes_detected"] = attrs
        assert error < 0.5, f"person map error {error:.2f} m"
        assert attrs.get("helmet") == "false" and attrs.get("vest") == "true", f"attributes {attrs}"
        res = node.call(SetActor.Request(name=target, operation="set_attributes",
                                         attributes=[KeyValue(key="helmet", value="true")]))
        assert res.success, res.message
        node.detections.clear()
        node.spin_for(3.0)
        persons = [d for d in node.detections[-1].detections if d.label == "person" and d.has_position]
        best = min(persons, key=lambda d: math.hypot(d.position.point.x - px, d.position.point.y - py))
        report["helmet_after_change"] = {kv.key: kv.value for kv in best.attributes}.get("helmet")
        assert report["helmet_after_change"] == "true", "helmet attribute did not update after set_attributes"
        report["vision_stats"] = None if node.stats is None else {
            "capture_fps": node.stats.capture_fps,
            "realtime_ratio": node.stats.realtime_ratio,
            "inference_ms": node.stats.inference_ms,
            "dropped_frames": node.stats.dropped_frames,
        }
        assert node.stats is not None and node.stats.realtime_ratio > 0.8, f"vision stats {report['vision_stats']}"
        if options.nav:
            # The person stands on the straight line to the goal; Nav2 must go around them.
            status = node.navigate(4.0, 0.0, 0.0, timeout=150)
            report["nav2_status"] = status
            assert status == GoalStatus.STATUS_SUCCEEDED, f"nav2 status {status}"
            node.spin_for(1.0)
            gx, gy, _ = node.robot_pose()
            report["goal_error_m"] = math.hypot(gx - 4.0, gy - 0.0)
            assert report["goal_error_m"] < 0.35, "robot did not stop at the goal"
        report["passed"] = True
    except AssertionError as error:
        report["error"] = str(error)
    finally:
        with open(options.output, "w") as f:
            json.dump(report, f, indent=2)
        print(json.dumps(report, indent=2))
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
