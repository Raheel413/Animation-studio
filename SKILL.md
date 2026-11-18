---
name: animation-studio
description: Direct a full animated video (60 s to 15 min) from a topic, script or voiceover using this repo's pipeline and style packs. Use when asked to make an animated video, explainer, or animation in any of the repo's styles.
---

# Animation Studio: director skill

You are the director. This repo turns a topic, a script, or a finished voiceover into a rendered MP4. One shared pipeline, one style pack per look. Read this file first, then the SKILL.md of the pack you choose.

## 0. Intake: ask once, then go

Ask the user these in ONE message (skip any they already answered):

1. **Topic or script?** If they have a script, take it as written. If not, you write it (section 2).
2. **Voiceover?** If they have a recording, get the file. If not, generate it with ElevenLabs (section 3). If there is no API key yet, use estimated timing so work is not blocked.
3. **Length and shape:** 60 s Short (9:16) up to 15 min long-form (16:9).
4. **Style pack:** recommend one from the table below; do not offer packs marked "planned".

If the user is not around to answer, pick the most reasonable reading, state it at the top of your work, and continue.

## 1. Style packs

| Pack | Status | Honest ceiling | Use for |
|---|---|---|---|
| `inkline` (vector, cut-paper + ink) | **built** | 9/10 | Research stories, explainers, comparisons, finance, psychology, history |
| `cutout-2d` (rigged puppet characters) | planned | 6/10 | Character-led stories |
| `blender-3d` (Python-driven Blender) | planned | 7/10 stylized | Objects, machines, maps, vehicles |
| `anime` (code-only limited animation) | planned | 4/10 | Action beats, impact frames. Code-only by owner's decision, so no AI keyframes |
| `rotoscope` (trace user-supplied footage) | planned | 7/10 | Stylizing footage the user owns |
| `lonely-astronaut` (Astro cutouts in Blender 3D sets, holograms, synthesized score) | **built** | 8/10 cinematic short | Lonely Astronaut episodes only: read `packs/lonely-astronaut/SKILL.md` |

Never promise "studio level" for a planned pack. Say what the ceiling is.

## 2. Script (when the user has none)

1. Research first. Every factual claim needs a real, citable source found by search. Keep a `sources` list (author, year, publication, finding) for the video description. Nothing unsourced goes in.
2. Follow the chosen pack's story architecture (Inkline: section 2 of its SKILL.md).
3. Length: 150 words per minute. 60 s = ~150 words. 10 min = ~1,500 words. 15 min = ~2,250 words.
4. Voice: second person, present tense, short sentences, concrete objects and numbers.
5. Banned: "it's not X, it's Y" / "not X but Y" / "not because X, but because Y"; the words delve, testament, tapestry, pivotal, showcase, underscore, realm, unleash, game-changer. The validator rejects these.
6. Long videos: plant an open loop in the hook and another near the midpoint; pay both off. One research reveal per 45-75 s.

## 3. Voiceover

- **User recording:** put it in `public/vo/`, set `vo_file`, and set each scene's `t_start`/`t_end` by ear or by a transcription with timestamps.
- **ElevenLabs:** `ELEVENLABS_API_KEY=... node core/scripts/vo_elevenlabs.mjs <scenes.json> --voice <voice_id>`. One request per scene, cached on disk, real timings written back into the file. Ask the user for the key and voice id; never write the key into the repo.
- **No voice yet:** `node core/scripts/timing.mjs <scenes.json>` estimates timings at 150 wpm so you can render a silent draft.

## 4. Beat sheet (`scenes.json`)

The script becomes a list of scenes; each scene is one narration line plus the visual events that happen during it. Schema: `core/schema/scenes.schema.json`. Element vocabulary: the pack's SKILL.md.

Rules for every pack:
- One scene per sentence or clause. A scene longer than ~6 s needs more than one visual event (`at` offsets).
- Every claim gets its own picture. No picture is on screen without a line that needs it.
- On-screen text never repeats the narration. Numbers the narrator says are allowed.
- No source labels on screen. Sources go in the description.
- Named people, companies and places get a drawn visual, not a text card.

## 5. Quality gates (do not skip)

1. `node core/scripts/validate.mjs <scenes.json>` must print `passed`. Fix every ERROR; fix or justify every warning.
2. Render the first 30 s only: `node core/scripts/render.mjs <scenes.json> --to 30`.
3. `node core/scripts/contact_sheet.mjs out/<name>.mp4 --every 2` and LOOK at the sheet. Check: nothing overlapping, nothing cut off, nothing empty for more than a few seconds, text readable, colours match the sides.
4. Show the user the 30 s draft before rendering the rest.
5. Full render, then a second contact sheet (`--every 10` for long videos) and a final look.

## 6. Render

`node core/scripts/render.mjs <scenes.json> [--out out/film.mp4] [--chunk 45]`

Renders in 45-second chunks and joins them, so a 15-minute film fits in 8 GB of RAM. Speed reference: about 6 s of render per 1 s of video on a 2-core machine. A 10-minute film is about an hour there; faster on better hardware. Shorts: set `"width": 1080, "height": 1920` in the film and lay scenes out for a vertical panel.

## 7. Deliver

Give the user: the MP4, the description text with the sources list, 3 title options, and a note of anything that is estimated (for example timings without a real voiceover).

## Adding a pack

Copy the shape of `packs/inkline`: a `SKILL.md` (look, story rules, element vocabulary), a `src/` renderer that reads the same `scenes.json`, and one example. A pack is "built" only after a real video has gone through gates 1-5.
