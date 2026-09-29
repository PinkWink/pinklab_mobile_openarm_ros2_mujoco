"""Print a one-line summary of the current /scan (samples, angle step, nearest/farthest, front/left/back/right)."""
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

rclpy.init(); n = Node("scan_probe"); got = {}
n.create_subscription(LaserScan, "/scan", lambda m: got.setdefault("m", m), qos_profile_sensor_data)
while "m" not in got:
    rclpy.spin_once(n, timeout_sec=0.2)
m = got["m"]; r = m.ranges; N = len(r)
at = lambda deg: r[int(round((math.radians(deg) - m.angle_min) / m.angle_increment)) % N]
fin = [x for x in r if math.isfinite(x)]
print(f"samples={N} angle_min={m.angle_min:.3f} angle_max={m.angle_max:.3f} increment={m.angle_increment:.4f} rad ({math.degrees(m.angle_increment):.1f} deg)")
print(f"range_min={m.range_min} range_max={m.range_max} finite={len(fin)} inf={N - len(fin)} nearest={min(fin):.3f} m farthest={max(fin):.3f} m")
print("ranges: front(0)=%.3f  left(90)=%.3f  back(180)=%.3f  right(-90)=%.3f" % (at(0), at(90), at(180), at(-90)))
n.destroy_node(); rclpy.shutdown()
