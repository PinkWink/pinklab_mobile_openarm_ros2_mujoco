#!/usr/bin/env python3
"""M2 예제 1: 카메라 핸들러에서 RGB + 세그멘테이션을 받아 YOLO 라벨을 자동으로 저장한다.

실행 (세그멘테이션 렌더 필요. 학습용이므로 해상도를 올린다):
    ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m2_yolo/01_capture_dataset.py:DatasetCapture \\
        camera_segmentation:=true camera_size:=640x480 camera_fps:=2
    다른 터미널에서 로봇을 움직이면(goal, teleop) 시점이 바뀐다. 02번은 이 과정을 자동화한다.
  옵션(환경변수): M2_DATASET=datasets/warehouse_raw  M2_INTERVAL=0.5 (저장 간격, 시뮬레이션 초)  M2_MAX=3000

배우는 점:
- 라벨의 출처는 MuJoCo 세그멘테이션(픽셀마다 body id)이다. warehouse_lecture.vision.labels.label_frame 이
  body id -> 클래스 박스로 바꾼다. 사람의 안전모·조끼는 geom 을 투영해 별도 클래스로 만든다.
- YOLO 라벨 형식: 한 줄에 "cls cx cy w h" (0~1 정규화). 이미지와 같은 이름의 .txt.
- 클래스 순서(labels.CLASSES)는 데이터셋의 계약이다. 학습·평가·핸들러가 모두 이 순서를 쓴다.
- 메타(meta.jsonl)에 카메라·시뮬레이션 시간·로봇 자세·배우 속성을 남긴다. 05번에서 안전모 정확도 평가에 쓴다.
"""

import json
import os
from pathlib import Path

import cv2
from warehouse_lecture.vision.labels import CLASSES, label_frame


class DatasetCapture:
    def __init__(self, root=None, interval=None, max_images=None):
        self.root = Path(root or os.environ.get("M2_DATASET", "datasets/warehouse_raw"))
        self.interval = float(interval if interval is not None else os.environ.get("M2_INTERVAL", "0.5"))
        self.max_images = int(max_images if max_images is not None else os.environ.get("M2_MAX", "3000"))
        self.last_save = None
        self.count = 0      # 저장한 이미지 수
        self.scene = 0      # 저장 회차. 같은 순간의 카메라들이 같은 번호를 공유한다 (분할 단위)
        self.done = False

    def setup(self, context):
        self.context = context
        if not context.pump.segmentation:
            raise ValueError("camera_segmentation:=true 가 필요하다")
        (self.root / "images").mkdir(parents=True, exist_ok=True)
        (self.root / "labels").mkdir(parents=True, exist_ok=True)
        (self.root / "classes.txt").write_text("\n".join(CLASSES) + "\n")
        self.meta = open(self.root / "meta.jsonl", "a")
        self.body_labels = context.body_labels()
        existing = sorted((self.root / "images").glob("*.png"))
        self.count = len(existing)
        self.scene = int(existing[-1].stem.split("_")[0]) + 1 if existing else 0
        context.node.get_logger().info(f"[m2-01] 데이터셋 {self.root} (기존 {self.count}장), {self.interval}s 간격, 최대 {self.max_images}장")

    def __call__(self, frames):
        if self.done:
            return
        first = next(iter(frames.values()))
        if self.last_save is not None and first.sim_time - self.last_save < self.interval:
            return
        self.last_save = first.sim_time
        self.save(frames)
        if self.count >= self.max_images:
            self.done = True
            self.context.node.get_logger().info(f"[m2-01] {self.count}장 저장 완료. 시뮬레이터를 종료해도 된다")

    def save(self, frames):
        ctx = self.context
        pose = ctx.physics.pose()
        for name, frame in frames.items():
            labels = label_frame(frame, ctx.physics, self.body_labels, actors=ctx.actors, min_pixels=24)
            stem = f"{self.scene:06d}_{name}"
            h, w = frame.rgb.shape[:2]
            cv2.imwrite(str(self.root / "images" / f"{stem}.png"), cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR))
            lines = []
            for cls, (x1, y1, x2, y2) in labels:
                cx, cy = (x1 + x2 + 1) / 2 / w, (y1 + y2 + 1) / 2 / h   # 픽셀 경계 포함(+1)
                bw, bh = (x2 - x1 + 1) / w, (y2 - y1 + 1) / h
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            (self.root / "labels" / f"{stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
            self.meta.write(json.dumps({
                "image": f"{stem}.png", "camera": name, "sim_time": round(frame.sim_time, 3),
                "robot_xyyaw": [round(float(v), 3) for v in pose],
                "labels": [CLASSES[c] for c, _ in labels],
                "actors": ctx.actors.states() if ctx.actors is not None else {},
            }, default=lambda o: getattr(o, "tolist", lambda: str(o))()) + "\n")
            self.count += 1
        self.scene += 1
        self.meta.flush()
        if self.count % 100 < len(frames):
            ctx.node.get_logger().info(f"[m2-01] {self.count}장 (마지막: {', '.join(CLASSES[c] for c, _ in labels) or '라벨 없음'})")

    def close(self):
        self.meta.close()
