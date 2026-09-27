"""Automatic YOLO labels from MuJoCo segmentation renders.

Class map for the lecture (index order is the dataset contract):
    0 person, 1 helmet, 2 safety_vest, 3 parcel_red, 4 parcel_blue, 5 parcel_yellow,
    6 forklift, 7 pallet, 8 cone, 9 extinguisher
"""

import numpy as np

CLASSES = [
    "person",
    "helmet",
    "safety_vest",
    "parcel_red",
    "parcel_blue",
    "parcel_yellow",
    "forklift",
    "pallet",
    "cone",
    "extinguisher",
]
PARCEL_COLORS = {"parcel_1": "parcel_red", "parcel_2": "parcel_blue", "parcel_3": "parcel_yellow"}


def _box_from_mask(mask, min_pixels):
    ys, xs = np.nonzero(mask)
    if len(xs) < min_pixels:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def label_frame(frame, physics, body_labels, actors=None, min_pixels=24):
    """Return [(class_index, (x1, y1, x2, y2)), ...] for one segmented CameraFrame.

    body_labels: MuJoCo body id -> (name, kind) (see HandlerContext.body_labels()).
    Person sub-parts (helmet, vest) are labelled from their geom ids so the detector
    can learn attribute classes; hidden parts (size 0.001) never reach min_pixels.
    """
    seg = frame.segmentation
    if seg is None:
        raise ValueError("Frame was rendered without segmentation")
    model = physics.model
    labels = []
    for body, (name, kind) in body_labels.items():
        mask = seg == body
        box = _box_from_mask(mask, min_pixels)
        if box is None:
            continue
        if kind == "person":
            labels.append((CLASSES.index("person"), box))
            spec = actors.actors[name]["spec"] if actors is not None else {}
            for part, cls, present in (
                ("helmet", "helmet", spec.get("helmet", True)),
                ("vest", "safety_vest", spec.get("vest", "none") != "none"),
            ):
                if not present:
                    continue
                geom = model.geom(f"{name}_{part}").id
                part_box = _geom_box(frame, physics, geom, min_pixels // 2)
                if part_box is not None:
                    labels.append((CLASSES.index(cls), part_box))
        elif kind == "parcel":
            labels.append((CLASSES.index(PARCEL_COLORS.get(name, "parcel_red")), box))
        elif kind in CLASSES:
            labels.append((CLASSES.index(kind), box))
    return labels


def _geom_box(frame, physics, geom_id, min_pixels):
    """Project a geom's bounding sphere to pixels and clip to the body's mask extent."""
    model, data = physics.model, physics.data
    body = model.geom_bodyid[geom_id]
    mask = frame.segmentation == body
    if not mask.any():
        return None
    centre = data.geom_xpos[geom_id]
    radius = float(np.max(model.geom_size[geom_id])) * (1.0 if model.geom_type[geom_id] == 2 else 1.4)
    T = np.linalg.inv(frame.T_world_optical)
    c = (T @ np.r_[centre, 1.0])[:3]
    if c[2] <= 0.05:
        return None
    K = frame.K
    f = K[0, 0]
    u, v = (K @ (c / c[2]))[:2]
    r = f * radius / c[2]
    x1, y1, x2, y2 = int(u - r), int(v - r), int(np.ceil(u + r)), int(np.ceil(v + r))
    h, w = mask.shape
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)
    if x2 <= x1 or y2 <= y1:
        return None
    sub = mask[y1 : y2 + 1, x1 : x2 + 1]
    if sub.sum() < min_pixels:
        return None
    ys, xs = np.nonzero(sub)
    return x1 + int(xs.min()), y1 + int(ys.min()), x1 + int(xs.max()), y1 + int(ys.max())


def to_yolo_lines(labels, width, height):
    lines = []
    for cls, (x1, y1, x2, y2) in labels:
        cx, cy = (x1 + x2 + 1) / 2 / width, (y1 + y2 + 1) / 2 / height
        w, h = (x2 - x1 + 1) / width, (y2 - y1 + 1) / height
        lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return lines


def dataset_yaml(root, names=CLASSES):
    return "\n".join(
        [
            f"path: {root}",
            "train: images/train",
            "val: images/val",
            "names:",
            *[f"  {i}: {n}" for i, n in enumerate(names)],
            "",
        ]
    )
