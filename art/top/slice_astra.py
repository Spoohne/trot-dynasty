"""Astra's overhead sheet (2026-11-03, mockups/pixel/top/astra/sheet_src.webp, 4 rows x 3 cols on brown) -> the 12x1 strip
the replay's blimp view takes. Keys the brown out, moves the blue silks/sulky onto the red dye key (dyeRed in the replay
dyes red pixels to each horse's silks), slices by the sheet's own cell pitch so Astra's alignment is kept.
    python art/top/slice_astra.py -> mockups/pixel/top/astra/cycle12.png (+ preview)"""
import os
import numpy as np
from PIL import Image
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mockups", "pixel", "top", "astra")
a = np.array(Image.open(os.path.join(D, "sheet_src.webp")).convert("RGBA")).astype(int)
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
blue = (b > r + 50) & (b > g + 25)                          # silks, helmet trim and sulky: blue in the sheet, red for the dye key
lum = (0.3 * r + 0.59 * g + 0.11 * b)[blue]
a[blue, 0], a[blue, 1], a[blue, 2] = np.clip(lum * 1.6 + 40, 0, 255).astype(int), 0, 0   # pure red: the replay's dye keeps the brightness (l = r / 200)
COLS, ROWS = (26, 545, 1064), (59, 309, 560, 811)         # measured cell origins; pitch 519 x ~251
FW, FH = 480, 160
strip = Image.new("RGBA", (FW * 12, FH))
k = 0
for y in ROWS:
    for x in COLS:
        cell = Image.fromarray(a[y - 4:y - 4 + FH, x - 4:x - 4 + FW].astype(np.uint8), "RGBA")
        strip.paste(cell, (k * FW, 0)); k += 1
strip.save(os.path.join(D, "cycle12.png"))
frames = [strip.crop((i * FW, 0, (i + 1) * FW, FH)) for i in range(12)]
pv = [Image.alpha_composite(Image.new("RGBA", f.size, (60, 50, 44, 255)), f).convert("P", palette=Image.ADAPTIVE) for f in frames]
pv[0].save(os.path.join(D, "cycle12_preview.gif"), save_all=True, append_images=pv[1:], duration=42, loop=0)
bb = [f.getbbox() for f in frames]
print("strip", strip.size, "frame", FW, FH, "content bbox range x", min(b[0] for b in bb), max(b[2] for b in bb), "y", min(b[1] for b in bb), max(b[3] for b in bb), "red px", int(blue.sum()))
