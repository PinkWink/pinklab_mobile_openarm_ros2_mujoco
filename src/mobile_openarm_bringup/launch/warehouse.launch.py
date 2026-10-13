"""One simulator and one robot_state_publisher for driving and manipulation."""

from pathlib import Path
import fcntl
import os
import sys
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    RegisterEventHandler,
    EmitEvent,
    SetEnvironmentVariable,
)
from launch.events import Shutdown
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from mobile_openarm_description.model import expand_urdf

_lock = None

# Per-profile defaults; sim_config.yaml overrides them, launch arguments override both.
# "" for camera_* means the cameras.yaml value.
PROFILES = {
    "full": dict(viewer_shadows="true", viewer_meshes="visual", camera_shadows="true",
                 camera_names="", camera_size="", camera_fps="", rviz_fps="30"),
    "lite": dict(viewer_shadows="false", viewer_meshes="visual", camera_shadows="true",
                 camera_names="base_camera,head_camera", camera_size="320x240", camera_fps="2", rviz_fps="15"),
    "minimal": dict(viewer_shadows="false", viewer_meshes="simple", camera_shadows="false",
                    camera_names="base_camera,head_camera", camera_size="320x240", camera_fps="2", rviz_fps="10"),
}
CHOICES = dict(profile=list(PROFILES), viewer=["true", "false"], rviz=["true", "false"],
               viewer_shadows=["true", "false"], viewer_meshes=["visual", "simple"],
               camera_shadows=["true", "false"])
SETTINGS = ["profile", "viewer", "rviz", *PROFILES["full"]]


def config_file(context):
    """config:=PATH, else $MOBILE_OPENARM_CONFIG, else sim_config.yaml in the workspace root."""
    path = LaunchConfiguration("config").perform(context) or os.environ.get("MOBILE_OPENARM_CONFIG", "")
    if path:
        return Path(path).expanduser()
    # <ws>/install/mobile_openarm_bringup/share/mobile_openarm_bringup
    return Path(get_package_share_directory("mobile_openarm_bringup")).parents[3] / "sim_config.yaml"


def load_settings(context):
    """Launch argument > sim_config.yaml > profile defaults, read fresh on every launch."""
    path = config_file(context)
    data = {}
    if path.exists():
        import yaml

        data = yaml.safe_load(path.read_text()) or {}
    elif LaunchConfiguration("config").perform(context):
        raise RuntimeError(f"config:={path} not found")

    def pick(key):
        value = LaunchConfiguration(key).perform(context)
        if value == "" and data.get(key) is not None:
            value = data[key]
            value = str(value).lower() if isinstance(value, bool) else str(value)
        return value

    s = {k: pick(k) for k in SETTINGS}
    s["profile"] = s["profile"] or "lite"
    s["viewer"] = s["viewer"] or "true"
    s["rviz"] = s["rviz"] or "true"
    if s["profile"] not in PROFILES:
        raise RuntimeError(f"profile {s['profile']!r} must be one of {list(PROFILES)} ({path})")
    for key, default in PROFILES[s["profile"]].items():
        s[key] = s[key] or default
    for key, choices in CHOICES.items():
        if s[key] not in choices:
            raise RuntimeError(f"{key} {s[key]!r} must be one of {choices} ({path})")
    return path if path.exists() else None, s


def rviz_config(path, fps, root):
    """A copy of the RViz config redrawn at fps instead of 30 (15 FPS = half the GPU load)."""
    if fps == "30":
        return str(path)
    copy = root / f"{path.stem}_{fps}fps.rviz"
    copy.write_text(path.read_text().replace("Frame Rate: 30", f"Frame Rate: {int(fps)}"))
    return str(copy)


def setup(context):
    global _lock
    root = Path(
        os.environ.get(
            "MOBILE_OPENARM_MODEL_DIR", str(Path.home() / ".cache/mobile_openarm")
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    _lock = (root / "run.lock").open("w")
    try:
        fcntl.flock(_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError(
            "Mobile OpenArm simulator is already running. Stop it before starting another session."
        )
    config, s = load_settings(context)
    print(f"[sim_config] {config or 'file not found, profile defaults'}", flush=True)
    print("[sim_config] " + " ".join(f"{k}={v or '-'}" for k, v in s.items()), flush=True)
    viewer = s["viewer"] == "true"
    rviz = s["rviz"] == "true"
    moveit = LaunchConfiguration("moveit").perform(context) == "true"
    mode = LaunchConfiguration("mode").perform(context)
    urdf = expand_urdf()
    path = root / "robot.urdf"
    path.write_text(urdf)
    # Plain `ros2 launch` runs under /usr/bin/python3 (the ros2 shebang); the simulator
    # needs the activated venv (scripts/env.sh), which has mujoco.
    venv = Path(os.environ.get("VIRTUAL_ENV", "")) / "bin/python3"
    interpreter = str(venv) if os.environ.get("VIRTUAL_ENV") and venv.exists() else sys.executable
    python = (
        str(Path(interpreter).parent / "mjpython")
        if viewer and sys.platform == "darwin"
        else interpreter
    )
    command = [
        python,
        "-m",
        "mobile_openarm_mujoco.bridge",
        "--urdf-file",
        str(path),
        "--output-dir",
        str(root),
    ]
    if viewer:
        command.append("--viewer")
        if s["viewer_shadows"] == "false":
            # Shadows cost one extra pass over the 2.7 M-triangle robot per light.
            command.append("--no-viewer-shadows")
        if s["viewer_meshes"] == "simple":
            command.append("--viewer-simple-meshes")
    spawn = resolve_spawn(LaunchConfiguration("spawn").perform(context))
    if spawn:
        command += ["--spawn", ",".join(f"{v:.4f}" for v in spawn)]
    actors = LaunchConfiguration("actors").perform(context)
    if actors:
        command += ["--actors-file", actors]
    camera_handler = LaunchConfiguration("camera_handler").perform(context)
    if camera_handler == "none":
        camera_handler = ""
    if camera_handler:
        command += ["--camera-handler", camera_handler]
        fps, names, size = s["camera_fps"], s["camera_names"], s["camera_size"]
        if s["camera_shadows"] == "false":
            command.append("--no-camera-shadows")
        if fps:
            command += ["--camera-fps", fps]
        if names:
            command += ["--camera-names", names]
        if size:
            command += ["--camera-size", size]
        if LaunchConfiguration("camera_depth").perform(context) == "true":
            command.append("--camera-depth")
        if LaunchConfiguration("camera_segmentation").perform(context) == "true":
            command.append("--camera-segmentation")
    physics = ExecuteProcess(cmd=command, output="screen", name="mobile_openarm_mujoco")

    def exited(event, ctx):
        return (
            []
            if ctx.is_shutdown
            else [EmitEvent(event=Shutdown(reason="MuJoCo backend exited"))]
        )

    actions = [
        physics,
        RegisterEventHandler(OnProcessExit(target_action=physics, on_exit=exited)),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": urdf, "use_sim_time": True}],
            output="screen",
        ),
    ]
    nav = Path(get_package_share_directory("mobile_openarm_navigation"))
    if mode != "drive":
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(nav / "launch/navigation.launch.py")),
                launch_arguments={
                    "mode": mode,
                    "map": LaunchConfiguration("map").perform(context),
                    "initial_pose": ",".join(f"{v:.4f}" for v in spawn) if spawn else "",
                }.items(),
            )
        )
    if moveit:
        m = Path(get_package_share_directory("mobile_openarm_moveit_config"))
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(m / "launch/moveit.launch.py")),
                launch_arguments={
                    "urdf_file": str(path),
                    "rviz": str(rviz).lower(),
                    "rviz_config": rviz_config(m / "config/moveit.rviz", s["rviz_fps"], root),
                }.items(),
            )
        )
        if mode != "drive" and LaunchConfiguration("skills").perform(context) == "true":
            actions.append(
                Node(
                    package="warehouse_skills",
                    executable="pick_place_server",
                    output="screen",
                    parameters=[{"use_sim_time": True, "locate": LaunchConfiguration("locate").perform(context)}],
                )
            )
    elif rviz:
        actions.append(
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=[
                    "-d",
                    rviz_config(nav / "config/navigation.rviz", s["rviz_fps"], root),
                    "-f",
                    "odom" if mode == "drive" else "map",
                ],
                parameters=[{"use_sim_time": True}],
                output="screen",
            )
        )
    return actions


def resolve_spawn(text):
    """'' -> None (mujoco.yaml spawn); 'X,Y,YAW' -> tuple; a locations.yaml name (pick_table, rack_c, ...) -> its base_goal."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        x, y, yaw = (float(v) for v in text.split(","))
        return x, y, yaw
    except ValueError:
        pass
    import yaml

    locations = Path(get_package_share_directory("warehouse_lecture")) / "worlds/locations.yaml"
    data = yaml.safe_load(locations.read_text())["locations"]
    if text not in data:
        raise RuntimeError(f"spawn:={text!r} is neither X,Y,YAW nor a location in {locations} ({', '.join(data)})")
    return tuple(float(v) for v in data[text]["base_goal"])


def generate_launch_description():
    env = {
        "ROS_LOCALHOST_ONLY": "1",
        "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
        "ROS_STATIC_PEERS": "",
        "ROS_DOMAIN_ID": os.environ.get("ROS_DOMAIN_ID", "43"),
    }
    return LaunchDescription(
        [
            *[SetEnvironmentVariable(k, v) for k, v in env.items()],
            DeclareLaunchArgument(
                "mode", default_value="nav", choices=["drive", "slam", "nav"]
            ),
            DeclareLaunchArgument(
                "map",
                default_value=str(
                    Path(get_package_share_directory("mobile_openarm_navigation"))
                    / "maps/warehouse.yaml"
                ),
            ),
            DeclareLaunchArgument("moveit", default_value="true", choices=["true", "false"]),
            DeclareLaunchArgument(
                "config",
                default_value="",
                description="Settings file; empty = $MOBILE_OPENARM_CONFIG or <workspace>/sim_config.yaml",
            ),
            *[
                DeclareLaunchArgument(k, default_value="", description=f"empty = sim_config.yaml / profile ({'|'.join(c)})")
                for k, c in CHOICES.items()
            ],
            DeclareLaunchArgument(
                "rviz_fps", default_value="", description="RViz redraw rate; empty = sim_config.yaml / profile"
            ),
            DeclareLaunchArgument(
                "camera_handler",
                default_value="warehouse_lecture.vision.pipeline:LecturePipeline",
                description="Direct Python module:attribute run in the simulator process; 'none' disables cameras",
            ),
            DeclareLaunchArgument(
                "camera_fps",
                default_value="",
                description="Simulation-time capture rate; empty = sim_config.yaml / profile",
            ),
            DeclareLaunchArgument(
                "camera_depth", default_value="true", choices=["true", "false"]
            ),
            DeclareLaunchArgument(
                "camera_segmentation",
                default_value="true",
                choices=["true", "false"],
                description="Render per-pixel body ids for dataset labelling",
            ),
            DeclareLaunchArgument(
                "camera_names",
                default_value="",
                description="Comma-separated cameras to render; empty = sim_config.yaml / profile",
            ),
            DeclareLaunchArgument(
                "camera_size",
                default_value="",
                description="Render size WxH; empty = sim_config.yaml / profile",
            ),
            DeclareLaunchArgument(
                "actors",
                default_value="",
                description="actors.yaml path; 'none' removes people and props; empty = package default",
            ),
            DeclareLaunchArgument(
                "skills", default_value="true", choices=["true", "false"],
                description="Start the PickPlace action server with MoveIt and Nav2",
            ),
            DeclareLaunchArgument(
                "locate", default_value="truth", choices=["truth", "vision"],
                description="Object localisation for PickPlace: simulator truth or camera detections",
            ),
            DeclareLaunchArgument(
                "spawn",
                default_value="",
                description="Robot start pose: a locations.yaml name (pick_table, place_table, rack_c, ...) or X,Y,YAW; empty = world origin. Also sets the AMCL initial pose",
            ),
            OpaqueFunction(function=setup),
        ]
    )
