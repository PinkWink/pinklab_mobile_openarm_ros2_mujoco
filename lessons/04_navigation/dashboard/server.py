"""Web dashboard for the patrol demo: mission, map, poses, cameras, detections in one browser page.

    python lessons/04_navigation/dashboard/server.py            # http://localhost:8080
    python lessons/04_navigation/dashboard/server.py --port 8090 --host 0.0.0.0

One process, two threads:
  * ROS thread  - an rclpy node subscribes to the robot topics and keeps only the latest values.
  * Flask thread - serves the page, a Server-Sent Events stream of that state (5 Hz), the map as PNG,
    MJPEG camera streams read from frame_tap.py's shared-memory JPEGs, and POST /api/command.
The browser never talks ROS; the server never renders anything but the map PNG.
"""
import argparse
import json
import math
import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from flask import Flask, Response, jsonify, request, send_from_directory
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Odometry, Path as NavPath
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
from warehouse_interfaces.msg import ActorStateArray, Detection3DArray

HERE = Path(__file__).parent
FRAMES = Path(os.environ.get("DASHBOARD_FRAMES", "/dev/shm/mobile_openarm_dashboard"))   # written by frame_tap.py
LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class RobotState(Node):
    """Latest robot state, written by ROS callbacks and read by Flask (guarded by one lock)."""

    def __init__(self):
        super().__init__("patrol_dashboard", parameter_overrides=[rclpy.Parameter("use_sim_time", value=True)])
        self.lock = threading.Lock()
        self.s = dict(truth=None, amcl=None, amcl_cov=None, odom=None, twist=[0.0, 0.0], plan=[], scan=[], actors=[],
                      detections={}, patrol=None, trail=[])
        self.map_png, self.map_meta = None, None
        self.wall0 = self.sim0 = None
        self.tf = Buffer()
        TransformListener(self.tf, self)
        self.cmd = self.create_publisher(String, "/patrol/command", 10)
        self.create_subscription(PoseStamped, "/ground_truth", self.on_truth, 10)
        self.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", self.on_amcl, LATCHED)
        self.create_subscription(Odometry, "/odom", self.on_odom, 10)
        self.create_subscription(NavPath, "/plan", self.on_plan, 10)
        self.create_subscription(LaserScan, "/scan", self.on_scan, qos_profile_sensor_data)
        self.create_subscription(OccupancyGrid, "/map", self.on_map, LATCHED)
        self.create_subscription(ActorStateArray, "/warehouse/actor_states", self.on_actors, 10)
        self.create_subscription(Detection3DArray, "/vision/detections", self.on_detections, 10)
        self.create_subscription(String, "/patrol/status", self.on_patrol, LATCHED)

    def put(self, **kw):
        with self.lock:
            self.s.update(kw)

    def on_truth(self, m):
        p = [round(m.pose.position.x, 3), round(m.pose.position.y, 3), round(yaw_of(m.pose.orientation), 3)]
        with self.lock:
            self.s["truth"] = p
            trail = self.s["trail"]
            if not trail or math.hypot(p[0] - trail[-1][0], p[1] - trail[-1][1]) > 0.05:
                trail.append(p[:2])
                del trail[:-2000]

    def on_amcl(self, m):
        p = m.pose.pose
        c = m.pose.covariance
        self.put(amcl=[round(p.position.x, 3), round(p.position.y, 3), round(yaw_of(p.orientation), 3)],
                 amcl_cov=[round(math.sqrt(max(c[0], 0)), 3), round(math.sqrt(max(c[7], 0)), 3), round(math.degrees(math.sqrt(max(c[35], 0))), 2)])

    def on_odom(self, m):
        p = m.pose.pose
        self.put(odom=[round(p.position.x, 3), round(p.position.y, 3), round(yaw_of(p.orientation), 3)],
                 twist=[round(m.twist.twist.linear.x, 3), round(m.twist.twist.angular.z, 3)])

    def on_plan(self, m):
        pts = [[round(p.pose.position.x, 2), round(p.pose.position.y, 2)] for p in m.poses[::4]]
        self.put(plan=pts)

    def on_scan(self, m):
        """Scan points in the map frame via TF (map → laser_link at the scan's stamp)."""
        try:
            t = self.tf.lookup_transform("map", m.header.frame_id, Time.from_msg(m.header.stamp))
        except Exception:
            return
        q, o = t.transform.rotation, t.transform.translation
        yaw = yaw_of(q)
        r = np.asarray(m.ranges)[::2]
        a = m.angle_min + np.arange(len(m.ranges))[::2] * m.angle_increment
        ok = np.isfinite(r)
        x = o.x + r[ok] * np.cos(a[ok] + yaw)
        y = o.y + r[ok] * np.sin(a[ok] + yaw)
        self.put(scan=np.round(np.c_[x, y], 2).tolist())

    def on_map(self, m):
        h, w = m.info.height, m.info.width
        d = np.array(m.data, dtype=np.int16).reshape(h, w)
        img = np.where(d < 0, 205, np.where(d >= 65, 0, 254)).astype(np.uint8)[::-1]   # row 0 = bottom → PNG top
        ok, png = cv2.imencode(".png", img)
        with self.lock:
            self.map_png = png.tobytes()
            self.map_meta = dict(resolution=m.info.resolution, width=w, height=h,
                                 origin=[m.info.origin.position.x, m.info.origin.position.y], version=time.time())

    def on_actors(self, m):
        people = []
        for a in m.actors:
            if a.kind != "person":
                continue
            attrs = {kv.key: kv.value for kv in a.attributes}
            people.append(dict(name=a.name, x=round(a.pose.position.x, 2), y=round(a.pose.position.y, 2),
                               moving=a.moving, helmet=attrs.get("helmet") == "true"))
        self.put(actors=people)

    def on_detections(self, m):
        by_cam = {}
        for d in m.detections:
            attrs = {kv.key: kv.value for kv in d.attributes}
            by_cam.setdefault(d.camera, []).append(dict(label=d.label, bbox=[round(float(v), 1) for v in d.bbox_xyxy], attrs=attrs,
                                                        pos=[round(d.position.point.x, 2), round(d.position.point.y, 2)] if d.has_position else None))
        now = time.time()
        with self.lock:
            for cam, dets in by_cam.items():
                self.s["detections"][cam] = dict(t=now, items=dets)
            for cam in list(self.s["detections"]):
                if cam not in by_cam and now - self.s["detections"][cam]["t"] > 1.5:
                    self.s["detections"][cam] = dict(t=now, items=[])

    def on_patrol(self, m):
        self.put(patrol=json.loads(m.data))

    def snapshot(self):
        sim = self.get_clock().now().nanoseconds * 1e-9
        wall = time.time()
        if self.wall0 is None and sim > 0:
            self.wall0, self.sim0 = wall, sim
        rtf = (sim - self.sim0) / (wall - self.wall0) if self.wall0 and wall - self.wall0 > 1 else None
        with self.lock:
            s = dict(self.s)
            s["detections"] = {k: v["items"] for k, v in self.s["detections"].items()}
        s.update(sim_time=round(sim, 2), rtf=None if rtf is None else round(rtf, 2), map_version=self.map_meta and self.map_meta["version"])
        return s


def make_app(state):
    app = Flask(__name__, static_folder=str(HERE / "static"), static_url_path="/static")

    @app.get("/")
    def index():
        return send_from_directory(HERE / "static", "index.html")

    @app.get("/api/state")
    def api_state():
        return jsonify(state.snapshot())

    @app.get("/api/stream")
    def api_stream():
        """Server-Sent Events: one JSON snapshot every 0.2 s over a single long HTTP response."""
        def gen():
            while True:
                yield f"data: {json.dumps(state.snapshot(), ensure_ascii=False)}\n\n"
                time.sleep(0.2)
        return Response(gen(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})

    @app.get("/api/map")
    def api_map():
        return jsonify(state.map_meta or {})

    @app.get("/api/map.png")
    def api_map_png():
        if state.map_png is None:
            return "no /map yet", 404
        return Response(state.map_png, mimetype="image/png", headers={"Cache-Control": "no-cache"})

    @app.get("/api/cameras")
    def api_cameras():
        meta = FRAMES / "meta.json"
        return jsonify(json.loads(meta.read_text()) if meta.exists() else {})

    @app.get("/camera/<name>.mjpg")
    def camera(name):
        """MJPEG: multipart/x-mixed-replace, a new JPEG part whenever frame_tap.py replaces the file."""
        path = FRAMES / f"{Path(name).name}.jpg"

        def gen():
            last = None
            while True:
                try:
                    mtime = path.stat().st_mtime_ns
                    if mtime != last:
                        last = mtime
                        jpg = path.read_bytes()
                        yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
                except FileNotFoundError:
                    pass
                time.sleep(0.05)
        return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.post("/api/command")
    def api_command():
        cmd = (request.get_json(silent=True) or {}).get("cmd", "")
        if cmd not in ("start", "cancel"):
            return jsonify(ok=False, error="cmd must be start or cancel"), 400
        state.cmd.publish(String(data=cmd))
        return jsonify(ok=True, cmd=cmd)

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open it to other PCs on the network")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)     # Ctrl+C goes to Flask, not rclpy
    state = RobotState()
    executor = SingleThreadedExecutor()
    executor.add_node(state)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    print(f"dashboard: http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}   (camera frames: {FRAMES})", flush=True)
    try:
        make_app(state).run(host=a.host, port=a.port, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:                                                          # stop the ROS thread before the interpreter exits
        executor.shutdown()
        spinner.join(timeout=2)
        state.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
