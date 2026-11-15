import React from 'react';
import {Easing, interpolate} from 'remotion';
import {circle, clamp, InkPath, paperShadow, prog, roundedRect} from '../ink';
import type {BarsEl, CheckGridEl, Film, NoteEl, PropEl, StampEl, TallyEl} from '../types';

type P<T> = {el: T; f: number; pal: Film['palette']};
const CARD = '#FBF8F1';
const sideColor = (pal: Film['palette'], side: 'a' | 'b' | null | undefined) =>
  side === 'a' ? pal.a : side === 'b' ? pal.b : pal.ink;

/** Rubber stamp: slams in, patchy ink, slightly rotated. One short judging word. */
export const Stamp: React.FC<P<StampEl>> = ({el, f, pal}) => {
  const p = interpolate(f, [0, 5], [0, 1], {...clamp, easing: Easing.in(Easing.cubic)});
  const s = interpolate(p, [0, 1], [1.9, 1]);
  const settle = f > 5 ? Math.sin((f - 5) * 1.3) * Math.exp(-(f - 5) / 3) * 0.04 : 0;
  const color = sideColor(pal, el.side);
  const w = Math.max(240, el.text.length * 62 + 90);
  return (
    <g transform={`rotate(${el.rotate ?? -6}) scale(${s + settle})`} opacity={f < 0 ? 0 : Math.min(1, p * 1.5)} filter="url(#stampink)">
      <rect x={-w / 2} y={-70} width={w} height={140} rx={16} fill="none" stroke={color} strokeWidth={10} />
      <rect x={-w / 2 + 16} y={-54} width={w - 32} height={108} rx={8} fill="none" stroke={color} strokeWidth={3} />
      <text x={0} y={30} textAnchor="middle" fontFamily="Fraunces" fontWeight={900} fontSize={88} letterSpacing={6} fill={color}>
        {el.text}
      </text>
    </g>
  );
};

/** Tally marks that write themselves, bundles of five. */
export const Tally: React.FC<P<TallyEl>> = ({el, f, pal}) => {
  const marks = [];
  const color = sideColor(pal, el.side);
  for (let i = 0; i < el.count; i++) {
    const bundle = Math.floor(i / 5);
    const k = i % 5;
    const bx = (bundle % 8) * 96;
    const by = Math.floor(bundle / 8) * 96;
    const jitter = ((i * 37) % 7) - 3;
    const p = prog(f, i * 1.6, 3);
    const d = k < 4 ? `M${bx + k * 15},${by + jitter} l${jitter * 0.5},62` : `M${bx - 10},${by + 46} L${bx + 58},${by + 12}`;
    marks.push(<InkPath key={i} d={d} p={p} ink={color} w={5} />);
  }
  return <g filter="url(#wobble)">{marks}</g>;
};

/** Handwritten note that writes on left to right. */
export const Note: React.FC<P<NoteEl> & {id: string}> = ({el, f, pal, id}) => {
  const size = el.size ?? 72;
  const w = el.text.length * size * 0.5 + 40;
  const p = prog(f, 0, Math.max(8, el.text.length * 1.4), Easing.linear);
  return (
    <g>
      <clipPath id={`clip-${id}`}>
        <rect x={-10} y={-size} width={w * p} height={size * 1.5} />
      </clipPath>
      <text clipPath={`url(#clip-${id})`} fontFamily="Caveat" fontWeight={700} fontSize={size} fill={sideColor(pal, el.side)}>
        {el.text}
      </text>
    </g>
  );
};

/** Two (or more) ink bars that grow; value written by hand at the end. */
export const Bars: React.FC<P<BarsEl>> = ({el, f, pal}) => {
  const max = Math.max(...el.rows.map((r) => r.value));
  const W = el.width ?? 760;
  return (
    <g>
      {el.rows.map((r, i) => {
        const start = i * 14;
        const grow = prog(f, start + 6, 26, Easing.inOut(Easing.cubic));
        const w = Math.max(6, (r.value / max) * W * grow);
        const y = i * 132;
        const txt = prog(f, start + 30, 8);
        return (
          <g key={i} transform={`translate(0,${y})`}>
            <text x={-24} y={50} textAnchor="end" fontFamily="Caveat" fontWeight={700} fontSize={54} fill={pal.ink} opacity={prog(f, start, 6)}>
              {r.label}
            </text>
            <g filter="url(#wobble)" style={{filter: paperShadow}}>
              <rect x={0} y={0} width={w} height={74} rx={8} fill={sideColor(pal, r.side)} />
              <rect x={0} y={0} width={w} height={74} rx={8} fill="none" stroke={pal.ink} strokeWidth={4} />
            </g>
            <text x={w + 22} y={54} fontFamily="Caveat" fontWeight={700} fontSize={62} fill={pal.ink} opacity={txt}>
              {r.display}
            </text>
          </g>
        );
      })}
    </g>
  );
};

/** Grid of checkboxes; `filled` of them take accent ink one by one. Use for "1 in 4", "half". */
export const CheckGrid: React.FC<P<CheckGridEl>> = ({el, f, pal}) => {
  const cols = el.cols ?? 10;
  const color = sideColor(pal, el.side ?? 'a');
  return (
    <g filter="url(#wobble)">
      {Array.from({length: el.total}, (_, i) => {
        const x = (i % cols) * 70;
        const y = Math.floor(i / cols) * 70;
        const box = prog(f, i * 0.6, 5);
        const fill = i < el.filled ? prog(f, el.total * 0.6 + 8 + i * 2.2, 4) : 0;
        return (
          <g key={i}>
            <rect x={x + 6} y={y + 6} width={46 * fill} height={46} fill={color} />
            <InkPath d={roundedRect(x, y, 58, 58, 8)} p={box} ink={pal.ink} w={3.5} />
          </g>
        );
      })}
    </g>
  );
};

/** Flat paper props with one or two interior ink lines. */
export const Prop: React.FC<P<PropEl>> = ({el, f, pal}) => {
  const p = prog(f, 0, 16);
  const fill = prog(f, 12, 8);
  const accent = el.side ? sideColor(pal, el.side) : CARD;
  let shapes: React.ReactNode = null;
  if (el.kind === 'sheet') {
    // tinted paper card laid behind a scene: gives collage depth. Slides in, never draws.
    const w = el.w ?? 900;
    const h = el.h ?? 620;
    const inP = interpolate(f, [0, 12], [0, 1], {...clamp, easing: Easing.out(Easing.back(1.1))});
    return (
      <g transform={`translate(0,${(1 - inP) * 90}) rotate(${(el.rotate ?? -2) * inP})`} opacity={Math.min(1, inP * 2)} style={{filter: 'drop-shadow(5px 8px 0 rgba(70,50,25,.15))'}}>
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={10} fill={CARD} />
        <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={10} fill={el.side ? sideColor(pal, el.side) : '#B9A77F'} opacity={0.2} />
      </g>
    );
  }
  if (el.kind === 'ground') {
    const w = el.w ?? 1400;
    return (
      <g filter="url(#wobble)">
        <InkPath d={`M${-w / 2},0 q${w / 4},-5 ${w / 2},0 t${w / 2},0`} p={prog(f, 0, 18)} ink={pal.ink} w={5} />
      </g>
    );
  }
  if (el.kind === 'building') {
    shapes = (
      <>
        <InkPath d={roundedRect(-190, -330, 380, 330, 10)} p={p} ink={pal.ink} fill={CARD} fillP={fill} />
        {[0, 1, 2].map((r) =>
          [0, 1, 2, 3].map((c) => (
            <InkPath key={`${r}${c}`} d={roundedRect(-158 + c * 84, -296 + r * 92, 56, 62, 5)} p={prog(f, 10 + (r * 4 + c) * 1.2, 6)} ink={pal.ink} w={3} />
          )),
        )}
        <InkPath d="M-260,0 H260" p={p} ink={pal.ink} />
      </>
    );
  } else if (el.kind === 'desk') {
    shapes = (
      <>
        <InkPath d={roundedRect(-130, -20, 260, 26, 6)} p={p} ink={pal.ink} fill={accent} fillP={fill} />
        <InkPath d="M-104,6 v92 M104,6 v92" p={p} ink={pal.ink} />
        <InkPath d={roundedRect(-44, -98, 88, 62, 6)} p={prog(f, 8, 10)} ink={pal.ink} fill={CARD} fillP={fill} />
        <InkPath d="M0,-36 v16" p={prog(f, 14, 4)} ink={pal.ink} />
      </>
    );
  } else if (el.kind === 'coin') {
    shapes = (
      <>
        <InkPath d={circle(0, 0, 44)} p={p} ink={pal.ink} fill="#E3B341" fillP={fill} />
        <InkPath d={circle(0, 0, 30)} p={prog(f, 8, 8)} ink={pal.ink} w={3} />
      </>
    );
  } else if (el.kind === 'phone') {
    shapes = (
      <>
        <InkPath d={roundedRect(-70, -130, 140, 260, 20)} p={p} ink={pal.ink} fill={CARD} fillP={fill} />
        <InkPath d="M-22,-108 h44" p={prog(f, 10, 5)} ink={pal.ink} w={5} />
      </>
    );
  } else if (el.kind === 'bus') {
    shapes = (
      <>
        <InkPath d={roundedRect(-260, -150, 520, 150, 22)} p={p} ink={pal.ink} fill="#E3B341" fillP={fill} />
        {[0, 1, 2, 3, 4].map((c) => (
          <InkPath key={c} d={roundedRect(-226 + c * 84, -126, 60, 52, 6)} p={prog(f, 8 + c * 1.5, 6)} ink={pal.ink} fill={CARD} fillP={fill} w={3} />
        ))}
        <InkPath d="M-260,-44 H260" p={prog(f, 12, 8)} ink={pal.ink} w={3} />
        <InkPath d={circle(-160, 4, 34)} p={prog(f, 10, 8)} ink={pal.ink} fill={pal.ink} fillP={fill} />
        <InkPath d={circle(160, 4, 34)} p={prog(f, 12, 8)} ink={pal.ink} fill={pal.ink} fillP={fill} />
      </>
    );
  } else if (el.kind === 'server') {
    shapes = (
      <>
        <InkPath d={roundedRect(-110, -340, 220, 340, 10)} p={p} ink={pal.ink} fill={el.side ? accent : '#5B6770'} fillP={fill} />
        {[0, 1, 2, 3, 4, 5].map((r) => (
          <g key={r}>
            <InkPath d={roundedRect(-86, -316 + r * 52, 172, 38, 5)} p={prog(f, 8 + r * 1.4, 6)} ink={pal.ink} fill={CARD} fillP={fill} w={3} />
            <circle cx={64} cy={-297 + r * 52} r={6} fill={(f + r * 7) % 24 < 12 ? '#7CC36E' : '#2E6B3F'} opacity={fill} />
          </g>
        ))}
      </>
    );
  } else if (el.kind === 'calendar') {
    shapes = (
      <>
        <InkPath d={roundedRect(-90, -100, 180, 200, 10)} p={p} ink={pal.ink} fill={CARD} fillP={fill} />
        <rect x={-88} y={-98} width={176 * fill} height={48} fill={accent === CARD ? pal.ink : accent} opacity={fill} />
        <InkPath d="M-50,-116 v30 M50,-116 v30" p={prog(f, 8, 5)} ink={pal.ink} w={6} />
      </>
    );
  }
  return (
    <g style={{filter: paperShadow}}>
      <g filter="url(#wobble)">{shapes}</g>
      {el.text && (
        <text x={0} y={el.kind === 'calendar' ? 62 : 20} textAnchor="middle" fontFamily="Fraunces" fontWeight={900} fontSize={el.kind === 'calendar' ? 92 : 56} fill={pal.ink} opacity={prog(f, 16, 6)}>
          {el.text}
        </text>
      )}
    </g>
  );
};
