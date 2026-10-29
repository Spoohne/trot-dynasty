"""Cut the stylized horse into rig parts: a body (with the tail and upper legs) and, for each of
the four legs, an upper and a lower piece with hinge points. Grey coat, so the game can tint it.

Coordinates are in the 1071x933 horse_a.png. Run from anywhere: writes mockups/rig/*.png + rig.json.
"""
import json, os
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "mockups", "rig")
HIP_Y, OVERLAP = 548, 26          # legs hang from just under the belly line; pieces overlap the body to hide the seam
KNEE = {"fore": 712, "hind": 705}
# each leg: a polygon covering it below the belly, in image coords. Near legs are the left of each pair.
LEGS = {
    "hind_near": [(92, 560), (175, 548), (215, 560), (150, 640), (162, 760), (185, 933), (92, 933)],
    "hind_far": [(175, 548), (300, 548), (290, 640), (240, 760), (290, 933), (185, 933), (162, 760), (150, 640), (215, 560)],
    "fore_near": [(590, 548), (700, 548), (668, 700), (650, 760), (668, 933), (590, 933)],
    "fore_far": [(700, 548), (760, 548), (745, 760), (740, 933), (668, 933), (650, 760), (668, 700)],
}
HINGE = {"hind_near": (165, 565), "hind_far": (230, 565), "fore_near": (640, 565), "fore_far": (705, 565)}


def mask(poly, size):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).polygon(poly, fill=255); return np.asarray(m) > 0


def main():
    os.makedirs(OUT, exist_ok=True)
    im = Image.open(os.path.join(HERE, "horse_a.png")).convert("RGBA")
    a = np.asarray(im).copy()
    H, W = a.shape[:2]
    yy = np.arange(H)[:, None]
    body = a.copy()
    legs_all = np.zeros((H, W), bool)
    rig = {"size": [W, H], "ground": H, "parts": {}}
    for name, poly in LEGS.items():
        m = mask(poly, (W, H)) & (yy >= HIP_Y - OVERLAP)
        legs_all |= m & (yy >= HIP_Y + 6)
        kind = name.split("_")[0]
        knee = KNEE[kind]
        for seg, sel in (("upper", m & (yy < knee + 14)), ("lower", m & (yy >= knee - 14))):
            p = a.copy(); p[~sel, 3] = 0
            ys, xs = np.nonzero(p[..., 3] > 0)
            if not len(xs):
                continue
            x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
            Image.fromarray(p[y0:y1, x0:x1]).save(os.path.join(OUT, f"{name}_{seg}.png"))
            hx, hy = HINGE[name]
            kx = int(np.median(xs[np.abs(ys - knee) < 4])) if np.any(np.abs(ys - knee) < 4) else hx
            pivot = (hx, hy) if seg == "upper" else (kx, knee)
            rig["parts"][f"{name}_{seg}"] = {"at": [int(x0), int(y0)], "pivot": [int(pivot[0]), int(pivot[1])]}
        rig["parts"][f"{name}_upper"]["knee"] = rig["parts"][f"{name}_lower"]["pivot"]
    body[legs_all, 3] = 0
    Image.fromarray(body).save(os.path.join(OUT, "body.png"))
    rig["parts"]["body"] = {"at": [0, 0], "pivot": [0, 0]}
    # the sulky and driver: one piece, the wheel cut out separately so it can spin
    s = Image.open(os.path.join(HERE, "sulky_a.png")).convert("RGBA")
    sa = np.asarray(s).copy()
    cx, cy, r = 207, 562, 205                                  # wheel hub and rim, in sulky_a.png
    yy2, xx2 = np.mgrid[0:sa.shape[0], 0:sa.shape[1]]
    wheel = (xx2 - cx) ** 2 + (yy2 - cy) ** 2 <= r * r
    w = sa.copy(); w[~wheel, 3] = 0
    Image.fromarray(w[cy - r:cy + r, cx - r:cx + r]).save(os.path.join(OUT, "wheel.png"))
    sa_no = sa.copy(); sa_no[wheel, 3] = 0
    Image.fromarray(sa_no).save(os.path.join(OUT, "sulky.png"))
    rig["sulky"] = {"size": [sa.shape[1], sa.shape[0]], "hub": [cx, cy], "r": r, "tip": [1015, 410]}
    json.dump(rig, open(os.path.join(OUT, "rig.json"), "w"), indent=1)
    assert all(os.path.exists(os.path.join(OUT, f"{n}_{s}.png")) for n in LEGS for s in ("upper", "lower")), "every leg has two pieces"
    print("parts:", sorted(rig["parts"]))


if __name__ == "__main__":
    main()
