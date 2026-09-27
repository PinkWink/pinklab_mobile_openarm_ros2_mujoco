"""Camera handler protocol for code that runs inside the live simulator process.

A handler is anything callable with ``handler(frames)`` where ``frames`` maps camera
name -> CameraFrame. Two optional hooks turn it into a full in-process participant:

    class MyHandler:
        def setup(self, context):   # once, before the first frame
            self.pub = context.node.create_publisher(...)
        def __call__(self, frames): ...
        def close(self):            # on shutdown

``--camera-handler module:attribute`` accepts a function, a callable object, or a class
(instantiated with no arguments). The module part may also be a path to a ``.py`` file
(``examples/m1_ros_vision/03_frames_handler.py:FramesHandler``), resolved against the
current directory. No ROS image topics exist; publish results instead.
"""

from dataclasses import dataclass, field
import importlib
import importlib.util
import inspect
from pathlib import Path
import sys


@dataclass
class HandlerContext:
    node: object  # rclpy Node of the simulator bridge (create publishers/subscribers/TF here)
    physics: object  # mobile_openarm_mujoco.model.Physics (model, data, scan(), pose())
    rig: object  # CameraRig (read on this thread only)
    pump: object  # CameraPump (fps is adjustable at runtime)
    settings: dict  # mujoco.yaml
    world: dict  # warehouse.yaml
    actors: object = None  # ActorAnimator or None
    camera_names: tuple = field(default_factory=tuple)
    output_dir: str = ""

    def sim_time(self):
        return float(self.physics.data.time)

    def stamp(self):
        return self.node.sim_stamp()

    def body_labels(self):
        """MuJoCo body id -> (name, kind) for actors and free warehouse objects."""
        labels = {}
        if self.actors is not None:
            labels.update(self.actors.body_labels())
        for obj in self.world.get("objects", []):
            labels[int(self.physics.model.body(obj["name"]).id)] = (obj["name"], "parcel")
        return labels


def load_handler(spec):
    module, separator, attribute = spec.partition(":")
    if not separator or not module or not attribute:
        raise ValueError("--camera-handler must be module:attribute")
    if module.endswith(".py"):
        path = Path(module).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"camera handler file not found: {module}")
        spec_obj = importlib.util.spec_from_file_location(f"camera_handler_{path.stem}", path)
        loaded = importlib.util.module_from_spec(spec_obj)
        sys.modules[spec_obj.name] = loaded  # dataclasses/pickle need the module registered
        spec_obj.loader.exec_module(loaded)
    else:
        loaded = importlib.import_module(module)
    try:
        target = getattr(loaded, attribute)
    except AttributeError as error:
        raise ValueError(f"{module} has no attribute {attribute!r}") from error
    if inspect.isclass(target):
        target = target()
    if not callable(target):
        raise TypeError("Camera handler must be callable")
    return target
