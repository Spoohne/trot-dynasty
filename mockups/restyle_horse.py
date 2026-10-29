# blender -b -P restyle_horse.py -- in.fbx out.glb strip.png faces
# Take the purchased, animator-made horse (Renderhub "Horse for Game") into the low-poly look: drop the riding tack,
# decimate the body to flat facets (skin weights survive), color each facet from the model's own albedo map (the
# saddle cloth painted over in coat), turn it to face +x in feet, find one clean stride in the clip and measure how
# far that stride travels, then export the GLB with just that stride.
import bpy, sys, math, random, os
from mathutils import Vector
SRC, OUT, STRIP, FACES = sys.argv[sys.argv.index("--") + 1:]
FT = 3.28084
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type == "MESH" and o.name != "Horse_LOW": bpy.data.objects.remove(o)          # stirrups, bridle
arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = sc.objects["Horse_LOW"]
import bmesh
bm = bmesh.new(); bm.from_mesh(body.data); seen, isl = set(), []
for v0 in bm.verts:
    if v0 in seen: continue
    st, part = [v0], []; seen.add(v0)
    while st:
        x = st.pop(); part.append(x)
        for e_ in x.link_edges:
            w_ = e_.other_vert(x)
            if w_ not in seen: seen.add(w_); st.append(w_)
    isl.append(part)
isl.sort(key=len); bmesh.ops.delete(bm, geom=[v0 for part in isl[:-1] for v0 in part], context="VERTS"); bm.to_mesh(body.data); bm.free()   # rivets
act = arm.animation_data.action

# ---- body shape and body motion, worked in armature space (rest bones give the horse's own axes)
from mathutils import Matrix, Quaternion
rb = arm.data.bones
fwd = (rb["HorseScull"].head_local - rb["HorsePelvis"].head_local); fwd.y = 0; fwd.normalize()   # armature space is Y-up (FBX)
up = Vector((0, 1, 0)); lat = fwd.cross(up)                                            # turning about lat by + drops the nose (checked on renders)
along = lambda p: p.dot(fwd)
# a leaner barrel: between the legs and above the elbows, narrow the trunk and lift the lower half of the belly
toA = arm.matrix_world.inverted() @ body.matrix_world; toM = toA.inverted()
U = (rb["HorseScull"].head_local - rb["HorsePelvis"].head_local).length / 1.3      # armature units per metre (the FBX is in cm)
a_hind, a_fore = sorted((along(rb["HorseLRearHoof"].head_local), along(rb["HorseLFrontHoof"].head_local)))
elbow = rb["HorseLRadius"].head_local.y
spine_z = lambda s: rb["HorsePelvis"].head_local.y + (rb["HorseRibcage"].head_local.y - rb["HorsePelvis"].head_local.y) * min(1, max(0, (s - a_hind) / (a_fore - a_hind)))
for v in body.data.vertices:
    p = toA @ v.co; s = along(p)
    if a_hind - .05 * U < s < a_fore + .05 * U and p.y > elbow + .04 * U:
        e = min(1, (s - a_hind + .05 * U) / (.35 * U), (a_fore + .05 * U - s) / (.35 * U)); edge = e * e * (3 - 2 * e)
        side = p.dot(lat); p -= lat * side * .2 * edge                                  # 20% narrower
        d = spine_z(s) - p.y
        D = spine_z(s) - elbow
        if d > .1 * U: fr = (d - .1 * U) / (D - .1 * U); p.y += fr * fr * .42 * (D - .1 * U) * edge   # tuck the lower belly up along a curve, most at the bottom
        v.co = toM @ p

# ---- facets, colored from the albedo map at each face's UV centre
img = bpy.data.images.load(SRC.rsplit(".", 1)[0] + ".fbm/Horse_Albedo Map.png")              # the FBX names its maps "Map #23" etc.
W_, H_ = img.size; px = img.pixels[:]
uvl = body.data.uv_layers.active.data
cols = {}
for p in body.data.polygons:
    u = sum(uvl[i].uv.x for i in p.loop_indices) / p.loop_total; v = sum(uvl[i].uv.y for i in p.loop_indices) / p.loop_total
    x, y = int(u % 1 * (W_ - 1)), int(v % 1 * (H_ - 1)); k = (y * W_ + x) * 4
    cols[p.index] = (px[k], px[k + 1], px[k + 2])
bpy.context.view_layer.objects.active = body
for o in sc.objects: o.select_set(o == body)
dec = body.modifiers.new("dec", "DECIMATE"); dec.ratio = 1 if os.environ.get("WRAP") else min(1, int(FACES) / len(body.data.polygons))
while body.modifiers.find("dec") > 0: bpy.ops.object.modifier_move_up(modifier="dec")
# decimation drops the per-face lookup, so carry the color on the mesh first as a face attribute
fa = body.data.attributes.new("fc", "FLOAT_COLOR", "FACE")
for p in body.data.polygons: c = cols[p.index]; fa.data[p.index].color = (c[0], c[1], c[2], 1)
bpy.ops.object.modifier_apply(modifier="dec")
fa = body.data.attributes["fc"]                                                        # re-fetch: the old handle dangles after the modifier rebuilds the mesh
for p in body.data.polygons: p.use_smooth = False
lum = lambda c: .3 * c[0] + .59 * c[1] + .11 * c[2]
coat = [fa.data[p.index].color for p in body.data.polygons]
brown = [c for c in coat if c[0] > c[1] * 1.15 and c[0] > c[2] * 1.3]
avg = [sum(c[i] for c in brown) / len(brown) for i in range(3)]
ca = body.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
import random; random.seed(4)
slot = {}
for p in body.data.polygons:
    c = list(fa.data[p.index].color)[:3]
    if c[2] > c[0] * 1.2: c = (.012, .012, .016); slot[p.index] = 2                 # the saddle seat: harness saddle, black tack
    elif c[1] > c[0] * 1.05 or (c[0] > .2 and c[2] > c[1] * 1.15): c = avg            # the model's green/pink riding cloth -> coat; our own saddle cloth goes on top   # the saddle cloth: recolored per runner
    c = [min(1, x * 1.7) for x in c]                                                    # the albedo is dark under our night key
    j = 1 + (random.random() - .5) * .14
    for li in p.loop_indices: ca.data[li].color = (c[0] * j, c[1] * j, c[2] * j, 1)
m = bpy.data.materials.new("coat"); m.use_nodes = True; nt = m.node_tree
vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"]); nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .75
body.data.materials.clear(); body.data.materials.append(m)
for nm, col in (("cloth", (.8, .1, .1, 1)), ("tack", (.01, .01, .012, 1))):
    mm = bpy.data.materials.new(nm); mm.use_nodes = True; mm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = col; body.data.materials.append(mm)
for p in body.data.polygons: p.material_index = slot.get(p.index, 0)

# ---- optional: swap in a different body mesh (GOAL_MESH, e.g. a Hunyuan horse made from a restyle of this horse's
# rest pose). It is fitted to the old body's rest-pose box, takes the old body's skin weights by nearest surface,
# and is painted by region; the old body is then dropped, so the bought skeleton and clip drive the new mesh.
import os
GOAL = os.environ.get("GOAL_MESH")
if GOAL:
    # ---- swap in a Meshy horse (textured, faceted, standing square). This time the SKELETON is fitted to the new
    # horse, not the horse to the skeleton: bone positions are remapped piecewise along the body (tail root, hind
    # hooves, fore hooves, nose) and scaled to its height and width, so the bought animation drives a horse of the
    # new proportions. The mesh is then skinned with automatic weights and the bought body dropped.
    old = body
    # 1. turn the rig so the head faces +x in world (metres, z up), as the Meshy horse will
    sc.frame_set(int(act.frame_range[0])); arm.data.pose_position = "REST"; bpy.context.view_layer.update()
    W = lambda n, tail=False: arm.matrix_world @ (rb[n].tail_local if tail else rb[n].head_local)
    d = W("HorseScull") - W("HorsePelvis"); arm.rotation_euler.z += -math.atan2(d.y, d.x); bpy.context.view_layer.update()
    L_old = dict(tail=W("HorseTail1").x, hind=W("HorseLRearHoof").x, fore=W("HorseLFrontHoof").x, nose=max(W("HorseScull").x, W("HorseScull", True).x),
                 back=W("HorseSpine4").z, ground=min(W("HorseLRearHoof").z, W("HorseLFrontHoof").z), width=abs(W("HorseLFrontHoof").y))
    # 2. the Meshy horse: head to +x, on the ground, metres (its own scale is arbitrary: match the old back height)
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=GOAL)
    new = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    for o in [o for o in bpy.data.objects if o not in before and o != new and o.type != "MESH"]: pass
    for o in bpy.context.selected_objects: o.select_set(False)
    new.select_set(True); bpy.context.view_layer.objects.active = new; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = [v.co.copy() for v in new.data.vertices]
    ext = [max(c[i] for c in co) - min(c[i] for c in co) for i in range(3)]
    if ext[1] > ext[0]:
        for v in new.data.vertices: v.co = Vector((v.co.y, -v.co.x, v.co.z))
    co = [v.co.copy() for v in new.data.vertices]
    ym_ = (min(c.y for c in co) + max(c.y for c in co)) / 2
    for v in new.data.vertices: v.co.y -= ym_                                               # centre sideways
    co = [v.co.copy() for v in new.data.vertices]
    x0, x1 = min(c.x for c in co), max(c.x for c in co); H0 = max(c.z for c in co); z0 = min(c.z for c in co)
    # head end: the end whose top is higher (head and ears rise above the croup)
    if max(c.z for c in co if c.x < x0 + (x1 - x0) * .25) > max(c.z for c in co if c.x > x1 - (x1 - x0) * .25):
        for v in new.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
    co = [v.co.copy() for v in new.data.vertices]; x0, x1 = min(c.x for c in co), max(c.x for c in co)
    low = [c for c in co if c.z < z0 + (H0 - z0) * .06]; xm = (min(c.x for c in low) + max(c.x for c in low)) / 2
    hind_x = sum(c.x for c in low if c.x < xm) / max(1, len([c for c in low if c.x < xm])); fore_x = sum(c.x for c in low if c.x > xm) / max(1, len([c for c in low if c.x > xm]))
    back_z = max(c.z for c in co if hind_x + (fore_x - hind_x) * .3 < c.x < hind_x + (fore_x - hind_x) * .8)
    s_ = (L_old["back"] - L_old["ground"]) / (back_z - z0)
    for v in new.data.vertices: v.co = Vector((v.co.x * s_, v.co.y * s_, (v.co.z - z0) * s_))
    co = [v.co.copy() for v in new.data.vertices]; x0, x1 = min(c.x for c in co), max(c.x for c in co)
    hind_x, fore_x = hind_x * s_, fore_x * s_
    tail_x = min(c.x for c in co if c.z > (L_old["back"] - L_old["ground"]) * .55)
    width = max(abs(c.y) for c in co if c.z < .25 * (L_old["back"] - L_old["ground"]) and c.x > xm * s_)
    L_new = dict(tail=tail_x + .12, hind=hind_x, fore=fore_x, nose=x1 - .02, back=L_old["back"], ground=0, width=width)
    print("FIT old", {k: round(v, 2) for k, v in L_old.items()}); print("FIT new", {k: round(v, 2) for k, v in L_new.items()})
    # 3. remap the bones: piecewise-linear in x through the landmarks, scaled in z and y
    # body: one affine map between the hind and fore hooves (no local shear); neck and head: their own linear
    # map from the withers to the nose, so the chain reaches the new nose
    sb = (L_new["fore"] - L_new["hind"]) / (L_old["fore"] - L_old["hind"])
    wx0 = W("HorseNeck1").x; wx_new = L_new["hind"] + (wx0 - L_old["hind"]) * sb
    sn = (L_new["nose"] - wx_new) / (L_old["nose"] - wx0)
    def fx(x):
        return L_new["hind"] + (x - L_old["hind"]) * sb if x <= wx0 else wx_new + (x - wx0) * sn
    sz = (L_new["back"] - L_new["ground"]) / (L_old["back"] - L_old["ground"]); sy = L_new["width"] / L_old["width"]
    # the head and neck: the new horse carries its head at its own height, so ahead of the withers the z scale
    # blends from the body's to one that lands the old nose on the new nose
    nose_old_z = max((W("HorseScull"), W("HorseScull", True)), key=lambda p: p.x).z; nose_new_z = max(c.z for c in co if c.x > x1 - .12)
    poll_new = max((c for c in co if c.x > x1 - .5), key=lambda c: c.z)
    L_new["poll_z"] = poll_new.z; print("HEAD old nose z", round(nose_old_z, 2), "new nose z", round(nose_new_z, 2), "new poll", tuple(round(v, 2) for v in poll_new))
    sz_head = (nose_new_z - L_new["ground"]) / (nose_old_z - L_old["ground"])
    wx_ = W("HorseNeck1").x
    def f(p):
        t = 0 if p.x <= wx_ else min(1, (p.x - wx_) / (L_old["nose"] - wx_))
        szz = sz * (1 - t) + sz_head * t
        return Vector((fx(p.x), p.y * sy, L_new["ground"] + (p.z - L_old["ground"]) * szz))
    ref_arm = arm.copy(); ref_arm.data = arm.data.copy(); sc.collection.objects.link(ref_arm); ref_arm.name = "ref_arm"
    ref_arm.data.pose_position = "POSE"                                                  # the copy was made while arm showed its rest pose
    ref_arm.animation_data_create(); ref_arm.animation_data.action = act                   # the original skeleton, still playing the clip
    if hasattr(act, "slots") and len(act.slots): ref_arm.animation_data.action_slot = act.slots[0]   # Blender 4.4+: a copy named differently gets no slot by itself
    M = arm.matrix_world.copy(); Mi = M.inverted()
    for o in bpy.context.selected_objects: o.select_set(False)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
    # connected bones share a joint, so map every head and tail from the ORIGINAL positions first, then assign
    targets = {eb.name: (Mi @ f(M @ eb.head), Mi @ f(M @ eb.tail)) for eb in arm.data.edit_bones}
    # the neck and head chain must run down the middle of the new neck, or the skin shears when it extends:
    # put each joint on the neck's centreline (mid-height of the mesh's cross-section at that x)
    withers_z = L_new["back"]
    def centre_z(x):
        band = [c for c in co if abs(c.x - x) < .06 and c.z > withers_z * .55]
        return (min(c.z for c in band) + max(c.z for c in band)) / 2 if len(band) > 6 else None
    chain = ["HorseNeck1", "HorseNeck2", "HorseNeck3", "HorseNeck4", "HorseNeck5", "HorseNeck6", "HorseScull"]
    for nm in chain:
        h_, t_ = targets[nm]; hw, tw = M @ h_, M @ t_
        for pt in (hw, tw):
            cz = centre_z(pt.x)
            if cz is not None and pt.x > wx_ + .05: pt.z = cz
        targets[nm] = (Mi @ hw, Mi @ tw)
    # the legs: each joint below the hip or shoulder goes to the centre of the new leg's cross-section at that
    # height, on its own side, so the chain runs down the middle of the limb instead of beside it
    legs_ = {"L": ["HorseLFemur", "HorseLTibia", "HorseLLargeCannon", "HorseLPhalanxPrima", "HorseLRearHoof",
                   "HorseLHumerus", "HorseLRadius", "HorseLMetacarpus", "HorseLPhalangesManus", "HorseLFrontHoof"],
             "R": ["HorseRLegFemur", "HorseRLegTibia", "HorseRLegLargeCannon", "HorseRLegPhalanxPrima", "HorseRLegRearHoof",
                   "HorseFrontRLegHumerus", "HorseFrontRLegRadius", "HorseFrontRLegMetacarpus", "HorseFrontRLegPhalangesManus", "HorseFrontRLegFrontHoof"]}
    def leg_centre(pt, sgn):
        band = [c for c in co if abs(c.z - pt.z) < .035 and c.y * sgn > 0 and abs(c.x - pt.x) < .22]
        if len(band) < 4: return None
        return Vector((sum(c.x for c in band) / len(band), sum(c.y for c in band) / len(band), pt.z))
    for side_, names in legs_.items():
        sgn = 1 if (M @ targets[names[0]][0]).y > 0 else -1
        for k_, nm in enumerate(names):
            h_, t_ = targets[nm]; hw, tw = M @ h_, M @ t_
            fix_head = k_ % 5 != 0                                                         # femur/humerus heads (hip, shoulder) stay
            for pt, do in ((hw, fix_head), (tw, True)):
                if not do or pt.z > withers_z * .62: continue                                # only below the trunk
                c_ = leg_centre(pt, sgn)
                if c_: pt.x, pt.y = c_.x, c_.y
            targets[nm] = (Mi @ hw, Mi @ tw)
    for eb in arm.data.edit_bones: eb.head, eb.tail = targets[eb.name]
    bpy.ops.object.mode_set(mode="OBJECT")
    WRAP = bool(os.environ.get("WRAP"))
    if WRAP:
        # keep the bought body and its painted weights: warp its vertices with the same map the bones took, so it
        # still sits on the skeleton; the Meshy mesh becomes the shape target for a shrinkwrap after retargeting
        Mo = old.matrix_world.copy(); Moi = Mo.inverted()
        for v in old.data.vertices: v.co = Moi @ f(Mo @ v.co)
        old.data.update()
    # 4. skin: automatic weights on the new mesh; flat faces; drop the old body (WRAP keeps the old body instead)
    wrap_target = new if WRAP else None
    if WRAP: new = old
    for p in new.data.polygons: p.use_smooth = False
    # Meshy exports every facet as its own triangle; weld them so bone-heat weighting sees one closed surface
    if WRAP: pass
    if not WRAP:
        for o in bpy.context.selected_objects: o.select_set(False)
        new.select_set(True); bpy.context.view_layer.objects.active = new
        bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.remove_doubles(threshold=1e-4); bpy.ops.object.mode_set(mode="OBJECT")
        print("welded to", len(new.data.vertices), "verts")
        new.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        print("weighted verts", sum(1 for v in new.data.vertices if v.groups))
        # clean-up: the face belongs to the skull alone (no floppy jaw or neck pull); at most 3 bones per vertex
        vg = new.vertex_groups; M2 = new.matrix_world
        sk = arm.data.bones["HorseScull"]; skull_x = min((M2.inverted() @ (arm.matrix_world @ sk.head_local)).x, (M2.inverted() @ (arm.matrix_world @ sk.tail_local)).x)   # the poll end
        head_idx = [v.index for v in new.data.vertices if v.co.x > skull_x - .03]
        for g_ in list(vg):
            if g_.name != "HorseScull": g_.remove(head_idx)
        vg["HorseScull"].add(head_idx, 1.0, "REPLACE")
        if "HorseJaw" in vg: vg.remove(vg["HorseJaw"])
        for o in bpy.context.selected_objects: o.select_set(False)
        new.select_set(True); bpy.context.view_layer.objects.active = new
        # the legs: heat weights spread thin limb vertices onto neighbouring bones, so below the trunk each vertex is
        # weighted to the two nearest bone segments of its own leg (by distance to the segment), hooves to the hoof
        def seg_dist(p, a_, b_):
            ab = b_ - a_; t = max(0, min(1, (p - a_).dot(ab) / max(1e-9, ab.dot(ab)))); return (p - (a_ + ab * t)).length
        Mw = arm.matrix_world
        segs = {nm: (Mw @ arm.data.bones[nm].head_local, Mw @ arm.data.bones[nm].tail_local) for names in legs_.values() for nm in names}
        leg_sets = {}
        for side_, names in legs_.items():
            for grp, idxs in (("hind", names[:5]), ("fore", names[5:])):
                leg_sets[(side_, grp)] = idxs
        cut_z = withers_z * .62
        for v in new.data.vertices:
            p = M2 @ v.co
            if p.z > cut_z: continue
            if p.x < L_new["hind"] - .18:                                                        # the tail: strip any leg bones heat gave it
                for g_ in list(vg):
                    if g_.name in segs: g_.remove([v.index])
                continue
            best = None
            for key_, names in leg_sets.items():
                ds = sorted((seg_dist(p, *segs[nm]), nm) for nm in names)
                if best is None or ds[0][0] < best[0][0]: best = ds
            if best[0][0] > .25: continue                                                       # belly, not a leg
            for g_ in list(vg): g_.remove([v.index])
            if best[0][1].endswith("Hoof") or p.z < .09: vg[best[0][1]].add([v.index], 1.0, "REPLACE"); continue
            d0, n0 = best[0]; d1, n1 = best[1]
            w0 = 1 / (d0 + 1e-4) ** 2; w1 = 1 / (d1 + 1e-4) ** 2
            if d1 > d0 * 2.2: w1 = 0                                                             # clearly on one segment
            tot = w0 + w1; vg[n0].add([v.index], w0 / tot, "REPLACE")
            if w1: vg[n1].add([v.index], w1 / tot, "REPLACE")
        bpy.ops.object.vertex_group_limit_total(limit=3); bpy.ops.object.vertex_group_normalize_all(lock_active=False)
        print("head verts", len(head_idx), "skull_x", round(skull_x, 2), "mesh x", round(min(v.co.x for v in new.data.vertices), 2), round(max(v.co.x for v in new.data.vertices), 2), "mw", [round(x, 2) for x in new.matrix_world.translation], "skull world", tuple(round(v, 2) for v in (arm.matrix_world @ arm.data.bones["HorseScull"].head_local)))
    if not WRAP: bpy.data.objects.remove(old)
    body = new; body.name = "Horse_LOW"
    for m_ in body.data.materials:
        if m_ and m_.use_nodes: m_.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = .8
    arm.data.pose_position = "POSE"; bpy.context.view_layer.update()
    # ---- retarget: for every frame and bone, give the fitted bone the same WORLD rotation change the original bone
    # makes from its own rest, so joints flex by the animator's angles whatever the new rest pose looks like.
    # The pelvis also takes the original's translation, scaled to the new body.
    f0_, f1_ = int(act.frame_range[0]), int(act.frame_range[1])
    act_new = bpy.data.actions.new("retarget"); arm.animation_data_create(); arm.animation_data.action = act_new
    order = []
    def walk(b):
        order.append(b.name)
        for c_ in b.children: walk(c_)
    for b in arm.data.bones:
        if b.parent is None: walk(b)
    Rw_new = arm.matrix_world; Rw_old = ref_arm.matrix_world
    rest_new = {n: (Rw_new @ arm.data.bones[n].matrix_local) for n in order}
    rest_old = {n: (Rw_old @ ref_arm.data.bones[n].matrix_local) for n in order}
    for pb in arm.pose.bones: pb.rotation_mode = "QUATERNION"
    for f in range(f0_, f1_ + 1):
        sc.frame_set(f)
        for n in order:
            pose_old = Rw_old @ ref_arm.pose.bones[n].matrix
            delta = pose_old @ rest_old[n].inverted()                                       # world-space change from rest
            target = delta @ rest_new[n]
            pb = arm.pose.bones[n]
            cur = Rw_new @ pb.matrix
            if pb.parent is None:
                t_old = pose_old.translation - rest_old[n].translation
                target.translation = rest_new[n].translation + Vector((t_old.x * sb, t_old.y * sy, t_old.z * sz))
            else:
                target.translation = cur.translation
            pb.matrix = Rw_new.inverted() @ target
            bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if pb.parent is None: pb.keyframe_insert("location", frame=f)
    for f_ in (f0_, f0_ + 5, f0_ + 10):
        sc.frame_set(f_)
        print("DBG f", f_, "ref hoof z", round((Rw_old @ ref_arm.pose.bones["HorseLFrontHoof"].matrix).translation.z, 3),
              "new hoof z", round((Rw_new @ arm.pose.bones["HorseLFrontHoof"].matrix).translation.z, 3),
              "new pelvis q", tuple(round(x, 3) for x in arm.pose.bones["HorsePelvis"].rotation_quaternion))
    if hasattr(act_new, "slots") and len(act_new.slots) and arm.animation_data.action_slot is None: arm.animation_data.action_slot = act_new.slots[0]
    act = act_new
    bpy.data.objects.remove(ref_arm)
    if WRAP:
        arm.data.pose_position = "REST"; bpy.context.view_layer.update()
        for o in bpy.context.selected_objects: o.select_set(False)
        body.select_set(True); bpy.context.view_layer.objects.active = body
        sw = body.modifiers.new("wrap", "SHRINKWRAP"); sw.target = wrap_target; sw.wrap_method = "NEAREST_SURFACEPOINT"
        while body.modifiers.find("wrap") > 0: bpy.ops.object.modifier_move_up(modifier="wrap")   # before the armature
        bpy.ops.object.modifier_apply(modifier="wrap")
        sm_ = body.modifiers.new("sm2", "SMOOTH"); sm_.iterations = 2; sm_.factor = .5
        while body.modifiers.find("sm2") > 0: bpy.ops.object.modifier_move_up(modifier="sm2")
        bpy.ops.object.modifier_apply(modifier="sm2")
        dc = body.modifiers.new("dec2", "DECIMATE"); dc.ratio = min(1, int(FACES) / len(body.data.polygons))
        while body.modifiers.find("dec2") > 0: bpy.ops.object.modifier_move_up(modifier="dec2")
        bpy.ops.object.modifier_apply(modifier="dec2")
        for p in body.data.polygons: p.use_smooth = False
        bpy.data.objects.remove(wrap_target)
        arm.data.pose_position = "POSE"; bpy.context.view_layer.update()
        print("WRAP done:", len(body.data.polygons), "faces")
    print("GOAL mesh in:", len(new.data.polygons), "faces,", len(new.vertex_groups), "groups; retargeted", f1_ - f0_ + 1, "frames")

# ---- face +x, in feet: turn the rig about z so the skull is ahead of the pelvis along +x
sc.frame_set(int(act.frame_range[0]))
pw = lambda n: arm.matrix_world @ arm.pose.bones[n].head
d = pw("HorseScull") - pw("HorsePelvis")
arm.rotation_euler.z += -math.atan2(d.y, d.x); arm.scale = (arm.scale.x * FT,) * 3
bpy.context.view_layer.update()

# ---- one stride: the period of the left fore hoof's height; then how far the ground moves under a planted hoof
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
hz, hx = [], []
for f in range(f0, f1 + 1):
    sc.frame_set(f); p = pw("HorseLFrontHoof"); hz.append(p.z); hx.append(p.x)
def err(T): return sum(abs(hz[i] - hz[i + T]) for i in range(len(hz) - T)) / (len(hz) - T)
T = min(range(8, len(hz) // 2 + 1), key=err)
zmin = min(hz); planted = [i for i in range(len(hz) - 1) if hz[i] < zmin + .15 and hz[i + 1] < zmin + .15]
v = sum(hx[i] - hx[i + 1] for i in planted) / max(1, len(planted))                  # ft per frame the hoof slides back
stride = v * T
print("PERIOD", T, "frames  STRIDE_FT", round(stride, 2), "err", round(err(T), 3))
act.frame_range = (f0, f0 + T); sc.frame_start, sc.frame_end = f0, f0 + T - 1
# the tail: the clip swings it hard, and a solid low-poly tail reads as a blade. Damp its rotations to 35% of the
# animated value (slerp toward rest) on every frame of the stride
from mathutils import Quaternion as Q_
TAIL_DAMP = float(os.environ.get("TAIL_DAMP", ".35"))
tails = [b for b in arm.pose.bones if b.name.startswith("HorseTail")]
for b in tails: b.rotation_mode = "QUATERNION"
for f in range(f0, f0 + T + 1):
    sc.frame_set(f)
    for b in tails:
        q = b.rotation_quaternion.copy(); b.rotation_quaternion = Q_((1, 0, 0, 0)).slerp(q, TAIL_DAMP); b.keyframe_insert("rotation_quaternion", frame=f)

# ---- body motion, in armature space
from mathutils import Matrix, Quaternion
# the animator moved the legs; add what a trotting body does on top: it rises and falls twice a stride (lowest
# mid-stance), pitches with each diagonal, rolls once a stride, the spine snakes a little, the neck is carried low
# and nods against the lift, and the tail swings and lifts. Phases are taken from the left fore's landing.
tl = min(range(T), key=lambda i: hz[i]) / T
pb = arm.pose.bones
def turn(name, axis, ang):
    b = pb[name]; p = b.head.copy()
    b.matrix = Matrix.Translation(p) @ Quaternion(axis, ang).to_matrix().to_4x4() @ Matrix.Translation(-p) @ b.matrix
    bpy.context.view_layer.update()
# which way is "nose down" about lat: try it on the neck and look where the skull goes
sc.frame_set(f0); y0 = pb["HorseScull"].head.y; turn("HorseNeck1", lat, .2); y1 = pb["HorseScull"].head.y
if y1 > y0: lat = -lat
sc.frame_set(f0)
touched = ["HorsePelvis", "HorseSpine2", "HorseSpine4", "HorseSpine6", "HorseRibcage", "HorseNeck1", "HorseNeck3", "HorseNeck5", "HorseScull"] + [f"HorseTail{k}" for k in range(1, 6)]
GALLOP = "Gallop" in SRC
# the added body-motion layer is off by default: it read as bobbing on the Meshy horse. BODY_LAYER=1 turns it on for the trot
for f in (range(f0, f0 + T + 1) if (os.environ.get("BODY_LAYER") and not GALLOP) else []):
    sc.frame_set(f); t = (f - f0) / T - tl; w2 = 4 * math.pi * t; w1 = 2 * math.pi * t
    b = pb["HorsePelvis"]; m = b.matrix.copy(); m.translation += up * (-.07 * U * math.cos(w2)); b.matrix = m; bpy.context.view_layer.update()
    turn("HorsePelvis", lat, .05 * math.sin(w2))                                       # positive = nose down
    turn("HorsePelvis", fwd, .045 * math.sin(w1))
    for k, n in enumerate(("HorseSpine2", "HorseSpine4", "HorseSpine6")):
        turn(n, up, .025 * math.sin(w1 + .5 * k)); turn(n, lat, -.015 * math.sin(w2 + .4 * k))
    turn("HorseRibcage", fwd, -.06 * math.sin(w1 + .6))
    turn("HorseNeck1", lat, .14 + .05 * math.cos(w2 + .9))                              # carried low, nodding
    turn("HorseNeck3", lat, .06 + .03 * math.cos(w2 + 1.3))
    turn("HorseNeck5", up, .02 * math.sin(w1 + 1.0))
    turn("HorseScull", lat, -.12 + .03 * math.cos(w2 + 1.7))                             # face back to the front
    for k in range(1, 6):
        turn(f"HorseTail{k}", up, .07 * math.sin(w1 - .5 * k)); turn(f"HorseTail{k}", lat, -.05 * math.sin(w2 - .5 * k))
    for n in touched:
        b = pb[n]; b.keyframe_insert("rotation_quaternion" if b.rotation_mode == "QUATERNION" else "rotation_euler", frame=f)
        if n == "HorsePelvis": b.keyframe_insert("location", frame=f)

# nose at +x for placing: report it
sc.frame_set(f0); nose = max((body.matrix_world @ v.co).x for v in body.data.vertices)
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
cl = [ev.matrix_world @ me.vertices[vi].co for p in me.polygons if p.material_index == 1 for vi in p.vertices]
if cl: print("CLOTH x", round(min(c.x for c in cl), 2), round(max(c.x for c in cl), 2), "z", round(min(c.z for c in cl), 2), round(max(c.z for c in cl), 2), "y", round(max(c.y for c in cl), 2))
ev.to_mesh_clear()
print("NOSE_X", round(nose, 2), "HEIGHT", round(max((body.matrix_world @ v.co).z for v in body.data.vertices), 2))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=True, export_force_sampling=True, export_frame_range=True, export_apply=False)

sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE" if (GOAL and not os.environ.get("WRAP")) else "VERTEX"
sc.render.resolution_x, sc.render.resolution_y = 600, 420; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 11; cam.location = (0, -40, 3.4); cam.rotation_euler = (math.pi / 2, 0, 0)
for k in range(6):
    sc.frame_set(f0 + round(T * k / 6)); sc.render.filepath = STRIP.replace(".png", f"_{k}.png"); bpy.ops.render.render(write_still=True)
