export type Side = 'a' | 'b' | null;

export type ElementBase = {
  type: string;
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
export type PropEl = ElementBase & {type: 'prop'; kind: 'building' | 'desk' | 'coin' | 'phone' | 'calendar' | 'sheet' | 'ground'; text?: string; w?: number; h?: number; rotate?: number};

export type El = CharacterEl | StampEl | TallyEl | NoteEl | BarsEl | CheckGridEl | PropEl;

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
};

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
