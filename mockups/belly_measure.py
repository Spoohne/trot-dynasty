# blender -b -P belly_measure.py -- horse.glb : per frame, the barrel's depth (back to belly) at 3 stations along it
import bpy, sys
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
rows = []
for f in range(f0, f1):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    out = []
    for x in (-6.3, -5.0, -3.9):                                                             # loin, mid-barrel, girth (ft from the nose)
        band = [p for p in P if abs(p.x - x) < .25 and abs(p.y) < .9 and p.z > 1.5]
        out.append(max(p.z for p in band) - min(p.z for p in band) if band else 0)
    rows.append(out)
import statistics as st
for i, nm in enumerate(("loin", "mid", "girth")):
    col = [r[i] for r in rows]; print(f"{nm:6s} depth min {min(col):.2f} max {max(col):.2f} swing {max(col)-min(col):.2f} ft")
