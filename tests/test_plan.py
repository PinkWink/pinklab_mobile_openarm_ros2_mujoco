"""RobotPlan schema, world validation, ROS conversion and the plan parser's few-shot examples (no simulator, no LLM)."""

from warehouse_interfaces.action import PickPlace
from warehouse_lecture.commands.plan import PlanStep, RobotPlan, StepAction
from warehouse_lecture.commands.plan_parser import EXAMPLES


def actions(plan):
    return [s.action.value for s in plan.steps]


def test_move_plan_validates_and_round_trips_through_ros():
    plan = RobotPlan(summary="s", reply="r", steps=[
        PlanStep(action="navigate", location="pick_table"), PlanStep(action="detect", target="parcel_red"),
        PlanStep(action="pick", target="parcel_red", location="pick_table"),
        PlanStep(action="navigate", location="place_table"), PlanStep(action="place", location="place_table")])
    assert plan.validate_world() == []
    assert plan.needs_confirmation()
    goal = plan.to_msg(utterance="u")
    assert goal.utterance == "u" and len(goal.steps) == 5 and goal.steps[2].action == "pick" and goal.steps[2].location == "pick_table"
    assert goal.steps[0].note  # describe() fills an empty note
    back = RobotPlan.from_msg(goal)
    assert actions(back) == actions(plan) and back.steps[4].target == "parcel_red"  # place inherits the held object


def test_missing_navigate_and_stations_are_filled_in():
    plan = RobotPlan(steps=[PlanStep(action="pick", target="parcel_blue"), PlanStep(action="place")])
    assert plan.validate_world() == []
    assert actions(plan) == ["navigate", "pick", "navigate", "place"]
    assert plan.steps[0].location.value == "pick_table" and plan.steps[1].location.value == "pick_table"
    assert plan.steps[2].location.value == "place_table" and plan.steps[3].location.value == "place_table"
    assert "자동 추가" in plan.steps[0].note


def test_semantic_problems_are_reported():
    assert any("든 것이 없는데" in p for p in RobotPlan(steps=[PlanStep(action="place", location="place_table")]).validate_world())
    assert any("든 채로 끝난다" in p for p in RobotPlan(steps=[PlanStep(action="pick", target="parcel_red", location="pick_table")]).validate_world())
    assert any("작업대" in p for p in RobotPlan(steps=[PlanStep(action="pick", target="parcel_red", location="rack_c"), PlanStep(action="place")]).validate_world())
    assert any("상자가 정해지지" in p for p in RobotPlan(steps=[PlanStep(action="pick", target="parcel"), PlanStep(action="place")]).validate_world())
    assert any("떨어뜨린다" in p for p in RobotPlan(steps=[PlanStep(action="pick", target="parcel_red"), PlanStep(action="gripper", target="open"), PlanStep(action="place")]).validate_world())
    assert RobotPlan().validate_world() == ["단계도 답변도 없다"]
    assert RobotPlan(reply="어떤 색?").validate_world() == []


def test_report_plan_needs_no_confirmation():
    plan = RobotPlan(steps=[PlanStep(action="navigate", location="rack_c"), PlanStep(action="report")])
    assert plan.validate_world() == [] and not plan.needs_confirmation()
    assert plan.describe().splitlines()[0].startswith("1. 랙 C로 이동")


def test_parser_examples_are_executable_plans():
    for text, plan in EXAMPLES:
        problems = plan.validate_world()
        assert problems == [], (text, problems)
        assert bool(plan.steps) == ("옮겨 줘" not in text)


def test_pick_place_goal_has_phase_field():
    goal = PickPlace.Goal(object="red", from_station="pick_table", phase="pick")
    assert goal.phase == "pick" and StepAction.place.value == "place"
