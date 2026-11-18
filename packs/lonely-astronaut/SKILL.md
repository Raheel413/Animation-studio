---
name: lonely-astronaut
description: Make a finished Lonely Astronaut episode (3-6 min cinematic animated short starring ASTRO) from a topic or premise, end to end in chat: story, voices, 3D sets, animation, score, sound, captions, MP4.
---

# Lonely Astronaut pack

Built and proven on Episode 1, "The Last Message Earth Ever Sent" (5:33, 1080p, 24 fps). Owner's verdict: "more like a movie". This file is the full recipe. Read it top to bottom before starting, then read `STORY.md`.

## 0. What the owner gives you

Usually a block like: WORKING TITLE, THUMBNAIL IDEA, MAIN QUESTION, OPENING 15 SECONDS, PLOT BEATS, PROMISED PAYOFF. Sometimes just a title. Either is enough. Do not ask what style or format: it is always this pack. Ask nothing unless the premise is genuinely unclear. The owner's laptop has **no GPU**; everything renders in the cloud workspace.

## 1. Look (locked; do not reinvent)

- **Astro** = 2D cutouts of the owner's own character art (`assets/c_*.png`, 6 angles + glove + helmet) placed inside **Blender-rendered 3D sets** (`plates/`). His visor eyes are code-drawn (8 expressions + CLOSED, blink, look direction, tremble) so he can act. Never rebuild Astro procedurally in 3D: the owner rejected that as "too cartoonish".
- Holograms (family, people back home) = simple Blender figures with an emission hologram shader, composited additively with scanlines and flicker.
- 2.39:1 letterbox (132 px bars), captions in the bottom bar, film grain, vignette, AgX.
- Colour rule: **cyan = memory/machines/the past, warm amber = living people/hope, red = danger**. Every episode keeps this.
- Cut-out limits: Astro swaps poses between shots and breathes/blinks; he never walks on screen. Hide it with camera moves, close-ups on the eyes, inserts of the glove (`glove()` anchors at the fingertips) and sound.

## 2. Story (the reason it works; full rules in STORY.md)

Write the beat table first and send it to the owner with `SendUserMessage` before spending any credits. Requirements:
- Hook in the first 10 s with **no words**: an on-screen question (screen text, alarm, an object) plus Astro's eyes reacting.
- One personal want, one hard clock or cost, one choice made **before** the payoff is known.
- Plant one small motif early (Ep 1: the height marks + "come home before I get tall") and pay it off 3 times.
- About 150-200 spoken words for 5 minutes. Silence and sound carry the rest. Voices: Astro (first person, dry, short lines) + at most 1-2 other characters, heard through holograms, radio or glass.
- End by answering the title's question clearly, then an end card that reframes it (Ep 1: "THE LAST MESSAGE EARTH EVER SENT / WEIGHED 46 KILOGRAMS.").
- Humanizer rules: no "it's not X, it's Y" / "not X but Y", no AI vocabulary (delve, testament, tapestry, pivotal, showcase, underscore).
- Known weak spot to fix in every new episode: a visual-only travel stretch with no new question (Ep 1, 2:40-3:40). Give journeys a danger or a question.

## 3. Voices

- Higgsfield usually has ~0 credits. Use **vidIQ ElevenLabs voices** (`mcp__VidIQ__vidiq_voiceover_generate`, 28 credits per 1,000 characters, **rounded up per call**): one `scriptLines` call per voice. Astro = "Eric" `cjVigY5qzO86Huf0OWal`. Girl/teen = "Jessica" `cgSgspJ2msm6clMCkdW9`. Check `vidiq_balance` first; budget the script to fit.
- A child voice = Jessica pitched up in the mix (`child` fx). Other fx in `audio.py`: `radio`, `muffled` (through glass), `cut` (signal cut off mid-word).
- **The workspace cannot download from assets.vidiq.com (proxy 403).** Route: open the combined MP3 URL in Claude in Chrome, run JS `fetch(location.href)` → blob → `<a download>` (one file per tab, or Chrome blocks the second), then `device_request_folder_access` for `~/Downloads`, `device_stage_files`, and split lines yourself using the returned `startSeconds` (trim silence at 0.01). Ask the owner once before downloading (filenames, source, size).

## 4. Setup in the workspace

```bash
P=/home/claude/animation-studio/packs/lonely-astronaut
mkdir -p /home/claude/film/{assets,plates,shots,audio,out}
cp $P/engine/*.py /home/claude/film/
cp $P/assets/* /home/claude/film/assets/
cp $P/plates/* /home/claude/film/plates/
cp $P/episodes/01-the-last-message/{shots.py,audio.py} /home/claude/film/   # template, then rewrite
pip install --break-system-packages bpy==5.3.0 rembg onnxruntime   # bpy only if new sets are needed
```
Paths are hard-coded to `/home/claude/film`. Voice WAVs go to `audio/<speaker>_<n>.wav` with `audio/lines.json` (durations).

## 5. Sets (plates.py)

Ready to reuse: `cockpit` (+`chair` foreground layer), `quarters` (hologram table, porthole, height wall), `wallclose`, `cargo` (pod in cradle), `podwindow`, `pod_space`, `ship`, `ship_burn`, `ship_rear`, `neptune`, `holo_child_0-3`, `holo_teen_0-7`. Each has a `.json` of projected screen points for compositing.

New set = new `plate_x()` function in `plates.py`: primitives + bevels, matte materials from the palette, camera, `mark()` the points you need, `render(name, transparent=True)` so space or other layers can show through windows. Draft at 8 samples first, view a contact sheet, fix, then final at 48-64 samples **in the background** (`nohup`). On 2 CPUs a 1080p interior at 64 samples takes ~6 min.

New hologram person: copy `noor()`; soft worried brows are angled up at the outside (`rot=(0, s * 0.18, 0)`); render pose x mouth-open/closed frames; `teen_frame()` picks frames from the voice envelope (lip flap).

## 6. Shots (shots.py)

`SHOTS = [(name, dur, fn(t, T), audio_cues, captions)]`. Reusable shot builders: `helmet_close` (expression close-up, tremble, warm/cyan rim), `cockpit_wide`, `quarters` (Astro foreground + hologram), `holo_close`, `cargo`, `podwindow` (frost melt, hand behind glass, glove), screen UIs (`screen_bg` + `ui_panel` typed text), `space_bg`, `earth(lights, lights_on)`, `sun`, `draw_marks`. Audio cues: `"VO:<line>[:fx]"` or an SFX name from `audio.py`.

Check before the full render: `python3 render.py stills <shot>:<t> ...` then `python3 sheet.py out/x.jpg out/stills/*.jpg` and **look** at the busiest moments. Stills are ~0.5 s each.

## 7. Sound (audio.py)

All synthesised: piano (inharmonic partials), pads, drones, pulses, shimmer, ~30 SFX, 3 reverbs, ducking under VO (music x0.3). The family theme lives in `THEME` (D minor) and `THEME_MAJ` (resolution). Score cues sit at the bottom, keyed by shot start times. After `python3 audio.py`, print per-shot RMS: dialogue shots around -20 to -24 dB, quiet shots no lower than about -32 dB. The workspace cannot play audio; say so honestly and suggest a headphones check.

## 8. Render and deliver

```bash
nohup python3 render.py shots a,b,c > render_a.log 2>&1 &   # 2 processes max (2 CPUs)
python3 assemble.py         # concat, loudnorm -14 LUFS, mux -> out/<title>.mp4
ffmpeg -i "out/<title>.mp4" -c:v libx264 -crf 23 -preset veryfast -c:a copy small.mp4   # ~350 MB delivery copy
```
About 0.2 s per frame (24 fps), so ~30 min per 5 min of film on one process. Pull a frame every ~15 s into a contact sheet and check it before sending with `SendUserFile`.

## 9. Gotchas already paid for

- **Out-of-memory kill:** sprite caches are capped (`maxsize=10`) and `look` is quantised. Keep it that way: trembling eyes otherwise create a new 17 MB sprite every frame.
- Eye auto-detection also catches the backpack ring and wrist screen. `prep_astro.py` keeps manual picks per pose.
- `podwindow` plate renders upside down. It is rotated 180 degrees and the glass is found by connected components.
- Frost melts centre-first (`1 - edge`) so a hand pressed on the glass shows.
- Glove anchor = fingertips `(0.38, 0.97)`; for a palm on glass use `(0.45, 0.62)`.
- Text on a cream hull disappears: use dark label plates.
- Blender `bpy.data.objects[0]` is alphabetical, not creation order.
- Close Chrome tabs you open; one download per tab.
