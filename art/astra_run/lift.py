"""Lift wraps and hood out of Astra's geared frames as overlays + masks, on the axle-locked base frames.
    python art/astra_run/lift.py <base dir of green outputs> <geared dir> <out dir> <n frames>
Base frames come out axle-locked at 480x304; overlays are only the gear pixels; the pixel check is printed."""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

ROOT = r"C:\Users\spooh\HarnessSim"; os.chdir(ROOT)
bdir, gdir, out, N = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
b0 = f"{bdir}/00.png"
CH = Image.open(b0).height if os.path.exists(b0) else 320                      # the canvas height follows the base frames (480 wide)


def wheel(a):
    d = (a[..., 2] > a[..., 0] + 60) & (a[..., 3] > 0); d[:150] = False; d[:, 170:] = False
    yy, xx = np.nonzero(d); return xx.mean(), yy.mean()


def cut(path):
    c = np.array(Image.open(path).convert("RGB")).astype(int)                     # the whole 1024 rows: a nodding head can reach the top
    r, g, b = c[..., 0], c[..., 1], c[..., 2]; key = (g > r + 50) & (g > b + 50); sp = (g > np.maximum(r, b)) & ~key; c[sp, 1] = np.maximum(r, b)[sp]
    a = np.array(Image.fromarray(np.dstack([c, np.where(key, 0, 255)]).astype(np.uint8)).resize((480, round(c.shape[0] * 480 / c.shape[1])), Image.LANCZOS)); a[..., 3] = np.where(a[..., 3] > 128, 255, 0)
    return a


ref = [wheel(np.array(Image.open(f"art/tack_layers/astra_assets/base/{i:02d}.png").convert("RGBA")).astype(int)) for i in range(12)]
rx, ry = np.mean([r[0] for r in ref]), np.mean([r[1] for r in ref])


def lock(a):
    wx, wy = wheel(a.astype(int)); tx, ty = getattr(lock, "target", (rx, ry + 8))        # the geared frame lands on its base frame's wheel
    o = Image.new("RGBA", (480, CH)); fi = Image.fromarray(a); o.paste(fi, (round(tx - wx), round(ty - wy)), fi); return o


for d in ("base", "wraps", "hood", "wraps-mask", "hood-mask"):
    os.makedirs(f"{out}/{d}", exist_ok=True)
bad = 0
for i in range(N):
    bp = f"{bdir}/out_{i:02d}.png"
    if os.path.exists(bp):
        base = lock(cut(bp))
    else:                                                               # frames already keyed and locked (SpriteCook's animation)
        base = Image.open(f"{bdir}/{i:02d}.png").convert("RGBA"); ba = np.array(base); ba[..., 3] = np.where(ba[..., 3] > 128, 255, 0); base = Image.fromarray(ba)
        wx, wy = wheel(ba.astype(int)); lock.target = (wx, wy)
    base.save(f"{out}/base/{i:02d}.png")
    geared = lock(cut(f"{gdir}/out_{i:02d}.png"))
    B, G = np.array(base).astype(int), np.array(geared).astype(int)
    diff = (np.abs(G[..., :3] - B[..., :3]).sum(2) > 40) | ((G[..., 3] > 0) != (B[..., 3] > 0))
    pale = (G[..., :3].sum(2) > 330) & (G[..., :3].max(2) - G[..., :3].min(2) < 55) & (G[..., 3] > 0)
    near = np.array(Image.fromarray((pale * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    gear = diff & near & (G[..., 3] > 0)
    yy, xx = np.mgrid[:CH, :480]; head = (xx > 330) & (yy < CH * .47); legs = (yy > CH * .53) & (xx > 130)
    comp = Image.fromarray(B.astype(np.uint8)); mask_all = np.zeros((CH, 480), bool)
    for name, zone in (("wraps", legs), ("hood", head)):
        m = gear & zone; o = np.zeros((CH, 480, 4), np.uint8); o[m] = G[m]; o[m, 3] = 255
        Image.fromarray(o).save(f"{out}/{name}/{i:02d}.png"); Image.fromarray((m * 255).astype(np.uint8)).save(f"{out}/{name}-mask/{i:02d}.png")
        comp.alpha_composite(Image.fromarray(o)); mask_all |= m
    bad += int(((np.array(comp) != B).any(2) & ~mask_all).sum())
print("frames", N, "pixels changed outside the gear masks:", bad)
