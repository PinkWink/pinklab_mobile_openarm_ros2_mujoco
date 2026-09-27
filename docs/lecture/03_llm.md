# M3. 비전 연동 최적화 및 LLM 구조와 프롬프트 엔지니어링

작성·검증: 2026-09-22, Ubuntu 24.04 / ROS 2 Jazzy / ultralytics 8.4 / OpenAI gpt-4.1-mini. 비전 예제는 `taskset -c 0-3`(4코어)에서, LLM 예제는 `.env`의 OPENAI_API_KEY로 확인했다. 예제는 `examples/m3_llm/`, 모듈 전체 API 비용은 약 0.06달러(logs/openai_usage.jsonl).

## 1. 목표와 요약

검출을 추적·속성·3D 위치로 승격해 조우 기록의 재료(Detection3DArray)를 만들고, OpenAI API로 상황을 서술·질의한다.

| 예제 | 내용 | 결과 |
|---|---|---|
| 01_tracking_attributes.py | ByteTrack ID + 사람 박스 안 helmet/vest 연관, 조끼 색, 다수결 | 가까운 사람(키 ≥ 80 px) 안전모 오분류 1/75, 조끼 0/75. 전체(원거리 포함) 안전모 10/182 |
| 02_detection3d_publisher.py | 깊이·tf2 → map 좌표 Detection3DArray, 정답 비교 | 상자 위치 오차 중앙값 2.5 cm(n=66), 사람 11.8 cm(n=349). 운반 스킬 `locate:=vision` 성공 |
| 03_pipeline_budget.py | 카메라 교대·스킵·해상도·ROI 예산 표 | 4코어: 2대 320 = 17 ms/프레임, 교대·ROI = 10 ms, 실시간 유지 |
| 04_openai_hello.py | 첫 호출, system prompt, 온도, max_tokens, 비용 로그 | 8회 호출 0.0007달러 |
| 05_prompt_patterns.py | zero/few-shot, 단계적 추론, 프롬프트 JSON, 거부 | zero 19/20, few 18→20/20(예시 추가), JSON 파싱 실패 0 |
| 06_structured_output.py | Structured Outputs(pydantic) / tool calling | 둘 다 20/20, 스키마 위반 0 |
| 07_vision_llm.py | 프레임을 LLM에 보내 장면 판독, YOLO와 비교 | 사람 수 YOLO 100 % vs LLM 70 %, 9 ms vs 1.5 s |
| 08_scene_narrator.py | 세계 상태 JSON → LLM → 한국어 보고(Utterance) | 상태 변화 시만 호출, 안전모 미착용자 우선 보고 |

검증 기준(계획서) 대비: 20개 상황 질의 채점표 → `questions.yaml`, 구조화 출력 20/20. JSON 파싱 실패율 0 → 05·06 모두 0. 속성 오분류율 → 가까운 사람 기준 안전모 1.3 %, 조끼 0 %. 모듈 API 비용 기록 → 로그와 각 예제의 세션 비용 출력.

## 2. 준비

```bash
source /opt/ros/jazzy/setup.bash && source scripts/env.sh
cp .env.example .env   # OPENAI_API_KEY 기입. 크레딧이 없으면 429 insufficient_quota
# 비전 (01~03): 시뮬레이터 인자로 핸들러를 넘긴다
taskset -c 0-3 ./scripts/mobile_openarm start viewer:=false rviz:=false \
  camera_handler:=examples/m3_llm/02_detection3d_publisher.py:Detection3DHandler camera_depth:=true camera_segmentation:=true
# LLM (04~07): 시뮬레이터 불필요
python examples/m3_llm/04_openai_hello.py
# 08: 승격된 검출기와 함께
LECTURE_HANDLERS="warehouse_lecture.vision.aruco:ArucoDetector,warehouse_lecture.vision.yolo_detector:YoloDetector3D" \
  ./scripts/mobile_openarm start viewer:=false camera_depth:=true
python examples/m3_llm/08_scene_narrator.py
```

## 3. 예제별 관찰 포인트

### 01. 추적과 속성
- 카메라마다 추적기를 따로 둔다(ultralytics는 모델 인스턴스당 추적기 하나). ByteTrack이 아직 확정하지 않은 박스는 id가 없다(-1). 이를 같은 키로 묶으면 속성 투표가 섞여 조끼 오분류가 19/135까지 올랐다. 프레임 안에서만 유일한 음수 키를 주고 투표에서 제외해 1/182로 내려갔다.
- 규칙: helmet 박스 중심이 사람 박스 위쪽 40 % 안이면 착용, safety_vest 박스 중심이 안이면 조끼. 조끼 색은 YOLO 클래스가 아니라 박스 픽셀 중앙값 색조(H < 28 → orange, 아니면 green).
- 남은 오분류는 원거리 사람이다(안전모가 몇 픽셀). 조우 기억(M5)은 가까이서 본 속성만 채택한다.

### 02. 3D 위치와 운반 스킬 연동
- M1-05와 같은 길(중앙 깊이 → K⁻¹ → 두께 보정 → tf2 map). WorkerHandler의 publish는 다음 캡처 시점이라 프레임 stamp의 TF가 도착해 있다.
- **정답 자세와 tf를 섞지 말 것.** 검출은 AMCL tf로 map 좌표가 됐는데 스킬은 시뮬레이터 정답 자세로 되돌려 AMCL 오차(3~4 cm)가 그대로 남아 집기가 64 %에서 실패했다. VisionLocator가 같은 tf(map→base_footprint)로 되돌리도록 고쳐 오차가 상쇄됐고, 카메라 검출만으로 운반이 성공했다(슬롯 오차 3.0 cm).
- 운반 스킬은 물체 이름(parcel_1)을 쓰고 검출기는 색 클래스(parcel_red)를 내므로 서버가 이름→색 라벨로 바꾼다.
- `rclpy`는 float 필드에 int를 넣으면 단언으로 프로세스가 죽는다(ColorRGBA(r=1)). 핸들러 예외는 시뮬레이터 전체를 죽인다.

### 03. CPU 예산

| 설정 | 추론 ms/프레임 | 이미지/초 | 실시간 비율(최소/평균) |
|---|---|---|---|
| 2대 매 프레임 320 | 17.1 | 8.0 | 0.90 / 1.00 |
| 카메라 교대 320 | 10.3 | 4.0 | 0.99 / 1.00 |
| 2대, 2프레임에 1번 320 | 17.7 | 4.0 | 0.99 / 1.00 |
| 2대 매 프레임 416 | 17.8 | 8.1 | 0.99 / 1.00 |
| 2대 매 프레임 224 | 17.4 | 8.1 | 0.99 / 1.00 |
| head 중앙 60 % ROI 416 | 10.1 | 4.0 | 0.99 / 1.00 |

- YOLO11n은 CPU에서 네트워크보다 호출당 오버헤드(전처리·NMS·Python)가 커서 224~416이 거의 같다. 예산을 줄이려면 해상도가 아니라 **이미지 수**(교대, ROI)를 줄인다. 416으로 올려도 손해가 없으므로 상자 검출이 부족하면 416을 쓴다.

### 04~06. LLM 기본, 프롬프트, 구조화
- temperature 0은 같은 문장을 반복하고 1은 표현이 바뀐다. max_tokens가 작으면 잘린다. 모든 호출은 `warehouse_lecture.llm.client.LLM`을 거쳐 모델·재시도·비용이 한곳에 기록된다.
- 프롬프트만으로 JSON을 받으면 형식은 지켜도 **어느 필드에 넣을지**를 틀린다(자세 이름을 attributes에). 규칙 문장보다 few-shot 예시 하나가 효과적이었다(18 → 20/20). 모호한 요청은 되묻고 위험한 요청은 거부한다(3/3).
- Structured Outputs는 pydantic 스키마(enum 포함)를 강제해 파싱 실패와 오타를 없앤다. tool calling은 의도마다 함수를 두어 인자 검증이 자연스럽고 M5 에이전트의 기초가 된다. 둘 다 20/20, 비용 각 0.007~0.009달러.

### 07. 비전 LLM vs YOLO (val 10장, detail=low)

| 항목 | YOLO | LLM |
|---|---|---|
| 사람 수 | 100 % | 70 % |
| 안전모 수 | 100 % | 70 % |
| 조끼 수 | 90 % | 60 % |
| 상자 색 | 90 % | 70 % |
| 지연 | 9 ms | 1.5 s |

- 실시간 인식은 YOLO, 설명·검증·질의응답은 LLM. 시뮬레이터의 단순 인체 모형은 LLM에게 낯설어 프롬프트에 장면 성격을 알려 줘야 한다. detail=high로 올리면 정확도가 오르지만 토큰이 늘어난다.

### 08. 상황 서술
- LLM에는 영상이 아니라 정리된 상태 JSON을 준다(검출 요약, 사람 속성·근처 장소, 상자 좌표, 로봇 위치). 두 카메라가 같은 물체를 보면 map 위치 0.5 m 이내로 하나로 센다. 장소는 한국어 별칭으로 넘긴다(키를 주면 모델이 제멋대로 번역한다).
- 상태 서명이 바뀔 때만 호출한다. 55초 순찰 동안 5회 호출, 0.0007달러. 출력은 Utterance(speaker=robot)로 `/warehouse/narration`에 발행되어 M4의 텍스트 콘솔이 보여 준다.

![tracking preview](01_tracks.png)

## 4. 이번 모듈에서 고친 기반 코드

- `warehouse_lecture/vision/yolo_detector.py` 추가: 01+02를 합친 `YoloDetector3D`(TruthDetector와 같은 Detection3DArray 계약). M5는 이것을 LECTURE_HANDLERS에 넣는다.
- `warehouse_skills/locate.py` VisionLocator: map 검출을 tf2로 base_footprint에 되돌린다(정답 자세 사용 금지). `pick_place_server.py`: vision 모드에서 물체 이름→색 라벨.
- `examples/m3_llm/questions.yaml`: 20개 질의 채점표(M4 명령 문법 테스트에도 재사용).

## 5. 다음 (M4)

명령 문법·실행기(RobotCommand → Nav2/PickPlace/팔 자세), 텍스트 대화 루프(음성은 쓰지 않기로 결정). 06의 Structured Outputs 스키마와 questions.yaml을 그대로 확장한다.
