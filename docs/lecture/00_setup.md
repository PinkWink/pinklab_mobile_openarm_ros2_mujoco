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

ROS 2 Jazzy(`ros-jazzy-desktop`)를 [공식 안내](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)대로 설치한 뒤, 나머지는 스크립트 하나로 끝난다.

```bash
git clone https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco.git
cd pinklab_mobile_openarm_ros2_mujoco
./scripts/install_lecture.sh        # sudo 비밀번호를 한 번 묻는다
./scripts/mobile_openarm doctor     # 환경 점검. 결과를 강사에게 보낸다
```

- `install_lecture.sh`가 하는 일: ROS 환경 자동 source → `scripts/apt_packages.txt`의 apt 패키지 중 빠진 것 설치 → `rosdep init/update`(처음 한 번) → `.venv-mobile-openarm`(시스템 Python + 시스템 site-packages 공유) 생성 → `requirements-mobile-openarm.txt`, `requirements-lecture.txt` 설치 → 의존성 충돌 검사 → 9개 패키지 빌드 → 단위 테스트. 여러 번 실행해도 안전하다.
- conda base가 켜진 터미널이어도 된다. venv는 항상 `/usr/bin/python3`로 만들고, 예전에 conda Python으로 만든 venv가 있으면 다시 만든다.
- 의존성 충돌 검사(`scripts/check_pip_deps.py`)는 강의와 무관한 apt 패키지끼리의 충돌(예: `yt-dlp ... has requirement websockets>=12.0, but you have websockets 10.4`)은 `WARN`으로만 보여 주고 넘어간다. `ERROR`가 나오면 그 줄을 강사에게 보낸다.

### 수업 전 점검 (`doctor`)

```bash
./scripts/mobile_openarm doctor          # 약 10초
./scripts/mobile_openarm doctor --api    # OpenAI 키를 넣은 뒤: API 실제 호출까지 확인
```

OS·CPU·RAM·디스크, apt 패키지, venv·Python 패키지 버전, 빌드, MuJoCo 오프스크린 렌더링 속도, OpenAI 키를 ✅/⚠️/❌로 보여 준다. ❌가 하나도 없으면 수업 준비 완료다. 결과는 `artifacts/doctor_report.txt`에 저장되므로 이 파일이나 화면 캡처를 수업 1주 전까지 강사에게 보낸다.

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

**새 터미널에서 source 할 필요가 없다.** `./scripts/mobile_openarm`이 ROS 2 Jazzy와 강좌 venv를 스스로 켠다. `ros2 ...`를 직접 치고 싶으면 그 터미널에서 `source scripts/env.sh` 한 줄만 실행한다(ROS·venv·domain 43·CycloneDDS를 한 번에 설정).

```bash
./scripts/mobile_openarm start                       # MuJoCo viewer + Nav2 + MoveIt + RViz, lite 프로파일
./scripts/mobile_openarm start rviz:=false           # RViz 없이 (저사양 권장)
./scripts/mobile_openarm start viewer:=false rviz:=false   # headless
./scripts/mobile_openarm start \
  camera_handler:=warehouse_lecture.vision.truth_detector:TruthDetector \
  camera_depth:=true camera_segmentation:=true       # 정답 검출기 핸들러 (M1·M3 기준선)
```

실행 설정은 작업 공간 맨 위 `sim_config.yaml`에 있고 실행할 때마다 읽힌다(빌드 불필요, 명령줄 인자가 우선). `profile: lite`(기본)는 카메라 2대(`base_camera`, `head_camera`), 320×240, 2 FPS로 시작한다. `full`은 cameras.yaml의 4대·640×480·5 FPS, `minimal`은 lite에 더해 뷰어 로봇을 충돌 형상으로 그리고 카메라 그림자를 끈다. 개별 항목 `camera_names`, `camera_size`, `camera_fps` 등이 프로파일보다 우선한다. `actors:=none`을 붙이면 사람·소품 없이 원래 창고로 실행된다.

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

- **설치 중 `pip 의존성 충돌이 있습니다`**: `ERROR:` 줄을 확인한다. `WARN`만 있으면 문제없다(강의와 무관한 apt 패키지 충돌). `ERROR`는 venv 패키지 버전 문제이므로 `requirements-lecture.txt`를 고치지 말고 그 줄을 강사에게 보낸다.
- **`강좌 venv(.venv-mobile-openarm)가 없습니다`**: 설치가 중간에 멈춘 경우. `./scripts/install_lecture.sh`를 다시 실행한다.
- **무엇이 문제인지 모를 때**: `./scripts/mobile_openarm doctor`의 ❌ 줄부터 해결한다.
- **`위 프로세스가 이전 실행에서 남아 있습니다`로 start가 멈춤**: 터미널을 닫았거나 시뮬레이터가 죽어서 노드(pick_place_server, move_group, Nav2 등)가 남은 경우. 그대로 다시 띄우면 같은 이름의 액션 서버가 둘이 되어 한 명령을 두 번 실행한다(팔이 멈추고 `Cannot push a new trajectory`). `./scripts/mobile_openarm stop`으로 정리한 뒤 다시 실행한다.
- **`ModuleNotFoundError: mujoco`로 bridge가 죽음**: wrapper 없이 `ros2 launch`를 직접 실행한 경우. `./scripts/mobile_openarm start`를 쓰거나 `source scripts/env.sh` 후 `ros2launch ...`로 실행한다.
- **`numpy.dtype size changed`**: venv에 numpy 2가 들어간 경우. `pip install "numpy<2"` 후 `rm -rf build/warehouse_interfaces install/warehouse_interfaces`하고 다시 빌드한다(CMake가 numpy 헤더 경로를 캐시한다).
- **zsh에서 `setup.bash` 오류**: ROS 스크립트는 bash 전용이다. bash를 쓰거나 `setup.zsh`를 source한다.
- **음성 없음**: 강좌는 텍스트 입출력만 쓴다(마이크·스피커 불필요).
