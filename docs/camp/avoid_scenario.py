"""A walking worker meets the robot while Nav2 drives it east along the centre aisle (spawn (0, 0, 0) → (6.2, 0, 0)).

    ./scripts/mobile_openarm nav moveit:=false          # 터미널 1 (새로 띄운 직후, 로봇이 원점에 있을 때)
    python docs/camp/avoid_scenario.py                    # 터미널 2: crossing (기본)
    python docs/camp/avoid_scenario.py --mode headon      # 마주 오는 근로자

crossing: worker_helmet_orange walks across the aisle at x = 3.4, (3.4, 3.0) ↔ (3.4, -3.0)
headon:   worker_helmet_orange walks west down the aisle, (5.5, 0) ↔ (-5.5, 0)
Both use /warehouse/set_actor (teleport + set_path, 0.4 m/s), then NavigateToPose and print the closest robot-worker distance.
"""
import argparse
import math
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Point, PoseStamped
from nav2_msgs.action import NavigateToPose
from warehouse_interfaces.msg import ActorStateArray
from warehouse_interfaces.srv import SetActor

WORKER = "worker_helmet_orange"


class Scenario(Node):
    def __init__(self):
        super().__init__("avoid_scenario", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.actor = self.create_client(SetActor, "/warehouse/set_actor")
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.robot = self.worker = None
        self.closest = (float("inf"), 0.0)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)
        self.create_subscription(ActorStateArray, "/warehouse/actor_states", self.on_actors, 10)

    def on_truth(self, m):
        self.robot = (m.pose.position.x, m.pose.position.y)
        self.check()

    def on_actors(self, m):
        for a in m.actors:
            if a.name == WORKER:
                self.worker = (a.pose.position.x, a.pose.position.y)

    def check(self):
        if self.robot and self.worker:
            d = math.dist(self.robot, self.worker)
            if d < self.closest[0]:
                self.closest = (d, self.get_clock().now().nanoseconds * 1e-9)

    def call(self, **kw):
        req = SetActor.Request(name=WORKER, **kw)
        future = self.actor.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=5)
        r = future.result()
        print(f"set_actor {kw['operation']}: {r.success} {r.message}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["crossing", "headon"], default="crossing")
    ap.add_argument("--speed", type=float, default=0.4, help="worker speed (m/s)")
    a = ap.parse_args()
    rclpy.init()
    n = Scenario()
    n.actor.wait_for_service(timeout_sec=10)
    n.nav.wait_for_server(timeout_sec=30)
    pose = PoseStamped().pose
    route = {"crossing": [(3.4, 3.0), (3.4, -3.0)], "headon": [(5.5, 0.0), (-5.5, 0.0)]}[a.mode]
    pose.position.x, pose.position.y = route[0]
    n.call(operation="teleport", pose=pose)
    n.call(operation="set_path", waypoints=[Point(x=x, y=y) for x, y in route], speed=a.speed)
    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = "map"
    goal.pose.pose.position.x, goal.pose.pose.position.y = 6.2, 0.0
    goal.pose.pose.orientation.w = 1.0                                          # yaw = 0 (east, the spawn heading)
    start = time.monotonic()
    handle = n.nav.send_goal_async(goal)
    rclpy.spin_until_future_complete(n, handle, timeout_sec=10)
    print(f"goal (6.2, 0.0, 0) accepted: {handle.result().accepted}", flush=True)
    result = handle.result().get_result_async()
    while not result.done():
        rclpy.spin_once(n, timeout_sec=0.05)
    status = result.result().status
    print(f"NavigateToPose result: status={status} (SUCCEEDED={GoalStatus.STATUS_SUCCEEDED})  {time.monotonic() - start:.1f} s", flush=True)
    print(f"closest robot-worker distance: {n.closest[0]:.2f} m (centre to centre)", flush=True)
    n.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
