#!/usr/bin/env python3
"""Make the PinkLAB chest logo mesh (OBJ + MTL + texture) from a transparent PNG.

    python3 scripts/make_logo_mesh.py "<logo.png>"      # writes src/mobile_openarm_description/meshes/pinklab_logo.*

The mesh covers only the opaque pixels (horizontal runs on a fine grid), so neither MuJoCo (which ignores
texture alpha) nor RViz draws a square background. Transparent texels get the colour of the nearest logo
pixel, so filtering at the outline never pulls in black. Frame: the logo lies in the y-z plane facing +x,
centred at the origin, SIZE wide (the URDF joint puts it on the chest).
"""
import sys
from pathlib import Path

import cv2
import numpy as np

SIZE = 0.085           # logo width [m]
GRID = 170             # cells across the width (0.5 mm each)
TEX = 512              # texture edge [px]
OUT = Path(__file__).resolve().parents[1] / "src/mobile_openarm_description/meshes"


def main():
    rgba = cv2.imread(sys.argv[1], cv2.IMREAD_UNCHANGED)
    alpha = rgba[:, :, 3]
    ys, xs = np.nonzero(alpha > 8)
    rgba = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = rgba.shape[:2]
    rgba = cv2.resize(rgba, (TEX, round(TEX * h / w)), interpolation=cv2.INTER_AREA)
    alpha = rgba[:, :, 3]
    # Bleed the logo colours outward into the transparent area (nearest opaque pixel).
    _, labels = cv2.distanceTransformWithLabels((alpha < 128).astype(np.uint8), cv2.DIST_L2, 5,
                                                labelType=cv2.DIST_LABEL_PIXEL)
    src = np.zeros((labels.max() + 1, 3), np.uint8)
    opaque = alpha >= 128
    src[labels[opaque]] = rgba[:, :, :3][opaque]
    rgba[:, :, :3] = src[labels]
    OUT.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT / "pinklab_logo.png"), rgba)

    th, tw = alpha.shape
    rows = round(GRID * th / tw)
    mask = cv2.resize((alpha >= 128).astype(np.uint8), (GRID, rows), interpolation=cv2.INTER_AREA) > 0
    cell = SIZE / GRID
    height = rows * cell
    verts, uvs, faces = [], [], []
    for r in range(rows):
        row = np.concatenate([[False], mask[r], [False]])
        edges = np.flatnonzero(row[1:] != row[:-1])
        for c0, c1 in zip(edges[::2], edges[1::2]):           # opaque run [c0, c1)
            z0, z1 = height / 2 - (r + 1) * cell, height / 2 - r * cell
            # Viewer facing the robot (looking along -x) has +y on the right: image column -> +y.
            y0, y1 = -SIZE / 2 + c0 * cell, -SIZE / 2 + c1 * cell
            k = len(verts)
            verts += [(0, y0, z0), (0, y1, z0), (0, y1, z1), (0, y0, z1)]
            u0, u1, v0, v1 = c0 / GRID, c1 / GRID, 1 - (r + 1) / rows, 1 - r / rows
            uvs += [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            faces += [(k, k + 1, k + 2), (k, k + 2, k + 3)]   # counter-clockwise seen from +x
    with open(OUT / "pinklab_logo.obj", "w") as f:
        f.write("# PinkLAB logo, made by scripts/make_logo_mesh.py\nmtllib pinklab_logo.mtl\nusemtl pinklab_logo\n")
        f.writelines(f"v {x:.6f} {y:.6f} {z:.6f}\n" for x, y, z in verts)
        f.writelines(f"vt {u:.6f} {v:.6f}\n" for u, v in uvs)
        f.write("vn 1 0 0\n")
        f.writelines(f"f {a + 1}/{a + 1}/1 {b + 1}/{b + 1}/1 {c + 1}/{c + 1}/1\n" for a, b, c in faces)
    (OUT / "pinklab_logo.mtl").write_text("newmtl pinklab_logo\nKa 1 1 1\nKd 1 1 1\nKs 0.1 0.1 0.1\nmap_Kd pinklab_logo.png\n")
    print(f"{len(faces)} triangles, {SIZE * 100:.1f} x {height * 100:.1f} cm -> {OUT}")


if __name__ == "__main__":
    main()
