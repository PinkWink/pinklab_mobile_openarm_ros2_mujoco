from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import yaml
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from mobile_openarm_description.model import expand_urdf, resolve_mesh
from mobile_openarm_mujoco.model import (
    Physics,
    build_model,
    initial_positions,
    load_world,
    share,
)
from mobile_openarm_mujoco.trajectory import Trajectory, validate_trajectory


@pytest.fixture(scope="module")
def model_path(tmp_path_factory):
    return build_model(tmp_path_factory.mktemp("mobile_openarm"))


def test_urdf_is_one_mobile_tree_with_real_assets():
    r = ET.fromstring(expand_urdf())
    links = [x.get("name") for x in r.findall("link")]
    joints = r.findall("joint")
    assert len(links) == len(set(links)) == 46
    children = [j.find("child").get("link") for j in joints]
    assert len(children) == len(set(children))
    assert set(links) - set(children) == {"base_footprint"}
    assert len([j for j in joints if j.get("type") == "revolute"]) == 14
    assert len([j for j in joints if j.find("mimic") is not None]) == 2
    assert (
        r.find("gazebo") is None
        and r.find("ros2_control") is None
        and "world" not in links
    )
    for mesh in r.findall(".//mesh"):
        assert resolve_mesh(mesh.get("filename")).is_file()
    for package in ["openarm_description", "vicpinky_description"]:
        source = Path(__file__).resolve().parents[1] / "src" / package
        for file, digest in json.loads(
            (source / "asset-sha256.json").read_text()
        ).items():
            assert hashlib.sha256((source / file).read_bytes()).hexdigest() == digest


def test_controller_and_moveit_joint_contract():
    r = ET.fromstring(expand_urdf())
    joints = {j.get("name") for j in r.findall("joint")}
    folder = share("mobile_openarm_moveit_config") / "config"
    s = ET.parse(folder / "mobile_openarm.srdf")
    for j in s.findall(".//joint"):
        assert j.get("name") in joints
    links = {l.get("name") for l in r.findall("link")}
    for p in s.findall("disable_collisions"):
        assert p.get("link1") in links and p.get("link2") in links
    c = yaml.safe_load((folder / "moveit_controllers.yaml").read_text())[
        "moveit_simple_controller_manager"
    ]
    controlled = [j for n in c["controller_names"] for j in c[n]["joints"]]
    assert len(controlled) == len(set(controlled)) == 16
    assert set(controlled) == set(initial_positions())
    assert s.find("virtual_joint").get("child_link") == "base_footprint"


def test_warehouse_and_map_are_consistent():
    w = load_world()
    assert math.prod(w["size"]) == 165.0
    assert len(w["objects"]) == 3
    for o in w["objects"]:
        assert o["size"][1] < 0.088 and o["mass"] > 0
    mapfile = share("mobile_openarm_navigation") / "maps/warehouse.yaml"
    m = yaml.safe_load(mapfile.read_text())
    assert (mapfile.parent / m["image"]).is_file() and m["resolution"] == 0.05


def test_physics_stability_drive_turn_and_gripper(model_path):
    p = Physics(model_path)
    assert p.radius == pytest.approx(0.0825) and p.track == pytest.approx(0.4288)
    for _ in range(200):
        p.step()
    assert np.linalg.norm(p.pose()[:2]) < 0.02
    assert (
        np.max(np.abs(p.positions(list(p.targets)) - list(p.targets.values()))) < 0.005
    )
    assert not p.data.warning.number.any()
    assert p.transport_ready()
    for _ in range(400):
        p.step(0.2, 0)
    assert 0.70 < p.pose()[0] < 0.85 and abs(p.pose()[1]) < 0.03
    assert np.linalg.norm(p.pose()[:2] - p.odom[:2]) < 0.03
    for _ in range(250):
        p.step(0, 0.4)
    assert 0.8 < p.pose()[2] < 1.15
    assert abs(p.pose()[2] - p.odom[2]) < 0.1
    p.set_targets(["openarm_left_finger_joint1"], [0.01])
    for _ in range(200):
        p.step()
    assert p.positions(
        ["openarm_left_finger_joint1", "openarm_left_finger_joint2"]
    ) == pytest.approx([0.01, 0.01], abs=0.001)
    assert not p.data.warning.number.any()


def test_lidar_uses_sensor_yaw_and_world_contacts(model_path):
    p = Physics(model_path)
    scan = p.scan()
    assert len(scan) == 360 and np.isfinite(scan).all()
    # The upstream sensor yaw is pi; scan[-pi] points east from x=0.185.
    assert scan[0] == pytest.approx(7.5 - 0.185, abs=0.03)
    assert scan[180] == pytest.approx(7.5 + 0.185, abs=0.03)


def trajectory(positions=((0.0,), (1.0,)), times=(0, 2)):
    return JointTrajectory(
        joint_names=["j"],
        points=[
            JointTrajectoryPoint(positions=list(p), time_from_start=Duration(sec=t))
            for p, t in zip(positions, times)
        ],
    )


def test_trajectory_interpolation_and_validation():
    t = trajectory()
    validate_trajectory(t, ["j"], {"j": (-2, 2)}, 0)
    s = Trajectory(t, [0])
    assert s.sample(1) == pytest.approx([0.5])
    assert s.sample(10) == pytest.approx([1])
    assert Trajectory(trajectory(((1.0,),), (2,)), [0]).sample(1) == pytest.approx(
        [0.5]
    )


@pytest.mark.parametrize(
    "points,times",
    [
        (((float("nan"),), (1.0,)), (0, 2)),
        (((0.0,), (3.0,)), (0, 2)),
        (((0.0,), (1.0,)), (2, 1)),
        (((0.0,), (1.0,)), (0, 0)),
    ],
)
def test_invalid_trajectories_are_rejected(points, times):
    with pytest.raises(ValueError):
        validate_trajectory(trajectory(points, times), ["j"], {"j": (-2, 2)}, 0)


def test_integrated_inertias_are_physically_valid():
    robot = ET.fromstring(expand_urdf())
    for link in robot.findall("link"):
        i = link.find("inertial/inertia")
        if i is None:
            continue
        xx, yy, zz, xy, xz, yz = [
            float(i.get(k)) for k in ["ixx", "iyy", "izz", "ixy", "ixz", "iyz"]
        ]
        eigenvalues = np.linalg.eigvalsh([[xx, xy, xz], [xy, yy, yz], [xz, yz, zz]])
        assert eigenvalues[0] > 0, link.get("name")
        assert eigenvalues[0] + eigenvalues[1] >= eigenvalues[2] - 1e-10, link.get(
            "name"
        )
