"""Probe MoveIt IK for the lesson-09 figures (needs the simulator in moveit mode).

    python docs/camp/ik_probe.py --out artifacts/dev/ik_probe.pkl

Saves: "reach" = left-arm IK success on an x-z grid at y = 0.20 m (GRASP_FORWARD, collision-aware, 3 seeds),
"multi" = distinct IK solutions for TCP (0.45, 0.20, 0.95) from random seeds (joint vectors).
"""
import argparse
import pickle

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseStamped
from moveit_msgs.msg import MoveItErrorCodes
from moveit_msgs.srv import GetPositionIK

from warehouse_skills.moveit_client import make_pose

NAMES = [f"openarm_left_joint{i}" for i in range(1, 8)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/dev/ik_probe.pkl")
    ap.add_argument("--step", type=float, default=0.05)
    o = ap.parse_args()
    rclpy.init()
    node = Node("ik_probe", parameter_overrides=[Parameter("use_sim_time", value=True)])
    cli = node.create_client(GetPositionIK, "/compute_ik")
    cli.wait_for_service(timeout_sec=30)
    rng = np.random.default_rng(0)

    def ik(xyz, seed):
        req = GetPositionIK.Request()
        r = req.ik_request
        r.group_name, r.ik_link_name = "left_arm", "openarm_left_hand_tcp"
        r.avoid_collisions = True
        r.timeout.nanosec = 200_000_000
        r.pose_stamped = PoseStamped()
        r.pose_stamped.header.frame_id = "base_footprint"
        r.pose_stamped.pose = make_pose(xyz)
        r.robot_state.is_diff = True
        r.robot_state.joint_state.name = NAMES
        r.robot_state.joint_state.position = [float(v) for v in seed]
        f = cli.call_async(req)
        rclpy.spin_until_future_complete(node, f, timeout_sec=5)
        res = f.result()
        if res is None or res.error_code.val != MoveItErrorCodes.SUCCESS:
            return None
        q = dict(zip(res.solution.joint_state.name, res.solution.joint_state.position))
        return np.array([q[n] for n in NAMES])

    ready = np.array([0, 0, 0, 1.65, 0, 0, 0.0])
    xs = np.round(np.arange(0.15, 0.80 + 1e-9, o.step), 3)
    zs = np.round(np.arange(0.45, 1.30 + 1e-9, o.step), 3)
    reach = np.zeros((len(zs), len(xs)), dtype=bool)
    for i, z in enumerate(zs):
        for j, x in enumerate(xs):
            seeds = [ready] + [rng.uniform(-1.5, 1.5, 7) for _ in range(2)]
            reach[i, j] = any(ik((x, 0.20, z), s) is not None for s in seeds)
        print(f"z={z:.2f}: {''.join('#' if v else '.' for v in reach[i])}")
    multi = []
    for _ in range(60):
        q = ik((0.45, 0.20, 0.95), rng.uniform(-2.0, 2.0, 7))
        if q is not None and all(np.abs(q - m).max() > 0.3 for m in multi):
            multi.append(q)
    print(f"distinct solutions: {len(multi)}")
    pickle.dump(dict(xs=xs, zs=zs, y=0.20, reach=reach, multi=multi), open(o.out, "wb"))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
