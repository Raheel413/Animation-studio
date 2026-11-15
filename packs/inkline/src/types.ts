export type Side = 'a' | 'b' | null;

export type ElementBase = {
  type: string;
  life?: number; // scenes it stays on screen, counting its own (default: until the shot ends)
  x: number; // px inside the 1920x1080 panel
  y: number;
  at?: number; // seconds after scene start
  side?: Side;
  scale?: number;
};


export type CharacterEl = ElementBase & {
  type: 'character';
  who: string;
  mood?: 'neutral' | 'happy' | 'sad' | 'worried';
  holding?: 'phone' | 'coin' | null;
  label?: string;
  enter?: 'draw' | 'left' | 'right';
  talk?: boolean; // mouth moves while the scene plays
};
export type StampEl = ElementBase & {type: 'stamp'; text: string; rotate?: number};
export type TallyEl = ElementBase & {type: 'tally'; count: number};
export type NoteEl = ElementBase & {type: 'note'; text: string; size?: number};
export type BarsEl = ElementBase & {
  type: 'bars';
  rows: {label: string; value: number; display: string; side: Side}[];
  width?: number;
};
export type CheckGridEl = ElementBase & {type: 'checkgrid'; total: number; filled: number; cols?: number};
export type PropEl = ElementBase & {type: 'prop'; kind: 'building' | 'desk' | 'coin' | 'phone' | 'calendar' | 'sheet' | 'ground' | 'bus' | 'server' | 'chair'; text?: string; w?: number; h?: number; rotate?: number};

export type ClippingEl = ElementBase & {
  type: 'clipping';
  source: string; // outlet name, printed small at the top
  date?: string;
  lines: string[]; // headline, pre-broken into lines
  hl?: number[]; // line indexes the highlighter sweeps over
  w?: number;
  size?: number;
  rotate?: number;
};
export type LineChartEl = ElementBase & {
  type: 'linechart';
  points: {v: number; t?: number; label?: string; tag?: string; tagDx?: number; tagDy?: number}[];
  title?: string;
  w?: number;
  h?: number;
  min?: number;
  max?: number;
  ref?: number; // dashed reference line, e.g. the old peak
  refLabel?: string;
  draw?: number; // frames the line takes to draw
};

export type ActorLook = {skin?: string; hair?: string; hairStyle?: 'short' | 'bun' | 'long' | 'cap' | 'bald'; shirt?: string; pants?: string; shoes?: string};
export type ActorEl = ElementBase & {
  type: 'actor';
  who: string; // matches a scene's speaker for lip-sync, and cues
  look?: ActorLook;
  pose?: string;
  mood?: string;
  gaze?: number; // -1 back .. 1 front
  face?: 1 | -1; // 1 faces right
  holding?: 'phone' | 'coin' | null;
  label?: string;
};
export type El = ActorEl | CharacterEl | StampEl | TallyEl | NoteEl | BarsEl | CheckGridEl | PropEl | ClippingEl | LineChartEl;

export type Scene = {
  id: string;
  t_start: number;
  t_end: number;
  vo: string;
  strip_x: number; // panel index on the strip
  elements: El[];
  camera?: {zoom?: number; focus?: [number, number]};
  transition_in?: 'travel' | 'ink_flood' | 'fold' | 'cut' | 'none';
  spine?: {text: string; value?: string};
  speaker?: string; // voice to use for this line (narrator by default)
  cues?: Cue[]; // direct actors already on screen
  hold?: boolean;
};

export type Cue = {who: string; at?: number; pose?: string; mood?: string; look?: number; face?: 1 | -1; walkTo?: number; walkDur?: number};

export type Film = {
  format: 'inkline';
  title?: string;
  fps?: number;
  width?: number;
  height?: number;
  palette: {paper: string; ink: string; a: string; b: string};
  spine: 'ledger' | 'route' | 'none';
  vo_file?: string | null; // file in public/
  music_file?: string | null;
  sfx?: boolean;
  scenes: Scene[];
};
