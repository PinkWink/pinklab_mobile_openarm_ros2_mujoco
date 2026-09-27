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
    viewer = LaunchConfiguration("viewer").perform(context) == "true"
    rviz = LaunchConfiguration("rviz").perform(context) == "true"
    moveit = LaunchConfiguration("moveit").perform(context) == "true"
    mode = LaunchConfiguration("mode").perform(context)
    urdf = expand_urdf()
    path = root / "robot.urdf"
    path.write_text(urdf)
    python = (
        str(Path(sys.executable).parent / "mjpython")
        if viewer and sys.platform == "darwin"
        else sys.executable
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
    spawn = resolve_spawn(LaunchConfiguration("spawn").perform(context))
    if spawn:
        command += ["--spawn", ",".join(f"{v:.4f}" for v in spawn)]
    profile = LaunchConfiguration("profile").perform(context)
    actors = LaunchConfiguration("actors").perform(context)
    if actors:
        command += ["--actors-file", actors]
    camera_handler = LaunchConfiguration("camera_handler").perform(context)
    if camera_handler == "none":
        camera_handler = ""
    if camera_handler:
        command += ["--camera-handler", camera_handler]
        fps = LaunchConfiguration("camera_fps").perform(context)
        names = LaunchConfiguration("camera_names").perform(context)
        size = LaunchConfiguration("camera_size").perform(context)
        if profile == "lite":
            # Low-spec default: two cameras, quarter resolution, slow capture.
            fps = fps or "2"
            names = names or "base_camera,head_camera"
            size = size or "320x240"
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
                    str(nav / "config/navigation.rviz"),
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
            *[
                DeclareLaunchArgument(
                    k, default_value="true", choices=["true", "false"]
                )
                for k in ["viewer", "rviz", "moveit"]
            ],
            DeclareLaunchArgument(
                "camera_handler",
                default_value="warehouse_lecture.vision.pipeline:LecturePipeline",
                description="Direct Python module:attribute run in the simulator process; 'none' disables cameras",
            ),
            DeclareLaunchArgument(
                "camera_fps",
                default_value="",
                description="Simulation-time capture rate; defaults to cameras.yaml",
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
                description="Comma-separated cameras to render; empty = all (lite: base,head)",
            ),
            DeclareLaunchArgument(
                "camera_size",
                default_value="",
                description="Render size WxH; empty = cameras.yaml (lite: 320x240)",
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
            DeclareLaunchArgument(
                "profile",
                default_value="lite",
                choices=["lite", "full"],
                description="lite = low-spec camera defaults; full = cameras.yaml defaults",
            ),
            OpaqueFunction(function=setup),
        ]
    )
