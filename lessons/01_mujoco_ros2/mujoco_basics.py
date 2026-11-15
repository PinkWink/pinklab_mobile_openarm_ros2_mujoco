"""MuJoCo Python basics, no ROS 2: load a model, write a command, step the physics, read the state.

  python lessons/01_mujoco_ros2/mujoco_basics.py

urdf_bridge.py is this loop with ROS 2 publishers and a subscriber added.
"""
from pathlib import Path

import mujoco

MJCF = Path(__file__).with_name("two_link_arm_from_urdf.xml")   # written by urdf_to_mjcf.py
if not MJCF.exists():
    raise SystemExit(f"{MJCF.name} not found: run  python lessons/01_mujoco_ros2/urdf_to_mjcf.py  first")

model = mujoco.MjModel.from_xml_path(str(MJCF))    # model: the description, never changes
data = mujoco.MjData(model)                        # data: the state, changes every step
print(f"joints {model.njnt}  actuators {model.nu}  timestep {model.opt.timestep} s")

data.ctrl[:] = [0.6, 1.5]                          # write: target angle of each actuator [rad]
for i in range(1000):
    mujoco.mj_step(model, data)                    # advance time by one timestep
    if i % 250 == 249:                             # read: joint angles and a body position
        print(f"t {data.time:.1f} s  qpos {data.qpos.round(3)}  camera_link xpos {data.body('camera_link').xpos.round(3)}")
