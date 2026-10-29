# blender -b -P prep_meshy.py -- in.fbx out.glb faces
# The Meshy rig (one fused mesh: horse mid-trot, sulky, driver, lines) into the faceted look: decimate, flat-shade,
# paint by region (coat, black points, red silks, dark wheels), head toward +x in feet, hooves on the ground.
import bpy, sys, math, random
from mathutils import Vector
SRC, OUT, FACES = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SRC)
sc = bpy.context.scene
ob = next(o for o in sc.objects if o.type == "MESH")
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# orientation: long axis to x; the head end is the one that is NOT where the wheels are (the two big discs sit
# low and wide at the back): compare lowest-z spread at each end
co = [v.co.copy() for v in ob.data.vertices]
lo = Vector([min(c[i] for c in co) for i in range(3)]); hi = Vector([max(c[i] for c in co) for i in range(3)])
if hi.y - lo.y > hi.x - lo.x:
    for v in ob.data.vertices: v.co = Vector((v.co.y, -v.co.x, v.co.z))
    co = [v.co.copy() for v in ob.data.vertices]; lo = Vector([min(c[i] for c in co) for i in range(3)]); hi = Vector([max(c[i] for c in co) for i in range(3)])
mid = (lo.x + hi.x) / 2
wide = lambda part: max(abs(c.y) for c in part)
back_w = wide([c for c in co if c.x > hi.x - (hi.x - lo.x) * .2]); front_w = wide([c for c in co if c.x < lo.x + (hi.x - lo.x) * .2])
if back_w > front_w:                                                                   # the wheels (widest, low) are at +x: flip so the head faces +x
    for v in ob.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
co = [v.co.copy() for v in ob.data.vertices]; lo = Vector([min(c[i] for c in co) for i in range(3)]); hi = Vector([max(c[i] for c in co) for i in range(3)])
s = 6.3 / (hi.z - lo.z)                                                                # whole rig 6.3 ft tall (driver's helmet to hoof)
for v in ob.data.vertices: v.co = Vector(((v.co.x - mid) * s, v.co.y * s, (v.co.z - lo.z) * s))
# facets
md = ob.modifiers.new("dec", "DECIMATE"); md.ratio = int(FACES) / len(ob.data.polygons); bpy.ops.object.modifier_apply(modifier="dec")
for p in ob.data.polygons: p.use_smooth = False
# paint by region
co = [v.co for v in ob.data.vertices]; H = max(c.z for c in co); X0, X1 = min(c.x for c in co), max(c.x for c in co)
xs = X0 + (X1 - X0) * .42                                                              # the sulky and driver live behind this
random.seed(7)
ca = ob.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
def lin(h): return [(int(h[i:i + 2], 16) / 255) ** 2.2 for i in (1, 3, 5)]
COAT, DARK, RED, WHITE, WHEEL, SKIN = lin("#7a4a2c"), lin("#17120f"), lin("#d42a2a"), lin("#e9ecf0"), lin("#1a1c22"), lin("#d6a985")
for p in ob.data.polygons:
    c = p.center
    if c.x > xs:                                                                       # the horse
        k = DARK if c.z < .25 * H else COAT
    else:                                                                              # sulky and driver
        if c.z < .5 * H: k = WHEEL
        elif c.z > .86 * H: k = RED                                                    # helmet
        elif c.x < xs - (xs - X0) * .35: k = RED                                       # torso
        else: k = WHITE                                                                # legs out along the shafts
    j = 1 + (random.random() - .5) * .16
    for li in p.loop_indices: ca.data[li].color = (k[0] * j, k[1] * j, k[2] * j, 1)
m = bpy.data.materials.new("coat"); m.use_nodes = True; nt = m.node_tree
vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
nt.links.new(vc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"]); nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .75
ob.data.materials.clear(); ob.data.materials.append(m)
print("FACES", len(ob.data.polygons), "H", round(H, 2), "X", round(X0, 2), round(X1, 2), "split", round(xs, 2))
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB")
