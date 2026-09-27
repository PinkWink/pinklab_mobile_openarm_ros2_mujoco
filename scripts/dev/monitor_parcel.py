"""Log parcel_1 height, right gripper finger position, and PickPlace phases with sim time."""
import sys, time, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import PoseArray
from sensor_msgs.msg import JointState
from warehouse_interfaces.action import PickPlace

rclpy.init()
n = Node("parcel_monitor", parameter_overrides=[Parameter("use_sim_time", value=True)])
state = {"z": None, "xy": None, "finger": None, "phase": ""}
out = open(sys.argv[1], "w")


def log(msg):
    t = n.get_clock().now().nanoseconds / 1e9
    out.write(f"{t:8.2f} z={state['z']} xy={state['xy']} finger={state['finger']} {msg}\n")
    out.flush()


def on_obj(m):
    p = m.poses[0].position
    state["z"] = round(p.z, 3)
    state["xy"] = (round(p.x, 2), round(p.y, 2))


def on_js(m):
    d = dict(zip(m.name, m.position))
    state["finger"] = round(1000 * d.get("openarm_right_finger_joint1", 0), 1)


def on_fb(m):
    fb = m.feedback
    text = f"[{fb.phase}] {fb.detail}"
    if text != state["phase"]:
        state["phase"] = text
        log(text)


n.create_subscription(PoseArray, "/warehouse/object_poses", on_obj, 10)
n.create_subscription(JointState, "/joint_states", on_js, 10)
n.create_subscription(PickPlace.Impl.FeedbackMessage, "/pick_place/_action/feedback", on_fb, 10)
last = time.monotonic()
while rclpy.ok():
    rclpy.spin_once(n, timeout_sec=0.05)
    if time.monotonic() - last > 0.5:
        log("tick")
        last = time.monotonic()
