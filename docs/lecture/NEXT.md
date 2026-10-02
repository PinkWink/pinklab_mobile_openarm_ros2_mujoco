# 다음 세션 재개 안내

마지막 갱신: 2026-09-29 밤 (hand-off, 내일 2026-09-30 이어서). PC를 다시 켠 뒤 이 문서만 보고 이어갈 수 있도록 쓴다.

## 0-0000000. 2026-10-02: 순찰 막힘 해결

- RotationShim 설정 시험: 제자리 회전은 해결됐지만 rack_a → rack_b 에서 여전히 Failed to make progress 4번 + spin 복구 (순찰 302 s).
- 진짜 원인: `nav2.yaml` 의 `BaseObstacle.scale: 0.05` 는 무시되고 있었다 (쓰는 critic 은 ObstacleFootprint). 실제 값은 기본 1.0 → 랙 기둥 사이(1.8 m 통로, 기둥 x=-5.0 · -3.1, y=-1.25) 에서 장애물 비용이 진행 점수를 이겨 v=0 으로 멈춤. `ObstacleFootprint.scale: 0.05` 로 바꿈.
- patrol.py 버그 2개 수정: ① near 판정에 Nav2 feedback `distance_remaining` 대신 AMCL ↔ 목표 거리 사용 (feedback 이 0 근처로 나와 4.4 m 떨어진 곳에서 '도착 처리'됨) ② 첫 구간에서 `self.truth` 가 None 이면 정지 기준이 안 잡혀 8 s 뒤 움직이는 중에도 cancel → 첫 정지가 늘 "near" 였던 이유.
- 결과: center_aisle → pick_table → rack_a → rack_b → place_table → center_aisle 6구간 모두 SUCCEEDED, 복구 0, near 0, 195 s.
- 회귀 확인 (모두 통과):
  - crossing: SUCCEEDED 34 s, 최소 1.05 m (페이지 1.16 m). 흐름은 같음 (감지 → 우회 → t≈9 s 잠깐 정지 → 재개), 우회 폭 y -0.14 (전 -0.27), 정지 0.7 s (전 1.1 s). 데이터 scratchpad 의 new_crossing.pkl (보관 안 함).
  - headon: SUCCEEDED 33 s, 최소 0.24 m (페이지 0.30 m). 늦게 반응해 겹치는 한계 그대로.
  - ⑥ `goal 1.2 -3.6 0` SUCCEEDED. Day 2: 원점 → `pick red --phase pick` 82 s → `pick red place_table --phase place` 90 s, 슬롯 오차 3.1 cm.
  - pytest 41 passed.
- ⑥ 페이지 코드 발췌를 RotationShim 으로 고쳐 3701866498 v2 로 재게시 (게시본과 로컬 md 대조: 차이는 이 발췌뿐). 충돌 회피 페이지(수치 1.16 / 0.30 m, 그림)는 사용자 결정으로 그대로 둠.
- 다음: 순찰 전체 캡처 → 개념 그림 → Confluence "전반부 통합 Demo" 페이지 (0-000000 의 '그 뒤' 참고).

## 0-000000. 2026-09-30 밤 hand-off: "전반부 통합 Demo" (순찰 + 웹 대시보드) 작업 중단 지점

**사용자 요청**: 전반부 통합 Demo = 내가 만든 지도로 창고 순찰 + Flask 웹 대시보드(미션 상태 · 카메라 · 위치 모니터링). Confluence 페이지(부모 3692396550)에 사용법과 구현 원리를 쓰되 **대시보드 부분은 페이지 맨 마지막에**. 아직 페이지는 안 만들었다.

**만든 것 (커밋 안 함, `lessons/04_navigation/`)**
- `patrol.py`: locations.yaml 이름 목록(기본 pick_table → rack_a → rack_b → place_table → center_aisle)을 NavigateToPose 로 차례로. `/patrol/status`(String JSON, latched) 발행, `/patrol/command`(start|cancel) 구독, `--wait` 는 시작 버튼 대기. 정지마다 truth 대비 AMCL · odom 오차 기록. **near 워치독**: 목표 0.25 m 안에서 8 s 동안 안 움직이면 cancel 후 status "near" 로 도착 처리 (DWB 가 xy_goal_tolerance 0.08 바로 밖, 옆을 보고 멈추는 경우).
- `dashboard/frame_tap.py`: `DashboardPipeline(LecturePipeline)` = 기존 비전 파이프라인 + 카메라마다 최신 JPEG 를 `/dev/shm/mobile_openarm_dashboard/<cam>.jpg` 에 원자적 저장 (+ meta.json). launch 인자 `camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline camera_fps:=5`.
- `dashboard/server.py`: Flask(설치돼 있음) + rclpy 노드(백그라운드 스레드, SingleThreadedExecutor, SignalHandlerOptions.NO 로 Ctrl+C 깨끗이 종료). `/api/stream`(SSE 5 Hz 상태 JSON), `/api/map` · `/api/map.png`, `/camera/<name>.mjpg`(MJPEG), `/api/cameras`, `POST /api/command`. 구독: /ground_truth /amcl_pose /odom /plan /scan(TF 로 map 변환) /map /warehouse/actor_states /vision/detections /patrol/status.
- `dashboard/static/{index.html,app.js,style.css}`: 지도 캔버스(실제 · AMCL · odom 로봇, /plan, 궤적, /scan, 사람(안전모 색), 정지 번호), 미션 카드(상태 · 진행바 · 정지표 · 시작/취소 버튼), 로봇 수치, 카메라 2대 + 검출 박스 오버레이(안전모 X 빨강), 이벤트 로그. 서버 재시작 시 MJPEG 재연결 처리.
- 검증됨: 모든 API 동작, 카메라 스트림 · 검출 박스 표시, 대시보드 cancel 버튼(API) 동작, 서버 Ctrl+C 정상 종료, pick_table 1구간 도착(19.8 s, AMCL 0.042 m / odom 0.003 m), rack_a 는 near 처리로 통과.
- 실행 순서: T1 `./scripts/mobile_openarm nav moveit:=false map:=$PWD/artifacts/maps/my_warehouse.yaml camera_fps:=5 camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline` → T2 `python lessons/04_navigation/dashboard/server.py` (http://localhost:8080) → T3 `python lessons/04_navigation/patrol.py --wait` → 브라우저의 [순찰 시작].

**막힌 곳 (다음에 먼저 할 일)**
- rack_a(랙 사이 좁은 통로, x=-4.0) 에서 rack_b 로 떠날 때 로봇이 전혀 못 움직임 (Failed to make progress 반복 → ABORTED). DWB 가 제자리 회전을 0.022~0.067 rad/s 로만 내서 바퀴 정지마찰(약 0.1 rad/s 필요)을 못 넘김 + ObstacleFootprint 비용이 큰 회전을 막음. 수동 /cmd_vel 로는 잘 움직이므로 브리지 · 물리 문제는 아님.
- **미검증 수정**: `src/mobile_openarm_navigation/config/nav2.yaml` 의 FollowPath 를 `nav2_rotation_shim_controller::RotationShimController`(primary DWB, rotate_to_heading_angular_vel 0.6, angular_dist_threshold 0.6, rotate_to_goal_heading true) 로 바꿨다. **아직 한 번도 돌려보지 않음** (사용자 중단). 다음 세션: ① 이 설정으로 patrol 전체 경로 시험 ② 잘 되면 ⑥ goal · 충돌 회피 시나리오 · Day 2 pick 재확인 (전체 스택 동작이 바뀜) ③ 안 되면 `git checkout src/mobile_openarm_navigation/config/nav2.yaml` 로 되돌리고 경로를 넓은 곳(pick_table, place_table, center_aisle, east_wall 등)으로 바꾸는 쪽 검토.
- 그 뒤: 순찰 전체 캡처(대시보드 · MuJoCo · 터미널) → 개념 그림(`draw_lesson07_figures.py` 예정) → Confluence 페이지 "전반부 통합 Demo" (순찰 흐름 → 실행 → 결과 → 코드, **대시보드 사용법 · 구현 원리(SSE · MJPEG · frame_tap · ROS 스레드)는 맨 끝**).
- 캡처 요령: Chrome `--app=http://localhost:8080` 창은 xdotool 클릭 · 키(F5, Ctrl+R)가 먹지 않음 → 시작은 `curl -X POST -H "Content-Type: application/json" -d '{"cmd":"start"}' localhost:8080/api/command`, 새로고침은 창을 닫고 다시 연다. MuJoCo 창이 위에 떠 있으니 캡처 전 MuJoCo · RViz 창을 최소화. 대시보드 캡처 영역 `import -window root -crop 1690x992+70+68` (창을 70,40 에 두었을 때).
- nohup 금지: `nohup … &` 로 띄운 launch 는 SIGINT 무시 → run_in_background 로 띄우고 `pkill -INT -f "[w]arehouse.launch.py mode:=nav"` 로 끈다.

## 0-00000. 2026-09-30 저녁: "ROS2 nav2의 충돌 회피" 페이지 신규 (3701145683)

- 원고 `docs/camp/lesson06_avoidance.md` (h2 4개: 1 개념 4절 → 2 crossing 실행 11절 → 3 headon 한계 5절 → 4 코드와 설정 4절 + 해 볼 것). 그림 17장 (`draw_lesson06_figures.py`, `render_lesson06_terminals.py`, 캡처는 `artifacts/dev/avoid_frames/`).
- 도구: `docs/camp/avoid_scenario.py` (`--mode crossing|headon`, /warehouse/set_actor 로 worker_helmet_orange teleport + set_path, NavigateToPose (6.2,0,0), 최소 거리 출력). **로봇이 원점에서 동쪽을 볼 때(새로 띄운 직후) 실행**. `nav_record.py` 에 actors · local_plan · global_series 추가. 데이터 `artifacts/dev/nav_crossing.pkl`(확대 화면 회차), `nav_crossing_wide.pkl`, `nav_headon.pkl`.
- 실측: crossing 최소 1.16 m (감지 6 s → 남쪽 우회 → 9~10 s 정지 대기 → 근로자 뒤로 재개). headon 최소 0.30 m (다가오는 속도 0.7 m/s, 1.5 m 에서야 반응 → 겹침). 처음 시도(서쪽 목표)는 180° 제자리 회전에 12 s 걸려 폐기.
- **코드 수정**: `navigation.rviz` 에 Global Costmap · Local Costmap (costmap 색) · Footprint · DWB Trajectories(/marker) · Local Plan 표시 추가. 그래서 ⑥ 페이지 캡처(표시 추가 전)와 지금 화면이 다르다. slam 모드에서는 이 표시들이 '데이터 없음' 상태.
- 함정: `nohup ... &` 로 띄운 launch 는 SIGINT 를 무시해 pkill -INT 로 안 죽고, TERM 뒤에도 자식이 남음 → 결국 KILL. launch 는 run_in_background 로 띄울 것.
- `draw_lesson05_figures.py` 의 amcl_compare 입력을 `artifacts/dev/nav_frames/` 로 옮김.
- 커밋 안 함.

## 0-0000. 2026-09-30 저녁: ⑥ "ROS2 Navigation" 페이지 신규 (3701866498)

- 원고 `docs/camp/lesson05_navigation.md` (h2 4개: 1 Nav2 란 8절 → 2 실행 22절 → 3 AMCL 실험 6절 → 4 코드와 설정 8절 + 해 볼 것). 그림 30장: `draw_lesson05_figures.py`(개념 14 + 실데이터 5: global_plan · local_costmap · speed · amcl_particles · amcl_compare), `render_lesson05_terminals.py`(6장), 화면 캡처 5장.
- 도구: `docs/camp/nav_record.py` (costmap · /plan · particle_cloud · amcl_pose · truth · odom → pkl). 데이터 `artifacts/dev/nav_run.pkl`(goal 명령 + RViz 목표), `nav_amcl.pkl`(틀린 initialpose 0.6,0.4,23° → 7 s 안에 퍼짐 0.49→0.09 m, 오차 3~6 cm).
- **코드 수정**: `navigation.rviz` · `moveit.rviz` 의 `nav2_rviz_plugins/GoalTool` 은 Navigation 2 패널이 없으면 목표를 안 보냄(버튼이 먹통) → `rviz_default_plugins/SetGoal` (Topic /goal_pose, 버튼 이름 2D Goal Pose) 로 교체. bt_navigator 가 /goal_pose 를 구독해 동작 확인.
- 실측: goal 1.2 -3.6 0 → 27.4 s SUCCEEDED, 복구 동작 없음. /plan 약 1 Hz 재계산.
- 커밋 안 함.

## 0-000. 2026-09-30 오후: ⑤ SLAM 페이지 신규 + ④ 개정

- 새 페이지 3701112888 "SLAM: SLAM Toolbox로 창고 지도 만들기" (부모 3692396550) ← `docs/camp/lesson04_slam.md` (h2 4개: 1 SLAM 이란 7절 → 2 실행 20절(명령 h3 · 실행 결과 h3 분리) → 3 지도 저장 6절 → 4 코드와 설정 5절(그림 절 먼저, 코드 절 뒤) + 해 볼 것). 그림 26장: `draw_lesson04_figures.py`(개념 13장 + 실데이터 4장: map_growth · map_compare · lidar_height · pose_graph_real), `render_lesson04_terminals.py`(터미널 캡처 7장, 실측 텍스트), 화면 캡처 2장(run_result · final_screen).
- 도구: `docs/camp/slam_tour.py` (/odom 웨이포인트 순회 58 m, `--record` 로 /map npz, `--shots` 로 화면 캡처). 실측 데이터 `artifacts/dev/slam_maps/wp0~7.npz`, `slam_graph.pkl`, `artifacts/maps/my_warehouse.{pgm,yaml}`.
- 함정: 기본 actors 로는 가장자리 통로에 사람·지게차가 있어 순회가 막힘 → `slam actors:=none`. 제자리 회전 P 제어는 0.12 rad/s 미만이면 마찰로 멈춤. RViz 뷰는 시작 후 휠 7칸 축소하면 창고 전체가 들어옴. Ceres `num_threads: 50 exceeds ... 16` 경고는 최적화 때마다 나오며 무해.
- 실측: 한 바퀴 뒤 map→odom (-0.023, 0.013, -0.37°), /map 301×222 @ 5 cm, 1 Hz, 포즈 그래프 노드 1110 · 루프 엣지 190. 라이다 높이 0.239 m → 작업대는 다리만, 선반은 기둥 + 아래 칸 상자만 지도에 남음(패키지 지도는 통째로 막힘). `start map:=$PWD/artifacts/maps/my_warehouse.yaml` 로 Nav2 active 확인.
- ④ 개정(v11→v20): 코드 절 그림 먼저, lidar/scan 발행 코드 추가, 브리지 프로세스 그림, odom 오차 원인 h3 7개(`draw_lesson03_drift_figures.py`, `odom_offline.py`). 미결: `odom_experiment.py` 가 /odom 과 한 틱 전 /ground_truth 를 짝지음 → 결과 그래프 재작성 제안 중.
- 커밋 안 함.

## 0-00. 2026-09-30 시작 체크리스트 (09-29 밤 점검 결과)

- ROS 프로세스는 모두 종료함(cleanup_ros.sh + `ros2 daemon stop`). 새로 시작하면 `source scripts/env.sh` 후 바로 띄우면 된다.
- 점검 결과 이상 없음: lesson01·02·03 md 가 참조하는 PNG 는 전부 존재, 중복·누락 없음. git 의 `D lesson02_intro_openarm.png` · `lesson02_intro_vicpinky.png` · `lesson02_pkg_files.png` 는 의도된 삭제(사이트 사진 그림으로 교체 / '이 페이지에서 보는 파일' 절 삭제).
- git: 09-29 오후 작업 전체를 커밋 9ad8d70 으로 push 함. 작업 트리 깨끗.
- **결정 대기**: `docs/camp/lesson03_square3_motion.png` 는 만들었지만 ④ 페이지에 안 들어감(3바퀴 절은 그래프만). 넣을지 지울지 사용자에게 확인.
- 검토 대기: ③ 3697442817, ④ 3696820239. Confluence 게시본과 로컬 md 의 일치 여부는 아직 대조 안 함.
- 다음 작업: 커리큘럼 ⑤ SLAM 페이지 (0-0 마지막 불릿 참고).

## 0-0. 2026-09-29 하루 요약 (다음 세션이 먼저 볼 것)

- Confluence EDU 학생 페이지 4장이 됐다: 소개(3692331022) · 설정(3692331054) · ① MuJoCo와 ROS2 연결(3692920898, v15) · ③ 로봇 모델 Description(3697442817, v10, 신규) · ④ 센서·TF·Odom(3696820239, v3, 신규). 각 페이지의 원고는 `docs/camp/lesson01_mujoco_ros2.md` · `lesson02_description.md` · `lesson03_sensors_odom.md`, 그림 생성 스크립트는 `draw_lesson01_xml_figures.py` · `draw_lesson01_py_figures.py` · `draw_lesson02_figures.py` · `draw_lesson03_figures.py`.
- 코드 변경: `src/vicpinky_description` · `src/openarm_description` 에 `launch/display.launch.py` + `rviz/display.rviz` 추가(빌드됨). 실험 도구 `docs/camp/odom_experiment.py` · `scan_probe.py`.
- git: 오전 작업은 커밋 c464fc3 으로 push 됨. **오후 작업(③ 페이지 v3 이후 개정, ④ 페이지 전체, 그림 · 스크립트)은 아직 커밋하지 않았다.** 사용자가 요청하면 `git add -A && git commit && git push`.
- 사용자 편집 습관(0-2 에 추가됨): 코드 절은 코드 + 그림만, 설명 불릿은 거의 다 지운다. 개념 절 불릿도 자주 지운다 → 새 페이지는 불릿을 최소로 쓰고 그림에 내용을 담는다.
- 다음 페이지 = 커리큘럼 ⑤ SLAM (`./scripts/mobile_openarm slam`, slam_toolbox, map → odom, 지도 저장) → ⑥ Nav2. 같은 규칙과 같은 도구(render_terminal.py, xdotool 캡처, draw_*_figures.py)로 만든다.


## 0-1. 배포 채널 (2026-09-27 저녁에 만든 것)

- **GitHub (public)**: https://github.com/PinkWink/pinklab_mobile_openarm_ros2_mujoco — 이 워크스페이스가 그대로 저장소(`main`). `gh` CLI가 PinkWink 계정으로 로그인돼 있다. 커밋·push는 사용자가 요청할 때만. 제외 규칙은 `.gitignore`(build/install/log, `.venv*`, `.env`, `confluence_token.txt`, artifacts/logs/runs/datasets, 가중치는 OpenVINO 320 하나만).
- **Confluence EDU 공간** (spaceId 2517565443, 부모 페이지 3692396550 "주행형 양팔로봇 수업자료 (mujoco + ROS2)"):
  - 3692331022 "패키지 소개와 단기 과정 커리큘럼" ← `docs/camp/intro_curriculum.md` (개조식, h3마다 그림 1장) + `architecture.png` + `intro_*.png` 21장 (`draw_intro_figures.py`, 2026-09-28 v10)
  - 3692331054 "환경 설정과 패키지 사용법" ← `docs/camp/setup_usage.md` (개조식, h3마다 그림 1장) + 그림 4장 (`draw_setup_figures.py`) + `setup_*.png` 26장 (setup_start_result.png · setup_display_result.png 는 실제 화면 캡처) (`draw_setup_detail_figures.py`, 2026-09-28)
  - 3692920898 "MuJoCo와 ROS2를 연결하기" (Gazebo vs MuJoCo + two_link_arm.xml 해설(2절, 2026-09-29 추가: URDF vs MJCF 4절 → mujoco.viewer 캡처 → 요소별 h3 10개, 그림 `draw_lesson01_xml_figures.py`) + 최소 브리지 3절: 실행 캡처 → Python↔MuJoCo 8절(MjModel · MjData · mj_step · 이름 찾기 · Renderer · viewer · 실시간, `draw_lesson01_py_figures.py`) → 함수별 코드 6절 → 'MuJoCo <-> ROS2' 요약 그림(`lesson01_exchange.png`) → 해 볼 것. 요소별 XML 절과 뷰어 절은 사용자 요청으로 불릿 없이 코드+그림만, 2026-09-29 v14) ← `docs/camp/lesson01_mujoco_ros2.md` (h3 32개 = 그림 32장) + `lesson01_*.png` (`draw_lesson01_figures.py` 블록선도 20장, `render_terminal.py` 로 그린 실제 CLI 출력 캡처 9장, 실제 화면 캡처 `lesson01_run_result.png` · `lesson01_pub1_motion.png` · `lesson01_pub2_motion.png` · `lesson01_t2_rqt_window.png`)
  - 3697442817 "로봇 모델(Description): URDF/Xacro → MJCF 와 robot_state_publisher" (커리큘럼 ③, 2026-09-29 v1) ← `docs/camp/lesson02_description.md` (h3 28개: 1 패키지 구분 3절 → 2 관계 편 URDF 하나가 세 곳으로 · Xacro 조립 · URDF→MJCF 더해지는 것 · 이름 일치 · TF 발행자 · display 6절 + 실행 캡처 8절 → 3 코드 편 12절(expand_urdf · warehouse.launch setup · build_model · link · joint 규칙 · geometry · lidar site/camera · actuator · mimic · Physics.__init__ · publish_state · display.launch) → 해 볼 것) + `lesson02_*.png` 29장 (`draw_lesson02_figures.py` 블록선도 21장, `render_terminal.py` CLI 캡처 8장) + `setup_display_result.png` 재사용. 2026-09-29 오후 추가(v3): '두 종류의 패키지' 뒤에 OpenARM · Vic Pinky 소개 h3 2개와 각 패키지 단독 display 명령·결과 h3 4개. 이를 위해 상류 패키지 `src/vicpinky_description` 과 `src/openarm_description` 에 `launch/display.launch.py` + `rviz/display.rviz` 를 추가(setup.py 에 launch/rviz 폴더 설치 등록, UPSTREAM.md 에 'Local additions' 기록; vicpinky 는 robot_core.xacro 를 xacro 로 펼치고, openarm 은 상류 예제 `urdf/example/v1.urdf` 를 그대로 씀, Fixed Frame 은 각각 base_footprint · world). 실행: `ros2 launch vicpinky_description display.launch.py`, `ros2 launch openarm_description display.launch.py`. v4: 소개 h3 2개는 공식 사이트 사진·사양 요약으로 교체(`lesson02_intro_openarm_site.png` = docs.openarm.dev 히어로+치수도, `lesson02_intro_vicpinky_site.png` = pinklab.art/vic-pinky 제품사진+제원도면, PIL 합성; 손그림 intro 함수는 제거). 주의: 사이트는 OpenArm 2.0 기준, 우리 자산은 v1.0. v5: 소개 h3 는 사진만 두고, 요약 불릿은 새 h3 'OpenARM 특징' · 'Vic Pinky 특징'(카드 블록선도 `lesson02_feat_*.png` + 불릿)으로 분리. v6: 특징 절 · display 절 불릿 삭제, '이 페이지에서 보는 파일' h3 삭제(그림·함수도 제거). 남은 불릿은 '크기 비교' 2개 · '해 볼 것' 3개뿐. v7: expand_urdf h3 제목에 '(다른 launch · 모듈이 import 해서 사용)' 추가. v8: 3 코드 편 맨 앞에 h3 '파생물의 흐름: model.py → robot.urdf → 누가 쓰나'(그림만, `lesson02_code_derived.png`; 사용자 질문 '왜 매번 생성하나'에 대한 답 = xacro 76 ms · MJCF 296 ms 로 싸고, 원본 xacro/YAML/launch 인자에 따라 달라지는 파생물이라 캐시하면 stale 위험). v9: 같은 그림 아래 행에 build_model 파생물 3종(mobile_openarm.urdf · *_<sha>.obj 41개 · warehouse.xml → MuJoCo) 추가. 같은 폴더의 aruco_*.png(markers.py) · cameras/(camera_demo) · run.lock 은 description 파생물이 아님. v10: '시뮬레이터 없이 보기 … URDF 와 MJCF 의 크기 비교'(h3 10개)를 2절에서 떼어 새 최상위 절 '4. 실행해보기'로 3 코드 편 뒤에 배치, '해 볼 것'은 맨 끝(4절 아래)으로 이동. 캡처는 `display.launch.py gui:=false rviz:=false` 를 bash 로 띄워 얻음(zsh 에서 setup.bash 소싱 실패 → `bash -c` 로 실행).
  - 3696820239 "센서 · TF · Odom: 브리지가 재는 것과 오도메트리" (커리큘럼 ④, 2026-09-29 v2) ← `docs/camp/lesson03_sensors_odom.md` (h2 5개: 1 Bringup(launch 트리 · mode · wrapper · drive 실행 캡처) → 2 센서(개요 · 라이다 scan() 코드 · LaserScan · echo/probe 캡처 · RViz · 엔코더 · 카메라 · clock/TF · view_frames 트리 · 주기 실측) → 3 Odom 계산(차동 기구학 · step 앞/뒤 코드 · publish_state · echo/tf 캡처) → 4 프레임과 실험(world/odom/base_footprint · /ground_truth · 사각형 주행 실험 1/3바퀴 그래프 · spawn 실험) → 5 의미와 단점 → 해 볼 것) + `lesson03_*.png` 35장 (`draw_lesson03_figures.py` 블록선도 18장, 터미널 캡처 11장, 화면 캡처 4장, 그래프 2장). 실험 도구: `docs/camp/odom_experiment.py`(/cmd_vel 로 사각형, odom 폐루프, /odom·/ground_truth CSV), `docs/camp/scan_probe.py`. 실측: 사각형 1바퀴(8 m) 오차 0.5 cm/0.19°, 3바퀴(24 m) 2.0 cm/0.77°; spawn:=pick_table 이면 truth (1.2,-3.6) vs odom (0,0). 뷰어+RViz+카메라 켠 상태의 hz 실측은 설정의 약 0.82배(실시간 비율). 장애물에 밀어붙이는 실험은 바퀴가 토크 한계에서 멈춰(미끄럼 없음) 시연이 안 돼 제외.
  - 갱신: `set -a; source ../confluence_token.txt; set +a; python3 scripts/publish_confluence.py <md> "<제목>" --update <pageId> [png...]`. 새 하위 페이지: `... <md> "<제목>" 3692396550 2517565443 [png...]`. 문법: `:::tip|info|note|warning|panel 제목 … :::`, `:::cards(2|3)` + `::card 제목`, `![..](x.png){width=1000}`.
- **Confluence PD 공간** (개발 기록, 부모 3683418127): Phase 0 3684663302, M1 3687055362, M2 3687776258, M3 3687251977, M4 3692527619, M5 3692527659.
- **학회 전달용 커리큘럼**: Claude Doc https://claude.ai/code/artifact/5d2472b7-3ceb-4be2-9ee2-2da6dbddba30 + 로컬 `../CAMP_CURRICULUM.md`. 강사 개발 계획은 `../LECTURE_PLAN.md`(v4).

## 0-2. 페이지 작성 규칙 (2026-09-28, 사용자 피드백으로 굳어진 것)

- 문장은 짧게, 전부 개조식. 표는 쓰지 않는다(사용자가 표를 모두 삭제시킴). h3가 최소 단위이고 나중에 슬라이드 한 장이 되므로 h3 본문은 짧게, **h3마다 대표 그림 1장**.
- 명령은 코드 블록으로 두되 **명령마다 h3를 나누고 실제 실행 결과를 캡처**해서 붙인다. 터미널 출력은 실제로 실행해 얻은 텍스트를 `docs/camp/render_terminal.py`로 터미널 모양 PNG로 그린다(한글 폰트 NanumGothicCoding). GUI는 `DISPLAY=:1`에서 xdotool 로 창을 배치하고 `import -window root -crop WxH+X+Y` 로 찍는다. 움직임(topic pub 등)은 보내기 전/후를 각각 찍어 PIL 로 좌우 합성한다(`lesson01_pub1_motion.png` 만든 방식, 코드는 세션 기록에만 있고 스크립트화 안 됨).
- 코드 설명은 "함수 이름 - 역할" h3 + 코드 발췌 + 블록선도. **불릿은 넣지 않는다** (2026-09-29 사용자가 lesson01·02 의 코드 절 불릿을 전부 삭제시킴). 개념 절의 불릿도 자주 지우므로 3개 이하로 짧게. 최상위 절은 md `##` (Confluence h2) 이고 사용자가 'h1' 이라고 부르는 것이 이것이다.
- 외부 제품 소개(OpenARM · Vic Pinky)는 공식 사이트 사진을 PIL 로 합성한 그림 1장 + 특징 카드 블록선도 1장으로 (lesson02 1절 견본). 시뮬레이터 화면 캡처는 `import -window root -crop 2230x866+0+0` 후 (62,30) 부터 잘라 독·상단바 제거; 창은 xdotool 로 MuJoCo 0,0 1100×820 · RViz 1120,0 1100×820 배치.
- 그림은 matplotlib, 직교 화살표만, 헬퍼는 `draw_intro_figures.py`(chain / flow_rows / tiles / rbox)를 다른 스크립트가 import 한다. 렌더 후 반드시 PNG를 눈으로 확인(글자 넘침이 잦다).
- Claude Code Bash 에서 `pkill -f`/`pgrep -f` 패턴이 자기 명령줄과 겹치면 셸이 죽는다 → `pgrep -f "^python lessons/..."` 처럼 앵커를 쓴다. 백그라운드로 띄운 파이썬은 SIGINT 를 무시하므로 종료 테스트는 `timeout -s INT` 로 포그라운드에서 한다.

## 0. 컨셉 변경 (2026-09-27)

6모듈 LLM·비전 강좌 계획(`../../LECTURE_PLAN.md` v3)은 **2일짜리 겨울 캠프**로 바뀌었다: "MuJoCo + ROS2 기반 Mobile Dual-Arm Robot & LMM Robotics", 수강생 60~80명.

- Day 1: Gazebo vs MuJoCo → MuJoCo+ROS2 브리지 → OpenARM 로봇 description → 센서/TF/odom/LiDAR → SLAM → Nav2 → 자율주행 데모.
- Day 2: MoveIt+MuJoCo → 팔/EE 제어 → Pick & Place → Nav2+Pick&Place 통합 → LMM(OpenAI API) → LMM→ROS2 Task Pipeline → MuJoCo 웹 대시보드(버퍼, 밀리면 데모만) → Final Mission(자연어 → LMM → Nav2/MoveIt → MuJoCo).
- GitHub 폴더: 01_mujoco_ros2, 02_robot_description, 03_slam, 04_navigation, 05_moveit, 06_pick_place, 07_mobile_manipulation, 08_lmm, 09_web_dashboard, 10_final_project.
- 운영: 도커 없음. 수강생이 직접 설치하고, GitHub의 **완성 소스**를 실행하며 강사 설명을 듣는다. 모듈당 50~70분(개념 → 핵심 코드 → 따라 실행 → 문제 해결). 수업 중 pip install 금지.
- 마감: 커리큘럼·시간표를 2026-09-29(화)까지 로봇학회에 전달.
- 범위 밖이 된 것: YOLO 학습(M2), 사람·안전모 조우 기억(M5), 센서 동기화(M6). "빨간 물체 검출"은 배포 가중치(OpenVINO CPU) 또는 HSV로 블랙박스 처리.

기존 자산과의 대응: 01~08, 10은 Phase 0 + M1~M4 코드로 거의 덮인다. 신규는 09 웹 대시보드, LMM의 **단계 목록** 출력(현재 스키마는 `move_object` 한 명령) + Task Manager, Gazebo vs MuJoCo 강의자료, 30줄짜리 최소 브리지 예제, 모듈별 README/실행 명령, git 저장소(현재 git 아님).

## 1. 지금 어디까지 왔나

- **강의 모듈 05·06 완료 (2026-09-27)**: `lessons/05_moveit/ee_control.py`(where/named/ik/pose/cartesian/gripper/demo) + README, `lessons/06_pick_place/pick_then_place.py`(phase pick → 같은 작업대에 place) + README. launch 인자 `spawn:=pick_table|X,Y,YAW`(MuJoCo 위치 + AMCL 초기 위치). 도킹은 이제 마커 쌍 측정만 쓰고 단일 마커는 무시(blind 구간은 마지막 쌍 측정의 odom 기준). 검증: EE demo 성공, red pick 39 s + place-back 42 s(3.7 cm), blue pick 70 s + place_table 103 s(1.8 cm).
- **M5 완료 (2026-09-27)**: LMM 작업 계획(RobotPlan: navigate/detect/pick/place/…) + Task Manager(`ros2 run warehouse_lecture task_manager`, /execute_plan). PickPlace 서버에 `phase`(all/pick/place)와 `held` 상태, 도킹 단일 마커 필터, 들기 대체 경로, 실패 복구(recover) 추가. 20문장 계획 정확도 20/20, Final Mission 3종(빨간 상자 운반 174 s, 랙 C 보고 66 s, 노란 상자 운반 155 s) 연속 성공. 문서 `docs/lecture/05_task_plan.md`, 예제 `examples/m5_task_plan/`, 테스트 41개.
- **M4 완료 (2026-09-27)**: 운반 명령 3회 연속 성공(빨강 152 s, 파랑 170 s, 노랑 154 s, 슬롯 오차 2.7~4.3 cm). 문서 `docs/lecture/04_command_dialog.md`. 노란 상자(옆 도킹)는 처음 성공. 고친 것: 옆 도킹 부호(`pick_place_server.py`, `-dock_side`), Nav2 `default_server_timeout` 20→200 ms, `NavClient.go_to` ABORTED 시 1회 재시도, 회귀 테스트 추가(tests 35개).
- M3 완료 (2026-09-22): `examples/m3_llm/`, `docs/lecture/03_llm.md`, Confluence 3687251977.
- M2 완료 (2026-09-22): `examples/m2_yolo/`, `docs/lecture/02_yolo.md`, Confluence 3687776258, 가중치 `weights/`.
- M1 완료 (2026-09-22): `examples/m1_ros_vision/`, `docs/lecture/01_ros_vision.md`, Confluence 3687055362.
- Phase 0 완료: `docs/lecture/phase0_report.md`, Confluence 3684663302 (부모 3683418127 "MuJoCo + ROS2 패키지 구성", space PD, spaceId 3419570180).
- 사용법 `docs/USAGE.md`, 설치 `docs/lecture/00_setup.md`. 소스는 git 저장소가 아니다. 원본 ZIP은 `../mobile_openarm_jazzy_ws.zip`.

## 2. 재부팅 후 다시 돌리는 순서

```bash
cd ~/mujoco_ros2/mobile_openarm_ws
source /opt/ros/jazzy/setup.bash          # zsh면 setup.zsh
source scripts/env.sh                    # venv + install setup + domain 43 + CycloneDDS
./scripts/cleanup_ros.sh
./scripts/mobile_openarm build           # 소스가 바뀌었을 때만 (config yaml 은 build/ 로 복사되므로 yaml 수정 후에도 필요)
python -m pytest tests -q                # 41개 통과 (약 1.2분). 시뮬레이터와 동시에 돌리지 말 것
./scripts/mobile_openarm start           # 시뮬레이터
```

M4 전체 데모(시뮬레이터 + 실행기 + 텍스트 대화)는 `docs/lecture/04_command_dialog.md` 2절, Final Mission(시뮬레이터 + task_manager + 04_final_mission.py)은 `docs/lecture/05_task_plan.md` 2절.

## 3. 다음 작업 (2일 과정 기준)

1. (완료 09-27) `LECTURE_PLAN.md` v4, 학회 전달 문서(Claude Doc + `CAMP_CURRICULUM.md`). 9/29 학회 전달은 사용자가 한다.
2. (완료 2026-09-27) 계획 수준 스키마 + Task Manager + PickPlace `phase`. 남은 것: 06_pick_place 실습 시나리오(`pick red --phase pick` → `pick red pick_table --phase place` 로 같은 작업대에 다시 놓기) 문서화·검증.
3. (완료) EE 제어 예제 → `lessons/05_moveit/`.
4. 09 웹 대시보드: 카메라 프레임은 핸들러 프로세스 안에 있으므로 핸들러가 JPEG를 websocket으로 내보내는 방식 또는 rosbridge + roslibjs. 로봇 상태(/odom, /joint_states, 스킬 phase) 표시 + 자연어 명령 입력(→ /warehouse/utterance).
4. GitHub 저장소: `git init`, `src/`는 하나(완성 코드), `lessons/01~10/README.md`에 실행 명령·핵심 코드 포인터. 설치 스크립트 + 사전 환경 점검 스크립트 강화(수강생 직접 설치).
5. ~~Gazebo vs MuJoCo 강의자료, 최소 브리지 예제(01_mujoco_ros2)~~ **완료 2026-09-28**: `lessons/01_mujoco_ros2/` (two_link_arm.xml = 2링크 팔 + 팔 끝 카메라, minimal_bridge.py 138줄: /clock /joint_states /tf /tip_camera/image_raw 발행 · /cmd 구독, README). Confluence 3692920898 v7 (Gazebo vs MuJoCo 6절 → 최소 브리지 → 실행 명령별 캡처 → 함수별 코드 구조 6절). 실행: `source scripts/env.sh; python lessons/01_mujoco_ros2/minimal_bridge.py --viewer`, 명령 `ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"`. 함정: MJCF 관절 range 는 `compiler angle="radian"` 없으면 도(degree) 단위; 관절에서 겹치는 캡슐은 contype=0 으로 자기 충돌 제외; 카메라 `xyaxes="0 -1 0 -1 0 0"` 이어야 링크 방향을 정방향으로 본다; `rclpy.init(signal_handler_options=SignalHandlerOptions.NO)` 라야 Ctrl+C 가 깨끗이 끝난다. 미결: `publish_joints` 가 TF 까지 발행해 이름이 좁다(사용자가 알고 있음, 나누려면 페이지 3장 코드 발췌도 같이 수정).
   **다음 세션은 여기서 시작**: (a) 페이지 3692920898 사용자 검토 후 남은 수정, (b) ~~커리큘럼 ③ Robot Description 페이지~~ **완료 2026-09-29** (3697442817, 사용자 검토 대기), (b-2) ~~커리큘럼 ④ Sensor·TF·Odom 페이지~~ **완료 2026-09-29** (3696820239, 사용자 검토 대기; 다음 페이지 = ⑤ SLAM), (c) `lessons/02~04`, `07~10` README, 수강생용 `INSTALL.md`와 `scripts/check_env.sh`(PASS/FAIL 표), 마지막에 09 웹 대시보드.
6. lessons README 틀은 `lessons/05_moveit/README.md`, `lessons/06_pick_place/README.md`를 따른다(목표 → 실행 → 화면에서 볼 것 → 핵심 코드 → 해 볼 것 → 문제 해결).

## 4. 개발용 도구

| 스크립트 | 용도 |
|---|---|
| `scripts/dev/restart_sim.sh [이름]` | headless 시뮬레이터 재시작 + 준비 대기. 로그 `artifacts/dev/<이름>.log`. `LAUNCH_ARGS="..."`로 인자 추가 |
| `scripts/dev/run_pick.sh [색] [from] [to]` | 운반 실행 + 상자 높이/손가락 타임라인 |
| `scripts/dev/monitor_parcel.py <log>` | parcel_1 높이·오른손가락·스킬 단계 기록 |
| `scripts/dev/grasp_physics.py` | ROS 없이 파지 유지 물리 실험 |
| `scripts/publish_confluence.py` | md → Confluence 하위 페이지 (토큰은 `../confluence_token.txt`) |
| `scripts/cleanup_ros.sh` | 잔여 ROS 프로세스 정리 |

## 5. 알아 두어야 할 함정

- `ros2 launch`를 그냥 치면 bridge가 mujoco를 못 찾는다. `env.sh`의 `ros2launch` 함수나 wrapper를 쓴다.
- ros2 CLI는 wrapper `exec` 또는 `env.sh` 환경에서만 노드가 보인다(CycloneDDS, domain 43). 토픽이 2개만 보이면 `ros2 daemon stop`.
- 시뮬레이터를 강제 종료하면 Nav2·MoveIt 자식이 남아 다음 실행에서 액션이 거부된다 → cleanup_ros.sh.
- `pkill -f 패턴`을 다른 명령과 같은 셸 줄에 쓰면 그 셸 자신이 죽는다. 종료는 별도의 짧은 명령으로, 패턴은 `p="command_exec""utor"; pkill -f "$p"`처럼 쪼개서.
- venv에 numpy 2가 들어가면 시스템 scipy와 충돌한다. `requirements-lecture.txt`의 고정 버전을 유지한다.
- 상자를 옮긴 뒤 세계는 초기화되지 않는다. 반복 시험은 시뮬레이터 재시작.
- 도킹 부호: `dock_side_for`(베이스의 축 기준 오프셋, +왼쪽)와 서보 `side`(베이스에서 본 축 위치)는 부호가 반대다.
- 4코어 제한에서 Nav2 BT의 goal 응답 타임아웃(default_server_timeout)이 20 ms면 ABORTED(6)가 난다. 200 ms로 둔다.
- `command_executor`와 `task_manager`는 둘 다 /execute_command 를 서비스하므로 하나만 띄운다. 시뮬레이터를 다시 띄우면 task_manager 도 다시 띄운다(든 물체 상태).
- 도킹은 마커 쌍 측정만 쓴다. 마커가 하나만 보이면 그 법선(±20°)이 횡 12 cm·거리 5 cm 를 틀리게 하므로 즉시 blind 구간으로 넘어간다(nav_client.dock). 상자가 planning scene 에 붙은 채 실패하면 recover() 가 풀어 준다.
