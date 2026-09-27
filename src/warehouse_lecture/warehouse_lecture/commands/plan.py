"""RobotPlan: a list of high-level steps the LMM produces and the Task Manager executes.

The LMM never touches joints or velocities. It only decides *what* happens in *which order*:
    navigate(pick_table) -> detect(parcel_red) -> pick(parcel_red @ pick_table)
    -> navigate(place_table) -> place(@ place_table)
``validate_world()`` checks the steps against the world (known places/objects, something must be
held before place, ...) and fills defaults; ``to_msg``/``from_msg`` convert to the
warehouse_interfaces/ExecutePlan goal.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field
from warehouse_interfaces.action import ExecutePlan
from warehouse_interfaces.msg import PlanStep as PlanStepMsg

from .schema import ARM_POSES, FIND_TARGETS, GRIPPER, PARCELS, PLACE_KO, STATIONS, TARGET_KO, Place


class StepAction(str, Enum):
    navigate = "navigate"      # Nav2 to a named place
    detect = "detect"          # confirm the target is visible to the cameras
    pick = "pick"              # dock at the table, grasp the object, lift to the carry pose
    place = "place"            # dock at the table, put the held object on a free slot
    arm_pose = "arm_pose"      # named MoveIt pose for both arms
    gripper = "gripper"        # open | close both grippers
    report = "report"          # describe what the cameras see (LLM)
    answer = "answer"          # say the reply (clarification, refusal, plain answer)


class PlanStep(BaseModel):
    action: StepAction
    target: str = Field("", description="pick/detect: parcel_red|parcel_blue|parcel_yellow|person 등. arm_pose: ready|hands_up|transport|home. gripper: open|close")
    location: Place = Field(Place.none, description="navigate: 목적지. pick: 물체가 있는 작업대. place: 놓을 작업대")
    note: str = Field("", description="이 단계를 한국어 한 구절로 (예: 픽업 작업대로 이동)")

    def describe(self):
        t = TARGET_KO.get(self.target, self.target)
        p = PLACE_KO.get(self.location.value, self.location.value)
        if self.action == StepAction.navigate:
            return f"{p}로 이동"
        if self.action == StepAction.detect:
            return f"{t} 확인"
        if self.action == StepAction.pick:
            return f"{p}에서 {t} 집기"
        if self.action == StepAction.place:
            return f"{p}에 놓기"
        if self.action == StepAction.report:
            return "주변 상황 보고"
        if self.action == StepAction.answer:
            return "답변"
        return f"{self.action.value} {self.target}".strip()

    def to_msg(self):
        return PlanStepMsg(action=self.action.value, target=self.target, location=self.location.value, arm="", note=self.note or self.describe())

    @classmethod
    def from_msg(cls, msg):
        return cls(action=StepAction(msg.action), target=msg.target, location=Place(msg.location or ""), note=msg.note)


class RobotPlan(BaseModel):
    """What the LMM returns: a summary, the ordered steps, and one sentence for the user."""

    summary: str = Field("", description="계획 전체를 한국어 한 문장으로")
    steps: List[PlanStep] = Field(default_factory=list, description="실행 순서대로. 되묻기·거부·단순 답변이면 비운다")
    reply: str = Field("", description="사용자에게 할 한 문장 (무엇을 할지, 또는 되묻기·거부·답)")

    # --- semantic validation ------------------------------------------------
    def validate_world(self):
        """Fill defaults, insert missing navigate steps, and return a list of problems (empty = executable)."""
        problems = []
        if not self.steps:
            if not self.reply:
                problems.append("단계도 답변도 없다")
            return problems
        fixed, held, here = [], None, None
        for step in self.steps:
            a = step.action
            if a == StepAction.navigate:
                if step.location == Place.none:
                    problems.append("이동 단계에 목적지가 없다")
                here = step.location
            elif a == StepAction.detect:
                if step.target not in FIND_TARGETS:
                    problems.append(f"확인할 대상이 정해지지 않았다: {step.target!r}")
            elif a == StepAction.pick:
                if step.target not in PARCELS:
                    problems.append(f"집을 상자가 정해지지 않았다: {step.target!r} (parcel_red/blue/yellow)")
                if step.location == Place.none:
                    step.location = here if (here and here.value in STATIONS) else Place.pick_table
                if step.location.value not in STATIONS:
                    problems.append(f"상자는 작업대(pick_table, place_table)에서만 집을 수 있다: {step.location.value}")
                if held is not None:
                    problems.append(f"이미 {TARGET_KO.get(held, held)}를 들고 있는데 또 집으려 한다")
                if here != step.location:
                    fixed.append(PlanStep(action=StepAction.navigate, location=step.location, note=f"{PLACE_KO.get(step.location.value, step.location.value)}로 이동 (자동 추가)"))
                    here = step.location
                held = step.target
            elif a == StepAction.place:
                if step.location == Place.none:
                    step.location = Place.place_table if here != Place.place_table else Place.pick_table
                if step.location.value not in STATIONS:
                    problems.append(f"상자는 작업대(pick_table, place_table)에만 놓을 수 있다: {step.location.value}")
                if held is None:
                    problems.append("든 것이 없는데 놓으려 한다 (pick 단계가 먼저 필요)")
                if not step.target and held:
                    step.target = held
                if here != step.location:
                    fixed.append(PlanStep(action=StepAction.navigate, location=step.location, note=f"{PLACE_KO.get(step.location.value, step.location.value)}로 이동 (자동 추가)"))
                    here = step.location
                held = None
            elif a == StepAction.arm_pose:
                if step.target not in ARM_POSES:
                    problems.append(f"모르는 팔 자세 {step.target!r} ({', '.join(ARM_POSES)})")
                if held is not None:
                    problems.append("상자를 든 채로 팔 자세를 바꾸면 떨어뜨린다")
            elif a == StepAction.gripper:
                if step.target not in GRIPPER:
                    problems.append(f"그리퍼는 open/close 만 된다: {step.target!r}")
                if held is not None and step.target == "open":
                    problems.append("상자를 든 채로 그리퍼를 열면 떨어뜨린다")
            fixed.append(step)
        if held is not None:
            problems.append(f"계획이 {TARGET_KO.get(held, held)}를 든 채로 끝난다 (place 단계가 없다)")
        self.steps = fixed
        return problems

    # --- ROS conversion -----------------------------------------------------
    def to_msg(self, utterance=""):
        goal = ExecutePlan.Goal()
        goal.summary, goal.utterance = self.summary, utterance
        goal.steps = [s.to_msg() for s in self.steps]
        return goal

    @classmethod
    def from_msg(cls, goal):
        return cls(summary=goal.summary, steps=[PlanStep.from_msg(s) for s in goal.steps], reply="")

    def describe(self):
        """Numbered Korean step list for confirmations and logs."""
        return "\n".join(f"{i + 1}. {s.note or s.describe()}" for i, s in enumerate(self.steps))

    def needs_confirmation(self):
        return any(s.action in (StepAction.pick, StepAction.place) for s in self.steps)
