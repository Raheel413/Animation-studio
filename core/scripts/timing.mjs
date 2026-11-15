#!/usr/bin/env node
// Fills t_start / t_end from the narration when there is no recorded voiceover yet.
// usage: node core/scripts/timing.mjs <scenes.json> [--wpm 150]
import fs from 'node:fs';
const file = process.argv[2];
const wpm = Number(process.argv[process.argv.indexOf('--wpm') + 1]) || 150;
const film = JSON.parse(fs.readFileSync(file, 'utf8'));
let t = 0;
for (const s of film.scenes) {
  const words = s.vo.trim().split(/\s+/).filter(Boolean).length;
  const speak = (words / wpm) * 60 + 0.45; // + breath
  const lastEl = Math.max(0, ...s.elements.map((e) => (e.at ?? 0) + (e.type === 'bars' ? 2.2 : e.type === 'tally' ? 0.4 + e.count * 0.06 : 1.1)));
  const dur = Math.max(1.6, speak, lastEl);
  s.t_start = +t.toFixed(2);
  s.t_end = +(t + dur).toFixed(2);
  t += dur;
}
fs.writeFileSync(file, JSON.stringify(film, null, 2));
console.log(`timed ${film.scenes.length} scenes, total ${t.toFixed(1)}s (estimated at ${wpm} wpm)`);
