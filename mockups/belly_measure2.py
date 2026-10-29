# blender -b -P belly_measure2.py -- horse.glb : take the belly-line vertices in the rest pose (underside, between the
# legs), then per frame measure how far each moves relative to a rigid frame carried by the Hips bone.
import bpy, sys
from mathutils import Vector
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
R = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
xs = sorted(p.x for p in R); x0, x1 = xs[0], xs[-1]
# belly: the lowest 15% of the body above the elbows, in the middle 30-60% of the length
zs = [p.z for p in R]; H = max(zs)
idx = [i for i, p in enumerate(R) if x0 + .3 * (x1 - x0) < p.x < x0 + .6 * (x1 - x0) and H * .42 < p.z < H * .55]
hip_rest = (arm.matrix_world @ arm.pose.bones["Hips"].matrix).copy()
arm.data.pose_position = "POSE"; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); worst = []
for f in range(f0, f1):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    hip = arm.matrix_world @ arm.pose.bones["Hips"].matrix
    rel = hip @ hip_rest.inverted()                                                          # rigid carry with the hips
    d = [((P[i]) - (rel @ R[i])).length for i in idx]
    worst.append((max(d), sum(d) / len(d)))
# which vertices drift worst, and what weights them
sc.frame_set(f0 + (f1 - f0) // 2); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
hip = arm.matrix_world @ arm.pose.bones["Hips"].matrix; rel = hip @ hip_rest.inverted()
bad = sorted(idx, key=lambda i: -((P[i]) - (rel @ R[i])).length)[:6]
for i in bad:
    v = body.data.vertices[i]
    print("BAD", i, "rest", tuple(round(c, 2) for c in R[i]), "drift", round(((P[i]) - (rel @ R[i])).length, 2), [(body.vertex_groups[g.group].name, round(g.weight, 2)) for g in v.groups if g.weight > .02])
print(f"belly verts {len(idx)}  avg drift {sum(w[1] for w in worst)/len(worst):.3f} ft  peak {max(w[0] for w in worst):.3f} ft")
