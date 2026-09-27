"""URDF-derived free-base MuJoCo model, encoder odometry, and ray-cast lidar."""

from pathlib import Path
import hashlib
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
import yaml
from ament_index_python.packages import get_package_share_directory
from mobile_openarm_description.model import expand_urdf, resolve_mesh


def share(package):
    return Path(get_package_share_directory(package))


def vector(values):
    return " ".join(f"{float(x):.12g}" for x in values)


def numbers(value):
    return np.array([float(x) for x in value.split()])


def origin(element):
    tag = element.find("origin")
    return {
        "pos": tag.get("xyz", "0 0 0") if tag is not None else "0 0 0",
        "euler": tag.get("rpy", "0 0 0") if tag is not None else "0 0 0",
    }


def load_settings(path=None):
    return yaml.safe_load(
        Path(path or share("mobile_openarm_mujoco") / "config/mujoco.yaml").read_text()
    )


def load_world(path=None):
    return yaml.safe_load(
        Path(
            path or share("mobile_openarm_mujoco") / "worlds/warehouse.yaml"
        ).read_text()
    )


def initial_positions():
    return yaml.safe_load(
        (
            share("mobile_openarm_description") / "config/initial_positions.yaml"
        ).read_text()
    )


def drive_poses():
    """Arm poses in which the base may drive (transport, carry ...)."""
    path = share("mobile_openarm_description") / "config/drive_poses.yaml"
    if not path.is_file():
        return {"transport": {k: v for k, v in initial_positions().items() if "finger" not in k}}
    return yaml.safe_load(path.read_text())


def camera_settings():
    return yaml.safe_load(
        (share("mobile_openarm_description") / "config/cameras.yaml").read_text()
    )


def rotation(rpy):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = (
        math.cos(r),
        math.sin(r),
        math.cos(p),
        math.sin(p),
        math.cos(y),
        math.sin(y),
    )
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ]
    )


def build_model(
    output_dir, urdf=None, config_file=None, world_file=None, actors_file=None
):
    """Write warehouse.xml. actors_file: None = default actors.yaml, "none" = no actors."""
    import trimesh
    from .actors import load_actors, add_actors
    from .markers import add_markers

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    robot = ET.fromstring(urdf or expand_urdf())
    ET.ElementTree(robot).write(out / "mobile_openarm.urdf", encoding="unicode")
    settings, warehouse = load_settings(config_file), load_world(world_file)
    actors = load_actors(actors_file)
    cameras = camera_settings()
    camera_frames = {name + "_optical_frame": name for name in cameras["cameras"]}
    links = {x.get("name"): x for x in robot.findall("link")}
    joints = robot.findall("joint")
    children = {}
    for j in joints:
        children.setdefault(j.find("parent").get("link"), []).append(j)
    root = ET.Element("mujoco", model="mobile_openarm_warehouse")
    ET.SubElement(
        root,
        "compiler",
        angle="radian",
        # URDF RPY rotates about fixed axes: Rz(yaw) @ Ry(pitch) @ Rx(roll).
        eulerseq="XYZ",
        autolimits="true",
        inertiafromgeom="false",
        fusestatic="false",
    )
    p = settings["physics"]
    ET.SubElement(
        root,
        "option",
        timestep=str(p["timestep"]),
        gravity=vector(p["gravity"]),
        integrator=p["integrator"],
        iterations=str(p["iterations"]),
        noslip_iterations=str(p.get("noslip_iterations", 0)),
        cone="elliptic",
    )
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1600", offheight="1000")
    # MuJoCo znear/zfar are multiples of model.stat.extent. Set both explicitly
    # so a 15 m warehouse does not clip away objects near the wrist cameras.
    extent = max(warehouse["size"])
    ET.SubElement(root, "statistic", extent=str(extent))
    ET.SubElement(
        visual,
        "map",
        znear=str(cameras["render"]["near_m"] / extent),
        zfar=str(cameras["render"]["far_m"] / extent),
    )
    defaults = ET.SubElement(root, "default")
    ET.SubElement(
        defaults,
        "geom",
        solref="0.008 1",
        solimp="0.95 0.99 0.001",
        friction="0.8 0.005 0.0001",
        condim="4",
    )
    asset = ET.SubElement(root, "asset")
    ET.SubElement(
        asset,
        "texture",
        name="floor_texture",
        type="2d",
        builtin="checker",
        rgb1="0.24 0.29 0.32",
        rgb2="0.3 0.35 0.38",
        width="512",
        height="512",
    )
    ET.SubElement(
        asset,
        "material",
        name="floor_material",
        texture="floor_texture",
        texrepeat="15 11",
    )
    world = ET.SubElement(root, "worldbody")
    for x in [-5, 0, 5]:
        ET.SubElement(
            world,
            "light",
            pos=f"{x} 0 5",
            dir="0 0 -1",
            diffuse="0.7 0.7 0.7",
            directional="true",
        )
    ET.SubElement(
        world,
        "geom",
        name="floor",
        type="plane",
        size="7.7 5.7 0.1",
        material="floor_material",
        group="0",
        contype="1",
        conaffinity="3",
    )
    for b in warehouse["boxes"]:
        ET.SubElement(
            world,
            "geom",
            name=b["name"],
            type="box",
            pos=vector(b["center"]),
            size=vector(np.array(b["size"]) / 2),
            rgba=vector(b["rgba"]),
            group="0",
            contype="1",
            conaffinity="3",
        )
    # Aisle paint is visual only, so it cannot affect lidar or contacts.
    for x in [-4.0, -1.1, 4.0]:
        ET.SubElement(
            world,
            "geom",
            type="box",
            pos=f"{x} 0 0.001",
            size=".025 5.3 .001",
            rgba="0.95 0.75 0.18 1",
            contype="0",
            conaffinity="0",
            group="2",
        )
    for obj in warehouse["objects"]:
        body = ET.SubElement(world, "body", name=obj["name"], pos=vector(obj["center"]))
        ET.SubElement(body, "freejoint", name=obj["name"] + "_free")
        # Explicit box inertia because URDF robot inertias must not be inferred from geometry.
        x, y, z = obj["size"]
        mass = obj["mass"]
        ET.SubElement(
            body,
            "inertial",
            pos="0 0 0",
            mass=str(mass),
            diaginertia=vector(
                mass / 12 * np.array([y * y + z * z, x * x + z * z, x * x + y * y])
            ),
        )
        ET.SubElement(
            body,
            "geom",
            name=obj["name"] + "_geom",
            type="box",
            size=vector(np.array(obj["size"]) / 2),
            rgba=vector(obj["rgba"]),
            group="0",
            contype="1",
            conaffinity="3",
            friction="1.2 0.01 0.001",
        )
    # People and props are mocap bodies: lidar- and camera-visible, never in the static map.
    add_actors(world, actors)
    add_markers(asset, world, warehouse.get("markers", []), out)
    materials = {
        m.get("name"): m.find("color").get("rgba")
        for m in robot.findall("material")
        if m.find("color") is not None
    }
    meshes = {}

    def geometry(body, element, is_visual, name, index):
        geom = element.find("geometry")[0]
        attrs = origin(element)
        attrs.update(
            name=f"{name}_{'visual' if is_visual else 'collision'}_{index}",
            group="2" if is_visual else "1",
            contype="0" if is_visual else "2",
            conaffinity="0" if is_visual else "3",
            rgba="0.72 0.76 0.8 1" if is_visual else "0.5 0.5 0.5 0",
        )
        mat = element.find("material")
        if is_visual and mat is not None:
            color = mat.find("color")
            attrs["rgba"] = (
                color.get("rgba")
                if color is not None
                else materials.get(mat.get("name"), attrs["rgba"])
            )
        if geom.tag == "mesh":
            path = resolve_mesh(geom.get("filename"))
            scale = numbers(geom.get("scale", "1 1 1"))
            key = (str(path), tuple(scale))
            if key not in meshes:
                mesh_name = "mesh_" + str(len(meshes))
                # Bake signed scale into vertices. Reflected OpenArm meshes otherwise
                # produce flipped normals or inconsistent inertial geometry.
                digest = hashlib.sha256(
                    (str(path) + str(tuple(scale))).encode()
                ).hexdigest()[:14]
                converted = out / f"{path.stem}_{digest}.obj"
                if (
                    not converted.exists()
                    or converted.stat().st_mtime < path.stat().st_mtime
                ):
                    mesh = trimesh.load(str(path), force="scene").to_geometry()
                    mesh.apply_scale(scale)
                    mesh.export(str(converted))
                ET.SubElement(
                    asset, "mesh", name=mesh_name, file=str(converted.resolve())
                )
                meshes[key] = mesh_name
            attrs.update(type="mesh", mesh=meshes[key])
        elif geom.tag == "box":
            attrs.update(type="box", size=vector(numbers(geom.get("size")) / 2))
        elif geom.tag == "sphere":
            attrs.update(type="sphere", size=geom.get("radius"))
        elif geom.tag == "cylinder":
            attrs.update(
                type="cylinder",
                size=vector([float(geom.get("radius")), float(geom.get("length")) / 2]),
            )
        else:
            raise ValueError(geom.tag)
        if not is_visual and name.endswith("_caster"):
            attrs.update(friction="0.002 0.00001 0.00001", priority="1", condim="3")
        if not is_visual and name in ["left_wheel", "right_wheel"]:
            attrs.update(friction="1.2 0.005 0.0001", priority="1")
            if settings["motors"].get("contact_shape") == "ellipsoid":
                r = float(geom.get("radius"))
                half = float(geom.get("length")) / 2
                attrs.update(type="ellipsoid", size=vector([r, r, half]))
        ET.SubElement(body, "geom", **attrs)

    def link(parent, name, joint=None):
        attrs = {"name": name}
        attrs.update(
            origin(joint)
            if joint is not None
            else {"pos": vector(settings["spawn"]["position"])}
        )
        body = ET.SubElement(parent, "body", **attrs)
        if joint is None:
            ET.SubElement(body, "freejoint", name="floating_base")
        elif joint.get("type") != "fixed":
            typ = joint.get("type")
            a = {
                "name": joint.get("name"),
                "type": "slide" if typ == "prismatic" else "hinge",
                "axis": joint.find("axis").get("xyz"),
                "damping": "0.1",
                "armature": "0.01" if typ != "prismatic" else "0.001",
            }
            if typ in ["revolute", "prismatic"]:
                lim = joint.find("limit")
                a["range"] = lim.get("lower") + " " + lim.get("upper")
            ET.SubElement(body, "joint", **a)
        source = links[name]
        inertial = source.find("inertial")
        if inertial is not None:
            I = inertial.find("inertia")
            vals = [float(I.get(k)) for k in ["ixx", "iyy", "izz", "ixy", "ixz", "iyz"]]
            xx, yy, zz, xy, xz, yz = vals
            matrix = np.array([[xx, xy, xz], [xy, yy, yz], [xz, yz, zz]])
            R = rotation(numbers(origin(inertial)["euler"]))
            matrix = R @ matrix @ R.T
            ET.SubElement(
                body,
                "inertial",
                pos=origin(inertial)["pos"],
                mass=inertial.find("mass").get("value"),
                fullinertia=vector(
                    [
                        matrix[0, 0],
                        matrix[1, 1],
                        matrix[2, 2],
                        matrix[0, 1],
                        matrix[0, 2],
                        matrix[1, 2],
                    ]
                ),
            )
        for v in [False, True]:
            for i, e in enumerate(source.findall("visual" if v else "collision")):
                geometry(body, e, v, name, i)
        if name == "laser_link":
            ET.SubElement(body, "site", name="lidar", size=".005", rgba="1 0 0 1")
        if name in camera_frames:
            camera_name = camera_frames[name]
            # Optical +Z forward/+Y down -> MuJoCo -Z forward/+Y up.
            ET.SubElement(
                body,
                "camera",
                name=camera_name,
                mode="fixed",
                quat="0 1 0 0",
                fovy=str(cameras["cameras"][camera_name]["fovy"]),
            )
        for child in children.get(name, []):
            link(body, child.find("child").get("link"), child)

    link(world, "base_footprint")
    contacts = ET.SubElement(root, "contact")
    # Skip contacts inside rigid assemblies and between adjacent articulated links.
    exclusions = set()
    pairs = json.loads(
        (
            share("mobile_openarm_description") / "config/collision_exclusions.json"
        ).read_text()
    )
    for pair in pairs + settings.get("convex_contact_exclusions", []):
        names = tuple(sorted(pair))
        if names not in exclusions and all(n in links for n in names):
            ET.SubElement(contacts, "exclude", body1=names[0], body2=names[1])
            exclusions.add(names)
    equality = ET.SubElement(root, "equality")
    for j in joints:
        mimic = j.find("mimic")
        if mimic is not None:
            ET.SubElement(
                equality,
                "joint",
                joint1=j.get("name"),
                joint2=mimic.get("joint"),
                polycoef=f"{mimic.get('offset', '0')} {mimic.get('multiplier', '1')} 0 0 0",
                solref="0.004 1",
            )
    actuators = ET.SubElement(root, "actuator")
    motors = settings["motors"]
    for side in ["left", "right"]:
        ET.SubElement(
            actuators,
            "velocity",
            name=side + "_motor",
            joint=side + "_wheel_joint",
            kv=str(motors["velocity_gain"]),
            ctrlrange=vector([-motors["max_speed"], motors["max_speed"]]),
            forcerange=vector([-motors["max_torque"], motors["max_torque"]]),
        )
    for j in joints:
        if (
            j.get("type") not in ["revolute", "prismatic"]
            or j.find("mimic") is not None
        ):
            continue
        lim = j.find("limit")
        cfg = settings["gripper" if j.get("type") == "prismatic" else "arm"]
        force = min(
            float(lim.get("effort")), cfg.get("max_force", float(lim.get("effort")))
        )
        ET.SubElement(
            actuators,
            "position",
            name=j.get("name") + "_position",
            joint=j.get("name"),
            kp=str(cfg["kp"]),
            kv=str(cfg["kv"]),
            ctrlrange=lim.get("lower") + " " + lim.get("upper"),
            forcerange=vector([-force, force]),
        )
    ET.indent(root)
    path = out / "warehouse.xml"
    ET.ElementTree(root).write(path, encoding="unicode")
    return path


def yaw_from_quat(q):
    w, x, y, z = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


class Physics:
    def __init__(self, model_path, config_file=None):
        import mujoco

        self.mj = mujoco
        self.settings = load_settings(config_file)
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        self.data = mujoco.MjData(self.model)
        self.bridge_period = 1 / self.settings["rates"]["bridge_hz"]
        self.radius = float(self.model.geom("left_wheel_collision_0").size[0])
        self.track = float(
            abs(
                self.model.body("left_wheel").pos[1]
                - self.model.body("right_wheel").pos[1]
            )
        )
        self.wheel_q = [
            self.model.joint(s + "_wheel_joint").qposadr[0] for s in ["left", "right"]
        ]
        self.wheel_ctrl = [
            self.model.actuator(s + "_motor").id for s in ["left", "right"]
        ]
        self.base_q = self.model.joint("floating_base").qposadr[0]
        self.joint_names = [
            self.model.joint(i).name
            for i in range(self.model.njnt)
            if self.model.jnt_type[i] in (2, 3)
        ]
        self.q_indices = [self.model.joint(n).qposadr[0] for n in self.joint_names]
        self.v_indices = [self.model.joint(n).dofadr[0] for n in self.joint_names]
        self.targets = initial_positions()
        self.transport_names = [n for n in self.targets if "finger" not in n]
        self.transport_values = np.array(
            [self.targets[n] for n in self.transport_names]
        )
        # Each arm may be in any drive pose independently (one arm carrying, one stowed).
        self.drive_poses = {
            name: np.array([pose[n] for n in self.transport_names])
            for name, pose in drive_poses().items()
        }
        for name, value in self.targets.items():
            self.data.qpos[self.model.joint(name).qposadr[0]] = value
            self.data.ctrl[self.model.actuator(name + "_position").id] = value
            if "finger_joint1" in name:
                self.data.qpos[
                    self.model.joint(name.replace("joint1", "joint2")).qposadr[0]
                ] = value
        self.odom = np.zeros(3)
        self.twist = np.zeros(2)
        self.command = np.zeros(2)
        self.angles = np.linspace(
            -math.pi, math.pi, self.settings["lidar"]["samples"], endpoint=False
        )
        self.rays = np.column_stack(
            [np.cos(self.angles), np.sin(self.angles), np.zeros(len(self.angles))]
        )
        self.ray_group = np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8)
        self.lidar_id = self.model.site("lidar").id
        mujoco.mj_forward(self.model, self.data)

    def positions(self, names):
        return np.array([self.data.qpos[self.model.joint(n).qposadr[0]] for n in names])

    def set_targets(self, names, values):
        for n, v in zip(names, values):
            self.targets[n] = float(v)
            self.data.ctrl[self.model.actuator(n + "_position").id] = v

    def hold(self, names):
        self.set_targets(names, self.positions(names))

    def transport_ready(self):
        """True when every arm is in one of the drive poses (transport, ready ...)."""
        q = self.positions(self.transport_names)
        tol = self.settings["control"]["transport_tolerance"]
        for side in ("left", "right"):
            idx = [i for i, n in enumerate(self.transport_names) if f"_{side}_" in n]
            if not any(
                np.max(np.abs(q[idx] - pose[idx])) < tol for pose in self.drive_poses.values()
            ):
                return False
        return True

    def step(self, linear=0.0, angular=0.0, steps=None):
        steps = steps or round(self.bridge_period / self.model.opt.timestep)
        dt = steps * self.model.opt.timestep
        cfg = self.settings["control"]
        change = np.array([cfg["acceleration"], cfg["angular_acceleration"]]) * dt
        self.command += np.clip(
            np.array([linear, angular]) - self.command, -change, change
        )
        v, w = self.command
        wheel = np.array([v - w * self.track / 2, v + w * self.track / 2]) / self.radius
        self.data.ctrl[self.wheel_ctrl] = np.clip(
            wheel,
            -self.settings["motors"]["max_speed"],
            self.settings["motors"]["max_speed"],
        )
        before = self.data.qpos[self.wheel_q].copy()
        if self.settings["arm"].get("bias_compensation", True):
            for name in self.transport_names:
                index = self.model.joint(name).dofadr[0]
                self.data.qfrc_applied[index] = self.data.qfrc_bias[index]
        self.mj.mj_step(self.model, self.data, nstep=steps)
        dl, dr = (self.data.qpos[self.wheel_q] - before) * self.radius
        ds, da = (dl + dr) / 2, (dr - dl) / self.track
        theta = self.odom[2] + da / 2
        self.odom += [ds * math.cos(theta), ds * math.sin(theta), da]
        self.twist[:] = [ds / dt, da / dt]

    def scan(self):
        self.mj.mj_forward(self.model, self.data)
        rays = np.ascontiguousarray(
            self.rays @ self.data.site_xmat[self.lidar_id].reshape(3, 3).T
        )
        distances = np.empty(len(rays))
        ids = np.empty(len(rays), dtype=np.int32)
        cfg = self.settings["lidar"]
        self.mj.mj_multiRay(
            self.model,
            self.data,
            self.data.site_xpos[self.lidar_id],
            rays.ravel(),
            self.ray_group,
            True,
            -1,
            ids,
            distances,
            None,
            len(rays),
            cfg["range_max"],
        )
        distances[(distances < cfg["range_min"]) | (distances > cfg["range_max"])] = (
            np.inf
        )
        return distances

    def pose(self):
        q = self.data.qpos[self.base_q : self.base_q + 7]
        return np.array([q[0], q[1], yaw_from_quat(q[3:7])])

    def set_base_pose(self, x, y, yaw):
        """Teleport the base (planar pose in the world frame) before the first step: lessons that
        start at a table do not have to drive there first. Odometry still starts at (0, 0, 0)."""
        q = self.data.qpos
        q[self.base_q], q[self.base_q + 1] = float(x), float(y)
        q[self.base_q + 3 : self.base_q + 7] = [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]
        self.data.qvel[:] = 0.0
        self.mj.mj_forward(self.model, self.data)
