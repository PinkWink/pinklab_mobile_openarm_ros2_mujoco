# MoveIt configuration provenance

User-supplied `openarm_ws.zip`, SHA256 `177990f0a12c74129fcccb95df7403ed5678aa23ca196c3f1422536cc3147c45`.

- SRDF derived from `openarm_ros2/openarm_bimanual_moveit_config/config/openarm_v1.0/openarm_bimanual.srdf`, Apache-2.0 header preserved in the source archive.
- RViz derived from `openarm_moveit/config/demo.rviz`, with the mobile frames and navigation displays added.
- KDL groups and controller names follow that workspace. Joint limits and OMPL configuration are adapted for conservative MuJoCo practice.
- The archive's standalone launch files, CAN hardware, process cleanup code and shell instructions are not invoked.
- Upstream OpenArm description: https://github.com/enactic/openarm_description/tree/1fba2cbc05001f05b4514120b70130b4ac06f409
