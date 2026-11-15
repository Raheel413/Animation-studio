#!/usr/bin/env node
// Synthesizes the paper-foley set with ffmpeg (Windows, macOS, Linux).
// Replace any file in public/sfx with a recorded one for more realism.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const o = 'public/sfx';
fs.mkdirSync(o, {recursive: true});
const run = (args, name) => {
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', ...args, `${o}/${name}`], {stdio: 'inherit'});
  console.log('made', name);
};
try { execFileSync('ffmpeg', ['-version'], {stdio: 'ignore'}); }
catch { console.error('ffmpeg not found. Install it and make sure "ffmpeg -version" works in a new terminal.'); process.exit(1); }
run(['-f', 'lavfi', '-i', 'anoisesrc=d=0.9:c=pink:a=0.5', '-af', 'highpass=f=2500,lowpass=f=7500,tremolo=f=19:d=0.9,afade=t=in:d=0.04,afade=t=out:st=0.6:d=0.3'], 'pen.wav');
run(['-f', 'lavfi', '-i', 'anoisesrc=d=0.35:c=pink:a=0.5', '-af', 'highpass=f=2800,lowpass=f=8000,tremolo=f=24:d=0.9,afade=t=out:st=0.2:d=0.15'], 'pen_short.wav');
run(['-f', 'lavfi', '-i', 'anoisesrc=d=0.7:c=brown:a=0.9', '-af', 'highpass=f=500,lowpass=f=3800,afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.4'], 'slide.wav');
run(['-f', 'lavfi', '-i', 'anoisesrc=d=0.5:c=white:a=0.5', '-af', 'highpass=f=1200,lowpass=f=6000,afade=t=in:d=0.02,afade=t=out:st=0.08:d=0.4,aecho=0.6:0.3:35:0.3'], 'fold.wav');
run(['-f', 'lavfi', '-i', 'sine=f=68:d=0.35', '-f', 'lavfi', '-i', 'anoisesrc=d=0.08:c=brown:a=1', '-filter_complex', '[0]afade=t=out:st=0.02:d=0.3,volume=2.2[a];[1]lowpass=f=1800,afade=t=out:d=0.08[b];[a][b]amix=inputs=2:normalize=0'], 'stamp.wav');
run(['-f', 'lavfi', '-i', 'anoisesrc=d=1.2:c=white:a=0.6', '-af', 'highpass=f=3000,tremolo=f=11:d=1,afade=t=out:st=0.9:d=0.3'], 'ticks.wav');
