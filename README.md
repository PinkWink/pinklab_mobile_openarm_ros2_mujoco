# pinklab_mobile_openarm_ros2_mujoco

MuJoCo + ROS 2 Jazzy 기반 **주행형 양팔 로봇(Vic Pinky 베이스 + OpenARM 양팔) & LMM Robotics** 단기 과정의 완성 코드입니다.
로봇이 창고를 자율주행하고, 작업대에서 상자를 집어 옮기고, 자연어 지령을 LMM이 작업 단계로 바꿔 ROS 2 Task Manager가 실행하는 파이프라인이 하나의 워크스페이스에 들어 있습니다.

```
자연어 지령 → LMM (OpenAI API) → 작업 단계 목록 → ROS 2 Task Manager → Nav2 / MoveIt → MuJoCo → 로봇 행동
```

- 물리: MuJoCo. Python 브리지가 `/clock`, `/joint_states`, TF, `/odom`, `/scan`을 발행하고 `/cmd_vel`과 관절 궤적 액션을 받습니다.
- 주행: SLAM Toolbox, Nav2(AMCL). 사람·지게차 배우가 돌아다니는 15 × 11 m 창고.
- Manipulation: MoveIt 2 양팔, PickPlace 스킬(ArUco 마커 도킹 → 카메라 검출 → 파지 → 놓기).
- 카메라: 영상 토픽 없이 시뮬레이터 프로세스 안의 Python 핸들러가 검출 결과만 발행합니다. 외장 GPU 없는 4코어 노트북에서 검증했습니다.
- LMM: OpenAI API Structured Outputs로 자연어 → 구조화 명령 / 작업 단계 목록. 텍스트 입출력만 씁니다.

## 환경

Ubuntu 24.04, ROS 2 Jazzy(native), Python 3.12, 4코어·16 GB 이상, 내장 그래픽(OpenGL 3.3+). 도커·VM은 지원하지 않습니다.

## 설치와 실행

```bash
git clone https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco.git
cd pinklab_mobile_openarm_ros2_mujoco
./scripts/install_lecture.sh            # venv + 의존성 + colcon build (docs/lecture/00_setup.md)
cp .env.example .env                    # OpenAI 키 (LMM 모듈에서만 필요)
./scripts/mobile_openarm start          # MuJoCo + Nav2 + MoveIt + RViz + 운반 스킬
./scripts/mobile_openarm pick red       # 다른 터미널: 빨간 상자를 픽업 작업대에서 적재 작업대로
```

자세한 명령과 launch 인자는 [docs/USAGE.md](docs/USAGE.md)를 보세요.

## 과정 구성

| 모듈 | 내용 | 실행 |
|---|---|---|
| ① Gazebo vs MuJoCo / Architecture | 시뮬레이터 구조 비교, 전체 파이프라인 | (강의) |
| ② MuJoCo + ROS 2 연결 | 브리지의 Topic / TF / Joint State / Control 인터페이스 | `./scripts/mobile_openarm drive` |
| ③ Robot Description | URDF/Xacro 통합 구조, TF 트리 | `./scripts/mobile_openarm display` |
| ④ Sensor / TF / Odometry / LiDAR | LaserScan, /odom, use_sim_time | `drive` + `teleop`, `examples/m1_ros_vision/02_scan_odom_subscriber.py` |
| ⑤ SLAM | SLAM Toolbox 지도 작성·저장 | `./scripts/mobile_openarm slam` |
| ⑥ Nav2 | AMCL, costmap, 자율주행 | `./scripts/mobile_openarm nav`, `goal X Y YAW` |
| ⑦ MoveIt + MuJoCo | planning group / scene, 이름 자세 | `./scripts/mobile_openarm moveit`, `arm both ready` |
| ⑧ Arm / End-Effector Control | IK, pose goal, Cartesian, 그리퍼 | [lessons/05_moveit](lessons/05_moveit/README.md) |
| ⑨ Pick & Place | 작업대 앞에서 집고 놓기 | [lessons/06_pick_place](lessons/06_pick_place/README.md) |
| ⑩ Navigation + Pick & Place 통합 | 주행 → 도킹 → 파지 → 운반 → 놓기 | `./scripts/mobile_openarm pick red` |
| ⑪ LMM + OpenAI API | Structured Outputs, 명령 스키마, 60문장 정확도 | `examples/m3_llm`, `examples/m4_command_dialog` |
| ⑫ LMM → ROS 2 Task Pipeline | 작업 단계 목록(RobotPlan) + Task Manager | `examples/m5_task_plan`, `ros2 run warehouse_lecture task_manager` |
| ⑬ Web Dashboard | 브라우저 상태 모니터링·지령 입력 | (준비 중) |
| ⑭ Final Mission | 자연어 → 계획 → 실행 → 결과 | `examples/m5_task_plan/04_final_mission.py` |

모듈별 README는 `lessons/`에 차례로 추가됩니다. 설계 기록과 검증 결과는 `docs/lecture/`에 있습니다.

## 저장소 구성

```
src/                ROS 2 패키지 10개 (description 3, mujoco 브리지, bringup, navigation, moveit_config, warehouse_interfaces / skills / lecture)
lessons/            모듈별 실습 안내와 스크립트
examples/           단계별 예제 (m1 ROS·비전, m3 LLM, m4 명령 대화, m5 작업 계획)
weights/            배포용 물체 검출 가중치 (YOLO11n, OpenVINO 320, CPU)
scripts/            wrapper(mobile_openarm), 설치·정리·검증 스크립트
docs/               사용 설명서, 카메라 API, 모듈별 검증 기록
tests/              시뮬레이터 없이 도는 단위 테스트 (python -m pytest tests -q)
```

## 라이선스와 출처

`src/openarm_description`, `src/vicpinky_description`의 로봇 모델과 메시는 각 원저작자의 라이선스를 따릅니다. 해당 패키지 안의 고지를 참고하세요.
