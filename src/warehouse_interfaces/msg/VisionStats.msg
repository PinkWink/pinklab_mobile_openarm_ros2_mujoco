# 카메라 핸들러의 처리율 통계 (저사양 PC 튜닝용)
std_msgs/Header header
float32 capture_fps       # 시뮬레이션 시간 기준 캡처 주기
float32 realtime_ratio    # 시뮬레이션 시간 / 실제 시간
float32 inference_ms      # 워커의 마지막 추론 시간
int32 queue_depth
int32 dropped_frames
string[] cameras
