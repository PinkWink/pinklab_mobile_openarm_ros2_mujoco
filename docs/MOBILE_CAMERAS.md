# MuJoCo 카메라 4대 · Python 직접 수신

주행 베이스 1대, 머리 위치의 상단 카메라 1대, 왼손·오른손 끝에 각각 1대를 장착했습니다. 머리 형상은 없으며 상단 카메라는 작은 지지대에 고정됩니다. 카메라 프레임은 통합 URDF에도 들어 있어 RViz와 MuJoCo의 장착 위치가 같습니다.

**영상은 실행 중인 MuJoCo의 `model`·`data`에서 Python으로 직접 렌더링합니다.** `Image`, `CompressedImage`, `CameraInfo` ROS 토픽이나 영상 브리지를 만들지 않습니다. 주행·MoveIt·관절 상태·TF는 기존 ROS 2 인터페이스를 사용합니다.

## 위치와 기본 설정

| 이름 | 부착 링크 | 위치 (부모 링크 기준, m) | 방향 / 수직 시야각 |
|---|---|---|---|
| `base_camera` | `base_link` | `(0.33, 0, 0.12)` | 주행 전방 / 65° |
| `head_camera` | `openarm_body_link0` | `(0.06, 0, 0.88)` | 전방에서 아래로 약 14° / 60° |
| `left_wrist_camera` | `openarm_left_hand` | `(0.06, 0, 0.015)` | 그리퍼 집기 방향으로 기울임 / 75° |
| `right_wrist_camera` | `openarm_right_hand` | `(0.06, 0, 0.015)` | 그리퍼 집기 방향으로 기울임 / 75° |

설정: `src/mobile_openarm_description/config/cameras.yaml`. 해상도 기본 **640 × 480**, 주기 **시뮬레이션 시간 기준 5 FPS**, near/far **0.01m / 50m**입니다. `xyz`, `rpy`, `fovy`, `render` 항목을 수정하고 빌드·재실행하면 URDF와 MJCF에 함께 반영됩니다. MJCF offscreen 최대 크기는 1600 × 1000입니다.

손목 카메라는 팔과 함께 이동·회전합니다. 영상 방향을 항상 수평으로 유지하는 안정화 카메라가 아닙니다. 장착 위치는 실습용 초기 배치이며 실제 카메라 사양을 정한 뒤 조정할 수 있습니다. 하우징과 지지대는 시각 형상만 있고 질량·충돌 형상은 없는 이상적인 센서입니다.

## 실행 중인 로봇의 영상을 받기

```bash
./scripts/mobile_openarm build
./scripts/mobile_openarm start \
  camera_handler:=mobile_openarm_mujoco.camera_demo:handle_frames
```

이 예제는 같은 시뮬레이터 프로세스에서 `handle_frames(frames)`를 호출합니다. 4대의 RGB NumPy 배열이 직접 들어오며, 예제 콜백은 매 시뮬레이션 1초마다 최신 PNG와 보정값 JSON을 `artifacts/mobile_generated/cameras/`에 덮어씁니다. 파일 저장은 확인용 예제 동작이며 영상 처리 코드는 전달받은 배열을 바로 사용하면 됩니다.

깊이도 받고, 캡처 부하를 줄이려면:

```bash
./scripts/mobile_openarm start \
  camera_handler:=mobile_openarm_mujoco.camera_demo:handle_frames \
  camera_depth:=true camera_fps:=2
```

viewer 없이도 카메라 렌더링은 가능합니다. 위 명령에 `viewer:=false rviz:=false`를 붙입니다. 화면 창이 없더라도 OpenGL 렌더링 환경은 필요합니다. Linux 디스플레이 없는 GPU 서버는 지원되는 드라이버에서 `MUJOCO_GL=egl`을 사용할 수 있습니다. macOS viewer는 실행 스크립트가 `mjpython`을 선택합니다.

`camera_handler`를 생략하면 카메라 장착은 유지하며 자동 렌더링은 하지 않습니다. 서로 다른 launch 명령을 동시에 실행하지 말고 기존 세션을 Ctrl+C로 종료한 후 시작합니다.

## 내 Python 영상 처리 코드 연결

예를 들어 `src/mobile_openarm_mujoco/mobile_openarm_mujoco/my_vision.py`를 만듭니다:

```python
def handle_frames(frames):
    base_rgb = frames["base_camera"].rgb
    upper_rgb = frames["head_camera"].rgb
    left_rgb = frames["left_wrist_camera"].rgb
    right_rgb = frames["right_wrist_camera"].rgb

    left = frames["left_wrist_camera"]
    depth = left.depth_m          # camera_depth:=true일 때 float32 배열
    K = left.K                    # 3x3 내부 파라미터
    T = left.T_world_optical      # 4x4: 광학 좌표 → MuJoCo world
    # 여기에 검출·분할·집기 위치 추정 코드를 연결합니다.
```

```bash
./scripts/mobile_openarm build
./scripts/mobile_openarm start \
  camera_handler:=mobile_openarm_mujoco.my_vision:handle_frames \
  camera_depth:=true
```

4대는 동일한 물리 상태와 `sim_time`에서 읽습니다. 콜백은 물리 스텝 사이에 동기적으로 호출됩니다. 렌더링·추론이 오래 걸리면 실제 시간 대비 시뮬레이션 진행이 느려질 수 있으므로 FPS를 조정하거나 전달받은 배열을 별도 작업 큐로 넘기세요. 배열은 렌더러 내부 버퍼의 복사본입니다. 다른 스레드에서 MuJoCo `data`를 동시에 변경하거나 이 렌더러를 호출하면 안 됩니다.

별도 Python 프로세스를 실행하는 것만으로 이미 실행 중인 시뮬레이터에 붙지는 않습니다. 실행 중인 로봇 영상을 사용하려면 위 콜백을 사용합니다. 프로세스 간 공유 메모리 전송은 현재 구현 범위에 포함하지 않습니다.

## Python에서 시뮬레이터를 직접 소유하는 경우

`CameraRig`는 ROS를 import하지 않으며 어떤 `MjModel`·`MjData`에도 사용할 수 있습니다. 자신의 시뮬레이션 루프에서:

```python
from mobile_openarm_mujoco.cameras import CameraRig

# model과 data는 이미 구동 중인 내 MuJoCo 시뮬레이터의 객체입니다.
with CameraRig(model, data, width=640, height=480) as cameras:
    frame = cameras.read("left_wrist_camera", depth=True)
    rgb = frame.rgb
    all_frames = cameras.read_all(depth=True)
```

`read()`와 `read_all()`은 렌더링 전 자세를 갱신하지만 물리 시간을 진행시키지 않습니다. 생성·읽기·닫기는 같은 스레드에서 수행합니다. 첫 읽기까지 GPU 컨텍스트를 만들지 않습니다.

## 배열과 좌표 규약

- `rgb`: `(H, W, 3)`, `uint8`, RGB 순서, 영상 좌측 상단이 원점.
- `depth_m`: `(H, W)`, `float32`, 광학 +Z 축 깊이(m). 카메라에서의 유클리드 거리가 아닙니다. far clip 배경은 `inf`, 깊이를 요청하지 않으면 `None`.
- `K`: 정사각 픽셀, 왜곡 없는 pinhole. 정수 좌표가 픽셀 중심이며 주점은 `((W-1)/2, (H-1)/2)`.
- `T_world_optical`: 광학 좌표 **+X 오른쪽, +Y 아래, +Z 전방** → MuJoCo world. ROS의 `map`·`odom`과 같은 좌표라고 가정하지 않습니다.
- `optical_frame`: `<camera_name>_optical_frame`; `sim_time`: 시뮬레이션 초.

유효 깊이 `z`의 픽셀 `(u, v)`는 `p_optical = z * inv(K) @ [u, v, 1]`로 역투영합니다. world 좌표는 `T_world_optical @ [p_optical_x, p_optical_y, p_optical_z, 1]`입니다. MuJoCo의 렌더링 카메라 축과 URDF 광학 축 차이는 API가 변환합니다.

## 검증과 예제 영상

```bash
./scripts/mobile_openarm exec python -m pytest \
  tests/test_mobile_openarm.py tests/test_mobile_cameras.py -q
./scripts/mobile_openarm exec python scripts/check_mobile_cameras.py
# MoveIt와 camera_demo 콜백 + depth가 실행 중일 때, 양팔이 움직이는 검사:
./scripts/mobile_openarm exec python scripts/check_mobile_cameras_live.py
```

독립 렌더링 검사는 별도의 장면을 생성합니다. 결과: `artifacts/mobile_cameras/four_cameras.png`, `validation.json`. 라이브 검사는 실행 중인 로봇의 카메라 갱신·손목 이동·ROS 영상 토픽 부재를 확인하며 결과는 `artifacts/mobile_openarm_camera_live.json`입니다. 물체 인식이나 완전한 pick-and-place는 아직 구현하지 않았습니다.

API 참고: [MuJoCo Python 렌더링](https://mujoco.readthedocs.io/en/3.6.0/python.html), [MuJoCo camera](https://mujoco.readthedocs.io/en/3.6.0/XMLreference.html#body-camera).
