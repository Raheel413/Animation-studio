#!/usr/bin/env bash
# Synthesizes the paper-foley set with ffmpeg. Replace any file in public/sfx with a recorded one for more realism.
set -e; o=public/sfx; mkdir -p $o; q="-loglevel error -y"
ffmpeg $q -f lavfi -i "anoisesrc=d=0.9:c=pink:a=0.5" -af "highpass=f=2500,lowpass=f=7500,tremolo=f=19:d=0.9,afade=t=in:d=0.04,afade=t=out:st=0.6:d=0.3" $o/pen.wav
ffmpeg $q -f lavfi -i "anoisesrc=d=0.35:c=pink:a=0.5" -af "highpass=f=2800,lowpass=f=8000,tremolo=f=24:d=0.9,afade=t=out:st=0.2:d=0.15" $o/pen_short.wav
ffmpeg $q -f lavfi -i "anoisesrc=d=0.7:c=brown:a=0.9" -af "highpass=f=500,lowpass=f=3800,afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.4" $o/slide.wav
ffmpeg $q -f lavfi -i "anoisesrc=d=0.5:c=white:a=0.5" -af "highpass=f=1200,lowpass=f=6000,afade=t=in:d=0.02,afade=t=out:st=0.08:d=0.4,aecho=0.6:0.3:35:0.3" $o/fold.wav
ffmpeg $q -f lavfi -i "sine=f=68:d=0.35" -f lavfi -i "anoisesrc=d=0.08:c=brown:a=1" -filter_complex "[0]afade=t=out:st=0.02:d=0.3,volume=2.2[a];[1]lowpass=f=1800,afade=t=out:d=0.08[b];[a][b]amix=inputs=2:normalize=0" $o/stamp.wav
ffmpeg $q -f lavfi -i "anoisesrc=d=1.2:c=white:a=0.6" -af "highpass=f=3000,tremolo=f=11:d=1,afade=t=out:st=0.9:d=0.3" $o/ticks.wav
