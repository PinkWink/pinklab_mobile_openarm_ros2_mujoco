"""Record a Pick & Place run for the lesson-10 figures (base, parcels, arms, gripper, docking command).

    python docs/camp/pick_record.py --seconds 200 --out artifacts/dev/pick_run.pkl

Saves (sim-time stamps): /joint_states (all joints), /ground_truth (base pose in the world), /warehouse/object_poses
(parcels in the world), /cmd_vel, /pick_place feedback (phase, detail), both TCP positions in base_footprint (TF 20 Hz),
/vision/detections (label, bbox, position) and /vision/markers (id, pose in base_footprint, pixel corners).
"""
import argparse
import pickle
import time

import rclpy
import rclpy.time
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseArray, PoseStamped, Twist
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformException, TransformListener
from warehouse_interfaces.action import PickPlace
from warehouse_interfaces.msg import ArucoMarkerArray, Detection3DArray


def stamp(s):
    return s.sec + s.nanosec * 1e-9


def pose(p):
    return (p.position.x, p.position.y, p.position.z, p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=200)
    parser.add_argument("--out", default="artifacts/dev/pick_run.pkl")
    options = parser.parse_args()
    rclpy.init()
    node = Node("pick_record", parameter_overrides=[Parameter("use_sim_time", value=True)])
    now = lambda: node.get_clock().now().nanoseconds * 1e-9  # noqa: E731
    data = dict(states=[], base=[], objects=[], cmd=[], feedback=[], tcp=[], detections=[], markers=[])
    tf = Buffer()
    TransformListener(tf, node, spin_thread=False)

    def tcp():
        row = dict(t=now())
        for side in ("left", "right"):
            try:
                p = tf.lookup_transform("base_footprint", f"openarm_{side}_hand_tcp", rclpy.time.Time()).transform.translation
                row[side] = (p.x, p.y, p.z)
            except TransformException:
                return
        data["tcp"].append(row)

    def detections(m):
        data["detections"].append(dict(t=stamp(m.header.stamp), items=[dict(
            label=d.label, score=d.score, camera=d.camera, bbox=tuple(d.bbox_xyxy), has_position=d.has_position,
            frame=d.position.header.frame_id, position=(d.position.point.x, d.position.point.y, d.position.point.z))
            for d in m.detections]))

    def markers(m):
        data["markers"].append(dict(t=stamp(m.header.stamp), frame=m.header.frame_id, items=[dict(
            id=k.id, pose=pose(k.pose), normal_yaw=k.normal_yaw, distance=k.distance, corners=tuple(k.corners)) for k in m.markers]))

    node.create_subscription(JointState, "/joint_states",
                             lambda m: data["states"].append(dict(t=stamp(m.header.stamp), names=list(m.name), positions=list(m.position))), 100)
    node.create_subscription(PoseStamped, "/ground_truth", lambda m: data["base"].append(dict(t=stamp(m.header.stamp), pose=pose(m.pose))), 50)
    node.create_subscription(PoseArray, "/warehouse/object_poses",
                             lambda m: data["objects"].append(dict(t=now(), poses=[pose(p) for p in m.poses])), 20)
    node.create_subscription(Twist, "/cmd_vel", lambda m: data["cmd"].append(dict(t=now(), vx=m.linear.x, vy=m.linear.y, wz=m.angular.z)), 50)
    node.create_subscription(PickPlace.Impl.FeedbackMessage, "/pick_place/_action/feedback",
                             lambda m: data["feedback"].append(dict(t=now(), phase=m.feedback.phase, detail=m.feedback.detail)), 50)
    node.create_subscription(Detection3DArray, "/vision/detections", detections, 20)
    node.create_subscription(ArucoMarkerArray, "/vision/markers", markers, 20)
    node.create_timer(0.05, tcp)
    end = time.time() + options.seconds
    last = 0
    while rclpy.ok() and time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
        if len(data["feedback"]) != last:
            last = len(data["feedback"])
            f = data["feedback"][-1]
            print(f"{f['t']:7.1f} [{f['phase']}] {f['detail']}", flush=True)
    with open(options.out, "wb") as f:
        pickle.dump(data, f)
    print("saved " + ", ".join(f"{len(v)} {k}" for k, v in data.items()) + f" -> {options.out}")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
