"""ArUco marker detection inside the simulator process -> /vision/markers (base_footprint).

The marker pose comes purely from the camera image, intrinsics and the camera's fixed
mounting on the robot. No simulator truth is used, so the same code works on a real robot.
"""

import math

import cv2
import numpy as np
from mobile_openarm_mujoco.bridge import stamp as sim_stamp
from mobile_openarm_mujoco.markers import DICTIONARY
from warehouse_interfaces.msg import ArucoMarker, ArucoMarkerArray

from ..ros.handler_base import WorkerHandler

OPTICAL_FROM_CAMERA = np.diag([1.0, -1.0, -1.0])  # MuJoCo camera (y up, -z fwd) -> optical (y down, z fwd)


def detect(rgb, K, sizes, dictionary=DICTIONARY, detector=None):
    """Return [(id, tvec_optical, R_optical, corners)] for markers whose id is in sizes."""
    if detector is None:
        detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary)), cv2.aruco.DetectorParameters()
        )
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    found = []
    if ids is None:
        return found
    for quad, marker_id in zip(corners, ids.ravel()):
        size = sizes.get(int(marker_id))
        if size is None:
            continue
        s = size / 2
        obj = np.array([[-s, s, 0], [s, s, 0], [s, -s, 0], [-s, -s, 0]], np.float32)
        ok, rvec, tvec = cv2.solvePnP(obj, quad[0], K.astype(np.float64), None, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if not ok:
            continue
        R, _ = cv2.Rodrigues(rvec)
        found.append((int(marker_id), tvec.ravel(), R, quad[0]))
    return found


def base_from_optical(physics, camera_name):
    """4x4 transform optical frame -> base_footprint from the robot's own kinematics."""
    model, data = physics.model, physics.data
    cam = model.camera(camera_name).id
    T_wo = np.eye(4)
    T_wo[:3, :3] = data.cam_xmat[cam].reshape(3, 3) @ OPTICAL_FROM_CAMERA
    T_wo[:3, 3] = data.cam_xpos[cam]
    base = model.body("base_footprint").id
    T_wb = np.eye(4)
    T_wb[:3, :3] = data.xmat[base].reshape(3, 3)
    T_wb[:3, 3] = data.xpos[base]
    return np.linalg.inv(T_wb) @ T_wo


class ArucoDetector(WorkerHandler):
    def __init__(self, camera="base_camera", topic="/vision/markers", adaptive=False, stats_topic="/vision/stats/aruco"):
        super().__init__(adaptive=adaptive, stats_topic=stats_topic)
        self.camera, self.topic = camera, topic
        self.detector = None
        self.sizes = {}

    def on_setup(self, context):
        self.pub = context.node.create_publisher(ArucoMarkerArray, self.topic, 10)
        self.sizes = {int(m["id"]): float(m["size"]) for m in context.world.get("markers", [])}
        self.detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICTIONARY)), cv2.aruco.DetectorParameters()
        )
        if self.camera not in context.camera_names:
            context.node.get_logger().warning(f"ArucoDetector: camera {self.camera} is not rendered; add it to camera_names")

    def prepare(self, frames):
        frame = frames.get(self.camera)
        if frame is None:
            return None
        return frame.rgb, frame.K, base_from_optical(self.context.physics, self.camera), frame.sim_time

    def process(self, item):
        rgb, K, T_bo, sim_time = item
        markers = []
        for marker_id, t, R, quad in detect(rgb, K, self.sizes, detector=self.detector):
            p = (T_bo @ np.r_[t, 1.0])[:3]
            Rb = T_bo[:3, :3] @ R
            normal = Rb[:, 2]
            markers.append((marker_id, p, Rb, math.atan2(normal[1], normal[0]), float(np.linalg.norm(t)), quad))
        return sim_time, markers

    def publish(self, result):
        sim_time, markers = result
        msg = ArucoMarkerArray()
        msg.header.stamp = sim_stamp(sim_time)
        msg.header.frame_id = "base_footprint"
        msg.camera = self.camera
        for marker_id, p, Rb, yaw, distance, quad in markers:
            m = ArucoMarker()
            m.id, m.size = marker_id, float(self.sizes[marker_id])
            m.pose.position.x, m.pose.position.y, m.pose.position.z = map(float, p)
            m.pose.orientation.x, m.pose.orientation.y, m.pose.orientation.z, m.pose.orientation.w = _quat(Rb)
            m.normal_yaw, m.distance = float(yaw), distance
            m.corners = [float(v) for v in quad.reshape(-1)]
            msg.markers.append(m)
        self.pub.publish(msg)


def _quat(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(R[i, i] - R[j, j] - R[k, k] + 1.0) * 2
    q = [0.0, 0.0, 0.0]
    q[i], q[j], q[k] = 0.25 * s, (R[j, i] + R[i, j]) / s, (R[k, i] + R[i, k]) / s
    return q[0], q[1], q[2], (R[k, j] - R[j, k]) / s
