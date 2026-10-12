"""Lesson 09 (Day 2 ⑬): the web dashboard takes a Korean instruction and runs it through the Task Manager.

    # terminal 1: simulator with the camera detectors + JPEG tap for the browser
    H=warehouse_lecture.vision
    LECTURE_HANDLERS="$H.aruco:ArucoDetector,$H.yolo_detector:YoloDetector3D" \\
      ./scripts/mobile_openarm start camera_depth:=true locate:=vision rviz:=false \\
      camera_handler:=lessons/04_navigation/dashboard/frame_tap.py:DashboardPipeline
    # terminal 2: Task Manager (serves /execute_plan)
    ./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager
    # terminal 3: this server, then open http://localhost:8080
    ./scripts/mobile_openarm exec python lessons/09_web_dashboard/server.py

Lesson 04's dashboard (map, poses, cameras, SSE, MJPEG) is reused as is. Added here:
  * POST /api/say         - one user turn -> PlanDialogManager (LLM plan, clarify, confirm) on a worker thread
  * POST /api/task_cancel - cancel the running /execute_plan goal
  * "task" in the SSE snapshot - chat, numbered steps with status, Task Manager feedback
The browser still never talks ROS: text goes in over HTTP, state comes back over the same SSE stream.
"""
import argparse
import importlib.util
import queue
import threading
import time
from pathlib import Path

import rclpy
from flask import jsonify, request, send_from_directory
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from warehouse_interfaces.action import ExecutePlan
from warehouse_lecture.commands.dialog import PlanDialogManager
from warehouse_lecture.commands.plan_parser import PlanParser
from warehouse_lecture.commands.schema import PLACE_KO
from warehouse_lecture.llm.client import LLM
from warehouse_lecture.memory.locations import Locations

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("nav_dashboard", HERE.parent / "04_navigation/dashboard/server.py")
nav_dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nav_dashboard)


class DeskState(nav_dashboard.RobotState):
    """Lesson 04's robot state + the instruction desk (dialog, plan steps, Task Manager feedback)."""

    def __init__(self):
        super().__init__()
        self.plan_client = ActionClient(self, ExecutePlan, "/execute_plan")
        self.task = dict(phase="idle", chat=[], steps=[], feedback=None, result=None, cost=0.0)
        self.goal = None                       # ClientGoalHandle while a plan runs
        self.cancelled = False                 # the user pressed [실행 취소] for this plan
        self.inbox = queue.Queue()             # user turns, handled one at a time
        self.places = Locations()
        self.llm = LLM()
        self.dialog = PlanDialogManager(PlanParser(self.llm), executor=self.execute, speak=self.speak)
        threading.Thread(target=self.work, daemon=True).start()

    def sim(self):
        return round(self.get_clock().now().nanoseconds * 1e-9, 1)

    def chat(self, who, text):
        with self.lock:
            self.task["chat"].append(dict(who=who, text=text, t=self.sim()))
            del self.task["chat"][:-40]

    def set_task(self, **kw):
        with self.lock:
            self.task.update(kw)

    def speak(self, text):
        """PlanDialogManager's voice: every reply (question, confirmation, result) becomes a robot chat line."""
        self.chat("robot", text)
        if self.dialog.pending is not None:                  # a plan waits for yes / no
            self.set_task(phase="confirm", steps=self.step_rows(self.dialog.pending))

    def work(self):
        while True:
            text = self.inbox.get()
            self.set_task(phase="thinking")
            try:
                self.dialog.handle(text)
            except Exception as e:                           # API key, network, Task Manager missing ...
                self.chat("robot", f"오류: {e}")
            with self.lock:
                self.task["cost"] = round(self.llm.session_cost, 4)
                if self.task["phase"] in ("thinking", "running"):
                    self.task["phase"] = "idle"
                if self.task["phase"] == "confirm" and self.dialog.pending is None:
                    self.task["phase"] = "idle"

    def step_rows(self, plan):
        """One row per step for the browser; 'goal' = the location's base_goal so the map can mark it."""
        rows = []
        for s in plan.steps:
            name = s.location.value if s.location else ""
            goal = self.places.goal(name)[:2] if name in self.places.locations else None
            rows.append(dict(text=s.note or s.describe(), action=s.action.value, status="pending",
                             place=PLACE_KO.get(name, name), goal=goal))
        return rows

    def execute(self, plan, text):
        """PlanDialogManager's executor: send the plan to /execute_plan and wait (the ROS thread runs the callbacks)."""
        if not self.plan_client.wait_for_server(timeout_sec=5.0):
            raise RuntimeError("/execute_plan 없음: ./scripts/mobile_openarm exec ros2 run warehouse_lecture task_manager")
        self.cancelled = False
        self.set_task(phase="running", steps=self.step_rows(plan), feedback=None, result=None)
        done = threading.Event()
        box = {}

        def on_feedback(m):
            f = m.feedback
            with self.lock:
                for i, row in enumerate(self.task["steps"]):
                    row["status"] = "done" if i < f.step else "active" if i == f.step else "pending"
                self.task["feedback"] = dict(step=f.step, total=f.total, action=f.action, phase=f.phase, detail=f.detail)

        def on_result(future):
            box["result"] = future.result().result
            done.set()

        def on_goal(future):
            self.goal = future.result()
            if not self.goal.accepted:
                box["rejected"] = True
                done.set()
                return
            self.goal.get_result_async().add_done_callback(on_result)

        self.plan_client.send_goal_async(plan.to_msg(utterance=text), feedback_callback=on_feedback).add_done_callback(on_goal)
        done.wait()
        self.goal = None
        if box.get("rejected"):
            raise RuntimeError("Task Manager 가 계획을 거부했습니다 (다른 계획 실행 중?)")
        r = box["result"]
        with self.lock:
            for i, row in enumerate(self.task["steps"]):
                if i < r.steps_done:
                    row["status"] = "done"
                elif i == r.failed_step:
                    row["status"] = "canceled" if self.cancelled else "failed"
                else:
                    row["status"] = "skipped"
            self.task["result"] = dict(success=r.success, steps_done=r.steps_done, failed_step=r.failed_step, spoken=r.spoken)
        return r

    def snapshot(self):
        s = super().snapshot()
        with self.lock:
            s["task"] = dict(self.task, chat=list(self.task["chat"]), steps=[dict(r) for r in self.task["steps"]])
        return s


def make_app(state):
    app = nav_dashboard.make_app(state)                      # lesson 04 routes: /api/stream, /api/map.png, /camera/<name>.mjpg ...

    def index():
        return send_from_directory(HERE / "static", "index.html")
    app.view_functions["index"] = index                      # same URL "/", this lesson's page

    @app.get("/desk/<path:name>")
    def desk_static(name):
        return send_from_directory(HERE / "static", name)

    @app.post("/api/say")
    def api_say():
        text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
        if not text:
            return jsonify(ok=False, error="빈 문장"), 400
        if state.task["phase"] in ("thinking", "running"):
            return jsonify(ok=False, error="로봇이 아직 이전 지령을 처리하는 중입니다"), 409
        state.chat("user", text)
        state.inbox.put(text)
        return jsonify(ok=True)

    @app.post("/api/task_cancel")
    def api_task_cancel():
        goal = state.goal
        if goal is None:
            return jsonify(ok=False, error="실행 중인 계획 없음"), 409
        state.cancelled = True
        goal.cancel_goal_async()
        state.chat("user", "(취소)")
        return jsonify(ok=True)

    return app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to open it to other PCs on the network")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    state = DeskState()
    executor = SingleThreadedExecutor()
    executor.add_node(state)
    spinner = threading.Thread(target=executor.spin, daemon=True)
    spinner.start()
    print(f"dashboard: http://{'localhost' if a.host in ('127.0.0.1', '0.0.0.0') else a.host}:{a.port}", flush=True)
    try:
        make_app(state).run(host=a.host, port=a.port, threaded=True, use_reloader=False)
    except KeyboardInterrupt:
        pass
    finally:
        if state.goal is not None:
            state.goal.cancel_goal_async()
        executor.shutdown()
        spinner.join(timeout=2)
        state.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
