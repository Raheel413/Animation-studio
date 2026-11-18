"""Compositing engine: premultiplied float32 RGBA layers, 1920x1080 @ 24 fps."""
import json, math, os, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 24
ROOT = "/home/claude/film"
BAR = 132                     # 2.39:1 letterbox bars
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_THIN = "/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf"
FONT_LIGHT = "/usr/share/fonts/opentype/inter/Inter-Light.otf"
FONT_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
FONT_MED = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

CYAN = (0.22, 0.74, 0.97); AMBER = (1.0, 0.70, 0.28); RED = (1.0, 0.25, 0.2)
ICE = (0.72, 0.95, 1.0); WHITE = (1, 1, 1)

# ------------------------------------------------------------------ timing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x):
    x = clamp(x); return x * x * (3 - 2 * x)
def ease_io(x):
    x = clamp(x); return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2
def ramp(t, t0, t1): return ease((t - t0) / max(t1 - t0, 1e-6))
def lin(t, t0, t1): return clamp((t - t0) / max(t1 - t0, 1e-6))
def kf(t, keys, fn=ease_io):
    """keys: [(time, value or tuple)]"""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = fn((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]

def noise1(t, seed=0, speed=1.0):
    """smooth 1D value noise in [-1,1]"""
    x = t * speed + seed * 17.13
    i = math.floor(x); f = x - i
    def h(n): return (math.sin(n * 127.1 + seed * 311.7) * 43758.5453) % 1.0 * 2 - 1
    u = f * f * (3 - 2 * f)
    return h(i) * (1 - u) + h(i + 1) * u

# ------------------------------------------------------------------ images
@functools.lru_cache(maxsize=64)
def load(path, scale=1.0):
    im = cv2.imread(os.path.join(ROOT, path), cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255
    im[..., :3] *= im[..., 3:4]
    if scale != 1.0:
        im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return im

def blank(): return np.zeros((H, W, 3), np.float32)

def put(dst, src, cx, cy, s=1.0, rot=0.0, op=1.0, anchor=(0.5, 0.5), add=False, flip=False):
    """composite premultiplied RGBA `src` onto RGB `dst` with transform."""
    if op <= 0.001: return dst
    h, w = src.shape[:2]
    ax, ay = w * anchor[0], h * anchor[1]
    M = cv2.getRotationMatrix2D((ax, ay), rot, s)
    if flip:
        M[0, :2] *= -1; M[0, 2] = -M[0, 2] + 2 * ax * s * math.cos(math.radians(rot)) if False else M[0, 2]
    M[0, 2] += cx - ax; M[1, 2] += cy - ay
    corners = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0, y0 = np.floor(corners.min(0)).astype(int) - 2
    x1, y1 = np.ceil(corners.max(0)).astype(int) + 2
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if X1 <= X0 or Y1 <= Y0: return dst
    M2 = M.copy(); M2[0, 2] -= X0; M2[1, 2] -= Y0
    interp = cv2.INTER_LINEAR if s > 0.5 else cv2.INTER_AREA
    if abs(s - 1) < 1e-3 and abs(rot) < 1e-3 and float(M[0, 2]).is_integer() and float(M[1, 2]).is_integer():
        interp = cv2.INTER_NEAREST
    if s < 0.5:   # pre-shrink for quality
        k = s / 0.5
        src = cv2.resize(src, None, fx=k * 1.0001, fy=k * 1.0001, interpolation=cv2.INTER_AREA)
        M2[:, :2] /= k
        h, w = src.shape[:2]
    reg = cv2.warpAffine(src, M2, (X1 - X0, Y1 - Y0), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    d = dst[Y0:Y1, X0:X1]
    if add:
        d += reg[..., :3] * op
    else:
        a = reg[..., 3:4] * op
        d *= (1 - a); d += reg[..., :3] * op
    return dst

def put_full(dst, src, op=1.0, add=False):
    if add: dst += src[..., :3] * op
    else:
        a = src[..., 3:4] * op; dst *= (1 - a); dst += src[..., :3] * op
    return dst

def glow(img, sigma=12, k=0.6, thresh=0.6):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(small - thresh, 0, None)
    bl = cv2.GaussianBlur(br, (0, 0), sigma / 4)
    return img + cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR) * k

def tint(src, mul=(1, 1, 1), add=(0, 0, 0)):
    o = src.copy(); o[..., :3] = o[..., :3] * np.array(mul, np.float32) + np.array(add, np.float32) * o[..., 3:4]
    return o

def rim(src, color=(0.6, 0.85, 1.0), strength=0.6, direction=(1, -0.3), width=6):
    """add a directional rim light inside the silhouette edge."""
    a = src[..., 3]
    er = cv2.erode(a, np.ones((3, 3), np.uint8), iterations=width)
    edge = np.clip(a - cv2.GaussianBlur(er, (0, 0), width * 0.6), 0, 1)
    gx = cv2.Sobel(cv2.GaussianBlur(a, (0, 0), width), cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(cv2.GaussianBlur(a, (0, 0), width), cv2.CV_32F, 0, 1)
    n = np.sqrt(gx ** 2 + gy ** 2) + 1e-6
    d = np.array(direction, np.float32); d /= np.linalg.norm(d)
    facing = np.clip(-(gx * d[0] + gy * d[1]) / n, 0, 1)
    o = src.copy(); o[..., :3] += edge[..., None] * facing[..., None] * np.array(color, np.float32) * strength
    return o

# ------------------------------------------------------------------ stars / space
@functools.lru_cache(maxsize=4)
def starfield(w=3200, h=1800, seed=1, density=1.0):
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), np.float32)
    # faint nebula
    neb = np.zeros((h // 8, w // 8), np.float32)
    neb = cv2.GaussianBlur(rng.random((h // 8, w // 8)).astype(np.float32), (0, 0), 9)
    neb = (neb - neb.min()) / (neb.max() - neb.min())
    neb = cv2.resize(neb ** 3, (w, h))
    img += neb[..., None] * np.array([0.03, 0.05, 0.11], np.float32)
    n = int(2600 * density)
    xs, ys = rng.integers(0, w, n), rng.integers(0, h, n)
    b = rng.random(n) ** 3
    for x, y, br in zip(xs, ys, b):
        c = np.array([0.8 + 0.2 * rng.random(), 0.85 + 0.1 * rng.random(), 1.0], np.float32) * (0.25 + 0.9 * br)
        if br > 0.75:
            cv2.circle(img, (int(x), int(y)), 2, c.tolist(), -1, cv2.LINE_AA)
        else:
            img[y, x] = c
    bloom = cv2.GaussianBlur(img, (0, 0), 2.2)
    img = img + bloom * 1.6
    return img

def space_bg(t, pan=(0, 0), zoom=1.0, seed=1):
    sf = starfield(seed=seed)
    h, w = sf.shape[:2]
    cw, ch = W / zoom, H / zoom
    x = (w - cw) / 2 + pan[0]; y = (h - ch) / 2 + pan[1]
    M = np.array([[zoom, 0, -x * zoom], [0, zoom, -y * zoom]], np.float32)
    return cv2.warpAffine(sf, M, (W, H), flags=cv2.INTER_LINEAR)

def disc(img, cx, cy, r, col, soft=1.5, op=1.0, add=False):
    """draw an anti-aliased filled circle (float)"""
    x0, x1 = int(max(cx - r - 4, 0)), int(min(cx + r + 4, W)); y0, y1 = int(max(cy - r - 4, 0)), int(min(cy + r + 4, H))
    if x1 <= x0 or y1 <= y0: return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    a = np.clip((r - d) / soft + 0.5, 0, 1)[..., None] * op
    reg = img[y0:y1, x0:x1]
    if add: reg += a * np.array(col, np.float32)
    else: reg *= (1 - a); reg += a * np.array(col, np.float32)
    return img

def bloom_spot(img, cx, cy, r, col, k=1.0):
    x0, x1 = int(max(cx - r * 4, 0)), int(min(cx + r * 4, W)); y0, y1 = int(max(cy - r * 4, 0)), int(min(cy + r * 4, H))
    if x1 <= x0 or y1 <= y0: return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
    img[y0:y1, x0:x1] += (np.exp(-d2) * k)[..., None] * np.array(col, np.float32)
    return img

def earth(img, cx, cy, r, lights=0.0, lights_on=1.0, seed=3, night_frac=0.45, dim=1.0, L=(-0.75, -0.35, 0.55)):
    """stylised Earth: blue disc, soft continents, crescent lit, city lights on the night side."""
    if r < 3:
        disc(img, cx, cy, max(r, 1.2), (0.45 * dim, 0.7 * dim, 1.0 * dim), soft=1.0)
        return bloom_spot(img, cx, cy, max(r, 2) * 3, (0.25, 0.45, 0.9), 0.5 * dim)
    S = int(r * 2 + 8)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    dx, dy = (xx - S / 2) / r, (yy - S / 2) / r
    d = np.sqrt(dx ** 2 + dy ** 2)
    inside = np.clip((1 - d) * r / 1.5 + 0.5, 0, 1)
    z = np.sqrt(np.clip(1 - d ** 2, 0, 1))
    rng = np.random.default_rng(seed)
    nz = cv2.resize(rng.random((24, 24)).astype(np.float32), (S, S), interpolation=cv2.INTER_CUBIC)
    nz = cv2.GaussianBlur(nz, (0, 0), S / 40)
    land = (nz > 0.55).astype(np.float32)
    land = cv2.GaussianBlur(land, (0, 0), S / 120 + 0.5)
    base = np.dstack([0.08 + 0.10 * land, 0.22 + 0.20 * land, 0.55 - 0.25 * land])
    L = np.array(L, np.float64); L /= np.linalg.norm(L)
    lam = np.clip(dx * L[0] + dy * L[1] + z * L[2], 0, 1)
    col = base * (0.06 + 1.2 * lam[..., None]) * dim
    atm = np.clip(1 - np.abs(1 - d) * 18, 0, 1) * (0.3 + lam)
    col += atm[..., None] * np.array([0.25, 0.55, 1.0]) * 0.8 * dim
    if lights > 0:
        night = np.clip(0.35 - lam * 2, 0, 1) * inside
        pts = rng.random((4000, 2))
        cl = np.zeros((S, S), np.float32)
        for i, (px, py) in enumerate(pts):
            x, y = int(px * S), int(py * S)
            if land[min(y, S - 1), min(x, S - 1)] > 0.5 and ((i * 7919) % 4000) / 4000.0 < lights_on:
                cl[min(y, S - 1), min(x, S - 1)] = 1.0
        cl = cv2.GaussianBlur(cl, (0, 0), 0.8) * 3 + cv2.GaussianBlur(cl, (0, 0), 3) * 2
        col += (cl * night)[..., None] * np.array([1.0, 0.75, 0.35]) * lights
    rgba = np.dstack([col * inside[..., None], inside]).astype(np.float32)
    put(img, rgba, cx, cy)
    return bloom_spot(img, cx, cy, r * 1.15, (0.15, 0.35, 0.8), 0.25 * dim)

# ------------------------------------------------------------------ text
@functools.lru_cache(maxsize=64)
def font(path, size): return ImageFont.truetype(path, size)

def text_layer(lines, size=34, path=FONT_MONO, color=(1, 1, 1), spacing=1.35, align="left", tracking=0, max_w=W):
    """returns premultiplied RGBA of the text block"""
    f = font(path, size)
    lh = int(size * spacing)
    def tw(s):
        return sum(f.getlength(ch) + tracking for ch in s) if tracking else f.getlength(s)
    wmax = int(max([tw(l) for l in lines] + [1])) + 8
    img = Image.new("L", (wmax, lh * len(lines) + 10), 0)
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        x = 4 if align == "left" else (wmax - tw(l)) / 2
        if tracking:
            for ch in l:
                d.text((x, i * lh), ch, font=f, fill=255); x += f.getlength(ch) + tracking
        else:
            d.text((x, i * lh), l, font=f, fill=255)
    a = np.asarray(img, np.float32)[..., None] / 255
    return np.dstack([a * np.array(color, np.float32), a]).astype(np.float32)

def typed(s, t, t0, cps=28):
    n = int(max(0, (t - t0) * cps))
    return s[:n]

# ------------------------------------------------------------------ astro
ASTRO = json.load(open(os.path.join(ROOT, "assets/astro.json")))

def _ellipse(cx, cy, rx, ry, n=40, rot=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return pts

def _arc(cx, cy, R, w, a0, a1, n=24):
    o = [(cx + (R + w) * math.cos(a0 + (a1 - a0) * i / n), cy + (R + w) * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    i_ = [(cx + (R - w) * math.cos(a1 - (a1 - a0) * i / n), cy + (R - w) * math.sin(a1 - (a1 - a0) * i / n)) for i in range(n + 1)]
    return o + i_

def _clip_top(poly, cut, tilt): return [(x, min(y, cut + tilt * x)) for x, y in poly]

def eye_shapes(E):
    rx, ry = 0.019, 0.031
    if E == "NEUTRAL": s = _ellipse(0, 0, rx, ry); return [s, s]
    if E == "CURIOUS": return [_ellipse(0, 0, rx * .9, ry * .85, rot=.12), _ellipse(0, .004, rx * 1.15, ry * 1.12, rot=-.08)]
    if E == "HAPPY": a = _arc(0, -.012, .02, .0065, math.radians(20), math.radians(160)); return [a, a]
    if E == "SAD": return [_clip_top(_ellipse(0, -.004, rx, ry * .85), .01, .45), _clip_top(_ellipse(0, -.004, rx, ry * .85), .01, -.45)]
    if E == "SUSPICIOUS": s = _ellipse(0, 0, rx * 1.35, ry * .22); return [s, s]
    if E == "SURPRISED": s = _ellipse(0, 0, .027, .029); return [s, s]
    if E == "FEARFUL": s = _ellipse(0, 0, rx * .7, ry * 1.05); return [s, s]
    if E == "SARCASTIC": s = _clip_top(_ellipse(0, -.008, rx * 1.15, ry * .75), -.006, 0); return [s, s]
    if E == "CLOSED": s = _ellipse(0, -0.01, rx * 1.1, ry * 0.12); return [s, s]
    raise ValueError(E)

@functools.lru_cache(maxsize=10)
def astro(pose="front34", expr="NEUTRAL", blink=0.0, look=(0.0, 0.0), scale=1.0):
    """sprite with code-drawn eyes. pose in full_cut/front/front34/sideL/sideR/back/back34/helmet"""
    base = load(f"assets/c_{pose}.png").copy()
    info = ASTRO[pose]
    eyes = info["eyes"]
    if eyes:
        h, w = base.shape[:2]
        SS = 2
        mask = np.zeros((h * SS, w * SS), np.uint8)
        shapes = eye_shapes(expr)
        if len(eyes) == 1:
            shapes = [shapes[1] if pose == "sideL" else shapes[0]]
        for e, poly in zip(eyes, shapes):
            sx = (e["w"] / 2) / 0.019 * 0.95; sy = (e["h"] / 2) / 0.031 * 0.95
            yb = 1.0 - 0.9 * blink
            pts = np.array([[(e["cx"] + look[0] * e["w"] * 0.4 + x * sx) * SS,
                             (e["cy"] + look[1] * e["h"] * 0.3 - y * sy * yb) * SS] for x, y in poly], np.int32)
            cv2.fillPoly(mask, [pts], 255, cv2.LINE_AA)
        m = cv2.resize(mask, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        ref = max(e["h"] for e in eyes)
        g1 = cv2.GaussianBlur(m, (0, 0), ref * 0.12)
        g2 = cv2.GaussianBlur(m, (0, 0), ref * 0.45)
        core = np.array([0.80, 0.97, 1.0], np.float32); cy_ = np.array(CYAN, np.float32)
        add = m[..., None] * core + g1[..., None] * cy_ * 0.6 + g2[..., None] * cy_ * 0.55
        base[..., :3] = base[..., :3] * (1 - m[..., None]) + add * base[..., 3:4]
    if scale != 1.0:
        base = cv2.resize(base, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return base

def blink_at(t, seed=0, every=3.7):
    ph = (t + seed * 1.3) % every
    return 1.0 if ph < 0.09 else (0.5 if ph < 0.14 else 0.0)

@functools.lru_cache(maxsize=10)
def astro_lit(pose, expr, blink, look, scale, mul, rimc, rims, rimdir):
    s = astro(pose, expr, blink, look, scale)
    s = tint(s, mul)
    if rims > 0: s = rim(s, rimc, rims, rimdir, width=max(2, int(4 * scale)))
    return s

def draw_astro(img, t, pose, cx, cy_feet, height, expr="NEUTRAL", look=(0, 0), mul=(1, 1, 1), rimc=(0.6, 0.85, 1.0),
               rims=0.0, rimdir=(1, -0.3), breathe=True, shadow=0.5, op=1.0, blink=True, rot=0.0, anchor_y=1.0):
    info = ASTRO[pose]
    h0 = info["size"][1]
    sc = height / h0
    bl = blink_at(t) if blink else 0.0
    bl = round(bl, 1)
    # cache sprites at a quantised scale, finish scaling in put()
    q = min(1.0, round(sc * 1.25, 2))
    spr = astro_lit(pose, expr, bl, tuple(round(v * 20) / 20 for v in look), q, tuple(mul), tuple(rimc), rims, tuple(rimdir))
    br = 1 + (0.006 * math.sin(t * 2 * math.pi / 3.6) if breathe else 0)
    if shadow > 0:
        sh = np.zeros((int(height * 0.14) + 8, int(height * 0.6) + 8, 4), np.float32)
        cv2.ellipse(sh, (sh.shape[1] // 2, sh.shape[0] // 2), (int(height * 0.27), int(height * 0.05)), 0, 0, 360, (0, 0, 0, 1), -1, cv2.LINE_AA)
        sh = cv2.GaussianBlur(sh, (0, 0), height * 0.02 + 1)
        put(img, sh, cx, cy_feet, op=shadow * op)
    put(img, spr, cx, cy_feet, s=sc / q, rot=rot, op=op, anchor=(0.5, anchor_y))
    return img

# ------------------------------------------------------------------ hologram
@functools.lru_cache(maxsize=16)
def holo_sprite(name, scale=1.0):
    s = load(f"plates/{name}.png", scale).copy()
    h = s.shape[0]
    rows = (np.arange(h) % 4 < 2).astype(np.float32) * 0.35 + 0.65
    s *= rows[:, None, None]
    fade = np.clip((np.linspace(1.0, 0.0, h) - 0.0) * 3.0, 0, 1)
    s *= fade[:, None, None]
    return s

def draw_holo(img, t, name, cx, cy_bottom, height, op=1.0, seed=0, beam=True, base_w=None):
    s0 = load(f"plates/{name}.png")
    sc = height / s0.shape[0]
    spr = holo_sprite(name, round(min(1.0, sc * 1.2), 2))
    k = height / spr.shape[0]
    fl = 0.86 + 0.08 * noise1(t, seed, 7) + 0.06 * math.sin(t * 50)
    jit = 0
    if noise1(t, seed + 5, 3) > 0.82:
        jit = 6 * noise1(t, seed + 9, 40)
    if beam:
        bw = base_w or height * 0.18
        poly = np.array([[cx - bw / 2, cy_bottom + height * 0.04], [cx + bw / 2, cy_bottom + height * 0.04],
                         [cx + height * 0.32, cy_bottom - height * 0.95], [cx - height * 0.32, cy_bottom - height * 0.95]], np.int32)
        cone = np.zeros((H, W), np.float32)
        cv2.fillPoly(cone, [poly], 1.0, cv2.LINE_AA)
        cone = cv2.GaussianBlur(cone, (0, 0), 18)
        grad = np.clip((np.arange(H) - (cy_bottom - height)) / height, 0, 1).astype(np.float32)
        img += (cone * grad[:, None] * 0.10 * op * fl)[..., None] * np.array(CYAN, np.float32)
    put(img, spr, cx + jit, cy_bottom, s=k, op=op * fl, anchor=(0.5, 1.0), add=True)
    bloom_spot(img, cx, cy_bottom - height * 0.5, height * 0.35, CYAN, 0.06 * op)
    return img

# ------------------------------------------------------------------ frost
@functools.lru_cache(maxsize=4)
def frost_tex(w, h, seed=2):
    rng = np.random.default_rng(seed)
    base = np.zeros((h, w), np.float32)
    for _ in range(int(w * h / 4000)):
        x, y = rng.integers(0, w), rng.integers(0, h)
        L = rng.integers(8, 60); a = rng.random() * math.pi
        for k in range(3):
            aa = a + k * math.pi / 3
            cv2.line(base, (int(x - math.cos(aa) * L), int(y - math.sin(aa) * L)),
                     (int(x + math.cos(aa) * L), int(y + math.sin(aa) * L)), float(0.3 + 0.7 * rng.random()), 1, cv2.LINE_AA)
    cloud = cv2.resize(rng.random((h // 20 + 2, w // 20 + 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    tex = np.clip(cv2.GaussianBlur(base, (0, 0), 1.0) * 0.6 + cv2.GaussianBlur(base, (0, 0), 6) * 1.6 + cloud * 0.7, 0, 1)
    melt = cv2.GaussianBlur(rng.random((h // 30 + 2, w // 30 + 2)).astype(np.float32), (0, 0), 1)
    melt = cv2.resize(melt, (w, h), interpolation=cv2.INTER_CUBIC)
    melt = (melt - melt.min()) / (melt.max() - melt.min() + 1e-6)
    # edges melt last
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx / w, 1 - xx / w), np.minimum(yy / h, 1 - yy / h)) * 2
    melt = np.clip(melt * 0.45 + (1 - edge) * 0.75, 0, 1)
    return tex, melt

def frost_layer(w, h, amount):
    """amount 1 = fully frosted, 0 = clear"""
    tex, melt = frost_tex(w, h)
    cover = np.clip((amount * 1.25 - (1 - melt)) * 4 + 0.5, 0, 1) if amount < 1 else np.ones_like(melt)
    a = np.clip(0.72 + tex * 0.28, 0, 1) * cover
    col = (0.80 + 0.2 * tex)[..., None] * np.array([0.86, 0.94, 1.0], np.float32)
    return np.dstack([col * a[..., None], a]).astype(np.float32)

# ------------------------------------------------------------------ finishing
_GRAIN = None
def finish(img, t, vign=0.55, grain=0.025, bars=True, lift=(0.008, 0.012, 0.024), caption=None, fade=1.0, sat=1.0):
    global _GRAIN
    if _GRAIN is None:
        rng = np.random.default_rng(7)
        _GRAIN = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
    yy, xx = np.ogrid[:H, :W]
    if not hasattr(finish, "_v"):
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        finish._v = np.clip(1 - (d - 0.55) * 0.7, 0, 1).astype(np.float32) ** 1.6
    img = img * (1 - vign + vign * finish._v[..., None])
    if sat != 1.0:
        g = img.mean(2, keepdims=True); img = g + (img - g) * sat
    img = img + np.array(lift, np.float32)
    # filmic soft clip
    img = np.clip(img, 0, None)
    img = np.where(img > 0.8, 0.8 + 0.2 * (1 - np.exp(-(img - 0.8) / 0.2)), img)
    g = cv2.resize(_GRAIN[int(t * FPS) % 6], (W, H), interpolation=cv2.INTER_LINEAR)
    img = img + g[..., None] * grain
    img = img * fade
    if bars:
        img[:BAR] = 0; img[H - BAR:] = 0
    if caption:
        txt, op = caption
        if op > 0.01:
            tl = text_layer([txt], size=34, path=FONT_REG, color=(0.93, 0.93, 0.9))
            put(img, tl, W / 2, H - BAR / 2 - 4, op=op)
    return np.clip(img, 0, 1)

def to8(img): return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
