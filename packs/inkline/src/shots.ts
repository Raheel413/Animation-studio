import type {Scene} from './types';

/** Shots: runs of consecutive scenes on the same strip panel. */
export const shotStart = (scenes: Scene[], i: number) => {
  let j = i;
  while (j > 0 && scenes[j - 1].strip_x === scenes[i].strip_x) j--;
  return j;
};
export const shotEnd = (scenes: Scene[], i: number) => {
  let j = i;
  while (j < scenes.length - 1 && scenes[j + 1].strip_x === scenes[i].strip_x) j++;
  return j;
};
