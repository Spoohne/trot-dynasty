"""Formation sheet for the replay library: every replay's field at six points, top-down (rail at top, leader at right).
    python v5_formations.py [half|mile]      writes v5/library/formations_<key>.png"""
import json, re, sys
import numpy as np
from PIL import Image, ImageDraw

key = sys.argv[1] if len(sys.argv) > 1 else "half"
p = open("v5/library/index.html", encoding="utf-8").read()
races = json.loads(re.search(r"window\.V3 = (\{.*?\});\n", p, re.S).group(1))[key]
cuts = [800, 1320, 2640, 3960, 4700, 5280]
CW, CH, SX, SY = 300, 110, 20, 20                                  # cell px, px per length, px per lane
img = Image.new("RGB", (CW * len(cuts), CH * len(races) + 20), "white"); d = ImageDraw.Draw(img)
COL = ["#d22", "#22d", "#eee", "#2a2", "#000", "#dd2", "#e6e", "#888"]
for c, ft in enumerate(cuts):
    d.text((c * CW + 5, 2), f"{ft} ft", fill="black")
for r, s in enumerate(races):
    P = [np.array(h["path"]).reshape(-1, 2) for h in s["horses"]]
    lead = np.max([q[:, 0] for q in P], 0)
    for c, ft in enumerate(cuts):
        k = int(np.argmax(lead >= ft)); x0, y0 = c * CW, 20 + r * CH
        d.rectangle([x0, y0, x0 + CW - 2, y0 + CH - 2], outline="#999")
        d.line([x0, y0 + 30, x0 + CW, y0 + 30], fill="#bbb")
        for h, q in zip(s["horses"], P):
            bx = x0 + CW - 10 - (lead[k] - q[k, 0]) / 8 * SX; by = y0 + 40 + (q[k, 1] - 4) / 7 * SY
            d.rectangle([bx - 15.5 / 8 * SX, by - 6, bx, by + 6], fill=COL[h["post"] - 1], outline="black")
            d.text((bx - 18, by - 6), str(h["post"]), fill="black" if h["post"] in (3, 6) else "white")
        if c == 0:
            d.text((x0 + 4, y0 + 90), s["title"][17:50], fill="black")
img.save(f"v5/library/formations_{key}.png")
