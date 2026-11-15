"""Show two_link_arm.urdf in RViz: robot_state_publisher + RViz, and a joint slider when there is no simulator.

  ros2 launch lessons/01_mujoco_ros2/view_urdf.launch.py              # no simulator: sliders publish /joint_states
  ros2 launch lessons/01_mujoco_ros2/view_urdf.launch.py sim:=true    # urdf_bridge.py publishes /joint_states and /clock
"""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

HERE = Path(__file__).parent


def generate_launch_description():
    sim = LaunchConfiguration("sim")
    sim_time = {"use_sim_time": ParameterValue(sim, value_type=bool)}
    urdf = (HERE / "two_link_arm.urdf").read_text()
    return LaunchDescription([
        DeclareLaunchArgument("sim", default_value="false"),
        # URDF + /joint_states -> /tf (every link frame) and /robot_description
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"robot_description": urdf}, sim_time]),
        # without a simulator somebody has to publish /joint_states: sliders
        Node(package="joint_state_publisher_gui", executable="joint_state_publisher_gui",
             condition=UnlessCondition(sim)),
        Node(package="rviz2", executable="rviz2", arguments=["-d", str(HERE / "two_link_arm.rviz")],
             parameters=[sim_time]),
    ])
