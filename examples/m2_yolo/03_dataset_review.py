#!/usr/bin/env python3
"""M2 예제 3: 수집한 원본(datasets/warehouse_raw)을 학습용 YOLO 데이터셋으로 분할·검토한다.

실행:
    ./scripts/mobile_openarm exec python examples/m2_yolo/03_dataset_review.py [--raw datasets/warehouse_raw] [--out datasets/warehouse] [--val 0.15]
출력:
    datasets/warehouse/{images,labels}/{train,val}  (하드링크: 용량을 두 배로 쓰지 않는다)
    datasets/warehouse/data.yaml                    (ultralytics 학습 입력)
    artifacts/m2/dataset_samples.png, class_hist.png

배우는 점:
- 분할은 "이미지"가 아니라 "장면" 단위로 한다. 같은 순간에 찍은 base/head 두 장은 같은 split 에 둔다 (누수 방지).
- 클래스 불균형을 숫자로 본다. 작은 물체(안전모, 상자)는 인스턴스는 많아도 픽셀이 작아 어렵다.
- 라벨 없는 이미지(negative)도 남긴다. 배경을 배우는 데 필요하다.
- 안전모 균형: person 라벨 대비 helmet 라벨 비율이 0.5 근처여야 "안전모 미착용" 판정이 편향되지 않는다.
"""

import argparse
import collections
import json
import os
import random
from pathlib import Path

import cv2
import yaml

COL = [(0, 255, 0), (0, 255, 255), (255, 128, 0), (0, 0, 255), (255, 0, 0), (0, 200, 255), (255, 0, 255), (120, 120, 255), (0, 140, 255), (255, 255, 255)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="datasets/warehouse_raw")
    ap.add_argument("--out", default="datasets/warehouse")
    ap.add_argument("--val", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    classes = raw.joinpath("classes.txt").read_text().split()
    images = sorted(raw.joinpath("images").glob("*.png"))
    scenes = sorted({p.stem.split("_")[0] for p in images})      # "000123" -> 장면 id (두 카메라 공통)
    random.Random(a.seed).shuffle(scenes)
    n_val = max(1, int(len(scenes) * a.val))
    split_of = {s: ("val" if i < n_val else "train") for i, s in enumerate(scenes)}

    for split in ("train", "val"):
        for kind in ("images", "labels"):
            d = out / kind / split
            if d.exists():
                for f in d.iterdir():
                    f.unlink()
            d.mkdir(parents=True, exist_ok=True)
    counts = {"train": collections.Counter(), "val": collections.Counter()}
    empty = collections.Counter()
    per_image = []
    for img in images:
        split = split_of[img.stem.split("_")[0]]
        lbl = raw / "labels" / (img.stem + ".txt")
        os.link(img, out / "images" / split / img.name)
        os.link(lbl, out / "labels" / split / lbl.name)
        lines = [l for l in lbl.read_text().splitlines() if l.strip()]
        if not lines:
            empty[split] += 1
        for l in lines:
            counts[split][classes[int(l.split()[0])]] += 1
        per_image.append(len(lines))

    data = {"path": str(out.resolve()), "train": "images/train", "val": "images/val", "names": {i: c for i, c in enumerate(classes)}}
    (out / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    print(f"이미지 {len(images)}장 = 장면 {len(scenes)}개 x 카메라 2 -> train {len(images) - sum(1 for i in images if split_of[i.stem.split('_')[0]] == 'val')}, "
          f"val {sum(1 for i in images if split_of[i.stem.split('_')[0]] == 'val')}")
    print(f"라벨 없는 이미지: train {empty['train']}, val {empty['val']} | 이미지당 라벨 평균 {sum(per_image) / max(1, len(per_image)):.1f}")
    print(f"{'class':14s} {'train':>7s} {'val':>6s}")
    for c in classes:
        print(f"{c:14s} {counts['train'][c]:7d} {counts['val'][c]:6d}")
    total = counts["train"] + counts["val"]
    ratio = total["helmet"] / max(1, total["person"])
    print(f"안전모 균형: helmet/person = {ratio:.2f} (0.5 근처가 목표; 사람 박스 중 일부는 머리가 잘려 helmet 이 안 보인다)")

    # 시각화: 무작위 6장 + 클래스 히스토그램
    art = Path("artifacts/m2"); art.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    picks = rng.sample([i for i in images if (raw / "labels" / (i.stem + ".txt")).stat().st_size > 0], 6)
    tiles = []
    for p in picks:
        im = cv2.imread(str(p)); h, w = im.shape[:2]
        for l in (raw / "labels" / (p.stem + ".txt")).read_text().splitlines():
            c, cx, cy, bw, bh = l.split(); c = int(c); cx, cy, bw, bh = map(float, (cx, cy, bw, bh))
            x1, y1, x2, y2 = int((cx - bw / 2) * w), int((cy - bh / 2) * h), int((cx + bw / 2) * w), int((cy + bh / 2) * h)
            cv2.rectangle(im, (x1, y1), (x2, y2), COL[c], 2)
            cv2.putText(im, classes[c], (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COL[c], 1)
        tiles.append(im)
    grid = cv2.vconcat([cv2.hconcat(tiles[:3]), cv2.hconcat(tiles[3:])])
    cv2.imwrite(str(art / "dataset_samples.png"), cv2.resize(grid, None, fx=0.6, fy=0.6))
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 3.5))
        xs = range(len(classes))
        ax.bar([x - 0.2 for x in xs], [counts["train"][c] for c in classes], 0.4, label="train")
        ax.bar([x + 0.2 for x in xs], [counts["val"][c] for c in classes], 0.4, label="val")
        ax.set_xticks(list(xs)); ax.set_xticklabels(classes, rotation=30, ha="right"); ax.set_ylabel("instances"); ax.legend()
        fig.tight_layout(); fig.savefig(art / "class_hist.png", dpi=110)
    except ImportError:
        print("matplotlib 없음: 히스토그램 생략")
    json.dump({"images": len(images), "scenes": len(scenes), "counts": {k: dict(v) for k, v in counts.items()}, "empty": dict(empty), "helmet_ratio": ratio},
              open(art / "dataset_stats.json", "w"), indent=1, ensure_ascii=False)
    print(f"저장: {out}/data.yaml, {art}/dataset_samples.png, class_hist.png")


if __name__ == "__main__":
    main()
