import React from 'react';
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import {Actor} from './elements/Actor';
import {Sprite} from './elements/Sprite';
import {Captions, Layered, Photo} from './elements/Photo';
import '@fontsource/anton/400.css';
import {shotEnd, shotStart} from './shots';
import '@fontsource/playfair-display/900.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/fraunces/900.css';
import '@fontsource/caveat/700.css';
import {clamp, InkDefs, prog} from './ink';
import {Character} from './elements/Character';
import {Bars, CheckGrid, Note, Prop, Stamp, Tally} from './elements/Parts';
import {Clipping, LineChart} from './elements/News';
import type {ActorEl, El, Film, Scene} from './types';

const PANEL = 1920;
const TRAVEL = 20; // frames a strip travel takes

/** Foley cues for an element: [file, seconds after it appears, volume]. */
const sfxFor = (el: El): [string, number, number][] => {
  switch (el.type) {
    case 'stamp':
      return [['stamp.wav', 0, 0.45]];
    case 'clipping':
      return [['slide.wav', 0, 0.22], ['marker.wav', 0.75, 0.3], ...(el.ring ? ([['penring.wav', 1.3, 0.3]] as [string, number, number][]) : [])];
    case 'bars':
      return [['ticker.wav', 0.35, 0.18]];
    case 'prop':
      return el.kind === 'calendar' ? [['shutter.wav', 0.1, 0.3]] : [];
    default:
      return [];
  }
};

export {shotStart, shotEnd};

/** Camera: travels along the strip between shots; inside a shot it eases between framings and drifts slowly. */
const useCamera = (film: Film, frame: number, fps: number) => {
  const scenes = film.scenes;
  let i = scenes.findIndex((s) => frame < s.t_end * fps);
  if (i < 0) i = scenes.length - 1;
  const s = scenes[i];
  const local = frame - s.t_start * fps;
  const j0 = shotStart(scenes, i);
  const framing = (k: number) => {
    // a scene keeps the framing of the scene before it in the same shot unless it sets its own
    for (let q = k; q >= j0; q--) if (scenes[q].camera) return scenes[q].camera!;
    return {zoom: 1.0, focus: [960, 540] as [number, number]};
  };
  const at = (k: number) => {
    const c = framing(k);
    return {cx: scenes[k].strip_x * PANEL + (c.focus?.[0] ?? 960), cy: c.focus?.[1] ?? 540, z: c.zoom ?? 1};
  };
  const now = at(i);
  const prev = i > j0 ? at(i - 1) : now;
  const t = interpolate(local, [0, 1.4 * fps], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const shotT = (frame - scenes[j0].t_start * fps) / fps;
  const drift = {x: shotT * 3, z: 0.06 * (1 - Math.exp(-shotT / 9))};
  let cx = prev.cx + (now.cx - prev.cx) * t + drift.x;
  let cy = prev.cy + (now.cy - prev.cy) * t;
  let z = prev.z + (now.z - prev.z) * t + drift.z;
  if (i === j0 && i > 0 && (s.transition_in ?? 'travel') === 'travel') {
    const pe = shotStart(scenes, i - 1);
    const pc = at(i - 1);
    const pT = (s.t_start - scenes[pe].t_start);
    const from = {cx: pc.cx + pT * 3, cy: pc.cy, z: pc.z + 0.06 * (1 - Math.exp(-pT / 9))};
    const tt = interpolate(local, [0, TRAVEL], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
    cx = from.cx + (cx - from.cx) * tt;
    cy = from.cy + (cy - from.cy) * tt;
    z = from.z + (z - from.z) * tt - Math.sin(tt * Math.PI) * 0.05;
  }
  // camera shake: 3 px for 0.2 s when a scene marks a crash
  for (const sc of scenes) {
    if (sc.shake === undefined) continue;
    const d = frame - (sc.t_start + sc.shake) * fps;
    if (d >= 0 && d < 0.2 * fps) {
      cx += Math.sin(d * 2.7) * 3;
      cy += Math.cos(d * 3.3) * 3;
    }
  }
  return {cx, cy, z, scene: s, index: i, local};
};

/** Actor state from the cues of its shot: pose cues, and walking (x offset, phase, blend, facing). */
const actorState = (film: Film, si: number, el: ActorEl, frame: number, fps: number) => {
  const scenes = film.scenes;
  const startF = (scenes[si].t_start + (el.at ?? 0)) * fps;
  const e = shotEnd(scenes, si);
  const cues: {f: number; pose?: string; mood?: string; look?: number; face?: 1 | -1}[] = [];
  const walks: {f0: number; f1: number; to: number}[] = [];
  for (let k = si; k <= e; k++) {
    for (const c of scenes[k].cues ?? []) {
      if (c.who !== el.who) continue;
      const f = (scenes[k].t_start + (c.at ?? 0)) * fps - startF;
      cues.push({f, pose: c.pose, mood: c.mood, look: c.look, face: c.face});
      if (c.walkTo !== undefined) walks.push({f0: f, f1: f + (c.walkDur ?? 1.6) * fps, to: c.walkTo});
    }
  }
  const lf = frame - startF;
  let x = el.x;
  let walking = 0;
  let dist = 0;
  let face: 1 | -1 = el.face ?? 1;
  for (const c of cues) if (c.face && lf >= c.f) face = c.face;
  for (const w of walks) {
    const from = x;
    if (lf <= w.f0) break;
    const t = interpolate(lf, [w.f0, w.f1], [0, 1], {...clamp, easing: Easing.inOut(Easing.sin)});
    x = from + (w.to - from) * t;
    dist += Math.abs(w.to - from) * t;
    if (lf < w.f1) {
      walking = Math.min(1, Math.min(lf - w.f0, w.f1 - lf) / 6);
      face = w.to >= from ? 1 : -1;
    }
  }
  return {cues, dx: x - el.x, walking, phase: dist / 26, face};
};

const Element: React.FC<{el: El; f: number; film: Film; id: string; seed: number; si: number; frame: number; fps: number; amp: number}> = ({el, f, film, id, seed, si, frame, fps, amp}) => {
  if (f < 0) return null;
  const pal = film.palette;
  switch (el.type) {
    case 'actor': {
      const st = actorState(film, si, el, frame, fps);
      const speaking = film.scenes.find((s) => frame >= s.t_start * fps && frame < s.t_end * fps)?.speaker === el.who;
      return (
        <g transform={`translate(${st.dx / (el.scale ?? 1)},0)`}>
          <Actor el={el} f={f} pal={pal} seed={seed} fps={fps} cues={st.cues} amp={speaking ? amp : 0} walkX={st.dx} walking={st.walking} walkPhase={st.phase} face={st.face} />
        </g>
      );
    }
    case 'character':
      return <Character el={el} f={f} pal={pal} seed={seed} />;
    case 'stamp':
      return <Stamp el={el} f={f} pal={pal} />;
    case 'tally':
      return <Tally el={el} f={f} pal={pal} />;
    case 'note':
      return <Note el={el} f={f} pal={pal} id={id} />;
    case 'bars':
      return <Bars el={el} f={f} pal={pal} />;
    case 'checkgrid':
      return <CheckGrid el={el} f={f} pal={pal} />;
    case 'prop':
      return <Prop el={el} f={f} pal={pal} />;
    case 'clipping':
      return <Clipping el={el} f={f} pal={pal} id={id} />;
    case 'desk':
      return <rect x={-el.w / 2} y={-el.h / 2} width={el.w} height={el.h} rx={18} fill="#181A1F" opacity={Math.min(1, f / 8)} style={{filter: 'drop-shadow(0 6px 18px rgba(0,0,0,.22))'}} />;
    case 'tag':
      return (
        <text x={0} y={0} fontFamily="JetBrains Mono" fontSize={26} letterSpacing={1} fill={el.dark ? '#E9E4D8' : '#3A3A3A'} opacity={Math.min(1, f / 10)}>
          {el.text.toUpperCase()}
        </text>
      );
    case 'linechart':
      return <LineChart el={el} f={f} pal={pal} />;
    default:
      return null;
  }
};

/** Ledger spine: a ruled paper column fixed in the margin; each scene may add one handwritten line. */
const Ledger: React.FC<{film: Film; frame: number; fps: number}> = ({film, frame, fps}) => {
  const rows = film.scenes.filter((s) => s.spine);
  if (!rows.length) return null;
  const first = rows[0].t_start * fps;
  const slide = interpolate(frame, [first - 4, first + 14], [520, 0], {...clamp, easing: Easing.out(Easing.cubic)});
  return (
    <div style={{position: 'absolute', right: 44, top: 84, width: 440, transform: `translateX(${slide}px) rotate(1.2deg)`, filter: 'drop-shadow(4px 6px 0 rgba(70,50,25,.18))'}}>
      <svg width={440} height={90 + rows.length * 64} style={{overflow: 'visible'}}>
        <rect width={440} height={90 + rows.length * 64} rx={6} fill="#FBF8F1" stroke={film.palette.ink} strokeWidth={3} />
        <line x1={52} y1={0} x2={52} y2={90 + rows.length * 64} stroke={film.palette.a} strokeWidth={2} opacity={0.6} />
        <text x={70} y={50} fontFamily="Fraunces" fontWeight={900} fontSize={30} letterSpacing={3} fill={film.palette.ink}>
          LEDGER
        </text>
        {rows.map((s, i) => {
          const f = frame - s.t_start * fps - 8;
          const y = 108 + i * 64;
          const p = prog(f, 0, 14, Easing.linear);
          return (
            <g key={s.id}>
              <line x1={0} y1={y + 14} x2={440} y2={y + 14} stroke={film.palette.ink} strokeWidth={1} opacity={0.25} />
              <clipPath id={`led-${i}`}>
                <rect x={60} y={y - 40} width={380 * p} height={60} />
              </clipPath>
              <g clipPath={`url(#led-${i})`} fontFamily="Caveat" fontWeight={700} fontSize={40} fill={film.palette.ink}>
                <text x={68} y={y}>{s.spine!.text}</text>
                <text x={424} y={y} textAnchor="end" fill={film.palette.a}>{s.spine!.value ?? ''}</text>
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

/** Route spine: dotted ink line along the bottom with a pin that advances each scene. */
const Route: React.FC<{film: Film; frame: number; fps: number; index: number; local: number}> = ({film, index, local}) => {
  const n = film.scenes.length;
  const t = interpolate(local, [0, 18], [Math.max(0, index - 1), index], {...clamp, easing: Easing.inOut(Easing.cubic)});
  const x = 120 + (t / Math.max(1, n - 1)) * 1680;
  return (
    <svg width={1920} height={90} style={{position: 'absolute', bottom: 24, left: 0}}>
      <line x1={120} y1={60} x2={1800} y2={60} stroke={film.palette.ink} strokeWidth={4} strokeDasharray="4 16" strokeLinecap="round" />
      <g transform={`translate(${x},60)`}>
        <path d="M0,0 C-22,-28 -18,-52 0,-52 C18,-52 22,-28 0,0 z" fill={film.palette.a} stroke={film.palette.ink} strokeWidth={3.5} />
        <circle cx={0} cy={-34} r={6} fill="#FBF8F1" />
      </g>
    </svg>
  );
};

/** Torn top and bottom edges: the story lives on a paper strip lying on a kraft desk. */
const EDGE = (() => {
  // one period of a jagged edge, 1920 wide, repeats seamlessly
  let top = 'M0,0 H3840 V46 ';
  let bot = 'M0,120 H3840 V74 ';
  for (let x = 3840; x >= 0; x -= 24) {
    const j = Math.sin(x * 0.0131 * Math.PI * 2 * (1920 / 1920)) * 5 + ((x * 7919) % 13) - 6;
    const jj = x % 1920 === 0 ? 0 : j;
    top += `L${x},${46 + jj} `;
    bot += `L${x},${74 - jj} `;
  }
  return {top: top + 'Z', bot: bot + 'Z'};
})();
const StripEdges: React.FC<{film: Film; tx: number; z: number}> = ({tx, z}) => {
  const off = (((tx % 1920) + 1920) % 1920) - 1920;
  const grow = (z - 1) * 60; // edges leave the frame as the camera pushes in
  const desk = '#CDBE9F';
  return (
    <>
      <svg width={3840} height={60} style={{position: 'absolute', top: -grow, left: off, filter: 'drop-shadow(0 5px 5px rgba(60,40,15,.28))'}}>
        <path d={EDGE.top} fill={desk} />
      </svg>
      <svg width={3840} height={120} viewBox="0 0 3840 120" style={{position: 'absolute', bottom: -grow, left: off, filter: 'drop-shadow(0 -4px 5px rgba(60,40,15,.22))'}}>
        <path d={EDGE.bot} fill={desk} />
      </svg>
    </>
  );
};

/** Full-screen transitions that hide a camera jump. */
const Transition: React.FC<{film: Film; frame: number; fps: number}> = ({film, frame, fps}) => {
  const hit = film.scenes.find((s, i) => i > 0 && (s.transition_in === 'ink_flood' || s.transition_in === 'fold') && Math.abs(frame - s.t_start * fps) <= 13);
  if (!hit) return null;
  const local = frame - hit.t_start * fps; // -13..13, camera jumps at 0
  if (hit.transition_in === 'ink_flood') {
    const side = hit.elements.find((e) => e.side)?.side ?? 'a';
    const color = side === 'b' ? film.palette.b : film.palette.a;
    const r = local < 0 ? interpolate(local, [-13, 0], [0, 150], {...clamp, easing: Easing.in(Easing.quad)}) : 150;
    const out = local >= 0 ? interpolate(local, [0, 13], [0, 150], {...clamp, easing: Easing.out(Easing.quad)}) : 0;
    return (
      <AbsoluteFill>
        <svg width="100%" height="100%" viewBox="0 0 192 108" preserveAspectRatio="none">
          <mask id="flood">
            <rect width={192} height={108} fill="black" />
            <circle cx={60} cy={70} r={r} fill="white" filter="url(#wobble)" />
            <circle cx={140} cy={40} r={out} fill="black" />
          </mask>
          <rect width={192} height={108} fill={color} mask="url(#flood)" />
        </svg>
      </AbsoluteFill>
    );
  }
  // fold: a paper sheet sweeps across with a crease shadow
  const x = interpolate(local, [-13, 13], [-110, 110], {...clamp, easing: Easing.inOut(Easing.cubic)});
  return (
    <AbsoluteFill style={{perspective: 1600}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          left: '-5%',
          width: '110%',
          transform: `translateX(${x}%) rotateY(${x * 0.12}deg)`,
          backgroundColor: film.palette.paper,
          backgroundImage: `linear-gradient(90deg, rgba(60,40,20,.28), rgba(60,40,20,0) 6%, rgba(60,40,20,0) 94%, rgba(60,40,20,.28)), url(${staticFile('paper.png')})`,
          boxShadow: '0 0 80px rgba(40,25,10,.45)',
        }}
      />
    </AbsoluteFill>
  );
};

/** Voice loudness (0..1) at the current frame, for lip-sync. */
const WithVoice: React.FC<{film: Film}> = ({film}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const audioData = useAudioData(staticFile(film.vo_file!));
  let amp = 0;
  if (audioData) {
    const bins = visualizeAudio({fps, frame, audioData, numberOfSamples: 32});
    amp = Math.min(1, (bins.slice(1, 12).reduce((a, b) => a + b, 0) / 11) * 7);
  }
  return <InklineFilm film={film} amp={amp} />;
};

export const Inkline: React.FC<{film: Film}> = ({film}) => (film.vo_file ? <WithVoice film={film} /> : <InklineFilm film={film} amp={-1} />);

const InklineFilm: React.FC<{film: Film; amp: number}> = ({film, amp: voiceAmp}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  // without a voice file, speakers flap their mouths so drafts still read
  const amp = voiceAmp >= 0 ? voiceAmp : Math.max(0, Math.sin(frame * 0.8)) * 0.7;
  const cam = useCamera(film, frame, fps);
  const k = width / PANEL; // lets the same film render at other sizes

  const tx = PANEL / 2 - cam.cx * cam.z;
  const ty = 540 - cam.cy * cam.z;

  return (
    <AbsoluteFill style={{backgroundColor: film.palette.paper}}>
      <InkDefs />
      <div style={{position: 'absolute', width: PANEL, height: 1080, transform: `scale(${k})`, transformOrigin: '0 0', overflow: 'hidden'}}>
        {/* paper: texture scrolls with the camera so the strip feels physical */}
        <AbsoluteFill style={{backgroundImage: `url(${staticFile('paper.png')})`, backgroundPosition: `${tx}px ${ty}px`, backgroundSize: `${1024 * cam.z}px`}} />

        {/* the strip */}
        <div style={{position: 'absolute', transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${cam.z})`}}>
          {film.scenes.map((s, si) => {
            if (Math.abs(s.strip_x * PANEL + PANEL / 2 - cam.cx) > PANEL * 1.6) return null; // cull far panels
            const start = s.t_start * fps;
            const last = (el: El) => film.scenes[Math.min(el.life ? si + el.life - 1 : shotEnd(film.scenes, si), shotEnd(film.scenes, si))];
            return s.elements.map((el, ei) => {
              const endF = last(el).t_end * fps;
              if (frame > endF + 1 && last(el) !== film.scenes[shotEnd(film.scenes, si)]) return null;
              const fade = el.life ? interpolate(frame, [endF - 8, endF], [1, 0], clamp) : 1;
              if (el.type === 'layered') {
                return (
                  <div key={`${s.id}-${ei}`} style={{opacity: fade}}>
                    <Layered el={el} f={frame - start - (el.at ?? 0) * fps} dur={(last(el).t_end - s.t_start) * fps} left={s.strip_x * PANEL + el.x} seed={si} amp={amp} />
                  </div>
                );
              }
              if (el.type === 'photo') {
                return (
                  <div key={`${s.id}-${ei}`} style={{opacity: fade}}>
                    <Photo el={el} f={frame - start - (el.at ?? 0) * fps} dur={(last(el).t_end - s.t_start) * fps} left={s.strip_x * PANEL + el.x} seed={si} />
                  </div>
                );
              }
              if (el.type === 'sprite') {
                const speaker = film.scenes[cam.index].speaker ?? 'narrator';
                return (
                  <div key={`${s.id}-${ei}`} style={{opacity: fade}}>
                    <Sprite el={el} film={film} si={si} frame={frame} fps={fps} amp={amp} speaking={speaker === el.who} left={s.strip_x * PANEL + el.x} />
                  </div>
                );
              }
              return (
                <svg
                  key={`${s.id}-${ei}`}
                  style={{position: 'absolute', left: s.strip_x * PANEL + el.x, top: el.y, overflow: 'visible', opacity: fade}}
                  width={1}
                  height={1}
                >
                  <g transform={`scale(${el.scale ?? 1})`}>
                    <Element el={el} f={frame - start - (el.at ?? 0) * fps} film={film} id={`${s.id}-${ei}`} seed={si * 7 + ei} si={si} frame={frame} fps={fps} amp={amp} />
                  </g>
                </svg>
              );
            });
          })}
        </div>

        {film.spine === 'ledger' && <Ledger film={film} frame={frame} fps={fps} />}
        {film.spine === 'route' && <Route film={film} frame={frame} fps={fps} index={cam.index} local={cam.local} />}
        <StripEdges film={film} tx={tx} z={cam.z} />
        <Transition film={film} frame={frame} fps={fps} />
        {film.captions && <Captions text={cam.scene.vo} local={cam.local} dur={(cam.scene.t_end - cam.scene.t_start) * fps} />}
        {/* soft paper vignette, no glow */}
        <AbsoluteFill style={{boxShadow: 'inset 0 0 220px rgba(90,65,30,.22)'}} />
      </div>

      {/* sound */}
      {film.vo_file && <Audio src={staticFile(film.vo_file)} />}
      {film.music_file && <Audio src={staticFile(film.music_file)} volume={0.12} />}
      {film.sfx !== false &&
        film.scenes.flatMap((s, si) => {
          const start = Math.round(s.t_start * fps);
          const out: React.ReactNode[] = [];
          if (si > 0 && s.strip_x !== film.scenes[si - 1].strip_x && (s.transition_in ?? 'travel') !== 'cut') {
            out.push(
              <Sequence key={`${s.id}-tr`} from={Math.max(0, start - (s.transition_in === 'travel' || !s.transition_in ? 0 : 12))} durationInFrames={40}>
                <Audio src={staticFile(s.transition_in === 'fold' ? 'sfx/fold.wav' : 'sfx/slide.wav')} volume={0.16} />
              </Sequence>,
            );
          }
          s.elements.forEach((el, ei) => {
            sfxFor(el).forEach(([file, dt, vol], k) =>
              out.push(
                <Sequence key={`${s.id}-${ei}-sfx${k}`} from={start + Math.round(((el.at ?? 0) + dt) * fps)} durationInFrames={45}>
                  <Audio src={staticFile(`sfx/${file}`)} volume={vol} />
                </Sequence>,
              ),
            );
          });
          if (s.shake !== undefined)
            out.push(
              <Sequence key={`${s.id}-thud`} from={start + Math.round(s.shake * fps)} durationInFrames={40}>
                <Audio src={staticFile('sfx/thud.wav')} volume={0.55} />
              </Sequence>,
            );
          return out;
        })}
    </AbsoluteFill>
  );
};
