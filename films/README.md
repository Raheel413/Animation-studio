# films/

Drop a scenes file here (for example `films/my-video.scenes.json`) and push it to `main`.
GitHub renders it in the cloud and attaches the MP4 to the run.

1. Push the file.
2. Open the **Actions** tab and click the newest **Render video** run.
3. When it goes green, download the video from **Artifacts** at the bottom of the run page.

Push several files at once and they render in parallel, one machine each.

To render a file that lives somewhere else, or to make the ElevenLabs voiceover first, use
**Actions → Render video → Run workflow** and fill in the form. The voiceover option needs a
repository secret named `ELEVENLABS_API_KEY` (Settings → Secrets and variables → Actions).

This repo is public, so anything you push here, and the rendered videos, can be seen by anyone.
Keep unreleased client scripts in a private repo.
