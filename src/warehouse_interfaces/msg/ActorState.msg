# 시뮬레이터가 발행하는 배우(사람·지게차 등)의 실제 상태. 평가용 ground truth.
string name              # actors.yaml의 이름
string kind              # person | forklift | pallet | cone | extinguisher
geometry_msgs/Pose pose  # MuJoCo world 좌표 (map 원점과 일치하도록 창고를 정의)
geometry_msgs/Vector3 velocity
bool moving
KeyValue[] attributes    # person: helmet, vest, shirt, height
