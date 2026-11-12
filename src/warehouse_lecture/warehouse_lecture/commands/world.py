"""WorldState: what the robot believes about the parcels (Final Mission ⑭).

The LLM planner cannot see the warehouse. Without this it always plans "pick at pick_table",
even for a parcel it already moved. WorldState keeps one line per parcel, is written into the
planner's system prompt, checks a plan before it runs, and is updated from the Task Manager
result (only the steps that actually finished change the belief).

    world = WorldState()                      # all three parcels on the pick table
    world.prompt()                            # text for the LLM system prompt
    world.check(plan)                         # [] or ["빨간 상자는 적재 작업대에 있다 (계획: 픽업 작업대에서 집기)"]
    world.apply(plan, result.steps_done, result.success)
"""

from .plan import StepAction
from .schema import PARCELS, PLACE_KO, TARGET_KO

HELD = "held"          # in the gripper
UNKNOWN = "unknown"    # a pick/place failed half-way: look before trusting the belief


class WorldState:
    def __init__(self, parcels=None):
        self.parcels = dict(parcels or {p: "pick_table" for p in PARCELS})
        self.history = []     # (before, after) per executed plan

    # --- the planner's view --------------------------------------------------
    def where(self, parcel):
        return self.parcels.get(parcel, UNKNOWN)

    def describe(self):
        """One Korean line, e.g. '빨간 상자: 적재 작업대 · 파란 상자: 픽업 작업대 · 노란 상자: 픽업 작업대'"""
        return " · ".join(f"{TARGET_KO[p]}: {self._ko(loc)}" for p, loc in self.parcels.items())

    def prompt(self):
        lines = [f"- {p}({TARGET_KO[p]}): {loc}({self._ko(loc)})" for p, loc in self.parcels.items()]
        return ("현재 상자 위치 (로봇이 마지막으로 확인한 것):\n" + "\n".join(lines) + "\n"
                "상자 위치 규칙 (위의 기본값 pick_table / place_table 보다 우선):\n"
                "- detect · pick 은 그 상자가 지금 있는 작업대(이 표)에서 한다. navigate 도 그 작업대로 간다.\n"
                "- 문장이 도착 작업대를 말하면 그 작업대를 그대로 쓴다. 상자가 이미 거기 있어도 바꾸지 않는다 (그 확인은 프로그램이 한다).\n"
                "- 문장에 도착지가 없거나 '다시', '원래 자리', '돌려놔' 라고만 하면 도착지는 그 상자가 지금 없는 다른 작업대다.\n"
                "- 위치가 unknown 인 상자는 pick_table 에서 찾는다.\n")

    # --- before running -----------------------------------------------------
    def check(self, plan):
        """Problems between the plan and the belief (empty = consistent). The facts are checked here,
        in code, not by the LLM: wrong source table, and a parcel that is already at the destination."""
        problems, belief = [], dict(self.parcels)
        held = next((p for p, loc in belief.items() if loc == HELD), None)
        origin = {}
        for step in plan.steps:
            if step.action == StepAction.pick:
                loc = belief.get(step.target, UNKNOWN)
                origin[step.target] = loc
                if loc not in (step.location.value, UNKNOWN, HELD):
                    origin[step.target] = "wrong_source"
                    problems.append(f"{TARGET_KO.get(step.target, step.target)}는 {self._ko(loc)}에 있다 "
                                    f"(계획: {self._ko(step.location.value)}에서 집기)")
                belief[step.target], held = HELD, step.target
            elif step.action == StepAction.place and held:
                if belief.get(held) == HELD and self.parcels.get(held) == step.location.value:
                    if origin.get(held) == "wrong_source":
                        problems.pop()      # say the simpler thing instead
                    problems.append(f"{TARGET_KO.get(held, held)}는 이미 {self._ko(step.location.value)}에 있다")
                belief[held], held = step.location.value, None
        return problems

    # --- after running ------------------------------------------------------
    def apply(self, plan, steps_done, success):
        """Replay the finished steps. A failed pick/place leaves that parcel UNKNOWN."""
        before = dict(self.parcels)
        held = next((p for p, loc in self.parcels.items() if loc == HELD), None)
        for i, step in enumerate(plan.steps):
            if i < steps_done:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target], held = HELD, step.target
                elif step.action == StepAction.place and held:
                    self.parcels[held], held = step.location.value, None
            elif i == steps_done and not success:
                if step.action == StepAction.pick and step.target in self.parcels:
                    self.parcels[step.target] = UNKNOWN
                elif step.action == StepAction.place and held:
                    self.parcels[held] = UNKNOWN
                break
        self.history.append((before, dict(self.parcels)))
        return self.parcels

    @staticmethod
    def _ko(loc):
        return {HELD: "그리퍼(들고 있음)", UNKNOWN: "확인 필요"}.get(loc, PLACE_KO.get(loc, loc))
