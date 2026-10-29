# blender -b -P rest_guide.py -- Horse_Base.fbx out.png
# Render the bought horse in its rest (bind) pose, tack removed, plain on white, slightly turned toward the camera:
# the guide image the restyle keeps the pose and proportions from, so the new mesh lines up with the rig.
import bpy, sys, math
from mathutils import Vector
SRC, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type == "MESH" and o.name != "Horse_LOW": bpy.data.objects.remove(o)
arm = next(o for o in sc.objects if o.type == "ARMATURE")
if arm.animation_data: arm.animation_data.action = None
for b in arm.pose.bones: b.matrix_basis.identity()
body = sc.objects["Horse_LOW"]; bpy.context.view_layer.update()
P = [body.matrix_world @ v.co for v in body.data.vertices]
lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)]); c = (lo + hi) / 2
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "SINGLE"
sc.display.shading.single_color = (.42, .25, .16)
sc.render.resolution_x = sc.render.resolution_y = 1024
w = bpy.data.worlds.new("w"); sc.world = w; w.color = (1, 1, 1)
sc.render.film_transparent = False
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = max(hi - lo) * 1.15
long_axis = Vector((1, 0, 0)) if hi.x - lo.x > hi.y - lo.y else Vector((0, 1, 0))
side = long_axis.cross(Vector((0, 0, 1))).normalized()
d = (side * math.cos(math.radians(25)) + long_axis * math.sin(math.radians(25))) * 20     # turned ~25 degrees
cam.location = c + d; cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True)
print("BOUNDS", tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))
