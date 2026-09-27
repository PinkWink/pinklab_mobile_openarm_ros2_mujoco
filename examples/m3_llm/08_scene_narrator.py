#!/usr/bin/env python3
"""M3 예제 8: 세계 상태(검출·로봇 위치·장소 이름)를 JSON 으로 만들어 LLM 에 보내고 한국어 상황 설명을 발행한다.

실행 (카메라 검출기가 /vision/detections 를 내고 있어야 한다):
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \\
        ./scripts/mobile_openarm start viewer:=false camera_depth:=true
    ./scripts/mobile_openarm exec python examples/m3_llm/08_scene_narrator.py [--every 8] [--duration 60]
    ./scripts/mobile_openarm exec ros2 topic echo /warehouse/narration

배우는 점:
- LLM 에는 영상이 아니라 "정리된 상태"를 준다: 검출 요약(클래스별 개수, 사람 속성, 상자 색), 로봇의 map 좌표와 가장 가까운 장소 이름,
  현재 시각. 토큰이 적고 결정적이며, 무엇을 근거로 말했는지 남는다.
- 상태가 바뀌었을 때만 호출한다(같은 상태면 재사용). 주기 호출은 비용·지연을 낳는다.
- 출력은 Utterance(speaker=robot) 로 발행한다. M4 의 텍스트 콘솔이 이 토픽을 읽어 보여 준다.
- 규칙: 보이는 것만 말한다, 없는 것을 지어내지 않는다, 안전모 미착용은 반드시 언급한다 — system prompt 에 넣는다.
"""

import argparse
import json
import math
import time
from collections import Counter

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from tf2_ros import Buffer, TransformListener, TransformException
from warehouse_interfaces.msg import Detection3DArray, Utterance
from warehouse_lecture.llm.client import LLM
from warehouse_lecture.memory.locations import Locations

SYSTEM = ("너는 창고 순찰 로봇 '핑키'다. 아래 JSON 은 네 카메라가 지금 보는 것과 네 위치다. 이를 근거로 현장 관리자에게 두세 문장의 한국어 상황 보고를 한다. "
          "규칙: JSON 에 있는 것만 말한다. 없는 것을 지어내지 않는다. 안전모를 쓰지 않은 사람이 있으면 반드시 먼저 말한다. 숫자와 장소 이름을 그대로 쓴다. 존댓말.")


class Narrator(Node):
    def __init__(self, every):
        super().__init__("m3_scene_narrator", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.every = every
        self.latest = None
        self.create_subscription(Detection3DArray, "/vision/detections", lambda m: setattr(self, "latest", m), 10)
        self.pub = self.create_publisher(Utterance, "/warehouse/narration", 10)
        self.tf_buffer = Buffer(); self.tf_listener = TransformListener(self.tf_buffer, self)
        self.locations = Locations()
        self.llm = LLM()
        self.last_state = None
        self.last_call = -1e9
        self.create_timer(1.0, self.tick)

    def robot_place(self):
        try:
            t = self.tf_buffer.lookup_transform("map", "base_footprint", rclpy.time.Time())
        except TransformException:
            return None
        x, y = t.transform.translation.x, t.transform.translation.y
        q = t.transform.rotation
        name, dist = self.locations.nearest(x, y)
        return {"x": round(x, 2), "y": round(y, 2), "yaw_deg": round(math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))),
                "nearest_place": self.place_name(name), "place_distance_m": round(dist, 2)}

    def place_name(self, key):
        """LLM 에는 한국어 이름을 준다 (locations.yaml 의 첫 별칭). 키를 주면 모델이 제멋대로 번역한다."""
        loc = self.locations.locations.get(key or "", {})
        return (loc.get("aliases") or [key or "알 수 없음"])[0]

    def world_state(self):
        """검출 메시지 -> LLM 에 줄 JSON. 두 카메라가 같은 물체를 보면(map 위치 0.5 m 이내) 하나로 센다."""
        det = self.latest
        seen = []          # (label, x, y) 중복 제거용
        objects = Counter()
        people, parcels = [], {}
        for d in det.detections:
            if d.label in ("helmet", "safety_vest"):
                continue
            if d.has_position:
                x, y = d.position.point.x, d.position.point.y
                if any(l == d.label and math.hypot(x - sx, y - sy) < 0.5 for l, sx, sy in seen):
                    continue
                seen.append((d.label, x, y))
            if d.label == "person":
                attrs = {kv.key: kv.value for kv in d.attributes}
                entry = {"helmet": attrs.get("helmet") == "true", "vest": attrs.get("vest", "none")}
                if d.has_position:
                    place, dist = self.locations.nearest(x, y)
                    entry["near"] = self.place_name(place)
                    entry["xy"] = [round(x, 1), round(y, 1)]
                people.append(entry)
            elif d.label.startswith("parcel_"):
                parcels[d.label[7:]] = [round(x, 2), round(y, 2)] if d.has_position else "seen"
            else:
                objects[d.label] += 1
        return {"sim_time_s": round(det.header.stamp.sec + det.header.stamp.nanosec * 1e-9, 1), "robot": self.robot_place(),
                "people": people, "parcels_on_table": parcels, "other_objects": dict(objects)}

    @staticmethod
    def signature(state):
        return json.dumps({"people": sorted((p["helmet"], p["vest"], p.get("near")) for p in state["people"]),
                           "parcels": sorted(state["parcels_on_table"]), "objects": state["other_objects"],
                           "place": state["robot"] and state["robot"]["nearest_place"]}, sort_keys=True, ensure_ascii=False)

    def tick(self):
        if self.latest is None:
            return
        state = self.world_state()
        if state["robot"] is None:
            return
        sig = self.signature(state)
        now = time.monotonic()
        if sig == self.last_state or now - self.last_call < self.every:
            return
        self.last_state, self.last_call = sig, now
        text = self.llm.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(state, ensure_ascii=False)}],
                             temperature=0.4, max_tokens=200, purpose="narration")
        msg = Utterance(); msg.header.stamp = self.get_clock().now().to_msg(); msg.speaker, msg.text, msg.language = "robot", text, "ko"
        self.pub.publish(msg)
        self.get_logger().info(f"상태: {json.dumps(state, ensure_ascii=False)[:300]}")
        self.get_logger().info(f"보고: {text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=float, default=8.0, help="호출 최소 간격(초)")
    ap.add_argument("--duration", type=float, default=0.0)
    a = ap.parse_args()
    rclpy.init()
    node = Narrator(a.every)
    end = time.monotonic() + a.duration if a.duration > 0 else None
    try:
        while rclpy.ok() and (end is None or time.monotonic() < end):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info(f"세션 비용 ${node.llm.session_cost:.4f}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
