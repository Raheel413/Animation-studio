import React from 'react';
import {Easing, interpolate} from 'remotion';
import {clamp, paperShadow} from '../ink';
import type {ActorEl, ActorLook, Film} from '../types';

/**
 * Rigged cut-paper actor: torso, head, two-part arms with hands, two-part legs with shoes.
 * Poses are joint angles; the actor eases between poses, breathes, shifts weight, blinks,
 * walks with a real cycle, and moves its mouth to the voice when it is the speaker.
 *
 * Angles: a limb is drawn pointing down; negative angles swing it toward the actor's front.
 */
export type Pose = {
  lean: number; // torso lean, + = forward
  tilt: number; // head tilt, + = down/forward
  lift: number; // shoulder lift px
  drop: number; // hip drop px (crouch / sit)
  fS: number; // front shoulder
  fE: number; // front elbow
  bS: number; // back shoulder
  bE: number; // back elbow
  fH: number; // front hip
  fK: number; // front knee
  bH: number; // back hip
  bK: number; // back knee
};

const P = (p: Partial<Pose>): Pose => ({lean: 0, tilt: 0, lift: 0, drop: 0, fS: -8, fE: -10, bS: 10, bE: -8, fH: -3, fK: 3, bH: 4, bK: 2, ...p});

export const POSES: Record<string, Pose> = {
  stand: P({}),
  relaxed: P({fS: -4, fE: -4, bS: 6, bE: -4, fH: -6, fK: 4, bH: 6}),
  point: P({fS: -100, fE: -6, bS: 12, bE: -10, lean: -2}),
  point_up: P({fS: -150, fE: -10, bS: 10, bE: -8, tilt: -8}),
  explain: P({fS: -48, fE: -58, bS: 18, bE: -40, lean: 2}),
  open_hands: P({fS: -40, fE: -70, bS: 40, bE: -70, tilt: 2}),
  shrug: P({fS: -18, fE: -105, bS: 18, bE: -105, lift: 10, tilt: 6}),
  head_hands: P({fS: -160, fE: -150, bS: 160, bE: 150, lift: 6, tilt: 4}),
  phone: P({fS: -26, fE: -118, bS: 8, bE: -20, tilt: 14, lean: 3}),
  phone_shock: P({fS: -30, fE: -120, bS: -60, bE: -90, tilt: -4, lean: -4, lift: 8}),
  think: P({fS: -24, fE: -152, bS: -18, bE: -96, tilt: -6}),
  arms_crossed: P({fS: -34, fE: -104, bS: -34, bE: -104, lean: -2}),
  slump: P({lean: 9, tilt: 16, fS: 4, fE: -2, bS: 2, bE: -2, drop: 6, fK: 8, bK: 8}),
  celebrate: P({fS: -170, fE: -14, bS: 170, bE: 14, tilt: -10, lift: 8}),
  wave: P({fS: -150, fE: -40, bS: 10, bE: -8}),
  sit: P({drop: 48, fH: -88, fK: 88, bH: -84, bK: 86, fS: -30, fE: -50, bS: -10, bE: -40, lean: 2}),
  sit_slump: P({drop: 50, fH: -86, fK: 86, bH: -82, bK: 84, fS: 0, fE: -30, bS: 4, bE: -20, lean: 12, tilt: 18}),
  drive: P({drop: 48, fH: -88, fK: 80, bH: -84, bK: 80, fS: -70, fE: -40, bS: -66, bE: -44, lean: -2}),
  hands_hips: P({fS: 28, fE: -120, bS: -28, bE: 120, lean: -2}),
  lean_in: P({lean: 10, tilt: 6, fS: -40, fE: -40, bS: 6, bE: -10}),
};

const DEFAULT_LOOK: Required<ActorLook> = {skin: '#E8B98F', hair: '#3A2A1E', hairStyle: 'short', shirt: '#4F7CAC', pants: '#2F3B52', shoes: '#2A2622'};

const mix = (a: Pose, b: Pose, t: number): Pose => {
  const o = {} as Pose;
  (Object.keys(a) as (keyof Pose)[]).forEach((k) => (o[k] = a[k] + (b[k] - a[k]) * t));
  return o;
};

type Cue = {f: number; pose?: string; mood?: string; look?: number; face?: 1 | -1};

export type ActorProps = {
  el: ActorEl;
  f: number; // frames since the actor appeared
  pal: Film['palette'];
  seed: number;
  fps: number;
  cues: Cue[]; // pose/mood changes, in frames since the actor appeared
  amp: number; // 0..1 voice loudness when this actor is speaking, else 0
  walkX: number; // current x offset from walking
  walking: number; // 0..1 walk blend
  walkPhase: number;
  face: 1 | -1;
};

const MOODS = ['neutral', 'happy', 'sad', 'worried', 'angry', 'surprised'] as const;

export const Actor: React.FC<ActorProps> = ({el, f, pal, seed, cues, amp, walking, walkPhase, face}) => {
  const look = {...DEFAULT_LOOK, ...(el.look ?? {})};
  const ink = pal.ink;

  // --- pose timeline with eased blends between cues
  const timeline: Cue[] = [{f: 0, pose: el.pose ?? 'stand', mood: el.mood ?? 'neutral', look: el.gaze ?? 0}, ...cues].sort((a, b) => a.f - b.f);
  let pose = POSES[timeline[0].pose ?? 'stand'] ?? POSES.stand;
  let mood = timeline[0].mood ?? 'neutral';
  let gaze = timeline[0].look ?? 0;
  for (let i = 1; i < timeline.length; i++) {
    const c = timeline[i];
    if (f < c.f) break;
    const t = interpolate(f, [c.f, c.f + 9], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
    if (c.pose) pose = mix(pose, POSES[c.pose] ?? pose, t);
    if (c.mood && t > 0.4) mood = c.mood;
    if (c.look !== undefined) gaze = gaze + (c.look - gaze) * t;
  }

  // --- life: breathing, weight shift, small gestures while talking
  const breathe = Math.sin((f + seed * 13) / 22) * 0.012;
  const sway = Math.sin((f + seed * 29) / 47) * 1.6;
  const talkBob = amp > 0.05 ? Math.sin(f * 0.5) * 2.2 * amp : 0;
  pose = {...pose, tilt: pose.tilt + Math.sin((f + seed * 7) / 31) * 2 + talkBob, fE: pose.fE + (amp > 0.05 ? Math.sin(f / 6) * 8 * amp : 0)};

  // --- walk cycle blends over legs and arms
  if (walking > 0) {
    const s = Math.sin(walkPhase);
    const c = Math.cos(walkPhase);
    const w: Pose = {
      ...pose,
      fH: -24 * s,
      bH: 24 * s,
      fK: Math.max(0, 34 * -c) + 4,
      bK: Math.max(0, 34 * c) + 4,
      fS: 18 * s - 6,
      bS: -18 * s + 6,
      fE: -14,
      bE: -14,
      lean: 4,
      drop: 0,
    };
    pose = mix(pose, w, walking);
  }
  const bounce = walking * Math.abs(Math.sin(walkPhase)) * -6;

  // --- appearance: pop up from the paper
  const inP = interpolate(f, [0, 12], [0, 1], {...clamp, easing: Easing.out(Easing.back(1.4))});
  const blink = (f + seed * 40) % 104 < 4 ? 0.12 : 1;

  // geometry (scale 1): feet at y=0
  const hipY = -122 + pose.drop + bounce;
  const shY = -236 + pose.drop + bounce - pose.lift * 0.4;
  const UA = 60;
  const FA = 56;
  const TH = 62;
  const SH = 60;

  const limb = (len: number, w: number, color: string) => (
    <rect x={-w / 2} y={-w / 2} width={w} height={len + w} rx={w / 2} fill={color} stroke={ink} strokeWidth={4} />
  );
  const arm = (sx: number, S: number, E: number, sleeve: string, front: boolean) => (
    <g transform={`translate(${sx},${shY + 8}) rotate(${S})`}>
      {limb(UA, 26, sleeve)}
      <g transform={`translate(0,${UA}) rotate(${E})`}>
        {limb(FA, 22, front ? look.skin : shade(look.skin))}
        <circle cx={0} cy={FA + 6} r={14} fill={front ? look.skin : shade(look.skin)} stroke={ink} strokeWidth={4} />
        {front && el.holding === 'phone' && (
          <g transform={`translate(10,${FA - 4}) rotate(${-S - E - 8})`}>
            <rect x={-14} y={-46} width={32} height={58} rx={6} fill="#24272B" stroke={ink} strokeWidth={3} />
            <rect x={-10} y={-41} width={24} height={44} rx={3} fill="#9FD3E6" />
          </g>
        )}
        {front && el.holding === 'coin' && <circle cx={6} cy={FA + 14} r={16} fill="#E3B341" stroke={ink} strokeWidth={3} />}
      </g>
    </g>
  );
  const leg = (hx: number, H: number, K: number, front: boolean) => (
    <g transform={`translate(${hx},${hipY}) rotate(${H})`}>
      {limb(TH, 30, front ? look.pants : shade(look.pants))}
      <g transform={`translate(0,${TH}) rotate(${K})`}>
        {limb(SH, 26, front ? look.pants : shade(look.pants))}
        <g transform={`translate(0,${SH + 6}) rotate(${-H - K})`}>
          <path d="M-14,-6 h26 q22,0 22,14 v4 h-48 z" fill={look.shoes} stroke={ink} strokeWidth={3.5} strokeLinejoin="round" />
        </g>
      </g>
    </g>
  );

  const m = MOODS.includes(mood as (typeof MOODS)[number]) ? mood : 'neutral';
  const brow =
    m === 'worried' || m === 'sad'
      ? {l: 'M-30,-24 l16,-6', r: 'M30,-24 l-16,-6'}
      : m === 'angry'
        ? {l: 'M-30,-30 l16,6', r: 'M30,-30 l-16,6'}
        : m === 'surprised'
          ? {l: 'M-30,-34 q8,-6 16,0', r: 'M30,-34 q-8,-6 -16,0'}
          : {l: 'M-30,-28 q8,-3 16,0', r: 'M30,-28 q-8,-3 -16,0'};
  const open = Math.min(1, amp * 1.6);
  const mouth =
    open > 0.08 ? (
      <ellipse cx={4} cy={22} rx={9 + 5 * open} ry={2 + 12 * open} fill="#5A1F1A" stroke={ink} strokeWidth={3} />
    ) : (
      <path
        d={
          m === 'happy'
            ? 'M-10,16 q14,14 28,0'
            : m === 'sad'
              ? 'M-8,24 q12,-10 24,0'
              : m === 'worried'
                ? 'M-8,22 q6,-5 12,0 q6,5 12,0'
                : m === 'surprised'
                  ? 'M0,20 a6,7 0 1 0 0.1,0'
                  : m === 'angry'
                    ? 'M-8,22 h24'
                    : 'M-6,20 q10,4 20,0'
        }
        fill="none"
        stroke={ink}
        strokeWidth={4}
        strokeLinecap="round"
      />
    );

  const hair = () => {
    const c = look.hair;
    switch (look.hairStyle) {
      case 'bun':
        return (
          <>
            <circle cx={-34} cy={-40} r={20} fill={c} stroke={ink} strokeWidth={4} />
            <path d="M-50,-6 q-2,-52 46,-52 q48,2 52,42 q-30,-22 -60,-18 q-24,4 -38,28 z" fill={c} stroke={ink} strokeWidth={4} />
          </>
        );
      case 'long':
        return <path d="M-52,40 q-14,-96 50,-98 q62,2 52,84 q-8,-46 -20,-56 q-40,14 -74,6 q-6,30 -8,64 z" fill={c} stroke={ink} strokeWidth={4} />;
      case 'cap':
        return (
          <>
            <path d="M-50,-14 q0,-48 50,-48 q50,0 50,48 z" fill={c} stroke={ink} strokeWidth={4} />
            <path d="M30,-16 h44 q6,0 0,8 h-50 z" fill={c} stroke={ink} strokeWidth={4} />
          </>
        );
      case 'bald':
        return null;
      default:
        return <path d="M-50,-4 q-4,-54 50,-54 q54,0 50,50 q-18,-24 -52,-26 q-30,0 -48,30 z" fill={c} stroke={ink} strokeWidth={4} />;
    }
  };

  return (
    <g transform={`scale(${inP})`} opacity={Math.min(1, inP * 2)} style={{filter: paperShadow}}>
      <g transform={`scale(${face},1)`}>
        {/* back limbs */}
        {leg(-10, pose.bH, pose.bK, false)}
        {arm(-30, pose.bS, pose.bE, shade(look.shirt), false)}
        {/* torso with lean around the hips */}
        <g transform={`rotate(${pose.lean} 0 ${hipY}) translate(0,${hipY}) scale(1,${1 + breathe}) translate(0,${-hipY}) translate(${sway * (1 - walking)},0)`}>
          <path
            d={`M-38,${shY - 2} q38,-14 76,0 l8,${hipY - shY + 6} q-46,10 -92,0 z`}
            fill={look.shirt}
            stroke={ink}
            strokeWidth={4}
            strokeLinejoin="round"
          />
          {/* belt line */}
          <path d={`M-44,${hipY - 2} q44,8 88,0`} stroke={ink} strokeWidth={3} fill="none" opacity={0.6} />
          {/* neck + head */}
          <rect x={-11} y={shY - 22} width={22} height={26} fill={look.skin} stroke={ink} strokeWidth={4} />
          <g transform={`translate(4,${shY - 66}) rotate(${pose.tilt})`}>
            <circle cx={0} cy={0} r={50} fill={look.skin} stroke={ink} strokeWidth={4} />
            {/* ear */}
            <ellipse cx={-38} cy={6} rx={8} ry={12} fill={look.skin} stroke={ink} strokeWidth={3.5} />
            {hair()}
            {/* eyes look toward gaze */}
            <g transform={`translate(${8 + gaze * 6},${2})`}>
              <ellipse cx={-14} cy={-4} rx={9} ry={11 * blink} fill="#FFFDF8" stroke={ink} strokeWidth={2.5} />
              <ellipse cx={18} cy={-4} rx={9} ry={11 * blink} fill="#FFFDF8" stroke={ink} strokeWidth={2.5} />
              {blink > 0.5 && (
                <>
                  <circle cx={-12 + gaze * 3} cy={-3 + (pose.tilt > 10 ? 3 : 0)} r={4.5} fill={ink} />
                  <circle cx={20 + gaze * 3} cy={-3 + (pose.tilt > 10 ? 3 : 0)} r={4.5} fill={ink} />
                </>
              )}
              <g stroke={ink} strokeWidth={4} strokeLinecap="round" fill="none">
                <path d={brow.l} transform="translate(2,0)" />
                <path d={brow.r} transform="translate(2,0)" />
              </g>
              {mouth}
            </g>
          </g>
        </g>
        {/* front limbs */}
        {leg(12, pose.fH, pose.fK, true)}
        {arm(30, pose.fS, pose.fE, look.shirt, true)}
      </g>
      {el.label && (
        <text x={0} y={52} textAnchor="middle" fontFamily="Caveat" fontWeight={700} fontSize={40} fill={ink} opacity={inP}>
          {el.label}
        </text>
      )}
    </g>
  );
};

/** Slightly darker copy of a colour for limbs on the far side. */
function shade(hex: string) {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.round(((n >> 16) & 255) * 0.82);
  const g = Math.round(((n >> 8) & 255) * 0.82);
  const b = Math.round((n & 255) * 0.82);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`;
}
