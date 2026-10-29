# blender -b -P anim_any.py -- in.(fbx|glb) out_dir [step]
# Render every `step`-th frame of a model's animation from the side, auto-framed, textured; for GIF review.
import bpy, sys, math, os
from mathutils import Vector
A = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = A[0], A[1]; STEP = int(A[2]) if len(A) > 2 else 1
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
(bpy.ops.import_scene.fbx if SRC.lower().endswith(".fbx") else bpy.ops.import_scene.gltf)(filepath=SRC)
sc = bpy.context.scene
arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = arm.animation_data.action if arm.animation_data and arm.animation_data.action else bpy.data.actions[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
meshes = [o for o in sc.objects if o.type == "MESH"]
def bounds():
    dg = bpy.context.evaluated_depsgraph_get(); P = []
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); P += [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
    return Vector([min(p[i] for p in P) for i in range(3)]), Vector([max(p[i] for p in P) for i in range(3)])
sc.frame_set(f0); lo, hi = bounds(); c = (lo + hi) / 2; size = max(hi - lo)
long_x = (hi.x - lo.x) >= (hi.y - lo.y)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 720, 480; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.5
d = Vector((0, -1, 0)) if long_x else Vector((1, 0, 0))
cam.location = c + d * size * 4; cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
for f in range(f0, f1, STEP):
    sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"f{f:03d}.png"); bpy.ops.render.render(write_still=True)
print("FRAMES", f0, f1, "size", round(size, 4))
