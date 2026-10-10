# 07. Navigation + Pick & Place (Day 2 ⑩)

## 목표

창고 가운데에서 출발해 픽업 작업대의 상자를 집고, 창고를 가로질러 적재 작업대에 놓는다. PickPlace 액션 하나(`phase=all`)가 Nav2 주행 → ArUco 도킹 → 카메라 위치 확인 → MoveIt 파지 → 운반 → 주행 → 도킹 → 놓기를 차례로 돌린다. 06 모듈(같은 작업대)에 주행이 붙은 것.

## 실행

```bash
# 기본 spawn (창고 가운데 0, 0). Nav2 + AMCL 이 warehouse 지도로 뜬다.
H=warehouse_lecture.vision
LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start camera_depth:=true locate:=vision viewer:=true rviz:=false

# "Managed nodes are active" 뒤 20 초쯤 기다린 다음 (바로 보내면 Nav2 가 goal 을 거부할 수 있다)
./scripts/mobile_openarm exec python lessons/07_nav_pick_place/transport.py red      # pick_table → place_table
./scripts/mobile_openarm exec python lessons/07_nav_pick_place/transport.py blue
./scripts/mobile_openarm exec python lessons/07_nav_pick_place/transport.py yellow

# 같은 일을 CLI 로
./scripts/mobile_openarm pick red pick_table place_table
```

## 화면에서 볼 것

- 단계마다 시작 시각, map 위치(TF map → base_footprint), 그 단계에서 달린 거리. 끝에 단계별 시간 표.
- 검증 2026-10-10 (이 PC, 벽시계): 빨강 256 s · 14.7 m · 슬롯 오차 1.1 cm (오른팔), 파랑 298 s · 4.6 cm (왼팔), 노랑 258 s · 1.8 cm (왼팔, 축에서 10 cm 옆으로 도킹).
- Nav2 는 사전 도킹 지점(`locations.yaml` base_goal)까지만 간다. 도착 오차(AMCL 기준 8 cm 허용, 실제 7 ~ 13 cm)는 마커 도킹이 지운다.

## 핵심 코드

| 무엇 | 어디 |
|---|---|
| 한 goal 로 운반 · 단계별 위치 출력 | `lessons/07_nav_pick_place/transport.py` |
| 상태 기계 (pick 절반 + place 절반) | `src/warehouse_skills/warehouse_skills/pick_place_server.py` `execute()`, `do_pick()`, `do_place()` |
| Nav2 사전 도킹 + 마커 정렬 + side-step | `pick_place_server.py` `navigate_and_dock()`, `nav_client.py` `go_to()`, `wait_markers()`, `sidestep()` |
| 사전 도킹 지점 | `src/warehouse_lecture/worlds/locations.yaml` (`pick_table`, `place_table` 의 `base_goal`) |
| Nav2 허용 오차 · 속도 | `src/mobile_openarm_navigation/config/nav2.yaml` |

## 해 볼 것

- `--to pick_table` 로 집은 작업대에 되돌려 놓기 (06 모듈과 비교: 주행이 빠지면 몇 초?)
- `locations.yaml` 의 `place_table` `base_goal` x 를 1.0 으로 바꿔 도킹 거리가 늘어날 때 시간 비교 (끝나면 1.2 로 되돌리기)
- 운반 중 `./scripts/mobile_openarm exec ros2 topic echo /pick_place/_action/feedback` 으로 feedback 을 직접 보기

## 문제 해결

- "Nav2 rejected the goal": 스택이 막 떴다. 20 초 뒤 다시.
- 상자를 옮긴 뒤 세계는 초기화되지 않는다. 같은 색을 다시 옮기려면 시뮬레이터를 다시 띄운다.
- 도킹이 오래 멈추면: 카메라 영상이 늦게 온다 (`/vision/stats`). 마커는 '찍힌 시각' 이 멈춘 뒤인 것만 쓰므로 기다리면 진행한다. `dock.timeout_s` (180 s) 를 넘으면 실패.
