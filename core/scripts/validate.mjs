#!/usr/bin/env node
// Quality gate for a scenes.json before any render. Exit code 1 on errors.
// usage: node core/scripts/validate.mjs <scenes.json>
import fs from 'node:fs';
const film = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const errors = [], warns = [];
const E = (id, m) => errors.push(`${id}: ${m}`), W = (id, m) => warns.push(`${id}: ${m}`);
const BANNED = [/\bnot (just |only |because )?[^.,;]{1,40}[,;]? but\b/i, /\bit'?s not [^.]{1,40}, it'?s\b/i, /\b(delve|testament|tapestry|pivotal|showcase|underscore[sd]?|landscape of|realm|unleash|game.changer)\b/i];
const words = (t) => t.toLowerCase().replace(/[^a-z0-9$% ]/g, ' ').split(/\s+/).filter((w) => w.length > 2);
let prevT = null, stamps = [], t0 = film.scenes[0]?.t_start;
if (t0 === undefined) E('film', 'no timings: run timing.mjs or vo_elevenlabs.mjs first');
film.scenes.forEach((s, i) => {
  const dur = s.t_end - s.t_start;
  if (!(dur > 0)) E(s.id, 'scene has no duration');
  if (i && Math.abs(s.t_start - film.scenes[i - 1].t_end) > 0.02) E(s.id, 'gap or overlap with previous scene');
  for (const re of BANNED) if (re.test(s.vo)) E(s.id, `banned phrasing in narration: ${s.vo.match(re)[0]}`);
  // on-screen text must not repeat the narration (numbers are allowed)
  const vo = new Set(words(s.vo));
  for (const e of s.elements) {
    const txt = e.type === 'note' || e.type === 'stamp' ? e.text : null;
    if (txt) {
      const tw = words(txt).filter((w) => !/\d/.test(w));
      if (tw.length && tw.every((w) => vo.has(w))) E(s.id, `on-screen "${txt}" repeats the narration`);
      if (e.type === 'stamp' && txt.trim().split(/\s+/).length > 2) W(s.id, `stamp "${txt}" should be one short word`);
    }
    if (e.type === 'stamp') stamps.push(s.t_start + (e.at ?? 0));
    if ((e.at ?? 0) > dur - 0.4) W(s.id, `${e.type} appears in the last 0.4 s and will be cut short`);
    if (film.spine === 'ledger' && e.type !== 'prop' && e.x > 1400 && e.y < 420) W(s.id, `${e.type} at x=${e.x},y=${e.y} sits under the ledger`);
  }
  // pacing: a visual event (element, transition) at least every N seconds
  const events = [0, ...s.elements.map((e) => e.at ?? 0), ...(s.cues ?? []).map((c) => c.at ?? 0)].sort((a, b) => a - b);
  events.push(dur);
  const maxGap = Math.max(...events.slice(1).map((v, k) => v - events[k]));
  const limit = s.t_start < 15 ? 2.2 : s.t_start < 35 ? 3.2 : 5.5;
  if (maxGap > limit && !s.hold) W(s.id, `${maxGap.toFixed(1)} s with no new visual (limit ${limit} s here; add "hold": true for a deliberate emotional hold)`);
  const tr = s.transition_in ?? 'travel';
  if (i && tr !== 'travel' && tr === prevT) W(s.id, `same special transition (${tr}) twice in a row`);
  prevT = tr;
});
stamps.forEach((t, i) => i && t - stamps[i - 1] < 12 && W('film', `stamps ${(t - stamps[i - 1]).toFixed(0)} s apart at ${t.toFixed(0)} s (keep them rare)`));
if (film.scenes.filter((s) => s.transition_in === 'cut').length > 3) W('film', 'more than 3 hard cuts');
const total = film.scenes.at(-1).t_end;
console.log(`${film.scenes.length} scenes, ${total.toFixed(1)} s`);
warns.forEach((w) => console.log('  warn  ' + w));
errors.forEach((e) => console.log('  ERROR ' + e));
console.log(errors.length ? 'FAILED' : warns.length ? 'passed with warnings' : 'passed');
process.exit(errors.length ? 1 : 0);
