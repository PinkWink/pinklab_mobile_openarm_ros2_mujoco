"""Vic Pinky base only: robot_state_publisher + joint_state_publisher_gui + RViz (RobotModel, TF).

Shows urdf/robot_core.xacro as it comes from upstream (no lidar/camera/gazebo xacros, no simulator).

    ros2 launch vicpinky_description display.launch.py
    ros2 launch vicpinky_description display.launch.py gui:=false   # sliders off
"""

from pathlib import Path

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    share = Path(get_package_share_directory("vicpinky_description"))
    urdf = xacro.process_file(str(share / "urdf/robot_core.xacro")).toxml()
    gui = LaunchConfiguration("gui").perform(context) == "true"
    actions = [
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": urdf}], output="screen"),
        Node(package="joint_state_publisher_gui" if gui else "joint_state_publisher",
             executable="joint_state_publisher_gui" if gui else "joint_state_publisher",
             parameters=[{"robot_description": urdf}], output="screen"),
    ]
    if LaunchConfiguration("rviz").perform(context) == "true":
        actions.append(Node(package="rviz2", executable="rviz2",
                            arguments=["-d", str(share / "rviz/display.rviz")], output="screen"))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true", choices=["true", "false"]),
        DeclareLaunchArgument("rviz", default_value="true", choices=["true", "false"]),
        OpaqueFunction(function=setup),
    ])
