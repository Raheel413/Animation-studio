import React from 'react';
import {Easing, interpolate} from 'remotion';
import {clamp, InkPath, paperShadow, prog} from '../ink';
import type {ClippingEl, Film, LineChartEl} from '../types';

type P<T> = {el: T; f: number; pal: Film['palette']};
const NEWSPRINT = '#F2EDE1';
const MARKER = '#F4D03F';

/** A newspaper clipping that slides onto the desk; a highlighter then sweeps across the chosen lines. */
export const Clipping: React.FC<P<ClippingEl> & {id: string}> = ({el, f, pal, id}) => {
  const size = el.size ?? 66;
  const longest = Math.max(...el.lines.map((l) => l.length));
  const W = Math.max(el.w ?? 1040, longest * size * 0.6 + 130);
  const lineH = size * 1.12;
  const head = el.lines.length * lineH;
  const H = 150 + head + 190;
  const inP = interpolate(f, [0, 14], [0, 1], {...clamp, easing: Easing.out(Easing.back(1.15))});
  const rot = (el.rotate ?? -2.5) * inP;
  // ragged scissor-cut outline, deterministic
  const jag = (n: number, len: number, seed: number) =>
    Array.from({length: n + 1}, (_, i) => [(i / n) * len, ((i * 7919 + seed) % 9) - 4] as const);
  const top = jag(26, W, 3).map(([x, j]) => `${x - W / 2},${-H / 2 + j}`);
  const right = jag(10, H, 5).map(([y, j]) => `${W / 2 + j},${y - H / 2}`);
  const bottom = jag(26, W, 11).map(([x, j]) => `${W / 2 - x},${H / 2 + j}`);
  const left = jag(10, H, 17).map(([y, j]) => `${-W / 2 + j},${H / 2 - y}`);
  const outline = `M${[...top, ...right, ...bottom, ...left].join(' L')} Z`;
  const x0 = -W / 2 + 56;
  const hy = -H / 2 + 150;
  return (
    <g transform={`translate(0,${(1 - inP) * 160}) rotate(${rot})`} opacity={Math.min(1, inP * 2)} style={{filter: 'drop-shadow(6px 10px 0 rgba(70,50,25,.18))'}}>
      <path d={outline} fill={NEWSPRINT} stroke="#CFC6B2" strokeWidth={2} />
      {/* masthead line: outlet and date */}
      <text x={x0} y={-H / 2 + 70} fontFamily="Fraunces" fontWeight={900} fontSize={30} letterSpacing={4} fill="#4A443B">
        {el.source.toUpperCase()}
      </text>
      <text x={W / 2 - 56} y={-H / 2 + 70} textAnchor="end" fontFamily="Fraunces" fontSize={26} fill="#6E665A">
        {el.date ?? ''}
      </text>
      <line x1={x0} y1={-H / 2 + 92} x2={W / 2 - 56} y2={-H / 2 + 92} stroke="#4A443B" strokeWidth={3} />
      <line x1={x0} y1={-H / 2 + 100} x2={W / 2 - 56} y2={-H / 2 + 100} stroke="#4A443B" strokeWidth={1} />
      {/* highlighter under the chosen lines */}
      {el.lines.map((ln, i) => {
        if (!(el.hl ?? []).includes(i)) return null;
        const order = (el.hl ?? []).indexOf(i);
        const p = prog(f, 22 + order * 10, 12, Easing.inOut(Easing.quad));
        const w = Math.min(W - 90, ln.length * size * 0.58 + 24);
        return <rect key={`h${i}`} x={x0 - 12} y={hy + i * lineH - size * 0.82} width={w * p} height={size * 0.98} fill={MARKER} opacity={0.75} rx={6} style={{mixBlendMode: 'multiply'}} />;
      })}
      <g fontFamily="Fraunces" fontWeight={900} fontSize={size} fill="#1E1B18">
        {el.lines.map((ln, i) => (
          <text key={i} x={x0} y={hy + i * lineH}>
            {ln}
          </text>
        ))}
      </g>
      {/* body copy as grey type lines in two columns */}
      {Array.from({length: 8}, (_, i) => {
        const col = i % 2;
        const row = Math.floor(i / 2);
        const cw = (W - 150) / 2;
        const len = cw * (row === 3 ? 0.55 : 0.92 + ((i * 13) % 7) / 100);
        return (
          <rect key={`b${i}`} x={x0 + col * (cw + 38)} y={hy + head - 10 + row * 34} width={len} height={12} rx={3} fill="#B9B1A1" opacity={0.75} />
        );
      })}
      <clipPath id={`cl-${id}`}>
        <rect x={-W / 2} y={-H / 2} width={W} height={H} />
      </clipPath>
    </g>
  );
};

/** Hand-inked line chart that draws itself left to right. Points can carry a tag written next to them. */
export const LineChart: React.FC<P<LineChartEl>> = ({el, f, pal}) => {
  const W = el.w ?? 1100;
  const H = el.h ?? 520;
  const vals = el.points.map((p) => p.v);
  const lo = el.min ?? Math.min(...vals);
  const hi = el.max ?? Math.max(...vals);
  const n = el.points.length;
  const X = (i: number) => (el.points[i].t !== undefined ? (el.points[i].t! / el.points[n - 1].t!) * W : (i / (n - 1)) * W);
  const Y = (v: number) => H - ((v - lo) / Math.max(1e-9, hi - lo)) * H;
  const color = el.side === 'b' ? pal.b : el.side === 'a' ? pal.a : pal.ink;
  const axes = prog(f, 0, 12);
  const drawDur = el.draw ?? 40;
  const line = prog(f, 10, drawDur, Easing.inOut(Easing.quad));
  const d = el.points.map((p, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(p.v).toFixed(1)}`).join(' ');
  const area = `${d} L${X(n - 1)},${H} L0,${H} Z`;
  return (
    <g style={{filter: paperShadow}}>
      {el.title && (
        <text x={0} y={-48} fontFamily="Caveat" fontWeight={700} fontSize={58} fill={pal.ink} opacity={prog(f, 0, 8)}>
          {el.title}
        </text>
      )}
      <g filter="url(#wobble)">
        <InkPath d={`M0,0 V${H} H${W}`} p={axes} ink={pal.ink} w={4} />
        {el.ref !== undefined && (
          <path d={`M0,${Y(el.ref)} H${W}`} stroke={pal.ink} strokeWidth={3} strokeDasharray="10 12" opacity={0.45 * axes} fill="none" />
        )}
        <clipPath id={`lc-${el.x}-${el.y}`}>
          <rect x={-10} y={-40} width={(W + 20) * line} height={H + 80} />
        </clipPath>
        <g clipPath={`url(#lc-${el.x}-${el.y})`}>
          <path d={area} fill={color} opacity={0.14} />
          <path d={d} fill="none" stroke={color} strokeWidth={9} strokeLinejoin="round" strokeLinecap="round" />
        </g>
      </g>
      {el.ref !== undefined && el.refLabel && (
        <text x={W - 6} y={Y(el.ref) - 14} textAnchor="end" fontFamily="Caveat" fontWeight={700} fontSize={40} fill={pal.ink} opacity={0.75 * axes}>
          {el.refLabel}
        </text>
      )}
      {el.points.map((p, i) => {
        const at = 10 + (X(i) / W) * drawDur;
        const show = prog(f, at, 6);
        return (
          <g key={i} opacity={show}>
            {p.label && (
              <text x={X(i)} y={H + 52} textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'} fontFamily="Caveat" fontWeight={700} fontSize={40} fill={pal.ink}>
                {p.label}
              </text>
            )}
            {p.tag && (
              <>
                <circle cx={X(i)} cy={Y(p.v)} r={14 * show} fill={color} stroke={pal.ink} strokeWidth={4} />
                <text
                  x={X(i) + (p.tagDx ?? 0)}
                  y={Y(p.v) + (p.tagDy ?? -34)}
                  textAnchor={i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}
                  fontFamily="Fraunces"
                  fontWeight={900}
                  fontSize={46}
                  fill={pal.ink}
                >
                  {p.tag}
                </text>
              </>
            )}
          </g>
        );
      })}
    </g>
  );
};
