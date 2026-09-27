"""Single-threaded MuJoCo stepping with ROS 2 navigation, arm actions, actors, and cameras."""

import argparse
from contextlib import nullcontext
import math
import os
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from builtin_interfaces.msg import Time
from geometry_msgs.msg import (
    Twist,
    TwistStamped,
    TransformStamped,
    PoseStamped,
    PoseArray,
    Pose,
)
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, LaserScan
from rosgraph_msgs.msg import Clock
from tf2_ros import TransformBroadcaster
from warehouse_interfaces.msg import ActorState, ActorStateArray, KeyValue
from warehouse_interfaces.srv import SetActor
from .model import build_model, Physics, load_world, camera_settings
from .actions import Controllers
from .actors import load_actors, ActorAnimator
from .handler import HandlerContext, load_handler


def stamp(seconds):
    ns = round(seconds * 1e9)
    return Time(sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000)


def planar(pose, xyz):
    pose.position.x = float(xyz[0])
    pose.position.y = float(xyz[1])
    pose.orientation.z = math.sin(xyz[2] / 2)
    pose.orientation.w = math.cos(xyz[2] / 2)


class Bridge(Node):
    def __init__(self, physics, world_file=None, actors=None):
        super().__init__("mobile_openarm_mujoco")
        self.physics = physics
        self.command = (0.0, 0.0)
        self.command_time = -math.inf
        self.tick = 0
        self.objects = [o["name"] for o in load_world(world_file)["objects"]]
        self.actors = actors
        self.create_subscription(Twist, "/cmd_vel", self.receive_command, 10)
        self.create_subscription(
            TwistStamped,
            "/cmd_vel_stamped",
            lambda msg: self.receive_command(msg.twist),
            10,
        )
        self.clock_pub = self.create_publisher(Clock, "/clock", 10)
        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.truth_pub = self.create_publisher(PoseStamped, "/ground_truth", 10)
        self.objects_pub = self.create_publisher(
            PoseArray, "/warehouse/object_poses", 10
        )
        self.actors_pub = self.create_publisher(
            ActorStateArray, "/warehouse/actor_states", 10
        )
        self.scan_pub = self.create_publisher(
            LaserScan, "/scan", qos_profile_sensor_data
        )
        self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
        self.tf = TransformBroadcaster(self)
        self.controllers = Controllers(self)
        if self.actors is not None:
            self.create_service(SetActor, "/warehouse/set_actor", self.set_actor)
        self.get_logger().info(
            f"Vic Pinky + OpenArm ready: radius={physics.radius:.4f}, track={physics.track:.4f}; "
            f"4 action servers; actors={len(self.actors.actors) if self.actors else 0}"
        )

    def sim_stamp(self):
        return stamp(self.physics.data.time)

    def receive_command(self, msg):
        if not all(math.isfinite(v) for v in [msg.linear.x, msg.angular.z]):
            return
        if self.controllers.reserved or not self.physics.transport_ready():
            self.command = (0.0, 0.0)
            return
        cfg = self.physics.settings["control"]
        self.command = (
            max(-cfg["max_linear"], min(cfg["max_linear"], msg.linear.x)),
            max(-cfg["max_angular"], min(cfg["max_angular"], msg.angular.z)),
        )
        self.command_time = time.monotonic()

    def set_actor(self, request, response):
        try:
            a = self.actors
            if request.name not in a.actors:
                raise ValueError(f"Unknown actor {request.name!r}")
            op = request.operation
            if op == "teleport":
                p = request.pose
                q = [p.orientation.w, p.orientation.x, p.orientation.y, p.orientation.z]
                yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] ** 2 + q[3] ** 2))
                a.teleport(request.name, p.position.x, p.position.y, yaw)
            elif op == "set_path":
                a.set_path(
                    request.name,
                    [(w.x, w.y) for w in request.waypoints],
                    request.speed or 0.5,
                    0.0,
                    True,
                )
            elif op == "set_attributes":
                a.set_attributes(request.name, {kv.key: kv.value for kv in request.attributes})
            elif op in ("pause", "resume"):
                a.pause(request.name, op == "pause")
            else:
                raise ValueError(f"Unknown operation {op!r}")
            response.success = True
            response.message = f"{op} applied to {request.name}"
        except (ValueError, KeyError) as error:
            response.success = False
            response.message = str(error)
        return response

    def advance(self):
        p = self.physics
        self.controllers.update()
        allowed = (
            not self.controllers.reserved
            and p.transport_ready()
            and time.monotonic() - self.command_time
            < p.settings["control"]["command_timeout"]
        )
        if self.actors is not None:
            self.actors.update(p.bridge_period)
        p.step(*(self.command if allowed else (0.0, 0.0)))
        now = self.sim_stamp()
        self.clock_pub.publish(Clock(clock=now))
        self.tick += 1
        rates = p.settings["rates"]
        if self.tick % round(rates["bridge_hz"] / rates["state_hz"]) == 0:
            self.publish_state(now)
        if self.tick % round(rates["bridge_hz"] / rates["scan_hz"]) == 0:
            scan = LaserScan()
            scan.header.stamp = now
            scan.header.frame_id = "laser_link"
            scan.angle_min = float(p.angles[0])
            scan.angle_max = float(p.angles[-1])
            scan.angle_increment = float(p.angles[1] - p.angles[0])
            scan.time_increment = 0.0
            scan.scan_time = 1 / rates["scan_hz"]
            scan.range_min = p.settings["lidar"]["range_min"]
            scan.range_max = p.settings["lidar"]["range_max"]
            scan.ranges = p.scan().astype("float32").tolist()
            self.scan_pub.publish(scan)

    def publish_state(self, now):
        p = self.physics
        odom = Odometry()
        odom.header.stamp = now
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_footprint"
        planar(odom.pose.pose, p.odom)
        odom.twist.twist.linear.x = float(p.twist[0])
        odom.twist.twist.angular.z = float(p.twist[1])
        for i, v in enumerate([0.0025, 0.0025, 1e6, 1e6, 1e6, 0.01]):
            odom.pose.covariance[7 * i] = v
            odom.twist.covariance[7 * i] = v
        self.odom_pub.publish(odom)
        tf = TransformStamped()
        tf.header = odom.header
        tf.child_frame_id = odom.child_frame_id
        tf.transform.translation.x = odom.pose.pose.position.x
        tf.transform.translation.y = odom.pose.pose.position.y
        tf.transform.rotation = odom.pose.pose.orientation
        self.tf.sendTransform(tf)
        joints = JointState()
        joints.header.stamp = now
        joints.name = p.joint_names
        joints.position = p.data.qpos[p.q_indices].tolist()
        joints.velocity = p.data.qvel[p.v_indices].tolist()
        self.joint_pub.publish(joints)
        truth = PoseStamped()
        truth.header.stamp = now
        truth.header.frame_id = "world"
        planar(truth.pose, p.pose())
        self.truth_pub.publish(truth)
        if self.tick % 10 == 0:
            poses = PoseArray()
            poses.header = truth.header
            for name in self.objects:
                b = p.data.body(name)
                pose = Pose()
                pose.position.x, pose.position.y, pose.position.z = map(float, b.xpos)
                (
                    pose.orientation.w,
                    pose.orientation.x,
                    pose.orientation.y,
                    pose.orientation.z,
                ) = map(float, b.xquat)
                poses.poses.append(pose)
            self.objects_pub.publish(poses)
            if self.actors is not None:
                self.publish_actors(truth.header)

    def publish_actors(self, header):
        msg = ActorStateArray()
        msg.header = header
        for name, s in self.actors.states().items():
            a = ActorState()
            a.name, a.kind = name, s["kind"]
            a.pose.position.x, a.pose.position.y, a.pose.position.z = map(float, s["position"])
            (
                a.pose.orientation.w,
                a.pose.orientation.x,
                a.pose.orientation.y,
                a.pose.orientation.z,
            ) = map(float, s["quat"])
            a.velocity.x, a.velocity.y, a.velocity.z = map(float, s["velocity"])
            a.moving = s["moving"]
            a.attributes = [KeyValue(key=k, value=v) for k, v in s["attributes"].items()]
            msg.actors.append(a)
        self.actors_pub.publish(msg)


def parse_size(text):
    try:
        width, height = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("--camera-size must look like 320x240")
    return width, height


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewer", action="store_true")
    parser.add_argument("--urdf-file")
    parser.add_argument("--physics-config")
    parser.add_argument("--world-file")
    parser.add_argument(
        "--actors-file",
        help="actors.yaml path; 'none' disables people and props (default: package actors.yaml)",
    )
    parser.add_argument(
        "--camera-handler",
        help="Python module:attribute (function, callable, or class) run in this process",
    )
    parser.add_argument("--camera-fps", type=float)
    parser.add_argument("--camera-depth", action="store_true")
    parser.add_argument(
        "--camera-segmentation",
        action="store_true",
        help="Also render per-pixel body ids (dataset labelling)",
    )
    parser.add_argument(
        "--camera-names",
        help="Comma-separated subset of cameras to render (default: all four)",
    )
    parser.add_argument(
        "--camera-size", type=parse_size, help="Render size WxH (default cameras.yaml)"
    )
    parser.add_argument(
        "--spawn",
        help="Initial base pose in the world/map frame as X,Y,YAW (m, m, rad); default = mujoco.yaml spawn",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get(
            "MOBILE_OPENARM_MODEL_DIR", str(Path.home() / ".cache/mobile_openarm")
        ),
    )
    options, ros_args = parser.parse_known_args(args)
    handler = None
    if options.camera_handler:
        try:
            handler = load_handler(options.camera_handler)
        except (ValueError, TypeError) as error:
            parser.error(str(error))
    urdf = Path(options.urdf_file).read_text() if options.urdf_file else None
    p = Physics(
        build_model(
            options.output_dir,
            urdf,
            options.physics_config,
            options.world_file,
            options.actors_file,
        ),
        options.physics_config,
    )
    if options.spawn:
        try:
            x, y, yaw = (float(v) for v in options.spawn.split(","))
        except ValueError:
            parser.error("--spawn must look like X,Y,YAW")
        p.set_base_pose(x, y, yaw)
    actors_spec = load_actors(options.actors_file)
    animator = ActorAnimator(p.model, p.data, actors_spec) if actors_spec["actors"] else None
    rclpy.init(args=ros_args)
    node = Bridge(p, options.world_file, animator)
    viewer = None
    cameras = None
    try:
        pump = None
        if handler is not None:
            from .cameras import CameraRig, CameraPump

            cfg = camera_settings()["render"]
            width, height = options.camera_size or (cfg["width"], cfg["height"])
            cameras = CameraRig(p.model, p.data, width=width, height=height)
            names = (
                tuple(n.strip() for n in options.camera_names.split(",") if n.strip())
                if options.camera_names
                else cameras.names
            )
            for name in names:
                if name not in cameras.names:
                    parser.error(f"Unknown camera {name!r}; available: {cameras.names}")
            pump = CameraPump(
                cameras,
                handler,
                fps=options.camera_fps
                if options.camera_fps is not None
                else cfg["fps"],
                depth=options.camera_depth,
                names=names,
                segmentation=options.camera_segmentation,
            )
            if hasattr(handler, "setup"):
                handler.setup(
                    HandlerContext(
                        node=node,
                        physics=p,
                        rig=cameras,
                        pump=pump,
                        settings=p.settings,
                        world=load_world(options.world_file),
                        actors=animator,
                        camera_names=names,
                        output_dir=options.output_dir,
                    )
                )
            node.get_logger().info(
                f"Direct Python cameras enabled: {names} at {width}x{height}, {pump.fps:g} FPS; no image topics"
            )
        if options.viewer:
            import mujoco.viewer

            viewer = mujoco.viewer.launch_passive(p.model, p.data)
            viewer.cam.lookat[:] = [0, 0, 0.5]
            viewer.cam.distance = 14
            viewer.cam.azimuth = 130
            viewer.cam.elevation = -50
            viewer.opt.geomgroup[1] = 0
        deadline = time.monotonic()
        # One callback per tick cannot keep up with /tf, /tf_static and joint state
        # traffic once handlers subscribe inside this process; drain a small batch.
        callbacks_per_tick = int(p.settings["rates"].get("ros_callbacks_per_tick", 8))
        while rclpy.ok() and (viewer is None or viewer.is_running()):
            for _ in range(callbacks_per_tick):
                rclpy.spin_once(node, timeout_sec=0.0)
            with viewer.lock() if viewer else nullcontext():
                node.advance()
                if pump is not None:
                    pump.update()
            if viewer and node.tick % 3 == 0:
                viewer.sync()
            deadline += p.bridge_period
            delay = deadline - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            elif delay < -0.25:
                deadline = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        if handler is not None and hasattr(handler, "close"):
            try:
                handler.close()
            except Exception as error:  # noqa: BLE001 - shutdown must continue
                node.get_logger().warning(f"Camera handler close failed: {error}")
        if cameras:
            cameras.close()
        if viewer:
            viewer.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
