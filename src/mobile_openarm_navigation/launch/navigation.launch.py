from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    share = Path(get_package_share_directory("mobile_openarm_navigation"))
    mode = LaunchConfiguration("mode").perform(context)
    mapfile = LaunchConfiguration("map").perform(context)
    params = str(share / "config/nav2.yaml")
    initial = LaunchConfiguration("initial_pose").perform(context).strip()
    amcl_params = [params]
    if initial:
        x, y, yaw = (float(v) for v in initial.split(","))
        amcl_params.append({"initial_pose": {"x": x, "y": y, "z": 0.0, "yaw": yaw}})
    actions = []
    lifecycle = []
    if mode == "slam" or (mode == "nav" and not mapfile):
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    str(
                        Path(get_package_share_directory("slam_toolbox"))
                        / "launch/online_async_launch.py"
                    )
                ),
                launch_arguments={
                    "use_sim_time": "true",
                    "autostart": "true",
                    "slam_params_file": str(share / "config/slam.yaml"),
                }.items(),
            )
        )
    if mode == "nav":
        if mapfile:
            if not Path(mapfile).is_file():
                raise RuntimeError(f"Map does not exist: {mapfile}")
            actions.extend(
                [
                    Node(
                        package="nav2_map_server",
                        executable="map_server",
                        name="map_server",
                        parameters=[params, {"yaml_filename": mapfile}],
                        output="screen",
                    ),
                    Node(
                        package="nav2_amcl",
                        executable="amcl",
                        name="amcl",
                        parameters=amcl_params,
                        output="screen",
                    ),
                ]
            )
            lifecycle += ["map_server", "amcl"]
        for pkg, exe in [
            ("nav2_controller", "controller_server"),
            ("nav2_planner", "planner_server"),
            ("nav2_smoother", "smoother_server"),
            ("nav2_behaviors", "behavior_server"),
            ("nav2_bt_navigator", "bt_navigator"),
        ]:
            actions.append(
                Node(
                    package=pkg,
                    executable=exe,
                    name=exe,
                    parameters=[params],
                    output="screen",
                )
            )
            lifecycle.append(exe)
        actions.append(
            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="mobile_lifecycle_manager",
                parameters=[
                    {
                        "use_sim_time": True,
                        "autostart": True,
                        "bond_timeout": 10.0,
                        "node_names": lifecycle,
                    }
                ],
                output="screen",
            )
        )
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "mode", default_value="nav", choices=["drive", "slam", "nav"]
            ),
            DeclareLaunchArgument("map", default_value=""),
            DeclareLaunchArgument("initial_pose", default_value="", description="AMCL initial pose X,Y,YAW (map frame); empty = nav2.yaml"),
            OpaqueFunction(function=setup),
        ]
    )
