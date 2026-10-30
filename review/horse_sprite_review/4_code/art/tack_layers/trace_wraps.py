"""Leg wraps traced onto the 12 runner frames as tintable layers: white-on-transparent, the stock pixel's light kept.
Each leg is found by its white fetlock spot; the wrap is the dark leg from that spot up WRAP px, stopping above the
hoof (anything below the spot). The band is the ring BAND px up the wrap, for the second color.
    python art/tack_layers/trace_wraps.py      -> wraps_cycle.png, wraps_band_cycle.png (+ previews)"""
import math, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "mockups", "pixel", "fe12_cycle.png")
N, LEGS_Y, LEGS_X = 12, 60, 48           # frames; the legs live below this row and right of the wheel
WHEEL = (27, 82, 24)                     # the bike wheel: never part of a leg
LEN, HALF, BAND = 14, 2.6, (7, 8)        # wrap length up the leg, half its width, the band's place along it


def trace(f):
    """One wrap per fetlock spot: a straight padded tube up the leg's own axis (found from the dark leg above the spot),
    LEN px long and the leg's width, with wrap lines across it; the hoof below the spot stays bare."""
    W, H = f.size; px = f.load()
    off_wheel = lambda x, y: math.hypot(x - WHEEL[0], y - WHEEL[1]) > WHEEL[2]
    is_spot = lambda p: p[3] and min(p[:3]) > 190
    leg = lambda p: p[3] > 0 and not (p[2] > p[0] + 40 and p[2] > p[1] + 30)   # any horse pixel, not the blue tack
    raw = [(x, y) for y in range(LEGS_Y, H) for x in range(LEGS_X, W) if is_spot(px[x, y]) and off_wheel(x, y)]
    spots = []                                             # one centre per white spot (a spot is a few pixels)
    for x, y in raw:
        if not any(math.hypot(x - a, y - b) < 4 for a, b in spots):
            grp = [(u, v) for u, v in raw if math.hypot(u - x, v - y) < 4]
            spots.append((sum(u for u, _ in grp) / len(grp), sum(v for _, v in grp) / len(grp)))
    wrap = Image.new("RGBA", (W, H)); band = Image.new("RGBA", (W, H)); wp, bp = wrap.load(), band.load()
    for sx, sy in spots:
        up = [(x, y) for y in range(max(LEGS_Y - 20, int(sy) - LEN - 2), int(sy) + 1) for x in range(max(0, int(sx) - LEN), min(W, int(sx) + LEN + 1))
              if leg(px[x, y]) and math.hypot(x - sx, y - sy) <= 8 and y <= sy and off_wheel(x, y)]   # the lower leg alone sets the axis
        if len(up) < 6:
            continue
        mx, my = sum(x for x, _ in up) / len(up), sum(y for _, y in up) / len(up)
        sxx = sum((x - mx) ** 2 for x, _ in up); syy = sum((y - my) ** 2 for _, y in up); sxy = sum((x - mx) * (y - my) for x, y in up)
        ang = 0.5 * math.atan2(2 * sxy, sxx - syy)             # the leg's long axis
        ax, ay = math.cos(ang), math.sin(ang)
        if ax * (mx - sx) + ay * (my - sy) < 0:                # pointing up the leg, away from the hoof
            ax, ay = -ax, -ay
        for y in range(max(0, int(sy) - LEN - 3), min(H, int(sy) + 3)):
            for x in range(max(0, int(sx) - LEN - 3), min(W, int(sx) + LEN + 3)):
                p = px[x, y]
                if not leg(p) or not off_wheel(x, y):
                    continue
                t = (x - sx) * ax + (y - sy) * ay; lat = abs(-(x - sx) * ay + (y - sy) * ax)
                if not (-1 <= t <= LEN and lat <= HALF):
                    continue
                if wp[x, y][3] or bp[x, y][3]:
                    continue
                edge = lat > HALF - 1 or t > LEN - 1 or t < 0 or any(not leg(px[x + dx, y + dy]) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= x + dx < W and 0 <= y + dy < H)
                stripe = int(t + lat * 0.6) % 3 == 0                    # the wrap's turns, a little on the bias
                g = 150 if edge else 205 if stripe else 248
                (bp if BAND[0] <= t <= BAND[1] else wp)[x, y] = (g, g, g, 255)
    return wrap, band


def tint(layer, hx):
    c = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5)); out = layer.copy(); px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            p = px[x, y]
            if p[3]:
                k = p[0] / 255; px[x, y] = tuple(min(255, int(v * k * 1.08)) for v in c) + (255,)
    return out


if __name__ == "__main__":
    im = Image.open(SRC).convert("RGBA"); w = im.width // N
    wraps, bands = Image.new("RGBA", im.size), Image.new("RGBA", im.size)
    frames = []
    for i in range(N):
        f = im.crop((i * w, 0, (i + 1) * w, im.height)); a, b = trace(f)
        assert sum(1 for p in a.get_flattened_data() if p[3]) > 30, f"frame {i}: no wraps found"
        wraps.paste(a, (i * w, 0)); bands.paste(b, (i * w, 0)); frames.append((f, a, b))
    wraps.save(os.path.join(HERE, "wraps_cycle.png")); bands.save(os.path.join(HERE, "wraps_band_cycle.png"))
    # previews: frame 0 big, the twelve as a sheet, the cycle as a gif; gold wraps with a royal band, and plain white
    def dress(f, a, b, c1, c2):
        o = f.copy(); o.alpha_composite(tint(a, c1)); o.alpha_composite(tint(b, c2)); return o
    bg = lambda s: Image.new("RGBA", s, (11, 17, 32, 255))
    for name, c1, c2 in (("gold", "#f2d233", "#1f4fbf"), ("white", "#f3f3f3", "#f3f3f3")):
        f0 = bg((w, im.height)); f0.alpha_composite(dress(*frames[0], c1, c2)); f0.resize((w * 4, im.height * 4), Image.NEAREST).save(os.path.join(HERE, f"wraps_f0_{name}.png"))
        sheet = bg((w * 4, im.height * 3))
        gif = []
        for i, fr in enumerate(frames):
            d = dress(*fr, c1, c2); sheet.alpha_composite(d, ((i % 4) * w, (i // 4) * im.height))
            g = bg((w, im.height)); g.alpha_composite(d); gif.append(g.resize((w * 3, im.height * 3), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(os.path.join(HERE, f"wraps_sheet_{name}.png"))
        gif[0].save(os.path.join(HERE, f"wraps_cycle_{name}.gif"), save_all=True, append_images=gif[1:], duration=70, loop=0, disposal=2)
    print("traced", N, "frames")
