"""Day-1 integrated demo: patrol named warehouse locations with Nav2.

Publishes the mission as JSON on /patrol/status (std_msgs/String, latched) so the web dashboard
(dashboard/server.py) or `ros2 topic echo` can follow it, and listens to /patrol/command
("start" | "cancel"). At every stop it compares where the robot really is (/ground_truth) with
what AMCL and odom believe.

    ./scripts/mobile_openarm nav moveit:=false map:=$PWD/artifacts/maps/my_warehouse.yaml   # 터미널 1
    python lessons/04_navigation/patrol.py                        # 터미널 2: 바로 출발
    python lessons/04_navigation/patrol.py --wait                 # 대시보드의 [순찰 시작] 버튼을 기다린다
    python lessons/04_navigation/patrol.py --route pick_table,center_aisle --loops 2
"""
import argparse
import json
import math
import time
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String

DEFAULT_ROUTE = ["pick_table", "rack_a", "rack_b", "place_table", "center_aisle"]
NEAR = "near"          # stopped just outside Nav2's xy_goal_tolerance (0.08 m) and not moving: count as arrived
NEAR_DIST, NEAR_STALL_S = 0.25, 8.0
LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def load_locations():
    path = Path(get_package_share_directory("warehouse_lecture")) / "worlds/locations.yaml"
    return yaml.safe_load(path.read_text())["locations"]


class Patrol(Node):
    def __init__(self, route, loops):
        super().__init__("patrol", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        places = load_locations()
        unknown = [n for n in route if n not in places]
        if unknown:
            raise SystemExit(f"unknown location(s) {unknown}; choose from {', '.join(places)}")
        stops = [n for _ in range(loops) for n in route]
        self.stops = [dict(name=n, label=places[n].get("aliases", [n])[0], goal=[float(v) for v in places[n]["base_goal"]],
                           status="pending", time=None, err_amcl=None, err_odom=None) for n in stops]
        self.state, self.index, self.message = "waiting", -1, "시작 명령을 기다리는 중"
        self.started = self.leg_started = None
        self.feedback = {}
        self.truth = self.amcl = self.odom = None
        self.command = None
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.pub = self.create_publisher(String, "/patrol/status", LATCHED)
        self.create_subscription(String, "/patrol/command", self.on_command, 10)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self.on_amcl, LATCHED)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_timer(0.5, self.publish)

    # --- inputs -----------------------------------------------------------
    def on_command(self, msg):
        self.command = msg.data.strip().lower()

    def on_truth(self, m):
        self.truth = (m.pose.position.x, m.pose.position.y, yaw_of(m.pose.orientation))

    def on_amcl(self, m):
        p = m.pose.pose
        self.amcl = (p.position.x, p.position.y, yaw_of(p.orientation))

    def on_odom(self, m):
        p = m.pose.pose
        self.odom = (p.position.x, p.position.y, yaw_of(p.orientation))

    def now(self):
        return self.get_clock().now().nanoseconds * 1e-9

    # --- output -----------------------------------------------------------
    def publish(self):
        now = self.now()
        status = dict(state=self.state, index=self.index, message=self.message, stops=self.stops, sim_time=now,
                      elapsed=None if self.started is None else now - self.started,
                      leg_elapsed=None if self.leg_started is None else now - self.leg_started, feedback=self.feedback)
        self.pub.publish(String(data=json.dumps(status, ensure_ascii=False)))

    def spin_for(self, seconds):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    # --- mission ------------------------------------------------------------
    def go(self, stop):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        x, y, yaw = stop["goal"]
        goal.pose.pose.position.x, goal.pose.pose.position.y = x, y
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)

        def on_feedback(fb):
            f = fb.feedback
            self.feedback = dict(distance_remaining=round(f.distance_remaining, 2), recoveries=f.number_of_recoveries,
                                 eta=round(f.estimated_time_remaining.sec + f.estimated_time_remaining.nanosec * 1e-9, 1))

        future = self.nav.send_goal_async(goal, feedback_callback=on_feedback)
        while not future.done():
            rclpy.spin_once(self, timeout_sec=0.05)
        handle = future.result()
        if not handle.accepted:
            return GoalStatus.STATUS_ABORTED
        result = handle.get_result_async()
        still, still_since = self.truth, time.monotonic()
        while not result.done():
            rclpy.spin_once(self, timeout_sec=0.05)
            # Watchdog: DWB can stall a few cm outside the goal tolerance, sideways to the goal, sending
            # rotations too small to overcome wheel friction. Close enough for a patrol: stop and move on.
            if self.truth and still and (math.hypot(self.truth[0] - still[0], self.truth[1] - still[1]) > 0.01
                                         or abs(self.truth[2] - still[2]) > 0.02):
                still, still_since = self.truth, time.monotonic()
            near = self.feedback.get("distance_remaining", 9.9) < NEAR_DIST
            if near and time.monotonic() - still_since > NEAR_STALL_S:
                self.command = "cancel_near"
            if self.command in ("cancel", "cancel_near"):
                reason = self.command
                self.command = None
                self.command = None
                cancel = handle.cancel_goal_async()
                while not cancel.done():
                    rclpy.spin_once(self, timeout_sec=0.05)
                return NEAR if reason == "cancel_near" else GoalStatus.STATUS_CANCELED
        return result.result().status

    def errors(self):
        """Distance from the true pose (world = map origin: spawn at (0, 0, 0)) to what AMCL and odom believe."""
        t = self.truth
        err = lambda p: None if (t is None or p is None) else round(math.hypot(p[0] - t[0], p[1] - t[1]), 3)
        return err(self.amcl), err(self.odom)

    def run(self, wait):
        if not self.nav.wait_for_server(timeout_sec=30):
            raise SystemExit("Nav2 (/navigate_to_pose) is not running: start ./scripts/mobile_openarm nav first")
        while self.now() == 0.0:
            rclpy.spin_once(self, timeout_sec=0.1)
        if wait:
            while self.command != "start":
                rclpy.spin_once(self, timeout_sec=0.1)
        self.command = None
        self.state, self.started = "running", self.now()
        print(f"patrol: {len(self.stops)} stops: {' → '.join(s['name'] for s in self.stops)}", flush=True)
        for i, stop in enumerate(self.stops):
            self.index, self.leg_started, self.feedback = i, self.now(), {}
            stop["status"] = "active"
            self.message = f"{stop['label']}({stop['name']}) 로 이동 중"
            self.publish()
            status = self.go(stop)
            stop["time"] = round(self.now() - self.leg_started, 1)
            if status == GoalStatus.STATUS_CANCELED:
                stop["status"], self.state, self.message = "canceled", "canceled", "취소됨"
                break
            if status not in (GoalStatus.STATUS_SUCCEEDED, NEAR):
                stop["status"], self.state, self.message = "failed", "failed", f"{stop['name']} 도착 실패 (status {status})"
                break
            self.spin_for(1.0)                                   # let AMCL settle at the stop
            stop["err_amcl"], stop["err_odom"] = self.errors()
            stop["status"] = "done" if status == GoalStatus.STATUS_SUCCEEDED else "near"
            print(f"  {i + 1}/{len(self.stops)} {stop['name']:<13} {stop['time']:5.1f} s   "
                  f"AMCL 오차 {stop['err_amcl']:.3f} m   odom 오차 {stop['err_odom']:.3f} m"
                  + ("   (목표 근처에서 멈춤 → 도착 처리)" if status == NEAR else ""), flush=True)
        else:
            self.state, self.message = "done", f"순찰 완료: {len(self.stops)} 곳, {self.now() - self.started:.0f} s"
        self.index, self.leg_started = -1, None
        self.publish()
        print(f"patrol: {self.state} ({self.message})", flush=True)
        self.spin_for(1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", default=",".join(DEFAULT_ROUTE), help="comma-separated names from locations.yaml")
    ap.add_argument("--loops", type=int, default=1)
    ap.add_argument("--wait", action="store_true", help="wait for 'start' on /patrol/command (dashboard button)")
    a = ap.parse_args()
    rclpy.init()
    node = Patrol([n.strip() for n in a.route.split(",") if n.strip()], a.loops)
    try:
        node.run(a.wait)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
