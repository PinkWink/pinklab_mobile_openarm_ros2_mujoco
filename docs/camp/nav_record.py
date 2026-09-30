"""Record what Nav2 is doing (for the lesson figures): costmaps, plans, AMCL particles, poses.

    python docs/camp/nav_record.py --seconds 120 --out artifacts/dev/nav_run.pkl

Saves: global costmap (latest), local costmap and particle cloud about once a second, every /plan,
/amcl_pose, /ground_truth and /odom with their sim-time stamps.
"""
import argparse
import pickle
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from nav2_msgs.msg import ParticleCloud


def yaw(q):
    return float(np.arctan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))


def grid(m):
    return dict(t=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, res=m.info.resolution,
                origin=(m.info.origin.position.x, m.info.origin.position.y),
                data=np.array(m.data, dtype=np.int16).reshape(m.info.height, m.info.width))


class Rec(Node):
    def __init__(self):
        super().__init__("nav_record", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        best = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.d = dict(global_costmap=None, local=[], plans=[], particles=[], amcl=[], truth=[], odom=[])
        self.last = {}
        self.create_subscription(OccupancyGrid, "/global_costmap/costmap", self.on_global, latched)
        self.create_subscription(OccupancyGrid, "/local_costmap/costmap", self.on_local, 10)
        self.create_subscription(Path, "/plan", self.on_plan, 10)
        self.create_subscription(ParticleCloud, "/particle_cloud", self.on_particles, best)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self.on_amcl, latched)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)

    def every(self, key, period=1.0):
        now = time.monotonic()
        if now - self.last.get(key, 0.0) < period:
            return False
        self.last[key] = now
        return True

    def on_global(self, m):
        self.d["global_costmap"] = grid(m)

    def on_local(self, m):
        if self.every("local"):
            self.d["local"].append(grid(m))

    def on_plan(self, m):
        self.d["plans"].append(dict(t=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                                    xy=np.array([(p.pose.position.x, p.pose.position.y) for p in m.poses])))

    def on_particles(self, m):
        if self.every("particles"):
            self.d["particles"].append(dict(t=m.header.stamp.sec + m.header.stamp.nanosec * 1e-9,
                                            xyt=np.array([(p.pose.position.x, p.pose.position.y, yaw(p.pose.orientation)) for p in m.particles]),
                                            w=np.array([p.weight for p in m.particles])))

    def on_amcl(self, m):
        p = m.pose.pose
        self.d["amcl"].append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, p.position.x, p.position.y, yaw(p.orientation),
                               m.pose.covariance[0], m.pose.covariance[7], m.pose.covariance[35]))

    def on_truth(self, m):
        if self.every("truth", 0.05):
            p = m.pose
            self.d["truth"].append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, p.position.x, p.position.y, yaw(p.orientation)))

    def on_odom(self, m):
        if self.every("odom", 0.05):
            p = m.pose.pose
            self.d["odom"].append((m.header.stamp.sec + m.header.stamp.nanosec * 1e-9, p.position.x, p.position.y, yaw(p.orientation),
                                   m.twist.twist.linear.x, m.twist.twist.angular.z))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--out", default="artifacts/dev/nav_run.pkl")
    a = ap.parse_args()
    rclpy.init()
    n = Rec()
    end = time.monotonic() + a.seconds
    try:
        while time.monotonic() < end:
            rclpy.spin_once(n, timeout_sec=0.05)
    except KeyboardInterrupt:
        pass
    pickle.dump(n.d, open(a.out, "wb"))
    print("saved", a.out, {k: (len(v) if isinstance(v, list) else v is not None) for k, v in n.d.items()})


if __name__ == "__main__":
    main()
