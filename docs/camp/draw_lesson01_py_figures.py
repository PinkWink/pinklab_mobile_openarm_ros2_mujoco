"""Figures for the lesson-01 page section "Python <-> MuJoCo" (how minimal_bridge.py talks to the mujoco library).
Output: docs/camp/lesson01_py_*.png. Helpers come from draw_intro_figures.py (orthogonal arrows only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from draw_intro_figures import C, INK, arrow, chain, fig_ax, flow_rows, label, note, rbox, save, tiles  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def overview():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "Python 코드가 MuJoCo 와 만나는 다섯 곳", bold=True, fs=12)
    tiles(ax, [("MjModel", ["from_xml_path(XML)", "모델 상수 · 바뀌지 않음", "nq · nu · timestep · 이름표"], C["green"]),
               ("MjData", ["MjData(model)", "현재 상태 · 매 스텝 변함", "time · qpos · xpos · ctrl"], C["teal"]),
               ("mj_step", ["mj_step(model, data)", "물리 한 스텝 = 2 ms", "루프마다 한 번"], C["yellow"]),
               ("Renderer", ["Renderer(model, 240, 320)", "오프스크린 카메라", "numpy 영상"], C["purple"]),
               ("viewer", ["launch_passive(model, data)", "화면 창 · 선택 사항", "루프마다 sync()"], C["grey"])],
          cols=5, y_top=3.7, gap=0.25, h=2.2, tfs=11.5, fs=8.6)
    note(ax, 0.3, 0.9, "ROS 2 쪽 코드는 이 다섯에서 값을 읽어 토픽으로 내고 (→ /clock /joint_states /tf /image_raw),", fs=9.5)
    note(ax, 0.3, 0.45, "/cmd 로 받은 값을 data.ctrl 에 쓴다 (←).  import mujoco 하나로 전부 쓴다.", fs=9.5)
    save(fig, "lesson01_py_overview.png")


def model():
    fig, ax = fig_ax(14, 3.8)
    note(ax, 0.3, 3.5, "MjModel.from_xml_path: XML → 모델 상수", bold=True, fs=12)
    chain(ax, [("two_link_arm.xml", ["MJCF 텍스트"]), ("from_xml_path()", ["읽고 컴파일", "한 번만"]),
               ("MjModel", ["nq = 2 · nu = 2", "opt.timestep = 0.002", "actuator_ctrlrange"]), ("이름표", ["joint(\"joint1\")", "body(\"link1\")", "camera \"tip_camera\""])],
          y=0.8, h=2.1, colors=[C["grey"], C["yellow"], C["green"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.35, "프로그램 내내 바뀌지 않는다.  브리지는 nu 로 /cmd 길이를 확인하고 ctrlrange 로 값을 자른다.", fs=9.5)
    save(fig, "lesson01_py_model.png")


def data():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "MjData(model): 현재 상태 · mj_step 마다 바뀐다", bold=True, fs=12)
    ax.add_patch(Rectangle((0.3, 0.9), 13.4, 2.9, fc="#EEF8F7", ec="#5FA8A0", lw=1.3, zorder=1))
    note(ax, 0.5, 3.55, "data", bold=True, fs=11, color="#2a6f68")
    tiles(ax, [("time", ["시뮬레이션 시각 (초)", "→ stamp() · /clock"], C["green"]), ("qpos · qvel", ["관절 각 · 각속도", "→ /joint_states"], C["green"]),
               ("xpos · xquat", ["body 위치 · 자세 (월드)", "→ /tf"], C["green"]), ("(렌더 입력)", ["update_scene(data)", "→ /tip_camera/image_raw"], C["green"]),
               ("ctrl", ["액추에이터 목표 [q1, q2]", "← /cmd (브리지가 쓴다)"], C["orange"])],
          cols=5, x0=0.5, y_top=3.3, gap=0.25, h=1.9, tfs=11, fs=8.4)
    note(ax, 0.3, 0.45, "초록 넷은 브리지가 읽기만 한다.  주황 하나만 브리지가 쓴다.  모두 numpy 배열이라 복사 없이 바로 본다.", fs=9.5)
    save(fig, "lesson01_py_data.png")


def step():
    fig, ax = fig_ax(14, 4.6)
    note(ax, 0.3, 4.3, "mj_step(model, data): 물리 한 스텝 (2 ms) 안에서 일어나는 일", bold=True, fs=12)
    flow_rows(ax, [("data.ctrl 읽기", "액추에이터 목표"), ("액추에이터 힘", "kp · (ctrl - q)"), ("중력 · 감쇠 · 접촉", "바닥 · 상자와의 접촉력"),
                   ("적분", "가속도 → 속도 → 위치"), ("qpos · qvel 갱신", "관절 상태"), ("xpos · xquat · time 갱신", "body 자세 · time += 0.002")],
              per_row=3, y_top=3.9, h=1.3, gap=0.3, row_gap=0.55, colors=[C["orange"], C["yellow"], C["yellow"], C["grey"], C["green"], C["green"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.3, "부르지 않으면 세계가 멈춘다.  뷰어는 물리를 돌리지 않는다 — 스텝은 우리 루프가 돌린다.", fs=9.5)
    save(fig, "lesson01_py_step.png")


def names():
    fig, ax = fig_ax(14, 4.4)
    note(ax, 0.3, 4.1, "model.joint() · model.body(): 이름 → 배열 번호", bold=True, fs=12)
    chain(ax, [("\"joint1\"", ["XML 의 name"]), ("model.joint(\"joint1\")", ["관절 정보"]), (".qposadr[0]  ·  .dofadr[0]", ["qpos 번호 · qvel 번호"]), ("data.qpos[i] · data.qvel[j]", ["각 · 각속도"])],
          y=2.35, h=1.35, colors=[C["grey"], C["green"], C["yellow"], C["teal"]], tfs=10.5, fs=8.6)
    chain(ax, [("\"link1\"", ["XML 의 name"]), ("model.body(\"link1\")", ["body 정보"]), (".id", ["행 번호"]), ("data.xpos[id] · data.xquat[id]", ["월드 위치 · 자세"])],
          y=0.6, h=1.35, colors=[C["grey"], C["green"], C["yellow"], C["teal"]], tfs=10.5, fs=8.6)
    save(fig, "lesson01_py_names.png")


def renderer():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "Renderer: 창 없이 카메라 영상을 그린다", bold=True, fs=12)
    chain(ax, [("Renderer(model, 240, 320)", ["__init__ 에서 한 번", "offwidth × offheight 안"]), ("update_scene(data, camera=…)", ["camera=\"tip_camera\"", "현재 상태로 장면 갱신 · 5 Hz"]),
               ("render()", ["numpy (240, 320, 3) uint8"]), ("Image 메시지", ["→ /tip_camera/image_raw"])],
          y=1.1, h=1.9, colors=[C["purple"], C["purple"], C["yellow"], C["blue"]], tfs=10, fs=8.6)
    note(ax, 0.3, 0.5, "viewer 와 별개다.  --viewer 없이도 돈다.  GPU 가 없어도 된다.", fs=9.5)
    save(fig, "lesson01_py_renderer.png")


def viewer():
    fig, ax = fig_ax(14, 4.0)
    note(ax, 0.3, 3.7, "viewer.launch_passive: 같은 model · data 를 보는 창", bold=True, fs=12)
    chain(ax, [("launch_passive(model, data)", ["창을 연다", "--viewer 일 때만"]), ("우리 루프", ["mj_step · 발행 · spin_once"]),
               ("viewer.sync()", ["루프마다 한 번", "창이 새 상태를 그린다"]), ("is_running()", ["창을 닫으면 False", "→ 루프 종료"])],
          y=1.1, h=1.9, colors=[C["grey"], C["purple"], C["grey"], C["red"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.5, "passive = 창은 보기만 한다.  물리를 돌리는 쪽은 우리 루프다.", fs=9.5)
    save(fig, "lesson01_py_viewer.png")


def realtime():
    fig, ax = fig_ax(14, 4.2)
    note(ax, 0.3, 3.9, "실시간 맞추기: 시뮬레이션 시각을 벽시계에 붙인다", bold=True, fs=12)
    chain(ax, [("mj_step", ["t = data.time", "2 ms 앞으로"]), ("lag = wall0 + t - now", ["시뮬레이션이 벽시계보다", "앞선 양 (초)"]),
               ("lag > 0", ["time.sleep(lag)", "벽시계를 기다린다"]), ("lag ≤ 0", ["자지 않고 계속", "실시간 비율 < 1"])],
          y=1.2, h=2.0, colors=[C["yellow"], C["grey"], C["green"], C["red"]], tfs=10.5, fs=8.6)
    note(ax, 0.3, 0.55, "mj_step 은 2 ms 시뮬레이션을 훨씬 빨리 끝낸다.  sleep 을 빼면 세계가 CPU 가 허용하는 만큼 빨리 감긴다.", fs=9.5)
    save(fig, "lesson01_py_realtime.png")


if __name__ == "__main__":
    for f in (overview, model, data, step, names, renderer, viewer, realtime):
        f()
