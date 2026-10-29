# blender -b -P anim_clip.py -- horse.glb out_dir : every frame of the clip from the side, textured, for a GIF
import bpy, sys, math, os
SRC, OUT = sys.argv[sys.argv.index("--") + 1:]
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=SRC)
sc = bpy.context.scene; arm = next(o for o in sc.objects if o.type == "ARMATURE")
act = bpy.data.actions[0]; arm.animation_data_create(); arm.animation_data.action = act
f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "VERTEX" if not any(m.node_tree.nodes.get("Image Texture") for m in bpy.data.materials if m.use_nodes) else "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 720, 420; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 12; cam.location = (0, -30, 3.2); cam.rotation_euler = (math.pi / 2, 0, 0)
for f in range(f0, f1):
    sc.frame_set(f); sc.render.filepath = os.path.join(OUT, f"f{f:03d}.png"); bpy.ops.render.render(write_still=True)
print("FRAMES", f1 - f0)
