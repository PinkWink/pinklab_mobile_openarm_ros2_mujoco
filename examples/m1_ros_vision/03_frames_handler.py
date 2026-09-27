#!/usr/bin/env python3
"""M1 예제 3: 첫 카메라 핸들러. 시뮬레이터 프로세스 안에서 프레임을 직접 받는다.

실행: 이 파일은 단독 실행하지 않고 시뮬레이터에 핸들러로 넘긴다.
    ./scripts/mobile_openarm start viewer:=false \\
        camera_handler:=examples/m1_ros_vision/03_frames_handler.py:FramesHandler camera_depth:=true
  (ArUco 도킹·정답 검출기를 함께 유지하려면 대신
    LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,examples/m1_ros_vision/03_frames_handler.py:FramesHandler" \\
        ./scripts/mobile_openarm start viewer:=false camera_depth:=true camera_segmentation:=true )
  창을 띄우지 않으려면 M1_WINDOW=0. 미리보기는 artifacts/m1/03_frames.png 에 1초마다 저장된다.

핸들러 프로토콜 (mobile_openarm_mujoco/handler.py):
    setup(context)   시작 시 한 번. context.node 로 퍼블리셔·TF 를 만들고, context.pump.fps 로 캡처율을 바꾼다.
    __call__(frames) 캡처 주기마다. frames = {카메라 이름: CameraFrame}. 시뮬레이터 메인 스레드에서 불리므로
                     여기서 오래 걸리면 시뮬레이션이 느려진다 (06번 예제에서 워커 스레드로 옮긴다).
    close()          종료 시.
CameraFrame: name, optical_frame, sim_time, rgb(HxWx3 uint8), depth_m(HxW float32 | None),
             K(3x3), T_world_optical(4x4), segmentation(HxW int32 | None)
"""

import os
import time
from pathlib import Path

import cv2
import numpy as np


class FramesHandler:
    def __init__(self):
        self.window = os.environ.get("M1_WINDOW", "1") != "0" and bool(os.environ.get("DISPLAY"))
        self.out = Path("artifacts/m1"); self.out.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self.last_sim = None
        self.last_report_wall = None
        self.last_report_sim = None
        self.handler_ms = []
        self.printed_intrinsics = False

    # --- 시작 시 한 번 ------------------------------------------------------
    def setup(self, context):
        self.context = context
        log = context.node.get_logger()
        log.info(f"[03] 카메라 {context.camera_names}, 캡처 {context.pump.fps:g} FPS (시뮬레이션 시간 기준), "
                 f"깊이 {'on' if context.pump.depth else 'off'}, 창 {'on' if self.window else 'off'}")
        log.info(f"[03] 전체 카메라 목록: {context.rig.names}")

    # --- 프레임마다 -----------------------------------------------------------
    def __call__(self, frames):
        t0 = time.perf_counter()
        self.calls += 1
        first = next(iter(frames.values()))
        log = self.context.node.get_logger()
        if not self.printed_intrinsics:
            self.printed_intrinsics = True
            for name, f in frames.items():
                fx, fy, cx, cy = f.K[0, 0], f.K[1, 1], f.K[0, 2], f.K[1, 2]
                pos = f.T_world_optical[:3, 3]
                log.info(f"[03] {name}: {f.rgb.shape[1]}x{f.rgb.shape[0]}, optical_frame={f.optical_frame}, "
                         f"K: fx={fx:.1f} fy={fy:.1f} cx={cx:.1f} cy={cy:.1f}")
                log.info(f"[03] {name}: 카메라 위치(world) = ({pos[0]:+.2f}, {pos[1]:+.2f}, {pos[2]:+.2f}), "
                         f"광축(world) = {np.round(f.T_world_optical[:3, 2], 2).tolist()}  <- optical z 축")
        # 1초(시뮬레이션 시간)마다 요약 출력 + 미리보기 저장
        if self.last_report_sim is None or first.sim_time - self.last_report_sim >= 1.0:
            now = time.perf_counter()
            if self.last_report_wall is not None:
                sim_dt = first.sim_time - self.last_report_sim
                wall_dt = now - self.last_report_wall
                ratio = sim_dt / wall_dt
                mean_ms = 1000 * sum(self.handler_ms) / max(1, len(self.handler_ms))
                parts = [f"[03] sim {first.sim_time:8.2f}s  프레임 {self.calls}회  실시간 비율 {ratio:.2f}  "
                         f"핸들러 {mean_ms:.1f} ms/호출"]
                for name, f in frames.items():
                    d = ""
                    if f.depth_m is not None:
                        finite = f.depth_m[np.isfinite(f.depth_m)]
                        d = f" depth {finite.min():.2f}~{finite.max():.2f} m" if finite.size else " depth: 전부 inf"
                    parts.append(f"{name} rgb mean {f.rgb.mean():.0f}{d}")
                log.info(" | ".join(parts))
            self.last_report_wall, self.last_report_sim = now, first.sim_time
            self.handler_ms.clear()
            self.save_preview(frames)
        if self.window:
            self.show(frames)
        self.handler_ms.append(time.perf_counter() - t0)

    # --- 표시 -----------------------------------------------------------------
    def compose(self, frames):
        tiles = []
        for name, f in frames.items():
            bgr = cv2.cvtColor(f.rgb, cv2.COLOR_RGB2BGR)
            cv2.putText(bgr, f"{name} t={f.sim_time:.1f}", (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            tiles.append(bgr)
            if f.depth_m is not None:
                d = np.nan_to_num(f.depth_m, posinf=0.0)
                d8 = np.clip(d / 5.0 * 255, 0, 255).astype(np.uint8)  # 0~5 m 를 0~255 로
                tiles.append(cv2.applyColorMap(d8, cv2.COLORMAP_JET))
        return cv2.hconcat(tiles)

    def save_preview(self, frames):
        tmp = self.out / "03_frames.tmp.png"
        cv2.imwrite(str(tmp), self.compose(frames))
        tmp.replace(self.out / "03_frames.png")

    def show(self, frames):
        try:
            cv2.imshow("M1-03 cameras (rgb | depth)", self.compose(frames))
            cv2.waitKey(1)  # 창 이벤트 처리. 없으면 창이 그려지지 않는다
        except cv2.error as error:
            self.context.node.get_logger().warn(f"[03] OpenCV 창을 열 수 없어 끈다: {error}")
            self.window = False

    def close(self):
        if self.window:
            cv2.destroyAllWindows()
