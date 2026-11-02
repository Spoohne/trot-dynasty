"""Watch lab stories in the game's own replay viewer (racegod/engine_lab.py --stories out.json).
    python racegod/replay_server.py <stories.json> [port, default 8115]     then http://127.0.0.1:<port>/"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK = os.path.join(ROOT, "mockups")
KIND = {".html": "text/html; charset=utf-8", ".png": "image/png", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
        ".webp": "image/webp", ".jpg": "image/jpeg", ".mp3": "audio/mpeg", ".wav": "audio/wav"}
STORIES = {}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, kind="application/json", code=200):
        if not isinstance(body, (bytes, str)):
            body = json.dumps(body)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = unquote(self.path.split("?")[0])
        if p == "/":
            rows = "".join(f"<li><a href='/replay/{rid}'>{rid}</a> &middot; {s['track']} &middot; {s['horses'][0]['name']} in {s['final']}</li>" for rid, s in sorted(STORIES.items()))
            return self.send(f"<html><body style='font:15px system-ui;padding:20px'><h2>RaceGod lab replays</h2><ul>{rows}</ul></body></html>", "text/html; charset=utf-8")
        if p.startswith("/race/") and p.endswith(".json"):
            s = STORIES.get(p[6:-5])
            return self.send(s) if s else self.send({"error": "not kept"}, code=404)
        if p.startswith("/replay/"):
            html = open(os.path.join(MOCK, "replay_hd2d.html"), encoding="utf-8").read()
            rid = p[len("/replay/"):]
            return self.send(html.replace("<!--RACE_ID-->null", json.dumps(rid)).replace('"__RACE_ID__"', json.dumps(rid)), "text/html; charset=utf-8")
        if p.startswith("/mock/"):
            path = os.path.normpath(os.path.join(MOCK, p[len("/mock/"):]))
            if path.startswith(MOCK + os.sep) and os.path.isfile(path):
                return self.send(open(path, "rb").read(), KIND.get(os.path.splitext(path)[1], "application/octet-stream"))
        return self.send({"error": "not found"}, code=404)


if __name__ == "__main__":
    STORIES.update(json.load(open(sys.argv[1])))
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8115
    print(f"{len(STORIES)} stories on http://127.0.0.1:{port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
