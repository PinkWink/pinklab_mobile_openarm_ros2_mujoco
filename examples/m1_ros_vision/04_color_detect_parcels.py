#!/usr/bin/env python3
"""M1 예제 4: HSV 색 분할로 작업대 위 상자(parcel)를 찾아 vision_msgs/Detection2DArray 로 발행한다.

실행 (시뮬레이터 인자로 핸들러를 넘긴다):
    ./scripts/mobile_openarm start viewer:=false \\
        camera_handler:=examples/m1_ros_vision/04_color_detect_parcels.py:ColorParcelDetector
    다른 터미널:
    ./scripts/mobile_openarm goal 1.2 -3.6 0            # pick_table 앞 사전 도킹 지점으로 이동
    ./scripts/mobile_openarm exec ros2 topic echo /vision/parcels_2d
  옵션(환경변수): M1_CAMERA=head_camera (검출 카메라), M1_WINDOW=0 (창 끄기)
  미리보기: artifacts/m1/04_color_detect.png

배우는 점:
- 핸들러 안에서 numpy 배열(frame.rgb)을 바로 OpenCV 로 처리하고, 결과만 ROS 메시지로 낸다.
- Detection2D: bbox.center.position(x, y), bbox.size_x/size_y 는 픽셀. results[0].hypothesis.class_id/score.
  header.frame_id 는 카메라 optical frame, stamp 는 시뮬레이션 시간(context.stamp()).
- 색만 쓰면 한계가 바로 보인다. 노란 상자(H 20~30)와 노란 안전모(H 25~30)를 구분하지 못하고,
  선반의 갈색 상자(H 13~20)가 경계에 걸린다. 05번에서 깊이·높이로, M2 에서 YOLO 로 해결한다.
"""

import os
import time
from pathlib import Path

import cv2
import numpy as np
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose

# OpenCV HSV: H 0~179, S/V 0~255. 값은 artifacts/m1/03_frames.png 에서 측정한 것. 조명이 바뀌면 다시 잰다.
COLOR_RANGES = {
    "parcel_red": [((0, 150, 60), (10, 255, 255)), ((170, 150, 60), (179, 255, 255))],  # 빨강은 H 0 을 넘어 두 구간
    "parcel_blue": [((85, 120, 60), (110, 255, 255))],
    "parcel_yellow": [((19, 120, 60), (32, 255, 255))],
}
MIN_AREA, MAX_AREA = 30, 3000  # 픽셀. 320x240 에서 1 m 거리의 4.5 cm 상자는 약 10x15 픽셀
DRAW = {"parcel_red": (0, 0, 255), "parcel_blue": (255, 128, 0), "parcel_yellow": (0, 255, 255)}


def detect_parcels(rgb):
    """RGB 프레임 -> [(label, (x1, y1, x2, y2), score)]. score 는 박스 안 마스크 채움 비율."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    kernel = np.ones((3, 3), np.uint8)
    found = []
    for label, ranges in COLOR_RANGES.items():
        mask = np.zeros(hsv.shape[:2], np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # 1~2 픽셀 잡음 제거
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if not MIN_AREA <= area <= MAX_AREA:
                continue
            found.append((label, (int(x), int(y), int(x + w), int(y + h)), float(area) / float(w * h)))
    return found


class ColorParcelDetector:
    def __init__(self):
        self.camera = os.environ.get("M1_CAMERA", "head_camera")
        self.window = os.environ.get("M1_WINDOW", "1") != "0" and bool(os.environ.get("DISPLAY"))
        self.out = Path("artifacts/m1"); self.out.mkdir(parents=True, exist_ok=True)
        self.last_report = None

    def setup(self, context):
        self.context = context
        if self.camera not in context.camera_names:
            raise ValueError(f"{self.camera} 는 활성 카메라가 아니다: {context.camera_names} (camera_names:= 로 추가)")
        self.pub = context.node.create_publisher(Detection2DArray, "/vision/parcels_2d", 10)
        context.node.get_logger().info(f"[04] {self.camera} 에서 HSV 상자 검출 -> /vision/parcels_2d")

    def __call__(self, frames):
        frame = frames[self.camera]
        t0 = time.perf_counter()
        found = detect_parcels(frame.rgb)
        ms = (time.perf_counter() - t0) * 1000

        msg = Detection2DArray()
        msg.header.stamp = self.context.stamp()          # 시뮬레이션 시간. 05번에서 tf 조회에 쓴다
        msg.header.frame_id = frame.optical_frame
        for label, (x1, y1, x2, y2), score in found:
            det = Detection2D()
            det.header = msg.header
            det.id = self.camera
            det.bbox.center.position.x = (x1 + x2) / 2.0
            det.bbox.center.position.y = (y1 + y2) / 2.0
            det.bbox.size_x, det.bbox.size_y = float(x2 - x1), float(y2 - y1)
            hyp = ObjectHypothesisWithPose()
            hyp.hypothesis.class_id, hyp.hypothesis.score = label, score
            det.results.append(hyp)
            msg.detections.append(det)
        self.pub.publish(msg)

        if self.last_report is None or frame.sim_time - self.last_report >= 1.0:
            self.last_report = frame.sim_time
            summary = ", ".join(f"{l}@({(b[0]+b[2])//2},{(b[1]+b[3])//2}) {b[2]-b[0]}x{b[3]-b[1]}" for l, b, _ in found) or "없음"
            self.context.node.get_logger().info(f"[04] t={frame.sim_time:.1f} 검출 {len(found)}개 ({ms:.1f} ms): {summary}")
            self.preview(frame, found)

    def preview(self, frame, found):
        bgr = cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR)
        for label, (x1, y1, x2, y2), score in found:
            cv2.rectangle(bgr, (x1, y1), (x2, y2), DRAW[label], 1)
            cv2.putText(bgr, f"{label[7:]} {score:.2f}", (x1, max(8, y1 - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, DRAW[label], 1)
        big = cv2.resize(bgr, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
        tmp = self.out / "04_color_detect.tmp.png"
        cv2.imwrite(str(tmp), big)
        tmp.replace(self.out / "04_color_detect.png")
        if self.window:
            try:
                cv2.imshow("M1-04 HSV parcels", big)
                cv2.waitKey(1)
            except cv2.error:
                self.window = False

    def close(self):
        if self.window:
            cv2.destroyAllWindows()
