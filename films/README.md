# films/

Drop a scenes file here (for example `films/my-video.scenes.json`) and push it to `main`.
GitHub renders it in the cloud and attaches the MP4 to the run.

1. Push the file.
2. Open the **Actions** tab and click the newest **Render video** run.
3. When it goes green, download the video from **Artifacts** at the bottom of the run page.

Push several files at once and they render in parallel, one machine each.

Every render makes the voiceover first with Deepgram (American male voice `aura-2-zeus-en`), as long as
the repository secret `DEEPGRAM_API_KEY` exists (Settings → Secrets and variables → Actions).
The voice MP3 is included in the download.

To pick another voice, use ElevenLabs, or render a file that lives somewhere else, use
**Actions → Render video → Run workflow** and fill in the form.

This repo is public, so anything you push here, and the rendered videos, can be seen by anyone.
Keep unreleased client scripts in a private repo.
