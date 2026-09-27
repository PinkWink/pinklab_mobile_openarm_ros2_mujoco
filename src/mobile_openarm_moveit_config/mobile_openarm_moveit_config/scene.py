"""Keep MoveIt obstacles aligned with MuJoCo despite encoder odometry drift."""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped, PoseArray, Pose
from nav_msgs.msg import Odometry
from shape_msgs.msg import SolidPrimitive
from moveit_msgs.msg import CollisionObject, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene
from std_msgs.msg import String
from mobile_openarm_mujoco.model import load_world, yaw_from_quat


class Scene(Node):
    def __init__(self):
        super().__init__("warehouse_planning_scene")
        self.world = load_world()
        self.truth = None
        self.odom = None
        self.objects = None
        self.pending = None
        # Objects currently attached to the robot (pick-and-place): stop mirroring them
        # from the simulator and remove the world copy so MoveIt keeps one instance.
        self.attached = set()
        self.remove_once = set()
        self.create_subscription(String, "/warehouse_scene/attached", self.set_attached, 1)
        self.create_subscription(
            PoseStamped, "/ground_truth", lambda m: setattr(self, "truth", m.pose), 10
        )
        self.create_subscription(
            Odometry, "/odom", lambda m: setattr(self, "odom", m.pose.pose), 10
        )
        self.create_subscription(
            PoseArray,
            "/warehouse/object_poses",
            lambda m: setattr(self, "objects", m.poses),
            10,
        )
        self.client = self.create_client(ApplyPlanningScene, "/apply_planning_scene")
        self.create_timer(0.5, self.update)

    def set_attached(self, msg):
        names = {n for n in msg.data.split(",") if n}
        self.remove_once |= names - self.attached
        self.attached = names

    def update(self):
        if (
            self.truth is None
            or self.odom is None
            or not self.client.service_is_ready()
        ):
            return
        if self.pending and not self.pending.done():
            return

        def yaw(p):
            return yaw_from_quat(
                [p.orientation.w, p.orientation.x, p.orientation.y, p.orientation.z]
            )

        angle = yaw(self.odom) - yaw(self.truth)
        c, s = math.cos(angle), math.sin(angle)
        dx = (
            self.odom.position.x - c * self.truth.position.x + s * self.truth.position.y
        )
        dy = (
            self.odom.position.y - s * self.truth.position.x - c * self.truth.position.y
        )

        def collision(name, size, pos, q=(1.0, 0.0, 0.0, 0.0)):
            obj = CollisionObject()
            obj.id = name
            obj.header.frame_id = "odom"
            obj.operation = CollisionObject.ADD
            obj.primitives = [
                SolidPrimitive(
                    type=SolidPrimitive.BOX, dimensions=list(map(float, size))
                )
            ]
            pose = Pose()
            pose.position.x = c * pos[0] - s * pos[1] + dx
            pose.position.y = s * pos[0] + c * pos[1] + dy
            pose.position.z = float(pos[2])
            # Compose yaw correction with the simulated object's full orientation.
            cw, sz = math.cos(angle / 2), math.sin(angle / 2)
            w, x, y, z = q
            pose.orientation.w = cw * w - sz * z
            pose.orientation.x = cw * x - sz * y
            pose.orientation.y = cw * y + sz * x
            pose.orientation.z = cw * z + sz * w
            obj.primitive_poses = [pose]
            return obj

        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.world.collision_objects = [
            collision(b["name"], b["size"], b["center"]) for b in self.world["boxes"]
        ]
        scene.world.collision_objects.append(
            collision("warehouse_floor", [15.0, 11.0, 0.1], [0.0, 0.0, -0.05])
        )
        for name in list(self.remove_once):
            removal = CollisionObject()
            removal.id = name
            removal.header.frame_id = "odom"
            removal.operation = CollisionObject.REMOVE
            scene.world.collision_objects.append(removal)
            self.remove_once.discard(name)
        if self.objects and len(self.objects) == len(self.world["objects"]):
            for b, p in zip(self.world["objects"], self.objects):
                if b["name"] in self.attached:
                    continue
                scene.world.collision_objects.append(
                    collision(
                        b["name"],
                        b["size"],
                        [p.position.x, p.position.y, p.position.z],
                        [
                            p.orientation.w,
                            p.orientation.x,
                            p.orientation.y,
                            p.orientation.z,
                        ],
                    )
                )
        self.pending = self.client.call_async(ApplyPlanningScene.Request(scene=scene))


def main():
    rclpy.init()
    node = Scene()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
