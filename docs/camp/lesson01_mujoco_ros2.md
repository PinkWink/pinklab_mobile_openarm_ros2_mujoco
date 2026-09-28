## 1. Gazebo vs MuJoCo

### 두 시뮬레이터

![Gazebo와 MuJoCo](lesson01_profile.png){width=1000}

- Gazebo는 ROS의 기본 시뮬레이터다. 서버 · 플러그인 · GUI가 한 프레임워크에 들어 있다.
- MuJoCo는 물리 엔진이다. 연구 · 강화학습 · 로봇 제어에서 표준으로 쓰인다.
- 둘 다 Apache 2.0 오픈소스다. 차이는 "얼마나 많은 것을 대신 해 주는가"에 있다.

### 구조 비교

![구조 비교](lesson01_arch.png){width=1000}

- Gazebo: gz-sim 서버가 세계를 돌린다. 센서 플러그인과 gz_ros2_control이 값을 낸다. ros_gz_bridge가 ROS 2 토픽으로 바꾼다.
- MuJoCo: Python 프로세스 하나다. `mj_step`을 부르고, 값을 읽고, rclpy로 발행한다.
- Gazebo는 층이 셋이다. MuJoCo는 우리가 쓴 루프 하나다.

### 물리 연산 방식

![물리 연산 비교](lesson01_physics.png){width=1000}

- 접촉: Gazebo(DART · ODE)는 강체 접촉을 LCP로 푼다. MuJoCo는 부드러운 접촉을 볼록 최적화로 푼다. 파지처럼 접촉이 많을 때 MuJoCo가 안정적이다.
- 시간 스텝: MuJoCo는 2 ms로도 안정하다. 같은 실시간 비율에서 계산량이 적다.
- 액추에이터: MuJoCo는 위치 · 속도 · 힘 액추에이터가 모델 안에 있다. 컨트롤러 스택 없이 관절을 잡는다.
- 센서: MuJoCo의 레이캐스트와 카메라 렌더는 함수 호출이다. 결과가 파이썬 배열로 온다.

### ROS 2 연동 방식

![ROS 2 연동 경로](lesson01_ros_path.png){width=1000}

- Gazebo: URDF/SDF에 플러그인 태그를 넣는다. gz-sim을 띄운다. ros_gz_bridge에 토픽 매핑 YAML을 준다.
- MuJoCo: MJCF를 만든다. Python 브리지가 표준 토픽 · TF · 액션을 낸다. Nav2와 MoveIt은 브리지가 Gazebo인지 MuJoCo인지 모른다.
- 브리지를 직접 쓰는 대신, 무엇이 언제 나가는지 코드 한 화면에서 다 보인다.

### 장단점

![장단점](lesson01_proscons.png){width=1000}

- Gazebo는 생태계가 넓다. 대신 무겁고, 저사양 노트북에서 느리다.
- MuJoCo는 가볍고 접촉이 안정적이다. 대신 ROS 2 연동과 월드를 직접 만든다.

### 이 과정에서 MuJoCo를 쓰는 이유

![MuJoCo를 고른 이유](lesson01_why.png){width=1000}

- 저사양 노트북에서 창고 + 양팔 + 카메라 4대가 실시간으로 돈다.
- 시뮬레이터 ↔ ROS 2 연결 코드가 파일 하나에 다 보인다. 이 페이지의 예제가 그 축소판이다.
- Pick & Place를 반복해도 상자가 튀지 않는다.
- 카메라를 Python에서 직접 받아 검출 결과만 발행한다.
- Gazebo는 설치하지 않는다. 비교 설명 이후 모든 실습은 MuJoCo로만 진행한다.

## 2. MuJoCo와 ROS 2 연결하기: 최소 브리지

### 예제 로봇: 2링크 팔 + 팔 끝 카메라

![예제 로봇](lesson01_arm.png){width=1000}

- 폴더: `lessons/01_mujoco_ros2/`. 파일 두 개다.
- `two_link_arm.xml`: MJCF. hinge 관절 2개, 위치 액추에이터 2개, 팔 끝 카메라 `tip_camera`, 바닥의 빨강 · 파랑 상자.
- `minimal_bridge.py`: 브리지 노드. 136줄이다.
- 관절 단위는 rad다. MJCF 기본은 도(degree)라서 `compiler angle="radian"`을 넣었다.
- 링크끼리는 충돌하지 않게 했다. 관절에서 캡슐이 겹치기 때문이다.

### 브리지가 주고받는 것

![브리지 입출력](lesson01_io.png){width=1000}

- 나가는 것: `/clock`, `/joint_states`(50 Hz), `/tf`(base_link → link1 → link2 → camera_link), `/tip_camera/image_raw`(320×240, 5 Hz).
- 들어오는 것: `/cmd`(`Float64MultiArray` [q1, q2] rad). 값이 `data.ctrl`에 들어가면 위치 액추에이터가 관절을 잡는다.
- 브리지 노드는 `use_sim_time`을 켠다. 시간은 `data.time`에서 온다.

### 스텝 루프

![스텝 루프](lesson01_loop.png){width=1000}

```python
def spin(self):
    wall0 = time.monotonic()
    while rclpy.ok():
        mujoco.mj_step(self.model, self.data)             # 1. physics step
        t = self.data.time
        self.clock_pub.publish(Clock(clock=stamp(t)))     # 2. sim time out
        if t >= self.next_joint:                          # 3. joint states + TF at 50 Hz
            self.publish_joints(t); self.next_joint += self.joint_period
        if t >= self.next_camera:                         # 4. camera image at 5 Hz
            self.publish_camera(t); self.next_camera += self.camera_period
        rclpy.spin_once(self, timeout_sec=0)              # 5. deliver /cmd callbacks
        lag = wall0 + t - time.monotonic()                # 6. keep real time
        if lag > 0:
            time.sleep(lag)
```

- 한 바퀴가 시뮬레이션 2 ms다. 발행 주기는 시뮬레이션 시간으로 센다.
- 마지막 `sleep`이 벽시계와 맞춘다. 이걸 빼면 CPU가 허용하는 만큼 빨리 돈다.
- Gazebo에서는 이 일을 gz_ros2_control과 센서 플러그인이 한다.

### 실행

![실행 방법](lesson01_run.png){width=1000}

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh

# 터미널 1: 브리지 (MuJoCo 창 포함)
python lessons/01_mujoco_ros2/minimal_bridge.py --viewer

# 터미널 2: 무엇이 나오는지
ros2 topic list
ros2 topic hz /joint_states
ros2 run tf2_ros tf2_echo base_link camera_link
ros2 run rqt_image_view rqt_image_view /tip_camera/image_raw

# 터미널 2: 관절 목표 보내기 (rad)
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.0, 0.0]}"
```

### 실행 결과

![실행 결과: MuJoCo 창(왼쪽)과 팔 끝 카메라 영상(오른쪽)](lesson01_run_result.png){width=1000}

```
$ ros2 topic list
/clock  /cmd  /joint_states  /parameter_events  /rosout  /tf  /tip_camera/image_raw

$ ros2 topic hz /joint_states
average rate: 50.004

$ ros2 topic echo --once /joint_states        (cmd [0.6, 1.5] 를 보낸 뒤)
name: [joint1, joint2]
position: [0.641, 1.517]

$ ros2 run tf2_ros tf2_echo base_link camera_link
- Translation: [0.396, 0.000, 0.156]
- Rotation: in RPY (radian) [3.142, 0.984, 3.142]

$ ros2 topic echo --once /tip_camera/image_raw --no-arr
frame_id: camera_link   height: 240   width: 320   encoding: rgb8   step: 960
```

### TF 트리

![TF 트리](lesson01_tf.png){width=1000}

- MuJoCo는 모든 body의 자세를 월드 기준(`xpos`, `xquat`)으로 준다.
- TF는 부모 → 자식 상대 자세다. `mju_negQuat`, `mju_mulQuat`, `mju_rotVecQuat` 세 함수로 바꾼다.
- 영상의 `frame_id`가 `camera_link`다. 그래서 검출 결과를 TF로 다른 프레임에 옮길 수 있다.

### 창고 브리지와의 관계

![창고 브리지로](lesson01_to_warehouse.png){width=1000}

- 창고 패키지의 브리지(`src/mobile_openarm_mujoco/mobile_openarm_mujoco/bridge.py`)는 같은 루프다.
- 더해진 것: 라이다 레이캐스트 → `/scan`, 바퀴 → `/odom` + TF, `/cmd_vel` 수신, FollowJointTrajectory 액션, 카메라 핸들러.
- 카메라 핸들러는 영상을 토픽으로 내지 않는다. 같은 프로세스에서 검출하고 `/vision/*`만 낸다.

### 해 볼 것

![해 볼 것](lesson01_try.png){width=1000}

- `--camera-hz 20`으로 올리고 CPU 사용량을 본다. 창고 브리지가 영상을 안 흘리는 이유가 보인다.
- `two_link_arm.xml`의 `kp`를 5로 낮춘다. 팔이 늘어진다.
- `link3`을 하나 더 붙이고 `joints` · `bodies` 목록에 넣는다. TF가 한 단 늘어난다.
