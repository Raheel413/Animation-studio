import subprocess, os, sys
sys.path.insert(0, "/home/claude/film")
import shots as S
tl, T = S.timeline()
files = [f"shots/{i:02d}_{s['name']}.mp4" for i, s in enumerate(tl)]
missing = [f for f in files if not os.path.exists(f)]
if missing: print("MISSING", missing); sys.exit(1)
open("out/list.txt", "w").write("".join(f"file '/home/claude/film/{f}'\n" for f in files))
run = lambda a: subprocess.run(a, check=True)
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "out/list.txt", "-c", "copy", "out/video.mp4"])
run(["ffmpeg", "-v", "error", "-y", "-i", "audio/mix_raw.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "audio/mix.wav"])
out = "out/Lonely Astronaut - The Last Message Earth Ever Sent.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", "out/video.mp4", "-i", "audio/mix.wav", "-map", "0:v", "-map", "1:a", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", "out/final.tmp.mp4"])
os.replace("out/final.tmp.mp4", out)
print("DONE", out)
