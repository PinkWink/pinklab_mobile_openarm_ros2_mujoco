"""One representative figure per h3 of the setup & usage Confluence page. Output: docs/camp/setup_*.png

Reuses the box / chain / tiles helpers of draw_intro_figures.py (orthogonal arrows, NanumGothic).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, cross, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


# ================================================================ 0. environment & prerequisites
def env_cards():
    fig, ax = fig_ax(14, 2.8)
    tiles(ax, [("지원 환경", ["Ubuntu 24.04 native + ROS 2 Jazzy", "4코어 · 16 GB · 내장 그래픽 (OpenGL 3.3+)", "외장 GPU · CUDA 불필요 (검출은 CPU)", "미지원: Windows · macOS · VM · WSL · 도커"], C["blue"]),
               ("필요한 것", ["GitHub 공개 저장소 clone", "디스크 20 GB 여유", "네트워크: apt · GitHub · api.openai.com", "OpenAI 키는 LMM 모듈부터 (강사 배포)"], C["yellow"]),
               ("소요 시간", ["ROS 2 Jazzy 설치 20~30분", "저장소 설치 스크립트 10~20분", "설치 확인 5분 (+ 운반 1회 3분)", "수업 중 설치 작업 없음 → 캠프 전에 끝낸다"], C["green"])],
          cols=3, y_top=2.6, h=2.4, tfs=12, fs=9.2)
    save(fig, "setup_env_cards.png")


# ================================================================ 1-1. ROS 2 Jazzy packages
def ros2_packages():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "① ROS 2 Jazzy + 이 패키지가 쓰는 추가 항목 (처음 한 번)", bold=True, fs=12)
    tiles(ax, [("ros-jazzy-desktop", ["공식 설치 안내 (Debs)", "RViz · rqt 포함"], C["blue"]),
               ("주행", ["navigation2 · nav2-bringup", "slam-toolbox"], C["yellow"]),
               ("팔", ["moveit: move-group · kinematics", "planners-ompl · configs-utils", "controller-manager · visualization"], C["green"]),
               ("도구", ["colcon · rosdep · git · venv", "xacro · rsp · tf2-tools · cyclonedds"], C["purple"])],
          cols=4, y_top=2.9, h=1.8, tfs=11.5, fs=8.8)
    note(ax, 0.3, 0.6, "마지막에  sudo rosdep init && rosdep update", fs=9.5)
    save(fig, "setup_ros2_packages.png")


# ================================================================ 1-2. install script
def install_script():
    fig, ax = fig_ax(14, 3.9)
    note(ax, 0.3, 3.6, "② git clone  →  ③ ./scripts/install_lecture.sh 가 하는 일", bold=True, fs=12)
    chain(ax, [("rosdep 확인", ["빠진 ROS 패키지 안내"]), ("가상환경", [".venv-mobile-openarm", "ROS Python과 분리"]),
               ("pip", ["torch CPU · ultralytics", "openai · mujoco …"]), (".env 생성", [".env.example 복사", "OpenAI 키 자리"]),
               ("colcon build", ["ROS 2 워크스페이스"]), ("단위 테스트", ["\"설치 완료\" 출력", "= 성공"])],
          y=1.2, h=1.9, gap=0.25, colors=[C["grey"], C["purple"], C["purple"], C["yellow"], C["blue"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.6, "고정 버전은 올리지 않는다:  numpy<2 · opencv-python<4.11 · setuptools<80 · ml-dtypes<0.6   (ROS Jazzy Python 스택 · colcon 호환)", fs=9.2, color="#C62828")
    save(fig, "setup_install_script.png")


# ================================================================ 1-2b. install_lecture.sh step by step
def install_script_detail():
    fig, ax = fig_ax(14, 5.2)
    note(ax, 0.3, 4.9, "scripts/install_lecture.sh 안에서 일어나는 일 (실패하면 그 단계에서 멈춘다: set -e)", bold=True, fs=12)
    flow_rows(ax, [("1  사전 검사", "ROS_DISTRO=jazzy · Linux 인지"), ("2  rosdep install", "src/ 의 package.xml 의존성"),
                   ("3  apt 누락 검사", "빠지면 안내 후 종료"), ("4  venv 생성", "system-site-packages"),
                   ("5  pip 설치", "requirements-*.txt 2개"), ("6  pip check", "의존성 충돌이면 종료"),
                   ("7  .env", "없으면 .env.example 복사"), ("8  colcon build", "symlink · 필요한 패키지만"),
                   ("9  pytest -x", "시뮬레이터 없이"), ("10  완료 안내", "\"설치 완료\" 출력")],
              per_row=5, y_top=4.5, h=1.35, gap=0.25, row_gap=0.7,
              colors=[C["grey"], C["blue"], C["blue"], C["purple"], C["purple"], C["purple"], C["yellow"], C["blue"], C["green"], C["green"]], tfs=10.5, fs=8.4)
    note(ax, 0.3, 0.35, "빌드 환경 변수: MOBILE_ENV_MODE=native      테스트 환경 변수: MOBILE_OPENARM_MODEL_DIR=artifacts/mobile_generated", fs=9.2)
    save(fig, "setup_install_script_detail.png")


# ================================================================ 1-2c. getting an OpenAI API key
def openai_signup():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "OpenAI API 키 발급 (platform.openai.com)", bold=True, fs=12)
    chain(ax, [("1  가입 · 로그인", ["platform.openai.com", "ChatGPT 계정과 같아도 됨"]), ("2  결제 수단 등록", ["Settings → Billing", "카드 등록 · 크레딧 충전 (선불)"]),
               ("3  API keys", ["Dashboard → API keys", "Create new secret key"]), ("4  키 복사", ["sk-… 는 한 번만 보인다", "바로 복사해 둔다"]),
               ("5  .env 에 붙여넣기", ["OPENAI_API_KEY=sk-…", "저장소에 커밋하지 않는다"])],
          y=1.3, h=2.1, gap=0.28, colors=[C["grey"], C["yellow"], C["blue"], C["red"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.6, "ChatGPT 유료 구독과 API 크레딧은 별개다.  이 과정의 호출량은 수 달러 수준이며 logs/openai_usage.jsonl 에 비용이 기록된다.", fs=9.2)
    save(fig, "setup_openai_signup.png")


# ================================================================ 1-3. OpenAI key
def openai_key():
    fig, ax = fig_ax(14, 3.8)
    note(ax, 0.3, 3.5, "④ OpenAI 키: LMM 모듈부터 필요하다", bold=True, fs=12)
    chain(ax, [(".env.example", ["저장소에 포함"]), (".env", ["OPENAI_API_KEY=sk-…", "수업용 키는 강사가 배포"]),
               ("llm.yaml", ["모델 · 가격표", "src/warehouse_lecture/config"]), ("openai_usage.jsonl", ["호출 기록: 토큰 · 비용", "logs/"])],
          y=1.3, h=1.8, x1=13.7, colors=[C["grey"], C["red"], C["yellow"], C["green"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.6, "키 없이 동작:  주행 · MoveIt · Pick & Place 모듈          키 필요:  ⑪ LMM 이후", fs=9.5)
    save(fig, "setup_openai_key.png")


# ================================================================ 1-4. env.sh per terminal
def env_sh():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "새 터미널마다: setup.bash → scripts/env.sh", bold=True, fs=12)
    chain(ax, [("source /opt/ros/jazzy/setup.bash", ["zsh 는 setup.zsh"]), ("source scripts/env.sh", ["가상환경 + install 환경", "ROS_DOMAIN_ID=43 · CycloneDDS(localhost)"]),
               ("ros2 · 예제 스크립트", ["이 터미널에서 바로 실행"])],
          y=1.5, h=1.8, colors=[C["blue"], C["purple"], C["green"]], tfs=10.5, fs=8.8)
    ax.add_patch(Rectangle((0.3, 0.3), 13.4, 0.85, fc="#FFFBF0", ec="#D9C48A", lw=1.0, zorder=1))
    note(ax, 0.5, 0.72, "source 안 한 터미널:  ./scripts/mobile_openarm exec <명령>", fs=9.5, color="#7a4b00")
    note(ax, 13.5, 0.72, "localhost 통신 → 강의실의 다른 노트북과 토픽이 섞이지 않는다", fs=9.5, ha="right", color="#7a4b00")
    save(fig, "setup_env_sh.png")


# ================================================================ 1-4b. env.sh step by step
def env_sh_detail():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "scripts/env.sh 안에서 일어나는 일 (source 해서 현재 셸에 적용)", bold=True, fs=12)
    flow_rows(ax, [("1  ROS 확인", "ROS_DISTRO=jazzy 아니면 중단"), ("2  가상환경 활성화", ".venv-mobile-openarm"),
                   ("3  워크스페이스", "install/local_setup.bash · zsh"), ("4  통신 범위", "DOMAIN_ID=43 · localhost 만"),
                   ("5  DDS", "CycloneDDS + cyclonedds.xml"), ("6  로그 위치", "ROS_HOME · ROS_LOG_DIR → .ros/"),
                   ("7  모델 · 파이썬", "MODEL_DIR · PYTHONNOUSERSITE=1"), ("8  ros2launch 함수", "venv python 으로 launch")],
              per_row=4, y_top=3.9, h=1.3, gap=0.25, row_gap=0.65,
              colors=[C["grey"], C["purple"], C["blue"], C["yellow"], C["yellow"], C["grey"], C["purple"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.3, "끝나면 한 줄 출력:  mobile_openarm env: domain 43, rmw rmw_cyclonedds_cpp, venv …", fs=9.2, color="#2e7d32")
    save(fig, "setup_env_sh_detail.png")


# ================================================================ 1-5. install check
def install_check():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "⑤ 설치 확인: 순서대로 네 가지", bold=True, fs=12)
    chain(ax, [("1  pytest", ["python -m pytest tests -q", "41개 PASS · 약 1.5분", "시뮬레이터 불필요"]),
               ("2  start", ["./scripts/mobile_openarm start", "MuJoCo 창 + RViz", "준비 완료 3줄"]),
               ("3  goal", ["mobile_openarm goal 1.0 0.6 0", "다른 터미널에서", "로봇이 자율주행"]),
               ("4  pick", ["mobile_openarm pick red", "픽업 → 적재 작업대 · 약 3분", "success=True"])],
          y=1.1, h=2.2, colors=[C["grey"], C["blue"], C["yellow"], C["green"]], tfs=11, fs=8.6)
    note(ax, 0.3, 0.55, "준비 완료 3줄:  Managed nodes are active  ·  You can start planning now!  ·  PickPlace server ready", fs=9.2, color="#2e7d32")
    save(fig, "setup_install_check.png")


# ================================================================ 2-1. wrapper commands
def commands():
    fig, ax = fig_ax(14, 6.4)
    note(ax, 0.3, 6.1, "./scripts/mobile_openarm <명령>", bold=True, fs=12)
    note(ax, 0.3, 5.7, "시뮬레이터 띄우기 (한 번에 하나만)", bold=True, fs=10.5, color="#1f4e79")
    tiles(ax, [("start (= nav)", ["MuJoCo + Nav2 + MoveIt", "+ RViz + 운반 스킬 + 카메라", "기본 · 통합 · LMM"], C["blue"]),
               ("drive", ["MuJoCo + 주행 RViz", "Nav2 · MoveIt 없음", "브리지 · 센서"], C["blue"]),
               ("slam", ["SLAM Toolbox 지도 작성", "", "SLAM"], C["blue"]),
               ("moveit", ["MuJoCo + MoveIt", "Nav2 없음", "팔 제어"], C["blue"]),
               ("display", ["URDF만 RViz + slider", "시뮬레이터와 동시 실행 금지", "Robot Description"], C["blue"])],
          cols=5, y_top=5.45, h=1.6, gap=0.25, tfs=11, fs=8.4)
    note(ax, 0.3, 3.5, "로봇 움직이기", bold=True, fs=10.5, color="#2e7d32")
    note(ax, 8.6, 3.5, "유틸", bold=True, fs=10.5, color="#555555")
    tiles(ax, [("teleop", ["키보드 주행 i / , / j / l / k"], C["green"]),
               ("goal X Y [YAW]", ["Nav2 목표 · 결과 대기"], C["green"]),
               ("arm {left|right|both} {자세}", ["transport · ready · hands_up · home"], C["green"]),
               ("pick OBJ [FROM] [TO]", ["운반 스킬 · OBJ = red / blue / yellow", "[--phase pick|place]"], C["green"]),
               ("build", ["colcon 빌드 · 소스 고쳤을 때만"], C["grey"]),
               ("exec CMD…", ["wrapper 환경에서 임의 명령"], C["grey"]),
               ("Ctrl+C", ["종료"], C["grey"]),
               ("scripts/cleanup_ros.sh", ["남은 프로세스 정리"], C["grey"])],
          cols=4, y_top=3.25, h=1.25, gap=0.25, tfs=10.5, fs=8.4)
    save(fig, "setup_commands.png")


# ================================================================ 2-2. launch args
def launch_args():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.8, "launch 인자  (start · drive · slam · moveit 뒤에  인자:=값)", bold=True, fs=12)
    tiles(ax, [("rviz · viewer · moveit", ["기본 true", "RViz · MuJoCo 창 · MoveIt 기동", "느리면 rviz:=false"], C["blue"]),
               ("profile", ["기본 lite", "lite: 카메라 2대 320×240 2 FPS", "full: 4대 640×480 5 FPS"], C["yellow"]),
               ("spawn", ["기본 원점", "pick_table · place_table · rack_c …", "또는 X,Y,YAW · AMCL 초기 위치도 함께"], C["green"]),
               ("locate", ["기본 truth (시뮬레이터 정답)", "vision = 카메라 검출", "운반 스킬의 물체 위치"], C["orange"]),
               ("camera_handler", ["기본 LecturePipeline", "시뮬레이터 안 Python 핸들러", "none = 렌더 안 함"], C["purple"]),
               ("actors", ["기본 패키지 정의", "사람 · 소품", "none = 빈 창고"], C["red"]),
               ("map", ["기본 패키지 지도", "map:='' 이면 SLAM + Nav2", ""], C["grey"])],
          cols=4, y_top=3.5, h=1.6, gap=0.25, tfs=11, fs=8.6)
    save(fig, "setup_launch_args.png")


# ================================================================ 2-3. common combos
def combos():
    fig, ax = fig_ax(14, 2.0)
    tiles(ax, [("저사양 노트북", ["start rviz:=false"], C["blue"]),
               ("작업대 앞에서 바로", ["start spawn:=pick_table"], C["yellow"]),
               ("카메라 검출로 운반", ["LECTURE_HANDLERS=ArUco+YOLO 핸들러", "start camera_depth:=true locate:=vision"], C["green"]),
               ("화면 없이 (headless)", ["start viewer:=false rviz:=false"], C["grey"])],
          cols=4, y_top=1.8, h=1.5, gap=0.25, tfs=11, fs=8.6)
    save(fig, "setup_combos.png")


# ================================================================ 3-1. locations
def locations():
    fig, ax = fig_ax(14, 2.0)
    tiles(ax, [("작업대", ["pick_table 픽업 작업대 (2.6, -3.6)", "place_table 적재 작업대 (2.6, 3.6)"], C["green"]),
               ("랙 · 통로 · 벽", ["rack_a ~ rack_f 랙 A~F", "center_aisle · east_wall · west_wall"], C["yellow"]),
               ("base_goal (▲)", ["Nav2 목표 = 사전 도킹 지점", "방향 = 진행 방향"], C["blue"]),
               ("한국어 별칭", ["locations.yaml 의 aliases", "LMM 파서가 그대로 쓴다"], C["orange"])],
          cols=4, y_top=1.8, h=1.5, gap=0.25, tfs=11, fs=8.8)
    save(fig, "setup_locations.png")


# ================================================================ 3-2. table / boxes / markers (side view)
def table_side():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "작업대 · 상자 · ArUco 마커 (옆에서 본 모습)", bold=True, fs=12)
    # floor
    ax.plot([1.0, 8.5], [0.6, 0.6], color=INK, lw=1.5)
    note(ax, 8.6, 0.6, "바닥", fs=9)
    # table top at 0.78 m -> scale 3.2 units per m
    S, x0, y0 = 3.2, 2.0, 0.6
    top = y0 + 0.78 * S
    ax.add_patch(Rectangle((x0, top - 0.12), 4.5, 0.12, fc="#C8E6C9", ec="#2E7D32", lw=1.2, zorder=3))
    for lx in (x0 + 0.25, x0 + 4.5 - 0.25 - 0.14):
        ax.add_patch(Rectangle((lx, y0), 0.14, top - 0.12 - y0, fc="#CFD8DC", ec="#607D8B", lw=1, zorder=2))
    # markers on legs at 0.3 m
    for lx in (x0 + 0.25, x0 + 4.5 - 0.25 - 0.14):
        ax.add_patch(Rectangle((lx - 0.06, y0 + 0.3 * S - 0.18), 0.26, 0.36, fc="white", ec="black", lw=1.2, zorder=4))
    label(ax, x0 + 2.25, y0 + 0.3 * S, "ArUco 마커 2개 / 작업대 · 다리 높이 0.3 m", fs=9)
    # boxes on top
    colors = ["#E53935", "#1E88E5", "#FDD835"]
    for i, c in enumerate(colors):
        bx = x0 + 0.5 + i * 0.75
        ax.add_patch(Rectangle((bx, top), 0.45 * S / 3.2 * 1.0, 0.6 * S / 3.2 * 1.0, fc=c, ec="black", lw=0.8, zorder=4))
    label(ax, x0 + 1.5, top + 0.9, "상자 3개: 빨강 · 파랑 · 노랑  45 × 45 × 60 mm", fs=9)
    # dimension lines
    arrow(ax, (x0 + 5.0, y0), (x0 + 5.0, top), style="<|-|>", color="#555555", lw=1.2)
    label(ax, x0 + 5.0, (y0 + top) / 2, "상판 높이 0.78 m", fs=9)
    arrow(ax, (x0, top - 0.3), (x0 - 0.9, top - 0.3), color="#1f4e79", lw=1.4)
    label(ax, x0 - 0.45, top - 0.05, "앞 가장자리 x = 2.18", color="#1f4e79", fs=8.8)
    # right side notes
    rbox(ax, 9.9, 2.55, 3.8, 1.35, "카메라에만 보인다", ["마커는 라이다 · 지도에 없다", "도킹은 카메라 검출로"], fc=C["yellow"], tfs=10.5, fs=8.8, align="left")
    rbox(ax, 9.9, 0.9, 3.8, 1.35, "마커 id", ["픽업 작업대 0 · 1", "적재 작업대 2 · 3"], fc=C["blue"], tfs=10.5, fs=8.8, align="left")
    save(fig, "setup_table_side.png")


# ================================================================ 3-3. actors
def actors():
    fig, ax = fig_ax(14, 2.0)
    tiles(ax, [("사람 4명", ["안전모 착용 2 · 미착용 2", "2명은 통로 왕복"], C["red"]),
               ("소품", ["지게차 · 팔레트", "콘 2 · 소화기"], C["yellow"]),
               ("센서에는 보이고 지도에는 없다", ["라이다 · 카메라에 보임", "정적 지도에 없음 → Nav2가 실시간 회피"], C["blue"]),
               ("actors.yaml", ["로봇과 물리 접촉 없음", "actors:=none 이면 제거"], C["grey"])],
          cols=4, y_top=1.8, h=1.5, gap=0.25, tfs=11, fs=8.8)
    save(fig, "setup_actors.png")


# ================================================================ 4. ROS 2 interfaces
def interfaces():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "ROS 2 인터페이스 한눈에", bold=True, fs=12)
    tiles(ax, [("표준 토픽 (브리지가 만든다)", ["/cmd_vel  /odom  /scan  /joint_states  /tf  /clock", "/cmd_vel 은 양팔이 주행 자세일 때만 유효 (인터록)"], C["purple"]),
               ("주행 · 팔 액션", ["/navigate_to_pose  (Nav2)", "/move_action  /compute_ik  /compute_cartesian_path", "/*_gripper_controller/gripper_cmd"], C["blue"]),
               ("스킬 · 실행기 액션", ["/pick_place  (object, from, to, arm, phase)", "/execute_command  ← command_executor", "/execute_plan  ← task_manager"], C["green"]),
               ("검출 결과", ["/vision/detections  /vision/markers", "카메라 핸들러 출력 · 영상 토픽 없음"], C["yellow"]),
               ("대화", ["/warehouse/utterance  사용자 문장", "/warehouse/narration  로봇 답", "콘솔 · 웹 대시보드"], C["orange"]),
               ("배우 · 정답 (평가용)", ["/warehouse/actor_states  /warehouse/set_actor", "/ground_truth  /warehouse/object_poses"], C["grey"])],
          cols=3, y_top=4.8, h=2.1, gap=0.3, tfs=11, fs=8.6)
    save(fig, "setup_interfaces.png")


# ================================================================ 5-1. pick examples
def pick_examples():
    fig, ax = fig_ax(14, 3.3)
    tiles(ax, [("pick red", ["pick_table → place_table 한 번에", "약 2.5~3분 · success=True"], C["green"]),
               ("pick red --phase pick", ["집고 운반 자세까지", "든 채 멈춘다"], C["yellow"]),
               ("pick red pick_table --phase place", ["든 상자를 같은 작업대에 다시", "pick 이후에만"], C["yellow"]),
               ("pick parcel_3 pick_table place_table --arm left", ["상자 · 출발 · 도착 · 팔 지정", "결과: 놓인 위치 · 슬롯 오차 1~4 cm"], C["blue"])],
          cols=2, y_top=3.1, h=1.4, gap=0.3, tfs=10.5, fs=8.8)
    save(fig, "setup_pick_examples.png")


# ================================================================ 5-2. pick cautions
def pick_cautions():
    fig, ax = fig_ax(14, 2.0)
    tiles(ax, [("세계는 초기화되지 않는다", ["반복하려면 시뮬레이터 재시작"], C["red"]),
               ("nothing is held", ["place 만 보냈다 → pick 먼저"], C["yellow"]),
               ("액션 거부", ["이전 실행이 남아 있다 → cleanup_ros.sh"], C["orange"]),
               ("skills.yaml", ["도킹 거리 · 파지 높이 · 슬롯 오프셋", "src/warehouse_skills/config"], C["grey"])],
          cols=4, y_top=1.8, h=1.5, gap=0.25, tfs=10.5, fs=8.8)
    save(fig, "setup_pick_cautions.png")


# ================================================================ 6-1. module -> simulator -> command
def modules():
    fig, ax = fig_ax(14, 5.6)
    note(ax, 0.3, 5.3, "모듈별: 띄우는 시뮬레이터 → 실행 명령", bold=True, fs=12)
    tiles(ax, [("② 브리지 · ④ 센서", ["drive", "teleop", "examples/m1_ros_vision/02_scan_odom_subscriber.py"], C["blue"]),
               ("③ Robot Description", ["display", "ros2 run tf2_tools view_frames"], C["blue"]),
               ("⑤ SLAM", ["slam", "teleop 로 한 바퀴 → 지도 저장"], C["yellow"]),
               ("⑥ Nav2", ["nav", "goal X Y YAW · RViz 2D Goal"], C["yellow"]),
               ("⑦ MoveIt · ⑧ EE 제어", ["moveit", "arm both ready", "lessons/05_moveit/ee_control.py demo"], C["green"]),
               ("⑨ Pick & Place", ["start spawn:=pick_table", "lessons/06_pick_place/pick_then_place.py red"], C["green"]),
               ("⑩ 통합 운반", ["start locate:=vision", "pick red"], C["green"]),
               ("⑪ LMM", ["시뮬레이터 불필요", "examples/m3_llm/04_openai_hello.py", "m4 …/02_nl_to_command.py · m5 …/02_nl_to_plan.py"], C["red"]),
               ("⑫ Task Pipeline · ⑭ Final Mission", ["start locate:=vision", "ros2 run warehouse_lecture task_manager", "examples/m5_task_plan/04_final_mission.py"], C["purple"])],
          cols=3, y_top=5.0, h=1.5, gap=0.25, tfs=10.5, fs=8.4)
    save(fig, "setup_modules.png")


# ================================================================ 6-2. lesson README structure
def lesson_readme():
    fig, ax = fig_ax(14, 2.6)
    note(ax, 0.3, 2.3, "각 lessons/NN/README.md 의 구성", bold=True, fs=12)
    chain(ax, ["목표", "실행", "화면에서 볼 것", "핵심 코드", "해 볼 것", "문제 해결"], y=0.5, h=1.2, gap=0.3,
          colors=[C["orange"], C["blue"], C["yellow"], C["purple"], C["green"], C["grey"]], tfs=10.5)
    save(fig, "setup_lesson_readme.png")


# ================================================================ 7. config files
def config_files():
    fig, ax = fig_ax(14, 5.4)
    note(ax, 0.3, 5.1, "자주 수정하는 설정 (src/ 아래) — YAML만 바꾸면 재시작으로 반영, 새 파일을 추가했으면 build", bold=True, fs=11.5)
    tiles(ax, [("mobile_openarm_mujoco/worlds", ["actors.yaml  사람 · 소품 배치 · 경로", "warehouse.yaml  랙 · 작업대 · 상자 · 마커"], C["green"]),
               ("mobile_openarm_mujoco/config", ["mujoco.yaml  물리 · 주행 제한"], C["green"]),
               ("mobile_openarm_description/config", ["cameras.yaml  카메라 위치 · FOV"], C["yellow"]),
               ("mobile_openarm_navigation/config", ["nav2.yaml  Nav2"], C["blue"]),
               ("mobile_openarm_moveit_config/config", ["*.yaml  MoveIt"], C["blue"]),
               ("warehouse_skills/config", ["skills.yaml  운반 스킬"], C["orange"]),
               ("warehouse_lecture/worlds", ["locations.yaml  장소 이름 · 순찰 경로"], C["purple"]),
               ("warehouse_lecture/config", ["llm.yaml  OpenAI 모델 (키는 .env)"], C["red"])],
          cols=3, y_top=4.8, h=1.4, gap=0.25, tfs=10.5, fs=8.6)
    save(fig, "setup_config_files.png")


# ================================================================ 8. troubleshooting
def trouble_env():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "실행 환경 문제: 증상 → 원인 → 조치", bold=True, fs=12)
    tiles(ax, [("ros2 CLI에 아무것도 안 보임", ["원인: env.sh 미적용 · wrapper 없이 실행", "조치: source scripts/env.sh 또는 mobile_openarm exec ros2 …", "토픽이 2개만 보이면 ros2 daemon stop 후 다시"], C["blue"]),
               ("액션 거부 · Nav2 없음 · 노드 중복", ["원인: 이전 실행 프로세스가 남아 있음", "조치: ./scripts/cleanup_ros.sh → 다시 start"], C["yellow"]),
               ("bridge가 ModuleNotFoundError: mujoco 로 죽음", ["원인: 가상환경 없이 ros2 launch 직접 실행", "조치: wrapper (./scripts/mobile_openarm start) 사용"], C["red"]),
               ("zsh에서 setup.bash 오류", ["원인: ROS 스크립트는 셸별 파일이 있다", "조치: source /opt/ros/jazzy/setup.zsh"], C["grey"])],
          cols=2, y_top=3.8, h=1.6, gap=0.3, tfs=10.5, fs=8.6)
    save(fig, "setup_trouble_env.png")


def trouble_run():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "동작 · 성능 · 키 문제: 증상 → 원인 → 조치", bold=True, fs=12)
    tiles(ax, [("numpy.dtype size changed", ["원인: 가상환경에 numpy 2 가 들어감", "조치: pip install \"numpy<2\"", "→ rm -rf build/warehouse_interfaces install/warehouse_interfaces → build"], C["red"]),
               ("화면이 느림", ["원인: RViz · 뷰어 · 카메라 렌더 부하", "조치: rviz:=false, 필요하면 viewer:=false", "카메라 기본이 2대 320×240 2 FPS 인지 확인 (profile:=lite)"], C["yellow"]),
               ("command_executor 와 task_manager 동시 실행", ["원인: 둘 다 /execute_command 를 서비스", "조치: 하나만 띄운다", "시뮬레이터를 다시 띄우면 task_manager 도 다시"], C["blue"]),
               ("OpenAI 429 insufficient_quota", ["원인: 키의 크레딧 · 사용 한도 소진", "조치: 강사에게 문의", "LMM 이전 모듈은 키 없이 진행"], C["orange"])],
          cols=2, y_top=3.8, h=1.6, gap=0.3, tfs=10.5, fs=8.6)
    save(fig, "setup_trouble_run.png")


if __name__ == "__main__":
    for f in (env_cards, ros2_packages, install_script, install_script_detail, openai_signup, openai_key, env_sh, env_sh_detail, install_check, commands, launch_args, combos,
              locations, table_side, actors, interfaces, pick_examples, pick_cautions, modules, lesson_readme, config_files,
              trouble_env, trouble_run):
        f()
