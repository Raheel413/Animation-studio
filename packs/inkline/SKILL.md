---
name: inkline-pack
description: Inkline style pack: second-person research stories drawn in ink on a paper strip, rendered with Remotion. Read after the repo's root SKILL.md when the chosen style is inkline.
---

# Inkline: research stories drawn in ink on paper

Daylight paper, cut-paper characters, ink that draws itself, one long strip the camera travels along. No glow, no dark scenes, no stick limbs.

## 1. Originality rules

Inkline exists so the video does not look like the glowing-stickman, navy-night, blue-vs-amber story channels. Never use: dark night worlds, glowing figures, clock-time chapter cards, crowds of figures for sample sizes, one-word yellow captions, neon punch words, a house split down the middle.

| Need | Inkline answer |
|---|---|
| World | Paper strip on a kraft desk, tinted paper `sheet` behind each scene |
| Characters | Geometric cut-paper bodies; the "you" character stays plain paper, others take a side colour |
| Two sides of the story | One accent colour per side (`side: "a"` / `"b"`) |
| Moving on | Camera travels along the strip; `fold` and `ink_flood` for big shifts |
| Section markers | A spine in the margin (`ledger` or `route`) |
| Sample sizes, shares | `tally`, `checkgrid`, `bars` |
| Emphasis | A rubber `stamp`: one short word that judges rather than repeats |

## 2. Story architecture (8-9 min version; scale to length)

1. **Hook, 0:00-0:35.** Second person, inside a situation in line one. Two paths. Research tested it; the result surprises the people who most need it. End on an open loop.
2. **Set-up, to 1:30.** Both paths through the first concrete moment. First research reveal.
3. **Escalation, to 5:30.** 4-6 beats, each a story moment plus one study. Each beat adds a spine line.
4. **Hinge, to 6:45.** One decisive moment, shown twice: path A, then path B.
5. **Time jump, to 8:00.** Weeks later, years later. Final reveal.
6. **Close.** Back to the hinge in one sentence; end on a question to the viewer.

60 s Short: hook, one beat, hinge, question.

## 3. Palette (pick by topic)

| Topic | a | b |
|---|---|---|
| Family / psychology | `#D9472B` | `#1F7A7A` |
| Money / finance | `#2E6B3F` | `#9C3D2E` |
| Military / history | `#5F6B3A` | `#A0522D` |
| Health / habits | `#2F4FA2` | `#C98A1B` |

Always `paper: "#F3EEE3"`, `ink: "#1E1B18"`.

## 4. Film file

```json
{
  "format": "inkline",
  "palette": {"paper": "#F3EEE3", "ink": "#1E1B18", "a": "#2E6B3F", "b": "#9C3D2E"},
  "spine": "ledger",
  "vo_file": null,
  "scenes": [
    {
      "id": "s01", "strip_x": 0, "transition_in": "none",
      "vo": "You're twenty-five. So is Maya.",
      "camera": {"zoom": 1.15, "focus": [900, 520]},
      "spine": {"text": "Maya / month", "value": "$200"},
      "elements": [ ... ]
    }
  ]
}
```

- `strip_x`: panel number on the strip. Use a new number for each scene (0, 1, 2 ...) so drawings do not pile up. Reuse a number only to return to a place on purpose.
- `transition_in`: `travel` (default), `fold`, `ink_flood`, `cut`, `none`. Never the same special transition twice in a row. At most 3 cuts per film.
- `camera`: optional slow push toward `focus` (panel pixels).
- `spine`: optional ledger line added when the scene starts.
- `hold: true`: marks a deliberate slow emotional scene so the validator allows it. At most 2 per film.
- `t_start` / `t_end` are written by the timing or voiceover script. Do not hand-write them.

## 5. Elements

A panel is 1920 x 1080. `x`,`y` are pixels in the panel; `at` is seconds after the scene starts; `scale` enlarges. With a ledger spine keep content left of x = 1400 in the top 420 px.

| type | Fields | Notes |
|---|---|---|
| `character` | `who`, `side`, `mood` (neutral, happy, sad, worried), `holding` (phone, coin), `label`, `enter` (draw, left, right) | `y` is the shoulder line. Scale 1.6-1.9 for main figures |
| `prop` | `kind`: building, desk, coin, phone, calendar, sheet, ground; `text`, `w`, `h`, `rotate` | `sheet` is the tinted backdrop: put it first in every scene. `calendar` + `text` shows an age or year |
| `stamp` | `text`, `rotate`, `side` | One word. At most one per 30 s |
| `tally` | `count`, `side` | For counts up to about 40 |
| `checkgrid` | `total`, `filled`, `cols`, `side` | "1 in 4" = total 20, filled 5 |
| `bars` | `rows[{label, value, display, side}]`, `width` | 2-3 rows |
| `note` | `text`, `size`, `side` | Handwritten. Must add something the narrator did not say |

Layout pattern that works: `sheet` at `at: 0`, `ground` line, main character left third, the data or object right of centre, stamp or note last.

## 6. Pacing

| Where | New visual event at least every |
|---|---|
| 0-15 s | 2.2 s |
| 15-35 s | 3.2 s |
| After | 5.5 s |

The validator enforces this. A visual event is a new element or a transition.

## 7. Sound

Paper foley is automatic (pen on draw-ons, thud on stamps, slide on travel, fold on folds). Regenerate with `npm run sfx`, or replace files in `public/sfx/` with recordings. Music: put a file in `public/` and set `music_file`; it plays at low volume under the voice. Choose sparse acoustic music (felt piano, nylon guitar).

## 8. Not built yet in this pack

Page-peel transition, calendar-tear and gauge spines, walking and gesturing characters, vertical (9:16) layout helpers, see-saw and line-chart data devices. Add them in `src/elements/` when a video needs them.
