"""Publish a simple markdown file as a Confluence child page (storage format), with optional attachments."""
# 사용: set -a; source ../confluence_token.txt; set +a; python3 scripts/publish_confluence.py <md> "<제목>" <parentId> <spaceId> [첨부 png...]
#       갱신: python3 scripts/publish_confluence.py <md> "<제목>" --update <pageId> [첨부 png...]
# 부모 페이지 3683418127 (MuJoCo + ROS2 패키지 구성), spaceId 3419570180 (PD). 지원 문법: ##~#### 제목, 단락, - 목록, 1. 목록, | 표 |, ``` 코드, ![..](png){width=900}, **굵게**, `코드`,\n#   :::info|tip|note|warning|panel 제목 ... ::: (패널), :::cards(2|3) ::card 제목 ... ::: (카드 다단)
import html
import json
import os
import re
import sys
import urllib.request
import base64
from pathlib import Path

BASE = os.environ["CONFLUENCE_URL"].rstrip("/")
AUTH = base64.b64encode(f"{os.environ['CONFLUENCE_EMAIL']}:{os.environ['CONFLUENCE_API_TOKEN']}".encode()).decode()


def request(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {AUTH}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"{}")


def inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


PANELS = {"info": "info", "tip": "tip", "note": "note", "warning": "warning", "panel": "panel"}


def panel(kind, title, body_html, bg=None):
    """Confluence panel macro (info/tip/note/warning) or a titled 'panel' box."""
    params = ""
    if title:
        params += f'<ac:parameter ac:name="title">{html.escape(title, quote=False)}</ac:parameter>'
    if kind == "panel":
        params += f'<ac:parameter ac:name="bgColor">{bg or "#F4F5F7"}</ac:parameter><ac:parameter ac:name="borderColor">#DFE1E6</ac:parameter>'
    return f'<ac:structured-macro ac:name="{PANELS[kind]}">{params}<ac:rich-text-body>{body_html}</ac:rich-text-body></ac:structured-macro>'


def block_end(lines, i, marker=":::"):
    """Index of the closing ':::' for a block opened at i (nesting-aware)."""
    depth, j = 1, i + 1
    while j < len(lines):
        if lines[j].startswith(":::"):
            if lines[j].strip() == ":::":
                depth -= 1
                if depth == 0:
                    return j
            else:
                depth += 1
        j += 1
    raise ValueError(f"unclosed block at line {i + 1}: {lines[i]}")


def cards(body_lines, columns=None):
    """'::card Title' sub-blocks -> a layout section with one panel per cell (2-3 per row)."""
    items, cur = [], None
    for line in body_lines:
        if line.startswith("::card"):
            cur = [line[6:].strip(), []]
            items.append(cur)
        elif cur is not None:
            cur[1].append(line)
    n = columns or (3 if len(items) % 3 == 0 and len(items) >= 3 else 2)
    kind = {2: "two_equal", 3: "three_equal"}[n]
    out = ["<ac:layout>"]
    for k in range(0, len(items), n):
        row = items[k:k + n]
        out.append(f'<ac:layout-section ac:type="{kind}">')
        for title, body in row:
            out.append("<ac:layout-cell>" + panel("panel", title, md_to_storage(chr(10).join(body))) + "</ac:layout-cell>")
        for _ in range(n - len(row)):
            out.append("<ac:layout-cell><p/></ac:layout-cell>")
        out.append("</ac:layout-section>")
    out.append("</ac:layout>")
    return "".join(out)


def md_to_storage(md):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^:::(info|tip|note|warning|panel|cards)(?:\((\d)\))?\s*(.*)$", line)
        if m:
            end = block_end(lines, i)
            body = lines[i + 1:end]
            if m.group(1) == "cards":
                out.append(cards(body, int(m.group(2)) if m.group(2) else None))
            else:
                out.append(panel(m.group(1), m.group(3).strip(), md_to_storage(chr(10).join(body))))
            i = end + 1; continue
        if line.startswith("```"):
            lang = line[3:].strip() or "bash"
            code, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            body = html.escape("\n".join(code), quote=False)
            out.append(f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{lang}</ac:parameter>'
                       f'<ac:plain-text-body><![CDATA[{chr(10).join(code)}]]></ac:plain-text-body></ac:structured-macro>')
            i += 1; continue
        if line.startswith("# "):
            i += 1; continue  # page title comes from the filename/argument
        m = re.match(r"^(#{2,4}) (.*)", line)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>"); i += 1; continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            rows = [r for r in rows if not all(re.fullmatch(r"-+", c) for c in r)]
            head, body = rows[0], rows[1:]
            out.append("<table><tbody><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table>")
            continue
        if line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:]); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>"); continue
        m = re.match(r"^\d+\. (.*)", line)
        if m:
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ol>"); continue
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)(?:\{width=(\d+)\})?", line)
        if m:
            name = Path(m.group(1)).name
            out.append(f'<ac:image ac:width="{m.group(2) or 640}"><ri:attachment ri:filename="{name}"/></ac:image>'); i += 1; continue
        if line.strip():
            para = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|\||- |\d+\. |```|!\[|:::|::card)", lines[i]):
                para.append(lines[i]); i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>"); continue
        i += 1
    return "\n".join(out)


def upload(page_id, path):
    """Attach a PNG; if one with the same name exists, upload a new version of it."""
    p = Path(path)
    boundary = "----claudeboundary"
    data = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{p.name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + p.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "X-Atlassian-Token": "nocheck"}
    existing = request("GET", f"{BASE}/wiki/rest/api/content/{page_id}/child/attachment?filename={p.name}")
    if existing.get("results"):
        att_id = existing["results"][0]["id"]
        request("POST", f"{BASE}/wiki/rest/api/content/{page_id}/child/attachment/{att_id}/data", data, headers)
        print("updated attachment", p.name)
    else:
        request("POST", f"{BASE}/wiki/rest/api/content/{page_id}/child/attachment", data, headers)
        print("attached", p.name)


def main():
    # 사용: publish_confluence.py <md> "<제목>" <parentId> <spaceId> [첨부 png...]        새 하위 페이지
    #       publish_confluence.py <md> "<제목>" --update <pageId> [첨부 png...]           기존 페이지 본문·제목 갱신
    md_file, title = sys.argv[1:3]
    body = md_to_storage(Path(md_file).read_text())
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if sys.argv[3] == "--update":
        page_id = sys.argv[4]
        attachments = sys.argv[5:]
        current = request("GET", f"{BASE}/wiki/api/v2/pages/{page_id}")
        payload = {"id": page_id, "status": "current", "title": title,
                   "body": {"representation": "storage", "value": body},
                   "version": {"number": current["version"]["number"] + 1, "message": "updated by publish_confluence.py"}}
        page = request("PUT", f"{BASE}/wiki/api/v2/pages/{page_id}", json.dumps(payload).encode(), headers)
        print("updated page", page_id, "version", page["version"]["number"], page["_links"]["base"] + page["_links"]["webui"])
    else:
        parent_id, space_id = sys.argv[3:5]
        attachments = sys.argv[5:]
        payload = {"spaceId": space_id, "status": "current", "title": title, "parentId": parent_id,
                   "body": {"representation": "storage", "value": body}}
        page = request("POST", f"{BASE}/wiki/api/v2/pages", json.dumps(payload).encode(), headers)
        page_id = page["id"]
        print("created page", page_id, page["_links"]["base"] + page["_links"]["webui"])
    for path in attachments:
        upload(page_id, path)


if __name__ == "__main__":
    main()
