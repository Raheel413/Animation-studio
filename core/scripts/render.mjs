#!/usr/bin/env node
// Chunked render: renders the film in ~45 s pieces and joins them with ffmpeg, so long videos fit in 8 GB RAM.
// usage: node core/scripts/render.mjs <scenes.json> [--out out/film.mp4] [--chunk 45] [--scale 1] [--from 0] [--to 30]
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
const arg = (k, d) => (process.argv.includes(k) ? process.argv[process.argv.indexOf(k) + 1] : d);
const file = process.argv[2];
const film = JSON.parse(fs.readFileSync(file, 'utf8'));
const fps = film.fps ?? 30;
const total = Math.ceil((film.scenes.at(-1).t_end + 0.6) * fps);
const out = arg('--out', `out/${path.basename(file).replace(/\.scenes\.json$|\.json$/, '')}.mp4`);
const chunk = Number(arg('--chunk', 45)) * fps;
const first = Math.round(Number(arg('--from', 0)) * fps);
const last = Math.min(total, Math.round(Number(arg('--to', total / fps)) * fps)) - 1;
const entry = `packs/${film.format}/src/index.ts`;
const cli = path.resolve('node_modules/@remotion/cli/remotion-cli.js');
const browser = process.env.CHROME_PATH || (fs.existsSync('/usr/bin/google-chrome') ? '/usr/bin/google-chrome' : null);
fs.mkdirSync(path.dirname(out), {recursive: true});
const tmp = fs.mkdtempSync(path.join(path.dirname(out), '.chunks-'));
const propsFile = path.join(tmp, 'props.json');
fs.writeFileSync(propsFile, JSON.stringify({film}));
const parts = [];
for (let a = first; a <= last; a += chunk) {
  const b = Math.min(last, a + chunk - 1);
  const part = path.join(tmp, `part-${String(parts.length).padStart(3, '0')}.mp4`);
  console.log(`rendering frames ${a}-${b} of ${total}`);
  // call the Remotion CLI through node directly: works the same on Windows, macOS and Linux
  execFileSync(process.execPath, [cli, 'render', entry, 'Inkline', part, `--props=${propsFile}`, `--frames=${a}-${b}`, `--scale=${arg('--scale', 1)}`, `--concurrency=${process.env.REMOTION_CONCURRENCY || 2}`, '--log=error', ...(browser ? [`--browser-executable=${browser}`] : [])], {stdio: 'inherit'});
  parts.push(part);
}
if (parts.length === 1) fs.copyFileSync(parts[0], out);
else {
  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, parts.map((p) => `file '${path.resolve(p)}'`).join('\n'));
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', out]);
}
fs.rmSync(tmp, {recursive: true, force: true});
console.log('wrote', out);
