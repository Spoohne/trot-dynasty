# blender -b -P lowpoly.py -- in.glb out.glb preview.png faces
# Import the Hunyuan mesh, stand it on the ground facing +X, decimate to a faceted low-poly, paint a bay coat by
# region (black lower legs, darker face), flat-shade, export, and render a side and three-quarter preview.
import bpy, bmesh, sys, math
from mathutils import Vector
a = sys.argv[sys.argv.index("--") + 1:]
src, dst, png, faces = a[0], a[1], a[2], int(a[3])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.context.view_layer.objects.active = obs[0]
for o in obs: o.select_set(True)
if len(obs) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# keep only the biggest connected piece (drops floaters)
bpy.ops.object.mode_set(mode="EDIT"); bm = bmesh.from_edit_mesh(ob.data)
islands, seen = [], set()
for v in bm.verts:
    if v.index in seen: continue
    stack, isl = [v], []
    seen.add(v.index)
    while stack:
        x = stack.pop(); isl.append(x)
        for e in x.link_edges:
            w = e.other_vert(x)
            if w.index not in seen: seen.add(w.index); stack.append(w)
    islands.append(isl)
islands.sort(key=len)
bmesh.ops.delete(bm, geom=[v for isl in islands[:-1] for v in isl], context="VERTS")
bmesh.update_edit_mesh(ob.data); bpy.ops.object.mode_set(mode="OBJECT")
# size: 8.6 ft nose to tail-root long; ground at z=0; longest horizontal axis becomes X
xs = [v.co for v in ob.data.vertices]
ext = [max(c[i] for c in xs) - min(c[i] for c in xs) for i in range(3)]
up = 1 if ext[1] > ext[2] * .9 and False else 2       # glTF import already converts Y-up to Blender Z-up
long = 0 if ext[0] >= ext[1] else 1
if long == 1: ob.rotation_euler.z = math.pi / 2; bpy.ops.object.transform_apply(rotation=True)
xs = [v.co for v in ob.data.vertices]
lo = Vector([min(c[i] for c in xs) for i in range(3)]); hi = Vector([max(c[i] for c in xs) for i in range(3)])
s = 9.0 / (hi.x - lo.x)
for v in ob.data.vertices: v.co = Vector(((v.co.x - (lo.x + hi.x) / 2) * s, (v.co.y - (lo.y + hi.y) / 2) * s, (v.co.z - lo.z) * s))
# which end is the head: the higher end (head and neck rise above the croup)
xs = [v.co for v in ob.data.vertices]
front = max((c for c in xs if c.x > 2.5), key=lambda c: c.z, default=Vector()).z
back = max((c for c in xs if c.x < -2.5), key=lambda c: c.z, default=Vector()).z
if back > front:
    for v in ob.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
H = max(c.z for c in (v.co for v in ob.data.vertices))
# clean the scan-like surface (voxel remesh + a light smooth), then decimate to the faceted look
r = ob.modifiers.new("rem", "REMESH"); r.mode = "VOXEL"; r.voxel_size = .07; bpy.ops.object.modifier_apply(modifier="rem")
sm = ob.modifiers.new("sm", "SMOOTH"); sm.iterations = 6; sm.factor = .6; bpy.ops.object.modifier_apply(modifier="sm")
bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode="OBJECT")
m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = min(1, faces / len(ob.data.polygons)); m.use_symmetry = True; m.symmetry_axis = "Y"
bpy.ops.object.modifier_apply(modifier="dec")
for p in ob.data.polygons: p.use_smooth = False
# paint by region: per-face color attribute
col = ob.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
import random; random.seed(3)
def srgb(h): return [((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (1, 3, 5)] + [1]
coat, dark, face = srgb("#5a3220"), srgb("#141012"), srgb("#3d2216")
for p in ob.data.polygons:
    c = p.center
    n = p.normal
    mane = 1.6 < c.x < 3.9 and c.z > H * .62 and n.z > .25 and n.x < .3
    k = dark if c.z < H * .33 or c.x < -3.7 or mane else (face if c.x > 3.4 and c.z > H * .55 else coat)
    j = 1 + (random.random() - .5) * .12                  # a touch of per-facet variation
    for li in p.loop_indices: col.data[li].color = [min(1, k[0] * j), min(1, k[1] * j), min(1, k[2] * j), 1]
mat = bpy.data.materials.new("horse"); mat.use_nodes = True
nt = mat.node_tree; bsdf = nt.nodes["Principled BSDF"]; attr = nt.nodes.new("ShaderNodeVertexColor"); attr.layer_name = "Col"
nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"]); bsdf.inputs["Roughness"].default_value = .8
ob.data.materials.clear(); ob.data.materials.append(mat)
print("faces", len(ob.data.polygons), "height", round(H, 2))
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", use_selection=False)
# preview renders
sc = bpy.context.scene; sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"
sc.display.shading.color_type = "VERTEX"; sc.render.resolution_x, sc.render.resolution_y = 900, 600
sc.world = bpy.data.worlds.new("w"); sc.world.color = (1, 1, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 12.5
for name, loc in (("side", (0, -30, 3.9)), ("q", (14, -22, 9))):
    cam.location = loc; d = Vector((0, 0, 3.9)) - Vector(loc); cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = png.replace(".png", f"_{name}.png"); bpy.ops.render.render(write_still=True)
