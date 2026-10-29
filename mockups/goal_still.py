# blender -b -P goal_still.py -- horse.glb sulky.glb num.png frame out.png
# A still framed like the goal image: the faceted bought horse mid-trot with black harness, a red saddle cloth with
# its number, the sulky and driver close behind, on a daylight track with a soft-focus infield behind.
import bpy, sys, math, random
from mathutils import Vector
HORSE, SULKY, NUM, FRAME, OUT = sys.argv[sys.argv.index("--") + 1:]
random.seed(2)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
lin = lambda h: tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5)) + (1,)
def mat(name, col, rough=.8):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(col); b.inputs["Roughness"].default_value = rough; return m
def flat(o):
    if o.type == "MESH":
        for p in o.data.polygons: p.use_smooth = False
def tube(pts, r, m, closed=False):
    cu = bpy.data.curves.new("t", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = r; cu.bevel_resolution = 1
    sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1); sp.use_cyclic_u = closed
    for k, p in enumerate(pts): sp.points[k].co = (*p, 1)
    o = bpy.data.objects.new("t", cu); sc.collection.objects.link(o); o.data.materials.append(m); return o

RED = "#d42a2a"; TACK = mat("tack", "#0c0c0e", .45)
# ---- horse at the chosen frame of its stride
before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=HORSE)
hobs = [o for o in bpy.data.objects if o not in before]
sc.frame_set(int(FRAME))
body = next(o for o in hobs if o.type == "MESH")
for m in body.data.materials:
    if m.name.startswith("cloth"): m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lin(RED)
flat(body)
dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh()
P = [ev.matrix_world @ v.co for v in me.vertices]; ev.to_mesh_clear()
def slab(x0, x1): return [p for p in P if x0 < p.x < x1]
def hi(x0, x1): return max(p.z for p in slab(x0, x1))
def lo(x0, x1, zmin): return min(p.z for p in slab(x0, x1) if p.z > zmin)
def wid(x0, x1, z0, z1): return max(abs(p.y) for p in slab(x0, x1) if z0 < p.z < z1)
mouth = max(P, key=lambda p: p.x)
# harness: girth band round the barrel behind the elbow, breast collar across the chest, back strap and crupper
gx = .6; top, bot = hi(gx - .2, gx + .2), lo(gx - .2, gx + .2, 2.2); w = wid(gx - .2, gx + .2, bot, top) + .04
ring = [(gx + .05 * math.cos(a), w * math.sin(a), (top + bot) / 2 + (top - bot) / 2 * 1.02 * math.cos(a)) for a in [k * math.pi / 8 for k in range(16)]]
import os
MESHY = bool(os.environ.get("MESHY"))
if not MESHY: tube(ring, .1, TACK, True)
cx = max(p.x for p in P if 3.2 < p.z < 4.2) - .05; cz = 3.9
if not MESHY: tube([(cx - 1.4, w * .98, cz + .3), (cx - .1, .55, cz), (cx, 0, cz - .1), (cx - .1, -.55, cz), (cx - 1.4, -w * .98, cz + .3)], .09, TACK)
tail = min(P, key=lambda p: p.x if p.z > hi(-3.5, -3.0) - .4 else 9)
if not MESHY and not os.environ.get("MESHY_SULKY"): tube([(gx - .3, 0, top + .1), (-1.6, 0, hi(-1.7, -1.5) + .06), (-2.8, 0, hi(-2.9, -2.7) + .05), (tail.x + .2, 0, tail.z)], .07, TACK)
# the number on both sides of the cloth
img = bpy.data.images.load(NUM); nm = bpy.data.materials.new("num"); nm.use_nodes = True
tx = nm.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = img; nm.node_tree.links.new(tx.outputs["Color"], nm.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
cloth = [ev.matrix_world @ v.co for v in body.data.vertices] if False else None
for s in (1, -1):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-.55, s * (wid(-1.4, .3, 3.0, 4.6) + .04), 3.95), rotation=(math.pi / 2, 0, 0 if s < 0 else math.pi)); bpy.context.object.scale = (1.9, 1.5, 1)   # the saddle cloth itself, number and all
    bpy.context.object.data.materials.append(nm)

# ---- sulky and driver; the sulky's axle sits 6 ft behind the horse's origin as in the replay
before = set(bpy.data.objects)
MS = os.environ.get("MESHY_SULKY")
if MS:
    # a Meshy sulky-and-driver: one textured mesh. Shafts to +x, wheels on the ground, 4.9 ft tall, shaft tips at the girth
    bpy.ops.import_scene.gltf(filepath=MS)
    so = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    for o in bpy.context.selected_objects: o.select_set(False)
    so.select_set(True); bpy.context.view_layer.objects.active = so
    if so.parent: bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")              # Meshy wraps the mesh in a node
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    sco = [v.co.copy() for v in so.data.vertices]
    if max(c.y for c in sco) - min(c.y for c in sco) > max(c.x for c in sco) - min(c.x for c in sco):
        for v in so.data.vertices: v.co = Vector((v.co.y, -v.co.x, v.co.z))
    sco = [v.co.copy() for v in so.data.vertices]; sx0, sx1 = min(c.x for c in sco), max(c.x for c in sco); sz0 = min(c.z for c in sco)
    lowpts = [c for c in sco if c.z < sz0 + (max(c.z for c in sco) - sz0) * .3]
    if sum(c.x for c in lowpts) / len(lowpts) > (sx0 + sx1) / 2:                       # the wheels are the low end: they go to -x
        for v in so.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
    sco = [v.co.copy() for v in so.data.vertices]; sz0 = min(c.z for c in sco)
    szh = max(c.z for c in sco) - sz0
    lowset = [c for c in sco if c.z < sz0 + szh * .5]; wy = max(abs(c.y) for c in lowset)
    wheel = [c for c in lowset if abs(c.y) > wy * .85]                                     # the wheels: widest of the low half
    print("WHEEL n", len(wheel), "wy", round(wy, 3), "dia", round(max(c.z for c in wheel) - min(c.z for c in wheel), 3), "H", round(szh, 3))
    wd = max(c.z for c in wheel) - min(c.z for c in wheel); wx = sum(c.x for c in wheel) / len(wheel)
    k = 2.4 / wd                                                                           # 28-inch wheels
    ym = (min(c.y for c in sco) + max(c.y for c in sco)) / 2                            # Meshy meshes are not centred sideways
    for v in so.data.vertices: v.co = Vector(((v.co.x - wx) * k, (v.co.y - ym) * k, (v.co.z - sz0) * k))
    rump = min(p.x for p in P if p.z > 2.5)                                             # the horse's rearmost point above the hocks
    shift = rump - 1.2; tip = max(v.co.x for v in so.data.vertices if v.co.z < 3.4)
    for v in so.data.vertices: v.co.x += shift
    # Meshy's shafts stop short: extend each shaft from its tip to the girth strap
    tips = [v.co for v in so.data.vertices if v.co.z < 3.4 and v.co.x > tip + shift - .25]
    for sgn in (1, -1):
        side = [c for c in tips if sgn * c.y > 0]
        if side:
            t = max(side, key=lambda c: c.x); tube([(t.x - .1, t.y, t.z), (gx + .4, sgn * 1.05, 3.55)], .065, mat("shaftx", RED, .6))
    print("SULKY k", round(k, 4), "wx", round(wx, 4), "sz0", round(sz0, 4), "shift", round(shift, 3), "tip", round(tip, 2))
    sc_ = [v.co for v in so.data.vertices]
    print("SULKY bbox x", round(min(c.x for c in sc_), 2), round(max(c.x for c in sc_), 2), "z", round(min(c.z for c in sc_), 2), round(max(c.z for c in sc_), 2))
    print("HORSE bbox x", round(min(p.x for p in P), 2), round(max(p.x for p in P), 2), "z", round(max(p.z for p in P), 2), "gx", gx, "mouth", tuple(round(v, 2) for v in mouth))
    bpy.context.view_layer.update()
    print("SO parent", so.parent.name if so.parent else None, "scale", tuple(round(x, 3) for x in so.scale), "loc", tuple(round(x, 2) for x in so.location), "users", so.data.users)
    wb = [so.matrix_world @ v.co for v in so.data.vertices]; print("SO world x", round(min(c.x for c in wb), 2), round(max(c.x for c in wb), 2), "z", round(min(c.z for c in wb), 2), round(max(c.z for c in wb), 2))
    print("OBJS", [(o.name, o.type, o.parent.name if o.parent else None) for o in bpy.data.objects if o.type in ("MESH", "EMPTY", "ARMATURE")][:12])
    for o in bpy.context.selected_objects: o.select_set(False)
    so.select_set(True); bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(__file__), "sulky_meshy_fit.glb"), export_format="GLB", use_selection=True); so.select_set(False)
    flat(so)
elif not MESHY: bpy.ops.import_scene.gltf(filepath=SULKY)
sobs = [o for o in bpy.data.objects if o not in before]
sroot = None if MS else next((o for o in sobs if o.parent is None), None)
if sroot: sroot.location.x = -5.6; sroot.scale = (.8, .8, .8)   # the Hunyuan driver came out oversized
for o in sobs:
    flat(o)
    for m in getattr(o.data, "materials", []) or []:
        if m and m.name.startswith("silk"): m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lin(RED)
bpy.context.view_layer.update()
drv = None if MS else next((o for o in sobs if o.name.startswith("driver")), None)
if drv:
    hands = max((drv.matrix_world @ v.co for v in drv.data.vertices if (drv.matrix_world @ v.co).z > 3.4), key=lambda p: p.x)
    for s in (1, -1): tube([(hands.x, s * .3, hands.z), (mouth.x - .45, s * .22, mouth.z + .15)], .025, TACK)

# ---- the set: daylight, raked dirt, a white rail, mown infield, hedge and a grandstand far behind
bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=20, size=1, location=(0, 10, 0)); g = bpy.context.object; g.scale = (160, 60, 1)
bpy.ops.object.transform_apply(scale=True)
for v in g.data.vertices: v.co.z += (random.random() - .5) * .12
ms = [mat(f"d{k}", c) for k, c in enumerate(["#b48a60", "#ab8159", "#bb9166", "#a67d56"])]
for m in ms: g.data.materials.append(m)
for p in g.data.polygons: p.material_index = random.randrange(4)
flat(g)
grass = [mat("g1", "#3f8a3a"), mat("g2", "#4a9a42")]
for k in range(14):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 34 + k * 9, .02)); o = bpy.context.object; o.scale = (400, 9, 1); o.data.materials.append(grass[k % 2])
rail = mat("rail", "#f2f4f6", .4)
tube([(-80, 32, 3.4), (80, 32, 3.4)], .3, rail)
for k in range(-10, 11):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(k * 8, 32, 1.7), scale=(.45, .45, 3.4)); bpy.context.object.data.materials.append(rail)
hedge = mat("hedge", "#2f6a34")
for k in range(-6, 7):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=5 + random.random() * 2, location=(k * 14 + random.random() * 4, 160, 3)); o = bpy.context.object; o.scale.z = .6; o.data.materials.append(hedge); flat(o)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 260, 9), scale=(300, 30, 18)); bpy.context.object.data.materials.append(mat("stand", "#2c3446"))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 244, 19), scale=(320, 40, 3)); bpy.context.object.data.materials.append(mat("roof", "#3b475e"))
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = lin("#cfe3f2"); bg.inputs[1].default_value = .9
bpy.ops.object.light_add(type="SUN"); s = bpy.context.object; s.data.energy = 3.2; s.data.color = (1, .95, .86); s.rotation_euler = (math.radians(52), 0, math.radians(-30)); s.data.angle = math.radians(4)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (-1.5, -34, 4.6); cam.data.lens = 50; cam.rotation_euler = (Vector((-1.5, 0, 3.6)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.dof.use_dof = True; cam.data.dof.focus_distance = 34; cam.data.dof.aperture_fstop = 2.2
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError: sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1490, 1054
sc.view_settings.view_transform = "AgX"
sc.render.filepath = OUT; bpy.ops.render.render(write_still=True); print("RENDERED")
