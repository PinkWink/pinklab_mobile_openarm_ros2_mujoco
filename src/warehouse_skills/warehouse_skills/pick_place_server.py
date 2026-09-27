"""PickPlace action server.

Phases (each reproducible by hand with the same ROS interfaces):
  navigate_pick  Nav2 to the station's fixed pre-dock pose (locations.yaml)
  dock           ArUco visual servo + short odometry segment (marker on the table legs)
  locate         object position relative to base_footprint (truth or camera)
  pre_grasp / grasp / lift   MoveIt IK + Cartesian moves, gripper, planning-scene attach
  carry          transport pose, undock backwards
  navigate_place / dock / place / retreat   mirror of the above at the place station
Goal.phase selects the halves: '' / all = pick then place in one goal; pick = up to the carry pose
(the server remembers what it holds); place = put the held object on to_station.
"""

import math
from pathlib import Path
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from mobile_openarm_mujoco.model import load_world
from warehouse_interfaces.action import PickPlace
from warehouse_lecture.memory.locations import Locations

from .locate import RobotPose, TruthLocator, VisionLocator
from .moveit_client import MoveItClient, SkillError, make_pose
from .nav_client import NavClient


def load_skills(path=None):
    file = Path(path) if path else Path(get_package_share_directory("warehouse_skills")) / "config/skills.yaml"
    return yaml.safe_load(file.read_text())


def srdf_states():
    srdf = ET.parse(Path(get_package_share_directory("mobile_openarm_moveit_config")) / "config/mobile_openarm.srdf")
    states = {"left": {}, "right": {}}
    for gs in srdf.findall("group_state"):
        side = gs.get("group").split("_")[0]
        if side in states:
            states[side][gs.get("name")] = {j.get("name"): float(j.get("value")) for j in gs.findall("joint")}
    return states


class PickPlaceServer(Node):
    def __init__(self):
        super().__init__("pick_place_server", parameter_overrides=[Parameter("use_sim_time", value=True)])
        self.declare_parameter("locate", "truth")  # truth | vision
        self.declare_parameter("skills_file", "")
        self.cfg = load_skills(self.get_parameter("skills_file").value or None)
        self.world = load_world()
        self.markers = {int(m["id"]): m for m in self.world.get("markers", [])}
        self.locations = Locations()
        self.states = srdf_states()
        self.moveit = MoveItClient(self, self.cfg, self.cfg["arms"])
        self.nav = NavClient(self, self.cfg)
        self.robot = RobotPose(self)
        self.truth = TruthLocator(self, self.robot)
        self.vision = VisionLocator(self, self.robot)
        self.busy = threading.Lock()
        self.held = None                      # {name, arm} after a phase=pick goal, until the place phase
        self.attached = None                  # {arm, name, pose} while a box is attached in the planning scene
        self.server = ActionServer(
            self,
            PickPlace,
            "/pick_place",
            execute_callback=self.execute,
            goal_callback=lambda _: GoalResponse.ACCEPT if not self.busy.locked() else GoalResponse.REJECT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup(),
        )
        self.get_logger().info("PickPlace server ready (/pick_place); waiting for MoveIt and Nav2")

    # --- lookups --------------------------------------------------------
    def table(self, key):
        name = self.world["stations"][self.locations.station(key)]["table"]
        box = next(b for b in self.world["boxes"] if b["name"] == name)
        return np.array(box["center"]), np.array(box["size"])

    def station(self, key):
        st = dict(self.cfg["stations"][key])
        st["offsets"] = {int(i): float(self.markers[int(i)]["offset_y"]) for i in st["markers"]}
        st["marker_x"] = float(self.markers[int(st["markers"][0])]["center"][0])
        centre, size = self.table(key)
        st["edge_x"], st["top_z"] = float(centre[0] - size[0] / 2), float(centre[2] + size[2] / 2)
        st["object_x"] = st["edge_x"] + float(self.cfg["place"]["x_from_edge"])
        return st

    def resolve_object(self, text):
        objects = self.cfg["objects"]
        if text in objects:
            return text
        for name, spec in objects.items():
            if spec["color"] == text.lower() or spec["color"] in text.lower():
                return name
        raise SkillError(f"unknown object {text!r}; use a name or colour ({', '.join(s['color'] for s in objects.values())})")

    def resolve_station(self, text):
        key = self.locations.resolve(text)
        if key is None or key not in self.cfg["stations"]:
            raise SkillError(f"unknown station {text!r}; use pick_table or place_table")
        return key

    def object_offset(self, name, key):
        """Object lateral offset from the station axis (m, +left when facing the table)."""
        (wx, wy, _), _ = self.truth.world(name)
        return wy - float(self.station(key)["axis_y"])

    @staticmethod
    def arm_for_offset(offset):
        """Arm whose shoulder is nearest to a lateral offset (m, +left)."""
        return "right" if offset < 0.0 else "left"

    @staticmethod
    def dock_side_for(offset, reach=0.25, max_side=0.2):
        """Lateral docking target (m, +left of the station axis) so that an object far from the
        axis ends up about ``reach`` m beside the base centre, within the arm's reach. Objects
        closer than ``reach`` keep the base on the axis (no side-step needed)."""
        if abs(offset) <= reach:
            return 0.0
        side = math.copysign(abs(offset) - reach, offset)
        return max(-max_side, min(max_side, side))

    def free_slot_offset(self, key, object_name, arm):
        """First free slot the chosen arm can reach: its own side first, then the centre."""
        st = self.station(key)
        others = [self.truth.world(n)[0] for n in self.truth.names if n != object_name]
        candidates = sorted(self.cfg["place"]["slot_offsets_y"], key=lambda o: -o if arm == "left" else o)
        for o in candidates:
            if (arm == "left" and o < -0.02) or (arm == "right" and o > 0.02):
                continue
            y = float(st["axis_y"]) + float(o)
            if all(np.hypot(p[0] - st["object_x"], p[1] - y) > 0.12 for p in others):
                return float(o)
        raise SkillError(f"no free slot on {key} reachable by the {arm} arm")

    def locator(self):
        return self.vision if self.get_parameter("locate").value == "vision" else self.truth

    def locate_object(self, name):
        """Object position relative to base_footprint. The camera pipeline labels parcels by
        colour class (parcel_red), so map the object name to that label in vision mode."""
        if self.get_parameter("locate").value == "vision":
            return self.vision.relative(f"parcel_{self.cfg['objects'][name]['color']}")
        return self.truth.relative(name)

    # --- phases ---------------------------------------------------------
    def navigate_and_dock(self, key, arm, target_side_fn, phase, feedback):
        """Nav2 to the fixed pre-dock pose, then ArUco docking on the station's marker pair.

        target_side_fn(origin, u) -> desired base offset from the station axis (m, +left of
        base = axis appears left) so that the arm's shoulder lines up with the object/slot.
        """
        goal = list(self.locations.goal(key))
        st = self.station(key)
        d = self.cfg["dock"]
        feedback(phase, 0.0, f"Nav2 to {key} pre-dock ({goal[0]:.2f}, {goal[1]:.2f})")
        self.nav.go_to(*goal)
        self.nav.settle()
        feedback(phase, 0.7, "arrived at pre-dock; looking for the markers")
        # The base docks on the station axis (side 0) unless the object is far off the axis
        # (dock_side_for); the arm is chosen by the object's side. Lateral errors above
        # max_lateral_error are corrected with an odometry side-step (turn, drive, turn back).
        for attempt in range(3):
            fixes = self.nav.wait_markers(st["markers"])
            along, side, turn, origin, u = self.nav.geometry(fixes, st["offsets"])
            target_side = target_side_fn(origin, u)
            lateral = side - target_side
            feedback(phase, 0.8, f"markers {sorted(fixes)}: along={along:.2f} side={side:+.3f} turn={math.degrees(turn):+.1f}deg; lateral error {lateral:+.3f}")
            if abs(lateral) <= float(d["max_lateral_error"]) or attempt == 2:
                break
            feedback(phase, 0.9, f"side-step {lateral:+.2f} m with odometry")
            if abs(turn) > 0.03:
                self.nav.turn(turn)
            self.nav.sidestep(lateral)
            self.nav.settle()
        if abs(lateral) > float(d["max_lateral_error"]) * 2:
            raise SkillError(f"lateral error {lateral:+.2f} m too large for docking")
        feedback(phase, 1.0, "pre-dock aligned")
        feedback("dock", 0.1, f"visual servo on markers {st['markers']} (target side {target_side:+.3f})")
        dx, residual = self.nav.dock(st["offsets"], self.cfg["dock"]["target_dx"], target_side, lambda t: feedback("dock", 0.5, t))
        dy = target_side + residual
        feedback("dock", 1.0, f"docked: plane dx={dx:.3f}, axis dy={dy:+.3f} (lateral residual {residual:+.3f})")
        return st, dx, dy

    def grasp(self, arm, name, feedback, rel=None):
        g = self.cfg["grasp"]
        size = self.cfg["objects"][name]["size"]
        dx, dy, dz = rel if rel is not None else self.locate_object(name)
        z = dz + float(g["z_offset"])
        feedback("locate", 1.0, f"{name} at dx={dx:.3f} dy={dy:+.3f} z={dz:.3f}")
        self.moveit.gripper(arm, g["open"], g["effort"])
        # Pre-grasp: start as far back as the arm can reach; shrink the offset if IK fails.
        offsets = [float(g["pre_offset_x"]), float(g["pre_offset_x"]) * 0.6, float(g["pre_offset_x"]) * 0.3]
        last_error = None
        for pre in offsets:
            feedback("pre_grasp", 0.2, f"planning to pre-grasp ({pre:+.2f} m behind the object)")
            try:
                self.moveit.move_pose(arm, make_pose([dx + pre, dy, z]))
                break
            except SkillError as error:
                last_error = error
        else:
            raise SkillError(f"pre-grasp unreachable: {last_error}")
        feedback("pre_grasp", 1.0, "at pre-grasp")
        feedback("grasp", 0.2, "approaching")
        self.moveit.move_cartesian(arm, [make_pose([dx, dy, z])])
        result = self.moveit.gripper(arm, g["close"], g["effort"])
        if not (float(g["close_min"]) <= result.position <= float(g["close_max"])):
            self.moveit.gripper(arm, g["open"], g["effort"])
            raise SkillError(f"grasp missed: finger stopped at {result.position * 1000:.1f} mm")
        feedback("grasp", 0.8, f"holding at {result.position * 1000:.1f} mm per finger")
        # Attached box in the hand frame: x = height (down), y = width (closing), z = depth (approach).
        self.moveit.attach(arm, name, [size[2], size[1], size[0]], below_tcp=float(g["z_offset"]))
        self.attached = {"arm": arm, "name": name, "pose": (dx, dy, z)}     # for recover() if the next moves fail
        feedback("lift", 0.3, "lifting")
        up = make_pose([dx, dy, z + float(g["lift_z"])])
        back = make_pose([dx + float(g["retreat_x"]), dy, z + float(g["lift_z"])])
        try:
            self.moveit.move_cartesian(arm, [up, back])
        except SkillError as error:
            # Near the reach limit (large dock residual) the straight-line retreat has no IK along
            # the way: lift straight up (short, almost always feasible), then let the planner find
            # a path to the retreat pose with the box attached and clear of the table.
            feedback("lift", 0.4, f"cartesian lift/retreat failed ({error}); lifting only, then planning the retreat")
            self.moveit.move_cartesian(arm, [up])
            self.moveit.move_pose(arm, back)
        feedback("lift", 1.0, "retreated")

    def place(self, arm, name, slot_dx, slot_dy, top_z, feedback):
        p, g = self.cfg["place"], self.cfg["grasp"]
        size = self.cfg["objects"][name]["size"]
        z = top_z + float(p["drop_z"]) + size[2] / 2 + float(g["z_offset"])
        feedback("place", 0.1, f"slot at dx={slot_dx:.3f} dy={slot_dy:+.3f}; planning to pre-place")
        self.moveit.move_pose(arm, make_pose([slot_dx + float(p["pre_offset_x"]), slot_dy, z + float(g["lift_z"])]))
        feedback("place", 0.5, "lowering")
        self.moveit.move_cartesian(arm, [make_pose([slot_dx, slot_dy, z + float(g["lift_z"])]),
                                         make_pose([slot_dx, slot_dy, z])])
        self.moveit.gripper(arm, g["open"], g["effort"])
        self.moveit.detach(arm, name)
        self.attached = None
        feedback("place", 0.8, "released")
        self.moveit.move_cartesian(arm, [make_pose([slot_dx + float(g["retreat_x"]), slot_dy, z + float(g["lift_z"])])])
        feedback("retreat", 0.5, "back to transport")

    # --- halves -----------------------------------------------------------
    def do_pick(self, goal, feedback):
        """Drive to the source station, dock, locate, grasp, carry pose, undock. Returns (name, arm, src)."""
        name = self.resolve_object(goal.object)
        src = self.resolve_station(goal.from_station or "pick_table")
        offset = self.object_offset(name, src)
        arm = goal.arm or self.arm_for_offset(offset)
        if arm not in self.cfg["arms"]:
            raise SkillError("arm must be left or right")
        feedback("start", 0.0, f"{name} sits {offset:+.2f} m from the {src} axis -> {arm} arm")
        self.moveit.move_named(arm, self.cfg["transport_pose"], self.states)
        dock_side = self.dock_side_for(offset)
        if dock_side:
            feedback("start", 0.1, f"object {offset:+.2f} m off the axis: dock {dock_side:+.2f} m to the side")
        # dock_side is the base offset from the axis (+left); the servo's target is the
        # axis offset as seen from the base, i.e. the opposite sign.
        self.navigate_and_dock(src, arm, lambda origin, u: -dock_side, "navigate_pick", feedback)
        # The dock leaves a lateral residual, so decide the arm from where the object
        # actually is relative to the base, not from the table axis.
        rel = self.locate_object(name)
        if not goal.arm and self.arm_for_offset(rel[1]) != arm:
            arm = self.arm_for_offset(rel[1])
            feedback("locate", 0.5, f"{name} is {rel[1]:+.3f} m from the base axis after docking -> {arm} arm instead")
        self.grasp(arm, name, feedback, rel)
        feedback("carry", 0.2, f"{self.cfg['carry_pose']} pose with object")
        self.moveit.move_named(arm, self.cfg["carry_pose"], self.states)
        self.nav.drive(-float(self.cfg["dock"]["undock_distance"]))
        return name, arm, src

    def do_place(self, goal, name, arm, feedback):
        """Drive to the destination station, dock, place on a free slot, transport pose, undock.
        Returns (station, slot offset)."""
        dst = self.resolve_station(goal.to_station or "place_table")
        offset = self.free_slot_offset(dst, name, arm)          # slots are defined relative to the station marker
        st, mdx, mdy = self.navigate_and_dock(dst, arm, lambda origin, u: 0.0, "navigate_place", feedback)
        slot_dx = mdx - (st["marker_x"] - st["object_x"])
        slot_dy = mdy + offset
        self.place(arm, name, slot_dx, slot_dy, st["top_z"], feedback)
        self.moveit.move_named(arm, self.cfg["transport_pose"], self.states)
        self.nav.drive(-float(self.cfg["dock"]["undock_distance"]))
        return st, offset

    def recover(self):
        """After a failure with a box attached in the planning scene: release it, detach, back the
        hand off and return the arm to the transport pose. Otherwise every later MoveIt request
        starts in collision (box touching the table) and the whole robot is stuck."""
        att, self.attached = self.attached, None
        if att is None:
            return
        arm, name, (dx, dy, z) = att["arm"], att["name"], att["pose"]
        g = self.cfg["grasp"]
        self.get_logger().warning(f"recovering: releasing {name} from the {arm} hand")
        for step, action in (("open gripper", lambda: self.moveit.gripper(arm, g["open"], g["effort"])),
                             ("detach", lambda: self.moveit.detach(arm, name)),
                             ("back off", lambda: self.moveit.move_cartesian(arm, [make_pose([dx + float(g["retreat_x"]), dy, z])])),
                             ("transport pose", lambda: self.moveit.move_named(arm, self.cfg["transport_pose"], self.states))):
            try:
                action()
            except SkillError as error:
                self.get_logger().warning(f"recover/{step} failed: {error}")
        if self.held and self.held["name"] == name:
            self.held = None

    # --- action -----------------------------------------------------------
    def execute(self, handle):
        goal = handle.request
        result = PickPlace.Result()
        start = time.monotonic()
        phase = {"name": "start"}

        def feedback(name, progress, detail):
            phase["name"] = name
            handle.publish_feedback(PickPlace.Feedback(phase=name, progress=float(progress), detail=detail))
            self.get_logger().info(f"[{name}] {detail}")
            if handle.is_cancel_requested:
                raise SkillError("cancelled")

        with self.busy:
            self.nav.cancel_requested = False
            try:
                self.moveit.ready()
                self.nav.ready()
                which = (goal.phase or "all").lower()
                if which not in ("all", "pick", "place"):
                    raise SkillError(f"phase must be all, pick or place (got {goal.phase!r})")
                if which == "place":
                    if self.held is None:
                        raise SkillError("nothing is held: run the pick phase first")
                    name, arm = self.held["name"], self.held["arm"]
                    feedback("start", 0.0, f"placing the held {name} ({arm} arm)")
                else:
                    if self.held is not None:
                        raise SkillError(f"already holding {self.held['name']}: place it first")
                    name, arm, src = self.do_pick(goal, feedback)
                if which == "pick":
                    (fx, fy, fz), _ = self.truth.world(name)
                    top_z = self.station(src)["top_z"]
                    lifted = float(fz - top_z)
                    result.success = bool(lifted > 0.02)
                    if result.success:
                        self.held = {"name": name, "arm": arm}
                        result.message = f"{name} held in the {arm} hand, {lifted:.3f} m above the table"
                    else:
                        result.message = f"{name} not lifted ({lifted:+.3f} m relative to the table top)"
                else:
                    st, offset = self.do_place(goal, name, arm, feedback)
                    self.held = None
                    (fx, fy, fz), _ = self.truth.world(name)
                    target = (st["object_x"], float(st["axis_y"]) + offset)
                    placed = float(math.hypot(fx - target[0], fy - target[1]))
                    fx, fy, fz = float(fx), float(fy), float(fz)
                    # Plain Python bool: rclpy's message conversion asserts on numpy.bool_.
                    result.success = bool(placed < 0.08 and fz > st["top_z"])
                    result.message = (f"{name} placed at ({fx:.2f}, {fy:.2f}, {fz:.3f}), {placed * 100:.1f} cm from the slot"
                                      if result.success else f"{name} ended at ({fx:.2f}, {fy:.2f}, {fz:.3f}), not on the slot")
                result.phase_reached = "done"
                handle.succeed() if result.success else handle.abort()
            except SkillError as error:
                self.nav.stop()
                result.success = False
                result.message = str(error)
                result.phase_reached = phase["name"]
                self.get_logger().error(f"PickPlace failed in {phase['name']}: {error}")
                self.recover()
                if handle.is_cancel_requested:
                    handle.canceled()
                else:
                    handle.abort()
            result.duration_s = float(time.monotonic() - start)
        return result

def main():
    rclpy.init()
    node = PickPlaceServer()
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
