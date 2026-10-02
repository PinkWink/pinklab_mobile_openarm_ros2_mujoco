"""Terminal captures for the lesson-09 (Arm / End-Effector Control) page. Text below is copied from real runs on
2026-10-02 (moveit mode; pose · cartesian · demo re-run after JointConstraint ±0.001 rad). Output: docs/camp/lesson09_cli_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
EE = "./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py"

render([(P, f"{EE} where"),
        (O, "left  TCP: x=0.375 y=+0.153 z=0.549   (shoulder y=+0.093)"),
        (O, "right TCP: x=0.375 y=-0.153 z=0.549   (shoulder y=-0.093)"),
        (P, f"{EE} named both ready"),
        (O, "left: -> ready"), (O, "right: -> ready")],
       OUT + "lesson09_cli_where.png", highlight=("TCP:",))

render([(P, f"{EE} ik left 0.45 0.20 0.95"),
        (O, "left IK for (0.45, 0.2, 0.95):"),
        (O, "   openarm_left_joint1      -1.705 rad ( -97.7 deg)"),
        (O, "   openarm_left_joint2      -1.063 rad ( -60.9 deg)"),
        (O, "   openarm_left_joint3      +1.573 rad ( +90.1 deg)"),
        (O, "   openarm_left_joint4      +1.804 rad (+103.4 deg)"),
        (O, "   openarm_left_joint5      +1.569 rad ( +89.9 deg)"),
        (O, "   openarm_left_joint6      -0.741 rad ( -42.4 deg)"),
        (O, "   openarm_left_joint7      -0.130 rad (  -7.5 deg)")],
       OUT + "lesson09_cli_ik.png", highlight=("IK for",))

render([(P, f"time {EE} pose left 0.45 0.20 0.95"),
        (O, "left: plan to TCP (0.45, 0.2, 0.95) (forward horizontal grasp)"),
        (O, "   reached x=0.450 y=+0.201 z=0.950, error 1.3 mm"),
        (O, ""), (O, "real\t0m11.231s"), (O, "user\t0m1.744s"), (O, "sys\t0m0.904s")],
       OUT + "lesson09_cli_pose.png", highlight=("reached", "real"))

render([(P, f"time {EE} cartesian left 0 0 -0.05"),
        (O, "left: straight line from (0.450, +0.200, 0.950) by (0.0, 0.0, -0.05)"),
        (O, "   followed 100 %, now x=0.450 y=+0.200 z=0.901"),
        (O, ""), (O, "real\t0m2.657s"), (O, "user\t0m1.129s"), (O, "sys\t0m0.865s")],
       OUT + "lesson09_cli_cart.png", highlight=("followed 100 %", "real"))

render([(P, f"{EE} gripper left close"),
        (O, "left gripper close: finger at 11.3 mm (stalled=False, reached=True)"),
        (P, f"{EE} gripper left open"),
        (O, "left gripper open: finger at 44.8 mm (stalled=False, reached=True)")],
       OUT + "lesson09_cli_gripper.png", highlight=("finger at",))

render([(P, f"{EE} pose left 0.65 0.20 0.95"),
        (O, "left: plan to TCP (0.65, 0.2, 0.95) (forward horizontal grasp)"),
        (O, "error: No IK solution for left arm at (0.65, 0.20, 0.95)"),
        (P, f"{EE} cartesian left 0.3 0 0"),
        (O, "left: straight line from (0.449, +0.192, 0.961) by (0.3, 0.0, 0.0)"),
        (O, "error: Cartesian path covers only 55% (error_code=1)")],
       OUT + "lesson09_cli_fail.png", highlight=("error:",))

render([(P, f"time {EE} demo"),
        (O, "left  TCP: x=0.374 y=+0.154 z=0.549   (shoulder y=+0.093)"),
        (O, "right TCP: x=0.374 y=-0.154 z=0.549   (shoulder y=-0.093)"),
        (O, "left: -> ready"), (O, "right: -> ready"),
        (O, "left: plan to TCP (0.45, 0.2, 0.95) (forward horizontal grasp)"),
        (O, "   reached x=0.450 y=+0.201 z=0.950, error 1.3 mm"),
        (O, "left: straight line from (0.450, +0.201, 0.950) by (0.0, 0.0, -0.05)"),
        (O, "   followed 100 %, now x=0.450 y=+0.201 z=0.900"),
        (O, "left gripper close: finger at 11.3 mm (stalled=False, reached=True)"),
        (O, "left gripper open: finger at 44.8 mm (stalled=False, reached=True)"),
        (O, "left: straight line from (0.450, +0.201, 0.900) by (0.0, 0.0, 0.05)"),
        (O, "   followed 100 %, now x=0.450 y=+0.201 z=0.949"),
        (O, "left: -> transport"), (O, "right: -> transport"),
        (O, "left  TCP: x=0.375 y=+0.154 z=0.550   (shoulder y=+0.093)"),
        (O, "right TCP: x=0.375 y=-0.154 z=0.550   (shoulder y=-0.093)"),
        (O, ""), (O, "real\t0m31.618s"), (O, "user\t0m3.187s"), (O, "sys\t0m0.958s")],
       OUT + "lesson09_cli_demo.png", highlight=("reached", "followed", "finger at", "real"))
