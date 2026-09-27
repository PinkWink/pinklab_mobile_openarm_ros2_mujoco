#!/usr/bin/env python3
"""M4 예제 4: 텍스트 콘솔. 사용자가 입력한 문장을 Utterance(speaker=user) 로 발행하고, 로봇의 말(Utterance speaker=robot)을 받아 출력한다.

실행:
    ./scripts/mobile_openarm exec python examples/m4_command_dialog/04_text_console.py
    다른 터미널에서 확인:
    ./scripts/mobile_openarm exec ros2 topic echo /warehouse/utterance
    ./scripts/mobile_openarm exec ros2 topic pub -1 /warehouse/narration warehouse_interfaces/msg/Utterance "{speaker: robot, text: 빨간 상자를 옮겼습니다., language: ko}"

배우는 점:
- 사용자 입출력을 ROS 토픽으로 분리하면 대화 관리자(05)·실행기(03)·상황 서술(M3-08)이 콘솔과 무관하게 돌아간다.
  콘솔은 언제든 다른 UI(웹, 채팅 앱)로 바꿀 수 있다.
- 사용자 문장: /warehouse/utterance (speaker=user). 로봇 문장: /warehouse/narration (speaker=robot). 둘 다 warehouse_interfaces/Utterance.
- 입력은 stdin 을 별도 스레드에서 읽는다. rclpy 스핀을 막지 않기 위해서다.
"""

import sys
import threading

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from warehouse_interfaces.msg import Utterance


class TextConsole(Node):
    def __init__(self):
        super().__init__("m4_text_console", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.pub = self.create_publisher(Utterance, "/warehouse/utterance", 10)
        self.create_subscription(Utterance, "/warehouse/narration", self.on_robot, 10)
        threading.Thread(target=self.read_stdin, daemon=True).start()
        print("문장을 입력하면 /warehouse/utterance 로 나간다. 빈 줄로 종료.", flush=True)

    def on_robot(self, msg):
        if msg.speaker == "robot":
            print(f"\n[robot] {msg.text}\n[user] ", end="", flush=True)

    def read_stdin(self):
        while True:
            line = sys.stdin.readline()
            if not line or not line.strip():
                rclpy.shutdown()
                return
            msg = Utterance()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.speaker, msg.text, msg.language = "user", line.strip(), "ko"
            self.pub.publish(msg)
            print("[user] ", end="", flush=True)


def main():
    rclpy.init()
    node = TextConsole()
    print("[user] ", end="", flush=True)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass


if __name__ == "__main__":
    main()
