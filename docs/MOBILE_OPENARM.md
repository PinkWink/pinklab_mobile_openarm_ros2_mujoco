# Vic Pinky + OpenArm · ROS 2 Jazzy · MuJoCo

현재 workspace에 **이동형 양팔 로봇 구성**을 추가했습니다. 기존 Pinky Pro는 `./scripts/pinky`, 새 로봇은 `./scripts/mobile_openarm`으로 실행합니다. Gazebo 노드·브리지·플러그인은 사용하지 않습니다.

현재 Mac의 `pinky-jazzy` 환경에서 빌드와 실행을 검증했습니다. Ubuntu 24.04 / ROS 2 Jazzy용 패키지 및 설치 절차도 포함했습니다. Ubuntu 실기 연결과 하중 검증은 이번 범위에 포함하지 않습니다.

## 빠른 실행

workspace에서:

```bash
./scripts/mobile_openarm build
./scripts/mobile_openarm start
```

MuJoCo viewer, MoveIt RViz, Nav2 + AMCL이 함께 실행됩니다. 기본 지도는 창고 형상에서 생성한 정적 지도입니다. 터미널에서 `Managed nodes are active`와 `You can start planning now!`를 확인합니다. 첫 GUI 실행은 macOS 바이너리 검사 때문에 늦어질 수 있습니다. **종료는 실행 터미널의 Ctrl+C**입니다.

다른 터미널에서:

```bash
./scripts/mobile_openarm goal 1.0 0.6 0.0
./scripts/mobile_openarm arm left ready
./scripts/mobile_openarm arm right ready
./scripts/mobile_openarm arm both transport
```

`arm` 명령은 `/move_action`으로 OMPL 계획을 요청하고, MuJoCo의 실제 관절 측정값으로 실행 완료를 확인합니다. `--plan-only`를 붙이면 계획만 수행합니다. 주행 전에 양팔을 `transport`로 복귀시켜야 합니다.

```bash
./scripts/mobile_openarm arm both ready --plan-only
./scripts/mobile_openarm teleop
```

키보드는 `i` 전진, `,` 후진, `j/l` 회전, `k` 정지입니다. Nav2 목표 실행 중에는 teleop 명령을 동시에 주지 않습니다. 기본 수동 속도는 0.25m/s, 명령 제한은 0.35m/s·0.7rad/s입니다. 명령이 0.5초 끊기면 감속 정지합니다. 팔·그리퍼 액션 실행 중에는 주행 명령을 받지 않고, 베이스가 움직이면 새 팔·그리퍼 액션을 거절합니다.

모드별 실행은 **한 번에 하나**만 사용합니다:

```bash
./scripts/mobile_openarm drive                 # 주행, MuJoCo, 기본 RViz
./scripts/mobile_openarm moveit                # MoveIt, MuJoCo, 양팔 RViz
./scripts/mobile_openarm slam                  # SLAM 지도 작성
./scripts/mobile_openarm nav                   # 기본 정적 지도 + AMCL + Nav2 + MoveIt
./scripts/mobile_openarm nav map:=''           # SLAM + Nav2
./scripts/mobile_openarm start viewer:=false rviz:=false  # headless
./scripts/mobile_openarm start moveit:=false    # 주행만 사용
```

SLAM은 회전 키프레임을 허용하고 `min_pass_through=1`을 사용합니다. 가상 라이다에는 잡음을 추가하지 않았습니다. 실센서 적용 시 이 설정을 재조정해야 합니다.

SLAM 지도 저장:

```bash
./scripts/mobile_openarm exec ros2 run nav2_map_server map_saver_cli \
  -f maps/mobile_warehouse --ros-args -p use_sim_time:=true
./scripts/mobile_openarm nav "map:=$(pwd)/maps/mobile_warehouse.yaml"
```

독립 `navigation.launch.py`, `moveit.launch.py`는 실행 중인 시뮬레이터에 추가할 때 사용합니다. 둘 다 로봇 또는 시뮬레이터를 중복 생성하지 않습니다. `warehouse.launch.py`가 전체 실행의 기본 진입점입니다.

## 패키지

| 패키지 | 역할 |
|---|---|
| `vicpinky_description` | 요청한 Vic Pinky 저장소의 원본 URDF와 메시 |
| `openarm_description` | ZIP의 repos 파일에 지정된 OpenArm v1.0 원본 자산 |
| `mobile_openarm_description` | 통합 xacro, 초기 자세, 충돌 제외 목록, 카메라 4대 장착 |
| `mobile_openarm_mujoco` | URDF → MJCF, 창고, 바퀴 물리, lidar, 팔/그리퍼 액션, Python 카메라 API |
| `mobile_openarm_navigation` | 주행·SLAM·Nav2 설정, 창고 지도, 목표점 명령 |
| `mobile_openarm_moveit_config` | SRDF, KDL, OMPL, 관절 제한, 양팔·그리퍼 컨트롤러, planning scene |
| `mobile_openarm_bringup` | MuJoCo·주행·MoveIt 통합 launch |

```text
map → odom → base_footprint → base_link
                              ├─ left_wheel / right_wheel
                              ├─ lidar_mount → laser_link
                              └─ openarm_mount → openarm_body_link0
                                                  ├─ openarm_left_* → hand_tcp
                                                  └─ openarm_right_* → hand_tcp
```

베이스 루트는 `base_footprint`이며 고정 `world` 링크로 묶지 않았습니다. ROS에서는 엔코더 오도메트리가 `odom → base_footprint`를 발행하고, MuJoCo에서는 free joint로 접촉 물리를 계산합니다. 양팔은 각각 7축, 그리퍼는 각각 1개 능동 관절 + 1개 mimic 관절입니다. `/joint_states`에는 바퀴 2개까지 총 20개 관절이 포함됩니다.

기본 장착 위치는 `base_link` 기준 x=0.0m(바퀴 축 = 회전 중심), z=0.13m입니다. 원본 OpenArm 기둥과 2kg 어댑터 판을 추가했습니다. 장착점은 `mobile_openarm_description/urdf/mobile_openarm.urdf.xacro`의 `mount_x`, `mount_z`로 수정합니다. 이것은 시뮬레이션 장착안이며 실제 체결 설계나 전도 안전성을 검증한 도면이 아닙니다.

## 주행과 MoveIt 인터페이스

| 인터페이스 | 기능 |
|---|---|
| `/cmd_vel` (`Twist`) | 차동 주행 |
| `/cmd_vel_stamped` (`TwistStamped`) | stamped 명령용 별도 입력 |
| `/odom`, `/tf` | 바퀴 엔코더 오도메트리 |
| `/scan` | `laser_link` 기준 360 rays, 10Hz |
| `/joint_states` | 실제 MuJoCo 관절 상태, 50Hz |
| `/clock` | 시뮬레이션 시간, 100Hz |
| `/ground_truth` | 검증 및 창고 planning scene 정렬용 실제 pose |
| `/warehouse/object_poses` | YAML objects 순서의 실제 물체 pose |
| `/left_joint_trajectory_controller/follow_joint_trajectory` | 왼팔 `FollowJointTrajectory` |
| `/right_joint_trajectory_controller/follow_joint_trajectory` | 오른팔 `FollowJointTrajectory` |
| `/left_gripper_controller/gripper_cmd` | 왼손 `GripperCommand` |
| `/right_gripper_controller/gripper_cmd` | 오른손 `GripperCommand` |

이번 시뮬레이션은 MoveIt Simple Controller Manager와 MuJoCo 액션 서버를 직접 연결합니다. `ros2_control_node`, `mock_components`, CAN 드라이버를 실행하지 않습니다. 성공은 관절이 실제 목표에 도달했을 때 반환합니다. 궤적 이름·길이·유한값·범위·시간을 검사하고, 동시 중복 목표 거절, 취소 후 현재 자세 유지, 위치 path/goal tolerance와 timeout을 처리합니다. 목표 속도 tolerance는 지원하며, 경로 속도 tolerance와 가속도 tolerance의 양수 지정은 거절합니다. 속도가 주어진 궤적은 cubic Hermite 보간, 위치만 있으면 선형 보간을 사용합니다. 가속도 샘플은 보간에 사용하지 않습니다.

MoveIt planning group: `left_arm`, `right_arm`, `both_arms`, `left_gripper`, `right_gripper`. 팔 자세: `home`, `hands_up`, `transport`, `ready`. 기본은 `transport`(joint4=1.2rad)입니다. `home`은 원본 영점 자세이며 **주행 자세가 아닙니다**.

그리퍼 직접 개폐 예:

```bash
./scripts/mobile_openarm exec ros2 action send_goal \
  /left_gripper_controller/gripper_cmd control_msgs/action/GripperCommand \
  '{command: {position: 0.035, max_effort: 15.0}}' --feedback
```

`position`은 한쪽 finger의 변위(m)이며 최대 0.044m입니다. 접촉으로 멈춘 경우 결과의 `stalled`와 `reached_goal`을 구분합니다.

## 카메라 4대

주행 베이스, 머리 위치, 양쪽 손목에 카메라를 장착했습니다. **영상은 ROS 토픽을 사용하지 않고 MuJoCo에서 Python NumPy 배열로 직접 받습니다.** RGB, 선택적 깊이, 내부 파라미터와 광학 좌표 변환을 제공합니다.

```bash
./scripts/mobile_openarm start \
  camera_handler:=mobile_openarm_mujoco.camera_demo:handle_frames \
  camera_depth:=true camera_fps:=2
```

실행 중인 동일한 물리 상태에서 4대의 영상을 읽어 Python 콜백으로 넘깁니다. 설정·콜백 예제·좌표 규약은 [카메라 안내](MOBILE_CAMERAS.md)를 참고하세요.

## 창고와 pick-and-place 확장

내부 바닥 **15 × 11m = 165㎡ ≈ 49.9평**, 6개 랙, 2개 작업대, 3개 동적 소형 상자가 있습니다. 랙 재고 상자는 고정 장애물이고, `parcel_1..3`은 자유 물체입니다. 집기용 상자는 45 × 45 × 60mm, 80g으로 그리퍼 간격 안에 들어갑니다. 작업대 상판 높이는 0.78m입니다.

한 원본 `src/mobile_openarm_mujoco/worlds/warehouse.yaml`을 MuJoCo와 MoveIt planning scene에 사용합니다. planning scene은 물체의 실제 pose를 갱신하고, ground truth와 엔코더 pose 차이를 보정해 `odom` 좌표계에 배치합니다. Nav2/SLAM은 ground truth를 입력으로 사용하지 않습니다. 정적 지도는 전체 높이의 장애물 투영이라 라이다 높이에 보이지 않는 상판도 지도에 반영됩니다.

창고를 수정한 후 지도와 설치 파일을 갱신합니다:

```bash
./scripts/mobile_openarm exec python scripts/generate_warehouse_map.py
./scripts/mobile_openarm build
```

이번 완료 범위는 주행·양팔 계획/실행 기반 구성입니다. **자동 물체 인식, grasp pose 선정, MoveIt Task Constructor, 물체 attach/detach, 물건을 집어 운반해 놓는 전체 시퀀스는 아직 구현하지 않았습니다.** 후속 실습은 주행 도킹 → 정지 → pre-grasp → 그리퍼 → lift → place → transport 복귀 순서로 확장하면 됩니다. YAML `stations`는 도킹 후보 좌표이며 집기 IK까지 검증한 목표는 아닙니다. attach/detach를 추가할 때에는 `warehouse_scene`의 해당 물체 갱신도 일시 중지하도록 연동해야 합니다.

## 물리 모델의 명시적 조정

- 바퀴 반지름 0.0825m, 간격 **0.4288m**를 URDF에서 가져옵니다. 원본 Gazebo 플러그인의 0.3788m와 다르므로 그 설정을 이식하지 않았습니다.
- URDF·메시는 보존합니다. MuJoCo에서만 타이어 충돌을 같은 반지름·폭의 ellipsoid로 둡니다. 원통의 넓은 접촉면에서 발생한 회전 미끄러짐을 줄이는 둥근 타이어 근사입니다. 캐스터는 원본 고정 구체 + 낮은 마찰입니다.
- 원본 네 finger의 비대각 관성 성분이 주관성 삼각부등식을 위반해 MuJoCo 컴파일을 실패시켰습니다. 통합 description의 `config/gripper_inertials.yaml`에서 대각값은 유지하고 곱관성을 0으로 둡니다. ROS·RViz·MuJoCo가 같은 보정 관성을 사용하며 원본 자산은 바꾸지 않았습니다.
- 양팔은 위치 PD + 이상적인 관절 bias torque 보상입니다. 베이스 전체를 띄우는 중력 제거 방식은 사용하지 않습니다. 실제 OpenArm 모터·CAN 및 실측 중력보상 모델과 동일하다고 가정하면 안 됩니다.
- MuJoCo mesh contact는 convex 근사입니다. 각 팔의 `link5/link7`은 이 근사에서 생기는 겹침만 MuJoCo 설정에서 제외합니다. MoveIt은 원본 collision mesh와 SRDF를 사용하며, ZIP의 광범위한 `Never` 목록을 그대로 복사하지 않았습니다.
- Nav2 footprint는 `transport` 자세용 0.76 × 0.64m 사각형 + padding 0.03m입니다. 다른 팔 자세에서는 bridge가 주행을 막습니다.
- 카메라는 이상적인 RGB·깊이 센서이며 하우징은 시각 형상만 포함합니다. IMU·실물 구동은 현재 구현하지 않았습니다.

## 설치 및 환경

이 Mac에는 필요한 MoveIt 2 패키지까지 설치되어 있습니다. 다른 Mac에서는 Miniconda와 기본 RoboStack 설치 후:

```bash
./scripts/install_mobile_openarm.sh
```

Ubuntu 24.04, ROS 2 Jazzy 설치 후:

```bash
sudo apt install python3-venv python3-colcon-common-extensions python3-rosdep
source /opt/ros/jazzy/setup.bash
# rosdep 초기화가 안 된 머신에서 한 번: sudo rosdep init && rosdep update
./scripts/install_mobile_openarm.sh
```

Ubuntu 새 터미널에서는:

```bash
source /opt/ros/jazzy/setup.bash
source .venv-mobile-openarm/bin/activate
./scripts/mobile_openarm start
```

Python 의존성은 `requirements-mobile-openarm.txt`, RoboStack 전체 환경은 `environment.yml`에 기록했습니다. 두 호스트의 build/install 폴더는 호환되지 않으므로 다른 OS에 옮길 때 소스에서 다시 빌드합니다.

실행 스크립트는 localhost만 사용하고 기본 **ROS_DOMAIN_ID=43**입니다. 기존 Pinky(domain 42)와 토픽이 섞이지 않습니다. 명령 도구도 `./scripts/mobile_openarm exec ...`를 통해 실행하세요. `MOBILE_ROS_DOMAIN_ID`로 새 로봇의 domain을 변경할 수 있습니다.

## 검증

```bash
./scripts/mobile_openarm exec python -m pytest tests/test_mobile_openarm.py -q
# 새로운 headless start 실행 후, 다른 터미널에서 (로봇이 실제로 움직입니다):
./scripts/mobile_openarm exec python scripts/check_mobile_openarm.py --nav
./scripts/mobile_openarm exec python scripts/render_mobile_openarm.py
# SLAM 모드가 실행 중일 때:
./scripts/mobile_openarm exec python scripts/check_mobile_slam.py
```

검증 결과는 `docs/MOBILE_OPENARM_VALIDATION.md`, 실제 장면은 `artifacts/mobile-openarm-robot.png`, `artifacts/mobile-openarm-warehouse.png`에 있습니다.

## 출처

- [Vic Pinky](https://github.com/pinklab-art/vic_pinky), commit `7a8ce991b57b44eafa46737578f489f2d57b22be`. 원본 package.xml의 라이선스 선언은 `TODO`입니다. 이 프로젝트는 원본 자산에 별도 재배포 라이선스를 부여하지 않습니다.
- [OpenArm description](https://github.com/enactic/openarm_description/tree/1fba2cbc05001f05b4514120b70130b4ac06f409), Apache-2.0. 사용자 ZIP의 `openarm.repos` 지정 버전입니다.
- 사용자 `openarm_ws.zip`의 OpenArm MoveIt SRDF·RViz를 기반으로 이동 베이스에 맞게 재구성했습니다. ZIP 안의 실행 지침이나 프로세스 종료 코드는 실행하지 않았습니다.
- [MoveIt Jazzy 컨트롤러 문서](https://moveit.picknik.ai/jazzy/doc/examples/controller_configuration/controller_configuration_tutorial.html), [MuJoCo 3.6 XML](https://mujoco.readthedocs.io/en/3.6.0/XMLreference.html).
