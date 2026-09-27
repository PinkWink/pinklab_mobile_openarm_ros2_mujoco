#!/usr/bin/env python3
"""M2 예제 6: CPU 배포 최적화. 입력 크기(640/416/320) x 백엔드(PyTorch/ONNX Runtime/OpenVINO/OpenVINO INT8) x 스레드 수의
지연·정확도 표를 만든다. 수강생 PC 조건으로 재려면 4코어로 제한한다.

실행:
    taskset -c 0-3 ./scripts/mobile_openarm exec python examples/m2_yolo/06_optimize_cpu.py [--weights weights/warehouse_yolo11n.pt]
        [--imgsz 640 416 320] [--threads 4 2 1] [--skip-int8] [--no-map]
출력: weights/warehouse_yolo11n_<imgsz>.onnx, weights/warehouse_yolo11n_<imgsz>_openvino_model/, ..._int8_openvino_model/
      artifacts/m2/benchmark_<가중치이름>.md / .json

배우는 점:
- 지연은 입력 픽셀 수에 거의 비례한다(640→320 은 약 4배). 정확도는 작은 물체에서 먼저 떨어진다. 둘의 교점을 찾는다.
- 같은 네트워크라도 런타임이 다르면 CPU 에서 2~3배 차이 난다. OpenVINO 는 Intel CPU 에서 가장 빠른 편이다.
- INT8 양자화는 보정(calibration) 데이터가 필요하고 정확도가 조금 떨어질 수 있다. 표로 확인한다.
- 스레드 열은 이 환경에서 차이가 없다: ultralytics/OpenVINO/ONNX Runtime 이 프로세스의 CPU affinity 로 스레드 수를 정하고
  OMP_NUM_THREADS·torch.set_num_threads 는 사실상 무시된다. 실제 변수는 코어 수다 (taskset -c 0 / 0-3 로 비교해 볼 것.
  Ryzen 9700X: OpenVINO 640 입력 1코어 17 ms, 4코어 6 ms). 시뮬레이터·ROS 와 CPU 를 나눠 쓰므로 핸들러 몫은 1~2코어로 본다.
- 목표(계획서): 4코어, 320 입력, 프레임당 60 ms 이하.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def export_all(weights, imgszs, skip_int8, data):
    from ultralytics import YOLO
    out = {}
    stem = Path(weights).with_suffix("")
    for s in imgszs:
        onnx = Path(f"{stem}_{s}.onnx")
        ov = Path(f"{stem}_{s}_openvino_model")
        ov8 = Path(f"{stem}_{s}_int8_openvino_model")
        if not onnx.exists():
            p = YOLO(weights).export(format="onnx", imgsz=s, opset=17, simplify=True, dynamic=False)
            Path(p).rename(onnx)
        if not ov.exists():
            p = YOLO(weights).export(format="openvino", imgsz=s, half=False)
            Path(p).rename(ov)
        if not skip_int8 and not ov8.exists():
            p = YOLO(weights).export(format="openvino", imgsz=s, int8=True, data=data)
            Path(p).rename(ov8)
        out[s] = {"pytorch": weights, "onnx": str(onnx), "openvino": str(ov)}
        if not skip_int8:
            out[s]["openvino_int8"] = str(ov8)
    return out


def bench_one(path, imgsz, threads, images, data, want_map):
    """별도 프로세스에서 스레드 수를 고정하고 지연(ms)과 mAP50 을 잰다."""
    code = f"""
import os, time, json, glob, cv2, numpy as np
os.environ["OMP_NUM_THREADS"] = "{threads}"; os.environ["OPENVINO_INFERENCE_NUM_THREADS"] = "{threads}"
import torch; torch.set_num_threads({threads}); cv2.setNumThreads({threads})
from ultralytics import YOLO
m = YOLO({path!r}, task="detect")
imgs = [cv2.imread(p) for p in {images!r}]
for im in imgs[:3]: m.predict(im, imgsz={imgsz}, device="cpu", verbose=False)
t = []
for im in imgs:
    s = time.perf_counter(); m.predict(im, imgsz={imgsz}, device="cpu", verbose=False); t.append((time.perf_counter() - s) * 1000)
r = {{"ms_median": float(np.median(t)), "ms_p90": float(np.percentile(t, 90))}}
if {want_map!r}:
    v = m.val(data={data!r}, imgsz={imgsz}, device="cpu", plots=False, verbose=False, project={str(Path("runs/m2").resolve())!r}, name="bench_tmp", exist_ok=True)
    r["map50"] = float(v.box.map50)
print("RESULT " + json.dumps(r))
"""
    env = dict(os.environ, OMP_NUM_THREADS=str(threads))
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    print(proc.stderr[-800:])
    return {"error": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="weights/warehouse_yolo11n.pt")
    ap.add_argument("--data", default="datasets/warehouse/data.yaml")
    ap.add_argument("--imgsz", type=int, nargs="+", default=[640, 416, 320])
    ap.add_argument("--threads", type=int, nargs="+", default=[4, 2, 1])
    ap.add_argument("--images", type=int, default=40, help="지연 측정에 쓸 val 이미지 수")
    ap.add_argument("--skip-int8", action="store_true")
    ap.add_argument("--no-map", action="store_true", help="mAP 생략 (지연만)")
    a = ap.parse_args()
    import yaml
    data = yaml.safe_load(Path(a.data).read_text())
    val = sorted((Path(data["path"]) / data["val"]).glob("*.png"))
    images = [str(p) for p in val[:: max(1, len(val) // a.images)]][: a.images]
    paths = export_all(a.weights, a.imgsz, a.skip_int8, a.data)
    rows = []
    cores = len(os.sched_getaffinity(0))
    print(f"CPU 코어 {cores}개 사용 가능 (taskset 으로 제한했는지 확인)")
    for s in a.imgsz:
        for backend, path in paths[s].items():
            for th in a.threads:
                want_map = (not a.no_map) and th == a.threads[0]      # mAP 는 스레드와 무관하니 한 번만
                r = bench_one(path, s, th, images, a.data, want_map)
                rows.append({"imgsz": s, "backend": backend, "threads": th, **r})
                print(f"  {s:4d} {backend:14s} th={th}  {r.get('ms_median', float('nan')):7.1f} ms (p90 {r.get('ms_p90', float('nan')):6.1f})"
                      + (f"  mAP50 {r['map50']:.3f}" if "map50" in r else ""))
    art = Path("artifacts/m2"); art.mkdir(parents=True, exist_ok=True)
    tag = Path(a.weights).stem
    (art / f"benchmark_{tag}.json").write_text(json.dumps({"cores": cores, "rows": rows}, indent=1))
    maps = {(r["imgsz"], r["backend"]): r.get("map50") for r in rows if "map50" in r}
    lines = [f"CPU {cores}코어, val {len(images)}장 중앙값 지연(ms). mAP50 은 val 전체.", "",
             "| imgsz | backend | " + " | ".join(f"{t} thread" for t in a.threads) + " | mAP50 |", "|---|---|" + "---|" * len(a.threads) + "---|"]
    for s in a.imgsz:
        for backend in paths[s]:
            cells = [f"{next((r['ms_median'] for r in rows if r['imgsz'] == s and r['backend'] == backend and r['threads'] == t), float('nan')):.1f}" for t in a.threads]
            m = maps.get((s, backend)); lines.append(f"| {s} | {backend} | " + " | ".join(cells) + f" | {m:.3f} |" if m is not None else f"| {s} | {backend} | " + " | ".join(cells) + " | - |")
    (art / f"benchmark_{tag}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"저장: {art}/benchmark_{tag}.md")


if __name__ == "__main__":
    main()
