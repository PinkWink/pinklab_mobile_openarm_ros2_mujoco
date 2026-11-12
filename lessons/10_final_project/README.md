# 10. Final Mission (Day 2 ⑭)

## 목표

자연어 지령 하나가 LLM 계획 → 확인 → ROS 2 Task Manager → Nav2 주행 → 도킹 · MoveIt Pick → 주행 → Place 까지 MuJoCo 안에서 끝까지 가는 것을 본다. ⑫ 와 다른 점 하나: 계획기가 **상자 위치표(WorldState)** 를 본다. 옮긴 뒤에는 표가 바뀌고, 다음 지령은 바뀐 표로 계획한다.

## 왜 상자 위치표가 필요한가

- LLM 은 창고를 보지 못한다. 표가 없으면 "빨간 상자 다시 픽업대로" 도 `pick@pick_table` 로 계획하고 detect 단계에서 실패한다 (⑫ 08 에서 본 실패).
- 표는 `PlanParser.parse(text, world=world)` 가 system 프롬프트 끝에 붙인다. LLM 은 여전히 단계 목록만 만든다.
- 실행 전에 `WorldState.check(plan)` 가 표와 계획을 비교한다 (집으려는 상자가 다른 작업대에 있으면 되묻기). 실행 뒤에는 `WorldState.apply(plan, steps_done, success)` 가 **끝난 단계만** 표에 반영한다 (pick 에서 실패하면 그 상자는 `unknown`).

## 실행

```bash
# 터미널 1: 시뮬레이터 (⑫ 와 같다)
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false
# 터미널 2: Task Manager
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
# 터미널 3: 시뮬레이터 없이 먼저 — 표가 있을 때와 없을 때의 계획 비교
./scripts/mobile_openarm exec python lessons/10_final_project/01_world_plan.py
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py --dry-run
# 터미널 3: Final Mission (시나리오 3개, 약 12 분)
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py --keyboard   # 직접 입력
```

- `.env` 에 `OPENAI_API_KEY` 가 있어야 한다 (⑪ 과 같음).
- "Managed nodes are active" 뒤 20 초쯤 기다린 다음 시작한다.
- 다시 시작할 때는 먼저 `./scripts/mobile_openarm stop` (이전 실행이 남아 있으면 `start` 가 멈추고 알려 준다).
- 시나리오는 이어서 실행해야 한다 (3 은 1 에서 옮긴 빨간 상자를 되돌린다). 시뮬레이터를 다시 띄우면 상자도 처음 자리로 돌아간다.

## 시나리오

1. "픽업 작업대로 가서 빨간 상자를 집고 적재 작업대로 옮겨" → 확인 → "응"
2. "상자 하나 적재대로 옮겨 줘" → 색 되묻기 → "파란 거" → 확인 → "응"
3. "빨간 상자 다시 픽업대로 가져와" → (표: 빨간 상자 = 적재 작업대) `pick@place_table` → `place@pick_table`

## 검증 (2026-11-12, 이 PC, gpt-4.1-mini)

- 01: 상자 위치표 없이 7/8 (그중 1건도 코드 검사 덕분에 실행은 막힘), 표를 넣으면 8/8 (3 회 연속). 회당 약 $0.017.
- 02: 시나리오 1 · 2 · 3 모두 5/5 단계 (179 s · 178 s · 140 s), 대화 7턴, LLM 비용 $0.0043.
- "이미 도착지에 있다" 판단은 LLM 이 아니라 `WorldState.check()` 가 한다. 프롬프트에 그 규칙을 넣었더니 LLM 이 멀쩡한 지령까지 비워 버렸다 (8 개 중 4~5 개).

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| 상자 위치표: 프롬프트 · 실행 전 검사 · 결과 반영 | `src/warehouse_lecture/warehouse_lecture/commands/world.py` `WorldState` |
| 표를 system 프롬프트에 붙이기 | `commands/plan_parser.py` `PlanParser.parse(..., world=)` |
| 대화 + 표 갱신 | `commands/dialog.py` `PlanDialogManager(world=)` |
| 시나리오 실행기 | `lessons/10_final_project/02_final_mission.py` |
| 단계 실행 (그대로 사용) | `commands/task_manager.py`, PickPlace 스킬 (`warehouse_skills`) |

## 해 볼 것

- `--keyboard` 로 "노란 상자도 적재대로" → "노란 상자 원래 자리로" 를 이어서 보내고 `[world]` 줄을 본다.
- `--dry-run --scenario 3` 만 실행한다. 표에서 빨간 상자가 이미 픽업 작업대에 있으므로 계획기가 무엇이라고 답하는지 본다.
- `01_world_plan.py` 에 문장을 하나 추가한다 (예: 표가 전부 적재 작업대일 때 "상자 다 원래대로").
