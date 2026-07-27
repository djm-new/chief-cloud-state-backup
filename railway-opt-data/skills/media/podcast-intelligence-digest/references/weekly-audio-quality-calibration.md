# Weekly Audio Quality Calibration

Use this reference when producing DJ's weekly podcast-of-podcasts audio digest.

## Current User Feedback

- Content quality improved when the workflow used finalist transcripts/audio transcription and episode-first synthesis.
- The delivery still failed when hosts sounded like two people alternating formulaic summaries.
- Preferred host dynamic:
  - **Expert/reviewer**: listened/read deeply, explains the episode's argument and why it matters.
  - **Interlocutor**: asks clarifying questions, challenges assumptions, draws out implications, and adds context/background facts that make the source easier to understand.
- Avoid: `MAYA summarizes thesis → SAM summarizes strongest argument → MAYA gives counterpoint → SAM gives why DJ should care` as a repeating template.
- Use the interlocutor to create real exchange: "Is that just branding?", "What is the weak point?", "Why should a software investor care about minerals?", "What question should DJ ask when diligencing this?"

## Voice Calibration

- Piper and Edge neural voices were judged too robotic for the weekly digest.
- Kokoro `af_heart` was judged good for Maya/expert.
- Candidate Sam/interlocutor Kokoro voices tested in order:
  1. `am_echo`
  2. `am_eric`
  3. `am_fenrir`
  4. `am_liam`
  5. `am_michael`
  6. `am_onyx`
  7. `am_puck`
  8. `bm_george`
  9. `bm_lewis`
- Sample artifact from this calibration: `/opt/data/podcast_digest/outputs/kokoro-sam-voice-options.ogg`.
- If no Kokoro Sam voice is acceptable, the next real quality step is premium TTS (ElevenLabs/OpenAI/Gemini/xAI/Mistral) rather than more local Piper/Edge tweaking.

## Practical Script Guidance

For each episode segment, prefer this conversational pattern:

1. Expert names show, episode, guest, and thesis.
2. Interlocutor asks the obvious high-value question DJ would ask.
3. Expert answers with transcript-grounded detail.
4. Interlocutor reframes the implication or adds background.
5. Expert gives the counterpoint/uncertainty.
6. Interlocutor asks what DJ should do with it.
7. Expert gives the actionable mental model.

Do not force every segment into the exact same seven turns; use it as a guardrail against summary-recitation.

## Production Checks

- Confirm each finalist's grounding label in the source JSON:
  - `page_transcript_like: true`, or
  - `audio_transcript_status: transcribed|cached`, or
  - explicitly metadata-only with a reason.
- Listen to at least the opening minute before delivery when changing voices.
- Verify the final `.ogg` with `ffprobe` for codec, duration, sample rate, channels, and size.
