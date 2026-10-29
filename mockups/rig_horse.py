# blender -b -P rig_horse.py -- horse.glb out.glb strip.png
# Fit a quadruped skeleton to the standing Hunyuan horse, skin it with automatic weights, keyframe one trot cycle
# (24 frames = one stride) and export a GLB with the animation. Renders a side-view strip of the cycle to check.
import bpy, sys, math, random
from mathutils import Vector
sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
A = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, STRIP = A
exec(open(__file__.replace("rig_horse.py", "lowpoly_lib.py")).read())          # prep(), paint_horse()

bpy.ops.wm.read_factory_settings(use_empty=True)
horse = prep(SRC, 10.0, 3000)
co = [v.co for v in horse.data.vertices]
if max((c.z for c in co if c.x < -2), default=0) > max((c.z for c in co if c.x > 2), default=0):
    for v in horse.data.vertices: v.co.x, v.co.y = -v.co.x, -v.co.y
co = [v.co.copy() for v in horse.data.vertices]
W = max(c.z for c in co if -1.5 < c.x < 0)                                    # height at the back
nose = max(co, key=lambda c: c.x)
low = [c for c in co if c.z < W * .22]
mx = sorted(c.x for c in low)[len(low) // 2]
def foot(front, left):
    g = [c for c in low if (c.x > mx) == front and (c.y > 0) == left]
    return Vector((sum(c.x for c in g) / len(g), sum(c.y for c in g) / len(g), 0))
feet = {(f, l): foot(f, l) for f in (True, False) for l in (True, False)}
# a standardbred is leaner than the reference cob: longer in the frame, narrower, and the barrel lifted so the
# belly sits higher and the legs read longer. Only the trunk between the legs is lifted; legs and head untouched.
fx0 = (feet[(True, True)].x + feet[(True, False)].x) / 2; hx0 = (feet[(False, True)].x + feet[(False, False)].x) / 2
for v in horse.data.vertices:
    c = v.co
    if hx0 + .2 < c.x < fx0 - .1 and W * .4 < c.z < W * .75:
        k = min(1, (c.z - W * .4) / (W * .1)) * min(1, (c.x - hx0 - .2) / .6, (fx0 - .1 - c.x) / .6)
        c.z += k * .3 * (W * .75 - c.z)
    c.y *= .82
for f in feet.values(): f.y *= .82
paint_horse(horse)
co = [v.co.copy() for v in horse.data.vertices]
print("W", round(W, 2), "nose", tuple(round(v, 2) for v in nose), "feet", {k: tuple(round(x, 2) for x in v) for k, v in feet.items()})

# ---- skeleton
arm_d = bpy.data.armatures.new("rig"); arm = bpy.data.objects.new("rig", arm_d); bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="EDIT")
eb = arm_d.edit_bones
def bone(name, h, t, parent=None, connect=False):
    b = eb.new(name); b.head, b.tail = Vector(h), Vector(t)
    if parent: b.parent = eb[parent]; b.use_connect = connect
    b.align_roll(Vector((0, 1, 0)))                                             # local Z = the horse's left: leg swings are rotations about Z
    return b
fx = (feet[(True, True)].x + feet[(True, False)].x) / 2; hx = (feet[(False, True)].x + feet[(False, False)].x) / 2
bone("root", (0, 0, W * .62), (0, 0, W * .8))
bone("hips", (hx + .4, 0, W * .8), (0, 0, W * .8), "root")
bone("chest", (0, 0, W * .8), (fx + .4, 0, W * .82), "root")
neck0 = Vector((fx + .6, 0, W * .88)); poll = Vector((nose.x - 1.6, 0, nose.z + .9))
bone("neck", neck0, neck0.lerp(poll, .5), "chest"); bone("neck2", neck0.lerp(poll, .5), poll, "neck", True)
bone("head", poll, (nose.x, 0, nose.z), "neck2", True)
tail0 = Vector((min(c.x for c in co if c.z > W * .7) + .3, 0, W * .88))
bone("tail", tail0, tail0 + Vector((-.6, 0, -.8)), "hips"); bone("tail2", tail0 + Vector((-.6, 0, -.8)), tail0 + Vector((-.9, 0, -2.2)), "tail", True)
for left in (True, False):
    s = "L" if left else "R"
    f = feet[(True, left)]; y = f.y
    bone(f"shoulder{s}", (f.x + .6, y * .8, W * .92), (f.x + .15, y, W * .56), "chest")
    bone(f"forearm{s}", (f.x + .15, y, W * .56), (f.x, y, W * .3), f"shoulder{s}", True)
    bone(f"fcannon{s}", (f.x, y, W * .3), (f.x - .02, y, W * .085), f"forearm{s}", True)
    bone(f"fpastern{s}", (f.x - .02, y, W * .085), (f.x + .2, y, 0), f"fcannon{s}", True)
    f = feet[(False, left)]; y = f.y
    bone(f"thigh{s}", (f.x + .1, y * .7, W * .88), (f.x + .55, y, W * .6), "hips")
    bone(f"gaskin{s}", (f.x + .55, y, W * .6), (f.x - .3, y, W * .32), f"thigh{s}", True)
    bone(f"hcannon{s}", (f.x - .3, y, W * .32), (f.x - .2, y, W * .085), f"gaskin{s}", True)
    bone(f"hpastern{s}", (f.x - .2, y, W * .085), (f.x + .05, y, 0), f"hcannon{s}", True)
bpy.ops.object.mode_set(mode="OBJECT")

# ---- skin
for o in bpy.context.selected_objects: o.select_set(False)
horse.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")
print("groups", len(horse.vertex_groups))

# ---- the trot: diagonal pairs (near fore with off hind) together; half the stride in stance sweeping back,
# half in swing where the knee/hock folds and the leg reaches forward. Angles: positive = hoof forward.
smooth = lambda x: x * x * (3 - 2 * x)
clamp = lambda x: max(0., min(1., x))
def legs(ph, fore):
    """Joint angles for one leg at stride phase ph (0..1), positive = hoof forward. Stance is the first 40%: the
    leg lands reaching with the knee soft, sweeps back under the body with the fetlock sinking deep under load,
    and flicks off the toe. Swing: the upper bone lifts first and high, the lower joints fold a beat later and
    unfold a beat later, so the leg rolls through instead of hinging. The hind leg never straightens: the hock
    stays bent through stance."""
    ph %= 1; st = .4
    if ph < st:
        u = ph / st; sweep = (.55 - 1.15 * u) if fore else (.5 - 1.0 * u)
        flick = smooth(clamp((u - .7) / .3)); give = math.sin(math.pi * clamp(u / .8)); land = 1 - smooth(clamp(u / .35))
        return ([sweep * .45, sweep * .55 + .1 * land, -.25 * land - .2 * flick, .6 * give - 1.0 * flick] if fore
                else [sweep * .55, sweep * .25 + .1, -.35 - .2 * flick, .5 * give - .9 * flick])
    u = (ph - st) / (1 - st)
    sweep = (-.6 + 1.15 * smooth(u)) if fore else (-.5 + 1.0 * smooth(u))
    lift = math.sin(math.pi * clamp(u / .8)); fold = math.sin(math.pi * clamp((u - .05) / .75)); tip = math.sin(math.pi * clamp((u - .1) / .8))
    if fore: return [sweep * .45 + .35 * lift, sweep * .55 + .85 * lift, -2.4 * fold, -1.0 * tip]
    return [sweep * .55 + .45 * lift, sweep * .25 + .1 + .8 * lift, -.35 - 1.9 * fold, -.9 * tip]
N = 32
sc = bpy.context.scene; sc.frame_start, sc.frame_end = 0, N - 1; sc.render.fps = 24
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="POSE")
pb = arm.pose.bones
for b in pb: b.rotation_mode = "XYZ"
act = bpy.data.actions.new("trot"); arm.animation_data_create(); arm.animation_data.action = act
for fr in range(N):
    t = fr / N
    for left in (True, False):
        s = "L" if left else "R"
        fo = t + (0 if left else .5); hi = t + (.5 if left else 0) + .04          # LF with RH, RF with LH
        for name, a in zip((f"shoulder{s}", f"forearm{s}", f"fcannon{s}", f"fpastern{s}"), legs(fo, True)):
            pb[name].rotation_euler.z = -a; pb[name].keyframe_insert("rotation_euler", frame=fr)
        for name, a in zip((f"thigh{s}", f"gaskin{s}", f"hcannon{s}", f"hpastern{s}"), legs(hi, False)):
            pb[name].rotation_euler.z = -a; pb[name].keyframe_insert("rotation_euler", frame=fr)
    pb["root"].location = (0, .16 * math.cos(4 * math.pi * t + .9), 0); pb["root"].keyframe_insert("location", frame=fr)   # bone Y is up the bone: the lift, twice a stride
    pb["root"].rotation_euler.z = .025 * math.sin(4 * math.pi * t); pb["root"].keyframe_insert("rotation_euler", frame=fr)
    # racing carriage: neck stretched out and down, head extended, with a small nod against the lift
    pb["neck"].rotation_euler.z = .28 + .05 * math.sin(4 * math.pi * t + 1.2); pb["neck"].keyframe_insert("rotation_euler", frame=fr)
    pb["neck2"].rotation_euler.z = .0; pb["neck2"].keyframe_insert("rotation_euler", frame=fr)
    pb["head"].rotation_euler.z = -.55 + .04 * math.sin(4 * math.pi * t + 1.6); pb["head"].keyframe_insert("rotation_euler", frame=fr)
    pb["tail2"].rotation_euler.z = .1 * math.sin(4 * math.pi * t); pb["tail2"].keyframe_insert("rotation_euler", frame=fr)
bpy.ops.object.mode_set(mode="OBJECT")

bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_animations=True, export_force_sampling=True, export_frame_range=True)
print("NOSE_X", round(nose.x, 3))

# ---- check: a strip of 6 frames from the side
sc.render.engine = "BLENDER_WORKBENCH"; sc.display.shading.light = "STUDIO"; sc.display.shading.color_type = "VERTEX"
sc.render.resolution_x, sc.render.resolution_y = 600, 420
sc.world = bpy.data.worlds.new("w")
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "ORTHO"; cam.data.ortho_scale = 12; cam.location = (0, -30, 3.8); cam.rotation_euler = (math.pi / 2, 0, 0)
for k, fr in enumerate(range(0, N, N // 6)):
    sc.frame_set(fr); sc.render.filepath = STRIP.replace(".png", f"_{k}.png"); bpy.ops.render.render(write_still=True)
