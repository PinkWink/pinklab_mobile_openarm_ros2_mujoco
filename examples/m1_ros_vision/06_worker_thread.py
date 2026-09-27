#!/usr/bin/env python3
"""M1 예제 6: 무거운 처리를 워커 스레드로 넘기는 패턴과 적응형 캡처율(FPS) 관찰.

두 핸들러를 번갈아 띄워 /vision/stats 를 비교한다 (M1_HEAVY_MS 로 "추론" 시간을 흉내낸다. 기본 300 ms):
  (A) 물리 스레드에서 그대로 처리 -> 시뮬레이션이 느려진다 (realtime_ratio < 1)
    M1_HEAVY_MS=300 ./scripts/mobile_openarm start viewer:=false \\
        camera_handler:=examples/m1_ros_vision/06_worker_thread.py:BlockingDetector
  (B) 워커 스레드 + 최신 프레임만 유지 + 적응형 FPS -> 시뮬레이션은 실시간, 검출이 늦거나 드물어진다
    M1_HEAVY_MS=300 ./scripts/mobile_openarm start viewer:=false \\
        camera_handler:=examples/m1_ros_vision/06_worker_thread.py:WorkerDetector
  다른 터미널:  ./scripts/mobile_openarm exec ros2 topic echo /vision/stats

배우는 점 (warehouse_lecture/ros/handler_base.py 의 WorkerHandler):
- prepare(frames)  물리 스레드. 가볍게. 워커에 넘길 것만 만든다 (numpy 배열 복사 정도).
- process(item)    워커 스레드. 무거운 계산. ROS 퍼블리셔·MuJoCo data 를 만지지 않는다.
- publish(result)  물리 스레드, 다음 캡처 때. 퍼블리셔는 여기서만 쓴다 (rclpy 퍼블리셔는 스레드 안전하지 않다).
- 큐 길이 1: 워커가 느리면 오래된 프레임을 버린다(dropped_frames). 지연을 쌓는 것보다 낫다.
- adaptive=True: realtime_ratio < 0.8 이면 pump.fps 를 25 % 낮추고, > 0.97 이면 다시 올린다.
- OpenCV/NumPy/ONNX 호출은 GIL 을 놓으므로 워커가 돌아도 물리 스레드가 진행한다. 순수 Python 루프는 그렇지 않다.
"""

import importlib.util
import os
import time
from pathlib import Path

import cv2
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from warehouse_lecture.ros.handler_base import WorkerHandler


def load_sibling(stem):
    path = Path(__file__).with_name(stem + ".py")
    spec = importlib.util.spec_from_file_location(stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect_parcels = load_sibling("04_color_detect_parcels").detect_parcels
HEAVY_MS = float(os.environ.get("M1_HEAVY_MS", "300"))
CAMERA = os.environ.get("M1_CAMERA", "head_camera")


def heavy_detect(rgb):
    """04번 검출 + 인위적인 부하. GIL 을 놓는 OpenCV 호출을 반복해 실제 추론(YOLO 등)처럼 CPU 를 쓴다."""
    end = time.perf_counter() + HEAVY_MS / 1000.0
    while time.perf_counter() < end:
        cv2.GaussianBlur(rgb, (31, 31), 0)
    return detect_parcels(rgb)


def to_msg(found, stamp, frame_id):
    msg = Detection2DArray()
    msg.header.stamp, msg.header.frame_id = stamp, frame_id
    for label, (x1, y1, x2, y2), score in found:
        det = Detection2D()
        det.header = msg.header
        det.bbox.center.position.x, det.bbox.center.position.y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        det.bbox.size_x, det.bbox.size_y = float(x2 - x1), float(y2 - y1)
        hyp = ObjectHypothesisWithPose()
        hyp.hypothesis.class_id, hyp.hypothesis.score = label, score
        det.results.append(hyp)
        msg.detections.append(det)
    return msg


class BlockingDetector:
    """(A) 물리 스레드에서 무거운 처리를 그대로 한다. 시뮬레이션이 그만큼 멈춘다."""

    def setup(self, context):
        self.context = context
        self.pub = context.node.create_publisher(Detection2DArray, "/vision/parcels_2d", 10)
        self.wall = self.sim = None
        self.last_report = None
        context.node.get_logger().info(f"[06A] 막는 방식: 매 프레임 {HEAVY_MS:.0f} ms 를 물리 스레드에서 소비")

    def __call__(self, frames):
        frame = frames[CAMERA]
        t0 = time.perf_counter()
        found = heavy_detect(frame.rgb)
        self.pub.publish(to_msg(found, self.context.stamp(), frame.optical_frame))
        ms = (time.perf_counter() - t0) * 1000
        now_wall, now_sim = time.monotonic(), self.context.sim_time()
        if self.wall is not None and (self.last_report is None or now_sim - self.last_report >= 1.0):
            ratio = (now_sim - self.sim) / (now_wall - self.wall)
            self.context.node.get_logger().info(
                f"[06A] sim {now_sim:7.1f}s  캡처 {self.context.pump.fps:.2f} FPS  실시간 비율 {ratio:.2f}  "
                f"처리 {ms:.0f} ms/프레임  검출 {len(found)}개")
            self.last_report = now_sim
        self.wall, self.sim = now_wall, now_sim


class WorkerDetector(WorkerHandler):
    """(B) WorkerHandler: prepare -> [워커] process -> publish. 적응형 FPS 와 통계는 기반 클래스가 한다."""

    def __init__(self):
        super().__init__(adaptive=os.environ.get("M1_ADAPTIVE", "1") != "0", min_fps=0.5)
        self.last_report = None
        self.published = 0

    def on_setup(self, context):
        self.pub = context.node.create_publisher(Detection2DArray, "/vision/parcels_2d", 10)
        context.node.get_logger().info(f"[06B] 워커 방식: {HEAVY_MS:.0f} ms 처리를 워커 스레드로, adaptive={self.adaptive}")

    def prepare(self, frames):
        f = frames[CAMERA]
        return (f.rgb.copy(), f.sim_time, f.optical_frame)   # 워커에 넘길 최소한. 물리 스레드는 여기서 끝

    def process(self, item):
        rgb, sim_time, frame_id = item
        return heavy_detect(rgb), sim_time, frame_id

    def publish(self, result):
        found, sim_time, frame_id = result
        self.pub.publish(to_msg(found, self.context.stamp(), frame_id))
        self.published += 1
        now = self.context.sim_time()
        if self.last_report is None or now - self.last_report >= 1.0:
            self.last_report = now
            self.context.node.get_logger().info(
                f"[06B] sim {now:7.1f}s  캡처 {self.context.pump.fps:.2f} FPS  실시간 비율 {self._ratio:.2f}  "
                f"추론 {self._inference_ms:.0f} ms  지연 {now - sim_time:.2f} s  버린 프레임 {self._dropped}  발행 {self.published}")
