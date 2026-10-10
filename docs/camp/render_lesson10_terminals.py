"""Terminal captures for the lesson-10 (Pick & Place) page. Text below is copied from real runs on 2026-10-10
(start spawn:=pick_table camera_depth:=true locate:=vision, ArucoDetector + YoloDetector3D). Output: docs/camp/lesson10_cli_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

OUT = "docs/camp/"
P, O = "prompt", "out"
PP = "./scripts/mobile_openarm exec python lessons/06_pick_place/pick_then_place.py"

render([(P, "H=warehouse_lecture.vision"),
        (P, 'LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \\'),
        (O, "  ./scripts/mobile_openarm start spawn:=pick_table camera_depth:=true locate:=vision viewer:=true rviz:=false"),
        (O, "..."),
        (O, "[move_group-11] You can start planning now!"),
        (O, "[pick_place_server-13] [INFO] [pick_place_server]: PickPlace server ready (/pick_place); waiting for MoveIt and Nav2"),
        (O, "[mobile_openarm_mujoco-1] [INFO] [mobile_openarm_mujoco]: YoloDetector3D: weights/warehouse_yolo11n_s320_320_openvino_model"),
        (O, "                          imgsz 320, cameras ['base_camera', 'head_camera'], 3D on"),
        (O, "[lifecycle_manager-10] [INFO] [mobile_lifecycle_manager]: Managed nodes are active")],
       OUT + "lesson10_t1.png", highlight=("PickPlace server ready", "YoloDetector3D", "Managed nodes are active", "start planning"))

render([(P, f"time {PP} red"),
        (O, ">> PickPlace phase=pick object=red station=pick_table  (parcel z=0.810 m)"),
        (O, "   [  0.0s start         ] parcel_1 sits -0.25 m from the pick_table axis -> right arm"),
        (O, "   [  0.0s navigate_pick ] Nav2 to pick_table pre-dock (1.20, -3.60)"),
        (O, "   [  1.3s navigate_pick ] arrived at pre-dock; looking for the markers"),
        (O, "   [  1.3s navigate_pick ] markers [0, 1]: along=1.04 side=+0.000 turn=-0.0deg; lateral error +0.000"),
        (O, "   [  1.3s dock          ] visual servo on markers [0, 1] (target side -0.000)"),
        (O, "   [  1.3s dock          ] visual dock: along=1.035 side=+0.000 lateral=+0.000 turn=-0.0deg"),
        (O, "   [  6.3s dock          ] visual dock: along=0.982 side=-0.010 lateral=-0.010 turn=+0.5deg"),
        (O, "   [  9.0s dock          ] visual dock: along=0.919 side=-0.000 lateral=-0.000 turn=+0.0deg"),
        (O, "   [  9.9s dock          ] blind segment +0.231 m (last fix along=0.919, side=-0.000, driven since fix 0.127)"),
        (O, "   [ 16.0s dock          ] docked: plane dx=0.560, axis dy=-0.000 (lateral residual -0.000)"),
        (O, "   [ 19.6s locate        ] parcel_1 at dx=0.510 dy=-0.246 z=0.815"),
        (O, "   [ 19.6s pre_grasp     ] planning to pre-grasp (-0.10 m behind the object)"),
        (O, "   [ 28.4s pre_grasp     ] at pre-grasp"),
        (O, "   [ 28.4s grasp         ] approaching"),
        (O, "   [ 32.6s grasp         ] holding at 24.5 mm per finger"),
        (O, "   [ 33.3s lift          ] lifting"),
        (O, "   [ 37.9s lift          ] retreated"),
        (O, "   [ 37.9s carry         ] hands_up pose with object"),
        (O, "<< SUCCEEDED success=True phase_reached=done 59s: parcel_1 held in the right hand, 0.107 m above the table"),
        (O, "   parcel z now 0.887 m; phase start times: start=0s, navigate_pick=0s, dock=1s, locate=20s, pre_grasp=20s, grasp=28s, lift=33s, carry=38s")],
       OUT + "lesson10_cli_pick.png", highlight=("<< SUCCEEDED", "locate ", "holding at", "docked:", "blind segment"))

render([(O, ">> PickPlace phase=place object=red station=pick_table  (parcel z=0.887 m)"),
        (O, "   [  0.0s start         ] placing the held parcel_1 (right arm)"),
        (O, "   [  0.0s navigate_place] Nav2 to pick_table pre-dock (1.20, -3.60)"),
        (O, "   [  4.2s navigate_place] arrived at pre-dock; looking for the markers"),
        (O, "   [  6.0s navigate_place] markers [0, 1]: along=1.10 side=-0.006 turn=-0.0deg; lateral error -0.006"),
        (O, "   [  6.0s dock          ] visual servo on markers [0, 1] (target side +0.000)"),
        (O, "   [  8.7s dock          ] visual dock: along=1.103 side=-0.022 lateral=-0.022 turn=+0.8deg"),
        (O, "   [ 11.3s dock          ] visual dock: along=1.042 side=+0.026 lateral=+0.026 turn=-1.7deg"),
        (O, "   [ 14.0s dock          ] visual dock: along=0.969 side=-0.002 lateral=-0.002 turn=-0.2deg"),
        (O, "   [ 16.6s dock          ] visual dock: along=0.910 side=+0.004 lateral=+0.004 turn=-0.6deg"),
        (O, "   [ 17.6s dock          ] blind segment +0.222 m (last fix along=0.910, side=+0.004, driven since fix 0.128)"),
        (O, "   [ 23.6s dock          ] docked: plane dx=0.560, axis dy=+0.004 (lateral residual +0.004)"),
        (O, "   [ 23.6s place         ] slot at dx=0.520 dy=-0.246; planning to pre-place"),
        (O, "   [ 32.1s place         ] lowering"),
        (O, "   [ 36.7s place         ] released"),
        (O, "   [ 41.0s retreat       ] back to transport"),
        (O, "<< SUCCEEDED success=True phase_reached=done 63s: parcel_1 placed at (2.19, -3.84, 0.810), 1.7 cm from the slot"),
        (O, "   parcel z now 0.810 m; phase start times: start=0s, navigate_place=0s, dock=6s, place=24s, retreat=41s"),
        (O, ""), (O, "real\t2m2.470s")],
       OUT + "lesson10_cli_place.png", highlight=("<< SUCCEEDED", "slot at", "released", "docked:", "real"))

render([(P, f"{PP} red --only place"),
        (O, ">> PickPlace phase=place object=red station=pick_table  (parcel z=0.810 m)"),
        (O, "<< ABORTED success=False phase_reached=start 0s: nothing is held: run the pick phase first")],
       OUT + "lesson10_cli_fail.png", highlight=("ABORTED",))

CLI = "./scripts/mobile_openarm pick"
render([(P, f"{CLI} red --phase pick")] + [(O, t) for t in ['[start   0%] parcel_1 sits -0.24 m from the pick_table axis -> right arm', '[navigate_pick   0%] Nav2 to pick_table pre-dock (1.20, -3.60)', '[navigate_pick  70%] arrived at pre-dock; looking for the markers', '[navigate_pick  80%] markers [0, 1]: along=1.12 side=+0.017 turn=-1.7deg; lateral error +0.017', '[navigate_pick 100%] pre-dock aligned', '[dock  10%] visual servo on markers [0, 1] (target side -0.000)', '[dock  50%] blind segment +0.234 m (last fix along=0.920, side=-0.007, driven since fix 0.126)', '[dock 100%] docked: plane dx=0.560, axis dy=-0.007 (lateral residual -0.007)', '[locate 100%] parcel_1 at dx=0.522 dy=-0.253 z=0.816', '[pre_grasp  20%] planning to pre-grasp (-0.10 m behind the object)', '[pre_grasp 100%] at pre-grasp', '[grasp  20%] approaching', '[grasp  80%] holding at 24.6 mm per finger', '[lift  30%] lifting', '[lift 100%] retreated', '[carry  20%] hands_up pose with object', 'PickPlace status=4 (SUCCEEDED=4) success=True phase=done 73s: parcel_1 held in the right hand, 0.106 m above the table']] +
       [(P, f"{CLI} red pick_table pick_table --phase place")] + [(O, t) for t in ['[start   0%] placing the held parcel_1 (right arm)', '[navigate_place   0%] Nav2 to pick_table pre-dock (1.20, -3.60)', '[navigate_place  70%] arrived at pre-dock; looking for the markers', '[navigate_place  80%] markers [0, 1]: along=1.17 side=+0.038 turn=-0.5deg; lateral error +0.038', '[navigate_place 100%] pre-dock aligned', '[dock  10%] visual servo on markers [0, 1] (target side +0.000)', '[dock  50%] blind segment +0.255 m (last fix along=0.942, side=+0.009, driven since fix 0.128)', '[dock 100%] docked: plane dx=0.560, axis dy=+0.009 (lateral residual +0.009)', '[place  10%] slot at dx=0.520 dy=-0.241; planning to pre-place', '[place  50%] lowering', '[place  80%] released', '[retreat  50%] back to transport', 'PickPlace status=4 (SUCCEEDED=4) success=True phase=done 62s: parcel_1 placed at (2.19, -3.85, 0.810), 0.9 cm from the slot']],
       OUT + "lesson10_cli_cli.png", highlight=("PickPlace status", "holding at", "docked:"))
