"""Twelve poses spaced by how far the legs travel, not by time, from one exact stride of a Seedance clip: the legs then
move about the same amount every step, like the stock runner, with no stall and lurch at the loop.
    python art/seedance_even.py <frames_dir> <out_dir>  -> 0000..0011.png, then seedance_loop.py <out_dir> 0 12 1 ...
The stride: the start and length (to a tenth of a frame) whose end best matches its start, in the steady middle of the
clip. The legs' travel: optical flow between consecutive frames in the leg area."""
import os, sys
import cv2
import numpy as np
from seedance_phases import between

N, LEGS = 12, (slice(250, 430), slice(150, 700))       # rows, columns of the clip that hold the legs


def gray(f):
    return np.ascontiguousarray(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)[LEGS])


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
    n = len([f for f in os.listdir(src) if f.endswith(".png")])
    fr = [cv2.imread(os.path.join(src, f"{j:04d}.png")) for j in range(n)]
    g = [gray(f) for f in fr]
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    step = []
    for j in range(n - 1):                                             # leg travel from frame j to j+1
        fl = dis.calc(g[j], g[j + 1], None); m = np.hypot(fl[..., 0], fl[..., 1])
        step.append(float(m[(g[j] > 40) & (g[j] < 215)].mean()))
    cum = np.concatenate([[0], np.cumsum(step)])
    at = lambda t: np.interp(t, np.arange(n), cum)                     # travel so far at (fractional) frame t

    def look(t):                                                       # the leg area at fractional frame t
        j = int(np.floor(t)); a = t - j
        if a < 1e-3:
            return g[j].astype(float)
        return (1 - a) * g[j].astype(float) + a * g[j + 1].astype(float)

    best = None
    for s in np.arange(15, n - 30, .5):                                # steady middle of the clip
        for p in np.arange(9.0, 12.01, .1):                            # the stride length
            if s + p >= n - 1:
                continue
            seam = np.abs(look(s) - look(s + p)).mean()
            if best is None or seam < best[0]:
                best = (seam, s, p)
    seam, s, p = best
    total = at(s + p) - at(s)
    times = []
    for k in range(N):                                                 # equal leg travel between poses
        want = at(s) + total * k / N
        times.append(float(np.interp(want, cum, np.arange(n))))
    for k, t in enumerate(times):
        j = int(np.floor(t)); a = t - j
        img = fr[j] if a < 1e-3 else between(fr[j], fr[j + 1], a, dis)
        cv2.imwrite(os.path.join(out, f"{k:04d}.png"), img)
    print(f"stride start {s} length {p:.1f} frames, seam {seam:.1f}")
    print("pose times", [round(t, 2) for t in times])
