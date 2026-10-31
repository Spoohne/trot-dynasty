"""Wire the Astra runner (art/astra_run/final) into the game: game-size sheets, the replay, race data, the Tack Room model."""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = r"C:\Users\spooh\HarnessSim"; os.chdir(ROOT)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12; SRC = sys.argv[2] if len(sys.argv) > 2 else "art/astra_run/final"
CROP = (14, 290)                                                    # source rows kept: the hooves sit on the frame's bottom edge (no floating)
W = 208; H = round((CROP[1] - CROP[0]) * W / 480)


def sheet(layer, mode="RGBA"):
    s = Image.new(mode, (W * N, H))
    for i in range(N):
        f = Image.open(f"{SRC}/{layer}/{i:02d}.png").convert(mode).crop((0, CROP[0], 480, CROP[1])).resize((W, H), Image.LANCZOS)
        if mode == "RGBA":
            a = np.array(f); a[..., 3] = np.where(a[..., 3] > 128, 255, 0); f = Image.fromarray(a)
        else:
            f = f.point(lambda v: 255 if v > 128 else 0)
        s.paste(f, (i * W, 0))
    return s


os.makedirs("mockups/pixel/tack", exist_ok=True)
sheet("base").save("mockups/pixel/astra_cycle.png")
sheet("wraps").save("mockups/pixel/tack/wraps12.png"); sheet("wraps-mask", "L").save("mockups/pixel/tack/wraps12_mask.png")
sheet("hood").save("mockups/pixel/tack/hood12.png"); sheet("hood-mask", "L").save("mockups/pixel/tack/hood12_mask.png")
json.dump({"frames": N, "cols": N, "frame_w": W, "frame_h": H, "overlay": True}, open("mockups/pixel/tack/wraps12.json", "w"))

a = np.array(Image.open("mockups/pixel/astra_cycle.png").convert("RGBA").crop((0, 0, W, H))).astype(int)
def blob(mask):
    lab, n = ndimage.label(mask); k = max(range(1, n + 1), key=lambda k: (lab == k).sum()); ys, xs = np.nonzero(lab == k); return xs, ys
pw = (a[..., :3].min(2) > 200) & (a[..., 3] > 0); pw[:, :95] = False; pw[:, 135:] = False; pw[:int(H * .25)] = False; pw[int(H * .5):] = False
xs, ys = blob(pw); pad = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
gw = (a[..., :3].min(2) > 185) & (a[..., 3] > 0); gw[:, :34] = False; gw[:, 70:] = False; gw[:int(H * .25)] = False; gw[int(H * .45):] = False
xs, ys = blob(gw); hand = (int(xs.mean()), int(ys.mean())); print("pad", pad, "glove", hand, "frame", W, H)
import re
p = "mockups/replay_hd2d.html"; s = open(p, encoding="utf-8").read()
s = re.sub(r"FH = RIG \? 136 : PAINTED \? 213 : \d+", f"FH = RIG ? 136 : PAINTED ? 213 : {H}", s)
s = re.sub(r"PAD = RIG \? \[136, 43, 15, 21\] : PAINTED \? \[210, 58, 34, 40\] : \[[\d, ]+\]", f"PAD = RIG ? [136, 43, 15, 21] : PAINTED ? [210, 58, 34, 40] : {pad}", s)
s = re.sub(r"const HAND = \[\(\d+ / FW - NOSE\) \* LEN_FT, \(1 - \d+ / FH\) \* H_FT\];", f"const HAND = [({hand[0]} / FW - NOSE) * LEN_FT, (1 - {hand[1]} / FH) * H_FT];", s)
s = re.sub(r"astra_cycle\.png\?v=(\d+)", lambda m: f"astra_cycle.png?v={int(m.group(1)) + 1}", s)
s = re.sub(r"tack/\$\{n\}\.png\?v=(\d+)", lambda m: f"tack/${{n}}.png?v={int(m.group(1)) + 1}", s)
open(p, "w", encoding="utf-8").write(s)
t = "tack_art.py"; u = open(t, encoding="utf-8").read(); u2 = re.sub(r'\|v(\d+)"', lambda m: f'|v{int(m.group(1)) + 1}"', u, count=1); open(t, "w", encoding="utf-8").write(u2)
sys.exit(0)                                                           # the one-time code patches below were applied on the first wiring


def patch(path, pairs):
    s = open(path, encoding="utf-8").read()
    for a_, b_ in pairs:
        assert s.count(a_) == 1, (path, a_[:60]); s = s.replace(a_, b_)
    open(path, "w", encoding="utf-8").write(s)


patch("mockups/replay_hd2d.html", [
    ('FH = RIG ? 136 : PAINTED ? 213 : 101, PAD = RIG ? [136, 43, 15, 21] : PAINTED ? [210, 58, 34, 40] : [105, 25, 18, 21]',
     'FH = RIG ? 136 : PAINTED ? 213 : 132, PAD = RIG ? [136, 43, 15, 21] : PAINTED ? [210, 58, 34, 40] : [108, 45, 15, 12]'),
    ('const HAND = [(35 / FW - NOSE) * LEN_FT, (1 - 37 / FH) * H_FT];', f'const HAND = [({hand[0]} / FW - NOSE) * LEN_FT, (1 - {hand[1]} / FH) * H_FT];'),
    (': P("/mock/pixel/fe12_cycle.png"); });', ': P("/mock/pixel/astra_cycle.png?v=1"); });   // the Astra runner: legs from real video, gear as overlays (art/astra_run/final)'),
    ('const wrapLoaded = WRAPS_OK ? Promise.all(["wraps12", "wraps12_mask"].map(n => new Promise(r => { const i = new Image(); i.onload = () => { if (n === "wraps12") wrapImg = i; else wrapMask = i; r(); }; i.onerror = r; i.src = P(`/mock/pixel/tack/${n}.png?v=12`); }))) : Promise.resolve();',
     'let hoodImg = null, hoodMask = null;                                   // the hood overlay and its mask, same sheet layout\n'
     'const GEAR = { wraps12: i => wrapImg = i, wraps12_mask: i => wrapMask = i, hood12: i => hoodImg = i, hood12_mask: i => hoodMask = i };\n'
     'const wrapLoaded = WRAPS_OK ? Promise.all(Object.keys(GEAR).map(n => new Promise(r => { const i = new Image(); i.onload = () => { GEAR[n](i); r(); }; i.onerror = r; i.src = P(`/mock/pixel/tack/${n}.png?v=13`); }))) : Promise.resolve();\n'
     'function overlay(base, layers) {                                        // the coated runner with its gear overlays drawn on, one canvas\n'
     '  const c = document.createElement("canvas"); c.width = base.width; c.height = base.height; const g = c.getContext("2d");\n'
     '  g.drawImage(base, 0, 0); for (const l of layers) if (l) g.drawImage(l, 0, 0); return c;\n'
     '}'),
    ('function wrapTint(c, hex) {\n  if (!wrapMask) return c;\n  if (!wrapTint.m) { const k = document.createElement("canvas"); k.width = wrapMask.width; k.height = wrapMask.height; const kg = k.getContext("2d"); kg.drawImage(wrapMask, 0, 0); wrapTint.m = kg.getImageData(0, 0, k.width, k.height).data; }\n  const m = wrapTint.m, g = c.getContext("2d")',
     'const maskData = new Map();\nfunction wrapTint(c, hex, mask = wrapMask) {                             // mask: which overlay\'s pixels take the color\n  if (!mask || !hex) return c;\n  if (!maskData.has(mask)) { const k = document.createElement("canvas"); k.width = mask.width; k.height = mask.height; const kg = k.getContext("2d"); kg.drawImage(mask, 0, 0); maskData.set(mask, kg.getImageData(0, 0, k.width, k.height).data); }\n  const m = maskData.get(mask), g = c.getContext("2d")'),
    ('    const wr = WRAPS_OK && wrapImg && h.wraps;                                     // in wraps: the wrapped cycle, dyed, then the wraps in its color\n'
     '    const fr = wr ? wrapMeta.frames : FR, cols = wr ? wrapMeta.cols : FR, rows = Math.ceil(fr / cols);   // a wrapped sheet may run longer than 12\n'
     '    const sil = dye(coat(wr ? wrapImg : cycleImg, h.coat), RACE.SILK[i], i + 1, RACE.DARK.includes(i + 1), RACE.PAD[i], FW, PAD, RIG ? [119, 42, 33, 25] : null, fr, cols);\n'
     '    const t = new THREE.CanvasTexture(grit(wr ? wrapTint(sil, h.wraps) : sil, FW, FH));',
     '    const wr = WRAPS_OK && wrapImg && h.wraps, hd = WRAPS_OK && hoodImg && h.mask;   // gear: overlays on the coated runner, each dyed in its own color\n'
     '    const fr = FR, cols = FR, rows = 1;\n'
     '    const sil = dye(overlay(coat(cycleImg, h.coat), [wr && wrapImg, hd && hoodImg]), RACE.SILK[i], i + 1, RACE.DARK.includes(i + 1), RACE.PAD[i], FW, PAD, RIG ? [119, 42, 33, 25] : null, fr, cols);\n'
     '    const t = new THREE.CanvasTexture(grit(wrapTint(wrapTint(sil, wr && h.wraps), hd && h.mask, hoodMask), FW, FH));'),
])
patch("mockups/race.js", [('wraps: h.wraps || "",', 'wraps: h.wraps || "", mask: h.mask || "",')])
patch("app.py", [
    ('                    r["wraps"] = kit_of(h)["wraps"] if h and "wraps" in fitted(h) else ""   # shortcut: the gear it wears now, not on race night',
     '                    r["wraps"] = kit_of(h)["wraps"] if h and "wraps" in fitted(h) else ""   # shortcut: the gear it wears now, not on race night\n'
     '                    r["mask"] = kit_of(h)["mask"] if h and "mask" in fitted(h) else ""'),
])
patch("tack_art.py", [
    ('FRAME = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")', 'FRAME = os.path.join(ROOT, "mockups", "pixel", "astra_cycle.png")'),
    ('        _wrapped.append((im.crop((0, 0, 208, 101)), m.crop((0, 0, 208, 101))))   # frame 0, whatever the sheet\'s length',
     '        f = frame0().copy(); f.alpha_composite(im.crop((0, 0, f.width, f.height)))          # frame 0 with the wraps overlay on\n'
     '        _wrapped.append((f, m.crop((0, 0, f.width, f.height))))'),
    ('    if "mask" in pieces:                                              # over the head, muzzle bare, the ear tips in the other color\n'
     '        other = rgb(cols["mask2"]) if "mask2" in cols else rgb(c2 if cols.get("mask", "p") == "p" else c1)\n'
     '        for y in range(9, 34):\n'
     '            for x in range(176, 201):\n'
     '                p = px[x, y]\n'
     '                if p[3] and ((p[0] > p[1] > p[2] and p[0] > 60) or (sum(p[:3]) < 150 and y < 16)):\n'
     '                    px[x, y] = other + (255,) if y < 15 else shade(p, col("mask"))',
     '    if "mask" in pieces:                                              # the hood overlay, dyed like the wraps\n'
     '        hood = Image.open(WRAPPED.replace("wraps12", "hood12")).convert("RGBA").crop((0, 0, W, H)); im.alpha_composite(hood); px = im.load()\n'
     '        hm, c = Image.open(WMASK.replace("wraps12", "hood12")).convert("L").crop((0, 0, W, H)).load(), col("mask")\n'
     '        for y in range(H):\n'
     '            for x in range(W):\n'
     '                if hm[x, y] > 128 and px[x, y][3]:\n'
     '                    px[x, y] = shade(px[x, y], c)'),
    ('    cx, cy = 27, 82', '    cx, cy = 23, 95'),
    ('            if x < 60 and y < 58:', '            if x < 60 and y < 70:'),
    ('|v14"', '|v15"'),
])
print("patched")
