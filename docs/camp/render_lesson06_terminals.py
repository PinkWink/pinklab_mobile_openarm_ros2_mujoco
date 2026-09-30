"""Terminal captures for the lesson-06 (Nav2 collision avoidance) page. Text copied from real runs on 2026-09-30
(nav mode, moveit:=false, fresh start at the spawn). Output: docs/camp/lesson06_cli_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"

render([(P, "python docs/camp/avoid_scenario.py                # crossing: 근로자가 x = 3.4 에서 통로를 가로지른다"),
        (O, "set_actor teleport: True teleport applied to worker_helmet_orange"),
        (O, "set_actor set_path: True set_path applied to worker_helmet_orange"),
        (O, "goal (6.2, 0.0, 0) accepted: True"),
        (O, "NavigateToPose result: status=4 (SUCCEEDED=4)  37.9 s"),
        (O, "closest robot-worker distance: 1.16 m (centre to centre)")],
       OUT + "lesson06_cli_crossing.png", highlight=("SUCCEEDED", "closest"))

render([(P, "python docs/camp/avoid_scenario.py --mode headon  # 근로자가 통로를 따라 마주 걸어온다"),
        (O, "set_actor teleport: True teleport applied to worker_helmet_orange"),
        (O, "set_actor set_path: True set_path applied to worker_helmet_orange"),
        (O, "goal (6.2, 0.0, 0) accepted: True"),
        (O, "NavigateToPose result: status=4 (SUCCEEDED=4)  38.1 s"),
        (O, "closest robot-worker distance: 0.30 m (centre to centre)")],
       OUT + "lesson06_cli_headon.png", highlight=("closest",))
