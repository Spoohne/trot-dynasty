"""Steady points on a runner frame: the bike wheel's centre (its blue disc) and the saddle pad's centre (the white
cloth on the back). Used to line SpriteCook's redrawn frames up with the stock cycle, and to measure drift."""
import math


def anchors(im):
    px = im.load(); W, H = im.size
    wheel = [(x, y) for y in range(H // 2, H) for x in range(W // 3) if px[x, y][3] and px[x, y][2] > px[x, y][0] + 60 and px[x, y][2] > 120]
    pad = [(x, y) for y in range(H // 2) for x in range(W // 3, W * 2 // 3) if px[x, y][3] and min(px[x, y][:3]) > 200]
    if len(wheel) < 20 or len(pad) < 10:
        return None
    c = lambda pts: (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
    return c(wheel), c(pad)


def nose(im):
    """The front of the horse: the rightmost opaque pixel in the head's rows."""
    px = im.load(); W, H = im.size
    for x in range(W - 1, -1, -1):
        for y in range(H // 2):
            if px[x, y][3]:
                return x, y
    return None


def gap(a):
    (wx, wy), (px_, py) = a
    return math.hypot(px_ - wx, py - wy)


def wheel_w(im):
    """The bike wheel's width (its blue disc), the rig's size."""
    px = im.load(); W, H = im.size
    xs = [x for y in range(H // 2, H) for x in range(W // 3) if px[x, y][3] and px[x, y][2] > px[x, y][0] + 60 and px[x, y][2] > 120]
    return max(xs) - min(xs) + 1 if xs else 0


def drift(today, cell):
    """How far a fitted frame sits off today's: wheel, saddle and nose apart, plus the rig's size off."""
    A, B = anchors(today), anchors(cell)
    if not B:
        return 999
    na, nb = nose(today), nose(cell)
    d = sum(abs(A[k][j] - B[k][j]) for k in (0, 1) for j in (0, 1)) + abs(na[0] - nb[0]) + abs(na[1] - nb[1])
    return d + 40 * abs(wheel_w(cell) / wheel_w(today) - 1)


def body(im):
    """The body's outline as a set: opaque pixels above the legs and right of the bike (back, belly, neck, head)."""
    px = im.load(); W, H = im.size
    return {(x, y) for y in range(H * 62 // 100) for x in range(W // 3, W) if px[x, y][3]}


def lines(im):
    """Where the back and the belly sit: top and bottom of the body at three points along it."""
    px = im.load(); W, H = im.size; out = []
    for x in (95, 120, 145):
        ys = [y for y in range(H * 70 // 100) if px[x, y][3]]
        out += [min(ys), max(ys)] if ys else [0, 0]
    return out
