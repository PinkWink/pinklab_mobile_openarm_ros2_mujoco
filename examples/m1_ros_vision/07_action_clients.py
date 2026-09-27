#!/usr/bin/env python3
"""M1 예제 7: Nav2 NavigateToPose 와 PickPlace 액션을 Python 에서 호출하고 피드백·결과·취소를 다룬다.

실행 (기본 파이프라인으로 띄운 시뮬레이터: ./scripts/mobile_openarm start viewer:=false):
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/07_action_clients.py nav pick_table      # 장소 이름
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/07_action_clients.py nav 1.2 -3.6 0      # 좌표
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/07_action_clients.py nav place_table --cancel-after 5
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/07_action_clients.py pick red pick_table place_table
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/07_action_clients.py tour   # 이동 -> 운반 -> 복귀

배우는 점:
- 액션 = 목표(goal) + 피드백 스트림 + 결과 + 취소. 토픽/서비스와 달리 오래 걸리는 일을 위한 인터페이스다.
- 흐름: wait_for_server -> send_goal_async -> (accepted?) -> get_result_async, 중간에 feedback_callback.
- use_sim_time=True 로 /clock 을 따라야 goal 의 stamp 와 tf 가 시뮬레이터와 맞는다.
- Ctrl+C 나 --cancel-after 로 cancel_goal_async 를 보내면 서버가 정리하고 CANCELED 상태로 끝난다.
- 장소 이름 -> 좌표는 warehouse_lecture/worlds/locations.yaml (M4 에서 LLM 이 이 이름을 쓴다).
"""

import argparse
import math
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose
from warehouse_interfaces.action import PickPlace
from warehouse_lecture.memory.locations import Locations

STATUS = {v: k[7:] for k, v in vars(GoalStatus).items() if k.startswith("STATUS_")}


class ActionDemo(Node):
    def __init__(self):
        super().__init__("m1_action_clients", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.pick = ActionClient(self, PickPlace, "/pick_place")
        self.locations = Locations()
        deadline = time.monotonic() + 5
        while self.get_clock().now().nanoseconds == 0 and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)   # /clock 첫 메시지를 기다린다
        if self.get_clock().now().nanoseconds == 0:
            raise RuntimeError("/clock 이 없다. 시뮬레이터가 떠 있는지 확인")

    # --- 공통 실행기 -------------------------------------------------------------
    def run_goal(self, client, goal, on_feedback, cancel_after=None, timeout=600.0):
        """goal 을 보내고 결과를 기다린다. (status, result) 를 돌려준다."""
        if not client.wait_for_server(timeout_sec=20.0):
            raise RuntimeError(f"{client._action_name} 서버가 없다")
        future = client.send_goal_async(goal, feedback_callback=on_feedback)
        rclpy.spin_until_future_complete(self, future, timeout_sec=10.0)
        handle = future.result()
        if handle is None or not handle.accepted:
            raise RuntimeError("goal 이 거부됐다 (서버가 바쁘거나 인자가 틀림)")
        self.get_logger().info(f"goal 수락: {handle.goal_id.uuid[:4].tolist()}...")
        result_future = handle.get_result_async()
        started = time.monotonic()
        cancelled = False
        try:
            while not result_future.done():
                rclpy.spin_once(self, timeout_sec=0.1)
                if cancel_after is not None and not cancelled and time.monotonic() - started > cancel_after:
                    self.get_logger().warn(f"{cancel_after:.0f}초 경과: 취소 요청")
                    handle.cancel_goal_async(); cancelled = True
                if time.monotonic() - started > timeout:
                    handle.cancel_goal_async(); cancelled = True
                    raise RuntimeError("시간 초과, 취소 요청")
        except KeyboardInterrupt:
            self.get_logger().warn("Ctrl+C: 취소 요청 후 결과를 기다린다")
            handle.cancel_goal_async()
            rclpy.spin_until_future_complete(self, result_future, timeout_sec=15.0)
        status = result_future.result().status if result_future.done() else GoalStatus.STATUS_UNKNOWN
        return status, (result_future.result().result if result_future.done() else None)

    # --- Nav2 -----------------------------------------------------------------------
    def navigate(self, x, y, yaw=0.0, cancel_after=None):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        last = {"d": None}

        def on_feedback(msg):
            f = msg.feedback
            if last["d"] is None or abs(f.distance_remaining - last["d"]) >= 0.25:
                last["d"] = f.distance_remaining
                self.get_logger().info(f"  Nav2: 남은 거리 {f.distance_remaining:.2f} m, 경과 {f.navigation_time.sec}s, "
                                       f"복구 {f.number_of_recoveries}회")

        self.get_logger().info(f"Nav2 -> ({x:.2f}, {y:.2f}, {math.degrees(yaw):.0f}°)")
        t0 = time.monotonic()
        status, _ = self.run_goal(self.nav, goal, on_feedback, cancel_after, timeout=180.0)
        self.get_logger().info(f"Nav2 결과: {STATUS.get(status, status)} ({time.monotonic() - t0:.0f}s)")
        return status == GoalStatus.STATUS_SUCCEEDED

    def navigate_named(self, name, cancel_after=None):
        key = self.locations.resolve(name)
        if key is None:
            raise SystemExit(f"모르는 장소 {name!r}. 가능: {', '.join(self.locations.names())}")
        x, y, yaw = self.locations.goal(key)
        self.get_logger().info(f"장소 '{name}' -> {key} base_goal {[x, y, yaw]}")
        return self.navigate(x, y, yaw, cancel_after)

    # --- PickPlace -----------------------------------------------------------------
    def pick_place(self, obj, src, dst, arm="", cancel_after=None):
        goal = PickPlace.Goal(object=obj, from_station=src, to_station=dst, arm=arm)
        last = {"text": ""}

        def on_feedback(msg):
            f = msg.feedback
            text = f"  [{f.phase} {f.progress * 100:3.0f}%] {f.detail}"
            if text != last["text"]:
                last["text"] = text
                self.get_logger().info(text)

        self.get_logger().info(f"PickPlace {obj}: {src} -> {dst}")
        status, result = self.run_goal(self.pick, goal, on_feedback, cancel_after, timeout=900.0)
        if result is not None:
            self.get_logger().info(f"PickPlace 결과: {STATUS.get(status, status)} success={result.success} "
                                   f"phase={result.phase_reached} {result.duration_s:.0f}s: {result.message}")
        return status == GoalStatus.STATUS_SUCCEEDED and result is not None and result.success


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("nav"); p.add_argument("target", nargs="+", help="장소 이름 또는 x y [yaw]"); p.add_argument("--cancel-after", type=float)
    p = sub.add_parser("pick"); p.add_argument("object"); p.add_argument("from_station", nargs="?", default="pick_table")
    p.add_argument("to_station", nargs="?", default="place_table"); p.add_argument("--arm", default="", choices=["", "left", "right"])
    p.add_argument("--cancel-after", type=float)
    p = sub.add_parser("tour"); p.add_argument("object", nargs="?", default="red")
    options = parser.parse_args()
    rclpy.init()
    ok = False
    node = ActionDemo()
    try:
        if options.cmd == "nav":
            if len(options.target) == 1 and not options.target[0].lstrip("-").replace(".", "").isdigit():
                ok = node.navigate_named(options.target[0], options.cancel_after)
            else:
                nums = [float(v) for v in options.target]
                ok = node.navigate(nums[0], nums[1], nums[2] if len(nums) > 2 else 0.0, options.cancel_after)
        elif options.cmd == "pick":
            ok = node.pick_place(options.object, options.from_station, options.to_station, options.arm, options.cancel_after)
        elif options.cmd == "tour":
            ok = (node.navigate_named("pick_table")            # 1) 픽업 작업대 앞으로
                  and node.pick_place(options.object, "pick_table", "place_table")   # 2) 운반 (스킬이 다시 도킹한다)
                  and node.navigate(0.0, 0.0, 0.0))              # 3) 출발점 복귀
            node.get_logger().info(f"tour {'성공' if ok else '실패'}")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
