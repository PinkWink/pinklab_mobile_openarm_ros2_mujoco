#!/usr/bin/env python3
"""Pull a Confluence page (written in the web editor) back into the publisher markdown.

publish_confluence.py 의 반대 방향. 게시본 storage 를 md 로 바꾸고, 그 md 를 다시
md_to_storage 로 변환해 게시본과 정규화 비교(왕복 검사)한 뒤에만 md 를 덮어쓴다.
본문이 참조하는 그림 중 로컬에 없거나 크기가 다른 첨부는 md 옆으로 내려받는다.
그림 설명(alt)은 게시본에 없으므로 기존 md 의 것을 파일명으로 재사용한다.

사용: set -a; source ../confluence_token.txt; set +a
      python3 scripts/pull_confluence.py <pageId> <md>            # 비교만 (기본)
      python3 scripts/pull_confluence.py <pageId> <md> --write    # 왕복 일치 시 md 덮어쓰기 + 그림 받기
      python3 scripts/pull_confluence.py --status <parentId> <md 폴더>   # 하위 페이지별 SAME/DIFF (그림 파일명으로 md 매칭)
옵션: --force  왕복 불일치여도 쓰기 (지원 안 되는 서식이 빠질 수 있음)
"""
import difflib
import html
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_confluence as pc  # noqa: E402

class N:
    def __init__(s, tag, attrs, parent=None): s.tag, s.a, s.kids, s.parent = tag, dict(attrs), [], parent
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True); s.root = N("root", []); s.cur = s.root
    def handle_starttag(s, t, a):
        n = N(t, a, s.cur); s.cur.kids.append(n)
        if t not in ("br",): s.cur = n
    def handle_startendtag(s, t, a): s.cur.kids.append(N(t, a, s.cur))
    def handle_endtag(s, t):
        c = s.cur
        while c is not s.root and c.tag != t: c = c.parent
        if c is not s.root: s.cur = c.parent
    def handle_data(s, d): s.cur.kids.append(d)
    def unknown_decl(s, d):
        if d.startswith("CDATA["): s.cur.kids.append(("CDATA", d[6:]))
WARN = []
def inl(n):
    out = []
    for k in n.kids:
        if isinstance(k, str): out.append(re.sub(r"\s*\n\s*", " ", k))
        elif isinstance(k, tuple): out.append(k[1])
        elif k.tag == "code": out.append("`" + inl(k) + "`")
        elif k.tag in ("strong", "b"): out.append("**" + inl(k) + "**")
        elif k.tag == "br": out.append(" ")
        elif k.tag == "a": out.append("[" + inl(k) + "](" + k.a.get("href", "") + ")")
        elif k.tag in ("p", "span", "ac:inline-comment-marker", "em", "u"):
            if k.tag in ("em", "u"): WARN.append("dropped " + k.tag)
            out.append(inl(k))
        else: WARN.append("inline? " + k.tag); out.append(inl(k))
    return "".join(out)
def param(n, name):
    for k in n.kids:
        if not isinstance(k, (str, tuple)) and k.tag == "ac:parameter" and k.a.get("ac:name") == name: return inl(k)
def child(n, tag):
    for k in n.kids:
        if not isinstance(k, (str, tuple)) and k.tag == tag: return k
def blocks(n, alts):
    out = []
    for k in n.kids:
        if isinstance(k, str):
            if k.strip(): WARN.append("stray text " + k.strip()[:40]); out.append(k.strip())
            continue
        if isinstance(k, tuple): continue
        t = k.tag
        if t in ("h1", "h2", "h3", "h4"): out.append("#" * max(2, int(t[1])) + " " + inl(k).strip())
        elif t == "p":
            if child(k, "ac:image"): out += blocks(k, alts)
            else:
                s = inl(k).strip()
                if s: out.append(s)
        elif t in ("ul", "ol"):
            items = [inl(li).strip() for li in k.kids if not isinstance(li, (str, tuple)) and li.tag == "li"]
            for li in k.kids:
                if not isinstance(li, (str, tuple)) and (child(li, "ul") or child(li, "ol")): WARN.append("nested list")
            out.append("\n".join(("- " if t == "ul" else f"{i+1}. ") + x for i, x in enumerate(items)))
        elif t == "table":
            rows = []
            def trs(x):
                for c in x.kids:
                    if isinstance(c, (str, tuple)): continue
                    if c.tag == "tr": yield c
                    else: yield from trs(c)
            for tr in trs(k):
                rows.append([inl(c).strip() for c in tr.kids if not isinstance(c, (str, tuple)) and c.tag in ("td", "th")])
            lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join("---" for _ in rows[0]) + "|"] + ["| " + " | ".join(r) + " |" for r in rows[1:]]
            out.append("\n".join(lines))
        elif t == "ac:image":
            att = child(k, "ri:attachment"); name = att.a["ri:filename"]
            w = k.a.get("ac:width"); out.append(f"![{alts.get(name, '')}]({name})" + (f"{{width={w}}}" if w else ""))
        elif t == "ac:structured-macro":
            nm = k.a.get("ac:name")
            if nm == "code":
                body = child(k, "ac:plain-text-body"); code = "".join(x[1] for x in body.kids if isinstance(x, tuple))
                out.append("```" + (param(k, "language") or "") + "\n" + code + "\n```")
            elif nm in pc.PANELS:
                title = param(k, "title") or ""; rb = child(k, "ac:rich-text-body")
                out.append(f":::{nm} {title}".rstrip() + "\n" + "\n\n".join(blocks(rb, alts)) + "\n:::")
            else: WARN.append("macro " + nm)
        elif t == "ac:layout":
            WARN.append("layout (cards) not converted")
        else: WARN.append("block? " + t)
    return out
def norm(s):
    s = html.unescape(s)
    s = re.sub(r'</?ac:inline-comment-marker[^>]*>', '', s)
    s = re.sub(r'\s*(ac:local-id|ac:macro-id|ac:schema-version|local-id|data-[a-z-]+|ri:version-at-save|ac:align|ac:layout|ac:original-height|ac:original-width|ac:custom-width|ac:alt)="[^"]*"', '', s)
    s = re.sub(r'\s*/>', '/>', s)
    s = s.replace('<ac:parameter ac:name="language">py</ac:parameter>', '<ac:parameter ac:name="language">python</ac:parameter>')  # web editor alias
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'<li>\s*<p>(.*?)</p>\s*</li>', r'<li>\1</li>', s)
    s = re.sub(r'<(t[hd])>\s*<p>(.*?)</p>\s*</t[hd]>', r'<\1>\2</\1>', s)
    s = re.sub(r'<p>\s*(<ac:image.*?</ac:image>)\s*</p>', r'\1', s)
    s = re.sub(r'<br/>', ' ', s)
    s = re.sub(r'>\s*<', '>\n<', s)
    return [l.strip() for l in s.strip().splitlines()]

def fetch(pid):
    p = pc.request("GET", f"{pc.BASE}/wiki/api/v2/pages/{pid}?body-format=storage")
    return p, p["body"]["storage"]["value"]


def convert(storage, old_md):
    alts = {Path(m.group(2)).name: m.group(1) for m in re.finditer(r"!\[((?:[^\[\]]|\[[^\]]*\])*)\]\(([^)]+)\)", old_md)}
    pre = re.split(r"(?m)^## ", old_md, 1)[0].rstrip()
    WARN.clear()
    p = P(); p.feed(storage)
    return (pre + "\n\n" if pre else "") + "\n\n".join(blocks(p.root, alts)) + "\n"


def diff(md, storage):
    a, b = norm(pc.md_to_storage(md)), norm(storage)
    return [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if not l.startswith(("---", "+++", "@@"))]


def attachments(pid):
    url, out = f"{pc.BASE}/wiki/api/v2/pages/{pid}/attachments?limit=250", {}
    while url:
        r = pc.request("GET", url)
        out.update({a["title"]: a for a in r["results"]})
        nxt = r.get("_links", {}).get("next")
        url = pc.BASE + "/wiki" + nxt.replace("/wiki", "", 1) if nxt else None
    return out


def changed_images(pid, storage, folder):
    atts, out = attachments(pid), []
    for name in sorted(set(re.findall(r'ri:filename="([^"]+)"', storage))):
        a, loc = atts.get(name), folder / name
        if a is None:
            print(f"  WARNING: {name} 은 본문에 있지만 첨부가 없음")
        elif not loc.exists() or loc.stat().st_size != a["fileSize"]:
            out.append((name, a))
    return out


def download(a, path):
    req = urllib.request.Request(pc.BASE + "/wiki" + a["downloadLink"])
    req.add_header("Authorization", f"Basic {pc.AUTH}")
    with urllib.request.urlopen(req) as r:
        path.write_bytes(r.read())


def status(parent, folder):
    mds = {p: set(re.findall(r"\]\(([^)]+\.png)\)", p.read_text())) for p in sorted(folder.glob("*.md"))}
    url = f"{pc.BASE}/wiki/api/v2/pages/{parent}/children?limit=250"
    for k in pc.request("GET", url)["results"]:
        page, storage = fetch(k["id"])
        imgs = set(re.findall(r'ri:filename="([^"]+)"', storage))
        best = max(mds, key=lambda p: len(mds[p] & imgs), default=None)
        if not best or not mds[best] & imgs:
            print(f"{k['id']} v{page['version']['number']:<3} ?    (md 없음) {k['title']}"); continue
        d = diff(best.read_text(), storage)
        print(f"{k['id']} v{page['version']['number']:<3} {'SAME' if not d else 'DIFF':4} {best.name:28} {k['title']}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if "--status" in flags:
        return status(args[0], Path(args[1]))
    pid, md_path = args[0], Path(args[1])
    page, storage = fetch(pid)
    old = md_path.read_text() if md_path.exists() else ""
    print(f"{pid} v{page['version']['number']} {page['title']}")
    print("  현재 md vs 게시본:", "SAME" if not diff(old, storage) else "DIFF")
    md = convert(storage, old)
    d = diff(md, storage)
    print("  왕복 검사:", "OK" if not d else f"{len(d)} 줄 불일치", "| 경고:", sorted(set(WARN)) or "없음")
    for line in d[:20]:
        print("   ", line[:200])
    imgs = changed_images(pid, storage, md_path.parent)
    for name, _ in imgs:
        print(f"  그림 {'변경' if (md_path.parent / name).exists() else '새로'}: {name}")
    if "--write" not in flags:
        print("  (비교만 함, 반영하려면 --write)"); return
    if d and "--force" not in flags:
        sys.exit("  왕복 불일치 → 쓰지 않음 (--force 로 강제)")
    md_path.write_text(md)
    for name, a in imgs:
        download(a, md_path.parent / name)
    print(f"  썼음: {md_path} · 그림 {len(imgs)}장")


if __name__ == "__main__":
    main()
