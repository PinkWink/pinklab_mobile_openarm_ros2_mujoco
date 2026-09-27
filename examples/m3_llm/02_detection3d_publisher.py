#!/usr/bin/env python3
"""M3 예제 2: 추적 결과(01번)에 깊이·TF 를 더해 map 좌표의 Detection3DArray(/vision/detections)를 발행한다.

실행 (깊이 필요. 세그멘테이션을 켜면 정답 위치와 비교):
    taskset -c 0-3 ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m3_llm/02_detection3d_publisher.py:Detection3DHandler camera_depth:=true camera_segmentation:=true
    ./scripts/mobile_openarm exec ros2 topic echo /vision/detections
  운반 스킬이 이 검출로 상자를 찾게 하려면 (정답 대신 카메라):
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,examples/m3_llm/02_detection3d_publisher.py:Detection3DHandler" \\
      ./scripts/mobile_openarm start viewer:=false camera_depth:=true locate:=vision
    ./scripts/mobile_openarm pick red

배우는 점:
- M1-05 와 같은 길: 박스 중앙 깊이 중앙값 → K⁻¹ 역투영 → (두께 보정) → tf2 로 map. 프레임 stamp 의 TF 는 다음 호출에 도착하므로
  한 호출 늦게 변환한다 (WorkerHandler 의 publish 가 이미 다음 캡처 시점이라 자연스럽게 맞는다).
- Detection3D 하나에 label, score, track_id, camera, bbox, map 위치, 속성(helmet/vest)을 모두 담는다. M5 조우 기억은 이 메시지만 본다.
- 사람 위치는 박스 중앙 깊이(몸통)라 발 위치보다 높다. z 는 바닥(0)으로 눌러 map 상 위치로 쓴다.
- 검증: 상자·사람 map 위치 오차(정답 대비)를 로그에 누적. 상자는 5 cm, 사람은 20 cm 안이면 충분하다.
"""

import importlib.util
import os
from pathlib import Path

import numpy as np
from geometry_msgs.msg import Point, PointStamped
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray
from warehouse_interfaces.msg import Detection3D, Detection3DArray, KeyValue
from mobile_openarm_mujoco.bridge import stamp as sim_stamp
from warehouse_lecture.ros.geometry import MapTransformer, median_depth, pixel_to_optical
from warehouse_lecture.vision.labels import PARCEL_COLORS


def load_sibling(stem):
    path = Path(__file__).with_name(stem + ".py")
    spec = importlib.util.spec_from_file_location(stem, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


TrackingHandler = load_sibling("01_tracking_attributes").TrackingHandler
HALF_DEPTH = {"parcel_red": 0.0225, "parcel_blue": 0.0225, "parcel_yellow": 0.0225, "person": 0.12, "forklift": 0.5, "pallet": 0.3,
              "cone": 0.12, "extinguisher": 0.06, "helmet": 0.1, "safety_vest": 0.1}
FLOOR_CLASSES = ("person", "forklift", "pallet", "cone", "extinguisher")


class Detection3DHandler(TrackingHandler):
    def __init__(self):
        super().__init__()
        self.pos_err = {"parcel": [], "person": []}

    def on_setup(self, context):
        super().on_setup(context)
        if not context.pump.depth:
            raise ValueError("camera_depth:=true 가 필요하다")
        self.tf = MapTransformer(context.node, target="map")
        self.pub3d = context.node.create_publisher(Detection3DArray, "/vision/detections", 10)
        self.pub_markers = context.node.create_publisher(MarkerArray, "/vision/markers3d", 10)
        context.node.get_logger().info("[m3-02] /vision/detections (map) + /vision/markers3d")

    def prepare(self, frames):
        items = super().prepare(frames)
        # 깊이 맵과 K, optical frame 도 워커/발행에 넘긴다 (frame 객체는 복사하지 않고 필요한 배열만)
        return [(it, frames[it[0]]) for it in items]

    def process(self, items):
        return [((it, frame), *self.trackers[it[0]].track(it[1])) for it, frame in items]

    def publish(self, results):
        super().publish([(it, dets, people) for (it, frame), dets, people in results])
        msg = Detection3DArray()
        markers = MarkerArray()
        truth = self.truth_positions() if self.body_labels is not None else {}
        for (it, frame), dets, people in results:
            name, rgb, sim_time, frame_id, _ = it
            stamp = sim_stamp(sim_time)          # 프레임의 시각. 지금은 다음 캡처 시점이라 이 TF 가 도착해 있다
            if not msg.header.stamp.sec and not msg.header.stamp.nanosec:
                msg.header.stamp, msg.header.frame_id = stamp, "map"
            for label, box, score, tid in dets:
                d = Detection3D()
                d.label, d.score, d.track_id, d.camera = label, float(score), int(tid), name
                d.bbox_xyxy = [float(v) for v in box]
                if label == "person" and tid in people:
                    p = people[tid]
                    d.attributes = [KeyValue(key="helmet", value="true" if p["helmet"] else "false"), KeyValue(key="vest", value=p["vest"])]
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
                        markers.markers.append(self.marker(len(markers.markers), label, p_map, stamp, tid))
                        self.compare(label, p_map, truth)
                msg.detections.append(d)
        self.pub3d.publish(msg)
        self.pub_markers.publish(markers)
        if self.frames % 8 == 0 and self.body_labels is not None:
            e = {k: (np.median(v) * 100 if v else float("nan")) for k, v in self.pos_err.items()}
            self.context.node.get_logger().info(f"[m3-02] map 위치 오차 중앙값: 상자 {e['parcel']:.1f} cm (n={len(self.pos_err['parcel'])}), 사람 {e['person']:.1f} cm (n={len(self.pos_err['person'])})")

    def truth_positions(self):
        d, ctx = self.context.physics.data, self.context
        out = {}
        for o in ctx.world["objects"]:
            if o["name"] in PARCEL_COLORS:
                out[PARCEL_COLORS[o["name"]]] = [np.array(d.body(o["name"]).xpos)]
        if ctx.actors is not None:
            for name, st in ctx.actors.states().items():
                out.setdefault(st["kind"], []).append(np.array(st["position"]))
        return out

    def compare(self, label, p_map, truth):
        key = "parcel" if label.startswith("parcel_") else "person" if label == "person" else None
        cands = truth.get(label, [])
        if key is None or not cands:
            return
        err = min(np.linalg.norm(p_map[:2] - c[:2]) for c in cands)
        if err < 1.0:                       # 다른 사람과 잘못 짝지은 경우는 제외
            self.pos_err[key].append(err)

    def marker(self, i, label, p, stamp, tid):
        m = Marker(); m.header.frame_id, m.header.stamp = "map", stamp
        m.ns, m.id, m.type, m.action = "detections", i, Marker.SPHERE if label.startswith("parcel_") else Marker.CYLINDER, Marker.ADD
        m.pose.position = Point(x=float(p[0]), y=float(p[1]), z=float(p[2]) + (0.9 if label == "person" else 0.0))
        m.pose.orientation.w = 1.0
        s = 0.06 if label.startswith("parcel_") else 0.4
        m.scale.x = m.scale.y = s; m.scale.z = 1.8 if label == "person" else s
        r, g, b = {"parcel_red": (1.0, 0.2, 0.2), "parcel_blue": (0.2, 0.5, 1.0), "parcel_yellow": (1.0, 0.9, 0.1), "person": (0.2, 1.0, 0.2)}.get(label, (0.7, 0.7, 0.7))
        m.color = ColorRGBA(r=float(r), g=float(g), b=float(b), a=0.6)   # rclpy 는 int 를 float 필드에 넣으면 단언으로 죽는다
        m.lifetime.sec = 1; m.text = f"{label}#{tid}"
        return m
