import React from 'react';
import {Easing, Img, interpolate, staticFile} from 'remotion';
import {clamp} from '../ink';
import type {PhotoEl} from '../types';

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
