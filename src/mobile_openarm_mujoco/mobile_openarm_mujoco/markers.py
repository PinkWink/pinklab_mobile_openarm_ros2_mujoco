"""ArUco marker plates in the warehouse: camera-visible, lidar-ignored, contact-free.

Each marker is a textured MuJoCo plane (finite render size) in geom group 2, so the
ray-cast lidar (group 0 only) and the static map never see it, while every camera does.
"""

import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

DICTIONARY = "DICT_4X4_50"


def marker_image(marker_id, size_m, plate_m, pixels=400):
    """White plate with the marker centred; returns a uint8 grayscale image."""
    import cv2

    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, DICTIONARY))
    inner = int(round(pixels * size_m / plate_m))
    border = (pixels - inner) // 2
    canvas = np.full((pixels, pixels), 255, np.uint8)
    canvas[border : border + inner, border : border + inner] = cv2.aruco.generateImageMarker(dictionary, int(marker_id), inner)
    return canvas


def add_markers(asset, worldbody, markers, out_dir):
    """Write marker PNGs into out_dir and append textured planes to the MJCF."""
    if not markers:
        return
    try:
        import cv2
    except ImportError:  # cameras without OpenCV: keep the world buildable
        return
    out = Path(out_dir)
    for spec in markers:
        marker_id = int(spec["id"])
        size, plate = float(spec["size"]), float(spec.get("plate", spec["size"] * 1.25))
        png = out / f"aruco_{marker_id}.png"
        cv2.imwrite(str(png), marker_image(marker_id, size, plate))
        name = f"aruco_{marker_id}"
        ET.SubElement(asset, "texture", name=name, type="2d", file=str(png.resolve()))
        ET.SubElement(asset, "material", name=name, texture=name, texuniform="false", texrepeat="1 1")
        yaw = float(spec.get("normal_yaw", math.pi))
        # Plane +z is the visible normal; local x runs to the viewer's right, local y up.
        x_axis = (-math.sin(yaw), math.cos(yaw), 0.0)
        y_axis = (0.0, 0.0, 1.0)
        body = ET.SubElement(
            worldbody,
            "body",
            name=name,
            pos=" ".join(f"{float(v):.6g}" for v in spec["center"]),
            xyaxes=" ".join(f"{v:.6g}" for v in (*x_axis, *y_axis)),
        )
        ET.SubElement(
            body,
            "geom",
            name=name + "_plate",
            type="plane",
            size=f"{plate / 2:.6g} {plate / 2:.6g} 0.01",
            material=name,
            group="2",
            contype="0",
            conaffinity="0",
        )
