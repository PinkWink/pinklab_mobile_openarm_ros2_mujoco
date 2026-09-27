"""ExecuteCommand action server: RobotCommand -> Nav2 / PickPlace / MoveIt / gripper (M4 example 03, promoted).

    ros2 run warehouse_lecture command_executor           (needs the simulator with moveit; camera detector for find/report)
    ros2 action send_goal /execute_command warehouse_interfaces/action/ExecuteCommand "{command: {intent: go_to, destination: rack_c}}"

State machine per intent (feedback phase/detail):
  move_object  arms->transport, PickPlace(object colour, source, destination)
  go_to        arms->transport (interlock: the base ignores /cmd_vel unless both arms are in a driving pose), Nav2 to base_goal
  find         check /vision/detections; else patrol locations.patrol waypoints until a matching detection appears
  report       world state from detections + pose -> LLM (or template) -> spoken
  answer       LLM answer from the same state (M5 adds encounter memory)
  arm_pose     MoveGroup both arms to an SRDF named pose (refused while driving)
  gripper      both grippers open/close
  stop         cancel the running goal, zero /cmd_vel
One command at a time; a new goal is rejected while one runs (except stop).
"""

import json
import math
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import rclpy
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from action_msgs.msg import GoalStatus
from ament_index_python.packages import get_package_share_directory
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Twist
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from nav2_msgs.action import NavigateToPose
from tf2_ros import Buffer, TransformException, TransformListener
from warehouse_interfaces.action import ExecuteCommand, PickPlace
from warehouse_interfaces.msg import Detection3DArray

from ..memory.locations import Locations
from .schema import PLACE_KO, TARGET_KO, Intent, RobotCommand  # noqa: F401 - re-exported for examples

class CommandError(Exception):
    pass


class CommandExecutor(Node):
    def __init__(self, use_llm=True, node_name="command_executor"):
        super().__init__(node_name, parameter_overrides=[Parameter("use_sim_time", value=True)])
        group = self.group = ReentrantCallbackGroup()
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose", callback_group=group)
        self.pick = ActionClient(self, PickPlace, "/pick_place", callback_group=group)
        self.move = ActionClient(self, MoveGroup, "/move_action", callback_group=group)
        self.grippers = {s: ActionClient(self, GripperCommand, f"/{s}_gripper_controller/gripper_cmd", callback_group=group) for s in ("left", "right")}
        self.cmd_vel = self.create_publisher(Twist, "/cmd_vel", 10)
        self.detections = None
        self.create_subscription(Detection3DArray, "/vision/detections", lambda m: setattr(self, "detections", m), 10, callback_group=group)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=False)
        self.locations = Locations()
        self.srdf = ET.parse(Path(get_package_share_directory("mobile_openarm_moveit_config")) / "config/mobile_openarm.srdf")
        self.arm_pose_name = None            # last commanded pose (None = unknown at start; simulator starts in transport)
        self.busy = threading.Lock()
        self.active = None                   # currently running goal handle of a sub-action (for stop)
        self.cancel_flag = False
        self.llm = None
        if use_llm:
            try:
                from ..llm.client import LLM
                self.llm = LLM()
            except Exception as error:  # noqa: BLE001 - no key: report/answer fall back to templates
                self.get_logger().warning(f"LLM unavailable ({error}); report/answer use templates")
        self.server = ActionServer(self, ExecuteCommand, "/execute_command", execute_callback=self.execute, goal_callback=self.on_goal,
                                   cancel_callback=lambda _: CancelResponse.ACCEPT, callback_group=group)
        self.get_logger().info("ExecuteCommand server ready (/execute_command)")

    # --- goal handling --------------------------------------------------------
    def on_goal(self, request):
        if request.command.intent == Intent.stop.value:
            return GoalResponse.ACCEPT
        return GoalResponse.ACCEPT if not self.busy.locked() else GoalResponse.REJECT

    def execute(self, handle):
        cmd = RobotCommand.from_msg(handle.request.command)
        result = ExecuteCommand.Result()
        if cmd.intent == Intent.stop:
            self.stop_everything()
            result.success, result.message, result.spoken = True, "stopped", "정지했습니다."
            handle.succeed()
            return result
        if not self.busy.acquire(blocking=False):
            result.success, result.message, result.spoken = False, "busy", "지금 다른 명령을 수행 중입니다."
            handle.abort()
            return result
        self.cancel_flag = False

        def feedback(phase, detail):
            handle.publish_feedback(ExecuteCommand.Feedback(phase=phase, detail=detail))
            self.get_logger().info(f"[{cmd.intent.value}/{phase}] {detail}")
            if handle.is_cancel_requested or self.cancel_flag:
                raise CommandError("취소됨")

        try:
            problems = cmd.validate_world()
            if problems:
                raise CommandError("; ".join(problems))
            spoken = getattr(self, "do_" + cmd.intent.value)(cmd, feedback)
            result.success, result.message, result.spoken = True, "ok", spoken
            handle.succeed()
        except CommandError as error:
            result.success, result.message, result.spoken = False, str(error), f"실패했습니다: {error}"
            self.get_logger().error(f"{cmd.intent.value} failed: {error}")
            if handle.is_cancel_requested:
                handle.canceled()
            else:
                handle.abort()
        finally:
            self.active = None
            self.busy.release()
        return result

    def stop_everything(self):
        self.cancel_flag = True
        if self.active is not None:
            try:
                self.active.cancel_goal_async()
            except Exception:  # noqa: BLE001
                pass
        for _ in range(3):
            self.cmd_vel.publish(Twist())
            time.sleep(0.05)

    # --- generic action call ----------------------------------------------------
    def call(self, client, goal, timeout, name, on_feedback=None):
        if not client.wait_for_server(timeout_sec=10.0):
            raise CommandError(f"{name} 서버가 없다")
        future = client.send_goal_async(goal, feedback_callback=on_feedback)
        self.wait(future, 10.0)
        gh = future.result()
        if gh is None or not gh.accepted:
            raise CommandError(f"{name} 거부됨")
        self.active = gh
        rf = gh.get_result_async()
        start = time.monotonic()
        while not rf.done():
            if self.cancel_flag:
                gh.cancel_goal_async()
                self.wait(rf, 15.0)
                raise CommandError("취소됨")
            if time.monotonic() - start > timeout:
                gh.cancel_goal_async()
                raise CommandError(f"{name} 시간 초과")
            time.sleep(0.05)
        self.active = None
        return rf.result()

    @staticmethod
    def wait(future, timeout):
        end = time.monotonic() + timeout
        while not future.done() and time.monotonic() < end:
            time.sleep(0.02)

    # --- primitives ---------------------------------------------------------------
    def arms_to(self, pose, feedback, side="both"):
        if pose == self.arm_pose_name and side == "both":
            return
        feedback("arm", f"팔을 {pose} 자세로")
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = "both_arms" if side == "both" else side + "_arm"
        req.allowed_planning_time, req.num_planning_attempts = 8.0, 5
        req.max_velocity_scaling_factor = req.max_acceleration_scaling_factor = 0.3
        req.start_state.is_diff = True
        c = Constraints(name=pose)
        for s in (["left", "right"] if side == "both" else [side]):
            state = self.srdf.find(f"group_state[@group='{s}_arm'][@name='{pose}']")
            if state is None:
                raise CommandError(f"SRDF 에 {pose} 자세가 없다")
            for j in state.findall("joint"):
                c.joint_constraints.append(JointConstraint(joint_name=j.get("name"), position=float(j.get("value")), tolerance_above=0.01, tolerance_below=0.01, weight=1.0))
        req.goal_constraints = [c]
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        r = self.call(self.move, goal, 90.0, "MoveIt")
        if r.status != GoalStatus.STATUS_SUCCEEDED or r.result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise CommandError(f"팔 이동 실패 (MoveIt error {r.result.error_code.val})")
        self.arm_pose_name = pose if side == "both" else None

    def nav_goal(self, x, y, yaw):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        return goal

    def navigate(self, key, feedback):
        """Arms to a driving pose, then Nav2 to a named place (see drive_to)."""
        self.arms_to("transport", feedback)     # interlock: base only drives with both arms in a driving pose
        self.drive_to(key, feedback)

    def drive_to(self, key, feedback):
        """Nav2 to a named place without touching the arms. Recovery: a person often stands on the goal
        (patrol paths cross the aisles), so wait and retry once, then fall back to a point 0.6 m short of the goal."""
        x, y, yaw = self.locations.goal(key)
        name = PLACE_KO.get(key, key)
        attempts = [(x, y, yaw, f"{name} ({x:.1f}, {y:.1f}) 로 이동"), (x, y, yaw, "목표가 막혀 5초 후 재시도")]
        here = self.robot_xy()
        if here:
            d = math.hypot(x - here[0], y - here[1])
            if d > 0.8:
                fx, fy = x - 0.6 * (x - here[0]) / d, y - 0.6 * (y - here[1]) / d
                attempts.append((fx, fy, yaw, f"목표 0.6 m 앞 ({fx:.1f}, {fy:.1f}) 로 대체"))
        last = [None]

        def on_fb(m):
            d = m.feedback.distance_remaining
            if last[0] is None or abs(d - last[0]) > 0.5:
                last[0] = d
                feedback("navigate", f"남은 거리 {d:.1f} m")

        status = None
        for i, (gx, gy, gyaw, text) in enumerate(attempts):
            if i == 1:
                time.sleep(5.0)
            feedback("navigate", text)
            r = self.call(self.nav, self.nav_goal(gx, gy, gyaw), 180.0, "Nav2", on_fb)
            status = r.status
            if status == GoalStatus.STATUS_SUCCEEDED:
                return
        raise CommandError(f"이동 실패 (Nav2 status {status})")

    def robot_xy(self):
        try:
            t = self.tf_buffer.lookup_transform("map", "base_footprint", rclpy.time.Time())
            return t.transform.translation.x, t.transform.translation.y
        except TransformException:
            return None

    def matching_detections(self, cmd):
        if self.detections is None:
            return []
        want = cmd.attribute_dict()
        out = []
        for d in self.detections.detections:
            if d.label != cmd.target or not d.has_position:
                continue
            attrs = {kv.key: kv.value for kv in d.attributes}
            if all(str(attrs.get(k, "")).lower() == str(v).lower() for k, v in want.items()):
                out.append(d)
        return out

    def world_state(self):
        det = self.detections
        xy = self.robot_xy()
        place = self.locations.nearest(*xy)[0] if xy else None
        state = {"robot_place": PLACE_KO.get(place, place or "알 수 없음"), "people": [], "parcels": {}, "objects": {}}
        if det is None:
            return state
        seen, objects = [], Counter()
        for d in det.detections:
            if d.label in ("helmet", "safety_vest"):
                continue
            if d.has_position:
                x, y = d.position.point.x, d.position.point.y
                if any(l == d.label and math.hypot(x - sx, y - sy) < 0.5 for l, sx, sy in seen):
                    continue
                seen.append((d.label, x, y))
                near = PLACE_KO.get(self.locations.nearest(x, y)[0], "알 수 없음")
            else:
                near = None
            if d.label == "person":
                a = {kv.key: kv.value for kv in d.attributes}
                state["people"].append({"helmet": a.get("helmet") == "true", "vest": a.get("vest", "none"), "near": near})
            elif d.label.startswith("parcel_"):
                state["parcels"][d.label[7:]] = near
            else:
                objects[TARGET_KO.get(d.label, d.label)] += 1
        state["objects"] = dict(objects)
        return state

    def narrate(self, state, question=None):
        if self.llm is None:
            people = state["people"]
            no_helmet = sum(not p["helmet"] for p in people)
            text = f"{state['robot_place']}에 있습니다. 사람 {len(people)}명" + (f", 그중 안전모 미착용 {no_helmet}명" if no_helmet else "") + \
                   (f", 상자 {', '.join(state['parcels'])}" if state["parcels"] else "") + "."
            return text if not question else "기억 기능은 다음 모듈에서 추가됩니다. " + text
        system = ("너는 창고 순찰 로봇 '핑키'다. JSON 은 지금 네 카메라가 보는 것과 위치다. JSON 에 있는 것만 근거로 한국어 두세 문장, 존댓말로 답한다. "
                  "안전모 미착용자가 있으면 먼저 말한다. 과거를 묻는데 JSON 에 없으면 지금 보이는 것만 말하고 기억에 없다고 한다.")
        user = json.dumps(state, ensure_ascii=False) + (f"\n질문: {question}" if question else "\n상황을 보고하라.")
        return self.llm.chat([{"role": "system", "content": system}, {"role": "user", "content": user}], temperature=0.3, max_tokens=200, purpose="executor_" + ("answer" if question else "report"))

    # --- intents ------------------------------------------------------------------
    def do_move_object(self, cmd, feedback):
        self.arms_to("transport", feedback)
        colour = cmd.target[7:]
        feedback("pick_place", f"{TARGET_KO[cmd.target]}: {cmd.source.value} -> {cmd.destination.value}")
        goal = PickPlace.Goal(object=colour, from_station=cmd.source.value, to_station=cmd.destination.value, arm="", phase="all")
        last = [""]

        def on_fb(m):
            t = f"{m.feedback.phase}: {m.feedback.detail}"
            if t != last[0]:
                last[0] = t
                feedback("pick_place", t)

        r = self.call(self.pick, goal, 900.0, "PickPlace", on_fb)
        self.arm_pose_name = "transport"
        if r.status != GoalStatus.STATUS_SUCCEEDED or not r.result.success:
            raise CommandError(f"운반 실패: {r.result.message}")
        return f"{TARGET_KO[cmd.target]}를 {PLACE_KO[cmd.destination.value]}에 옮겼습니다."

    def do_go_to(self, cmd, feedback):
        self.navigate(cmd.destination.value, feedback)
        return f"{PLACE_KO[cmd.destination.value]}에 도착했습니다."

    def do_find(self, cmd, feedback):
        what = TARGET_KO.get(cmd.target, cmd.target) + ("".join(f" ({k}={v})" for k, v in cmd.attribute_dict().items()))
        hits = self.matching_detections(cmd)
        visited = 0
        for wp in self.locations.patrol:
            if hits:
                break
            visited += 1
            feedback("search", f"{what} 을(를) 찾는 중: 순찰 {visited}/{len(self.locations.patrol)}")
            self.arms_to("transport", feedback)
            goal = self.nav_goal(wp[0], wp[1], wp[2])
            found = []

            def on_fb(_m):
                if not found:
                    found.extend(self.matching_detections(cmd))
                    if found:
                        self.cancel_flag = True      # stop driving as soon as the target is seen

            try:
                self.call(self.nav, goal, 180.0, "Nav2", on_fb)
            except CommandError:
                if not found:
                    raise
                self.cancel_flag = False
                self.cmd_vel.publish(Twist())
            hits = found or self.matching_detections(cmd)
        if not hits:
            raise CommandError(f"{what} 을(를) 순찰 경로에서 찾지 못했다")
        d = max(hits, key=lambda h: h.score)
        place = PLACE_KO.get(self.locations.nearest(d.position.point.x, d.position.point.y)[0], "알 수 없는 곳")
        return f"{what} 을(를) {place} 근처 ({d.position.point.x:.1f}, {d.position.point.y:.1f})에서 찾았습니다."

    def do_report(self, cmd, feedback):
        feedback("report", "상황 정리")
        return self.narrate(self.world_state())

    def do_answer(self, cmd, feedback):
        if cmd.reply and not any(kv.key == "question" for kv in []):
            pass
        feedback("answer", cmd.reply or "질문에 답변")
        # A parse-time reply (clarification/refusal) is spoken as is; otherwise answer from the world state.
        return cmd.reply if cmd.reply else self.narrate(self.world_state(), question="지금 보이는 것을 말해줘")

    def do_arm_pose(self, cmd, feedback):
        self.arms_to(cmd.target, feedback)
        return f"팔을 {cmd.target} 자세로 바꿨습니다."

    def do_gripper(self, cmd, feedback):
        pos = 0.044 if cmd.target == "open" else 0.012
        feedback("gripper", f"양쪽 그리퍼 {cmd.target}")
        for side, client in self.grippers.items():
            goal = GripperCommand.Goal()
            goal.command.position, goal.command.max_effort = float(pos), 25.0
            r = self.call(client, goal, 15.0, f"{side} gripper")
            if r.status != GoalStatus.STATUS_SUCCEEDED:
                raise CommandError(f"{side} 그리퍼 실패")
        return f"그리퍼를 {'열었' if cmd.target == 'open' else '닫았'}습니다."


def main():
    rclpy.init()
    node = CommandExecutor()
    executor = MultiThreadedExecutor(num_threads=6)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
