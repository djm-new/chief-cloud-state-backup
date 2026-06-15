# Weekly audio pipeline notes

This note captures the working end-to-end pattern for DJ's weekly "podcast of podcasts" audio briefing.

## What worked

- Entry script: `/opt/data/scripts/podcast_weekly_audio.py`
- Invocation used for validation: `PODCAST_WEEKLY_FORCE_RUN=1 /opt/hermes/.venv/bin/python3 /opt/data/scripts/podcast_weekly_audio.py --days 7 --top-n 5`
- Output artifacts:
  - `...-weekly-podcast-of-podcasts.md`
  - `...-weekly-podcast-of-podcasts-sources.json`
  - `...-weekly-podcast-of-podcasts-meta.json`
  - `weekly-podcast-of-podcasts-YYYY-MM-DD.ogg`

## Reliable pipeline shape

1. Discover the week's strongest items from the daily digests.
2. Optionally fetch supporting page text/description excerpts for the finalists.
3. Ask the model for an *original* two-host script, not a recap.
4. Chunk the script into TTS-sized pieces.
5. Synthesize each chunk with Hermes TTS.
6. Concatenate/re-encode to a final OGG/Opus file.
7. Verify with `ffprobe` before delivery.
8. Deliver on Telegram with `MEDIA:/absolute/path/to/file`.

## Production notes

- The script includes a time gate so it only runs in the intended weekly window unless `PODCAST_WEEKLY_FORCE_RUN=1` is set.
- The first concat attempt should be re-encoded to OGG/Opus if stream-copying MP3 chunks fails.
- The final output should be a durable text artifact plus audio, not audio alone.
- The show should stay tailored to DJ's interests: AI platform strategy, capital allocation, governance, operator insights, and durable market frameworks.

## Verification

- Use `ffprobe` to confirm codec, channels, sample rate, and duration.
- Confirm the markdown script reads like a real two-host show (`MAYA` / `SAM`), with a closing "what DJ should watch next week" section.
