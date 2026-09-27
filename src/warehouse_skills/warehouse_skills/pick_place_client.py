"""CLI: ros2 run warehouse_skills pick_place red pick_table place_table [--arm left] [--phase pick|place]"""

import argparse
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from warehouse_interfaces.action import PickPlace


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("object", help="parcel name or colour (red/blue/yellow)")
    parser.add_argument("from_station", nargs="?", default="pick_table")
    parser.add_argument("to_station", nargs="?", default="place_table")
    parser.add_argument("--arm", default="", choices=["", "left", "right"])
    parser.add_argument("--phase", default="", choices=["", "all", "pick", "place"], help="pick: 집고 운반 자세까지, place: 든 물체 놓기")
    parser.add_argument("--timeout", type=float, default=600.0)
    options = parser.parse_args(args)
    rclpy.init()
    node = Node("pick_place_cli", parameter_overrides=[Parameter("use_sim_time", value=True)])
    client = ActionClient(node, PickPlace, "/pick_place")
    code = 1
    try:
        if not client.wait_for_server(timeout_sec=30):
            raise RuntimeError("/pick_place action server not available (start with moveit:=true)")
        goal = PickPlace.Goal(object=options.object, from_station=options.from_station,
                              to_station=options.to_station, arm=options.arm, phase=options.phase)
        last = {"text": ""}

        def on_feedback(msg):
            text = f"[{msg.feedback.phase} {msg.feedback.progress * 100:3.0f}%] {msg.feedback.detail}"
            if text != last["text"]:
                print(text, flush=True)
                last["text"] = text

        future = client.send_goal_async(goal, feedback_callback=on_feedback)
        rclpy.spin_until_future_complete(node, future, timeout_sec=10)
        handle = future.result()
        if handle is None or not handle.accepted:
            raise RuntimeError("goal rejected (another PickPlace running?)")
        result = handle.get_result_async()
        deadline = time.monotonic() + options.timeout
        while not result.done() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not result.done():
            handle.cancel_goal_async()
            raise RuntimeError("timed out; cancel requested")
        r = result.result()
        print(f"PickPlace status={r.status} (SUCCEEDED={GoalStatus.STATUS_SUCCEEDED}) success={r.result.success} "
              f"phase={r.result.phase_reached} {r.result.duration_s:.0f}s: {r.result.message}")
        code = 0 if r.result.success else 1
    finally:
        node.destroy_node()
        rclpy.shutdown()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
