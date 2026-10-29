# blender -b -P inspect_any.py -- in.(fbx|glb) out_prefix
# What a model holds: objects, tri counts, armature and actions, materials and images, bounds; then three rendered
# views (side, three-quarter, front) with its own textures, on a plain background.
import bpy, sys, math
from mathutils import Vector
SRC, OUT = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
(bpy.ops.import_scene.fbx if SRC.lower().endswith(".fbx") else bpy.ops.import_scene.gltf)(filepath=SRC)
sc = bpy.context.scene
for o in sc.objects:
    s = f"OBJ {o.name} {o.type}"
    if o.type == "MESH":
        s += f" tris~{sum(len(p.vertices) - 2 for p in o.data.polygons)} verts={len(o.data.vertices)} groups={len(o.vertex_groups)} mats={[m.name if m else None for m in o.data.materials]}"
        s += f" shaded_smooth={sum(p.use_smooth for p in o.data.polygons)}/{len(o.data.polygons)} uv={len(o.data.uv_layers)} parent={o.parent.name if o.parent else None}"
    if o.type == "ARMATURE":
        s += f" bones={len(o.data.bones)}"
        a = o.animation_data.action if o.animation_data else None
        s += f" action={a.name if a else None} range={tuple(a.frame_range) if a else None}"
    print(s)
print("ACTIONS", [(a.name, tuple(a.frame_range)) for a in bpy.data.actions])
print("IMAGES", [(i.name, tuple(i.size), i.filepath[-60:]) for i in bpy.data.images])
for m in bpy.data.materials:
    if m.use_nodes: print("MAT", m.name, [(n.type, getattr(getattr(n, "image", None), "name", None)) for n in m.node_tree.nodes if n.type in ("TEX_IMAGE", "BSDF_PRINCIPLED")])
meshes = [o for o in sc.objects if o.type == "MESH"]
P = [o.matrix_world @ Vector(b) for o in meshes for b in o.bound_box]
lo = Vector([min(p[i] for p in P) for i in range(3)]); hi = Vector([max(p[i] for p in P) for i in range(3)])
print("BOUNDS", tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))
c = (lo + hi) / 2; size = max(hi - lo)
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "TEXTURE"
sc.render.resolution_x, sc.render.resolution_y = 700, 500; sc.world = bpy.data.worlds.new("w"); sc.world.color = (.75, .75, .78)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = size * 1.15
long_x = (hi.x - lo.x) >= (hi.y - lo.y)
side = Vector((0, -1, 0)) if long_x else Vector((1, 0, 0)); fwd = Vector((1, 0, 0)) if long_x else Vector((0, 1, 0))
for name, d in (("side", side), ("q", (side + fwd * .6 + Vector((0, 0, .35))).normalized()), ("front", fwd)):
    cam.location = c + d * size * 3; cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = f"{OUT}_{name}.png"; bpy.ops.render.render(write_still=True)
