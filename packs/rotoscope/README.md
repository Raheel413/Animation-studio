# Rotoscope (planned)

**Ceiling: 7/10.** Needs source footage. Use footage you shot or have the rights to; tracing someone else's video does not remove their copyright.

Pipeline: footage -> ffmpeg frame extraction at 12 fps (on twos) -> edge and region tracing (OpenCV edge detection + colour quantization, optional potrace vector lines) -> boil/jitter and flat fills -> reassemble with ffmpeg and the voiceover.

Build order: 1) trace script with 3 look presets (ink line, flat colour, line + flats), 2) temporal smoothing to control flicker, 3) one 30 s test.
