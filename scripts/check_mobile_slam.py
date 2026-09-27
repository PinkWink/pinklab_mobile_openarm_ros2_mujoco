"""Wait for an observed SLAM map; ignore the initial empty map message."""

import json
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from rclpy.qos import QoSProfile, DurabilityPolicy


def main():
    rclpy.init()
    node = Node("mobile_slam_check")
    result = []
    node.create_subscription(
        OccupancyGrid,
        "/map",
        result.append,
        QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL),
    )
    deadline = time.monotonic() + 45
    report = {}
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if not result:
                continue
            msg = result[-1]
            known = sum(x >= 0 for x in msg.data)
            occupied = sum(x > 50 for x in msg.data)
            if known > 100 and occupied > 50:
                report = {
                    "frame": msg.header.frame_id,
                    "width": msg.info.width,
                    "height": msg.info.height,
                    "resolution": msg.info.resolution,
                    "known_cells": known,
                    "occupied_cells": occupied,
                }
                break
        assert report, "No observed SLAM map within 45 seconds"
        Path("artifacts/mobile_openarm_slam.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(json.dumps(report, indent=2))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
