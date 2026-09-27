"""Actors: mocap people/props visible to lidar and cameras, movable, with attributes."""

import numpy as np
import pytest

from mobile_openarm_mujoco.actors import load_actors, ActorAnimator, PERSON_ATTRIBUTES
from mobile_openarm_mujoco.cameras import CameraRig
from mobile_openarm_mujoco.handler import HandlerContext, load_handler
from mobile_openarm_mujoco.model import Physics, build_model, load_world


@pytest.fixture(scope="module")
def paths(tmp_path_factory):
    root = tmp_path_factory.mktemp("actors")
    return build_model(root / "with"), build_model(root / "without", actors_file="none")


def test_actor_spec_is_valid_and_balanced(tmp_path):
    spec = load_actors()
    people = [a for a in spec["actors"] if a["kind"] == "person"]
    assert len(people) >= 4
    assert sum(a["helmet"] for a in people) == len(people) // 2
    for a in people:
        assert set(PERSON_ATTRIBUTES) <= set(a)
    assert load_actors("none")["actors"] == []
    for bad in [
        "actors:\n- {name: a, kind: dragon}\n",
        "actors:\n- {name: a, kind: person, vest: purple}\n",
        "actors:\n- {name: a, kind: cone}\n- {name: a, kind: cone}\n",
        "actors:\n- {name: a, kind: person, height: 3.0}\n",
    ]:
        file = tmp_path / "bad.yaml"
        file.write_text(bad)
        with pytest.raises(ValueError):
            load_actors(file)


def test_actors_are_mocap_lidar_visible_and_contact_free(paths):
    with_actors, without = Physics(paths[0]), Physics(paths[1])
    spec = load_actors()
    assert with_actors.model.nmocap == len(spec["actors"]) and without.model.nmocap == 0
    changed = np.abs(with_actors.scan() - without.scan()) > 0.05
    assert changed.sum() >= 10  # cones, people and props intersect lidar rays
    # East/west reference rays used by the base lidar test stay clear.
    assert with_actors.scan()[0] == pytest.approx(without.scan()[0], abs=0.03)
    assert with_actors.scan()[180] == pytest.approx(without.scan()[180], abs=0.03)
    for actor in spec["actors"]:
        body = with_actors.model.body(actor["name"]).id
        geoms = np.nonzero(with_actors.model.geom_bodyid == body)[0]
        assert len(geoms) > 0
        assert (with_actors.model.geom_contype[geoms] == 0).all()
        assert (with_actors.model.geom_conaffinity[geoms] == 0).all()
        assert (with_actors.model.geom_group[geoms] == 0).all()


def test_animator_walks_waits_and_keeps_robot_still(paths):
    p = Physics(paths[0])
    anim = ActorAnimator(p.model, p.data, load_actors())
    walker = next(n for n, s in anim.actors.items() if s["path"])
    start = anim.states()[walker]["position"].copy()
    for _ in range(900):
        anim.update(p.bridge_period)
        p.step()
    moved = np.linalg.norm(anim.states()[walker]["position"] - start)
    assert moved > 1.0 and anim.states()[walker]["moving"]
    assert np.linalg.norm(p.pose()[:2]) < 0.02 and not p.data.warning.number.any()
    anim.pause(walker)
    before = anim.states()[walker]["position"].copy()
    for _ in range(100):
        anim.update(p.bridge_period)
    assert np.allclose(anim.states()[walker]["position"], before)
    anim.teleport(walker, 1.0, -1.0, 0.5)
    assert np.allclose(anim.states()[walker]["position"][:2], [1.0, -1.0])
    with pytest.raises(ValueError):
        anim.set_path(walker, [[0, 0]], speed=5.0)


def test_person_attributes_change_live_model(paths):
    p = Physics(paths[0])
    anim = ActorAnimator(p.model, p.data, load_actors())
    person = next(n for n, s in anim.actors.items() if s["spec"]["kind"] == "person")
    anim.set_attributes(person, {"helmet": "false", "vest": "none", "shirt": "red"})
    assert anim.attributes(person)["helmet"] == "false"
    assert p.model.geom(person + "_helmet").size[0] < 0.01
    assert p.model.geom(person + "_vest").rgba[3] == 0
    anim.set_attributes(person, {"helmet": "true", "vest": "green"})
    assert p.model.geom(person + "_helmet").size[0] > 0.1
    assert p.model.geom(person + "_vest").rgba[1] > 0.9
    with pytest.raises(ValueError):
        anim.set_attributes(person, {"vest": "purple"})
    prop = next(n for n, s in anim.actors.items() if s["spec"]["kind"] != "person")
    with pytest.raises(ValueError):
        anim.set_attributes(prop, {"helmet": "true"})


def test_segmentation_boxes_label_actors_and_parcels(paths):
    p = Physics(paths[0])
    anim = ActorAnimator(p.model, p.data, load_actors())
    anim.teleport("cone_1", 1.2, 0.0, 0.0)
    with CameraRig(p.model, p.data, width=320, height=240) as rig:
        frame = rig.read("base_camera", depth=True, segmentation=True)
        assert frame.segmentation.shape == (240, 320) and frame.segmentation.dtype == np.int32
        labels = {}
        labels.update(anim.body_labels())
        for obj in load_world()["objects"]:
            labels[int(p.model.body(obj["name"]).id)] = (obj["name"], "parcel")
        boxes = rig.body_boxes(frame.segmentation)
        named = {labels[b][0]: box for b, box in boxes.items() if b in labels}
        assert "cone_1" in named
        x1, y1, x2, y2 = named["cone_1"]
        assert 0 <= x1 < x2 < 320 and 0 <= y1 < y2 < 240
        assert np.isfinite(frame.depth_m[(y1 + y2) // 2, (x1 + x2) // 2])
        assert frame.depth_m[(y1 + y2) // 2, (x1 + x2) // 2] == pytest.approx(1.2 - 0.33, abs=0.15)


def test_handler_loading_accepts_function_object_and_class():
    assert callable(load_handler("mobile_openarm_mujoco.camera_demo:handle_frames"))
    for bad in ["nomodule", "mobile_openarm_mujoco.camera_demo:", ":x"]:
        with pytest.raises(ValueError):
            load_handler(bad)
    with pytest.raises(TypeError):
        load_handler("mobile_openarm_mujoco.camera_demo:_last_saved")
    context = HandlerContext(node=None, physics=None, rig=None, pump=None, settings={}, world={})
    assert context.camera_names == () and context.actors is None


def test_handler_loading_accepts_file_path(tmp_path):
    source = tmp_path / "03_student_handler.py"
    source.write_text("class Student:\n    def __call__(self, frames):\n        self.last = frames\n")
    handler = load_handler(f"{source}:Student")
    handler({})
    assert handler.last == {}
    with pytest.raises(ValueError):
        load_handler(f"{tmp_path / 'missing.py'}:Student")
    with pytest.raises(ValueError):
        load_handler(f"{source}:Nope")
