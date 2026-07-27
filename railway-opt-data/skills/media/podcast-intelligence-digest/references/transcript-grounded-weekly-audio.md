# Transcript-grounded weekly audio notes

Session lesson: the weekly "podcast of podcasts" should not be built from digest bullets alone.

## Grounding order

1. Pick the week's strongest episode finalists from the daily digests.
2. Look up the episode in the local podcast DB to recover better link/audio metadata when the digest URL is thin.
3. Fetch the episode page text.
4. Prefer actual transcript-like page text when present; otherwise use the page description/excerpt as fallback grounding.
5. Record how many finalists were transcript-grounded so the run can report coverage.

## Script requirements

- The LLM should write an *original* two-host conversation, not a summary list.
- Speaker turns should be short and speakable.
- Use the page text/transcript excerpts as the grounding source; do not ask the model to invent specifics.
- Keep the angle tuned to DJ's taste: CEOs, investors, AI leaders, platform strategy, software economics, durable frameworks.

## Audio production requirements

- Parse the script as dialogue, not as one monolithic TTS blob.
- Remove markdown bold and stage directions before synthesis.
- Use distinct voices for MAYA and SAM, with slight rate/pitch differences so the hosts do not sound cloned.
- Insert natural pauses between turns and slightly longer pauses at section breaks.
- Convert each synthesized chunk to a common sample rate/channel count before concatenation.
- Verify the final file with `ffprobe` and deliver with `MEDIA:/absolute/path`.

## Practical checks

- The weekly audio should sound like a real conversation, not a narrated outline.
- If the result sounds mechanical, improve dialogue segmentation/voice mapping before changing the model prompt.
- Report transcript-grounded coverage in the run output so quality regressions are obvious.