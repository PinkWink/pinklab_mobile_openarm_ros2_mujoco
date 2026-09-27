"""Example live callback. Replace handle_frames with your Python vision code."""

import json
import os
from pathlib import Path

from PIL import Image
import numpy as np

_last_saved = None


def handle_frames(frames):
    """Receives real live frames directly, without ROS image subscriptions."""
    global _last_saved
    now = next(iter(frames.values())).sim_time
    # Write a latest-frame preview once a simulation second; do not grow a dataset.
    if _last_saved is not None and 0 <= now - _last_saved < 1.0:
        return
    out = (
        Path(
            os.environ.get(
                "MOBILE_OPENARM_MODEL_DIR", str(Path.home() / ".cache/mobile_openarm")
            )
        )
        / "cameras"
    )
    out.mkdir(parents=True, exist_ok=True)
    metadata = {}
    for name, frame in frames.items():
        temporary = out / (name + ".tmp.png")
        Image.fromarray(frame.rgb).save(temporary)
        temporary.replace(out / (name + ".png"))
        if frame.depth_m is not None:
            temporary_depth = out / (name + ".tmp.npy")
            np.save(temporary_depth, frame.depth_m)
            temporary_depth.replace(out / (name + "_depth.npy"))
        metadata[name] = {
            "sim_time": frame.sim_time,
            "K": frame.K.tolist(),
            "T_world_optical": frame.T_world_optical.tolist(),
        }
    temporary = out / "frames.tmp.json"
    temporary.write_text(json.dumps(metadata, indent=2) + "\n")
    temporary.replace(out / "frames.json")
    _last_saved = now
