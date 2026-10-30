"""Wrap overlays on today's frozen runner. A candidate frame (inpainted, SpriteCook edit, hand-painted) only ever gives
up its wrap pixels on the lower legs; today's frame is never replaced, so the horse can't change.
    python art/tack_layers/overlay.py <source> <dir with fNN.png candidates>   -> overlays/<source>/fNN.png (RGBA, wraps only)
    python art/tack_layers/overlay.py check <wraps sheet> <mask>              -> fails if any pixel outside the mask moved"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
W, H, N = 208, 101, 12
BASE = Image.open(os.path.join(ROOT, "mockups", "pixel", "fe12_cycle.png")).convert("RGBA")
OUT = os.path.join(HERE, "overlays")


def base(i):
    return BASE.crop((i * W, 0, (i + 1) * W, H))


def zone(b):
    """Where wraps may go: the lower legs (below the knees, right of the sulky, off the wheel), a pixel or two wider for padding."""
    a = np.array(b)[..., 3] > 0
    m = np.zeros_like(a); m[64:, 40:] = a[64:, 40:]
    yy, xx = np.mgrid[:H, :W]; wheel = np.hypot(xx - 30, yy - 75) <= 28
    grown = np.array(Image.fromarray((m & ~wheel).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
    return grown & ~wheel


def align(i, cand):
    """A redrawn candidate (any size) shifted onto today's frame where the silhouettes overlap best."""
    cand = cand.convert("RGBA")
    if cand.size == (W, H):
        return cand
    ba = (np.array(base(i))[..., 3] > 0)[:64]; best = None                # matched on the body: the legs are what changed
    bb = base(i).getbbox(); cb = cand.getbbox()
    for k in np.arange(.94, 1.2, .02):
        c = cand.crop(cb).resize((round((cb[2] - cb[0]) * k), round((cb[3] - cb[1]) * k)), Image.NEAREST)
        for dx in range(-6, 7):
            for dy in range(-4, 5):
                t = Image.new("RGBA", (W, H)); t.paste(c, (bb[0] + dx, bb[3] - c.height + dy)); ta = (np.array(t)[..., 3] > 0)[:64]
                sc = int((ta & ba).sum()) - int((ta ^ ba).sum())
                if best is None or sc > best[0]:
                    best = (sc, t)
    return best[1]


def extract(i, cand):
    """Only the candidate's pixels that differ from today's, inside the leg zone, and only opaque ones (overlays add, never erase)."""
    b, c = np.array(base(i)).astype(int), np.array(cand.convert("RGBA")).astype(int)
    diff = (np.abs(c[..., :3] - b[..., :3]).sum(2) > 30) | (c[..., 3] != b[..., 3])
    pale = (c[..., :3].sum(2) > 330) & (c[..., :3].max(2) - c[..., :3].min(2) < 50) & (c[..., 3] > 0)
    near = np.array(Image.fromarray(pale.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0   # the cloth and its 1-px border only
    take = zone(base(i)) & diff & (c[..., 3] > 0) & near
    o = np.zeros((H, W, 4), np.uint8); o[take] = c[take]; o[take, 3] = 255
    return Image.fromarray(o)


def tint_mask(o):
    """The wrap cloth to recolor: the overlay's pale, unsaturated pixels (its dark border keeps its own color)."""
    a = np.array(o).astype(int); pale = (a[..., :3].sum(2) > 330) & (a[..., :3].max(2) - a[..., :3].min(2) < 50) & (a[..., 3] > 0)
    return Image.fromarray(pale.astype(np.uint8) * 255)


def compose(overlays):
    """Today's sheet with each frame's overlay laid on, plus the tint mask: what the game loads."""
    sheet, mask = BASE.copy(), Image.new("L", BASE.size)
    for i, o in enumerate(overlays):
        if o is None:
            continue
        sheet.alpha_composite(o, (i * W, 0)); mask.paste(tint_mask(o), (i * W, 0))
    return sheet, mask


def check(sheet, overlays_alpha):
    """The milestone rule: same size, and every pixel outside the overlays identical to today's runner."""
    s, b = np.array(sheet.convert("RGBA")), np.array(BASE)
    assert s.shape == b.shape, f"size changed: {s.shape} vs {b.shape}"
    out = ~(np.array(overlays_alpha) > 0)
    bad = (s != b).any(2) & out
    assert not bad.any(), f"{int(bad.sum())} pixels outside the wraps changed"
    return True


if __name__ == "__main__":
    src, d = sys.argv[1], sys.argv[2]
    od = os.path.join(OUT, src); os.makedirs(od, exist_ok=True)
    ovs, alpha = [], Image.new("L", BASE.size)
    for i in range(N):
        p = os.path.join(d, f"f{i + 1:02d}.png")
        if not os.path.exists(p):
            ovs.append(None); continue
        o = extract(i, align(i, Image.open(p))); o.save(os.path.join(od, f"f{i + 1:02d}.png")); ovs.append(o); alpha.paste(o.getchannel("A"), (i * W, 0))
    sheet, mask = compose(ovs); check(sheet, alpha)
    sheet.save(os.path.join(od, "_sheet.png")); mask.save(os.path.join(od, "_mask.png"))
    print(src, sum(o is not None for o in ovs), "overlays; check passed")
