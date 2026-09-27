# 순찰 중 만난 사람·물체의 기억 한 건
string id
string kind
KeyValue[] attributes
geometry_msgs/PoseStamped pose   # map 좌표
string place                     # locations.yaml 기준 가장 가까운 장소 이름
builtin_interfaces/Time first_seen
builtin_interfaces/Time last_seen
int32 sightings
string snapshot_path
string description               # LLM 또는 규칙이 만든 한 줄 설명
