#!/usr/bin/env python3
"""M1 예제 2: /scan 과 /odom 을 구독해 최근접 장애물과 로봇 상태를 읽고, 사람이 다가오면 경고를 발행한다.

실행 (시뮬레이터가 떠 있는 상태에서):
    ./scripts/mobile_openarm exec python examples/m1_ros_vision/02_scan_odom_subscriber.py
    옵션: --duration 30 (초, 0이면 Ctrl+C까지)  --warn-distance 1.5 (m)  --rate 1.0 (출력 Hz)

배우는 점:
- 센서 토픽은 sensor_data QoS(best effort)로 구독한다. 늦은 프레임은 버리는 편이 낫기 때문이다.
- /scan 은 laser_link 기준 극좌표다. index -> 각도 = angle_min + i * angle_increment.
  laser_link 는 base_link 기준 yaw 180° 로 장착돼 있어(실제 Pinky 라이다와 같음) 로봇 기준 방위로 바꾸려면
  tf 로 base_link -> laser_link 회전을 조회해 더해야 한다. 센서 프레임과 로봇 프레임을 구분하는 습관을 들인다.
- /odom 은 odom 프레임(바퀴 적분, 드리프트 있음). map 좌표는 tf2로 map -> base_footprint 를 조회한다.
- /warehouse/actor_states 는 시뮬레이터의 정답(ground truth)이다. 뒤 모듈에서는 이 값을 카메라 검출로 대체한다.
- 경고는 std_msgs/String 으로 /warehouse/alerts 에 발행한다. 다른 터미널에서
    ./scripts/mobile_openarm exec ros2 topic echo /warehouse/alerts
"""

import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener, TransformException
from warehouse_interfaces.msg import ActorStateArray

SECTORS = [(-45, 45, "앞"), (45, 135, "왼쪽"), (-135, -45, "오른쪽")]  # 나머지는 뒤


def sector_name(deg):
    for lo, hi, name in SECTORS:
        if lo <= deg < hi:
            return name
    return "뒤"


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class ScanOdomWatcher(Node):
    def __init__(self, warn_distance, rate):
        # /clock 이 있으므로 use_sim_time=True. 그래야 스탬프·tf 시간이 시뮬레이터와 맞는다.
        super().__init__("m1_scan_odom", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.warn_distance = warn_distance
        self.scan = None
        self.odom = None
        self.actors = None
        self.person_last = {}  # name -> (sim_time, distance) 접근 속도 계산용
        self.create_subscription(LaserScan, "/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(Odometry, "/odom", self.on_odom, qos_profile_sensor_data)
        self.create_subscription(ActorStateArray, "/warehouse/actor_states", self.on_actors, 10)
        self.alerts = self.create_publisher(String, "/warehouse/alerts", 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.create_timer(1.0 / rate, self.report)
        self.counts = {"scan": 0, "odom": 0, "actors": 0}
        self.laser_yaw = None  # base_link 기준 laser_link 의 yaw (tf 에서 한 번 조회)

    # --- 콜백은 저장만 한다. 계산과 출력은 타이머에서 --------------------------------
    def on_scan(self, msg):
        self.scan, self.counts["scan"] = msg, self.counts["scan"] + 1

    def on_odom(self, msg):
        self.odom, self.counts["odom"] = msg, self.counts["odom"] + 1

    def on_actors(self, msg):
        self.actors, self.counts["actors"] = msg, self.counts["actors"] + 1

    # --- 계산 ---------------------------------------------------------------------
    def laser_yaw_offset(self):
        if self.laser_yaw is None:
            try:
                t = self.tf_buffer.lookup_transform("base_link", "laser_link", rclpy.time.Time())
                self.laser_yaw = yaw_of(t.transform.rotation)
                self.get_logger().info(f"laser_link 는 base_link 기준 yaw {math.degrees(self.laser_yaw):+.0f}° 로 장착")
            except TransformException:
                return 0.0
        return self.laser_yaw

    def nearest_obstacle(self):
        """(거리 m, 로봇 기준 방위 deg, 구역). 유효 범위 밖(inf, < range_min)은 무시."""
        s = self.scan
        best = None
        for i, r in enumerate(s.ranges):
            if s.range_min <= r <= s.range_max and (best is None or r < best[0]):
                best = (r, i)
        if best is None:
            return None
        deg = math.degrees(s.angle_min + best[1] * s.angle_increment + self.laser_yaw_offset())
        deg = (deg + 180) % 360 - 180
        return best[0], deg, sector_name(deg)

    def map_pose(self):
        """map -> base_footprint (x, y, yaw). AMCL 이 아직 없으면 None."""
        try:
            t = self.tf_buffer.lookup_transform("map", "base_footprint", rclpy.time.Time())
        except TransformException:
            return None
        p, q = t.transform.translation, t.transform.rotation
        return p.x, p.y, yaw_of(q)

    def nearest_person(self, robot_xy):
        """가장 가까운 사람: (name, 거리, 접근 속도 m/s (+면 다가옴), 속성 dict)."""
        now = self.get_clock().now().nanoseconds * 1e-9
        best = None
        for a in self.actors.actors:
            if a.kind != "person":
                continue
            d = math.hypot(a.pose.position.x - robot_xy[0], a.pose.position.y - robot_xy[1])
            closing = 0.0
            if a.name in self.person_last:
                t0, d0 = self.person_last[a.name]
                if now > t0:
                    closing = (d0 - d) / (now - t0)
            self.person_last[a.name] = (now, d)
            if best is None or d < best[1]:
                best = (a.name, d, closing, {kv.key: kv.value for kv in a.attributes})
        return best

    # --- 주기 출력 ----------------------------------------------------------------
    def report(self):
        if self.scan is None or self.odom is None:
            self.get_logger().info(f"대기 중: scan={self.counts['scan']} odom={self.counts['odom']} 메시지")
            return
        lines = []
        obs = self.nearest_obstacle()
        if obs:
            lines.append(f"최근접 장애물 {obs[0]:.2f} m, 방위 {obs[1]:+.0f}° ({obs[2]})")
        p, v = self.odom.pose.pose, self.odom.twist.twist
        lines.append(f"odom ({p.position.x:+.2f}, {p.position.y:+.2f}, {math.degrees(yaw_of(p.orientation)):+.0f}°) "
                     f"속도 {v.linear.x:+.2f} m/s, 회전 {math.degrees(v.angular.z):+.0f} °/s")
        mp = self.map_pose()
        if mp:
            lines.append(f"map  ({mp[0]:+.2f}, {mp[1]:+.2f}, {math.degrees(mp[2]):+.0f}°)  <- tf map->base_footprint")
        if self.actors is not None and mp:
            person = self.nearest_person(mp[:2])
            if person:
                name, d, closing, attr = person
                helmet = "안전모 " + ("착용" if attr.get("helmet") == "true" else "미착용")
                lines.append(f"가장 가까운 사람 {name} {d:.2f} m, 접근 속도 {closing:+.2f} m/s, {helmet}")
                if d < self.warn_distance and closing > 0.05:
                    text = f"경고: {name}({helmet})이 {d:.2f} m 에서 {closing:.2f} m/s 로 접근"
                    self.alerts.publish(String(data=text))
                    self.get_logger().warn(text)
        self.get_logger().info(" | ".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=0.0, help="초. 0이면 Ctrl+C 까지")
    parser.add_argument("--warn-distance", type=float, default=1.5)
    parser.add_argument("--rate", type=float, default=1.0)
    options = parser.parse_args()
    rclpy.init()
    node = ScanOdomWatcher(options.warn_distance, options.rate)
    end = time.monotonic() + options.duration if options.duration > 0 else None
    try:
        while rclpy.ok() and (end is None or time.monotonic() < end):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(f"수신: scan={node.counts['scan']} odom={node.counts['odom']} actors={node.counts['actors']}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
