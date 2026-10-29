# Run inside Blender (MCP execute or blender -P). Builds the static low-poly racing horse in its own scene "Horse".
# Shape is traced from mockups/pixel/race_b.png: every point below is in sprite pixels (x right, y down) and
# converted to feet (1 px = K ft, buttock at x=0, ground at y=GROUND), facing +x like the sulky's shafts.
import bpy, math
from mathutils import Vector

K, X0, GROUND = 0.066, 112, 172
def P(x, y, d=0.0): return Vector(((x - X0) * K, d, (GROUND - y) * K))

sc = bpy.data.scenes.get("Horse") or bpy.data.scenes.new("Horse")
bpy.context.window.scene = sc
for o in list(sc.collection.all_objects): bpy.data.objects.remove(o)

def mat(name, hexc, rough=.85, painted=False):
    """painted: the base color comes from the mesh's "paint" color attribute (see paint() below)."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    rgb = tuple((int(hexc[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5))
    b.inputs["Base Color"].default_value = rgb + (1,); b.inputs["Roughness"].default_value = rough
    if painted:
        vc = next((n for n in m.node_tree.nodes if n.type == "VERTEX_COLOR"), None) or m.node_tree.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "paint"; m.node_tree.links.new(vc.outputs["Color"], b.inputs["Base Color"])
    m["rgb"] = rgb
    for k in ("Specular IOR Level", "Specular"):                      # no sheen: keep the coat a saturated sprite bay
        if k in b.inputs: b.inputs[k].default_value = 0
    m.diffuse_color = rgb + (1,); return m
COAT, POINTS, MANE, WHITE, HOOF = (mat("coat", "#6e2c10", painted=True), mat("points", "#17120f"), mat("mane", "#0f0d10"),
                                   mat("marking", "#f4f2ee"), mat("hoof", "#26221f"))
# the far legs are painted darker, as the sprites do, so the crossing pair under the belly reads apart
FAR = (mat("coat_far", "#3c1709", painted=True), mat("points_far", "#0b0908"), mat("marking_far", "#8f8a84"), mat("hoof_far", "#141210"))

root = bpy.data.objects.new("horse", None); sc.collection.objects.link(root)

def loft(name, secs, sides=6, mats=None):
    """secs: (point, half_height, half_width). Rings sit square to the path; ends are capped.
    mats: material index per section (faces take the index of their back ring)."""
    pts = [s[0] for s in secs]; verts, faces, fm = [], [], []
    for i, (p, h, w) in enumerate(secs):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        up = Vector((-t.z, 0, t.x))          # perpendicular to t in the side plane
        if up.z < 0 and abs(t.z) < .9: up = -up
        for k in range(sides):
            a = 2 * math.pi * k / sides + math.pi / sides
            verts.append(p + up * (h * math.sin(a)) + Vector((0, w * math.cos(a), 0)))
    for i in range(len(secs) - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            faces.append((a, b, b + sides, a + sides)); fm.append(mats[i] if mats else 0)
    faces.append(tuple(reversed(range(sides)))); fm.append(mats[0] if mats else 0)
    n = len(secs) - 1; faces.append(tuple(n * sides + k for k in range(sides))); fm.append(mats[-1] if mats else 0)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update(); me.validate()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.parent = root
    for p, m in zip(me.polygons, fm): p.material_index = m; p.use_smooth = False
    return ob

def px(sec, d=0.0):
    return [(P(x, y, d), h * K, w * K) for x, y, h, w in sec]

# body, neck and head: one tube from the buttock to the muzzle
body = loft("body", px([
    (112, 101, 9, 8), (114, 101, 13.5, 11), (117, 101, 16, 13), (122, 102, 17.5, 14.5), (128, 103, 18.5, 15),
    (135, 104, 19, 15), (142, 105, 19.5, 15), (149, 105, 20, 15), (156, 105, 20, 14.5), (163, 105, 19.5, 14),
    (170, 105, 18.5, 13.5), (176, 104, 17.5, 13), (182, 103, 16, 12), (191, 97, 15, 10), (199, 89, 13.5, 8), (206, 81, 11, 6.5),
    (212, 74, 8, 5.5), (218, 78, 9, 5.5), (226, 86, 8, 4.8), (234, 93, 6, 4.2), (240, 98, 4, 3.6)]), sides=10,
    mats=[0] * 21)
for m in (COAT, WHITE): body.data.materials.append(m)
# blaze: the small white strip down the face
for p in body.data.polygons:
    c = p.center
    if c.x > P(225, 0).x and c.x < P(236, 0).x and p.normal.x > .35 and p.normal.z > .35 and abs(c.y) < .12:
        p.material_index = 1

# legs: near side at -y (toward the camera), lateral pairs as a pacer moves them
LEGS = {  # (x, y, half-height, half-width) from the body down to the hoof; black from index BLACK on
    "fore_near": (-.42, 3, [(182, 112, 8, 6.5), (186, 126, 6.5, 5.5), (198, 133, 5, 4.2), (210, 140, 3.6, 3.4),
                            (219, 149, 2.8, 2.8), (226, 156, 3, 3), (232, 161, 2.4, 2.4), (237, 165, 3, 3.2)]),
    "fore_far": (.42, 3, [(178, 113, 8, 6.5), (178, 127, 6.5, 5.5), (173, 133, 5, 4.2), (168, 139, 3.6, 3.4),
                          (162, 145, 2.8, 2.8), (156, 151, 3, 3), (152, 156, 2.4, 2.4), (150, 162, 3, 3.2)]),
    "hind_near": (-.45, 3, [(132, 106, 12, 8), (138, 120, 8, 6), (144, 130, 5, 4.5), (149, 139, 3.8, 3.4),
                            (153, 148, 2.8, 2.8), (158, 157, 3, 3), (161, 161, 2.4, 2.4), (164, 166, 3, 3.2)]),
    "hind_far": (.45, 3, [(124, 105, 12, 8), (121, 120, 8, 6), (116, 130, 5, 4.5), (111, 139, 3.8, 3.4),
                          (113, 146, 2.8, 2.8), (117, 152, 3, 3), (121, 155, 2.4, 2.4), (126, 158, 3, 3.2)]),
}
for name, (d, black, sec) in LEGS.items():
    n = len(sec); mats = [0 if i < black else 1 for i in range(n - 1)]
    mats[-2] = 2; mats[-1] = 3                       # white coronet band, then the hoof
    o = loft(name, px(sec, d), sides=6, mats=mats)
    for m in (FAR if d > 0 else (COAT, POINTS, WHITE, HOOF)): o.data.materials.append(m)

# ears: two small pyramids just behind the poll
for d in (-.14, .14):
    base, tip = P(212, 69, d), P(213, 59, d * 1.2)
    me = bpy.data.meshes.new("ear"); s = .09
    vs = [base + Vector((s, 0, 0)), base + Vector((-s, -s * .6, 0)), base + Vector((-s, s * .6, 0)), tip]
    me.from_pydata([tuple(v) for v in vs], [], [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]); me.update()
    o = bpy.data.objects.new("ear", me); sc.collection.objects.link(o); o.parent = root; me.materials.append(COAT)

# mane: a jagged fin of flat spikes along the crest, leaning back from the poll to the withers
crest = [(209, 68), (204, 74), (199, 79), (193, 83), (186, 85), (178, 86), (170, 87), (162, 88)]
vs, fs = [], []
for i in range(len(crest) - 1):
    (x0, y0), (x1, y1) = crest[i], crest[i + 1]
    for d in (-.13, .13):
        a, b = P(x0, y0 + 2, d), P(x1, y1 + 2, d)
        tip = P((x0 + x1) / 2 - 8, (y0 + y1) / 2 - 7 + (i % 2) * 3, d * 1.6)
        j = len(vs); vs += [a, b, tip]; fs.append((j, j + 1, j + 2))
me = bpy.data.meshes.new("mane"); me.from_pydata([tuple(v) for v in vs], [], fs); me.update()
o = bpy.data.objects.new("mane", me); sc.collection.objects.link(o); o.parent = root; me.materials.append(MANE)
o.modifiers.new("solid", "SOLIDIFY").thickness = .05

# tail: a short dark tapering tube off the dock, streaming back
tail = loft("tail", px([(114, 96, 3.5, 3), (105, 101, 5, 4), (96, 108, 6, 4.5), (88, 116, 5, 3.5), (82, 124, 2, 2)]),
            sides=5)
tail.data.materials.append(MANE)

# painted coat: muscle regions traced from race_b as side-view outlines (sprite px). The mesh is cut along every
# outline edge and triangulated, so tone boundaries follow anatomy instead of the tube's grid, then each face takes
# its region's step of the sprite's own coat ramp. Lights still shade on top. Later regions win.
import bmesh
RAMP = ("#3a1809", "#55230d", "#6c2d10", "#7f3615", "#9f4921", "#bb5d2f")   # race_b's coat quintiles + top 4%, x1.18
REGIONS = [
    (4, [(108, 98), (114, 88), (126, 86), (136, 94), (134, 106), (124, 112), (112, 110)]),      # haunch
    (5, [(114, 96), (120, 90), (128, 92), (126, 102), (117, 104)]),                             # hip point
    (4, [(166, 90), (178, 92), (192, 103), (193, 115), (185, 119), (175, 108)]),                 # shoulder blade
    (5, [(178, 99), (187, 104), (189, 112), (182, 112)]),                                      # point of shoulder
    (4, [(185, 119), (194, 121), (201, 131), (195, 134), (186, 127)]),                         # forearm
    (4, [(184, 90), (198, 80), (208, 70), (213, 73), (204, 86), (191, 96)]),                   # neck crest
    (4, [(219, 77), (228, 82), (231, 90), (222, 90)]),                                         # cheek
    (4, [(134, 117), (143, 123), (147, 133), (140, 134), (134, 125)]),                          # gaskin
    (1, [(140, 101), (151, 105), (151, 118), (139, 116)]),                                     # flank
    (1, [(108, 112), (124, 112), (131, 126), (127, 140), (114, 136), (106, 122)]),              # back of the thigh
    (1, [(130, 108), (138, 116), (141, 128), (134, 131)]),                                     # stifle crease
    (1, [(164, 107), (175, 110), (179, 124), (169, 129), (161, 119)]),                          # behind the elbow
    (1, [(138, 118), (180, 118), (180, 130), (138, 130)]),                                     # belly
    (0, [(146, 123), (174, 123), (174, 130), (146, 130)]),                                     # belly, deepest
    (1, [(191, 104), (202, 96), (212, 91), (217, 98), (205, 104), (196, 111)]),                 # throat, under the neck
]
def inside(x, y, poly):
    c = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0): c = not c
    return c
def sp(co): return co.x / K + X0, GROUND - co.z / K                         # mesh point -> sprite px
def cut(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    for _, poly in REGIONS:
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            lo, hi = (min(x0, x1) - 3, min(y0, y1) - 3), (max(x0, x1) + 3, max(y0, y1) + 3)
            fs = [f for f in bm.faces if all(lo[i] <= sp(f.calc_center_median())[i] <= hi[i] for i in (0, 1))]
            if not fs: continue
            d = P(x1, y1) - P(x0, y0)
            geom = list({e for f in fs for e in f.edges}) + fs + list({v for f in fs for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=P(x0, y0), plane_no=Vector((-d.z, 0, d.x)).normalized())
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons: p.use_smooth = False
def tri(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons: p.use_smooth = False
def lin(h): return tuple((int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5))
def paint(o, far):
    ca = o.data.color_attributes.get("paint") or o.data.color_attributes.new("paint", "FLOAT_COLOR", "CORNER")
    for p in o.data.polygons:
        x, y = sp(p.center); t = 2
        for tone, poly in REGIONS:
            if inside(x, y, poly): t = tone
        c = tuple(v * .7 for v in lin(RAMP[t]))                              # the sun adds light back: match race_b's on-screen bay
        if far: c = tuple(v * .3 for v in c)                                  # far legs sit in shadow
        for li in p.loop_indices: ca.data[li].color = c + (1,)
for o in root.children:
    if any(m and m.name in ("coat", "coat_far") for m in o.data.materials):
        if o.name in LEGS: tri(o)                 # legs keep loft vertex order so stride.py can pose them as shape keys;
        else: cut(o)                              # their paint is laid in this pose and rides along with the faces
        paint(o, o.name.endswith("_far"))

print("faces", sum(len(o.data.polygons) for o in root.children))
