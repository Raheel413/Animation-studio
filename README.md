# Animation Studio

A script-to-video animation pipeline that Claude can run end to end. Give it a topic, a script, or a finished voiceover; it returns a rendered MP4 from 60 seconds to 15 minutes. Everything on screen is drawn by code: no stock footage, no AI-generated video.

One shared pipeline. One pack per visual style.

## Status

| Pack | Status |
|---|---|
| **Inkline** (vector: cut-paper characters and ink on a paper strip) | Built. Sample renders. |
| Cut-out 2D characters | Planned |
| 3D (Blender + Python) | Planned |
| Anime (code-only limited animation) | Planned |
| Rotoscope (traces footage you own) | Planned |

Each planned pack has a design note in `packs/<name>/README.md` with its realistic quality ceiling.

## Quick start

```bash
npm install
npm run sample                                                # render the 24 s sample to out/ten-years.mp4
node core/scripts/timing.mjs  packs/inkline/examples/ten-years.scenes.json   # estimate timings
node core/scripts/validate.mjs packs/inkline/examples/ten-years.scenes.json  # quality gate
node core/scripts/render.mjs   packs/inkline/examples/ten-years.scenes.json  # -> out/ten-years.mp4
node core/scripts/contact_sheet.mjs out/ten-years.mp4                        # frames to review
npm run studio                                                # live preview
```

Needs Node 20+ and ffmpeg on your PATH (check with `ffmpeg -version` in a new terminal). Remotion downloads its own headless browser on the first render. Works on Windows (PowerShell), macOS and Linux. Paper sound effects ship in `public/sfx/`; `npm run sfx` rebuilds them.

## Render in the cloud (GitHub Actions)

You don't need to render on your own machine. Push a scenes file into `films/` and GitHub renders it, or go to **Actions → Render video → Run workflow** and give it any scenes file. The MP4 and a contact sheet show up under **Artifacts** on the run page. See `films/README.md`.

## With Claude

Open the repo in Claude Code and say: *"Read SKILL.md and make a 3-minute Inkline video about ..."*. `SKILL.md` is the director's manual: intake questions, script rules, voiceover, beat sheet, quality gates, render. Each pack has its own `SKILL.md` with the look and the element vocabulary.

## Pipeline

```
topic / script / voiceover
   -> research + script            (SKILL.md section 2)
   -> scenes.json beat sheet       (core/schema/scenes.schema.json)
   -> voiceover + real timings     (core/scripts/vo_elevenlabs.mjs, or timing.mjs for a silent draft)
   -> validate                     (core/scripts/validate.mjs)
   -> render in chunks             (core/scripts/render.mjs)
   -> contact sheet review         (core/scripts/contact_sheet.mjs)
```

## Voiceover

```bash
ELEVENLABS_API_KEY=... node core/scripts/vo_elevenlabs.mjs my.scenes.json --voice <voice_id>
```

Generates one clip per scene (cached), joins them, and writes real scene timings back into the file. This script has not yet been run against a live key.

## Known limits

- Only the Inkline pack exists. The sample is a 23-second hook, not a full film.
- Render speed is about 6 s per second of video on 2 CPU cores.
- No music is included. Sound effects are synthesized.
- Inkline characters stand, bob, blink and change mood. They do not walk or gesture yet.

## License

MIT
