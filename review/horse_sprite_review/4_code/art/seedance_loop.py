"""A Seedance clip turned into the replay's 12-frame runner: one stride's 12 evenly spaced poses (taken from three
strides' worth of frames, so each lands close to its exact phase), the flat grey backdrop keyed out, shrunk to sprite
scale with a reduced palette, and handed to fe_prep's pinning (fix_pace, level at the saddle pad).
    python art/seedance_loop.py <frames_dir> <start> <span> <strides> <out.png>
e.g. python art/seedance_loop.py art/seedance_out/test1_frames 44 32 3 mockups/pixel/tack/sd_fe12.png"""
import os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BG = np.array([128, 128, 128])
N = 12


def pick(start, span, strides):
    """For each of the 12 phases of one stride, the frame in [start, start+span) whose phase is closest."""
    per = span / strides
    out = []
    for k in range(N):
        want = k / N
        best = min(range(start, start + span), key=lambda j: min(abs(((j - start) % per) / per - want), 1 - abs(((j - start) % per) / per - want)))
        out.append(best)
    return out


def key(im):
    """The grey backdrop out at full size: near-grey, unsaturated pixels are backdrop; the horse is the one big shape
    left (specks and stray islands dropped, pinholes filled), so the outline comes out solid."""
    import cv2
    a = np.asarray(im.convert("RGB")).astype(int)
    edge = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3), a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bgc = np.median(edge, 0)                                          # the backdrop's own color, read off the frame's edges
    green = bgc[1] > bgc[0] + 60 and bgc[1] > bgc[2] + 60
    if green:                                                         # a green screen: green-dominant pixels are backdrop
        fg = ~((a[..., 1] > a[..., 0] + 35) & (a[..., 1] > a[..., 2] + 25))
    else:
        d = np.abs(a - bgc).sum(2); sat = a.max(2) - a.min(2)
        fg = ~((d < 42) & (sat < 18))
    fg = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg, 8)
    keep = np.zeros_like(fg)
    for k in range(1, n):
        if stats[k, cv2.CC_STAT_AREA] > 400:                         # the horse, driver and bike, not specks
            keep[lab == k] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    keep = cv2.erode(keep, np.ones((3, 3), np.uint8))               # one pixel off the outline: the compressed, backdrop-tinted edge
    if green:                                                         # any green still bleeding into the edge, pulled back to neutral
        spill = (a[..., 1] > (a[..., 0] + a[..., 2]) / 2 + 10) & (keep > 0)
        a = a.copy(); a[spill, 1] = ((a[spill, 0] + a[spill, 2]) / 2).astype(int)
    rgba = np.dstack([a, keep * 255]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def stock_palette():
    """Today's runner's own colors, so a coat reads the same as the rest of the field."""
    s = Image.open(os.path.join(HERE, "..", "mockups", "pixel", "fe12_cycle.png")).convert("RGBA")
    a = np.asarray(s); px = a[a[..., 3] > 0][:, :3]
    pal = Image.fromarray(px.reshape(-1, 1, 3).astype(np.uint8)).quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    return pal


if __name__ == "__main__":
    fdir, start, span, strides, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    idx = pick(start, span, strides); print("frames:", idx)
    PAL = stock_palette()
    fr = [key(Image.open(os.path.join(fdir, f"{j:04d}.png"))) for j in idx]
    bb = [f.getbbox() for f in fr]
    x0 = min(b[0] for b in bb); y0 = min(b[1] for b in bb); x1 = max(b[2] for b in bb); y1 = max(b[3] for b in bb)
    W = round((x1 - x0) / 2); H = round((y1 - y0) / 2)                  # the still went in at 2x the sprite grid
    sheet = Image.new("RGBA", (W * N, H))
    for i, f in enumerate(fr):
        c = f.crop((x0, y0, x1, y1))
        rgb = c.convert("RGB").resize((W, H), Image.BOX)
        al = c.getchannel("A").resize((W, H), Image.BOX).point(lambda v: 255 if v > 140 else 0)
        q = rgb.quantize(palette=PAL, dither=Image.Dither.NONE).convert("RGB")          # today's colors, no dither speckle
        q.putalpha(al); sheet.paste(q, (i * W, 0))
    raw = out.replace(".png", "_raw.png"); sheet.save(raw)
    pix = os.path.join(HERE, "..", "mockups", "pixel")
    subprocess.run([sys.executable, os.path.join(pix, "fix_pace.py"), os.path.relpath(raw, pix), str(N), os.path.relpath(out, pix), "--bob", "0", "--anchor", "pad"], check=True, cwd=pix)
    print("frame", W, H, "->", out)
