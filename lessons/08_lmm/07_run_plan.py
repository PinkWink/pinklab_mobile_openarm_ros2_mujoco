#!/usr/bin/env python3
"""Lesson 08-7: send a RobotPlan to the Task Manager (/execute_plan) and watch every step.

    # terminal 1: simulator with the camera detectors (as in lesson 07)
    H=warehouse_lecture.vision
    LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start camera_depth:=true locate:=vision viewer:=true rviz:=false
    # terminal 2: Task Manager (serves /execute_plan and /execute_command)
    ./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
    # terminal 3:
    ./scripts/mobile_openarm exec python lessons/08_lmm/07_run_plan.py navigate:rack_c report
    ./scripts/mobile_openarm exec python lessons/08_lmm/07_run_plan.py navigate:pick_table detect:parcel_red pick:parcel_red@pick_table navigate:place_table place:@place_table
    ./scripts/mobile_openarm exec python lessons/08_lmm/07_run_plan.py --nl "노란 상자 적재대로"

The Task Manager runs the steps in order and publishes (step, total, action, phase, detail) feedback. If a step fails it
stops there and the result says how many steps were done (steps_done, failed_step) and what is still held (spoken).
"""
import argparse
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from warehouse_interfaces.action import ExecutePlan
from warehouse_lecture.commands.plan import PlanStep, RobotPlan


def build(items):
    """'navigate:rack_c' 'detect:parcel_red' 'pick:parcel_red@pick_table' 'place:@place_table' 'report' -> RobotPlan."""
    steps = []
    for item in items:
        action, _, rest = item.partition(":")
        target, _, location = rest.partition("@")
        if action == "navigate" and target and not location:
            target, location = "", target
        steps.append(PlanStep(action=action, target=target, location=location))
    return RobotPlan(summary=" > ".join(items), steps=steps)


class PlanClient(Node):
    def __init__(self):
        super().__init__("lesson08_plan_client", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.client = ActionClient(self, ExecutePlan, "/execute_plan")

    def run(self, plan, utterance="", timeout=1800.0):
        if not self.client.wait_for_server(timeout_sec=15.0):
            raise SystemExit("/execute_plan not available: ./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager")
        print(">> plan:\n   " + plan.describe().replace("\n", "\n   "), flush=True)
        t0 = time.monotonic()
        last = [""]

        def on_fb(m):
            f = m.feedback
            text = f"   [{time.monotonic() - t0:5.1f}s {f.step + 1}/{f.total} {f.action}/{f.phase}] {f.detail}"
            if text[10:] != last[0] and "visual dock" not in f.detail:
                last[0] = text[10:]
                print(text, flush=True)

        future = self.client.send_goal_async(plan.to_msg(utterance=utterance), feedback_callback=on_fb)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10)
        handle = future.result()
        if handle is None or not handle.accepted:
            print("   rejected (another plan running?)")
            return None
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result, timeout_sec=timeout)
        if not result.done():
            handle.cancel_goal_async()
            print("   timeout")
            return None
        r = result.result().result
        status = {v: k[7:] for k, v in vars(GoalStatus).items() if k.startswith("STATUS_")}[result.result().status]
        print(f"<< {status} success={r.success} steps_done={r.steps_done}/{len(plan.steps)} failed_step={r.failed_step} "
              f"({time.monotonic() - t0:.0f} s)")
        print(f"   spoken: {r.spoken}")
        return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("steps", nargs="*", help="action[:target][@location] ...")
    ap.add_argument("--nl", help="plan a Korean instruction with the LLM first")
    a = ap.parse_args()
    if a.nl:
        from warehouse_lecture.commands.plan_parser import PlanParser
        plan = PlanParser().parse(a.nl)
    elif a.steps:
        plan = build(a.steps)
    else:
        ap.error("give steps or --nl")
    problems = plan.validate_world()
    if problems or not plan.steps:
        print("not executable:", "; ".join(problems) or plan.reply)
        sys.exit(1)
    rclpy.init()
    node = PlanClient()
    try:
        r = node.run(plan, utterance=a.nl or "")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0 if r is not None and r.success else 1)


if __name__ == "__main__":
    main()
