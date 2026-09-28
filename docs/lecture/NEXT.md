# 다음 세션 재개 안내

마지막 갱신: 2026-09-28 저녁 (hand-off). PC를 다시 켠 뒤 이 문서만 보고 이어갈 수 있도록 쓴다.

## 0-1. 배포 채널 (2026-09-27 저녁에 만든 것)

- **GitHub (public)**: https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco — 이 워크스페이스가 그대로 저장소(`main`). `gh` CLI가 PinkWink 계정으로 로그인돼 있다. 커밋·push는 사용자가 요청할 때만. 제외 규칙은 `.gitignore`(build/install/log, `.venv*`, `.env`, `confluence_token.txt`, artifacts/logs/runs/datasets, 가중치는 OpenVINO 320 하나만).
- **Confluence EDU 공간** (spaceId 2517565443, 부모 페이지 3692396550 "주행형 양팔로봇 수업자료 (mujoco + ROS2)"):
  - 3692331022 "패키지 소개와 단기 과정 커리큘럼" ← `docs/camp/intro_curriculum.md` (개조식, h3마다 그림 1장) + `architecture.png` + `intro_*.png` 21장 (`draw_intro_figures.py`, 2026-09-28 v10)
  - 3692331054 "환경 설정과 패키지 사용법" ← `docs/camp/setup_usage.md` (개조식, h3마다 그림 1장) + 그림 4장 (`draw_setup_figures.py`) + `setup_*.png` 26장 (setup_start_result.png · setup_display_result.png 는 실제 화면 캡처) (`draw_setup_detail_figures.py`, 2026-09-28)
  - 3692920898 "MuJoCo와 ROS2를 연결하기" (Gazebo vs MuJoCo + 최소 브리지, 2026-09-28 v7) ← `docs/camp/lesson01_mujoco_ros2.md` (h3 32개 = 그림 32장) + `lesson01_*.png` (`draw_lesson01_figures.py` 블록선도 20장, `render_terminal.py` 로 그린 실제 CLI 출력 캡처 9장, 실제 화면 캡처 `lesson01_run_result.png` · `lesson01_pub1_motion.png` · `lesson01_pub2_motion.png` · `lesson01_t2_rqt_window.png`)
  - 갱신: `set -a; source ../confluence_token.txt; set +a; python3 scripts/publish_confluence.py <md> "<제목>" --update <pageId> [png...]`. 새 하위 페이지: `... <md> "<제목>" 3692396550 2517565443 [png...]`. 문법: `:::tip|info|note|warning|panel 제목 … :::`, `:::cards(2|3)` + `::card 제목`, `![..](x.png){width=1000}`.
- **Confluence PD 공간** (개발 기록, 부모 3683418127): Phase 0 3684663302, M1 3687055362, M2 3687776258, M3 3687251977, M4 3692527619, M5 3692527659.
- **학회 전달용 커리큘럼**: Claude Doc https://claude.ai/code/artifact/5d2472b7-3ceb-4be2-9ee2-2da6dbddba30 + 로컬 `../CAMP_CURRICULUM.md`. 강사 개발 계획은 `../LECTURE_PLAN.md`(v4).

## 0-2. 페이지 작성 규칙 (2026-09-28, 사용자 피드백으로 굳어진 것)

- 문장은 짧게, 전부 개조식. 표는 쓰지 않는다(사용자가 표를 모두 삭제시킴). h3가 최소 단위이고 나중에 슬라이드 한 장이 되므로 h3 본문은 짧게, **h3마다 대표 그림 1장**.
- 명령은 코드 블록으로 두되 **명령마다 h3를 나누고 실제 실행 결과를 캡처**해서 붙인다. 터미널 출력은 실제로 실행해 얻은 텍스트를 `docs/camp/render_terminal.py`로 터미널 모양 PNG로 그린다(한글 폰트 NanumGothicCoding). GUI는 `DISPLAY=:1`에서 xdotool 로 창을 배치하고 `import -window root -crop WxH+X+Y` 로 찍는다. 움직임(topic pub 등)은 보내기 전/후를 각각 찍어 PIL 로 좌우 합성한다(`lesson01_pub1_motion.png` 만든 방식, 코드는 세션 기록에만 있고 스크립트화 안 됨).
- 코드 설명은 "함수 이름 - 역할" h3 + 코드 발췌 + 블록선도 + 불릿 3~4개 (lesson01 페이지 3장 끝부분 6개 절이 견본).
- 그림은 matplotlib, 직교 화살표만, 헬퍼는 `draw_intro_figures.py`(chain / flow_rows / tiles / rbox)를 다른 스크립트가 import 한다. 렌더 후 반드시 PNG를 눈으로 확인(글자 넘침이 잦다).
- Claude Code Bash 에서 `pkill -f`/`pgrep -f` 패턴이 자기 명령줄과 겹치면 셸이 죽는다 → `pgrep -f "^python lessons/..."` 처럼 앵커를 쓴다. 백그라운드로 띄운 파이썬은 SIGINT 를 무시하므로 종료 테스트는 `timeout -s INT` 로 포그라운드에서 한다.

## 0. 컨셉 변경 (2026-09-27)

6모듈 LLM·비전 강좌 계획(`../../LECTURE_PLAN.md` v3)은 **2일짜리 겨울 캠프**로 바뀌었다: "MuJoCo + ROS2 기반 Mobile Dual-Arm Robot & LMM Robotics", 수강생 60~80명.

- Day 1: Gazebo vs MuJoCo → MuJoCo+ROS2 브리지 → OpenARM 로봇 description → 센서/TF/odom/LiDAR → SLAM → Nav2 → 자율주행 데모.
- Day 2: MoveIt+MuJoCo → 팔/EE 제어 → Pick & Place → Nav2+Pick&Place 통합 → LMM(OpenAI API) → LMM→ROS2 Task Pipeline → MuJoCo 웹 대시보드(버퍼, 밀리면 데모만) → Final Mission(자연어 → LMM → Nav2/MoveIt → MuJoCo).
- GitHub 폴더: 01_mujoco_ros2, 02_robot_description, 03_slam, 04_navigation, 05_moveit, 06_pick_place, 07_mobile_manipulation, 08_lmm, 09_web_dashboard, 10_final_project.
- 운영: 도커 없음. 수강생이 직접 설치하고, GitHub의 **완성 소스**를 실행하며 강사 설명을 듣는다. 모듈당 50~70분(개념 → 핵심 코드 → 따라 실행 → 문제 해결). 수업 중 pip install 금지.
- 마감: 커리큘럼·시간표를 2026-09-29(화)까지 로봇학회에 전달.
- 범위 밖이 된 것: YOLO 학습(M2), 사람·안전모 조우 기억(M5), 센서 동기화(M6). "빨간 물체 검출"은 배포 가중치(OpenVINO CPU) 또는 HSV로 블랙박스 처리.

기존 자산과의 대응: 01~08, 10은 Phase 0 + M1~M4 코드로 거의 덮인다. 신규는 09 웹 대시보드, LMM의 **단계 목록** 출력(현재 스키마는 `move_object` 한 명령) + Task Manager, Gazebo vs MuJoCo 강의자료, 30줄짜리 최소 브리지 예제, 모듈별 README/실행 명령, git 저장소(현재 git 아님).

## 1. 지금 어디까지 왔나

- **강의 모듈 05·06 완료 (2026-09-27)**: `lessons/05_moveit/ee_control.py`(where/named/ik/pose/cartesian/gripper/demo) + README, `lessons/06_pick_place/pick_then_place.py`(phase pick → 같은 작업대에 place) + README. launch 인자 `spawn:=pick_table|X,Y,YAW`(MuJoCo 위치 + AMCL 초기 위치). 도킹은 이제 마커 쌍 측정만 쓰고 단일 마커는 무시(blind 구간은 마지막 쌍 측정의 odom 기준). 검증: EE demo 성공, red pick 39 s + place-back 42 s(3.7 cm), blue pick 70 s + place_table 103 s(1.8 cm).
- **M5 완료 (2026-09-27)**: LMM 작업 계획(RobotPlan: navigate/detect/pick/place/…) + Task Manager(`ros2 run warehouse_lecture task_manager`, /execute_plan). PickPlace 서버에 `phase`(all/pick/place)와 `held` 상태, 도킹 단일 마커 필터, 들기 대체 경로, 실패 복구(recover) 추가. 20문장 계획 정확도 20/20, Final Mission 3종(빨간 상자 운반 174 s, 랙 C 보고 66 s, 노란 상자 운반 155 s) 연속 성공. 문서 `docs/lecture/05_task_plan.md`, 예제 `examples/m5_task_plan/`, 테스트 41개.
- **M4 완료 (2026-09-27)**: 운반 명령 3회 연속 성공(빨강 152 s, 파랑 170 s, 노랑 154 s, 슬롯 오차 2.7~4.3 cm). 문서 `docs/lecture/04_command_dialog.md`. 노란 상자(옆 도킹)는 처음 성공. 고친 것: 옆 도킹 부호(`pick_place_server.py`, `-dock_side`), Nav2 `default_server_timeout` 20→200 ms, `NavClient.go_to` ABORTED 시 1회 재시도, 회귀 테스트 추가(tests 35개).
- M3 완료 (2026-09-22): `examples/m3_llm/`, `docs/lecture/03_llm.md`, Confluence 3687251977.
- M2 완료 (2026-09-22): `examples/m2_yolo/`, `docs/lecture/02_yolo.md`, Confluence 3687776258, 가중치 `weights/`.
- M1 완료 (2026-09-22): `examples/m1_ros_vision/`, `docs/lecture/01_ros_vision.md`, Confluence 3687055362.
- Phase 0 완료: `docs/lecture/phase0_report.md`, Confluence 3684663302 (부모 3683418127 "MuJoCo + ROS2 패키지 구성", space PD, spaceId 3419570180).
- 사용법 `docs/USAGE.md`, 설치 `docs/lecture/00_setup.md`. 소스는 git 저장소가 아니다. 원본 ZIP은 `../mobile_openarm_jazzy_ws.zip`.

## 2. 재부팅 후 다시 돌리는 순서

```bash
cd ~/mujoco_ros2/mobile_openarm_ws
source /opt/ros/jazzy/setup.bash          # zsh면 setup.zsh
source scripts/env.sh                    # venv + install setup + domain 43 + CycloneDDS
./scripts/cleanup_ros.sh
./scripts/mobile_openarm build           # 소스가 바뀌었을 때만 (config yaml 은 build/ 로 복사되므로 yaml 수정 후에도 필요)
python -m pytest tests -q                # 41개 통과 (약 1.2분). 시뮬레이터와 동시에 돌리지 말 것
./scripts/mobile_openarm start           # 시뮬레이터
```

M4 전체 데모(시뮬레이터 + 실행기 + 텍스트 대화)는 `docs/lecture/04_command_dialog.md` 2절, Final Mission(시뮬레이터 + task_manager + 04_final_mission.py)은 `docs/lecture/05_task_plan.md` 2절.

## 3. 다음 작업 (2일 과정 기준)

1. (완료 09-27) `LECTURE_PLAN.md` v4, 학회 전달 문서(Claude Doc + `CAMP_CURRICULUM.md`). 9/29 학회 전달은 사용자가 한다.
2. (완료 2026-09-27) 계획 수준 스키마 + Task Manager + PickPlace `phase`. 남은 것: 06_pick_place 실습 시나리오(`pick red --phase pick` → `pick red pick_table --phase place` 로 같은 작업대에 다시 놓기) 문서화·검증.
3. (완료) EE 제어 예제 → `lessons/05_moveit/`.
4. 09 웹 대시보드: 카메라 프레임은 핸들러 프로세스 안에 있으므로 핸들러가 JPEG를 websocket으로 내보내는 방식 또는 rosbridge + roslibjs. 로봇 상태(/odom, /joint_states, 스킬 phase) 표시 + 자연어 명령 입력(→ /warehouse/utterance).
4. GitHub 저장소: `git init`, `src/`는 하나(완성 코드), `lessons/01~10/README.md`에 실행 명령·핵심 코드 포인터. 설치 스크립트 + 사전 환경 점검 스크립트 강화(수강생 직접 설치).
5. ~~Gazebo vs MuJoCo 강의자료, 최소 브리지 예제(01_mujoco_ros2)~~ **완료 2026-09-28**: `lessons/01_mujoco_ros2/` (two_link_arm.xml = 2링크 팔 + 팔 끝 카메라, minimal_bridge.py 138줄: /clock /joint_states /tf /tip_camera/image_raw 발행 · /cmd 구독, README). Confluence 3692920898 v7 (Gazebo vs MuJoCo 6절 → 최소 브리지 → 실행 명령별 캡처 → 함수별 코드 구조 6절). 실행: `source scripts/env.sh; python lessons/01_mujoco_ros2/minimal_bridge.py --viewer`, 명령 `ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"`. 함정: MJCF 관절 range 는 `compiler angle="radian"` 없으면 도(degree) 단위; 관절에서 겹치는 캡슐은 contype=0 으로 자기 충돌 제외; 카메라 `xyaxes="0 -1 0 -1 0 0"` 이어야 링크 방향을 정방향으로 본다; `rclpy.init(signal_handler_options=SignalHandlerOptions.NO)` 라야 Ctrl+C 가 깨끗이 끝난다. 미결: `publish_joints` 가 TF 까지 발행해 이름이 좁다(사용자가 알고 있음, 나누려면 페이지 3장 코드 발췌도 같이 수정).
   **다음 세션은 여기서 시작**: (a) 페이지 3692920898 사용자 검토 후 남은 수정, (b) 다음 페이지 = 커리큘럼 ③ "OpenARM Mobile Dual-Arm Launch / Robot Description" (`./scripts/mobile_openarm display`, URDF/Xacro → MJCF, TF 트리; 환경 설정 페이지 2장 "description" 절 캡처 재사용 가능) 을 같은 규칙(0-2)으로 3692396550 아래에 작성, (c) `lessons/02~04`, `07~10` README, 수강생용 `INSTALL.md`와 `scripts/check_env.sh`(PASS/FAIL 표), 마지막에 09 웹 대시보드.
6. lessons README 틀은 `lessons/05_moveit/README.md`, `lessons/06_pick_place/README.md`를 따른다(목표 → 실행 → 화면에서 볼 것 → 핵심 코드 → 해 볼 것 → 문제 해결).

## 4. 개발용 도구

| 스크립트 | 용도 |
|---|---|
| `scripts/dev/restart_sim.sh [이름]` | headless 시뮬레이터 재시작 + 준비 대기. 로그 `artifacts/dev/<이름>.log`. `LAUNCH_ARGS="..."`로 인자 추가 |
| `scripts/dev/run_pick.sh [색] [from] [to]` | 운반 실행 + 상자 높이/손가락 타임라인 |
| `scripts/dev/monitor_parcel.py <log>` | parcel_1 높이·오른손가락·스킬 단계 기록 |
| `scripts/dev/grasp_physics.py` | ROS 없이 파지 유지 물리 실험 |
| `scripts/publish_confluence.py` | md → Confluence 하위 페이지 (토큰은 `../confluence_token.txt`) |
| `scripts/cleanup_ros.sh` | 잔여 ROS 프로세스 정리 |

## 5. 알아 두어야 할 함정

- `ros2 launch`를 그냥 치면 bridge가 mujoco를 못 찾는다. `env.sh`의 `ros2launch` 함수나 wrapper를 쓴다.
- ros2 CLI는 wrapper `exec` 또는 `env.sh` 환경에서만 노드가 보인다(CycloneDDS, domain 43). 토픽이 2개만 보이면 `ros2 daemon stop`.
- 시뮬레이터를 강제 종료하면 Nav2·MoveIt 자식이 남아 다음 실행에서 액션이 거부된다 → cleanup_ros.sh.
- `pkill -f 패턴`을 다른 명령과 같은 셸 줄에 쓰면 그 셸 자신이 죽는다. 종료는 별도의 짧은 명령으로, 패턴은 `p="command_exec""utor"; pkill -f "$p"`처럼 쪼개서.
- venv에 numpy 2가 들어가면 시스템 scipy와 충돌한다. `requirements-lecture.txt`의 고정 버전을 유지한다.
- 상자를 옮긴 뒤 세계는 초기화되지 않는다. 반복 시험은 시뮬레이터 재시작.
- 도킹 부호: `dock_side_for`(베이스의 축 기준 오프셋, +왼쪽)와 서보 `side`(베이스에서 본 축 위치)는 부호가 반대다.
- 4코어 제한에서 Nav2 BT의 goal 응답 타임아웃(default_server_timeout)이 20 ms면 ABORTED(6)가 난다. 200 ms로 둔다.
- `command_executor`와 `task_manager`는 둘 다 /execute_command 를 서비스하므로 하나만 띄운다. 시뮬레이터를 다시 띄우면 task_manager 도 다시 띄운다(든 물체 상태).
- 도킹은 마커 쌍 측정만 쓴다. 마커가 하나만 보이면 그 법선(±20°)이 횡 12 cm·거리 5 cm 를 틀리게 하므로 즉시 blind 구간으로 넘어간다(nav_client.dock). 상자가 planning scene 에 붙은 채 실패하면 recover() 가 풀어 준다.
