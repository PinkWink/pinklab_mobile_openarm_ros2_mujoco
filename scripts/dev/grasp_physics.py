"""Offline grasp-hold experiment: box between the right fingers in hands_up, then drive hard."""
import sys
import numpy as np, mujoco
from mobile_openarm_mujoco.model import Physics, build_model

effort = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
close = float(sys.argv[2]) if len(sys.argv) > 2 else 0.012
noslip = int(sys.argv[3]) if len(sys.argv) > 3 else 0
impratio = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
p = Physics(build_model("artifacts/mobile_generated_test"))
m, d = p.model, p.data
m.opt.noslip_iterations = noslip
m.opt.impratio = impratio
print(f"effort={effort} close={close} noslip={noslip} impratio={impratio}")
# Right arm to hands_up, gripper open
for i in range(1, 8):
    n = f"openarm_right_joint{i}"
    v = 2.0 if i == 4 else 0.0
    d.qpos[m.joint(n).qposadr[0]] = v
    d.ctrl[m.actuator(n + "_position").id] = v
d.qpos[m.joint("openarm_right_finger_joint1").qposadr[0]] = 0.044
d.qpos[m.joint("openarm_right_finger_joint2").qposadr[0]] = 0.044
d.ctrl[m.actuator("openarm_right_finger_joint1_position").id] = 0.044
mujoco.mj_forward(m, d)
# Box at the TCP, 2 cm "below" along hand x, oriented with the hand (box z along hand x -> height axis)
hand = m.body("openarm_right_hand").id
R = d.xmat[hand].reshape(3, 3)
tcp = d.xpos[m.body("openarm_right_hand_tcp").id]
centre = tcp + R[:, 0] * 0.02
box = m.joint("parcel_1_free").qposadr[0]
d.qpos[box : box + 3] = centre
# quaternion of the box: box x -> hand z (approach), box y -> hand y, box z -> -hand x (height up)
Rb = np.column_stack([R[:, 2], R[:, 1], -R[:, 0]])
q = np.empty(4); mujoco.mju_mat2Quat(q, Rb.ravel()); d.qpos[box + 3 : box + 7] = q
d.qvel[:] = 0
mujoco.mj_forward(m, d)
aid = m.actuator("openarm_right_finger_joint1_position").id
m.actuator_forcerange[aid] = [-effort, effort]
d.ctrl[aid] = close
fq = m.joint("openarm_right_finger_joint1").qposadr[0]
def rel():
    return np.linalg.norm(d.qpos[box : box + 3] - d.xpos[m.body("openarm_right_hand_tcp").id])
for _ in range(200): p.step()
print(f"after close: finger={1000*d.qpos[fq]:.1f}mm force={d.actuator_force[aid]:.1f}N box-tcp={rel():.3f} contacts={d.ncon}")
# contacts between fingers and box
names = {m.geom(c.geom1).name + "|" + m.geom(c.geom2).name for c in d.contact[: d.ncon] if "parcel_1" in m.geom(c.geom1).name + m.geom(c.geom2).name}
print("box contacts:", sorted(names))
phases = [("accel fwd", 0.35, 0.0, 600), ("turn", 0.35, 0.7, 600), ("brake", 0.0, 0.0, 300), ("reverse", -0.35, 0.0, 600), ("spin", 0.0, 0.7, 600), ("cruise", 0.35, 0.0, 3000), ("stop", 0.0, 0.0, 300)]
for name, v, w, n in phases:
    for _ in range(n): p.step(v, w)
    print(f"{name:10s} finger={1000*d.qpos[fq]:.1f}mm box-tcp={rel():.3f} box z={d.qpos[box+2]:.3f} base v={p.twist[0]:.2f}")
print("HELD" if rel() < 0.05 else "DROPPED")
