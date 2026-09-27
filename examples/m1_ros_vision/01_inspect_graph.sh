#!/usr/bin/env bash
# M1 예제 1: 실행 중인 로봇의 ROS 2 그래프(노드·토픽·서비스·액션·TF)를 읽는다.
#
# 실행 (시뮬레이터가 떠 있는 상태에서, 다른 터미널):
#   ./scripts/mobile_openarm exec bash examples/m1_ros_vision/01_inspect_graph.sh
#   또는 `source scripts/env.sh` 한 셸에서  bash examples/m1_ros_vision/01_inspect_graph.sh
#
# 핵심 관찰: 카메라가 4대 있는데 Image/CameraInfo 토픽은 하나도 없다. 영상은 시뮬레이터
# 프로세스 안에서 Python 핸들러가 직접 받고(03번 예제), 검출 결과만 ROS 토픽으로 나온다.
# 출력은 artifacts/m1/01_inspect_graph.txt 에도 저장된다.
set -o pipefail
WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$WS/artifacts/m1"; mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/01_inspect_graph.txt"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

section() { printf '\n=== %s ===\n' "$1"; }

{
section "환경"
echo "ROS_DISTRO=${ROS_DISTRO:-?}  ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}  RMW=${RMW_IMPLEMENTATION:-default}"
topics="$(ros2 topic list 2>/dev/null)"
n_topics="$(printf '%s\n' "$topics" | grep -c .)"
if (( n_topics < 10 )); then
  echo "토픽이 ${n_topics}개만 보인다. 시뮬레이터가 안 떠 있거나, ros2 데몬이 다른 RMW로 떠 있다."
  echo "  -> ./scripts/mobile_openarm start 로 시뮬레이터를 띄우고, 'ros2 daemon stop' 후 다시 실행"
  exit 1
fi

section "노드 ($(ros2 node list 2>/dev/null | grep -c .)개)"
ros2 node list 2>/dev/null | sort | while read -r n; do
  case "$n" in
    /mobile_openarm_mujoco) tag="시뮬레이터 브리지 (MuJoCo, 센서, 컨트롤러, 카메라 핸들러)";;
    /amcl|/map_server|/planner_server|/controller_server|/bt_navigator*|/behavior_server|/smoother_server|/*costmap*|/mobile_lifecycle_manager) tag="Nav2";;
    /move_group*|/moveit*|/robot_state_publisher) tag="MoveIt / 로봇 모델";;
    /pick_place_server|/warehouse_planning_scene) tag="강좌용 (warehouse_skills / warehouse_lecture)";;
    /transform_listener_impl_*) tag="tf2 리스너 (내부)";;
    *) tag="";;
  esac
  printf '  %-45s %s\n' "$n" "$tag"
done

section "토픽 (전체 ${n_topics}개 중 센서·로봇·강좌 토픽)"
ros2 topic list -t 2>/dev/null | grep -E "^/(scan|odom|joint_states|cmd_vel|cmd_vel_stamped|ground_truth|map|tf|tf_static|clock) \[|^/(vision|warehouse)/" | sort |
  sed 's/^/  /'

section "영상 토픽 확인"
img="$(ros2 topic list -t 2>/dev/null | grep -E "sensor_msgs/msg/(Image|CompressedImage|CameraInfo)" || true)"
if [[ -z "$img" ]]; then
  echo "  Image / CompressedImage / CameraInfo 토픽: 없음"
  echo "  카메라 프레임(TF)은 있다:"
  timeout 8 ros2 topic echo /tf_static --once 2>/dev/null | grep -oE "child_frame_id: [a-z_]*camera[a-z_]*" | sort -u | sed 's/^/    /'
  cat <<'TXT'
  이유: 이 강좌의 설계 원칙 1번(LECTURE_PLAN.md)이다. 영상은 시뮬레이터 프로세스 안의 Python
  콜백(camera_handler)으로만 받고, 검출·추적·속성 판정을 그 프로세스에서 끝낸 뒤 결과만 ROS로
  내보낸다. 영상을 토픽으로 복사·직렬화하는 비용을 없애 GPU 없는 수강생 PC에서도 실시간을
  지키기 위해서다(기본값: 카메라 2대, 320x240, 2 FPS). 03번 예제에서 첫 핸들러를 만든다.
  결과 토픽:
    /vision/detections_2d  vision_msgs/Detection2DArray        (2D 박스)
    /vision/detections     warehouse_interfaces/Detection3DArray (map 좌표)
    /vision/markers        warehouse_interfaces/ArucoMarkerArray (도킹용 ArUco)
    /vision/stats          warehouse_interfaces/VisionStats     (처리율, 실시간 비율)
TXT
else
  echo "  영상 토픽이 있다 (예상과 다름):"; printf '%s\n' "$img" | sed 's/^/    /'
fi

section "서비스 (강좌용)"
ros2 service list -t 2>/dev/null | grep -E "^/warehouse/|^/(apply_planning_scene|get_planning_scene|compute_ik|compute_cartesian_path) " | sort | sed 's/^/  /'

section "액션 ($(ros2 action list 2>/dev/null | grep -c .)개)"
ros2 action list -t 2>/dev/null | sort | sed 's/^/  /'

section "MuJoCo 브리지 노드의 인터페이스"
ros2 node info /mobile_openarm_mujoco 2>/dev/null | grep -vE "parameter|get_type_description|/rosout|/clock"

section "TF 트리 (2초 수집, [static] 은 tf_static, 아니면 Hz)"
( cd "$TMP" && ros2 run tf2_tools view_frames -t 2 -o frames >/dev/null 2>&1 )
python3 - "$TMP/frames.gv" <<'PY'
import re, sys
edges = re.findall(r'"([^"]+)" -> "([^"]+)"\[label="[^"]*?Average rate: ([0-9.]+)', open(sys.argv[1]).read())
children, parents = {}, {}
for p, c, rate in edges:
    children.setdefault(p, []).append((c, float(rate)))
    parents[c] = p
roots = sorted(set(parents.values()) - set(parents))
def show(node, prefix="", rate=None):
    tag = "" if rate is None else ("  [static]" if rate >= 9999 else f"  ({rate:.0f} Hz)")
    print(f"{prefix}{node}{tag}")
    kids = sorted(children.get(node, []))
    for i, (c, r) in enumerate(kids):
        last = i == len(kids) - 1
        show(c, prefix.replace("├─ ", "│  ").replace("└─ ", "   ") + ("└─ " if last else "├─ "), r)
for r in roots:
    show(r)
print(f"\n프레임 {len(parents) + len(roots)}개, 루트: {', '.join(roots)}")
PY
cat <<'TXT'
  map -> odom 은 AMCL(위치 추정), odom -> base_footprint 는 바퀴 오도메트리(시뮬레이터),
  base_link 아래 정적 프레임은 robot_state_publisher(URDF), 팔 관절은 /joint_states 에서 나온다.
  카메라의 *_optical_frame 이 05번 예제(픽셀 -> map 좌표)의 출발 프레임이다.
TXT

section "토픽 주기 (5초 측정)"
for t in /scan /odom /joint_states /vision/stats; do
  hz="$(timeout 6 ros2 topic hz "$t" -w 20 2>/dev/null | grep -m1 "average rate" | awk '{print $3}')"
  printf '  %-16s %s Hz\n' "$t" "${hz:-?}"
done
echo "  /scan·/odom 은 시뮬레이션 시간 기준. /vision/stats 의 realtime_ratio 가 1.0 이면 실시간."
} 2>&1 | tee "$OUT"
echo
echo "저장: $OUT"
