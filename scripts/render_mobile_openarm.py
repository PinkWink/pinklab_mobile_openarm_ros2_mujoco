from pathlib import Path
import mujoco
from PIL import Image
from mobile_openarm_mujoco.model import Physics, build_model

p = Physics(build_model("artifacts/mobile_generated"))
for _ in range(100):
    p.step()
opt = mujoco.MjvOption()
opt.geomgroup[1] = 0
with mujoco.Renderer(p.model, height=900, width=1400) as renderer:
    for filename, lookat, distance, azimuth, elevation in [
        ("mobile-openarm-warehouse.png", [0, 0, 0.5], 19, 125, -58),
        ("mobile-openarm-robot.png", [0, 0, 0.7], 2.6, 135, -20),
    ]:
        cam = mujoco.MjvCamera()
        cam.lookat[:] = lookat
        cam.distance = distance
        cam.azimuth = azimuth
        cam.elevation = elevation
        renderer.update_scene(p.data, camera=cam, scene_option=opt)
        Image.fromarray(renderer.render()).save(Path("artifacts") / filename)
print("Rendered warehouse and robot")
