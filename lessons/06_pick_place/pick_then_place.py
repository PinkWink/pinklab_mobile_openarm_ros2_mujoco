#!/usr/bin/env python3
"""Lesson 06 (Pick & Place): grasp a parcel and put it back on the same table, without driving across the warehouse.

Start the simulator with the robot already at the pick table (no Nav2 travel; the skill only docks the last metre):
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start spawn:=pick_table camera_depth:=true locate:=vision viewer:=true rviz:=false
Then:
    ./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red                 # pick red, place it back on pick_table
    ./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py blue --to place_table   # (with driving) place on the other table
    ./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red --only pick       # stop while holding; inspect in the viewer
    ./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red --only place      # then finish

Equivalent CLI (same action, same phases):
    ./scripts/mobile_openarm pick red --phase pick
    ./scripts/mobile_openarm pick red pick_table --phase place

What to notice (feedback phases printed with their timing):
  navigate_pick  Nav2 to the pre-dock pose (already there -> instant)
  dock           ArUco marker pair visual servo + short odometry segment
  locate         object position relative to base_footprint (camera detections, locate:=vision)
  pre_grasp / grasp / lift   IK to a pose behind the parcel, straight-line approach, gripper close (stall = holding), attach, lift + retreat
  carry          hands_up pose (the parcel clears the base and the table), undock 0.75 m
  place          dock again, free slot relative to the marker, lower, open, detach, retreat, transport pose
"""

import argparse
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseArray
from warehouse_interfaces.action import PickPlace

PARCELS = {"red": 0, "blue": 1, "yellow": 2}     # index in /warehouse/object_poses (parcel_1..3)


class PhaseClient(Node):
    def __init__(self):
        super().__init__("lesson06_pick_then_place", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.client = ActionClient(self, PickPlace, "/pick_place")
        self.poses = None
        self.create_subscription(PoseArray, "/warehouse/object_poses", lambda m: setattr(self, "poses", m.poses), 10)

    def parcel_z(self, colour):
        return self.poses[PARCELS[colour]].position.z if self.poses else float("nan")

    def run(self, colour, phase, station, timeout=600.0):
        if not self.client.wait_for_server(timeout_sec=30.0):
            raise SystemExit("/pick_place not available: start the simulator with moveit:=true (default) and skills:=true")
        goal = PickPlace.Goal(object=colour, phase=phase)
        if phase == "pick":
            goal.from_station = station
        else:
            goal.to_station = station
        print(f">> PickPlace phase={phase} object={colour} station={station}  (parcel z={self.parcel_z(colour):.3f} m)")
        t0 = time.monotonic()
        timeline = {}
        last = [""]

        def on_fb(m):
            f = m.feedback
            timeline.setdefault(f.phase, time.monotonic() - t0)
            text = f"   [{time.monotonic() - t0:5.1f}s {f.phase:14s}] {f.detail}"
            if text[10:] != last[0]:
                last[0] = text[10:]
                print(text, flush=True)

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
        print(f"<< {status} success={r.success} phase_reached={r.phase_reached} {r.duration_s:.0f}s: {r.message}")
        print(f"   parcel z now {self.parcel_z(colour):.3f} m; phase start times: " + ", ".join(f"{k}={v:.0f}s" for k, v in timeline.items()))
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("colour", choices=list(PARCELS))
    ap.add_argument("--from", dest="src", default="pick_table")
    ap.add_argument("--to", dest="dst", default="pick_table", help="where to put it down (default: back on the same table)")
    ap.add_argument("--only", choices=["pick", "place"], help="run one half only")
    a = ap.parse_args()
    rclpy.init()
    node = PhaseClient()
    ok = True
    try:
        for _ in range(20):                     # wait for object poses
            rclpy.spin_once(node, timeout_sec=0.2)
            if node.poses:
                break
        if a.only != "place":
            r = node.run(a.colour, "pick", a.src)
            ok = bool(r and r.success)
        if ok and a.only != "pick":
            r = node.run(a.colour, "place", a.dst)
            ok = bool(r and r.success)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
