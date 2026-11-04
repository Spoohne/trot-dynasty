"""Astra's head-on sheet (2026-11-03, mockups/pixel/top/astra/front_sheet_src.webp, 4 rows x 3 cols on brown) -> the 12x1
strip for the replay's head-on card (the horse coming straight at the lens). Same keying as slice_astra.py: brown out,
the blue silks kept as they are (the angle cards dye blue), cells cut by the sheet's own pitch.
    python art/top/slice_astra_front.py -> mockups/pixel/top/astra/head12.png (+ preview gif)"""
import os
import numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mockups", "pixel", "top", "astra")
a = np.array(Image.open(os.path.join(D, "front_sheet_src.webp")).convert("RGBA")).astype(int)
bg = a[0, 0, :3]
d = np.abs(a[:, :, :3] - bg).sum(2)
alpha = np.clip((d - 14) / 18, 0, 1)                      # soft key on the flat brown; the coat is a different brown
from scipy import ndimage
hard = d >= 32
closed = ndimage.binary_closing(hard, structure=np.ones((5, 5), bool)) | hard   # the leg fronts are painted in the background's own brown: close the silhouette (radius 2) to keep them
mixed = (alpha > 0.3) & (alpha < 1)                       # edge pixels that are a blend of art and brown: un-mix the brown out (a grey horse would wear a brown rim)
for ch in range(3):
    a[:, :, ch][mixed] = np.clip((a[:, :, ch][mixed] - (1 - alpha[mixed]) * bg[ch]) / alpha[mixed], 0, 255)
alpha = np.where(closed, 1.0, np.where(alpha > 0.3, alpha, 0.0))   # filled pixels go opaque (pure brown ones stay raw: shadow on the leg); faint edge dust is dropped
a[:, :, 3] = (alpha * 255).astype(int)
r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
blue = (b > r + 50) & (b > g + 25)                        # kept blue: the angle cards' paintSilks keys on blue, unlike the overhead's dyeRed
m = d > 40
def bands(idx, gap):
    out = []; s = p = idx[0]
    for i in idx[1:]:
        if i > p + gap: out.append((s, p)); s = i
        p = i
    out.append((s, p)); return out
rows = bands(np.where(m.any(1))[0], 8); cols = bands(np.where(m.any(0))[0], 20)
assert len(rows) == 4 and len(cols) == 3, (rows, cols)
FW, FH = 168, 240                                          # content is ~158 x 231: a little air round it
strip = Image.new("RGBA", (FW * 12, FH)); k = 0
for (y0, y1) in rows:
    for (x0, x1) in cols:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2          # each cell centered on its own content: the sheet's columns aren't on one pitch
        cell = Image.fromarray(a[cy - FH // 2:cy + FH // 2, cx - FW // 2:cx + FW // 2].astype(np.uint8), "RGBA")
        strip.paste(cell, (k * FW, 0)); k += 1
strip.save(os.path.join(D, "head12.png"))
frames = [strip.crop((i * FW, 0, (i + 1) * FW, FH)) for i in range(12)]
pv = [Image.alpha_composite(Image.new("RGBA", f.size, (60, 50, 44, 255)), f).convert("P", palette=Image.ADAPTIVE) for f in frames]
pv[0].save(os.path.join(D, "head12_preview.gif"), save_all=True, append_images=pv[1:], duration=42, loop=0)
print("rows", rows, "cols", cols, "strip", strip.size, "red px", int(blue.sum()))
