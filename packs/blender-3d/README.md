# 3D with Blender (planned)

**Ceiling: 7/10 for stylized, low-poly or clay looks. Not film-studio realism.**

Blender run headless (`blender -b -P script.py`) with Python that builds scenes from the same scenes.json: primitives and modifiers for models, keyframed cameras, toon or clay shaders, Eevee for speed. Frames come back as image sequences and are joined with the voiceover by ffmpeg.

Limits: needs 16 GB RAM and a GPU to be practical; a 10-minute film is hours of rendering. Organic characters are the weak point; machines, vehicles, maps and architecture are the strong point.

Build order: 1) scene builder for primitives + camera moves, 2) shader presets, 3) chunked render + resume, 4) one 60 s test film.
