"""Task Manager: ExecutePlan action server that runs a RobotPlan step by step.

    ros2 run warehouse_lecture task_manager      (serves /execute_plan AND /execute_command; do not run command_executor at the same time)

Role split (the point of the lecture module):
  LMM            decides the steps  (plan_parser.py -> RobotPlan)
  Task Manager   orchestrates       (this node: order, feedback, stop, failure -> spoken result)
  Nav2 / MoveIt  execute            (via the PickPlace skill server and the executor primitives)
Steps:
  navigate(location)   Nav2 to the named place (arms to transport unless something is held: the carry pose is a driving pose)
  detect(target)       wait until the cameras report the label (/vision/detections)
  pick(target @ loc)   PickPlace phase=pick: dock, grasp, carry pose, undock  -> the object is held
  place(@ loc)         PickPlace phase=place: dock, put the held object on a free slot, transport pose, undock
  arm_pose / gripper / report / answer   as in the single-command executor
"""

import time

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.executors import MultiThreadedExecutor
from action_msgs.msg import GoalStatus
from warehouse_interfaces.action import ExecutePlan, PickPlace

from .executor import CommandError, CommandExecutor
from .plan import RobotPlan, StepAction
from .schema import PLACE_KO, TARGET_KO, Intent, RobotCommand


def subject_particle(word):
    """Korean subject particle: 이 after a final consonant, 가 after a vowel (상자가, 사람이)."""
    code = ord(word[-1]) - 0xAC00 if word else -1
    return "이" if 0 <= code < 11172 and code % 28 else "가"


class TaskManager(CommandExecutor):
    DETECT_TIMEOUT_S = 10.0

    def __init__(self, use_llm=True):
        super().__init__(use_llm=use_llm, node_name="task_manager")
        self.held = None                     # parcel label held after a pick step
        self.plan_server = ActionServer(self, ExecutePlan, "/execute_plan", execute_callback=self.execute_plan,
                                        goal_callback=lambda _: GoalResponse.ACCEPT if not self.busy.locked() else GoalResponse.REJECT,
                                        cancel_callback=lambda _: CancelResponse.ACCEPT, callback_group=self.group)
        self.get_logger().info("ExecutePlan server ready (/execute_plan)")

    # --- plan execution -----------------------------------------------------------
    def execute_plan(self, handle):
        plan = RobotPlan.from_msg(handle.request)
        result = ExecutePlan.Result()
        result.steps_done, result.failed_step = 0, -1
        if not self.busy.acquire(blocking=False):
            result.success, result.message, result.spoken = False, "busy", "지금 다른 명령을 수행 중입니다."
            handle.abort()
            return result
        self.cancel_flag = False
        total = len(plan.steps)
        said = []
        try:
            problems = plan.validate_world()
            if problems:
                raise CommandError("; ".join(problems))
            for i, step in enumerate(plan.steps):
                def feedback(phase, detail, _i=i, _step=step):
                    handle.publish_feedback(ExecutePlan.Feedback(step=int(_i), total=int(total), action=_step.action.value, phase=phase, detail=detail))
                    self.get_logger().info(f"[{_i + 1}/{total} {_step.action.value}/{phase}] {detail}")
                    if handle.is_cancel_requested or self.cancel_flag:
                        raise CommandError("취소됨")

                feedback("start", step.note or step.describe())
                try:
                    said.append(self.run_step(step, feedback))
                except CommandError as error:
                    result.failed_step = int(i)
                    raise CommandError(f"{i + 1}단계({step.note or step.describe()}) 실패: {error}")
                result.steps_done = int(i + 1)
            result.success, result.message = True, "ok"
            result.spoken = self.summarize(plan, said)
            handle.succeed()
        except CommandError as error:
            result.success, result.message = False, str(error)
            done = f"{result.steps_done}단계까지 마쳤지만 " if result.steps_done else ""
            result.spoken = f"{done}실패했습니다: {error}"
            if self.held:
                result.spoken += f" {TARGET_KO.get(self.held, self.held)}를 아직 들고 있습니다."
            self.get_logger().error(f"plan failed: {error}")
            if handle.is_cancel_requested:
                handle.canceled()
            else:
                handle.abort()
        finally:
            self.active = None
            self.busy.release()
        return result

    def summarize(self, plan, said):
        """One or two sentences for the user: what was placed / reported first; detections and
        arm moves only when nothing was placed; plain arrivals last."""
        for actions in ((StepAction.place, StepAction.report, StepAction.answer),
                        (StepAction.detect, StepAction.arm_pose, StepAction.gripper),
                        (StepAction.navigate,)):
            parts = [s for step, s in zip(plan.steps, said) if step.action in actions and s]
            if parts:
                return " ".join(parts[-2:])
        return plan.summary or "완료했습니다."

    # --- steps ------------------------------------------------------------------------
    def run_step(self, step, feedback):
        a = step.action
        if a == StepAction.navigate:
            return self.step_navigate(step, feedback)
        if a == StepAction.detect:
            return self.step_detect(step, feedback)
        if a == StepAction.pick:
            return self.step_pick(step, feedback)
        if a == StepAction.place:
            return self.step_place(step, feedback)
        # Single-command intents share the executor's implementation.
        cmd = RobotCommand(intent=Intent(a.value), target=step.target, destination=step.location, reply=step.note if a == StepAction.answer else "")
        problems = cmd.validate_world()
        if problems:
            raise CommandError("; ".join(problems))
        return getattr(self, "do_" + a.value)(cmd, feedback)

    def step_navigate(self, step, feedback):
        key = step.location.value
        if self.held is None:
            self.navigate(key, feedback)                 # arms -> transport, then Nav2
        else:
            self.drive_to(key, feedback)                 # holding: the carry pose is a driving pose, do not touch the arms
        return f"{PLACE_KO.get(key, key)}에 도착했습니다."

    def step_detect(self, step, feedback):
        cmd = RobotCommand(intent=Intent.find, target=step.target)
        what = TARGET_KO.get(step.target, step.target)
        end = time.monotonic() + self.DETECT_TIMEOUT_S
        hits = self.matching_detections(cmd)
        while not hits and time.monotonic() < end:
            feedback("detect", f"{what} 을(를) 카메라로 찾는 중")
            time.sleep(1.0)
            hits = self.matching_detections(cmd)
        if not hits:
            raise CommandError(f"{what}{subject_particle(what)} 카메라에 보이지 않는다")
        d = max(hits, key=lambda h: h.score)
        x, y = d.position.point.x, d.position.point.y
        place = PLACE_KO.get(self.locations.nearest(x, y)[0], "알 수 없는 곳")
        feedback("detect", f"{what} at ({x:.2f}, {y:.2f}) score {d.score:.2f} [{d.camera}]")
        return f"{what}{subject_particle(what)} {place}에 보입니다."

    def step_pick(self, step, feedback):
        if self.held is not None:
            raise CommandError(f"이미 {TARGET_KO.get(self.held, self.held)}를 들고 있다")
        self.arms_to("transport", feedback)
        colour = step.target[7:]
        goal = PickPlace.Goal(object=colour, from_station=step.location.value, to_station="", arm="", phase="pick")
        self.arm_pose_name = None                        # the skill moves the arms; assume nothing afterwards
        r = self.call(self.pick, goal, 600.0, "PickPlace", self._skill_feedback(feedback))
        if r.status != GoalStatus.STATUS_SUCCEEDED or not r.result.success:
            raise CommandError(f"집기 실패: {r.result.message}")
        self.held = step.target
        return f"{TARGET_KO[step.target]}를 집었습니다."

    def step_place(self, step, feedback):
        if self.held is None:
            raise CommandError("든 것이 없다")
        goal = PickPlace.Goal(object=self.held[7:], from_station="", to_station=step.location.value, arm="", phase="place")
        self.arm_pose_name = None
        r = self.call(self.pick, goal, 600.0, "PickPlace", self._skill_feedback(feedback))
        if r.status != GoalStatus.STATUS_SUCCEEDED or not r.result.success:
            raise CommandError(f"놓기 실패: {r.result.message}")
        held, self.held = self.held, None
        return f"{TARGET_KO[held]}를 {PLACE_KO[step.location.value]}에 놓았습니다."

    @staticmethod
    def _skill_feedback(feedback):
        last = [""]

        def on_fb(m):
            t = f"{m.feedback.phase}: {m.feedback.detail}"
            if t != last[0]:
                last[0] = t
                feedback("pick_place", t)
        return on_fb


def main():
    rclpy.init()
    node = TaskManager()
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
