# 04. 전반부 통합 Demo: 창고 순찰과 웹 대시보드 (Day 1 ⑤⑥ 마무리)

## 목표

⑤ 에서 만든 지도로 Nav2 순찰을 돈다. 정지마다 실제 위치(/ground_truth)와 AMCL · odom 추정을 비교해 기록한다. 같은 순찰을 브라우저 대시보드(지도 · 카메라 · 미션 상태)로 본다.

## 실행: 순찰

```bash
# 터미널 1: Nav2 (⑤ 에서 저장한 지도. 지도가 없으면 map:= 를 빼면 패키지 지도를 쓴다)
./scripts/mobile_openarm nav moveit:=false map:=$PWD/artifacts/maps/my_warehouse.yaml
# 터미널 2: 순찰 (기본 경로: pick_table → rack_a → rack_b → place_table → center_aisle)
./scripts/mobile_openarm exec python lessons/04_navigation/patrol.py
./scripts/mobile_openarm exec python lessons/04_navigation/patrol.py --route pick_table,center_aisle --loops 2
# 터미널 3: 순찰 상태 (JSON)
./scripts/mobile_openarm exec ros2 topic echo --once /patrol/status
```

- "Managed nodes are active" 뒤 20 초쯤 기다린 다음 순찰을 시작한다 (바로 보내면 Nav2 가 goal 을 거부할 수 있다).
- 끝낼 때: `./scripts/mobile_openarm stop`

## 실행: 웹 대시보드

```bash
# 터미널 1: 카메라 프레임을 브라우저용 JPEG 로 남기는 frame_tap 핸들러를 붙여서
./scripts/mobile_openarm nav moveit:=false map:=$PWD/artifacts/maps/my_warehouse.yaml \
  camera_fps:=5 camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline
# 터미널 2: 대시보드 서버 → 브라우저에서 http://localhost:8080
./scripts/mobile_openarm exec python lessons/04_navigation/dashboard/server.py   # 다른 PC 에서 보려면 --host 0.0.0.0
# 터미널 3: 순찰 (대시보드의 [순찰 시작] 버튼을 기다린다)
./scripts/mobile_openarm exec python lessons/04_navigation/patrol.py --wait
```

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| 순찰: Nav2 goal · 목표 근처 워치독 · 정지마다 기록 · /patrol/status | `lessons/04_navigation/patrol.py` |
| 대시보드 서버: SSE · 지도 · MJPEG · 순찰 명령 | `lessons/04_navigation/dashboard/server.py` |
| 카메라 프레임 저장 (시뮬레이터 안 Python 핸들러) | `lessons/04_navigation/dashboard/frame_tap.py` |
| 브라우저 | `lessons/04_navigation/dashboard/static/` |
| 랙 통로 제자리 회전 (RotationShim) | `src/mobile_openarm_navigation/config/nav2.yaml` `FollowPath` |

⑬ 웹 대시보드(`lessons/09_web_dashboard`)는 이 서버를 그대로 쓰고 자연어 지령 입력을 더한다.
