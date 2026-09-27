#!/usr/bin/env python3
"""M1 예제 5: 검출 박스의 픽셀 + 깊이 -> 카메라 optical 좌표 -> tf2 로 map 좌표 -> Marker 발행. 정답과 오차 비교.

실행 (04번 검출기를 그대로 쓰므로 두 핸들러를 함께 얹는다. 깊이 필요):
    LECTURE_HANDLERS="examples/m1_ros_vision/04_color_detect_parcels.py:ColorParcelDetector,examples/m1_ros_vision/05_pixel_to_map.py:PixelToMap" \\
        ./scripts/mobile_openarm start viewer:=false camera_depth:=true
    다른 터미널:
    ./scripts/mobile_openarm goal 1.2 -3.6 0
    ./scripts/mobile_openarm exec ros2 topic echo /vision/parcel_markers      # RViz: MarkerArray, map 프레임
  옵션: M1_CAMERA=head_camera

배우는 점:
- 역투영: p_optical = z * K^-1 [u v 1]^T. z 는 depth_m[v, u] (박스 중앙 영역의 중앙값이 안정적).
  깊이는 카메라에 보이는 '앞면'까지의 거리다. 물체 중심을 원하면 광선 방향으로 물체 두께의 절반을 더한다.
- 픽셀에서 map 으로 가는 길은 둘이다.
    (a) frame.T_world_optical: 시뮬레이터 정답 자세. 실제 로봇엔 없다.
    (b) tf2: <camera>_optical_frame -> map. 실제 로봇이 쓰는 길이고 AMCL 오차가 포함된다.
  tf 조회 시각은 반드시 프레임의 시뮬레이션 시간(stamp)이어야 한다. "지금"으로 조회하면 로봇이 움직일 때 어긋난다.
- 그런데 그 시각의 TF 는 같은 틱 안에서는 아직 버퍼에 없다(다른 노드가 보낸 /tf 는 다음 틱에 도착한다).
  그래서 검출 결과와 stamp 를 보관해 두고 다음 호출(0.5 s 뒤)에 변환한다. 실제 로봇에서도 같은 패턴을 쓴다.
- 3D 로 가면 색 검출의 한계가 풀린다. 안전모는 z≈1.6 m, 상자는 z≈0.81 m 이므로 높이로 걸러낸다.
- 검증 기준: 상자 map 좌표 오차 < 5 cm (정답은 시뮬레이터 물리 상태. /warehouse/object_poses 도 같은 값).
"""

import importlib.util
import os
from pathlib import Path

import numpy as np
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray
from mobile_openarm_mujoco.bridge import stamp as sim_stamp
from warehouse_lecture.ros.geometry import MapTransformer, median_depth, optical_to_world, pixel_to_optical


def load_sibling(stem):
    """같은 폴더의 번호 붙은 예제 파일을 모듈로 읽는다 (파일명이 숫자로 시작해 import 문을 못 쓴다)."""
    path = Path(__file__).with_name(stem + ".py")
    spec = importlib.util.spec_from_file_location(stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect_parcels = load_sibling("04_color_detect_parcels").detect_parcels

TABLE_Z = (0.70, 0.95)   # 이 높이 범위(m) 밖의 검출은 상자가 아니다 (안전모, 선반 상자 제거)
PARCEL_HALF_DEPTH = 0.0225  # 상자 4.5 cm 의 절반. 깊이는 앞면까지라서 중심은 이만큼 더 멀다
COLORS = {"parcel_red": (1.0, 0.2, 0.2), "parcel_blue": (0.2, 0.5, 1.0), "parcel_yellow": (1.0, 0.9, 0.1)}
TRUTH_LABEL = {"parcel_1": "parcel_red", "parcel_2": "parcel_blue", "parcel_3": "parcel_yellow"}


class PixelToMap:
    def __init__(self):
        self.camera = os.environ.get("M1_CAMERA", "head_camera")
        self.last_report = None
        self.pending = None  # (frame, found) 직전 호출의 검출. TF 가 도착한 뒤 변환한다

    def setup(self, context):
        self.context = context
        self.node = context.node
        if not context.pump.depth:
            raise ValueError("깊이가 필요하다: camera_depth:=true 로 시뮬레이터를 띄운다")
        self.tf = MapTransformer(self.node, target="map")
        self.pub = self.node.create_publisher(MarkerArray, "/vision/parcel_markers", 10)
        self.node.get_logger().info(f"[05] {self.camera} 픽셀+깊이 -> map, Marker -> /vision/parcel_markers")

    def truth_positions(self):
        """시뮬레이터 물리 상태에서 상자의 실제 world 위치 (map 원점 = world 원점)."""
        d, m = self.context.physics.data, self.context.physics.model
        return {TRUTH_LABEL[o["name"]]: np.array(d.body(o["name"]).xpos) for o in self.context.world["objects"]
                if o["name"] in TRUTH_LABEL}

    def __call__(self, frames):
        # 1) 이번 프레임은 검출만 하고 보관한다. 2) 직전 프레임을 그 프레임의 stamp 로 map 에 변환한다.
        current = frames[self.camera]
        pending, self.pending = self.pending, (current, detect_parcels(current.rgb))
        if pending is None:
            return
        frame, found = pending
        stamp = sim_stamp(frame.sim_time)
        markers, rows = MarkerArray(), []
        for i, (label, box, score) in enumerate(found):
            z = median_depth(frame, box)
            if z is None:
                continue
            u, v = (box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0
            p_opt = pixel_to_optical(frame, u, v, z)
            p_opt = p_opt * (1.0 + PARCEL_HALF_DEPTH / np.linalg.norm(p_opt))   # 광선을 따라 중심까지 연장
            p_world = optical_to_world(frame, p_opt)               # (a) 시뮬레이터 정답 자세
            p_map = self.tf.to_map(frame, p_opt, stamp)             # (b) tf2, 실제 로봇의 길
            if p_map is None:
                continue
            on_table = TABLE_Z[0] <= p_map[2] <= TABLE_Z[1]
            rows.append((label, z, p_world, p_map, on_table))
            if not on_table:
                continue
            markers.markers.append(self.marker(i, label, p_map, stamp))
        self.pub.publish(markers)

        if self.last_report is None or frame.sim_time - self.last_report >= 1.0:
            self.last_report = frame.sim_time
            truth = self.truth_positions()
            log = self.node.get_logger()
            log.info(f"[05] t={frame.sim_time:.1f} 후보 {len(rows)}개, 작업대 높이 통과 {len(markers.markers)}개")
            for label, z, pw, pm, ok in rows:
                # 오차를 둘로 나눠 본다: (a) 정답 자세 경로 = 순수 비전(픽셀·깊이) 오차, (b) tf 경로 = 비전 + AMCL 위치 오차
                err_vision = np.linalg.norm(pw[:2] - truth[label][:2]) if label in truth else float("nan")
                err_tf = np.linalg.norm(pm[:2] - truth[label][:2]) if label in truth else float("nan")
                log.info(f"[05]   {label:13s} depth {z:.2f} m  map ({pm[0]:+.2f}, {pm[1]:+.2f}, {pm[2]:.2f})  "
                         f"오차 비전 {err_vision * 100:4.1f} cm / tf(비전+AMCL) {err_tf * 100:4.1f} cm  "
                         f"{'상자' if ok else '높이 탈락(안전모/선반)'}")

    def marker(self, i, label, p, stamp):
        m = Marker()
        m.header.frame_id, m.header.stamp = "map", stamp
        m.ns, m.id, m.type, m.action = "parcels", i, Marker.SPHERE, Marker.ADD
        m.pose.position = Point(x=float(p[0]), y=float(p[1]), z=float(p[2]))
        m.pose.orientation.w = 1.0
        m.scale.x = m.scale.y = m.scale.z = 0.06
        r, g, b = COLORS[label]
        m.color = ColorRGBA(r=r, g=g, b=b, a=0.9)
        m.lifetime.sec = 1
        m.text = label
        return m
