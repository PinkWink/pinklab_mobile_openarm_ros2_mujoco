#!/usr/bin/env python3
"""Lesson 05 (MoveIt): end-effector control of the OpenARM arms from Python, without the pick-and-place skill.

Run the simulator with MoveIt first (any of these):
    ./scripts/mobile_openarm moveit viewer:=true rviz:=false                  # MuJoCo + MoveIt only
    ./scripts/mobile_openarm start spawn:=pick_table                          # full stack, robot already at the pick table
Then:
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py where                       # TCP poses of both arms (TF)
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py named both ready            # SRDF named pose (ready | hands_up | transport | home)
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py ik left 0.45 0.20 0.95      # IK only: print the 7 joint angles
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py pose left 0.45 0.20 0.95    # plan + execute to a TCP position (fingers forward, horizontal)
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py cartesian left 0 0 -0.05    # straight-line move relative to the current TCP
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py gripper left close          # open | close
    ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py demo                        # the sequence below

What to notice:
- Poses are TCP positions in base_footprint (x forward, y left, z up; table top is 0.78 m). The orientation is fixed
  to the skill's forward horizontal grasp (GRASP_FORWARD) so a pose is just three numbers here.
- IK (/compute_ik) gives joint angles for a pose; a *pose goal* is IK + a joint-space plan (collision-free, may swing);
  a *Cartesian path* (/compute_cartesian_path) keeps the TCP on a straight line and fails when the line leaves the reach.
- Nothing here talks to the robot's motors directly: MoveIt plans, then sends the trajectory to the MuJoCo bridge's
  FollowJointTrajectory action, the same interface a real robot controller would offer.
"""

import argparse
import math
import sys
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from tf2_ros import Buffer, TransformException, TransformListener

from warehouse_skills.moveit_client import GRASP_FORWARD, MoveItClient, SkillError, make_pose
from warehouse_skills.pick_place_server import load_skills, srdf_states

OPEN, CLOSE, EFFORT = 0.044, 0.012, 25.0


class EEControl(Node):
    def __init__(self):
        super().__init__("lesson05_ee_control", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.cfg = load_skills()
        self.arms = self.cfg["arms"]
        self.moveit = MoveItClient(self, self.cfg, self.arms)
        self.states = srdf_states()
        self.tf = Buffer()
        self.tf_listener = TransformListener(self.tf, self, spin_thread=False)

    def tcp(self, side, timeout=3.0):
        """Current TCP position (x, y, z) in base_footprint, from TF."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                t = self.tf.lookup_transform("base_footprint", self.arms[side]["tcp_link"], rclpy.time.Time()).transform.translation
                return t.x, t.y, t.z
            except TransformException:
                time.sleep(0.1)
        raise SkillError(f"no TF for {self.arms[side]['tcp_link']}")

    # --- commands --------------------------------------------------------------------
    def where(self):
        for side in ("left", "right"):
            x, y, z = self.tcp(side)
            print(f"{side:5s} TCP: x={x:.3f} y={y:+.3f} z={z:.3f}   (shoulder y={self.arms[side]['shoulder_y']:+.3f})")

    def named(self, side, name):
        for s in (["left", "right"] if side == "both" else [side]):
            if name not in self.states[s]:
                raise SkillError(f"unknown pose {name!r}; SRDF has {', '.join(self.states[s])}")
            print(f"{s}: -> {name}")
            self.moveit.move_named(s, name, self.states)

    def ik(self, side, xyz):
        q = self.moveit.solve_ik(side, make_pose(xyz))
        print(f"{side} IK for {tuple(round(v, 3) for v in xyz)}:")
        for name, value in zip(self.moveit.arm_joints(side), q):
            print(f"   {name:24s} {value:+.3f} rad ({math.degrees(value):+6.1f} deg)")

    def pose(self, side, xyz):
        print(f"{side}: plan to TCP {tuple(round(v, 3) for v in xyz)} (forward horizontal grasp)")
        self.moveit.move_pose(side, make_pose(xyz))
        x, y, z = self.tcp(side)
        err = math.dist((x, y, z), xyz)
        print(f"   reached x={x:.3f} y={y:+.3f} z={z:.3f}, error {err * 1000:.1f} mm")

    def cartesian(self, side, dxyz):
        x, y, z = self.tcp(side)
        target = (x + dxyz[0], y + dxyz[1], z + dxyz[2])
        print(f"{side}: straight line from ({x:.3f}, {y:+.3f}, {z:.3f}) by {tuple(dxyz)}")
        fraction = self.moveit.move_cartesian(side, [make_pose(target)])
        x, y, z = self.tcp(side)
        print(f"   followed {fraction * 100:.0f} %, now x={x:.3f} y={y:+.3f} z={z:.3f}")

    def gripper(self, side, action):
        pos = OPEN if action == "open" else CLOSE
        r = self.moveit.gripper(side, pos, EFFORT)
        print(f"{side} gripper {action}: finger at {r.position * 1000:.1f} mm (stalled={r.stalled}, reached={r.reached_goal})")

    def demo(self):
        """ready pose -> hover over the table edge -> down 5 cm -> close -> open -> up -> back to transport."""
        self.where()
        self.named("both", "ready")
        self.pose("left", (0.45, 0.20, 0.95))
        self.cartesian("left", (0.0, 0.0, -0.05))
        self.gripper("left", "close")
        self.gripper("left", "open")
        self.cartesian("left", (0.0, 0.0, 0.05))
        self.named("both", "transport")
        self.where()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["where", "named", "ik", "pose", "cartesian", "gripper", "demo"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    rclpy.init()
    node = EEControl()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    import threading
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    code = 0
    try:
        node.moveit.ready(timeout=30.0)
        c, args = a.command, a.args
        if c == "where":
            node.where()
        elif c == "named":
            node.named(args[0], args[1])
        elif c in ("ik", "pose", "cartesian"):
            side, xyz = args[0], tuple(float(v) for v in args[1:4])
            getattr(node, c)(side, xyz)
        elif c == "gripper":
            node.gripper(args[0], args[1])
        elif c == "demo":
            node.demo()
    except (SkillError, IndexError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        code = 1
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()
