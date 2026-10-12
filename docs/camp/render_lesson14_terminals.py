"""Terminal captures for the lesson-14 (⑬ Web Dashboard) page, cut from the real logs of the 2026-10-12 run
(artifacts/dev/l13dash/sim.log · tm.log · server.log). ROS stamps and colour codes are stripped; nothing is rewritten.
Output: docs/camp/lesson14_t1.png, lesson14_t2.png, lesson14_t3.png
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
DATA = Path("artifacts/dev/l13dash")
P, O = "prompt", "out"


def clean(line):
    line = re.sub(r"\x1b\[[0-9;]*m", "", line.rstrip("\n"))
    return re.sub(r" \[\d{10}\.\d+\]", "", line)                     # ROS wall stamp


def pick(path, patterns, limit=None):
    out = []
    for line in open(path, errors="replace"):
        if any(p in line for p in patterns):
            out.append(clean(line))
    return out[:limit] if limit else out


T1 = ("H=warehouse_lecture.vision; LECTURE_HANDLERS=\"\\$H.aruco:ArucoDetector,\\$H.yolo_detector:YoloDetector3D\" \\",   # \\$: not matplotlib math
      "  ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false \\",
      "  camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline")
t1 = pick(DATA / "sim.log", ["process started with pid [", "You can start planning now", "PickPlace server ready", "Vic Pinky + OpenArm ready",
                             "Direct Python cameras enabled", "Managed nodes are active"])
render([(P, T1[0]), (O, T1[1]), (O, T1[2])] + [(O, t) for t in t1], OUT + "lesson14_t1.png", width=16.0,
       highlight=("cameras enabled", "Managed nodes are active", "PickPlace server ready"))

t2 = pick(DATA / "tm.log", ["server ready"]) + pick(DATA / "tm.log", ["[task_manager]: [1/5 navigate/start]", "[task_manager]: [2/5", "[task_manager]: [3/5 pick/start]"], limit=4)
render([(P, "./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager")] + [(O, t) for t in t2], OUT + "lesson14_t2.png",
       highlight=("ExecutePlan server ready",))

t3 = [clean(l) for l in open(DATA / "server.log", errors="replace") if "dashboard:" in l or "Running on" in l or "Serving Flask" in l]
t3 += pick(DATA / "server.log", ['"GET / HTTP', '"GET /desk/desk.js', '"GET /api/stream', '"POST /api/say'], limit=6)
render([(P, "./scripts/mobile_openarm exec python lessons/09_web_dashboard/server.py")] + [(O, t) for t in t3], OUT + "lesson14_t3.png",
       highlight=("dashboard: http://localhost:8080", "POST /api/say"))
