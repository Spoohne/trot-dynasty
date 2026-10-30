"""SpriteCook's wraps lifted off its edited frame and pasted onto OUR frame at our legs: every wrap pixel is
SpriteCook's, the horse under it is the stock runner. Output is a white tintable layer.
    python art/tack_layers/paste_wraps.py <frame index> <spritecook edit png> [<out layer png>]"""
import math, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "mockups", "pixel", "fe12_cycle.png")
WHEEL, LEGS_Y = (27, 82, 24), 58


def frame(i):
    im = Image.open(SRC).convert("RGBA"); w = im.width // 12
    return im.crop((i * w, 0, (i + 1) * w, im.height))


def spots(f, wheel=WHEEL):
    """Fetlock spots (white markings low on the legs), as centres."""
    px = f.load(); W, H = f.size
    raw = [(x, y) for y in range(LEGS_Y, H) for x in range(W) if px[x, y][3] and min(px[x, y][:3]) > 190
           and math.hypot(x - wheel[0], y - wheel[1]) > wheel[2]]
    out = []
    for x, y in raw:
        if not any(math.hypot(x - a, y - b) < 4 for a, b in out):
            g = [(u, v) for u, v in raw if math.hypot(u - x, v - y) < 4]
            out.append((sum(u for u, _ in g) / len(g), max(v for _, v in g)))
    return out


def blobs(sc):
    """SpriteCook's wraps: the white padded pieces low on the legs, with their grey shading and outline."""
    px = sc.load(); W, H = sc.size
    gear = lambda p: p[3] and max(p[:3]) - min(p[:3]) < 40 and sum(p[:3]) > 330          # white to grey, unsaturated
    wheel = (WHEEL[0] * W / 208, WHEEL[1], WHEEL[2])
    seen, out = set(), []
    for y in range(LEGS_Y, H):
        for x in range(W):
            if (x, y) in seen or not gear(px[x, y]) or math.hypot(x - wheel[0], y - wheel[1]) <= wheel[2]:
                continue
            stack, b = [(x, y)], []
            seen.add((x, y))
            while stack:
                u, v = stack.pop(); b.append((u, v))
                for du in (-1, 0, 1):
                    for dv in (-1, 0, 1):
                        q = (u + du, v + dv)
                        if 0 <= q[0] < W and LEGS_Y <= q[1] < H and q not in seen and gear(px[q]):
                            seen.add(q); stack.append(q)
            if len(b) >= 12:
                out.append(b)
    return out


def paste(i, sc_path):
    f, sc = frame(i), Image.open(sc_path).convert("RGBA")
    sx_scale = f.width / sc.width
    ours = spots(f); layer = Image.new("RGBA", f.size); lp = layer.load(); spx = sc.load()
    for b in blobs(sc):
        bx = sum(u for u, _ in b) / len(b) * sx_scale; by = max(v for _, v in b)       # the wrap's foot, in our frame's x
        if not ours:
            break
        tx, ty = min(ours, key=lambda s: (s[0] - bx) ** 2 + (s[1] - by) ** 2)
        if math.hypot(tx - bx, ty - by) > 14:                                         # no leg of ours there
            continue
        dx, dy = round(tx - bx), round(ty - by)
        for u, v in b:
            x, y = round(u * sx_scale) + dx, v + dy
            if 0 <= x < f.width and 0 <= y < f.height and f.getpixel((x, y))[3]:      # only onto our horse's leg
                g = sum(spx[u, v][:3]) // 3
                lp[x, y] = (g, g, g, 255)
    return f, layer


def tint(layer, hx):
    c = tuple(int(hx[i:i + 2], 16) for i in (1, 3, 5)); out = layer.copy(); px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            if px[x, y][3]:
                k = px[x, y][0] / 255; px[x, y] = tuple(min(255, int(v * k * 1.05)) for v in c) + (255,)
    return out


if __name__ == "__main__":
    i, sc = int(sys.argv[1]), sys.argv[2]
    f, layer = paste(i, sc)
    assert sum(1 for p in layer.get_flattened_data() if p[3]) > 20, "no wraps landed"
    layer.save(sys.argv[3] if len(sys.argv) > 3 else os.path.join(HERE, f"paste_f{i}.png"))
    print("pasted", sum(1 for p in layer.get_flattened_data() if p[3]), "px")
