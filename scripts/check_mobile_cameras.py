"""Render all four cameras directly and check RGB/depth calibration. No ROS graph."""

import json
from pathlib import Path
import time

import mujoco
import numpy as np
from PIL import Image, ImageDraw

from mobile_openarm_mujoco.cameras import CameraRig
from mobile_openarm_mujoco.model import Physics, build_model


def main():
    out = Path("artifacts/mobile_cameras")
    out.mkdir(parents=True, exist_ok=True)
    p = Physics(build_model("artifacts/mobile_generated"))
    for _ in range(100):
        p.step()
    qpos = p.data.qpos.copy()
    report = {}
    with CameraRig(p.model, p.data) as cameras:
        start = time.monotonic()
        frames = cameras.read_all(
            ["base_camera", "head_camera", "left_wrist_camera", "right_wrist_camera"],
            depth=True,
        )
        elapsed = time.monotonic() - start
        assert len(frames) == 4
        assert len({frame.sim_time for frame in frames.values()}) == 1
        np.testing.assert_array_equal(qpos, p.data.qpos)
        mosaic = Image.new("RGB", (1280, 1020), "#141b24")
        draw = ImageDraw.Draw(mosaic)
        for i, (name, frame) in enumerate(frames.items()):
            assert frame.rgb.shape == (480, 640, 3) and frame.rgb.dtype == np.uint8
            assert (
                frame.depth_m.shape == (480, 640) and frame.depth_m.dtype == np.float32
            )
            assert float(frame.rgb.std()) > 10, name
            valid = np.isfinite(frame.depth_m)
            assert valid.mean() > 0.25 and frame.depth_m[valid].min() > 0, name
            image = Image.fromarray(frame.rgb)
            image.save(out / (name + ".png"))
            np.save(out / (name + "_depth.npy"), frame.depth_m)
            x, y = (i % 2) * 640, (i // 2) * 510
            draw.text((x + 12, y + 8), name, fill="white")
            mosaic.paste(image, (x, y + 30))
            report[name] = {
                "sim_time": frame.sim_time,
                "rgb_shape": list(frame.rgb.shape),
                "valid_depth_fraction": float(valid.mean()),
                "depth_min_m": float(frame.depth_m[valid].min()),
                "K": frame.K.tolist(),
                "T_world_optical": frame.T_world_optical.tolist(),
            }
        # The next RGB render must not alias or overwrite a previous frame.
        old = frames["base_camera"].rgb.copy()
        cameras.read("right_wrist_camera")
        np.testing.assert_array_equal(old, frames["base_camera"].rgb)
        mosaic.save(out / "four_cameras.png")
        report["four_rgb_depth_first_capture_wall_seconds"] = elapsed

    # A known target 1 m down optical +Z tests axis conventions and metric depth.
    model = mujoco.MjModel.from_xml_string("""<mujoco>
      <visual><global offwidth="320" offheight="240"/><map znear="0.001" zfar="10"/></visual>
      <asset><material name="red" rgba="1 0.05 0.05 1" specular="0"/></asset>
      <worldbody><light pos="0 0 0" dir="0 0 1" diffuse="0.4 0.4 0.4" specular="0 0 0"/>
      <camera name="test" pos="0 0 0" quat="0 1 0 0" fovy="60"/>
      <geom type="box" pos="0 0 1.05" size="0.5 0.5 0.05" material="red"/>
      </worldbody></mujoco>""")
    data = mujoco.MjData(model)
    with CameraRig(model, data, width=320, height=240) as cameras:
        frame = cameras.read("test", depth=True)
        assert abs(float(frame.depth_m[120, 160]) - 1.0) < 0.005
        np.testing.assert_allclose(frame.T_world_optical, np.eye(4), atol=1e-9)
        assert frame.rgb[120, 160, 0] > 2 * int(frame.rgb[120, 160, 1]), frame.rgb[
            120, 160
        ]
    report["metric_depth_and_optical_axes"] = "passed"
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
