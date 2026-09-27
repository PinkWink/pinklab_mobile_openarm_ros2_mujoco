#!/usr/bin/env python3
"""M2 예제 2: 배우 위치·속성, 상자 위치, 조명, 로봇 시점을 무작위로 바꾸며 데이터셋을 자동 수집한다.

실행:
    M2_MAX=3000 ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m2_yolo/02_domain_randomization.py:RandomizedCapture \\
        camera_segmentation:=true camera_size:=640x480 camera_fps:=4
  (수집 중 로봇을 순간이동시키므로 AMCL 이 틀어진다. 수집이 끝나면 시뮬레이터를 다시 띄운다.)
  옵션: M2_SEED=0  M2_EVERY=1 (몇 프레임마다 랜덤화)  01번의 M2_DATASET/M2_MAX

배우는 점 (도메인 랜덤화):
- 시뮬레이터 정답 라벨은 공짜지만 다양성이 없다. 위치·자세·조명·외형을 흔들어 분포를 넓혀야 실제(또는 다른 시점)에서 견딘다.
- 여기서는 핸들러가 같은 프로세스라서 ActorAnimator/MuJoCo 모델을 직접 만진다. 다른 프로세스에서는
  /warehouse/set_actor 서비스(teleport, set_attributes, set_path)로 같은 일을 한다.
- 안전모 유무를 50:50 으로 맞춰야 M3·M5 의 "안전모 안 쓴 사람" 질의가 편향되지 않는다.
- 로봇 순간이동은 freejoint qpos 를 직접 쓴다(데이터 수집 전용). 벽·랙과 겹치지 않는 통로 좌표만 쓴다.
"""

import importlib.util
import math
import os
import random
from pathlib import Path

import numpy as np


def load_sibling(stem):
    path = Path(__file__).with_name(stem + ".py")
    spec = importlib.util.spec_from_file_location(stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DatasetCapture = load_sibling("01_capture_dataset").DatasetCapture

# 통로 좌표 (랙 x∈{-5.5,-2.6,5.5}, y∈{±2.7}; 작업대 (2.6, ±3.6)). 로봇은 여기서 ±0.3 m 흔든다.
ROBOT_SPOTS = [(0.0, 0.0), (0.0, -4.6), (0.0, 4.6), (4.0, -1.0), (4.0, 1.0), (4.0, 4.6), (4.0, -4.6),
               (-4.0, 4.6), (-4.0, -4.6), (-4.0, 0.0), (-1.0, 0.0), (1.5, 0.0)]
# 상자는 작업대 위에만 있어 드물다. 작업대 앞 시점(0.7~1.6 m)을 전체의 약 40 % 로 섞는다.
TABLE_SPOTS = [(1.2, -3.6), (1.2, 3.6), (0.9, -3.3), (0.9, 3.9), (1.5, -3.9), (1.5, 3.3), (0.7, -3.6), (0.7, 3.6)]
# 사람·소품을 놓을 통로 구간: (x 범위, y 범위)
ACTOR_ZONES = [((-1.3, -0.9), (-2.5, 2.5)), ((3.7, 4.3), (-4.3, 4.6)), ((-3.0, 1.0), (4.3, 4.8)),
               ((-3.0, 1.0), (-4.8, -4.3)), ((-4.3, -3.7), (-4.0, 4.0)), ((1.4, 3.6), (-4.7, -4.3)),
               ((1.4, 3.6), (4.3, 4.7)), ((5.8, 6.8), (-1.5, 1.5))]
# 지게차(약 2 m)는 좁은 통로에 두면 랙과 겹쳐 박스가 랙을 관통한다. 넓은 구역만 쓴다.
FORKLIFT_ZONES = [((5.8, 6.8), (-2.0, 2.0)), ((-2.5, 0.5), (4.4, 4.7)), ((-2.5, 0.5), (-4.7, -4.4)), ((6.0, 6.8), (-4.0, -3.0))]
TABLE_X, TABLE_Y = 2.18, {"pick": -3.6, "place": 3.6}


class RandomizedCapture(DatasetCapture):
    def __init__(self):
        super().__init__()
        self.rng = random.Random(int(os.environ.get("M2_SEED", "0")))
        self.every = int(os.environ.get("M2_EVERY", "1"))
        self.frames_seen = 0

    def setup(self, context):
        super().setup(context)
        m = context.physics.model
        self.light_diffuse0 = m.light_diffuse.copy()
        self.light_dir0 = m.light_dir.copy()
        self.shirts = [c for c in context.actors.colors if not c.endswith("_vest") and c not in ("helmet", "skin", "pants")]
        self.people = [n for n, s in context.actors.actors.items() if s["spec"]["kind"] == "person"]
        self.props = [n for n, s in context.actors.actors.items() if s["spec"]["kind"] != "person"]
        self.parcels = [o["name"] for o in context.world["objects"]]
        for n in self.people + self.props:
            context.actors.pause(n)          # 경로 이동을 멈추고 순간이동만 쓴다
        context.node.get_logger().info(f"[m2-02] 랜덤화: 사람 {len(self.people)}, 소품 {len(self.props)}, 상자 {len(self.parcels)}, 조명 {m.nlight}")

    def __call__(self, frames):
        if self.done:
            return
        super().__call__(frames)
        self.frames_seen += 1
        if self.frames_seen % self.every == 0:
            self.randomize()

    # --- 랜덤화 --------------------------------------------------------------
    def randomize(self):
        ctx, rng = self.context, self.rng
        # 1) 로봇 시점: 통로의 한 지점 + 무작위 yaw. 절반은 작업대 앞(상자·마커 학습).
        if rng.random() < 0.4:
            rx, ry = rng.choice(TABLE_SPOTS)
            rx += rng.uniform(-0.15, 0.15); ry += rng.uniform(-0.2, 0.2)
            yaw = math.atan2(TABLE_Y["pick" if ry < 0 else "place"] - ry, TABLE_X - rx) + rng.uniform(-0.35, 0.35)  # 작업대를 보게
        else:
            rx, ry = rng.choice(ROBOT_SPOTS)
            rx += rng.uniform(-0.3, 0.3); ry += rng.uniform(-0.3, 0.3)
            yaw = rng.uniform(-math.pi, math.pi)
        self.teleport_robot(rx, ry, yaw)
        # 2) 사람: 위치 + 안전모(50 %) + 조끼 + 셔츠. 로봇과 1 m 이상, 서로 0.7 m 이상 떨어지게.
        taken = [(rx, ry)]
        for n in self.people:
            x, y = self.free_point(taken, 1.0); taken.append((x, y))
            ctx.actors.teleport(n, x, y, rng.uniform(-math.pi, math.pi))
            ctx.actors.set_attributes(n, {"helmet": rng.random() < 0.5, "vest": rng.choice(["orange", "green", "none", "none"]),
                                          "shirt": rng.choice(self.shirts)})
        # 3) 소품: 절반 확률로 자리를 옮긴다 (지게차는 큰 물체라 넓은 구역만).
        for n in self.props:
            if rng.random() < 0.5:
                kind = ctx.actors.actors[n]["spec"]["kind"]
                zones = FORKLIFT_ZONES if kind == "forklift" else ACTOR_ZONES
                x, y = self.free_point(taken, 1.6 if kind == "forklift" else 1.2, zones); taken.append((x, y))
                ctx.actors.teleport(n, x, y, rng.uniform(-math.pi, math.pi))
        # 4) 상자: 두 작업대에 나눠 무작위 y 로 놓는다 (겹치지 않게 0.12 m 간격).
        self.shuffle_parcels()
        # 5) 조명: 밝기 0.35~1.0 배, 방향 살짝 기울임.
        m = ctx.physics.model
        for i in range(m.nlight):
            m.light_diffuse[i] = self.light_diffuse0[i] * rng.uniform(0.35, 1.0)
            d = self.light_dir0[i] + np.array([rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0.0])
            m.light_dir[i] = d / np.linalg.norm(d)

    def free_point(self, taken, min_dist, zones=ACTOR_ZONES):
        for _ in range(50):
            (x0, x1), (y0, y1) = self.rng.choice(zones)
            x, y = self.rng.uniform(x0, x1), self.rng.uniform(y0, y1)
            if all(math.hypot(x - tx, y - ty) >= min_dist for tx, ty in taken):
                return x, y
        return x, y

    def teleport_robot(self, x, y, yaw):
        p = self.context.physics
        q = p.base_q
        p.data.qpos[q:q + 2] = [x, y]
        p.data.qpos[q + 3:q + 7] = [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]
        v = p.model.joint("floating_base").dofadr[0]
        p.data.qvel[v:v + 6] = 0.0

    def shuffle_parcels(self):
        p, rng = self.context.physics, self.rng
        table = rng.choice(list(TABLE_Y.values()))
        ys = []
        for name in self.parcels:
            side = table if rng.random() < 0.7 else rng.choice(list(TABLE_Y.values()))
            for _ in range(20):
                y = side + rng.uniform(-0.38, 0.38)
                if all(abs(y - oy) > 0.12 for oy in ys):
                    break
            ys.append(y)
            j = p.model.joint(name + "_free")
            qa, va = j.qposadr[0], j.dofadr[0]
            yaw = rng.uniform(-math.pi, math.pi)
            p.data.qpos[qa:qa + 7] = [TABLE_X + rng.uniform(-0.03, 0.03), y, 0.815, math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
            p.data.qvel[va:va + 6] = 0.0
