"""Drive a square with /cmd_vel (closed loop on /odom) while recording /odom and /ground_truth; save CSV.

    source scripts/env.sh; python docs/camp/odom_experiment.py --side 2.0 --out artifacts/dev/odom_square
Odometry starts at (0, 0, 0) and the robot spawns at the world origin, so both paths start together.
"""
import argparse, csv, math, time
from pathlib import Path

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry


def yaw(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class Recorder(Node):
    def __init__(self):
        super().__init__("odom_experiment", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.cmd = self.create_publisher(Twist, "/cmd_vel", 10)
        self.odom = self.truth = None
        self.rows = []
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)

    def on_odom(self, m):
        self.odom = (m.pose.pose.position.x, m.pose.pose.position.y, yaw(m.pose.pose.orientation))
        self.record()

    def on_truth(self, m):
        self.truth = (m.pose.position.x, m.pose.position.y, yaw(m.pose.orientation))

    def record(self):
        if self.odom and self.truth:
            t = self.get_clock().now().nanoseconds * 1e-9
            self.rows.append((t, *self.odom, *self.truth))

    def spin_a_bit(self):
        rclpy.spin_once(self, timeout_sec=0.05)

    def drive(self, v, w, until):
        """Publish (v, w) until `until(start_odom, odom)` is true; odom itself closes the loop."""
        msg = Twist(); msg.linear.x = float(v); msg.angular.z = float(w)
        start = self.odom
        while not until(start, self.odom):
            self.cmd.publish(msg); self.spin_a_bit()
        self.cmd.publish(Twist())
        end = time.monotonic() + 1.0
        while time.monotonic() < end:
            self.spin_a_bit()

    def forward(self, v, distance):
        self.drive(v, 0.0, lambda s, o: math.hypot(o[0] - s[0], o[1] - s[1]) >= distance)

    def turn(self, w, angle):
        self.drive(0.0, w, lambda s, o: ((o[2] - s[2] + math.pi) % (2 * math.pi) - math.pi) >= angle)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--side", type=float, default=2.0)
    ap.add_argument("--speed", type=float, default=0.3)
    ap.add_argument("--turn", type=float, default=0.5)
    ap.add_argument("--laps", type=int, default=1)
    ap.add_argument("--out", default="artifacts/dev/odom_square")
    a = ap.parse_args()
    rclpy.init()
    n = Recorder()
    while n.odom is None or n.truth is None:
        rclpy.spin_once(n, timeout_sec=0.1)
    for _ in range(a.laps):
        for _ in range(4):
            n.forward(a.speed, a.side - a.speed ** 2 / (2 * 0.45))     # stop early: the bridge decelerates at 0.45 m/s^2
            n.turn(a.turn, math.pi / 2 - a.turn ** 2 / (2 * 1.0) - 0.04)  # same for the 1.0 rad/s^2 angular ramp (+ latency)
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    with open(str(out) + ".csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["t", "odom_x", "odom_y", "odom_yaw", "true_x", "true_y", "true_yaw"]); w.writerows(n.rows)
    o = n.rows[-1]
    err = math.hypot(o[1] - o[4], o[2] - o[5]); dyaw = (o[3] - o[6] + math.pi) % (2 * math.pi) - math.pi
    print(f"samples={len(n.rows)}  final odom=({o[1]:.3f}, {o[2]:.3f}, {math.degrees(o[3]):.1f} deg)  truth=({o[4]:.3f}, {o[5]:.3f}, {math.degrees(o[6]):.1f} deg)  pos error={err*100:.1f} cm  yaw error={math.degrees(dyaw):.2f} deg")
    n.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
