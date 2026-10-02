"""Blocking MoveIt helpers for use from an executor thread (MultiThreadedExecutor)."""

import math
import time

import numpy as np
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from control_msgs.action import GripperCommand
from geometry_msgs.msg import Pose, PoseStamped
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    AttachedCollisionObject,
    CollisionObject,
    Constraints,
    JointConstraint,
    MoveItErrorCodes,
    PlanningScene,
)
from moveit_msgs.srv import ApplyPlanningScene, GetCartesianPath, GetPositionIK
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String


class SkillError(RuntimeError):
    pass


def wait(future, timeout, what):
    end = time.monotonic() + timeout
    while not future.done():
        if time.monotonic() > end:
            raise SkillError(f"{what} timed out after {timeout:.0f}s")
        time.sleep(0.02)
    return future.result()


def quat_from_axes(x, y, z):
    """xyzw quaternion whose columns are the given world-frame axes."""
    R = np.column_stack([x, y, z])
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        return [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s]
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(R[i, i] - R[j, j] - R[k, k] + 1.0) * 2
    q = [0.0, 0.0, 0.0, 0.0]
    q[i] = 0.25 * s
    q[j] = (R[j, i] + R[i, j]) / s
    q[k] = (R[k, i] + R[i, k]) / s
    q[3] = (R[k, j] - R[j, k]) / s
    return q


# Forward horizontal grasp: hand z (approach) -> +x, hand y (finger closing) -> +y, hand x -> -z.
GRASP_FORWARD = quat_from_axes(np.array([0, 0, -1.0]), np.array([0, 1.0, 0]), np.array([1.0, 0, 0]))


def make_pose(xyz, quat=GRASP_FORWARD):
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = map(float, xyz)
    pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = map(float, quat)
    return pose


class MoveItClient:
    def __init__(self, node, cfg, arms):
        self.node = node
        self.cfg = cfg
        self.arms = arms
        group = ReentrantCallbackGroup()
        self.joints = {}
        node.create_subscription(JointState, "/joint_states", self._joints, 10, callback_group=group)
        self.ik = node.create_client(GetPositionIK, "/compute_ik", callback_group=group)
        self.cartesian = node.create_client(GetCartesianPath, "/compute_cartesian_path", callback_group=group)
        self.scene = node.create_client(ApplyPlanningScene, "/apply_planning_scene", callback_group=group)
        self.move = ActionClient(node, MoveGroup, "/move_action", callback_group=group)
        self.execute = ActionClient(node, ExecuteTrajectory, "/execute_trajectory", callback_group=group)
        self.grippers = {
            side: ActionClient(node, GripperCommand, f"/{a['gripper']}/gripper_cmd", callback_group=group)
            for side, a in arms.items()
        }
        self.attached_pub = node.create_publisher(String, "/warehouse_scene/attached", 1)

    def _joints(self, msg):
        self.joints.update(zip(msg.name, msg.position))

    def ready(self, timeout=30.0):
        end = time.monotonic() + timeout
        for client in (self.ik, self.cartesian, self.scene):
            if not client.wait_for_service(timeout_sec=max(0.1, end - time.monotonic())):
                raise SkillError(f"MoveIt service {client.srv_name} unavailable")
        for client in (self.move, self.execute, *self.grippers.values()):
            if not client.wait_for_server(timeout_sec=max(0.1, end - time.monotonic())):
                raise SkillError("MoveIt action server unavailable")
        while not self.joints and time.monotonic() < end:
            time.sleep(0.05)

    # --- arm ------------------------------------------------------------
    def arm_joints(self, side):
        return [f"openarm_{side}_joint{i}" for i in range(1, 8)]

    def solve_ik(self, side, pose, avoid_collisions=True):
        """Best IK solution (closest to the current joints) among several KDL restarts."""
        arm = self.arms[side]
        names = self.arm_joints(side)
        seed = np.array([self.joints.get(n, 0.0) for n in names])
        best = None
        for _ in range(int(self.cfg["moveit"]["ik_attempts"])):
            req = GetPositionIK.Request()
            r = req.ik_request
            r.group_name, r.ik_link_name = arm["group"], arm["tcp_link"]
            r.avoid_collisions = avoid_collisions
            r.timeout.nanosec = 200_000_000
            r.pose_stamped = PoseStamped()
            r.pose_stamped.header.frame_id = "base_footprint"
            r.pose_stamped.pose = pose
            r.robot_state.is_diff = True
            r.robot_state.joint_state.name = names
            r.robot_state.joint_state.position = seed.tolist()
            res = wait(self.ik.call_async(req), 5.0, "compute_ik")
            if res.error_code.val != MoveItErrorCodes.SUCCESS:
                continue
            q = dict(zip(res.solution.joint_state.name, res.solution.joint_state.position))
            sol = np.array([q[n] for n in names])
            cost = float(np.linalg.norm(sol - seed))
            if best is None or cost < best[0]:
                best = (cost, sol)
        if best is None:
            raise SkillError(f"No IK solution for {side} arm at ({pose.position.x:.2f}, {pose.position.y:.2f}, {pose.position.z:.2f})")
        return best[1]

    def move_joints(self, side, positions, timeout=60.0):
        goal = MoveGroup.Goal()
        req = goal.request
        req.group_name = self.arms[side]["group"]
        m = self.cfg["moveit"]
        req.allowed_planning_time = float(m["planning_time"])
        req.num_planning_attempts = int(m["attempts"])
        req.max_velocity_scaling_factor = float(m["velocity_scaling"])
        req.max_acceleration_scaling_factor = float(m["acceleration_scaling"])
        req.start_state.is_diff = True
        c = Constraints(name="skill")
        # 목표는 IK 로 검증된 관절값이다. ±0.01 rad 이면 계획 끝이 관절마다 ~0.01 rad 달라져 TCP 가 수 mm ~ 1 cm 틀어진다.
        for name, value in zip(self.arm_joints(side), positions):
            c.joint_constraints.append(
                JointConstraint(joint_name=name, position=float(value), tolerance_above=0.001, tolerance_below=0.001, weight=1.0)
            )
        req.goal_constraints = [c]
        goal.planning_options.planning_scene_diff.is_diff = True
        goal.planning_options.planning_scene_diff.robot_state.is_diff = True
        handle = wait(self.move.send_goal_async(goal), 10.0, "move_action goal")
        if not handle.accepted:
            raise SkillError("MoveIt rejected the joint goal")
        result = wait(handle.get_result_async(), timeout, "move_action result")
        code = result.result.error_code.val
        if code != MoveItErrorCodes.SUCCESS:
            raise SkillError(f"MoveIt joint motion failed (error_code={code})")

    def move_named(self, side, name, srdf_states):
        self.move_joints(side, [srdf_states[side][name][j] for j in self.arm_joints(side)])

    def move_pose(self, side, pose):
        self.move_joints(side, self.solve_ik(side, pose))

    def move_cartesian(self, side, waypoints, timeout=60.0):
        """Straight-line motion of the TCP through waypoints (base_footprint frame)."""
        arm = self.arms[side]
        m = self.cfg["moveit"]
        req = GetCartesianPath.Request()
        req.header.frame_id = "base_footprint"
        req.start_state.is_diff = True
        req.group_name, req.link_name = arm["group"], arm["tcp_link"]
        req.waypoints = list(waypoints)
        req.max_step = float(m["cartesian_step"])
        req.jump_threshold = 0.0
        req.avoid_collisions = True
        req.max_velocity_scaling_factor = float(m["velocity_scaling"])
        req.max_acceleration_scaling_factor = float(m["acceleration_scaling"])
        res = wait(self.cartesian.call_async(req), 10.0, "compute_cartesian_path")
        if res.error_code.val != MoveItErrorCodes.SUCCESS or res.fraction < float(m["cartesian_min_fraction"]):
            raise SkillError(f"Cartesian path covers only {res.fraction * 100:.0f}% (error_code={res.error_code.val})")
        goal = ExecuteTrajectory.Goal(trajectory=res.solution)
        handle = wait(self.execute.send_goal_async(goal), 10.0, "execute_trajectory goal")
        if not handle.accepted:
            raise SkillError("MoveIt rejected the Cartesian trajectory")
        result = wait(handle.get_result_async(), timeout, "execute_trajectory result")
        if result.result.error_code.val != MoveItErrorCodes.SUCCESS:
            raise SkillError(f"Cartesian execution failed (error_code={result.result.error_code.val})")
        return res.fraction

    # --- gripper --------------------------------------------------------
    def gripper(self, side, position, effort, timeout=15.0):
        goal = GripperCommand.Goal()
        goal.command.position, goal.command.max_effort = float(position), float(effort)
        handle = wait(self.grippers[side].send_goal_async(goal), 10.0, "gripper goal")
        if not handle.accepted:
            raise SkillError("Gripper goal rejected (is the base moving or an arm action active?)")
        result = wait(handle.get_result_async(), timeout, "gripper result").result
        return result

    # --- planning scene attach / detach --------------------------------
    def attach(self, side, name, size, below_tcp=0.0):
        """Attach a box to the hand. below_tcp: how far the box centre sits below the TCP
        (the hand's +x axis points down in the forward grasp), so collision checks use
        the real object position rather than the TCP."""
        arm = self.arms[side]
        obj = CollisionObject()
        obj.id = name
        obj.header.frame_id = arm["hand_link"]
        obj.operation = CollisionObject.ADD
        obj.primitives = [SolidPrimitive(type=SolidPrimitive.BOX, dimensions=[float(v) for v in size])]
        pose = Pose()
        pose.position.x = float(below_tcp)
        pose.position.z = 0.0835  # TCP offset along the hand's approach axis
        pose.orientation.w = 1.0
        obj.primitive_poses = [pose]
        att = AttachedCollisionObject()
        att.link_name = arm["hand_link"]
        att.object = obj
        att.touch_links = [
            arm["hand_link"],
            arm["tcp_link"],
            f"openarm_{side}_left_finger",
            f"openarm_{side}_right_finger",
        ]
        self.attached_pub.publish(String(data=name))
        time.sleep(0.6)  # let warehouse_scene drop its world copy first
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.robot_state.attached_collision_objects = [att]
        wait(self.scene.call_async(ApplyPlanningScene.Request(scene=scene)), 5.0, "attach")

    def detach(self, side, name):
        att = AttachedCollisionObject()
        att.link_name = self.arms[side]["hand_link"]
        att.object.id = name
        att.object.operation = CollisionObject.REMOVE
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.robot_state.attached_collision_objects = [att]
        wait(self.scene.call_async(ApplyPlanningScene.Request(scene=scene)), 5.0, "detach")
        self.attached_pub.publish(String(data=""))
