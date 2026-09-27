from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from mobile_openarm_moveit_config.config import parameters


def setup(context):
    path = LaunchConfiguration("urdf_file").perform(context)
    params = parameters(Path(path).read_text() if path else None)
    actions = [
        Node(
            package="moveit_ros_move_group",
            executable="move_group",
            output="screen",
            parameters=[params],
        ),
        Node(
            package="mobile_openarm_moveit_config",
            executable="warehouse_scene",
            output="screen",
            parameters=[{"use_sim_time": True}],
        ),
    ]
    if LaunchConfiguration("rviz").perform(context) == "true":
        actions.append(
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=[
                    "-d",
                    str(
                        Path(
                            get_package_share_directory("mobile_openarm_moveit_config")
                        )
                        / "config/moveit.rviz"
                    ),
                ],
                parameters=[params],
                output="screen",
            )
        )
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("urdf_file", default_value=""),
            DeclareLaunchArgument("rviz", default_value="true"),
            OpaqueFunction(function=setup),
        ]
    )
