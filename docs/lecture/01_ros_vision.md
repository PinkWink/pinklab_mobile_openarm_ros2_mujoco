# M1. ROS 2 로봇 통신 인프라 및 Python 비전 처리

작성·검증: 2026-09-22, Ubuntu 24.04 / ROS 2 Jazzy native / Python 3.12 / MuJoCo 3.6.0. 강사 PC(16코어)와 `taskset -c 0-3` 4코어 제한에서 모두 확인했다. 예제는 `examples/m1_ros_vision/`에 번호 순으로 있고 각 파일 첫머리에 실행 방법과 배우는 점을 적었다. 설치는 `docs/lecture/00_setup.md`, 명령 전체는 `docs/USAGE.md`.

## 1. 목표와 요약

로봇의 노드·토픽·서비스·액션·TF 구조를 읽고, 시뮬레이터 프로세스 안에서 카메라 영상을 OpenCV로 처리해 **결과만 ROS로 내보내는** 구조를 익힌다. 이 강좌는 영상 토픽을 만들지 않는다(LECTURE_PLAN.md 설계 원칙 1). 영상은 `camera_handler`라는 Python 콜백으로만 받고, 검출·3D 위치·통계만 메시지로 나간다.

| 예제 | 내용 | 결과 |
|---|---|---|
| 01_inspect_graph.sh | 노드 24, 토픽 82, 액션 17, TF 프레임 48 출력. 영상 토픽 0개 확인 | `artifacts/m1/01_inspect_graph.txt` |
| 02_scan_odom_subscriber.py | /scan 최근접 장애물 방위, /odom, tf map 좌표, 사람 접근 경고 발행 | 방문객 1.29 m 접근 시 `/warehouse/alerts` 발행 |
| 03_frames_handler.py | 첫 카메라 핸들러: K, T_world_optical, 깊이, OpenCV 창, 처리율 | 핸들러 4.3 ms/호출, 실시간 비율 1.00 |
| 04_color_detect_parcels.py | HSV 분할 → Detection2DArray(`/vision/parcels_2d`) | 상자 3개 검출 0.5 ms. 안전모·선반 상자 오검출 2개(의도된 한계) |
| 05_pixel_to_map.py | 깊이 역투영 → tf2 map → MarkerArray, 정답 비교 | 비전 오차 0.4~1.0 cm, tf 경로(AMCL 포함) 1.8~3.1 cm |
| 06_worker_thread.py | 물리 스레드 차단 vs 워커 스레드 + 적응형 FPS | 차단: 실시간 비율 0.54. 워커: 1.00, 700 ms 추론도 시뮬레이션 유지 |
| 07_action_clients.py | Nav2·PickPlace 액션 호출·피드백·취소 | tour(이동 20 s → 운반 148 s → 복귀 30 s) 성공, 취소 CANCELED 확인 |

검증 기준(계획서): parcel map 좌표 오차 < 5 cm → 비전 1.0 cm 이하 충족. 4코어 실시간 비율 ≥ 0.9 → 03~05 동시 실행 중 0.99~1.01. PickPlace 1회 성공 → 07 tour 성공.

## 2. 준비

```bash
cd ~/mujoco_ros2/mobile_openarm_ws
source /opt/ros/jazzy/setup.bash && source scripts/env.sh
./scripts/mobile_openarm start viewer:=false          # 터미널 1 (기본 파이프라인: ArUco + 정답 검출기)
./scripts/mobile_openarm exec bash examples/m1_ros_vision/01_inspect_graph.sh   # 터미널 2
```

핸들러 예제(03~06)는 시뮬레이터 인자로 파일을 넘긴다. `camera_handler:=<파일.py>:<클래스>` 형식이며 여러 개는 `LECTURE_HANDLERS`로 묶는다.

```bash
./scripts/mobile_openarm start viewer:=false camera_handler:=examples/m1_ros_vision/03_frames_handler.py:FramesHandler camera_depth:=true
LECTURE_HANDLERS="examples/m1_ros_vision/04_color_detect_parcels.py:ColorParcelDetector,examples/m1_ros_vision/05_pixel_to_map.py:PixelToMap" \
  ./scripts/mobile_openarm start viewer:=false camera_depth:=true
```

## 3. 예제별 관찰 포인트

### 01. 그래프 읽기
- 노드는 세 무리다: 시뮬레이터 브리지(`/mobile_openarm_mujoco`: 센서, 컨트롤러 액션 서버 4개, 카메라 핸들러), Nav2 10개, MoveIt 5개. 강좌용은 `/pick_place_server`, `/warehouse_planning_scene`.
- `sensor_msgs/Image`, `CameraInfo` 토픽은 없다. 카메라 프레임(TF)은 4대분이 있다. 결과 토픽은 `/vision/detections_2d`, `/vision/detections`(map 좌표), `/vision/markers`(ArUco), `/vision/stats`.
- TF 트리: `map → odom`은 AMCL(약 10 Hz), `odom → base_footprint`는 바퀴 오도메트리(50 Hz), 그 아래 정적 프레임은 URDF, 팔 관절은 `/joint_states`(약 17 Hz 갱신). 카메라의 `*_optical_frame`이 05번의 출발점이다.
- `ros2 topic list`에 토픽이 2개만 보이면 `ros2` 데몬이 다른 RMW로 떠 있는 것이다. `ros2 daemon stop` 후 다시 실행한다.

### 02. /scan, /odom 구독과 경고
- 센서는 `qos_profile_sensor_data`(best effort)로 구독한다. 콜백은 저장만 하고 계산·출력은 1 Hz 타이머에서 한다.
- **laser_link는 base_link 기준 yaw 180°로 장착**되어 있다(실제 Pinky와 동일). 스캔 각도를 그대로 쓰면 앞뒤가 뒤집힌다. tf로 `base_link → laser_link` 회전을 한 번 조회해 더한다. 센서 프레임과 로봇 프레임을 구분하는 습관을 여기서 만든다.
- map 좌표는 tf `map → base_footprint`로 얻는다. `/odom`은 odom 프레임이라 드리프트가 있다.
- 사람 위치는 `/warehouse/actor_states`(시뮬레이터 정답)에서 읽는다. 뒤 모듈에서 카메라 검출로 대체한다. 시험은 `set_actor` 서비스로 방문객을 로봇 쪽으로 걷게 해서 했다.

### 03. 첫 카메라 핸들러
- 핸들러는 시뮬레이터 **메인 스레드**에서 캡처 주기(기본 2 FPS, 시뮬레이션 시간)마다 불린다. 여기서 오래 걸리면 시뮬레이션이 느려진다(06번).
- `frame.K`(320x240에서 fx≈188/208), `frame.T_world_optical`(optical → world 4x4), `frame.depth_m`(`camera_depth:=true`일 때). 카메라 위치와 광축을 world 좌표로 찍어 확인한다.
- OpenCV 창은 `cv2.imshow` + `cv2.waitKey(1)`. DISPLAY가 없거나 `M1_WINDOW=0`이면 PNG만 저장한다.

![03 base/head camera with depth at the pick table](03_frames_predock.png)

### 04. HSV 색 검출
- 320x240에서 1 m 앞 4.5 cm 상자는 약 10x15 픽셀이다. `cv2.inRange` → `MORPH_OPEN` → `connectedComponentsWithStats` → 면적 필터.
- HSV 범위는 실제 프레임에서 측정했다(빨강 H 4~10, 파랑 90~102, 노랑 20~30). 노란 안전모(H 25~30)와 선반 갈색 상자(H 13~20)가 노랑 범위에 걸려 **오검출 2개**가 난다. 이것이 색 검출의 한계이며, 05번(높이)과 M2(YOLO)가 푸는 문제다.
- `Detection2D`: `bbox.center.position`, `bbox.size_x/y`는 픽셀, `results[0].hypothesis.class_id/score`. `header.frame_id`는 optical frame, stamp는 시뮬레이션 시간.

![04 HSV detections: 3 parcels plus helmet and shelf false positives](04_color_detect.png)

### 05. 픽셀 → map 좌표
- 역투영 `p = z K⁻¹ [u v 1]ᵀ`. z는 박스 중앙 영역 깊이의 중앙값. 깊이는 **앞면까지**의 거리라 중심을 원하면 광선 방향으로 두께 절반(2.25 cm)을 더한다. 이 보정 전에는 x가 일관되게 4 cm 가까웠다.
- map으로 가는 길 둘: (a) `T_world_optical`(시뮬레이터 정답 자세) (b) tf2 `optical → map`(실제 로봇의 길, AMCL 오차 포함). 로그에 두 오차를 나눠 찍는다. 비전 오차 0.4~1.0 cm, tf 경로 1.8~3.1 cm(실행마다 AMCL 오차 2~5 cm).
- **tf 조회 시각은 프레임의 stamp**여야 하고, 그 시각의 TF는 같은 틱 안에서는 아직 없다(다른 노드의 `/tf`는 다음 틱에 도착). 검출과 stamp를 보관해 다음 호출(0.5 s 뒤)에 변환한다. 처음엔 "extrapolation into the future"로 전부 실패했다.
- 높이 필터(0.70~0.95 m)로 안전모(z 1.56 m)와 선반 상자(4.7 m 거리)를 걸러 상자 3개만 Marker로 낸다.
- AMCL 오차는 비전에서 잡지 않는다. 작업대 근처 정밀 진입은 ArUco 마커 도킹(운반 스킬)이 맡는다.

### 06. 워커 스레드와 적응형 FPS
- (A) 물리 스레드에서 300 ms 처리: 캡처 2 FPS, **실시간 비율 0.54**. (B) `WorkerHandler`(prepare → 워커 process → publish) + 700 ms 처리: **실시간 비율 1.00**, 추론 701 ms, 지연 1.5 s, 버린 프레임 누적(큐 길이 1).
- `/vision/stats`: capture_fps, realtime_ratio, inference_ms, queue_depth, dropped_frames. 적응형 스로틀은 실시간 비율 < 0.8일 때 FPS를 25 % 낮춘다. 워커가 GIL을 놓는 OpenCV/ONNX 호출이면 16코어에서는 발동하지 않는다. 4코어 저사양에서 M2 YOLO로 다시 본다.
- 퍼블리셔는 물리 스레드(`publish`)에서만 쓴다. rclpy 퍼블리셔는 스레드 안전하지 않다.

### 07. 액션 클라이언트
- `wait_for_server → send_goal_async → accepted → get_result_async`, 중간 `feedback_callback`. `--cancel-after 4`로 Nav2 취소 → 결과 CANCELED.
- 장소 이름 → 좌표는 `warehouse_lecture/worlds/locations.yaml`(M4에서 LLM이 이 이름을 쓴다). `tour`는 pick_table 이동 → PickPlace red → 원점 복귀.

## 4. 4코어 제한 검증

`taskset -c 0-3`로 시뮬레이터(Nav2, MoveIt 포함)를 띄우고 03+04+05 핸들러를 동시에 올린 뒤 pick_table로 이동, 검출·변환 수행.

| 항목 | 값 |
|---|---|
| 실시간 비율(03 핸들러 측정, 20 샘플) | 0.99~1.01 |
| 핸들러 처리 시간 | 03: 4.3 ms, 04: 0.5 ms |
| 상자 map 오차(비전 / tf) | 0.4~1.0 cm / 1.8~3.1 cm |
| 운반 1회(기본 파이프라인, 4코어, Phase 0 재검증) | 성공, realtime_ratio ≥ 0.994 |

## 5. 이번 모듈에서 고친 기반 코드

- `mobile_openarm_mujoco/handler.py` `load_handler`: `파일.py:속성` 스펙 지원(숫자로 시작하는 예제 파일을 import 문 없이 로드). 테스트 추가.
- `mobile_openarm_moveit_config/config/joint_limits.yaml`: 팔 14관절에 URDF보다 0.01 rad 넓은 위치 한계. 컨트롤러가 한계에 붙은 목표를 0.0003 rad 넘겨 멈추면 MoveIt 2.12의 `CheckStartStateBounds`가 START_STATE_INVALID(-26)를 냈다. Phase 0의 `fix_start_state: true`는 2.12에서 continuous/planar/floating 관절 정규화만 하므로 효과가 없었다(소스 확인).
- `warehouse_skills`: 도킹 후 베이스 기준 상자 위치로 팔을 다시 고른다. `dock.max_lateral_error` 0.10 → 0.05.
- `scripts/dev/*`: `env.sh`를 source해 wrapper와 같은 RMW(CycloneDDS)를 쓰고 `ros2 daemon stop`을 자동 실행.

## 6. 함정 정리

- laser_link yaw 180°. 스캔 방위를 로봇 기준으로 바꿀 것.
- 프레임 stamp의 TF는 다음 틱에 도착한다. 보관 후 변환.
- 깊이는 앞면. 중심은 두께 절반을 더한다.
- 색 검출은 안전모·선반과 섞인다. 높이(05) 또는 학습 검출기(M2)로 푼다.
- 핸들러 예외는 시뮬레이터를 죽인다. 창 열기 등 실패할 수 있는 호출은 try/except.
- 시뮬레이터와 CLI의 RMW가 다르면 커스텀 메시지가 안 보인다. wrapper `exec` 또는 `env.sh`만 쓰고, 이상하면 `ros2 daemon stop`.

## 7. 다음 (M2)

색 검출을 YOLO로 바꾼다. 정답 검출기(세그멘테이션)로 자동 라벨 데이터셋을 만들고, 강사 GPU/Colab에서 학습한 가중치를 배포해 CPU(ONNX/OpenVINO, 320 입력)에서 06번의 `WorkerHandler`로 돌린다. 4코어에서 적응형 FPS가 실제로 작동하는지 그때 본다.
