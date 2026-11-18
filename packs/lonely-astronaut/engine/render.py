"""render.py stills <name:t> ...   |   render.py shots <i0> <i1> [step]   |   render.py env"""
import sys, os, subprocess, json, math
import numpy as np, cv2
sys.path.insert(0, "/home/claude/film")
from eng import *
import shots as S
from scipy.io import wavfile

def build_env():
    tl, total = S.timeline()
    env = {}
    for s in tl:
        for off, cue, g in s["cues"]:
            if cue.startswith("VO:noor"):
                name = cue.split(":")[1]
                sr, x = wavfile.read(f"{ROOT}/audio/{name}.wav")
                x = np.abs(x.astype(np.float32))
                hop = sr // FPS
                n = len(x) // hop
                e = np.array([x[i * hop:(i + 1) * hop].mean() for i in range(n)])
                e = np.convolve(e, np.ones(2) / 2, mode="same")
                f0 = int(round((s["start"] + off) * FPS))
                for i, v in enumerate(e):
                    env[f0 + i] = float(v)
    return env

def caption_at(shot, t):
    for off, dur, txt in shot["caps"]:
        if off - 0.15 <= t <= off + dur + 0.3:
            op = ramp(t, off - 0.15, off + 0.1) * (1 - ramp(t, off + dur, off + dur + 0.3))
            return (txt, op)
    return None

def frame(shot, t):
    T = shot["start"] + t
    img = shot["fn"](t, T)
    fade_in = ramp(t, 0, 0.35) if shot["name"] in ("title", "ship_alone", "end", "goodnight", "wall_reveal", "map", "travel", "erase_wall", "new_mark") else 1.0
    fade_out = 1.0
    if shot["name"] in ("helmet_sad", "holo_e", "erase_wall", "home"): fade_out = 1 - ramp(t, shot["dur"] - 0.6, shot["dur"])
    if shot["name"] == "end": fade_out = 1 - ramp(t, shot["dur"] - 1.0, shot["dur"])
    return finish(img, T, caption=caption_at(shot, t), fade=fade_in * fade_out)

def main():
    S.ENV.update(build_env())
    tl, total = S.timeline()
    by = {s["name"]: s for s in tl}
    mode = sys.argv[1]
    if mode == "stills":
        os.makedirs(f"{ROOT}/out/stills", exist_ok=True)
        for arg in sys.argv[2:]:
            n, t = arg.split(":")
            img = frame(by[n], float(t))
            cv2.imwrite(f"{ROOT}/out/stills/{n}_{t}.jpg", cv2.cvtColor(to8(img), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 88])
            print("still", n, t, flush=True)
    elif mode == "shots":
        names = sys.argv[2].split(",")
        for n in names:
            s = by[n]
            idx = [x["name"] for x in tl].index(n)
            out = f"{ROOT}/shots/{idx:02d}_{n}.mp4"
            tmp = out.replace(".mp4", ".tmp.mp4")
            nf = int(round(s["dur"] * FPS))
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                                  "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
            for i in range(nf):
                p.stdin.write(to8(frame(s, i / FPS)).tobytes())
            p.stdin.close(); p.wait()
            if p.returncode == 0: os.replace(tmp, out)
            print("shot", idx, n, nf, flush=True)

if __name__ == "__main__":
    main()
