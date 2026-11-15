## 1. Final Mission: 문장 하나로 창고 운반 끝까지

### 전체 파이프라인

![문장 → LLM 계획 → 검증 → Task Manager → Nav2 · PickPlace → MuJoCo, 결과 → 상자 위치표](lesson15_pipeline.png){width=1000}

### 왜 상자 위치표가 필요한가

![⑫ 표 없음: detect 실패 / ⑭ 표 있음: 적재 작업대에서 집어 되돌림](lesson15_why.png){width=1000}

### WorldState: 표 · 검사 · 갱신

![prompt() · check(plan) · apply()](lesson15_world.png){width=1000}

### LLM 은 의도, 코드는 사실

![누가 무엇을 정하나 · 프롬프트를 바꿔 가며 잰 정확도](lesson15_roles.png){width=1000}

### 시나리오 3 개

![빨강 → 파랑(되묻기) → 빨강 되돌리기](lesson15_scenarios.png){width=1000}

## 2. 실행: lessons/10_final_project

### 터미널: 01_world_plan (시뮬레이터 없이)

```bash
./scripts/mobile_openarm exec python lessons/10_final_project/01_world_plan.py
```

### 실행 결과: 01_world_plan

![같은 8 문장, 표 없음 7/8 · 표 있음 8/8](lesson15_cli_world_plan.png){width=1000}

### 실행: 터미널 1 (start)

```bash
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false   # ⑫ 와 같다
```

### 실행 결과: 시작 화면

![창고 가운데에서 시작, 상자 세 개는 픽업 작업대 위](lesson15_start.png){width=1000}

### 실행: 터미널 2 (task_manager)

```bash
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
```

### 실행 결과: 터미널 2

![task_manager: /execute_command · /execute_plan](lesson13_t2.png){width=1000}

### 터미널 3: 02_final_mission

```bash
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py               # 시나리오 3 개 이어서
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py --keyboard    # 직접 입력
```

### 실행 결과: 시나리오 1

![빨간 상자: 확인 → 5 단계 179 s → 표: 빨강 = 적재 작업대 ('남은 거리' · PickPlace 세부 줄 생략)](lesson15_cli_s1.png){width=1000}

### 실행 결과: 시나리오 2

![색 되묻기 → 파란 거 → 5 단계 178 s](lesson15_cli_s2.png){width=1000}

### 실행 결과: 시나리오 3

![표를 보고 적재 작업대에서 집기 → 픽업 작업대에 놓기, 140 s](lesson15_cli_s3.png){width=1000}

### 세 시나리오의 경로

![/ground_truth 경로: 출발 → 픽업 ↔ 적재](lesson15_routes.png){width=1000}

### 장면: 집기와 놓기

![시나리오마다 집기 · 놓기 (기록한 상태를 오프스크린 렌더)](lesson15_scenes.png){width=1000}

### 움직이는 그림: 세 시나리오 이어서

![Final Mission (움직이는 그림)](lesson15_final.gif){width=720}

### 시간 흐름

![단계별 시간과 표 변화 (실측)](lesson15_timeline.png){width=1000}

### 터미널: 표가 처음 상태일 때 시나리오 3 만

```bash
./scripts/mobile_openarm exec python lessons/10_final_project/02_final_mission.py --dry-run --scenario 3
```

### 실행 결과: 코드가 실행을 막는다

![빨간 상자는 이미 픽업 작업대에 있다 → 실행 0 회](lesson15_cli_dry.png){width=1000}

### 끝낼 때: stop

```bash
./scripts/mobile_openarm stop      # 이 워크스페이스의 노드를 모두 종료
```

### 실행 결과: 남은 프로세스가 있으면 start 가 멈춘다

![이전 실행이 남아 있으면 start 가 목록을 보여 주고 멈춤 → stop 으로 정리](lesson15_cli_stop.png){width=1000}

## 3. 코드

### 표를 프롬프트로 - world.py WorldState.prompt 함수

```python
# src/warehouse_lecture/warehouse_lecture/commands/world.py
    def prompt(self):
        lines = [f"- {p}({TARGET_KO[p]}): {loc}({self._ko(loc)})" for p, loc in self.parcels.items()]
        return ("현재 상자 위치 (로봇이 마지막으로 확인한 것):\n" + "\n".join(lines) + "\n"
                "상자 위치 규칙 (위의 기본값 pick_table / place_table 보다 우선):\n"
                "- detect · pick 은 그 상자가 지금 있는 작업대(이 표)에서 한다. navigate 도 그 작업대로 간다.\n"
                "- 문장이 도착 작업대를 말하면 그 작업대를 그대로 쓴다. 상자가 이미 거기 있어도 바꾸지 않는다 (그 확인은 프로그램이 한다).\n"
                "- 문장에 도착지가 없거나 '다시', '원래 자리', '돌려놔' 라고만 하면 도착지는 그 상자가 지금 없는 다른 작업대다.\n"
                "- 위치가 unknown 인 상자는 pick_table 에서 찾는다.\n")
```

- LLM 은 창고를 볼 수 없음 → 상자마다 한 줄씩 지금 위치를 글로 알려 줌
- 앞 글 프롬프트의 기본값(`pick_table` → `place_table`)보다 이 표가 우선이라고 명시
- "이미 거기 있다" 판단은 LLM 에게 맡기지 않고 코드(`check`)가 함

### system 프롬프트 끝에 붙이기 - plan_parser.py PlanParser.parse 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/plan_parser.py
    def parse(self, text, context=None, world=None):
        system = SYSTEM if world is None else SYSTEM + "\n" + world.prompt()
        messages = [{"role": "system", "content": system}]
        for q, plan in EXAMPLES:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": plan.model_dump_json()})
        for user, assistant in (context or []):
            messages.append({"role": "user", "content": user})
            messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": text})
        return self.llm.parse(messages, RobotPlan, temperature=0.0, purpose="plan_parse")
```

- `world` 가 없으면 앞 글과 같은 프롬프트 → 이전 예제는 그대로 동작
- 메시지 순서: system(규칙 + 표) → 예시 → 이전 대화 → 이번 문장
- 표는 호출할 때마다 새로 만들어짐 → 상자를 옮긴 뒤에는 바뀐 위치가 들어감

### 출발 작업대 검사 - world.py WorldState.check 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/world.py
    def check(self, plan):
        problems, belief = [], dict(self.parcels)
        held = next((p for p, loc in belief.items() if loc == HELD), None)
        origin = {}
        for step in plan.steps:
            if step.action == StepAction.pick:
                loc = belief.get(step.target, UNKNOWN)
                origin[step.target] = loc
                if loc not in (step.location.value, UNKNOWN, HELD):
                    origin[step.target] = "wrong_source"
                    problems.append(f"{TARGET_KO.get(step.target, step.target)}는 {self._ko(loc)}에 있다 "
                                    f"(계획: {self._ko(step.location.value)}에서 집기)")
```

- `belief` = 표의 복사본 · 계획을 단계대로 따라가며 바꿔 봄 (실제 표는 그대로)
- 표의 위치와 계획의 pick 작업대가 다르면 문제로 기록
- `unknown` · `held` 인 상자는 틀렸다고 할 근거가 없어 통과

### 이미 도착지에 있나 - world.py WorldState.check 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/world.py
                # (이어서)
                belief[step.target], held = HELD, step.target
            elif step.action == StepAction.place and held:
                if belief.get(held) == HELD and self.parcels.get(held) == step.location.value:
                    if origin.get(held) == "wrong_source":
                        problems.pop()      # say the simpler thing instead
                    problems.append(f"{TARGET_KO.get(held, held)}는 이미 {self._ko(step.location.value)}에 있다")
                belief[held], held = step.location.value, None
        return problems
```

- 실행 전 표(`self.parcels`)의 위치 = 놓을 작업대 → "이미 거기 있다" 로 돌려보냄
- 출발지 오류와 겹치면 앞의 것을 지우고(`pop`) 더 쉬운 문장 하나만 남김
- 빈 목록 = 표와 계획이 어긋나지 않음

### 끝난 단계만 반영 - world.py WorldState.apply 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/world.py
    def apply(self, plan, steps_done, success):
        before = dict(self.parcels)
        held = next((p for p, loc in self.parcels.items() if loc == HELD), None)
        for i, step in enumerate(plan.steps):
            if i < steps_done:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target], held = HELD, step.target
                elif step.action == StepAction.place and held:
                    self.parcels[held], held = step.location.value, None
```

- 계획이 아니라 Task Manager 결과의 `steps_done` 까지만 표에 반영
- pick 이 끝나면 `held` · place 가 끝나면 그 작업대 → 중간에 멈추면 든 채로 남음

### 실패한 단계는 unknown - world.py WorldState.apply 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/world.py
            # (이어서)
            elif i == steps_done and not success:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target] = UNKNOWN
                elif step.action == StepAction.place and held:
                    self.parcels[held] = UNKNOWN
                break
        self.history.append((before, dict(self.parcels)))
        return self.parcels
```

- pick · place 도중 실패하면 상자가 어디 있는지 알 수 없음 → `unknown`
- `i == steps_done` = 실패한 바로 그 단계 · 그 뒤 단계는 보지 않음 (`break`)
- `history` 에 실행 전후의 표를 남김

### 계획 → 검사 - dialog.py PlanDialogManager.handle 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/dialog.py
        plan = self.parser.parse(utterance, context=self.context, world=self.world)
        problems = plan.validate_world()
        if self.world is not None and not problems:
            problems = self.world.check(plan)
        self._remember(utterance, plan)
        if not plan.steps or problems:
            if plan.steps and problems:   # the plan exists but cannot run: say why, not the LLM's "will do"
                reply = "그대로는 실행할 수 없습니다 (" + "; ".join(problems) + "). 다시 말씀해 주세요."
            else:
                reply = plan.reply or ("; ".join(problems) if problems else "")
```

- 검사 두 번: `validate_world` (계획 자체의 모순) → `world.check` (위치표와의 모순)
- 단계는 있는데 문제가 있으면 LLM 의 `reply` 대신 이유를 넣은 문장으로 되물음

### 실행 → 표 갱신 - dialog.py PlanDialogManager._execute 함수

```python
# src/warehouse_lecture/warehouse_lecture/commands/dialog.py
    def _execute(self, plan, text):
        if self.executor is None:
            return self._say("execute(dry)", plan.describe(), plan)
        self._say("execute", plan.reply or plan.summary or plan.describe(), plan)
        result = self.executor(plan, text)
        if self.world is not None and result is not None:
            self.world.apply(plan, result.steps_done, result.success)
        spoken = getattr(result, "spoken", None) or str(result)
        return self._say("result", spoken, plan)
```

- 실행이 끝나면 결과의 `steps_done` · `success` 로 표를 고침 → 다음 문장의 프롬프트에 반영
- `executor` 가 없으면 실행 없이 단계 목록만 말함 (dry)

### 시나리오와 표 하나 - 02_final_mission.py 발췌

```python
# lessons/10_final_project/02_final_mission.py
SCENARIOS = {
    1: ["픽업 작업대로 가서 빨간 상자를 집고 적재 작업대로 옮겨", "응"],
    2: ["상자 하나 적재대로 옮겨 줘", "파란 거", "응"],
    3: ["빨간 상자 다시 픽업대로 가져와", "응"],
}
    # (main 안)
    world = WorldState()
    dm = PlanDialogManager(PlanParser(llm), executor=execute, speak=speak, world=world)
```

- 문장 목록 = 한 시나리오의 대화 · 마지막 "응" 은 확인 질문의 대답
- `WorldState()` 초기값 = 세 상자 모두 `pick_table`
- 앞 글의 `PlanDialogManager` 에 `world=` 하나만 더 넘김

### 시나리오 이어서 실행 - 02_final_mission.py main 함수 발췌

```python
# lessons/10_final_project/02_final_mission.py
        for n in a.scenario or sorted(SCENARIOS):
            print(f"\n===== 시나리오 {n}")
            dm.context.clear()          # each scenario is a new conversation; the world table carries over
            for text in SCENARIOS[n]:
                print(f"[user] {text}")
                turn(text)
            print(f"[world] {world.describe()}")
```

- `context` 는 시나리오마다 비움 (새 대화) · `world` 표는 지우지 않아 계속 이어짐
- 시나리오 3 의 "다시 픽업대로" 는 시나리오 1 이 바꾼 표가 있어야 풀림

### 해 볼 것

- `--keyboard` 로 "노란 상자도 적재대로" → "노란 상자 원래 자리로" 를 이어서 보내고 `[world]` 줄 보기
- `01_world_plan.py` 의 `CASES` 에 문장 하나 추가 (예: 세 상자가 모두 적재 작업대일 때 "상자 다 원래대로")
- `world.py` 의 "말한 도착지는 그대로" 규칙 줄을 지우고 `01_world_plan.py --only world` 를 다시 실행해 정확도 비교
