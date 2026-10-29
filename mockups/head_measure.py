# blender -b -P head_measure.py -- horse.glb : per frame, the face's angle below horizontal (poll->muzzle bone) and
# the neck's angle above horizontal, plus how much each swings over the stride
import bpy, sys, math
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
def ang(n, down):
    pb = arm.pose.bones[n]; h = arm.matrix_world @ pb.head; t = arm.matrix_world @ pb.tail; d = t - h
    return math.degrees(math.atan2(-d.z if down else d.z, math.hypot(d.x, d.y)))
arm.data.pose_position = "REST"; bpy.context.view_layer.update()
print(f"REST face {ang('headend', True):.0f} deg below horizontal, neck {ang('head', False):.0f} deg above")
arm.data.pose_position = "POSE"
fa, ne = [], []
for f in range(f0, f1):
    sc.frame_set(f); fa.append(ang("headend", True)); ne.append(ang("head", False))
print(f"RUN face {min(fa):.0f}..{max(fa):.0f} (avg {sum(fa)/len(fa):.0f}) deg below horiz; neck {min(ne):.0f}..{max(ne):.0f} (avg {sum(ne)/len(ne):.0f}) deg above")

# the visible face, tracked on fixed vertices: muzzle tip and the poll (top of the skull a head-length back), chosen at rest
body = next(o for o in sc.objects if o.type == "MESH")
def pts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return P
arm.data.pose_position = "REST"; bpy.context.view_layer.update(); R = pts()
xs = [p.x for p in R]; L = max(xs) - min(xs)
im = max(range(len(R)), key=lambda i: R[i].x - .3 * R[i].z)
band = [i for i in range(len(R)) if abs(R[i].x - (R[im].x - .2 * L)) < .03 * L]
ip = max(band, key=lambda i: R[i].z)
def ang(P): d = P[im] - P[ip]; return math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y)))
rest = ang(R); arm.data.pose_position = "POSE"; vals = []; nz = []; hp = []; dx = []; dzz = []
inose = im; iwith = max(range(len(R)), key=lambda i: R[i].z if abs(R[i].x - (min(xs) + .62 * L)) < .03 * L else -9)
for f in range(f0, f1):
    sc.frame_set(f); P = pts(); vals.append(ang(P)); d = P[inose] - P[iwith]; nz.append(math.degrees(math.atan2(d.z, d.x))); dx.append(d.x); dzz.append(d.z)
    pb = arm.pose.bones["Hips"]; v = (arm.matrix_world.to_3x3() @ (pb.tail - pb.head)); hp.append(math.degrees(math.atan2(v.z, math.hypot(v.x, v.y))))
print(f"TRAVEL nose vs withers: fore-aft {max(dx)-min(dx):.2f} ft, up-down {max(dzz)-min(dzz):.2f} ft"); print(f"PUMP nose-vs-withers swing {max(nz)-min(nz):.0f} deg; body pitch swing {max(hp)-min(hp):.0f} deg")
print(f"MESH face line: rest {rest:.0f}, running {min(vals):.0f}..{max(vals):.0f} (avg {sum(vals)/len(vals):.0f}) deg below horizontal; nod swing {max(vals)-min(vals):.0f} deg")
