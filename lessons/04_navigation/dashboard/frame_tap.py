"""Camera handler for the web dashboard: the usual lecture vision pipeline + latest JPEG per camera.

MuJoCo renders the cameras inside the simulator process and no image topics exist, so this handler
(loaded with camera_handler:=...) writes each camera's newest frame to shared memory
(/dev/shm/mobile_openarm_dashboard/<camera>.jpg). dashboard/server.py streams those files to the browser.

    ./scripts/mobile_openarm nav moveit:=false camera_fps:=5 \
        camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline
"""
import json
import os
from pathlib import Path

import cv2

from warehouse_lecture.vision.pipeline import LecturePipeline

FRAMES = Path(os.environ.get("DASHBOARD_FRAMES", "/dev/shm/mobile_openarm_dashboard"))


class DashboardPipeline(LecturePipeline):
    """ArUco + detections as before, then JPEG-encode every frame (~1 ms for 320 x 240)."""

    def setup(self, context):
        super().setup(context)
        FRAMES.mkdir(parents=True, exist_ok=True)

    def __call__(self, frames):
        super().__call__(frames)                         # /vision/* first: the dashboard is only a viewer
        meta = {}
        for name, frame in frames.items():
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(frame.rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            tmp = FRAMES / f".{name}.jpg.tmp"
            tmp.write_bytes(jpg.tobytes())
            os.replace(tmp, FRAMES / f"{name}.jpg")       # atomic: the server never reads half a file
            meta[name] = dict(sim_time=frame.sim_time, width=frame.rgb.shape[1], height=frame.rgb.shape[0])
        tmp = FRAMES / ".meta.json.tmp"
        tmp.write_text(json.dumps(meta))
        os.replace(tmp, FRAMES / "meta.json")
