"""Record what MoveIt planned and what the MuJoCo arm actually did (for the lesson figures).

    python docs/camp/arm_record.py --seconds 40 --out artifacts/dev/arm_run.pkl

Saves: every /display_planned_path (joint names, time_from_start, positions), every /joint_states
(arm + finger joints) with sim-time stamps, and both TCP positions in base_footprint from TF at 20 Hz (key "tcp").
"""
import argparse
import pickle
import time

import rclpy
import rclpy.time
from rclpy.node import Node
from rclpy.parameter import Parameter
from moveit_msgs.msg import DisplayTrajectory
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformException, TransformListener


def stamp(s):
    return s.sec + s.nanosec * 1e-9


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=40)
    parser.add_argument("--out", default="artifacts/dev/arm_run.pkl")
    options = parser.parse_args()
    rclpy.init()
    node = Node("arm_record", parameter_overrides=[Parameter("use_sim_time", value=True)])
    data = dict(plans=[], states=[], tcp=[])
    tf = Buffer()
    TransformListener(tf, node, spin_thread=False)

    def tcp():
        row = dict(t=node.get_clock().now().nanoseconds * 1e-9)
        for side in ("left", "right"):
            try:
                p = tf.lookup_transform("base_footprint", f"openarm_{side}_hand_tcp", rclpy.time.Time()).transform.translation
                row[side] = (p.x, p.y, p.z)
            except TransformException:
                return
        data["tcp"].append(row)

    def plan(msg):
        for t in msg.trajectory:
            jt = t.joint_trajectory
            data["plans"].append(dict(
                t=node.get_clock().now().nanoseconds * 1e-9, names=list(jt.joint_names),
                times=[stamp(p.time_from_start) for p in jt.points],
                positions=[list(p.positions) for p in jt.points]))
        print(f"plan: {len(data['plans'])}")

    def state(msg):
        data["states"].append(dict(t=stamp(msg.header.stamp), names=list(msg.name), positions=list(msg.position)))

    node.create_subscription(DisplayTrajectory, "/display_planned_path", plan, 10)
    node.create_subscription(JointState, "/joint_states", state, 100)
    node.create_timer(0.05, tcp)
    end = time.time() + options.seconds
    while rclpy.ok() and time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    with open(options.out, "wb") as f:
        pickle.dump(data, f)
    print(f"saved {len(data['plans'])} plans, {len(data['states'])} states, {len(data['tcp'])} tcp -> {options.out}")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
