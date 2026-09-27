"""MoveIt-compatible action servers driven by the single physics thread."""

from functools import partial
import math
import numpy as np
from rclpy.action import ActionServer, GoalResponse, CancelResponse
from rclpy.task import Future
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from .trajectory import validate_trajectory, Trajectory, seconds


class Controllers:
    def __init__(self, node):
        self.node = node
        self.physics = node.physics
        self.active = {}
        self.reserved = set()
        self.servers = []
        self.names = {}
        for side in ["left", "right"]:
            arm = side + "_joint_trajectory_controller"
            gripper = side + "_gripper_controller"
            self.names[arm] = [f"openarm_{side}_joint{i}" for i in range(1, 8)]
            self.names[gripper] = [f"openarm_{side}_finger_joint1"]
            for key, kind, suffix in [
                (arm, FollowJointTrajectory, "follow_joint_trajectory"),
                (gripper, GripperCommand, "gripper_cmd"),
            ]:
                self.servers.append(
                    ActionServer(
                        node,
                        kind,
                        "/" + key + "/" + suffix,
                        goal_callback=lambda request, k=key: self.goal(k, request),
                        cancel_callback=lambda handle: CancelResponse.ACCEPT,
                        execute_callback=partial(self.execute, key),
                    )
                )

    def goal(self, key, request):
        p = self.physics
        if (
            key in self.reserved
            or np.max(np.abs(p.twist)) > 0.04
            or np.max(np.abs(p.command)) > 0.04
        ):
            return GoalResponse.REJECT
        try:
            if "trajectory" in key:
                limits = {
                    n: p.model.jnt_range[p.model.joint(n).id] for n in self.names[key]
                }
                validate_trajectory(
                    request.trajectory, self.names[key], limits, p.data.time
                )
                for tolerance in list(request.path_tolerance) + list(
                    request.goal_tolerance
                ):
                    if tolerance.name not in self.names[key]:
                        raise ValueError("Unknown tolerance joint")
                    if any(
                        not math.isfinite(v) or (v < 0 and v != -1)
                        for v in [
                            tolerance.position,
                            tolerance.velocity,
                            tolerance.acceleration,
                        ]
                    ):
                        raise ValueError("Invalid tolerance")
                    if tolerance.acceleration > 0:
                        raise ValueError("Acceleration tolerance is not supported")
                if any(t.velocity > 0 for t in request.path_tolerance):
                    raise ValueError("Path velocity tolerance is not supported")
                if request.multi_dof_trajectory.points:
                    raise ValueError("Multi-DOF trajectory is not supported")
                if seconds(request.goal_time_tolerance) < 0:
                    raise ValueError("Negative goal timeout")
            else:
                q = request.command.position
                effort = request.command.max_effort
                if (
                    not math.isfinite(q)
                    or not 0 <= q <= 0.044
                    or not math.isfinite(effort)
                    or effort < 0
                ):
                    raise ValueError("Invalid gripper command")
        except ValueError as error:
            self.node.get_logger().warning(str(error))
            return GoalResponse.REJECT
        self.reserved.add(key)
        self.node.command = (0.0, 0.0)
        self.node.command_time = -math.inf
        return GoalResponse.ACCEPT

    async def execute(self, key, handle):
        p = self.physics
        names = (
            list(handle.request.trajectory.joint_names)
            if "trajectory" in key
            else self.names[key]
        )
        state = {
            "handle": handle,
            "names": names,
            "future": Future(),
            "start": p.data.time,
            "last_feedback": -1.0,
        }
        if "trajectory" in key:
            state["trajectory"] = Trajectory(
                handle.request.trajectory, p.positions(names)
            )
            state["start"] = max(
                p.data.time, seconds(handle.request.trajectory.header.stamp)
            )
        else:
            state.update(
                last_position=float(p.positions(names)[0]), last_motion=p.data.time
            )
            aid = p.model.actuator(names[0] + "_position").id
            effort = (
                handle.request.command.max_effort or p.settings["gripper"]["max_force"]
            )
            effort = min(effort, p.settings["gripper"]["max_force"])
            p.model.actuator_forcerange[aid] = [-effort, effort]
            p.set_targets(names, [handle.request.command.position])
        self.active[key] = state
        return await state["future"]

    def finish(self, key, state, result, status):
        p = self.physics
        if status != "succeed":
            p.hold(state["names"])
        getattr(state["handle"], status)()
        state["future"].set_result(result)
        self.active.pop(key)
        self.reserved.discard(key)
        self.node.command = (0.0, 0.0)
        self.node.command_time = -math.inf

    def tolerance_failed(self, state, desired, goal=False):
        req = state["handle"].request
        names = state["names"]
        p = self.physics
        values = req.goal_tolerance if goal else req.path_tolerance
        tol = {t.name: t for t in values}
        default = p.settings["arm"]["goal_tolerance"] if goal else 0.35
        actual = p.positions(names)
        for i, n in enumerate(names):
            t = tol.get(n)
            position = t.position if t and t.position != 0 else default
            if position != -1 and abs(actual[i] - desired[i]) > position:
                return True
            if t and t.velocity > 0 and goal:
                if abs(p.data.qvel[p.model.joint(n).dofadr[0]]) > t.velocity:
                    return True
        return False

    def update(self):
        p = self.physics
        for key, state in list(self.active.items()):
            h = state["handle"]
            t = p.data.time - state["start"]
            is_arm = "trajectory" in key
            result = (
                FollowJointTrajectory.Result() if is_arm else GripperCommand.Result()
            )
            if h.is_cancel_requested:
                self.finish(key, state, result, "canceled")
                continue
            if is_arm:
                traj = state["trajectory"]
                desired = traj.sample(t)
                p.set_targets(state["names"], desired)
                if t >= 0 and p.data.time - state["last_feedback"] >= 0.05:
                    feedback = FollowJointTrajectory.Feedback()
                    feedback.header.stamp = self.node.sim_stamp()
                    feedback.joint_names = state["names"]
                    feedback.desired = JointTrajectoryPoint(positions=desired.tolist())
                    feedback.actual = JointTrajectoryPoint(
                        positions=p.positions(state["names"]).tolist()
                    )
                    feedback.error = JointTrajectoryPoint(
                        positions=(desired - p.positions(state["names"])).tolist()
                    )
                    h.publish_feedback(feedback)
                    state["last_feedback"] = p.data.time
                if 0 < t < traj.times[-1] and self.tolerance_failed(state, desired):
                    result.error_code = result.PATH_TOLERANCE_VIOLATED
                    result.error_string = "Measured position exceeded path tolerance"
                    self.finish(key, state, result, "abort")
                    continue
                timeout = (
                    seconds(h.request.goal_time_tolerance)
                    or p.settings["arm"]["goal_time_tolerance"]
                )
                if t >= traj.times[-1] and not self.tolerance_failed(
                    state, traj.positions[-1], True
                ):
                    result.error_code = result.SUCCESSFUL
                    self.finish(key, state, result, "succeed")
                elif t > traj.times[-1] + timeout:
                    result.error_code = result.GOAL_TOLERANCE_VIOLATED
                    result.error_string = "Measured joints did not reach the goal"
                    self.finish(key, state, result, "abort")
            else:
                position = float(p.positions(state["names"])[0])
                aid = p.model.actuator(state["names"][0] + "_position").id
                effort = float(p.data.actuator_force[aid])
                reached = (
                    abs(position - h.request.command.position)
                    < p.settings["gripper"]["goal_tolerance"]
                )
                if abs(position - state["last_position"]) > 0.0001:
                    state["last_motion"] = p.data.time
                    state["last_position"] = position
                stalled = p.data.time - state["last_motion"] > 1.0 and not reached
                result.position = position
                result.effort = effort
                result.reached_goal = reached
                result.stalled = stalled
                if p.data.time - state["last_feedback"] >= 0.05:
                    h.publish_feedback(
                        GripperCommand.Feedback(
                            position=position,
                            effort=effort,
                            reached_goal=reached,
                            stalled=stalled,
                        )
                    )
                    state["last_feedback"] = p.data.time
                if reached or stalled:
                    self.finish(key, state, result, "succeed")
                elif t > 6:
                    self.finish(key, state, result, "abort")
