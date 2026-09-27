"""Base class for camera handlers that run heavy work off the physics thread.

Flow per captured frame set (physics thread, inside the simulator process):
    frames -> ``prepare(frames)`` (cheap, may read physics/TF) -> queue
Worker thread:
    ``process(item)`` (YOLO inference etc.) -> result
Physics thread, next capture:
    ``publish(result)`` (ROS publishers live on the bridge node; use them here only)

Only the newest queued item is kept, so a slow worker drops frames instead of
delaying the simulation. ``adaptive`` lowers the capture FPS when the simulator
falls behind real time and raises it again when there is headroom.
"""

import queue
import threading
import time

from warehouse_interfaces.msg import VisionStats


class WorkerHandler:
    def __init__(self, *, adaptive=True, min_fps=0.5, stats_topic="/vision/stats"):
        self.adaptive = adaptive
        self.min_fps = min_fps
        self.stats_topic = stats_topic
        self.context = None
        self._queue = queue.Queue(maxsize=1)
        self._results = queue.Queue()
        self._thread = None
        self._stop = threading.Event()
        self._dropped = 0
        self._inference_ms = 0.0
        self._wall = None
        self._sim = None
        self._target_fps = None
        self._stats_pub = None
        self._ratio = 1.0

    # --- override these -------------------------------------------------
    def prepare(self, frames):
        """Physics thread. Return the item handed to the worker (default: frames)."""
        return frames

    def process(self, item):
        """Worker thread. Heavy computation; must not touch ROS publishers or MuJoCo data."""
        return item

    def publish(self, result):
        """Physics thread. Publish ROS messages built from a worker result."""

    def on_setup(self, context):
        """Physics thread. Create publishers/subscribers on ``context.node`` here."""

    # --- protocol -------------------------------------------------------
    def setup(self, context):
        self.context = context
        self._target_fps = context.pump.fps
        self._stats_pub = context.node.create_publisher(VisionStats, self.stats_topic, 10)
        self.on_setup(context)
        self._thread = threading.Thread(target=self._run, name="camera-worker", daemon=True)
        self._thread.start()

    def __call__(self, frames):
        while True:
            try:
                self.publish(self._results.get_nowait())
            except queue.Empty:
                break
        item = self.prepare(frames)
        if item is not None:
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
                self._dropped += 1
                self._queue.put_nowait(item)
        self._throttle()

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    # --- internals ------------------------------------------------------
    def _run(self):
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            start = time.perf_counter()
            try:
                result = self.process(item)
            except Exception as error:  # noqa: BLE001 - keep the worker alive
                self.context.node.get_logger().error(f"Camera worker failed: {error!r}")
                continue
            self._inference_ms = (time.perf_counter() - start) * 1000
            if result is not None:
                self._results.put(result)

    def _throttle(self):
        ctx = self.context
        now_wall, now_sim = time.monotonic(), ctx.sim_time()
        if self._wall is not None and now_wall > self._wall:
            ratio = (now_sim - self._sim) / (now_wall - self._wall)
            self._ratio = 0.7 * self._ratio + 0.3 * ratio
            if self.adaptive:
                pump = ctx.pump
                if self._ratio < 0.8 and pump.fps > self.min_fps:
                    pump.fps = max(self.min_fps, pump.fps * 0.75)
                elif self._ratio > 0.97 and pump.fps < self._target_fps:
                    pump.fps = min(self._target_fps, pump.fps * 1.15)
        self._wall, self._sim = now_wall, now_sim
        msg = VisionStats()
        msg.header.stamp = ctx.stamp()
        msg.capture_fps = float(ctx.pump.fps)
        msg.realtime_ratio = float(self._ratio)
        msg.inference_ms = float(self._inference_ms)
        msg.queue_depth = self._queue.qsize()
        msg.dropped_frames = self._dropped
        msg.cameras = list(ctx.camera_names)
        self._stats_pub.publish(msg)
