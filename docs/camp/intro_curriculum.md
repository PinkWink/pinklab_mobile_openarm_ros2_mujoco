## 1. 이 패키지는 무엇인가

이 수업 자료의 바탕은 **MuJoCo + ROS 2 Jazzy 위에서 돌아가는 주행형 양팔 로봇 시뮬레이션 패키지**다. Vic Pinky 모바일 베이스 위에 OpenARM 양팔을 올린 로봇이 15 × 11 m 창고를 돌아다니며 상자를 집어 옮긴다.

- **물리 엔진은 MuJoCo, 로봇 소프트웨어는 ROS 2.** Gazebo 플러그인 대신 Python 브리지 하나가 MuJoCo를 스텝하면서 `/clock`, `/joint_states`, TF, `/odom`, `/scan`을 발행하고 `/cmd_vel`과 관절 궤적 액션을 받는다. ROS 2 쪽에서 보면 실제 로봇과 같은 인터페이스다.
- **주행.** 라이다·오도메트리를 SLAM Toolbox와 Nav2에 연결해 지도를 만들고 자율주행한다. 창고에는 걸어 다니는 사람과 지게차·팔레트 같은 소품이 있어 회피를 볼 수 있다.
- **양팔 Manipulation.** MoveIt으로 두 팔(각 7관절 + 그리퍼)을 계획하고, 작업대 앞에서 상자를 집어 다른 작업대에 놓는 Pick & Place 스킬이 들어 있다. 작업대 진입은 카메라가 본 ArUco 마커로 정밀 도킹한다.
- **카메라는 Python 직접 수신.** 영상은 ROS 토픽으로 흘리지 않고 시뮬레이터 프로세스 안의 Python 콜백으로 받아 검출 결과(물체 3D 위치, 마커)만 ROS 메시지로 낸다. 저사양 노트북에서도 실시간이 유지된다.
- **LMM 연결.** OpenAI API로 자연어 지령을 작업 단계 목록(이동 → 확인 → 집기 → 이동 → 놓기)으로 바꾸고, ROS 2 Task Manager가 그 순서대로 Nav2와 MoveIt을 부른다. LMM은 관절이나 속도를 직접 다루지 않는다.

### 구조

![패키지 구조](architecture.png)

블록선도는 위에서 아래로 네 층이다.

1. **지령 층 — 사용자 · LMM · Task Manager.** 사용자가 텍스트 콘솔이나 웹 대시보드에 문장을 입력하면 LMM(OpenAI API, Structured Outputs)이 이를 `navigate / detect / pick / place` 같은 단계 목록(RobotPlan)으로 바꾼다. ROS 2 Task Manager는 그 목록을 받아 단계를 순서대로 실행하고, 확인·중단·실패 보고를 맡으며, 결과를 문장으로 되돌려 준다. 이 층에서는 좌표나 관절 값이 나오지 않는다.
2. **실행 층 — Nav2 · PickPlace 스킬 · MoveIt.** `navigate` 단계는 Nav2(AMCL + costmap + planner)가 맡고, `pick / place` 단계는 PickPlace 스킬 서버가 맡는다. 스킬 서버는 Nav2로 작업대 앞 사전 도킹 지점까지 간 뒤 ArUco 마커 쌍으로 정밀 도킹하고, 카메라 검출로 상자 위치를 잡고, MoveIt으로 팔을 계획·실행해 집고 놓는다. 스킬 하나가 Nav2와 MoveIt을 함께 쓰는 구조를 여기서 본다.
3. **브리지 층 — MuJoCo ↔ ROS 2 브리지 · 카메라 핸들러.** 브리지는 MuJoCo를 일정 주기로 스텝하며 표준 ROS 2 인터페이스를 만든다. 나가는 것은 `/clock`, `/joint_states`, TF, `/odom`, `/scan`이고 들어오는 것은 `/cmd_vel`과 관절 궤적 액션이다. 카메라 핸들러는 같은 프로세스에서 렌더된 프레임을 받아 물체와 마커를 검출하고 `/vision/detections`, `/vision/markers`만 발행한다. 영상 토픽은 없다.
4. **물리 층 — MuJoCo 세계.** Vic Pinky 베이스 + OpenARM 양팔, 창고, 작업대 2개와 상자 3개, ArUco 마커, 사람·지게차 배우, 라이다, 카메라 4대가 한 모델 안에 있다.

한 줄로 요약하면, **"자연어 지령 → LMM → Task Planning → ROS 2 → Nav2 / MoveIt → MuJoCo → 로봇 행동"** 파이프라인이 처음부터 끝까지 하나의 워크스페이스에 들어 있는 패키지다. Ubuntu 24.04, ROS 2 Jazzy, 외장 GPU 없는 4코어 노트북에서 검증했다.

## 2. 수업 형식: 단기 과정

이 자료는 **단기 집중 수업**용이다. 수강생이 처음부터 코드를 짜는 수업이 아니라, GitHub에 배포된 완성 코드(https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco)를 단계별로 실행하면서 각 단계의 핵심 코드와 ROS / MuJoCo 연결 구조를 이해하고, 마지막에 전체 시스템을 연결해 보는 과정이다.

- 대상: ROS 2 기초를 아는 학부·대학원생.
- 진행: 모듈마다 개념 설명 → 핵심 코드 설명 → 따라 실행 → 결과 확인·문제 해결. 각 모듈은 `ros2 launch` 또는 스크립트 명령 하나로 실행된다.
- 환경: 수강생 본인 노트북(Ubuntu 24.04, 4코어·16 GB 이상, 내장 그래픽)에 사전 설치. 수업 중 설치 작업은 하지 않는다.
- 전반부 목표: ROS 2 Launch → MuJoCo → LiDAR → SLAM → Nav2까지 연결해 양팔 로봇이 창고에서 자율주행하는 상태.
- 후반부 목표: 자연어 명령 → LMM → Task Planning → ROS 2 → Nav2 / MoveIt → MuJoCo → 로봇 행동까지 전체 파이프라인 완성.

## 3. 커리큘럼

### 전반부 — MuJoCo + ROS 2 로봇 시스템 구축

| 모듈 | 내용 |
|---|---|
| ① Gazebo vs MuJoCo / 전체 Architecture | 두 시뮬레이터의 구조와 물리 연산 방식, ROS 2 연동 방식 비교, 장단점, 이 과정의 전체 파이프라인 |
| ② MuJoCo + ROS 2 연결 | 스텝 루프에서 Topic / TF / Joint State / Control 인터페이스를 만드는 브리지 구조, 최소 브리지 예제 |
| ③ OpenARM Mobile Dual-Arm Launch / Robot Description | 로봇 Launch, URDF/Xacro 통합 구조(베이스 → 양팔 → 센서), Joint·Link·TF 트리, URDF → MJCF 변환 |
| ④ Sensor / TF / Odometry / LiDAR | 라이다 → LaserScan, 바퀴 오도메트리 → /odom + TF, use_sim_time, 센서 프레임 |
| ⑤ SLAM | SLAM Toolbox와 MuJoCo 연결, 파라미터, 지도 생성·저장 |
| ⑥ Nav2 | AMCL, costmap, 경로 계획, 사람·장애물 회피, Goal Pose 자율주행 |
| 전반부 통합 Demo | Launch → MuJoCo → LiDAR → SLAM → Nav2 전체 연결 |

### 후반부 — MoveIt + Mobile Manipulation + LMM

| 모듈 | 내용 |
|---|---|
| ⑦ MoveIt + MuJoCo | MoveIt 패키지 구조, Planning Group / Planning Scene, MoveIt ↔ MuJoCo Joint Control 연결 |
| ⑧ Arm / End-Effector Control | IK, pose goal, Cartesian path, 그리퍼, 양팔 제어 |
| ⑨ Pick & Place | 작업대 앞에서 물체 위치 확인 → 접근 → 파지 → 들기 → 놓기, Planning Scene 물체 attach |
| ⑩ Navigation + Pick & Place 통합 | 주행 → 도킹 → 파지 → 운반 → 주행 → 도킹 → 놓기 상태 기계, ArUco 마커 정밀 도킹, End-to-End 운반 |
| ⑪ LMM + OpenAI API | LMM의 역할, 자연어 → Structured Command, 스키마 검증과 세계 검증의 분리, 변환 정확도 측정 |
| ⑫ LMM → ROS 2 Task Pipeline | 자연어 → 작업 단계 목록 → Task Manager가 Nav2 / MoveIt / Pick & Place 액션을 순차 실행, 되묻기·확인, 실패 복구 |
| ⑬ MuJoCo Web Dashboard | 브라우저에서 로봇 상태 모니터링과 자연어 지령 입력, ROS 2 / MuJoCo / 웹 통신 구조 |
| ⑭ Final Mission | 자연어 지령 → LMM 작업 순서 생성 → Task Manager 실행 → Nav2 이동 → MoveIt Pick → 이동 → Place |

### 핵심 파이프라인

사용자 자연어 명령 → LMM(OpenAI API) → Task Planning / Structured Command → ROS 2 Task Manager → Nav2 / MoveIt → MuJoCo → Mobile Dual-Arm Robot 행동.

예: "픽업 작업대로 이동해서 빨간 상자를 집고 적재 작업대로 옮겨." → Navigate(pick_table) → Detect(red parcel) → Pick → Navigate(place_table) → Place.

## 4. 이 과정에서 익히는 기술 스택

| 분야 | 기술 | 이 과정에서 직접 하는 것 | 모듈 |
|---|---|---|---|
| 물리 시뮬레이션 | MuJoCo, MJCF, Python 바인딩(`mujoco`) | 스텝 루프·액추에이터·센서(라이다 레이캐스트, 카메라 렌더)가 코드로 어떻게 돌아가는지 보고, Gazebo와 구조를 비교한다 | ①② |
| ROS 2 Jazzy | Topic / Service / Action, TF2, `use_sim_time`, launch 파일과 파라미터, lifecycle 노드, colcon 워크스페이스 | 시뮬레이터를 ROS 2 인터페이스로 감싼 브리지를 읽고, `ros2 topic / action / run tf2_tools` 로 시스템을 들여다본다 | ②③④ |
| 로봇 모델링 | URDF / Xacro, Joint · Link · TF 트리, URDF → MJCF 변환, robot_state_publisher | 모바일 베이스 + 양팔 + 센서를 합친 완성 모델의 구조를 읽고 RViz 에서 관절을 움직여 본다 | ③ |
| 센서와 위치 추정 | LaserScan, Odometry, TF(odom → base, map → odom) | 라이다·오도메트리가 어디서 만들어지고 어떤 프레임에 실리는지 확인한다 | ④ |
| SLAM · 자율주행 | SLAM Toolbox, Nav2(AMCL, costmap, planner, controller, behavior tree) | 지도를 만들고 저장한 뒤 Goal Pose 로 자율주행한다. 사람·장애물 회피, 파라미터의 효과를 본다 | ⑤⑥ |
| Manipulation | MoveIt 2(planning group, planning scene, IK `/compute_ik`, Cartesian path, 이름 자세), 그리퍼 액션, FollowJointTrajectory | 양팔 IK 와 경로 계획, 직선 이동, 그리퍼 제어를 Python 으로 호출하고 궤적이 시뮬레이터로 넘어가는 경로를 본다 | ⑦⑧ |
| 인지 | ArUco 마커 자세 추정, 배포된 YOLO 가중치(OpenVINO, CPU) 로 물체 검출, 깊이 → 3D 위치, TF 로 좌표 변환 | 카메라가 본 마커로 정밀 도킹하고, 검출 결과로 상자 위치를 잡아 집는다. 영상을 토픽으로 흘리지 않는 설계의 이유를 이해한다 | ⑨⑩ |
| Pick & Place · Mobile Manipulation | 스킬 서버(액션) 상태 기계, 도킹 → 파지 → 운반 → 놓기, planning scene attach/detach, 실패 복구 | 주행과 팔 동작이 하나의 액션으로 묶이는 구조를 실행하고 단계별 피드백을 읽는다 | ⑨⑩ |
| LMM · 프롬프트 엔지니어링 | OpenAI API, Structured Outputs(pydantic 스키마), few-shot, 스키마 검증과 세계 검증의 분리, 변환 정확도 측정, 비용 로그 | 자연어 지령을 구조화 명령과 작업 단계 목록으로 바꾸고 테스트셋으로 정확도를 잰다 | ⑪⑫ |
| Task Planning · 시스템 통합 | ROS 2 Task Manager(액션 서버), 단계 순차 실행, 확인·되묻기 대화, 인터록(주행 자세), 실패 보고 | LMM 이 만든 계획을 Nav2 / MoveIt / 스킬 액션으로 실행하는 파이프라인을 완성한다 | ⑫⑭ |
| 운영 · UI | 텍스트 콘솔(Utterance 토픽), 웹 대시보드(websocket ↔ ROS 2), RViz, MuJoCo viewer | 브라우저에서 로봇 상태를 보고 지령을 보내며 ROS 2 / MuJoCo / 웹 사이의 데이터 흐름을 설명할 수 있다 | ⑬ |
| 개발 도구 | Ubuntu 24.04, Python 3.12 venv, colcon, git, 설치·점검 스크립트 | 완성 코드를 clone 하고 빌드·점검해 실행한다. 저사양 노트북에서 실시간을 유지하는 설정(카메라 2대 320×240 2 FPS, CPU 추론)을 다룬다 | 전체 |

정리하면 **시뮬레이션 → ROS 2 → 주행 → Manipulation → 인지 → LMM → 통합**의 순서로 쌓이며, 각 층의 코드가 위 블록선도의 한 상자에 대응한다.

## 5. 코드 저장소

완성 코드는 GitHub 공개 저장소에 있다: **https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco**

- `src/` ROS 2 패키지 10개(로봇 description, MuJoCo 브리지, bringup, navigation, moveit_config, warehouse_interfaces / skills / lecture), `lessons/` 모듈별 실습 안내, `examples/` 단계별 예제, `weights/` 배포용 검출 가중치, `scripts/` 실행·설치 스크립트, `docs/` 사용 설명서와 검증 기록, `tests/` 단위 테스트.
- 설치는 저장소의 README와 `docs/lecture/00_setup.md`를 따른다. Ubuntu 24.04 + ROS 2 Jazzy(native) 기준이며 도커·VM은 지원하지 않는다.
- 교육과 협업 문의: contact@pinklab.art (https://pinklab.art)
