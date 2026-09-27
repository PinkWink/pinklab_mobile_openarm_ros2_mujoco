"""warehouse_skills: marker-pair docking geometry and grasp pose conventions (no simulator)."""

import math

import numpy as np
import pytest

from warehouse_skills.moveit_client import GRASP_FORWARD, make_pose, quat_from_axes
from warehouse_skills.nav_client import NavClient


def fixes_for(robot_xy, robot_yaw, markers, noise=0.0):
    """Synthetic base-frame marker fixes for a robot pose in the world (markers face -x)."""
    c, s = math.cos(robot_yaw), math.sin(robot_yaw)
    out = {}
    for marker_id, (mx, my) in markers.items():
        ex, ey = mx - robot_xy[0], my - robot_xy[1]
        dx, dy = c * ex + s * ey, -s * ex + c * ey
        normal_yaw = math.atan2(math.sin(math.pi - robot_yaw), math.cos(math.pi - robot_yaw)) + noise
        out[marker_id] = (dx + noise, dy - noise, normal_yaw, math.hypot(dx, dy))
    return out


MARKERS = {0: (2.22, -3.82), 1: (2.22, -3.38)}
OFFSETS = {0: -0.22, 1: 0.22}


@pytest.mark.parametrize("robot", [((1.2, -3.6), 0.0), ((1.1, -3.5), math.radians(12)), ((1.3, -3.75), math.radians(-9))])
def test_pair_geometry_recovers_pose_regardless_of_heading(robot):
    (x, y), yaw = robot
    along, side, turn, origin, u = NavClient.geometry(fixes_for((x, y), yaw, MARKERS), OFFSETS)
    assert along == pytest.approx(2.22 - x, abs=1e-6)
    assert side == pytest.approx(-3.6 - y, abs=1e-6)  # axis appears left when the robot is right of it
    assert turn == pytest.approx(-yaw, abs=1e-6)
    assert np.linalg.norm(u) == pytest.approx(1.0)


def test_single_marker_fallback_uses_its_normal():
    fixes = fixes_for((1.2, -3.6), math.radians(5), MARKERS)
    only = {0: fixes[0]}
    along, side, turn, _, _ = NavClient.geometry(only, OFFSETS)
    assert along == pytest.approx(1.02, abs=1e-6)
    assert side == pytest.approx(0.0, abs=1e-6)
    assert turn == pytest.approx(-math.radians(5), abs=1e-6)
    with pytest.raises(Exception):
        NavClient.geometry({}, OFFSETS)


def test_forward_grasp_orientation_points_fingers_horizontally():
    x, y, z, w = GRASP_FORWARD
    R = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    assert R[:, 2] == pytest.approx([1, 0, 0])   # approach (+z hand) forward
    assert R[:, 1] == pytest.approx([0, 1, 0])   # finger closing axis horizontal
    assert R[:, 0] == pytest.approx([0, 0, -1])  # hand x points down
    q = quat_from_axes(np.array([0, 0, -1.0]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0]))
    assert np.allclose(q, GRASP_FORWARD)
    pose = make_pose([0.44, 0.09, 0.83])
    assert (pose.position.x, pose.position.y, pose.position.z) == (0.44, 0.09, 0.83)


def test_side_dock_target_puts_base_on_the_object_side():
    """Yellow parcel regression (2026-09-27): dock_side_for gives the base offset (+left of the
    axis); the servo's target is the axis offset seen from the base, so it must be negated.
    A base standing left of the axis sees the axis on its right (side < 0)."""
    from warehouse_skills.pick_place_server import PickPlaceServer

    assert PickPlaceServer.dock_side_for(0.05) == 0.0
    assert PickPlaceServer.dock_side_for(-0.25) == 0.0
    dock_side = PickPlaceServer.dock_side_for(0.35)
    assert dock_side == pytest.approx(0.10)
    assert PickPlaceServer.dock_side_for(0.60) == pytest.approx(0.20)  # clamped to max_side
    # Base 0.10 m left of the axis (y = -3.5): the geometry reports side = -0.10 = -dock_side.
    _, side, _, _, _ = NavClient.geometry(fixes_for((1.2, -3.6 + dock_side), 0.0, MARKERS), OFFSETS)
    assert side == pytest.approx(-dock_side, abs=1e-6)
