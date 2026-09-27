#!/usr/bin/env python3
"""M2 예제 7: 핸들러 안에서 YOLO(CPU, OpenVINO/ONNX) 추론 -> Detection2DArray 발행. 정답과 비교하고 /vision/stats 를 본다.

실행 (세그멘테이션을 켜면 정답과 자동 비교한다. 수강생 PC 조건은 taskset 으로 흉내낸다):
    taskset -c 0-3 ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m2_yolo/07_yolo_handler.py:YoloHandler camera_segmentation:=true
    다른 터미널:
    ./scripts/mobile_openarm exec ros2 topic echo /vision/stats
    ./scripts/mobile_openarm exec ros2 topic echo /vision/yolo_2d
    ./scripts/mobile_openarm goal 1.2 -3.6 0       # 작업대 앞으로 가서 상자 검출 확인
  옵션: WAREHOUSE_YOLO=weights/warehouse_yolo11n_320_openvino_model  M2_IMGSZ=320  M2_CONF=0.4  M2_THREADS=2  M1_WINDOW=0
  미리보기: artifacts/m2/07_yolo.png

배우는 점:
- M1-06 의 WorkerHandler 그대로다. prepare 에서 프레임을 복사하고, process(워커)에서 YOLO 를 돌리고, publish 에서 메시지를 낸다.
- 래퍼는 warehouse_lecture.vision.yolo.YoloDetector 로 승격했다 (M3 부터 이것을 import 한다).
- 정답(세그멘테이션 라벨)과 IoU 0.5 매칭으로 정밀도·재현율을 누적한다. 시뮬레이터에서만 가능한 공짜 평가다.
- 목표: 4코어에서 2대 카메라 2 FPS 실시간 유지(realtime_ratio ≥ 0.9), 프레임당 ≤ 60 ms.
"""

import os
from collections import Counter
from pathlib import Path

import cv2
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from warehouse_lecture.ros.handler_base import WorkerHandler
from warehouse_lecture.vision.labels import CLASSES, label_frame
from warehouse_lecture.vision.yolo import YoloDetector

COL = {"person": (0, 255, 0), "helmet": (0, 255, 255), "safety_vest": (255, 128, 0), "parcel_red": (0, 0, 255), "parcel_blue": (255, 0, 0),
       "parcel_yellow": (0, 200, 255), "forklift": (255, 0, 255), "pallet": (120, 120, 255), "cone": (0, 140, 255), "extinguisher": (255, 255, 255)}


def iou(a, b):
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


class YoloHandler(WorkerHandler):
    def __init__(self):
        super().__init__(adaptive=True, min_fps=0.5)
        self.imgsz = int(os.environ.get("M2_IMGSZ", "320"))
        self.conf = float(os.environ.get("M2_CONF", "0.4"))
        self.threads = int(os.environ.get("M2_THREADS", "2"))
        self.window = os.environ.get("M1_WINDOW", "1") != "0" and bool(os.environ.get("DISPLAY"))
        self.out = Path("artifacts/m2"); self.out.mkdir(parents=True, exist_ok=True)
        self.tp = Counter(); self.fp = Counter(); self.fn = Counter()
        self.frames = 0
        self.last_report = None

    def on_setup(self, context):
        self.pub = context.node.create_publisher(Detection2DArray, "/vision/yolo_2d", 10)
        self.detector = YoloDetector(imgsz=self.imgsz, conf=self.conf, threads=self.threads)   # 워커에서만 쓴다
        self.body_labels = context.body_labels() if context.pump.segmentation else None
        context.node.get_logger().info(f"[m2-07] {self.detector.path} imgsz {self.imgsz} conf {self.conf} threads {self.threads}; 정답 비교 {'on' if self.body_labels else 'off'}")

    # 물리 스레드: 프레임 복사 + (세그멘테이션이 있으면) 정답 라벨. 둘 다 싸다.
    def prepare(self, frames):
        items = []
        for name, f in frames.items():
            truth = None
            if self.body_labels is not None:
                truth = [(CLASSES[c], box) for c, box in label_frame(f, self.context.physics, self.body_labels, actors=self.context.actors, min_pixels=24)]
            items.append((name, f.rgb.copy(), f.sim_time, f.optical_frame, truth))
        return items

    # 워커 스레드: YOLO
    def process(self, items):
        dets = self.detector.detect_batch([it[1] for it in items])
        return [(it, d) for it, d in zip(items, dets)]

    # 물리 스레드: 발행 + 평가 + 미리보기
    def publish(self, results):
        stamp = self.context.stamp()
        tiles = []
        for (name, rgb, sim_time, frame_id, truth), dets in results:
            msg = Detection2DArray()
            msg.header.stamp, msg.header.frame_id = stamp, frame_id
            for label, (x1, y1, x2, y2), score in dets:
                d = Detection2D(); d.header = msg.header; d.id = name
                d.bbox.center.position.x, d.bbox.center.position.y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                d.bbox.size_x, d.bbox.size_y = float(x2 - x1), float(y2 - y1)
                h = ObjectHypothesisWithPose(); h.hypothesis.class_id, h.hypothesis.score = label, score
                d.results.append(h); msg.detections.append(d)
            self.pub.publish(msg)
            if truth is not None:
                for label, box in truth:
                    if any(l == label and iou(b, box) >= 0.5 for l, b, _ in dets):
                        self.tp[label] += 1
                    else:
                        self.fn[label] += 1
                for l, b, _ in dets:
                    if not any(l == label and iou(b, box) >= 0.5 for label, box in truth):
                        self.fp[l] += 1
            if self.window or self.frames % 4 == 0:
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                for label, (x1, y1, x2, y2), score in dets:
                    cv2.rectangle(bgr, (x1, y1), (x2, y2), COL.get(label, (200, 200, 200)), 1)
                    cv2.putText(bgr, f"{label} {score:.2f}", (x1, max(10, y1 - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, COL.get(label, (200, 200, 200)), 1)
                cv2.putText(bgr, f"{name} {self.detector.last_ms:.0f} ms", (4, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                tiles.append(bgr)
        self.frames += 1
        if tiles:
            grid = cv2.hconcat(tiles)
            tmp = self.out / "07_yolo.tmp.png"; cv2.imwrite(str(tmp), grid); tmp.replace(self.out / "07_yolo.png")
            if self.window:
                try:
                    cv2.imshow("M2-07 YOLO", grid); cv2.waitKey(1)
                except cv2.error:
                    self.window = False
        now = self.context.sim_time()
        if self.last_report is None or now - self.last_report >= 2.0:
            self.last_report = now
            tp, fp, fn = sum(self.tp.values()), sum(self.fp.values()), sum(self.fn.values())
            prec, rec = tp / max(1, tp + fp), tp / max(1, tp + fn)
            self.context.node.get_logger().info(
                f"[m2-07] sim {now:6.1f}s 추론 {self._inference_ms:.0f} ms/배치({len(results)}장) 캡처 {self.context.pump.fps:.2f} FPS 실시간 {self._ratio:.2f} "
                f"버림 {self._dropped}" + (f" | 누적 정밀도 {prec:.2f} 재현율 {rec:.2f} (TP {tp} FP {fp} FN {fn})" if self.body_labels else ""))
