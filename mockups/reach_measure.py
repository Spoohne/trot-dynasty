# blender -b -P reach_measure.py -- horse.glb : how far the front and hind hooves travel fore-aft relative to the body
# over a stride (reach), and the body's height range
import bpy, sys
SRC = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1]); W = arm.matrix_world
fx, hx, hip = [], [], []
for f in range(f0, f1):
    sc.frame_set(f); hp = W @ arm.pose.bones["Hips"].head
    fx.append((W @ arm.pose.bones["frontleg2"].tail).x - hp.x); hx.append((W @ arm.pose.bones["backleg2"].tail).x - hp.x); hip.append(hp.z)
print(f"REACH front hoof {max(fx)-min(fx):.2f} ft, hind hoof {max(hx)-min(hx):.2f} ft; hip height {min(hip):.2f}..{max(hip):.2f}")
