"""Operate the MuJoCo viewer UI with the mouse, record the screen, and write a captioned GIF.

The viewer (python -m mujoco.viewer --mjcf=...) must already be open at 1400 x 900 and on top.
  python3 docs/camp/record_viewer_ui.py <window id> <scenario> <work folder>
Scenarios are the functions at the bottom (coordinates are window pixels of the 1400 x 900 viewer).
Output: docs/camp/intro_mj_<scenario>.gif  (+ <work folder>/<scenario>.mp4 and timeline json)
"""
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS, OUT_W = 1400, 900, 6, 860
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"


def sh(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


class Recorder:
    def __init__(self, win, name, work):
        self.win, self.name, self.work = win, name, Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        info = sh("xwininfo", "-id", win)
        self.x0 = int(info.split("Absolute upper-left X:")[1].split()[0])
        self.y0 = int(info.split("Absolute upper-left Y:")[1].split()[0])
        self.timeline, self.pos = [], (700, 450)
        sh("xdotool", "windowactivate", win)
        time.sleep(0.6)
        self.mouse(*self.pos)
        self.mp4 = self.work / f"{name}.mp4"
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-framerate", "20", "-draw_mouse", "1",
                                    "-video_size", f"{W}x{H}", "-i", f":1+{self.x0},{self.y0}", "-c:v", "libx264", "-qp", "0",
                                    "-preset", "ultrafast", str(self.mp4)], stdin=subprocess.PIPE)
        time.sleep(1.2)                                   # ffmpeg start-up; captions begin after this
        self.t0 = time.monotonic() - 1.0

    def now(self):
        return time.monotonic() - self.t0

    def mouse(self, x, y):
        sh("xdotool", "mousemove", str(self.x0 + int(x)), str(self.y0 + int(y)))
        self.pos = (x, y)

    def cap(self, text, box=None):
        """Caption (and optional highlight box x0, y0, x1, y1) shown from now until the next cap()."""
        self.timeline.append({"t": self.now(), "text": text, "box": box})

    def wait(self, s):
        time.sleep(s)

    def glide(self, x, y, dur=0.6):
        (sx, sy), n = self.pos, max(2, int(dur / 0.03))
        for k in range(1, n + 1):
            self.mouse(sx + (x - sx) * k / n, sy + (y - sy) * k / n)
            time.sleep(0.03)

    def click(self, x, y, button=1, double=False):
        self.glide(x, y)
        time.sleep(0.25)
        sh("xdotool", "click", *(["--repeat", "2", "--delay", "120"] if double else []), str(button))
        time.sleep(0.3)

    def drag(self, x0, y0, x1, y1, dur=1.5, button=1, hold=0.2):
        self.glide(x0, y0)
        time.sleep(0.25)
        sh("xdotool", "mousedown", str(button))
        time.sleep(0.15)
        self.glide(x1, y1, dur)
        time.sleep(hold)
        sh("xdotool", "mouseup", str(button))
        time.sleep(0.2)

    def sweep(self, y, xs, dur=1.2, button=1):
        """Press at xs[0] and visit the other xs without releasing (one slider, several values)."""
        self.glide(xs[0], y)
        time.sleep(0.25)
        sh("xdotool", "mousedown", str(button))
        for x in xs[1:]:
            self.glide(x, y, dur)
            time.sleep(0.5)
        sh("xdotool", "mouseup", str(button))
        time.sleep(0.2)

    def key(self, k):
        sh("xdotool", "key", k)
        time.sleep(0.3)

    def keydown(self, k):
        sh("xdotool", "keydown", k)

    def keyup(self, k):
        sh("xdotool", "keyup", k)

    def finish(self):
        self.cap("", None)
        time.sleep(0.3)
        self.ff.communicate(b"q")
        (self.work / f"{self.name}.json").write_text(json.dumps(self.timeline, ensure_ascii=False))
        make_gif(self.mp4, self.timeline, Path("docs/camp") / f"intro_mj_{self.name}.gif", self.work / self.name)


def make_gif(mp4, timeline, out, frame_dir):
    frame_dir.mkdir(parents=True, exist_ok=True)
    for f in frame_dir.glob("*.png"):
        f.unlink()
    sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"fps={FPS},scale={OUT_W}:-1:flags=lanczos", str(frame_dir / "%04d.png"))
    scale, bar = OUT_W / W, 52
    f_cap, f_no = ImageFont.truetype(BOLD, 21), ImageFont.truetype(BOLD, 18)
    end = timeline[-1]["t"]
    frames = []
    for i, path in enumerate(sorted(frame_dir.glob("*.png"))):
        t = i / FPS
        if t < timeline[0]["t"] or t > end:
            continue
        k = max(j for j, e in enumerate(timeline) if e["t"] <= t)
        e = timeline[k]
        src = Image.open(path).convert("RGB")
        img = Image.new("RGB", (src.width, src.height + bar), "#111111")
        img.paste(src, (0, 0))
        d = ImageDraw.Draw(img)
        if e["box"]:
            x0, y0, x1, y1 = (v * scale for v in e["box"])
            for off in (0, 1, 2):
                d.rectangle((x0 - off, y0 - off, x1 + off, y1 + off), outline="#FFD400")
        badge = f"{k + 1}/{len(timeline) - 1}"
        d.rounded_rectangle((10, src.height + 12, 22 + d.textlength(badge, font=f_no), src.height + 46), 7, fill="#FFD400")
        d.text((16, src.height + 16), badge, fill="#111111", font=f_no)
        d.text(((src.width - d.textlength(e["text"], font=f_cap)) / 2, src.height + 15), e["text"], fill="white", font=f_cap)
        frames.append(img)
    pal = frames[len(frames) // 2].quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    q[0].save(out, save_all=True, append_images=q[1:], duration=round(1000 / FPS), loop=0, optimize=False)
    print("saved", out, len(frames), "frames", f"{len(frames) / FPS:.1f} s", f"{out.stat().st_size / 1e6:.1f} MB")
    for n in (len(frames) // 3, 2 * len(frames) // 3, len(frames) - 1):
        frames[n].save(frame_dir.parent / f"{frame_dir.name}_check{n}.png")


# ---- viewer layout (window pixels, 1400 x 900, default panels) ---------------------------------
PAUSE, RUN, RESET = (67, 427), (187, 427), (67, 457)
KEY_ROW, LOAD_KEY = (132, 504, 244, 530), (67, 547)
CONTROL_HEAD, JOINT_HEAD = (1257, 55), (1257, 21)
SIM_BOX = (8, 384, 248, 688)


def ctrl_row(i):
    """Row i (0-based) of the Control panel when it is the only expanded panel on the right."""
    y = 115 + 30 * i
    return y, (1140, y - 14, 1376, y + 14)


def slider_x(value, lo, hi):
    return 1262 + (1372 - 1262) * (value - lo) / (hi - lo)


# ---- scenarios -------------------------------------------------------------------------------
def panda_key(r):
    """Fresh viewer with franka_emika_panda/scene.xml: load the keyframe 'home'."""
    r.cap("처음: 관절이 모두 0 인 자세로 서 있다"); r.wait(2.0)
    r.cap("Simulation › Key 칸을 끌어 0 번 키프레임을 고른다", KEY_ROW)
    r.drag(140, 517, 200, 517, dur=0.8); r.wait(0.8)
    r.cap("Load key 를 누르면 저장된 자세 'home' 으로 바뀐다", (10, 534, 126, 560))
    r.click(*LOAD_KEY); r.wait(2.5)
    r.cap("Reset 을 누르면 처음 자세로 돌아간다", (10, 444, 126, 470))
    r.click(*RESET); r.wait(2.0)
    r.cap("다시 Load key → home 자세", (10, 534, 126, 560))
    r.click(*LOAD_KEY); r.wait(2.0)


def panda_control(r):
    """Panda at 'home' with the Control panel collapsed: move joints with the Control sliders."""
    r.cap("오른쪽 Control 을 눌러 펼친다 (액추에이터마다 슬라이더 하나)", (1138, 42, 1378, 68))
    r.click(*CONTROL_HEAD); r.wait(1.5)
    y, box = ctrl_row(0)
    r.cap("actuator1 슬라이더 → 맨 아래 관절이 돌아 팔 전체가 회전", box)
    r.sweep(y, [slider_x(0, -2.9, 2.9), slider_x(1.3, -2.9, 2.9), slider_x(-1.3, -2.9, 2.9), slider_x(0, -2.9, 2.9)]); r.wait(1.0)
    y, box = ctrl_row(3)
    r.cap("actuator4 슬라이더 → 팔꿈치가 펴졌다 굽는다", box)
    r.sweep(y, [slider_x(-1.57, -3.07, -0.07), slider_x(-0.5, -3.07, -0.07), slider_x(-2.6, -3.07, -0.07), slider_x(-1.57, -3.07, -0.07)]); r.wait(1.0)
    y, box = ctrl_row(7)
    r.cap("actuator8 슬라이더 → 그리퍼가 닫혔다 열린다", box)
    r.sweep(y, [1370, 1264, 1370], dur=1.4); r.wait(1.2)
    r.cap("슬라이더 값 = 위치 액추에이터의 목표 각 (data.ctrl)", (1138, 42, 1378, 340)); r.wait(2.5)


def panda_push(r):
    """Panda at 'home', simulation running: select a body and push it with the mouse."""
    r.cap("링크를 더블클릭하면 선택된다", None)
    r.click(880, 262, double=True); r.wait(1.2)
    r.cap("Ctrl 을 누른 채 오른쪽 버튼으로 끌면 힘으로 민다", None)
    r.keydown("ctrl")
    r.drag(880, 262, 1000, 380, dur=1.5, button=3, hold=1.2)
    r.keyup("ctrl"); r.wait(0.3)
    r.cap("놓으면 위치 액추에이터가 원래 목표로 되돌린다", None); r.wait(2.5)
    r.cap("빈 곳에서 왼쪽 끌기 = 시점 회전 · 휠 = 확대 · 축소", None)
    r.drag(500, 700, 620, 660, dur=1.2); r.wait(0.3)
    r.drag(620, 660, 500, 700, dur=1.2); r.wait(0.8)


def go2_run(r):
    """Fresh viewer with unitree_go2/scene.xml (robot already collapsed): pause, load key, run."""
    r.cap("Go2: 토크 액추에이터 12 개 · 제어기가 없어 주저앉아 있다"); r.wait(2.5)
    r.cap("Pause 를 눌러 시뮬레이션을 멈춘다 (Space 키와 같음)", (10, 414, 126, 440))
    r.click(*PAUSE); r.wait(1.0)
    r.cap("Key 를 0 으로 하고 Load key → 'home' 자세로 서 있다 (멈춘 상태)", (10, 504, 246, 560))
    r.drag(140, 517, 200, 517, dur=0.8); r.wait(0.4)
    r.click(*LOAD_KEY); r.wait(2.5)
    r.cap("Run 을 누르면 물리가 다시 돈다 → 붙잡는 힘이 없어 주저앉는다", (128, 414, 244, 440))
    r.click(*RUN); r.wait(4.0)
    r.cap("버티게 하려면 제어기가 토크를 계속 넣어야 한다", None); r.wait(2.5)


def go2_render(r):
    """Go2 collapsed on the floor, view zoomed in, left panels all folded except Rendering: switch visualisation flags."""
    r.cap("Rendering 을 펼치면 '무엇을 그릴지' 켜고 끄는 버튼이 나온다", (8, 178, 248, 840)); r.wait(2.5)
    r.cap("Contact Force → 바닥이 로봇을 받치는 힘이 화살표로 보인다", (12, 602, 126, 628))
    r.click(67, 615); r.wait(2.5)
    r.cap("Transparent → 몸체가 반투명해진다", (12, 632, 126, 658))
    r.click(67, 645); r.wait(2.5)
    r.cap("Joint → 관절 축이 보인다", (12, 392, 126, 418))
    r.click(67, 405); r.wait(3.0)


def display_slider(r):
    """display.launch.py: RViz client area at the record origin (1090 x 900), joint_state_publisher_gui (290 x 900) right of it."""
    r.cap("오른쪽 창 = joint_state_publisher_gui · 관절마다 슬라이더 하나", (1100, 4, 1392, 896)); r.wait(2.5)
    r.cap("openarm_left_joint4 슬라이더 → 왼팔 팔꿈치가 굽는다", (1118, 428, 1340, 484))
    r.sweep(464, [1135, 1290, 1150, 1250], dur=1.5); r.wait(1.0)
    r.cap("openarm_left_joint1 슬라이더 → 왼쪽 어깨가 돈다", (1118, 227, 1340, 283))
    r.sweep(263, [1267, 1190, 1320, 1267], dur=1.5); r.wait(1.0)
    r.cap("슬라이더 값 → /joint_states → robot_state_publisher → /tf → RViz", None); r.wait(3.0)


SCENARIOS = {f.__name__: f for f in (panda_key, panda_control, panda_push, go2_run, go2_render, display_slider)}

if __name__ == "__main__":
    if sys.argv[1] == "--gif":                             # rebuild a GIF from an existing recording
        work, name = Path(sys.argv[3]), sys.argv[2]
        make_gif(work / f"{name}.mp4", json.loads((work / f"{name}.json").read_text()), Path("docs/camp") / f"intro_mj_{name}.gif", work / name)
    else:
        rec = Recorder(sys.argv[1], sys.argv[2], sys.argv[3])
        try:
            SCENARIOS[sys.argv[2]](rec)
        finally:
            subprocess.run(["xdotool", "keyup", "ctrl"]); subprocess.run(["xdotool", "mouseup", "1"]); subprocess.run(["xdotool", "mouseup", "3"])
            rec.finish()
