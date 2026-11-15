#!/usr/bin/env node
// Generates the voiceover with Deepgram Aura-2, one request per scene, and writes real timings back into scenes.json.
// usage: DEEPGRAM_API_KEY=... node core/scripts/vo_deepgram.mjs <scenes.json> [--voice aura-2-zeus-en] [--gap 0.35]
// American male voices: aura-2-zeus-en (deep, trustworthy), aura-2-orion-en (calm, approachable),
// aura-2-arcas-en (smooth, clear), aura-2-apollo-en (confident, casual).
// Several speakers: give a scene "speaker": "dee" and map it in the film: "voices": {"narrator": "aura-2-zeus-en", "dee": "aura-2-thalia-en"}.
// --voice overrides the narrator only.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import crypto from 'node:crypto';
const arg = (k, d) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : d);
const key = process.env.DEEPGRAM_API_KEY;
if (!key) { console.error('Set DEEPGRAM_API_KEY'); process.exit(2); }
const narrator = arg('--voice', process.env.DEEPGRAM_VOICE || null);
const file = process.argv[2];
const film = JSON.parse(fs.readFileSync(file, 'utf8'));
const voices = {narrator: 'aura-2-zeus-en', ...(film.voices ?? {}), ...(narrator ? {narrator} : {})};
const voiceFor = (s) => voices[s.speaker ?? 'narrator'] ?? voices.narrator;
const gap = Number(arg('--gap', 0.35));
const name = path.basename(file).replace(/\.scenes\.json$|\.json$/, '');
const dir = `out/vo/${name}`;
fs.mkdirSync(dir, {recursive: true}); fs.mkdirSync('public/vo', {recursive: true});
const seconds = (f) => Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).toString());

async function speak(text, mp3, voice) {
  for (let attempt = 1; attempt <= 4; attempt++) {
    const res = await fetch(`https://api.deepgram.com/v1/speak?model=${voice}&encoding=mp3`, {
      method: 'POST',
      headers: {Authorization: `Token ${key}`, 'content-type': 'application/json'},
      body: JSON.stringify({text}),
    });
    if (res.ok) { fs.writeFileSync(mp3, Buffer.from(await res.arrayBuffer())); return; }
    const body = await res.text();
    if (res.status === 429 || res.status >= 500) { console.warn(`retry ${attempt}: ${res.status}`); await new Promise((r) => setTimeout(r, 2000 * attempt)); continue; }
    console.error(res.status, body); process.exit(1);
  }
  console.error('Deepgram kept failing'); process.exit(1);
}

let t = 0; const parts = [];
for (const s of film.scenes) {
  const voice = voiceFor(s);
  const key = crypto.createHash('sha1').update(voice + '|' + s.vo).digest('hex').slice(0, 10);
  const mp3 = `${dir}/${s.id}-${key}.mp3`;
  if (!fs.existsSync(mp3)) await speak(s.vo, mp3, voice); // cached by voice + text: re-runs cost nothing
  const lastEl = Math.max(0, ...s.elements.map((e) => (e.at ?? 0) + 1));
  const dur = Math.max(seconds(mp3) + (s.gap ?? gap), lastEl);
  s.t_start = +t.toFixed(3); s.t_end = +(t + dur).toFixed(3);
  parts.push({mp3, dur}); t += dur;
  console.log(s.id, dur.toFixed(2) + 's');
}
// pad each line to its scene length, then join and level the loudness
const inputs = parts.flatMap((p) => ['-i', p.mp3]);
const fc = parts.map((p, i) => `[${i}]aresample=44100,apad=whole_dur=${p.dur.toFixed(3)}[a${i}]`).join(';') + ';' + parts.map((_, i) => `[a${i}]`).join('') + `concat=n=${parts.length}:v=0:a=1,loudnorm=I=-16:TP=-1.5[o]`;
execFileSync('ffmpeg', ['-loglevel', 'error', '-y', ...inputs, '-filter_complex', fc, '-map', '[o]', `public/vo/${name}.mp3`]);
film.vo_file = `vo/${name}.mp3`;
fs.writeFileSync(file, JSON.stringify(film, null, 2));
console.log(`voiceover (${Object.values(voices).join(', ')}) ${t.toFixed(1)}s -> public/vo/${name}.mp3; timings written to ${file}`);
