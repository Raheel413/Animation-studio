"""Score + sound design + VO mix for THE LAST MESSAGE EARTH EVER SENT. Writes audio/mix.wav"""
import sys, os, json, math, subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve
sys.path.insert(0, "/home/claude/film")
import shots as S

SR = 48000
tl, TOTAL = S.timeline()
START = {s["name"]: s["start"] for s in tl}
N = int((TOTAL + 2) * SR)
music = np.zeros((N, 2), np.float32)
sfx = np.zeros((N, 2), np.float32)
vo = np.zeros((N, 2), np.float32)
bed = np.zeros((N, 2), np.float32)
rng = np.random.default_rng(11)

def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    e = np.full(n, s, np.float32)
    if a: e[:a] = np.linspace(0, 1, a)
    if d: e[a:a + d] = np.linspace(1, s, min(d, max(n - a, 0)))[: len(e[a:a + d])]
    if r and n > r: e[-r:] *= np.linspace(1, 0, r)
    return e
def lp(x, f, order=2): return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0).astype(np.float32)
def hp(x, f, order=2): return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0).astype(np.float32)
def bp(x, f1, f2, order=2): return sosfilt(butter(order, [f1, f2], "band", fs=SR, output="sos"), x, axis=0).astype(np.float32)
def add(buf, t, x, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0: return
    if x.ndim == 1:
        L, R = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        x = np.stack([x * L * 1.414, x * R * 1.414], 1)
    j = min(len(buf), i + len(x))
    buf[max(i, 0):j] += x[max(0, -i): j - i] * gain

def reverb_ir(sec=3.0, damp=3.0, seed=1):
    r = np.random.default_rng(seed)
    n = int(sec * SR); t = np.arange(n) / SR
    ir = np.stack([r.normal(0, 1, n), r.normal(0, 1, n)], 1) * np.exp(-t * damp)[:, None]
    ir = lp(ir, 6000); ir[:int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))[:, None]
    return (ir / np.sqrt((ir ** 2).sum(0))).astype(np.float32)
def reverb(x, ir, wet=0.3):
    out = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1).astype(np.float32)
    return x * (1 - wet) + out * wet

# ================================================================= instruments
def piano(t0, m, dur=2.0, vel=0.5, pan=0.0):
    f = mtof(m); L = dur + 3.5
    n = int(L * SR); t = np.arange(n) / SR
    x = np.zeros(n, np.float32); B = 0.00035
    dec = 1.0 + (m - 50) * 0.035
    for k in range(1, 10):
        fk = k * f * math.sqrt(1 + B * k * k)
        if fk > 16000: break
        a = (1 / k ** 1.25) * (0.6 + 0.4 * vel) ** (k * 0.4)
        x += a * np.sin(2 * np.pi * fk * t + rng.random() * 6) * np.exp(-t * (0.55 * dec + 0.45 * k * dec))
    x *= np.minimum(1, t / 0.004)
    rel = np.clip((dur + 0.25 - t) / 0.25, 0, 1) ** 2 * 0.85 + 0.15 * np.exp(-np.maximum(t - dur, 0) * 4)
    x *= np.where(t < dur, 1, rel)
    ham = lp(rng.normal(0, 1, int(0.03 * SR)).astype(np.float32), 2500) * np.exp(-np.arange(int(0.03 * SR)) / SR * 120) * 0.08
    x[: len(ham)] += ham
    add(music, t0, x * vel * 0.32, pan=pan + (m - 64) / 60)

def pad(t0, t1, notes, vol=0.12, att=2.0, rel=3.0, bright=900, pan_w=0.5):
    n = int((t1 - t0 + rel) * SR); t = np.arange(n) / SR
    out = np.zeros((n, 2), np.float32)
    for i, m in enumerate(notes):
        f = mtof(m)
        for d, pan in ((-0.0025, -pan_w), (0.0, 0.0), (0.0028, pan_w)):
            ff = f * (1 + d)
            x = np.zeros(n, np.float32)
            for k in range(1, 9):
                if k * ff > 5000: break
                x += np.sin(2 * np.pi * k * ff * t + rng.random() * 6) / k
            x *= 0.6 + 0.4 * np.sin(2 * np.pi * (0.07 + 0.03 * i) * t + i)
            L, R = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            out[:, 0] += x * L; out[:, 1] += x * R
    out = lp(out, bright)
    e = np.ones(n, np.float32)
    a = int(att * SR); r = int(rel * SR); body = int((t1 - t0) * SR)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[body:] = np.linspace(1, 0, n - body) ** 2
    out *= e[:, None] * vol / max(len(notes), 1) ** 0.5 / 3
    add(music, t0, out)

def drone(t0, t1, m, vol=0.1, att=3, rel=3):
    n = int((t1 - t0 + rel) * SR); t = np.arange(n) / SR
    f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) + 0.25 * np.sin(2 * np.pi * f * 3.01 * t)
    x = x * (0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t))
    e = env_adsr(n, att, 0, 1, rel)
    add(music, t0, (x * e * vol).astype(np.float32))

def shimmer(t0, t1, notes, vol=0.03):
    n = int((t1 - t0 + 3) * SR); t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for m in notes:
        x += np.sin(2 * np.pi * mtof(m) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * (0.2 + rng.random() * 0.3) * t + rng.random() * 6))
    add(music, t0, x * env_adsr(n, 2.5, 0, 1, 3) * vol / len(notes), pan=0.0)

def pulse(t0, t1, m, rate=2.0, vol=0.08, decay=8.0):
    k = 0
    while t0 + k / rate < t1:
        tt = t0 + k / rate
        n = int(0.5 * SR); t = np.arange(n) / SR
        f = mtof(m)
        x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * decay)
        prog = (tt - t0) / max(t1 - t0, 1e-3)
        add(music, tt, lp(x.astype(np.float32), 1200) * vol * (0.5 + 0.5 * prog))
        k += 1

# ----------------------------------------------------------------- themes
D3, F3, A3, Bb2, C3, F2, G2, D2, A2 = 50, 53, 57, 46, 48, 41, 43, 38, 45
THEME = [(0, 69, 1), (1, 74, 1), (2, 72, 1), (3, 69, 2), (5, 67, 1), (6, 65, 1), (7, 67, 1), (8, 69, 1), (9, 62, 3),
         (12, 69, 1), (13, 74, 1), (14, 76, 1), (15, 77, 2), (17, 76, 0.5), (17.5, 74, 2.5)]
CHORDS_MIN = [(0, [D3, A3, 65]), (3, [Bb2, F3, 62]), (6, [F2, C3, A3]), (9, [D3, A3, 65]), (12, [Bb2, F3, 62]), (15, [C3, G2 + 12, 64])]
THEME_MAJ = [(0, 72, 1), (1, 77, 1), (2, 76, 1), (3, 72, 2), (5, 70, 1), (6, 69, 1), (7, 70, 1), (8, 72, 1), (9, 65, 3),
             (12, 72, 1), (13, 77, 1), (14, 79, 1), (15, 81, 2), (17, 79, 0.5), (17.5, 77, 3.5)]
CHORDS_MAJ = [(0, [F2, C3, A3]), (3, [Bb2, F3, D3 + 12]), (6, [D3, A3, 65]), (9, [F2, C3, A3]), (12, [Bb2, F3, 62]), (15, [F2, C3, 69])]

def theme(t0, beat=1.0, vel=0.5, major=False, upto=None, left=True, oct=0):
    mel = THEME_MAJ if major else THEME
    ch = CHORDS_MAJ if major else CHORDS_MIN
    for b, m, d in mel:
        if upto is not None and b >= upto: break
        piano(t0 + b * beat, m + oct, d * beat * 0.95, vel * (0.9 + 0.2 * rng.random()))
    if left:
        for b, notes in ch:
            if upto is not None and b >= upto: break
            for i, m in enumerate(notes):
                piano(t0 + b * beat + i * 0.12 * beat, m, 2.6 * beat, vel * 0.55)

# ================================================================= SFX
def noise(n): return rng.normal(0, 1, n).astype(np.float32)
def mx(*xs):
    n = max(len(x) for x in xs); o = np.zeros(n, np.float32)
    for x in xs: o[:len(x)] += x
    return o
def tone(f, dur, decay=6.0, f2=None):
    n = int(dur * SR); t = np.arange(n) / SR
    ff = f if f2 is None else f * (f2 / f) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(ff) / SR
    return (np.sin(ph) * np.exp(-t * decay)).astype(np.float32)

IR_SMALL = reverb_ir(1.2, 5.5, 2); IR_BIG = reverb_ir(3.5, 2.0, 3); IR_SPACE = reverb_ir(5.0, 1.2, 4)

def sfx_make(name):
    if name == "ping":
        x = mx(tone(1320, 2.5, 2.2) * 0.6, tone(2640, 1.2, 5) * 0.15)
        return reverb(np.stack([x, x], 1), IR_BIG, 0.4)
    if name == "type":
        n = int(1.4 * SR); x = np.zeros(n, np.float32)
        for k in range(int(1.3 * 26)):
            i = int((k / 26 + rng.random() * 0.01) * SR)
            c = hp(noise(400), 2500) * np.exp(-np.arange(400) / 40) * (0.4 + 0.6 * rng.random())
            x[i:i + 400] += c[: len(x[i:i + 400])]
        return x * 0.35
    if name in ("beep", "beep_low"):
        f = 980 if name == "beep" else 520
        x = np.concatenate([tone(f, 0.12, 4), np.zeros(int(0.08 * SR), np.float32), tone(f, 0.12, 4)])
        return x * 0.4
    if name == "heartbeat":
        out = np.zeros(int(4 * SR), np.float32)
        for k in range(4):
            for off, a in ((0, 1.0), (0.22, 0.6)):
                th = lp(mx(tone(55, 0.25, 18), 0.3 * noise(int(0.25 * SR)) * np.exp(-np.arange(int(0.25 * SR)) / SR * 30)), 180)
                i = int((k * 1.0 + off) * SR); out[i:i + len(th)] += th * a
        return out * 0.9
    if name == "servo":
        n = int(0.8 * SR); t = np.arange(n) / SR
        x = bp(noise(n), 300, 1800) * 0.3 + np.sin(2 * np.pi * (180 + 80 * t) * t) * 0.2
        return (x * env_adsr(n, 0.1, 0, 1, 0.3)).astype(np.float32)
    if name == "holo_on":
        n = int(2.0 * SR); t = np.arange(n) / SR
        x = np.zeros(n, np.float32)
        for k in range(5):
            x += np.sin(2 * np.pi * (600 + 300 * k) * (1 + t * 0.6) * t + k) * 0.08
        cr = noise(n) * (rng.random(n) > 0.995) * 0.6
        x = (x + hp(cr, 2000)) * env_adsr(n, 0.3, 0.4, 0.5, 1.0)
        return reverb(np.stack([x, x], 1), IR_SMALL, 0.35)
    if name == "radio_click":
        x = np.concatenate([hp(noise(int(0.03 * SR)), 1500) * 0.6, bp(noise(int(0.25 * SR)), 800, 4000) * 0.08])
        return x
    if name == "static":
        n = int(2.0 * SR)
        x = bp(noise(n), 500, 5000) * (0.6 + 0.4 * np.abs(np.sin(np.arange(n) / SR * 23))) * env_adsr(n, 0.05, 0, 1, 0.8)
        return x * 0.35
    if name == "static_burst":
        n = int(0.9 * SR)
        x = bp(noise(n), 300, 7000) * env_adsr(n, 0.005, 0, 1, 0.5)
        return x * 0.9
    if name == "click":
        return np.concatenate([hp(noise(int(0.012 * SR)), 1000) * 0.9, tone(1800, 0.08, 40) * 0.4])
    if name in ("powerdown", "powerdown_far"):
        n = int(4.0 * SR)
        x = tone(420, 4.0, 0.6, f2=35) * 0.7 + lp(noise(n), 300) * 0.25 * np.exp(-np.arange(n) / SR * 0.9)
        x = reverb(np.stack([x, x], 1), IR_BIG, 0.4)
        return x * (0.4 if name == "powerdown_far" else 1.0)
    if name == "powerup":
        n = int(5.0 * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * np.cumsum(60 + 160 * (t / 5) ** 0.6) / SR) * 0.4 + lp(noise(n), 200) * 0.15
        return (x * env_adsr(n, 2.5, 0, 1, 1.5)).astype(np.float32)
    if name == "beam":
        n = int(2.5 * SR); t = np.arange(n) / SR
        x = np.sin(2 * np.pi * np.cumsum(200 + 900 * t / 2.5) / SR) * 0.25 + hp(noise(n), 3000) * 0.08
        return reverb(np.stack([x * env_adsr(n, 0.2, 0, 1, 1)] * 2, 1), IR_SPACE, 0.5)
    if name in ("launch_far", "engine", "engine_soft"):
        dur = {"launch_far": 4.0, "engine": 7.5, "engine_soft": 4.0}[name]
        n = int(dur * SR); t = np.arange(n) / SR
        x = lp(noise(n), 160, 4) * 3.0 + np.sin(2 * np.pi * 38 * t) * 0.4 + lp(noise(n), 900) * 0.25
        e = env_adsr(n, 0.6 if name == "engine" else 1.5, 0, 1, 1.5)
        return (x * e * (1.0 if name == "engine" else 0.5)).astype(np.float32)
    if name == "alarm_soft":
        out = np.zeros(int(5 * SR), np.float32)
        for k in range(6):
            for j, f in enumerate((880, 660)):
                b = tone(f, 0.28, 3) * 0.35
                i = int((k * 0.8 + j * 0.3) * SR); out[i:i + len(b)] += b
        return out
    if name == "winch":
        n = int(5.5 * SR); t = np.arange(n) / SR
        x = bp(noise(n), 200, 1200) * (0.5 + 0.5 * np.sin(2 * np.pi * 14 * t) ** 2) * 0.5 + np.sin(2 * np.pi * 95 * t) * 0.1
        return (x * env_adsr(n, 0.3, 0, 1, 0.5)).astype(np.float32)
    if name == "clunk":
        n = int(1.2 * SR)
        x = mx(lp(noise(n), 400) * np.exp(-np.arange(n) / SR * 9) * 1.5, tone(70, 1.2, 5) * 0.8, tone(410, 0.8, 7) * 0.15)
        return reverb(np.stack([x, x], 1), IR_BIG, 0.35)
    if name == "hiss":
        n = int(2.5 * SR)
        return hp(noise(n), 2500) * env_adsr(n, 0.1, 0, 1, 1.5) * 0.25
    if name in ("frost", "melt"):
        dur = 5.0 if name == "frost" else 8.0
        n = int(dur * SR); x = np.zeros(n, np.float32)
        for k in range(int(dur * (20 if name == "frost" else 6))):
            i = rng.integers(0, n - 2000)
            c = hp(noise(300), 3000) * np.exp(-np.arange(300) / 30)
            x[i:i + 300] += c * rng.random()
        if name == "melt":
            for k in range(6):
                d = tone(1400 + rng.random() * 800, 0.25, 18, f2=700) * 0.25
                i = rng.integers(0, n - len(d)); x[i:i + len(d)] += d
        return reverb(np.stack([x, x], 1), IR_SMALL, 0.3) * 0.6
    if name == "knock_soft":
        out = np.zeros(int(1.2 * SR), np.float32)
        for k in range(2):
            th = mx(lp(noise(int(0.15 * SR)), 900) * np.exp(-np.arange(int(0.15 * SR)) / SR * 40), tone(180, 0.15, 30) * 0.5)
            i = int(k * 0.35 * SR); out[i:i + len(th)] += th
        return reverb(np.stack([out, out], 1), IR_SMALL, 0.3) * 0.8
    if name == "glass_touch":
        x = mx(lp(noise(int(0.2 * SR)), 600) * np.exp(-np.arange(int(0.2 * SR)) / SR * 30), tone(2200, 1.6, 2.5) * 0.08, tone(3300, 1.2, 3) * 0.05)
        return reverb(np.stack([x, x], 1), IR_SMALL, 0.4)
    if name == "marker":
        n = int(2.2 * SR); t = np.arange(n) / SR
        x = bp(noise(n), 1500, 6000) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 3.2 * t))) * env_adsr(n, 0.05, 0, 1, 0.2)
        return x * 0.22
    raise KeyError(name)

# ================================================================= VO
def load_vo(name, fx):
    src = f"{S.ROOT}/audio/{name}.wav"
    af = {"": "highpass=f=90,acompressor=threshold=-20dB:ratio=3:attack=5:release=80",
          "child": "asetrate=48000*1.24,aresample=48000,atempo=0.82,highpass=f=250,lowpass=f=5200,acompressor=threshold=-20dB:ratio=3",
          "radio": "highpass=f=380,lowpass=f=3400,acompressor=threshold=-24dB:ratio=6,volume=1.6",
          "muffled": "lowpass=f=1500,highpass=f=120,volume=1.5",
          "cut": "highpass=f=90,acompressor=threshold=-20dB:ratio=3"}[fx]
    out = f"/tmp/vo_{name}_{fx}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ac", "1", "-ar", str(SR), out], check=True)
    sr, x = wavfile.read(out)
    x = x.astype(np.float32)
    if x.dtype != np.float32 or np.abs(x).max() > 2: x = x / 32768.0
    if fx == "cut": x = x[: int(3.95 * SR)]; x[-200:] *= np.linspace(1, 0, 200)
    if fx == "radio":
        x = np.tanh(x * 2.0) * 0.7
        x = x + bp(noise(len(x)), 1000, 4000) * 0.012
    x = x / (np.abs(x).max() + 1e-6) * 0.7
    st = np.stack([x, x], 1)
    if fx == "muffled": st = reverb(st, IR_SMALL, 0.25)
    elif fx in ("", "cut"): st = reverb(st, IR_SMALL, 0.12)
    elif fx == "child": st = reverb(st, IR_SMALL, 0.2)
    return st

VO_SPANS = []
for s in tl:
    for off, cue, g in s["cues"]:
        T = s["start"] + off
        if cue.startswith("VO:"):
            parts = cue.split(":"); name = parts[1]; fx = parts[2] if len(parts) > 2 else ""
            x = load_vo(name, fx)
            add(vo, T, x, g)
            VO_SPANS.append((T, T + len(x) / SR))
        else:
            x = sfx_make(cue)
            add(sfx, T, x, g, pan=0.0)

# ================================================================= ambience beds
INTERIOR = {"cockpit_intro", "goodnight", "wall_reveal", "log_214", "holo_arrives", "holo_a", "holo_b", "holo_c", "helmet_listen",
            "holo_smile", "helmet_moved", "holo_d", "holo_e", "signal_end", "decide", "cargo_arrive", "podwin_frozen", "last_play",
            "touch_wall", "helmet_surprised", "helmet_sad", "pod_wake", "frost_melt", "helmet_realize", "hand", "helmet_reply",
            "height_line", "new_mark", "incoming", "glove_hover", "press_play", "map", "power_dialog", "confirm"}
for s in tl:
    n = int(s["dur"] * SR); t = np.arange(n) / SR
    if s["name"] in INTERIOR:
        lvl = 0.05 if s["name"] not in ("erase_holo", "erase_wall") else 0.0
        x = (np.sin(2 * np.pi * 50 * t) * 0.5 + np.sin(2 * np.pi * 100 * t) * 0.25) * 0.4 + lp(noise(n), 250) * 1.2
        add(bed, s["start"], x * lvl)
    elif s["name"] not in ("erase_holo", "erase_wall", "title", "end"):
        x = lp(noise(n), 120, 4) * 3.0
        add(bed, s["start"], x * 0.02)
k = int(0.3 * SR)
bed = lp(bed, 2000)

# ================================================================= score
st = START
drone(0.5, st["title"], D2, 0.07, att=4)
shimmer(1.0, st["title"] - 1, [81, 86, 88], 0.035)
piano(st["title"] + 0.8, 74, 4, 0.45); piano(st["title"] + 0.8, D2, 5, 0.35)
theme(st["ship_alone"], beat=1.0, vel=0.42)
pad(st["ship_alone"], st["wall_reveal"] + 7, [D3, A3, 65], 0.10)
theme(st["goodnight"] + 6.0, beat=1.05, vel=0.36, upto=9, left=False, oct=12)
drone(st["log_214"], st["press_play"] + 3, D2, 0.06)
pad(st["holo_arrives"] + 1.0, st["holo_b"] + 4.0, [D3, A3, 65], 0.07, att=3)
pad(st["holo_c"], st["helmet_listen"] + 4, [Bb2, F3, 62], 0.07, att=2)
pad(st["alone_wide"], st["holo_smile"] + 2, [F2, C3, A3, 72], 0.09, att=1.5)
piano(st["holo_smile"] + 0.8, 74, 3, 0.4); piano(st["holo_smile"] + 1.6, 69, 3, 0.35); piano(st["helmet_moved"] + 0.5, 65, 4, 0.33)
pad(st["helmet_moved"], st["holo_e"] + 4.3, [D3, A3, 65], 0.07)
drone(st["signal_end"] + 0.5, st["decide"], D2, 0.05)
pulse(st["map"] + 0.5, st["map"] + 9, 62, rate=1.0, vol=0.05, decay=14)
pad(st["decide"] + 1.0, st["burn"] + 1, [Bb2, F3, 62, 69], 0.09, att=2.5)
pad(st["burn"], st["travel"] + 10, [D3, A3, 64, 69], 0.10, att=1.0, bright=1400)
pulse(st["burn"] + 0.8, st["neptune"], D2 + 12, rate=4.0, vol=0.09, decay=10)
pulse(st["travel"], st["neptune"], A2 + 12, rate=2.0, vol=0.05, decay=6)
pad(st["neptune"], st["neptune"] + 8, [Bb2, F3, 62, 69, 74], 0.11, att=2, bright=2200)
shimmer(st["neptune"], st["neptune"] + 8, [81, 86, 89], 0.05)
pad(st["pod_tumble"], st["power_dialog"] + 9, [D2, D3 + 1, A3, 63], 0.07, att=2)
pulse(st["pod_tumble"], st["power_dialog"] + 9, D2, rate=1.1, vol=0.07, decay=9)
theme(st["last_play"] + 0.4, beat=1.15, vel=0.36, upto=9, left=True)
piano(st["touch_wall"] + 4.0, 62, 6, 0.3); piano(st["touch_wall"] + 4.0, D2, 6, 0.25)
for i, m in enumerate((74, 72, 69, 67, 65, 62)):
    piano(st["erase_wall"] + 0.4 + i * 1.1, m, 1.6, 0.36 - i * 0.03)
pad(st["pod_wake"] + 0.5, st["frost_melt"] + 9, [F2, C3, A3], 0.08, att=4, bright=700)
pad(st["frost_melt"], st["helmet_realize"] + 4, [Bb2, F3, 62, 69], 0.09, att=4, bright=1100)
theme(st["hand"] + 0.4, beat=0.95, vel=0.4, major=True, upto=12)
pad(st["hand"], st["height_line"] + 5, [F2, C3, A3, 72], 0.12, att=2, bright=1500)
shimmer(st["hand"] + 5.0, st["height_line"] + 5, [84, 89, 93], 0.04)
theme(st["new_mark"] + 0.5, beat=0.9, vel=0.38, major=True, upto=9, oct=0)
theme(st["home"] + 0.5, beat=1.0, vel=0.45, major=True)
pad(st["home"], st["end"] + 13, [F2, C3, A3, 72, 76], 0.13, att=3, rel=4, bright=1600)
piano(st["end"] + 12.5, 65, 6, 0.4); piano(st["end"] + 12.5, 41, 6, 0.4); piano(st["end"] + 12.6, 69, 6, 0.35); piano(st["end"] + 12.7, 72, 6, 0.33)

music = reverb(music, IR_BIG, 0.38)
sfx_r = reverb(sfx, IR_SMALL, 0.12)

# ================================================================= mix with ducking
duck = np.ones(N, np.float32)
for a, b in VO_SPANS:
    i0, i1 = int((a - 0.25) * SR), int((b + 0.4) * SR)
    duck[max(i0, 0):i1] = 0.3
k = int(0.25 * SR)
duck = np.convolve(duck, np.ones(k) / k, mode="same").astype(np.float32)
mix = music * 1.9 * duck[:, None] + sfx_r * 0.8 + bed * duck[:, None] + vo * 1.0
mix = mix[: int(TOTAL * SR)]
mix = np.tanh(mix * 1.1) / 1.1
wavfile.write(f"{S.ROOT}/audio/mix_raw.wav", SR, mix.astype(np.float32))
print("mix written", mix.shape[0] / SR, "peak", float(np.abs(mix).max()))
