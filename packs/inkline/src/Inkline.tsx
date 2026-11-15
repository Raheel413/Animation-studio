import React from 'react';
import {AbsoluteFill, Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import '@fontsource/fraunces/900.css';
import '@fontsource/caveat/700.css';
import {clamp, InkDefs, prog} from './ink';
import {Character} from './elements/Character';
import {Bars, CheckGrid, Note, Prop, Stamp, Tally} from './elements/Parts';
import {Clipping, LineChart} from './elements/News';
import type {El, Film, Scene} from './types';

const PANEL = 1920;
const TRAVEL = 20; // frames a strip travel takes

const sfxFor = (el: El): string | null =>
  el.type === 'stamp' ? 'stamp.wav' : el.type === 'clipping' ? 'slide.wav' : el.type === 'tally' || el.type === 'checkgrid' ? 'ticks.wav' : el.type === 'note' ? 'pen_short.wav' : 'pen.wav';

/** Camera: travels along the strip between scenes, drifts and zooms inside a scene. */
const useCamera = (film: Film, frame: number, fps: number) => {
  const scenes = film.scenes;
  let i = scenes.findIndex((s) => frame < s.t_end * fps);
  if (i < 0) i = scenes.length - 1;
  const s = scenes[i];
  const prev = scenes[Math.max(0, i - 1)];
  const start = s.t_start * fps;
  const len = Math.max(1, (s.t_end - s.t_start) * fps);
  const local = frame - start;

  const target = (sc: Scene, t: number) => {
    const z = interpolate(t, [0, 1], [1, sc.camera?.zoom ?? 1.04], clamp);
    const fx = sc.camera?.focus?.[0] ?? PANEL / 2;
    const fy = sc.camera?.focus?.[1] ?? 540;
    const pull = sc.camera?.zoom ? interpolate(t, [0, 1], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)}) : 0;
    return {
      cx: sc.strip_x * PANEL + interpolate(pull, [0, 1], [PANEL / 2, fx]) + t * 26, // slow dolly
      cy: interpolate(pull, [0, 1], [540, fy]),
      z,
    };
  };

  const now = target(s, local / len);
  const kind = s.transition_in ?? 'travel';
  if (i === 0 || kind !== 'travel') return {...now, scene: s, index: i, local};
  const from = target(prev, 1);
  const t = interpolate(local, [0, TRAVEL], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
  return {
    cx: interpolate(t, [0, 1], [from.cx, now.cx]),
    cy: interpolate(t, [0, 1], [from.cy, now.cy]),
    // slight pull-back mid-travel so the move reads as a physical camera
    z: interpolate(t, [0, 1], [from.z, now.z]) - Math.sin(t * Math.PI) * 0.06,
    scene: s,
    index: i,
    local,
  };
};

const Element: React.FC<{el: El; f: number; film: Film; id: string; seed: number}> = ({el, f, film, id, seed}) => {
  if (f < 0) return null;
  const pal = film.palette;
  switch (el.type) {
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

export const Inkline: React.FC<{film: Film}> = ({film}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
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
            return s.elements.map((el, ei) => (
              <svg
                key={`${s.id}-${ei}`}
                style={{position: 'absolute', left: s.strip_x * PANEL + el.x, top: el.y, overflow: 'visible'}}
                width={1}
                height={1}
              >
                <g transform={`scale(${el.scale ?? 1})`}>
                  <Element el={el} f={frame - start - (el.at ?? 0) * fps} film={film} id={`${s.id}-${ei}`} seed={si * 7 + ei} />
                </g>
              </svg>
            ));
          })}
        </div>

        {film.spine === 'ledger' && <Ledger film={film} frame={frame} fps={fps} />}
        {film.spine === 'route' && <Route film={film} frame={frame} fps={fps} index={cam.index} local={cam.local} />}
        <StripEdges film={film} tx={tx} z={cam.z} />
        <Transition film={film} frame={frame} fps={fps} />
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
          if (si > 0 && (s.transition_in ?? 'travel') !== 'cut') {
            out.push(
              <Sequence key={`${s.id}-tr`} from={Math.max(0, start - (s.transition_in === 'travel' || !s.transition_in ? 0 : 12))} durationInFrames={40}>
                <Audio src={staticFile(s.transition_in === 'fold' ? 'sfx/fold.wav' : 'sfx/slide.wav')} volume={0.35} />
              </Sequence>,
            );
          }
          s.elements.forEach((el, ei) => {
            const file = sfxFor(el);
            if (!file) return;
            out.push(
              <Sequence key={`${s.id}-${ei}-sfx`} from={start + Math.round((el.at ?? 0) * fps)} durationInFrames={45}>
                <Audio src={staticFile(`sfx/${file}`)} volume={el.type === 'stamp' ? 0.7 : 0.3} />
              </Sequence>,
            );
          });
          return out;
        })}
    </AbsoluteFill>
  );
};
