# blender -b -P scene.py -- horse.glb driver.glb numdir out.png
# Look-dev still: five low-poly rigs (Hunyuan horse + driver, primitive sulky) trotting on a faceted night track.
import bpy, bmesh, sys, math, random
from mathutils import Vector
A = sys.argv[sys.argv.index("--") + 1:]
HORSE, DRIVER, NUMDIR, OUT = A
random.seed(5)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def lin(h): return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5)) + (1,)
def mat(name, col, emit=0, rough=.85):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(col); b.inputs["Roughness"].default_value = rough
    if emit: b.inputs["Emission Color"].default_value = lin(col); b.inputs["Emission Strength"].default_value = emit
    return m
def flat(ob):
    for p in ob.data.polygons: p.use_smooth = False

def prep(path, length, faces):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    obs = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in bpy.context.selected_objects: o.select_set(False)
    for o in obs: o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    for o in [o for o in bpy.data.objects if o not in before and o != ob]: bpy.data.objects.remove(o)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.mode_set(mode="EDIT"); bm = bmesh.from_edit_mesh(ob.data)
    seen, isl_all = set(), []
    for v in bm.verts:
        if v in seen: continue
        st, isl = [v], []; seen.add(v)
        while st:
            x = st.pop(); isl.append(x)
            for e in x.link_edges:
                w = e.other_vert(x)
                if w not in seen: seen.add(w); st.append(w)
        isl_all.append(isl)
    isl_all.sort(key=len)
    bmesh.ops.delete(bm, geom=[v for i in isl_all[:-1] for v in i], context="VERTS")
    bmesh.update_edit_mesh(ob.data); bpy.ops.object.mode_set(mode="OBJECT")
    co = [v.co for v in ob.data.vertices]
    if (max(c.y for c in co) - min(c.y for c in co)) > (max(c.x for c in co) - min(c.x for c in co)):
        ob.rotation_euler.z = math.pi / 2; bpy.ops.object.transform_apply(rotation=True)
    co = [v.co.copy() for v in ob.data.vertices]
    lo = Vector([min(c[i] for c in co) for i in range(3)]); hi = Vector([max(c[i] for c in co) for i in range(3)])
    s = length / (hi.x - lo.x)
    for v in ob.data.vertices: v.co = Vector(((v.co.x - (lo.x + hi.x) / 2) * s, (v.co.y - (lo.y + hi.y) / 2) * s, (v.co.z - lo.z) * s))
    for name, m in (("rem", None), ("sm", None), ("dec", None)):
        if name == "rem": md = ob.modifiers.new(name, "REMESH"); md.mode = "VOXEL"; md.voxel_size = length / 130
        elif name == "sm": md = ob.modifiers.new(name, "SMOOTH"); md.iterations = 5; md.factor = .6
        else:
            md = ob.modifiers.new(name, "DECIMATE"); md.ratio = 1
        bpy.ops.object.modifier_apply(modifier=name) if name != "dec" else None
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode="OBJECT")
    md = ob.modifiers["dec"]; md.ratio = min(1, faces / len(ob.data.polygons)); bpy.ops.object.modifier_apply(modifier="dec")
    flat(ob); return ob

# ---- horse: head toward +x (the end whose top is higher), painted by region with per-facet variation
horse = prep(HORSE, 10.0, 2600)
co = [v.co for v in horse.data.vertices]
if max((c.z for c in co if c.x < -2), default=0) > max((c.z for c in co if c.x > 2), default=0):
    for v in horse.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
H = max(v.co.z for v in horse.data.vertices)
nose = max(horse.data.vertices, key=lambda v: v.co.x).co.copy()
ca = horse.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
for p in horse.data.polygons:
    c, n = p.center, p.normal
    mane = 1.5 < c.x < 4.2 and c.z > H * .66 and n.z > .2 and n.x < .35
    k = (.012, .009, .009) if (c.z < H * .3 or c.x < -3.6 or mane) else ((.05, .022, .012) if c.x > 3.6 and c.z > H * .55 else (.11, .045, .022))
    j = 1 + (random.random() - .5) * .18
    for li in p.loop_indices: ca.data[li].color = (k[0] * j, k[1] * j, k[2] * j, 1)
def coat_mat(tint):
    m = bpy.data.materials.new("coat"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"; mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1; mix.inputs[7].default_value = tint
    nt.links.new(vc.outputs["Color"], mix.inputs[6]); nt.links.new(mix.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = .75
    return m

# ---- driver: feet toward +x (the far end from the head), seated on the seat; material slots silk / white / boots / skin
drv = prep(DRIVER, 4.6, 1800)
co = [v.co for v in drv.data.vertices]; top = max(co, key=lambda c: c.z)
if top.x > 0:
    for v in drv.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
DH = max(v.co.z for v in drv.data.vertices); DX = max(v.co.x for v in drv.data.vertices)
slots = ["silk", "white", "boot", "skin"]
for s in slots: drv.data.materials.append(mat(s, "#ffffff"))
for p in drv.data.polygons:
    c = p.center
    p.material_index = 2 if c.x > DX - .75 else (1 if c.z < DH * .42 and c.x > -1.2 else 0)

# ---- one rig, in lane z, nose at x, silks color
def dup(ob):
    d = ob.copy(); d.data = ob.data.copy(); sc.collection.objects.link(d); return d
def tube(p0, p1, r, m):
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=r, depth=d.length, location=(p0 + p1) / 2)
    o = bpy.context.object; o.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m); flat(o); return o
def rig(x, y, num, silk, tint):
    h = dup(horse); h.location = (x - nose.x, y, 0); h.data.materials.clear(); h.data.materials.append(coat_mat(tint))
    silkM = mat(f"silk{num}", silk, rough=.6)
    # saddle cloth with the number, both sides
    img = bpy.data.images.load(f"{NUMDIR}/num{num}.png"); nm = bpy.data.materials.new(f"num{num}"); nm.use_nodes = True
    tx = nm.node_tree.nodes.new("ShaderNodeTexImage"); tx.image = img; nb = nm.node_tree.nodes["Principled BSDF"]; nm.node_tree.links.new(tx.outputs["Color"], nb.inputs["Base Color"])
    bx = x - nose.x
    for s in (1, -1):
        bpy.ops.mesh.primitive_plane_add(size=1.5, location=(bx + .3, y + s * 1.12, H * .6), rotation=(math.pi / 2, 0, 0 if s < 0 else math.pi))
        bpy.context.object.data.materials.append(nm)
    tube((bx + .9, y - 1.15, H * .6 + 1.05), (bx + .9, y + 1.15, H * .6 + 1.05), .06, mat("tack", "#111114"))
    # sulky
    ax = bx - 7.2; frame = silkM; dark = mat("wheel", "#14161b", rough=.5)
    for s in (1, -1):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.15, depth=.1, location=(ax, y + s * 2.05, 1.15), rotation=(math.pi / 2, 0, random.random()))
        bpy.context.object.data.materials.append(dark); flat(bpy.context.object)
        bpy.ops.mesh.primitive_torus_add(major_radius=1.12, minor_radius=.07, major_segments=16, minor_segments=4, location=(ax, y + s * 2.11, 1.15), rotation=(math.pi / 2, 0, 0))
        bpy.context.object.data.materials.append(frame)
        tube((ax, y + s * 2.0, 1.15), (ax + 1.0, y + s * 1.6, 2.9), .07, frame)
        tube((ax + 1.0, y + s * 1.6, 2.9), (bx + 2.6, y + s * 1.15, H * .55), .07, frame)
    tube((ax, y - 2.05, 1.15), (ax, y + 2.05, 1.15), .07, frame)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ax - .3, y, 2.45), scale=(1.0, 1.1, .18)); bpy.context.object.data.materials.append(mat("seat", "#1c1e25"))
    d = dup(drv); d.location = (ax - .9 + 2.3, y, 2.35 - .15)
    d.data.materials[0] = silkM; d.data.materials[1] = mat("white", "#e9ecf0"); d.data.materials[2] = mat("boot", "#0d0d0f"); d.data.materials[3] = mat("skin", "#d6a985")
    for s in (1, -1): tube((ax + 1.6, y + s * .45, 4.3), (x - .3, y + s * .25, nose.z - .2), .025, mat("line", "#0d0d0f"))

SILK = ["#7b2bbf", "#f2c418", "#1e9e3a", "#d8262a", "#1e50ff"]
TINT = [(1, 1, 1, 1), (1.2, 1.1, 1.05, 1), (.7, .62, .6, 1), (1.35, 1.15, 1.0, 1), (.85, .8, .8, 1)]
for i in range(5): rig(44 - i * 22, -2 if i % 2 else 2.5, i + 1, SILK[i], TINT[i])
horse.hide_render = drv.hide_render = True                                   # the originals at the origin are only templates

# ---- the world: faceted dirt, grass infield, rail, light towers, grandstand, tote board
def facets(w, d, nx, ny, loc, cols, jit):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=nx, y_subdivisions=ny, size=1, location=loc); g = bpy.context.object; g.scale = (w, d, 1)
    bpy.ops.object.transform_apply(scale=True)
    for v in g.data.vertices: v.co.z += (random.random() - .5) * jit
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode="OBJECT")
    ms = [mat("g", c) for c in cols]
    for m in ms: g.data.materials.append(m)
    for p in g.data.polygons: p.material_index = random.randrange(len(ms))
    flat(g); return g
facets(600, 140, 120, 30, (0, -40, 0), ["#5e3d25", "#66432a", "#563822", "#6d482d", "#5a3b24"], .35)
facets(1400, 600, 90, 40, (0, 330, -.05), ["#2c6a2a", "#33752f", "#285f27", "#387c33"], .8)
rail = mat("rail", "#e8ecf2", rough=.4)
tube((-300, 16, 3.2), (300, 16, 3.2), .17, rail)
for k in range(76): tube((-300 + k * 8, 16, 0), (-300 + k * 8, 16, 3.2), .12, rail)
lamp = mat("lamp", "#fff6dd", emit=40)
for tx in (-260, -60, 140, 330):
    tube((tx, 420, 0), (tx, 420, 85), .9, mat("pole", "#5a637a"))
    bpy.ops.mesh.primitive_cube_add(size=1, location=(tx, 419, 88), scale=(12, 1, 7)); bpy.context.object.data.materials.append(lamp)
    bpy.ops.object.light_add(type="SPOT", location=(tx, 300, 86)); L = bpy.context.object
    L.data.energy = 2.2e6; L.data.spot_size = math.radians(70); L.data.color = (1, .95, .85); L.data.shadow_soft_size = 3
    L.rotation_euler = (Vector((tx * .3, -10, 0)) - L.location).to_track_quat("-Z", "Y").to_euler()
stand = mat("stand", "#20263a"); win = mat("win", "#ffd9a0", emit=1.2)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-170, 380, 18), scale=(260, 50, 36)); bpy.context.object.data.materials.append(stand)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-170, 354.5, 27), scale=(250, 1, 3)); bpy.context.object.data.materials.append(win)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-170, 354.5, 13), scale=(250, 1, 14)); bpy.context.object.data.materials.append(mat("crowd", "#3b3f55", emit=.6))
bpy.ops.mesh.primitive_cube_add(size=1, location=(-170, 375, 38), scale=(280, 70, 2)); bpy.context.object.data.materials.append(mat("roof", "#39425f"))
bpy.ops.mesh.primitive_cube_add(size=1, location=(95, 260, 16), scale=(46, 2, 22)); bpy.context.object.data.materials.append(mat("tote", "#111522"))
bpy.ops.mesh.primitive_cube_add(size=1, location=(95, 258.9, 16), scale=(40, .5, 17)); bpy.context.object.data.materials.append(mat("led", "#ffb030", emit=3))

# ---- night: navy sky, a cool moon fill, warm key from the near-side lights
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = lin("#0d1a4a"); w.node_tree.nodes["Background"].inputs[1].default_value = .6
bpy.ops.object.light_add(type="SUN", location=(0, 0, 50)); s = bpy.context.object; s.data.energy = 1.4; s.data.color = (1, .93, .82); s.rotation_euler = (math.radians(50), 0, math.radians(-35))
bpy.ops.object.light_add(type="SUN", location=(0, 0, 50)); s = bpy.context.object; s.data.energy = .35; s.data.color = (.6, .7, 1); s.rotation_euler = (math.radians(-40), 0, math.radians(160))
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (-2, -78, 10); cam.data.lens = 40
cam.rotation_euler = (Vector((-2, 0, 6.5)) - cam.location).to_track_quat("-Z", "Y").to_euler()
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError: sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [l.name for l in []] else "None"
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("RENDERED", OUT)
