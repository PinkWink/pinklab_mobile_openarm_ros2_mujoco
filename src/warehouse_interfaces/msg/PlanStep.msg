# LMM 이 만든 작업 계획의 한 단계. Task Manager 가 순서대로 실행한다.
string action        # navigate | detect | pick | place | arm_pose | gripper | report | answer
string target        # pick/detect: parcel_red|parcel_blue|parcel_yellow|person ... ; arm_pose: 자세 이름 ; gripper: open|close
string location      # navigate: 목적지 ; pick: 물체가 있는 작업대 ; place: 놓을 작업대 (locations.yaml 키)
string arm           # left | right | 비우면 자동
string note          # 사용자에게 보여 줄 한 구절 (예: "픽업 작업대로 이동")
