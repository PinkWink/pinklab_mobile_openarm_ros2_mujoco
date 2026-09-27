# Phase 0 결과: 강좌용 기반 코드 확장

작성·검증: 2026-09-21, Ubuntu 24.04 / ROS 2 Jazzy native / Python 3.12 / MuJoCo 3.6.0. 원본 ZIP(mobile_openarm_jazzy_ws, Mac 검증본)을 Ubuntu에서 빌드·검증한 뒤 강좌 6개 모듈이 공통으로 쓰는 기반을 추가했다. 자세한 사용법은 저장소의 docs/USAGE.md, 설치는 docs/lecture/00_setup.md, 계획은 LECTURE_PLAN.md에 있다.

## 1. 요약

| 항목 | 결과 |
|---|---|
| Ubuntu 빌드·원본 통합 검사 | 10개 패키지 빌드, Nav2 목표 SUCCEEDED(오차 0.065 m), 카메라 라이브 검사 통과 |
| 사람·소품 배우 | 사람 4명(안전모 착용 2 / 미착용 2), 지게차, 팔레트, 콘 2, 소화기. 라이다·카메라에 보이고 정적 지도에는 없음 |
| 카메라 핸들러 확장 | setup/close 훅, ROS 발행·TF 조회, 세그멘테이션 렌더, 카메라 선택·해상도, 저사양 lite 프로파일 |
| ArUco 도킹 | Nav2 사전 도킹 → 마커 2개 시각 서보 → 오도메트리 직진. 잔차 1~5 cm |
| 운반 스킬 | 빨간 상자(오른팔), 파란 상자(왼팔) 픽업→적재 작업대 성공, 슬롯 오차 1~4 cm, 회당 약 2.5분 |
| 인터페이스 | warehouse_interfaces 17종(msg 12, srv 3, action 2) |
| 강좌 공통 코드 | OpenAI 클라이언트, STT/TTS, 장소 사전, 정답 검출기, ArUco 핸들러, 워커 스레드 핸들러 베이스 |
| 테스트 | 33개 통과(시뮬레이터 불필요, 약 1.2분) |

머리 카메라(head_camera)에서 본 창고: 안전모 없는 방문자, 콘, 지게차, 랙. 이 영상은 ROS 토픽이 아니라 시뮬레이터 프로세스 안 Python 배열이다.

![head camera view with actors](../../artifacts/mobile_generated/actors_head.png)

## 2. 설계 결정

- 카메라 영상은 ROS 토픽으로 내보내지 않는다. 검출·마커·속성 판정은 시뮬레이터 프로세스 안 Python 핸들러에서 끝내고 결과 메시지만 발행한다.
- LLM·음성은 OpenAI API만 사용한다. 수강생 PC에는 GPU가 없다고 가정하고 카메라 기본값을 2대·320×240·2 FPS로 낮췄다.
- 작업 장소 진입은 Nav2와 분리했다. Nav2는 작업대 앞 약 1 m 고정 지점까지만 가고, 그 뒤는 작업대 다리에 걸린 ArUco 마커를 베이스 카메라로 보며 도킹한다. 마커 하나의 법선은 320×240에서 ±20° 흔들려 작업대마다 마커 2개를 두고 두 중심을 잇는 선으로 방향을 구한다.
- 베이스는 항상 작업대 축 중앙에 도킹하고 물체가 있는 쪽 팔을 선택한다. 차동구동의 횡이동을 없앤다.
- 파지는 전방 수평 파지만 쓴다. 상판 0.78 m, 어깨 0.917 m에서는 위에서 내려잡는 자세의 IK 해가 없다.
- 라이다 V자 홈 도킹은 대안으로 보류했다. 마커 도킹이 실환경에서 불안정하면 전환한다.
- 팔 기둥을 바퀴 축(base_link x=0, 회전 중심)으로 옮겼다. 이전 -0.08 m.

## 3. 원본 대비 변경

| 구분 | 내용 |
|---|---|
| worlds/actors.yaml (신규) | 배우 정의. 속성(helmet, vest, shirt, height)이 외형에 드러남. 경로 순회·정지 |
| worlds/warehouse.yaml | parcel을 작업대 앞 가장자리(x 2.18)로 이동, 사전 도킹 station, ArUco markers 4개 |
| model.py / actors.py / markers.py | mocap 배우, 텍스처 평면 마커(라이다·지도 제외), noslip_iterations 옵션 |
| bridge.py / handler.py | 핸들러 setup/close, 배우 애니메이션, /warehouse/actor_states, /warehouse/set_actor, 틱당 ROS 콜백 8개 |
| cameras.py | segmentation 렌더, 카메라 부분 선택, 런타임 FPS 조절 |
| description | drive_poses.yaml(transport/ready/hands_up), display.launch.py, mount_x 0.0 |
| navigation | inflation_radius 0.9 → 0.55 |
| moveit_config | fix_start_state true, warehouse_scene의 부착 물체 제외 |
| trajectory.py | 관절 한계 허용 오차 1e-3 |
| mujoco.yaml | noslip_iterations 5, ros_callbacks_per_tick 8 |
| warehouse_interfaces (신규) | ActorState, Detection3D, Encounter, RobotCommand, Utterance, VisionStats, ArucoMarker / SetActor, QueryEncounters, AskRobot / PickPlace, ExecuteCommand |
| warehouse_lecture (신규) | ros/handler_base, ros/geometry, vision/labels·truth_detector·aruco·pipeline, llm/client, speech/stt·tts, memory/locations, config/llm.yaml, worlds/locations.yaml |
| warehouse_skills (신규) | /pick_place 액션 서버, MoveIt·Nav2·도킹 클라이언트, config/skills.yaml |
| scripts | install_lecture.sh, env.sh, cleanup_ros.sh, check_actors_live.py, wrapper에 pick·display |

## 4. 검증 기록

| 검사 | 결과 |
|---|---|
| tests/ 33개 | 통과 |
| scripts/check_mobile_openarm.py --nav | Nav2 (1.0, 0.6) SUCCEEDED, 오차 0.065 m, 그리퍼·궤적 검증 통과 |
| scripts/check_mobile_cameras_live.py | 양팔 ready 후 손목 카메라 0.154 m 이동, 4대 타임스탬프 일치, 영상 토픽 0 |
| scripts/check_actors_live.py --nav | 사람 map 위치 오차 0.20 m, 안전모 속성 변경 반영, 실시간 비율 1.0, 사람 우회 Nav2 도착 오차 0.02 m |
| pick red (오른팔) | 성공, 슬롯 오차 4 cm |
| pick blue (왼팔) | 성공, 슬롯 오차 1.2 cm |

## 5. 해결한 문제

- bridge가 틱당 ROS 콜백을 하나만 처리해 핸들러의 TF 조회가 0.8초 뒤처짐 → 틱당 8개 처리.
- 검출의 map 변환에 현재 시각을 써서 미래 TF 조회 실패 → 프레임의 sim_time 사용.
- 마커 하나의 법선 잡음 → 마커 쌍.
- 2 FPS 카메라의 촬영-도착 지연(최대 0.5초)으로 맹목 구간 5 cm 과주행 → 오도메트리 이력에서 촬영 시각 위치를 찾아 보정.
- 파지한 상자가 주행 중 손가락 사이에서 서서히 빠짐(MuJoCo creep) → noslip_iterations 5.
- transport/ready 운반 자세에서 상자가 베이스 상판·작업대 모서리에 닿음 → hands_up 운반, drive_poses.yaml.
- Cartesian 경로의 관절값이 한계를 1e-7 넘어 궤적 거부 → 허용 오차 1e-3, MoveIt fix_start_state.
- 액션 결과에 numpy bool이 들어가 서버 SIGABRT → Python 타입으로 캐스팅.
- 이전 세션의 launch 자식 프로세스가 남아 노드 중복 → scripts/cleanup_ros.sh.

## 6. 남은 일과 다음 단계

- (2026-09-22 완료) 팔 장착점 x=0 + dock.target_dx 0.56으로 red·blue 운반 재검증. 도킹 후 베이스 기준 위치로 팔을 다시 고르도록 수정, max_lateral_error 0.05.
- (2026-09-22 완료) 4코어 제한(taskset -c 0-3)에서 운반 중 realtime_ratio ≥ 0.99.
- Colab 학습 노트북과 YOLO 가중치 배포는 M2에서.
- 다음은 M1(ROS 2 통신 인프라 및 Python 비전 처리) 예제 7개 작성이다. 순서와 검증 기준은 LECTURE_PLAN.md 2절.
