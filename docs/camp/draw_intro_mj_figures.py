"""Figures for the page "MuJoCo 소개" (viewer tour with two Menagerie robots). Output: docs/camp/intro_mj_*.png

  python3 docs/camp/draw_intro_mj_figures.py [capture folder]      # run from the workspace root
The capture folder (artifacts/dev/intro: viewer screenshots and logs) is needed for the annotated screenshots and
terminal renders. The GIFs are made by record_viewer_ui.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, OUT, arrow, chain, fig_ax, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

BLUE, GREEN, PURPLE, BROWN = "#1f4e79", "#2e7d32", "#5e4b8b", "#7a4b00"


def what():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "MuJoCo = Multi-Joint dynamics with Contact", bold=True, fs=12)
    tiles(ax, [("무엇", ["관절로 이어진 물체와 접촉을", "빠르고 안정적으로 푸는 물리 엔진"], C["green"]),
               ("누가", ["Emo Todorov 가 개발 (Roboti)", "2021 DeepMind 인수 · 2022 오픈소스"], C["blue"]),
               ("어디에", ["로봇 제어 · 강화학습 연구", "조작 · 보행처럼 접촉이 많은 문제"], C["yellow"]),
               ("어떻게", ["C 라이브러리 + Python 바인딩", "pip install mujoco 한 줄"], C["purple"])],
          cols=4, y_top=3.9, gap=0.25, h=1.5, tfs=11.5, fs=8.8)
    chain(ax, [("모델 (MJCF · URDF)", ["XML 파일 하나"]), ("mj_step", ["물리 한 스텝"]), ("상태 (qpos · 접촉 …)", ["numpy 배열로 바로 읽음"]), ("뷰어 · 렌더러", ["화면 · 카메라 영상"])],
          y=0.9, h=1.05, colors=[C["grey"], C["green"], C["teal"], C["purple"]], tfs=10.5, fs=8.8)
    note(ax, 0.3, 0.4, "라이선스 Apache 2.0.  시뮬레이터 '프로그램' 이라기보다 내 코드에서 부르는 '라이브러리' 다.", fs=9.5)
    save(fig, "intro_mj_what.png")


def package():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "pip install mujoco 에 들어 있는 것", bold=True, fs=12)
    tiles(ax, [("물리 엔진", ["MjModel · MjData", "mj_step · mj_forward"], C["green"]),
               ("뷰어", ["python -m mujoco.viewer", "이 글에서 쓰는 창"], C["blue"]),
               ("렌더러", ["mujoco.Renderer", "창 없이 카메라 영상"], C["purple"]),
               ("모델 편집", ["mujoco.MjSpec", "코드로 모델 고치기"], C["yellow"]),
               ("(별도) MJX", ["pip install mujoco-mjx", "GPU 로 수천 개 병렬"], C["grey"])],
          cols=5, y_top=2.9, gap=0.22, h=1.45, tfs=11, fs=8.6)
    note(ax, 0.3, 0.85, "로봇 모델은 들어 있지 않다 → 아래에서 MuJoCo Menagerie 를 받는다.", fs=9.5)
    note(ax, 0.3, 0.42, "이 과정의 설치 스크립트가 이미 mujoco 를 설치했다 (source scripts/env.sh 뒤 바로 사용).", fs=9.5)
    save(fig, "intro_mj_package.png")


def compare():
    fig, ax = fig_ax(14, 7.7)
    note(ax, 0.3, 7.4, "Gazebo · MuJoCo · Isaac Sim", bold=True, fs=12)
    cols = [("Gazebo (gz-sim)", C["yellow"]), ("MuJoCo", C["green"]), ("Isaac Sim", C["blue"])]
    rows = [("만든 곳", ["Open Robotics (OSRF)", "Google DeepMind", "NVIDIA (Omniverse)"]),
            ("물리", ["엔진 교체형 · 기본 DART", "자체 엔진 · 부드러운 접촉", "PhysX · GPU 가속"]),
            ("화면", ["OGRE 렌더 · 센서 플러그인", "내장 OpenGL · 단순하고 가벼움", "RTX 레이트레이싱 · 사실적"]),
            ("모델 형식", ["SDF (URDF 변환)", "MJCF (URDF 읽기 가능)", "USD (URDF 가져오기)"]),
            ("ROS 2 연결", ["ros_gz_bridge · gz_ros2_control", "브리지를 직접 작성 (이 과정)", "ROS 2 Bridge 확장 내장"]),
            ("필요한 PC", ["보통 · GUI 가 무거움", "노트북 CPU · 내장 그래픽", "RTX GPU 필수 · 고사양"]),
            ("강점", ["ROS 2 표준 · 예제가 가장 많음", "빠름 · 접촉 안정 · 코드가 다 보임", "사실적 영상 · 합성 데이터 · 대규모 학습"])]
    x0, lw, cw, top, rh = 0.3, 1.9, 3.83, 7.0, 0.72
    for j, (name, fc) in enumerate(cols):
        rbox(ax, x0 + lw + 0.1 + j * (cw + 0.1), top - 0.6, cw, 0.6, name, fc=fc, tfs=11.5)
    for i, (head, cells) in enumerate(rows):
        y = top - 0.6 - (i + 1) * (rh + 0.08)
        rbox(ax, x0, y, lw, rh, head, fc=C["grey"], tfs=10.5)
        for j, text in enumerate(cells):
            rbox(ax, x0 + lw + 0.1 + j * (cw + 0.1), y, cw, rh, text, fc="#FFFFFF" if j != 1 else "#F4FBF4", tfs=9.2, lw=1.0)
    note(ax, 0.3, 0.3, "셋 다 '틀린 것' 이 없다.  무엇을 대신 해 주는가 · 어떤 PC 가 필요한가가 다르다.", fs=9.5)
    save(fig, "intro_mj_compare.png")


def when():
    fig, ax = fig_ax(14, 3.6)
    note(ax, 0.3, 3.3, "언제 무엇을 고르나", bold=True, fs=12)
    tiles(ax, [("Gazebo", ["ROS 2 튜토리얼 · 패키지를 그대로 쓸 때", "센서 플러그인 · 월드가 이미 있을 때", "ros2_control 을 실물과 똑같이 쓸 때"], C["yellow"]),
               ("MuJoCo", ["집기 · 보행처럼 접촉이 중요한 작업", "제어 · 강화학습을 빠르게 반복할 때", "저사양 PC · 수업 · 코드를 다 보고 싶을 때"], C["green"]),
               ("Isaac Sim", ["사실적인 카메라 영상이 필요할 때", "합성 데이터 · 디지털 트윈", "RTX GPU 로 대규모 병렬 학습 (Isaac Lab)"], C["blue"])],
          cols=3, y_top=2.9, gap=0.3, h=1.75, tfs=11.5, fs=8.8)
    note(ax, 0.3, 0.55, "이 과정: 저사양 노트북 60 ~ 80 대 · 파지 안정 · 연결 코드를 직접 읽기 → MuJoCo.", fs=9.5)
    save(fig, "intro_mj_when.png")


def menagerie():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "MuJoCo Menagerie: DeepMind 가 관리하는 로봇 모델 모음", bold=True, fs=12)
    tiles(ax, [("로봇 팔 · 손", ["Franka Panda · UR5e · KUKA iiwa", "Shadow Hand · Robotiq 그리퍼"], C["blue"]),
               ("4 족 · 휴머노이드", ["Unitree Go2 · Spot · ANYmal", "Unitree H1 · G1 · Apollo"], C["green"]),
               ("그 밖에", ["드론 · 모바일 매니퓰레이터", "ALOHA · Stretch · TidyBot"], C["yellow"])],
          cols=3, y_top=3.9, gap=0.3, h=1.4, tfs=11, fs=8.8)
    chain(ax, [("<로봇>/<로봇>.xml", ["로봇만 (body · joint · actuator)"]), ("<로봇>/scene.xml", ["로봇 + 바닥 · 빛 (이걸 연다)"]), ("<로봇>/assets/", ["mesh 파일"])],
          y=1.0, h=1.05, colors=[C["grey"], C["orange"], C["grey"]], tfs=10.5, fs=8.8, arrows=False)
    note(ax, 0.3, 0.45, "모델 약 70 종 · 내려받은 크기 약 2.5 GB.  python -m mujoco.viewer --mjcf=<로봇>/scene.xml 로 연다.", fs=9.5)
    save(fig, "intro_mj_menagerie.png")


def panels():
    fig, ax = fig_ax(14, 5.0)
    note(ax, 0.3, 4.7, "뷰어 패널: 왼쪽 = 시뮬레이션과 보기 · 오른쪽 = 로봇 조작", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 0.9), 8.6, 3.5, fc="#F3F7FF", ec="#8FAADC", lw=1.3, zorder=1))
    ax.add_patch(Rectangle((9.2, 0.9), 4.5, 3.5, fc="#F5F1FB", ec="#9C8BC9", lw=1.3, zorder=1))
    note(ax, 0.5, 4.15, "왼쪽 패널", bold=True, fs=11, color=BLUE); note(ax, 9.4, 4.15, "오른쪽 패널", bold=True, fs=11, color=PURPLE)
    left = [("File", "저장 · 화면 캡처 · 종료"), ("Option", "도움말 · 정보 · 글자 크기"), ("Simulation", "Pause · Run · Load key"), ("Watch", "값 하나 지켜보기"),
            ("Physics", "중력 · 스텝 · 적분기"), ("Rendering", "그릴 것 켜고 끄기"), ("Visualization", "화살표 크기 · 색"), ("Group enable", "geom 그룹 보이기")]
    for i, (t, sub) in enumerate(left):
        r, c = divmod(i, 4)
        rbox(ax, 0.5 + c * 2.1, 2.55 - r * 1.45, 1.95, 1.25, t, [sub], fc=C["blue"] if t not in ("Simulation", "Rendering") else C["orange"], tfs=10, fs=7.9)
    right = [("Joint", "관절 값 직접 (멈춘 상태)"), ("Control", "액추에이터 목표 · 슬라이더"), ("Equality", "구속 켜고 끄기")]
    for i, (t, sub) in enumerate(right):
        rbox(ax, 9.4, 3.05 - i * 1.02, 4.1, 0.9, t, [sub], fc=C["purple"] if t != "Control" else C["orange"], tfs=10, fs=8.4)
    note(ax, 0.3, 0.45, "주황 = 이 글에서 직접 눌러 보는 곳.  제목 줄을 누르면 접히고 펼쳐진다.", fs=9.5)
    save(fig, "intro_mj_panels.png")


def keys():
    fig, ax = fig_ax(14, 4.9)
    note(ax, 0.3, 4.6, "마우스와 키: 이것만 알면 된다", bold=True, fs=12)
    tiles(ax, [("시점", ["왼쪽 끌기 = 회전", "오른쪽 끌기 = 이동 · 휠 = 확대"], C["blue"]),
               ("고르기", ["더블클릭 = body 선택", "Esc = 자유 시점으로"], C["blue"]),
               ("밀기", ["Ctrl + 오른쪽 끌기 = 힘", "Ctrl + 왼쪽 끌기 = 회전력"], C["orange"]),
               ("시간", ["Space = 멈춤 · 재생", "→ = 멈춘 상태에서 한 스텝"], C["green"]),
               ("패널", ["Tab = 왼쪽 패널 숨김", "Shift + Tab = 오른쪽 패널"], C["grey"]),
               ("도움말", ["F1 = 단축키 목록", "F2 = 시뮬레이션 정보"], C["grey"])],
          cols=3, y_top=4.2, gap=0.3, h=1.45, tfs=11, fs=9)
    note(ax, 0.3, 0.45, "밀기는 재생 중에만 힘이 들어간다.  뷰어의 F1 화면이 원본이다 (아래 캡처).", fs=9.5)
    save(fig, "intro_mj_keys.png")


def two_robots():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "두 로봇의 차이: 액추에이터가 무엇을 받는가", bold=True, fs=12)
    for x, name, fc, kind, slider, result in ((0.3, "Franka Panda", C["blue"], "위치 액추에이터 8 개", "슬라이더 = 목표 각", "스스로 자세를 유지"),
                                              (7.15, "Unitree Go2", C["green"], "토크 액추에이터 12 개", "슬라이더 = 토크", "제어기가 없으면 주저앉음")):
        rbox(ax, x, 2.6, 6.55, 1.2, name, [kind], fc=fc, tfs=11.5, fs=9.4)
        rbox(ax, x, 1.0, 3.1, 1.2, slider, ["data.ctrl 에 들어가는 값"], fc=C["orange"], tfs=10.5, fs=8.6)
        rbox(ax, x + 3.45, 1.0, 3.1, 1.2, result, ["Load key 뒤 Run 했을 때"], fc=C["grey"], tfs=10.5, fs=8.6)
        arrow(ax, (x + 1.55, 2.6), (x + 1.55, 2.2)); arrow(ax, (x + 3.1, 1.6), (x + 3.45, 1.6))
    note(ax, 0.3, 0.45, "둘 다 '누가 data.ctrl 을 채우는가' 의 문제다.  뷰어에서는 사람이, 다음 글부터는 ROS 2 노드가 채운다.", fs=9.5)
    save(fig, "intro_mj_two_robots.png")


def captures(cap):
    from PIL import Image, ImageDraw, ImageFont
    bold = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
    f_big = ImageFont.truetype(bold, 30)
    for src, dst in (("panda0.png", "intro_mj_panda_open.png"), ("go2_0.png", "intro_mj_go2_open.png"), ("go2_help.png", "intro_mj_help.png")):
        Image.open(cap / src).convert("RGB").save(OUT / dst); print("saved", dst)
    # screen layout: the Panda screenshot with three labelled regions
    img = Image.open(cap / "panda1.png").convert("RGB")
    d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1), color, text, tx, ty in (((3, 3, 252, 862), "#FFD400", "① 왼쪽 패널", 290, 20), ((272, 3, 1128, 896), "#4FC3F7", "② 3D 화면", 290, 840),
                                                  ((1133, 3, 1396, 380), "#FF8A65", "③ 오른쪽 패널", 890, 20)):
        for off in range(4):
            d.rectangle((x0 - off, y0 - off, x1 + off, y1 + off), outline=color)
        w = d.textlength(text, font=f_big)
        d.rounded_rectangle((tx - 8, ty - 4, tx + w + 8, ty + 40), 8, fill=color)
        d.text((tx, ty), text, fill="#111111", font=f_big)
    img.save(OUT / "intro_mj_layout.png"); print("saved intro_mj_layout.png")


def terminals(cap):
    from render_terminal import render
    out = lambda name, lines, **kw: (render(lines, str(OUT / name), **kw), print("saved", name))
    listing = [("out", l.rstrip()) for l in (cap / "ls_all.log").read_text().expandtabs(8).splitlines()]
    out("intro_mj_t_clone.png", [("prompt", "git clone --depth 1 https://github.com/google-deepmind/mujoco_menagerie.git ~/mujoco_menagerie"),
                                 ("out", "Cloning into '/home/pw/mujoco_menagerie'..."), ("out", "Updating files: 100% (3313/3313), done."),
                                 ("prompt", "ls ~/mujoco_menagerie/unitree_go2")]
        + [("out", "  ".join((cap / "ls_go2.log").read_text().split()))], highlight=("scene.xml",))
    out("intro_mj_t_list.png", [("prompt", "ls -d ~/mujoco_menagerie/*/ | xargs -n1 basename | column -c 110")] + listing)


if __name__ == "__main__":
    for f in (what, package, compare, when, menagerie, panels, keys, two_robots):
        f()
    if len(sys.argv) > 1:
        captures(Path(sys.argv[1])); terminals(Path(sys.argv[1]))
