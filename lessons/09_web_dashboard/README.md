# 09. MuJoCo Web Dashboard (Day 2 ⑬)

## 목표

브라우저에서 시뮬레이션과 로봇 상태를 보면서 한국어 작업 지령을 입력한다. 문장은 ⑫ 의 `PlanDialogManager`(LLM 계획 · 되묻기 · 확인)를 거쳐 Task Manager(`/execute_plan`)로 가고, 단계 진행과 결과 문장이 같은 화면에 돌아온다. 브라우저는 ROS 를 모른다: 문장은 HTTP POST 로 들어가고, 상태는 SSE 한 줄기로 나온다.

## 실행

```bash
# 터미널 1: 시뮬레이터 (⑫ 와 같고, 카메라 JPEG 를 브라우저용으로 남기는 frame_tap 핸들러만 다르다)
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false \
  camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline
# 터미널 2: Task Manager
./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
# 터미널 3: 대시보드 서버 → 브라우저에서 http://localhost:8080
./scripts/mobile_openarm exec python lessons/09_web_dashboard/server.py
```

- `.env` 에 `OPENAI_API_KEY` 가 있어야 한다 (⑪ 과 같음).
- "Managed nodes are active" 뒤 20 초쯤 기다린 다음 지령을 보낸다 (바로 보내면 Nav2 가 goal 을 거부할 수 있다).
- 다른 PC · 휴대폰에서 보기: `server.py --host 0.0.0.0` → `http://<이 PC IP>:8080`

## 화면에서 볼 것

- 작업 지령: 대화(사용자 · 로봇), 단계 목록(pending → active → done / failed / canceled / skipped), 진행 막대, Task Manager 피드백 한 줄, [실행 취소].
- 지도: 04 대시보드와 같고, 계획에 나온 장소를 보라색 마름모로 표시 (진행 중인 단계의 장소는 진하게).
- 검증 2026-10-12 (이 PC): "빨간 상자 적재대로 옮겨" → 확인 → "응" → 5/5 단계 약 235 s, LLM $0.001. "랙 C 가서 뭐 있는지 알려줘" → 확인 없이 2/2. 실행 중 [실행 취소] → 0.4 s 안에 PickPlace 정지, "2단계까지 마치고 취소했습니다."

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| 서버: 04 대시보드 재사용 + 지령 · 취소 API + SSE 의 task | `lessons/09_web_dashboard/server.py` |
| 브라우저: 대화 · 단계 · 지도 위 장소 | `lessons/09_web_dashboard/static/desk.js`, `index.html`, `desk.css` |
| 지도 · 카메라 · SSE (그대로 사용) | `lessons/04_navigation/dashboard/server.py`, `static/app.js`, `frame_tap.py` |
| 대화 상태 (되묻기 · 확인) | `src/warehouse_lecture/warehouse_lecture/commands/dialog.py` `PlanDialogManager` |
| 단계 실행 · 취소 전달 | `src/warehouse_lecture/warehouse_lecture/commands/task_manager.py`, `executor.py` `on_cancel()`, `call()` |

## 해 볼 것

- 빠른 지령 버튼(`index.html` 의 `.quick`)에 "파란 상자 적재대로 옮겨" 를 추가한다.
- 실행 중에 [실행 취소] → 단계 목록의 canceled / skipped 와 결과 문장을 본다. 이어서 같은 지령을 다시 보내 끝까지 가는지 본다.
- `server.py --host 0.0.0.0` 으로 띄우고 휴대폰에서 지령을 보낸다.
