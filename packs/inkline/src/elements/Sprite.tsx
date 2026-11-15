import React from 'react';
import {Easing, Img, interpolate, staticFile} from 'remotion';
import {clamp} from '../ink';
import manifest from '../../../../public/cast/manifest.json';
import type {Film, SpriteEl} from '../types';
import {shotEnd} from '../shots';

const M = manifest as unknown as Record<string, Record<string, [number, number, number]>>;

type Beat = {f: number; pose?: string; flip?: boolean; slump?: boolean};

/** Collect this sprite's pose cues from every scene of its shot, in frames since the shot began. */
const beatsFor = (film: Film, si: number, el: SpriteEl, fps: number) => {
  const startF = (film.scenes[si].t_start + (el.at ?? 0)) * fps;
  const out: Beat[] = [{f: 0, pose: el.pose, flip: el.flip, slump: el.slump}];
  for (let k = si; k <= shotEnd(film.scenes, si); k++) {
    for (const c of film.scenes[k].cues ?? []) {
      if (c.who !== el.who) continue;
      out.push({f: (film.scenes[k].t_start + (c.at ?? 0)) * fps - startF, pose: c.pose, flip: c.flip, slump: c.slump});
    }
  }
  return {beats: out.sort((a, b) => a.f - b.f), startF};
};

/**
 * Illustrated cut-paper character. Poses swap with a short squash-and-stretch pop and a crossfade;
 * between swaps the cutout breathes and sways, and bobs with the voice when it is the speaker.
 * Anchored at the top of the head (x = head centre, y = head top) and scaled by the tallest pose,
 * so the body stays the same size and place whichever pose is showing. h = height of the tallest pose.
 */
export const Sprite: React.FC<{el: SpriteEl; film: Film; si: number; frame: number; fps: number; amp: number; speaking: boolean; left: number}> = ({
  el,
  film,
  si,
  frame,
  fps,
  amp,
  speaking,
  left,
}) => {
  const {beats, startF} = beatsFor(film, si, el, fps);
  const f = frame - startF;
  if (f < 0) return null;

  // current and previous pose
  let cur = beats[0];
  let prev = beats[0];
  let flip = !!beats[0].flip;
  let slump = !!beats[0].slump;
  let changedAt = 0;
  for (const b of beats.slice(1)) {
    if (f < b.f) break;
    if (b.pose && b.pose !== cur.pose) {
      prev = cur;
      cur = {...cur, pose: b.pose};
      changedAt = b.f;
    }
    if (b.flip !== undefined) flip = b.flip;
    if (b.slump !== undefined) slump = b.slump;
  }
  const since = f - changedAt;
  const swap = changedAt > 0 ? interpolate(since, [0, 4], [0, 1], clamp) : 1;
  // 0.2 s squash-and-stretch pop on every pose change
  const pop = changedAt > 0 ? interpolate(since, [0, 3, 6], [0.96, 1.025, 1], {...clamp, easing: Easing.out(Easing.quad)}) : 1;

  const enter = interpolate(f, [0, 12], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});
  const breathe = 1 + Math.sin((f + el.x) / 26) * 0.006;
  const sway = Math.sin((f + el.x * 0.3) / 53) * 0.5;
  const talk = speaking ? Math.min(1, amp * 1.5) : 0;
  const bob = -talk * 6 + (speaking ? Math.sin(f / 4.5) * 1.2 * talk : 0);
  const tilt = sway + (speaking ? Math.sin(f / 7) * 0.8 * talk : 0) + (slump ? 2.5 : 0);

  const poses = M[el.who] ?? {};
  const maxH = Math.max(...Object.values(poses).map((p) => p[1]));
  const k = (el.h ?? 820) / maxH;
  const layer = (pose: string, opacity: number) => {
    const [w, h, ax] = poses[pose] ?? [500, maxH, 250];
    return (
      <Img
        key={pose}
        src={staticFile(`cast/${el.who}/${pose}.png`)}
        style={{position: 'absolute', left: -ax * k, top: 0, width: w * k, height: h * k, opacity, filter: 'drop-shadow(0 6px 9px rgba(20,18,15,.22))'}}
      />
    );
  };

  return (
    <div
      style={{
        position: 'absolute',
        left,
        top: el.y + (1 - enter) * 120 + (slump ? 14 : 0),
        opacity: enter,
        transformOrigin: `0px ${maxH * k}px`,
        transform: `translateY(${bob}px) rotate(${tilt}deg) scale(${flip ? -1 : 1}, 1) scale(${pop}, ${(2 - pop) * breathe * (slump ? 0.975 : 1)})`,
      }}
    >
      {swap < 1 && prev.pose && layer(prev.pose, 1 - swap)}
      {cur.pose && layer(cur.pose, swap)}
    </div>
  );
};
