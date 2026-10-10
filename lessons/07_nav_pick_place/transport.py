#!/usr/bin/env python3
"""Lesson 07 (Navigation + Pick & Place): one PickPlace goal that drives across the warehouse.

Start the full stack from the warehouse centre (default spawn, Nav2 + AMCL on the warehouse map):
    H=warehouse_lecture.vision
    LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start camera_depth:=true locate:=vision viewer:=true rviz:=true
Then:
    ./scripts/mobile_openarm exec python lessons/07_nav_pick_place/transport.py red                         # pick_table -> place_table
    ./scripts/mobile_openarm exec python lessons/07_nav_pick_place/transport.py blue --from pick_table --to place_table

Equivalent CLI (same action, phase=all):
    ./scripts/mobile_openarm pick red pick_table place_table

What to notice:
  The skill is one state machine: navigate_pick -> dock -> locate -> pre_grasp -> grasp -> lift -> carry
  -> navigate_place -> dock -> place -> retreat. Nav2 only brings the base to the station's pre-dock pose
  (locations.yaml base_goal); the last half metre is the ArUco marker docking, so Nav2's goal tolerance
  does not decide where the hand ends up. This script prints, for every phase, when it started, where the
  robot was on the map (TF map -> base_footprint, i.e. AMCL) and how far the base drove during the phase.
"""

import argparse
import math
import sys
import time

import rclpy
import rclpy.time
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from tf2_ros import Buffer, TransformException, TransformListener
from warehouse_interfaces.action import PickPlace


class Transport(Node):
    def __init__(self):
        super().__init__("lesson07_transport", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.client = ActionClient(self, PickPlace, "/pick_place")
        self.tf = Buffer()
        TransformListener(self.tf, self, spin_thread=False)
        self.path = 0.0
        self.last_xy = None
        self.create_timer(0.2, self.odometer)

    def where(self):
        """Robot pose on the map from TF (map -> odom from AMCL, odom -> base_footprint from the bridge)."""
        try:
            tf = self.tf.lookup_transform("map", "base_footprint", rclpy.time.Time()).transform
        except TransformException:
            return None
        q = tf.rotation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        return tf.translation.x, tf.translation.y, yaw

    def odometer(self):
        p = self.where()
        if p is None:
            return
        if self.last_xy is not None:
            self.path += math.hypot(p[0] - self.last_xy[0], p[1] - self.last_xy[1])
        self.last_xy = p[:2]

    def run(self, colour, src, dst, timeout=900.0):
        if not self.client.wait_for_server(timeout_sec=30.0):
            raise SystemExit("/pick_place not available: start the simulator with moveit:=true (default) and skills:=true")
        end = time.monotonic() + 10.0
        while self.where() is None and time.monotonic() < end:   # let TF (map -> base_footprint) fill first
            rclpy.spin_once(self, timeout_sec=0.1)
        goal = PickPlace.Goal(object=colour, from_station=src, to_station=dst, phase="all")
        print(f">> PickPlace object={colour} {src} -> {dst}")
        t0 = time.monotonic()
        rows = []                                             # (phase, start s, path at start)
        last = [""]

        def on_fb(m):
            f = m.feedback
            if not rows or rows[-1][0] != f.phase:
                rows.append((f.phase, time.monotonic() - t0, self.path))
                p = self.where()
                at = f"map ({p[0]:+.2f}, {p[1]:+.2f}, {math.degrees(p[2]):+4.0f}deg)" if p else "map (no TF)"
                print(f"   [{time.monotonic() - t0:5.1f}s] {f.phase:14s} at {at}  driven {self.path:5.2f} m", flush=True)
            if f.detail != last[0] and not f.detail.startswith("visual dock"):
                last[0] = f.detail
                print(f"            {f.detail}", flush=True)

        future = self.client.send_goal_async(goal, feedback_callback=on_fb)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        gh = future.result()
        if gh is None or not gh.accepted:
            print("   rejected (another PickPlace running?)")
            return None
        rf = gh.get_result_async()
        end = time.monotonic() + timeout
        while not rf.done() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not rf.done():
            gh.cancel_goal_async()
            print("   timeout")
            return None
        r = rf.result().result
        status = {v: k[7:] for k, v in vars(GoalStatus).items() if k.startswith("STATUS_")}[rf.result().status]
        total = time.monotonic() - t0
        print(f"<< {status} success={r.success} phase_reached={r.phase_reached} {r.duration_s:.0f}s: {r.message}")
        print("   phase            start   time  driven")
        for i, (phase, start, path) in enumerate(rows):
            stop, path_end = (rows[i + 1][1], rows[i + 1][2]) if i + 1 < len(rows) else (total, self.path)
            print(f"   {phase:14s} {start:6.1f} {stop - start:6.1f} {path_end - path:6.2f} m")
        print(f"   total                  {total:6.1f} {self.path:6.2f} m")
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("colour", choices=["red", "blue", "yellow"])
    ap.add_argument("--from", dest="src", default="pick_table")
    ap.add_argument("--to", dest="dst", default="place_table")
    a = ap.parse_args()
    rclpy.init()
    node = Transport()
    try:
        r = node.run(a.colour, a.src, a.dst)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0 if r and r.success else 1)


if __name__ == "__main__":
    main()
