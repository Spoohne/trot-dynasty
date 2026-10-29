# blender -b -P belly_strip.py -- horse.glb out.png : six frames framed on the barrel, side view
import bpy, sys, math
SRC, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
if hasattr(act, "slots") and len(act.slots): arm.animation_data.action_slot = act.slots[0]
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 600, 420; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 7; cam.location = (-4.4, -30, 3.6); cam.rotation_euler = (math.pi / 2, 0, 0)
for k in range(6):
    sc.frame_set(f0 + round((f1 - f0) * k / 6)); sc.render.filepath = OUT.replace(".png", f"_{k}.png"); bpy.ops.render.render(write_still=True)
