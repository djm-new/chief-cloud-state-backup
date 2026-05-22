---
name: podcast-audio-production
description: "Use when turning a script, outline, or article into a deliverable podcast/audio episode. Covers script prep, TTS chunking, ffmpeg assembly, intro/outro beds, verification, and Telegram media delivery."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [podcast, audio, tts, ffmpeg, media-production, telegram]
    related_skills: [songwriting-and-ai-music, songsee]
---

# Podcast Audio Production

## Overview

Use this skill to produce a podcast-style audio file from a user-provided script or source material. The goal is a usable media artifact, not just a rewritten script: clean narration, optional simple intro/outro music, a standard audio container, and verification before delivery.

This skill is intentionally pragmatic. If premium multi-speaker voice cloning or studio mastering tools are not available, produce the best reliable version with the available TTS and `ffmpeg`, clearly noting any limitations only after delivering the artifact.

## When to Use

- User says "make this podcast," "turn this into audio," "record this script," or asks for a spoken episode from text.
- User provides a host/dialogue script with speaker labels and expects an audio deliverable.
- User asks for a short narrated explainer, news brief, voice memo, or podcast segment.
- You need to assemble multiple TTS segments into one final MP3/OGG/WAV with pauses/music.

Don't use for:

- Pure music generation from lyrics/tags — use `songwriting-and-ai-music` or `heartmula` instead.
- Audio analysis/spectrogram/feature extraction — use `songsee`.
- YouTube transcript extraction/summarization — use `youtube-content` first, then this skill if audio output is requested.

## Default Workflow

1. **Parse the user's intent and deliverable.**
   - If they ask to "make" a podcast and provide a script, assume they want an audio file unless they explicitly ask for text editing only.
   - Preserve the user's script unless they ask for rewriting, fact-checking, or shortening.
   - Remove or adapt bracketed production cues like `[BEAT]` and `[laughs]` if the TTS engine reads them awkwardly.

2. **Prepare a clean production script.**
   - Save the cleaned script to `/tmp/<slug>_script.txt` or structured `/tmp/<slug>_segments.json` for reproducibility.
   - Treat labels such as `MAYA:` / `SAM:` as **speaker directions, not spoken text**. Strip labels before TTS; never let the output say the character name before every line unless the user explicitly asks for a table read.
   - For dialogue, split by speaker and synthesize with distinct voices. This is required for a two-host podcast feel; a single narrator reading alternating lines is a fallback only if the user approves or no other path is possible.
   - Prefer high-quality TTS providers for final deliverables, especially ElevenLabs when `ELEVENLABS_API_KEY` is available. If premium TTS is unavailable, use the best available multi-voice neural provider and disclose the limitation after delivering.

3. **Chunk long scripts before TTS.**
   - Split on paragraph boundaries into chunks of roughly 2,000-3,500 characters.
   - Smaller chunks improve reliability and make retries cheap.
   - Name outputs predictably: `/tmp/<slug>_voice_1.ogg`, `/tmp/<slug>_voice_2a.ogg`, etc.

4. **Generate TTS.**
   - For polished podcast work, check for premium providers first: ElevenLabs (`ELEVENLABS_API_KEY`), then OpenAI/MiniMax/Mistral if configured, then free neural TTS fallbacks.
   - Use separate voice IDs/names per host (e.g. one female-presenting voice for Maya, one male-presenting voice for Sam when the script implies that pairing). Keep voices consistent across the whole episode.
   - Send only the line text to TTS — no `MAYA:`, `SAM:`, bracketed cues, or stage directions.
   - Use the available TTS tool if present.
   - For transient provider failures on a long chunk, retry by splitting that chunk into smaller parts rather than restarting the whole episode.
   - Keep successful chunks and only regenerate failed ones.

5. **Assemble with `ffmpeg`.**
   - Verify `ffmpeg` is available.
   - Convert all voice chunks to a common format, sample rate, and channel count before concatenation.
   - Add short silence between chunks (0.5-1.0s) for breath.
   - If the script requests intro/outro music and no music asset is supplied, generate a subtle tonal bed rather than leaving the cue literal.

6. **Export a delivery format.**
   - Default to MP3 for podcasts because it is broadly supported.
   - Use OGG/Opus when the platform should send a voice-note style bubble.
   - Use clear names like `/tmp/the-overview-orbital-data-centers.mp3`.

7. **Verify before replying.**
   - Run `ffprobe` on the final file.
   - Check codec, duration, size, channel count, and sample rate.
   - Ensure all intended chunks are present in the concat list.

8. **Deliver through the platform.**
   - On Telegram, include `MEDIA:/absolute/path/to/file` in the final response.
   - Include runtime and a short note about what was produced.
   - If the user asks about faster listening, mention Telegram's player speed controls when available, or suggest opening the MP3 in a podcast/audio app such as VLC/Overcast/Apple Podcasts that supports 1.25x-2x playback.

## Multi-Speaker Dialogue Standard

For host/interview scripts, the default deliverable is a produced conversation, not a table read.

- Parse each `SPEAKER: line` into structured segments like `{"speaker":"MAYA","text":"..."}` and synthesize only the `text`.
- Use distinct voices per speaker and maintain a stable mapping for the whole episode.
- Convert `[BEAT]` into silence, music cues into actual beds, and stage directions like `[laughs]` into performance direction or omission — not spoken words.
- If a premium provider such as ElevenLabs is configured, use it for final podcast output. If it is not configured, use the best available distinct neural voices and say so in the final note.
- See `references/multi-speaker-dialogue.md` for the structured segment pattern and production pitfalls.

## Useful Commands

Generate simple intro/outro beds when no music asset is available:

```bash
ffmpeg -y \
  -f lavfi -i "sine=frequency=220:duration=4" \
  -f lavfi -i "sine=frequency=330:duration=4" \
  -filter_complex "[0:a][1:a]amix=inputs=2:normalize=0,volume=0.10,afade=t=in:st=0:d=0.8,afade=t=out:st=3:d=1" \
  -ar 44100 -ac 2 -b:a 160k /tmp/intro.mp3
```

Generate short silence:

```bash
ffmpeg -y -f lavfi -i "anullsrc=r=44100:cl=stereo" -t 0.7 -b:a 160k /tmp/silence.mp3
```

Normalize voice chunks to a common MP3 format:

```bash
for f in /tmp/episode_voice_*.ogg; do
  out="${f%.ogg}.mp3"
  ffmpeg -y -i "$f" -ar 44100 -ac 2 -b:a 160k "$out"
done
```

Create a concat manifest:

```bash
cat > /tmp/episode_concat.txt <<'EOF'
file '/tmp/intro.mp3'
file '/tmp/silence.mp3'
file '/tmp/episode_voice_1.mp3'
file '/tmp/silence.mp3'
file '/tmp/episode_voice_2.mp3'
file '/tmp/silence.mp3'
file '/tmp/outro.mp3'
EOF
```

Concatenate and verify:

```bash
ffmpeg -y -f concat -safe 0 -i /tmp/episode_concat.txt -c copy /tmp/final-episode.mp3
ffprobe -v error \
  -select_streams a:0 \
  -show_entries stream=codec_name,channels,sample_rate \
  -show_entries format=duration,size \
  -of json /tmp/final-episode.mp3
```

## Handling Long Scripts and TTS Provider Errors

- A TTS provider can fail on one chunk while others succeed. Treat that as a partial success.
- Retry only the failed chunk, ideally split into two or more smaller chunks at paragraph breaks.
- Do not encode transient failures as durable claims about the provider being unavailable.
- If a chunk repeatedly fails because of punctuation or special characters, simplify curly quotes, em dashes, bracketed cues, and unusual symbols in that chunk.

## Script Cleanup Guidelines

- Convert `[INTRO MUSIC FADES IN]` and `[OUTRO MUSIC]` into actual audio-bed placement when feasible.
- Convert `[BEAT]` into silence in assembly or remove it from TTS text.
- Convert stage directions like `*[laughs]*` into either a natural phrase omission or leave it out; most TTS engines read these literally.
- Keep pronunciation-sensitive names intact unless the user asks for phonetic spelling.

## Common Pitfalls

1. **Reading speaker labels aloud.** `MAYA:` / `SAM:` are production directions. Strip them before synthesis and use them only to choose the voice.
2. **Using one voice for a two-host script.** This sounds like a person reading a script, not a conversation. Use separate voices per character/host.
3. **Using low-quality TTS when premium TTS is configured.** Prefer ElevenLabs or another high-quality provider for final podcasts; fall back only when credentials/tools are unavailable.
4. **Delivering only text when the user asked to make a podcast.** Produce an audio file and attach it.
5. **Sending unverified media.** Always run `ffprobe` on the final file before delivery.
6. **One giant TTS request.** Long scripts are more fragile; chunk them before synthesis.
7. **Restarting after one failed chunk.** Keep successful outputs and split/retry only the failed chunk.
8. **Literal production cues in narration.** Remove or implement cues; don't let TTS read `[BEAT]` as dialogue.
9. **Mismatched concat formats.** Convert all inputs to the same codec/sample rate/channels or use a re-encoding concat path.
10. **Overclaiming production quality.** If premium TTS was unavailable, call out the limitation briefly after delivering.

## Verification Checklist

- [ ] Clean script saved under `/tmp` or a task workspace.
- [ ] Long script split into reliable TTS-sized chunks.
- [ ] Every TTS chunk generated successfully.
- [ ] Dialogue speaker labels stripped from spoken TTS text.
- [ ] Distinct, consistent voices assigned for each recurring speaker.
- [ ] Premium TTS checked first for polished podcast requests when credentials are available.
- [ ] Music/silence cues implemented or intentionally omitted.
- [ ] Final audio assembled in a common deliverable format.
- [ ] `ffprobe` confirms codec, duration, size, channels, and sample rate.
- [ ] Final response includes `MEDIA:/absolute/path/to/file` and runtime.
