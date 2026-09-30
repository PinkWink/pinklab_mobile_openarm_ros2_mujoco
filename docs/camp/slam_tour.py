"""Drive a fixed loop through the warehouse on /odom so SLAM Toolbox can build a map (teleop 대신 쓰는 자동 순회).

    source /opt/ros/jazzy/setup.bash; source scripts/env.sh
    ./scripts/mobile_openarm slam                                  # 터미널 1
    python docs/camp/slam_tour.py                                  # 터미널 2
    python docs/camp/slam_tour.py --shots artifacts/dev/slam_shots # 웨이포인트마다 화면 캡처 (강의 자료용)

Waypoints are world coordinates; odom starts at the spawn (0, 0, 0), so they are odom coordinates as well.
"""
import argparse
import math
import subprocess
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile
import numpy as np

# perimeter loop: east aisle → north lane → west lane → south lane → back to the start
ROUTE = [(6.4, 0.0), (6.4, 4.8), (-6.6, 4.8), (-6.6, -4.8), (6.4, -4.8), (6.4, 0.0), (0.0, 0.0)]


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Tour(Node):
    def __init__(self):
        super().__init__("slam_tour", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.pose = None
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.map = None
        self.create_subscription(OccupancyGrid, "/map", self.on_map, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))

    def on_map(self, m):
        self.map = m

    def save_map(self, path):
        """Keep the latest /map and the robot odom pose (for drawing the map as it grows)."""
        m = self.map
        if m is None:
            return
        np.savez_compressed(path, data=np.array(m.data, dtype=np.int8).reshape(m.info.height, m.info.width),
                            resolution=m.info.resolution, origin=[m.info.origin.position.x, m.info.origin.position.y],
                            pose=self.pose, stamp=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)

    def on_odom(self, m):
        q = m.pose.pose.orientation
        self.pose = (m.pose.pose.position.x, m.pose.pose.position.y,
                     math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))

    def send(self, v, w):
        msg = Twist(); msg.linear.x = float(v); msg.angular.z = float(w)
        self.cmd.publish(msg)
        rclpy.spin_once(self, timeout_sec=0.05)

    def turn_to(self, heading):
        while abs(e := wrap(heading - self.pose[2])) > 0.03:
            self.send(0.0, math.copysign(max(0.12, min(0.5, 1.5 * abs(e))), e))   # at least 0.12 rad/s: slower stalls on friction

    def go(self, x, y, speed):
        self.turn_to(math.atan2(y - self.pose[1], x - self.pose[0]))
        best, since = float("inf"), time.monotonic()
        while (d := math.hypot(x - self.pose[0], y - self.pose[1])) > 0.08:
            e = wrap(math.atan2(y - self.pose[1], x - self.pose[0]) - self.pose[2])
            self.send(min(speed, 0.6 * d + 0.05) * max(0.0, math.cos(e)), 1.5 * e)
            if d < best - 0.02:
                best, since = d, time.monotonic()
            elif time.monotonic() - since > 5.0:          # blocked (person, forklift ...): skip this waypoint
                print(f"  blocked {d:.2f} m before ({x:+.1f}, {y:+.1f}); skipping", flush=True)
                break
        for _ in range(20):
            self.send(0.0, 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=0.3)
    ap.add_argument("--shots", help="capture the screen (DISPLAY) after each waypoint into this folder")
    ap.add_argument("--record", help="save /map + robot pose as wp<i>.npz at the start and after each waypoint")
    a = ap.parse_args()
    rclpy.init()
    n = Tour()
    while n.pose is None:
        rclpy.spin_once(n, timeout_sec=0.1)
    start = time.monotonic()
    if a.record:
        Path(a.record).mkdir(parents=True, exist_ok=True)
        t0 = time.monotonic()
        while n.map is None and time.monotonic() - t0 < 5.0:
            rclpy.spin_once(n, timeout_sec=0.1)
        n.save_map(f"{a.record}/wp0.npz")
    for i, (x, y) in enumerate(ROUTE, 1):
        n.go(x, y, a.speed)
        print(f"waypoint {i}/{len(ROUTE)} ({x:+.1f}, {y:+.1f}) reached  odom=({n.pose[0]:+.2f}, {n.pose[1]:+.2f})  {time.monotonic() - start:.0f} s", flush=True)
        if a.record:
            end = time.monotonic() + 1.2               # map_update_interval is 1 s: wait for the next /map
            while time.monotonic() < end:
                rclpy.spin_once(n, timeout_sec=0.05)
            n.save_map(f"{a.record}/wp{i}.npz")
        if a.shots:
            Path(a.shots).mkdir(parents=True, exist_ok=True)
            subprocess.run(["import", "-window", "root", "-crop", "2230x866+0+0", f"{a.shots}/wp{i}.png"], check=False)
    n.turn_to(0.0)
    n.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
