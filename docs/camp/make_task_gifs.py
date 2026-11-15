"""Captioned GIFs for the lesson 07 - 15 pages, from runs recorded earlier (no simulator needed).

  MUJOCO_GL=egl python docs/camp/make_task_gifs.py [name ...]      # workspace root, venv python; no name = all
Robot scenes are offscreen MuJoCo renders of the recorded state (pick_record.py / arm_record.py pickles: joint states,
base pose, parcel poses) with a chase camera; the subtitle is the PickPlace feedback phase at that moment.
Screen GIFs (patrol, dashboards) are the screenshots saved while those pages were written.
"""
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from make_nav_gifs import captioned, write  # noqa: E402

DEV = Path("artifacts/dev")
BOLD = "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"
PHASE = {"start": "시작: 상자 위치를 보고 집을 팔을 고른다", "navigate_pick": "픽업 작업대 앞으로 이동", "dock": "도킹: ArUco 마커를 보며 작업대에 맞춘다",
         "locate": "카메라로 상자 위치를 찾는다", "pre_grasp": "집기 직전 자세로 팔을 뻗는다", "grasp": "그리퍼를 닫아 상자를 집는다",
         "lift": "들어 올린다", "carry": "운반 자세로 팔을 든다", "navigate_place": "적재 작업대 앞으로 이동",
         "place": "내려놓고 그리퍼를 연다", "retreat": "팔을 거두고 물러난다"}
CLOSE = {"dock", "locate", "pre_grasp", "grasp", "lift", "carry", "place", "retreat"}


def near(rows, t):
    lo, hi = 0, len(rows) - 1
    while lo < hi:                                       # rows are sorted by time
        mid = (lo + hi) // 2
        if rows[mid]["t"] < t:
            lo = mid + 1
        else:
            hi = mid
    return rows[lo]


class Replay:
    def __init__(self, run, w=720, h=405):
        import mujoco
        self.mj, self.run = mujoco, run
        self.m = mujoco.MjModel.from_xml_path("artifacts/mobile_generated/warehouse.xml")
        self.d = mujoco.MjData(self.m)
        self.r = mujoco.Renderer(self.m, h, w)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[1] = 0                         # hide collision geoms
        self.cam = mujoco.MjvCamera()
        self.az = None
        self.base = self.m.joint("floating_base").qposadr[0]

    def set(self, t):
        m, d, run = self.m, self.d, self.run
        s = near(run["states"], t)
        for n, q in zip(s["names"], s["positions"]):
            try:
                d.qpos[m.joint(n).qposadr[0]] = q
            except KeyError:
                pass
        a = self.base
        if "base" in run:
            p = near(run["base"], t)["pose"]
            d.qpos[a:a + 2] = p[:2]
            d.qpos[a + 3:a + 7] = [p[6], p[3], p[4], p[5]]
            for i, q in enumerate(near(run["objects"], t)["poses"]):
                b = m.joint(f"parcel_{i + 1}_free").qposadr[0]
                d.qpos[b:b + 3] = q[:3]
                d.qpos[b + 3:b + 7] = [q[6], q[3], q[4], q[5]]
        self.mj.mj_forward(m, d)
        w, x, y, z = d.qpos[a + 3:a + 7]
        return d.qpos[a], d.qpos[a + 1], math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

    def image(self, t, distance, offset=35.0, elevation=-28.0, height=0.75, ahead=0.35):
        x, y, yaw = self.set(t)
        target = yaw + offset
        if self.az is None:
            self.az = target
        self.az += ((target - self.az + 180) % 360 - 180) * 0.25      # the camera swings round slowly
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        self.cam.lookat[:] = [x + ahead * c, y + ahead * s, height]
        self.cam.distance, self.cam.azimuth, self.cam.elevation = distance, self.az, elevation
        self.r.update_scene(self.d, self.cam, self.opt)
        return Image.fromarray(self.r.render())


def hud(img, text):
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(BOLD, 18)
    d.rounded_rectangle((img.width - 22 - d.textlength(text, font=font), 8, img.width - 8, 36), 6, fill="#111111")
    d.text((img.width - 15 - d.textlength(text, font=font), 12), text, fill="#FFD75F", font=font)
    return img


def task(pkl, name, t0, t1, dt, labels=None, lead=None, tail_text="끝: 상자가 옮겨졌다", scenario=None):
    """Replay [t0, t1] of a PickPlace recording, one frame per dt sim seconds."""
    run = pickle.load(open(DEV / pkl, "rb"))
    labels = {**PHASE, **(labels or {})}
    fb, rp = run["feedback"], Replay(run)
    frames, durs = [], []
    for t in np.arange(t0, t1, dt):
        past = [f for f in fb if f["t"] <= t]
        phase = past[-1]["phase"] if past else None
        done = bool(past) and t > fb[-1]["t"] + 3
        text = tail_text if done else labels.get(phase, lead or "명령을 기다린다")
        img = rp.image(t, 2.3 if phase in CLOSE and not done else 3.6)
        tag = f"시뮬레이션 {t - t0:4.0f} s"
        if scenario:
            tag = scenario(t) + "  ·  " + tag
        frames.append(captioned(hud(img, tag), text)); durs.append(110)
    durs[0], durs[-1] = 1200, 3000
    write(frames, durs, name, colors=128)


def pick_place():        # lesson 10: spawned at the pick table, so the "navigate" phases are only a short side step
    task("pick_red.pkl", "lesson10_pick_place.gif", 17.0, 100.0, 0.9,
         labels={"navigate_pick": "작업대 앞에서 옆으로 자리를 맞춘다", "navigate_place": "놓을 자리 앞으로 옆걸음"},
         tail_text="끝: 빨간 상자를 집어 옆자리에 놓았다")


def transport():         # lesson 11: one parcel across the warehouse (first PickPlace goal of the recording)
    task("transport_red.pkl", "lesson11_transport.gif", 28.0, 214.0, 1.7,
         labels={"navigate_pick": "픽업 작업대 앞으로 이동 (Nav2)", "navigate_place": "창고를 가로질러 적재 작업대로 (Nav2)"},
         tail_text="끝: 빨간 상자가 적재 작업대로 옮겨졌다")


def mission():           # lesson 13: one text mission through the Task Manager
    task("mission_l13b.pkl", "lesson13_mission.gif", 270.0, 432.0, 1.5,
         labels={"navigate_pick": "단계 1: 픽업 작업대로 이동", "navigate_place": "단계 4: 놓을 자리로 이동"},
         lead="문장을 받아 단계 목록을 만드는 중", tail_text="끝: 파란 상자 미션 5 단계 완료")


def final():             # lesson 15: three sentences in a row
    run = pickle.load(open(DEV / "l14/final_mission.pkl", "rb"))
    fb = run["feedback"]
    starts = [f["t"] for i, f in enumerate(fb) if f["phase"] == "start" and (i == 0 or fb[i - 1]["phase"] != "start")][::2]   # pick + place goal per scenario
    names = ["시나리오 1", "시나리오 2", "시나리오 3"]
    task("l14/final_mission.pkl", "lesson15_final.gif", 50.0, 530.0, 4.0,
         labels={"navigate_pick": "상자가 있는 작업대로 이동 (Nav2)", "navigate_place": "옮길 작업대로 이동 (Nav2)"},
         lead="문장을 받아 계획을 세우는 중", tail_text="끝: 문장 세 개를 차례로 실행했다",
         scenario=lambda t: names[min(2, max(0, sum(s <= t for s in starts) - 1))])


def arm(pkl, name, t0, t1, dt, stages, distance=1.75):
    """Replay of an arm-only recording (arm_record.py): the base stays where the model puts it."""
    run = pickle.load(open(DEV / pkl, "rb"))
    rp = Replay(run)
    frames, durs = [], []
    for t in np.arange(t0, t1, dt):
        text = next(s for a, s in reversed(stages) if t >= a)
        img = rp.image(t, distance, offset=150.0, elevation=-12.0, height=1.0, ahead=0.25)
        frames.append(captioned(hud(img, f"시뮬레이션 {t - t0:4.1f} s"), text)); durs.append(110)
    durs[0], durs[-1] = 1200, 2500
    write(frames, durs, name, colors=96)


def moveit_ready():      # lesson 08: `arm both ready` executed by the MuJoCo trajectory action
    run = pickle.load(open(DEV / "arm_ready.pkl", "rb"))
    t_plan = run["plans"][0]["t"]
    t_end = t_plan + run["plans"][0]["times"][-1]
    arm("arm_ready.pkl", "lesson08_ready.gif", t_plan - 1.0, t_end + 2.0, 0.12,
        [(0, "운반 자세에서 시작"), (t_plan, "MoveIt 이 계획한 궤적을 MuJoCo 의 양팔이 따라간다"), (t_end, "ready 자세 도착")])


def ee_demo():           # lesson 09: ready -> IK pose -> straight down -> grip -> straight up  (times from draw_lesson09_figures.py)
    arm("ee_demo.pkl", "lesson09_ee_demo.gif", 51.0, 67.0, 0.14,
        [(0, "운반 자세에서 시작"), (52.0, "ready 자세로 (관절 목표)"), (55.6, "IK: 손끝을 목표 위치 · 자세로"),
         (63.0, "Cartesian: 손끝을 똑바로 아래로"), (64.1, "그리퍼 닫기"), (64.3, "Cartesian: 똑바로 위로"), (65.4, "끝")])


def screens(folder, pattern, name, crop, width, stages, ms=450, every=1, last=None):
    files = sorted((DEV / folder).glob(pattern))[:last]
    frames, durs = [], []
    for k, f in enumerate(files):
        if k % every and k != len(files) - 1:
            continue
        text = next((s for a, s in reversed(stages) if k >= a), None)
        if text is None:
            continue
        img = Image.open(f).convert("RGB")
        if crop:
            img = img.crop(crop)
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
        frames.append(captioned(img, text, f"{k + 1}/{len(files)}")); durs.append(ms)
    durs[0], durs[-1] = 1500, 3000
    write(frames, durs, name, colors=128)


def patrol():            # lesson 07: MuJoCo + RViz screenshots every 4 s (about 3 sim seconds) of the recorded patrol
    screens("patrol_frames", "s0*.png", "lesson07_patrol.gif", (10, 5, 2270, 955), 1100,
            [(0, "순찰 시작: 1/5 픽업 작업대로"), (7, "2/5 랙 A 로"), (19, "3/5 랙 B 로"), (30, "4/5 적재 작업대로"),
             (41, "5/5 중앙 통로로"), (49, "순찰 완료: 5 곳 · 148 s")], ms=380, last=56)


def patrol_dash():       # lesson 07: the web dashboard during the same kind of patrol (headless Chrome, every 3.3 s)
    screens("dash_frames", "d0*.png", "lesson07_dashboard.gif", None, 1000,
            [(0, "웹 대시보드: 지도 · 미션 · 로봇 상태 · 카메라"),
             (3, "순찰 중: 지도에 로봇 · 경로 · 사람, 오른쪽에 도착 기록과 카메라 검출이 쌓인다")], ms=420)


def task_dash():         # lesson 14: the task dashboard, a frame every 2 s (every third frame used)
    screens("l13dash/final", "f*.png", "lesson14_dashboard.gif", None, 900,
            [(0, "문장을 입력해 보낸다 → LLM 이 계획을 세운다"), (7, "계획 5 단계를 보여 주고 확인을 받는다 (응)"),
             (10, "단계 1: 픽업 작업대로 이동 (파란 줄 = 지금 하는 단계)"), (16, "단계 2 ~ 4: 상자 확인 · 집기 · 적재 작업대로 이동"),
             (100, "단계 5: 적재 작업대에 놓기"), (133, "완료 보고가 대화창에 뜬다"), (137, "둘째 문장: 랙 C 로 가서 주변을 알려 달라"),
             (160, "셋째 문장: 노란 상자 운반 · 도중에 '실행 취소'")], ms=330, every=3)


ALL = {f.__name__: f for f in (pick_place, transport, mission, final, moveit_ready, ee_demo, patrol, patrol_dash, task_dash)}

if __name__ == "__main__":
    for n in sys.argv[1:] or ALL:
        ALL[n]()
