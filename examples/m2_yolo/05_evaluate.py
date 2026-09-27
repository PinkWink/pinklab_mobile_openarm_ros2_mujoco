#!/usr/bin/env python3
"""M2 예제 5: 배포 가중치를 val 분할로 평가한다. mAP, 클래스별 AP, 혼동 행렬, 실패 사례, 안전모 유무 정확도.

실행:
    ./scripts/mobile_openarm exec python examples/m2_yolo/05_evaluate.py [--weights weights/warehouse_yolo11n.pt] [--imgsz 640 320]
출력: artifacts/m2/eval_<imgsz>.json, confusion_matrix_<imgsz>.png, failures_<imgsz>.png

배우는 점:
- mAP50 은 "IoU 0.5 이상으로 맞춘 박스" 기준 평균 정밀도. 학습 해상도(640)와 배포 해상도(320)에서 각각 본다.
  작은 물체(안전모, 상자)는 320 에서 가장 먼저 떨어진다.
- 혼동 행렬은 어떤 클래스가 서로 섞이는지(예: 조끼 색 vs 셔츠) 보여준다.
- 실패 사례를 눈으로 보는 것이 숫자보다 다음 할 일을 잘 알려준다 (가림, 작은 크기, 라벨 잡음).
- 안전모 유무 정확도: 사람 박스마다 "안에 helmet 박스가 있는가"를 정답과 예측으로 비교한다. M3·M5 의 속성 판정 규칙과 같다.
"""

import argparse
import json
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml


def iou(a, b):
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def read_labels(path, w, h, classes):
    out = []
    if not path.exists():
        return out
    for l in path.read_text().splitlines():
        if not l.strip():
            continue
        c, cx, cy, bw, bh = l.split(); cx, cy, bw, bh = map(float, (cx, cy, bw, bh))
        out.append((classes[int(c)], (int((cx - bw / 2) * w), int((cy - bh / 2) * h), int((cx + bw / 2) * w), int((cy + bh / 2) * h))))
    return out


def has_helmet(person_box, boxes):
    """사람 박스 위쪽 40 % 안에 중심이 있는 helmet 박스가 있으면 착용."""
    x1, y1, x2, y2 = person_box
    for label, (hx1, hy1, hx2, hy2) in boxes:
        if label != "helmet":
            continue
        cx, cy = (hx1 + hx2) / 2, (hy1 + hy2) / 2
        if x1 - 4 <= cx <= x2 + 4 and y1 - 8 <= cy <= y1 + 0.4 * (y2 - y1):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/warehouse_yolo11n.pt")
    ap.add_argument("--data", default="datasets/warehouse/data.yaml")
    ap.add_argument("--imgsz", type=int, nargs="+", default=[640, 320])
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--failures", type=int, default=6)
    a = ap.parse_args()
    from ultralytics import YOLO

    data = yaml.safe_load(Path(a.data).read_text())
    classes = [data["names"][i] for i in sorted(data["names"])]
    val_dir = Path(data["path"]) / data["val"]
    images = sorted(val_dir.glob("*.png"))
    art = Path("artifacts/m2"); art.mkdir(parents=True, exist_ok=True)
    model = YOLO(a.weights)
    for imgsz in a.imgsz:
        # 1) 표준 지표
        r = model.val(data=a.data, imgsz=imgsz, device="cpu", conf=0.001, plots=True, verbose=False, project=str(Path("runs/m2").resolve()), name=f"val_{imgsz}", exist_ok=True)
        per_class = {classes[int(c)]: float(v) for c, v in zip(r.box.ap_class_index, r.box.ap50)}
        cm = Path(r.save_dir) / "confusion_matrix.png"
        if cm.exists():
            shutil.copy(cm, art / f"confusion_matrix_{imgsz}.png")
        # 2) 사람별 안전모 유무 + 실패 사례 (conf 임계 적용, 배포 조건과 같게)
        helmet_total = helmet_correct = 0
        scored = []
        for img_path in images:
            im = cv2.imread(str(img_path)); h, w = im.shape[:2]
            gt = read_labels(Path(str(img_path).replace("/images/", "/labels/")).with_suffix(".txt"), w, h, classes)
            res = model.predict(im, imgsz=imgsz, conf=a.conf, device="cpu", verbose=False)[0]
            pred = [(classes[int(c)], tuple(int(v) for v in b)) for b, c in zip(res.boxes.xyxy.cpu().numpy(), res.boxes.cls.cpu().numpy())]
            # 매칭: 같은 클래스, IoU >= 0.5
            unmatched_gt = [g for g in gt if not any(p[0] == g[0] and iou(p[1], g[1]) >= 0.5 for p in pred)]
            unmatched_pred = [p for p in pred if not any(p[0] == g[0] and iou(p[1], g[1]) >= 0.5 for g in gt)]
            scored.append((len(unmatched_gt) + len(unmatched_pred), img_path, gt, pred, unmatched_gt, unmatched_pred))
            for label, box in gt:
                if label != "person" or (box[3] - box[1]) < 40:
                    continue                                   # 아주 작은(먼) 사람은 판정 대상에서 뺀다
                matched = [p for p in pred if p[0] == "person" and iou(p[1], box) >= 0.5]
                if not matched:
                    continue
                helmet_total += 1
                helmet_correct += has_helmet(box, gt) == has_helmet(matched[0][1], pred)
        helmet_acc = helmet_correct / max(1, helmet_total)
        # 3) 실패 사례 그림: 오류 수가 많은 이미지. 초록 = 정답, 빨강 = 예측, 노랑 = 놓친 정답
        scored.sort(key=lambda t: -t[0])
        tiles = []
        for _, img_path, gt, pred, ug, up in scored[: a.failures]:
            im = cv2.imread(str(img_path))
            for label, (x1, y1, x2, y2) in gt:
                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 200, 0), 1)
            for label, (x1, y1, x2, y2) in up:
                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 2); cv2.putText(im, "FP " + label, (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
            for label, (x1, y1, x2, y2) in ug:
                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 255), 2); cv2.putText(im, "miss " + label, (x1, min(im.shape[0] - 4, y2 + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
            tiles.append(im)
        while len(tiles) % 3:
            tiles.append(np.zeros_like(tiles[0]))
        rows = [cv2.hconcat(tiles[i:i + 3]) for i in range(0, len(tiles), 3)]
        cv2.imwrite(str(art / f"failures_{imgsz}.png"), cv2.resize(cv2.vconcat(rows), None, fx=0.6, fy=0.6))
        summary = {"weights": a.weights, "imgsz": imgsz, "map50": float(r.box.map50), "map50_95": float(r.box.map), "ap50_per_class": per_class,
                   "helmet_accuracy": helmet_acc, "helmet_persons": helmet_total, "val_images": len(images), "conf": a.conf}
        (art / f"eval_{imgsz}.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
        print(f"\n=== imgsz {imgsz}: mAP50 {r.box.map50:.3f}  mAP50-95 {r.box.map:.3f}  안전모 유무 정확도 {helmet_acc * 100:.1f}% ({helmet_total}명)")
        for c in classes:
            print(f"  AP50 {c:14s} {per_class.get(c, float('nan')):.3f}")
        print(f"  저장: {art}/eval_{imgsz}.json, confusion_matrix_{imgsz}.png, failures_{imgsz}.png")


if __name__ == "__main__":
    main()
