import React from 'react';
import {Easing, Img, interpolate, staticFile} from 'remotion';
import {clamp} from '../ink';
import type {CounterEl, MapEl, ScreenEl} from '../types';

const MARKER = 'rgba(255,205,0,.55)';
const CRIMSON = '#D93829';

/**
 * A real article screenshot: the page card lifts onto a dark desk, the camera pushes toward the
 * highlighted line, a marker sweeps across it, then a red pen circles the key words.
 */
export const Screen: React.FC<{el: ScreenEl; f: number; dur: number; left: number; seed: number}> = ({el, f, dur, left, seed}) => {
  if (f < 0) return null;
  const W = el.w ?? 1300;
  const s = W / el.iw; // image px -> panel px
  const H = el.ih * s;
  const inP = interpolate(f, [0, 16], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const t = interpolate(f, [0, Math.max(1, dur)], [0, 1], clamp);
  // push toward the first highlight (or the centre) over the whole hold
  const target = el.hl?.[0] ?? el.ring ?? [0, 0, el.iw, el.ih];
  const tx = ((target[0] + target[2]) / 2) * s - W / 2;
  const ty = ((target[1] + target[3]) / 2) * s - H / 2;
  const push = (el.push ?? 0.16) * Easing.inOut(Easing.sin)(t);
  const rot = (seed % 2 ? -1 : 1) * 1.2 * (1 - inP) + (seed % 2 ? 0.5 : -0.5);
  const hl0 = (el.hlAt ?? 0.9) * 30;
  return (
    <div
      style={{
        position: 'absolute',
        left: left - W / 2,
        top: el.y - H / 2,
        width: W,
        height: H,
        opacity: inP,
        transform: `translateY(${(1 - inP) * 70}px) rotate(${rot}deg) scale(${1 + push}) translate(${-tx * push * 2.2}px, ${-ty * push * 2.2}px)`,
        transformOrigin: '50% 50%',
      }}
    >
      <div style={{position: 'absolute', inset: 0, boxShadow: '0 30px 60px rgba(0,0,0,.45), 0 4px 10px rgba(0,0,0,.3)', borderRadius: 10, overflow: 'hidden', background: '#fff'}}>
      <Img src={staticFile(el.src)} style={{width: W, height: H, display: 'block'}} />
      <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}} viewBox={`0 0 ${el.iw} ${el.ih}`}>
        {(el.hl ?? []).map((r, i) => {
          const p = interpolate(f, [hl0 + i * 9, hl0 + i * 9 + 12], [0, 1], {...clamp, easing: Easing.inOut(Easing.quad)});
          return <rect key={i} x={r[0] - 6} y={r[1] - 4} width={(r[2] - r[0] + 12) * p} height={r[3] - r[1] + 8} fill={MARKER} rx={4} style={{mixBlendMode: 'multiply'}} />;
        })}
        {el.ring &&
          (() => {
            const [x0, y0, x1, y1] = el.ring;
            const cx = (x0 + x1) / 2;
            const cy = (y0 + y1) / 2;
            const rx = (x1 - x0) / 2 + 22;
            const ry = (y1 - y0) / 2 + 16;
            const a = hl0 + (el.hl?.length ?? 0) * 9 + 14;
            const p = interpolate(f, [a, a + 12], [0, 1], {...clamp, easing: Easing.out(Easing.quad)});
            return (
              <path
                d={`M${cx - rx * 0.2},${cy - ry} C${cx + rx * 1.1},${cy - ry * 1.15} ${cx + rx * 1.15},${cy + ry} ${cx},${cy + ry} C${cx - rx * 1.2},${cy + ry} ${cx - rx * 1.15},${cy - ry * 0.9} ${cx + rx * 0.15},${cy - ry * 1.1}`}
                fill="none"
                stroke={CRIMSON}
                strokeWidth={5}
                strokeLinecap="round"
                pathLength={1}
                strokeDasharray="1 1"
                strokeDashoffset={1 - p}
              />
            );
          })()}
      </svg>
      </div>
      {el.tag && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: -52,
            padding: '8px 14px',
            background: '#111',
            color: '#F2EDE1',
            fontFamily: 'JetBrains Mono',
            fontSize: 22,
            letterSpacing: 1,
            borderRadius: 4,
            opacity: interpolate(f, [10, 18], [0, 1], clamp),
          }}
        >
          SOURCE: {el.tag.toUpperCase()}
        </div>
      )}
    </div>
  );
};

/** A big ticking number (e.g. the national debt) that counts from `from` to `to` and keeps creeping. */
export const Counter: React.FC<{el: CounterEl; f: number; fps: number; left: number}> = ({el, f, fps, left}) => {
  if (f < 0) return null;
  const p = interpolate(f, [0, (el.dur ?? 1.6) * fps], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const v = (el.from ?? 0) + ((el.to ?? 0) - (el.from ?? 0)) * p + Math.max(0, f - (el.dur ?? 1.6) * fps) * (el.perFrame ?? 0);
  const txt = el.from == null ? el.prefix : el.prefix + v.toLocaleString('en-US', {maximumFractionDigits: el.decimals ?? 0, minimumFractionDigits: el.decimals ?? 0}) + (el.suffix ?? '');
  const inP = interpolate(f, [0, 10], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: left - 900, top: el.y - 110, width: 1800, textAlign: 'center', opacity: inP}}>
      {el.label && <div style={{fontFamily: 'JetBrains Mono', fontSize: 30, letterSpacing: 4, color: el.dark ? '#FFFFFF' : '#3A3A3A', marginBottom: 10, textShadow: el.dark ? '0 2px 12px rgba(0,0,0,.9)' : 'none'}}>{el.label.toUpperCase()}</div>}
      <div style={{fontFamily: 'Anton', fontSize: el.size ?? 150, color: el.color ?? (el.dark ? '#FFFFFF' : '#1A1A1A'), fontVariantNumeric: 'tabular-nums', letterSpacing: 2, textShadow: el.dark ? '0 8px 30px rgba(0,0,0,.5)' : 'none'}}>
        {txt}
      </div>
    </div>
  );
};

/**
 * Illustrated map with a keyframed camera (cx, cy, scale in image px) and name pins that pop in.
 * Image is drawn at its natural size times `fit` so the whole map fills the frame at scale 1.
 */
export const MapView: React.FC<{el: MapEl; f: number; fps: number; left: number}> = ({el, f, fps, left}) => {
  if (f < 0) return null;
  const t = f / fps;
  const ks = el.cam;
  let k = 0;
  while (k < ks.length - 2 && t > ks[k + 1][0]) k++;
  const a = ks[k];
  const b = ks[Math.min(k + 1, ks.length - 1)];
  const p = b[0] === a[0] ? 1 : Easing.inOut(Easing.cubic)(Math.max(0, Math.min(1, (t - a[0]) / (b[0] - a[0]))));
  const cx = a[1] + (b[1] - a[1]) * p;
  const cy = a[2] + (b[2] - a[2]) * p;
  const sc = a[3] + (b[3] - a[3]) * p;
  const fit = 1920 / el.iw;
  const s = fit * sc;
  const fade = el.cut ? 1 : interpolate(f, [0, 8], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: left - 960, top: 0, width: 1920, height: 1080, overflow: 'hidden', opacity: fade, background: '#DCE8C8'}}>
      <div style={{position: 'absolute', left: 960 - cx * s, top: 540 - cy * s, width: el.iw * s, height: el.ih * s}}>
        <Img src={staticFile(el.src)} style={{width: '100%', height: '100%'}} />
        {(el.pins ?? []).map((pin, i) => {
          const pf = f - pin.at * fps;
          if (pf < 0 || (pin.until != null && t > pin.until)) return null;
          const pop = interpolate(pf, [0, 7, 11], [0, 1.15, 1], clamp);
          return (
            <div key={i} style={{position: 'absolute', left: pin.x * s, top: pin.y * s, transform: `translate(-50%, -100%) scale(${pop / Math.max(1, sc * 0.55)})`, transformOrigin: '50% 100%'}}>
              <div style={{background: pin.color ?? '#111', color: '#fff', fontFamily: 'Anton', fontSize: 44, padding: '6px 20px', borderRadius: 8, whiteSpace: 'nowrap', boxShadow: '0 6px 16px rgba(0,0,0,.35)', letterSpacing: 1}}>
                {pin.label}
                {pin.sub && <span style={{fontFamily: 'JetBrains Mono', fontSize: 26, marginLeft: 12, opacity: 0.85}}>{pin.sub}</span>}
              </div>
              <div style={{width: 0, height: 0, margin: '0 auto', borderLeft: '14px solid transparent', borderRight: '14px solid transparent', borderTop: `18px solid ${pin.color ?? '#111'}`}} />
            </div>
          );
        })}
      </div>
    </div>
  );
};
