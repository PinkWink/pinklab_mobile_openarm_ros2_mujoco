#!/usr/bin/env python3
"""Find (and stop) processes left over from an earlier ./scripts/mobile_openarm run.

A process belongs to this workspace when its environment has ROS_HOME=<workspace>/.ros/mobile_openarm
(the wrapper exports it, every launched node inherits it). Typical leftovers after a crash or a closed
terminal: pick_place_server, move_group, nav2 servers, the MuJoCo bridge. A second simulator started next
to them gives two servers for one action name: both execute the same goal and the arm gets two
trajectories at once ("Cannot push a new trajectory while another is being executed").

    python3 scripts/stack_procs.py            # list simulator-stack leftovers, exit 1 if any
    python3 scripts/stack_procs.py --all      # also tools started with `exec` (task_manager, dashboards, ...)
    python3 scripts/stack_procs.py --kill     # stop everything of this workspace (SIGTERM, then SIGKILL)
"""
import argparse
import os
import signal
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
MARKER = f"ROS_HOME={WORKSPACE}/.ros/mobile_openarm".encode()
# Started by `start`/`drive`/... (the launch file); `exec` tools are only reported with --all.
SIM_KEYS = ("ros2 launch", "mobile_openarm_mujoco", "/opt/ros/jazzy/lib/", "/install/mobile_openarm_",
            "/install/warehouse_skills/", "rviz2")
IGNORE = ("_ros2_daemon", "stack_procs.py")


def ours():
    """[(pid, cmdline)] of live processes with this workspace's ROS_HOME, not this process or its parents."""
    skip, pid = set(), os.getpid()
    while pid > 1:                                   # our own ancestry (the wrapper that runs this check)
        skip.add(pid)
        try:
            pid = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    out = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit() or int(d.name) in skip:
            continue
        try:
            if MARKER not in (d / "environ").read_bytes().split(b"\0"):
                continue
            cmd = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:                              # gone, or another user's process
            continue
        if cmd and not any(k in cmd for k in IGNORE):
            out.append((int(d.name), cmd))
    return sorted(out)


def is_sim(cmd):
    return any(k in cmd for k in SIM_KEYS)


def short(cmd, width=110):
    words = cmd.split()
    for i, w in enumerate(words):                    # drop the interpreter: show the node / module name
        if "/lib/" in w or w == "-m" or w.endswith("/ros2"):
            words = words[i + (w == "-m"):]
            break
    text = " ".join(Path(w).name if w.startswith("/") else w for w in words)
    return text if len(text) <= width else text[:width - 3] + "..."


def kill(procs, wait=8.0):
    for pid, _ in procs:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    end = time.monotonic() + wait
    while time.monotonic() < end and any(Path(f"/proc/{p}").exists() for p, _ in procs):
        time.sleep(0.2)
    left = [(p, c) for p, c in procs if Path(f"/proc/{p}").exists()]
    for pid, _ in left:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    return len(procs), len(left)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="exec 로 띄운 도구까지 보기")
    ap.add_argument("--kill", action="store_true", help="이 워크스페이스의 프로세스를 모두 종료")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    procs = ours()
    if a.kill:
        if not procs:
            print("정리할 프로세스가 없습니다.")
            return 0
        for pid, cmd in procs:
            print(f"  종료: {pid:>7}  {short(cmd)}")
        n, forced = kill(procs)
        print(f"{n}개 종료" + (f" (그중 {forced}개는 SIGKILL)" if forced else ""))
        return 0
    shown = procs if a.all else [(p, c) for p, c in procs if is_sim(c)]
    if shown and not a.quiet:
        for pid, cmd in shown:
            print(f"  {pid:>7}  {short(cmd)}")
    return 1 if shown else 0


if __name__ == "__main__":
    sys.exit(main())
