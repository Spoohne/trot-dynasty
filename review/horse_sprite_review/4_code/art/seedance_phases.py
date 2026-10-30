"""Twelve evenly spaced poses from ONE continuous stride of a Seedance clip, written as 0000..0011.png so
seedance_loop.py can take them in order (start 0, span 12, strides 1).
    python art/seedance_phases.py <frames_dir> <start> <period> <out_dir> nearest|flow
nearest: the closest real frame to each phase (one stride has ~10.7 frames, so one or two repeat).
flow:    each phase made from its two neighbouring frames with optical flow, so all 12 are true in-betweens."""
import os, sys
import cv2
import numpy as np

N = 12


def warp(img, flow, t):
    h, w = flow.shape[:2]
    gx, gy = np.meshgrid(np.arange(w), np.arange(h))
    return cv2.remap(img, (gx + flow[..., 0] * t).astype(np.float32), (gy + flow[..., 1] * t).astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def between(a, b, t, dis):
    """The pose a fraction t of the way from frame a to frame b: each warped toward the other, blended by distance."""
    ga, gb = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
    # one real frame, bent toward the in-between: no cross-fade, so a fast leg never shows twice (ghosting)
    if t <= .5:
        return warp(a, dis.calc(gb, ga, None), t)          # sample a backward along b->a flow
    return warp(b, dis.calc(ga, gb, None), 1 - t)


if __name__ == "__main__":
    src, start, period, out, mode = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
    os.makedirs(out, exist_ok=True)
    rd = lambda j: cv2.imread(os.path.join(src, f"{j:04d}.png"))
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST if False else cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    used = []
    for k in range(N):
        pos = start + k * period / N
        if mode == "nearest":
            j = int(round(pos)); img = rd(j); used.append(j)
        else:
            j = int(np.floor(pos)); t = pos - j
            img = rd(j) if t < 1e-3 else between(rd(j), rd(j + 1), t, dis); used.append(round(pos, 2))
        cv2.imwrite(os.path.join(out, f"{k:04d}.png"), img)
    print(mode, used)
