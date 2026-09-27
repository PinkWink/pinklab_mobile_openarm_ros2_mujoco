"""YOLO + ByteTrack + attributes + 3D positions -> /vision/detections (map frame).

Promoted from M3 examples 01/02. This is the camera-based replacement for
TruthDetector: same Detection3DArray contract, so the skill server (locate:=vision)
and the M5 encounter memory work unchanged.

    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \\
        ./scripts/mobile_openarm start camera_depth:=true locate:=vision
Env: WAREHOUSE_YOLO (weights), YOLO_IMGSZ=320, YOLO_CONF=0.4, YOLO_VOTES=5
"""

import os
from collections import Counter, defaultdict, deque

import cv2
import numpy as np
from geometry_msgs.msg import PointStamped
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from warehouse_interfaces.msg import Detection3D, Detection3DArray, KeyValue

from mobile_openarm_mujoco.bridge import stamp as sim_stamp

from ..ros.geometry import MapTransformer, median_depth, pixel_to_optical
from ..ros.handler_base import WorkerHandler
from .yolo import resolve_weights

# Half thickness along the viewing ray: depth hits the visible face, the centre is further.
HALF_DEPTH = {"parcel_red": 0.0225, "parcel_blue": 0.0225, "parcel_yellow": 0.0225, "person": 0.12, "forklift": 0.5,
              "pallet": 0.3, "cone": 0.12, "extinguisher": 0.06, "helmet": 0.1, "safety_vest": 0.1}
FLOOR_CLASSES = ("person", "forklift", "pallet", "cone", "extinguisher")


def vest_colour(rgb, box):
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    patch = rgb[y1 + h // 4: y2 - h // 4 or y2, x1 + w // 4: x2 - w // 4 or x2]
    if patch.size == 0:
        return "orange"
    hsv = cv2.cvtColor(patch.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    sat = hsv[:, 1] > 80
    hue = np.median(hsv[sat, 0]) if sat.any() else np.median(hsv[:, 0])
    return "orange" if hue < 28 else "green"


def associate(dets, rgb):
    """[(label, box, score, tid)] -> {tid: {"box", "score", "helmet": bool, "vest": str}} for persons."""
    people = {tid: {"box": box, "score": score, "helmet": False, "vest": "none"} for label, box, score, tid in dets if label == "person"}
    for label, box, score, tid in dets:
        if label not in ("helmet", "safety_vest"):
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        for p in people.values():
            x1, y1, x2, y2 = p["box"]
            if not (x1 - 4 <= cx <= x2 + 4):
                continue
            if label == "helmet" and y1 - 8 <= cy <= y1 + 0.4 * (y2 - y1):
                p["helmet"] = True
            elif label == "safety_vest" and y1 <= cy <= y2:
                p["vest"] = vest_colour(rgb, box)
    return people


class CameraTracker:
    """One camera: YOLO + ByteTrack + majority vote of person attributes per track."""

    def __init__(self, weights, imgsz, conf, votes):
        from ultralytics import YOLO

        self.model = YOLO(weights, task="detect")
        self.imgsz, self.conf = imgsz, conf
        self.history = defaultdict(lambda: deque(maxlen=votes))
        self.model.predict(np.zeros((imgsz, imgsz, 3), np.uint8), imgsz=imgsz, device="cpu", verbose=False)

    def track(self, rgb):
        r = self.model.track(np.ascontiguousarray(rgb[..., ::-1]), imgsz=self.imgsz, conf=self.conf, persist=True,
                             tracker="bytetrack.yaml", device="cpu", verbose=False)[0]
        dets = []
        if r.boxes is not None and len(r.boxes):
            ids = r.boxes.id.int().tolist() if r.boxes.id is not None else [-1] * len(r.boxes)
            for i, ((x1, y1, x2, y2), c, s, tid) in enumerate(zip(r.boxes.xyxy.numpy(), r.boxes.cls.int().tolist(), r.boxes.conf.tolist(), ids)):
                dets.append((self.model.names[c], (int(x1), int(y1), int(x2), int(y2)), float(s), int(tid) if tid >= 0 else -1 - i))
        people = associate(dets, rgb)
        for tid, p in people.items():
            if tid < 0:
                p["age"] = 0
                continue
            self.history[tid].append((p["helmet"], p["vest"]))
            votes = self.history[tid]
            p["helmet"] = sum(v[0] for v in votes) * 2 > len(votes)
            p["vest"] = Counter(v[1] for v in votes).most_common(1)[0][0]
            p["age"] = len(votes)
        return dets, people


class YoloDetector3D(WorkerHandler):
    def __init__(self, weights=None, imgsz=None, conf=None, votes=None, topic="/vision/detections", topic_2d="/vision/detections_2d"):
        super().__init__(adaptive=True)
        self.weights = resolve_weights(weights)
        self.imgsz = int(imgsz or os.environ.get("YOLO_IMGSZ", "320"))
        self.conf = float(conf or os.environ.get("YOLO_CONF", "0.4"))
        self.votes = int(votes or os.environ.get("YOLO_VOTES", "5"))
        self.topic, self.topic_2d = topic, topic_2d
        self.trackers = {}

    def on_setup(self, context):
        node = context.node
        self.pub = node.create_publisher(Detection3DArray, self.topic, 10)
        self.pub_2d = node.create_publisher(Detection2DArray, self.topic_2d, 10)
        self.tf = MapTransformer(node, target="map") if context.pump.depth else None
        self.trackers = {name: CameraTracker(self.weights, self.imgsz, self.conf, self.votes) for name in context.camera_names}
        node.get_logger().info(f"YoloDetector3D: {self.weights} imgsz {self.imgsz}, cameras {list(self.trackers)}, "
                               f"3D {'on' if self.tf else 'off (camera_depth:=true for positions)'}")

    def prepare(self, frames):
        return [(name, f.rgb.copy(), f.sim_time, f.optical_frame, f) for name, f in frames.items()]

    def process(self, items):
        return [(it, *self.trackers[it[0]].track(it[1])) for it in items]

    def publish(self, results):
        msg, msg_2d = Detection3DArray(), Detection2DArray()
        for (name, rgb, sim_time, frame_id, frame), dets, people in results:
            stamp = sim_stamp(sim_time)  # the frame's own time: that TF has arrived by now
            if not (msg.header.stamp.sec or msg.header.stamp.nanosec):
                msg.header.stamp, msg.header.frame_id = stamp, "map"
                msg_2d.header.stamp, msg_2d.header.frame_id = stamp, frame_id
            for label, box, score, tid in dets:
                d = Detection3D()
                d.label, d.score, d.track_id, d.camera = label, float(score), int(tid), name
                d.bbox_xyxy = [float(v) for v in box]
                if label == "person" and tid in people:
                    p = people[tid]
                    d.attributes = [KeyValue(key="helmet", value="true" if p["helmet"] else "false"), KeyValue(key="vest", value=p["vest"])]
                if self.tf is not None and frame.depth_m is not None:
                    z = median_depth(frame, box)
                    if z is not None:
                        u, v = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
                        p_opt = pixel_to_optical(frame, u, v, z)
                        p_opt = p_opt * (1.0 + HALF_DEPTH.get(label, 0.05) / np.linalg.norm(p_opt))
                        p_map = self.tf.to_map(frame, p_opt, stamp)
                        if p_map is not None:
                            if label in FLOOR_CLASSES:
                                p_map[2] = 0.0
                            d.has_position = True
                            d.position = PointStamped()
                            d.position.header.stamp, d.position.header.frame_id = stamp, "map"
                            d.position.point.x, d.position.point.y, d.position.point.z = map(float, p_map)
                msg.detections.append(d)
                det = Detection2D()
                det.header = msg_2d.header
                det.id = f"{name}:{tid}"
                det.bbox.center.position.x, det.bbox.center.position.y = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
                det.bbox.size_x, det.bbox.size_y = float(box[2] - box[0]), float(box[3] - box[1])
                hyp = ObjectHypothesisWithPose()
                hyp.hypothesis.class_id, hyp.hypothesis.score = label, float(score)
                det.results.append(hyp)
                msg_2d.detections.append(det)
        self.pub.publish(msg)
        self.pub_2d.publish(msg_2d)
