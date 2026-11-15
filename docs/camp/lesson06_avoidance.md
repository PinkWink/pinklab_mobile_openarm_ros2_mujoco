## 1. 움직이는 장애물과 Nav2

### 시나리오: 걷는 근로자와 마주치기

![crossing · headon 시나리오](lesson06_scenario.png){width=1000}

### 회피의 동작 흐름

![보고 → 칠하고 → 다시 계획하고 → 속도를 고른다](lesson06_flow.png){width=1000}

### marking 과 clearing

![obstacle_layer 의 marking · clearing](lesson06_mark_clear.png){width=1000}

### RViz2 에서 인지 결과 보기

![RViz2 표시와 뜻](lesson06_rviz_displays.png){width=1000}

## 2. 실행: 가로지르는 근로자 피하기

### 실행: 터미널 1 (nav)

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
./scripts/mobile_openarm nav moveit:=false      # 새로 띄운 직후 (로봇이 원점, 동쪽을 볼 때)
```

### 실행 결과: 시작 화면

![RViz2: Global Costmap 을 끄고 확대한 화면 (Local Costmap · Footprint · Lidar)](lesson06_run_result.png){width=1000}

### 터미널 2: 시나리오 실행

```bash
source /opt/ros/jazzy/setup.bash
source scripts/env.sh
python docs/camp/avoid_scenario.py              # 근로자가 x = 3.4 에서 통로를 가로지르고, 로봇은 (6.2, 0) 으로
```

### 실행 결과: 시나리오

![avoid_scenario.py 출력](lesson06_cli_crossing.png){width=1000}

### 움직이는 그림: 가로지르는 근로자 피하기

![crossing (움직이는 그림)](lesson06_crossing.gif){width=970}

### RViz2 로 본 회피 과정

![① 접근 → ② 감지 · 우회 → ③ 북쪽으로 · 제자리 회전 → ④ 재개](lesson06_rviz_sequence.png){width=1000}

### 같은 순간의 MuJoCo 창

![MuJoCo 창의 네 장면](lesson06_mujoco_sequence.png){width=1000}

### Global Costmap 을 켠 화면

![근로자 · 콘 · 선반 다리가 모두 막힘으로 칠해진 global costmap](lesson06_rviz_wide.png){width=1000}

### 실측: local costmap 과 경로

![네 순간의 local costmap · footprint · /plan · /local_plan](lesson06_local_snapshots.png){width=1000}

### 실측: 타임라인

![거리 · 속도 · 경로가 휘는 정도](lesson06_timeline.png){width=1000}

### 실측: 위에서 본 궤적

![/plan 은 길이 막힐 때만 새로 그려진다](lesson06_paths.png){width=1000}

## 3. 한계: 마주 오는 근로자

### 터미널 2: headon 시나리오

```bash
python docs/camp/avoid_scenario.py --mode headon     # 새로 띄운 직후에 실행
```

### 실행 결과: headon

![headon 출력: 최소 거리 0.15 m](lesson06_cli_headon.png){width=1000}

### 움직이는 그림: 마주 오는 근로자

![headon (움직이는 그림)](lesson06_headon.gif){width=970}

### headon 의 궤적과 거리

![마주 오는 근로자를 제때 피하지 못했다](lesson06_headon.png){width=1000}

### 같은 순간의 MuJoCo 창 (headon)

![다가온다 → 겹친다 → 지나간 뒤](lesson06_headon_mujoco.png){width=1000}

### 왜 늦게 피하나

![속도 예측이 없는 costmap 의 한계와 보완](lesson06_why_late.png){width=1000}

## 4. 코드와 설정

### 회피에 관여하는 파라미터

![nav2.yaml 파라미터](lesson06_params.png){width=1000}

### 로봇을 따라다니는 5 m 창 - nav2.yaml local_costmap 발췌

```yaml
# mobile_openarm_navigation/config/nav2.yaml  (발췌)
local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 10.0
      publish_frequency: 5.0
      global_frame: odom
      rolling_window: true
      width: 5
      height: 5
      resolution: 0.05
      plugins: [obstacle_layer, inflation_layer]
```

- 초당 10 번 갱신 · 5 번 발행 → 움직이는 사람이 0.1 초 안에 반영됨
- `global_frame: odom` + `rolling_window` → 지도가 아니라 지금 보이는 것만 담음
- 레이어 둘: 라이다로 칠하는 `obstacle_layer` · 둘레를 부풀리는 `inflation_layer`

### 라이다로 장애물 칠하고 지우기 - nav2.yaml local_costmap 발췌

```yaml
# nav2.yaml local_costmap (이어서)
      obstacle_layer:
        plugin: nav2_costmap_2d::ObstacleLayer
        observation_sources: scan
        scan:
          topic: /scan
          data_type: LaserScan
          clearing: true              # 레이가 지나간 칸을 비운다
          marking: true               # 레이가 멈춘 칸을 막힘으로
          raytrace_max_range: 20.0
          obstacle_max_range: 19.5
```

- `marking`: 광선이 멈춘 칸을 막힘으로 · `clearing`: 광선이 지나간 칸을 비움
- clearing 이 있어야 사람이 지나간 자리가 다시 빈 칸이 됨

### 장애물 부풀리기와 footprint - nav2.yaml local_costmap 발췌

```yaml
# nav2.yaml local_costmap (이어서)
      inflation_layer:
        plugin: nav2_costmap_2d::InflationLayer
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
      footprint: '[[0.38,0.32],[0.38,-0.32],[-0.38,-0.32],[-0.38,0.32]]'
```

- 막힌 칸 둘레 55 cm 까지 비용 · 멀어질수록 낮아짐 (`cost_scaling_factor` 가 클수록 빨리)
- controller 는 `footprint` 사각형이 막힌 칸에 닿는 궤적을 버림

### 길이 막힐 때만 다시 계획 - navigation.launch.py 발췌

```python
# mobile_openarm_navigation/launch/navigation.launch.py  (발췌)
bt_xml = str(Path(get_package_share_directory("nav2_bt_navigator"))
             / "behavior_trees/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml")
for pkg, exe in [..., ("nav2_bt_navigator", "bt_navigator")]:
    actions.append(Node(
        package=pkg, executable=exe, name=exe,
        parameters=[params, {"default_nav_to_pose_bt_xml": bt_xml}] if exe == "bt_navigator" else [params],
    ))
```

- 기본 BT 는 1 초마다 전역 경로를 다시 계산 · 이 BT 는 경로가 막혔을 때만
- `bt_navigator` 에만 파라미터 하나를 더함 · 나머지 서버는 `nav2.yaml` 그대로

### Global · Local Costmap 표시 추가 - navigation.rviz 발췌

```yaml
# mobile_openarm_navigation/config/navigation.rviz  (발췌: 이번에 추가한 표시)
    - Class: rviz_default_plugins/Map
      Name: Global Costmap
      Topic: {Value: /global_costmap/costmap, Durability Policy: Transient Local}
      Color Scheme: costmap
      Alpha: 0.3
    - Class: rviz_default_plugins/Map
      Name: Local Costmap
      Topic: {Value: /local_costmap/costmap, Durability Policy: Transient Local}
      Color Scheme: costmap
      Alpha: 0.7
```

- costmap 도 지도와 같은 메시지 (OccupancyGrid) → RViz 의 Map 표시로 봄
- `Color Scheme: costmap` → 비용이 색으로 · `Alpha` 로 두 장을 겹쳐 봄

### Footprint · DWB 궤적 · Local Plan 표시 추가 - navigation.rviz 발췌

```yaml
# navigation.rviz (이어서)
    - Class: rviz_default_plugins/Polygon
      Name: Footprint
      Topic: {Value: /local_costmap/published_footprint}
    - Class: rviz_default_plugins/MarkerArray
      Name: DWB Trajectories
      Topic: {Value: /marker}
    - Class: rviz_default_plugins/Path
      Name: Local Plan
      Topic: {Value: /local_plan}
```

- Footprint = 로봇 외곽 · DWB Trajectories = controller 가 평가한 후보 궤적
- Local Plan = 그중 고른 궤적 (`/local_plan`)

### 근로자 움직이기 - avoid_scenario.py 발췌

```python
# docs/camp/avoid_scenario.py  (발췌)
route = {"crossing": [(3.4, 3.0), (3.4, -3.0)], "headon": [(5.5, 0.0), (-5.5, 0.0)]}[a.mode]
pose.position.x, pose.position.y = route[0]
n.call(operation="teleport", pose=pose)                                   # /warehouse/set_actor
n.call(operation="set_path", waypoints=[Point(x=x, y=y) for x, y in route], speed=a.speed)
goal = NavigateToPose.Goal()
goal.pose.header.frame_id = "map"
goal.pose.pose.position.x, goal.pose.pose.position.y = 6.2, 0.0
goal.pose.pose.orientation.w = 1.0                                        # yaw = 0 (동쪽)
handle = n.nav.send_goal_async(goal)                                      # /navigate_to_pose
```

- `/warehouse/set_actor` 서비스: 근로자를 출발점에 놓고 (`teleport`) 걸을 길을 줌 (`set_path`)
- 그와 동시에 로봇에 `/navigate_to_pose` 목표 → 통로에서 만나게 됨

### 해 볼 것

- `--speed 0.2` 로 근로자를 천천히 걷게 해 headon 다시 실행 → 최소 거리 비교
- `nav2.yaml` 의 `inflation_radius` 를 0.8 로 키워 headon 다시 실행 → 더 일찍 피하는지 확인
- RViz 에서 Local Costmap 만 켜고 근로자가 지나간 칸이 비워지는(clearing) 순간 관찰
- `navigation.launch.py` 의 `default_nav_to_pose_bt_xml` 을 빼고(기본 BT: 1 초마다 다시 계획) crossing 다시 실행 → /plan 횟수와 목표에서 좌우로 도는지 비교
