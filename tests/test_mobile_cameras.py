"""Camera geometry and scheduling tests without an OpenGL context."""

import threading
from types import SimpleNamespace

import mujoco
import numpy as np
import pytest

from mobile_openarm_mujoco.cameras import CameraRig, CameraPump
from mobile_openarm_mujoco.model import Physics, build_model, camera_settings


@pytest.fixture(scope="module")
def physics(tmp_path_factory):
    return Physics(build_model(tmp_path_factory.mktemp("mobile_cameras")))


def test_four_optical_frames_and_following(physics):
    p = physics
    cfg = camera_settings()["cameras"]
    assert p.model.ncam == 4
    for name in cfg:
        i = p.model.camera(name).id
        optical = p.data.body(name + "_optical_frame")
        assert p.data.cam_xpos[i] == pytest.approx(optical.xpos)
        assert p.data.cam_xmat[i].reshape(3, 3) @ np.diag([1, -1, -1]) == pytest.approx(
            optical.xmat.reshape(3, 3)
        )
    assert p.data.cam_xpos[p.model.camera("head_camera").id, 2] > 1.0
    base_forward = -p.data.cam_xmat[p.model.camera("base_camera").id].reshape(3, 3)[
        :, 2
    ]
    assert base_forward == pytest.approx([1, 0, 0], abs=1e-8)
    head_forward = -p.data.cam_xmat[p.model.camera("head_camera").id].reshape(3, 3)[
        :, 2
    ]
    assert head_forward[0] > 0.9 and head_forward[2] < -0.2
    before = p.data.cam_xpos.copy()
    q = p.data.qpos.copy()
    p.data.qpos[p.model.joint("openarm_left_joint4").qposadr[0]] += 0.4
    mujoco.mj_forward(p.model, p.data)
    assert (
        np.linalg.norm(
            p.data.cam_xpos[p.model.camera("left_wrist_camera").id]
            - before[p.model.camera("left_wrist_camera").id]
        )
        > 0.05
    )
    for name in ["base_camera", "head_camera", "right_wrist_camera"]:
        assert p.data.cam_xpos[p.model.camera(name).id] == pytest.approx(
            before[p.model.camera(name).id]
        )
    p.data.qpos[:] = q
    mujoco.mj_forward(p.model, p.data)


def test_camera_calibration_and_lifecycle_without_gpu(physics):
    with CameraRig(physics.model, physics.data, width=320, height=240) as cameras:
        K = cameras.intrinsics("base_camera")
        assert K[0, 0] == pytest.approx(120 / np.tan(np.deg2rad(65) / 2))
        assert K[:, 2] == pytest.approx([159.5, 119.5, 1])
        assert physics.model.vis.map.znear * physics.model.stat.extent == pytest.approx(
            0.01
        )
        assert physics.model.vis.map.zfar * physics.model.stat.extent == pytest.approx(
            50
        )
        assert (
            cameras._renderer is None
        )  # On-demand API never requires GL until read().
        with pytest.raises(ValueError):
            cameras.read("not_a_camera")
        failures = []

        def wrong_thread():
            try:
                cameras.read("base_camera")
            except RuntimeError as error:
                failures.append(str(error))

        worker = threading.Thread(target=wrong_thread)
        worker.start()
        worker.join()
        assert len(failures) == 1
    with pytest.raises(RuntimeError):
        cameras.read("base_camera")


def test_callback_rate_and_simulation_reset():
    samples = []
    rig = SimpleNamespace(data=SimpleNamespace(time=0.0), read_all=lambda **_: "frames")
    pump = CameraPump(rig, samples.append, fps=5)
    for t in [0.0, 0.01, 0.19, 0.2, 0.21, 0.4, 0.01]:
        rig.data.time = t
        pump.update()
    assert samples == ["frames"] * 4
    for fps in [0, -1, float("nan"), float("inf")]:
        with pytest.raises(ValueError):
            CameraPump(rig, samples.append, fps=fps)
