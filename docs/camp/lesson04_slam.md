## 1. SLAM 이란

### Odom 만으로는 부족하다

![Odom 만으로는 부족한 이유](lesson04_why_slam.png){width=1000}

### SLAM: 위치 추정과 지도 작성을 함께

![SLAM 의 순환 구조](lesson04_slam_loop.png){width=1000}

### 점유 격자 지도 (Occupancy Grid)

![점유 격자 지도](lesson04_occupancy.png){width=1000}

### TF: map → odom → base_footprint

![map → odom → base_footprint](lesson04_tf_chain.png){width=1000}

### SLAM Toolbox

![SLAM Toolbox 의 구성](lesson04_toolbox.png){width=1000}

### 스캔 매칭

![스캔 매칭](lesson04_scan_matching.png){width=1000}

### 포즈 그래프와 루프 클로징

![포즈 그래프와 루프 클로징](lesson04_pose_graph.png){width=1000}

## 2. 실행: 창고 지도 만들기

### slam 모드가 띄우는 것

![slam 모드가 띄우는 프로세스](lesson04_slam_tree.png){width=1000}

### 실행: 터미널 1 (slam)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
./scripts/mobile_openarm slam actors:=none     # 사람 · 지게차 없이 (움직이는 물체가 지도에 남지 않게)
```

### 실행 결과: 터미널 1

![터미널 1: slam 실행](lesson04_t1_slam.png){width=1000}

### 실행 결과: 시작 화면

![MuJoCo 창(왼쪽)과 RViz2(오른쪽, Fixed Frame map): 출발 자리에서 본 첫 지도](lesson04_run_result.png){width=1000}

### 터미널 2: ros2 node list · ros2 topic list

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
ros2 node list
ros2 topic list | grep -E 'map|slam|pose'
```

### 실행 결과: node list · topic list

![slam_toolbox 노드와 /map 토픽](lesson04_cli_nodes.png){width=1000}

### 터미널 3: teleop 으로 운전

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
./scripts/mobile_openarm teleop
```

### 실행 결과: teleop

![teleop_twist_keyboard](lesson04_t3_teleop.png){width=1000}

### teleop 키와 운전 요령

![teleop 키](lesson04_teleop_keys.png){width=1000}

### 터미널 3: 자동 순회 (teleop 대신)

```bash
python docs/camp/slam_tour.py        # 가장자리 통로를 한 바퀴 돌고 출발점으로 (약 58 m)
```

### 실행 결과: 자동 순회

![slam_tour.py 출력](lesson04_cli_tour.png){width=1000}

### 지도가 자라는 모습

![출발 → 한 바퀴: 실제 /map 기록](lesson04_map_growth.png){width=1000}

### 움직이는 그림: 지도가 자라는 모습

![지도가 자라는 모습 (움직이는 그림)](lesson04_map_growth.gif){width=900}

### 실행 결과: 한 바퀴 뒤의 화면

![한 바퀴 뒤 RViz2 의 지도](lesson04_final_screen.png){width=1000}

### 터미널 2: map → odom 보정값

```bash
ros2 run tf2_ros tf2_echo map odom
```

### 실행 결과: map → odom

![한 바퀴 뒤 map → odom](lesson04_cli_tf_map_odom.png){width=1000}

### 터미널 2: /map 정보와 주기

```bash
ros2 topic echo --once /map --field info
ros2 topic hz /map
```

### 실행 결과: /map 정보와 주기

![/map 의 info 와 발행 주기](lesson04_cli_map_info.png){width=1000}

### 실제 포즈 그래프

![한 바퀴 뒤 slam_toolbox 의 포즈 그래프](lesson04_pose_graph_real.png){width=1000}

## 3. 지도 저장

### map_saver_cli

![map_saver_cli 가 만드는 파일](lesson04_map_files.png){width=1000}

### 터미널 2: 지도 저장

```bash
mkdir -p artifacts/maps
ros2 run nav2_map_server map_saver_cli -f artifacts/maps/my_warehouse
cat artifacts/maps/my_warehouse.yaml
```

### 실행 결과: 지도 저장

![map_saver_cli 실행 결과](lesson04_cli_map_saver.png){width=1000}

### yaml 의 뜻

![yaml 필드](lesson04_yaml_fields.png){width=1000}

### 내 지도와 패키지 지도

![SLAM 지도와 패키지 지도 비교](lesson04_map_compare.png){width=1000}

### 라이다 높이와 지도

![라이다 평면 높이](lesson04_lidar_height.png){width=1000}

## 4. 코드와 설정

### mode 에 따른 분기

![navigation.launch.py 의 분기](lesson04_launch_branch.png){width=1000}

### slam · nav 일 때 navigation.launch 부르기 - warehouse.launch.py setup 함수 발췌

```python
# mobile_openarm_bringup/launch/warehouse.launch.py
def setup(context):   # 발췌
    mode = LaunchConfiguration("mode").perform(context)
    nav = Path(get_package_share_directory("mobile_openarm_navigation"))
    if mode != "drive":                                   # slam · nav 일 때만
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(nav / "launch/navigation.launch.py")),
                launch_arguments={"mode": mode, "map": LaunchConfiguration("map").perform(context), ...}.items(),
            )
        )
```

- `mode:=drive` 면 SLAM · Nav2 쪽 launch 를 아예 부르지 않음
- `mode` · `map` 인자를 그대로 넘김 → 갈라지는 곳은 `navigation.launch.py` 한 군데

### RViz 띄우기와 Fixed Frame 고르기 - warehouse.launch.py setup 함수 발췌

```python
# warehouse.launch.py setup (이어서)
    if moveit:
        ...                                               # MoveIt 이 자기 RViz 를 띄운다
    elif rviz:
        actions.append(Node(package="rviz2", executable="rviz2",
                            arguments=["-d", str(nav / "config/navigation.rviz"),
                                       "-f", "odom" if mode == "drive" else "map"],   # slam 이면 Fixed Frame = map
                            parameters=[{"use_sim_time": True}]))
```

- drive 는 `map` 프레임이 없어서 Fixed Frame = `odom` · slam · nav 는 `map`
- `-f` 로 Fixed Frame 만 바꿈 → RViz 설정 파일은 하나를 함께 씀

### slam_toolbox launch 포함하기 - navigation.launch.py setup 함수 발췌

```python
# mobile_openarm_navigation/launch/navigation.launch.py
def setup(context):   # 발췌
    share = Path(get_package_share_directory("mobile_openarm_navigation"))
    mode = LaunchConfiguration("mode").perform(context)
    mapfile = LaunchConfiguration("map").perform(context)
    actions = []
    if mode == "slam" or (mode == "nav" and not mapfile):
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(Path(get_package_share_directory("slam_toolbox")) / "launch/online_async_launch.py")
                ),
```

- slam 모드이거나, nav 모드인데 지도 파일이 없으면 SLAM 을 띄움
- `online_async` = 달리면서 실시간으로 · 계산이 밀리면 스캔을 건너뜀

### slam_toolbox 에 넘기는 인자 - navigation.launch.py setup 함수 발췌

```python
# navigation.launch.py setup (이어서)
                launch_arguments={
                    "use_sim_time": "true",                                  # /clock 기준
                    "autostart": "true",                                     # lifecycle 을 바로 active 로
                    "slam_params_file": str(share / "config/slam.yaml"),
                }.items(),
            )
        )
    ...                                                                      # nav: map_server · amcl · Nav2 (⑥)
    return actions
```

- `use_sim_time`: `/clock` (시뮬레이션 시각) 기준으로 동작
- `autostart`: lifecycle 노드를 띄우자마자 active 로
- 나머지 설정은 모두 `slam.yaml`

### slam.yaml 주요 파라미터

![slam.yaml 파라미터](lesson04_params.png){width=1000}

### 좌표계와 입력 토픽 - slam.yaml 발췌

```yaml
# mobile_openarm_navigation/config/slam.yaml  (발췌)
slam_toolbox:
  ros__parameters:
    use_sim_time: true
    solver_plugin: solver_plugins::CeresSolver
    mode: mapping
    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    scan_topic: /scan
```

- 프레임 이름 셋은 브리지 · URDF 가 내는 TF 이름과 같아야 함
- `scan_topic` = 앞 글의 `/scan`
- `mode: mapping` = 지도를 새로 만듦 (만든 지도 위에서 위치만 찾는 `localization` 도 있음)

### 지도 해상도 · 갱신 주기 · 루프 클로징 - slam.yaml 발췌

```yaml
# slam.yaml (이어서)
    resolution: 0.05
    max_laser_range: 20.0
    minimum_time_interval: 0.1
    minimum_travel_distance: 0.05
    minimum_travel_heading: 0.05
    transform_publish_period: 0.02
    map_update_interval: 1.0
    use_scan_matching: true
    do_loop_closing: true
```

- `resolution: 0.05` → 지도 한 칸 = 5 cm
- `minimum_travel_distance` · `heading`: 이만큼 움직여야 새 스캔을 그래프에 추가
- `do_loop_closing`: 왔던 곳을 다시 알아보고 쌓인 오차를 한꺼번에 바로잡음

### 해 볼 것

- `./scripts/mobile_openarm slam` (actors 켠 채로) 로 지도 만들기 → 사람 · 지게차가 지도에 남는 모습 확인
- `slam.yaml` 의 `resolution` 을 0.1 로 바꿔 다시 만들기 → pgm 크기 · 선반 모양 비교
- 저장한 지도로 출발: `./scripts/mobile_openarm start map:=$PWD/artifacts/maps/my_warehouse.yaml` (⑥ 미리보기)
