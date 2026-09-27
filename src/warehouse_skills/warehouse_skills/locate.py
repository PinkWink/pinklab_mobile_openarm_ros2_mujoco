"""Where is the object relative to the robot? Truth (simulator) now, camera-based later.

Both locators return base_footprint-relative (dx, dy, dz) so that the skill server does
not care where the estimate came from. The lecture replaces TruthLocator with a vision
locator built from the in-process camera handler (Detection3DArray).
"""

import math

import numpy as np
from rclpy.callback_groups import ReentrantCallbackGroup
from geometry_msgs.msg import PoseArray, PoseStamped
from mobile_openarm_mujoco.model import load_world, yaw_from_quat
from warehouse_interfaces.msg import Detection3DArray

from .moveit_client import SkillError


def _yaw(pose):
    return yaw_from_quat([pose.orientation.w, pose.orientation.x, pose.orientation.y, pose.orientation.z])


class RobotPose:
    """Base pose in the world/map frame from simulator ground truth."""

    def __init__(self, node):
        self.pose = None
        node.create_subscription(PoseStamped, "/ground_truth", lambda m: setattr(self, "pose", m.pose), 10,
                                 callback_group=ReentrantCallbackGroup())

    def xyyaw(self):
        if self.pose is None:
            raise SkillError("no /ground_truth yet")
        return self.pose.position.x, self.pose.position.y, _yaw(self.pose)

    def relative(self, wx, wy, wz=0.0):
        """World point -> base_footprint (dx, dy, dz)."""
        x, y, yaw = self.xyyaw()
        c, s = math.cos(yaw), math.sin(yaw)
        ex, ey = wx - x, wy - y
        return c * ex + s * ey, -s * ex + c * ey, wz


class TruthLocator:
    def __init__(self, node, robot_pose):
        self.robot = robot_pose
        self.names = [o["name"] for o in load_world()["objects"]]
        self.poses = None
        node.create_subscription(PoseArray, "/warehouse/object_poses", lambda m: setattr(self, "poses", m.poses), 10,
                                 callback_group=ReentrantCallbackGroup())

    def world(self, name):
        if self.poses is None:
            raise SkillError("no /warehouse/object_poses yet")
        p = self.poses[self.names.index(name)]
        return np.array([p.position.x, p.position.y, p.position.z]), _yaw(p)

    def relative(self, name):
        (wx, wy, wz), _ = self.world(name)
        return self.robot.relative(wx, wy, wz)


class VisionLocator:
    """Latest Detection3D of a label from the in-process camera handler.

    Detections carry map coordinates produced through the AMCL TF chain, so they are
    converted back to base_footprint with the *same* TF (at the detection's stamp) rather
    than with ground truth: the localisation error then cancels out and what remains is
    the camera error (a few cm), which is what a real robot would see.
    """

    def __init__(self, node, robot_pose, topic="/vision/detections"):
        from tf2_ros import Buffer, TransformListener
        import tf2_geometry_msgs  # noqa: F401 - registers PointStamped transforms

        self.node = node
        self.robot = robot_pose
        self.latest = None
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, node, spin_thread=False)
        node.create_subscription(Detection3DArray, topic, lambda m: setattr(self, "latest", m), 10,
                                 callback_group=ReentrantCallbackGroup())

    def relative(self, label):
        import rclpy.duration
        from tf2_ros import TransformException

        if self.latest is None:
            raise SkillError("no /vision/detections yet")
        hits = [d for d in self.latest.detections if d.label == label and d.has_position]
        if not hits:
            raise SkillError(f"{label} not visible")
        best = max(hits, key=lambda d: d.score)
        frame = best.position.header.frame_id
        try:
            out = self.buffer.transform(best.position, "base_footprint", timeout=rclpy.duration.Duration(seconds=0.5))
        except TransformException as error:
            if frame == "map":  # fall back to the simulator pose if TF is not available
                p = best.position.point
                return self.robot.relative(p.x, p.y, p.z)
            raise SkillError(f"TF {frame} -> base_footprint failed: {error}")
        return float(out.point.x), float(out.point.y), float(out.point.z)
