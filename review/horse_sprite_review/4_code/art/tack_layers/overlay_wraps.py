"""Wraps as overlays on the untouched stock runner: each of SpriteCook's wraps is cut from its fitted redraw, turned to
the angle of today's leg and laid along it from the fetlock up. Today's horse never moves, so nothing jitters.
    python art/tack_layers/overlay_wraps.py   -> overlay_cycle.png, overlay_mask.png, previews"""
import math, os
import numpy as np
from PIL import Image
import assemble_wraps as A
from wrap_tint import dye

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, N = 208, 101, 12
WHEEL = (30, 75, 27)


def legs(o):
    """Today's legs: (fetlock x, y, unit axis up the leg) from each white fetlock spot and the dark leg above it."""
    px = o.load()
    off = lambda x, y: math.hypot(x - WHEEL[0], y - WHEEL[1]) > WHEEL[2] + 2
    raw = [(x, y) for y in range(58, H) for x in range(48, W) if px[x, y][3] and min(px[x, y][:3]) > 190 and off(x, y)]
    spots = []
    for x, y in raw:
        if not any(math.hypot(x - a, y - b) < 4 for a, b, *_ in spots):
            g = [(u, v) for u, v in raw if math.hypot(u - x, v - y) < 4]
            spots.append((sum(u for u, _ in g) / len(g), min(v for _, v in g)))
    out = []
    leg = lambda p: p[3] and not (p[2] > p[0] + 40 and p[2] > p[1] + 30)
    for sx, sy in spots:
        up = [(x, y) for y in range(int(sy) - 10, int(sy)) for x in range(int(sx) - 8, int(sx) + 9)
              if 0 <= x < W and 0 <= y < H and leg(px[x, y]) and math.hypot(x - sx, y - sy) <= 9 and off(x, y)]
        if len(up) < 5:
            continue
        mx, my = np.mean([x for x, _ in up]), np.mean([y for _, y in up])
        cov = np.cov(np.array(up, float).T); val, vec = np.linalg.eigh(cov); ax = vec[:, 1]
        if ax[0] * (mx - sx) + ax[1] * (my - sy) < 0:
            ax = -ax
        out.append((sx, sy, ax / np.linalg.norm(ax)))
    return out


def blobs(cell, mask):
    """SpriteCook's wraps in its fitted frame: pieces of the wrap mask, each with its foot and its axis up the leg."""
    m = np.array(mask) > 128; seen = np.zeros_like(m); out = []
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        stack, pts = [(y, x)], []; seen[y, x] = True
        while stack:
            v, u = stack.pop(); pts.append((u, v))
            for dv in (-1, 0, 1):
                for du in (-1, 0, 1):
                    q = (v + dv, u + du)
                    if 0 <= q[0] < H and 0 <= q[1] < W and m[q] and not seen[q]:
                        seen[q] = True; stack.append(q)
        if len(pts) < 12:
            continue
        P = np.array(pts, float); c = P.mean(0); val, vec = np.linalg.eigh(np.cov(P.T)); ax = vec[:, 1]
        if ax[1] > 0:                                                   # pointing up the leg (toward smaller y)
            ax = -ax
        t = (P - c) @ ax
        foot = c + ax * t.min()
        out.append((pts, foot, ax))
    return out


def overlay(i):
    o = A.orig.crop((i * W, 0, (i + 1) * W, H))
    cell = A.size(A.settle(A.fit(i), i), i); mask = A.wraps(cell)
    ours = legs(o)
    out = o.copy(); po = out.load(); cp = cell.load()
    lay = Image.new("L", (W, H)); lp = lay.load()
    used = set()
    for pts, foot, ax in sorted(blobs(cell, mask), key=lambda b: -len(b[0])):
        if not ours:
            break
        k = min(range(len(ours)), key=lambda j: math.hypot(ours[j][0] - foot[0], ours[j][1] - foot[1]))
        sx, sy, tax = ours[k]
        if k in used or math.hypot(sx - foot[0], sy - foot[1]) > 22:
            continue
        used.add(k)
        ang = math.atan2(tax[1], tax[0]) - math.atan2(ax[1], ax[0])     # turn SpriteCook's wrap onto today's leg
        ca, sa = math.cos(ang), math.sin(ang)
        src = {(u, v) for u, v in pts}
        fx, fy = foot
        tx0, ty0 = sx, sy - 1                                          # the wrap's foot just above today's fetlock
        r = 18
        for y in range(int(ty0) - r, int(ty0) + 4):                     # inverse map: every target pixel looks back
            for x in range(int(tx0) - r, int(tx0) + r):
                if not (0 <= x < W and 0 <= y < H):
                    continue
                dx, dy = x - tx0, y - ty0
                u = round(fx + ca * dx + sa * dy); v = round(fy - sa * dx + ca * dy)
                if (u, v) in src:
                    po[x, y] = cp[u, v]; lp[x, y] = 255
    return out, lay


if __name__ == "__main__":
    sheet, msheet = Image.new("RGBA", (W * N, H)), Image.new("L", (W * N, H))
    for i in range(N):
        f, m = overlay(i); sheet.paste(f, (i * W, 0)); msheet.paste(m, (i * W, 0))
        print(i, "legs today", len(legs(A.orig.crop((i * W, 0, (i + 1) * W, H)))), "wrap px", int((np.array(m) > 0).sum()))
    sheet.save(os.path.join(HERE, "overlay_cycle.png")); msheet.save(os.path.join(HERE, "overlay_mask.png"))
    t = Image.fromarray(dye(np.array(sheet), np.array(msheet) > 128, "#1f4fbf"))
    o = A.orig
    frames, grid = [], Image.new("RGBA", (W * 4, H * 3), (58, 38, 26, 255))
    for i in range(N):
        grid.alpha_composite(t.crop((i * W, 0, (i + 1) * W, H)), ((i % 4) * W, (i // 4) * H))
        f = Image.new("RGBA", (W, H * 2 + 6), (58, 38, 26, 255)); f.alpha_composite(o.crop((i * W, 0, (i + 1) * W, H))); f.alpha_composite(t.crop((i * W, 0, (i + 1) * W, H)), (0, H + 6))
        frames.append(f.resize((W * 3, f.height * 3), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
    grid.resize((grid.width * 2, grid.height * 2), Image.NEAREST).save(os.path.join(HERE, "overlay_sheet.png"))
    frames[0].save(os.path.join(HERE, "overlay_vs_today.gif"), save_all=True, append_images=frames[1:], duration=70, loop=0)
    f0 = Image.new("RGBA", (W, H), (58, 38, 26, 255)); f0.alpha_composite(t.crop((0, 0, W, H))); f0.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(HERE, "overlay_f0.png"))
