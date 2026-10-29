# blender -b -P neck_len.py -- horse.glb : how much the neck's length (withers top to poll top, on fixed vertices) changes over the stride
import bpy, sys
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]
def pts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return P
arm.data.pose_position = "REST"; bpy.context.view_layer.update(); R = pts()
xs = [p.x for p in R]; L = max(xs) - min(xs); x0 = min(xs)
iw = max((i for i in range(len(R)) if abs(R[i].x - (x0 + .62 * L)) < .03 * L), key=lambda i: R[i].z)
ip = max((i for i in range(len(R)) if abs(R[i].x - (x0 + .86 * L)) < .03 * L), key=lambda i: R[i].z)
l0 = (R[ip] - R[iw]).length
arm.data.pose_position = "POSE"; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); ls = []
for f in range(f0, f1): sc.frame_set(f); P = pts(); ls.append((P[ip] - P[iw]).length / l0)
print(f"NECK length vs rest: {100*min(ls):.0f}%..{100*max(ls):.0f}%  (stretch swing {100*(max(ls)-min(ls)):.0f}%)")
