# 사용 설명서 — Vic Pinky + OpenArm 창고 시뮬레이터 (강좌 확장판)

기준: Ubuntu 24.04, ROS 2 Jazzy native, GPU 없음. 2026-09-21 기준 Phase 0 완료 상태.
설치는 [lecture/00_setup.md](lecture/00_setup.md), 강좌 계획은 `../LECTURE_PLAN.md`, 원본 패키지 설명은 [MOBILE_OPENARM.md](MOBILE_OPENARM.md)를 본다.

## 1. 터미널 준비

모든 터미널에서 먼저 실행한다. 셸이 zsh이면 `setup.zsh`, bash이면 `setup.bash`.

```bash
cd ~/mujoco_ros2/mobile_openarm_ws
source /opt/ros/jazzy/setup.zsh
source .venv-mobile-openarm/bin/activate
```

**ros2 CLI는 wrapper를 거치거나(`exec`), `scripts/env.sh`를 source 한 셸에서 실행한다.** wrapper가 CycloneDDS, `ROS_DOMAIN_ID=43`, localhost 통신을 설정하므로, 아무 설정 없는 셸에서 `ros2 topic list`를 치면 다른 미들웨어로 붙어 아무것도 보이지 않는다. 직접 실행 방법은 2-1절.

```bash
./scripts/mobile_openarm exec ros2 topic list
./scripts/mobile_openarm exec ros2 topic echo /warehouse/actor_states --once
```

## 2. wrapper 명령 한눈에

| 명령 | 동작 |
|---|---|
| `./scripts/mobile_openarm build` | 10개 패키지 colcon 빌드 (symlink install) |
| `start` (= `nav`) | MuJoCo + Nav2(정적 지도, AMCL) + MoveIt + RViz + 운반 스킬 서버 + 카메라 파이프라인 |
| `drive` | MuJoCo + 주행 RViz만 (Nav2·MoveIt 없음) |
| `slam` | SLAM Toolbox로 지도 작성 |
| `moveit` | MuJoCo + MoveIt (Nav2 없음) |
| `display` | **URDF만** RViz + joint slider (시뮬레이터와 동시 실행 금지) |
| `goal X Y [YAW]` | Nav2 목표 한 번 보내고 결과 대기 |
| `arm {left|right|both} {transport|ready|hands_up|home}` | MoveIt 이름 자세 계획·실행 (`--plan-only`) |
| `pick OBJ [FROM] [TO] [--phase pick|place]` | 운반 스킬 (`red`/`blue`/`yellow` 또는 `parcel_1..3`, 기본 pick_table → place_table). `--phase pick`: 도킹·파지·운반 자세까지, `--phase place`: 든 상자를 TO 에 놓기 |
| `teleop` | 키보드 주행 (i/,/j/l/k) |
| `exec CMD...` | wrapper 환경에서 임의 명령 실행 (ros2 CLI, pytest, 스크립트) |
| `shell` | wrapper 환경의 bash |

`./scripts/cleanup_ros.sh`는 이전 세션이 남긴 Nav2·MoveIt·시뮬레이터 프로세스를 모두 종료한다. 액션이 거부되거나 `navigate_to_pose unavailable`이 나오면 먼저 이것을 실행한다.

## 2-1. wrapper 없이 ros2 launch / ros2 run 으로 실행

wrapper는 환경변수를 설정하고 아래 명령을 대신 실행할 뿐이다. 직접 실행하려면 먼저 같은 환경을 만든다.

```bash
source /opt/ros/jazzy/setup.zsh      # bash: setup.bash
source scripts/env.sh                # venv 활성화, install/local_setup, domain 43, CycloneDDS, 모델 캐시 경로
```

`scripts/env.sh`가 설정하는 것: `ROS_DOMAIN_ID=43`, `ROS_LOCALHOST_ONLY=1`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` + `CYCLONEDDS_URI`, `ROS_HOME`/`ROS_LOG_DIR`(`.ros/mobile_openarm`), `MOBILE_OPENARM_MODEL_DIR`(`artifacts/mobile_generated`), `PYTHONNOUSERSITE=1`.

**왜 CycloneDDS인가.** 이 프로젝트에서 새로 고른 것이 아니라 원본 ZIP(2026-09-19, macOS RoboStack에서 검증)이 wrapper와 `environment.yml`에 이미 CycloneDDS를 지정하고 있었고, 선택 이유는 원본 문서에 남아 있지 않다. 짐작되는 배경은 두 가지다. macOS RoboStack에서는 FastDDS의 공유메모리 전송이 자주 문제를 일으켜 CycloneDDS를 쓰는 것이 관례이고, `src/mobile_openarm_bringup/config/cyclonedds.xml`처럼 127.0.0.1 unicast 전용(멀티캐스트 끔, peer 127.0.0.1)으로 통신을 이 PC 안에 가두는 설정을 XML 한 장으로 강제하기 쉽다. domain 43과 함께 수강생 여러 명이 같은 네트워크에서 실습해도 토픽이 섞이지 않게 하려는 의도로 읽힌다. Ubuntu native Jazzy에서는 기본 RMW(FastDDS)로도 시뮬레이터와 운반 스킬이 정상 동작함을 확인했으므로(2026-09-22), CycloneDDS가 없으면 wrapper와 env.sh가 기본 RMW로 폴백한다. 다만 시뮬레이터와 CLI의 RMW가 다르면 커스텀 메시지 토픽(`/vision/stats` 등)이 보이지 않고, `ros2` 데몬은 처음 띄운 셸의 RMW를 유지하므로 RMW를 바꿨을 때 `ros2 topic list`에 토픽이 2개만 보이면 `ros2 daemon stop` 후 다시 실행한다. 강좌에서는 한 PC의 모든 터미널이 같은 RMW를 쓰도록 wrapper `exec` 또는 `env.sh`만 사용한다.

**주의: `ros2 launch`는 venv Python으로 실행해야 한다.** `/opt/ros/jazzy/bin/ros2`의 인터프리터는 시스템 Python이고, launch가 MuJoCo bridge를 자기 인터프리터로 띄우므로 그냥 `ros2 launch`를 치면 bridge가 `ModuleNotFoundError: mujoco`로 죽는다. `env.sh`가 만든 `ros2launch` alias를 쓰거나 `python "$(command -v ros2)" launch ...`로 실행한다. `ros2 run`은 설치된 실행 파일이 venv 인터프리터를 가리키므로 그대로 써도 된다.

| wrapper | 직접 실행 |
|---|---|
| `start`, `nav` | `ros2launch mobile_openarm_bringup warehouse.launch.py mode:=nav` |
| `drive` | `ros2launch mobile_openarm_bringup warehouse.launch.py mode:=drive moveit:=false` |
| `slam` | `ros2launch mobile_openarm_bringup warehouse.launch.py mode:=slam moveit:=false` |
| `moveit` | `ros2launch mobile_openarm_bringup warehouse.launch.py mode:=drive moveit:=true` |
| `display` | `ros2 launch mobile_openarm_description display.launch.py` (bridge가 없으므로 시스템 `ros2 launch`도 됨) |
| `goal X Y YAW` | `ros2 run mobile_openarm_navigation goal X Y YAW` |
| `arm SIDE POSE` | `ros2 run mobile_openarm_moveit_config joint_goal SIDE POSE` |
| `pick OBJ FROM TO` | `ros2 run warehouse_skills pick_place OBJ FROM TO` |
| `teleop` | `ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p speed:=0.25 -p turn:=0.5` |
| (운반 스킬 서버만 따로) | `ros2 run warehouse_skills pick_place_server --ros-args -p use_sim_time:=true -p locate:=truth` |
| (MoveIt만 기존 시뮬레이터에 추가) | `ros2 launch mobile_openarm_moveit_config moveit.launch.py urdf_file:=artifacts/mobile_generated/robot.urdf` |
| (Nav2만 기존 시뮬레이터에 추가) | `ros2 launch mobile_openarm_navigation navigation.launch.py mode:=nav map:=$(ros2 pkg prefix mobile_openarm_navigation)/share/mobile_openarm_navigation/maps/warehouse.yaml` |

launch 인자(`viewer:=false rviz:=false camera_handler:=... actors:=none` 등)는 3절과 같다. 직접 실행할 때도 시뮬레이터는 한 번에 하나만 띄운다.

액션·서비스 직접 호출 예:

```bash
ros2 action send_goal /pick_place warehouse_interfaces/action/PickPlace \
  "{object: red, from_station: pick_table, to_station: place_table, arm: ''}" --feedback
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 1.0, y: 0.6}, orientation: {w: 1.0}}}}"
ros2 action send_goal /left_gripper_controller/gripper_cmd control_msgs/action/GripperCommand \
  "{command: {position: 0.035, max_effort: 15.0}}"
ros2 service call /warehouse/set_actor warehouse_interfaces/srv/SetActor \
  "{name: cone_1, operation: teleport, pose: {position: {x: 1.5, y: 0.0}, orientation: {w: 1.0}}}"
```

## 3. 시뮬레이터 실행과 launch 인자

```bash
./scripts/mobile_openarm start                         # 기본 (lite 프로파일)
./scripts/mobile_openarm start rviz:=false             # 저사양 PC 권장
./scripts/mobile_openarm start viewer:=false rviz:=false   # headless
```

준비 완료 신호는 터미널의 `Managed nodes are active`, `You can start planning now!`, `PickPlace server ready` 세 줄이다. 종료는 Ctrl+C. 한 번에 시뮬레이터 하나만 실행한다(lock 파일로 막는다).

| 인자 | 기본값 | 의미 |
|---|---|---|
| `mode` | nav | drive / slam / nav |
| `profile` | lite | lite: 카메라 2대(base, head) 320×240 2 FPS. full: cameras.yaml(4대 640×480 5 FPS) |
| `viewer`, `rviz`, `moveit` | true | 각각 MuJoCo 창, RViz, MoveIt 기동 |
| `skills` | true | `/pick_place` 액션 서버 (moveit:=true일 때) |
| `locate` | truth | 운반 스킬의 물체 위치 출처. truth = 시뮬레이터 실제값, vision = 카메라 검출 (M3 이후) |
| `camera_handler` | `warehouse_lecture.vision.pipeline:LecturePipeline` | 시뮬레이터 프로세스 안에서 도는 Python 카메라 핸들러. `none`이면 카메라 렌더링 안 함 |
| `camera_names`, `camera_size`, `camera_fps` | 프로파일 값 | 렌더 카메라 부분 선택, 해상도 `WxH`, 시뮬레이션 시간 기준 FPS |
| `camera_depth`, `camera_segmentation` | true | 깊이, 픽셀별 body id 렌더 |
| `actors` | 패키지 actors.yaml | 배우 정의 파일 경로. `none`이면 사람·소품 없음 |
| `map` | 패키지 warehouse.yaml | 정적 지도. `map:=''`이면 SLAM + Nav2 |
| `spawn` | (원점) | 로봇 시작 위치: locations.yaml 이름(`pick_table`, `place_table`, `rack_c` …) 또는 `X,Y,YAW`. MuJoCo 위치와 AMCL 초기 위치를 함께 맞춘다. 강의 06 모듈용 |

## 4. 창고 구성

- 크기 15 × 11 m. 랙 6개(x = −5.5, −2.6, 5.5; y = ±2.7), 픽업 작업대 (2.6, −3.6), 적재 작업대 (2.6, 3.6). 상판 높이 0.78 m.
- parcel_1(빨강)·2(파랑)·3(노랑): 45×45×60 mm, 픽업 작업대 앞 가장자리 x = 2.18, y = −3.85 / −3.55 / −3.25.
- ArUco 마커(DICT_4X4_50): 작업대 다리 평면 x = 2.22, 높이 0.30 m, 작업대마다 2개(id 0·1 픽업, 2·3 적재), 축 기준 y ±0.22. 라이다와 정적 지도에는 보이지 않고 카메라에만 보인다.
- 배우(`src/mobile_openarm_mujoco/worlds/actors.yaml`): 사람 4명(안전모 착용 2, 미착용 2, 조끼·셔츠·키 다름, 2명은 통로 왕복), 지게차, 팔레트, 콘 2, 소화기. 라이다와 카메라에 보이고 정적 지도에는 없으며 로봇과 물리 접촉은 없다.
- 이름 있는 장소(`src/warehouse_lecture/worlds/locations.yaml`): pick_table, place_table, rack_a~f, center_aisle 등과 한국어 별칭, 사전 도킹 좌표, 순찰 경로.

## 5. ROS 인터페이스

원본 인터페이스(`/cmd_vel`, `/odom`, `/scan`, `/joint_states`, `/tf`, `/clock`, `/ground_truth`, `/warehouse/object_poses`, MoveIt·그리퍼 액션)는 [MOBILE_OPENARM.md](MOBILE_OPENARM.md) 참고. 강좌에서 추가한 것:

| 인터페이스 | 타입 | 내용 |
|---|---|---|
| `/warehouse/actor_states` | `ActorStateArray` | 배우 실제 위치·속도·속성(helmet, vest, shirt, height). 평가용 ground truth |
| `/warehouse/set_actor` | `SetActor` 서비스 | `teleport` / `set_path` / `set_attributes` / `pause` / `resume` |
| `/vision/detections` | `Detection3DArray` | 정답 검출기 출력. 클래스, bbox, map 좌표, 사람 속성(helmet/vest) |
| `/vision/detections_2d` | `vision_msgs/Detection2DArray` | 같은 검출의 2D 표준 형식 |
| `/vision/markers` | `ArucoMarkerArray` | 베이스 카메라가 본 ArUco 마커의 base_footprint 기준 자세 |
| `/vision/stats`, `/vision/stats/aruco` | `VisionStats` | 캡처 FPS, 실시간 비율, 추론 시간, 드롭 프레임 |
| `/pick_place` | `PickPlace` 액션 | 운반 스킬 (object, from_station, to_station, arm, phase=all/pick/place) |
| `/execute_command` | `ExecuteCommand` 액션 | 한 문장 명령 실행기 (`ros2 run warehouse_lecture command_executor`) |
| `/execute_plan` | `ExecutePlan` 액션 | 단계 목록(RobotPlan) 실행 Task Manager (`ros2 run warehouse_lecture task_manager`, /execute_command 도 함께 제공) |
| `/warehouse_scene/attached` | `std_msgs/String` | planning scene에 부착 중인 물체 이름 (스킬 내부용) |

**카메라 영상 토픽은 없다.** `Image`, `CameraInfo`가 검색되지 않는 것이 정상이다.

배우 조작 예:

```bash
./scripts/mobile_openarm exec ros2 service call /warehouse/set_actor warehouse_interfaces/srv/SetActor \
  "{name: worker_no_helmet_red, operation: teleport, pose: {position: {x: 3.0, y: 0.3}, orientation: {z: 1.0, w: 0.0}}}"
./scripts/mobile_openarm exec ros2 service call /warehouse/set_actor warehouse_interfaces/srv/SetActor \
  "{name: worker_no_helmet_red, operation: set_attributes, attributes: [{key: helmet, value: 'true'}]}"
```

## 6. 카메라 핸들러 (Python 전용 영상 처리)

핸들러는 시뮬레이터 프로세스 안에서 `handler(frames)`로 호출된다. `frames[name]`은 `CameraFrame`(rgb, depth_m, segmentation, K, T_world_optical, sim_time). 객체 핸들러는 `setup(context)`·`close()` 훅을 가질 수 있고, `context.node`로 ROS 발행·구독·TF를 쓴다. 자세한 규약은 [MOBILE_CAMERAS.md](MOBILE_CAMERAS.md)와 `src/mobile_openarm_mujoco/mobile_openarm_mujoco/handler.py`.

| 핸들러 | 역할 |
|---|---|
| `warehouse_lecture.vision.pipeline:LecturePipeline` (기본) | 아래 두 개를 합성. 환경변수 `LECTURE_HANDLERS="mod:attr,mod:attr"`로 구성 변경 |
| `warehouse_lecture.vision.aruco:ArucoDetector` | 마커 검출 → `/vision/markers` |
| `warehouse_lecture.vision.truth_detector:TruthDetector` | 세그멘테이션 정답 검출 → `/vision/detections` |
| `mobile_openarm_mujoco.camera_demo:handle_frames` | 시뮬레이션 1초마다 PNG 저장 (`artifacts/mobile_generated/cameras/`) |

카메라가 보는 화면을 파일로 확인하려면:

```bash
LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.truth_detector:TruthDetector,mobile_openarm_mujoco.camera_demo:handle_frames" \
  ./scripts/mobile_openarm start
```

무거운 처리는 `warehouse_lecture/ros/handler_base.py`의 `WorkerHandler`를 상속해 `prepare`(물리 스레드) → `process`(워커 스레드) → `publish`(물리 스레드)로 나눈다. 시뮬레이션이 실시간보다 느려지면 캡처 FPS를 자동으로 낮춘다.

## 7. 운반 스킬 (PickPlace)

```bash
./scripts/mobile_openarm pick red                       # pick_table → place_table
./scripts/mobile_openarm pick parcel_3 pick_table place_table --arm left
```

단계와 화면에서 볼 것:

1. `navigate_pick`: Nav2로 작업대 앞 사전 도킹 지점(x 1.2)까지.
2. `dock`: 베이스 카메라의 ArUco 마커 2개로 시각 서보 → 마지막 0.25 m는 오도메트리 직진. 베이스는 작업대 축 중앙에 선다. Nav2 잔차가 10 cm를 넘으면 오도메트리 옆걸음(90° 회전-직진-복귀) 후 진행.
3. `locate` → `pre_grasp` → `grasp`: 물체가 있는 쪽 팔 자동 선택, 전방 수평 파지(tcp는 상자 중심 2 cm 위), 손가락 정지 위치 16~28 mm면 파지 성공.
4. `lift` → `carry`: 4 cm 들어 14 cm 후퇴 후 hands_up 자세(상자가 베이스·상판 위를 지남)로 0.75 m 후진.
5. `navigate_place` → `dock` → `place`: 마커 축 기준 슬롯(y −0.25 / 0 / +0.25 중 팔이 닿는 빈 자리)에 내려놓고 분리 → transport 복귀 → 후진.

결과는 `status=4 success=True`와 놓인 위치·슬롯 오차로 출력된다. 회당 약 2.5분. 상자는 세계가 초기화되지 않으므로 반복 시험은 시뮬레이터를 재시작한다. 파라미터는 `src/warehouse_skills/config/skills.yaml`(도킹 거리·속도, 파지 높이·힘, 슬롯 오프셋, MoveIt 설정).

## 8. URDF만 보기

```bash
./scripts/mobile_openarm display            # RViz(RobotModel, TF) + joint slider
./scripts/mobile_openarm display gui:=false # 슬라이더 없이
```

팔 기둥은 바퀴 축(base_link x=0, 차동구동 회전 중심)에 있고, 장착 높이는 z=0.13이다. 바꾸려면 `src/mobile_openarm_description/urdf/mobile_openarm.urdf.xacro`의 `mount_x`, `mount_z`. 장착점을 옮기면 `skills.yaml`의 `dock.target_dx`(어깨에서 물체까지 0.52 m 유지)도 같이 조정한다.

## 9. 검증 절차

```bash
./scripts/mobile_openarm exec python -m pytest tests -q          # 33개, 시뮬레이터 불필요, 약 1.2분
# start 후 다른 터미널에서 (로봇이 실제로 움직인다)
./scripts/mobile_openarm exec python scripts/check_mobile_openarm.py --nav   # 원본 통합 검사
./scripts/mobile_openarm exec python scripts/check_actors_live.py --nav      # 배우·검출·속성 변경·사람 회피
./scripts/mobile_openarm pick red && ./scripts/mobile_openarm pick blue      # 오른팔·왼팔 운반
```

라이브 검사는 JSON을 출력하며 `"passed": true`를 확인한다. `artifacts/*.json`에 결과가 남는다.

## 10. 자주 수정하는 설정

| 대상 | 파일 |
|---|---|
| 사람·소품 배치, 속성, 경로 | `mobile_openarm_mujoco/worlds/actors.yaml` |
| 랙·작업대·상자·마커·스테이션 | `mobile_openarm_mujoco/worlds/warehouse.yaml` (창고 형상 변경 후 `scripts/generate_warehouse_map.py`) |
| 물리, 주행 제한, 틱당 ROS 콜백 수, noslip | `mobile_openarm_mujoco/config/mujoco.yaml` |
| 주행 허용 팔 자세 | `mobile_openarm_description/config/drive_poses.yaml` |
| 카메라 위치·FOV·해상도 | `mobile_openarm_description/config/cameras.yaml` |
| Nav2 (팽창 반경 0.55 등) | `mobile_openarm_navigation/config/nav2.yaml` |
| MoveIt 계획 (`fix_start_state` 등) | `mobile_openarm_moveit_config/config/ompl_planning.yaml` |
| 운반 스킬 | `warehouse_skills/config/skills.yaml` |
| 이름 있는 장소·순찰 경로 | `warehouse_lecture/worlds/locations.yaml` |
| OpenAI 모델·가격표 | `warehouse_lecture/config/llm.yaml`, 키는 `.env` |

경로는 모두 `src/` 아래. YAML만 바꾸면 재시작으로 반영되고, 새 파일을 추가했으면 `build`가 필요하다.

## 11. 문제 해결

- **ros2 CLI에 아무것도 안 보임**: wrapper 없이 실행한 경우. `./scripts/mobile_openarm exec ros2 ...`.
- **액션 거부, Nav2 없음, 노드 중복**: `./scripts/cleanup_ros.sh` 후 다시 `start`.
- **bridge가 `ModuleNotFoundError: mujoco`로 죽음**: venv 미활성화 터미널.
- **`numpy.dtype size changed`**: venv에 numpy 2가 들어감. `pip install "numpy<2"`, `rm -rf build/warehouse_interfaces install/warehouse_interfaces`, 재빌드.
- **도킹 중 마커를 못 찾음**: 사전 도킹에서 크게 틀어진 경우. 자동 회전 탐색 후에도 실패하면 `pick`을 다시 실행.
- **파지 후 상자를 떨어뜨림**: `mujoco.yaml`의 `noslip_iterations`가 0이면 발생. 5로 둔다.
- **display와 start를 같이 켜면 모델이 겹침**: 둘 다 `/joint_states`, `/tf`를 발행한다. 하나만 실행.
