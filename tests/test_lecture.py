"""warehouse_lecture: labels from segmentation, named locations, worker handler, LLM config."""

import queue
import time
from types import SimpleNamespace

import numpy as np
import pytest

from mobile_openarm_mujoco.actors import load_actors, ActorAnimator
from mobile_openarm_mujoco.cameras import CameraRig
from mobile_openarm_mujoco.handler import HandlerContext
from mobile_openarm_mujoco.model import Physics, build_model, load_world
from warehouse_lecture.vision.labels import CLASSES, label_frame, to_yolo_lines, dataset_yaml
from warehouse_lecture.memory.locations import Locations
from warehouse_lecture.llm.client import load_config, tool_schema


@pytest.fixture(scope="module")
def physics(tmp_path_factory):
    return Physics(build_model(tmp_path_factory.mktemp("lecture")))


def test_segmentation_labels_cover_person_parts_and_parcels(physics):
    p = physics
    anim = ActorAnimator(p.model, p.data, load_actors())
    person = "worker_helmet_orange"
    # 3 m ahead: the base camera sits at 0.21 m, so a helmet at 1.66 m needs distance to stay in view.
    anim.teleport(person, 3.0, 0.0, 3.14)
    labels_by_body = anim.body_labels()
    for obj in load_world()["objects"]:
        labels_by_body[int(p.model.body(obj["name"]).id)] = (obj["name"], "parcel")
    with CameraRig(p.model, p.data, width=320, height=240) as rig:
        frame = rig.read("base_camera", segmentation=True)
        labels = label_frame(frame, p, labels_by_body, actors=anim)
    classes = {CLASSES[c] for c, _ in labels}
    assert {"person", "helmet", "safety_vest"} <= classes
    person_box = next(b for c, b in labels if CLASSES[c] == "person")
    helmet_box = next(b for c, b in labels if CLASSES[c] == "helmet")
    assert helmet_box[1] <= person_box[1] + 5  # helmet sits at the top of the person box
    assert helmet_box[3] - helmet_box[1] < (person_box[3] - person_box[1]) / 3
    lines = to_yolo_lines(labels, 320, 240)
    for line in lines:
        cls, cx, cy, w, h = line.split()
        assert 0 <= int(cls) < len(CLASSES)
        assert all(0 < float(v) <= 1 for v in (cx, cy, w, h))
    assert "names:" in dataset_yaml("/tmp/x") and "9: extinguisher" in dataset_yaml("/tmp/x")
    anim.set_attributes(person, {"helmet": "false", "vest": "none"})
    with CameraRig(p.model, p.data, width=320, height=240) as rig:
        frame = rig.read("base_camera", segmentation=True)
        labels = label_frame(frame, p, labels_by_body, actors=anim)
    assert {CLASSES[c] for c, _ in labels} & {"helmet", "safety_vest"} == set()


def test_locations_resolve_aliases_and_describe_positions():
    loc = Locations()
    assert loc.resolve("픽업 작업대") == "pick_table"
    assert loc.resolve("적재대") == "place_table"
    assert loc.resolve("Pick Station") == "pick_table"
    assert loc.resolve("랙 C") == "rack_c"
    assert loc.resolve("") is None and loc.resolve("달나라") is None
    assert loc.goal("pick_table") == [1.2, -3.6, 0.0]
    assert loc.station("pick_table") == "pick" and loc.station("rack_a") is None
    name, d = loc.nearest(2.3, -3.4)
    assert name == "pick_table" and d < 0.5
    assert "픽업" in loc.describe(2.3, -3.4)
    assert loc.nearest(-7.0, -5.0)[0] is None
    assert len(loc.patrol) >= 5 and all(len(w) == 3 for w in loc.patrol)
    assert "pick_table" in loc.prompt_table()


def test_worker_handler_drops_frames_and_throttles():
    from warehouse_lecture.ros.handler_base import WorkerHandler

    published = []

    class Slow(WorkerHandler):
        def process(self, item):
            time.sleep(0.05)
            return item

        def publish(self, result):
            published.append(result)

    stats = []
    node = SimpleNamespace(
        create_publisher=lambda *_: SimpleNamespace(publish=stats.append),
        get_logger=lambda: SimpleNamespace(error=print),
        sim_stamp=lambda: None,
    )
    clock = {"t": 0.0}
    pump = SimpleNamespace(fps=4.0)
    context = HandlerContext(node=node, physics=None, rig=None, pump=pump, settings={}, world={}, camera_names=("base_camera",))
    context.sim_time = lambda: clock["t"]
    context.stamp = lambda: None
    h = Slow(adaptive=True, min_fps=1.0)
    h.setup(context)
    for i in range(6):
        clock["t"] += 0.1  # simulation advances 0.1 s while wall time advances less
        h(f"frames{i}")
        time.sleep(0.01)
    time.sleep(0.3)
    h("frames-last")
    assert h._dropped >= 2 and published and published[-1] != "frames-last"
    assert stats and stats[-1].dropped_frames == h._dropped
    # Simulation slower than real time -> FPS is lowered towards min_fps.
    for i in range(8):
        clock["t"] += 0.01
        time.sleep(0.03)
        h("x")
    assert pump.fps < 4.0
    h.close()


def test_llm_config_and_tool_schema_are_well_formed():
    cfg = load_config()
    for key in ("chat", "vision"):  # 음성(stt/tts)은 2026-09-22 에 제거
        assert cfg["models"][key]
    assert cfg["pricing"][cfg["models"]["chat"]]["input"] >= 0
    tool = tool_schema("navigate_to", "Go somewhere", {"location": {"type": "string"}})
    assert tool["type"] == "function" and tool["function"]["parameters"]["required"] == ["location"]
    assert tool["function"]["parameters"]["additionalProperties"] is False
