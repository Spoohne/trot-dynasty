# Run inside Blender after build_horse.py: brings in mockups/sulky_driver.glb (build_sulky.py's output) and fits it
# to race_b.png. The sulky is scaled so its wheel matches the sprite's (22.6 px radius, hub at 35.5,153); the driver
# keeps its own size, reclines 0.35 rad and sits with the seat of the pants on the seat (sprite 30,127).
import bpy
from mathutils import Vector
K, X0, GROUND = 0.066, 112, 172
sc = bpy.data.scenes["Horse"]; bpy.context.window.scene = sc
for o in [o for o in sc.objects if o.name.startswith(("sulky", "wheel", "driver", "Cylinder", "Cube", "Torus"))]:
    bpy.data.objects.remove(o)
for m in [m for m in bpy.data.materials if m.name.split(".")[0] in ("silk", "white", "boot", "skin", "wheel", "seat", "spoke")]:
    bpy.data.materials.remove(m)                                      # so a rerun imports "silk", not "silk.001"
bpy.ops.import_scene.gltf(filepath=r"C:\Users\spooh\HarnessSim\mockups\sulky_driver.glb")
root = bpy.data.objects["sulky"]; S = 1.49 / 1.19
root.scale = (S,) * 3; root.location = ((35.5 - X0) * K, 0, (GROUND - 153) * K - 1.15 * S)
root.parent = bpy.data.objects["horse"]
m = bpy.data.materials["silk"]; b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.0, 0.025, 0.42, 1)       # race_b's blue; the replay re-dyes "silk" per runner
d = bpy.data.objects["driver"]
d.scale = (1 / S,) * 3; d.rotation_mode = "XYZ"                     # glTF imports in quaternion mode
d.rotation_euler = (0, -.35, 0); d.location = (1.4, 0, 2.2); bpy.context.view_layer.update()
vs = [d.matrix_world @ v.co for v in d.data.vertices]
xm = min(c.x for c in vs) + .25 * (max(c.x for c in vs) - min(c.x for c in vs))
butt = min((c for c in vs if c.x < xm), key=lambda c: c.z)
sh = Vector(((30 - X0) * K, 0, (GROUND - 127) * K)) - butt; sh.y = 0
M = d.matrix_world.copy(); M.translation += sh; d.matrix_world = M
