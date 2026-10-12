"""Screenshot a live web page every few seconds with headless Chrome over the DevTools protocol (no extra packages).

    python3 docs/camp/cdp_capture.py http://localhost:8080 artifacts/dev/l13dash/frames --every 3 --size 1600x1000
Writes f000.png, f001.png, ... until Ctrl+C or --count frames.
"""
import argparse
import base64
import json
import os
import signal
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path


class WebSocket:
    """Just enough RFC 6455 for DevTools: text frames, client masking, no fragmentation on send."""

    def __init__(self, url):
        host, _, path = url[len("ws://"):].partition("/")
        h, _, p = host.partition(":")
        self.s = socket.create_connection((h, int(p)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(f"GET /{path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                       f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.s.recv(1)
        if b" 101 " not in resp.split(b"\r\n")[0]:
            raise RuntimeError(resp.decode(errors="replace"))

    def send(self, text):
        data, mask = text.encode(), os.urandom(4)
        n = len(data)
        head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack(">H", n) if n < 65536 else bytes([0x80 | 127]) + struct.pack(">Q", n))
        self.s.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    def recv(self):
        out = b""
        while True:
            b0, b1 = self._exact(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._exact(8))[0]
            out += self._exact(n)
            if b0 & 0x80:
                return out.decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--every", type=float, default=3.0)
    ap.add_argument("--count", type=int, default=0, help="0 = until Ctrl+C")
    ap.add_argument("--size", default="1600x1000")
    ap.add_argument("--port", type=int, default=9333)
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))   # kill -TERM also closes Chrome
    with socket.socket() as probe:                     # an orphaned Chrome on this port would be reused silently
        if probe.connect_ex(("127.0.0.1", a.port)) == 0:
            raise SystemExit(f"port {a.port} is busy (old headless Chrome?)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    w, h = a.size.split("x")
    profile = tempfile.mkdtemp(prefix="cdp_")
    chrome = subprocess.Popen(["google-chrome", "--headless=new", f"--remote-debugging-port={a.port}", f"--user-data-dir={profile}",
                               f"--window-size={w},{h}", "--hide-scrollbars", "--no-first-run", a.url],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/json"))
                page = next(p for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        ws = WebSocket(page["webSocketDebuggerUrl"])
        msg_id = 0
        i = 0
        while not a.count or i < a.count:
            time.sleep(a.every)
            msg_id += 1
            ws.send(json.dumps({"id": msg_id, "method": "Page.captureScreenshot", "params": {"format": "png"}}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == msg_id:
                    break
            (out / f"f{i:03d}.png").write_bytes(base64.b64decode(m["result"]["data"]))
            print(f"f{i:03d}.png {time.strftime('%H:%M:%S')}", flush=True)
            i += 1
    except KeyboardInterrupt:
        pass
    finally:
        chrome.terminate()
        chrome.wait(timeout=5)


if __name__ == "__main__":
    main()
