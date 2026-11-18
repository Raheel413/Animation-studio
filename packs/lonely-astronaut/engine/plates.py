"""Blender plates for The Last Message Earth Ever Sent.
usage: python3 plates.py <plate> <samples> [scale]
Each plate renders 1920x1080 (or square for holograms) and writes plates/<name>.png
plus plates/<name>.json with projected screen points for compositing."""
import sys, math, json
import bpy, bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

PLATE, SAMPLES = sys.argv[-2], int(sys.argv[-1])
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
COLL = sc.collection

def srgb(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return (*[x / 12.92 if x <= 0.04045 else ((x + .055) / 1.055) ** 2.4 for x in c], 1)

_M = {}
def mat(hexc, rough=0.6, emit=0.0, metal=0.0, coat=0.0, alpha=1.0, trans=0.0):
    k = (hexc, rough, emit, metal, coat, alpha, trans)
    if k in _M: return _M[k]
    m = bpy.data.materials.new(f"m{len(_M)}"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = srgb(hexc)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat: b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = srgb(hexc)
        b.inputs["Emission Strength"].default_value = emit
    if trans: b.inputs["Transmission Weight"].default_value = trans
    if alpha < 1: b.inputs["Alpha"].default_value = alpha
    _M[k] = m
    return m

def _obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); COLL.objects.link(o); return o

def fin(o, m, bevel=0.0, sub=0, smooth=True):
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel:
        b = o.modifiers.new("b", "BEVEL"); b.width = bevel; b.segments = 4; b.limit_method = "ANGLE"
    if sub:
        s = o.modifiers.new("s", "SUBSURF"); s.levels = s.render_levels = sub
    o.data.materials.append(m); return o

def box(size, loc, m, bevel=0.02, rot=(0, 0, 0), sub=0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    o = _obj("box", bm); o.location = loc; o.rotation_euler = rot
    return fin(o, m, bevel, sub)

def cyl(r, d, loc, m, rot=(0, 0, 0), bevel=0.01, segs=64, r2=None):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r if r2 is None else r2, depth=d)
    o = _obj("cyl", bm); o.location = loc; o.rotation_euler = rot
    return fin(o, m, bevel)

def sph(r, loc, m, scale=(1, 1, 1), segs=64):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=segs // 2, radius=r)
    o = _obj("sph", bm); o.location = loc; o.scale = scale
    return fin(o, m)

def tor(R, r, loc, m, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=96, minor_segments=20)
    o = bpy.context.active_object; o.location, o.rotation_euler, o.scale = loc, rot, scale
    return fin(o, m)

def capsule_x(L, r, loc, m):
    """capsule lying along X"""
    o = cyl(r, L, loc, m, rot=(0, math.pi / 2, 0), bevel=r * 0.95, segs=64)
    o.modifiers["b"].segments = 10
    return o

def cut(o, cutter):
    b = o.modifiers.new("cut", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = cutter; b.solver = "EXACT"
    cutter.hide_render = cutter.hide_viewport = True

def look(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat("-Z", "Y").to_euler()

def area(loc, target, energy, size, col="#FFFFFF", shape="SQUARE"):
    l = bpy.data.lights.new("a", "AREA"); l.energy = energy; l.size = size; l.color = srgb(col)[:3]
    o = bpy.data.objects.new("a", l); COLL.objects.link(o); o.location = loc; look(o, target); return o

def point(loc, energy, col="#FFFFFF", r=0.05):
    l = bpy.data.lights.new("p", "POINT"); l.energy = energy; l.color = srgb(col)[:3]; l.shadow_soft_size = r
    o = bpy.data.objects.new("p", l); COLL.objects.link(o); o.location = loc; return o

def sun(direction, energy, col="#FFFFFF", angle=0.03):
    l = bpy.data.lights.new("s", "SUN"); l.energy = energy; l.color = srgb(col)[:3]; l.angle = angle
    o = bpy.data.objects.new("s", l); COLL.objects.link(o)
    o.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler(); return o

def camera(loc, target, lens=35, fstop=0, focus=None):
    cd = bpy.data.cameras.new("c"); cd.lens = lens
    if fstop:
        cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
        cd.dof.focus_distance = (Vector(focus or target) - Vector(loc)).length
    c = bpy.data.objects.new("c", cd); COLL.objects.link(c); c.location = loc; look(c, target)
    sc.camera = c; return c

def world(hexc="#05070D", strength=1.0):
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = srgb(hexc)
    w.node_tree.nodes["Background"].inputs[1].default_value = strength

POINTS = {}
def mark(name, p):
    POINTS[name] = Vector(p)

def render(name, w=1920, h=1080, transparent=False):
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.film_transparent = transparent
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.filepath = f"plates/{name}.png"
    bpy.context.view_layer.update()
    pts = {}
    for k, p in POINTS.items():
        v = world_to_camera_view(sc, sc.camera, p)
        pts[k] = [round(v.x * w, 1), round((1 - v.y) * h, 1)]
    json.dump(pts, open(f"plates/{name}.json", "w"))
    bpy.ops.render.render(write_still=True)
    print("DONE", name)

# ------------------------------------------------------------ palette
CREAM, CREAM2, SLATE, SLATE2, DARK = "#D9D2C3", "#BDB4A2", "#3A4354", "#2A3140", "#1A1F2A"
ORANGE, AMBER, CYAN, RED = "#D97724", "#FFB347", "#38BDF8", "#FF3B30"

def console_screens(base_loc, w, h, n, col, emit=3.0, tilt=0.0, z_step=0.0):
    for i in range(n):
        x = base_loc[0] + (i - (n - 1) / 2) * (w + 0.04)
        box((w, 0.01, h), (x, base_loc[1], base_loc[2] + i * z_step), mat(col, 0.3, emit), bevel=0.004, rot=(tilt, 0, 0))

# ============================================================ COCKPIT
def cockpit_shell():
    wall = box((5.0, 0.25, 3.4), (0, 1.3, 1.6), mat(SLATE2, 0.7), bevel=0.03)
    hole = box((3.4, 1.0, 1.55), (0, 1.3, 1.85), mat(SLATE2), bevel=0.3)
    hole.modifiers["b"].segments = 8
    cut(wall, hole)
    # cream window frame ring
    fr = box((3.62, 0.18, 1.77), (0, 1.16, 1.85), mat(CREAM, 0.55), bevel=0.32)
    fr.modifiers["b"].segments = 8
    fh = box((3.4, 1.0, 1.55), (0, 1.16, 1.85), mat(CREAM), bevel=0.3); fh.modifiers["b"].segments = 8
    cut(fr, fh)
    # mullions
    for x in (-0.6, 0.6):
        box((0.06, 0.08, 1.6), (x, 1.12, 1.85), mat(CREAM, 0.55), bevel=0.02)
    box((6, 6, 0.2), (0, -1.0, -0.1), mat(DARK, 0.8), bevel=0)            # floor
    box((6, 6, 0.2), (0, -1.0, 3.3), mat(SLATE2, 0.8), bevel=0)           # ceiling
    for s in (-1, 1):
        box((0.25, 5, 3.4), (s * 2.5, -1.0, 1.6), mat(SLATE, 0.7), bevel=0.03)
        # ribs
        for y in (-2.6, -1.5, -0.4, 0.6):
            box((0.12, 0.14, 3.2), (s * 2.36, y, 1.6), mat(SLATE2, 0.6), bevel=0.03)
        # warm strip lights on the side walls
        box((0.03, 3.6, 0.04), (s * 2.36, -1.0, 2.75), mat(AMBER, 0.3, 6.0), bevel=0.01)
    # front console: sloped desk
    desk = box((3.6, 0.7, 0.18), (0, 0.72, 0.92), mat(CREAM2, 0.55), bevel=0.06, rot=(math.radians(-18), 0, 0))
    box((3.6, 0.5, 0.85), (0, 0.85, 0.42), mat(SLATE, 0.6), bevel=0.05)
    # screens on the desk
    for i, (x, col, w) in enumerate([(-1.25, CYAN, 0.45), (-0.55, AMBER, 0.35), (0.0, CYAN, 0.5), (0.55, AMBER, 0.35), (1.25, CYAN, 0.45)]):
        box((w, 0.02, 0.22), (x, 0.62, 1.07), mat(col, 0.3, 2.2 if col == CYAN else 1.6), bevel=0.01, rot=(math.radians(-58), 0, 0))
    # small buttons
    for i in range(14):
        x = -1.5 + i * 0.23
        c = [ORANGE, CYAN, CREAM, RED][i % 4]
        cyl(0.025, 0.03, (x, 0.48, 0.99), mat(c, 0.4, 1.5 if c in (CYAN, RED) else 0), rot=(math.radians(-18), 0, 0))
    # side consoles angled
    for s in (-1, 1):
        box((0.7, 1.2, 0.9), (s * 1.95, 0.1, 0.45), mat(SLATE, 0.6), bevel=0.05)
        box((0.7, 1.2, 0.1), (s * 1.95, 0.1, 0.95), mat(CREAM2, 0.55), bevel=0.04)
        box((0.5, 0.02, 0.32), (s * 1.95, -0.05, 1.25), mat(CYAN if s < 0 else AMBER, 0.3, 1.8), bevel=0.01,
            rot=(math.radians(-70), 0, s * math.radians(-30)))
    # overhead panel with warm light
    box((2.6, 0.9, 0.12), (0, 0.2, 3.12), mat(CREAM2, 0.6), bevel=0.04)
    box((2.2, 0.6, 0.02), (0, 0.2, 3.05), mat("#FFD9A0", 0.3, 4.0), bevel=0.01)

def plate_cockpit():
    world("#000000", 0)
    cockpit_shell()
    area((0, 0.2, 2.9), (0, -0.6, 0.8), 260, 2.2, "#FFD7A8")
    area((0, 2.6, 1.9), (0, -1, 1.2), 140, 3.0, "#7FB2FF")   # cool spill from the window
    point((-1.2, 0.5, 1.15), 30, CYAN, 0.2); point((1.2, 0.5, 1.15), 30, CYAN, 0.2)
    camera((0, -2.55, 1.42), (0, 1.3, 1.62), lens=26)
    for n, p in {"win_tl": (-1.7, 1.2, 2.62), "win_br": (1.7, 1.2, 1.08), "chair": (0, -0.6, 1.2)}.items(): mark(n, p)
    render("cockpit", transparent=True)

def plate_chair():
    world("#000000", 0)
    cockpit_shell()
    for o in list(COLL.objects):
        if o.type == "MESH": o.hide_render = False
    # hide everything, render chair as its own layer (holdout the rest)
    hold = bpy.data.materials.new("hold"); hold.use_nodes = True
    nt = hold.node_tree; nt.nodes.clear()
    ho = nt.nodes.new("ShaderNodeHoldout"); out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(ho.outputs[0], out.inputs[0])
    for o in list(COLL.objects):
        if o.type == "MESH":
            o.data.materials.clear(); o.data.materials.append(hold)
    # chair
    seat = mat("#4E5668", 0.75)
    box((0.95, 0.85, 0.22), (0, -0.55, 0.62), seat, bevel=0.08)
    box((0.95, 0.2, 0.62), (0, -0.98, 0.98), seat, bevel=0.09, rot=(math.radians(12), 0, 0))
    box((0.7, 0.18, 0.12), (0, -1.03, 1.30), mat(CREAM2, 0.55), bevel=0.05, rot=(math.radians(12), 0, 0))
    cyl(0.09, 0.5, (0, -0.55, 0.3), mat(SLATE2, 0.5))
    for s in (-1, 1):
        box((0.12, 0.6, 0.1), (s * 0.55, -0.55, 0.82), mat(CREAM2, 0.55), bevel=0.04)
    area((0, 0.2, 2.9), (0, -0.6, 0.8), 260, 2.2, "#FFD7A8")
    area((0, 2.6, 1.9), (0, -1, 1.2), 140, 3.0, "#7FB2FF")
    camera((0, -2.55, 1.42), (0, 1.3, 1.62), lens=26)
    mark("chair_top", (0, -1.0, 1.34)); mark("chair_seat", (0, -0.55, 0.75))
    render("chair", transparent=True)

# ============================================================ QUARTERS (hologram corner + height wall)
def plate_quarters():
    world("#000000", 0)
    box((6, 0.3, 3.4), (0, 0.4, 1.6), mat(SLATE2, 0.7), bevel=0.03)                  # back wall
    port = cyl(0.55, 1.0, (-1.35, 0.4, 1.75), mat(SLATE2), rot=(math.pi / 2, 0, 0))
    cut(bpy.data.objects[0], port)
    tor(0.58, 0.07, (-1.35, 0.24, 1.75), mat(CREAM, 0.5), rot=(math.pi / 2, 0, 0))
    for x in (-2.4, -0.25, 2.1):
        box((0.14, 0.18, 3.2), (x, 0.22, 1.6), mat(SLATE, 0.6), bevel=0.03)
    box((6, 6, 0.2), (0, -2.0, -0.1), mat(DARK, 0.8), bevel=0)
    box((6, 6, 0.2), (0, -2.0, 3.3), mat(SLATE2, 0.8), bevel=0)
    # the height wall: tall cream panel with a printed ruler
    box((0.62, 0.06, 2.3), (1.05, 0.22, 1.25), mat("#E4DDCD", 0.65), bevel=0.03)
    for i in range(23):
        z = 0.2 + i * 0.1
        L = 0.16 if i % 5 == 0 else 0.07
        box((L, 0.012, 0.008), (0.8 + L / 2, 0.185, z), mat(SLATE, 0.6), bevel=0)
    # console table with hologram projector
    box((1.5, 0.7, 0.08), (0.0, -0.25, 0.86), mat(CREAM2, 0.55), bevel=0.03)
    box((1.4, 0.6, 0.8), (0.0, -0.2, 0.42), mat(SLATE, 0.6), bevel=0.04)
    cyl(0.2, 0.06, (0.0, -0.3, 0.93), mat(SLATE2, 0.4), bevel=0.02)
    tor(0.17, 0.012, (0.0, -0.3, 0.965), mat(CYAN, 0.3, 6.0))
    cyl(0.12, 0.01, (0.0, -0.3, 0.962), mat("#9FE6FF", 0.3, 2.5))
    # a mug and a small photo frame on the table, lived-in
    cyl(0.045, 0.1, (-0.5, -0.35, 0.95), mat(ORANGE, 0.5), bevel=0.01)
    box((0.14, 0.02, 0.18), (0.48, -0.1, 0.99), mat(CREAM, 0.5), bevel=0.01, rot=(math.radians(-12), 0, math.radians(-15)))
    # warm practicals
    box((4.6, 0.04, 0.04), (0, 0.2, 2.85), mat(AMBER, 0.3, 5.0), bevel=0.01)
    area((0.2, -1.2, 2.8), (0, 0.2, 0.9), 180, 2.0, "#FFD3A0")
    area((-1.35, 1.6, 1.75), (-0.5, -1, 1.2), 60, 1.0, "#7FB2FF")
    point((0.0, -0.3, 1.25), 25, CYAN, 0.3)
    camera((0.15, -3.6, 1.35), (0.15, 0.3, 1.2), lens=32)
    mark("wall_bl", (0.76, 0.19, 0.2)); mark("wall_tl", (0.76, 0.19, 2.4))
    mark("wall_br", (1.34, 0.19, 0.2)); mark("wall_tr", (1.34, 0.19, 2.4))
    mark("holo_base", (0.0, -0.3, 0.97)); mark("floor_astro", (-0.75, -0.7, 0.0))
    mark("port_c", (-1.35, 0.4, 1.75)); mark("port_e", (-0.8, 0.4, 1.75))
    render("quarters", transparent=True)

def plate_wallclose():
    """close-up of the height wall for the marking / erasing shots"""
    world("#000000", 0)
    box((3, 0.3, 3.4), (0, 0.4, 1.6), mat(SLATE2, 0.7), bevel=0.03)
    box((0.62, 0.06, 2.3), (0.0, 0.22, 1.25), mat("#E4DDCD", 0.65), bevel=0.03)
    for i in range(23):
        z = 0.2 + i * 0.1
        L = 0.16 if i % 5 == 0 else 0.07
        box((L, 0.012, 0.008), (-0.25 + L / 2, 0.185, z), mat(SLATE, 0.6), bevel=0)
    area((0.6, -1.2, 2.4), (0, 0.2, 1.2), 120, 1.6, "#FFD3A0")
    area((-0.8, -0.6, 0.8), (0, 0.2, 1.2), 30, 1.0, "#7FB2FF")
    camera((0.25, -1.85, 1.25), (0.0, 0.2, 1.25), lens=40)
    mark("wall_bl", (-0.25, 0.19, 0.2)); mark("wall_tl", (-0.25, 0.19, 2.4))
    mark("wall_br", (0.25, 0.19, 0.2)); mark("wall_tr", (0.25, 0.19, 2.4))
    render("wallclose", transparent=True)

# ============================================================ POD
def pod_model(frost=False, loc=(0, 0, 0)):
    x0, y0, z0 = loc
    body = mat("#E8EEF2" if frost else CREAM, 0.85 if frost else 0.5)
    capsule_x(2.2, 0.55, (x0, y0, z0), body)
    for dx in (-0.55, 0.55):
        cyl(0.565, 0.08, (x0 + dx, y0, z0), mat("#C9D6E0" if frost else ORANGE, 0.6), rot=(0, math.pi / 2, 0))
    # window (dark glass) on the top-front
    win = box((0.72, 0.46, 0.08), (x0 + 0.1, y0 - 0.2, z0 + 0.5), mat("#0A1220" if not frost else "#B9CFE0", 0.08 if not frost else 0.5, coat=1.0),
              bevel=0.12, rot=(math.radians(-22), 0, 0))
    win.modifiers["b"].segments = 6
    box((0.84, 0.56, 0.06), (x0 + 0.1, y0 - 0.2, z0 + 0.47), mat(SLATE, 0.5), bevel=0.12, rot=(math.radians(-22), 0, 0))
    # name plate
    box((0.4, 0.02, 0.09), (x0 + 0.1, y0 - 0.545, z0 + 0.14), mat("#C7C1B2" if not frost else "#DCE6EE", 0.6), bevel=0.01)
    # beacon
    cyl(0.05, 0.08, (x0 - 0.8, y0, z0 + 0.53), mat(SLATE, 0.5))
    sph(0.05, (x0 - 0.8, y0, z0 + 0.6), mat(RED, 0.3, 8.0))
    # thrusters / end caps
    for s in (-1, 1):
        cyl(0.22, 0.16, (x0 + s * 1.12, y0, z0), mat(SLATE2, 0.5), rot=(0, math.pi / 2, 0))
    return win

def plate_pod_space():
    world("#000000", 0)
    pod_model(frost=True)
    sun((0.4, 1.0, -0.3), 4.0, "#E8F2FF")
    area((-3, -3, 2), (0, 0, 0), 80, 3, "#6E88FF")
    camera((2.6, -4.2, 1.6), (0, 0, 0), lens=50)
    render("pod_space", 1400, 1000, transparent=True)

def plate_cargo():
    world("#000000", 0)
    pod_model(frost=True, loc=(0, 0, 0.75))
    box((8, 8, 0.2), (0, 0, -0.1), mat("#20252F", 0.75), bevel=0)
    for i in range(-3, 4):
        box((8, 0.04, 0.012), (0, i * 0.8, 0.005), mat(SLATE, 0.5), bevel=0)
    box((8, 0.3, 4), (0, 2.4, 2), mat(SLATE2, 0.7), bevel=0.02)
    for x in (-3, -1.5, 0, 1.5, 3):
        box((0.2, 0.25, 4), (x, 2.2, 2), mat(SLATE, 0.6), bevel=0.04)
    box((0.3, 8, 4), (-3.6, 0, 2), mat(SLATE2, 0.7), bevel=0.02)
    # cradle
    for dx in (-0.7, 0.7):
        box((0.3, 1.2, 0.35), (dx, 0, 0.17), mat(SLATE, 0.6), bevel=0.05)
    # cables from the wall to the pod
    for k, (sx, sz) in enumerate([(-1.2, 1.6), (0.8, 1.2)]):
        cu = bpy.data.curves.new("cab", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.03; cu.bevel_resolution = 4
        sp = cu.splines.new("BEZIER"); sp.bezier_points.add(2)
        for bp, p in zip(sp.bezier_points, [(sx, 2.25, sz), (sx * 0.6, 1.0, 0.05), (sx * 0.4, 0.5, 0.95)]):
            bp.co = p; bp.handle_left_type = bp.handle_right_type = "AUTO"
        cu.materials.append(mat("#2B2F36", 0.6))
        o = bpy.data.objects.new("cab", cu); COLL.objects.link(o)
    box((6, 0.05, 0.06), (0, 2.2, 3.4), mat(AMBER, 0.3, 4), bevel=0.01)
    box((0.06, 6, 0.06), (-3.4, 0, 3.4), mat("#9CC8FF", 0.3, 3), bevel=0.01)
    area((0.5, -0.5, 3.6), (0, 0, 0.7), 300, 2.5, "#D8E6FF")
    area((-2.5, 1.5, 1.5), (0, 0, 0.8), 80, 1.5, "#FFB070")
    camera((2.9, -3.5, 2.0), (0.05, 0.1, 0.75), lens=34)
    mark("pod_win", (0.1, -0.2, 1.3)); mark("floor_astro", (1.5, -1.2, 0.0)); mark("plate", (0.1, -0.56, 0.89))
    render("cargo", transparent=True)

def plate_podwindow():
    """close-up of the frosted pod window from above-front (frost + name added in 2D)"""
    world("#000000", 0)
    win = pod_model(frost=False, loc=(0, 0, 0))
    area((0.6, -1.6, 2.2), (0.1, -0.2, 0.5), 120, 1.4, "#D8E6FF")
    area((-1.0, -0.5, 1.2), (0.1, -0.2, 0.5), 40, 1.0, "#FFB070")
    c = camera((0.1, 0.2, 1.55), (0.1, -0.2, 0.5), lens=38)
    # window corners in the window's local frame
    import mathutils
    R = mathutils.Euler((math.radians(-22), 0, 0)).to_matrix()
    for n, (lx, ly) in {"w_tl": (-0.36, 0.23), "w_tr": (0.36, 0.23), "w_bl": (-0.36, -0.23), "w_br": (0.36, -0.23)}.items():
        mark(n, Vector((0.1, -0.2, 0.5)) + R @ Vector((lx, ly, 0.045)))
    mark("plate_c", (0.1, -0.56, 0.14))
    render("podwindow", transparent=True)

# ============================================================ SHIP
def ship_model(engines=0.0):
    hull = mat(CREAM, 0.5); trim = mat(SLATE, 0.55)
    capsule_x(4.2, 0.6, (0, 0, 0), hull)
    sph(0.6, (2.1, 0, 0), hull, scale=(1.5, 1, 1))
    sph(0.36, (2.65, 0, 0.18), mat("#0B1424", 0.06, coat=1.0), scale=(1.2, 1.05, 0.7))   # canopy
    for x in (0.9, -0.2, -1.3):
        cyl(0.615, 0.07, (x, 0, 0), mat(ORANGE, 0.55), rot=(0, math.pi / 2, 0))
    tor(1.25, 0.16, (-0.6, 0, 0), mat(CREAM2, 0.5), rot=(0, math.pi / 2, 0))           # ring module
    for a in range(4):
        ang = a * math.pi / 2
        box((0.1, 0.1, 1.2), (-0.6, math.sin(ang) * 0.65, math.cos(ang) * 0.65), trim, bevel=0.02, rot=(ang, 0, 0))
    for s in (-1, 1):   # nacelles
        capsule_x(1.6, 0.26, (-2.0, s * 0.85, -0.15), hull)
        box((0.8, 0.5, 0.08), (-1.7, s * 0.5, -0.1), trim, bevel=0.03)
        cyl(0.22, 0.3, (-2.85, s * 0.85, -0.15), trim, rot=(0, math.pi / 2, 0), r2=0.3)
        if engines:
            sph(0.2, (-3.02, s * 0.85, -0.15), mat("#7FD4FF", 0.2, engines), scale=(0.4, 1, 1))
    for s in (-1, 1):   # solar wings
        box((1.4, 2.0, 0.04), (-0.6, s * 2.4, 0), mat("#1C2A48", 0.35, coat=0.6), bevel=0.02)
        box((1.44, 2.04, 0.02), (-0.6, s * 2.4, -0.01), trim, bevel=0.01)
    cyl(0.04, 0.6, (0.3, 0, 0.85), trim)
    d = sph(0.32, (0.3, 0, 1.2), mat(CREAM2, 0.4), scale=(1, 1, 0.35))
    sph(0.04, (2.0, 0.45, 0.35), mat(RED, 0.3, 6)); sph(0.04, (2.0, -0.45, 0.35), mat("#3BFF7A", 0.3, 6))
    box((0.5, 0.02, 0.12), (1.3, -0.61, 0.1), mat(SLATE2, 0.5), bevel=0.01)   # name plate area

def plate_ship(name, engines=0.0, cam=(5.5, -9.0, 2.4)):
    world("#000000", 0)
    ship_model(engines)
    sun((0.6, 0.9, -0.35), 3.5, "#FFF1DD")
    area((-4, -6, -2), (0, 0, 0), 300, 6, "#4D6BFF")
    area((-6, 6, 3), (0, 0, 0), 500, 4, "#9FD8FF")     # rim from behind
    camera(cam, (0, 0, 0), lens=50)
    render(name, 1800, 1100, transparent=True)

# ============================================================ NEPTUNE
def plate_neptune():
    world("#000000", 0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=192, ring_count=96)
    p = bpy.context.active_object
    for f in p.data.polygons: f.use_smooth = True
    m = bpy.data.materials.new("nep"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.9
    tc = N.new("ShaderNodeTexCoord")
    noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 3.0; noise.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    add = N.new("ShaderNodeMath"); add.operation = "MULTIPLY_ADD"
    L.new(noise.outputs["Fac"], add.inputs[0]); add.inputs[1].default_value = 0.25; L.new(sep.outputs["Z"], add.inputs[2])
    wave = N.new("ShaderNodeMath"); wave.operation = "SINE"
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 14
    L.new(add.outputs[0], mul.inputs[0]); L.new(mul.outputs[0], wave.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = srgb("#1E4FA8"); ramp.color_ramp.elements[1].color = srgb("#5B95E6")
    rng = N.new("ShaderNodeMapRange"); rng.inputs["From Min"].default_value = -1
    L.new(wave.outputs[0], rng.inputs["Value"]); L.new(rng.outputs[0], ramp.inputs[0])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.08
    pw = N.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.5
    L.new(lw.outputs["Facing"], pw.inputs[0])
    b.inputs["Emission Color"].default_value = srgb("#7FD8FF")
    L.new(pw.outputs[0], b.inputs["Emission Strength"])
    p.data.materials.append(m)
    p.rotation_euler = (math.radians(14), 0, 0)
    sun((-1, 0.6, -0.2), 4.5, "#FFFFFF")
    camera((0, -4.2, 0), (0, 0, 0), lens=50)
    render("neptune", 1600, 1600, transparent=True)

# ============================================================ HOLOGRAMS (Noor)
def holo_mat(strength=1.0, dark=False):
    m = bpy.data.materials.new("holo"); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    em = N.new("ShaderNodeEmission")
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    rng = N.new("ShaderNodeMapRange")
    rng.inputs["To Min"].default_value = 0.35 * strength; rng.inputs["To Max"].default_value = 2.4 * strength
    L.new(lw.outputs["Facing"], rng.inputs["Value"])
    em.inputs["Color"].default_value = srgb("#0C2A3A" if dark else "#7FE3FF")
    L.new(rng.outputs[0], em.inputs["Strength"])
    L.new(em.outputs[0], out.inputs[0])
    return m

def limb(p1, p2, r, m, r2=None):
    p1, p2 = Vector(p1), Vector(p2)
    o = cyl(r, (p2 - p1).length, (p1 + p2) / 2, m, bevel=min(r, r2 or r) * 0.9, r2=r2)
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(p2 - p1).to_euler()
    o.modifiers["b"].segments = 8
    return o

def noor(age="child", arm=0.0, mouth=0.0, tilt=0.0, turn=0.0, smile=0.0):
    H = holo_mat(); D = holo_mat(0.18, dark=True)
    root = bpy.data.objects.new("root", None); COLL.objects.link(root)
    made = []
    def P(o):
        made.append(o); return o
    if age == "child":
        hz = 0.98
        P(sph(0.17, (0, 0, hz), H, scale=(1, 0.95, 1.0)))
        P(sph(0.178, (0, 0.025, hz + 0.035), H, scale=(1.03, 1.0, 0.93)))
        P(box((0.26, 0.05, 0.06), (0, -0.14, hz + 0.1), H, bevel=0.025))           # fringe
        for s in (-1, 1):
            P(sph(0.07, (s * 0.2, 0.04, hz + 0.02), H))
            P(sph(0.024, (s * 0.06, -0.152, hz - 0.01), D, scale=(1, 0.6, 1.25)))
        P(sph(0.03, (0, -0.16, hz - 0.085), D, scale=(1.5, 0.5, 0.35 + mouth)))
        P(limb((0, 0, 0.8), (0, 0, 0.42), 0.12, H, r2=0.2))                         # dress
        for s in (-1, 1):
            P(limb((s * 0.07, 0, 0.42), (s * 0.075, 0, 0.04), 0.045, H))
            P(sph(0.055, (s * 0.075, -0.02, 0.03), H, scale=(1, 1.4, 0.6)))
        P(limb((-0.12, 0, 0.76), (-0.2, 0, 0.5), 0.038, H)); P(sph(0.045, (-0.205, 0, 0.47), H))
        a = math.radians(arm)
        sh = Vector((0.12, 0, 0.76)); el = sh + Vector((0.16, 0, 0.12))
        hd = el + Vector((math.sin(a) * 0.17, -0.02, math.cos(a) * 0.17))
        P(limb(sh, el, 0.038, H)); P(limb(el, hd, 0.036, H)); P(sph(0.048, hd, H))
        cam_t, cam_l = (0, 0, 0.55), (0, -2.9, 0.62)
    else:
        hz = 1.55
        P(sph(0.13, (0, 0, hz), H, scale=(0.94, 0.95, 1.1)))
        P(sph(0.142, (0, 0.03, hz + 0.035), H, scale=(1.04, 1.0, 0.98)))         # hair crown
        P(box((0.22, 0.05, 0.07), (0.015, -0.115, hz + 0.085), H, bevel=0.03, rot=(0, 0.12, 0)))  # fringe
        for s in (-1, 1):
            P(box((0.055, 0.17, 0.24), (s * 0.122, 0.025, hz - 0.075), H, bevel=0.027))
            P(sph(0.019, (s * 0.046, -0.117, hz - 0.002), D, scale=(1, 0.6, 1.3)))
            P(box((0.042, 0.01, 0.007), (s * 0.047, -0.121, hz + 0.044), D, bevel=0.003, rot=(0, s * 0.18, 0)))
        P(sph(0.024, (0, -0.124, hz - 0.07), D, scale=(1.4 + smile, 0.45, 0.22 + mouth * 1.5)))
        P(limb((0, 0, hz - 0.12), (0, 0, hz - 0.22), 0.045, H))
        P(sph(0.21, (0, 0.01, hz - 0.33), H, scale=(1.18, 0.6, 0.42)))          # hoodie shoulders
        P(cyl(0.235, 0.34, (0, 0.01, hz - 0.5), H, r2=0.2, bevel=0.04))
        P(tor(0.075, 0.028, (0, 0.02, hz - 0.215), H, scale=(1.25, 1, 0.8)))       # hood ring
        for s in (-1, 1):
            P(limb((s * 0.035, -0.11, hz - 0.27), (s * 0.04, -0.13, hz - 0.42), 0.007, H))   # strings
        cam_t, cam_l = (0, 0, hz - 0.1), (0, -1.35, hz - 0.04)
    for o in made:
        o.parent = root
    root.rotation_euler = (0, math.radians(tilt), math.radians(turn))
    camera(cam_l, cam_t, lens=50)
    world("#000000", 0)

def plate_holo(age, frames):
    for i, kw in enumerate(frames):
        for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
        _M.clear()
        noor(age, **kw)
        render(f"holo_{age}_{i}", 900, 900, transparent=True)

PLATES = {
    "cockpit": plate_cockpit, "chair": plate_chair, "quarters": plate_quarters, "wallclose": plate_wallclose,
    "pod_space": plate_pod_space, "cargo": plate_cargo, "podwindow": plate_podwindow,
    "ship": lambda: plate_ship("ship", 0.0), "ship_burn": lambda: plate_ship("ship_burn", 14.0),
    "ship_rear": lambda: plate_ship("ship_rear", 0.0, cam=(-9.5, -4.0, 1.6)),
    "neptune": plate_neptune,
    "holo_child": lambda: plate_holo("child", [dict(arm=a, mouth=m) for a, m in ((-10, 0), (15, 0.6), (40, 0.3), (15, 0))]),
    "holo_teen": lambda: plate_holo("teen", [dict(mouth=0, tilt=0), dict(mouth=0.5, tilt=0), dict(mouth=0, tilt=4, turn=-8),
                                              dict(mouth=0.5, tilt=4, turn=-8), dict(mouth=0, tilt=-3, turn=10), dict(mouth=0.5, tilt=-3, turn=10),
                                              dict(mouth=0, smile=0.6, tilt=2), dict(mouth=0.25, smile=0.6, tilt=2)]),
}
PLATES[PLATE]()
