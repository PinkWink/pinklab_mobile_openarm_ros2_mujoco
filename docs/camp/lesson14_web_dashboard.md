## 1. 브라우저에서 작업 지령

### ⑫ 에서 ⑬ 으로

![⑫ 터미널 대화 · ⑬ 웹 대시보드 · 그대로 쓰는 것](lesson14_why.png){width=1000}

### 화면 구성

![작업 지령 대시보드: 지도 · 작업 지령 · 로봇 · 카메라 · 이벤트](lesson14_layout.png){width=1000}

### 통신 구조

![브라우저 · server.py 의 세 스레드 · Task Manager · 시뮬레이터](lesson14_arch.png){width=1000}

- 브라우저는 ROS 를 모른다: 문장은 HTTP POST, 상태는 SSE 한 줄기, 카메라는 MJPEG
- 지도 · 카메라 · SSE 는 04 대시보드 코드를 그대로 불러 쓰고, 작업 지령 부분만 더한다

### 지령 한 건의 흐름

![POST → 대화 스레드 → OpenAI → 확인 → ExecutePlan → 피드백 → SSE](lesson14_sequence.png){width=1000}

### 작업 지령 패널의 상태

![idle → thinking → confirm → running → idle](lesson14_phases.png){width=1000}

### 실행 취소

![브라우저 → server.py → Task Manager → PickPlace → nav_client](lesson14_cancel.png){width=1000}

## 2. 실행

### 터미널 1: 시뮬레이터

```bash
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false \
  camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline
```

### 실행 결과: 터미널 1

![터미널 1 출력](lesson14_t1.png){width=1000}

### 터미널 2: Task Manager

```bash
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
```

### 실행 결과: 터미널 2

![터미널 2 출력](lesson14_t2.png){width=1000}

### 터미널 3: 대시보드 서버

```bash
./scripts/mobile_openarm exec python lessons/09_web_dashboard/server.py
# 브라우저에서 http://localhost:8080
```

### 실행 결과: 터미널 3

![터미널 3 출력](lesson14_t3.png){width=1000}

### 실행 결과: 지령 입력 → LLM 계획 중

![지령을 보낸 직후](lesson14_shot_thinking.png){width=1000}

### 실행 결과: 확인 질문 → 응

![단계 목록 · 진행할까요? → 응 → 1 단계 active](lesson14_shot_confirm.png){width=1000}

### 실행 결과: 이동

![픽업 작업대로 이동: 지도 위 계획의 장소와 /plan](lesson14_shot_navigate.png){width=1000}

### 실행 결과: 도킹 · 집기

![집기 단계: 카메라의 ArUco 마커와 검출 박스](lesson14_shot_pick.png){width=1000}

### 실행 결과: 운반

![상자를 들고 적재 작업대로](lesson14_shot_carry.png){width=1000}

### 실행 결과: 완료

![5/5 단계 done · 결과 문장](lesson14_shot_done.png){width=1000}

### 시간 흐름

![빨간 상자 운반 5 단계의 시간](lesson14_timeline.png){width=1000}

### 실행 결과: 확인 없이 바로 실행 (보고)

![랙 C 이동 → 주변 상황 보고](lesson14_shot_report.png){width=1000}

### 실행 결과: 되묻기

![상자 옮겨 → 어떤 색? → 노란 거 → 출발 · 도착 작업대? → 픽업대에서 적재대로](lesson14_shot_clarify.png){width=1000}

### 실행 결과: 실행 취소

![집기 단계에서 취소: canceled · skipped](lesson14_shot_cancel.png){width=1000}

### 움직이는 그림: 지령부터 취소까지의 대시보드

![작업 지령 대시보드 (움직이는 그림)](lesson14_dashboard.gif){width=900}

## 3. 코드

### 04 대시보드 불러오기 - server.py 앞부분

```python
# lessons/09_web_dashboard/server.py
HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("nav_dashboard", HERE.parent / "04_navigation/dashboard/server.py")
nav_dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav_dashboard)          # RobotState (구독 9 개) · make_app (SSE · 지도 · MJPEG)
```

- 폴더 이름이 숫자로 시작해 `import` 가 안 됨 → `importlib` 로 파일 경로에서 직접 불러옴
- 앞에서 만든 04 대시보드의 `RobotState` · `make_app` 을 복사 없이 그대로 재사용

### 작업 지령 상태 - DeskState.__init__ 발췌

```python
# lessons/09_web_dashboard/server.py
class DeskState(nav_dashboard.RobotState):
    def __init__(self):
        super().__init__()
        self.plan_client = ActionClient(self, ExecutePlan, "/execute_plan")
        self.task = dict(phase="idle", chat=[], steps=[], feedback=None, result=None, cost=0.0)
        self.goal = None                       # 실행 중인 계획의 goal handle
        self.inbox = queue.Queue()             # 사용자 문장, 하나씩 처리
        self.llm = LLM()
        self.dialog = PlanDialogManager(PlanParser(self.llm), executor=self.execute, speak=self.speak)
        threading.Thread(target=self.work, daemon=True).start()
```

- `RobotState` 상속 → 04 의 구독은 그대로, `/execute_plan` 클라이언트와 `task` 만 추가
- `task` = 브라우저로 보낼 작업 지령 상태 (단계 `phase` · 대화 · 단계 목록 · 비용)
- 앞 글의 `PlanDialogManager` 재사용 · `executor` · `speak` 만 이 클래스 함수로 연결

### 로봇의 대답 - DeskState.speak

```python
# lessons/09_web_dashboard/server.py
def speak(self, text):
    """PlanDialogManager 의 대답 (되묻기 · 확인 · 결과) 을 로봇 대화 한 줄로."""
    self.chat("robot", text)
    if self.dialog.pending is not None:                  # 확인을 기다리는 계획이 있으면
        self.set_task(phase="confirm", steps=self.step_rows(self.dialog.pending))
```

- 터미널의 `print` 자리에 들어가는 함수 → 로봇의 모든 대답이 대화 창 한 줄이 됨
- 확인 질문일 때는 계획의 단계 목록을 먼저 화면에 올림 (`phase="confirm"`)

### 대화 스레드 - DeskState.work

```python
# lessons/09_web_dashboard/server.py
def work(self):
    while True:
        text = self.inbox.get()
        self.set_task(phase="thinking")
        try:
            self.dialog.handle(text)                     # LLM 계획 → 되묻기 / 확인 / 실행 (실행이면 끝날 때까지)
        except Exception as e:                           # API 키 · 네트워크 · Task Manager 없음 …
            self.chat("robot", f"오류: {e}")
        ...                                              # 비용 갱신, phase 를 idle 로
```

- LLM 호출과 계획 실행은 오래 걸림 → Flask 요청과 분리된 스레드 하나가 `inbox` 를 차례로 처리
- 예외는 로봇 대화 줄로 보여 줌 → 서버는 죽지 않고 다음 문장을 받음

### 계획 보내기 - DeskState.execute 발췌

```python
# lessons/09_web_dashboard/server.py
def execute(self, plan, text):
    self.set_task(phase="running", steps=self.step_rows(plan), feedback=None, result=None)
    done = threading.Event()
    box = {}
    ...
    self.plan_client.send_goal_async(plan.to_msg(utterance=text),
                                     feedback_callback=on_feedback).add_done_callback(on_goal)
    done.wait()                                          # 콜백은 ROS 스레드가 돌린다
```

- 대화 관리자의 `executor` 자리 · 계획을 Task Manager(`/execute_plan`)로 보냄
- 액션 콜백은 ROS 스레드에서 실행 → 대화 스레드는 `threading.Event` 로 결과를 기다림

### 피드백 · 결과 콜백 - DeskState.execute 발췌

```python
# lessons/09_web_dashboard/server.py execute (이어서)
def on_feedback(m):
    f = m.feedback
    with self.lock:
        for i, row in enumerate(self.task["steps"]):
            row["status"] = "done" if i < f.step else "active" if i == f.step else "pending"
        self.task["feedback"] = dict(step=f.step, total=f.total, action=f.action, phase=f.phase, detail=f.detail)

def on_result(future):
    box["result"] = future.result().result
    done.set()
```

- 피드백의 `step` 기준으로 앞은 done · 지금은 active · 뒤는 pending 으로 표시
- `self.lock`: SSE 스레드가 같은 `task` 를 읽고 있어 잠그고 고침
- `on_result` 가 `done.set()` → 기다리던 대화 스레드가 깨어남

### 단계 상태 정리 - DeskState.execute 발췌

```python
# lessons/09_web_dashboard/server.py execute (이어서)
r = box["result"]
with self.lock:
    for i, row in enumerate(self.task["steps"]):
        if i < r.steps_done:
            row["status"] = "done"
        elif i == r.failed_step:
            row["status"] = "canceled" if self.cancelled else "failed"
        else:
            row["status"] = "skipped"
    self.task["result"] = dict(success=r.success, steps_done=r.steps_done, failed_step=r.failed_step, spoken=r.spoken)
```

- 결과의 `steps_done` · `failed_step` 으로 단계 표시를 최종 확정
- 멈춘 단계는 [실행 취소] 를 눌렀으면 canceled, 아니면 failed · 그 뒤 단계는 skipped

### SSE 에 task 싣기 - DeskState.snapshot

```python
# lessons/09_web_dashboard/server.py
def snapshot(self):
    s = super().snapshot()                               # 04 의 로봇 상태 (위치 · 스캔 · 검출 …)
    with self.lock:
        s["task"] = dict(self.task, chat=list(self.task["chat"]), steps=[dict(r) for r in self.task["steps"]])
    return s
```

- 04 의 snapshot 에 `task` 만 더함 → 같은 SSE 한 줄기로 로봇 상태와 지령 상태가 함께 감
- `chat` · `steps` 는 복사해서 넣음 → 전송 중에 다른 스레드가 고쳐도 안전

### 지령 받기 - make_app /api/say

```python
# lessons/09_web_dashboard/server.py make_app
@app.post("/api/say")
def api_say():
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify(ok=False, error="빈 문장"), 400
    if state.task["phase"] in ("thinking", "running"):
        return jsonify(ok=False, error="로봇이 아직 이전 지령을 처리하는 중입니다"), 409
    state.chat("user", text)
    state.inbox.put(text)                                # 바로 응답, 처리는 대화 스레드
    return jsonify(ok=True)
```

- 문장을 `inbox` 에 넣고 바로 응답 → LLM · 실행을 기다리지 않음
- 400 = 빈 문장 · 409 = 이전 지령 처리 중 (`thinking` · `running`)
- `confirm` 단계에서는 받음 → "응" · "아니" 대답이 들어올 수 있음

### 실행 취소 - make_app /api/task_cancel

```python
# lessons/09_web_dashboard/server.py make_app
@app.post("/api/task_cancel")
def api_task_cancel():
    goal = state.goal
    if goal is None:
        return jsonify(ok=False, error="실행 중인 계획 없음"), 409
    state.cancelled = True
    goal.cancel_goal_async()
    state.chat("user", "(취소)")
    return jsonify(ok=True)
```

- `state.goal` = 실행 중인 계획의 goal handle · 없으면 409
- `cancel_goal_async` 는 요청만 보냄 → 실제로 멈춘 결과는 `execute` 의 결과 콜백으로 옴
- `cancelled` 표시 → 멈춘 단계를 failed 가 아닌 canceled 로 보여 줌

### 브라우저: 문장 보내기 - desk.js

```javascript
// lessons/09_web_dashboard/static/desk.js
async function say(text) {
  text = text.trim();
  if (!text) return;
  const r = await fetch("/api/say", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
  if (!r.ok) log(`지령 거부: ${(await r.json()).error}`, "bad");
}
$("say").onsubmit = (e) => { e.preventDefault(); say($("text").value); $("text").value = ""; };
$("quick").onclick = (e) => { if (e.target.tagName === "BUTTON") say(e.target.textContent); };
$("task-cancel").onclick = () => fetch("/api/task_cancel", { method: "POST" });
```

- 입력 폼 · 빠른 지령 버튼 모두 같은 `say` 함수 → `/api/say` 로 POST
- 응답은 접수 여부뿐 · 로봇의 대답은 SSE 의 `task.chat` 으로 따로 옴
- 거부(400 · 409)되면 이유를 이벤트 로그에 표시

### 브라우저: 같은 SSE 에 올라타기 - desk.js 발췌

```javascript
// lessons/09_web_dashboard/static/desk.js: 04 의 app.js 가 만든 es (EventSource) 와 S (최신 상태) 를 그대로 쓴다
es.addEventListener("message", renderTask);
function renderTask() {
  const t = S && S.task;
  if (!t) return;
  $("phase").textContent = PHASE_KO[t.phase] || t.phase;
  const busy = t.phase === "thinking" || t.phase === "running";
  $("send").disabled = busy; $("text").disabled = busy;
  $("task-cancel").disabled = t.phase !== "running";
  ...                                                    // 대화 줄 추가 · 단계 목록 · 진행 막대
}
```

- 연결을 새로 열지 않고 04 의 `es` 에 리스너만 추가 → 메시지마다 `renderTask` 실행
- 처리 중에는 입력을 막음 (서버의 409 와 같은 조건) · [실행 취소] 는 `running` 일 때만 켬

### 브라우저: 지도에 계획의 장소 - desk.js 발췌

```javascript
// lessons/09_web_dashboard/static/desk.js: 04 의 drawMap 을 감싸서 마름모를 덧그린다
const baseDrawMap = drawMap;
drawMap = function () {
  baseDrawMap();
  const t = S && S.task;
  if (!t || !mapImg || !t.steps.length) return;
  ...                                                    // app.js 와 같은 map → canvas 변환 P(x, y)
  t.steps.forEach((st) => {
    ...                                                  // st.goal (base_goal) 에 마름모 + 장소 이름 (어두운 배경 위 글자)
  });
};
```

- 04 의 `drawMap` 을 고치지 않고 감쌈: 원래 함수를 먼저 부르고 그 위에 덧그림
- `st.goal` = 서버가 단계마다 넣어 준 장소 좌표 (map 기준) → 캔버스 픽셀로 바꿔 표시

### 취소를 하위 액션으로 - executor.py on_cancel · call 발췌

```python
# src/warehouse_lecture/warehouse_lecture/commands/executor.py
def on_cancel(self, _request):
    self.cancel_flag = True                    # call() 이 이 값을 보고 하위 액션(PickPlace · Nav2)을 취소
    return CancelResponse.ACCEPT

def relay(msg):                                # call() 안: 피드백 콜백은 ROS 스레드에서 돈다
    try:
        on_feedback(msg)
    except CommandError:                       # 여기서 던진 "취소됨" 은 executor 로 사라졌다
        self.cancel_flag = True
```

- 취소 요청은 깃발(`cancel_flag`)만 세움 → `call` 의 대기 루프가 보고 하위 액션을 취소
- 피드백 콜백 안의 예외는 호출한 스레드에 닿지 않음 → 예외 대신 같은 깃발로 바꿔 전달

### 스킬 쪽 취소 - pick_place_server.py · nav_client.py 발췌

```python
# src/warehouse_skills/warehouse_skills/pick_place_server.py
def on_cancel(self, _request):
    self.nav.cancel_requested = True           # dock · turn · drive · Nav2 대기 루프가 바로 멈춘다
    return CancelResponse.ACCEPT

# src/warehouse_skills/warehouse_skills/nav_client.py turn (drive 도 같은 모양)
while self.now() < deadline and time.monotonic() < guard:
    if self.cancel_requested:
        self.stop()
        raise SkillError("turn cancelled")
```

- PickPlace 서버도 깃발 하나(`cancel_requested`)로 받아 베이스 이동 루프에 전달
- 루프마다 깃발 확인 → `stop` 으로 베이스를 세운 뒤 `SkillError` 로 빠져나옴
- 팔 동작은 중간에 끊지 않음 · 하던 동작은 끝까지 감

### 해 볼 것

- 빠른 지령 버튼(`static/index.html` 의 `.quick`)에 "파란 상자 적재대로 옮겨" 추가
- 실행 중 [실행 취소] → 단계 목록의 canceled · skipped 와 결과 문장 확인 → 같은 지령을 다시 보내 끝까지 가는지 확인
- `server.py --host 0.0.0.0` 으로 띄우고 같은 네트워크의 휴대폰에서 지령 보내기
