"""Verify the Python camera callback in a running MoveIt simulation.

Start with camera_demo:handle_frames, camera_depth:=true, camera_fps:=2.
This check moves both arms to ready, verifies wrist-camera motion, then returns
them to transport. ROS is used only for clock/graph checks and arm commands.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import rclpy
from rosgraph_msgs.msg import Clock


def main():
    root = Path(os.environ["MOBILE_OPENARM_MODEL_DIR"]) / "cameras"
    rclpy.init()
    node = rclpy.create_node("direct_camera_checks")
    clock = []
    node.create_subscription(
        Clock,
        "/clock",
        lambda m: clock.append(m.clock.sec + m.clock.nanosec * 1e-9),
        10,
    )

    def fresh_frames(after=-1):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if (root / "frames.json").is_file():
                frames = json.loads((root / "frames.json").read_text())
                stamp = frames["base_camera"]["sim_time"]
                if clock and stamp > after and abs(clock[-1] - stamp) < 2:
                    return frames
        raise RuntimeError("No fresh direct Python camera frames")

    def arm(pose):
        subprocess.run(
            [
                sys.executable,
                "-m",
                "mobile_openarm_moveit_config.joint_goal",
                "both",
                pose,
            ],
            check=True,
            timeout=110,
        )

    try:
        before = fresh_frames()
        camera_topics = [
            name
            for name, kinds in node.get_topic_names_and_types()
            if set(kinds)
            & {
                "sensor_msgs/msg/Image",
                "sensor_msgs/msg/CompressedImage",
                "sensor_msgs/msg/CameraInfo",
            }
        ]
        assert not camera_topics, camera_topics
        report = {
            "ros_image_or_camera_info_topics": camera_topics,
            "viewer_and_python_callback": "running",
        }
        try:
            arm("ready")
            current = json.loads((root / "frames.json").read_text())["base_camera"][
                "sim_time"
            ]
            after = fresh_frames(current)
            distances = {}
            for name in before:
                a, b = (
                    np.array(before[name]["T_world_optical"]),
                    np.array(after[name]["T_world_optical"]),
                )
                distances[name] = float(np.linalg.norm(b[:3, 3] - a[:3, 3]))
                depth = np.load(root / (name + "_depth.npy"))
                assert depth.shape == (480, 640) and np.isfinite(depth).any()
            assert distances["left_wrist_camera"] > 0.05
            assert distances["right_wrist_camera"] > 0.05
            assert distances["base_camera"] < 0.02 and distances["head_camera"] < 0.02
            report["camera_displacement_m_after_ready"] = distances
            report["live_frame_sim_time"] = after["base_camera"]["sim_time"]
            report["observed_clock_time"] = clock[-1]
            report["four_matching_timestamps"] = (
                len({f["sim_time"] for f in after.values()}) == 1
            )
            assert report["four_matching_timestamps"]
        finally:
            arm("transport")
        report["passed"] = True
        Path("artifacts/mobile_openarm_camera_live.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
        print(json.dumps(report, indent=2))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
