# Shared Blender helpers for the low-poly pipeline: exec'd by rig_horse.py (needs bpy, bmesh, math, random, Vector).
import bpy, bmesh, math, random
from mathutils import Vector

def flat(ob):
    for p in ob.data.polygons: p.use_smooth = False

def prep(path, length, faces):
    """Import a Hunyuan GLB, keep the largest piece, stand it on z=0 with its long axis on x, scaled to `length`,
    then voxel-remesh, smooth and decimate to `faces` flat triangles."""
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
    md = ob.modifiers.new("rem", "REMESH"); md.mode = "VOXEL"; md.voxel_size = length / 130; bpy.ops.object.modifier_apply(modifier="rem")
    md = ob.modifiers.new("sm", "SMOOTH"); md.iterations = 5; md.factor = .6; bpy.ops.object.modifier_apply(modifier="sm")
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT"); bpy.ops.mesh.quads_convert_to_tris(); bpy.ops.object.mode_set(mode="OBJECT")
    md = ob.modifiers.new("dec", "DECIMATE"); md.ratio = min(1, faces / len(ob.data.polygons)); bpy.ops.object.modifier_apply(modifier="dec")
    flat(ob); return ob

def paint_horse(horse, seed=3):
    """Bay coat by region into a 'Col' corner color attribute: black lower legs, mane and tail, darker face,
    and small per-facet shifts so the facets read. Head must face +x."""
    random.seed(seed)
    H = max(v.co.z for v in horse.data.vertices)
    ca = horse.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
    for p in horse.data.polygons:
        c, n = p.center, p.normal
        mane = 1.5 < c.x < 4.2 and c.z > H * .66 and n.z > .2 and n.x < .35
        k = (.012, .009, .009) if (c.z < H * .3 or c.x < -3.6 or mane) else ((.05, .022, .012) if c.x > 3.6 and c.z > H * .55 else (.11, .045, .022))
        j = 1 + (random.random() - .5) * .18
        for li in p.loop_indices: ca.data[li].color = (k[0] * j, k[1] * j, k[2] * j, 1)
    m = bpy.data.materials.new("coat"); m.use_nodes = True; nt = m.node_tree
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"
    nt.links.new(vc.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"]); nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = .75
    horse.data.materials.clear(); horse.data.materials.append(m)
