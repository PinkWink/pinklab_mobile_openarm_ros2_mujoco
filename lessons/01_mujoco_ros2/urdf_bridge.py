"""MuJoCo <-> ROS 2 bridge for a robot that starts as a URDF.

The model comes from two_link_arm.urdf (urdf_to_mjcf.build). The bridge sends out what only the simulator knows and
leaves the rest to standard ROS 2 nodes: robot_state_publisher turns /joint_states + the same URDF into /tf.

  publishes   /clock (rosgraph_msgs/Clock)                 data.time
              /joint_states (sensor_msgs/JointState)       qpos, qvel, actuator torque
              /tip_camera/image_raw (sensor_msgs/Image)    rendered inside MuJoCo, frame camera_optical_frame
              /tip_pose (geometry_msgs/PoseStamped)        camera_optical_frame seen from base_link, from xpos / xquat
  subscribes  /cmd (std_msgs/Float64MultiArray)            target angles in rad, actuator order -> data.ctrl

  python lessons/01_mujoco_ros2/urdf_bridge.py --viewer
  ros2 launch lessons/01_mujoco_ros2/view_urdf.launch.py sim:=true
  ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"
"""
import argparse
import time

import mujoco
import mujoco.viewer
import numpy as np
import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, JointState
from std_msgs.msg import Float64MultiArray

from urdf_to_mjcf import build

BASE, TIP, CAMERA = "base_link", "camera_optical_frame", "tip_camera"


def stamp(t):
    """float seconds -> builtin_interfaces/Time"""
    return Time(sec=int(t), nanosec=int((t - int(t)) * 1e9))


class UrdfBridge(Node):
    def __init__(self, viewer, state_hz, camera_hz):
        super().__init__("urdf_bridge", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        _, self.model = build()                              # URDF -> MjModel
        self.data = mujoco.MjData(self.model)
        # joint names and array addresses, read from the model (nothing typed by hand)
        self.joints = [self.model.joint(i).name for i in range(self.model.njnt)]
        self.qadr = [int(self.model.joint(j).qposadr[0]) for j in self.joints]
        self.vadr = [int(self.model.joint(j).dofadr[0]) for j in self.joints]

        self.clock_pub = self.create_publisher(Clock, "/clock", 10)
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.image_pub = self.create_publisher(Image, "/tip_camera/image_raw", 2)
        self.pose_pub = self.create_publisher(PoseStamped, "/tip_pose", 10)
        self.create_subscription(Float64MultiArray, "/cmd", self.on_cmd, 10)

        self.renderer = mujoco.Renderer(self.model, height=240, width=320)
        self.state_period, self.camera_period = 1.0 / state_hz, 1.0 / camera_hz
        self.next_state = self.next_camera = 0.0
        self.viewer = None
        if viewer:
            self.viewer = mujoco.viewer.launch_passive(self.model, self.data, show_left_ui=False, show_right_ui=False)
            cam = self.viewer.cam                            # side view, the same direction as the RViz config
            cam.lookat[:], cam.distance, cam.azimuth, cam.elevation = [0.25, 0.0, 0.25], 1.5, 90, -15
        self.get_logger().info(f"bridge up: joints {self.joints}, {self.model.nu} actuators, cmd on /cmd")

    # ---- ROS -> MuJoCo --------------------------------------------------------------------------
    def on_cmd(self, msg):
        q = np.asarray(msg.data, dtype=float)
        if q.size != self.model.nu or not np.all(np.isfinite(q)):
            self.get_logger().warn(f"/cmd ignored: need {self.model.nu} finite values, got {list(msg.data)}")
            return
        low, high = self.model.actuator_ctrlrange.T
        self.data.ctrl[:] = np.clip(q, low, high)            # the next mj_step moves the arm

    # ---- MuJoCo -> ROS --------------------------------------------------------------------------
    def publish_joints(self, t):
        js = JointState()
        js.header.stamp = stamp(t)
        js.name = self.joints
        js.position = self.data.qpos[self.qadr].tolist()
        js.velocity = self.data.qvel[self.vadr].tolist()
        js.effort = self.data.qfrc_actuator[self.vadr].tolist()
        self.joint_pub.publish(js)

    def publish_tip_pose(self, t):
        b, c = self.model.body(BASE).id, self.model.body(TIP).id
        # xpos / xquat are world poses. Pose of the tip seen from the base: q = conj(q_base) * q_tip
        q_base_inv, q, p = np.zeros(4), np.zeros(4), np.zeros(3)
        mujoco.mju_negQuat(q_base_inv, self.data.xquat[b])
        mujoco.mju_mulQuat(q, q_base_inv, self.data.xquat[c])
        mujoco.mju_rotVecQuat(p, self.data.xpos[c] - self.data.xpos[b], q_base_inv)
        msg = PoseStamped()
        msg.header.stamp, msg.header.frame_id = stamp(t), BASE
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = p.tolist()
        o = msg.pose.orientation
        o.w, o.x, o.y, o.z = q.tolist()                      # MuJoCo quaternion order is [w, x, y, z]
        self.pose_pub.publish(msg)

    def publish_camera(self, t):
        self.renderer.update_scene(self.data, camera=CAMERA)
        rgb = self.renderer.render()                         # (240, 320, 3) uint8
        img = Image()
        img.header.stamp, img.header.frame_id = stamp(t), TIP
        img.height, img.width, img.encoding, img.step = rgb.shape[0], rgb.shape[1], "rgb8", rgb.shape[1] * 3
        img.data = rgb.tobytes()
        self.image_pub.publish(img)

    # ---- the loop -------------------------------------------------------------------------------
    def spin(self):
        wall0 = time.monotonic()
        while rclpy.ok() and (self.viewer is None or self.viewer.is_running()):
            mujoco.mj_step(self.model, self.data)             # 1. physics step
            t = self.data.time
            self.clock_pub.publish(Clock(clock=stamp(t)))     # 2. simulation time
            if t >= self.next_state:                          # 3. joint states + tip pose
                self.publish_joints(t); self.publish_tip_pose(t); self.next_state += self.state_period
            if t >= self.next_camera:                         # 4. camera image
                self.publish_camera(t); self.next_camera += self.camera_period
            rclpy.spin_once(self, timeout_sec=0)              # 5. /cmd callbacks run here, between two steps
            if self.viewer is not None:
                self.viewer.sync()
            lag = wall0 + t - time.monotonic()                # 6. keep pace with the wall clock
            if lag > 0:
                time.sleep(lag)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--viewer", action="store_true", help="open the MuJoCo viewer window")
    ap.add_argument("--state-hz", type=float, default=50.0)
    ap.add_argument("--camera-hz", type=float, default=5.0)
    args = ap.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)   # Ctrl+C -> KeyboardInterrupt, not a mid-loop shutdown
    node = UrdfBridge(args.viewer, args.state_hz, args.camera_hz)
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
