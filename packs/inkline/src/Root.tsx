import React from 'react';
import {Composition} from 'remotion';
import {Inkline} from './Inkline';
import type {Film} from './types';
import sample from '../examples/ten-years.scenes.json';

export const Root: React.FC = () => (
  <Composition
    id="Inkline"
    component={Inkline as unknown as React.FC<Record<string, unknown>>}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={300}
    defaultProps={{film: sample as unknown as Film}}
    calculateMetadata={({props}) => {
      const film = (props as {film: Film}).film;
      const fps = film.fps ?? 30;
      const end = film.scenes[film.scenes.length - 1].t_end;
      return {fps, width: film.width ?? 1920, height: film.height ?? 1080, durationInFrames: Math.ceil((end + 0.6) * fps)};
    }}
  />
);
