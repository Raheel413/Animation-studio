import React from 'react';
import {Easing, interpolate} from 'remotion';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** 0..1 progress of an animation that starts at `start` and lasts `dur` frames. */
export const prog = (frame: number, start: number, dur: number, ease = Easing.out(Easing.cubic)) =>
  interpolate(frame, [start, start + dur], [0, 1], {...clamp, easing: ease});

/** SVG filters shared by every element. Rendered once. */
export const InkDefs: React.FC = () => (
  <svg width={0} height={0} style={{position: 'absolute'}}>
    <defs>
      {/* uneven hand-drawn line */}
      <filter id="wobble" x="-5%" y="-5%" width="110%" height="110%">
        <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves={2} seed={7} result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale={5} />
      </filter>
      {/* patchy rubber-stamp ink */}
      <filter id="stampink" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves={2} seed={11} result="n" />
        <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3.2 2.55" result="holes" />
        <feComposite in="SourceGraphic" in2="holes" operator="in" result="inked" />
        <feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves={1} seed={3} result="w" />
        <feDisplacementMap in="inked" in2="w" scale={3} />
      </filter>
    </defs>
  </svg>
);

export const paperShadow = 'drop-shadow(3px 5px 0px rgba(70,50,25,0.16))';

type PathProps = {
  d: string;
  p: number; // draw progress 0..1
  ink: string;
  fill?: string;
  fillP?: number; // fill opacity progress
  w?: number;
  dash?: string;
};

/** A path that draws itself on, then (optionally) fills. */
export const InkPath: React.FC<PathProps> = ({d, p, ink, fill = 'none', fillP = 1, w = 4}) => (
  <>
    {fill !== 'none' && <path d={d} fill={fill} opacity={fillP} stroke="none" />}
    <path
      d={d}
      fill="none"
      stroke={ink}
      strokeWidth={w}
      strokeLinecap="round"
      strokeLinejoin="round"
      pathLength={1}
      strokeDasharray={1}
      strokeDashoffset={1 - p}
      opacity={p > 0 ? 1 : 0}
    />
  </>
);

export const roundedRect = (x: number, y: number, w: number, h: number, r: number) =>
  `M${x + r},${y} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 -${r},${r} h-${w - 2 * r} a${r},${r} 0 0 1 -${r},-${r} v-${h - 2 * r} a${r},${r} 0 0 1 ${r},-${r} z`;

export const circle = (cx: number, cy: number, r: number) =>
  `M${cx - r},${cy} a${r},${r} 0 1 0 ${2 * r},0 a${r},${r} 0 1 0 -${2 * r},0 z`;
