"""Sprite Lab: a local page for assembling the replay's 12-frame wrapped runner from any candidate frames, by eye.
    python art/spritelab/server.py        then open http://127.0.0.1:8120
Serves the page and the pool (build_pool.py), and on Export writes the chosen sheet and its wrap mask into the game
(mockups/pixel/tack/wraps12.png + wraps12_mask.png) and bumps the replay's version. It never deploys."""
import base64, io, json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); ART = os.path.dirname(HERE); ROOT = os.path.dirname(ART)
sys.path.insert(0, os.path.join(ART, "tack_layers"))
POOL = os.path.join(HERE, "pool")
OVL = os.path.join(ART, "tack_layers", "overlays")
W, H = 208, 101
MAX_W = 4096                                                            # some phones won't load a wider image: long sheets go in rows
TYPES = {".html": "text/html; charset=utf-8", ".png": "image/png", ".json": "application/json", ".js": "text/javascript"}


def compose(slots):
    """The 12 chosen frames with each slot's nudge and size, as the game's sheet and mask."""
    n = len(slots); rows = -(-n * W // MAX_W); cols = -(-n // rows)
    sheet, mask = Image.new("RGBA", (W * cols, H * rows)), Image.new("L", (W * cols, H * rows))
    for i, s in enumerate(slots):
        X, Y = (i % cols) * W, (i // cols) * H
        f = Image.open(os.path.join(POOL, s["src"], f"{s['frame']:04d}.png")).convert("RGBA")
        m = Image.open(os.path.join(POOL, s["src"], f"{s['frame']:04d}_m.png")).convert("L")
        k = float(s.get("scale", 1)); dx, dy = int(s.get("dx", 0)), int(s.get("dy", 0))
        if abs(k - 1) > 1e-3:                                          # sized about the hooves' line, like the game's fitting
            bb = f.getbbox() or (0, 0, W, H); cx, by = (bb[0] + bb[2]) / 2, bb[3]
            ox, oy = round(cx - cx * k), round(by - by * k)
            f2, m2 = Image.new("RGBA", (W, H)), Image.new("L", (W, H))
            fs = f.resize((round(W * k), round(H * k)), Image.NEAREST); ms = m.resize(fs.size, Image.NEAREST)
            f2.paste(fs, (ox, oy), fs); m2.paste(ms, (ox, oy)); f, m = f2, m2
        cell = Image.new("RGBA", (W, H)); cell.paste(f, (dx, dy), f); sheet.paste(cell, (X, Y))
        mc = Image.new("L", (W, H)); mc.paste(m, (dx, dy)); mask.paste(mc, (X, Y))
    return sheet, mask, cols


def bump_versions():
    rp = os.path.join(ROOT, "mockups", "replay_hd2d.html"); s = open(rp, encoding="utf-8").read()
    s2 = re.sub(r"tack/\$\{n\}\.png\?v=(\d+)", lambda m_: f"tack/${{n}}.png?v={int(m_.group(1)) + 1}", s)
    if s2 != s:
        open(rp, "w", encoding="utf-8").write(s2)
    ta = os.path.join(ROOT, "tack_art.py"); t = open(ta, encoding="utf-8").read()
    t2 = re.sub(r'\|v(\d+)"', lambda m_: f'|v{int(m_.group(1)) + 1}"', t, count=1)
    if t2 != t:
        open(ta, "w", encoding="utf-8").write(t2)


def wraps_export(overlays, choice):
    """Today's runner plus the chosen overlays; refused unless every pixel outside the wraps is today's."""
    import overlay as O
    ovs, alpha = [], Image.new("L", O.BASE.size)
    for i, d in enumerate(overlays):
        if not d:
            ovs.append(None); continue
        o = Image.open(io.BytesIO(base64.b64decode(d.split(",", 1)[1]))).convert("RGBA")
        if o.size != (W, H):
            raise ValueError("overlay size")
        ovs.append(o); alpha.paste(o.getchannel("A"), (i * W, 0))
    sheet, mask = O.compose(ovs); O.check(sheet, alpha)
    keep = os.path.join(OVL, "exports"); os.makedirs(keep, exist_ok=True)
    n = len([f for f in os.listdir(keep) if f.endswith(".json")]) + 1
    for i, o in enumerate(ovs):
        if o is not None:
            o.save(os.path.join(keep, f"e{n:03d}_f{i + 1:02d}.png"))
    json.dump({"choice": choice}, open(os.path.join(keep, f"e{n:03d}.json"), "w"))
    tack = os.path.join(ROOT, "mockups", "pixel", "tack")
    sheet.save(os.path.join(tack, "wraps12.png")); mask.save(os.path.join(tack, "wraps12_mask.png"))
    json.dump({"frames": N_BASE, "cols": N_BASE}, open(os.path.join(tack, "wraps12.json"), "w"))
    bump_versions()
    return n


N_BASE = 12


def export(slots):
    sheet, mask, cols = compose(slots)
    tack = os.path.join(ROOT, "mockups", "pixel", "tack"); os.makedirs(tack, exist_ok=True)
    keep = os.path.join(HERE, "exports"); os.makedirs(keep, exist_ok=True)
    n = len([f for f in os.listdir(keep) if f.endswith(".json")]) + 1
    json.dump(slots, open(os.path.join(keep, f"export_{n:03d}.json"), "w"), indent=1)   # every export kept, to go back to
    sheet.save(os.path.join(keep, f"export_{n:03d}.png"))
    sheet.save(os.path.join(tack, "wraps12.png")); mask.save(os.path.join(tack, "wraps12_mask.png"))
    json.dump({"frames": len(slots), "cols": cols}, open(os.path.join(tack, "wraps12.json"), "w"))   # the replay reads the length here
    rp = os.path.join(ROOT, "mockups", "replay_hd2d.html"); s = open(rp, encoding="utf-8").read()
    s2 = re.sub(r"tack/\$\{n\}\.png\?v=(\d+)", lambda m_: f"tack/${{n}}.png?v={int(m_.group(1)) + 1}", s)
    if s2 != s:
        open(rp, "w", encoding="utf-8").write(s2)
    ta = os.path.join(ROOT, "tack_art.py"); t = open(ta, encoding="utf-8").read()
    t2 = re.sub(r'\|v(\d+)"', lambda m_: f'|v{int(m_.group(1)) + 1}"', t, count=1)
    if t2 != t:
        open(ta, "w", encoding="utf-8").write(t2)
    return n


class Lab(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, kind="text/html; charset=utf-8", code=200):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code); self.send_header("Content-Type", kind); self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            return self.send(open(os.path.join(HERE, "index.html"), "rb").read())
        if p == "/stock.png":
            return self.send(open(os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png"), "rb").read(), "image/png")
        if p == "/wraps":
            return self.send(open(os.path.join(HERE, "wraps.html"), "rb").read())
        if p.startswith("/overlays/"):
            f = os.path.normpath(os.path.join(OVL, p[len("/overlays/"):]))
            if f.startswith(OVL + os.sep) and os.path.isfile(f):
                return self.send(open(f, "rb").read(), "image/png")
            return self.send(b"", "image/png", 404)
        if p.startswith("/pool/"):
            f = os.path.normpath(os.path.join(POOL, p[len("/pool/"):]))
            if f.startswith(POOL + os.sep) and os.path.isfile(f):
                return self.send(open(f, "rb").read(), TYPES.get(os.path.splitext(f)[1], "application/octet-stream"))
        if p == "/exports":
            keep = os.path.join(HERE, "exports")
            names = sorted(f[:-5] for f in os.listdir(keep) if f.endswith(".json")) if os.path.isdir(keep) else []
            return self.send(json.dumps(names), "application/json")
        if p.startswith("/exports/") and p.endswith(".json"):
            f = os.path.join(HERE, "exports", os.path.basename(p))
            if os.path.isfile(f):
                return self.send(open(f, "rb").read(), "application/json")
        self.send("not found", code=404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path == "/wraps-export":
            ovs = body.get("overlays", [])
            if len(ovs) != N_BASE:
                return self.send(json.dumps({"error": "need 12 frames"}), "application/json", 400)
            try:
                n = wraps_export(ovs, body.get("choice"))
            except (AssertionError, ValueError) as e:
                return self.send(json.dumps({"error": str(e)}), "application/json", 400)
            return self.send(json.dumps({"ok": True, "export": n}), "application/json")
        if self.path == "/export":
            slots = body.get("slots", [])
            if not 8 <= len(slots) <= 32 or any(not s or "src" not in s or "frame" not in s for s in slots):
                return self.send(json.dumps({"error": "fill every pose first"}), "application/json", 400)
            n = export(slots)
            return self.send(json.dumps({"ok": True, "export": n}), "application/json")
        self.send("not found", code=404)


if __name__ == "__main__":
    print("Sprite Lab at http://127.0.0.1:8120")
    ThreadingHTTPServer(("127.0.0.1", 8120), Lab).serve_forever()
