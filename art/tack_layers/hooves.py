"""How much the hooves change shape through a cycle: each hoof is a near-black blob low on a leg; across the twelve
frames its size and its length-to-width should hold. Lower is steadier.
    python art/tack_layers/hooves.py <sheet.png> [<sheet.png> ...]"""
import sys
import numpy as np
from PIL import Image

W, H, N = 208, 101, 12


def hooves(frame):
    a = np.array(frame.convert("RGBA")).astype(int)
    dark = (a[:, :, 3] > 0) & (a[:, :, :3].sum(2) < 110)
    dark[: int(H * .7)] = False; dark[:, :70] = False
    seen = np.zeros_like(dark); out = []
    for y, x in zip(*np.nonzero(dark)):
        if seen[y, x]:
            continue
        st, pts = [(y, x)], []; seen[y, x] = True
        while st:
            v, u = st.pop(); pts.append((v, u))
            for dv in (-1, 0, 1):
                for du in (-1, 0, 1):
                    q = (v + dv, u + du)
                    if 0 <= q[0] < H and 0 <= q[1] < W and dark[q] and not seen[q]:
                        seen[q] = True; st.append(q)
        if len(pts) >= 6:
            P = np.array(pts, float); ev = np.linalg.eigvalsh(np.cov(P.T)) if len(pts) > 2 else [1, 1]
            out.append((len(pts), (ev[-1] / max(ev[0], .25)) ** .5))
    return out


def score(path):
    im = Image.open(path).convert("RGBA")
    blobs = [b for i in range(N) for b in hooves(im.crop((i * W, 0, (i + 1) * W, H)))]
    areas = np.array([a for a, _ in blobs], float); asp = np.array([r for _, r in blobs], float)
    return dict(hooves=len(blobs), area_spread=round(areas.std() / areas.mean(), 2), shape_spread=round(asp.std() / asp.mean(), 2),
                biggest_vs_median=round(areas.max() / np.median(areas), 1))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, score(p))
