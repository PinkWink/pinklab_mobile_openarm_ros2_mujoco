# 06. Pick & Place (Day 2 ⑨)

## 목표

주행 없이 작업대 앞에서 상자를 집고(pick) 같은 작업대의 빈 자리에 다시 놓는다(place). PickPlace 스킬의 단계(도킹 → 위치 확인 → pre-grasp → grasp → lift → carry / dock → place)와 각 단계가 쓰는 ROS 인터페이스를 본다. 주행을 포함한 통합은 07 모듈.

## 실행

```bash
# 로봇을 픽업 작업대 앞(사전 도킹 지점)에 바로 놓고 시작한다. spawn:= 은 MuJoCo 위치와 AMCL 초기 위치를 함께 맞춘다.
LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start spawn:=pick_table camera_depth:=true locate:=vision viewer:=true rviz:=false

# 빨간 상자를 집고 같은 작업대에 다시 놓기 (검증 2026-09-27: 집기 39 s, 놓기 42 s, 슬롯 오차 3.7 cm)
./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red

# 반쪽씩: 집은 채 멈춰서 뷰어로 살펴보고, 그 다음 놓기
./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red --only pick
./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py red --only place

# 같은 일을 CLI 로
./scripts/mobile_openarm pick red --phase pick
./scripts/mobile_openarm pick red pick_table --phase place
```

## 화면에서 볼 것

- 단계별 시각과 피드백: `navigate_pick`(이미 도착 → 1 s) → `dock`(마커 쌍 시각 서보 + 짧은 blind 구간, 잔차 1~2 cm) → `locate`(카메라 검출, 상자 위치 dx≈0.54 dy≈-0.25) → `pre_grasp` → `grasp`(손가락 24.5 mm 에서 정지 = 잡음) → `lift` → `carry`(hands_up).
- pick 결과 메시지: 상자가 상판보다 약 9 cm 위에 있다. place 뒤: 상자가 슬롯에서 몇 cm 떨어졌는지.
- MuJoCo 뷰어에서 상자가 손에 붙어 올라가고, RViz(켰다면) planning scene 에 상자가 손에 attach 된다.

## 핵심 코드

| 단계 | 어디 (`src/warehouse_skills/warehouse_skills/`) |
|---|---|
| 액션 정의 (goal.phase = all / pick / place) | `warehouse_interfaces/action/PickPlace.action` |
| 상태 기계: pick 절반 / place 절반, 든 물체 기억(`held`) | `pick_place_server.py` `do_pick()`, `do_place()`, `execute()` |
| 도킹(마커 쌍 → 축 위치, 시각 서보, blind 구간) | `nav_client.py` `geometry()`, `dock()` |
| 물체 위치(정답 / 카메라) | `locate.py` `TruthLocator`, `VisionLocator` (같은 TF 로 되돌려 AMCL 오차 상쇄) |
| 파지: pre-grasp IK → 직선 접근 → 그리퍼 → attach → 들기 | `pick_place_server.py` `grasp()` 약 30줄 |
| 놓기: 빈 슬롯 → 내리기 → 열기 → detach | `free_slot_offset()`, `place()` |
| 파라미터(높이 여유, 손가락 폐쇄 범위, 슬롯 간격, 도킹 거리) | `config/skills.yaml` |
| 실패 복구(붙은 상자 풀기) | `recover()` |

## 해 볼 것

- `skills.yaml` `grasp.close_min/close_max` 를 좁혀 "grasp missed" 를 만들어 본다.
- `place.slot_offsets_y` 를 바꿔 다른 자리에 놓는다.
- `--to place_table` 로 다른 작업대에 놓아 07 모듈(주행 포함)로 넘어간다 (검증: 파란 상자 집기 70 s + 적재대 놓기 103 s, 슬롯 오차 1.8 cm).

## 문제 해결

- "nothing is held: run the pick phase first": place 만 보냈다. pick 먼저.
- 상자를 옮긴 뒤 세계는 초기화되지 않는다. 반복하려면 시뮬레이터를 다시 띄운다.
- 액션이 거부되면 이전 실행이 남아 있다: `./scripts/cleanup_ros.sh` 후 재시작.
