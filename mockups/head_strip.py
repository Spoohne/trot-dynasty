# blender -b -P head_strip.py -- horse.glb out.png
# Six frames of the exported horse's clip, framed on the head and neck from the side, to check the skinning there.
import bpy, sys, math
from mathutils import Vector
SRC, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene
arm = next(o for o in sc.objects if o.type == "ARMATURE"); body = next(o for o in sc.objects if o.type == "MESH")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 600, 420; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 5.5
for k in range(6):
    f = f0 + round((f1 - f0) * k / 6); sc.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
    P = [ev.matrix_world @ v.co for v in me.vertices]; nose = max(P, key=lambda p: p.x); ev.to_mesh_clear()
    cam.location = (nose.x - 2.2, -30, nose.z - .4); cam.rotation_euler = (math.pi / 2, 0, 0)
    sc.render.filepath = OUT.replace(".png", f"_{k}.png"); bpy.ops.render.render(write_still=True)
    print("FRAME", f, "nose", tuple(round(v, 2) for v in nose))
