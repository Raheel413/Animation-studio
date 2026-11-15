import React from 'react';
import {Easing, interpolate} from 'remotion';
import {circle, clamp, InkPath, paperShadow, prog, roundedRect} from '../ink';
import type {CharacterEl, Film} from '../types';

const CARD = '#FBF8F1';

/** Cut-paper character: geometric body, ink outline, paper shadow. No stick limbs, no glow. */
export const Character: React.FC<{el: CharacterEl; f: number; pal: Film['palette']; seed: number}> = ({el, f, pal, seed}) => {
  const accent = el.side === 'a' ? pal.a : el.side === 'b' ? pal.b : CARD;
  const mood = el.mood ?? 'neutral';
  const enter = el.enter ?? 'draw';

  const body = prog(f, 0, 12);
  const head = prog(f, 6, 12);
  const fill = prog(f, 12, 8);
  const face = prog(f, 18, 6);
  const slide =
    enter === 'draw'
      ? 0
      : interpolate(f, [0, 16], [enter === 'left' ? -260 : 260, 0], {...clamp, easing: Easing.out(Easing.back(1.2))});

  // idle life: small bob + head sway, offset per character so they never move in sync
  const bob = Math.sin((f + seed * 17) / 14) * 3;
  const sway = Math.sin((f + seed * 31) / 22) * 2 + (mood === 'sad' ? 9 : mood === 'worried' ? -5 : 0);
  const blink = (f + seed * 40) % 95 < 4 ? 0.15 : 1;

  const talking = el.talk && Math.sin(f * 0.9) > 0.1;
  const mouth = talking
    ? 'M-13,12 q13,22 26,0 q-13,-5 -26,0 z'
    : mood === 'happy'
      ? 'M-16,14 q16,16 32,0'
      : mood === 'sad'
        ? 'M-14,22 q14,-12 28,0'
        : mood === 'worried'
          ? 'M-12,18 q6,-6 12,0 q6,6 12,0'
          : 'M-12,17 h24';

  return (
    <g transform={`translate(${slide},${bob})`} style={{filter: paperShadow}}>
      <g filter="url(#wobble)">
        {/* torso */}
        <InkPath d={roundedRect(-62, 0, 124, 178, 34)} p={body} ink={pal.ink} fill={accent} fillP={fill} />
        {/* paper arm tab, only when holding something */}
        {el.holding && (
          <g opacity={fill}>
            <InkPath d={roundedRect(40, 62, 74, 30, 15)} p={fill} ink={pal.ink} fill={accent} />
            {el.holding === 'phone' && <InkPath d={roundedRect(98, 34, 34, 58, 7)} p={fill} ink={pal.ink} fill={pal.ink} />}
            {el.holding === 'coin' && <InkPath d={circle(120, 66, 22)} p={fill} ink={pal.ink} fill="#E3B341" />}
          </g>
        )}
        {/* head */}
        <g transform={`translate(0,-52) rotate(${sway})`}>
          <InkPath d={circle(0, 0, 54)} p={head} ink={pal.ink} fill={CARD} fillP={fill} />
          <g opacity={face}>
            <ellipse cx={-18} cy={-6} rx={5.5} ry={6.5 * blink} fill={pal.ink} />
            <ellipse cx={18} cy={-6} rx={5.5} ry={6.5 * blink} fill={pal.ink} />
            {mood === 'worried' && <path d="M-30,-20 l14,-7 M30,-20 l-14,-7" stroke={pal.ink} strokeWidth={3.5} strokeLinecap="round" />}
            <path d={mouth} fill="none" stroke={pal.ink} strokeWidth={4} strokeLinecap="round" />
          </g>
        </g>
      </g>
      {el.label && (
        <text
          x={0}
          y={226}
          textAnchor="middle"
          fontFamily="Caveat"
          fontWeight={700}
          fontSize={46}
          fill={pal.ink}
          opacity={face}
        >
          {el.label}
        </text>
      )}
    </g>
  );
};
