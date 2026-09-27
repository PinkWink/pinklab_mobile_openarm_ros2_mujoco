"""Nav2 goals plus ArUco-guided docking with /cmd_vel (blocking, executor-thread safe).

Docking has two parts: a visual servo while the marker is in view (lateral offset and
heading are corrected from the marker pose) and a short odometry-measured straight
segment for the last centimetres where the camera can no longer see the marker.
"""

from collections import deque
import math
import time

from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from nav2_msgs.action import NavigateToPose
from warehouse_interfaces.msg import ArucoMarkerArray

from .moveit_client import SkillError, wait


class NavClient:
    def __init__(self, node, cfg):
        self.node = node
        self.cfg = cfg
        group = ReentrantCallbackGroup()
        self.nav = ActionClient(node, NavigateToPose, "/navigate_to_pose", callback_group=group)
        self.cmd = node.create_publisher(Twist, "/cmd_vel", 10)
        self.odom = None
        self.odom_history = deque(maxlen=200)  # (sim_time, x, y) at 50 Hz = 4 s
        node.create_subscription(Odometry, "/odom", self._odom, 10, callback_group=group)
        self.markers = None
        self.markers_wall = 0.0
        self.markers_odom = None
        node.create_subscription(ArucoMarkerArray, "/vision/markers", self._markers, 10, callback_group=group)
        self.cancel_requested = False

    def _odom(self, msg):
        self.odom = msg
        p = msg.pose.pose.position
        self.odom_history.append((msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9, p.x, p.y))

    def _markers(self, msg):
        self.markers = msg
        self.markers_wall = time.monotonic()
        # Odometry at the *capture* time of the image (header stamp), not at arrival: at
        # 2 FPS the fix can be 0.5 s old, i.e. 5 cm of travel that a blind segment must
        # not drive twice.
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        best = None
        for t_odom, x, y in self.odom_history:
            if best is None or abs(t_odom - stamp) < abs(best[0] - stamp):
                best = (t_odom, x, y)
        self.markers_odom = (best[1], best[2]) if best is not None else (self._odom_xy() if self.odom is not None else None)

    def ready(self, timeout=30.0):
        if not self.nav.wait_for_server(timeout_sec=timeout):
            raise SkillError("Nav2 navigate_to_pose unavailable")

    # --- Nav2 -----------------------------------------------------------
    def go_to(self, x, y, yaw, timeout=180.0, attempts=2):
        """Send a Nav2 goal and wait. A goal that Nav2 aborts (e.g. a planner ack timeout on a
        loaded PC, status 6) is re-sent once; the pose is idempotent so a retry is safe."""
        last = None
        for attempt in range(1, attempts + 1):
            try:
                return self._go_to_once(x, y, yaw, timeout)
            except SkillError as e:
                if self.cancel_requested or "status" not in str(e) or attempt == attempts:
                    raise
                last = e
                self.node.get_logger().warning(f"{e}; retrying Nav2 goal ({attempt}/{attempts - 1})")
                self.stop()
                time.sleep(1.0)
        raise last

    def _go_to_once(self, x, y, yaw, timeout):
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.node.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
        goal.pose.pose.orientation.z, goal.pose.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        handle = wait(self.nav.send_goal_async(goal), 10.0, "navigate_to_pose goal")
        if not handle.accepted:
            raise SkillError("Nav2 rejected the goal")
        future = handle.get_result_async()
        end = time.monotonic() + timeout
        while not future.done():
            if self.cancel_requested or time.monotonic() > end:
                handle.cancel_goal_async()
                raise SkillError("navigation cancelled" if self.cancel_requested else "navigation timed out")
            time.sleep(0.1)
        status = future.result().status
        if status != GoalStatus.STATUS_SUCCEEDED:
            raise SkillError(f"Nav2 finished with status {status}")

    # --- low-level motion ----------------------------------------------
    def _publish(self, v, w):
        msg = Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.cmd.publish(msg)

    def stop(self):
        for _ in range(3):
            self._publish(0.0, 0.0)
            time.sleep(0.05)

    def _odom_xy(self):
        if self.odom is None:
            raise SkillError("no /odom")
        p = self.odom.pose.pose.position
        return p.x, p.y

    def marker(self, marker_id, max_age=1.5):
        """Latest (dx, dy, normal_yaw, distance) of a marker in base_footprint, or None."""
        if self.markers is None or time.monotonic() - self.markers_wall > max_age:
            return None
        for m in self.markers.markers:
            if m.id == marker_id:
                return m.pose.position.x, m.pose.position.y, m.normal_yaw, m.distance
        return None

    def fixes(self, ids, max_age=1.5):
        """{id: (dx, dy, normal_yaw, distance)} for the currently visible markers among ids."""
        out = {}
        for marker_id in ids:
            m = self.marker(marker_id, max_age)
            if m is not None:
                out[marker_id] = m
        return out

    @staticmethod
    def geometry(fixes, offsets):
        """Station axis geometry from one or two marker fixes.

        offsets: {id: lateral offset of the marker from the station axis (m, +left)}.
        Returns (along, side, turn, origin, u):
          along  distance from base_footprint to the marker plane along its normal
          side   base offset from the station axis (positive = axis appears to the left)
          turn   heading change (rad, +left) that aligns the base with the axis
          origin axis origin (table centre on the marker plane) in base_footprint (x, y)
          u      unit vector of increasing lateral offset in base_footprint
        With two markers the direction comes from the line between them (robust);
        with one it falls back to that marker's estimated normal (noisy at low resolution).
        """
        ids = [i for i in offsets if i in fixes]
        if not ids:
            raise SkillError("no marker fix")
        pts = {i: (fixes[i][0], fixes[i][1]) for i in ids}
        if len(ids) >= 2:
            a, b = sorted(ids, key=lambda i: offsets[i])[:2]
            ux, uy = pts[b][0] - pts[a][0], pts[b][1] - pts[a][1]
            norm = math.hypot(ux, uy)
            if norm < 1e-3:
                raise SkillError("marker pair degenerate")
            ux, uy = ux / norm, uy / norm
            scale = norm / (offsets[b] - offsets[a])
            ox, oy = pts[a][0] - ux * offsets[a] * scale, pts[a][1] - uy * offsets[a] * scale
        else:
            i = ids[0]
            psi = fixes[i][2]
            nx, ny = math.cos(psi), math.sin(psi)
            ux, uy = ny, -nx
            ox, oy = pts[i][0] - ux * offsets[i], pts[i][1] - uy * offsets[i]
        nx, ny = -uy, ux  # plane normal pointing toward the robot
        h = math.atan2(ny, -nx)
        along = -(ox * nx + oy * ny)
        side = ox * ux + oy * uy
        return along, side, -h, (ox, oy), (ux, uy)

    def settle(self, seconds=1.0):
        """Stop and wait so that the next camera fix is taken from a stationary robot."""
        self.stop()
        time.sleep(seconds)

    def wait_markers(self, ids, timeout=6.0, search=True, need=2, max_age=0.7):
        """Fresh fixes for at least `need` of the ids (or any, if need > visible); sweeps to find them.

        Only fixes younger than max_age are accepted so that a stale image taken while
        Nav2 was still turning is never combined with the current robot state.
        """
        need = min(need, len(ids))
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            f = self.fixes(ids, max_age=max_age)
            if len(f) >= need:
                return f
            time.sleep(0.1)
        if not search:
            raise SkillError(f"ArUco markers {ids} not visible")
        best = {}
        for w, seconds in ((0.25, 2.5), (-0.25, 5.0), (0.25, 2.5)):
            start = time.monotonic()
            while time.monotonic() - start < seconds:
                f = self.fixes(ids)
                if len(f) >= need:
                    self.stop()
                    return f
                if len(f) > len(best):
                    best = f
                self._publish(0.0, w)
                time.sleep(0.1)
        self.stop()
        if best:
            return best
        raise SkillError(f"ArUco markers {ids} not found after a heading sweep")

    def dock(self, offsets, target_dx, target_side, feedback=None):
        """Servo until the marker plane is target_dx ahead and the base sits target_side off the axis."""
        d = self.cfg["dock"]
        ids = list(offsets)
        visual_end = float(d["visual_end_dx"])
        end = time.monotonic() + float(d["timeout_s"])
        last = None
        last_odom = None          # odometry at the capture time of the last *pair* fix
        while time.monotonic() < end:
            if self.cancel_requested:
                self.stop()
                raise SkillError("docking cancelled")
            f = self.fixes(ids, max_age=0.8)
            if len(f) < 2:
                # A single marker (the outer one has left the view just before visual_end) gives a
                # noisy normal at 320x240: +-20 deg, i.e. a 12 cm side jump or a 5 cm range error that
                # the blind segment would trust. Only pair fixes count; with one marker or none we go
                # blind from the last pair fix (its odometry stamp bounds the distance driven since).
                if last is not None and last[0] <= visual_end + 0.15:
                    break
                self._publish(0.0, 0.0)
                time.sleep(0.1)
                continue
            along, side, turn, _, _ = self.geometry(f, offsets)
            if last is not None and abs(side - last[1]) > 0.08:
                side = last[1]        # outlier pair fix (mis-detected corner): keep the previous lateral estimate
            last = (along, side, turn)
            last_odom = self.markers_odom
            if along <= visual_end:
                break
            lateral = side - float(target_side)
            v = min(float(d["max_speed"]), max(0.03, float(d["gain"]) * (along - float(target_dx))))
            w = float(d["lateral_gain"]) * lateral / max(along, 0.3) + float(d["heading_gain"]) * turn
            w = max(-0.3, min(0.3, w))
            self._publish(v, w)
            if feedback:
                feedback(f"visual dock: along={along:.3f} side={side:+.3f} lateral={lateral:+.3f} turn={math.degrees(turn):+.1f}deg")
            time.sleep(0.1)
        else:
            self.stop()
            raise SkillError("docking timed out while the markers were visible")
        if last is None:
            self.stop()
            raise SkillError("markers never seen during docking")
        self.stop()
        along, side, turn = last
        travelled = 0.0
        if last_odom is not None:
            x, y = self._odom_xy()
            travelled = math.hypot(x - last_odom[0], y - last_odom[1])
        if abs(turn) > 0.02:
            self.turn(turn)
        remaining = along - travelled - float(target_dx)
        if feedback:
            feedback(f"blind segment {remaining:+.3f} m (last fix along={along:.3f}, side={side:+.3f}, driven since fix {travelled:.3f})")
        self.drive(remaining, speed=float(d["blind_speed"]))
        return float(target_dx), side - float(target_side)

    def sidestep(self, lateral, speed=0.08):
        """Move sideways by `lateral` (m, +left) with turn-drive-turn using wheel odometry."""
        sign = 1.0 if lateral >= 0 else -1.0
        self.turn(sign * math.pi / 2)
        self.drive(abs(lateral), speed=speed)
        self.turn(-sign * math.pi / 2)

    def turn(self, angle, speed=0.25):
        """Rotate in place by angle (rad, +left) measured with wheel odometry."""
        if self.odom is None:
            raise SkillError("no /odom")
        q = self.odom.pose.pose.orientation
        yaw0 = 2 * math.atan2(q.z, q.w)
        sign = 1.0 if angle >= 0 else -1.0
        deadline = time.monotonic() + abs(angle) / speed + 3.0
        while time.monotonic() < deadline:
            q = self.odom.pose.pose.orientation
            yaw = 2 * math.atan2(q.z, q.w)
            done = math.atan2(math.sin(yaw - yaw0), math.cos(yaw - yaw0))
            if sign * done >= abs(angle) - 0.01:
                break
            self._publish(0.0, sign * speed)
            time.sleep(0.05)
        self.stop()

    def drive(self, distance, speed=0.08):
        """Straight drive measured with wheel odometry (negative = backward)."""
        if abs(distance) < 0.005:
            return
        sign = 1.0 if distance >= 0 else -1.0
        x0, y0 = self._odom_xy()
        deadline = time.monotonic() + abs(distance) / speed + 5.0
        while time.monotonic() < deadline:
            if self.cancel_requested:
                break
            x, y = self._odom_xy()
            travelled = math.hypot(x - x0, y - y0)
            if travelled >= abs(distance) - 0.004:
                break
            v = speed if abs(distance) - travelled > 0.05 else max(0.03, speed * 0.4)
            self._publish(sign * v, 0.0)
            time.sleep(0.05)
        self.stop()
