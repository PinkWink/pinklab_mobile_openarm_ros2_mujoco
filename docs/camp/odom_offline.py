"""Square drive inside MuJoCo only (no ROS): odom and ground truth read at the very same step.

    source /opt/ros/jazzy/setup.bash; source scripts/env.sh
    python docs/camp/odom_offline.py            # -> artifacts/dev/odom_offline.csv
"""
import csv
import math
from pathlib import Path

from mobile_openarm_mujoco.model import Physics

p = Physics("artifacts/mobile_generated/warehouse.xml")
for _ in range(100):
    p.step(0.0, 0.0)                     # settle on the floor
p.odom[:] = 0.0
x0, y0, a0 = p.pose()
rows, t = [], 0.0


def run(phase, v, w, ticks):
    global t
    for _ in range(ticks):
        p.step(v, w)
        t += p.bridge_period
        x, y, a = p.pose()
        c, s = math.cos(-a0), math.sin(-a0)
        rows.append((round(t, 3), phase, *p.odom, c * (x - x0) - s * (y - y0), s * (x - x0) + c * (y - y0), a - a0))


for _ in range(4):
    run("straight", 0.3, 0.0, 727)       # ~2 m at 0.3 m/s incl. ramp
    run("stop", 0.0, 0.0, 100)
    run("turn", 0.0, 0.5, 339)           # ~90 deg at 0.5 rad/s incl. ramp
    run("stop", 0.0, 0.0, 100)
out = Path("artifacts/dev/odom_offline.csv")
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["t", "phase", "odom_x", "odom_y", "odom_yaw", "true_x", "true_y", "true_yaw"])
    w.writerows(rows)
print("wrote", out, len(rows))
