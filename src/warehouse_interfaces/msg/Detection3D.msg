# 카메라 핸들러(Python)가 내보내는 검출 하나. 영상 자체는 발행하지 않는다.
string label             # YOLO 클래스 또는 색 이름
float32 score
int32 track_id           # 추적 없으면 -1
string camera            # base_camera | head_camera | left_wrist_camera | right_wrist_camera
float32[4] bbox_xyxy     # 픽셀 좌표 (x1, y1, x2, y2)
bool has_position
geometry_msgs/PointStamped position   # frame_id에 표기된 좌표계 (optical_frame 또는 map)
KeyValue[] attributes    # person: helmet, vest 등
