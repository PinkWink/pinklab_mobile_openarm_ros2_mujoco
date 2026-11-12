"""Terminal captures for the lesson-15 (⑭ Final Mission) page, filtered from the real logs of 2026-11-12
(gpt-4.1-mini). Kept: dialog, the confirmation step list, each step's start line, detect result, result line,
spoken sentence and the [world] table. Dropped: the repeated ">> plan" block and PickPlace detail lines
("남은 거리", "visual dock", ...). Output: docs/camp/lesson15_cli_*.png

    python3 docs/camp/render_lesson15_terminals.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from render_terminal import render  # noqa: E402

D = Path("artifacts/dev/l14")
OUT = "docs/camp/"
P, O = "prompt", "out"
EX = "./scripts/mobile_openarm exec python lessons/10_final_project/"


def strip(lines):
    return [l.rstrip("\n") for l in lines if "[WARN]" not in l]


# 01_world_plan: both modes, as printed
lines = strip(open(D / "01_final.log"))
render([(P, EX + "01_world_plan.py")] + [(O, l) for l in lines],
       OUT + "lesson15_cli_world_plan.png", width=19.0, highlight=("== ", "XX", "none :", "world:"))


def scenario(n):
    """Scenario n of final_run2.log, filtered."""
    text = strip(open(D / "final_run2.log"))
    start = next(i for i, l in enumerate(text) if l.startswith(f"===== 시나리오 {n}"))
    end = next((i for i, l in enumerate(text) if i > start and l.startswith("===== ")), len(text))
    world_before = [l for l in text[:start] if l.startswith("[world]")][-1]
    out, in_plan = [world_before, ""], False
    for l in text[start:end]:
        s = l.strip()
        if s.startswith(">> plan"):
            in_plan = True
            continue
        if in_plan and re.match(r"^\d\. ", s):
            continue
        in_plan = False
        if (l.startswith(("=====", "[user]", "[robot]", "[world]", "진행할까요?")) or re.match(r"^\d\. ", l)
                or "/start]" in l or ("detect/detect] " in l and " at (" in l) or s.startswith("<<") or s.startswith("말하기")):
            out.append(l)
    return out


for n in (1, 2, 3):
    render([(O, l) for l in scenario(n)], OUT + f"lesson15_cli_s{n}.png", width=15.0,
           highlight=("[world]", "/start]", "<< SUCCEEDED", "[robot]"))

lines = [l for l in strip(open(D / "dry_s3.log")) if l.strip()]
render([(P, EX + "02_final_mission.py --dry-run --scenario 3")] + [(O, l) for l in lines],
       OUT + "lesson15_cli_dry.png", width=15.0, highlight=("[robot]", "[world]"))

refused = strip(open(D / "start_refused.log"))
stopped = strip(open(D / "stop.log"))
render([(P, "./scripts/mobile_openarm start")] + [(O, l) for l in refused] + [(P, "./scripts/mobile_openarm stop")] + [(O, l) for l in stopped],
       OUT + "lesson15_cli_stop.png", width=15.0, highlight=("남아 있습니다", "개 종료"))
print("saved lesson15_cli_*.png")
