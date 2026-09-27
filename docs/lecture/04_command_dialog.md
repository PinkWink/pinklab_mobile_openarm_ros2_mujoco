# M4. 로봇 명령어 구조화 및 텍스트 기반 대화

작성·검증: 2026-09-22 ~ 2026-09-27, Ubuntu 24.04 / ROS 2 Jazzy / OpenAI gpt-4.1-mini, `taskset -c 0-3`(4코어). 예제는 `examples/m4_command_dialog/`, 본체는 `src/warehouse_lecture/warehouse_lecture/commands/`. 음성(STT/TTS)은 쓰지 않는다(2026-09-22 결정): 사용자는 텍스트를 입력하고 로봇 답을 텍스트로 읽는다.

겨울 캠프 2일 과정(2026-09-27 개편)에서는 이 모듈이 `08_lmm`(자연어 → Structured Command → ROS2 Task Manager)과 `10_final_project`의 기반 코드가 된다.

## 1. 목표와 요약

자연어 문장을 구조화 명령(RobotCommand)으로 바꾸고, 실행기(ExecuteCommand 액션)가 Nav2·PickPlace·MoveIt을 순서대로 불러 수행한 뒤 결과를 문장으로 돌려준다. 되묻기·확인·문맥이 있는 다중 턴 대화를 텍스트로 만든다.

| 예제 | 내용 | 결과 |
|---|---|---|
| 01_command_schema.py | pydantic RobotCommand, validate_world(장소·물체·자세 사전), ROS 메시지 변환 | 형식 위반과 의미 위반(상자를 랙으로)을 다른 층에서 잡음 |
| 02_nl_to_command.py | 한국어 60문장 → 명령 변환 정확도 (Structured Outputs, few-shot 4개) | 58/60 = 96.7 % (기준 ≥ 90 %) |
| 03_command_executor.py | ExecuteCommand 액션 서버 + 클라이언트, 의도별 하위 액션 상태 기계 | demo(팔 자세·그리퍼·이동·보고·사람 찾기) 성공, move_object red 135 s |
| 04_text_console.py | 사용자 문장 `/warehouse/utterance` ↔ 로봇 답 `/warehouse/narration` | UI와 대화 로직 분리 |
| 05_dialog_manager.py | 되묻기·확인·문맥 기억 | 스크립트 대화 15/15, 모호 명령 5개 모두 되묻기 |
| 06_text_move_object.py | 텍스트 운반 명령 → 확인 → 실행 → 결과 문장, 단계별 지연 | **3회 연속 성공** (빨강 152 s, 파랑 170 s, 노랑 154 s), 6턴 LLM 비용 0.0019달러 |

의도별 변환 정확도(02): move_object 8/8, go_to 10/10, find 10/10, report 4/5, answer 14/14, arm_pose 4/5, gripper 4/4, stop 4/4. 틀린 둘은 "주위에 누가 있어?"(report를 answer로), "팔 내려서 주행 자세로"(arm_pose 슬롯)다.

## 2. 준비와 실행

```bash
source /opt/ros/jazzy/setup.bash && source scripts/env.sh && ./scripts/cleanup_ros.sh
# 터미널 1: 시뮬레이터 (ArUco + YOLO 검출기, 카메라 기반 물체 위치)
LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start viewer:=false rviz:=false camera_depth:=true locate:=vision
# 터미널 2: 실행기
./scripts/mobile_openarm exec ros2 run warehouse_lecture command_executor
# 터미널 3: 대화
./scripts/mobile_openarm exec python examples/m4_command_dialog/06_text_move_object.py \
  --lines "빨간 상자 적재대로 옮겨 줘" "응" "파란 상자 옮겨" "네" "노란 상자를 적재 작업대로" "응"
```

`.env`에 `OPENAI_API_KEY`가 필요하다(02·03 `--nl`·05·06). 01·04는 키 없이 돈다.

## 3. 구조

```
사용자 문장 ─ DialogManager(05) ─ CommandParser(02, Structured Outputs) ─ RobotCommand(01)
                    │ 확인/되묻기                                              │ ExecuteCommand 액션
                    └────────────── 결과 문장 ◀──── CommandExecutor(03) ──────┘
                                                      ├ move_object → /pick_place (warehouse_skills)
                                                      ├ go_to       → Nav2 navigate_to_pose
                                                      ├ find        → 순찰 + /vision/detections
                                                      ├ report/answer → 세계 상태 JSON + LLM
                                                      ├ arm_pose    → MoveGroup 이름 자세
                                                      └ gripper / stop
```

- **스키마와 검증은 다른 층.** Structured Outputs는 형식만 보장한다. "빨간 상자를 랙 A로"는 형식상 맞지만 `validate_world()`가 잡는다. 기본값(source=pick_table)도 검증 층이 채운다.
- **LLM은 고수준 명령만 만든다.** 관절·속도는 전부 ROS 쪽(Nav2, MoveIt, 스킬 서버)이 맡는다. 실행기는 RobotCommand 메시지만 본다.
- **인터록.** 베이스는 양팔이 주행 자세(transport 등, `drive_poses.yaml`)일 때만 `/cmd_vel`을 받는다. go_to·move_object는 먼저 팔을 transport로 보낸다.
- **한 번에 한 명령.** 실행 중 새 명령은 거부하고 stop만 받는다. stop은 하위 goal을 취소하고 `/cmd_vel` 0을 보낸다.
- **복구.** Nav2 목표가 막히면(사람·소품) 한 번 기다려 재시도하고, 그래도 안 되면 목표 0.6 m 앞으로 대체한다. Nav2가 goal을 ABORTED(6)로 끝내면 스킬 클라이언트가 한 번 다시 보낸다.
- **대화 상태는 세 가지.** 되묻는 중(clarifying), 확인 대기(pending), 최근 문맥(context). 확인은 비싼 행동(운반)에만 건다.
- **지연.** 이해(LLM 파서) 1.4~2.2 s, 행동(운반) 150~170 s. "시작합니다"를 먼저 보내고 끝나면 결과를 보낸다.

## 4. 3회 연속 운반 검증 (2026-09-27)

| 상자 | 축 오프셋 | 팔 | 픽업 도킹 잔차 | 적재 도킹 잔차 | 슬롯 오차 | 소요 |
|---|---|---|---|---|---|---|
| 빨강 parcel_1 | -0.25 m | 오른팔 | -1.4 cm | +1.3 cm | 3.3 cm | 152 s |
| 파랑 parcel_2 | +0.05 m | 왼팔 | -0.4 cm | -0.4 cm | 4.3 cm | 170 s |
| 노랑 parcel_3 | +0.35 m | 왼팔, 옆 도킹 +0.10 m | +2.9 cm | +5.9 cm | 2.7 cm | 154 s |

노란 상자는 축에서 0.35 m 떨어져 있어 베이스를 축 왼쪽 0.10 m에 도킹해야 왼팔이 닿는다(`dock_side_for`). 이번에 처음 성공했다.

## 5. 이번 모듈에서 고친 기반 코드

1. `mobile_openarm_mujoco/trajectory.py` `LIMIT_TOLERANCE` 1e-3 → 0.02. MoveIt 관절 한계를 URDF보다 0.01 rad 넓혔으므로(M1) 브리지의 궤적 검증도 그만큼 느슨해야 한다. 아니면 MoveIt 실행이 error -4 "Goal was rejected"로 실패한다.
2. `pick_place_server.dock_side_for()`: 축에서 0.25 m 넘게 떨어진 상자는 도킹 목표를 그쪽으로 최대 0.2 m 옮긴다.
3. **옆 도킹 부호 수정(2026-09-27).** `dock_side_for`는 베이스의 축 기준 오프셋(+왼쪽)이고, 서보 목표 `side`는 베이스에서 본 축의 위치(축이 왼쪽에 보이면 +)다. 둘은 부호가 반대인데 그대로 넘겨 로봇이 노란 상자 반대쪽에 도킹했고 카메라에 상자가 보이지 않았다(`parcel_yellow not visible`). `-dock_side`로 넘긴다. 회귀 테스트 `tests/test_skills.py::test_side_dock_target_puts_base_on_the_object_side`.
4. **Nav2 goal 응답 타임아웃(2026-09-27).** 4코어 제한에서 YOLO·MoveIt·Nav2가 함께 돌면 bt_navigator가 `compute_path_to_pose` 서버의 goal 응답을 20 ms 안에 못 받아 goal을 ABORTED(6)로 끝냈다. `nav2.yaml` `default_server_timeout` 20 → 200 ms. 스킬의 `NavClient.go_to`는 Nav2가 ABORTED로 끝내면 같은 목표를 한 번 다시 보낸다.

## 6. 함정

- `pkill -f 패턴`을 다른 명령과 같은 셸 줄에 쓰면 그 셸 자신이 죽는다. 종료는 별도 명령으로, 패턴은 쪼개서.
- 상자를 옮긴 뒤 세계는 초기화되지 않는다. 반복 시험은 시뮬레이터 재시작.
- 시뮬레이터 종료 후 Nav2·MoveIt 자식이 남으면 액션이 거부된다 → `scripts/cleanup_ros.sh`.
- `ros2 topic list`에 토픽이 2개만 보이면 데몬이 다른 RMW로 떠 있다 → `ros2 daemon stop`.

## 7. 다음

겨울 캠프 2일 과정 개편에 따라 M5(조우 기억)·M6(센서 동기화)는 진행하지 않는다. 다음은 LMM이 단계 목록(Navigate → Pick → Navigate → Place)을 내고 Task Manager가 순서대로 실행하는 계획 수준 스키마, 웹 대시보드, GitHub 저장소 구조다. `NEXT.md` 참고.
