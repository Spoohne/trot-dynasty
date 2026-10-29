# blender -b -P build_sulky.py -- driver.glb out.glb preview.png
# The sulky and its driver as one low-poly GLB, in feet, axle at the origin, shafts running forward (+x) to the
# horse. Materials are named so the replay can recolor per runner: "silk" (driver's jacket and helmet, the sulky
# frame), "white", "boot", "skin", "wheel", "seat". Each wheel hangs from an unrotated empty ("wheelL"/"wheelR")
# at its hub, so the page spins it about its own lateral axis.
import bpy, sys, math
from mathutils import Vector
DRV, OUT, PNG = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
exec(open(__file__.replace("build_sulky.py", "lowpoly_lib.py")).read())
sc = bpy.context.scene

def mat(name, hexc, rough=.7):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = tuple((int(hexc[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5)) + (1,)
    b.inputs["Roughness"].default_value = rough; return m
SILK, WHITE, BOOT, SKIN, WHEEL, SEAT = (mat("silk", "#ffffff", .55), mat("white", "#e9ecf0"), mat("boot", "#0d0d0f"),
                                        mat("skin", "#d6a985"), mat("wheel", "#14161b", .5), mat("seat", "#1c1e25"))
def tube(p0, p1, r, m, parent=None):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); flat(o)
    if parent: o.parent = parent
    return o

root = bpy.data.objects.new("sulky", None); sc.collection.objects.link(root)
# wheels: dark disc, colored rim, two spokes; on empties at the hubs
for s, nm in ((1, "wheelL"), (-1, "wheelR")):
    e = bpy.data.objects.new(nm, None); sc.collection.objects.link(e); e.location = (0, s * 2.05, 1.15); e.parent = root
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.15, depth=.1, location=(0, 0, 0), rotation=(math.pi / 2, 0, 0))
    o = bpy.context.object; o.data.materials.append(WHEEL); flat(o); o.parent = e
    bpy.ops.mesh.primitive_torus_add(major_radius=1.12, minor_radius=.07, major_segments=16, minor_segments=4, location=(0, s * .06, 0), rotation=(math.pi / 2, 0, 0))
    o = bpy.context.object; o.data.materials.append(SILK); flat(o); o.parent = e
    for a in (0, math.pi / 2): tube((1.05 * math.cos(a), s * .07, 1.05 * math.sin(a)), (-1.05 * math.cos(a), s * .07, -1.05 * math.sin(a)), .03, mat("spoke", "#4a505c"), e)
    # the frame: from the hub up and forward in an arch, then out along the shaft to the horse's girth
    tube((0, s * 2.0, 1.15), (.9, s * 1.6, 2.75), .07, SILK, root)
    tube((.9, s * 1.6, 2.75), (3.4, s * 1.25, 3.25), .07, SILK, root)
    tube((3.4, s * 1.25, 3.25), (6.6, s * 1.1, 3.9), .065, SILK, root)
tube((0, -2.05, 1.15), (0, 2.05, 1.15), .07, SILK, root)                                   # axle
tube((.9, -1.6, 2.75), (.9, 1.6, 2.75), .06, SILK, root)                                   # cross bar under the seat
bpy.ops.mesh.primitive_cube_add(size=1, location=(-.3, 0, 2.45), scale=(1.0, 1.1, .18)); o = bpy.context.object; o.data.materials.append(SEAT); flat(o); o.parent = root
bpy.ops.mesh.primitive_cube_add(size=1, location=(-.8, 0, 2.95), scale=(.15, 1.0, .85)); o = bpy.context.object; o.rotation_euler.y = -.35; o.data.materials.append(SEAT); flat(o); o.parent = root

# the driver: Hunyuan mesh, feet toward +x, painted into the named slots
drv = prep(DRV, 4.6, 1800)
co = [v.co for v in drv.data.vertices]
if max(co, key=lambda c: c.z).x > 0:
    for v in drv.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
DH = max(v.co.z for v in drv.data.vertices); DX = max(v.co.x for v in drv.data.vertices)
drv.data.materials.clear()                                                     # the Hunyuan import brings its own slot 0
for m in (SILK, WHITE, BOOT, SKIN): drv.data.materials.append(m)
top = max(drv.data.vertices, key=lambda v: v.co.z).co.copy()
for p in drv.data.polygons:
    c = p.center
    face = (c - top).length < .75 and c.x > top.x + .12 and c.z < top.z - .3
    p.material_index = 2 if c.x > DX - .75 else (1 if c.z < DH * .42 and c.x > -1.2 else (3 if face else 0))
drv.location = (1.4, 0, 2.2); drv.parent = root
drv.name = "driver"

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_apply=True)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "MATERIAL"
sc.render.resolution_x, sc.render.resolution_y = 800, 450; sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 12; cam.location = (3.5, -30, 6); cam.rotation_euler = (Vector((3.5, 0, 2.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
sc.render.filepath = PNG; bpy.ops.render.render(write_still=True)
