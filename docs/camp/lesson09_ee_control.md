## 1. 손끝(End-Effector)으로 움직이기

### 관절 공간에서 작업 공간으로

![관절 공간 · 작업 공간 · 그리퍼](lesson09_why.png){width=1000}

### 좌표계: base_footprint 와 TCP

![base_footprint 기준 TCP 위치 (실측)](lesson09_frames.png){width=1000}

### 손의 방향: GRASP_FORWARD

![GRASP_FORWARD: 손 축과 로봇 축](lesson09_grasp.png){width=1000}

### IK: 손끝 자세 → 관절 7 개

![solve_ik 흐름](lesson09_ik_concept.png){width=1000}

### 같은 손끝, 다른 팔 모양

![같은 TCP (0.45, 0.20, 0.95) 에 대한 IK 해 4 개 (MuJoCo 렌더, 빨간 점 = 목표)](lesson09_ik_multi.png){width=1000}

### 손이 닿는 범위

![왼팔 도달 범위 (y = 0.20 m, /compute_ik 실측)](lesson09_reach.png){width=1000}

### pose goal 과 Cartesian path

![손을 옮기는 두 가지 방법](lesson09_pose_vs_cart.png){width=1000}

### 그리퍼

![GripperCommand 가 끝나는 조건](lesson09_gripper_concept.png){width=1000}

## 2. 실행: ee_control.py

### 실행: 터미널 1 (moveit)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
./scripts/mobile_openarm moveit viewer:=true rviz:=true     # ⑦ 과 같다
```

### 실행 결과: 터미널 1

![터미널 1: moveit 실행](lesson08_t1_moveit.png){width=1000}

### 실행 결과: 시작 화면

![MuJoCo 창(왼쪽)과 RViz2(오른쪽): 두 팔 transport 자세](lesson09_run_result.png){width=1000}

### 터미널 2: where · named

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py where              # 두 TCP 위치 (TF)
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py named both ready   # ⑦ 의 이름 자세
```

### 실행 결과: where · named

![where · named 결과](lesson09_cli_where.png){width=1000}

### 실행 결과: transport → ready

![named both ready 전과 뒤 (왼쪽 옆에서 본 MuJoCo 렌더)](lesson09_run_ready.png){width=1000}

### 터미널 2: ik

```bash
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py ik left 0.45 0.20 0.95   # 계산만, 팔은 안 움직인다
```

### 실행 결과: ik

![ik 결과: 관절 7 개](lesson09_cli_ik.png){width=1000}

### 터미널 2: pose

```bash
time ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py pose left 0.45 0.20 0.95
```

### 실행 결과: pose

![pose 결과](lesson09_cli_pose.png){width=1000}

### 실행 결과: ready → pose

![pose 전과 뒤 (빨간 점 = 목표 TCP)](lesson09_run_pose.png){width=1000}

### 터미널 2: cartesian

```bash
time ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py cartesian left 0 0 -0.05   # 지금 TCP 에서 5 cm 아래로 직선
```

### 실행 결과: cartesian

![cartesian 결과](lesson09_cli_cart.png){width=1000}

### 실행 결과: 5 cm 아래로

![cartesian 전과 뒤](lesson09_run_cart.png){width=1000}

### 손끝이 지나간 길

![demo 의 왼손 TCP 경로 (TF 실측): pose 는 곡선, cartesian 은 직선](lesson09_tcp_path.png){width=1000}

### pose 오차는 어디서 오나

![목표 관절 허용 범위 ± 0.01 rad 와 ± 0.001 rad 의 TCP 오차 (실측)](lesson09_pose_error.png){width=1000}

### 터미널 2: gripper

```bash
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py gripper left close
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py gripper left open
```

### 실행 결과: gripper

![gripper 결과](lesson09_cli_gripper.png){width=1000}

### 실행 결과: 열림 · 닫힘

![왼손 그리퍼 open · close (정면 근접 렌더)](lesson09_run_gripper.png){width=1000}

### 손가락 간격

![close → open 동안의 손가락 간격 (/joint_states)](lesson09_gripper.png){width=1000}

### 터미널 2: 실패하는 명령 두 가지

```bash
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py pose left 0.65 0.20 0.95   # 너무 멀다
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py cartesian left 0.3 0 0     # 앞으로 30 cm 직선
```

### 실행 결과: 실패

![IK 실패 · Cartesian 55 %](lesson09_cli_fail.png){width=1000}

### 터미널 2: demo

```bash
time ./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py demo   # ready → pose → 아래 5 cm → 닫기 · 열기 → 위 5 cm → transport
```

### 실행 결과: demo

![demo 결과](lesson09_cli_demo.png){width=1000}

### 움직이는 그림: demo 의 손끝 동작

![demo (움직이는 그림)](lesson09_ee_demo.gif){width=720}

## 3. 코드와 설정

### 명령과 함수

![ee_control.py 명령 → MoveItClient 함수 → 인터페이스](lesson09_ee_flow.png){width=1000}

### 목표 자세 만들기 - moveit_client.py make_pose 함수

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py
# Forward horizontal grasp: hand z (approach) -> +x, hand y (finger closing) -> +y, hand x -> -z.
GRASP_FORWARD = quat_from_axes(np.array([0, 0, -1.0]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0]))


def make_pose(xyz, quat=GRASP_FORWARD):
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = map(float, xyz)
    pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = map(float, quat)
    return pose
```

- `GRASP_FORWARD`: 손끝이 앞 (+x) 을 향하고 손가락이 좌우 (y) 로 닫히는 수평 파지 방향
- 위치 (x, y, z) 만 주면 방향은 기본값 → `Pose` 메시지 완성
- `quat_from_axes`: 손 좌표축 세 개의 방향으로 quaternion (x, y, z, w) 계산

### 시드와 IK 요청 설정 - moveit_client.py solve_ik 함수

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py
def solve_ik(self, side, pose, avoid_collisions=True):
    arm = self.arms[side]
    names = self.arm_joints(side)
    seed = np.array([self.joints.get(n, 0.0) for n in names])          # 현재 관절값
    best = None
    for _ in range(int(self.cfg["moveit"]["ik_attempts"])):            # 12 번
        req = GetPositionIK.Request()
        r = req.ik_request
        r.group_name, r.ik_link_name = arm["group"], arm["tcp_link"]   # left_arm, openarm_left_hand_tcp
        r.avoid_collisions = avoid_collisions
        r.timeout.nanosec = 200_000_000                                # 0.2 s
```

- 시드 = 현재 `/joint_states` 관절값 · IK 는 시드에서 출발해 수치적으로 해를 찾음
- `ik_attempts` 12 번 반복 → 여러 해 중에서 고르기 위함
- `avoid_collisions`: 충돌하는 해는 제외 · `tcp_link` = 목표 자세를 맞출 손끝 링크

### 목표 자세 · 시작 관절로 /compute_ik 호출 - moveit_client.py solve_ik 함수

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py solve_ik (이어서)
        r.pose_stamped = PoseStamped()
        r.pose_stamped.header.frame_id = "base_footprint"
        r.pose_stamped.pose = pose
        r.robot_state.is_diff = True
        r.robot_state.joint_state.name = names
        r.robot_state.joint_state.position = seed.tolist()
        res = wait(self.ik.call_async(req), 5.0, "compute_ik")         # 서비스 /compute_ik
```

- 목표 자세의 기준 프레임 = `base_footprint` (로봇 기준 좌표)
- `robot_state` 에 시드 관절을 넣어 IK 의 출발점으로 사용
- `wait`: 응답을 최대 5 [s] 기다림 · 넘으면 `SkillError`

### 지금 자세와 가장 가까운 해 고르기 - moveit_client.py solve_ik 함수

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py solve_ik (이어서)
        if res.error_code.val != MoveItErrorCodes.SUCCESS:
            continue
        q = dict(zip(res.solution.joint_state.name, res.solution.joint_state.position))
        sol = np.array([q[n] for n in names])
        cost = float(np.linalg.norm(sol - seed))                       # 지금 자세와의 거리
        if best is None or cost < best[0]:
            best = (cost, sol)
    if best is None:
        raise SkillError(f"No IK solution for {side} arm at (...)")
    return best[1]
```

- 실패한 시도는 건너뜀 · 성공한 해 중 시드와의 관절 거리 (`norm`) 가 최소인 것 선택
- 가장 덜 움직이는 해 → 팔이 크게 휘돌지 않음
- 해가 하나도 없으면 `SkillError`

### pose goal → 관절 목표 MoveGroup 요청 - moveit_client.py move_pose · move_joints 함수 발췌

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py
def move_pose(self, side, pose):
    self.move_joints(side, self.solve_ik(side, pose))                 # IK → 관절 목표


def move_joints(self, side, positions, timeout=60.0):   # 발췌
    goal = MoveGroup.Goal()
    req = goal.request
    req.group_name = self.arms[side]["group"]
    m = self.cfg["moveit"]
    req.max_velocity_scaling_factor = float(m["velocity_scaling"])    # 0.35
    req.start_state.is_diff = True
```

- pose goal 을 그대로 보내지 않고 IK 로 구한 관절값을 관절 목표로 계획
- 요청 형태는 앞 글 `joint_goal.py` 의 MoveGroup 요청과 같음
- 속도 비율 · 계획 시간은 `skills.yaml` 의 `moveit` 블록에서 읽음

### 관절 제약 ± 0.001 rad 로 보내기 - moveit_client.py move_joints 함수 발췌

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py move_joints (이어서)
    c = Constraints(name="skill")
    for name, value in zip(self.arm_joints(side), positions):
        c.joint_constraints.append(JointConstraint(joint_name=name, position=float(value),
                                                   tolerance_above=0.001, tolerance_below=0.001, weight=1.0))
    req.goal_constraints = [c]                                        # ± 0.001 rad → 손끝 약 1 mm (± 0.01 이면 수 mm ~ 1 cm)
    handle = wait(self.move.send_goal_async(goal), 10.0, "move_action goal")
    result = wait(handle.get_result_async(), timeout, "move_action result")
```

- IK 로 검증한 관절값이 목표 → 허용 범위를 좁혀 손끝 오차 약 1 [mm]
- `wait`: 수락 10 [s] · 결과는 `timeout` (기본 60 [s]) 까지 대기

### Cartesian path 요청 - moveit_client.py move_cartesian 함수 발췌

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py
def move_cartesian(self, side, waypoints, timeout=60.0):   # 발췌
    req = GetCartesianPath.Request()
    req.header.frame_id = "base_footprint"
    req.start_state.is_diff = True
    req.group_name, req.link_name = arm["group"], arm["tcp_link"]
    req.waypoints = list(waypoints)                                  # 끝점 (자세는 GRASP_FORWARD)
    req.max_step = float(m["cartesian_step"])                        # 1 cm 마다 IK
    req.jump_threshold = 0.0
    req.avoid_collisions = True
```

- `/compute_cartesian_path`: 손끝이 waypoint 까지 직선으로 가는 궤적 계산
- `max_step` 0.01 [m] 간격으로 IK 를 풀어 이음
- `jump_threshold` 0 = 관절 급변 검사 끔

### 경로 비율 확인 후 실행 - moveit_client.py move_cartesian 함수 발췌

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py move_cartesian (이어서)
    res = wait(self.cartesian.call_async(req), 10.0, "compute_cartesian_path")
    if res.error_code.val != MoveItErrorCodes.SUCCESS or res.fraction < float(m["cartesian_min_fraction"]):
        raise SkillError(f"Cartesian path covers only {res.fraction * 100:.0f}% (error_code={res.error_code.val})")
    goal = ExecuteTrajectory.Goal(trajectory=res.solution)           # 계획된 궤적을 그대로 실행
    handle = wait(self.execute.send_goal_async(goal), 10.0, "execute_trajectory goal")
    result = wait(handle.get_result_async(), timeout, "execute_trajectory result")
    return res.fraction
```

- `fraction` = 요청한 직선 중 계획된 비율 (0 ~ 1) · 0.9 미만이면 실행하지 않음
- MoveGroup 과 달리 계획 (서비스) 과 실행 (`/execute_trajectory` 액션) 이 나뉨

### 그리퍼 - moveit_client.py gripper 함수

```python
# src/warehouse_skills/warehouse_skills/moveit_client.py
def gripper(self, side, position, effort, timeout=15.0):
    goal = GripperCommand.Goal()
    goal.command.position, goal.command.max_effort = float(position), float(effort)   # 0.012 m · 25 N
    handle = wait(self.grippers[side].send_goal_async(goal), 10.0, "gripper goal")
    if not handle.accepted:
        raise SkillError("Gripper goal rejected (is the base moving or an arm action active?)")
    result = wait(handle.get_result_async(), timeout, "gripper result").result
    return result                                                      # position · reached_goal · stalled
```

- `gripper_cmd` 액션 · 목표 = 손가락 위치 [m] + 최대 힘 [N]
- 거부 = 앞 글의 브리지 goal 검사 (베이스 주행 중 · 같은 그리퍼 실행 중)
- 물체를 잡으면 `reached_goal` 대신 `stalled` 가 True

### 그리퍼 도달 · 멈춤 판정 - actions.py Controllers.update 함수 발췌

```python
# src/mobile_openarm_mujoco/mobile_openarm_mujoco/actions.py
else:   # 그리퍼 (발췌)
    position = float(p.positions(state["names"])[0])
    reached = abs(position - h.request.command.position) < p.settings["gripper"]["goal_tolerance"]   # 2 mm
    if abs(position - state["last_position"]) > 0.0001:
        state["last_motion"] = p.data.time
        state["last_position"] = position
    stalled = p.data.time - state["last_motion"] > 1.0 and not reached                            # 1 s 정지
```

- `reached`: 목표 위치 ± 2 [mm] 안
- `stalled`: 못 닿은 채 1 [s] 동안 0.1 [mm] 도 안 움직임 → 물체에 막힘

### 그리퍼 결과 채우고 끝내기 - actions.py Controllers.update 함수 발췌

```python
# src/mobile_openarm_mujoco/mobile_openarm_mujoco/actions.py Controllers.update (이어서)
    result.position = position
    result.reached_goal = reached
    result.stalled = stalled
    if reached or stalled:
        self.finish(key, state, result, "succeed")
    elif t > 6:
        self.finish(key, state, result, "abort")
```

- 도달 · 멈춤 둘 다 `succeed` → 잡았는지는 호출한 쪽이 `stalled` · `position` 으로 판단
- 6 [s] 넘게 둘 다 아니면 abort

### skills.yaml 의 moveit 값

![skills.yaml moveit 블록](lesson09_params.png){width=1000}

### skills.yaml 발췌

```yaml
# src/warehouse_skills/config/skills.yaml (발췌)
moveit:
  planning_time: 5.0
  attempts: 4
  velocity_scaling: 0.35
  acceleration_scaling: 0.35
  ik_attempts: 12
  cartesian_step: 0.01
  cartesian_min_fraction: 0.9
arms:
  left: {shoulder_y: 0.093, tcp_link: openarm_left_hand_tcp, group: left_arm, gripper: left_gripper_controller, hand_link: openarm_left_hand}
  right: {shoulder_y: -0.093, tcp_link: openarm_right_hand_tcp, group: right_arm, gripper: right_gripper_controller, hand_link: openarm_right_hand}
```

- `moveit`: 계획 시간 [s] · 시도 횟수 · 속도 비율 · IK 반복 · 직선 간격 [m] · 최소 비율
- `arms`: 팔마다 계획 그룹 · 손끝 링크 (`tcp_link`) · 그리퍼 컨트롤러 이름을 연결

### 해 볼 것

- 도달 범위 그림을 보고 `pose left 0.35 0.20 1.15` 처럼 초록 칸의 끝을 골라 성공 · 실패 확인
- `cartesian left 0 0.1 0` (왼쪽으로 10 cm) 과 `cartesian left 0 -0.1 0` 을 비교 → 몸통 쪽으로는 몇 % 까지 가는지
- `move_joints` 의 `tolerance_above/below` 를 0.01 · 0.05 로 넓혀 `pose` 오차와 계획 시간 비교 (끝나면 0.001 로 되돌리기)
