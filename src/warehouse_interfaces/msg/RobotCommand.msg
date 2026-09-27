# 자연어를 LLM이 구조화한 명령
string request_id
string intent            # move_object | go_to | find | report | answer | arm_pose | gripper | stop
string target            # 물체·사람·자세 이름 (예: parcel_red, person, ready)
string source            # move_object의 출발 장소
string destination       # move_object / go_to의 목적 장소
KeyValue[] params        # 추가 인자 (예: attributes=helmet:false, question=...)
string utterance         # 원문
