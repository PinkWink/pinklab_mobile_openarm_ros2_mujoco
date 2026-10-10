# 08. LMM + OpenAI API (Day 2 ⑪) · LMM → ROS 2 Task Pipeline (⑫)

## 목표

한국어 문장을 로봇이 실행할 수 있는 구조화 명령(`RobotCommand`)으로 바꾼다. OpenAI Structured Outputs 로 모양을 고정하고(스키마 검증), `validate_world()` 로 이 창고에서 가능한지 따로 본다(세계 검증). 60 문장으로 변환 정확도를 재고, 호출마다 토큰과 비용을 기록한다. 실행은 ⑫(Task Manager).

## 준비

```bash
cp .env.example .env        # OPENAI_API_KEY=sk-... 기입. .env 는 git 에 올리지 않는다 (.gitignore)
# 모델 · 단가: src/warehouse_lecture/config/llm.yaml (models.chat = gpt-4.1-mini)
```

시뮬레이터는 필요 없다.

## 실행

```bash
./scripts/mobile_openarm exec python lessons/08_lmm/01_hello.py                 # 첫 호출: 답 · 토큰 · 비용 · 지연
./scripts/mobile_openarm exec python lessons/08_lmm/02_structured_command.py    # 문장 → RobotCommand → 세계 검증
./scripts/mobile_openarm exec python lessons/08_lmm/02_structured_command.py "파란 상자 적재대로 옮겨" "랙 C 로 가"
./scripts/mobile_openarm exec python lessons/08_lmm/03_accuracy.py              # 60 문장 정확도 (약 1 분, 약 $0.035)
./scripts/mobile_openarm exec python lessons/08_lmm/04_cost_log.py              # 오늘 쓴 토큰 · 비용 (목적별)
```

## 화면에서 볼 것

- 02: `{'intent': 'fly'}` 는 API 를 부르기 전에 pydantic 이 거부한다(스키마). "노란 상자를 랙 C 로 옮겨" 는 모양은 맞지만 `validate_world()` 가 거부한다(세계).
- 03 (2026-10-10, gpt-4.1-mini, temperature 0, 3 회): 58 · 59 · 58 / 60, 평균 0.95 ~ 0.98 s, 회당 $0.035. 틀린 문장은 "주위에 누가 있어?"(report → find), "팔 내려서 주행 자세로"(transport → home).
- 명령 한 번 입력 1,327 토큰 = system 규칙 592 + 예시 224 + JSON 스키마 490 + 문장 약 21. 출력 48 토큰.

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| OpenAI 호출 · 재시도 · 비용 로그 | `src/warehouse_lecture/warehouse_lecture/llm/client.py` (`LLM.chat`, `LLM.parse`, `_record`) |
| RobotCommand 스키마 · 세계 검증 | `src/warehouse_lecture/warehouse_lecture/commands/schema.py` (`RobotCommand`, `validate_world`) |
| 프롬프트 (규칙 · 예시 4 개) | `src/warehouse_lecture/warehouse_lecture/commands/parser.py` (`SYSTEM`, `EXAMPLES`, `CommandParser.parse`) |
| 60 문장 테스트셋 | `examples/m4_command_dialog/commands_test.yaml` |
| 모델 · 단가 · 로그 위치 | `src/warehouse_lecture/config/llm.yaml` |

## 해 볼 것

- `parser.py` 의 SYSTEM 규칙에 "'누가 있어?' 처럼 주변 사람 전체를 묻는 말은 report" 를 넣고 03 을 다시 돌려 report 정확도 비교
- `03_accuracy.py --model gpt-4.1` (또는 `gpt-4.1-nano`) 로 정확도 · 지연 비교. 단가가 llm.yaml 에 없으면 비용은 0 으로 찍힌다 — 단가를 먼저 넣는다
- 테스트셋에 자기 문장 5 개를 더해 (`--test my_tests.yaml`) 어떤 문장에서 틀리는지 보기

---

## ⑫ LMM → ROS 2 Task Pipeline (05 ~ 08)

### 목표

지령 하나를 **단계 목록**(`RobotPlan`: navigate · detect · pick · place · arm_pose · gripper · report · answer)으로 바꾸고, ROS 2 Task Manager(`/execute_plan`)가 Nav2 · PickPlace(MoveIt) · 카메라로 차례로 실행한다. 되묻기 · 확인 · 실패 보고까지 텍스트 대화로.

### 실행

```bash
# 시뮬레이터 없이
./scripts/mobile_openarm exec python lessons/08_lmm/05_plan.py              # 지령 → 단계 목록 · validate_world (자동 추가 · 거부)
./scripts/mobile_openarm exec python lessons/08_lmm/06_plan_accuracy.py     # 20 문장 계획 정확도 (약 $0.02)

# 터미널 1: 시뮬레이터 (07 모듈과 같다)
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision viewer:=true rviz:=false
# 터미널 2: Task Manager (command_executor 와 같이 띄우지 않는다)
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
# 터미널 3
./scripts/mobile_openarm exec python lessons/08_lmm/07_run_plan.py navigate:rack_c report
./scripts/mobile_openarm exec python lessons/08_lmm/08_text_mission.py      # 키보드 대화 (빈 줄로 끝)
./scripts/mobile_openarm exec python lessons/08_lmm/08_text_mission.py --lines "상자 옮겨" "파란 거 적재대로" "응"
```

### 화면에서 볼 것 (2026-10-10 실측)

- 05: `[pick parcel_red, place @place_table]` → navigate 두 개가 `(자동 추가)`. `[navigate, place]` → "든 것이 없는데 놓으려 한다".
- 06: 20/20, 문장당 평균 1.2 s, $0.019.
- 08: "상자 옮겨" → 되묻기 → "파란 거 적재대로" → 단계 5 개 + "진행할까요?" → "응" → 5/5 성공 244 s. 이어서 "빨간 상자 적재대로 옮겨"(이미 옮긴 상자) → 2 단계 detect 에서 멈춤: "1단계까지 마쳤지만 실패했습니다: 2단계(빨간 상자 확인) 실패: 빨간 상자가 카메라에 보이지 않는다".
- LLM 은 지금 상자가 어디 있는지 모른다. detect 단계가 집기 전에 싸게 확인한다.

### 핵심 코드

| 무엇 | 어디 |
|---|---|
| RobotPlan · PlanStep · validate_world | `src/warehouse_lecture/warehouse_lecture/commands/plan.py` |
| 계획 프롬프트 (규칙 · 예시 4 개) | `commands/plan_parser.py` |
| ExecutePlan 서버: 단계 실행 · 피드백 · 실패 문장 | `commands/task_manager.py` (`execute_plan`, `run_step`, `step_detect`, `step_pick`, `step_place`) |
| 되묻기 · 확인 | `commands/dialog.py` (`PlanDialogManager.handle`) |
| 액션 정의 | `src/warehouse_interfaces/action/ExecutePlan.action` |

### 해 볼 것

- `07_run_plan.py pick:parcel_red@pick_table place:@place_table` (navigate 없이) 로 자동 추가 확인
- `08_text_mission.py` 에서 "파란 상자 옮기고 노란 상자도 적재대로" → 10 단계 계획 확인 후 "아니" 로 취소
- `task_manager.py` 의 `DETECT_TIMEOUT_S` 를 3 으로 줄이면 detect 가 언제 실패하는지 보기 (끝나면 10 으로)
