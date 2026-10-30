"""The wrapped runner animated the way the stock one was (frame-engine, fe_prep, fix_pace), fitted into the replay's
208x101 cells at the stock horse's size, wheel on the stock wheel; then its wrap mask and the previews.
    python art/tack_layers/fit_anim.py   -> mockups/pixel/tack/wraps12.png + wraps12_mask.png (candidate), previews here"""
import os
import numpy as np
from PIL import Image
import assemble_wraps as A
from anchors import anchors
from wrap_tint import dye

HERE = os.path.dirname(os.path.abspath(__file__))
PIX = os.path.join(HERE, "..", "..", "mockups", "pixel")
W, H, N = 208, 101, 12
src = Image.open(os.path.join(PIX, "tack", "wraps_fe12.png")).convert("RGBA"); sw = src.width // N
stock = A.orig
area = lambda im: (np.array(im)[:, 70:, 3] > 0).sum()
k = (np.mean([area(stock.crop((i * W, 0, (i + 1) * W, H))) for i in range(N)]) /
     np.mean([area(src.crop((i * sw, 0, (i + 1) * sw, src.height)).resize((W, H))) for i in range(N)])) ** .5
ow = np.mean([anchors(stock.crop((i * W, 0, (i + 1) * W, H)))[0][0] for i in range(N)])
oy = np.mean([anchors(stock.crop((i * W, 0, (i + 1) * W, H)))[0][1] for i in range(N)])
def build(k):
    out = []
    for i in range(N):
        f = src.crop((i * sw, 0, (i + 1) * sw, src.height)).resize((round(W * k), round(H * k)), Image.NEAREST)
        a = anchors(f); c = Image.new("RGBA", (W, H)); c.paste(f, (round(ow - a[0][0]), round(oy - a[0][1])), f); out.append(c)
    return out


for _ in range(2):                                                      # settle the scale on the real fitted frames
    trial = build(k)
    k *= (np.mean([area(stock.crop((i * W, 0, (i + 1) * W, H))) for i in range(N)]) / np.mean([area(c) for c in trial])) ** .5
cells = []
for i in range(N):
    f = src.crop((i * sw, 0, (i + 1) * sw, src.height)).resize((round(W * k), round(H * k)), Image.NEAREST)
    a = anchors(f)
    dx, dy = round(ow - a[0][0]), round(oy - a[0][1])                   # one wheel, same place every frame
    c = Image.new("RGBA", (W, H)); c.paste(f, (dx, dy), f); cells.append(c)
masks = [A.wraps(c) for c in cells]
PAST = 4                                                                # the pastern left bare above the hoof
KEEP = 99                                                               # wrap height from the fetlock up, like the still's pads


def trim(cell, mask):
    """The animation drew the wraps knee-high: keep KEEP px of each from its foot up the leg; the rest becomes the
    bay's black lower leg, its shading kept. And the white the animation left behind the driver becomes dark tail."""
    from overlay_wraps import blobs
    px, mp = cell.load(), mask.load()
    for pts, foot, ax in blobs(cell, mask):
        for u, v in pts:
            t = (u - foot[0]) * ax[0] + (v - foot[1]) * ax[1]
            if t > KEEP + PAST or t < PAST:                              # bare pastern below, bare leg above
                p = px[u, v]; l = sum(p[:3]) / 765
                g = int(4 + 22 * l * l); px[u, v] = (g, g + 3, g + 10, p[3]); mp[u, v] = 0        # the stock runner's blue-black points
    for y in range(28, 60):                                             # behind the driver, ahead of the saddle pad
        for x in range(48, 98):
            p = px[x, y]
            if p[3] and max(p[:3]) - min(p[:3]) < 40 and sum(p[:3]) > 330:
                l = sum(p[:3]) / 765; g = int(4 + 22 * l * l); px[x, y] = (g, g + 3, g + 10, p[3])
    return cell, mask


for c, m in zip(cells, masks):
    trim(c, m)
sheet, msheet = Image.new("RGBA", (W * N, H)), Image.new("L", (W * N, H))
for i, (c, m) in enumerate(zip(cells, masks)):
    sheet.alpha_composite(c, (i * W, 0)); msheet.paste(m, (i * W, 0))
sheet.save(os.path.join(HERE, "anim_cycle.png")); msheet.save(os.path.join(HERE, "anim_mask.png"))
t = Image.fromarray(dye(np.array(sheet), np.array(msheet) > 128, "#1f4fbf"))
frames = []
for i in range(N):
    f = Image.new("RGBA", (W, H * 2 + 6), (58, 38, 26, 255))
    f.alpha_composite(stock.crop((i * W, 0, (i + 1) * W, H))); f.alpha_composite(t.crop((i * W, 0, (i + 1) * W, H)), (0, H + 6))
    frames.append(f.resize((W * 3, f.height * 3), Image.NEAREST).convert("P", palette=Image.ADAPTIVE))
frames[0].save(os.path.join(HERE, "anim_vs_today.gif"), save_all=True, append_images=frames[1:], duration=1000 // 24, loop=0)
g = Image.new("RGBA", (W * 4, H * 3), (58, 38, 26, 255))
for i in range(N):
    g.alpha_composite(t.crop((i * W, 0, (i + 1) * W, H)), ((i % 4) * W, (i // 4) * H))
g.resize((g.width * 2, g.height * 2), Image.NEAREST).save(os.path.join(HERE, "anim_sheet.png"))
print("scale", round(k, 3), "area vs stock", [round(area(c) / area(stock.crop((i * W, 0, (i + 1) * W, H))), 2) for i, c in enumerate(cells)])
