#!/usr/bin/env python3
"""M3 예제 7: 카메라 프레임을 이미지 입력으로 LLM 에 보내 장면 설명·안전모 판정을 받고 YOLO 결과와 비교한다.

실행 (val 이미지와 정답 라벨을 쓴다. 시뮬레이터 불필요):
    ./scripts/mobile_openarm exec python examples/m3_llm/07_vision_llm.py [--n 10] [--detail low]
출력: artifacts/m3/vision_llm.json

배우는 점:
- 이미지 한 장 = 토큰 (detail=low 는 85 토큰 고정, high 는 타일 수에 비례). 호출 지연은 1~4 초. 실시간 인식은 YOLO(수십 ms), LLM 은 검증·설명·질의응답용.
- parse_image + pydantic 스키마로 "사람 수, 안전모 착용 수, 상자 색 목록, 한 줄 설명"을 구조화해 받으면 YOLO 와 바로 비교할 수 있다.
- 시뮬레이터 그래픽(단순한 사람 모형)은 LLM 에게 낯설다. 프롬프트에 장면의 성격(시뮬레이션, 노란 반구 = 안전모)을 알려 주면 좋아진다.
- 비용: 10장 x low detail 이면 수 센트 이하. 로그(logs/openai_usage.jsonl)로 확인한다.
"""

import argparse
import json
import time
from pathlib import Path
from typing import List

import cv2
import yaml
from pydantic import BaseModel, Field
from warehouse_lecture.llm.client import LLM
from warehouse_lecture.vision.yolo import YoloDetector

PROMPT = ("이 사진은 창고 로봇 시뮬레이터의 카메라 영상이다. 사람은 단순한 인체 모형이고, 머리 위 노란 반구가 안전모, 몸통의 주황/초록 조끼가 안전조끼다. "
          "작업대 위의 작은 정육면체는 상자(빨강/파랑/노랑)다. 사진을 보고 답하라.")


class SceneRead(BaseModel):
    people: int = Field(description="보이는 사람 수")
    helmets: int = Field(description="안전모를 쓴 사람 수")
    vests: int = Field(description="안전조끼를 입은 사람 수")
    parcel_colors: List[str] = Field(description="보이는 상자 색 목록: red/blue/yellow")
    description: str = Field(description="장면을 한국어 한 문장으로")


def truth_of(label_path, classes):
    counts = {"people": 0, "helmets": 0, "vests": 0, "parcel_colors": []}
    for l in Path(label_path).read_text().splitlines():
        if not l.strip():
            continue
        c = classes[int(l.split()[0])]
        if c == "person": counts["people"] += 1
        elif c == "helmet": counts["helmets"] += 1
        elif c == "safety_vest": counts["vests"] += 1
        elif c.startswith("parcel_"): counts["parcel_colors"].append(c[7:])
    return counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--detail", default="low", choices=["low", "high"])
    ap.add_argument("--data", default="datasets/warehouse/data.yaml")
    a = ap.parse_args()
    data = yaml.safe_load(Path(a.data).read_text())
    classes = [data["names"][i] for i in sorted(data["names"])]
    val = Path(data["path"]) / data["val"]
    # 사람이 있는 head 카메라 이미지를 고른다
    images = [p for p in sorted(val.glob("*head_camera.png")) if "0 " in Path(str(p).replace("/images/", "/labels/")).with_suffix(".txt").read_text()[:2]][: a.n]
    llm, yolo = LLM(), YoloDetector(imgsz=320, conf=0.4)
    rows = []
    for p in images:
        rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB)
        truth = truth_of(Path(str(p).replace("/images/", "/labels/")).with_suffix(".txt"), classes)
        t0 = time.perf_counter(); dets = yolo.detect(rgb); yolo_ms = (time.perf_counter() - t0) * 1000
        y = {"people": sum(d[0] == "person" for d in dets), "helmets": sum(d[0] == "helmet" for d in dets),
             "vests": sum(d[0] == "safety_vest" for d in dets), "parcel_colors": sorted(d[0][7:] for d in dets if d[0].startswith("parcel_"))}
        t0 = time.perf_counter()
        try:
            r = llm.parse_image(rgb, PROMPT, SceneRead, detail=a.detail, purpose="vision_scene")
            llm_ms = (time.perf_counter() - t0) * 1000
            l = {"people": r.people, "helmets": r.helmets, "vests": r.vests, "parcel_colors": sorted(c.lower() for c in r.parcel_colors), "description": r.description}
        except ValueError as error:
            llm_ms = (time.perf_counter() - t0) * 1000; l = {"error": str(error)}
        rows.append({"image": p.name, "truth": truth, "yolo": y, "llm": l, "yolo_ms": yolo_ms, "llm_ms": llm_ms})
        print(f"{p.name}: 정답 사람{truth['people']}/안전모{truth['helmets']}/조끼{truth['vests']} 상자{truth['parcel_colors']} | "
              f"YOLO {y['people']}/{y['helmets']}/{y['vests']} {y['parcel_colors']} ({yolo_ms:.0f} ms) | "
              f"LLM {l.get('people')}/{l.get('helmets')}/{l.get('vests')} {l.get('parcel_colors')} ({llm_ms / 1000:.1f} s)")
        print(f"    LLM 설명: {l.get('description', l.get('error'))}")
    def acc(key, src):
        return sum(r[src].get(key) == r["truth"][key] for r in rows) / len(rows)
    summary = {k: {"yolo": acc(k, "yolo"), "llm": acc(k, "llm")} for k in ("people", "helmets", "vests")}
    summary["parcel_colors"] = {"yolo": sum(sorted(r["yolo"]["parcel_colors"]) == sorted(r["truth"]["parcel_colors"]) for r in rows) / len(rows),
                                "llm": sum(sorted(r["llm"].get("parcel_colors", [])) == sorted(r["truth"]["parcel_colors"]) for r in rows) / len(rows)}
    print("\n항목별 정답 일치율 (이미지 기준):")
    for k, v in summary.items():
        print(f"  {k:14s} YOLO {v['yolo'] * 100:5.0f} %   LLM {v['llm'] * 100:5.0f} %")
    print(f"평균 지연: YOLO {sum(r['yolo_ms'] for r in rows) / len(rows):.0f} ms, LLM {sum(r['llm_ms'] for r in rows) / len(rows) / 1000:.1f} s; 비용 ${llm.session_cost:.4f}")
    Path("artifacts/m3").mkdir(parents=True, exist_ok=True)
    Path("artifacts/m3/vision_llm.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
