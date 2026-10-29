# exec inside Blender right after build_horse.py (same namespace: K, X0, GROUND, P, LEGS). Poses the four legs as
# 12 shape keys f00..f11 copied from the approved mockups/pixel/fe12_cycle.png.
# Traced per frame in race_b pixels (fe12 frames scaled x46/39 onto race_b's wheel; frame 0 lands on race_b exactly):
# for the near fore and near hind, the white coronet's center and the toe. The far legs are the same legs half a
# cycle (6 frames) on, as a pacer's lateral pairs alternate. Each leg is solved with fixed bone lengths (2-bone IK,
# knee bending forward, hock back), so nothing stretches from frame to frame. The body stays pinned, like fe12.
import math
from mathutils import Vector

NEAR = {  # frame: (coronet center, toe)
    "fore": [((228, 156), (237, 165)), ((216, 166), (226, 172)), ((196, 168), (205, 174)), ((160, 169), (169, 174)),
             ((141, 169), (150, 175)), ((131, 167), (138, 175)), ((126, 160), (112, 165)), ((146, 155), (136, 160)),
             ((166, 157), (155, 161)), ((188, 156), (180, 161)), ((195, 153), (187, 158)), ((216, 151), (214, 160))],
    "hind": [((160, 160), (170, 166)), ((147, 168), (156, 174)), ((128, 170), (137, 175)), ((103, 170), (112, 175)),
             ((98, 163), (104, 172)), ((100, 156), (90, 160)), ((112, 151), (103, 155)), ((128, 149), (120, 153)),
             ((145, 150), (140, 156)), ((157, 153), (158, 160)), ((163, 156), (170, 162)), ((163, 158), (172, 165))],
}
FORE_TOP, ELBOW_R, HIND_TOP = Vector((182, 112)), 14.6, Vector((124, 98))   # shoulder; hind pivots at the hip joint
HALF_BAND, HOOF = 3.9, 6.4                     # white band half-length (fetlock..coronet), coronet..toe, in sprite px
V = lambda p: Vector(p)

def ends(c, t):
    """fetlock, coronet, toe along the hoof-pastern axis through the traced white band."""
    c, t = V(c), V(t); u = (c - t).normalized()
    return c + u * HALF_BAND, c - u * HALF_BAND, c - u * (HALF_BAND + HOOF)
def elbow(f):
    down = Vector((0, 1)); return FORE_TOP + (down * .3 + (f - FORE_TOP).normalized() * .7).normalized() * ELBOW_R  # the elbow swings with the leg
def ik(a, t, l1, l2, front):
    d = t - a; L = min(max(d.length, abs(l1 - l2) + 1e-3), l1 + l2 - 1e-3); u = d.normalized()
    x = (l1 * l1 - l2 * l2 + L * L) / (2 * L); h = math.sqrt(max(0, l1 * l1 - x * x)); n = Vector((-u.y, u.x))
    ks = (a + u * x + n * h, a + u * x - n * h)
    return (max if front else min)(ks, key=lambda k: k.x), a + u * L
# bone lengths are race_b's own (frame 0 as approved). When a frame needs more reach, the elbow / hip moves toward
# the hoof (the shoulder and pelvis swinging) instead of the bones stretching or the knee folding.
BONES = {"fore": (27.8, 22.6), "hind": (48.0, 20.1)}
MAX_SHIFT = 12
def reach_from(base, f, kind):
    l1, l2 = BONES[kind]; d = f - base; over = d.length - (l1 + l2 - .5)
    return base + d.normalized() * min(max(over, 0), MAX_SHIFT) if over > 0 else base

def straighten(e, f):
    """A nearly straight fore (within 12 px of full reach) is made straight by rotating the elbow round the shoulder
    (up to 35 deg), not by kinking the knee; a leg folded in flight keeps its default elbow."""
    L = sum(BONES["fore"]) - 1
    if (f - e).length < L - 12: return e
    a0 = math.atan2(e.y - FORE_TOP.y, e.x - FORE_TOP.x)
    cands = [FORE_TOP + Vector((math.cos(a0 + math.radians(d)), math.sin(a0 + math.radians(d)))) * ELBOW_R for d in range(-35, 36, 1)]
    return min(cands, key=lambda c: abs((f - c).length - L) + .02 * (c - e).length)

def pose(kind, frame):
    f, c, t = ends(*NEAR[kind][frame])
    l1, l2 = BONES[kind]
    if kind == "fore":
        e = reach_from(straighten(elbow(f), f), f, kind); k, f2 = ik(e, f, l1, l2, True)
        pts = [FORE_TOP, e, (e + k) / 2, k]
    else:
        hip = reach_from(HIND_TOP, f, kind); k, f2 = ik(hip, f, l1, l2, False)
        pts = [hip, hip.lerp(k, .38), hip.lerp(k, .72), k]
    s = f2 - f                                                   # if a fetlock was out of reach, carry the hoof with it
    return pts + [(k + f2) / 2, f2, c + s, t + s]

def ring_verts(secs, sides=6):                                   # the same vertex order build_horse.loft makes
    pts = [s[0] for s in secs]; out = []
    for i, (p, h, w) in enumerate(secs):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((-tg.z, 0, tg.x))
        if up.z < 0 and abs(tg.z) < .9: up = -up
        for k in range(sides):
            a = 2 * math.pi * k / sides + math.pi / sides
            out.append(p + up * (h * math.sin(a)) + Vector((0, w * math.cos(a), 0)))
    return out

for name, (d, black, sec) in LEGS.items():
    o = bpy.data.objects[name]; kind = name.split("_")[0]; far = name.endswith("_far")
    if not o.data.shape_keys: o.shape_key_add(name="Basis", from_mix=False)
    for fr in range(12):
        pts = pose(kind, (fr + 6) % 12 if far else fr)
        secs = [(P(p.x, p.y, d), h * K, w * K) for p, (_, _, h, w) in zip(pts, sec)]
        kb = o.data.shape_keys.key_blocks.get(f"f{fr:02d}") or o.shape_key_add(name=f"f{fr:02d}", from_mix=False)
        for v, co in zip(kb.data, ring_verts(secs)): v.co = co
        kb.value = 0

def show(frame):
    for name in LEGS:
        for kb in bpy.data.objects[name].data.shape_keys.key_blocks[1:]: kb.value = 1.0 if kb.name == f"f{frame:02d}" else 0.0
print("bones", {k: tuple(round(v, 1) for v in b) for k, b in BONES.items()})
