# Mobile OpenArm 검증 기록

검증일: 2026-09-19. macOS arm64, RoboStack ROS 2 Jazzy, Python 3.12, MuJoCo 3.6.0, MoveIt 2.12.4.

## 빌드와 모델

- ament_python 패키지 7개 colcon 빌드 성공.
- 단일 루트 `base_footprint`, 링크 46개, URDF joint 45개 (카메라 링크·광학 프레임·상단 지지대 포함). 바퀴 2 + 팔 14 + finger 4의 관절 상태 발행.
- MuJoCo: nq=48, nv=44, actuator=18 (바퀴 2 + 팔 14 + 그리퍼 2). 로봇과 상자 3개는 free body.
- 원본 자산 SHA256 일치, 메시 URI 해석, SRDF·controller joint 이름 정합성 확인.
- 타이어를 같은 외형 치수의 ellipsoid로 근사한 뒤 회전과 엔코더 오도메트리 일치 시험 통과. 상세 조정은 MOBILE_OPENARM.md 참조.

## 자동 테스트

- `tests/test_mobile_openarm.py`: **11 passed**. 관성 유효성·구조·자산·컨트롤러 계약·창고 지도·정지 안정성·직진·회전·그리퍼 mimic·lidar 방향·잘못된 궤적 거절.
- 기존 `tests/test_physics.py`, `tests/test_backends.py`: **10 passed**. 기존 Pinky 구성 회귀 없음.
- `ruff check --select F`: 통과. shell 구문 검사 통과.
- trimesh/NumPy 내부 shape 변경 deprecation warning은 남아 있으며 테스트 실패는 아님.

## 실제 ROS 통합 실행

`./scripts/mobile_openarm start viewer:=false rviz:=false`에서 `scripts/check_mobile_openarm.py --nav` 실행:

| 검사 | 결과 |
|---|---|
| `/joint_states` | 20관절 |
| `/scan` | 360 rays |
| odom → lidar / 좌우 TCP TF | 3개 연결 확인 |
| MoveIt collision world | 114개 물체 |
| 양쪽 GripperCommand | .005 → .035 → .025m 실제 관절 도달 |
| 잘못된 이름 / 동시 중복 trajectory | 거절 |
| trajectory 취소 | CANCELED, 측정 자세 유지 |
| 팔 동작 중 cmd_vel | 베이스 이동 < 2.5cm |
| cmd_vel watchdog | 약 0.485m 이동 후 정지 |
| Nav2 `(1.0, 0.6, 0)` 목표 | SUCCEEDED (status=4) |
| 목표점 실제 위치 오차 | 약 **0.0853m** |

별도 MoveIt `/move_action` 시험:

- 왼팔 `ready`: OMPL 계획 → 실제 MuJoCo 실행 성공.
- 양팔 `ready`, `transport`: 두 FollowJointTrajectory 서버 동시 실행 성공.
- Nav2 이동 후 최종 모델에서 양팔 `ready` 및 `transport` 재검증: status=4, MoveIt error_code=1 (SUCCESS).

실행 결과: `artifacts/mobile_openarm_integration.json`.
빌드·테스트·MoveIt·Nav2 실행 로그: `artifacts/mobile_openarm_*.log`.
최종 장면: `artifacts/mobile-openarm-robot.png`, `artifacts/mobile-openarm-warehouse.png`.

## 검증 범위

Ubuntu 24.04 native Jazzy는 설치/패키지 구성만 제공했으며, 이 Mac에서 실제 Ubuntu 실행을 검증했다고 주장하지 않습니다. 실물 CAN 제어, 카메라 인식, 완전한 grasp/lift/place 시퀀스는 미구현입니다. 정적 창고 지도·AMCL 경로의 도착 시험을 수행했습니다. SLAM launch는 제공하며 별도 기동 검증 결과를 아래에 기록합니다.

## GUI 및 SLAM

- macOS `mjpython` MuJoCo viewer 기동 및 MoveIt RViz의 interactive marker 연결 확인.
- RViz에서 planning group `left_arm`의 command-ready 상태 확인.
- RViz가 원본 finger 관성 오류를 검출해 통합 description에 물리적으로 유효한 관성 보정을 공유하도록 수정했고, 모든 통합 링크의 주관성 유효성 시험을 추가했습니다. 원본 자산은 유지합니다.
- 비전 기능은 범위 밖이므로 RViz의 optional `/recognize_objects` 서버 부재 로그가 남습니다. MoveIt 계획/실행에는 영향을 주지 않습니다.

- 최종 SLAM 기동 시험: `map` 좌표계, 300 × 220 cells, 해상도 0.05000000074505806m, 관측 4708 cells, 점유 260 cells. 별도 이동 시험에서도 지도 증가를 확인했습니다.
- SLAM에서 회전 키프레임을 허용하고, 잡음 없는 가상 라이다에 맞춰 `min_pass_through=1`로 설정했습니다.

## Python 직접 카메라 추가 검증

- 베이스·상단·왼손·오른손 카메라 4대. URDF 광학 프레임과 MuJoCo 카메라 외부 파라미터 일치, 손목 이동 추종 확인.
- 카메라 축 검증에서 발견한 URDF RPY 변환을 수정: MuJoCo compiler `eulerseq="XYZ"`로 고정축 roll/pitch/yaw 적용. 전방 카메라가 로봇 +X를 보는지 별도 검사.
- 7개 패키지 재빌드 성공. 모델·주행·카메라 테스트 **14 passed**, ruff F 검사 통과.
- 실제 OpenGL에서 4 × 640 × 480 RGB 및 float32 깊이 렌더링 성공. 동일 시뮬레이션 시각, 읽기 전후 qpos 불변, 이전 RGB 버퍼 보존 확인.
- 알려진 거리의 평면에서 광학 깊이 1m를 오차 5mm 이내로 확인. macOS의 `ARB_clip_control` 부재 경고는 남으므로 이 결과를 전 거리의 정밀도 보증으로 해석하지 않음.
- MuJoCo viewer + MoveIt + Python 콜백(2 FPS, 깊이 포함) 동시 실행 성공. 양팔 `ready` → `transport` 계획·실행 성공.
- 양팔 `ready` 후 왼손·오른손 카메라 이동 0.1486m / 0.1500m. 베이스·상단 카메라 이동 약 0.00003m. 네 프레임의 `sim_time` 일치 및 실행 중 `/clock`과 정합 확인.
- 실행 중 ROS 그래프에 `sensor_msgs/msg/Image`, `CompressedImage`, `CameraInfo` 토픽 **0개**.
- 기본 headless 모드의 전체 회귀 검사 성공: 그리퍼·액션 취소·주행 인터록·watchdog·Nav2. 목표 `(1.0, 0.6, 0)` 도달 status=4, 실제 위치 오차 **0.0661m**.
- 카메라 4대 RGB-D 직접 수신(2 FPS)을 켠 별도 Nav2 목표 주행도 성공: status=4, 실제 위치 오차 **0.0542m**. 일부 controller 주기 지연 경고는 남음.

결과: `artifacts/mobile_cameras/validation.json`, `four_cameras.png`, `artifacts/mobile_openarm_camera_live.json`, `artifacts/mobile_openarm_camera_regression.json`, `artifacts/mobile_openarm_camera_nav.json`.

렌더링·사용자 콜백은 물리 루프에서 동기 실행하므로 실제 시간 처리율은 FPS와 영상 처리 비용에 따라 달라집니다. 카메라를 켠 상태에서 기존 고정 wall-clock 간격의 전체 회귀 스크립트를 실행한 시도는 취소 후 팔 재요청 시 주행 인터록으로 거절되었습니다. 기본 모드의 전체 회귀와 카메라의 실제 동시 MoveIt 검증은 위와 같이 별도로 통과했습니다. 실시간 처리율을 보장하지 않으며 실제 시간 간격만으로 정지·동작 완료를 추정하지 말고 상태와 액션 결과를 확인해야 합니다.
