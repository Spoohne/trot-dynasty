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
    """SpriteCook's frame i on our cell: its content scaled to our content's height, left and bottom edges matched."""
    o = orig.crop((i * W, 0, (i + 1) * W, H)); ob = o.getbbox()
    s = Image.open(os.path.join(HERE, "sc", f"w{i:02d}.png")).convert("RGBA"); s = s.crop(s.getbbox())
    k = (ob[3] - ob[1]) / s.height
    s = s.resize((max(1, round(s.width * k)), ob[3] - ob[1]), Image.NEAREST)
    cell = Image.new("RGBA", (W, H)); cell.alpha_composite(s.crop((0, 0, min(s.width, W - ob[0]), s.height)), (ob[0], ob[1]))
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
    cells = [fit(i) for i in range(N)]; masks = [wraps(c) for c in cells]
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
