# blender -b -P deform_measure.py -- horse.glb : belly drift vs the spine, and "tinfoil" (faces in the upper legs and
# flanks that crush below 55% of their rest area, or flip) across the stride
import bpy, sys
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]
def pts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return P
arm.data.pose_position = "REST"; bpy.context.view_layer.update(); R = pts()
hip_rest = (arm.matrix_world @ arm.pose.bones["Hips"].matrix).copy()
H = max(p.z for p in R); xs = [p.x for p in R]; x0, x1 = min(xs), max(xs)
belly = [i for i, p in enumerate(R) if x0 + .3 * (x1 - x0) < p.x < x0 + .6 * (x1 - x0) and H * .42 < p.z < H * .55]
polys = [p.vertices[:] for p in body.data.polygons]
def area(P, f):
    a, b, c = P[f[0]], P[f[1]], P[f[2]]; return (b - a).cross(c - a)
zone = [k for k, f in enumerate(polys) if H * .3 < sum(R[i].z for i in f) / 3 < H * .62]   # upper legs, elbows, stifles, flanks
A0 = {k: area(R, polys[k]) for k in zone}
arm.data.pose_position = "POSE"; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); drift = []; crush = []
from collections import Counter
where = Counter()
def owner(f):
    c = Counter()
    for i in f:
        for g in body.data.vertices[i].groups: c[body.vertex_groups[g.group].name] += g.weight
    return c.most_common(1)[0][0] if c else "?"
own = {k: owner(polys[k]) for k in zone}
zone = [k for k in zone if not own[k].startswith('tail')]                               # the tail is meant to fold
A0 = {k: A0[k] for k in zone}
for f in range(f0, f1):
    sc.frame_set(f); P = pts()
    rel = (arm.matrix_world @ arm.pose.bones["Hips"].matrix) @ hip_rest.inverted()
    drift.append(sum(((P[i]) - (rel @ R[i])).length for i in belly) / len(belly))
    bad = 0
    for k in zone:
        a = area(P, polys[k]); a0 = A0[k]
        if a0.length < 1e-9: continue
        if a.length < .55 * a0.length or a.dot(a0) < 0: bad += 1; where[own[k]] += 1
    crush.append(bad / len(zone))
print("WHERE", where.most_common(6)); print(f"MEASURE belly_drift {sum(drift)/len(drift):.3f} ft  tinfoil avg {100*sum(crush)/len(crush):.1f}%  worst frame {100*max(crush):.1f}%")
