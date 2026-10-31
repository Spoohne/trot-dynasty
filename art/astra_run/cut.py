"""Cut a 4x3 green-screen grid back into 12 frames at 480x304, keyed, and locked to the original axle."""
import sys
import numpy as np
from PIL import Image
CW, CH, FW, FH = 384, 341, 384, 243; OY = (CH - FH) // 2
def wheel(a):
    d = (a[..., 2] > a[..., 0] + 60) & (a[..., 3] > 0); d[:150] = False; d[:, 170:] = False
    yy, xx = np.nonzero(d); return xx.mean(), yy.mean()
def cut(grid, outdir):
    import os; os.makedirs(outdir, exist_ok=True)
    G = np.array(Image.open(grid).convert("RGB")).astype(int)
    ref = [wheel(np.array(Image.open(f"tack_layers/astra_assets/base/{i:02d}.png").convert("RGBA")).astype(int)) for i in range(12)]
    rx, ry = np.mean([r[0] for r in ref]), np.mean([r[1] for r in ref]); drift = []
    for i in range(12):
        x0, y0 = (i % 4) * CW, (i // 4) * CH + OY - 20
        c = G[y0:y0 + FH + 40, x0:x0 + CW]; r, g, b = c[..., 0], c[..., 1], c[..., 2]
        key = (g > r + 50) & (g > b + 50); c = c.copy(); sp = (g > np.maximum(r, b)) & ~key; c[sp, 1] = np.maximum(r, b)[sp]
        f = Image.fromarray(np.dstack([c, np.where(key, 0, 255)]).astype(np.uint8)).resize((480, round((FH + 40) * 480 / 384)), Image.LANCZOS)
        a = np.array(f); a[..., 3] = np.where(a[..., 3] > 128, 255, 0); f = Image.fromarray(a)
        wx, wy = wheel(a.astype(int)); drift.append((wx, wy))
        out = Image.new("RGBA", (480, 304)); out.paste(f, (round(rx - wx), round(ry - wy)), f); out.save(f"{outdir}/{i:02d}.png")
    print("raw wheel drift x %.1f y %.1f" % (max(d[0] for d in drift) - min(d[0] for d in drift), max(d[1] for d in drift) - min(d[1] for d in drift)))
if __name__ == "__main__":
    cut(sys.argv[1], sys.argv[2])
