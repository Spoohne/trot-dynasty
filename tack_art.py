"""The Tack Room's horse model: frame 0 of the replay runner with the barn's gear painted on in its two colors.
shortcut: the pieces are pixel masks found on the stock frame (blue tack, wheel geometry, head and leg boxes), not drawn
art; swap each for a SpriteCooked layer sheet when the kit goes into the replay."""
import hashlib, math, os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")
CACHE = os.path.join(ROOT, "mockups", "brand", "emblem", "cache")
WRAPPED = os.path.join(ROOT, "mockups", "pixel", "tack", "wraps12.png")      # SpriteCook's leg wraps on the cycle, and the mask of them
WMASK = os.path.join(ROOT, "mockups", "pixel", "tack", "wraps12_mask.png")
PIECES = ("harness", "mask", "wraps", "bike")
EARS, BAND = 6, 2           # the hood's top rows are its ears; each wrap's top rows its band (the second colors)
_frame, _wrapped = [], []


def frame0():
    if not _frame:
        im = Image.open(FRAME).convert("RGBA")
        _frame.append(im.crop((0, 0, im.width // 12, im.height)))
    return _frame[0]


def wrapped0():
    """Frame 0 in SpriteCook's wraps, and the mask of the wrap pixels."""
    if not _wrapped:
        im, m = Image.open(WRAPPED).convert("RGBA"), Image.open(WMASK).convert("L")
        f = frame0().copy(); f.alpha_composite(im.crop((0, 0, f.width, f.height)))          # frame 0 with the wraps overlay on
        _wrapped.append((f, m.crop((0, 0, f.width, f.height))))
    return _wrapped[0]


def rgb(hx):
    return tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5))


def dye(p, base):
    """The replay's silks dye (paintSilks in replay_hd2d.html): the color scaled by the stock pixel's light, up to 1.3x."""
    l = min(1.3, (p[0] + p[1] + p[2]) / 3 / 70)
    return tuple(min(255, int(c * l)) for c in base) + (p[3],)


def fabric(px, m, W, H, c, pick=None):
    """The replay's wrapTint: dyed like fabric, its light stretched, the color muted a touch, the edges darker.
    pick(x, y, on) may return a second color for some of the masked pixels (the hood's ears, the wraps' band)."""
    soft = lambda c: tuple(v * .88 + sum(c) / 3 * .12 for v in c)
    on = lambda x, y: 0 <= x < W and 0 <= y < H and m[x, y] > 128
    for y in range(H):
        for x in range(W):
            if m[x, y] > 128 and px[x, y][3]:
                k = min(1, max(0, (sum(px[x, y][:3]) / 765 - .45) / .53))
                s = (.5 + .55 * k) * (1 if on(x - 1, y) and on(x + 1, y) and on(x, y - 1) and on(x, y + 1) else .8)
                col = soft((pick and pick(x, y, on)) or c)
                px[x, y] = tuple(min(255, int(v * s)) for v in col) + (255,)


def paint(pieces, cols, c1, c2):
    """pieces: the fitted set; cols: role -> hex (the horse's own) or 'p'/'s' (the barn's primary/secondary).
    Painted with the replay's own formulas, so the model looks as the horse will on the track."""
    col = lambda k: rgb(cols[k]) if str(cols.get(k, "")).startswith("#") else rgb(c1 if cols.get(k, "p") == "p" else c2)
    im = (wrapped0()[0] if "wraps" in pieces else frame0()).copy(); px = im.load(); W, H = im.size
    blue = lambda p: p[3] > 0 and p[2] > p[0] + 40 and p[2] > p[1] + 20
    cx, cy, R = 30, 78, 20.5                                          # the wheel on the stock frame (hub and radius measured)
    hm = None
    if "mask" in pieces:                                              # the hood overlay; the bridle on it turns to leather (leatherStraps)
        hood = Image.open(WRAPPED.replace("wraps12", "hood12")).convert("RGBA").crop((0, 0, W, H)); im.alpha_composite(hood); px = im.load()
        hm = Image.open(WMASK.replace("wraps12", "hood12")).convert("L").crop((0, 0, W, H)).load()
    near_hood = lambda x, y: hm is not None and any(0 <= x + dx < W and 0 <= y + dy < H and hm[x + dx, y + dy] >= 128
                                                    for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2))
    silks = rgb(c1)                                                   # a driver in the barn's colors, for the look
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if not blue(p):
                continue
            if near_hood(x, y):
                l = sum(p[:3]) / 765
                px[x, y] = (int(34 + 70 * l), int(24 + 50 * l), int(18 + 36 * l), p[3])
            elif math.hypot(x - cx, y - cy) <= R:
                px[x, y] = dye(p, col("bike") if "bike" in pieces else silks)
            elif x < 60 and y < 70:
                px[x, y] = dye(p, silks)
            else:
                px[x, y] = dye(p, col("harness") if "harness" in pieces else silks)
    if "bike" in pieces:                                              # the hub in its own color
        for y in range(int(cy) - 4, int(cy) + 5):
            for x in range(int(cx) - 4, int(cx) + 5):
                if 0 <= x < W and 0 <= y < H and px[x, y][3] and math.hypot(x - cx, y - cy) < 3.6:
                    px[x, y] = dye(px[x, y], col("hub"))
    if "mask" in pieces:
        top = min(y for y in range(H) for x in range(W) if hm[x, y] > 128)
        fabric(px, hm, W, H, col("mask"), lambda x, y, on: col("mask2") if y < top + EARS else None)   # the ears in the second color
        shadow = tuple(int(v * .55) for v in col("mask"))             # maskFringe: light specks round the hood go to its shadow
        for y in range(H):
            for x in range(W):
                p = px[x, y]
                if p[3] and hm[x, y] < 128 and sum(p[:3]) / 3 >= 165 and near_hood(x, y):
                    px[x, y] = shadow + (p[3],)
    if "wraps" in pieces:
        fabric(px, wrapped0()[1].load(), W, H, col("wraps"), lambda x, y, on: col("wraps2") if not on(x, y - BAND) else None)   # each wrap's top rows: the band
    return im


def render(pieces, cols, c1, c2):
    """The model's PNG at 3x, cached like the emblems; returns its path under /mock."""
    pieces = tuple(p for p in PIECES if p in pieces)
    key = "tack|" + ",".join(pieces) + "|" + ",".join(f"{k}{v}" for k, v in sorted(cols.items())) + f"|{c1}|{c2}|v23"
    name = hashlib.md5(key.encode()).hexdigest()[:12] + ".png"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        im = paint(pieces, cols, c1, c2)
        im.resize((im.width * 3, im.height * 3), Image.NEAREST).save(path)
    return "/mock/brand/emblem/cache/" + name


if __name__ == "__main__":
    full = render(PIECES, {"bike": "p", "hub": "s"}, "#8e44ad", "#f3f3f3")
    bare = render((), {}, "#8e44ad", "#f3f3f3")
    assert full != bare and os.path.exists(os.path.join(ROOT, full.replace("/mock/", "mockups/")))
    a, b = paint(PIECES, {}, "#8e44ad", "#f3f3f3").load(), paint((), {}, "#8e44ad", "#f3f3f3").load()
    W, H = frame0().size
    assert sum(a[x, y] != b[x, y] for x in range(W) for y in range(H)) > 400, "the kit paints something"
    print("tack art ok")
