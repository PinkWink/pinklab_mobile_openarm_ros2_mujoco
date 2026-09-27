from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from mobile_openarm_description.model import expand_urdf


def parameters(urdf=None):
    folder = (
        Path(get_package_share_directory("mobile_openarm_moveit_config")) / "config"
    )

    def load(name):
        return yaml.safe_load((folder / name).read_text())

    return {
        "robot_description": urdf or expand_urdf(),
        "robot_description_semantic": (folder / "mobile_openarm.srdf").read_text(),
        "robot_description_kinematics": load("kinematics.yaml"),
        "robot_description_planning": load("joint_limits.yaml"),
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl": load("ompl_planning.yaml"),
        **load("moveit_controllers.yaml"),
        "use_sim_time": True,
        "allow_trajectory_execution": True,
        "moveit_manage_controllers": False,
        "trajectory_execution.allowed_execution_duration_scaling": 2.0,
        "trajectory_execution.allowed_goal_duration_margin": 4.0,
        "trajectory_execution.allowed_start_tolerance": 0.05,
        "publish_robot_description": True,
        "publish_robot_description_semantic": True,
        "publish_planning_scene": True,
        "publish_geometry_updates": True,
        "publish_state_updates": True,
        "publish_transforms_updates": True,
    }
