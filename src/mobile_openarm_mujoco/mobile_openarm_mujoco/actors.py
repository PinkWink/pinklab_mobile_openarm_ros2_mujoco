"""Warehouse actors: primitive people with visible safety attributes, plus static props.

Actors are MuJoCo mocap bodies. They are visible to the cameras and to the ray-cast
lidar (geom group 0, opaque), but they do not exert contact forces on the robot
(contype/conaffinity 0). Navigation must avoid them through the Nav2 obstacle layer.
"""

from pathlib import Path
import math
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from ament_index_python.packages import get_package_share_directory

KINDS = ("person", "forklift", "pallet", "cone", "extinguisher")
VESTS = ("orange", "green", "none")
PERSON_ATTRIBUTES = ("helmet", "vest", "shirt", "height")


def load_actors(path=None):
    if path in ("none", ""):
        return {"colors": {}, "actors": []}
    file = Path(
        path
        or Path(get_package_share_directory("mobile_openarm_mujoco"))
        / "worlds/actors.yaml"
    )
    data = yaml.safe_load(file.read_text()) or {}
    data.setdefault("colors", {})
    data.setdefault("actors", [])
    names = [a["name"] for a in data["actors"]]
    if len(names) != len(set(names)):
        raise ValueError("Actor names must be unique")
    for actor in data["actors"]:
        if actor.get("kind") not in KINDS:
            raise ValueError(f"Unknown actor kind for {actor.get('name')}: {actor.get('kind')}")
        actor.setdefault("pose", [0.0, 0.0, 0.0])
        if actor["kind"] == "person":
            actor.setdefault("helmet", True)
            actor.setdefault("vest", "none")
            actor.setdefault("shirt", "gray")
            actor.setdefault("height", 1.7)
            if actor["vest"] not in VESTS:
                raise ValueError(f"Unknown vest for {actor['name']}: {actor['vest']}")
            if not 1.4 <= float(actor["height"]) <= 2.1:
                raise ValueError(f"Unrealistic height for {actor['name']}")
    return data


def _vec(values):
    return " ".join(f"{float(x):.6g}" for x in values)


def yaw_quat(yaw):
    return [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]


def _color(colors, name, default=(0.5, 0.5, 0.5, 1)):
    return colors.get(name, default)


def _geom(body, name, **attrs):
    attrs.setdefault("group", "0")
    attrs.setdefault("contype", "0")
    attrs.setdefault("conaffinity", "0")
    return ET.SubElement(body, "geom", name=name, **attrs)


def _person(body, actor, colors):
    s = float(actor["height"]) / 1.7
    n = actor["name"]
    pants = _vec(_color(colors, "pants"))
    shirt = _vec(_color(colors, actor["shirt"]))
    skin = _vec(_color(colors, "skin"))
    for side, x in (("l", -0.09), ("r", 0.09)):
        _geom(
            body,
            f"{n}_leg_{side}",
            type="capsule",
            fromto=_vec([x * s, 0, 0.12 * s, x * s, 0, 0.80 * s]),
            size=str(0.075 * s),
            rgba=pants,
        )
    _geom(
        body,
        f"{n}_torso",
        type="box",
        pos=_vec([0, 0, 1.08 * s]),
        size=_vec([0.18 * s, 0.11 * s, 0.30 * s]),
        rgba=shirt,
    )
    # Vest wraps the middle of the torso so shirt colour stays visible at shoulders.
    vest = actor["vest"]
    vest_rgba = _color(colors, vest + "_vest", (1, 0.45, 0.05, 1))
    _geom(
        body,
        f"{n}_vest",
        type="box",
        pos=_vec([0, 0, 1.06 * s]),
        size=_vec([0.19 * s, 0.12 * s, 0.20 * s]) if vest != "none" else "0.001 0.001 0.001",
        rgba=_vec(vest_rgba) if vest != "none" else "0 0 0 0",
    )
    for side, x in (("l", -0.25), ("r", 0.25)):
        _geom(
            body,
            f"{n}_arm_{side}",
            type="capsule",
            fromto=_vec([x * s, 0, 1.32 * s, (x + math.copysign(0.03, x)) * s, 0, 0.86 * s]),
            size=str(0.045 * s),
            rgba=shirt,
        )
    _geom(
        body,
        f"{n}_head",
        type="sphere",
        pos=_vec([0, 0, 1.55 * s]),
        size=str(0.11 * s),
        rgba=skin,
    )
    helmet = bool(actor["helmet"])
    _geom(
        body,
        f"{n}_helmet",
        type="sphere",
        pos=_vec([0, 0, 1.585 * s]),
        size=str(0.125 * s) if helmet else "0.001",
        rgba=_vec(_color(colors, "helmet", (0.98, 0.85, 0.1, 1))) if helmet else "0 0 0 0",
    )


def _forklift(body, actor, colors):
    n = actor["name"]
    yellow, dark = "0.95 0.65 0.05 1", "0.15 0.15 0.15 1"
    _geom(body, f"{n}_chassis", type="box", pos="0 0 0.45", size="0.75 0.5 0.35", rgba=yellow)
    _geom(body, f"{n}_counterweight", type="box", pos="-0.7 0 0.4", size="0.25 0.45 0.3", rgba=dark)
    for side, y in (("l", 0.4), ("r", -0.4)):
        for end, x in (("f", 0.45), ("b", -0.55)):
            _geom(body, f"{n}_wheel_{side}{end}", type="cylinder", pos=_vec([x, y, 0.22]), size="0.22 0.1",
                  quat="0.7071 0.7071 0 0", rgba=dark)
        _geom(body, f"{n}_post_{side}", type="box", pos=_vec([0.0, y * 0.9, 1.45]), size="0.04 0.04 0.7", rgba=dark)
        _geom(body, f"{n}_mast_{side}", type="box", pos=_vec([0.95, y * 0.55, 1.1]), size="0.04 0.04 1.1", rgba=dark)
        _geom(body, f"{n}_fork_{side}", type="box", pos=_vec([1.6, y * 0.45, 0.08]), size="0.6 0.06 0.02", rgba="0.6 0.6 0.62 1")
    _geom(body, f"{n}_roof", type="box", pos="0 0 2.15", size="0.6 0.45 0.03", rgba=dark)
    _geom(body, f"{n}_seat", type="box", pos="-0.2 0 0.95", size="0.25 0.25 0.15", rgba="0.25 0.25 0.3 1")


def _pallet(body, actor, colors):
    n = actor["name"]
    wood = "0.72 0.55 0.32 1"
    _geom(body, f"{n}_deck", type="box", pos="0 0 0.125", size="0.6 0.4 0.02", rgba=wood)
    for i, y in enumerate((-0.36, 0.0, 0.36)):
        _geom(body, f"{n}_stringer_{i}", type="box", pos=_vec([0, y, 0.05]), size="0.6 0.04 0.05", rgba=wood)
    _geom(body, f"{n}_load", type="box", pos="0 0 0.5", size="0.5 0.35 0.35", rgba="0.62 0.44 0.26 1")


def _cone(body, actor, colors):
    n = actor["name"]
    orange = "1.0 0.4 0.05 1"
    _geom(body, f"{n}_base", type="box", pos="0 0 0.02", size="0.2 0.2 0.02", rgba=orange)
    _geom(body, f"{n}_body", type="cylinder", pos="0 0 0.38", size="0.09 0.34", rgba=orange)
    _geom(body, f"{n}_stripe", type="cylinder", pos="0 0 0.5", size="0.092 0.05", rgba="0.95 0.95 0.95 1")


def _extinguisher(body, actor, colors):
    n = actor["name"]
    _geom(body, f"{n}_tank", type="cylinder", pos="0 0 0.28", size="0.08 0.25", rgba="0.85 0.1 0.1 1")
    _geom(body, f"{n}_valve", type="cylinder", pos="0 0 0.58", size="0.03 0.05", rgba="0.15 0.15 0.15 1")
    _geom(body, f"{n}_hose", type="capsule", fromto="0.06 0 0.55 0.12 0 0.25", size="0.015", rgba="0.1 0.1 0.1 1")


BUILDERS = {
    "person": _person,
    "forklift": _forklift,
    "pallet": _pallet,
    "cone": _cone,
    "extinguisher": _extinguisher,
}


def add_actors(worldbody, actors):
    """Append one mocap body per actor to an MJCF worldbody element."""
    colors = actors.get("colors", {})
    for actor in actors["actors"]:
        x, y, yaw = actor["pose"]
        body = ET.SubElement(
            worldbody,
            "body",
            name=actor["name"],
            mocap="true",
            pos=_vec([x, y, 0]),
            quat=_vec(yaw_quat(yaw)),
        )
        BUILDERS[actor["kind"]](body, actor, colors)


class ActorAnimator:
    """Moves mocap actors along waypoints and exposes ground-truth state."""

    def __init__(self, model, data, actors):
        self.model, self.data = model, data
        self.colors = actors.get("colors", {})
        self.actors = {}
        for actor in actors["actors"]:
            body = model.body(actor["name"])
            mocap = int(model.body_mocapid[body.id])
            if mocap < 0:
                raise ValueError(f"Actor {actor['name']} is not a mocap body")
            state = {
                "spec": actor,
                "body_id": body.id,
                "mocap": mocap,
                "yaw": float(actor["pose"][2]),
                "velocity": np.zeros(3),
                "paused": False,
                "path": None,
            }
            self.actors[actor["name"]] = state
            path = actor.get("path")
            if path:
                self.set_path(actor["name"], path["waypoints"], path.get("speed", 0.5),
                              path.get("wait_s", 0.0), path.get("loop", True))

    # --- path following -------------------------------------------------
    def set_path(self, name, waypoints, speed=0.5, wait_s=0.0, loop=True):
        points = [np.array([float(p[0]), float(p[1])]) for p in waypoints]
        if not points:
            raise ValueError("Path needs at least one waypoint")
        if not 0 < float(speed) <= 2.0:
            raise ValueError("Actor speed must be within (0, 2] m/s")
        self.actors[name]["path"] = {
            "points": points,
            "speed": float(speed),
            "wait": float(wait_s),
            "loop": bool(loop),
            "index": 0,
            "wait_until": -1.0,
        }

    def teleport(self, name, x, y, yaw=None):
        state = self.actors[name]
        self.data.mocap_pos[state["mocap"]] = [x, y, 0.0]
        if yaw is not None:
            state["yaw"] = float(yaw)
            self.data.mocap_quat[state["mocap"]] = yaw_quat(state["yaw"])
        state["velocity"][:] = 0
        if state["path"]:
            state["path"]["index"] = 0

    def pause(self, name, paused=True):
        self.actors[name]["paused"] = paused
        self.actors[name]["velocity"][:] = 0

    def update(self, dt):
        for name, state in self.actors.items():
            path = state["path"]
            if path is None or state["paused"]:
                continue
            m = state["mocap"]
            position = self.data.mocap_pos[m][:2].copy()
            if self.data.time < path["wait_until"]:
                state["velocity"][:] = 0
                continue
            target = path["points"][path["index"]]
            delta = target - position
            distance = float(np.linalg.norm(delta))
            step = path["speed"] * dt
            if distance <= step:
                position = target
                state["velocity"][:] = 0
                next_index = path["index"] + 1
                if next_index >= len(path["points"]):
                    if not path["loop"]:
                        path["index"] = len(path["points"]) - 1
                        self.data.mocap_pos[m][:2] = position
                        state["path"] = None
                        continue
                    next_index = 0
                path["index"] = next_index
                path["wait_until"] = self.data.time + path["wait"]
            else:
                direction = delta / distance
                position = position + direction * step
                state["velocity"][:2] = direction * path["speed"]
                state["yaw"] = math.atan2(direction[1], direction[0])
                self.data.mocap_quat[m] = yaw_quat(state["yaw"])
            self.data.mocap_pos[m][:2] = position

    # --- attributes -----------------------------------------------------
    def attributes(self, name):
        spec = self.actors[name]["spec"]
        if spec["kind"] != "person":
            return {}
        return {
            "helmet": "true" if spec["helmet"] else "false",
            "vest": spec["vest"],
            "shirt": spec["shirt"],
            "height": f"{float(spec['height']):.2f}",
        }

    def set_attributes(self, name, attributes):
        """Change a person's visible attributes in the live model (helmet, vest, shirt)."""
        state = self.actors[name]
        spec = state["spec"]
        if spec["kind"] != "person":
            raise ValueError(f"{name} is not a person")
        s = float(spec["height"]) / 1.7
        for key, value in attributes.items():
            if key == "helmet":
                helmet = str(value).lower() in ("1", "true", "yes", "on")
                spec["helmet"] = helmet
                g = self.model.geom(f"{name}_helmet")
                g.size[0] = 0.125 * s if helmet else 0.001
                g.rgba[:] = _color(self.colors, "helmet", (0.98, 0.85, 0.1, 1)) if helmet else (0, 0, 0, 0)
            elif key == "vest":
                if value not in VESTS:
                    raise ValueError(f"Unknown vest: {value}")
                spec["vest"] = value
                g = self.model.geom(f"{name}_vest")
                if value == "none":
                    g.size[:] = [0.001, 0.001, 0.001]
                    g.rgba[:] = (0, 0, 0, 0)
                else:
                    g.size[:] = [0.19 * s, 0.12 * s, 0.20 * s]
                    g.rgba[:] = _color(self.colors, value + "_vest", (1, 0.45, 0.05, 1))
            elif key == "shirt":
                if value not in self.colors:
                    raise ValueError(f"Unknown colour: {value}")
                spec["shirt"] = value
                for geom in (f"{name}_torso", f"{name}_arm_l", f"{name}_arm_r"):
                    self.model.geom(geom).rgba[:] = self.colors[value]
            else:
                raise ValueError(f"Attribute {key} cannot be changed at runtime")

    # --- ground truth ---------------------------------------------------
    def states(self):
        """Name -> dict(kind, position xyz, quat wxyz, velocity, moving, attributes)."""
        out = {}
        for name, state in self.actors.items():
            m = state["mocap"]
            out[name] = {
                "kind": state["spec"]["kind"],
                "position": self.data.mocap_pos[m].copy(),
                "quat": self.data.mocap_quat[m].copy(),
                "velocity": state["velocity"].copy(),
                "moving": bool(np.any(state["velocity"] != 0)),
                "attributes": self.attributes(name),
            }
        return out

    def body_labels(self):
        """MuJoCo body id -> (actor name, kind) for segmentation-based labelling."""
        return {s["body_id"]: (n, s["spec"]["kind"]) for n, s in self.actors.items()}
