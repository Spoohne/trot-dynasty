"""The wraps dyed like fabric, not filled like paint: the stock wrap's shading stretched so its turns and padding show,
the color muted a touch and dimmed to the track lights, the edges darker so the wrap sits on the leg.
Mirrored in the replay (wrapTint in replay_hd2d.html) and the Tack Room model (tack_art.paint): keep the three in step."""
import numpy as np

LO, SPAN = .45, .53          # the stock wrap's light runs about .5 to 1: stretched to the full range
DARK, LIGHT = .5, .55        # dyed light runs DARK..DARK+LIGHT of the color (chosen 2026-10-30, setting B)
MUTE, EDGE = .12, .8         # 12% toward grey; edge pixels at 80%


def dye(rgb_px, mask, hexcol):
    """rgb_px: HxWx4 uint8; mask: HxW bool (wrap pixels). Returns a dyed copy."""
    out = rgb_px.copy(); a = out.astype(float)
    c = np.array([int(hexcol[i:i + 2], 16) for i in (1, 3, 5)], float)
    c = c * (1 - MUTE) + c.mean() * MUTE
    sel = mask & (a[:, :, 3] > 0)
    k = np.clip((a[:, :, :3].mean(2) / 255 - LO) / SPAN, 0, 1)
    s = DARK + LIGHT * k
    edge = np.zeros_like(sel)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        edge |= sel & ~np.roll(np.roll(sel, dy, 0), dx, 1)
    s = np.where(edge, s * EDGE, s)
    out[sel, :3] = np.clip(c[None, :] * s[sel][:, None], 0, 255).astype(np.uint8)
    return out
