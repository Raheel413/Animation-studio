#!/usr/bin/env node
// Generates the voiceover with ElevenLabs, one request per scene, and writes real timings back into scenes.json.
// usage: ELEVENLABS_API_KEY=... node core/scripts/vo_elevenlabs.mjs <scenes.json> --voice <voice_id> [--model eleven_multilingual_v2] [--gap 0.35]
// NOTE: written against the documented /with-timestamps endpoint; not yet run with a live key.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const arg = (k, d) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : d);
const key = process.env.ELEVENLABS_API_KEY;
const voice = arg('--voice', process.env.ELEVENLABS_VOICE_ID);
if (!key || !voice) { console.error('Set ELEVENLABS_API_KEY and pass --voice <voice_id>'); process.exit(2); }
const file = process.argv[2];
const film = JSON.parse(fs.readFileSync(file, 'utf8'));
const gap = Number(arg('--gap', 0.35));
const name = path.basename(file).replace(/\.scenes\.json$|\.json$/, '');
const dir = `out/vo/${name}`;
fs.mkdirSync(dir, {recursive: true}); fs.mkdirSync('public/vo', {recursive: true});
let t = 0; const parts = [];
for (const [i, s] of film.scenes.entries()) {
  const mp3 = `${dir}/${s.id}.mp3`;
  let speech;
  if (fs.existsSync(mp3) && fs.existsSync(mp3 + '.json')) speech = JSON.parse(fs.readFileSync(mp3 + '.json', 'utf8')); // cached: re-runs cost nothing
  else {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voice}/with-timestamps?output_format=mp3_44100_128`, {
      method: 'POST', headers: {'xi-api-key': key, 'content-type': 'application/json'},
      body: JSON.stringify({text: s.vo, model_id: arg('--model', 'eleven_multilingual_v2'), previous_text: film.scenes[i - 1]?.vo, next_text: film.scenes[i + 1]?.vo}),
    });
    if (!res.ok) { console.error(s.id, res.status, await res.text()); process.exit(1); }
    const j = await res.json();
    fs.writeFileSync(mp3, Buffer.from(j.audio_base64, 'base64'));
    speech = {end: j.alignment.character_end_times_seconds.at(-1), alignment: j.alignment};
    fs.writeFileSync(mp3 + '.json', JSON.stringify(speech));
  }
  const lastEl = Math.max(0, ...s.elements.map((e) => (e.at ?? 0) + 1));
  const dur = Math.max(speech.end + gap, lastEl);
  s.t_start = +t.toFixed(3); s.t_end = +(t + dur).toFixed(3);
  parts.push({mp3, dur}); t += dur;
  console.log(s.id, dur.toFixed(2) + 's');
}
// pad each line to its scene length, then join
const inputs = parts.flatMap((p) => ['-i', p.mp3]);
const fc = parts.map((p, i) => `[${i}]apad=whole_dur=${p.dur.toFixed(3)}[a${i}]`).join(';') + ';' + parts.map((_, i) => `[a${i}]`).join('') + `concat=n=${parts.length}:v=0:a=1,loudnorm=I=-16:TP=-1.5[o]`;
execFileSync('ffmpeg', ['-loglevel', 'error', '-y', ...inputs, '-filter_complex', fc, '-map', '[o]', `public/vo/${name}.mp3`]);
film.vo_file = `vo/${name}.mp3`;
fs.writeFileSync(file, JSON.stringify(film, null, 2));
console.log(`voiceover ${t.toFixed(1)}s -> public/vo/${name}.mp3; timings written to ${file}`);
