"""The wrapped cycle: SpriteCook's 12 edited frames (sc/wNN.png) fitted back onto the runner's 208x101 cells, each
scaled to the original frame's height and lined up on the original's bike side so the driver and bike hold steady.
The wraps (SpriteCook's white padding low on the legs) are found in each frame so they can be tinted any color.
    python art/tack_layers/assemble_wraps.py   -> wrapped_cycle.png, wrapped_mask.png, previews"""
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
N, W, H = 12, 208, 101
orig = Image.open(os.path.join(HERE, "..", "..", "mockups", "pixel", "fe12_cycle.png")).convert("RGBA")


def fit(i):
    """The better of the two fits for frame i: the horse's length matched, or the bike's size held."""
    from anchors import drift
    o = orig.crop((i * W, 0, (i + 1) * W, H))
    return min((fit_length(i), fit_rig(i)), key=lambda c: drift(o, c))


def fit_rig(i):
    """The bike held at today's size: one scale from the wheel's width, moved onto today's wheel and saddle height."""
    from anchors import anchors, wheel_w
    o = orig.crop((i * W, 0, (i + 1) * W, H))
    s = Image.open(os.path.join(HERE, "sc", f"w{i:02d}.png")).convert("RGBA"); s = s.crop(s.getbbox())
    k = wheel_w(o) / wheel_w(s)
    s = s.resize((max(1, round(s.width * k)), max(1, round(s.height * k))), Image.NEAREST)
    (ow, op), (sw, sp) = anchors(o), anchors(s)
    dx, dy = round(ow[0] - sw[0]), round((ow[1] + op[1]) / 2 - (sw[1] + sp[1]) / 2)
    cell = Image.new("RGBA", (W, H)); cell.paste(s, (dx, dy), s)
    return cell


def fit_length(i):
    """SpriteCook's frame i on our cell, pinned on steady points so the rig doesn't jump between frames: stretched so
    its wheel and nose land on ours (length), its wheel-to-saddle-pad drop matched (height), then moved onto our wheel."""
    from anchors import anchors, nose
    o = orig.crop((i * W, 0, (i + 1) * W, H))
    s = Image.open(os.path.join(HERE, "sc", f"w{i:02d}.png")).convert("RGBA"); s = s.crop(s.getbbox())
    (ow, op), on = anchors(o), nose(o)
    (sw, sp), sn = anchors(s), nose(s)
    xs, xt = [sw[0], sp[0], sn[0]], [ow[0], op[0], on[0]]                 # length: least squares on wheel, saddle and nose together
    mx, mt = sum(xs) / 3, sum(xt) / 3
    kx = sum((a - mx) * (b - mt) for a, b in zip(xs, xt)) / sum((a - mx) ** 2 for a in xs)
    ky = (op[1] - ow[1]) / (sp[1] - sw[1])
    ky = min(max(ky, kx * .9), kx * 1.1)                                   # never squash the horse more than a little
    s = s.resize((max(1, round(s.width * kx)), max(1, round(s.height * ky))), Image.NEAREST)
    dx, dy = round(mt - mx * kx), round(ow[1] - sw[1] * ky)
    cell = Image.new("RGBA", (W, H)); cell.alpha_composite(s, (dx, dy)) if dx >= 0 and dy >= 0 else cell.paste(s, (dx, dy), s)
    return cell


def settle(cell, i):
    """The frame nudged until its body (back, belly, neck, head, above the legs) overlaps today's best: a small
    scale and shift, so the horse rides as level as the stock runner instead of bobbing."""
    import numpy as np
    o = np.array(orig.crop((i * W, 0, (i + 1) * W, H)))[:, :, 3] > 0
    top, x0 = H * 62 // 100, W // 3
    target = o[:top, x0:]
    best = (-1, cell)
    for k in (.94, .96, .98, 1.0, 1.02, 1.04, 1.06):
        sc = cell.resize((round(W * k), round(H * k)), Image.NEAREST)
        base = Image.new("RGBA", (W, H)); base.paste(sc, (round((W - sc.width) / 2), round(H - sc.height)), sc)   # scaled about the ground line
        a = np.array(base)[:, :, 3] > 0
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                m = np.roll(np.roll(a, dy, 0), dx, 1)[:top, x0:]
                iou = (m & target).sum() / max(1, (m | target).sum())
                if iou > best[0]:
                    best = (iou, (k, dx, dy, base))
    k, dx, dy, base = best[1]
    out = Image.new("RGBA", (W, H)); out.paste(base, (dx, dy), base)
    return out


def steady(cell, i):
    """Today's wheel and driver laid over SpriteCook's: they're the same on every horse, so they never pulse."""
    o = orig.crop((i * W, 0, (i + 1) * W, H)); po, pc = o.load(), cell.load()
    for y in range(H):
        for x in range(70):
            in_wheel = ((x - 30) ** 2 + (y - 75) ** 2) ** .5 <= 27
            in_driver = x < 62 and y < 58
            if in_wheel or in_driver:
                pc[x, y] = po[x, y] if po[x, y][3] else (pc[x, y] if not in_driver else (0, 0, 0, 0))
    return cell


def wraps(cell):
    """The wrap pixels: white to light grey, unsaturated, on the lower legs (below the saddle pad, off the wheel)."""
    m = Image.new("L", cell.size); px, mp = cell.load(), m.load()
    for y in range(int(H * 0.58), H):
        for x in range(30, W):
            p = px[x, y]
            if ((x - 27) ** 2 + (y - 82) ** 2) ** .5 > 24 and p[3] and max(p[:3]) - min(p[:3]) < 38 and sum(p[:3]) > 360:
                mp[x, y] = 255
    return m


def tint(cell, mask, hx):
    c = tuple(int(hx[j:j + 2], 16) for j in (1, 3, 5)); out = cell.copy(); px, mp = out.load(), mask.load()
    for y in range(H):
        for x in range(W):
            if mp[x, y]:
                k = sum(px[x, y][:3]) / 765; px[x, y] = tuple(min(255, int(v * (0.35 + 0.75 * k))) for v in c) + (255,)
    return out


if __name__ == "__main__":
    cells = [steady(settle(fit(i), i), i) for i in range(N)]; masks = [wraps(c) for c in cells]
    for i, m in enumerate(masks):
        assert m.getbbox(), f"frame {i}: no wraps found"
    sheet, msheet = Image.new("RGBA", (W * N, H)), Image.new("L", (W * N, H))
    for i, (c, m) in enumerate(zip(cells, masks)):
        sheet.alpha_composite(c, (i * W, 0)); msheet.paste(m, (i * W, 0))
    sheet.save(os.path.join(HERE, "wrapped_cycle.png")); msheet.save(os.path.join(HERE, "wrapped_mask.png"))
    bg = lambda: Image.new("RGBA", (W, H), (11, 17, 32, 255))
    for name, hx in (("white", None), ("gold", "#f2d233"), ("royal", "#1f4fbf")):
        frames, grid = [], Image.new("RGBA", (W * 4, H * 3), (11, 17, 32, 255))
        for i, (c, m) in enumerate(zip(cells, masks)):
            f = bg(); f.alpha_composite(c if hx is None else tint(c, m, hx))
            grid.alpha_composite(f, ((i % 4) * W, (i // 4) * H))
            frames.append(f.resize((W * 3, H * 3), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
        frames[0].save(os.path.join(HERE, f"wrapped_{name}.gif"), save_all=True, append_images=frames[1:], duration=70, loop=0)
        grid.resize((grid.width * 2, grid.height * 2), Image.NEAREST).save(os.path.join(HERE, f"wrapped_sheet_{name}.png"))
    # side by side with today's runner, so any wobble shows against the stride we have
    pair = []
    for i, c in enumerate(cells):
        f = Image.new("RGBA", (W, H * 2 + 6), (11, 17, 32, 255)); f.alpha_composite(orig.crop((i * W, 0, (i + 1) * W, H))); f.alpha_composite(c, (0, H + 6))
        pair.append(f.resize((W * 3, (H * 2 + 6) * 3), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
    pair[0].save(os.path.join(HERE, "wrapped_vs_today.gif"), save_all=True, append_images=pair[1:], duration=70, loop=0)
    f0 = bg(); f0.alpha_composite(cells[0]); f0.resize((W * 4, H * 4), Image.NEAREST).save(os.path.join(HERE, "wrapped_f0.png"))
    print("assembled", N)
