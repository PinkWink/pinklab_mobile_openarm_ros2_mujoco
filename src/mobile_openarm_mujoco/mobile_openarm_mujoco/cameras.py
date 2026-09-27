"""Direct NumPy camera frames from the caller's live MuJoCo model/data.

No ROS nodes, Image/CameraInfo publishers, sockets, or second simulation.
Create, render, and close on one thread; do not step the data concurrently.
"""

from dataclasses import dataclass
import threading

import mujoco
import numpy as np


@dataclass(frozen=True)
class CameraFrame:
    name: str
    optical_frame: str
    sim_time: float
    rgb: np.ndarray  # uint8, H x W x 3, RGB, top-left origin
    depth_m: np.ndarray | None  # float32, optical Z depth in metres, inf at far clip
    K: np.ndarray  # 3 x 3 intrinsics, zero-based integer pixel centres
    T_world_optical: np.ndarray  # 4 x 4, optical coordinates -> MuJoCo world
    # int32, H x W, MuJoCo body id per pixel, -1 for background/sky. None unless requested.
    segmentation: np.ndarray | None = None


class CameraRig:
    def __init__(self, model, data, *, width=640, height=480):
        if (
            not isinstance(width, int)
            or not isinstance(height, int)
            or min(width, height) <= 0
        ):
            raise ValueError("Camera width and height must be positive integers")
        if width > model.vis.global_.offwidth or height > model.vis.global_.offheight:
            raise ValueError("Camera size exceeds the MJCF offscreen framebuffer size")
        self.model, self.data = model, data
        self.width, self.height = width, height
        self.names = tuple(model.camera(i).name for i in range(model.ncam))
        self._ids = {name: model.camera(name).id for name in self.names}
        self._thread = threading.get_ident()
        self._renderer = None
        self._closed = False
        self._options = mujoco.MjvOption()
        self._options.geomgroup[1] = 0  # Visible surfaces, not collision proxies.

    def _check(self, name=None):
        if self._closed:
            raise RuntimeError("CameraRig is closed")
        if threading.get_ident() != self._thread:
            raise RuntimeError("CameraRig must be used on its creating thread")
        if name is not None and name not in self._ids:
            raise ValueError(f"Unknown camera {name!r}; available: {self.names}")

    def intrinsics(self, name):
        self._check(name)
        fovy = np.deg2rad(self.model.cam_fovy[self._ids[name]])
        focal = self.height / (2 * np.tan(fovy / 2))
        return np.array(
            [
                [focal, 0.0, (self.width - 1) / 2],
                [0.0, focal, (self.height - 1) / 2],
                [0.0, 0.0, 1.0],
            ]
        )

    def _capture(self, name, depth, segmentation=False):
        if self._renderer is None:
            self._renderer = mujoco.Renderer(
                self.model, height=self.height, width=self.width
            )
        renderer = self._renderer
        renderer.disable_depth_rendering()
        renderer.disable_segmentation_rendering()
        renderer.update_scene(self.data, camera=name, scene_option=self._options)
        rgb = renderer.render().copy()
        depth_m = None
        if depth:
            renderer.enable_depth_rendering()
            try:
                depth_m = renderer.render().astype(np.float32, copy=True)
                far = float(self.model.vis.map.zfar * self.model.stat.extent)
                depth_m[depth_m >= far * 0.9999] = np.inf
            finally:
                renderer.disable_depth_rendering()
        bodies = None
        if segmentation:
            renderer.enable_segmentation_rendering()
            try:
                # (H, W, 2): object id and object type per pixel; -1 where nothing was hit.
                ids = renderer.render()
                geom = ids[..., 1] == mujoco.mjtObj.mjOBJ_GEOM
                bodies = np.full(ids.shape[:2], -1, dtype=np.int32)
                bodies[geom] = self.model.geom_bodyid[ids[..., 0][geom]]
            finally:
                renderer.disable_segmentation_rendering()
        transform = np.eye(4)
        i = self._ids[name]
        transform[:3, :3] = self.data.cam_xmat[i].reshape(3, 3) @ np.diag(
            [1.0, -1.0, -1.0]
        )
        transform[:3, 3] = self.data.cam_xpos[i]
        return CameraFrame(
            name,
            name + "_optical_frame",
            float(self.data.time),
            rgb,
            depth_m,
            self.intrinsics(name),
            transform,
            bodies,
        )

    def read(self, name, *, depth=False, segmentation=False):
        """Render one camera at the current simulation state; never advances time."""
        self._check(name)
        mujoco.mj_forward(self.model, self.data)
        return self._capture(name, depth, segmentation)

    def read_all(self, names=None, *, depth=False, segmentation=False):
        """Render the selected cameras at the same state and simulation timestamp."""
        self._check()
        names = self.names if names is None else tuple(names)
        for name in names:
            self._check(name)
        mujoco.mj_forward(self.model, self.data)
        return {name: self._capture(name, depth, segmentation) for name in names}

    def body_boxes(self, segmentation, min_pixels=16):
        """Pixel bounding boxes (x1, y1, x2, y2) per visible body id from a segmentation map."""
        boxes = {}
        for body in np.unique(segmentation):
            if body < 0:
                continue
            ys, xs = np.nonzero(segmentation == body)
            if len(xs) < min_pixels:
                continue
            boxes[int(body)] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        return boxes

    def close(self):
        if self._closed:
            return
        self._check()
        if self._renderer is not None:
            self._renderer.close()
        self._closed = True

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *_):
        self.close()


class CameraPump:
    """Deliver frames to a same-process Python callback at a simulation-time rate."""

    def __init__(
        self, rig, handler, *, fps=5.0, depth=False, names=None, segmentation=False
    ):
        if not np.isfinite(fps) or fps <= 0:
            raise ValueError("Camera FPS must be finite and positive")
        if not callable(handler):
            raise TypeError("Camera handler must be callable")
        self.rig, self.handler = rig, handler
        self.period, self.depth = 1.0 / fps, depth
        self.names = tuple(names) if names else None
        self.segmentation = segmentation
        self._last = None

    @property
    def fps(self):
        return 1.0 / self.period

    @fps.setter
    def fps(self, value):
        """Handlers may lower the capture rate at runtime on slow machines."""
        if not np.isfinite(value) or value <= 0:
            raise ValueError("Camera FPS must be finite and positive")
        self.period = 1.0 / value

    def update(self):
        now = float(self.rig.data.time)
        if (
            self._last is None
            or now < self._last
            or now - self._last >= self.period - 1e-9
        ):
            self.handler(
                self.rig.read_all(
                    names=self.names, depth=self.depth, segmentation=self.segmentation
                )
            )
            self._last = now
