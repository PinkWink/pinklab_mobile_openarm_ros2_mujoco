#!/usr/bin/env python3
"""Conservative 2D projection of the same warehouse boxes used by MuJoCo."""

import argparse
from pathlib import Path
import numpy as np
import yaml
from mobile_openarm_mujoco.model import load_world


def generate(output, world_file=None):
    world = load_world(world_file)
    resolution = 0.05
    origin = np.array([-7.7, -5.7])
    pixels = np.full((228, 308), 254, dtype=np.uint8)
    for box in world["boxes"]:
        center = np.array(box["center"][:2])
        half = np.array(box["size"][:2]) / 2
        low = np.floor((center - half - origin) / resolution).astype(int)
        high = np.ceil((center + half - origin) / resolution).astype(int)
        pixels[
            max(0, low[1]) : min(pixels.shape[0], high[1]),
            max(0, low[0]) : min(pixels.shape[1], high[0]),
        ] = 0
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = output.with_suffix(".pgm")
    image.write_bytes(
        f"P5\n{pixels.shape[1]} {pixels.shape[0]}\n255\n".encode()
        + np.flipud(pixels).tobytes()
    )
    output.write_text(
        yaml.safe_dump(
            {
                "image": image.name,
                "mode": "trinary",
                "resolution": resolution,
                "origin": [*map(float, origin), 0.0],
                "negate": 0,
                "occupied_thresh": 0.65,
                "free_thresh": 0.25,
            },
            sort_keys=False,
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "--output", default="src/mobile_openarm_navigation/maps/warehouse.yaml"
    )
    p.add_argument("--world")
    o = p.parse_args()
    generate(o.output, o.world)
