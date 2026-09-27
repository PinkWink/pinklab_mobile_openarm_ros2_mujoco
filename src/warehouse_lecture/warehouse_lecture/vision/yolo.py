"""CPU YOLO wrapper for in-process camera handlers (M2 onwards).

Loads a .pt, .onnx or OpenVINO directory exported by ultralytics and returns plain
Python detections so handlers do not depend on ultralytics result objects.

    det = YoloDetector("weights/warehouse_yolo11n_s320_320_openvino_model", imgsz=320, conf=0.4)
    for label, (x1, y1, x2, y2), score in det.detect(frame.rgb): ...
"""

import os
import time
from pathlib import Path

import numpy as np

from .labels import CLASSES

DEFAULT_WEIGHTS = "weights/warehouse_yolo11n_s320_320_openvino_model"  # 320 으로 미세조정한 모델의 OpenVINO 내보내기


def resolve_weights(path=None):
    """Pick the first existing candidate: explicit path, env WAREHOUSE_YOLO, OpenVINO, ONNX, .pt."""
    candidates = [path, os.environ.get("WAREHOUSE_YOLO"), DEFAULT_WEIGHTS,
                  "weights/warehouse_yolo11n_s320_320.onnx", "weights/warehouse_yolo11n_320_openvino_model",
                  "weights/warehouse_yolo11n_s320.pt", "weights/warehouse_yolo11n.pt"]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    raise FileNotFoundError("no YOLO weights found; run examples/m2_yolo/04 and 06 or copy weights/ from the instructor")


class YoloDetector:
    def __init__(self, weights=None, imgsz=320, conf=0.4, iou=0.5, threads=None, classes=CLASSES):
        from ultralytics import YOLO

        if threads:
            os.environ.setdefault("OMP_NUM_THREADS", str(threads))
            try:
                import torch
                torch.set_num_threads(int(threads))
            except ImportError:
                pass
        self.path = resolve_weights(weights)
        self.imgsz, self.conf, self.iou = int(imgsz), float(conf), float(iou)
        task = "detect"
        self.model = YOLO(self.path, task=task)
        names = self.model.names if isinstance(self.model.names, dict) else dict(enumerate(self.model.names))
        # Exported models keep the training names; fall back to the lecture class list.
        self.names = {int(k): str(v) for k, v in names.items()} if names and not str(names.get(0, "")).isdigit() else dict(enumerate(classes))
        self.last_ms = 0.0
        self.detect(np.zeros((self.imgsz, self.imgsz, 3), np.uint8))  # warm-up (first call compiles/allocates)

    def detect(self, rgb, conf=None):
        """rgb: HxWx3 uint8 (RGB). Returns [(label, (x1, y1, x2, y2), score)] in pixels of the input image."""
        results = self.detect_batch([rgb], conf)
        return results[0]

    def detect_batch(self, rgbs, conf=None):
        start = time.perf_counter()
        # ultralytics expects BGR ndarrays for numpy input. Exported models (ONNX/OpenVINO) have a
        # fixed batch of 1, so run one image at a time; batching gains nothing on CPU anyway.
        results = []
        for img in rgbs:
            bgr = np.ascontiguousarray(img[..., ::-1])
            results.extend(self.model.predict(bgr, imgsz=self.imgsz, conf=conf or self.conf, iou=self.iou, device="cpu", verbose=False))
        self.last_ms = (time.perf_counter() - start) * 1000
        out = []
        for r in results:
            dets = []
            if r.boxes is not None and len(r.boxes):
                xyxy = r.boxes.xyxy.cpu().numpy()
                cls = r.boxes.cls.cpu().numpy().astype(int)
                scores = r.boxes.conf.cpu().numpy()
                for (x1, y1, x2, y2), c, s in zip(xyxy, cls, scores):
                    dets.append((self.names.get(int(c), str(c)), (int(x1), int(y1), int(x2), int(y2)), float(s)))
            out.append(dets)
        return out
