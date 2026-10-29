# blender -b -P inspect_fbx.py -- in.fbx strip.png
# Report what an FBX holds (meshes, armature, bones, action frame range, size) and render 6 side-view frames.
import bpy, sys, math
from mathutils import Vector
SRC, STRIP = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
sc = bpy.context.scene
for o in sc.objects:
    info = o.type
    if o.type == "MESH": info += f" tris~{sum(len(p.vertices) - 2 for p in o.data.polygons)} dims={tuple(round(d, 2) for d in o.dimensions)} groups={len(o.vertex_groups)}"
    if o.type == "ARMATURE":
        info += f" bones={len(o.data.bones)}"
        a = o.animation_data.action if o.animation_data else None
        if a: info += f" action={a.name} frames={tuple(a.frame_range)}"
    print("OBJ", o.name, info)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
print("BONES", [b.name for b in arm.data.bones][:60])
a = arm.animation_data.action
f0, f1 = int(a.frame_range[0]), int(a.frame_range[1])
meshes = [o for o in sc.objects if o.type == "MESH"]
lo = Vector([min((o.matrix_world @ Vector(b))[i] for o in meshes for b in o.bound_box) for i in range(3)])
hi = Vector([max((o.matrix_world @ Vector(b))[i] for o in meshes for b in o.bound_box) for i in range(3)])
print("BOUNDS", tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 600, 420; sc.world = bpy.data.worlds.new("w")
c = (lo + hi) / 2; size = max(hi - lo)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.15
long_x = (hi.x - lo.x) >= (hi.y - lo.y)
cam.location = c + (Vector((0, -size * 3, 0)) if long_x else Vector((size * 3, 0, 0)))
cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
for k in range(6):
    sc.frame_set(f0 + round((f1 - f0) * k / 6)); sc.render.filepath = STRIP.replace(".png", f"_{k}.png"); bpy.ops.render.render(write_still=True)
