# 카메라 핸들러가 검출한 ArUco 마커 하나 (배열 header의 frame_id 기준, 보통 base_footprint)
int32 id
float32 size               # 검은 정사각형 한 변 (m)
geometry_msgs/Pose pose    # 마커 중심; z축 = 마커가 바라보는 법선
float32 normal_yaw         # base 기준 법선 방향 (rad). 정면으로 마주 보면 pi
float32 distance           # 카메라에서 마커까지 (m)
float32[8] corners         # 픽셀 좌표 x1,y1,...,x4,y4
