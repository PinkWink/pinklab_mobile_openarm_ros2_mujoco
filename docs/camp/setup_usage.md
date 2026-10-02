## 0. 시작 전에

### 지원 환경 · 필요한 것 · 소요 시간

![지원 환경](setup_env_cards.png){width=1000}

- 지원 환경: Ubuntu 24.04 native + ROS 2 Jazzy · 4코어 · 16 GB · 내장 그래픽이면 충분
- 저장소: https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco

## 1. 환경 설정

### 설치 흐름

![설치 흐름](setup_flow.png){width=1000}

- 다섯 단계를 순서대로 1회만 수행 (10~20분 소요)
- 매 터미널마다 `source /opt/ros/jazzy/setup.bash` → `source scripts/env.sh` 실행

### ① ROS 2 Jazzy + 추가 패키지

![ROS 2 패키지](setup_ros2_packages.png){width=1000}

### ① ROS 2 Jazzy + 추가 패키지 설치 명령

- 공식 안내에 따라 `ros-jazzy-desktop` 설치: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
- 이 패키지가 사용하는 추가 항목 설치

```bash
sudo apt install python3-venv python3-colcon-common-extensions python3-rosdep git \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox \
  ros-jazzy-moveit-ros-move-group ros-jazzy-moveit-kinematics ros-jazzy-moveit-planners-ompl \
  ros-jazzy-moveit-simple-controller-manager ros-jazzy-moveit-ros-visualization ros-jazzy-moveit-configs-utils \
  ros-jazzy-teleop-twist-keyboard ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-xacro ros-jazzy-robot-state-publisher \
  ros-jazzy-rviz2 ros-jazzy-vision-msgs ros-jazzy-message-filters ros-jazzy-tf2-geometry-msgs ros-jazzy-tf2-tools
sudo rosdep init && rosdep update
```

### ② 저장소 받기 → ③ 설치 스크립트

![설치 스크립트](setup_install_script.png){width=1000}

### ③ 설치 스크립트

```bash
git clone https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco.git
cd pinklab_mobile_openarm_ros2_mujoco
source /opt/ros/jazzy/setup.bash
./scripts/install_lecture.sh
```

- 스크립트 수행 순서: rosdep 확인 → 가상환경 → pip → `.env` 생성 → `colcon build` → 단위 테스트
- 마지막에 "설치 완료" 출력 시 성공
- 고정 버전(`numpy<2`, `opencv-python<4.11`, `setuptools<80`, `ml-dtypes<0.6`) 업그레이드 금지 — ROS Jazzy Python 스택 · colcon 호환 목적

### install_lecture.sh 가 하는 일

![install_lecture.sh 단계](setup_install_script_detail.png){width=1000}

### OpenAI API 키 받는 법

![OpenAI API 키 발급](setup_openai_signup.png){width=1000}

### OpenAI API 키 받는 법: 절차와 링크

- 가입 · 로그인: https://platform.openai.com (ChatGPT 계정 그대로 사용 가능)
- 결제 수단 등록: https://platform.openai.com/settings/organization/billing/overview 에서 카드 등록 후 크레딧 충전
- 키 생성: https://platform.openai.com/api-keys 에서 "Create new secret key" 클릭
- `sk-`로 시작하는 키는 생성 시 한 번만 표시 → 즉시 복사해 보관
- 복사한 키를 `.env`의 `OPENAI_API_KEY=`에 붙여넣기 · 저장소 커밋 금지
- ChatGPT 유료 구독과 API 크레딧은 별개 · 이 과정의 호출량은 수 달러 수준

### ④ OpenAI 키

![OpenAI 키](setup_openai_key.png){width=1000}

### ④ OpenAI 키 설정 명령

```bash
cp .env.example .env      # OPENAI_API_KEY=sk-...
```

- LMM 모듈부터 필요
- 주행 · MoveIt · Pick & Place 모듈은 키 없이 동작
- 모델 · 가격표: `src/warehouse_lecture/config/llm.yaml` · 호출 기록: `logs/openai_usage.jsonl`

### 새 터미널마다 (env.sh)

![env.sh](setup_env_sh.png){width=1000}

### 터미널을 열 때마다 하는 명령

```bash
cd ~/pinklab_mobile_openarm_ros2_mujoco
source /opt/ros/jazzy/setup.bash      # zsh 는 setup.zsh
source scripts/env.sh
```

- `env.sh` 설정 항목: 가상환경 + install 환경 + `ROS_DOMAIN_ID=43` + CycloneDDS(localhost)
- source 안 한 터미널에서는 `./scripts/mobile_openarm exec <명령>` 사용
- localhost 통신이라 같은 강의실 다른 노트북과 토픽 혼선 없음

### env.sh 가 하는 일

![env.sh 단계](setup_env_sh_detail.png){width=1000}

### env.sh 실행 결과

![env.sh 실행 결과](setup_env_sh_result.png){width=1000}

### ⑤ 설치 확인

- `./scripts/mobile_openarm start` 실행 결과 (왼쪽: MuJoCo 창, 오른쪽: RViz2)

![./scripts/mobile_openarm start 실행 화면: MuJoCo 창(왼쪽)과 RViz2(오른쪽)](setup_start_result.png){width=1000}

## 2. 실행 구조

### 터미널 두 개

![실행 구조](run_structure.png){width=1000}

- 터미널 1: `./scripts/mobile_openarm start` — launch 하나로 모든 프로세스 실행
- 터미널 2: 명령과 예제 — `source scripts/env.sh` 후 실행

### wrapper 명령

![wrapper 명령](setup_commands.png){width=1000}

- 시뮬레이터는 한 번에 하나만 실행 (lock 파일로 중복 차단)
- 종료는 Ctrl+C · 남은 프로세스는 `./scripts/cleanup_ros.sh`로 정리

### launch 인자

![launch 인자](setup_launch_args.png){width=1000}

- `start`, `drive`, `slam`, `moveit` 뒤에 `인자:=값` 형식으로 추가
- 느리면 `rviz:=false` · 카메라 기본값은 `profile:=lite`(2대 320×240 2 FPS)

### description

- 시뮬레이터 없이 로봇 모델(URDF)만 RViz2에 표시 — Joint · Link · TF 트리 구조 확인용
- 슬라이더 창에서 관절 조작 시 RViz2의 로봇과 TF가 함께 움직임
- 시뮬레이터 실행 중에는 사용 금지 (둘 다 `/joint_states` · `/tf` 발행)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
ros2 launch mobile_openarm_description display.launch.py              # RViz2 + 관절 슬라이더
ros2 launch mobile_openarm_description display.launch.py gui:=false   # 슬라이더 없이
# 같은 것: ./scripts/mobile_openarm display
```

### 실행결과

![display.launch.py 실행 화면: RViz2(왼쪽)와 관절 슬라이더(오른쪽)](setup_display_result.png){width=1000}

## 3. 창고와 로봇

### 창고 배치도

![창고 배치도](warehouse_map.png){width=1000}

- 15 × 11 m 창고 · 출처: `warehouse.yaml` · `locations.yaml` · `actors.yaml`
- 별 = 기본 시작 위치 · 삼각형 = 이름 있는 장소의 `base_goal`

### 장소 이름 (locations.yaml)

![장소 이름](setup_locations.png){width=1000}

- `pick_table` 픽업 작업대 (2.6, −3.6) · `place_table` 적재 작업대 (2.6, 3.6)
- `rack_a` ~ `rack_f` 랙 A~F · `center_aisle` · `east_wall` · `west_wall`
- 삼각형 = `base_goal` — Nav2 목표이자 사전 도킹 지점
- 한국어 별칭은 LMM 파서가 그대로 사용

### 상자 · 작업대 · 마커

![작업대 옆모습](setup_table_side.png){width=1000}

### 배우 (actors.yaml)

![배우](setup_actors.png){width=1000}

## 4. ROS 2 인터페이스

### 인터페이스 한눈에

![ROS 2 인터페이스](setup_interfaces.png){width=1000}

## 5. 자주 수정하는 설정

### 설정 파일 지도 (src/ 아래)

![설정 파일](setup_config_files.png){width=1000}

## 6. 문제 해결

### 실행 환경 문제

![실행 환경 문제](setup_trouble_env.png){width=1000}

### 동작 · 성능 · 키 문제

![동작 · 성능 · 키 문제](setup_trouble_run.png){width=1000}
