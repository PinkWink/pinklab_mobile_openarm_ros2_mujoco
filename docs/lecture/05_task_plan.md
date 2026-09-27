# M5. LMM 작업 계획(RobotPlan)과 ROS 2 Task Manager

작성·검증: 2026-09-27, Ubuntu 24.04 / ROS 2 Jazzy / OpenAI gpt-4.1-mini, `taskset -c 0-3`(4코어). 예제는 `examples/m5_task_plan/`, 본체는 `src/warehouse_lecture/warehouse_lecture/commands/{plan,plan_parser,task_manager}.py`와 `warehouse_skills` PickPlace 서버의 `phase` 인자.

겨울 캠프 2일 과정에서 이 모듈은 `08_lmm`(후반: 자연어 → 단계 목록)과 `10_final_project`의 본체다. M4가 "한 문장 = 한 명령"이었다면, 여기서는 LMM이 **작업 단계 목록**을 만들고 Task Manager가 순서대로 실행한다.

## 1. 목표와 요약

"픽업 작업대로 가서 빨간 상자를 집고 적재 작업대로 옮겨" → LMM → `[navigate, detect, pick, navigate, place]` → Task Manager → Nav2 / PickPlace(MoveIt) → MuJoCo. LMM은 관절·속도를 만들지 않고 단계만 정한다.

| 예제 | 내용 | 결과 |
|---|---|---|
| 01_plan_schema.py | RobotPlan/PlanStep(pydantic), validate_world(빠진 navigate 자동 추가, 작업대 기본값, 든 것 없이 place 금지 등), ExecutePlan goal 변환 | LLM·시뮬레이터 없이 동작 |
| 02_nl_to_plan.py | 한국어 지령 20문장 → 단계 목록 정확도 (Structured Outputs, few-shot 4개) | **20/20 = 100 %** (기준 90 %), 비용 0.019달러 |
| 03_task_manager.py | ExecutePlan 클라이언트: 단계 목록·자연어·mission 프리셋 실행, 단계별 피드백 | |
| 04_final_mission.py | 텍스트 지령 → 계획 → 확인(단계 목록 표시) → 실행 → 결과 문장 | **미션 3종 연속 성공** (아래 4절) |

## 2. 준비와 실행

```bash
source /opt/ros/jazzy/setup.bash && source scripts/env.sh && ./scripts/cleanup_ros.sh
# 터미널 1: 시뮬레이터 (ArUco + YOLO 검출기, 카메라 기반 물체 위치)
LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start viewer:=false rviz:=false camera_depth:=true locate:=vision
# 터미널 2: Task Manager (/execute_plan + /execute_command. command_executor 와 동시에 띄우지 않는다)
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
# 터미널 3: Final Mission
./scripts/mobile_openarm exec python examples/m5_task_plan/04_final_mission.py \
  --lines "픽업 작업대로 가서 빨간 상자 집고 적재 작업대로 옮겨" "응" "랙 C 앞에 가서 사람 있는지 알려줘" "노란 상자 적재대로" "네"
```

스킬만 단계별로 부를 때: `./scripts/mobile_openarm pick red --phase pick` (도킹·파지·운반 자세까지, 상자를 든 채 끝남) → `./scripts/mobile_openarm pick red place_table --phase place` (든 상자를 놓기). 06_pick_place 모듈에서는 같은 작업대에 다시 놓는 식으로 주행 없이 실습할 수 있다.

## 3. 구조

```
사용자 문장 ─ PlanDialogManager ─ PlanParser(LLM, Structured Outputs) ─ RobotPlan.validate_world()
                  │ 확인: 단계 목록 표시                                        │ ExecutePlan 액션
                  └───────────── 결과 문장 ◀──── TaskManager ◀───────────────────┘
                                                    ├ navigate → Nav2 (든 것이 없으면 팔을 transport 로; 들고 있으면 팔은 그대로)
                                                    ├ detect   → /vision/detections 에 라벨이 보일 때까지 최대 10 s
                                                    ├ pick     → /pick_place phase=pick  (도킹·파지·운반 자세·후진)
                                                    ├ place    → /pick_place phase=place (도킹·놓기·transport·후진)
                                                    └ arm_pose / gripper / report / answer → 실행기(M4)와 같은 코드
```

- **역할 분리.** LMM = 순서와 대상(무엇을, 어디서, 어디로). Task Manager = 순차 실행·피드백·중단·실패 보고. Nav2 = 주행. PickPlace/MoveIt = 도킹·파지·놓기. MuJoCo = 물리.
- **스키마와 의미 검증.** Structured Outputs는 형식만 보장한다. `validate_world()`가 "든 것이 없는데 place", "상자를 랙에서 pick", "상자를 든 채 끝남", "든 채 그리퍼 open"을 잡고, 빠진 navigate를 자동으로 끼워 넣는다.
- **스킬 서버의 상태.** PickPlace 서버가 `phase=pick` 뒤 든 물체(`held`)를 기억하고 `phase=place`에서 쓴다. Task Manager도 `held`를 두어 든 채 이동할 때 팔을 건드리지 않는다(운반 자세 hands_up은 주행 허용 자세).
- **확인.** pick/place가 있는 계획만 확인을 받고, 확인 문장에 단계 목록을 그대로 보여 준다. 이동+보고는 바로 실행한다.
- **실패 보고.** 몇 단계까지 했는지, 무엇을 들고 있는지를 문장으로 알린다. 다음 지령은 그 상태에서 이어진다.

## 4. Final Mission 검증 (2026-09-27)

| 지령 | 계획 | 결과 | 소요 |
|---|---|---|---|
| 픽업 작업대로 가서 빨간 상자 집고 적재 작업대로 옮겨 | navigate → detect → pick → navigate → place | 5/5 성공, 슬롯 오차 1.7 cm | 174 s |
| 랙 C 앞에 가서 사람 있는지 알려줘 | navigate → report | 2/2 성공, "랙 C에는 사람이 보이지 않습니다…" | 66 s |
| 노란 상자 적재대로 | navigate → detect → pick(옆 도킹 +0.10 m) → navigate → place | 5/5 성공, 슬롯 오차 1.1 cm | 155 s |

이해(LLM 계획) 1.5~2.0 s, 5턴 LLM 비용 0.0032달러. detect는 사전 도킹 지점(작업대에서 1.2 m)에서 head 카메라로 확인됐다(빨간 상자 점수 0.90).

## 5. 이번 모듈에서 고친 기반 코드

1. **PickPlace `phase` 인자** (`all` / `pick` / `place`). 서버를 `do_pick`·`do_place` 두 절반으로 나누고 `held` 상태를 둔다. pick 결과는 상자가 상판보다 2 cm 이상 올라왔는지로 판정한다.
2. **도킹 단일 마커 필터** (`nav_client.dock`). 바깥 마커가 시야를 벗어나면 남은 마커 하나의 법선으로 축을 추정했는데, 320×240에서 이 법선이 ±20° 흔들려 마지막 측정이 12 cm 튀었고 blind 구간이 그 값을 믿었다(첫 실행에서 베이스가 축에서 12 cm 벗어나 들기 실패). 이제 마커가 하나만 보이면 거리(along)만 받고 횡·방향은 마지막 쌍 측정을 유지한다. 쌍 측정도 이전 값과 8 cm 넘게 다르면 버린다. 수정 후 잔차 0.2 / 0.8 / 1.6 / 1.8 cm.
3. **들기 대체 경로.** 상자가 팔 도달 한계 근처면 들기+후퇴 직선 경로(Cartesian)가 0 %로 실패한다. 이때 4 cm 들기만 직선으로 하고 후퇴 자세는 플래너로 계획한다.
4. **실패 복구** (`PickPlaceServer.recover`). 상자가 planning scene에 붙은 채 실패하면 이후 모든 MoveIt 요청이 START_STATE_IN_COLLISION(-10)으로 막혔다. 실패 시 그리퍼 열기 → detach → 손 후퇴 → transport 자세를 차례로 시도한다.
5. `CommandExecutor`에 노드 이름 인자와 `drive_to`(팔을 건드리지 않는 Nav2)를 분리했고, 한국어 이름표(PLACE_KO/TARGET_KO)를 `schema.py`로 옮겼다. `task_manager`는 실행기를 상속해 `/execute_command`도 함께 서비스한다.

## 6. 함정

- `command_executor`와 `task_manager`를 같이 띄우면 `/execute_command` 서버가 둘이 된다. 하나만 띄운다.
- 상자를 든 채 `arm_pose`/`gripper open`은 검증 단계에서 막힌다. 든 채로 끝나는 계획도 막힌다(place가 없다).
- 반복 시험은 시뮬레이터 재시작(세계가 초기화되지 않는다). 시뮬레이터를 다시 띄우면 스킬 서버의 `held`도 초기화되지만 Task Manager의 `held`는 남는다 → Task Manager도 다시 띄운다.
- `pkill -f 패턴`은 별도 명령으로, 패턴은 쪼개서(`p="task_man""ager"`).

## 7. 다음

웹 대시보드(09), PickPlace 단계 실행을 이용한 06 모듈 실습 시나리오, EE 제어 예제(05), 최소 브리지 예제(01), GitHub 저장소 구조. `NEXT.md` 참고.
