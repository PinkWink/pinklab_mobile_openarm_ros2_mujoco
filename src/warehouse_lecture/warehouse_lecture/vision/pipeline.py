"""Compose several in-process camera handlers behind the single --camera-handler slot.

Default lecture pipeline: ArUco docking markers (base camera) + ground-truth detector
(segmentation). Set LECTURE_HANDLERS="module:attr,module:attr" to change the list.

    camera_handler:=warehouse_lecture.vision.pipeline:LecturePipeline \
    camera_depth:=true camera_segmentation:=true
"""

import os

from mobile_openarm_mujoco.handler import load_handler


class CompositeHandler:
    def __init__(self, handlers):
        self.handlers = list(handlers)

    def setup(self, context):
        for h in self.handlers:
            if hasattr(h, "setup"):
                h.setup(context)

    def __call__(self, frames):
        for h in self.handlers:
            h(frames)

    def close(self):
        for h in self.handlers:
            if hasattr(h, "close"):
                h.close()


class LecturePipeline(CompositeHandler):
    def __init__(self):
        spec = os.environ.get("LECTURE_HANDLERS", "")
        if spec:
            handlers = [load_handler(s.strip()) for s in spec.split(",") if s.strip()]
        else:
            from .aruco import ArucoDetector
            from .truth_detector import TruthDetector

            handlers = [ArucoDetector(adaptive=False), TruthDetector()]
        super().__init__(handlers)
