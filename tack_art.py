"""The Tack Room's horse model: frame 0 of the replay's 416 runner (the smoothed sheet the replay draws) with the barn's gear
painted on in its two colors.
shortcut: the pieces are pixel masks found on the stock frame (blue tack, wheel geometry, head and leg boxes), not drawn
art; swap each for a SpriteCooked layer sheet when the kit goes into the replay."""
import hashlib, math, os
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
FRAME = os.path.join(ROOT, "mockups", "pixel", "fe12_cycle416.png")       # 6 across, 2 down, 416x202 a frame
CACHE = os.path.join(ROOT, "mockups", "brand", "emblem", "cache")
WRAPPED = os.path.join(ROOT, "mockups", "pixel", "tack", "wraps12416.png")      # SpriteCook's leg wraps on the cycle, and the mask of them
WMASK = os.path.join(ROOT, "mockups", "pixel", "tack", "wraps12_mask416.png")
PIECES = ("harness", "mask", "wraps")
_frame, _wrapped = [], []


def frame0():
    if not _frame:
        im = Image.open(FRAME).convert("RGBA")
        _frame.append(im.crop((0, 0, im.width // 6, im.height // 2)))
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
    cx, cy, R = 60, 156, 41                                           # the wheel on the stock frame (hub and radius measured on the 208 frame, doubled)
    hm = None
    if "mask" in pieces:                                              # the hood overlay; the bridle on it turns to leather (leatherStraps)
        hood = Image.open(WRAPPED.replace("wraps12", "hood12")).convert("RGBA").crop((0, 0, W, H)); im.alpha_composite(hood); px = im.load()
        hm = Image.open(WMASK.replace("wraps12", "hood12")).convert("L").crop((0, 0, W, H)).load()
    near_hood = lambda x, y: hm is not None and any(0 <= x + dx < W and 0 <= y + dy < H and hm[x + dx, y + dy] >= 128
                                                    for dy in range(-4, 5) for dx in range(-4, 5))
    on_h = "harness" in pieces                                        # Harness: jacket, harness and bike in its first color, helmet stripe in its second
    silks, trim = (col("harness"), col("harness2")) if on_h else (rgb(c1), rgb(c2))   # unfitted: the barn's colors, for the look
    dys = [y for y in range(H) for x in range(120) if blue(px[x, y]) and math.hypot(x - cx, y - cy) > R]
    helmet = min(dys) + .13 * (max(dys) - min(dys)) if dys else -1     # the replay's rule: the top of the driver's blue is his helmet
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if not blue(p):
                continue
            if near_hood(x, y):
                l = sum(p[:3]) / 765
                px[x, y] = (int(34 + 70 * l), int(24 + 50 * l), int(18 + 36 * l), p[3])
            elif x < 120 and y < helmet:
                px[x, y] = dye(p, trim)
            else:
                px[x, y] = dye(p, silks)
    if "mask" in pieces:
        fabric(px, hm, W, H, col("mask"))
        shadow = tuple(int(v * .55) for v in col("mask"))             # maskFringe: light specks round the hood go to its shadow
        for y in range(H):
            for x in range(W):
                p = px[x, y]
                if p[3] and hm[x, y] < 128 and sum(p[:3]) / 3 >= 165 and near_hood(x, y):
                    px[x, y] = shadow + (p[3],)
    if "wraps" in pieces:
        fabric(px, wrapped0()[1].load(), W, H, col("wraps"))
    return im


def render(pieces, cols, c1, c2):
    """The model's PNG at the 416 runner's own size, cached like the emblems; returns its path under /mock."""
    pieces = tuple(p for p in PIECES if p in pieces)
    key = "tack|" + ",".join(pieces) + "|" + ",".join(f"{k}{v}" for k, v in sorted(cols.items())) + f"|{c1}|{c2}|v26"
    name = hashlib.md5(key.encode()).hexdigest()[:12] + ".png"
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        im = paint(pieces, cols, c1, c2)
        im.save(path)                                                  # shown at this size: no nearest-pixel stretch
    return "/mock/brand/emblem/cache/" + name


if __name__ == "__main__":
    full = render(PIECES, {"harness": "#8e44ad", "harness2": "#f3f3f3"}, "#8e44ad", "#f3f3f3")
    bare = render((), {}, "#8e44ad", "#f3f3f3")
    assert full != bare and os.path.exists(os.path.join(ROOT, full.replace("/mock/", "mockups/")))
    a, b = paint(PIECES, {}, "#8e44ad", "#f3f3f3").load(), paint((), {}, "#8e44ad", "#f3f3f3").load()
    W, H = frame0().size
    assert sum(a[x, y] != b[x, y] for x in range(W) for y in range(H)) > 400, "the kit paints something"
    print("tack art ok")
