"""Pixel <-> 3D helpers and TF lookups for in-process camera handlers.

Two routes from a pixel to the world exist and the lecture uses both on purpose:
  * ``frame.T_world_optical`` gives the MuJoCo world pose directly (simulation truth).
  * ROS TF (``<camera>_optical_frame`` -> ``map``) is what a real robot would use and
    includes AMCL localisation error. Detections published for navigation use TF.
"""

import numpy as np
import rclpy.time
from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer, TransformListener, TransformException
import tf2_geometry_msgs  # noqa: F401 - registers PointStamped transforms


def pixel_to_optical(frame, u, v, depth_m=None):
    """Back-project pixel (u, v) using the frame's intrinsics; depth defaults to the depth map."""
    z = frame.depth_m[int(v), int(u)] if depth_m is None else depth_m
    if not np.isfinite(z) or z <= 0:
        return None
    return z * (np.linalg.inv(frame.K) @ np.array([u, v, 1.0]))


def median_depth(frame, box, shrink=0.3):
    """Robust depth inside a bbox (x1, y1, x2, y2): median of the central region."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    cx1, cx2 = int(x1 + w * shrink), int(np.ceil(x2 - w * shrink))
    cy1, cy2 = int(y1 + h * shrink), int(np.ceil(y2 - h * shrink))
    patch = frame.depth_m[cy1 : max(cy2, cy1 + 1), cx1 : max(cx2, cx1 + 1)]
    valid = patch[np.isfinite(patch)]
    return float(np.median(valid)) if valid.size else None


def optical_to_world(frame, point):
    return (frame.T_world_optical @ np.r_[point, 1.0])[:3]


class MapTransformer:
    """TF listener on the bridge node; converts optical-frame points to map at a stamp."""

    def __init__(self, node, target="map"):
        self.node = node
        self.target = target
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, node, spin_thread=False)

    def to_map(self, frame, point_optical, stamp=None, timeout_s=0.0):
        msg = PointStamped()
        msg.header.frame_id = frame.optical_frame
        msg.header.stamp = stamp if stamp is not None else self.node.sim_stamp()
        msg.point.x, msg.point.y, msg.point.z = map(float, point_optical)
        try:
            out = self.buffer.transform(
                msg, self.target, timeout=rclpy.duration.Duration(seconds=timeout_s)
            )
        except TransformException as error:
            self.node.get_logger().warning(
                f"TF {frame.optical_frame} -> {self.target} failed: {error}",
                throttle_duration_sec=2.0,
            )
            return None
        return np.array([out.point.x, out.point.y, out.point.z])
