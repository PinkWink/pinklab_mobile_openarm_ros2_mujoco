"""Ground-truth detector: segmentation render -> Detection3DArray in the map frame.

This is the "perfect YOLO" used before students train their own model (M1, M3
comparisons) and as the reference in evaluations. It exercises the whole in-process
pipeline: camera frames -> labels -> depth back-projection -> TF -> ROS messages.

Run inside the simulator:
    camera_handler:=warehouse_lecture.vision.truth_detector:TruthDetector camera_depth:=true camera_segmentation:=true
"""

import numpy as np
from geometry_msgs.msg import PointStamped
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from warehouse_interfaces.msg import Detection3D, Detection3DArray, KeyValue

from mobile_openarm_mujoco.bridge import stamp as sim_stamp

from ..ros.geometry import MapTransformer, median_depth, pixel_to_optical
from ..ros.handler_base import WorkerHandler
from .labels import CLASSES, label_frame


class TruthDetector(WorkerHandler):
    def __init__(self, topic="/vision/detections", topic_2d="/vision/detections_2d", min_pixels=24):
        super().__init__(adaptive=True)
        self.topic, self.topic_2d, self.min_pixels = topic, topic_2d, min_pixels

    def on_setup(self, context):
        node = context.node
        self.pub = node.create_publisher(Detection3DArray, self.topic, 10)
        self.pub_2d = node.create_publisher(Detection2DArray, self.topic_2d, 10)
        self.tf = MapTransformer(node)
        self.labels_by_body = context.body_labels()

    def prepare(self, frames):
        """Physics thread: label from segmentation (cheap NumPy), keep depth for the worker."""
        ctx = self.context
        items = []
        for name, frame in frames.items():
            if frame.segmentation is None:
                if not getattr(self, "_warned", False):
                    ctx.node.get_logger().warning("TruthDetector: camera_segmentation:=true is required; skipping")
                    self._warned = True
                return None
            labels = label_frame(frame, ctx.physics, self.labels_by_body, actors=ctx.actors, min_pixels=self.min_pixels)
            items.append((name, frame, labels))
        return items

    def process(self, items):
        """Worker thread: depth statistics per box (no ROS, no MuJoCo)."""
        out = []
        for name, frame, labels in items:
            for cls, box in labels:
                depth = median_depth(frame, box) if frame.depth_m is not None else None
                point = None
                if depth is not None:
                    u, v = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                    point = pixel_to_optical(frame, u, v, depth)
                out.append((name, frame, CLASSES[cls], box, point))
        return out

    def publish(self, results):
        """Physics thread: TF to map and publish."""
        # Positions are transformed at the frame's own simulation time: that TF has
        # arrived by now, whereas "now" would be a future time the buffer cannot serve.
        stamp = sim_stamp(results[0][1].sim_time) if results else self.context.stamp()
        msg = Detection3DArray()
        msg.header.stamp = stamp
        msg.header.frame_id = "map"
        msg_2d = Detection2DArray()
        msg_2d.header = msg.header
        people = {}
        for name, frame, label, box, point in results:
            d = Detection3D()
            d.label, d.score, d.track_id, d.camera = label, 1.0, -1, name
            d.bbox_xyxy = [float(v) for v in box]
            if point is not None:
                p = self.tf.to_map(frame, point, stamp)
                if p is not None:
                    d.has_position = True
                    d.position = PointStamped()
                    d.position.header.stamp = stamp
                    d.position.header.frame_id = "map"
                    d.position.point.x, d.position.point.y, d.position.point.z = map(float, p)
            msg.detections.append(d)
            if label == "person":
                people[(name, box)] = d
            det = Detection2D()
            det.header = msg.header
            det.bbox.center.position.x = (box[0] + box[2]) / 2
            det.bbox.center.position.y = (box[1] + box[3]) / 2
            det.bbox.size_x, det.bbox.size_y = float(box[2] - box[0]), float(box[3] - box[1])
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id, hyp.hypothesis.score = label, 1.0
            det.results.append(hyp)
            msg_2d.detections.append(det)
        # Attribute association: a helmet/vest box inside a person box tags that person.
        for name, frame, label, box, _ in results:
            if label not in ("helmet", "safety_vest"):
                continue
            cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
            for (cam, pbox), d in people.items():
                if cam == name and pbox[0] <= cx <= pbox[2] and pbox[1] <= cy <= pbox[3]:
                    key = "helmet" if label == "helmet" else "vest"
                    d.attributes.append(KeyValue(key=key, value="true"))
        for d in people.values():
            keys = {kv.key for kv in d.attributes}
            for key in ("helmet", "vest"):
                if key not in keys:
                    d.attributes.append(KeyValue(key=key, value="false"))
        self.pub.publish(msg)
        self.pub_2d.publish(msg_2d)
