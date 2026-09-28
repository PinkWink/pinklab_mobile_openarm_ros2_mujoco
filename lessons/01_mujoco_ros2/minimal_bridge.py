"""Minimal MuJoCo <-> ROS 2 bridge: a 2-link arm with a camera on the tip.

One process steps MuJoCo and speaks ROS 2. Everything the big warehouse bridge does is a bigger version of this loop.

  publishes   /clock (rosgraph_msgs/Clock)        simulation time -> use_sim_time nodes follow it
              /joint_states (sensor_msgs/JointState)
              /tf (base_link -> link1 -> link2 -> camera_link)
              /tip_camera/image_raw (sensor_msgs/Image, rgb8)   rendered inside MuJoCo
  subscribes  /cmd (std_msgs/Float64MultiArray)   [joint1, joint2] target angles in rad -> position actuators

  python lessons/01_mujoco_ros2/minimal_bridge.py --viewer
  ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"
"""
import argparse
import time
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import Float64MultiArray
from tf2_ros import TransformBroadcaster

XML = Path(__file__).with_name("two_link_arm.xml")


def stamp(t):
    """float seconds -> builtin_interfaces/Time"""
    from builtin_interfaces.msg import Time
    return Time(sec=int(t), nanosec=int((t - int(t)) * 1e9))


class MinimalBridge(Node):
    def __init__(self, viewer, camera_hz, joint_hz):
        super().__init__("minimal_bridge", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.model = mujoco.MjModel.from_xml_path(str(XML))
        self.data = mujoco.MjData(self.model)
        self.joints = ["joint1", "joint2"]
        self.bodies = ["base_link", "link1", "link2", "camera_link"]

        self.clock_pub = self.create_publisher(Clock, "/clock", 10)
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.image_pub = self.create_publisher(Image, "/tip_camera/image_raw", 2)
        self.tf_pub = TransformBroadcaster(self)
        self.create_subscription(Float64MultiArray, "/cmd", self.on_cmd, 10)

        self.renderer = mujoco.Renderer(self.model, height=240, width=320)
        self.joint_period, self.camera_period = 1.0 / joint_hz, 1.0 / camera_hz
        self.next_joint = self.next_camera = 0.0
        self.viewer = None
        if viewer:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data)
        self.get_logger().info(f"bridge up: {self.model.nq} joints, camera 320x240 @ {camera_hz} Hz, cmd on /cmd")

    # ---- ROS -> MuJoCo --------------------------------------------------------------------------
    def on_cmd(self, msg):
        if len(msg.data) == self.model.nu:
            self.data.ctrl[:] = np.clip(msg.data, self.model.actuator_ctrlrange[:, 0], self.model.actuator_ctrlrange[:, 1])

    # ---- MuJoCo -> ROS --------------------------------------------------------------------------
    def publish_joints(self, t):
        js = JointState()
        js.header.stamp = stamp(t)
        js.name = self.joints
        js.position = [float(self.data.qpos[self.model.joint(j).qposadr[0]]) for j in self.joints]
        js.velocity = [float(self.data.qvel[self.model.joint(j).dofadr[0]]) for j in self.joints]
        self.joint_pub.publish(js)

        tfs = []
        for parent, child in zip(self.bodies[:-1], self.bodies[1:]):
            p, c = self.model.body(parent).id, self.model.body(child).id
            # child pose expressed in the parent body frame: q_rel = conj(q_parent) * q_child
            q_parent_inv, q_rel, pos_rel = np.zeros(4), np.zeros(4), np.zeros(3)
            mujoco.mju_negQuat(q_parent_inv, self.data.xquat[p])
            mujoco.mju_mulQuat(q_rel, q_parent_inv, self.data.xquat[c])
            mujoco.mju_rotVecQuat(pos_rel, self.data.xpos[c] - self.data.xpos[p], q_parent_inv)
            tf = TransformStamped()
            tf.header.stamp, tf.header.frame_id, tf.child_frame_id = stamp(t), parent, child
            tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = map(float, pos_rel)
            tf.transform.rotation.w, tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z = map(float, q_rel)
            tfs.append(tf)
        self.tf_pub.sendTransform(tfs)

    def publish_camera(self, t):
        self.renderer.update_scene(self.data, camera="tip_camera")
        rgb = self.renderer.render()
        img = Image()
        img.header.stamp, img.header.frame_id = stamp(t), "camera_link"
        img.height, img.width, img.encoding, img.step = rgb.shape[0], rgb.shape[1], "rgb8", rgb.shape[1] * 3
        img.data = rgb.tobytes()
        self.image_pub.publish(img)

    # ---- the loop -------------------------------------------------------------------------------
    def spin(self):
        dt = self.model.opt.timestep
        wall0 = time.monotonic()
        while rclpy.ok() and (self.viewer is None or self.viewer.is_running()):
            mujoco.mj_step(self.model, self.data)             # 1. physics step
            t = self.data.time
            self.clock_pub.publish(Clock(clock=stamp(t)))     # 2. sim time out
            if t >= self.next_joint:                          # 3. joint states + TF at joint_hz
                self.publish_joints(t); self.next_joint += self.joint_period
            if t >= self.next_camera:                         # 4. camera image at camera_hz
                self.publish_camera(t); self.next_camera += self.camera_period
            rclpy.spin_once(self, timeout_sec=0)              # 5. deliver /cmd callbacks
            if self.viewer is not None:
                self.viewer.sync()
            lag = wall0 + t - time.monotonic()                # 6. keep real time
            if lag > 0:
                time.sleep(lag)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--viewer", action="store_true", help="open the MuJoCo viewer window")
    ap.add_argument("--camera-hz", type=float, default=5.0)
    ap.add_argument("--joint-hz", type=float, default=50.0)
    args = ap.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)   # Ctrl+C -> KeyboardInterrupt, not a mid-loop shutdown
    node = MinimalBridge(args.viewer, args.camera_hz, args.joint_hz)
    try:
        node.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
