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

## 2. 로봇 모델 파일: two_link_arm.xml

### 로봇을 적는 두 형식: URDF와 MJCF

![URDF와 MJCF](lesson01_xml_formats.png){width=1000}

- URDF는 ROS의 로봇 기술 형식이다. RViz · MoveIt · robot_state_publisher가 읽는다.
- MJCF는 MuJoCo의 모델 형식이다. mujoco 라이브러리가 직접 읽는다.
- 둘 다 XML이다. 링크와 관절의 트리를 적는다는 점은 같다.
- 창고 로봇은 URDF(xacro)로 적고 MJCF로 바꿔 쓴다. 이 예제는 MJCF 하나만 쓴다.

### 트리를 적는 방법이 다르다

![트리를 적는 방법](lesson01_xml_tree.png){width=1000}

- URDF: `<link>`와 `<joint>`를 나란히 나열한다. `<joint>`의 parent · child 이름이 트리를 만든다.
- MJCF: `<body>` 안에 `<body>`를 넣어 트리를 만든다. 관절은 자식 body 안에 `<joint>`로 적는다.
- MJCF의 body `pos`는 부모 body 기준이다. URDF의 joint origin과 같은 역할이다.

### 파일 안에 담기는 것이 다르다

![파일 안에 담기는 것](lesson01_xml_contents.png){width=1000}

- URDF: 형상 · 관성 · 관절 한계까지다. 물리 옵션 · 액추에이터 · 센서는 파일 밖(ros2_control · 플러그인)에 있다.
- MJCF: `<option>`(중력 · 시간 스텝) · `<actuator>` · `<camera>` · `<light>`가 파일 안에 있다.
- 그래서 MJCF 파일 하나면 시뮬레이션이 바로 돈다. 브리지 없이 뷰어로 열 수 있다.

### 단위와 기본값이 다르다

![단위와 기본값](lesson01_xml_units.png){width=1000}

- 각도: URDF는 항상 rad다. MJCF는 기본이 도(degree)다. `compiler angle="radian"`으로 맞춘다.
- 관성: URDF는 `<inertial>`을 직접 적는다. MJCF는 geom 크기와 밀도에서 자동 계산한다.
- 충돌: URDF는 `<collision>`이 따로 있다. MJCF는 geom 하나가 시각과 충돌을 겸한다. `contype=0`으로 끈다.

### 모델만 먼저 보기: mujoco.viewer

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
python -m mujoco.viewer --mjcf=lessons/01_mujoco_ros2/two_link_arm.xml
```

![mujoco.viewer 로 연 two_link_arm.xml](lesson01_xml_viewer.png){width=1000}

### 파일 전체 구조

```xml
<mujoco model="two_link_arm">
  <compiler angle="radian"/>
  <option timestep="0.002" gravity="0 0 -9.81"/>
  <visual> ... </visual>
  <asset> ... </asset>
  <default> ... </default>
  <worldbody> ... </worldbody>
  <actuator> ... </actuator>
</mujoco>
```

![파일 전체 구조](lesson01_xml_structure.png){width=1000}

### compiler · option - 단위와 물리 스텝

```xml
<compiler angle="radian"/>
<option timestep="0.002" gravity="0 0 -9.81"/>
```

![compiler 와 option](lesson01_xml_compiler.png){width=1000}

### visual · asset - 렌더 크기와 바닥 무늬

```xml
<visual>
  <global offwidth="640" offheight="480"/>
</visual>
<asset>
  <texture name="grid" type="2d" builtin="checker" rgb1="0.85 0.85 0.85" rgb2="0.65 0.65 0.65" width="256" height="256"/>
  <material name="floor" texture="grid" texrepeat="6 6" reflectance="0.1"/>
</asset>
```

![visual 과 asset](lesson01_xml_asset.png){width=1000}

### default - 팔 링크의 공통 속성

```xml
<default>
  <!-- arm geoms do not collide with each other (capsules overlap at the joints) -->
  <default class="arm"><geom contype="0" conaffinity="0"/></default>
</default>
```

![default class arm](lesson01_xml_default.png){width=1000}

### worldbody - 빛 · 바닥 · 상자

```xml
<worldbody>
  <light pos="0.5 -0.5 2.0" dir="-0.3 0.3 -1"/>
  <geom name="floor" type="plane" size="2 2 0.05" material="floor"/>
  <geom name="red_box" type="box" pos="0.55 0.08 0.04" size="0.04 0.04 0.04" rgba="0.9 0.2 0.2 1"/>
  <geom name="blue_box" type="box" pos="0.62 -0.10 0.03" size="0.03 0.03 0.03" rgba="0.2 0.3 0.9 1"/>
  ...
</worldbody>
```

![worldbody 의 고정물](lesson01_xml_world.png){width=1000}

### body 트리 - base_link → link1 → link2 → camera_link

```xml
<body name="base_link" pos="0 0 0">
  <body name="link1" pos="0 0 0.06">
    <body name="link2" pos="0 0 0.30">
      <body name="camera_link" pos="0 0 0.26">
      </body>
    </body>
  </body>
</body>
```

![body 트리](lesson01_xml_bodies.png){width=1000}

### joint - hinge 관절 두 개

```xml
<body name="link1" pos="0 0 0.06">
  <joint name="joint1" type="hinge" axis="0 1 0" range="-1.57 1.57" damping="0.5"/>
  ...
  <body name="link2" pos="0 0 0.30">
    <joint name="joint2" type="hinge" axis="0 1 0" range="-2.0 2.0" damping="0.5"/>
```

![joint](lesson01_xml_joint.png){width=1000}

### geom - capsule 로 그린 링크

```xml
<geom class="arm" name="base" type="cylinder" size="0.05 0.03" pos="0 0 0.03" rgba="0.3 0.3 0.3 1"/>
<geom class="arm" name="link1_geom" type="capsule" fromto="0 0 0 0 0 0.30" size="0.02" rgba="0.2 0.5 0.9 1"/>
<geom class="arm" name="link2_geom" type="capsule" fromto="0 0 0 0 0 0.25" size="0.018" rgba="0.9 0.6 0.2 1"/>
<geom class="arm" name="camera_body" type="box" size="0.015 0.02 0.01" rgba="0.1 0.1 0.1 1"/>
```

![geom](lesson01_xml_geom.png){width=1000}

### camera - 팔 끝 카메라의 방향

```xml
<body name="camera_link" pos="0 0 0.26">
  <geom class="arm" name="camera_body" type="box" size="0.015 0.02 0.01" rgba="0.1 0.1 0.1 1"/>
  <camera name="tip_camera" pos="0 0 0.01" xyaxes="0 -1 0 -1 0 0" fovy="60"/>
</body>
```

![camera](lesson01_xml_camera.png){width=1000}

### actuator - 관절을 잡는 위치 액추에이터

```xml
<actuator>
  <position name="joint1_pos" joint="joint1" kp="30" ctrlrange="-1.57 1.57"/>
  <position name="joint2_pos" joint="joint2" kp="20" ctrlrange="-2.0 2.0"/>
</actuator>
```

![actuator](lesson01_xml_actuator.png){width=1000}

### 브리지가 이 파일에서 찾는 이름

![브리지가 찾는 이름](lesson01_xml_names.png){width=1000}

## 3. MuJoCo와 ROS 2 연결하기: 최소 브리지

### 예제 로봇: 2링크 팔 + 팔 끝 카메라

![예제 로봇](lesson01_arm.png){width=1000}

- 폴더: `lessons/01_mujoco_ros2/`. 파일 두 개다.
- `two_link_arm.xml`: MJCF. hinge 관절 2개, 위치 액추에이터 2개, 팔 끝 카메라 `tip_camera`, 바닥의 빨강 · 파랑 상자.

### 브리지가 주고받는 것

![브리지 입출력](lesson01_io.png){width=1000}

- 나가는 것: `/clock`, `/joint_states`(50 Hz), `/tf`(base_link → link1 → link2 → camera_link), `/tip_camera/image_raw`(320×240, 5 Hz).
- 들어오는 것: `/cmd`(`Float64MultiArray` [q1, q2] rad). 값이 `data.ctrl`에 들어가면 위치 액추에이터가 관절을 잡는다.
- 브리지 노드는 `use_sim_time`을 켠다. 시간은 `data.time`에서 온다.

### 스텝 루프

![스텝 루프](lesson01_loop.png){width=1000}

### 스텝 루프 def spin 코드

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

### 실행: 터미널 1 (브리지)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
python lessons/01_mujoco_ros2/minimal_bridge.py --viewer     # MuJoCo 창 포함
```

![터미널 1: 브리지 실행](lesson01_t1_bridge.png){width=1000}

### minimal_bridge.py 의 실행 결과

![minimal_bridge.py 실행 결과: MuJoCo 창(왼쪽)과 팔 끝 카메라 영상(오른쪽)](lesson01_run_result.png){width=1000}

### 터미널 2: 환경 설정

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
```

![터미널 2: 환경 설정](lesson01_t2_source.png){width=1000}

### 터미널 2: ros2 topic list

```bash
ros2 topic list
```

![ros2 topic list](lesson01_cli_topic_list.png){width=1000}

### 터미널 2: ros2 topic hz /joint_states

```bash
ros2 topic hz /joint_states
```

![ros2 topic hz /joint_states](lesson01_cli_hz.png){width=1000}

### 터미널 2: tf2_echo base_link camera_link

```bash
ros2 run tf2_ros tf2_echo base_link camera_link
```

![tf2_echo base_link camera_link](lesson01_cli_tf_echo.png){width=1000}

### 터미널 2: rqt_image_view /tip_camera/image_raw

```bash
ros2 run rqt_image_view rqt_image_view /tip_camera/image_raw
```

![rqt_image_view 실행](lesson01_t2_rqt_cmd.png){width=1000}

![rqt_image_view 창: 팔 끝 카메라 영상](lesson01_t2_rqt_window.png){width=600}

### 터미널 2: ros2 topic pub /cmd [0.6, 1.5]

```bash
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.6, 1.5]}"
ros2 topic echo --once /joint_states
```

![ros2 topic pub /cmd 후 ros2 topic echo /joint_states](lesson01_cli_joint_states.png){width=1000}

### [0.6, 1.5] 를 보내기 전후의 MuJoCo 창과 카메라 영상

- 아래는 같은 순간의 MuJoCo 창과 팔 끝 카메라 영상이다. 왼쪽이 보내기 전, 오른쪽이 보낸 뒤다.
- 보내기 전 카메라 영상이 검은 것은 정상이다. 초기 자세에서는 팔이 수직이라 카메라가 하늘을 본다.

![topic pub 전후의 MuJoCo 창과 카메라 영상](lesson01_pub1_motion.png){width=1000}

### 터미널 2: ros2 topic pub /cmd [0.0, 0.0]

```bash
ros2 topic pub -1 /cmd std_msgs/msg/Float64MultiArray "{data: [0.0, 0.0]}"
```

![ros2 topic pub /cmd [0.0, 0.0]](lesson01_t2_pub2.png){width=1000}

### [0.0, 0.0] 을 보내기 전후의 MuJoCo 창

- 왼쪽이 보내기 전, 오른쪽이 보낸 뒤다. 팔이 초기 자세로 돌아온다.

![topic pub [0.0, 0.0] 전후의 MuJoCo 창](lesson01_pub2_motion.png){width=1000}

### 터미널 2: ros2 topic echo /tip_camera/image_raw

```bash
ros2 topic echo --once /tip_camera/image_raw --no-arr
```

![ros2 topic echo /tip_camera/image_raw](lesson01_cli_image.png){width=1000}

### TF 트리

![TF 트리](lesson01_tf.png){width=1000}

- MuJoCo는 모든 body의 자세를 월드 기준(`xpos`, `xquat`)으로 준다.
- TF는 부모 → 자식 상대 자세다. `mju_negQuat`, `mju_mulQuat`, `mju_rotVecQuat` 세 함수로 바꾼다.
- 영상의 `frame_id`가 `camera_link`다. 그래서 검출 결과를 TF로 다른 프레임에 옮길 수 있다.

### Python과 MuJoCo의 연결

```python
import mujoco
import mujoco.viewer

self.model = mujoco.MjModel.from_xml_path(str(XML))                  # 모델 (상수)
self.data = mujoco.MjData(self.model)                                # 상태 (매 스텝 변함)
mujoco.mj_step(self.model, self.data)                                # 물리 한 스텝
self.renderer = mujoco.Renderer(self.model, height=240, width=320)   # 오프스크린 카메라
self.viewer = mujoco.viewer.launch_passive(self.model, self.data)    # 화면 창 (선택)
```

![Python 코드가 MuJoCo 와 만나는 다섯 곳](lesson01_py_overview.png){width=1000}

### 모델 읽기 - MjModel.from_xml_path

```python
XML = Path(__file__).with_name("two_link_arm.xml")
self.model = mujoco.MjModel.from_xml_path(str(XML))
dt = self.model.opt.timestep          # 0.002
self.model.nq, self.model.nu          # 관절 수 2, 액추에이터 수 2
```

![MjModel](lesson01_py_model.png){width=1000}

### 상태 만들기 - MjData

```python
self.data = mujoco.MjData(self.model)
self.data.time                      # 시뮬레이션 시각 (초)
self.data.qpos, self.data.qvel      # 관절 각 · 각속도
self.data.xpos, self.data.xquat     # body 위치 · 자세 (월드 기준)
self.data.ctrl                      # 액추에이터 목표
```

![MjData](lesson01_py_data.png){width=1000}

### 물리 한 스텝 - mj_step

```python
while rclpy.ok():
    mujoco.mj_step(self.model, self.data)   # data.time += model.opt.timestep
    t = self.data.time
```

![mj_step](lesson01_py_step.png){width=1000}

### 이름으로 찾기 - model.joint · model.body

```python
self.model.joint("joint1").qposadr[0]   # qpos 안의 번호
self.model.joint("joint1").dofadr[0]    # qvel 안의 번호
self.model.body("link1").id             # xpos · xquat 의 행 번호
```

![이름으로 찾기](lesson01_py_names.png){width=1000}

### 오프스크린 렌더 - Renderer

```python
self.renderer = mujoco.Renderer(self.model, height=240, width=320)   # __init__ 에서 한 번
self.renderer.update_scene(self.data, camera="tip_camera")           # 5 Hz 마다
rgb = self.renderer.render()                                          # (240, 320, 3) uint8
```

![Renderer](lesson01_py_renderer.png){width=1000}

### 화면 창 - viewer.launch_passive

```python
if viewer:
    self.viewer = mujoco.viewer.launch_passive(self.model, self.data)

while rclpy.ok() and (self.viewer is None or self.viewer.is_running()):
    ...
    if self.viewer is not None:
        self.viewer.sync()
```

![viewer](lesson01_py_viewer.png){width=1000}

### 실시간 맞추기 - 벽시계와 시뮬레이션 시각

```python
wall0 = time.monotonic()
while ...:
    mujoco.mj_step(self.model, self.data)
    ...
    lag = wall0 + t - time.monotonic()   # 시뮬레이션이 벽시계보다 앞선 만큼
    if lag > 0:
        time.sleep(lag)
```

![실시간 맞추기](lesson01_py_realtime.png){width=1000}

### 노드 초기화 - __init__ 함수

```python
self.model = mujoco.MjModel.from_xml_path(str(XML))
self.data = mujoco.MjData(self.model)
self.joints = ["joint1", "joint2"]
self.bodies = ["base_link", "link1", "link2", "camera_link"]

self.clock_pub = self.create_publisher(Clock, "/clock", 10)
self.joint_pub = self.create_publisher(JointState, "/joint_states", 10)
self.image_pub = self.create_publisher(Image, "/tip_camera/image_raw", 2)
self.tf_pub = TransformBroadcaster(self)
self.create_subscription(Float64MultiArray, "/cmd", self.on_cmd, 10)

self.renderer = mujoco.Renderer(self.model, height=240, width=320)
self.joint_period, self.camera_period = 1.0 / joint_hz, 1.0 / camera_hz
```

![__init__ 구조](lesson01_fn_init.png){width=1000}

### Joint State 발행 - publish_joints 함수 (앞부분)

```python
def publish_joints(self, t):
    js = JointState()
    js.header.stamp = stamp(t)
    js.name = self.joints
    js.position = [float(self.data.qpos[self.model.joint(j).qposadr[0]]) for j in self.joints]
    js.velocity = [float(self.data.qvel[self.model.joint(j).dofadr[0]]) for j in self.joints]
    self.joint_pub.publish(js)
```

![publish_joints 앞부분 구조](lesson01_fn_joints.png){width=1000}

### TF 발행 - publish_joints 함수 (뒷부분)

```python
    tfs = []
    for parent, child in zip(self.bodies[:-1], self.bodies[1:]):
        p, c = self.model.body(parent).id, self.model.body(child).id
        # child pose expressed in the parent body frame: q_rel = conj(q_parent) * q_child
        q_parent_inv, q_rel, pos_rel = np.zeros(4), np.zeros(4), np.zeros(3)
        mujoco.mju_negQuat(q_parent_inv, self.data.xquat[p])
        mujoco.mju_mulQuat(q_rel, q_parent_inv, self.data.xquat[c])
        mujoco.mju_rotVecQuat(pos_rel, self.data.xpos[c] - self.data.xpos[p], q_parent_inv)
        tf = TransformStamped()
        tf.header.stamp, tf.header.frame_id, tf.child_frame_id = stamp(t), parent, child
        tf.transform.translation.x, tf.transform.translation.y, tf.transform.translation.z = map(float, pos_rel)
        tf.transform.rotation.w, tf.transform.rotation.x, tf.transform.rotation.y, tf.transform.rotation.z = map(float, q_rel)
        tfs.append(tf)
    self.tf_pub.sendTransform(tfs)
```

![publish_joints 뒷부분 구조](lesson01_fn_tf.png){width=1000}

### 카메라 영상 발행 - publish_camera 함수

```python
def publish_camera(self, t):
    self.renderer.update_scene(self.data, camera="tip_camera")
    rgb = self.renderer.render()
    img = Image()
    img.header.stamp, img.header.frame_id = stamp(t), "camera_link"
    img.height, img.width, img.encoding, img.step = rgb.shape[0], rgb.shape[1], "rgb8", rgb.shape[1] * 3
    img.data = rgb.tobytes()
    self.image_pub.publish(img)
```

![publish_camera 구조](lesson01_fn_camera.png){width=1000}

### 명령 수신 - on_cmd 함수

```python
def on_cmd(self, msg):
    if len(msg.data) == self.model.nu:
        self.data.ctrl[:] = np.clip(msg.data, self.model.actuator_ctrlrange[:, 0], self.model.actuator_ctrlrange[:, 1])
```

![on_cmd 구조](lesson01_fn_cmd.png){width=1000}

### 시뮬레이션 시각 - stamp 함수와 /clock

```python
def stamp(t):
    """float seconds -> builtin_interfaces/Time"""
    return Time(sec=int(t), nanosec=int((t - int(t)) * 1e9))

# spin() 안에서 매 스텝
self.clock_pub.publish(Clock(clock=stamp(t)))
```

![stamp 와 /clock 구조](lesson01_fn_clock.png){width=1000}

### 창고 브리지와의 관계

![창고 브리지로](lesson01_to_warehouse.png){width=1000}

### MuJoCo <-> ROS2

![MuJoCo와 ROS 2 사이에 오가는 토픽](lesson01_exchange.png){width=1000}

### 해 볼 것

![해 볼 것](lesson01_try.png){width=1000}

- `--camera-hz 20`으로 올리고 CPU 사용량을 본다. 창고 브리지가 영상을 안 흘리는 이유가 보인다.
- `two_link_arm.xml`의 `kp`를 5로 낮춘다. 팔이 늘어진다.
- `link3`을 하나 더 붙이고 `joints` · `bodies` 목록에 넣는다. TF가 한 단 늘어난다.
