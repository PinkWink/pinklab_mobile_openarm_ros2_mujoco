# 00. 강좌 환경 설정 (Ubuntu 24.04 / ROS 2 Jazzy / GPU 없음)

이 문서는 강좌 6개 모듈이 공통으로 쓰는 환경을 만든다. 카메라 영상은 ROS 토픽 없이 시뮬레이터 프로세스 안의 Python 콜백으로만 처리하고, LLM·음성은 OpenAI API를 쓴다. 로컬 GPU는 필요 없다.

## 수강생 PC 최소 사양

| 항목 | 최소 | 비고 |
|---|---|---|
| CPU | 4코어 x86-64 (AVX2) | YOLO11n ONNX 320 입력 기준 프레임당 60ms 이하 목표 |
| RAM | 16 GB | 시뮬레이터 + Nav2 + MoveIt + YOLO 동시 구동 |
| GPU | 내장 그래픽 (OpenGL 3.3+) | MuJoCo 오프스크린 렌더링용. CUDA 불필요 |
| 디스크 | 20 GB 여유 | venv 약 2 GB, 데이터셋·가중치 포함 |
| OS | Ubuntu 24.04 + ROS 2 Jazzy (native) | `ros-jazzy-desktop` + Nav2 + MoveIt |
| 네트워크 | HTTPS로 api.openai.com 접근 | 강좌용 OpenAI 키 필요 |

## 설치

```bash
sudo apt install python3-venv python3-colcon-common-extensions python3-rosdep portaudio19-dev \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-moveit-ros-move-group ros-jazzy-moveit-kinematics ros-jazzy-moveit-planners-ompl \
  ros-jazzy-moveit-simple-controller-manager ros-jazzy-moveit-ros-visualization ros-jazzy-moveit-configs-utils \
  ros-jazzy-teleop-twist-keyboard ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-xacro ros-jazzy-robot-state-publisher \
  ros-jazzy-rviz2 ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-geometry-msgs
source /opt/ros/jazzy/setup.bash
# 처음 한 번: sudo rosdep init && rosdep update
./scripts/install_lecture.sh
```

설치 스크립트는 `.venv-mobile-openarm`(시스템 site-packages 공유)을 만들고 `requirements-mobile-openarm.txt`, `requirements-lecture.txt`를 설치한 뒤 9개 패키지를 빌드하고 단위 테스트를 돌린다.

`requirements-lecture.txt`의 고정 버전은 이유가 있다. 바꾸기 전에 읽어 둘 것.

| 고정 | 이유 |
|---|---|
| `numpy<2` | ROS Jazzy의 Python 스택(scipy, tf 변환 등)이 numpy 1.26 기준으로 빌드됨 |
| `opencv-python<4.11` | 4.11부터 numpy 2를 요구 |
| `setuptools<80` | colcon-core 0.20 요구사항 |
| `torch` CPU 인덱스 | CUDA 휠(수 GB)을 받지 않기 위해 |
| `ml-dtypes<0.6` | onnx가 끌어오는 최신 버전이 numpy 2 전용 |

## OpenAI 키

```bash
cp .env.example .env    # OPENAI_API_KEY=sk-... 입력
```

모델 이름·온도·가격표는 `src/warehouse_lecture/config/llm.yaml` 한 곳에서 관리한다. 모든 호출은 `logs/openai_usage.jsonl`에 토큰 수와 비용 추정이 기록된다. 강좌용 키는 프로젝트 단위로 발급하고 월 사용 한도를 걸어 둔다.

## 실행

명령 전체 목록과 인터페이스는 [../USAGE.md](../USAGE.md)에 있다. ros2 CLI는 `./scripts/mobile_openarm exec ros2 ...`로 실행한다(wrapper가 CycloneDDS와 domain 43을 설정한다).

새 터미널마다:

```bash
source /opt/ros/jazzy/setup.bash
source .venv-mobile-openarm/bin/activate
```

```bash
./scripts/mobile_openarm start                       # MuJoCo viewer + Nav2 + MoveIt + RViz, lite 프로파일
./scripts/mobile_openarm start rviz:=false           # RViz 없이 (저사양 권장)
./scripts/mobile_openarm start viewer:=false rviz:=false   # headless
./scripts/mobile_openarm start \
  camera_handler:=warehouse_lecture.vision.truth_detector:TruthDetector \
  camera_depth:=true camera_segmentation:=true       # 정답 검출기 핸들러 (M1·M3 기준선)
```

`profile:=lite`(기본)는 카메라 2대(`base_camera`, `head_camera`), 320×240, 2 FPS로 시작한다. `profile:=full`은 cameras.yaml의 4대·640×480·5 FPS를 쓴다. 개별 인자 `camera_names:=`, `camera_size:=`, `camera_fps:=`가 프로파일보다 우선한다. `actors:=none`을 붙이면 사람·소품 없이 원래 창고로 실행된다.

## 새로 추가된 것 (원본 ZIP 대비)

| 구분 | 내용 |
|---|---|
| `worlds/actors.yaml` | 사람 4명(안전모 2/2, 조끼·셔츠·키 변형), 지게차, 팔레트, 콘 2, 소화기. mocap body라 라이다·카메라에 보이고 정적 지도에는 없음 |
| `/warehouse/actor_states` | 배우 실제 위치·속성(ground truth). 평가·자동 라벨링용 |
| `/warehouse/set_actor` 서비스 | teleport / set_path / set_attributes / pause / resume |
| 카메라 핸들러 프로토콜 | `setup(context)`·`close()` 훅, `context.node`로 ROS 발행·TF 조회, `--camera-names/--camera-size/--camera-segmentation` |
| `CameraFrame.segmentation` | 픽셀별 MuJoCo body id (YOLO 자동 라벨의 근거) |
| `warehouse_interfaces` | ActorState, Detection3D, Encounter, RobotCommand, Utterance, VisionStats / SetActor, QueryEncounters, AskRobot / PickPlace, ExecuteCommand |
| `warehouse_lecture` | `ros/handler_base.py`(워커 스레드 + 적응형 FPS), `ros/geometry.py`(역투영·TF), `vision/labels.py`, `vision/truth_detector.py`, `vision/aruco.py`, `vision/pipeline.py`(기본 핸들러 = ArUco + 정답 검출), `llm/client.py`, `speech/`, `memory/locations.py` |
| `warehouse_skills` | `/pick_place` 액션 서버, MoveIt·Nav2·도킹 클라이언트, `config/skills.yaml` |
| bridge 콜백 처리 | 틱당 ROS 콜백 8개 처리 (`rates.ros_callbacks_per_tick`). 핸들러가 /tf를 구독해도 지연 없음 |

## 운반 스킬 (PickPlace)

강좌 M4·M5의 "어디서 어디로 물건 옮겨" 명령이 호출하는 기반 스킬이다. `start`(moveit:=true) 시 `/pick_place` 액션 서버가 함께 뜬다.

```bash
./scripts/mobile_openarm pick red pick_table place_table     # 색 또는 parcel_1..3
```

| 단계 | 방법 |
|---|---|
| navigate | Nav2로 `locations.yaml`의 사전 도킹 지점(작업대 앞 약 1 m)까지만 이동 |
| dock | 작업대 다리에 걸린 **ArUco 마커 2개**(베이스 카메라, Python 핸들러)로 시각 서보 → 마지막 0.3 m는 오도메트리 직진. 잔차 1~5 cm |
| locate | 물체의 base_footprint 기준 위치 (`locate:=truth` 기본, `vision`은 M3 이후) |
| grasp | 물체 옆에 있는 팔 자동 선택 → MoveIt IK 사전 파지 → 직선 접근 → 그리퍼(정지 위치로 파지 판정) → planning scene 부착 |
| carry | `hands_up` 자세(상자가 베이스·상판 위를 지남)로 후진 0.75 m → Nav2 |
| place | 마커 기준 슬롯(y −0.25/0/+0.25)에 내려놓고 분리 → transport 복귀 |

원본 대비 바뀐 물리·설정: `drive_poses.yaml`(주행 허용 자세 transport/ready/hands_up), `mujoco.yaml`의 `noslip_iterations: 5`(파지 물체 creep 방지), Nav2 `inflation_radius 0.55`, MoveIt `fix_start_state: true`, 궤적 한계 허용 오차 1e-3. parcel은 작업대 앞 가장자리(x 2.18)에 있고, 마커는 `warehouse.yaml`의 `markers`에 정의한다. 라이다 기반 V자 홈 도킹은 대안으로 남겨 두었다(마커 도킹이 실환경에서 불안정하면 전환).

## 검증

```bash
python -m pytest tests -q                                   # 시뮬레이터 불필요, 약 1.5분
python scripts/check_mobile_openarm.py --nav                # 원본 통합 검사 (start 후 다른 터미널)
python scripts/check_actors_live.py --nav                   # 배우·정답 검출·속성 변경·Nav2 회피 (기본 파이프라인으로 start 후)
./scripts/mobile_openarm pick red                           # 운반 스킬 끝까지 (약 3분)
```

## 자주 겪는 문제

- **`ModuleNotFoundError: mujoco`로 bridge가 죽음**: venv를 활성화하지 않고 `ros2 launch`를 직접 실행한 경우. `./scripts/mobile_openarm start`를 쓰거나 venv를 먼저 활성화한다.
- **`numpy.dtype size changed`**: venv에 numpy 2가 들어간 경우. `pip install "numpy<2"` 후 `rm -rf build/warehouse_interfaces install/warehouse_interfaces`하고 다시 빌드한다(CMake가 numpy 헤더 경로를 캐시한다).
- **zsh에서 `setup.bash` 오류**: ROS 스크립트는 bash 전용이다. bash를 쓰거나 `setup.zsh`를 source한다.
- **음성 없음**: 강좌는 텍스트 입출력만 쓴다(마이크·스피커 불필요).
