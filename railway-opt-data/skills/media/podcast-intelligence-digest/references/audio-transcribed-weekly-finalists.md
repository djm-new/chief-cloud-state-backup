# Audio-transcribed weekly finalists

Use this when DJ asks for the weekly podcast-of-podcasts to truly "listen" to episodes with no transcript. Do not ask DJ to download audio.

## Required behavior

- For weekly finalists, classify each source as one of:
  - `page_transcript_like: true` — page/transcript text is primary grounding.
  - `audio_transcript_status: transcribed|cached` — podcast audio was downloaded and transcribed locally.
  - metadata-only — explicit fallback; do not imply the episode was listened to.
- Audio-only finalists must be downloaded server-side from RSS `audio_url`, transcribed locally, chunked, and condensed into evidence notes before script drafting.
- Production transcription must use full audio. `PODCAST_WEEKLY_STT_MAX_SECONDS=0` means full episode; use positive values only for smoke tests.

## Current implementation pattern

- Script: `/opt/data/scripts/podcast_weekly_audio.py`
- STT env: `/opt/data/venvs/podcast-stt`
- STT packages: `faster-whisper` + `ctranslate2`
- Default STT model: `PODCAST_WEEKLY_STT_MODEL=base`
- Transcript cache: `/opt/data/podcast_digest/transcripts/<stable_episode_key>/`
- Transcript artifact: `transcript.txt`
- Chunk evidence artifact: `chunk-notes.md`
- Metadata artifact: `meta.json` with duration/segment count and `max_seconds`

Example production run:

```bash
export PODCAST_WEEKLY_FORCE_RUN=1
export PODCAST_WEEKLY_TRANSCRIBE_AUDIO=1
export PODCAST_WEEKLY_STT_MAX_SECONDS=0
export PODCAST_WEEKLY_STT_MODEL=base
export PODCAST_WEEKLY_TTS_BACKEND=piper
/opt/hermes/.venv/bin/python /opt/data/scripts/podcast_weekly_audio.py --days 7 --top-n 5
```

Smoke test only:

```bash
PODCAST_WEEKLY_STT_MAX_SECONDS=30 PODCAST_WEEKLY_TRANSCRIBE_AUDIO=1 \
  /opt/hermes/.venv/bin/python /opt/data/scripts/podcast_weekly_audio.py --days 7 --top-n 1 --dry-run
```

## Verification gates

Before sending the product, verify:

1. `python3 -m py_compile /opt/data/scripts/podcast_weekly_audio.py`
2. Source JSON shows every finalist and grounding status.
3. Counts printed by the run include both:
   - `Transcript-grounded finalists: X/N`
   - `Audio-transcribed finalists: Y/N`
4. For each audio-transcribed finalist, inspect `meta.json` and confirm:
   - `max_seconds` is `0` for production.
   - transcript duration roughly matches the source audio duration.
   - transcript segments are non-trivial.
5. Final script names every finalist episode, not just the top three.
6. Final audio passes `ffprobe` with Opus/OGG, mono/48kHz, and plausible duration.

## Pitfalls from June 2026 calibration

- A successful STT run is not enough: the script model can still write a short generic draft or silently drop a finalist. Compare the source JSON against the final script before delivery.
- If the model-produced script is too compressed, use the grounded source JSON and transcript notes to expand a finished episode-first script manually/with a stronger generation pass. Do not ship a four-minute digest when DJ asked for a meaningful weekly podcast.
- Do not let theme synthesis precede episode coverage. Each main block must begin with show, episode, guest/person, thesis, and DJ-relevant takeaway.
- Do not speak speaker labels. `MAYA:` / `SAM:` are production directions only.
