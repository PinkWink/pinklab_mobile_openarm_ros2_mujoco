## 1. 도킹 · 인식 · 팔을 하나의 스킬로

### ⑧ 에서 ⑨ 로

![이동 + 도킹 · 인식 · 팔 + 그리퍼](lesson10_why.png){width=1000}

### PickPlace 액션

![goal · feedback · result](lesson10_action.png){width=1000}

### 단계: pick 절반과 place 절반

![phase=pick · phase=place · phase=all](lesson10_phases.png){width=1000}

### 작업대 · 마커 · 상자 · 슬롯

![픽업 작업대 위에서 본 모습 (world 파일 + /ground_truth 실측)](lesson10_layout.png){width=1000}

### 도킹: 마커 두 개로 마지막 50 cm

![along · side · turn 과 속도 명령](lesson10_dock_concept.png){width=1000}

### 위치 확인: 카메라 → base_footprint

![head_camera → YOLO → map → base_footprint](lesson10_locate_concept.png){width=1000}

### 잡기: pre-grasp → 직선 접근 → 들기

![오른손 TCP 경로 (옆에서 본 x-z, TF 실측)](lesson10_grasp_concept.png){width=1000}

## 2. 실행: pick_then_place.py

### 실행: 터미널 1 (start)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start spawn:=pick_table camera_depth:=true locate:=vision viewer:=true rviz:=false
```

### 실행 결과: 터미널 1

![터미널 1: start (MoveIt · Nav2 · PickPlace 서버 · 카메라 핸들러)](lesson10_t1.png){width=1000}

### 실행 결과: 시작 화면

![MuJoCo 창: 로봇이 픽업 작업대 앞 (spawn:=pick_table)](lesson10_run_result.png){width=1000}

### 터미널 2: pick_then_place.py

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
time ./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red   # 집고, 같은 작업대에 다시 놓기
```

### 실행 결과: pick 절반

![pick 절반: 단계별 feedback 과 결과](lesson10_cli_pick.png){width=1000}

### 실행 결과: place 절반

![place 절반: 단계별 feedback 과 결과](lesson10_cli_place.png){width=1000}

### 실행 결과: 도킹

![사전 도킹 지점 → blind 시작 → 도킹 끝 (오프스크린 렌더)](lesson10_run_dock.png){width=1000}

### 도킹 그래프

![마커면까지 거리 · 마커 쌍 측정 · /cmd_vel (실측)](lesson10_dock_graph.png){width=1000}

### 카메라가 본 것

![locate 때 head_camera 화면과 YOLO 검출 상자](lesson10_camera.png){width=1000}

### 실행 결과: 잡기

![pre-grasp · grasp · lift · carry (오프스크린 렌더)](lesson10_run_grasp.png){width=1000}

### 손가락 · 손끝 · 상자 높이

![pick 동안 손가락 간격, 오른손 TCP z, 상자 z (실측)](lesson10_hold_graph.png){width=1000}

### 실행 결과: 놓기

![pre-place · release · retreat (오프스크린 렌더)](lesson10_run_place.png){width=1000}

### 단계별 시간

![pick 44 s · place 51 s (sim 시각)](lesson10_timeline.png){width=1000}

### 터미널 2: 실패하는 명령

```bash
./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red --only place   # 든 것이 없는데 놓기
```

### 실행 결과: 실패

![nothing is held](lesson10_cli_fail.png){width=1000}

### 같은 일을 CLI 로

```bash
./scripts/mobile_openarm pick red --phase pick                            # 집은 채 멈춘다 (뷰어로 살펴보기)
./scripts/mobile_openarm pick red pick_table pick_table --phase place     # 인자: 색 · 출발 작업대 · 놓을 작업대 (기본 place_table)
```

### 실행 결과: CLI

![pick CLI: --phase pick 다음 --phase place (visual dock 줄은 생략)](lesson10_cli_cli.png){width=1000}

## 3. 코드와 설정

### 함수 구조

![execute → do_pick / do_place → 단계 함수](lesson10_code_flow.png){width=1000}

### 액션 보내기 - pick_then_place.py run 함수 발췌

```python
# lessons/06_pick_place/pick_then_place.py
goal = PickPlace.Goal(object=colour, phase=phase)            # red, pick | place
if phase == "pick":
    goal.from_station = station
else:
    goal.to_station = station


def on_fb(m):                                                 # feedback 마다 한 줄
    f = m.feedback
    print(f"   [{time.monotonic() - t0:5.1f}s {f.phase:14s}] {f.detail}", flush=True)


future = self.client.send_goal_async(goal, feedback_callback=on_fb)   # 액션 /pick_place
rclpy.spin_until_future_complete(self, future, timeout_sec=10)
gh = future.result()
rf = gh.get_result_async()
while not rf.done() and time.monotonic() < end:
    rclpy.spin_once(self, timeout_sec=0.1)
r = rf.result().result                                        # success · message · phase_reached · duration_s
```

### 절반 고르기 - pick_place_server.py execute 함수 발췌

```python
# warehouse_skills/pick_place_server.py
which = (goal.phase or "all").lower()
if which == "place":
    if self.held is None:
        raise SkillError("nothing is held: run the pick phase first")
    name, arm = self.held["name"], self.held["arm"]           # pick 절반이 기억해 둔 것
else:
    name, arm, src = self.do_pick(goal, feedback)
if which == "pick":
    lifted = float(fz - top_z)                                # 상자가 상판보다 얼마나 위에 있나 (정답 위치)
    result.success = bool(lifted > 0.02)
    if result.success:
        self.held = {"name": name, "arm": arm}
else:
    st, offset = self.do_place(goal, name, arm, feedback)
    placed = float(math.hypot(fx - target[0], fy - target[1]))   # 슬롯 중심에서 몇 cm
    result.success = bool(placed < 0.08 and fz > st["top_z"])
```

### pick 절반 - pick_place_server.py do_pick 함수 발췌

```python
# warehouse_skills/pick_place_server.py
def do_pick(self, goal, feedback):
    name = self.resolve_object(goal.object)                   # red → parcel_1
    src = self.resolve_station(goal.from_station or "pick_table")
    offset = self.object_offset(name, src)                    # 작업대 축에서 -0.25 m
    arm = goal.arm or self.arm_for_offset(offset)             # 음수 → 오른팔
    self.moveit.move_named(arm, self.cfg["transport_pose"], self.states)
    dock_side = self.dock_side_for(offset)                    # 0.25 m 이내면 축 위에 도킹
    self.navigate_and_dock(src, arm, lambda origin, u: -dock_side, "navigate_pick", feedback)
    rel = self.locate_object(name)                            # 카메라: (dx, dy, z) in base_footprint
    if not goal.arm and self.arm_for_offset(rel[1]) != arm:
        arm = self.arm_for_offset(rel[1])                     # 도킹 잔차 때문에 반대쪽이면 팔 바꾸기
    self.grasp(arm, name, feedback, rel)
    self.moveit.move_named(arm, self.cfg["carry_pose"], self.states)   # hands_up
    self.nav.drive(-float(self.cfg["dock"]["undock_distance"]))       # 0.75 m 후진
    return name, arm, src
```

### 도킹 - nav_client.py dock 함수 발췌

```python
# warehouse_skills/nav_client.py
end = time.monotonic() + float(d["timeout_s"])                # 180 s (벽시계)
while time.monotonic() < end:
    f = self.fixes(ids, max_age=0.8)                          # 0.8 s 안에 찍힌 마커만
    if len(f) < 2:                                            # 쌍이 아니면 멈추고 기다림
        if last is not None and last[0] <= visual_end + 0.15:
            break
        self._publish(0.0, 0.0)
        time.sleep(0.1)
        continue
    along, side, turn, _, _ = self.geometry(f, offsets)
    last = (along, side, turn)
    last_odom = self.markers_odom
    if along <= visual_end:                                   # 0.80 m 안: 바깥 마커가 곧 화면 밖
        break
    lateral = side - float(target_side)
    v = min(float(d["max_speed"]), max(0.03, float(d["gain"]) * (along - float(target_dx))))
    w = float(d["lateral_gain"]) * lateral / max(along, 0.3) + float(d["heading_gain"]) * turn
    self._publish(v, max(-0.3, min(0.3, w)))
    time.sleep(0.1)
# blind: 마지막 측정 뒤 이미 간 거리를 빼고 오도메트리로 직진
remaining = along - travelled - float(target_dx)
self.drive(remaining, speed=float(d["blind_speed"]))
```

### 위치 확인 - locate.py VisionLocator.relative 함수 발췌

```python
# warehouse_skills/locate.py
def relative(self, label, wait=10.0):
    since = self.node.get_clock().now().nanoseconds * 1e-9    # 부른 시각 (sim)
    end = time.monotonic() + wait
    while True:
        m = self.latest                                       # 마지막 /vision/detections
        fresh = m is not None and m.header.stamp.sec + m.header.stamp.nanosec * 1e-9 >= since
        hits = [d for d in m.detections if d.label == label and d.has_position] if fresh else []
        if hits:
            break
        if time.monotonic() > end:
            raise SkillError(f"{label} not visible")
        time.sleep(0.05)
    best = max(hits, key=lambda d: d.score)
    out = self.buffer.transform(best.position, "base_footprint", timeout=rclpy.duration.Duration(seconds=0.5))
    return float(out.point.x), float(out.point.y), float(out.point.z)   # map → base_footprint (같은 TF)
```

### 잡기 - pick_place_server.py grasp 함수 발췌

```python
# warehouse_skills/pick_place_server.py
dx, dy, dz = rel
z = dz + float(g["z_offset"])                                 # 물체 중심 + 2 cm
self.moveit.gripper(arm, g["open"], g["effort"])              # 44 mm
for pre in offsets:                                           # -0.10, -0.06, -0.03 m
    try:
        self.moveit.move_pose(arm, make_pose([dx + pre, dy, z]))   # ⑧ 의 pose goal
        break
    except SkillError as error:
        last_error = error
self.moveit.move_cartesian(arm, [make_pose([dx, dy, z])])     # ⑧ 의 Cartesian: 직선 접근
result = self.moveit.gripper(arm, g["close"], g["effort"])    # 12 mm 명령 → 상자에 막혀 멈춤
if not (float(g["close_min"]) <= result.position <= float(g["close_max"])):
    raise SkillError(f"grasp missed: finger stopped at {result.position * 1000:.1f} mm")
self.moveit.attach(arm, name, [size[2], size[1], size[0]], below_tcp=float(g["z_offset"]))   # planning scene
up = make_pose([dx, dy, z + float(g["lift_z"])])              # 4 cm 위
back = make_pose([dx + float(g["retreat_x"]), dy, z + float(g["lift_z"])])   # 14 cm 뒤
self.moveit.move_cartesian(arm, [up, back])
```

### 놓기 - pick_place_server.py place 함수 발췌

```python
# warehouse_skills/pick_place_server.py
z = top_z + float(p["drop_z"]) + size[2] / 2 + float(g["z_offset"])   # 상판 + 4 mm + 상자 반 + 2 cm
self.moveit.move_pose(arm, make_pose([slot_dx + float(p["pre_offset_x"]), slot_dy, z + float(g["lift_z"])]))
self.moveit.move_cartesian(arm, [make_pose([slot_dx, slot_dy, z + float(g["lift_z"])]),
                                 make_pose([slot_dx, slot_dy, z])])   # 앞으로 12 cm → 아래로 4 cm
self.moveit.gripper(arm, g["open"], g["effort"])
self.moveit.detach(arm, name)
self.moveit.move_cartesian(arm, [make_pose([slot_dx + float(g["retreat_x"]), slot_dy, z + float(g["lift_z"])])])
```

### skills.yaml 의 값

![skills.yaml dock · grasp · place](lesson10_params.png){width=1000}

### skills.yaml 발췌

```yaml
# src/warehouse_skills/config/skills.yaml (발췌)
dock:
  target_dx: 0.56
  visual_end_dx: 0.80
  max_speed: 0.10
  blind_speed: 0.06
  gain: 0.6
  lateral_gain: 1.2
  heading_gain: 0.4
  timeout_s: 180.0
  undock_distance: 0.75
grasp:
  pre_offset_x: -0.10
  lift_z: 0.04
  retreat_x: -0.14
  z_offset: 0.02
  open: 0.044
  close: 0.012
  close_min: 0.016
  close_max: 0.028
  effort: 25.0
place:
  pre_offset_x: -0.12
  drop_z: 0.004
  slot_offsets_y: [-0.25, 0.0, 0.25]
  x_from_edge: 0.055
carry_pose: hands_up
```

### 해 볼 것

- `pick_then_place.py blue` · `yellow` 로 바꿔 팔 선택 (feedback 의 `-> left arm` / `right arm`) 과 놓는 슬롯 비교
- `skills.yaml` 의 `grasp.close_max` 를 0.020 으로 좁혀 `grasp missed` 를 만들고, 실패 뒤 팔이 어떻게 풀려나는지 (`recover()`) 보기 (끝나면 0.028 로 되돌리기)
- `--to place_table` 로 반대편 작업대에 놓아 ⑩ (주행 + Pick & Place) 로 넘어가기
