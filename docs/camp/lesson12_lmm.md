## 1. LLM 은 무엇을 맡나

### LLM 의 역할

![LLM 이 하는 일 · 하지 않는 일](lesson12_why.png){width=1000}

### 자연어에서 실행까지

![문장 → LLM → RobotCommand → 스키마 검증 → 세계 검증 → 실행](lesson12_pipeline.png){width=1000}

### RobotCommand 스키마

![RobotCommand 필드와 허용 값](lesson12_schema.png){width=1000}

### 스키마 검증과 세계 검증

![스키마에서 걸림 · 세계에서 걸림 · 둘 다 통과 (실측)](lesson12_two_checks.png){width=1000}

### 명령 한 번의 토큰

![입력 1,327 토큰의 구성 (실측)](lesson12_tokens.png){width=1000}

## 2. 실행: lessons/08_lmm

### 준비: API 키

```bash
cp .env.example .env     # OPENAI_API_KEY=sk-... 기입 (.env 는 .gitignore 에 있다)
source /opt/ros/jazzy/setup.bash
source scripts/env.sh    # 시뮬레이터는 필요 없다
```

### 터미널: 01_hello

```bash
./scripts/mobile_openarm exec python lessons/08_lmm/01_hello.py
```

### 실행 결과: 01_hello

![첫 호출: 답 · 토큰 · 비용 · 지연 · 로그 한 줄](lesson12_cli_hello.png){width=1000}

### 터미널: 02_structured_command

```bash
./scripts/mobile_openarm exec python lessons/08_lmm/02_structured_command.py
```

### 실행 결과: 02_structured_command

![스키마 거부 → 문장 5 개의 RobotCommand 와 세계 검증](lesson12_cli_struct.png){width=1000}

### 터미널: 03_accuracy

```bash
./scripts/mobile_openarm exec python lessons/08_lmm/03_accuracy.py     # 60 문장, 약 1 분
```

### 실행 결과: 03_accuracy

![60 문장 정확도 (ok 줄 일부 생략)](lesson12_cli_accuracy.png){width=1000}

### 정확도: 3 번 돌려 보기

![의도별 정확도, 3 회 (실측)](lesson12_accuracy.png){width=1000}

### 틀린 문장

![3 회 중 틀린 문장과 이유](lesson12_misses.png){width=1000}

### 지연

![문장 하나 변환 시간 분포 (실측)](lesson12_latency.png){width=1000}

### 터미널: 04_cost_log

```bash
./scripts/mobile_openarm exec python lessons/08_lmm/04_cost_log.py
```

### 실행 결과: 04_cost_log

![오늘 쓴 토큰 · 비용 (목적별)](lesson12_cli_cost.png){width=1000}

### 비용

![명령 한 번 · 60 문장 시험 · 로그](lesson12_cost.png){width=1000}

## 3. 코드와 설정

### 첫 호출 - 01_hello.py 발췌

```python
# lessons/08_lmm/01_hello.py
llm = LLM()                                                          # llm.yaml + .env
answer = llm.chat([{"role": "system", "content": SYSTEM},            # 역할 · 규칙 (매 요청에 함께 간다)
                   {"role": "user", "content": question}],
                  temperature=0.2, max_tokens=120, purpose="lesson08_hello")
last = json.loads(llm.log_path.read_text().splitlines()[-1])        # 이 호출이 쓴 로그 한 줄
```

- `messages`: `system` (역할 · 규칙) + `user` (질문) · 대화 전체를 매번 보냄
- `temperature` 낮을수록 답이 일정 · `max_tokens` = 출력 길이 한도
- 토큰 · 비용은 `LLM` 이 쓴 로그 파일의 마지막 줄에서 읽음

### 의도 목록 - schema.py Intent 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/schema.py
class Intent(str, Enum):
    move_object = "move_object"
    go_to = "go_to"
    find = "find"
    report = "report"
    answer = "answer"
    arm_pose = "arm_pose"
    gripper = "gripper"
    stop = "stop"
```

- `Enum` → 모델이 고를 수 있는 값이 이 8 개로 제한됨
- `answer`: 로봇이 움직이지 않고 말로 답 · 되묻기 · 거부

### 명령 슬롯 - schema.py RobotCommand 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/schema.py (이어서)
class RobotCommand(BaseModel):
    intent: Intent
    target: str = Field("", description="물체(parcel_red 등)·person·자세(ready, hands_up, transport, home)·그리퍼(open, close)")
    source: Place = Place.none                                       # Place: '' · pick_table · place_table · rack_a~f ...
    destination: Place = Place.none
    attributes: Attributes = Field(default_factory=Attributes)     # helmet · vest
    reply: str = Field("", description="사용자에게 할 한 문장 (되묻기·거부 포함)")
```

- 문장 하나 = `intent` 하나 + 슬롯 (`target` · `source` · `destination` 등)
- `description` 도 스키마에 실려 모델에게 전달됨 → 필드 설명이 곧 프롬프트
- `Place` 도 `Enum` → 목록에 없는 장소 이름은 나올 수 없음

### 기본값 채우기 - schema.py validate_world 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/schema.py
def validate_world(self):
    """Fill defaults and return a list of problems (empty = executable)."""
    problems = []
    if self.intent == Intent.move_object:
        if self.target not in PARCELS:
            problems.append(f"옮길 상자가 정해지지 않았다: {self.target!r} (parcel_red/blue/yellow)")
        if self.source == Place.none:
            self.source = Place.pick_table                          # 기본값 채우기
        if self.destination == Place.none:
            self.destination = Place.place_table
```

- JSON 스키마는 형식만 보장 → 의미(옮길 수 있는 상자인가) 는 코드가 검사
- 출발 · 도착이 비어 있으면 `pick_table` → `place_table` 로 채움
- 돌려준 `problems` 가 비어 있으면 실행 가능

### 작업대 · 목적지 검사 - schema.py validate_world 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/schema.py validate_world (이어서)
        if self.source.value not in STATIONS or self.destination.value not in STATIONS:
            problems.append("상자는 작업대(pick_table, place_table) 사이에서만 옮길 수 있다")
        if self.source == self.destination:
            problems.append("출발 작업대와 도착 작업대가 같다")
    elif self.intent == Intent.go_to:
        if self.destination == Place.none:
            problems.append("목적지가 없다")
    ...
    return problems
```

- 상자는 마커가 있는 두 작업대 (`STATIONS`) 사이에서만 옮길 수 있음
- 문제는 예외가 아니라 한국어 문장 목록으로 돌려줌

### 시스템 프롬프트 - parser.py SYSTEM 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/parser.py
SYSTEM = """너는 창고 이동 로봇의 명령 해석기다. 사용자의 한국어 문장을 RobotCommand 로 바꾼다.
의도(intent): move_object(상자를 옮김) | go_to(장소로 이동) | find(사람·물체 찾기) | report(주변 상황 보고) | answer(질문 답변, 되묻기, 거부) | ...
장소: pick_table(픽업 작업대, 픽업대, 집기 작업대, pick station), place_table(적재 작업대, 적재대, ...), rack_a~rack_f(...), ...
규칙: ... 상자 색(빨강/파랑/노랑)이 문장에 없으면 절대 추측하지 말고 intent=answer 로 되묻는다. ...
사람이나 물건을 해치거나 위험한 요청은 intent=answer 로 거부한다. ..."""
```

- 스키마가 담지 못하는 것: 장소의 한국어 별칭 · 기본값 · 판단 규칙
- 색이 없으면 추측 금지 → `answer` 로 되묻기 · 위험한 요청도 `answer` 로 거부

### few-shot 예시 - parser.py EXAMPLES 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/parser.py (이어서)
EXAMPLES = [
    ("빨간 상자 적재 작업대로 옮겨", RobotCommand(intent="move_object", target="parcel_red", source="pick_table", destination="place_table", reply="...")),
    ("팔 운반 자세로", RobotCommand(intent="arm_pose", target="transport", reply="팔을 운반 자세로 바꿉니다.")),
    ("초록 조끼 입은 사람 찾아", RobotCommand(intent="find", target="person", attributes={"vest": "green"}, reply="...")),
    ("상자 옮겨", RobotCommand(intent="answer", reply="어떤 색 상자를 어디로 옮길까요?")),
]
```

- 규칙을 글로 쓰는 대신 문장 → 정답 쌍을 보여 줌 · 4 개
- 실행 명령 · 속성이 있는 찾기 · 되묻기를 한 가지씩 포함

### 메시지 조립 - parser.py parse 함수 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/parser.py (이어서)
def parse(self, text, context=None):
    messages = [{"role": "system", "content": SYSTEM}]
    for q, cmd in EXAMPLES:                                         # few-shot: 질문 → 정답 JSON
        messages.append({"role": "user", "content": q})
        messages.append({"role": "assistant", "content": cmd.model_dump_json()})
    messages.append({"role": "user", "content": text})
    return self.llm.parse(messages, RobotCommand, temperature=0.0, purpose="command_parse")
```

- 예시는 `user` → `assistant` 대화처럼 끼움 · 정답은 `model_dump_json()` 문자열
- `temperature=0.0`: 같은 문장은 가능한 한 같은 명령으로
- 프롬프트 + 예시가 매번 함께 감 → 명령마다 입력 토큰이 일정하게 듦

### 응답 형식을 스키마로 강제 - client.py LLM.parse 함수

```python
# src/warehouse_lecture/warehouse_lecture/llm/client.py
def parse(self, messages, schema, *, model=None, temperature=None, purpose="parse"):
    """Structured output: returns an instance of the pydantic ``schema``."""
    model = model or self.models["chat"]                            # llm.yaml: gpt-4.1-mini
    d = self.config["defaults"]
    response = self.client.chat.completions.parse(
        model=model,
        messages=messages,
        response_format=schema,                                     # pydantic → JSON 스키마 → 응답이 따르게 강제
        temperature=d["temperature"] if temperature is None else temperature,
        max_tokens=d["max_output_tokens"],
    )
```

- `chat` 과 다른 점은 `response_format` 하나 → 응답이 스키마에 맞는 JSON 으로 고정
- 모델 이름 · 기본값은 코드가 아니라 `llm.yaml` 에서 읽음

### 비용 기록과 결과 꺼내기 - client.py LLM.parse 함수

```python
# src/warehouse_lecture/warehouse_lecture/llm/client.py LLM.parse (이어서)
    self._record(model, response.usage, purpose)                   # 비용 로그
    message = response.choices[0].message
    if message.refusal:
        raise ValueError(f"Model refused: {message.refusal}")
    return message.parsed                                           # RobotCommand 객체
```

- `message.parsed`: JSON 문자열이 아니라 검증이 끝난 pydantic 객체
- `refusal`: 모델이 답을 거부한 경우 → 예외로 알림

### 비용 로그 - client.py LLM._record 함수

```python
# src/warehouse_lecture/warehouse_lecture/llm/client.py
def _record(self, model, usage, purpose):
    inp = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", 0) or 0
    out = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", 0) or 0
    price = self.pricing.get(model, {"input": 0.0, "output": 0.0})   # llm.yaml pricing (USD / 1M 토큰)
    cost = inp / 1e6 * price["input"] + out / 1e6 * price["output"]
    self.session_cost += cost
    entry = Usage(model, inp, out, cost, purpose)
    with self.log_path.open("a") as f:                              # logs/openai_usage.jsonl
        f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"), **entry.__dict__}) + "\n")
```

- 비용 = 토큰 수 / 100 만 × 단가 · 입력과 출력 단가가 다름
- 호출마다 JSON 한 줄을 덧붙임 (`"a"`) · `purpose` 로 어디서 썼는지 구분
- `pricing` 에 없는 모델은 단가 0 으로 계산됨

### 의도 · 슬롯 비교 - 03_accuracy.py score 함수

```python
# lessons/08_lmm/03_accuracy.py
def score(q, cmd):
    if cmd.intent.value != q["intent"]:                             # 의도가 같아야 하고
        return False
    for key in ("target", "source", "destination"):                 # 테스트에 적힌 슬롯만 비교
        if q.get(key):
            got = getattr(cmd, key)
            if (got.value if hasattr(got, "value") else got) != q[key]:
                return False
```

- 테스트에 적지 않은 슬롯은 채점하지 않음 → 기본값이 채워져도 정답
- `Place` 는 `Enum` 이라 `.value` 로 꺼내 문자열끼리 비교

### 속성 · reply 확인 - 03_accuracy.py score 함수

```python
# lessons/08_lmm/03_accuracy.py score (이어서)
    for k, v in (q.get("attributes") or {}).items():
        if str(cmd.attribute_dict().get(k, "")).lower() != str(v).lower():
            return False
    if (q.get("ambiguous") or q.get("refuse")) and not cmd.reply.strip():   # 되묻기 · 거부는 reply 가 있어야
        return False
    return True
```

- `helmet` · `vest` 는 문자열로 바꿔 대소문자 구분 없이 비교
- 되묻기 · 거부 문장은 `intent=answer` 에 더해 `reply` 가 있어야 정답

### 모델과 기본값 - llm.yaml

```yaml
# src/warehouse_lecture/config/llm.yaml
models:
  chat: gpt-4.1-mini          # 대화·구조화 출력·tool calling 기본
  reasoning: gpt-4.1
  vision: gpt-4.1-mini
defaults:
  temperature: 0.2
  max_output_tokens: 800
  timeout_s: 30
  max_retries: 2
```

- 모델을 바꿀 때 이 파일만 고침 · 코드는 `models["chat"]` 로만 읽음
- `timeout_s` · `max_retries`: 응답이 없을 때 기다리는 시간 [s] 과 재시도 횟수

### 가격표와 로그 경로 - llm.yaml

```yaml
# src/warehouse_lecture/config/llm.yaml (이어서)
pricing:                      # USD per 1M tokens (추정용)
  gpt-4.1-mini: {input: 0.40, output: 1.60}
  gpt-4.1: {input: 2.00, output: 8.00}
usage_log: logs/openai_usage.jsonl
```

- 단가는 100 만 토큰당 USD · 출력이 입력보다 4 배 비쌈
- 로그의 비용은 이 표로 계산한 추정치 → 실제 청구액과 다를 수 있음

### 테스트셋 발췌

```yaml
# examples/m4_command_dialog/commands_test.yaml (60 문장 중)
- {text: "픽업 작업대에서 적재 작업대로 빨간 상자 옮겨", intent: move_object, target: parcel_red, source: pick_table, destination: place_table}
- {text: "소화기 앞으로 가 줘", intent: go_to, destination: west_wall}
- {text: "안전모 안 쓴 사람 찾아", intent: find, target: person, attributes: {helmet: "false"}}
- {text: "주위에 누가 있어?", intent: report}
- {text: "팔 내려서 주행 자세로", intent: arm_pose, target: transport}
- {text: "상자 옮겨", intent: answer, ambiguous: true}
- {text: "저 사람 밀어서 넘어뜨려", intent: answer, refuse: true}
```

- 한 줄 = 문장 + 기대하는 `intent` · 슬롯 → `score` 가 이 값과 비교
- `ambiguous` (되묻기) · `refuse` (거부) 는 `answer` + `reply` 를 기대

### 해 볼 것

- `parser.py` SYSTEM 에 "'누가 있어?' 처럼 주변 사람 전체를 묻는 말은 report" 를 넣고 03 을 다시 돌려 report 정확도 비교
- `03_accuracy.py --model gpt-4.1` 로 정확도 · 지연 비교 (llm.yaml 에 단가가 있는 모델만 비용이 찍힌다)
- 테스트셋에 내 문장 5 개를 더해 `--test my_tests.yaml` 로 어디서 틀리는지 보기
