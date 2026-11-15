import React from 'react';
import {Easing, Img, interpolate, staticFile} from 'remotion';
import {clamp} from '../ink';
import type {LayeredEl, PhotoEl} from '../types';

/** Full-frame still with a slow Ken Burns push (direction alternates per photo) and a short crossfade in. */
export const Photo: React.FC<{el: PhotoEl; f: number; dur: number; left: number; seed: number}> = ({el, f, dur, left, seed}) => {
  if (f < 0) return null;
  const W = el.w ?? 1920;
  const H = el.h ?? 1080;
  const t = interpolate(f, [0, Math.max(1, dur)], [0, 1], clamp);
  const zoom = (el.zoom ?? 0.09) * Easing.inOut(Easing.sin)(t);
  const dir = seed % 4;
  const dx = (dir === 0 ? -1 : dir === 1 ? 1 : 0) * 40 * t;
  const dy = (dir === 2 ? -1 : dir === 3 ? 1 : 0) * 22 * t;
  const fade = interpolate(f, [0, 6], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', left: left - W / 2, top: el.y - H / 2, width: W, height: H, overflow: 'hidden', opacity: fade}}>
      <Img src={staticFile(el.src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `translate(${dx}px, ${dy}px) scale(${1.02 + zoom})`}} />
    </div>
  );
};

/** Bold word-group captions in the lower third, timed by word length across each scene. */
export const Captions: React.FC<{text: string; local: number; dur: number}> = ({text, local, dur}) => {
  const words = text.split(/\s+/).filter(Boolean);
  const groups: string[][] = [];
  for (let i = 0; i < words.length; i += 4) groups.push(words.slice(i, i + 4));
  const weight = (g: string[]) => g.join(' ').length + 3;
  const total = groups.reduce((a, g) => a + weight(g), 0);
  let acc = 0;
  let cur = groups[groups.length - 1] ?? [];
  for (const g of groups) {
    const end = ((acc + weight(g)) / total) * dur;
    if (local < end) {
      cur = g;
      break;
    }
    acc += weight(g);
  }
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 118, textAlign: 'center', pointerEvents: 'none'}}>
      <span
        style={{
          fontFamily: 'Anton',
          fontSize: 76,
          letterSpacing: 1,
          color: '#FFFFFF',
          WebkitTextStroke: '10px #111',
          paintOrder: 'stroke fill',
          textShadow: '0 6px 14px rgba(0,0,0,.35)',
        }}
      >
        {cur.join(' ')}
      </span>
    </div>
  );
};

type Layer = {src: string; x: number; y: number; w: number; h: number; role: 'hero' | 'prop' | 'attached'};

/**
 * 2.5D build of one illustrated still split into layers (bg + props + hero).
 * Props pop in one after another and float; the hero rises in, breathes from the feet and bobs with the voice;
 * layers sit at different depths so the slow camera push gives parallax. Big pieces glued to the hero stay put,
 * small ones (a hand, the legs) move with him so nothing tears.
 */
export const Layered: React.FC<{el: LayeredEl; f: number; dur: number; left: number; seed: number; amp: number}> = ({el, f, dur, left, seed, amp}) => {
  if (f < 0) return null;
  const W = 1920;
  const H = 1071;
  const t = interpolate(f, [0, Math.max(1, dur)], [0, 1], clamp);
  const push = 0.07 * Easing.inOut(Easing.sin)(t);
  const fade = interpolate(f, [0, 5], [0, 1], clamp);
  const hero = el.layers.find((l) => l.role === 'hero');
  const heroArea = hero ? hero.w * hero.h : 1;
  const hx = hero ? hero.x + hero.w / 2 : W / 2;
  const hy = hero ? hero.y + hero.h : H;
  // hero motion, anchored at his feet
  const heroIn = interpolate(f, [0, 12], [0, 1], {...clamp, easing: Easing.out(Easing.back(1.6))});
  const breathe = 1 + Math.sin((f + seed * 9) / 22) * 0.012;
  const talk = Math.min(1, amp * 1.4);
  const bob = -talk * 7 + Math.sin(f / 5) * 1.5 * talk;
  const tilt = Math.sin((f + seed * 5) / 37) * 0.6 + Math.sin(f / 7) * 0.5 * talk;
  const heroT = `translate(${hx}px, ${hy}px) translateY(${(1 - heroIn) * 60 + bob}px) rotate(${tilt}deg) scale(${0.94 + 0.06 * heroIn}, ${(0.94 + 0.06 * heroIn) * breathe}) translate(${-hx}px, ${-hy}px)`;
  const depth = (k: number, role: string) => (role === 'hero' ? 1.18 : 1.06 + (k % 3) * 0.03);
  let propIdx = 0;
  return (
    <div style={{position: 'absolute', left: left - W / 2, top: el.y - H / 2, width: W, height: H, overflow: 'hidden', opacity: fade}}>
      <div style={{position: 'absolute', inset: 0, transformOrigin: '50% 50%', transform: `scale(${1.02 + push * 0.6})`}}>
        <Img src={staticFile(el.bg)} style={{width: '100%', height: '100%'}} />
      </div>
      {el.layers.map((l, k) => {
        const cx = l.x + l.w / 2;
        const cy = l.y + l.h / 2;
        const dz = depth(k, l.role);
        const s = 1.02 + push * dz;
        // parallax: scale about the frame centre, more for nearer layers
        const px = (cx - W / 2) * (s - 1);
        const py = (cy - H / 2) * (s - 1);
        let inner = '';
        let op = 1;
        if (l.role === 'hero' || (l.role === 'attached' && l.w * l.h < heroArea * 0.6)) {
          inner = heroT;
          op = Math.min(1, heroIn * 1.5);
        } else if (l.role === 'prop') {
          const at = 6 + propIdx++ * 4;
          const p = interpolate(f, [at, at + 5, at + 10], [0.7, 1.06, 1], {...clamp, easing: Easing.out(Easing.quad)});
          op = interpolate(f, [at, at + 4], [0, 1], clamp);
          const fy = Math.sin((f + k * 23) / 38) * 5;
          const fr = Math.sin((f + k * 17) / 51) * 0.8;
          inner = `translate(${cx}px, ${cy}px) translateY(${fy}px) rotate(${fr}deg) scale(${p}) translate(${-cx}px, ${-cy}px)`;
        }
        return (
          <div key={k} style={{position: 'absolute', inset: 0, transformOrigin: '0 0', transform: `translate(${px}px, ${py}px) scale(${s})`, opacity: op}}>
            <div style={{position: 'absolute', inset: 0, transformOrigin: '0 0', transform: inner}}>
              <Img src={staticFile(l.src)} style={{position: 'absolute', left: l.x, top: l.y, width: l.w, height: l.h, filter: l.role === 'hero' ? 'drop-shadow(0 8px 10px rgba(20,18,15,.18))' : 'none'}} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
