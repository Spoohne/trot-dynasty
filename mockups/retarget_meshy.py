# blender -b -P retarget_meshy.py -- meshy_rig.fbx textured.glb bought_clip.fbx out.glb gif_dir
# Put the animator's clip (Renderhub "Horse for Game", 46 bones) onto the Meshy quadruped rig (27 bones, Meshy's own
# learned skin weights). For every frame each Meshy bone takes the same WORLD-space rotation change from rest as its
# mapped source bone; the hips also take the source pelvis's travel, scaled by hip height. Meshy's weights are never
# touched. The texture comes from the textured Meshy GLB (same mesh, same UVs). Exports one looping stride.
import bpy, sys, math, os
from mathutils import Vector, Matrix, Quaternion
RIG, TEX, CLIP, OUT, GIF = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def imp(path):
    before = set(bpy.data.objects)
    (bpy.ops.import_scene.fbx if path.lower().endswith(".fbx") else bpy.ops.import_scene.gltf)(filepath=path)
    return [o for o in bpy.data.objects if o not in before]

# ---- target: the Meshy rig, in its bind pose
tgt_objs = imp(RIG)
tgt = next(o for o in tgt_objs if o.type == "ARMATURE"); body = next(o for o in tgt_objs if o.type == "MESH")
if tgt.animation_data: tgt.animation_data.action = None
for pb in tgt.pose.bones: pb.matrix_basis.identity()
# texture from the textured GLB (identical mesh and UVs)
tex_objs = imp(TEX); tm = next(o for o in tex_objs if o.type == "MESH")
body.data.materials.clear(); body.data.materials.append(tm.data.materials[0])
for o in tex_objs: bpy.data.objects.remove(o)
for p in body.data.polygons: p.use_smooth = False

# ---- rigid barrel: Meshy's weights let the thigh and shoulder bones pull on the belly. Between the shoulder and the
# stifle, above the elbow, hand the leg bones' share of each vertex to the spine (Hips at the back, chest at the
# front, blended by position), so gathering legs no longer fold the middle. The legs' own weights are untouched.
def wb(n, tail=False):
    b = tgt.data.bones[n]; return tgt.matrix_world @ (b.tail_local if tail else b.head_local)
fwd_ = (wb("headend") - wb("Hips")); fwd_.z = 0; fwd_.normalize()
along = lambda p: p.dot(fwd_)
a_back, a_front = along(wb("backleg")), along(wb("frontleg"))
z_cut = min(wb("frontleg0").z, wb("backleg0").z)                                             # elbow / stifle height
LEG = [n for n in tgt.data.bones.keys() if "leg" in n]
vg = body.vertex_groups; gi = {g.name: g.index for g in vg}; Mb = body.matrix_world
def seg_d(p, a_, b_):
    ab = b_ - a_; t = max(0, min(1, (p - a_).dot(ab) / max(1e-12, ab.dot(ab)))); return (p - (a_ + ab * t)).length
UPPER = {n: (wb(n), wb(n, True)) for n in ("backleg", "R_backleg", "frontleg", "R_frontleg", "backleg0", "R_backleg0", "frontleg0", "R_frontleg0")}
D_ = wb("Hips").z - z_cut                                                                     # barrel depth, for scale
R_IN, R_OUT = float(os.environ.get("R_IN", ".15")) * D_, float(os.environ.get("R_OUT", ".45")) * D_   # leg-owned radius, and the blend out to the barrel
# smoother joints first: diffuse every bone's weights a few steps across the surface, so bends spread over more skin
WSMOOTH = int(os.environ.get("WSMOOTH", "0"))
if WSMOOTH:
    for o in bpy.context.selected_objects: o.select_set(False)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
    bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=.5, repeat=WSMOOTH, expand=0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.vertex_group_normalize_all(lock_active=False)
RIGID = os.environ.get("RIGID", "1") == "1"
moved = 0
for v in body.data.vertices:
    p = Mb @ v.co; a_ = along(p)
    if not RIGID or not (a_back - .3 * abs(a_front - a_back) < a_ < a_front + .05 * abs(a_front - a_back)) or p.z < z_cut: continue
    legs_here = [(vg[g.group].name, g.weight) for g in v.groups if vg[g.group].name in LEG]
    legw = sum(w for _, w in legs_here)
    if legw <= 0: continue
    # how much to take from the legs: none near the elbow/stifle line, rising to 85% high on the barrel, and fading out
    # toward the front and back ends so the joints where legs meet body still blend
    zr = (p.z - z_cut) / max(1e-6, wb("Hips").z - z_cut)
    ar = (a_ - a_back) / (a_front - a_back)
    # the whole barrel between the legs belongs to the spine; the legs keep only a short blend just above elbow/stifle
    take = max(0, min(1, (zr + .05) / .2)) * max(0, min(1, (ar + .3) / .25, (1.05 - ar) / .15))   # reaches back over the flank to the stifle
    # ...but never over the upper leg itself: skin near the thigh or forearm bone stays the leg's, fading in with distance
    dmin = min(seg_d(p, *UPPER[n]) for n in UPPER)
    take *= max(0, min(1, (dmin - R_IN) / (R_OUT - R_IN)))
    if take <= 0: continue
    t = max(0, min(1, ar))                                                                   # 0 at the hips, 1 at the chest
    for n, w in legs_here: vg[n].add([v.index], w * (1 - take), "REPLACE")
    vg["Hips"].add([v.index], legw * take * (1 - t), "ADD"); vg["chest"].add([v.index], legw * take * t, "ADD")
    moved += 1
print("BARREL verts rigidified", moved)

# ---- a poll joint: Meshy hangs the whole neck AND head on one "head" bone, so the face can only follow the neck.
# Re-seat the spare "headend" bone as a skull bone from the poll to the muzzle, and move the head's skin onto it
# (blending across the throatlatch), so the neck can stretch while the face stays carried forward.
Mb = body.matrix_world
RP = [Mb @ v.co for v in body.data.vertices]
a_nose = max(along(p) for p in RP)
headpts = [p for p in RP if along(p) > a_nose - .45 * (a_nose - a_front)]
muzzle = max(headpts, key=lambda p: along(p) - .3 * p.z)
L_head = .25 * (a_nose - along(wb("Hips")))                                                # a horse's head is about a quarter of nose-to-croup
cand = [p for p in RP if abs(along(p) - (along(muzzle) - L_head)) < .06 * (a_nose - a_front)]
poll_top = max(cand, key=lambda p: p.z); poll_bot = min((p for p in cand if p.z > wb("frontleg0").z), key=lambda p: p.z)
poll = (poll_top + poll_bot) / 2; poll = poll + (poll_top - poll) * .35                       # joint a bit above the middle of the neck there
a_poll = along(poll)
Ti = tgt.matrix_world.inverted()
for o in bpy.context.selected_objects: o.select_set(False)
tgt.select_set(True); bpy.context.view_layer.objects.active = tgt; bpy.ops.object.mode_set(mode="EDIT")
eb = tgt.data.edit_bones["headend"]; eb.use_connect = False
eb.head = Ti @ poll; eb.tail = Ti @ muzzle
bpy.ops.object.mode_set(mode="OBJECT")
span = .08 * (a_nose - a_front)
nface = 0
for v in body.data.vertices:
    p = Mb @ v.co; w = max(0, min(1, (along(p) - (a_poll - span)) / (2 * span)))
    if w <= 0 or p.z < poll_bot.z - .5 * (poll_top.z - poll_bot.z) and along(p) < a_poll: continue
    w = w * w * (3 - 2 * w)
    for g in v.groups:
        n_ = vg[g.group].name
        if n_ not in ("headend", "earend", "R_earend"): vg[n_].add([v.index], g.weight * (1 - w), "REPLACE")
    vg["headend"].add([v.index], w, "ADD"); nface += 1
for g_ in ("earend", "R_earend"):                                                           # ears ride the skull
    if g_ in vg:
        for v in body.data.vertices:
            for g in v.groups:
                if vg[g.group].name == g_: vg["headend"].add([v.index], g.weight, "ADD"); vg[g_].remove([v.index]); break
for o in bpy.context.selected_objects: o.select_set(False)
body.select_set(True); bpy.context.view_layer.objects.active = body; bpy.ops.object.vertex_group_normalize_all(lock_active=False)
print("POLL joint: face verts moved", nface)

# ---- a real neck: Meshy has no neck bone (its "head" bone starts at the throat; the neck's skin is shared between
# "chest" and "head"). Add one from the base of the neck to the throat, parented to the chest, carry "head" on it,
# and move the neck's skin onto it, so the neck can be carried and swung from the withers without stretching.
hb = wb("head")
nb_a = along(wb("chest")) + .25 * (along(hb) - along(wb("chest")))                           # base of the neck, a little ahead of the chest joint
sec = [p for p in RP if abs(along(p) - nb_a) < .03 * (a_nose - a_front) and p.z > wb("frontleg0").z]
neck_base = Vector(fwd_ * nb_a) + Vector((0, 0, (max(p.z for p in sec) + min(p.z for p in sec)) / 2))
neck_base = neck_base + Vector((0, 0, 0)) - fwd_ * 0                                          # (on the midline)
neck_base.y = hb.y if abs(fwd_.x) > abs(fwd_.y) else neck_base.y
neck_base = neck_base - fwd_ * (along(neck_base) - nb_a)
for o in bpy.context.selected_objects: o.select_set(False)
tgt.select_set(True); bpy.context.view_layer.objects.active = tgt; bpy.ops.object.mode_set(mode="EDIT")
E = tgt.data.edit_bones
nk = E.new("neck"); nk.head = Ti @ neck_base; nk.tail = Ti @ hb; nk.parent = E["chest"]; nk.use_connect = False
nk.roll = E["chest"].roll
E["head"].parent = nk; E["head"].use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")
vg.new(name="neck")
a_hb = along(hb); nmoved = 0
for v in body.data.vertices:
    p = Mb @ v.co; a_ = along(p)
    if a_ < nb_a - .1 * (a_hb - nb_a) or p.z < wb("frontleg0").z: continue                       # the whole neck, underside included, down to the elbow line
    w = max(0, min(1, (a_ - (nb_a - .1 * (a_hb - nb_a))) / (.35 * (a_hb - nb_a)))); w = w * w * (3 - 2 * w)
    take = 0
    for g in v.groups:
        n_ = vg[g.group].name
        if n_ == "chest": take += g.weight * w; vg[n_].add([v.index], g.weight * (1 - w), "REPLACE")
        elif n_ == "head" and a_ < a_hb - .15 * (a_hb - nb_a):                                 # the head bone's share of the lower neck
            t_ = g.weight * w; take += t_; vg[n_].add([v.index], g.weight - t_, "REPLACE")
    if take > 0: vg["neck"].add([v.index], take, "ADD"); nmoved += 1
print("NECK bone added: verts", nmoved)

# ---- source: the bought rig playing its clip
src_objs = imp(CLIP)
src = next(o for o in src_objs if o.type == "ARMATURE")
for o in src_objs:
    if o.type == "MESH": bpy.data.objects.remove(o)
act = src.animation_data.action
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])

def world_head(arm, n, tail=False):
    b = arm.data.bones[n]; return arm.matrix_world @ (b.tail_local if tail else b.head_local)
# face the source the same way as the target (both z-up in Blender): turn it about z
ft = world_head(tgt, "headend") - world_head(tgt, "Hips"); ft.z = 0
fs = world_head(src, "HorseScull") - world_head(src, "HorsePelvis"); fs.z = 0
src.rotation_euler.z += math.atan2(ft.y, ft.x) - math.atan2(fs.y, fs.x)
bpy.context.view_layer.update()
k_h = (world_head(tgt, "Hips").z - min(world_head(tgt, n, True).z for n in ("frontleg2", "backleg2"))) / \
      (world_head(src, "HorsePelvis").z - min(world_head(src, n).z for n in ("HorseLFrontHoof", "HorseLRearHoof")))

# ---- the map: Meshy bone <- source bone (Meshy's unprefixed side is the horse's left)
MAP = {"Hips": "HorsePelvis", "chest": "HorseRibcage", "head": "HorseNeck3", "headend": "HorseScull",
       "tail": "HorseTail1", "tailstart": "HorseTail2", "tail1": "HorseTail3", "tail2": "HorseTail5", "tail3": "HorseTail7",
       "frontleg": "HorseLHumerus", "frontleg0": "HorseLRadius", "frontleg1": "HorseLMetacarpus", "frontleg2": "HorseLPhalangesManus",
       "R_frontleg": "HorseFrontRLegHumerus", "R_frontleg0": "HorseFrontRLegRadius", "R_frontleg1": "HorseFrontRLegMetacarpus", "R_frontleg2": "HorseFrontRLegPhalangesManus",
       "backleg": "HorseLFemur", "backleg0": "HorseLTibia", "backleg1": "HorseLLargeCannon", "backleg2": "HorseLPhalanxPrima",
       "R_backleg": "HorseRLegFemur", "R_backleg0": "HorseRLegTibia", "R_backleg1": "HorseRLegLargeCannon", "R_backleg2": "HorseRLegPhalanxPrima"}
TAIL_DAMP = .5

order = []
def walk(b):
    order.append(b.name)
    for c in b.children: walk(c)
for b in tgt.data.bones:
    if b.parent is None: walk(b)
Wt, Ws = tgt.matrix_world, src.matrix_world
rest_t = {n: Wt @ tgt.data.bones[n].matrix_local for n in order}
rest_s = {n: Ws @ src.data.bones[n].matrix_local for n in MAP.values()}
rest_rot_t = {n: rest_t[n].to_quaternion() for n in order}
rest_rot_s = {n: rest_s[n].to_quaternion() for n in MAP.values()}
hip_rest_s = rest_s["HorsePelvis"].translation.copy()

# ---- the stride period first, from the SOURCE (left fore hoof height), then sample the source densely over one stride
hz = []
for f in range(f0, f1 + 1):
    sc.frame_set(f); hz.append((Ws @ src.pose.bones["HorseLFrontHoof"].matrix).translation.z)
T = min(range(8, len(hz) // 2 + 1), key=lambda T: sum(abs(hz[i] - hz[i + T]) for i in range(len(hz) - T)))
SUB = 4                                                                                     # 4 samples per source frame
t_land = min(range(T), key=lambda i: hz[i]) / T                                              # leading fore on the ground (stride fraction)
FT_PER_UNIT = 9.0 / (a_nose - min(along(p) for p in RP))                                       # the baked horse is 9 ft nose to tail
REACH_FT = float(os.environ.get("REACH", "0"))                                             # calibrated: .06 gives ~0.85 ft of fore-aft head travel
PUMP = float(os.environ.get("PUMP", ".15")); PUMP_LAG = float(os.environ.get("PUMP_LAG", ".08"))   # radians of neck drive; how late after the strike it bottoms
N = T * SUB
srcq = {s: [] for s in set(MAP.values())}; hipz = []
for k in range(N):
    fr = f0 + k / SUB; sc.frame_set(int(fr), subframe=fr - int(fr))
    for s_ in srcq: srcq[s_].append((Ws @ src.pose.bones[s_].matrix).to_quaternion())
    hipz.append((Ws @ src.pose.bones["HorsePelvis"].matrix).translation.z - hip_rest_s.z)
delta = {s_: [q @ rest_rot_s[s_].inverted() for q in qs] for s_, qs in srcq.items()}
def qmean(qs):
    acc = Quaternion((0, 0, 0, 0)); r = qs[0]
    for q in qs:
        if q.dot(r) < 0: q = -q
        acc = Quaternion((acc.w + q.w, acc.x + q.x, acc.y + q.y, acc.z + q.z))
    acc.normalize(); return acc
mean = {s_: qmean(v) for s_, v in delta.items()}
# shaping, in stride fractions: overlapping action (lag), how much of the oscillation to keep (amp), and a held offset
lat = Vector((-ft.y, ft.x, 0)).normalized(); upv = Vector((0, 0, 1))
def turn_sign(bone_t, axis):
    """+1 if turning bone_t's world rest about axis by + raises its tail end (z), else -1."""
    h = rest_t[bone_t].translation; tvec = (Wt @ tgt.data.bones[bone_t].tail_local) - h
    return 1 if (Quaternion(axis, .1) @ tvec).z > tvec.z else -1
HEAD_LIFT = float(os.environ.get("HEAD_LIFT", "-.1"))                                        # radians the face is raised toward the horizon
HEAD_AMP = float(os.environ.get("HEAD_AMP", ".4"))                                          # share of the clip's head nod kept
SHAPE = {"head": dict(lag=.06, amp=float(os.environ.get("NECK_AMP", ".5")), hold=float(os.environ.get("NECK_HOLD", "0"))), "headend": dict(lag=.07, amp=HEAD_AMP, hold=0)}
TAIL = ["tail", "tailstart", "tail1", "tail2", "tail3"]
s_tail = turn_sign("tailstart", lat)
for i_, n_ in enumerate(TAIL): SHAPE[n_] = dict(lag=.06 + .07 * i_, amp=.45, hold=0)
sgn_neck = turn_sign("head", lat)
sgn_face = turn_sign("headend", lat)                                                       # + raises the muzzle
sgn_nk = turn_sign("neck", lat)                                                                # + raises the head end of the neck
NECK_DOWN = float(os.environ.get("NECK_DOWN", "-.55"))                                          # radians: carry the neck lower, toward the back line
CHEST_FOLLOW = float(os.environ.get("CHEST_FOLLOW", ".1"))                              # 0 = chest moves rigidly with the hips, 1 = the animator's ribcage
def qamp(mean_, q, amp):
    """q's offset from mean_, scaled by amp (amp > 1 exaggerates: slerp can't extrapolate)."""
    d = mean_.inverted() @ q
    if d.w < 0: d = -d
    ax, an = d.to_axis_angle(); return mean_ @ Quaternion(ax, an * amp)
HIP_AMP = float(os.environ.get("HIP_AMP", "1.6"))
LEG_AMP = float(os.environ.get("LEG_AMP", "1"))
BEND_AMP = float(os.environ.get("BEND_AMP", "1.15"))                                        # how much more the knees/fetlocks open and fold                                          # bow-to-stern rock of the body
def shaped(n, s_, k):
    if n == "Hips": return qamp(mean[s_], delta[s_][k], HIP_AMP)
    if "leg" in n:
        # reach comes from the top of the limb: amplify the shoulder/hip bone's swing; each lower bone keeps its own
        # bend RELATIVE TO THE BONE ABOVE (optionally a little more), so the whole leg carries forward as one unit
        par = tgt.data.bones[n].parent.name
        if "leg" not in par: return qamp(mean[s_], delta[s_][k], LEG_AMP)
        ps = MAP[par]
        rel = delta[ps][k].inverted() @ delta[s_][k]
        relm = qmean([delta[ps][j].inverted() @ delta[s_][j] for j in range(N)])
        return shaped(par, ps, k) @ qamp(relm, rel, BEND_AMP)
    if n == "chest":                                                                       # keep the barrel rigid: the chest mostly rides with the hips
        return qamp(mean["HorsePelvis"], delta["HorsePelvis"][k], HIP_AMP).slerp(delta[s_][k], CHEST_FOLLOW)
    sh = SHAPE.get(n)
    if not sh: return delta[s_][k]
    kk = int(round(k - sh["lag"] * N)) % N
    q = qamp(mean[s_], delta[s_][kk], sh["amp"])                                          # soften (<1) or drive (>1) the swing around its mean
    if sh["hold"]: q = Quaternion(lat, sgn_neck * sh["hold"]) @ q                           # lower/extend (-) or lift (+)
    if n == "headend": q = Quaternion(lat, sgn_face * HEAD_LIFT) @ q                       # carry the face forward, nose out
    if n == "headend":                                                                     # face counters the neck's swing, staying level
        ph = 2 * math.pi * (k / N - t_land - PUMP_LAG)
        q = Quaternion(lat, sgn_face * PUMP * float(os.environ.get("FACE_REACH", "-.6")) * math.cos(ph - .5)) @ q
    if n in TAIL:
        i_ = TAIL.index(n); ph = 2 * math.pi * (k / N - .11 * i_)
        lift = s_tail * (.32 if i_ == 0 else .06)                                          # carried up off the rump
        wave = s_tail * .12 * (1 + .5 * i_) * math.sin(2 * ph)                             # streams: twice a stride, travelling down
        sway = .05 * (1 + .4 * i_) * math.sin(ph)
        q = Quaternion(lat, lift + wave) @ Quaternion(upv, sway) @ q
    return q

new_act = bpy.data.actions.new(os.environ.get("CLIP_NAME", "gallop")); tgt.animation_data_create(); tgt.animation_data.action = new_act
for pb in tgt.pose.bones: pb.rotation_mode = "QUATERNION"
sc.render.fps = 30 * SUB                                                                   # dense keys at whole frames: same duration
MOCAP = os.environ.get("MOCAP")
if MOCAP:
    # ---- motion from video: every bone takes the ABSOLUTE side-view angle of the matching tracked segment; the
    # body's height comes from planting the lowest hoof on the ground each frame. No source clip is used.
    import json
    cyc = json.load(open(MOCAP)); NM = cyc["_N"]
    SRC_FPS = float(os.environ.get("SRC_FPS", "24")); per = cyc["_period_frames"]
    N = NM; sc.render.fps = max(1, round(NM * SRC_FPS / per))                               # one cycle lasts the video's stride duration
    up_ = Vector((0, 0, 1)); kax = fwd_.cross(up_).normalized()                                # + rotates fwd toward up
    th = lambda v: math.atan2(v.z, v.dot(fwd_))
    def tv(j, a, b):                                                                          # video vector a->b at sample j, as (x fwd, z up)
        pa, pb_ = cyc[a][j], cyc[b][j]; return Vector((pb_[0] - pa[0], pb_[1] - pa[1]))
    vth = lambda v2: math.atan2(v2.y, v2.x)
    mid = lambda j, a, b: [(cyc[a][j][0] + cyc[b][j][0]) / 2, (cyc[a][j][1] + cyc[b][j][1]) / 2]
    for j in range(NM): cyc.setdefault("_ear", []).append(mid(j, "right_earbase", "left_earbase"))
    rest_dir = {n: (Wt @ tgt.data.bones[n].tail_local) - (Wt @ tgt.data.bones[n].head_local) for n in order}
    back_th = [vth(tv(j, "back_end", "back_base")) for j in range(NM)]; back_mean = sum(back_th) / NM
    ABS = {  # rig bone: (video from, video to)
        "frontleg0": ("front_left_thai", "front_left_knee"), "frontleg1": ("front_left_knee", "front_left_paw"),
        "R_frontleg0": ("front_right_thai", "front_right_knee"), "R_frontleg1": ("front_right_knee", "front_right_paw"),
        "backleg0": ("back_left_thai", "back_left_knee"), "backleg1": ("back_left_knee", "back_left_paw"),
        "R_backleg0": ("back_right_thai", "back_right_knee"), "R_backleg1": ("back_right_knee", "back_right_paw"),
        "neck": ("neck_base", "throat_base"), "headend": ("_ear", "nose"),
        # the top of each limb: withers -> elbow, croup -> stifle, so the shoulder and hip swing the whole leg
        "frontleg": ("back_base", "front_left_thai"), "R_frontleg": ("back_base", "front_right_thai"),
        "backleg": ("back_end", "back_left_thai"), "R_backleg": ("back_end", "back_right_thai")}
    RIDE = {"chest": "Hips",
            "frontleg2": "frontleg1", "R_frontleg2": "R_frontleg1", "backleg2": "backleg1", "R_backleg2": "R_backleg1",
            "head": "neck", "earend": "headend", "R_earend": "headend"}
    def amean(vals):
        return math.atan2(sum(math.sin(x) for x in vals), sum(math.cos(x) for x in vals))
    vmean = {n: amean([vth(tv(j, *ABS[n])) for j in range(NM)]) for n in ABS}
    SWING = float(os.environ.get("SWING", "1.0"))
    HOOVES = ["frontleg2", "R_frontleg2", "backleg2", "R_backleg2"]
    ground = min((Wt @ tgt.data.bones[h].tail_local).z for h in HOOVES)
    new_rot = {}
    for k in range(N + 1):
        j = k % NM
        for n in order:
            pb = tgt.pose.bones[n]
            if n == "Hips": rot = Quaternion(kax, back_th[j] - back_mean) @ rest_rot_t[n]
            elif n in ABS:
                # the video's swing for this segment about its own stride-average, added to OUR rest angle: our horse
                # keeps its proportions and posture, and takes the real horse's timing and range of motion
                a, b = ABS[n]; rot = Quaternion(kax, SWING * (vth(tv(j, a, b)) - vmean[n])) @ rest_rot_t[n]
            elif n in RIDE:
                p_ = RIDE[n]; rot = new_rot[p_] @ rest_rot_t[p_].inverted() @ rest_rot_t[n]
            elif n in TAIL:
                i_ = TAIL.index(n); ph = 2 * math.pi * (k / N - .11 * i_); p_ = tgt.data.bones[n].parent.name
                carry = Quaternion(lat, s_tail * ((.32 if i_ == 0 else .06) + .1 * (1 + .5 * i_) * math.sin(2 * ph)))
                sway = Quaternion(upv, .04 * (1 + .4 * i_) * math.sin(ph))
                rot = carry @ sway @ new_rot[p_] @ rest_rot_t[p_].inverted() @ rest_rot_t[n]
            else: rot = (Wt @ pb.matrix).to_quaternion()
            new_rot[n] = rot
            pos = rest_t[n].translation if n == "Hips" else (Wt @ pb.matrix).translation
            pb.matrix = Wt.inverted() @ Matrix.LocRotScale(pos, rot, rest_t[n].to_scale())
            bpy.context.view_layer.update()
        low = min((Wt @ tgt.pose.bones[h].tail).z for h in HOOVES)                             # plant the lowest hoof
        hp = tgt.pose.bones["Hips"]; m = Wt @ hp.matrix; m.translation.z += ground - low; hp.matrix = Wt.inverted() @ m
        bpy.context.view_layer.update()
        for n in order:
            tgt.pose.bones[n].keyframe_insert("rotation_quaternion", frame=k)
        hp.keyframe_insert("location", frame=k)
    # stride length: how far a planted hoof slides back per cycle, in rig units -> feet
    xs = []
    for k in range(N):
        sc.frame_set(k); xs.append(((Wt @ tgt.pose.bones["frontleg2"].tail).dot(fwd_), (Wt @ tgt.pose.bones["frontleg2"].tail).z))
    planted = [i for i in range(N) if xs[i][1] < ground + .02 * (a_nose - a_front)]
    slide = sum(xs[i][0] - xs[(i + 1) % N][0] for i in planted if (i + 1) % N in planted) / max(1, len(planted))
    print("MOCAP stride ~", round(slide * N * FT_PER_UNIT, 1), "ft per cycle;", N, "samples at", sc.render.fps, "fps")
for k in ([] if MOCAP else range(N + 1)):
    kk = k % N
    for n in order:
        pb = tgt.pose.bones[n]
        if n == "neck":
            ph_ = 2 * math.pi * (kk / N - t_land - PUMP_LAG)
            dq = shaped("chest", MAP["chest"], kk)
            rot = Quaternion(lat, sgn_nk * (NECK_DOWN - PUMP * math.cos(ph_))) @ dq @ rest_rot_t[n]
            pb.matrix = Wt.inverted() @ Matrix.LocRotScale((Wt @ pb.matrix).translation, rot, rest_t[n].to_scale())
            bpy.context.view_layer.update(); pb.keyframe_insert("rotation_quaternion", frame=k); continue
        if n not in MAP: pb.keyframe_insert("rotation_quaternion", frame=k); continue
        s_ = MAP[n]
        rot = shaped(n, s_, kk) @ rest_rot_t[n]
        pos = (Wt @ pb.matrix).translation
        if n == "Hips": pos = rest_t[n].translation + Vector((0, 0, hipz[kk] * k_h * float(os.environ.get("BOB_AMP", "1.3"))))   # bob only: the replay moves it forward
        if n == "head":                                                                          # the reach: the neck pushes forward on the strike, draws back in flight
            ph_ = 2 * math.pi * (kk / N - t_land - PUMP_LAG)
            pos = pos + fwd_ * (REACH_FT / FT_PER_UNIT) * math.cos(ph_)
        pb.matrix = Wt.inverted() @ Matrix.LocRotScale(pos, rot, rest_t[n].to_scale())
        bpy.context.view_layer.update()
        pb.keyframe_insert("rotation_quaternion", frame=k)
        if n in ("Hips", "head"): pb.keyframe_insert("location", frame=k)
if hasattr(new_act, "slots") and len(new_act.slots) and tgt.animation_data.action_slot is None:
    tgt.animation_data.action_slot = new_act.slots[0]
f0 = 0; new_act.frame_range = (0, N); sc.frame_start, sc.frame_end = 0, N - 1
print("STRIDE frames", T, "x", SUB, "k_h", round(k_h, 4), "neck sign", sgn_neck, "tail sign", s_tail)

bpy.data.objects.remove(src)
for a_ in list(bpy.data.actions):
    if a_ != new_act: bpy.data.actions.remove(a_)                                          # only the gallop goes out
# bake to feet, nose toward +x, hooves on z=0, so the page uses it as is
sc.frame_set(f0); bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
nose = max(P, key=lambda p: p.dot(ft.normalized())); tailp = min(P, key=lambda p: p.dot(ft.normalized()))
length = (nose - tailp).dot(ft.normalized()); zmin = min(p.z for p in P)
k = 9.0 / length
rig_root = bpy.data.objects.new("horse_root", None); sc.collection.objects.link(rig_root)
tgt.parent = rig_root; tgt.matrix_parent_inverse = Matrix.Identity(4)
rig_root.rotation_euler.z = -math.atan2(ft.y, ft.x); rig_root.scale = (k, k, k)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
rig_root.location = (-max(p.x for p in P), 0, -min(p.z for p in P))                          # nose at x=0, hooves on the ground
bpy.context.view_layer.update()
print("BAKED scale", round(k, 2))
for o in bpy.context.selected_objects: o.select_set(False)
rig_root.select_set(True)
tgt.select_set(True); body.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=True, export_animations=True,
                          export_force_sampling=True, export_frame_range=True)

# review frames
if os.environ.get("NOGIF"): sys.exit(0)
os.makedirs(GIF, exist_ok=True)
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)]); c = (lo + hi) / 2; size = max(hi - lo)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 720, 480; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.5
side = Vector((0, -1, 0))                                                                  # baked: the horse runs along +x
cam.location = c + side * size * 4; cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
for f in range(0, N, 2):
    sc.frame_set(f); sc.render.filepath = os.path.join(GIF, f"f{f:03d}.png"); bpy.ops.render.render(write_still=True)
