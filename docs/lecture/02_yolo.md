# M2. YOLO 기반 객체 탐지 모델 학습 및 최적화 (CPU 기준)

작성·검증: 2026-09-22, Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12 / ultralytics 8.4 / MuJoCo 3.6. 학습은 강사 PC(RTX 5060 Ti, 별도 venv `.venv-yolo-gpu`), 추론·벤치마크는 `taskset -c 0-3`(Ryzen 7 9700X 4코어)에서 확인했다. 예제는 `examples/m2_yolo/`, 가중치는 `weights/`, 데이터셋은 `datasets/`(생성물, 배포하지 않음).

## 1. 목표와 요약

세그멘테이션 자동 라벨로 데이터셋을 만들고 10개 클래스(person, helmet, safety_vest, parcel_red/blue/yellow, forklift, pallet, cone, extinguisher) YOLO11n을 학습한 뒤, CPU에서 실시간이 나오게 최적화해 핸들러에 배포한다.

| 예제 | 내용 | 결과 |
|---|---|---|
| 01_capture_dataset.py | 핸들러에서 RGB + 세그멘테이션 → YOLO 라벨 자동 저장 | 640x480, 2 카메라, meta.jsonl |
| 02_domain_randomization.py | 로봇 시점·배우 위치/속성·상자·조명 랜덤화 자동 수집 | 3000장(1500 장면) 21분 |
| 03_dataset_review.py | 장면 단위 분할, 클래스 분포, 안전모 균형, 샘플 그림 | train 2550 / val 450 |
| 04_train_yolo_cpu.py | 수강생 CPU 학습 / 강사 GPU 전체 학습 / 320 미세조정, Colab 노트북 | GPU 60 epoch 9분 mAP50 0.930 |
| 05_evaluate.py | mAP, 클래스별 AP, 혼동 행렬, 실패 사례, 안전모 유무 정확도 | 640: 0.930 / 97.9 %, 320: 0.834 / 95.5 % |
| 06_optimize_cpu.py | 해상도 x 백엔드(PyTorch/ONNX/OpenVINO/INT8) 벤치마크 표 | 320 OpenVINO 2 ms(4코어) |
| 07_yolo_handler.py | WorkerHandler + OpenVINO 추론 → Detection2DArray, 정답 비교 | 2장 16~25 ms, 실시간 1.00, P 0.94 / R 0.93 |

검증 기준(계획서) 대비: 배포 가중치 val mAP50 ≥ 0.9 → 0.930(640 학습·평가) 충족. 4코어 320 입력 프레임당 ≤ 60 ms → 2 ms(OpenVINO) 충족. 2대 카메라 2 FPS 실시간 → realtime_ratio 1.00, 버림 0 충족. 안전모 유무 정확도 ≥ 95 % → 97.9 %(640), 95.5 %(320) 충족. 단, 320 입력의 mAP50은 0.834로 작은 상자에서 떨어진다(아래 4절).

## 2. 준비

```bash
source /opt/ros/jazzy/setup.bash && source scripts/env.sh
# 수집 (약 20분, 끝나면 시뮬레이터를 다시 띄운다. 로봇을 순간이동시켜 AMCL 이 틀어지기 때문)
M2_MAX=3000 ./scripts/mobile_openarm start viewer:=false rviz:=false \
  camera_handler:=examples/m2_yolo/02_domain_randomization.py:RandomizedCapture \
  camera_segmentation:=true camera_size:=640x480 camera_fps:=4
python examples/m2_yolo/03_dataset_review.py
python examples/m2_yolo/04_train_yolo_cpu.py --subset 300 --epochs 15 --imgsz 320    # 수강생: 4코어 8분
```

강사 배포 가중치(수강생은 `weights/`를 받아 05부터 진행):

```bash
python3 -m venv .venv-yolo-gpu && .venv-yolo-gpu/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128 ultralytics onnx onnxruntime onnxslim
.venv-yolo-gpu/bin/python examples/m2_yolo/04_train_yolo_cpu.py --full --epochs 60 --imgsz 640 --device 0   # weights/warehouse_yolo11n.pt
.venv-yolo-gpu/bin/python examples/m2_yolo/04_train_yolo_cpu.py --finetune 320 --epochs 30 --device 0      # weights/warehouse_yolo11n_s320.pt
taskset -c 0-3 python examples/m2_yolo/06_optimize_cpu.py --weights weights/warehouse_yolo11n_s320.pt --imgsz 320   # OpenVINO/ONNX/INT8 내보내기
```

## 3. 예제별 관찰 포인트

### 01. 자동 라벨
- 라벨의 출처는 MuJoCo 세그멘테이션(픽셀마다 body id). `warehouse_lecture.vision.labels.label_frame`이 body → 클래스 박스로 바꾸고, 사람의 안전모·조끼는 geom을 투영해 별도 클래스로 만든다(안 쓴 사람은 geom 크기 0.001이라 라벨이 생기지 않는다).
- YOLO 형식 `cls cx cy w h`(0~1). `labels.CLASSES` 순서가 데이터셋의 계약이다. 같은 순간의 카메라들은 같은 장면 번호를 공유한다(`000123_head_camera.png`).

### 02. 도메인 랜덤화
- 핸들러가 시뮬레이터 프로세스 안이라 `ActorAnimator.teleport/set_attributes`, `model.light_*`, 로봇·상자 freejoint qpos를 직접 쓴다. 다른 프로세스에서는 `/warehouse/set_actor` 서비스로 같은 일을 한다.
- 안전모 50 %, 조끼 orange/green/none, 셔츠 7색, 조명 0.35~1.0배, 상자는 두 작업대에 무작위 배치. 로봇 시점의 40 %는 작업대 앞(상자가 작업대 위에만 있어 드물기 때문).
- **지게차는 넓은 구역에만** 놓는다. 좁은 통로에 두면 랙과 겹쳐 박스가 랙을 관통한다(첫 수집에서 발견).
- 라벨 없는 이미지(전체의 19 %)는 배경 학습용으로 남긴다.

![dataset samples with automatic labels](dataset_samples.png)

### 03. 분할과 분포
- 장면 단위 85/15 분할. 인스턴스: person 2489, safety_vest 1170, cone 1169, forklift 969, helmet 905, pallet 728, parcel 각 530~570, extinguisher 521. helmet/person = 0.36인데 사람의 절반이 안전모를 써도 먼 사람은 안전모가 12픽셀 미만이라 라벨이 안 생긴다.

![class histogram](class_hist.png)

### 04. 학습

| 설정 | 시간 | val mAP50 | 용도 |
|---|---|---|---|
| 300장, 5 epoch, 320, CPU 4코어 | 3.2분 | 0.149 | 절차 체험(너무 짧다) |
| 300장, 15 epoch, 320, CPU 4코어 | 8.2분 | 0.527 | **수강생 권장** |
| 2550장, 60 epoch, 640, RTX 5060 Ti | 9.0분 | 0.930 (mAP50-95 0.788) | 배포 `warehouse_yolo11n.pt` |
| 위 가중치 → 320 미세조정 30 epoch, GPU | 1.7분 | 0.834 @320 (미세조정 전 0.803) | 배포 `warehouse_yolo11n_s320.pt` |

- 시뮬레이터 영상은 색·조명이 단조로워 hsv/scale 증강을 세게 준다(04 스크립트와 Colab 노트북 동일).
- ultralytics 8.4는 상대 경로 `project`를 `runs/detect/` 아래로 옮긴다. 절대 경로를 주고 `trainer.save_dir`에서 결과를 읽는다.
- `requirements-lecture.txt`는 CPU torch다. GPU 학습은 별도 venv(`.venv-yolo-gpu`, torch cu128).

### 05. 평가

| imgsz | mAP50 | mAP50-95 | 안전모 정확도 | 낮은 클래스 |
|---|---|---|---|---|
| 640 (`warehouse_yolo11n.pt`) | 0.930 | 0.788 | 97.9 % (334명) | pallet 0.882, safety_vest 0.888 |
| 320 (같은 가중치) | 0.803 | 0.616 | 95.8 % (307명) | parcel_blue 0.615, safety_vest 0.737 |
| 320 (`_s320.pt`) | 0.834 | 0.656 | 95.5 % (313명) | parcel_blue 0.662 |

- 320에서 떨어지는 것은 작은 물체다: 1 m 거리의 4.5 cm 상자가 320 입력에서 10픽셀이다. 실패 사례는 원거리의 사람·안전모·조끼와 화면 가장자리에 걸린 지게차.
- 안전모 유무는 "사람 박스 위쪽 40 % 안에 helmet 박스 중심이 있는가"로 판정한다. M3·M5의 속성 판정 규칙과 같다.

![failure cases at 320: misses (yellow) and false positives (red)](failures_320.png)

### 06. CPU 최적화

4코어(taskset), val 40장 중앙값(ms), `warehouse_yolo11n.pt`:

| imgsz | PyTorch | ONNX Runtime | OpenVINO | OpenVINO INT8 | mAP50 (FP32 / INT8) |
|---|---|---|---|---|---|
| 640 | 20.1 | 14.2 | 6.0 | 4.9 | 0.929 / 0.925 |
| 416 | 12.3 | 6.6 | 3.0 | 2.5 | 0.884 / 0.877 |
| 320 | 8.4 | 4.0 | 2.1 | 1.8 | 0.799 / 0.795 |

- OpenVINO가 PyTorch보다 3~4배 빠르다(AMD Zen 5에서도). INT8은 20 % 더 빠르고 mAP 손실 0.005 이내.
- **스레드 환경변수는 효과가 없다.** 런타임이 프로세스 affinity로 스레드 수를 정한다. 코어가 실제 변수: OpenVINO 640은 1코어 17 ms, 4코어 6 ms, 16코어 4 ms. 수강생 PC에서는 시뮬레이터·Nav2·MoveIt과 코어를 나눠 쓰므로 1~2코어 기준으로 본다.
- 결론: 4코어 예산이면 **416 OpenVINO(3 ms, mAP50 0.884)**도 여유가 있다. 기본은 계획대로 320이며 M3에서 상자 검출이 부족하면 416으로 올린다.

### 07. 핸들러 배포
- `warehouse_lecture.vision.yolo.YoloDetector`(승격된 래퍼): .pt/.onnx/OpenVINO를 같은 API로 연다. 내보낸 모델은 배치 1 고정이라 한 장씩 추론한다.
- M1-06의 WorkerHandler 그대로: prepare(프레임 복사 + 세그멘테이션 정답 라벨) → process(YOLO) → publish(`/vision/yolo_2d`, 정밀도·재현율 누적).
- 4코어에서 시뮬레이터(Nav2·MoveIt 포함)와 함께: 2장 배치 16~25 ms, 캡처 2 FPS 유지, 실시간 비율 1.00, 버림 0, 작업대 앞 누적 정밀도 0.94 / 재현율 0.93.

![YOLO handler at the pick table](07_yolo.png)

## 4. 한계와 다음 단계

- 320 입력의 mAP50 0.834는 작은 상자 때문이다. 대안: (a) 416 입력(3 ms), (b) 상자 검출은 작업대 앞에서만 필요하므로 도킹 후 손목 카메라로 근접 검출, (c) M1-05처럼 깊이·높이 필터를 결합. M3에서 결정한다.
- 시뮬레이터 정답으로만 평가했다. 실제 카메라로 옮기면 도메인 갭이 생긴다(랜덤화가 그 대비다).
- 산출물: `weights/warehouse_yolo11n.pt`, `warehouse_yolo11n_s320.pt`, `*_openvino_model/`, `*.onnx`, `notebooks/train_yolo_colab.ipynb`, `artifacts/m2/`(eval_*.json, benchmark_*.md, 그림).

## 5. 이번 모듈에서 고친 기반 코드

- `warehouse_lecture/vision/yolo.py` 추가(YoloDetector, 가중치 자동 탐색: 환경변수 `WAREHOUSE_YOLO` → s320 OpenVINO → ONNX → .pt).
- 예제 04는 `--full`(640 전체 학습), `--finetune 320`, 수강생 `--subset` 모드를 한 스크립트로 제공한다.
