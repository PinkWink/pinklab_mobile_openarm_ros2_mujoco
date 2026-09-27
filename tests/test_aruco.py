"""ArUco marker plates: built into the world, invisible to lidar, detected from the base camera."""

import math

import numpy as np
import pytest

from mobile_openarm_mujoco.cameras import CameraRig
from mobile_openarm_mujoco.model import Physics, build_model, load_world
from warehouse_lecture.vision.aruco import base_from_optical, detect


@pytest.fixture(scope="module")
def physics(tmp_path_factory):
    return Physics(build_model(tmp_path_factory.mktemp("aruco")))


def test_markers_exist_and_do_not_touch_lidar_or_contacts(physics):
    m = physics.model
    markers = load_world()["markers"]
    assert len(markers) == 4 and {x["station"] for x in markers} == {"pick", "place"}
    for spec in markers:
        g = m.geom(f"aruco_{spec['id']}_plate")
        assert g.group[0] == 2 and g.contype[0] == 0 and g.conaffinity[0] == 0
        assert m.geom_type[g.id] == 0  # plane
    scan = physics.scan()
    assert np.isfinite(scan).all()


@pytest.mark.parametrize("distance", [1.2, 0.9, 0.75])
def test_marker_pose_from_base_camera(physics, distance):
    p = physics
    spec = next(x for x in load_world()["markers"] if x["station"] == "pick")
    mx, my, mz = spec["center"]
    # Park the robot in front of the marker with a small lateral offset and heading error.
    lateral, heading = 0.06, math.radians(-4)
    q = p.base_q
    p.data.qpos[q : q + 3] = [mx - distance, my + lateral, 0.002]
    p.data.qpos[q + 3 : q + 7] = [math.cos(heading / 2), 0, 0, math.sin(heading / 2)]
    p.mj.mj_forward(p.model, p.data)
    with CameraRig(p.model, p.data, width=320, height=240) as rig:
        frame = rig.read("base_camera")
    found = detect(frame.rgb, frame.K, {int(x["id"]): float(x["size"]) for x in load_world()["markers"]})
    assert int(spec["id"]) in [f[0] for f in found]
    found = [f for f in found if f[0] == int(spec["id"])]
    T = base_from_optical(p, "base_camera")
    pos = (T @ np.r_[found[0][1], 1.0])[:3]
    # Expected marker position in base_footprint given the parked pose.
    c, s = math.cos(heading), math.sin(heading)
    ex, ey = distance, -lateral
    expected = np.array([c * ex + s * ey, -s * ex + c * ey, mz])
    assert np.linalg.norm(pos - expected) < 0.03, (pos, expected)
    normal = (T[:3, :3] @ found[0][2])[:, 2]
    yaw = math.atan2(normal[1], normal[0])
    # Robot turned +heading (left) -> the marker normal appears rotated by -heading.
    assert abs(math.atan2(math.sin(yaw - math.pi + heading), math.cos(yaw - math.pi + heading))) < math.radians(8)
    p.data.qpos[q : q + 7] = [0, 0, 0.002, 1, 0, 0, 0]
    p.mj.mj_forward(p.model, p.data)
