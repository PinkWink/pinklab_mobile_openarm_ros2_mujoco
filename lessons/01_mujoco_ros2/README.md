# 01. MuJoCo + ROS 2 연결 — 최소 브리지 (Day 1 ①②)

## 목표

MuJoCo를 ROS 2에 연결하는 데 필요한 것이 "스텝 루프 하나"임을 본다. 2링크 팔과 팔 끝 카메라만 있는 작은 모델로, 시뮬레이터가 ROS 2에 무엇을 내보내고 무엇을 받는지 확인한다. 창고 패키지의 브리지(`src/mobile_openarm_mujoco/.../bridge.py`)는 이 루프에 라이다 · 오도메트리 · 궤적 액션 · 카메라 핸들러를 더한 것이다.

## 파일

| 파일 | 내용 |
|---|---|
| `two_link_arm.xml` | MJCF. 링크 2개(hinge 2개), 위치 액추에이터 2개, 팔 끝 카메라 `tip_camera`, 바닥의 빨강 · 파랑 상자 |
| `minimal_bridge.py` | 브리지 노드. MuJoCo를 스텝하며 `/clock` `/joint_states` `/tf` `/tip_camera/image_raw`를 내고 `/cmd`를 받는다 |

## 실행

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh

# 터미널 1: 브리지 (MuJoCo 창 포함)
python lessons/01_mujoco_ros2/minimal_bridge.py --viewer

# 터미널 2: 무엇이 나오는지
ros2 topic list
ros2 topic hz /joint_states                 # 50 Hz
ros2 topic echo --once /joint_states
ros2 run tf2_ros tf2_echo base_link camera_link
ros2 run rqt_image_view rqt_image_view /tip_camera/image_raw   # 팔 끝 카메라 영상

# 터미널 2: 관절 목표 보내기 (rad)
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.0, 0.0]}"
```

## 화면에서 볼 것

- MuJoCo 창에서 팔이 목표 각도로 움직이고, 같은 순간 `/joint_states` 값과 `tf2_echo`의 `camera_link` 위치가 바뀐다.
- rqt_image_view 에서 팔 끝 카메라가 보는 장면이 바뀐다. 카메라는 MuJoCo 안에서 렌더된다.
- `/clock` 이 시뮬레이션 시간을 낸다. `use_sim_time` 을 켠 노드는 이 시간을 따른다.

## 핵심 코드

`minimal_bridge.py` 의 `spin()` 이 전부다.

1. `mj_step` 한 번 → 시뮬레이션 시간이 `timestep`(2 ms) 만큼 간다.
2. `/clock` 발행.
3. 50 Hz 마다 `/joint_states` 와 `/tf` (base_link → link1 → link2 → camera_link). TF 는 MuJoCo 의 `xpos` / `xquat` 에서 부모 기준 상대 자세로 계산한다.
4. 5 Hz 마다 카메라 렌더 → `sensor_msgs/Image` 로 발행.
5. `spin_once` 로 `/cmd` 콜백을 처리 → `data.ctrl` 에 목표 각도를 넣는다. 액추에이터가 위치 제어를 한다.
6. 벽시계와 맞춰 잔다 → 실시간.

Gazebo 라면 이 일을 `gz_ros2_control` 과 센서 플러그인이 한다. MuJoCo 에는 그런 플러그인이 없어서 Python 루프로 직접 쓴다. 대신 무엇이 언제 나가는지 코드 한 화면에서 다 보인다.

## 해 볼 것

- `--camera-hz 20` 으로 올리고 `ros2 topic hz /tip_camera/image_raw` 와 CPU 사용량을 본다. 창고 패키지가 영상을 토픽으로 흘리지 않고 검출 결과만 내는 이유가 여기 있다.
- `two_link_arm.xml` 의 `kp` 를 5 로 낮추면 팔이 늘어진다. 위치 액추에이터의 강성이 무엇인지 본다.
- `link3` 을 하나 더 붙이고 `joints` / `bodies` 목록에 넣어 본다.

## 문제 해결

- `ModuleNotFoundError: mujoco` → `source scripts/env.sh` 를 안 했다. 가상환경 python 이어야 한다.
- 창이 안 뜨고 `GLFW` 오류 → 화면 없는 환경. `--viewer` 를 빼면 카메라 렌더는 오프스크린으로 계속 된다.
- 창고 시뮬레이터와 동시에 띄우지 않는다. 둘 다 `/clock` `/joint_states` `/tf` 를 낸다.
