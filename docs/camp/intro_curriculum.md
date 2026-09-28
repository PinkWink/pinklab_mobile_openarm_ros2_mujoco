## 1. 이 패키지는 무엇인가

### 한 줄 소개

![패키지 개요](intro_overview.png){width=1000}

- MuJoCo + ROS 2 Jazzy 위에서 돌아가는 주행형 양팔 로봇 시뮬레이션 패키지다.
- Vic Pinky 모바일 베이스 위에 OpenARM 양팔을 올렸다.
- 로봇은 15 × 11 m 창고를 돌아다니며 상자를 집어 옮긴다.
- 시뮬레이터는 Gazebo가 아닌 MuJoCo다. Gazebo는 설치하지 않는다.
- MuJoCo를 Gazebo처럼 ROS 2에 연결하는 방법을 먼저 다룬다.
- 이후 주행(SLAM · Nav2), 양팔 Manipulation(MoveIt), LMM 연동까지 모두 MuJoCo 위에서 실습한다.

### 물리 엔진은 MuJoCo, 로봇 소프트웨어는 ROS 2

![MuJoCo ↔ ROS 2 브리지](intro_bridge.png){width=1000}

- Gazebo 플러그인 대신 Python 브리지 하나가 MuJoCo를 스텝한다.
- 브리지가 `/clock`, `/joint_states`, TF, `/odom`, `/scan`을 발행한다.
- 브리지가 `/cmd_vel`과 관절 궤적 액션을 받는다.
- ROS 2 쪽에서 보면 실제 로봇과 같은 인터페이스다.

### 주행

![주행 스택](intro_nav.png){width=1000}

- 라이다와 오도메트리를 SLAM Toolbox에 연결해 지도를 만든다.
- Nav2가 그 지도 위에서 자율주행한다.
- 창고에는 걸어 다니는 사람과 지게차 · 팔레트가 있다. 회피 동작을 눈으로 확인할 수 있다.

### 양팔 Manipulation

![양팔 Manipulation](intro_manip.png){width=1000}

- MoveIt으로 두 팔(각 7관절 + 그리퍼)을 계획한다.
- 작업대 앞에서 상자를 집어 다른 작업대에 놓는 Pick & Place 스킬이 들어 있다.
- 작업대 진입은 카메라가 본 ArUco 마커로 정밀 도킹한다.

### 카메라는 Python 직접 수신

![카메라 처리 경로](intro_camera.png){width=1000}

- 영상은 ROS 토픽으로 흘리지 않는다.
- 시뮬레이터 프로세스 안의 Python 콜백이 프레임을 받는다.
- 검출 결과(물체 3D 위치, 마커)만 ROS 메시지로 낸다.
- 그래서 저사양 노트북에서도 실시간이 유지된다.

### LMM 연결

![LMM의 역할](intro_lmm.png){width=1000}

- OpenAI API가 자연어 지령을 작업 단계 목록으로 바꾼다. 예: 이동 → 확인 → 집기 → 이동 → 놓기.
- ROS 2 Task Manager가 그 순서대로 Nav2와 MoveIt을 부른다.
- LMM은 관절이나 속도를 직접 다루지 않는다.

### 전체 구조

![패키지 구조](architecture.png){width=1000}

### 네 층의 역할

![네 층 요약](intro_layers.png){width=1000}

### 한 줄 요약

![핵심 파이프라인](intro_pipeline.png){width=1000}

- **자연어 지령 → LMM → Task Planning → ROS 2 → Nav2 / MoveIt → MuJoCo → 로봇 행동**.
- 이 파이프라인이 처음부터 끝까지 하나의 워크스페이스에 들어 있다.
- Ubuntu 24.04, ROS 2 Jazzy, 외장 GPU 없는 4코어 노트북에서 검증했다.

## 2. 수업 형식: 단기 과정

### 수업의 성격

![수업 형식](intro_format.png){width=1000}

- 단기 집중 수업용 자료다.
- 수강생이 처음부터 코드를 짜는 수업이 아니다.
- GitHub에 배포된 완성 코드를 단계별로 실행한다: https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco
- 각 단계의 핵심 코드와 ROS / MuJoCo 연결 구조를 이해한다.
- 마지막에 전체 시스템을 연결해 본다.

### 대상과 환경

![대상과 환경](intro_env.png){width=1000}

- 대상: ROS 2 기초를 아는 학부 · 대학원생.
- 환경: 수강생 본인 노트북. Ubuntu 24.04, 4코어 · 16 GB 이상, 내장 그래픽.
- 캠프 전에 사전 설치한다. 수업 중 설치 작업은 하지 않는다.
- 시뮬레이터는 MuJoCo만 사용한다. Gazebo 설치는 필요하지 않다.

### 모듈 진행 방식

![모듈 진행](intro_cycle.png){width=1000}

- 모듈마다 개념 설명 → 핵심 코드 설명 → 따라 실행 → 결과 확인 · 문제 해결 순서로 진행한다.
- 각 모듈은 `ros2 launch` 또는 스크립트 명령 하나로 실행된다.

### 전반부 · 후반부 목표

![전반부 · 후반부 목표](intro_goals.png){width=1000}

- 전반부: ROS 2 Launch → MuJoCo → LiDAR → SLAM → Nav2를 연결한다. 양팔 로봇이 창고에서 자율주행한다.
- 후반부: 자연어 명령 → LMM → Task Planning → ROS 2 → Nav2 / MoveIt → MuJoCo → 로봇 행동 파이프라인을 완성한다.

## 3. 커리큘럼

### 전반부 — MuJoCo(비 Gazebo) + ROS 2 로봇 시스템 구축

![전반부 모듈](intro_curriculum_front.png){width=1000}

### 후반부 — MoveIt + Mobile Manipulation + LMM

![후반부 모듈](intro_curriculum_back.png){width=1000}

### 핵심 파이프라인

![핵심 파이프라인과 예시](intro_pipeline_example.png){width=1000}

- 사용자 자연어 명령 → LMM(OpenAI API) → Task Planning / Structured Command → ROS 2 Task Manager → Nav2 / MoveIt → MuJoCo → 로봇 행동.
- 예: "픽업 작업대로 이동해서 빨간 상자를 집고 적재 작업대로 옮겨."
- 결과: Navigate(pick_table) → Detect(red parcel) → Pick → Navigate(place_table) → Place.

## 4. 이 과정에서 익히는 기술 스택

### A. 시뮬레이션 · ROS 2 · 모델 · 센서 (모듈 ①~④)

![기술 스택 A](intro_stack_sim.png){width=1000}

### B. 주행 · Manipulation · 인지 · Pick & Place (모듈 ⑤~⑩)

![기술 스택 B](intro_stack_motion.png){width=1000}

### C. LMM · Task Planning · UI · 개발 도구 (모듈 ⑪~⑭)

![기술 스택 C](intro_stack_lmm.png){width=1000}

### 쌓이는 순서

![쌓이는 순서](intro_stack_order.png){width=1000}


## 5. 코드 저장소

### 저장소 구성

![저장소 구성](intro_repo.png){width=1000}

- 완성 코드는 GitHub 공개 저장소에 있다: **https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco**
- `src/`: ROS 2 패키지 10개. 로봇 description, MuJoCo 브리지, bringup, navigation, moveit_config, warehouse_interfaces / skills / lecture.
- `lessons/` 모듈별 실습 안내. `examples/` 단계별 예제. `weights/` 배포용 검출 가중치.
- `scripts/` 실행 · 설치 스크립트. `docs/` 사용 설명서와 검증 기록. `tests/` 단위 테스트.

### 설치와 문의

![설치 안내](intro_install.png){width=1000}

- 설치는 저장소의 README와 `docs/lecture/00_setup.md`를 따른다.
- Ubuntu 24.04 + ROS 2 Jazzy(native) 기준이다. 도커 · VM은 지원하지 않는다.
- 교육과 협업 문의: contact@pinklab.art (https://pinklab.art)
