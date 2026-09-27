cmake_minimum_required(VERSION 3.8)
project(warehouse_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(action_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/KeyValue.msg"
  "msg/ActorState.msg"
  "msg/ActorStateArray.msg"
  "msg/Detection3D.msg"
  "msg/Detection3DArray.msg"
  "msg/Encounter.msg"
  "msg/EncounterArray.msg"
  "msg/RobotCommand.msg"
  "msg/PlanStep.msg"
  "msg/Utterance.msg"
  "msg/VisionStats.msg"
  "msg/ArucoMarker.msg"
  "msg/ArucoMarkerArray.msg"
  "srv/SetActor.srv"
  "srv/QueryEncounters.srv"
  "srv/AskRobot.srv"
  "action/PickPlace.action"
  "action/ExecuteCommand.action"
  "action/ExecutePlan.action"
  DEPENDENCIES std_msgs geometry_msgs builtin_interfaces action_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
