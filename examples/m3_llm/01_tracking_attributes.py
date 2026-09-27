#!/usr/bin/env python3
"""M3 예제 1: ByteTrack 으로 검출에 지속 ID 를 붙이고, 사람 박스 안의 helmet/vest 박스를 연관해 속성을 만든다.

실행 (세그멘테이션을 켜면 정답 속성과 비교해 오분류율을 누적한다):
    taskset -c 0-3 ./scripts/mobile_openarm start viewer:=false rviz:=false \\
        camera_handler:=examples/m3_llm/01_tracking_attributes.py:TrackingHandler camera_segmentation:=true
    ./scripts/mobile_openarm exec ros2 topic echo /vision/tracks_2d
  옵션: WAREHOUSE_YOLO, M2_IMGSZ=320, M2_CONF=0.4, M3_VOTES=5 (속성 다수결 창), M1_WINDOW=0
  미리보기: artifacts/m3/01_tracks.png

배우는 점:
- 추적(ByteTrack)은 검출 박스만 보고 프레임 간 IoU·칼만 예측으로 같은 물체에 같은 ID 를 준다. 카메라마다 추적기를 따로 둔다.
- 속성 연관 규칙: helmet 박스 중심이 사람 박스 위쪽 40 % 안에 있으면 helmet=true, safety_vest 박스 중심이 사람 박스 안에 있으면
  vest=색. 조끼 색은 YOLO 클래스가 아니라 박스 픽셀의 평균 색조(H)로 정한다(orange < 28 <= green, OpenCV 0~179).
- 속성은 프레임마다 흔들리므로 ID 별로 최근 N 프레임 다수결로 안정화한다. 이것이 M5 조우 기억의 재료다.
- Detection2D.id 에 "카메라:트랙ID" 를 넣어 2D 메시지로도 추적을 전달한다.
"""

import os
from collections import Counter, defaultdict, deque
from pathlib import Path

import cv2
import numpy as np
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose
from warehouse_lecture.ros.handler_base import WorkerHandler
from warehouse_lecture.vision.labels import CLASSES, label_frame
from warehouse_lecture.vision.yolo import resolve_weights

COL = {"person": (0, 255, 0), "helmet": (0, 255, 255), "safety_vest": (255, 128, 0), "parcel_red": (0, 0, 255), "parcel_blue": (255, 0, 0),
       "parcel_yellow": (0, 200, 255), "forklift": (255, 0, 255), "pallet": (120, 120, 255), "cone": (0, 140, 255), "extinguisher": (255, 255, 255)}


def iou(a, b):
    ix1, iy1, ix2, iy2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def vest_colour(rgb, box):
    """조끼 박스 중앙 영역의 평균 색조로 orange/green 판정."""
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    patch = rgb[y1 + h // 4: y2 - h // 4 or y2, x1 + w // 4: x2 - w // 4 or x2]
    if patch.size == 0:
        return "orange"
    hsv = cv2.cvtColor(patch.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    hue = np.median(hsv[hsv[:, 1] > 80, 0]) if (hsv[:, 1] > 80).any() else np.median(hsv[:, 0])
    return "orange" if hue < 28 else "green"


def associate(dets, rgb):
    """dets: [(label, box, score, track_id)] -> {track_id: {"box":..., "helmet": bool, "vest": str}} (사람만)."""
    people = {}
    for label, box, score, tid in dets:
        if label == "person":
            people[tid] = {"box": box, "score": score, "helmet": False, "vest": "none"}
    for label, box, score, tid in dets:
        if label not in ("helmet", "safety_vest"):
            continue
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        for p in people.values():
            x1, y1, x2, y2 = p["box"]
            if not (x1 - 4 <= cx <= x2 + 4):
                continue
            if label == "helmet" and y1 - 8 <= cy <= y1 + 0.4 * (y2 - y1):
                p["helmet"] = True
            elif label == "safety_vest" and y1 <= cy <= y2:
                p["vest"] = vest_colour(rgb, box)
    return people


class CameraTracker:
    """카메라 하나의 YOLO + ByteTrack + 속성 다수결."""

    def __init__(self, weights, imgsz, conf, votes):
        from ultralytics import YOLO
        self.model = YOLO(weights, task="detect")
        self.imgsz, self.conf = imgsz, conf
        self.history = defaultdict(lambda: deque(maxlen=votes))   # track_id -> [(helmet, vest), ...]
        self.model.predict(np.zeros((imgsz, imgsz, 3), np.uint8), imgsz=imgsz, device="cpu", verbose=False)

    def track(self, rgb):
        r = self.model.track(np.ascontiguousarray(rgb[..., ::-1]), imgsz=self.imgsz, conf=self.conf, persist=True,
                             tracker="bytetrack.yaml", device="cpu", verbose=False)[0]
        dets = []
        if r.boxes is not None and len(r.boxes):
            ids = r.boxes.id.int().tolist() if r.boxes.id is not None else [-1] * len(r.boxes)
            for i, ((x1, y1, x2, y2), c, s, tid) in enumerate(zip(r.boxes.xyxy.numpy(), r.boxes.cls.int().tolist(), r.boxes.conf.tolist(), ids)):
                # ByteTrack 이 아직 확정하지 않은 박스는 id 가 없다(-1). 서로 섞이지 않게 프레임 안에서만 유일한 음수 키를 준다.
                dets.append((self.model.names[c], (int(x1), int(y1), int(x2), int(y2)), float(s), int(tid) if tid >= 0 else -1 - i))
        people = associate(dets, rgb)
        for tid, p in people.items():
            if tid < 0:
                p["age"] = 0                         # 미확정 트랙: 투표하지 않는다 (속성은 이번 프레임 값 그대로)
                continue
            self.history[tid].append((p["helmet"], p["vest"]))
            votes = self.history[tid]
            p["helmet"] = sum(v[0] for v in votes) * 2 > len(votes)                 # 다수결
            p["vest"] = Counter(v[1] for v in votes).most_common(1)[0][0]
            p["age"] = len(votes)
        return dets, people


class TrackingHandler(WorkerHandler):
    def __init__(self):
        super().__init__(adaptive=True)
        self.weights = resolve_weights()
        self.imgsz = int(os.environ.get("M2_IMGSZ", "320"))
        self.conf = float(os.environ.get("M2_CONF", "0.4"))
        self.votes = int(os.environ.get("M3_VOTES", "5"))
        self.window = os.environ.get("M1_WINDOW", "1") != "0" and bool(os.environ.get("DISPLAY"))
        self.out = Path("artifacts/m3"); self.out.mkdir(parents=True, exist_ok=True)
        self.trackers = {}
        self.attr_total = Counter(); self.attr_wrong = Counter()
        self.last_report = None
        self.frames = 0

    def on_setup(self, context):
        self.pub = context.node.create_publisher(Detection2DArray, "/vision/tracks_2d", 10)
        self.trackers = {name: CameraTracker(self.weights, self.imgsz, self.conf, self.votes) for name in context.camera_names}
        self.body_labels = context.body_labels() if context.pump.segmentation else None
        context.node.get_logger().info(f"[m3-01] {self.weights}, 카메라별 추적기 {list(self.trackers)}, 다수결 {self.votes}프레임, 정답 비교 {'on' if self.body_labels else 'off'}")

    def truth_people(self, frame):
        """정답: 사람 박스 + 실제 속성 (배우 spec)."""
        out = []
        if self.body_labels is None:
            return out
        ctx = self.context
        for body, (name, kind) in self.body_labels.items():
            if kind != "person":
                continue
            mask = frame.segmentation == body
            ys, xs = np.nonzero(mask)
            if len(xs) < 24:
                continue
            attrs = ctx.actors.attributes(name)
            out.append(((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())), attrs["helmet"] == "true", attrs["vest"]))
        return out

    def prepare(self, frames):
        return [(name, f.rgb.copy(), f.sim_time, f.optical_frame, self.truth_people(f)) for name, f in frames.items()]

    def process(self, items):
        return [(it, *self.trackers[it[0]].track(it[1])) for it in items]

    def publish(self, results):
        stamp = self.context.stamp()
        tiles = []
        for (name, rgb, sim_time, frame_id, truth), dets, people in results:
            msg = Detection2DArray(); msg.header.stamp, msg.header.frame_id = stamp, frame_id
            for label, (x1, y1, x2, y2), score, tid in dets:
                d = Detection2D(); d.header = msg.header; d.id = f"{name}:{tid}"
                d.bbox.center.position.x, d.bbox.center.position.y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                d.bbox.size_x, d.bbox.size_y = float(x2 - x1), float(y2 - y1)
                h = ObjectHypothesisWithPose(); h.hypothesis.class_id, h.hypothesis.score = label, score
                d.results.append(h); msg.detections.append(d)
            self.pub.publish(msg)
            # 정답 속성과 비교 (IoU 0.5 로 사람 매칭, 키 40 px 이상, 다수결이 찬 트랙만)
            for tbox, t_helmet, t_vest in truth:
                if tbox[3] - tbox[1] < 40:
                    continue
                match = [p for p in people.values() if iou(p["box"], tbox) >= 0.5 and p.get("age", 0) >= self.votes]
                if not match:
                    continue
                p = match[0]
                near = tbox[3] - tbox[1] >= 80          # 가까운 사람(키 80 px 이상)은 따로 센다: 먼 사람은 안전모가 몇 픽셀이라 놓친다
                if near and (p["helmet"] != t_helmet or p["vest"] != t_vest) and self.attr_wrong["helmet_near"] + self.attr_wrong["vest_near"] < 12:
                    self.context.node.get_logger().warn(f"[m3-01] 오분류 {name} 키 {tbox[3] - tbox[1]}px: 예측 helmet={p['helmet']} vest={p['vest']} / 정답 helmet={t_helmet} vest={t_vest}")
                for key, wrong in (("helmet", p["helmet"] != t_helmet), ("vest", p["vest"] != t_vest)):
                    self.attr_total[key] += 1; self.attr_wrong[key] += wrong
                    if near:
                        self.attr_total[key + "_near"] += 1; self.attr_wrong[key + "_near"] += wrong
            if self.window or self.frames % 4 == 0:
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                for label, (x1, y1, x2, y2), score, tid in dets:
                    cv2.rectangle(bgr, (x1, y1), (x2, y2), COL.get(label, (200, 200, 200)), 1)
                    text = f"#{tid} {label}"
                    if tid in people and label == "person":
                        p = people[tid]; text += f" {'H' if p['helmet'] else '-'} {p['vest'][:1]}"
                    cv2.putText(bgr, text, (x1, max(10, y1 - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, COL.get(label, (200, 200, 200)), 1)
                cv2.putText(bgr, name, (4, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                tiles.append(bgr)
        self.frames += 1
        if tiles:
            grid = cv2.hconcat(tiles); tmp = self.out / "01_tracks.tmp.png"; cv2.imwrite(str(tmp), grid); tmp.replace(self.out / "01_tracks.png")
            if self.window:
                try:
                    cv2.imshow("M3-01 tracks", grid); cv2.waitKey(1)
                except cv2.error:
                    self.window = False
        now = self.context.sim_time()
        if self.last_report is None or now - self.last_report >= 2.0:
            self.last_report = now
            summary = []
            for (name, *_), dets, people in results:
                for tid, p in people.items():
                    summary.append(f"{name[:4]}#{tid}:{'helmet' if p['helmet'] else 'nohelmet'}/{p['vest']}({p.get('age', 0)})")
            err = " ".join(f"{k} 오분류 {self.attr_wrong[k]}/{self.attr_total[k]}" for k in ("helmet", "vest", "helmet_near", "vest_near")) if self.body_labels else ""
            self.context.node.get_logger().info(f"[m3-01] sim {now:6.1f}s 추론 {self._inference_ms:.0f} ms 실시간 {self._ratio:.2f} | 사람 {' '.join(summary) or '없음'} | {err}")
