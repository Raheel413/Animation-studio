"""Shot list for THE LAST MESSAGE EARTH EVER SENT. Each shot: (name, duration, fn(t, T) -> float RGB)."""
import json, math, functools
import numpy as np, cv2
from eng import *

def P(name): return json.load(open(f"{ROOT}/plates/{name}.json"))
VO = json.load(open(f"{ROOT}/audio/lines.json"))

# ---------------------------------------------------------------- helpers
class Cam:
    """scale s about focus (fx,fy) then shift by (dx,dy)."""
    def __init__(self, fx, fy, s=1.0, dx=0.0, dy=0.0): self.fx, self.fy, self.s, self.dx, self.dy = fx, fy, s, dx, dy
    def m(self, x, y): return (self.fx + (x - self.fx) * self.s + self.dx, self.fy + (y - self.fy) * self.s + self.dy)
    def plate(self, img, layer, op=1.0, add=False):
        h, w = layer.shape[:2]
        x, y = self.m(0, 0)
        return put(img, layer, x, y, s=self.s * (W / w), op=op, anchor=(0, 0), add=add)

def blur_layer(name, sigma):
    return _blurred(name, sigma)

@functools.lru_cache(maxsize=8)
def _blurred(name, sigma):
    l = load(name).copy(); return cv2.GaussianBlur(l, (0, 0), sigma)

def ui_panel(lines, t, colors=None, size=40, x=210, y=250, cursor=True, t_starts=None, cps=34, path=FONT_MONO):
    """typed terminal text; returns list of (layer, x, y)"""
    out = []
    for i, l in enumerate(lines):
        t0 = t_starts[i] if t_starts else i * 1.2
        s = typed(l, t, t0, cps)
        if not s: continue
        if cursor and len(s) < len(l) or (cursor and i == len(lines) - 1 and int(t * 2) % 2 == 0 and len(s) == len(l)):
            s = s + "█"
        col = colors[i] if colors else CYAN
        out.append((text_layer([s], size=size, path=path, color=col), x, y + i * size * 1.6))
    return out

def draw_ui(img, items, op=1.0, glow_k=0.0):
    for lay, x, y in items:
        put(img, lay, x, y, op=op, anchor=(0, 0))
        if glow_k:
            g = lay.copy(); g = cv2.GaussianBlur(g, (0, 0), 6)
            put(img, g, x, y, op=op * glow_k, anchor=(0, 0), add=True)
    return img

def screen_bg(img, t, tint_col=(0.02, 0.05, 0.08), curve=True):
    """a monitor face filling the frame: dark glass, scanlines, faint grid, edge bezel."""
    img[:] = np.array(tint_col, np.float32)
    if not hasattr(screen_bg, "lines"):
        r = (np.arange(H) % 3 == 0).astype(np.float32)
        screen_bg.lines = (1 - 0.18 * r)[:, None, None]
        g = np.zeros((H, W), np.float32)
        for x in range(0, W, 80): g[:, x] = 1
        for y in range(0, H, 80): g[y, :] = 1
        screen_bg.grid = cv2.GaussianBlur(g, (0, 0), 0.6)[..., None] * np.array([0.02, 0.06, 0.08], np.float32)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.maximum(np.abs(xx - W / 2) / (W / 2), np.abs(yy - H / 2) / (H / 2))
        screen_bg.edge = np.clip((d - 0.86) * 8, 0, 1)[..., None]
    img += screen_bg.grid
    return img

def screen_post(img):
    img *= screen_bg.lines
    img *= (1 - screen_bg.edge * 0.9)
    return img

def voice_env(T):
    """amplitude of Noor's current line at absolute time T (set by timeline)."""
    return ENV.get(int(T * FPS), 0.0)
ENV = {}

def teen_frame(T, pose=0, smile=False):
    """pick hologram frame by pose with mouth driven by voice envelope"""
    open_ = voice_env(T) > 0.05
    if smile: return f"holo_teen_{7 if open_ else 6}"
    return f"holo_teen_{pose * 2 + (1 if open_ else 0)}"

def stars_window(img, t, rect, earth_pos=None, earth_r=3.0, pan=(0, 0)):
    x0, y0, x1, y1 = [int(v) for v in rect]
    sb = space_bg(t, pan=pan, zoom=1.0)
    img[y0:y1, x0:x1] = sb[y0:y1, x0:x1]
    if earth_pos: earth(img, earth_pos[0], earth_pos[1], earth_r)
    return img

def sun(img, x, y, r=5, k=1.0):
    disc(img, x, y, r, (1.0, 0.97, 0.9))
    bloom_spot(img, x, y, r * 4, (1.0, 0.85, 0.6), 0.6 * k)
    bloom_spot(img, x, y, r * 14, (0.9, 0.6, 0.35), 0.08 * k)
    return img

# ---------------------------------------------------------------- plate geometry
PC = P("cockpit"); PCH = P("chair"); PQ = P("quarters"); PW = P("wallclose"); PCG = P("cargo")
WIN = (PC["win_tl"][0], PC["win_tl"][1], PC["win_br"][0], PC["win_br"][1])

def wall_y(z, pts):   # wall height (m, 0.2..2.4) -> screen y on a wall plate
    b, t_ = pts["wall_bl"][1], pts["wall_tl"][1]
    return b + (t_ - b) * (z - 0.2) / 2.2

MARKS = [(0.98, "3"), (1.06, "4"), (1.13, "5"), (1.19, "6"), (1.25, "7"), (1.31, "8"),
         (1.37, "9"), (1.43, "10"), (1.49, "11"), (1.54, "12"), (1.585, "13")]

def draw_marks(img, cam, pts, t, visible=None, new_mark=None):
    """pencil marks across the height panel, with age labels."""
    xl, xr = pts["wall_bl"][0], pts["wall_br"][0]
    for i, (z, lab) in enumerate(MARKS):
        op = 1.0 if visible is None else visible(i)
        if op <= 0.01: continue
        y = wall_y(z, pts)
        x0, y0 = cam.m(xl + (xr - xl) * 0.05, y); x1, _ = cam.m(xl + (xr - xl) * 0.72, y)
        ln = np.zeros((14, int(x1 - x0) + 4, 4), np.float32)
        cv2.line(ln, (2, 7), (ln.shape[1] - 3, 7 + (i % 3 - 1)), (0.55, 0.22, 0.05, 1.0), 3, cv2.LINE_AA)
        put(img, ln, x0, y0, s=cam.s ** 0, op=op, anchor=(0, 0.5))
        tl = text_layer([lab], size=int(22 * cam.s), path=FONT_MED, color=(0.45, 0.2, 0.06))
        put(img, tl, x1 + 10 * cam.s, y0, op=op * 0.9, anchor=(0, 0.5))
    if new_mark:
        z, lab, prog = new_mark
        y = wall_y(z, pts)
        x0, y0 = cam.m(xl + (xr - xl) * 0.05, y); x1, _ = cam.m(xl + (xr - xl) * 0.85, y)
        L = int((x1 - x0) * prog)
        if L > 2:
            ln = np.zeros((16, L + 4, 4), np.float32)
            cv2.line(ln, (2, 8), (L + 1, 8), (0.85, 0.40, 0.08, 1.0), 4, cv2.LINE_AA)
            put(img, ln, x0, y0, anchor=(0, 0.5))
        if prog > 0.95:
            tl = text_layer([lab], size=int(24 * cam.s), path=FONT_MED, color=(0.85, 0.40, 0.08))
            put(img, tl, x1 + 12, y0, op=ramp(prog, 0.95, 1.0), anchor=(0, 0.5))
    return img

def glove(img, x, y, s=1.0, rot=0.0, op=1.0, mul=(1, 1, 1), anchor=(0.38, 0.97)):
    """(x, y) is where the fingertips land."""
    g = tint(load("assets/c_glove.png"), mul)
    return put(img, g, x, y, s=s, rot=rot, op=op, anchor=anchor)

# ================================================================= SHOTS
def s_incoming(t, T):
    img = blank(); screen_bg(img, t)
    lines = ["INCOMING TRANSMISSION", "ORIGIN ......... EARTH  /  DSN-14", "CLASS .......... FINAL VERIFIED SIGNAL", "ADDRESSED TO ... ASTRO"]
    cols = [AMBER, CYAN, (1.0, 0.45, 0.35), CYAN]
    items = ui_panel(lines, t, cols, size=46, x=230, y=300, t_starts=[1.2, 2.8, 4.4, 6.2], cps=30)
    draw_ui(img, items, glow_k=0.8)
    if t > 7.6:
        pulse = 0.65 + 0.35 * math.sin((t - 7.6) * 4)
        b = text_layer(["[  ▶  PLAY  ]"], size=54, path=FONT_MONO_B, color=CYAN)
        put(img, b, W / 2, 790, op=ramp(t, 7.6, 8.2) * pulse)
        put(img, cv2.GaussianBlur(b, (0, 0), 10), W / 2, 790, op=ramp(t, 7.6, 8.2) * pulse, add=True)
    if 1.2 < t < 3:   # blinking dot
        disc(img, 196, 326, 9, AMBER, op=0.5 + 0.5 * math.sin(t * 14))
    screen_post(img)
    s = 1.0 + 0.05 * ramp(t, 0, 10)
    out = blank(); put(out, np.dstack([img, np.ones((H, W, 1), np.float32)]), W / 2, H / 2, s=s)
    return out * ramp(t, 0.0, 0.8)

def helmet_close(t, T, expr, look=(0, 0), push=(1.0, 1.06), dur=5.0, glow_side=-1, cyan_k=0.9, warm=False, tremble=0.0):
    img = blank()
    bg = _blurred("plates/cockpit.png", 14)
    put(img, bg, W / 2, H / 2, s=1.25 + 0.03 * t / dur)
    img *= 0.45
    bloom_spot(img, W * (0.15 if glow_side < 0 else 0.85), H * 0.45, 420, CYAN if not warm else AMBER, 0.18)
    s = push[0] + (push[1] - push[0]) * ease_io(t / dur)
    lk = (look[0] + tremble * noise1(t, 3, 9) * 0.25, look[1] + tremble * noise1(t, 4, 9) * 0.2)
    rd = (-1, -0.2) if glow_side < 0 else (1, -0.2)
    mul = (0.92, 0.95, 1.0) if not warm else (1.0, 0.9, 0.8)
    draw_astro(img, t, "full_cut", W / 2 + 40, 1080 + 2600 * s * 0.55, 2600 * s, expr=expr, look=lk,
               mul=mul, rimc=CYAN if not warm else AMBER, rims=cyan_k, rimdir=rd, shadow=0)
    return img

def s_helmet_surprised(t, T): return helmet_close(t, T, "SURPRISED", dur=5.0)
def s_helmet_sad_down(t, T): return helmet_close(t, T, "SAD", look=(0.0, 0.7), dur=3.5, push=(1.06, 1.08))

def s_glove_hover(t, T):
    img = blank(); screen_bg(img, t)
    b = text_layer(["[  ▶  PLAY  ]"], size=110, path=FONT_MONO_B, color=CYAN)
    pulse = 0.7 + 0.3 * math.sin(t * 4)
    put(img, b, W * 0.46, H * 0.48, op=pulse)
    put(img, cv2.GaussianBlur(b, (0, 0), 16), W * 0.46, H * 0.48, op=pulse, add=True)
    screen_post(img)
    # glove reaches in, hovers, pulls back
    y = kf(t, [(0, 1500), (1.6, 640), (3.0, 625), (4.2, 1500)])
    x = kf(t, [(0, 1500), (1.6, 1010), (3.0, 1000), (4.2, 1500)])
    glove(img, x, y + 6 * math.sin(t * 2.3), s=2.0, rot=160, mul=(0.75, 0.85, 1.0))
    return img

def s_title(t, T):
    img = space_bg(t, pan=(t * 6, 0)) * 0.8
    tl = text_layer(["THE LAST MESSAGE EARTH EVER SENT"], size=56, path=FONT_THIN, color=(0.95, 0.95, 0.95), tracking=14)
    op = ramp(t, 1.0, 2.8) * (1 - ramp(t, 6.4, 7.8))
    put(img, tl, W / 2, H / 2, op=op)
    return img

def s_ship_alone(t, T):
    img = space_bg(t, pan=(-120 + t * 5, 30))
    sun(img, 1560, 300, 6)
    earth(img, 1520, 318, 2.4)
    sp = load("plates/ship.png")
    put(img, sp, 640 + t * 9, 560, s=0.42)
    tl = text_layer([typed("KESTREL  ·  OUTER SYSTEM SURVEY  ·  CREW: 1", t, 1.5, 24)], size=26, path=FONT_MONO, color=(0.75, 0.85, 0.95))
    put(img, tl, 120, H - BAR - 70, anchor=(0, 0.5), op=0.9 * (1 - ramp(t, 7, 8)))
    return img

def cockpit_wide(t, T, s0=1.0, s1=1.05, dur=7.0, expr="NEUTRAL", earth_r=3.2, focus=None, astro_on=True, earth_glint=0.0):
    img = blank()
    fx, fy = focus or (W / 2, H * 0.45)
    cam = Cam(fx, fy, s0 + (s1 - s0) * ease_io(t / dur))
    sb = space_bg(t, pan=(t * 2, 0))
    put(img, np.dstack([sb, np.ones((H, W, 1), np.float32)]), *cam.m(W / 2, H / 2), s=cam.s)
    ex, ey = cam.m(W * 0.58, H * 0.36)
    sun(img, ex + 30 * cam.s, ey - 10 * cam.s, 4 * cam.s, 0.7)
    earth(img, ex, ey, earth_r * cam.s)
    if earth_glint: bloom_spot(img, ex, ey, 30 * cam.s, (0.3, 0.55, 1.0), earth_glint)
    cam.plate(img, load("plates/cockpit.png"))
    if astro_on:
        cx, cy = cam.m(PCH["chair_top"][0], PCH["chair_top"][1])
        draw_astro(img, t, "back", cx, cy + 250 * cam.s, 560 * cam.s, expr=expr, mul=(0.62, 0.62, 0.7),
                   rimc=(0.55, 0.75, 1.0), rims=0.9, rimdir=(0, -1), shadow=0)
    cam.plate(img, load("plates/chair.png"))
    return img

def s_cockpit_intro(t, T): return cockpit_wide(t, T, 1.0, 1.06, 7.0)

def quarters(t, T, holo=None, holo_op=1.0, expr="NEUTRAL", look=(0, 0), s0=1.0, s1=1.04, dur=8.0, focus=None,
             astro_x=None, holo_h=300, dim=1.0, astro_on=True, holo_seed=0):
    img = blank()
    fx, fy = focus or (W * 0.45, H * 0.55)
    cam = Cam(fx, fy, s0 + (s1 - s0) * ease_io(t / dur))
    sb = space_bg(t, pan=(t * 3, 40))
    put(img, np.dstack([sb, np.ones((H, W, 1), np.float32)]), *cam.m(W / 2, H / 2), s=cam.s)
    pc = PQ["port_c"]
    earth(img, *cam.m(pc[0] + 40, pc[1] - 30), 2.2 * cam.s)
    cam.plate(img, load("plates/quarters.png"))
    img *= dim
    ax = astro_x if astro_x is not None else 470
    hb = PQ["holo_base"]
    if astro_on:
        lit = 0.75 + 0.25 * holo_op if holo else 0.75
        draw_astro(img, t, "sideL", *cam.m(ax, 1250), 920 * cam.s, expr=expr, look=look,
                   mul=(0.85 * lit * dim, 0.82 * lit * dim, 0.8 * lit * dim), rimc=CYAN, rims=0.9 * holo_op if holo else 0.25,
                   rimdir=(1, -0.2), shadow=0.0)
    if holo and holo_op > 0:
        draw_holo(img, t, holo, *cam.m(hb[0], hb[1] - 4), holo_h * cam.s, op=holo_op, seed=holo_seed)
    return img

def s_goodnight(t, T):
    hop = ramp(t, 0.8, 1.6) * (0.6 + 0.4 * (1 if t > 1.6 else (math.sin(t * 40) > 0)))
    fr = int((t * 6) % 4)
    expr = "HAPPY" if 2.6 < t < 7.5 else "NEUTRAL"
    return quarters(t, T, holo=f"holo_child_{fr}", holo_op=hop, expr=expr, s0=1.0, s1=1.08, dur=12, holo_h=300)

def s_wall_reveal(t, T):
    img = blank()
    dy = kf(t, [(0, -380), (6.5, 300)])
    cam = Cam(W / 2, H / 2, 1.25, 0, dy)
    cam.plate(img, load("plates/wallclose.png"))
    draw_marks(img, cam, PW, t)
    # the empty space above the last mark
    return img

def s_log_214(t, T):
    img = cockpit_wide(t, T, 1.18, 1.24, 8.0, focus=(W / 2, H * 0.55))
    tl = text_layer(["DAY 214 OF SILENCE"], size=30, path=FONT_MONO, color=AMBER)
    put(img, tl, 150, BAR + 60, anchor=(0, 0.5), op=ramp(t, 0.3, 1.0))
    if t > 5.6:
        tl2 = text_layer([typed("NO REPLY", t, 5.6, 14)], size=30, path=FONT_MONO, color=(1, 0.4, 0.3))
        put(img, tl2, 150, BAR + 105, anchor=(0, 0.5))
    return img

def s_log_215(t, T):
    img = space_bg(t, pan=(t * 3, -20), zoom=1.0)
    sun(img, 300, 420, 4, 0.8); earth(img, 330, 432, 1.8)
    sp = load("plates/ship_rear.png")
    put(img, sp, 1180 - t * 4, 600, s=0.16)
    tl = text_layer(["DAY 215"], size=30, path=FONT_MONO, color=AMBER)
    put(img, tl, 150, BAR + 60, anchor=(0, 0.5), op=ramp(t, 0.3, 1.0))
    if t > 4.0:
        tl2 = text_layer([typed("NO REPLY", t, 4.0, 14)], size=30, path=FONT_MONO, color=(1, 0.4, 0.3))
        put(img, tl2, 150, BAR + 105, anchor=(0, 0.5))
    return img

def s_press_play(t, T):
    img = blank(); screen_bg(img, t)
    tl = text_layer(["DAY 216"], size=30, path=FONT_MONO, color=AMBER); put(img, tl, 230, 220, anchor=(0, 0.5))
    lines = ["INCOMING TRANSMISSION", "ORIGIN ......... EARTH  /  DSN-14", "CLASS .......... FINAL VERIFIED SIGNAL", "ADDRESSED TO ... ASTRO"]
    cols = [AMBER, CYAN, (1.0, 0.45, 0.35), CYAN]
    for i, (l, c) in enumerate(zip(lines, cols)):
        put(img, text_layer([l], size=46, color=c), 230, 300 + i * 74, anchor=(0, 0))
    pressed = t > 3.0
    lab = "[  ▶  PLAYING  ]" if pressed else "[  ▶  PLAY  ]"
    b = text_layer([lab], size=54, path=FONT_MONO_B, color=CYAN if not pressed else (0.9, 1, 1))
    pulse = 1.0 if pressed else 0.65 + 0.35 * math.sin(t * 4)
    put(img, b, W / 2, 790, op=pulse)
    put(img, cv2.GaussianBlur(b, (0, 0), 10), W / 2, 790, op=pulse * (2.0 if 3.0 < t < 3.3 else 1.0), add=True)
    screen_post(img)
    y = kf(t, [(0, 1500), (2.2, 830), (3.0, 800), (3.4, 825), (5.0, 1500)])
    x = kf(t, [(0, 1400), (2.2, 990), (3.0, 985), (5.0, 1400)])
    glove(img, x, y, s=1.5, rot=160, mul=(0.75, 0.85, 1.0))
    if pressed: img *= 1 - 0.5 * ramp(t, 4.2, 5.0)
    return img

def s_holo_arrives(t, T):
    on = ramp(t, 0.6, 2.2)
    glitch = 1.0 if t > 2.2 else (1.0 if math.sin(t * 37) > -0.2 else 0.2)
    expr = "SURPRISED" if t < 4.0 else "NEUTRAL"
    return quarters(t, T, holo=teen_frame(T, 0), holo_op=on * glitch, expr=expr, s0=1.05, s1=1.14, dur=8,
                    focus=(W * 0.5, H * 0.5), holo_h=400, holo_seed=2)

def holo_close(t, T, pose=0, smile=False, s0=1.0, s1=1.04, dur=5.0, op=1.0, glitch=0.0, seed=3):
    img = blank()
    bg = _blurred("plates/quarters.png", 10)
    put(img, bg, W * 0.62, H * 0.62, s=1.9)
    img *= 0.42
    s = s0 + (s1 - s0) * ease_io(t / dur)
    name = teen_frame(T, pose, smile)
    g = glitch * (1 if math.sin(t * 53) > 0.3 else 0)
    jx = (40 * noise1(t, 7, 30)) * g
    draw_holo(img, t, name, W / 2 + jx, H * 1.03, 1050 * s, op=op * (1 - 0.6 * g), seed=seed, beam=False)
    if g:
        band = int((noise1(t, 9, 20) * 0.5 + 0.5) * H)
        img[max(band - 30, 0):band + 30] = np.roll(img[max(band - 30, 0):band + 30], int(80 * noise1(t, 11, 50)), axis=1)
    return img

def s_earth_dark(t, T):
    img = space_bg(t, pan=(0, 0)) * 0.7
    sun(img, 1700, 250, 7, 0.5)
    lo = 1.0 - ramp(t, 0.8, 3.6)
    earth(img, W * 0.47, H * 0.52, 300 + 10 * t, lights=2.2, lights_on=lo, seed=5, L=(-0.95, -0.15, 0.12))
    # satellites going dark: small dots around the planet
    for i in range(14):
        a = i * 2 * math.pi / 14 + t * 0.05
        x, y = W * 0.47 + math.cos(a) * 420, H * 0.52 + math.sin(a) * 140
        on = 1.0 if t < 0.8 + i * 0.18 else 0.0
        disc(img, x, y, 2.2, (0.7, 0.9, 1.0) if on else (0.15, 0.17, 0.2))
        if on: bloom_spot(img, x, y, 6, (0.5, 0.8, 1.0), 0.6)
    return img

def s_dish(t, T):
    img = space_bg(t, pan=(0, -200), zoom=1.0) * 0.8
    yy = np.arange(H, dtype=np.float32)[:, None]
    img += (np.clip((yy - 380) / 420, 0, 1) ** 1.5 * 0.55)[..., None] * np.array([0.10, 0.16, 0.32], np.float32)
    # hill + dish silhouette
    ground = np.zeros((H, W, 4), np.float32)
    pts = np.array([[0, 820], [500, 760], [900, 735], [1300, 770], [1920, 800], [1920, 1080], [0, 1080]], np.int32)
    cv2.fillPoly(ground, [pts], (0.01, 0.012, 0.02, 1), cv2.LINE_AA)
    cv2.ellipse(ground, (960, 560), (230, 120), -25, 0, 360, (0.015, 0.018, 0.028, 1), -1, cv2.LINE_AA)
    cv2.ellipse(ground, (960, 560), (218, 108), -25, 190, 350, (0.04, 0.05, 0.07, 1), 6, cv2.LINE_AA)
    cv2.line(ground, (960, 560), (1040, 740), (0.015, 0.018, 0.028, 1), 22, cv2.LINE_AA)
    cv2.line(ground, (900, 740), (1100, 740), (0.015, 0.018, 0.028, 1), 26, cv2.LINE_AA)
    cv2.line(ground, (960, 560), (1030, 470), (0.015, 0.018, 0.028, 1), 6, cv2.LINE_AA)
    put_full(img, ground)
    # the beam
    if t > 1.2:
        k = ramp(t, 1.2, 1.8) * (1 - 0.3 * ramp(t, 3, 3.5))
        beam = np.zeros((H, W), np.float32)
        cv2.line(beam, (1030, 470), (1030 + 900, -300), 1.0, 5, cv2.LINE_AA)
        b = cv2.GaussianBlur(beam, (0, 0), 3) * 1.2 + cv2.GaussianBlur(beam, (0, 0), 18) * 1.5
        img += (b * k)[..., None] * np.array(CYAN, np.float32)
        bloom_spot(img, 1030, 470, 40, CYAN, 0.6 * k)
    # candle-lit windows of a few houses
    for x in (220, 330, 1450, 1580, 1690):
        disc(img, x, 805 + (x % 7), 3, (1.0, 0.7, 0.35)); bloom_spot(img, x, 805, 10, (1.0, 0.6, 0.3), 0.25)
    return img

def s_alone_wide(t, T):
    z = kf(t, [(0, 1.0), (6.0, 0.62)])
    img = space_bg(t, pan=(0, 0), zoom=1.0)
    sp = load("plates/ship.png")
    put(img, sp, W * 0.5, H * 0.5, s=0.22 * z)
    bloom_spot(img, W * 0.5 + 120 * z, H * 0.5 - 40 * z, 6, (1, 0.3, 0.3), 0.6 * (math.sin(t * 3) > 0.6))
    return img

def s_launch(t, T):
    img = space_bg(t, pan=(t * 4, 0)) * 0.75
    sun(img, 300, 260, 6, 0.6)
    earth(img, W * 0.32, H * 0.6, 230, lights=2.2, lights_on=0.06, seed=5, L=(-0.95, -0.2, 0.15))
    if t > 0.6:
        u = ramp(t, 0.6, 4.0)
        x0, y0 = W * 0.32 + 170, H * 0.6 - 140
        x1, y1 = x0 + 1100 * u, y0 - 380 * u
        tr = np.zeros((H, W), np.float32)
        cv2.line(tr, (int(x0), int(y0)), (int(x1), int(y1)), 1.0, 2, cv2.LINE_AA)
        img += (cv2.GaussianBlur(tr, (0, 0), 2) * 0.6)[..., None] * np.array([1.0, 0.8, 0.6], np.float32)
        disc(img, x1, y1, 3, (1, 0.95, 0.85)); bloom_spot(img, x1, y1, 14, (1.0, 0.7, 0.4), 0.7)
    return img

def s_signal_end(t, T):
    img = quarters(t, T, holo=None, expr="SAD", look=(0.2, 0.4), s0=1.0, s1=1.03, dur=7.5, dim=0.85)
    tl = text_layer([typed("SIGNAL ENDED.", t, 1.0, 16)], size=30, path=FONT_MONO, color=(1, 0.45, 0.35))
    put(img, tl, 150, BAR + 60, anchor=(0, 0.5))
    tl2 = text_layer([typed("ATTACHMENT:  TRAJECTORY.DAT", t, 2.6, 22)], size=30, path=FONT_MONO, color=CYAN)
    put(img, tl2, 150, BAR + 105, anchor=(0, 0.5))
    return img

def s_map(t, T):
    img = blank(); screen_bg(img, t, (0.015, 0.03, 0.05))
    cx, cy = 560, 600
    ov = np.zeros((H, W), np.float32)
    for r in (50, 85, 125, 190, 300, 400, 500):
        cv2.ellipse(ov, (cx, cy), (r, int(r * 0.42)), 0, 0, 360, 0.5, 1, cv2.LINE_AA)
    img += ov[..., None] * np.array([0.1, 0.35, 0.5], np.float32)
    sun(img, cx, cy, 8, 0.8)
    earth(img, cx + 85, cy - 8, 3.5)
    put(img, text_layer(["EARTH"], 20, FONT_MONO, (0.5, 0.7, 1)), cx + 85, cy - 30, op=0.8)
    nx, ny = cx + 500 * math.cos(-0.6), cy + 500 * 0.42 * math.sin(-0.6)
    disc(img, nx, ny, 9, (0.35, 0.55, 1.0)); put(img, text_layer(["NEPTUNE"], 22, FONT_MONO, (0.5, 0.7, 1)), nx - 20, ny - 34, anchor=(0.5, 0.5))
    kx, ky = cx + 280, cy + 190
    disc(img, kx, ky, 6, AMBER); put(img, text_layer(["KESTREL"], 22, FONT_MONO, AMBER), kx + 14, ky + 4, anchor=(0, 0.5))
    ox, oy = nx + 40 + 3 * t, ny + 36
    blink = 1.0 if (t * 2) % 1 < 0.6 else 0.3
    disc(img, ox, oy, 6, RED, op=blink); bloom_spot(img, ox, oy, 16, RED, 0.5 * blink)
    if t > 2.0:
        u = ramp(t, 2.0, 5.0)
        pts = [(kx + (ox - kx) * (i / 60), ky + (oy - ky) * (i / 60) - math.sin(i / 60 * math.pi) * 60) for i in range(int(60 * u) + 1)]
        for i in range(0, len(pts) - 1, 2):
            cv2.line(img, (int(pts[i][0]), int(pts[i][1])), (int(pts[i + 1][0]), int(pts[i + 1][1])), AMBER, 2, cv2.LINE_AA)
    lines = ["OBJECT ....... UNKNOWN", "STATUS ....... DRIFTING, NO ENGINES", "LIFE SIGNS ... FAINT", "INTERCEPT .... 41 DAYS"]
    cols = [CYAN, CYAN, (1, 0.45, 0.35), AMBER]
    draw_ui(img, ui_panel(lines, t, cols, size=32, x=1160, y=380, t_starts=[0.5, 1.6, 2.8, 5.2], cps=30), glow_k=0.6)
    screen_post(img)
    return img

def s_decide(t, T):
    return cockpit_wide(t, T, 1.12, 1.2, 7.0, focus=(W * 0.55, H * 0.42), earth_r=3.6, earth_glint=0.15 * ramp(t, 1, 4))

def s_burn(t, T):
    img = space_bg(t, pan=(t * 30 * ramp(t, 2, 7), 0))
    sun(img, 260, 300, 5, 0.6)
    on = ramp(t, 0.8, 2.0)
    x = W * 0.45 + 900 * ramp(t, 2.5, 7.5) ** 2
    s = 0.48 - 0.25 * ramp(t, 2.5, 7.5)
    sp0 = load("plates/ship.png"); sp1 = load("plates/ship_burn.png")
    shake = 3 * on * noise1(t, 2, 25)
    put(img, sp0, x, H / 2 + shake, s=s, op=1 - on)
    put(img, sp1, x, H / 2 + shake, s=s, op=on)
    # exhaust plume
    if on > 0:
        ex, ey = x - 0.36 * 1800 * s, H / 2 + 40 * s + shake
        for k, (r, c, a) in enumerate([(90, (0.4, 0.8, 1.0), 0.8), (260, (0.3, 0.55, 1.0), 0.35), (600, (0.25, 0.4, 0.9), 0.1)]):
            bloom_spot(img, ex - 60 * s, ey, r * s * 2, c, a * on)
    return img

def s_travel(t, T):
    img = space_bg(t, pan=(t * 12, 0))
    nep = load("plates/neptune.png")
    put(img, nep, W * 0.72, H * 0.45, s=0.06 + 0.33 * ramp(t, 0, 10) ** 1.6)
    sp = load("plates/ship_burn.png")
    put(img, sp, W * 0.32 + t * 18, H * 0.62, s=0.17)
    bloom_spot(img, W * 0.32 + t * 18 - 140, H * 0.62 + 10, 18, (0.4, 0.8, 1.0), 0.6)
    day = int(1 + 40 * ramp(t, 0.5, 9.0))
    tl = text_layer([f"DAY {day:02d} / 41"], size=30, path=FONT_MONO, color=AMBER)
    put(img, tl, 150, BAR + 60, anchor=(0, 0.5))
    return img

def s_neptune(t, T):
    img = space_bg(t, pan=(t * 4, 0)) * 0.8
    nep = load("plates/neptune.png")
    put(img, nep, W * 0.55, H * 1.02, s=1.15 + 0.02 * t)
    ox, oy = W * 0.66 - t * 3, H * 0.3
    blink = 1.0 if (t * 1.2) % 1 < 0.25 else 0.0
    disc(img, ox, oy, 3.5, (0.85, 0.9, 1.0)); bloom_spot(img, ox, oy, 14, RED, 1.4 * blink)
    if t > 2.0:
        k = ramp(t, 2.0, 2.6)
        r = 60 - 20 * k
        box = np.zeros((H, W), np.float32)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx, cy = int(ox + dx * r), int(oy + dy * r)
            cv2.line(box, (cx, cy), (cx - dx * 16, cy), 1.0, 2, cv2.LINE_AA); cv2.line(box, (cx, cy), (cx, cy - dy * 16), 1.0, 2, cv2.LINE_AA)
        img += (box * k)[..., None] * np.array(AMBER, np.float32)
        put(img, text_layer([typed("OBJECT ACQUIRED", t, 2.6, 18)], 26, FONT_MONO, AMBER), ox + 60, oy - 50, anchor=(0, 0.5))
    sp = load("plates/ship_rear.png")
    put(img, sp, W * 0.25 + t * 6, H * 0.5, s=0.3)
    return img

@functools.lru_cache(maxsize=1)
def beacon_pos():
    p = load("plates/pod_space.png")
    r, g, b, a = [p[..., i] for i in range(4)]
    m = (r > 0.6) & (g < 0.35) & (a > 0.5)
    ys, xs = np.where(m)
    return (float(xs.mean()), float(ys.mean())) if len(xs) else (p.shape[1] * 0.35, p.shape[0] * 0.3)

def s_pod_tumble(t, T):
    img = space_bg(t, pan=(t * 2, 0)) * 0.9
    nep = load("plates/neptune.png")
    put(img, nep, W * 0.12, H * 1.15, s=1.6)
    pod = load("plates/pod_space.png")
    rot = -8 + t * 2.2
    cx, cy = W * 0.55, H * 0.5
    put(img, pod, cx, cy, s=0.95, rot=rot)
    bx, by = beacon_pos(); ph, pw = pod.shape[:2]
    dx, dy = (bx - pw / 2) * 0.95, (by - ph / 2) * 0.95
    a = math.radians(rot)
    px, py = cx + dx * math.cos(a) + dy * math.sin(a), cy - dx * math.sin(a) + dy * math.cos(a)
    blink = 1.0 if (t * 0.8) % 1 < 0.12 else 0.0
    bloom_spot(img, px, py, 30, RED, 1.0 * blink)
    ls = text_layer(["LIFE SUPPORT   3%"], 34, FONT_MONO_B, (1, 0.35, 0.3))
    k = (0.7 + 0.3 * math.sin(t * 6)) * ramp(t, 1.5, 2.0)
    put(img, ls, 150, BAR + 60, anchor=(0, 0.5), op=k)
    put(img, cv2.GaussianBlur(ls, (0, 0), 8), 150, BAR + 60, anchor=(0, 0.5), op=k, add=True)
    return img

def s_tether(t, T):
    img = space_bg(t, pan=(t * 2, 0))
    nep = load("plates/neptune.png")
    put(img, nep, W * 0.85, H * 1.2, s=1.3)
    sp = load("plates/ship.png")
    put(img, sp, W * 0.28, H * 0.5, s=0.5)
    pod = load("plates/pod_space.png")
    u = ramp(t, 2.5, 6.5)
    px, py = W * 0.82 - 520 * u, H * 0.42 + 40 * u
    put(img, pod, px, py, s=0.32 - 0.04 * u, rot=12 - 12 * u)
    if t > 0.8:
        k = ramp(t, 0.8, 2.2)
        sx, sy = W * 0.28 + 220, H * 0.5 + 20
        ex, ey = sx + (px - 60 - sx) * k, sy + (py - sy) * k
        cv2.line(img, (int(sx), int(sy)), (int(ex), int(ey)), (0.6, 0.62, 0.66), 3, cv2.LINE_AA)
    return img

def cargo(t, T, expr="CURIOUS", look=(0.3, 0.2), s0=1.0, s1=1.05, dur=8, pod_glow=0.0, astro_on=True, frost_plate=1.0):
    img = blank()
    cam = Cam(W * 0.5, H * 0.55, s0 + (s1 - s0) * ease_io(t / dur))
    cam.plate(img, load("plates/cargo.png"))
    pw = PCG["pod_win"]
    if pod_glow > 0:
        bloom_spot(img, *cam.m(pw[0], pw[1]), 140 * cam.s, (1.0, 0.75, 0.45), 0.35 * pod_glow)
        bloom_spot(img, *cam.m(pw[0], pw[1] + 60), 300 * cam.s, (1.0, 0.65, 0.4), 0.12 * pod_glow)
    if astro_on:
        draw_astro(img, t, "front34", *cam.m(1380, 1300), 1000 * cam.s, expr=expr, look=look,
                   mul=(0.8, 0.83, 0.9), rimc=(1.0, 0.75, 0.5) if pod_glow else (0.7, 0.85, 1.0),
                   rims=0.5 + 0.5 * pod_glow, rimdir=(-1, -0.2), shadow=0.0)
    return img

def s_cargo_arrive(t, T): return cargo(t, T, "CURIOUS", (-0.4, 0.2), 1.0, 1.06, 8)

@functools.lru_cache(maxsize=1)
def podwin_layer():
    p = load("plates/podwindow.png")
    p = cv2.rotate(p, cv2.ROTATE_180)
    lum = p[..., :3].mean(2); a = p[..., 3]
    m = ((lum < 0.06) & (a > 0.9)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = stats[i, :4]
    glass = (lab == i).astype(np.float32)
    glass = cv2.GaussianBlur(glass, (0, 0), 1.5)
    return p, (x, y, w, h), glass

@functools.lru_cache(maxsize=1)
def hand_layer(w=520, h=640):
    """a child's hand pressed against glass from inside, lit warm."""
    SS = 2; img = np.zeros((h * SS, w * SS), np.uint8)
    cx, cy = w * SS // 2, int(h * SS * 0.62)
    cv2.ellipse(img, (cx, cy), (int(w * SS * 0.27), int(h * SS * 0.24)), 0, 0, 360, 255, -1, cv2.LINE_AA)
    fingers = [(-0.19, -0.30, 0.055, 0.18, -12), (-0.065, -0.40, 0.058, 0.22, -4), (0.065, -0.41, 0.058, 0.23, 3),
               (0.185, -0.33, 0.053, 0.19, 10), (-0.33, -0.02, 0.06, 0.16, -55)]
    for fx, fy, rw, rh, ang in fingers:
        cv2.ellipse(img, (int(cx + fx * w * SS), int(cy + fy * h * SS)), (int(rw * w * SS), int(rh * h * SS)), ang, 0, 360, 255, -1, cv2.LINE_AA)
    cv2.rectangle(img, (int(cx - w * SS * 0.2), cy), (int(cx + w * SS * 0.2), h * SS), 255, -1, cv2.LINE_AA)
    a = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    a = cv2.GaussianBlur(a, (0, 0), 2.5)
    inner = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8), iterations=10), (0, 0), 12)
    col = np.dstack([0.78 * (0.55 + 0.45 * inner), 0.55 * (0.55 + 0.45 * inner), 0.45 * (0.55 + 0.45 * inner)])
    fade = np.clip(np.linspace(1.6, -0.2, h), 0, 1)[:, None]
    a = a * fade
    return np.dstack([col * a[..., None], a]).astype(np.float32)

def podwindow(t, T, frost=1.0, glow=0.0, name_op=0.0, hand=0.0, glove_on=0.0, s0=1.0, s1=1.04, dur=6.0, unreadable=False):
    img = blank()
    p, (x, y, w, h), glass = podwin_layer()
    fit = (W * 0.6) / w
    cam = Cam(x + w / 2, y + h / 2, fit * (s0 + (s1 - s0) * ease_io(t / dur)), W / 2 - (x + w / 2), H * 0.42 - (y + h / 2))
    # interior behind glass: warm when powered
    inside = np.zeros((H, W, 3), np.float32)
    if glow > 0:
        bloom_spot(inside, *cam.m(x + w * 0.5, y + h * 0.6), w * 0.4 * cam.s, (1.0, 0.7, 0.45), 0.5 * glow)
    if hand > 0:
        hl = hand_layer()
        put(inside, hl, *cam.m(x + w * 0.52, y + h * 0.95), s=(h * 1.05 / hl.shape[0]) * cam.s, op=hand, anchor=(0.5, 1.0))
    bg = _blurred("plates/cargo.png", 16)
    put(img, bg, W / 2, H / 2, s=1.3); img *= 0.5
    cam.plate(img, p)
    gm = np.zeros((H, W, 3), np.float32); cam.plate(gm, np.dstack([glass] * 3 + [glass]))
    gmask = gm[..., 0:1]
    img += inside * gmask
    # frost on glass
    if frost > 0.01:
        fl = frost_layer(int(w), int(h), frost)
        fl = fl * glass[y:y + h, x:x + w, None]
        X, Y = cam.m(x, y)
        put(img, fl, X, Y, s=cam.s, anchor=(0, 0))
        if glow > 0: put(img, fl, X, Y, s=cam.s, anchor=(0, 0), op=0.35 * glow, add=True)
    # name label on the hull above the window
    lx, ly = cam.m(x + w / 2, y - 0.14 * h)
    lab = np.zeros((84, 860, 4), np.float32)
    cv2.rectangle(lab, (0, 0), (859, 83), (0.16, 0.18, 0.22, 1), -1)
    cv2.rectangle(lab, (6, 6), (853, 77), (0.45, 0.48, 0.52, 1), 2)
    put(img, lab, lx, ly, s=cam.s)
    put(img, text_layer(["PASSENGER:"], 30, FONT_MONO_B, (0.75, 0.78, 0.8)), lx - 400 * cam.s, ly, s=cam.s, anchor=(0, 0.5))
    if name_op > 0:
        tl = text_layer(["NOOR A.  ·  AGE 14"], 34, FONT_MONO_B, (1.0, 0.85, 0.6))
        put(img, tl, lx - 150 * cam.s, ly, s=cam.s, op=name_op, anchor=(0, 0.5))
    put(img, frost_layer(560, 76, 1 - name_op), lx + 140 * cam.s, ly, s=cam.s)
    if glove_on > 0:
        gx, gy = cam.m(x + w * 0.52, y + h * 0.42)
        glove(img, gx + (1 - glove_on) * 200, gy + (1 - glove_on) * 500, s=2.0 * cam.s, rot=180, op=min(1, glove_on * 2),
              mul=(0.78, 0.8, 0.85), anchor=(0.45, 0.62))
    return img

def s_podwin_frozen(t, T):
    img = podwindow(t, T, frost=1.0, unreadable=True, s0=1.0, s1=1.06, dur=6)
    return img

def s_power_dialog(t, T):
    img = blank(); screen_bg(img, t, (0.04, 0.015, 0.015))
    lines = ["SHIP POWER ............. 11%", "POD LIFE SUPPORT ....... NEEDS 9%", "MEMORY ARCHIVE ......... NEEDS 4%"]
    draw_ui(img, ui_panel(lines, t, [AMBER, (1, 0.45, 0.35), CYAN], size=38, x=230, y=230, t_starts=[0.3, 1.1, 1.9], cps=40), glow_k=0.5)
    if t > 3.2:
        k = ramp(t, 3.2, 3.6)
        box = np.zeros((H, W), np.float32)
        cv2.rectangle(box, (330, 520), (1590, 900), 1.0, 2, cv2.LINE_AA)
        img += (box * k)[..., None] * np.array((1, 0.45, 0.35), np.float32)
        q = ["TRANSFER ALL POWER TO POD?", "ARCHIVE WILL BE ERASED:  4,012 MESSAGES", "THIS CANNOT BE UNDONE."]
        draw_ui(img, ui_panel(q, t, [WHITE, (1, 0.55, 0.45), (1, 0.55, 0.45)], size=40, x=400, y=570, t_starts=[3.6, 4.6, 6.0], cps=38, cursor=False), glow_k=0.4)
        if t > 7.0:
            put(img, text_layer(["[ CONFIRM ]        [ CANCEL ]"], 40, FONT_MONO_B, CYAN), W / 2, 850, op=ramp(t, 7.0, 7.4))
    if (t * 1.5) % 1 < 0.5 and t > 3.2:
        img += np.array([0.03, 0.0, 0.0], np.float32)
    screen_post(img)
    return img

def s_last_play(t, T):
    fr = int((t * 6) % 4)
    hop = ramp(t, 0.5, 1.2)
    return quarters(t, T, holo=f"holo_child_{fr}", holo_op=hop, expr="SAD", look=(0.5, 0.1), s0=1.12, s1=1.2, dur=8,
                    focus=(W * 0.42, H * 0.6), holo_h=300, dim=0.8)

def s_touch_wall(t, T):
    img = blank()
    cam = Cam(W / 2, H / 2, 1.25, 0, 300)
    cam.plate(img, load("plates/wallclose.png"))
    img *= 0.85
    draw_marks(img, cam, PW, t)
    y13 = wall_y(MARKS[-1][0], PW)
    gx, gy = cam.m(PW["wall_bl"][0] + 120, y13)
    glove(img, kf(t, [(0, gx + 500), (2.0, gx + 40), (5.0, gx + 30)]), kf(t, [(0, gy + 600), (2.0, gy - 20), (5.0, gy - 25)]),
          s=2.2, rot=170, mul=(0.78, 0.78, 0.82))
    return img

def s_confirm(t, T):
    img = blank(); screen_bg(img, t, (0.04, 0.015, 0.015))
    q = ["TRANSFER ALL POWER TO POD?", "ARCHIVE WILL BE ERASED:  4,012 MESSAGES", "THIS CANNOT BE UNDONE."]
    for i, (l, c) in enumerate(zip(q, [WHITE, (1, 0.55, 0.45), (1, 0.55, 0.45)])):
        put(img, text_layer([l], 40, color=c), 400, 570 + i * 64, anchor=(0, 0))
    pressed = t > 2.6
    b = text_layer(["[ CONFIRM ]"], 40, FONT_MONO_B, (1, 1, 1) if pressed else CYAN)
    put(img, b, W / 2 - 230, 850)
    put(img, text_layer(["[ CANCEL ]"], 40, FONT_MONO_B, CYAN), W / 2 + 250, 850, op=0.6)
    if pressed: put(img, cv2.GaussianBlur(b, (0, 0), 10), W / 2 - 230, 850, add=True, op=1.5 * (1 - ramp(t, 2.6, 3.4)))
    screen_post(img)
    y = kf(t, [(0, 1500), (1.6, 875), (2.6, 855), (2.8, 875), (4.0, 1500)])
    glove(img, kf(t, [(0, 1100), (1.6, 745), (4.0, 1100)]), y, s=1.5, rot=160, mul=(0.75, 0.85, 1.0))
    img *= 1 - 0.85 * ramp(t, 3.0, 4.0)
    return img

def s_erase_holo(t, T):
    fr = int((t * 6) % 4)
    op = (1 - ramp(t, 0.5, 3.5))
    dim = 0.8 - 0.35 * ramp(t, 0.5, 4.0)
    img = quarters(t, T, holo=f"holo_child_{fr}", holo_op=op * (1 if math.sin(t * 61) > -0.5 else 0.3), expr="SAD", look=(0.5, 0.2),
                   s0=1.2, s1=1.22, dur=5, focus=(W * 0.42, H * 0.6), holo_h=300, dim=dim, holo_seed=8)
    # dissolving particles drifting up from the hologram
    rng = np.random.default_rng(3)
    hb = PQ["holo_base"]
    cam = Cam(W * 0.42, H * 0.6, 1.2 + 0.02 * t / 5)
    bx, by = cam.m(hb[0], hb[1])
    k = ramp(t, 0.5, 2.0) * (1 - ramp(t, 3.5, 5))
    for i in range(160):
        px = bx + (rng.random() - 0.5) * 220 + noise1(t, i, 0.7) * 20
        py = by - rng.random() * 360 - (t * 40 * (0.5 + rng.random()))
        disc(img, px, py, 1.6, CYAN, op=k * rng.random(), add=True)
    return img

def s_erase_wall(t, T):
    img = blank()
    cam = Cam(W / 2, H / 2, 1.25, 0, kf(t, [(0, 300), (6.0, -250)]))
    cam.plate(img, load("plates/wallclose.png"))
    img *= 0.8 - 0.25 * ramp(t, 0, 6)
    n = len(MARKS)
    def vis(i):
        k = n - 1 - i                         # top mark erases first
        t_off = 0.35 + k * 0.42
        return 1 - ramp(t, t_off, t_off + 0.5)
    draw_marks(img, cam, PW, t, visible=vis)
    cnt = int(4012 * (1 - ramp(t, 0.3, 5.0)))
    put(img, text_layer([f"ARCHIVE  {cnt:,}"], 30, FONT_MONO, CYAN), 150, BAR + 60, anchor=(0, 0.5), op=0.9)
    return img

def s_pod_wake(t, T):
    img = cargo(t, T, "SAD", (-0.4, 0.2), 1.06, 1.1, 7, pod_glow=ramp(t, 1.0, 5.0))
    pct = int(3 + 37 * ramp(t, 1.5, 6.5))
    col = (1, 0.45, 0.35) if pct < 15 else ((1, 0.75, 0.35) if pct < 30 else (0.45, 1, 0.6))
    put(img, text_layer([f"POD LIFE SUPPORT   {pct}%"], 30, FONT_MONO_B, col), 150, BAR + 60, anchor=(0, 0.5))
    return img

def s_frost_melt(t, T):
    return podwindow(t, T, frost=1 - 0.8 * ramp(t, 0.5, 8.0), glow=0.6 + 0.4 * ramp(t, 0, 4), name_op=ramp(t, 5.0, 8.0), s0=1.0, s1=1.05, dur=9)

def s_helmet_realize(t, T): return helmet_close(t, T, "SURPRISED", look=(0, 0.2), dur=4.0, push=(1.04, 1.1), warm=True, glow_side=1, tremble=0.4)

def s_hand(t, T):
    return podwindow(t, T, frost=0.2, glow=1.0, name_op=1.0, hand=ramp(t, 0.6, 2.4), glove_on=ramp(t, 3.4, 6.0),
                     s0=1.08, s1=1.16, dur=8)

def s_helmet_reply(t, T): return helmet_close(t, T, "HAPPY" if t > 1.4 else "SURPRISED", look=(0, 0.2), dur=6.0, push=(1.1, 1.14), warm=True, glow_side=1, tremble=0.6 if t > 1.4 else 0.2)

def s_height_line(t, T):
    return podwindow(t, T, frost=0.2, glow=1.0, name_op=1.0, hand=1.0, glove_on=1.0, s0=1.16, s1=1.2, dur=5)

def s_new_mark(t, T):
    img = blank()
    cam = Cam(W / 2, H / 2, 1.25, 0, 420)
    cam.plate(img, load("plates/wallclose.png"))
    img *= 0.62 + 0.25 * ramp(t, 0, 2)
    prog = ramp(t, 2.0, 4.0)
    draw_marks(img, cam, PW, t, visible=lambda i: 0.0, new_mark=(1.66, "14 · IN PERSON", prog))
    y = wall_y(1.66, PW)
    xl, xr = PW["wall_bl"][0], PW["wall_br"][0]
    gx, gy = cam.m(xl + (xr - xl) * (0.05 + 0.8 * prog), y)
    glove(img, kf(t, [(0, gx + 400), (1.8, gx + 20), (4.0, gx + 20), (6, gx + 600)]),
          kf(t, [(0, gy + 600), (1.8, gy - 10), (4.0, gy - 10), (6, gy + 700)]), s=2.0, rot=170, mul=(0.85, 0.82, 0.8))
    return img

def s_home(t, T):
    img = space_bg(t, pan=(t * -3, 0))
    sun(img, W * 0.5 + 90, H * 0.4 - 30, 5, 0.6)
    earth(img, W * 0.5, H * 0.4, 5.0)
    bloom_spot(img, W * 0.5, H * 0.4, 22, (0.3, 0.55, 1.0), 0.5)
    sp = load("plates/ship_rear.png")
    put(img, sp, W * 0.5 - 60 + 40 * ease(t / 9), H * 0.62 - 30 * ease(t / 9), s=0.5 - 0.12 * ease(t / 9))
    bloom_spot(img, W * 0.5 - 60 + 40 * ease(t / 9), H * 0.62 + 90, 30, (0.4, 0.8, 1.0), 0.3 * ramp(t, 5, 6))
    return img

def s_end(t, T):
    img = space_bg(t, pan=(t * 3, 0)) * 0.4
    a = text_layer(["THE LAST MESSAGE EARTH EVER SENT"], 46, FONT_THIN, (0.92, 0.92, 0.92), tracking=12)
    b = text_layer(["WEIGHED 46 KILOGRAMS."], 46, FONT_LIGHT, (1.0, 0.82, 0.6), tracking=12)
    put(img, a, W / 2, H / 2 - 40, op=ramp(t, 0.8, 2.4) * (1 - ramp(t, 8.6, 10)))
    put(img, b, W / 2, H / 2 + 40, op=ramp(t, 3.4, 5.0) * (1 - ramp(t, 8.6, 10)))
    c = text_layer(["LONELY ASTRONAUT"], 26, FONT_LIGHT, (0.7, 0.75, 0.8), tracking=10)
    put(img, c, W / 2, H / 2, op=ramp(t, 10.5, 11.5) * (1 - ramp(t, 13.5, 14.5)))
    return img

# ================================================================= TIMELINE
# (name, dur, fn, audio cues [(offset, cue, gain)], captions [(offset, dur, text)])
SHOTS = [
    ("incoming", 10.0, s_incoming, [(1.2, "ping", 0.8), (1.2, "type", 0.5), (2.8, "type", 0.5), (4.4, "type", 0.5), (6.2, "type", 0.5), (7.6, "beep", 0.4)], []),
    ("helmet_surprised", 5.0, s_helmet_surprised, [(0.4, "heartbeat", 0.3)], []),
    ("glove_hover", 4.5, s_glove_hover, [(1.4, "servo", 0.2)], []),
    ("helmet_sad", 3.5, s_helmet_sad_down, [], []),
    ("title", 8.0, s_title, [], []),
    ("ship_alone", 8.0, s_ship_alone, [], []),
    ("cockpit_intro", 7.0, s_cockpit_intro, [], []),
    ("goodnight", 12.0, s_goodnight, [(0.8, "holo_on", 0.5), (2.2, "VO:noor_0:child", 1.0)], [(2.2, 3.0, "Goodnight, Dad! Come home before I get tall!")]),
    ("wall_reveal", 7.0, s_wall_reveal, [], []),
    ("log_214", 8.0, s_log_214, [(1.0, "radio_click", 0.5), (1.2, "VO:astro_0:radio", 1.0), (5.5, "static", 0.35)], [(1.2, 4.1, "Kestrel to Earth. Day two hundred and fourteen. Still here.")]),
    ("log_215", 6.0, s_log_215, [(0.6, "radio_click", 0.5), (0.8, "VO:astro_1:radio", 1.0), (3.9, "static", 0.3)], [(0.8, 3.0, "Kestrel to Earth... Day two hundred and fifteen.")]),
    ("press_play", 5.0, s_press_play, [(0.2, "ping", 0.6), (3.0, "click", 0.35)], []),
    ("holo_arrives", 8.0, s_holo_arrives, [(0.6, "holo_on", 0.7), (2.4, "VO:noor_1", 1.0)], [(2.4, 5.5, "Hi, Dad. It's me. I'm fourteen now, so... don't freak out about the height.")]),
    ("holo_a", 5.2, lambda t, T: holo_close(t, T, 0, dur=5.2), [(0.3, "VO:noor_2", 1.0)], [(0.3, 4.9, "The sun had a really bad day.")]),
    ("earth_dark", 4.6, s_earth_dark, [(0.8, "powerdown_far", 0.35)], [(0.0, 4.6, "Every satellite went dark in one night. No power, no phones, nothing.")]),
    ("holo_b", 4.6, lambda t, T: holo_close(t, T, 1, dur=4.6, s0=1.04, s1=1.08), [], [(0.0, 3.6, "We're okay down here. Cold, and dark... but okay.")]),
    ("holo_c", 4.4, lambda t, T: holo_close(t, T, 2, dur=4.4), [(0.4, "VO:noor_3", 1.0)], [(0.4, 4.0, "They got one big dish working.")]),
    ("dish", 4.0, s_dish, [(1.2, "beam", 0.4)], [(0.0, 4.0, "Enough power for one last message, for the whole planet.")]),
    ("helmet_listen", 4.4, lambda t, T: helmet_close(t, T, "CURIOUS", dur=4.4, push=(1.02, 1.06)), [], [(0.0, 3.6, "People fought about it for weeks. What to say. Who to send it to.")]),
    ("alone_wide", 6.0, s_alone_wide, [(0.4, "VO:noor_4", 1.0)], [(0.4, 4.5, "Then somebody pointed out there's only one person left out there to hear it.")]),
    ("holo_smile", 3.6, lambda t, T: holo_close(t, T, 3, smile=True, dur=3.6, s0=1.06, s1=1.1), [(0.5, "VO:noor_5", 1.0)], [(0.5, 2.1, "So... it's yours.")]),
    ("helmet_moved", 5.0, lambda t, T: helmet_close(t, T, "SAD", dur=5.0, push=(1.04, 1.1), tremble=0.5), [], []),
    ("launch", 4.4, s_launch, [(0.4, "VO:noor_6", 1.0), (0.6, "launch_far", 0.3)], [(0.4, 4.0, "We launched the last thing we could launch.")]),
    ("holo_d", 4.2, lambda t, T: holo_close(t, T, 2, dur=4.2, s0=1.04, s1=1.1), [], [(0.0, 3.6, "It's slow, and it's cold, and it can't steer. Mom packed it herself.")]),
    ("holo_e", 5.4, lambda t, T: holo_close(t, T, 0, dur=5.4, s0=1.08, s1=1.16, glitch=ramp(t, 3.2, 4.3), op=1 - ramp(t, 4.4, 4.6)),
     [(0.4, "VO:noor_7:cut", 1.0), (4.45, "static_burst", 0.6)], [(0.4, 4.0, "Coordinates are in the file. Please catch it, Dad. Please don't let it—")]),
    ("signal_end", 7.5, s_signal_end, [(1.0, "beep_low", 0.4)], []),
    ("map", 9.0, s_map, [(0.5, "type", 0.4), (1.6, "type", 0.4), (2.8, "type", 0.4), (5.2, "type", 0.4)], []),
    ("decide", 7.0, s_decide, [(3.2, "VO:astro_2", 1.0)], [(3.2, 1.9, "Okay, kid. I'm coming.")]),
    ("burn", 8.0, s_burn, [(0.8, "engine", 0.5)], []),
    ("travel", 10.0, s_travel, [], []),
    ("neptune", 8.0, s_neptune, [(2.6, "beep", 0.4)], []),
    ("pod_tumble", 8.0, s_pod_tumble, [(1.5, "alarm_soft", 0.35)], []),
    ("tether", 7.0, s_tether, [(0.8, "winch", 0.5), (6.3, "clunk", 0.8)], []),
    ("cargo_arrive", 7.0, s_cargo_arrive, [(0.3, "hiss", 0.3)], []),
    ("podwin_frozen", 6.0, s_podwin_frozen, [(0.5, "frost", 0.3)], []),
    ("power_dialog", 9.0, s_power_dialog, [(0.3, "type", 0.4), (3.2, "alarm_soft", 0.3)], []),
    ("last_play", 8.0, s_last_play, [(0.5, "holo_on", 0.4), (1.6, "VO:noor_0:child", 0.9)], [(1.6, 3.0, "Goodnight, Dad! Come home before I get tall!")]),
    ("touch_wall", 5.0, s_touch_wall, [], []),
    ("confirm", 4.5, s_confirm, [(2.6, "click", 0.35)], []),
    ("erase_holo", 5.0, s_erase_holo, [(0.4, "powerdown", 0.7)], []),
    ("erase_wall", 7.0, s_erase_wall, [], []),
    ("pod_wake", 7.0, s_pod_wake, [(0.8, "powerup", 0.5)], []),
    ("frost_melt", 9.0, s_frost_melt, [(0.5, "melt", 0.35)], []),
    ("helmet_realize", 4.0, s_helmet_realize, [(0.2, "heartbeat", 0.3)], []),
    ("hand", 8.0, s_hand, [(1.0, "knock_soft", 0.6), (5.4, "glass_touch", 0.5)], []),
    ("helmet_reply", 6.0, s_helmet_reply, [(0.3, "VO:noor_8:muffled", 1.0), (1.4, "VO:noor_9:muffled", 1.0), (3.8, "VO:astro_3", 1.0)],
     [(0.3, 0.8, "Dad?"), (1.4, 1.5, "Did you get my message?"), (3.8, 1.3, "Yeah. I got it.")]),
    ("height_line", 5.0, s_height_line, [(0.6, "VO:noor_10:muffled", 1.0)], [(0.6, 2.8, "I told you not to freak out about the height.")]),
    ("new_mark", 6.5, s_new_mark, [(2.0, "marker", 0.6)], []),
    ("home", 9.0, s_home, [(2.0, "radio_click", 0.5), (2.2, "VO:astro_4:radio", 1.0), (5.5, "engine_soft", 0.4)], [(2.2, 3.3, "Kestrel to Earth. Two passengers. Coming home.")]),
    ("end", 15.0, s_end, [], []),
]

def timeline():
    out, T = [], 0.0
    for name, dur, fn, cues, caps in SHOTS:
        out.append(dict(name=name, start=T, dur=dur, fn=fn, cues=cues, caps=caps))
        T += dur
    return out, T

if __name__ == "__main__":
    tl, total = timeline()
    for s in tl: print(f"{s['start']:7.2f} {s['dur']:5.1f} {s['name']}")
    print("TOTAL", total)
