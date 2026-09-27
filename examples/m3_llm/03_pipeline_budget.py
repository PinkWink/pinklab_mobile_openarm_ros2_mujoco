#!/usr/bin/env python3
"""M3 예제 3: 비전 파이프라인의 CPU 예산 배분. 카메라 교대·프레임 스킵·해상도·ROI 설정을 한 실행에서 순환하며
추론 시간, 실시간 비율, 검출 수를 재고 표로 남긴다.

실행 (수강생 PC 조건. 코어를 더 줄여 보면 차이가 커진다: taskset -c 0-1):
    taskset -c 0-3 ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m3_llm/03_pipeline_budget.py:BudgetHandler camera_fps:=4
  옵션: M3_PERIOD=20 (설정당 시뮬레이션 초)  M3_CONFIGS=all,alternate,skip2,size416,size224,roi
  출력: artifacts/m3/budget.md

배우는 점:
- 예산은 "초당 추론 픽셀 수"다. 카메라 2대 x 4 FPS x 320² 과 교대(1대씩) 또는 스킵(2프레임에 1번)은 같은 검출 지연을 두고 절반이다.
- 해상도는 지연에 제곱으로, 정확도에는 작은 물체부터 영향을 준다(M2-06 표). ROI(관심 영역만 자르기)는 작업대 앞처럼 볼 곳이 정해졌을 때 해상도를 지키면서 픽셀을 줄인다.
- 실시간 비율이 1 아래로 내려가면 시뮬레이터(로봇)가 느려지는 것이다. 실제 로봇이면 제어 주기가 밀린다. 예산은 여기서 정한다.
- WorkerHandler 의 적응형 FPS 는 마지막 안전장치다. 설계 단계에서 예산을 맞추는 것이 먼저다.
"""

import os
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from warehouse_lecture.ros.handler_base import WorkerHandler
from warehouse_lecture.vision.yolo import YoloDetector

CONFIGS = {
    "all":       {"desc": "2대 매 프레임 320", "cams": "all", "skip": 1, "imgsz": 320, "roi": None},
    "alternate": {"desc": "카메라 교대(프레임마다 1대) 320", "cams": "alternate", "skip": 1, "imgsz": 320, "roi": None},
    "skip2":     {"desc": "2대, 2프레임에 1번 320", "cams": "all", "skip": 2, "imgsz": 320, "roi": None},
    "size416":   {"desc": "2대 매 프레임 416", "cams": "all", "skip": 1, "imgsz": 416, "roi": None},
    "size224":   {"desc": "2대 매 프레임 224", "cams": "all", "skip": 1, "imgsz": 224, "roi": None},
    "roi":       {"desc": "head 카메라 중앙 60 % 만 416 (작업대 전용)", "cams": "head", "skip": 1, "imgsz": 416, "roi": 0.6},
}


class BudgetHandler(WorkerHandler):
    def __init__(self):
        super().__init__(adaptive=False)       # 예산 실험이므로 자동 스로틀은 끈다
        self.period = float(os.environ.get("M3_PERIOD", "20"))
        self.names = [c for c in os.environ.get("M3_CONFIGS", ",".join(CONFIGS)).split(",") if c]
        self.detectors = {}
        self.index = -1
        self.stats = defaultdict(lambda: {"ms": [], "ratio": [], "dets": 0, "frames": 0, "images": 0})
        self.frame_no = 0
        self.turn = 0
        self.start = None
        self.done = False

    def on_setup(self, context):
        for s in sorted({CONFIGS[c]["imgsz"] for c in self.names}):
            self.detectors[s] = YoloDetector(imgsz=s, conf=0.4)
        self.head = "head_camera" if "head_camera" in context.camera_names else context.camera_names[0]
        context.node.get_logger().info(f"[m3-03] 설정 {self.names}, 각 {self.period:.0f}s, 카메라 {context.camera_names}, 캡처 {context.pump.fps:g} FPS")
        self.next_config()

    def next_config(self):
        self.index += 1
        if self.index >= len(self.names):
            self.done = True
            self.report()
            return
        self.cfg = CONFIGS[self.names[self.index]]
        self.start = self.context.sim_time()
        self.context.node.get_logger().info(f"[m3-03] >>> {self.names[self.index]}: {self.cfg['desc']}")

    def prepare(self, frames):
        if self.done:
            return None
        now = self.context.sim_time()
        if now - self.start >= self.period:
            self.next_config()
            if self.done:
                return None
        cfg = self.cfg
        self.frame_no += 1
        if self.frame_no % cfg["skip"]:
            return None                               # 프레임 스킵
        names = list(frames)
        if cfg["cams"] == "alternate":
            names = [names[self.turn % len(names)]]; self.turn += 1
        elif cfg["cams"] == "head":
            names = [self.head]
        items = []
        for n in names:
            rgb = frames[n].rgb
            if cfg["roi"]:
                h, w = rgb.shape[:2]; r = cfg["roi"]
                y0, x0 = int(h * (1 - r) / 2), int(w * (1 - r) / 2)
                rgb = rgb[y0:y0 + int(h * r), x0:x0 + int(w * r)]
            items.append((n, rgb.copy()))
        return (self.names[self.index], items)

    def process(self, item):
        name, items = item
        det = self.detectors[CONFIGS[name]["imgsz"]]
        t0 = time.perf_counter()
        results = det.detect_batch([rgb for _, rgb in items])
        return name, (time.perf_counter() - t0) * 1000, len(items), sum(len(r) for r in results)

    def publish(self, result):
        name, ms, n_img, n_det = result
        s = self.stats[name]
        s["ms"].append(ms); s["ratio"].append(self._ratio); s["dets"] += n_det; s["frames"] += 1; s["images"] += n_img

    def report(self):
        lines = [f"캡처 {self.context.pump.fps:g} FPS(시뮬레이션 시간), 설정당 {self.period:.0f}s, CPU {len(os.sched_getaffinity(0))}코어. 추론 ms 는 배치(프레임) 기준 중앙값.", "",
                 "| 설정 | 내용 | 추론 ms/프레임 | 이미지/초 | 검출/초 | 실시간 비율(최소/평균) |", "|---|---|---|---|---|---|"]
        for n in self.names:
            s = self.stats[n]
            if not s["frames"]:
                continue
            lines.append(f"| {n} | {CONFIGS[n]['desc']} | {np.median(s['ms']):.1f} | {s['images'] / self.period:.1f} | {s['dets'] / self.period:.1f} | "
                         f"{min(s['ratio']):.2f} / {np.mean(s['ratio']):.2f} |")
        out = Path("artifacts/m3"); out.mkdir(parents=True, exist_ok=True)
        (out / "budget.md").write_text("\n".join(lines) + "\n")
        self.context.node.get_logger().info("[m3-03] 완료\n" + "\n".join(lines))
