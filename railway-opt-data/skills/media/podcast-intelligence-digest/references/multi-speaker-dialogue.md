# Multi-Speaker Dialogue Production Notes

Use this reference when a user provides a host/dialogue script (`MAYA:`, `SAM:`, etc.) or asks for an explainer podcast in that style.

## Core rule

Speaker labels are directions for production, not narration. Never synthesize `MAYA:` or `SAM:` as spoken words unless the user explicitly asks for a table read.

## Recommended segment representation

Store scripts as structured segments before synthesis:

```json
[
  {"type": "music", "cue": "INTRO MUSIC FADES IN, THEN UNDER"},
  {"speaker": "MAYA", "text": "Hey, welcome back to The Overview. I’m Maya."},
  {"speaker": "SAM", "text": "And I’m Sam. Today I want to start with a question."},
  {"type": "pause", "duration": 0.75},
  {"speaker": "MAYA", "text": "Okay, sell me."},
  {"type": "music", "cue": "OUTRO MUSIC SWELLS, FADES"}
]
```

Benefits:
- Voice selection uses `speaker`.
- TTS receives only `text`.
- Cues become actual music/silence, not spoken words.
- Failed segments can be regenerated independently.

## Voice-quality preference

For polished podcasts, check premium TTS first:
1. ElevenLabs when `ELEVENLABS_API_KEY` is configured.
2. Other high-quality configured providers (OpenAI/MiniMax/Mistral/etc.).
3. Free neural fallback with distinct voices.

When falling back, still use separate voices per speaker and disclose the limitation after delivery.

## Production checklist for dialogue

- Parse every `SPEAKER:` line into `{speaker, text}`.
- Remove bracketed directions from TTS text: `[BEAT]`, `[laughs]`, `[INTRO MUSIC]`.
- Choose stable voice mapping per speaker for the whole episode.
- Add short gaps between turns (roughly 0.15–0.35s) and longer gaps for `[BEAT]` (roughly 0.6–1.0s).
- Normalize segments to a common sample rate/channel count before concat.
- Verify the final file with `ffprobe` and deliver via `MEDIA:/absolute/path` on Telegram.

## Failure mode to avoid

A single voice reading labels aloud sounds like one person reading a script, not a conversation. If that is the only possible output path, tell the user before producing it or label it clearly as a rough narration draft.

Also avoid assuming the model will emit clean `MAYA:` / `SAM:` lines. In practice the script may arrive with markdown emphasis (`**MAYA:**`), blank spacer lines after labels, or other formatting noise. Normalize those away before parsing, then synthesize from speaker turns plus explicit pause cues.
