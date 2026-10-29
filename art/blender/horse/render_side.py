# Side-on ortho render framed exactly like race_b.png: 1 sprite pixel = K ft, so at RES = 242 the horse lands on
# the sprite's own pixels. Camera on -y looking +y (the horse's near side, facing right). Set OUT and RES first.
import bpy, math
from mathutils import Vector
sc = bpy.data.scenes["Horse"]; K, X0, GROUND = 0.066, 112, 172
cam = bpy.data.objects.get("side_cam") or bpy.data.objects.new("side_cam", bpy.data.cameras.new("side_cam"))
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cam.data.type = "ORTHO"; cam.data.ortho_scale = 242 * K
cam.location = ((121 - X0) * K, -40, (GROUND - 121) * K); cam.rotation_euler = (math.pi / 2, 0, 0)
sc.camera = cam
sun = bpy.data.objects.get("key") or bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
if sun.name not in sc.collection.objects: sc.collection.objects.link(sun)
sun.data.energy = 6.0; sun.rotation_euler = (math.radians(32), 0, math.radians(35))  # steep from above, camera side: lit topline, shadowed belly
fill = bpy.data.objects.get("fill") or bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
if fill.name not in sc.collection.objects: sc.collection.objects.link(fill)
fill.data.energy = .3; fill.rotation_euler = (math.radians(110), 0, math.radians(20))  # low, camera side: keeps bellies off black
sc.world = sc.world or bpy.data.worlds.new("horse_world"); sc.world.use_nodes = True
bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (.06, .06, .08, 1); bg.inputs[1].default_value = .12
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True, scene=sc.name)
print(sc.render.engine, OUT)
