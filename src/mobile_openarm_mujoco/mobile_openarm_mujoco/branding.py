"""PinkLAB logo on the OpenArm chest (URDF link pinklab_logo, mesh from scripts/make_logo_mesh.py).

The generic URDF -> MJCF mesh conversion (trimesh -> OBJ) drops texture coordinates, so the logo mesh is
loaded as is, with its texture. The mesh is a single sheet; inertia="shell" keeps MuJoCo from needing a
closed volume (the link has no mass anyway).
"""

from pathlib import Path
import xml.etree.ElementTree as ET

MESH = "pinklab_logo.obj"


def is_logo(path):
    return Path(path).name == MESH


def logo_geom(asset, path):
    """Add the logo mesh, texture and material to <asset>; return the geom attributes."""
    path = Path(path).resolve()
    if asset.find("mesh[@name='pinklab_logo']") is None:
        ET.SubElement(asset, "texture", name="pinklab_logo", type="2d", file=str(path.with_suffix(".png")))
        ET.SubElement(asset, "material", name="pinklab_logo", texture="pinklab_logo", specular="0.2", shininess="0.3",
                      emission="0.35")
        ET.SubElement(asset, "mesh", name="pinklab_logo", file=str(path), inertia="shell")
    return dict(type="mesh", mesh="pinklab_logo", material="pinklab_logo", rgba="1 1 1 1")
