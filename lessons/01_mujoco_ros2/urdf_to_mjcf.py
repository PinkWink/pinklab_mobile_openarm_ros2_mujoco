"""URDF -> MJCF: read two_link_arm.urdf with MuJoCo and add what a URDF does not have.

A URDF describes the robot only. A simulation also needs physics options, a floor, light, actuators and sensors.
This script adds them with mujoco.MjSpec (the model-editing API) and saves the result as MJCF.

  python lessons/01_mujoco_ros2/urdf_to_mjcf.py            # report + two_link_arm_from_urdf.xml
  python lessons/01_mujoco_ros2/urdf_to_mjcf.py --raw      # what MuJoCo makes of a plain URDF (no <mujoco> tag, nothing added)
  python -m mujoco.viewer --mjcf=lessons/01_mujoco_ros2/two_link_arm_from_urdf.xml
"""
import argparse
import re
from pathlib import Path

import mujoco

HERE = Path(__file__).parent
URDF = HERE / "two_link_arm.urdf"
MJCF = HERE / "two_link_arm_from_urdf.xml"
KP = {"joint1": 30.0, "joint2": 20.0}          # position-actuator gains: not in the URDF


def build(urdf=URDF):
    """URDF file -> (MjSpec, MjModel) ready to simulate."""
    spec = mujoco.MjSpec.from_file(str(urdf))               # 1. MuJoCo parses the URDF itself

    spec.option.timestep = 0.002                             # 2. physics options (URDF has none)
    for geom in spec.geoms:                                  #    <collision> shapes: keep contact, hide in the viewer
        if geom.contype:
            geom.group = 3
    # base_link is welded to the world, and MuJoCo skips the parent-child contact filter for such bodies:
    # without this line link1 hits the base cylinder and stops at 0.24 rad
    spec.add_exclude(bodyname1="base_link", bodyname2="link1")

    world = spec.worldbody                                   # 3. the world around the robot
    world.add_light(pos=[0.5, -0.5, 2.0], dir=[-0.3, 0.3, -1.0])
    world.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[2, 2, 0.05], rgba=[0.8, 0.8, 0.8, 1])
    world.add_geom(name="red_box", type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0.55, 0.08, 0.04],
                   size=[0.04, 0.04, 0.04], rgba=[0.9, 0.2, 0.2, 1])
    world.add_geom(name="blue_box", type=mujoco.mjtGeom.mjGEOM_BOX, pos=[0.62, -0.10, 0.03],
                   size=[0.03, 0.03, 0.03], rgba=[0.2, 0.3, 0.9, 1])

    # 4. camera sensor on the ROS optical frame (z forward, y down). A MuJoCo camera looks along its -z with +y up,
    #    so it is the optical frame turned 180 deg about x: quat [w, x, y, z] = [0, 1, 0, 0]
    spec.body("camera_optical_frame").add_camera(name="tip_camera", quat=[0, 1, 0, 0], fovy=60)

    for joint in spec.joints:                                # 5. one position actuator per joint
        act = spec.add_actuator(name=f"{joint.name}_pos", target=joint.name, trntype=mujoco.mjtTrn.mjTRN_JOINT)
        act.set_to_position(kp=KP[joint.name])
        act.ctrlrange, act.ctrllimited = joint.range, True   #    command limit = URDF <limit lower upper>

    return spec, spec.compile()                              # 6. MjModel


def report(model, title):
    names = lambda kind, n: [mujoco.mj_id2name(model, kind, i) for i in range(n)]
    print(f"[{title}]")
    print(f"  body     {model.nbody}: {names(mujoco.mjtObj.mjOBJ_BODY, model.nbody)}")
    print(f"  joint    {model.njnt}: {names(mujoco.mjtObj.mjOBJ_JOINT, model.njnt)}")
    print(f"  geom     {model.ngeom}   (contact on: {int((model.geom_contype > 0).sum())})")
    print(f"  actuator {model.nu}: {names(mujoco.mjtObj.mjOBJ_ACTUATOR, model.nu)}")
    print(f"  camera   {model.ncam}: {names(mujoco.mjtObj.mjOBJ_CAMERA, model.ncam)}")
    print(f"  mass     {model.body_mass.sum():.2f} kg")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", action="store_true", help="load the URDF without its <mujoco> tag, add nothing, report")
    args = ap.parse_args()
    if args.raw:
        plain = re.sub(r"<mujoco>.*?</mujoco>", "", URDF.read_text(), flags=re.S)
        report(mujoco.MjModel.from_xml_string(plain), f"{URDF.name} as a plain URDF")
        return
    spec, model = build()
    report(model, f"{URDF.name} -> {MJCF.name}")
    MJCF.write_text(spec.to_xml())
    print(f"  saved    {MJCF}")


if __name__ == "__main__":
    main()
