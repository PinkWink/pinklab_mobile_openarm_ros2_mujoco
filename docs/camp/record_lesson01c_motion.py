"""Step the /cmd target a little at a time and screenshot the MuJoCo and RViz windows at every step.

Run while urdf_bridge.py --viewer and view_urdf.launch.py sim:=true are up:
  python docs/camp/record_lesson01c_motion.py <MuJoCo window id> <RViz window id> <out folder>
Writes mj_NNN.png, rviz_NNN.png and steps.json (commanded target and /joint_states at each step).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

GOAL, UP, DOWN, SETTLE = np.array([0.6, 1.5]), 24, 10, 0.45


def main():
    mj, rviz, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node("motion_recorder")
    pub = node.create_publisher(Float64MultiArray, "/cmd", 10)
    state = {}
    node.create_subscription(JointState, "/joint_states", lambda m: state.update(q=list(m.position), tau=list(m.effort)), 10)
    targets = [GOAL * 0] * 2 + [GOAL * k / UP for k in range(1, UP + 1)] + [GOAL] * 2 + [GOAL * (1 - k / DOWN) for k in range(1, DOWN + 1)]
    steps = []
    for i, target in enumerate(targets):
        pub.publish(Float64MultiArray(data=target.tolist()))
        end = time.monotonic() + SETTLE                       # let the arm settle and a fresh camera image arrive
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.02)
        for name, wid in (("mj", mj), ("rviz", rviz)):
            subprocess.run(["import", "-window", wid, str(out / f"{name}_{i:03d}.png")], check=True)
        rclpy.spin_once(node, timeout_sec=0.05)
        steps.append({"cmd": target.tolist(), **state})
        print(i, np.round(target, 3), np.round(state.get("q", []), 3), flush=True)
    (out / "steps.json").write_text(json.dumps(steps))
    node.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
