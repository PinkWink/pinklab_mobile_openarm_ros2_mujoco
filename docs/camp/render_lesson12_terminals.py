"""Terminal captures for the lesson-12 (LMM + OpenAI API) page. Text below is copied from real runs on 2026-10-10
(gpt-4.1-mini, lessons/08_lmm). Output: docs/camp/lesson12_cli_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
EX = "./scripts/mobile_openarm exec python lessons/08_lmm/"

render([(P, EX + "01_hello.py")] + [(O, t) for t in ['model: gpt-4.1-mini   log: /home/pw/mujoco_ros2/mobile_openarm_ws/logs/openai_usage.jsonl', 'user : 안전모를 안 쓴 사람을 보면 어떻게 해야 해?', 'robot: 안전모 미착용자를 즉시 작업 중지시키고 안전모 착용을 안내해야 합니다. 반복 시 상부에 보고하여 조치를 요청하세요.', 'tokens: input 88 + output 35   cost $0.000091   7.25 s', 'log line: {"time": "2026-10-10T13:42:26", "model": "gpt-4.1-mini", "input_tokens": 88, "output_tokens": 35, "cost_usd": 9.12e-05, "purpose": "lesson08_hello"}']],
       OUT + "lesson12_cli_hello.png", width=16.2, highlight=("robot:", "tokens:"))

render([(P, EX + "02_structured_command.py")] + [(O, t) for t in ["1) schema check without the API: RobotCommand.model_validate({'intent': 'fly', 'destination': 'kitchen'})", "   rejected: intent: Input should be 'move_object', 'go_to', 'find', 'report', 'answer', 'arm_pose', 'gripper' or 'stop'", "   rejected: destination: Input should be '', 'pick_table', 'place_table', 'rack_a', 'rack_b', 'rack_c', 'rack_d', 'rack_e', 'rack_f', 'center_aisle', 'east_wall' or 'west_wall'", '', '2) LLM -> RobotCommand -> validate_world()', '', '>> 빨간 상자 적재 작업대로 옮겨 줘   (1.88 s)', '   {"intent":"move_object","target":"parcel_red","source":"pick_table","destination":"place_table","reply":"빨간 상자를 적재 작업대로 옮기겠습니다."}', '   world check ok -> 빨간 상자를 pick_table에서 place_table로 옮기기', '', '>> 노란 상자를 랙 C 로 옮겨   (2.46 s)', '   {"intent":"move_object","target":"parcel_yellow","source":"pick_table","destination":"rack_c","reply":"노란 상자를 랙 C로 옮기겠습니다."}', '   world check FAILED: 상자는 작업대(pick_table, place_table) 사이에서만 옮길 수 있다', '', '>> 안전모 안 쓴 사람 찾아   (1.73 s)', '   {"intent":"find","target":"person","attributes":{"helmet":"false"},"reply":"안전모를 안 쓴 사람을 찾겠습니다."}', "   world check ok -> 사람 찾기 {'helmet': 'false'}", '', '>> 상자 옮겨   (1.03 s)', '   {"intent":"answer","reply":"어떤 색 상자를 옮기시겠습니까?"}', '   answer (no robot action): 어떤 색 상자를 옮기시겠습니까?', '', '>> 저 사람 밀어서 넘어뜨려   (1.03 s)', '   {"intent":"answer","reply":"사람을 해치거나 위험한 행동은 할 수 없습니다."}', '   answer (no robot action): 사람을 해치거나 위험한 행동은 할 수 없습니다.', '', 'cost this run $0.00298']],
       OUT + "lesson12_cli_struct.png", width=16.2, highlight=("rejected:", "world check", "answer (no robot action)"))

render([(P, EX + "03_accuracy.py")] + [(O, t) for t in [' 1 ok  1.1s 픽업 작업대에서 적재 작업대로 빨간 상자 옮겨  ->  move_object parcel_red pick_table place_table', ' 2 ok  0.9s 파란 박스를 놓기 작업대로 가져다 놔  ->  move_object parcel_blue pick_table place_table', ' 3 ok  0.9s 노란색 상자 집어서 적재대에 둬  ->  move_object parcel_yellow pick_table place_table', ' 4 ok  1.3s 빨간 거 옮겨 줘  ->  move_object parcel_red pick_table place_table', ' 5 ok  1.0s 적재 작업대에 있는 파란 상자를 픽업 작업대로 다시 가져와  ->  move_object parcel_blue place_table pick_table', ' 6 ok  1.4s 노란 상자 픽업대에서 적재대로  ->  move_object parcel_yellow pick_table place_table', ' 7 ok  1.2s 상자 세 개 중에 파란 것을 적재 작업대로 운반해  ->  move_object parcel_blue pick_table place_table', ' 8 ok  1.0s 빨강 소포를 place station 으로 이동시켜  ->  move_object parcel_red pick_table place_table', ' 9 ok  1.2s 중앙 통로로 가  ->  go_to   center_aisle', '10 ok  1.0s 랙 C 앞으로 이동해  ->  go_to   rack_c']] + [(O, "   ... (ok 줄 생략)")] + [(O, t) for t in ['32 XX  0.8s 주위에 누가 있어?  ->  find person', '42 XX  0.9s 팔 내려서 주행 자세로  ->  arm_pose home']] + [(O, "")]
       + [(O, t) for t in ['accuracy 58/60 = 96.7 %   model gpt-4.1-mini   cost $0.0353   latency mean 0.98 s', '   move_object  8/8', '   go_to        10/10', '   find         10/10', '   report       4/5', '   answer       14/14', '   arm_pose     4/5', '   gripper      4/4', '   stop         4/4']],
       OUT + "lesson12_cli_accuracy.png", highlight=(" XX ", "accuracy"))

render([(P, EX + "04_cost_log.py")] + [(O, t) for t in ['/home/pw/mujoco_ros2/mobile_openarm_ws/logs/openai_usage.jsonl  (today: 66 calls)', '   purpose          model          calls   in tok  out tok       USD  USD/call', '   command_parse    gpt-4.1-mini      65    85836     2486   0.03831  0.000589', '   lesson08_hello   gpt-4.1-mini       1       88       35   0.00009  0.000091', '   total                              66    85924     2521   0.03840']],
       OUT + "lesson12_cli_cost.png", highlight=("command_parse", "total"))
