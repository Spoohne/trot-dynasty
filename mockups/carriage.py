# blender -b -P carriage.py -- horse.glb : head carriage against the back. Heights (ft) of the poll and the muzzle
# relative to the withers, and the neck's angle above the back line (croup -> withers), over the stride
import bpy, sys, math
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]
def pts():
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear(); return P
arm.data.pose_position = "REST"; bpy.context.view_layer.update(); R = pts()
xs = [p.x for p in R]; L = max(xs) - min(xs); x0 = min(xs)
top = lambda fr: max((i for i in range(len(R)) if abs(R[i].x - (x0 + fr * L)) < .025 * L), key=lambda i: R[i].z)
iw, ic, ip = top(.60), top(.30), top(.86)                                                     # withers, croup, poll
im = max(range(len(R)), key=lambda i: R[i].x - .3 * R[i].z)                                    # muzzle
def m(P):
    w = P[iw]; back = w - P[ic]; neck = P[ip] - w
    a = math.degrees(math.atan2(neck.z, neck.x) - math.atan2(back.z, back.x))
    return P[ip].z - w.z, P[im].z - w.z, a
r = m(R); print(f"REST  poll {r[0]:+.2f} ft, muzzle {r[1]:+.2f} ft vs withers; neck {r[2]:.0f} deg above the back")
arm.data.pose_position = "POSE"; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); V = []
for f in range(f0, f1): sc.frame_set(f); V.append(m(pts()))
for k, nm in enumerate(("poll", "muzzle", "neck angle")):
    c = [v[k] for v in V]; u = "deg" if k == 2 else "ft"
    print(f"RUN   {nm:10s} {min(c):+.2f}..{max(c):+.2f} (avg {sum(c)/len(c):+.2f}) {u}")
