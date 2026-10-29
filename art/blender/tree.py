# blender -b -P tree.py -- out.blend preview.png
# A low-poly infield tree: tapered trunk, a few branches, faceted foliage clumps, flat-shaded.
import bpy, math, random, sys
from mathutils import Vector

out, png = sys.argv[sys.argv.index("--") + 1:][:2]
random.seed(4)
bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    return m


bark, leaf, leaf2 = mat("bark", (0.16, 0.09, 0.05)), mat("leaf", (0.09, 0.28, 0.08)), mat("leaf_light", (0.18, 0.42, 0.10))


def limb(a, b, r0, r1):
    """A tapered 6-sided cone from a to b."""
    d = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=r0, radius2=r1, depth=d.length, location=a + d / 2)
    o = bpy.context.object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.data.materials.append(bark)
    return o


parts = [limb(Vector((0, 0, 0)), Vector((0, 0, 3.2)), 0.35, 0.18)]
tips = []
for i in range(5):
    ang = i * 2 * math.pi / 5 + random.uniform(-.3, .3)
    a = Vector((0, 0, random.uniform(2.0, 3.0)))
    b = a + Vector((math.cos(ang) * 1.4, math.sin(ang) * 1.4, random.uniform(1.0, 1.8)))
    parts.append(limb(a, b, 0.14, 0.05))
    tips.append(b)
tips.append(Vector((0, 0, 3.6)))
for t in tips:
    for _ in range(2):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=random.uniform(0.9, 1.3),
                                              location=t + Vector([random.uniform(-.5, .5) for _ in range(3)]))
        o = bpy.context.object
        o.scale = (1, 1, random.uniform(.75, .95))
        o.data.materials.append(random.choice([leaf, leaf2]))
        parts.append(o)
bpy.ops.object.select_all(action="DESELECT")
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
tree = bpy.context.object
tree.name = "Tree"
bpy.ops.object.shade_flat()

# ground, sun and a camera for the preview
bpy.ops.mesh.primitive_plane_add(size=14)
bpy.context.object.data.materials.append(mat("grass", (0.12, 0.2, 0.08)))
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(30)))
bpy.context.object.data.energy = 3
bpy.ops.object.camera_add(location=(9, -9, 5.5))
cam = bpy.context.object
cam.rotation_mode = "QUATERNION"
cam.rotation_quaternion = (Vector((0, 0, 2.6)) - cam.location).to_track_quat("-Z", "Y")
sc = bpy.context.scene
sc.camera = cam
sc.world = bpy.data.worlds.new("sky")
sc.world.color = (0.35, 0.45, 0.6)
sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = 640, 640
sc.render.filepath = png
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("TREE", len(tree.data.polygons), "faces")
