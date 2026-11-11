"""pip check 를 강의 의존 트리 기준으로 판정한다.

venv 를 --system-site-packages 로 만들기 때문에 pip check 는 Ubuntu apt 패키지끼리의 충돌
(예: apt yt-dlp 2024.04 가 websockets>=12 를 요구하지만 apt websockets 는 10.4)까지 보고한다.
이런 충돌은 강의와 무관하므로 경고만 하고, 강의에 영향을 주는 충돌만 오류로 판정한다.

ERROR: 강의 의존 트리 안의 패키지가 깨졌거나, venv 에 설치된 패키지가 얽힌 충돌
WARN:  강의 의존 트리 밖 apt 패키지끼리의 충돌, 해석할 수 없는 pip check 출력

    python scripts/check_pip_deps.py requirements-mobile-openarm.txt requirements-lecture.txt

종료 코드 0 = 통과, 1 = 오류. doctor.py 도 check() 를 가져다 쓴다.
"""
import importlib.metadata as md
import re
import subprocess
import sys

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")
CONFLICT = re.compile(r"(\S+) \S+ (?:has requirement|requires) ([A-Za-z0-9_.\-]+)")


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def requirement_names(paths):
    names = set()
    for path in paths:
        for line in open(path, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line and not line.startswith("-"):
                names.add(norm(NAME.match(line)[0]))
    return names


def closure(roots, dists):
    seen, stack = set(), list(roots)
    while stack:
        name = stack.pop()
        if name in seen or name not in dists:
            continue
        seen.add(name)
        for req in dists[name].requires or []:
            if not re.search(r"extra\s*==", req):
                stack.append(norm(NAME.match(req)[0]))
    return seen


def check(req_files, out=print):
    """Return (errors, warnings) as lists of pip check lines."""
    dists = {}
    for d in md.distributions():
        name = d.metadata["Name"]
        if name:  # 메타데이터가 깨진 배포판은 건너뛴다
            dists.setdefault(norm(name), d)
    used = closure(requirement_names(req_files), dists)

    def in_venv(name):
        d = dists.get(name)
        return d is not None and str(d.locate_file("")).startswith(sys.prefix)

    proc = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    errors, warnings = [], []
    lines = [l for l in proc.stdout.splitlines() if l.strip() and not l.startswith("No broken requirements")]
    if proc.returncode != 0 and not lines:
        # pip check 자체가 실패(출력 없음) → 판정 불가이므로 오류로 본다.
        errors.append("pip check 실행 실패: " + (proc.stderr.strip() or f"exit {proc.returncode}"))
        out("ERROR:", errors[-1])
    for line in lines:
        m = CONFLICT.match(line)
        if not m:
            warnings.append(line)
            out("WARN (해석할 수 없는 pip check 출력):", line)
            continue
        requirer, required = norm(m[1]), norm(m[2])
        if requirer in used or in_venv(requirer) or in_venv(required):
            errors.append(line)
            out("ERROR:", line)
        else:
            warnings.append(line)
            out("WARN (강의 의존 트리 밖 apt 패키지끼리 충돌, 무시):", line)
    return errors, warnings


def main():
    errors, _ = check(sys.argv[1:])
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
