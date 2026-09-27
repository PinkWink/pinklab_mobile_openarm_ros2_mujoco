"""URDF only: robot_state_publisher + joint_state_publisher_gui + RViz (RobotModel, TF).

No simulator, Nav2 or MoveIt. Move the sliders to see every joint and its frames.
Do not run this while the simulator is running: both publish /joint_states and /tf.

    ros2 launch mobile_openarm_description display.launch.py
    ros2 launch mobile_openarm_description display.launch.py gui:=false   # sliders off
"""

from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from mobile_openarm_description.model import expand_urdf


def setup(context):
    share = Path(get_package_share_directory("mobile_openarm_description"))
    urdf = expand_urdf()
    gui = LaunchConfiguration("gui").perform(context) == "true"
    actions = [
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[{"robot_description": urdf}],
            output="screen",
        ),
        Node(
            package="joint_state_publisher_gui" if gui else "joint_state_publisher",
            executable="joint_state_publisher_gui" if gui else "joint_state_publisher",
            parameters=[{"robot_description": urdf}],
            output="screen",
        ),
    ]
    if LaunchConfiguration("rviz").perform(context) == "true":
        actions.append(
            Node(
                package="rviz2",
                executable="rviz2",
                arguments=["-d", str(share / "config/display.rviz")],
                output="screen",
            )
        )
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("gui", default_value="true", choices=["true", "false"]),
            DeclareLaunchArgument("rviz", default_value="true", choices=["true", "false"]),
            OpaqueFunction(function=setup),
        ]
    )
