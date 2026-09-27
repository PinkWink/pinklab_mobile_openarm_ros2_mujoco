#!/usr/bin/env python3
"""M2 예제 4: YOLO11n 학습. 수강생은 소규모 CPU 학습으로 절차를 익히고, 전체 학습은 강사 GPU 또는 Colab 에서 한다.

수강생 (CPU, 약 10~15분):
    ./scripts/mobile_openarm exec python examples/m2_yolo/04_train_yolo_cpu.py --subset 300 --epochs 5 --imgsz 320
강사 (GPU 별도 venv; requirements-lecture.txt 는 CPU torch 이므로 학습용 venv 를 따로 만든다):
    python3 -m venv .venv-yolo-gpu && .venv-yolo-gpu/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 ultralytics onnx onnxruntime onnxslim
    .venv-yolo-gpu/bin/python examples/m2_yolo/04_train_yolo_cpu.py --full --epochs 60 --imgsz 640 --device 0
    -> weights/warehouse_yolo11n.pt (배포용). Colab: notebooks/train_yolo_colab.ipynb
    .venv-yolo-gpu/bin/python examples/m2_yolo/04_train_yolo_cpu.py --finetune 320 --epochs 30 --device 0
    -> weights/warehouse_yolo11n_s320.pt: 배포 해상도(320)로 미세조정. 학습·추론 해상도가 다르면 작은 물체 AP 가 크게 떨어진다.
배우는 점:
- 데이터·모델·입력 크기·epoch 가 학습 시간을 결정한다. CPU 에서는 300장 x 320 x 5 epoch 도 10분이 넘는다.
- 결과는 runs/m2/<이름>/ 에 남는다: results.csv(손실·mAP 곡선), confusion_matrix.png, val_batch*.jpg, weights/best.pt.
- 같은 스크립트로 GPU 전체 학습을 돌리면 mAP50 0.9 이상이 나온다. 수강생은 그 가중치(weights/)를 받아 05~07 을 진행한다.
"""

import argparse
import random
import shutil
import time
from pathlib import Path


def make_subset(src, n, seed=0):
    """train 에서 n 장만 뽑은 데이터셋(val 은 그대로). 하드링크라 용량이 늘지 않는다."""
    import os, yaml
    dst = src.parent / f"{src.name}_subset{n}"
    if dst.exists():
        shutil.rmtree(dst)
    for kind in ("images", "labels"):
        (dst / kind / "train").mkdir(parents=True)
        os.symlink((src / kind / "val").resolve(), dst / kind / "val")
    imgs = sorted((src / "images" / "train").glob("*.png"))
    for img in random.Random(seed).sample(imgs, min(n, len(imgs))):
        os.link(img, dst / "images" / "train" / img.name)
        os.link(src / "labels" / "train" / (img.stem + ".txt"), dst / "labels" / "train" / (img.stem + ".txt"))
    data = yaml.safe_load((src / "data.yaml").read_text()); data["path"] = str(dst.resolve())
    (dst / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="datasets/warehouse")
    ap.add_argument("--model", default="yolo11n.pt")
    ap.add_argument("--subset", type=int, default=300, help="train 이미지 수 (--full 이면 무시)")
    ap.add_argument("--full", action="store_true", help="전체 데이터로 학습하고 weights/ 에 배포")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--name", default=None)
    ap.add_argument("--finetune", type=int, default=0, help="weights/warehouse_yolo11n.pt 를 이 해상도로 미세조정해 _s<해상도>.pt 로 저장")
    a = ap.parse_args()
    from ultralytics import YOLO

    data = Path(a.data)
    if a.finetune:
        a.full, a.imgsz, a.model = True, a.finetune, "weights/warehouse_yolo11n.pt"
    if not a.full:
        data = make_subset(data, a.subset)
    name = a.name or (f"finetune_{a.imgsz}" if a.finetune else f"full_{a.imgsz}" if a.full else f"cpu_{a.subset}_{a.imgsz}")
    project = str(Path("runs/m2").resolve())   # 상대 경로면 ultralytics 가 runs/detect/ 아래로 옮긴다
    print(f"학습: {data}/data.yaml, {a.model}, imgsz {a.imgsz}, epochs {a.epochs}, device {a.device} -> {project}/{name}")
    t0 = time.time()
    model = YOLO(a.model)
    model.train(data=str(data / "data.yaml"), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device=a.device,
                workers=a.workers, project=project, name=name, exist_ok=True, plots=True, verbose=False,
                # 시뮬레이터 영상은 조명·색이 단조롭다. 색·크기 증강을 조금 세게 준다.
                hsv_h=0.02, hsv_s=0.6, hsv_v=0.5, scale=0.5, fliplr=0.5, mosaic=1.0, close_mosaic=max(1, a.epochs // 6),
                lr0=0.002 if a.finetune else 0.01, warmup_epochs=1 if a.finetune else 3)
    minutes = (time.time() - t0) / 60
    best = Path(model.trainer.save_dir) / "weights" / "best.pt"
    metrics = YOLO(str(best)).val(data=str(data / "data.yaml"), imgsz=a.imgsz, device=a.device, plots=False, verbose=False)
    print(f"완료 {minutes:.1f}분: mAP50 {metrics.box.map50:.3f}, mAP50-95 {metrics.box.map:.3f} -> {best}")
    if a.full:
        Path("weights").mkdir(exist_ok=True)
        target = f"weights/warehouse_yolo11n_s{a.imgsz}.pt" if a.finetune else "weights/warehouse_yolo11n.pt"
        shutil.copy(best, target)
        print(f"배포: {target}")


if __name__ == "__main__":
    main()
