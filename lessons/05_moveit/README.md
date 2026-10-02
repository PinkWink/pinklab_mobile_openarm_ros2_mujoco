# 05. MoveIt + MuJoCo / Arm · End-Effector Control (Day 2 ⑦⑧)

## 목표

MoveIt이 OpenARM 양팔을 계획하고, 그 궤적이 MuJoCo 브리지의 FollowJointTrajectory 액션으로 실행되는 구조를 이해한다. 이름 자세 → IK → pose goal → Cartesian path → 그리퍼 순서로 팔을 직접 움직여 본다.

## 실행

```bash
# 시뮬레이터 + MoveIt (Nav2 없음). RViz MotionPlanning 패널을 보려면 rviz:=true
./scripts/mobile_openarm moveit viewer:=true rviz:=true

# 이름 자세 (SRDF group_state): ready | hands_up | transport | home
./scripts/mobile_openarm arm both ready
./scripts/mobile_openarm arm left hands_up

# End-Effector 제어 예제
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py where                      # 두 팔 TCP 위치 (TF)
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py ik left 0.45 0.20 0.95     # IK 만: 관절 7개 출력
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py pose left 0.45 0.20 0.95   # 계획 + 실행
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py cartesian left 0 0 -0.05   # 현재 TCP 에서 직선으로 5 cm 내리기
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py gripper left close
./scripts/mobile_openarm exec python lessons/05_moveit/ee_control.py demo                       # 위를 한 번에
```

## 화면에서 볼 것

- MuJoCo 창에서 팔이 움직이고, RViz MotionPlanning에서 같은 계획이 보인다. 두 화면이 같은 `/joint_states`를 보고 있다.
- `demo`: ready 자세 → TCP (0.45, 0.20, 0.95)로 계획 이동(오차 약 1 mm) → 직선 하강 5 cm(100 %) → 그리퍼 닫힘 11 mm / 열림 45 mm → 복귀.

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| planning group·이름 자세 | `src/mobile_openarm_moveit_config/config/mobile_openarm.srdf` (left_arm, right_arm, both_arms, grippers; ready/hands_up/transport/home) |
| MoveIt 컨트롤러 ↔ 브리지 궤적 액션 | `config/moveit_controllers.yaml`, `mobile_openarm_mujoco/trajectory.py` (관절 한계 검사 `LIMIT_TOLERANCE`) |
| IK 요청 (`/compute_ik`) | `warehouse_skills/moveit_client.py` `solve_ik()` 약 25줄: 현재 관절을 seed 로, 여러 번 시도해 가장 가까운 해 |
| pose goal = IK + 관절 공간 계획 | `move_pose()` → `move_joints()` (MoveGroup 액션, JointConstraint) |
| Cartesian path (`/compute_cartesian_path`) | `move_cartesian()`: 직선 waypoints, fraction < 0.9 면 실패 |
| 그리퍼 | GripperCommand 액션, 닫힘 위치에서 stalled 판정 |

## 해 볼 것

- `pose left 0.65 0.20 0.95` 처럼 멀리 보내 IK 실패를 보고, 도달 범위를 감으로 익힌다.
- `joint_limits.yaml` 의 속도 배율을 바꾸고 같은 동작의 시간을 비교한다.
- `cartesian` 으로 큰 이동(0.3 m)을 시켜 fraction 이 100 % 가 안 되는 경우를 만든다.

## 문제 해결

- "MoveIt action server unavailable": 시뮬레이터가 `moveit:=true` 로 떠 있는지(`moveit`/`start` 모드) 확인.
- 계획은 되는데 실행이 거부(error -4)되면 관절 한계 근처다. 브리지 `LIMIT_TOLERANCE`(0.02)가 MoveIt 한계 여유(0.01)보다 커야 한다.
- 팔이 움직이는 동안 베이스는 `/cmd_vel` 을 무시한다(인터록). 주행은 양팔이 주행 자세(transport 등)일 때만.
