# Local TTS backend calibration

## Outcome
Earlier testing found **Piper** was the fastest cost-effective local backend, but DJ later judged both **Piper** and **Edge TTS** too robotic for the weekly digest. Do not treat speed as production quality.

### Tested options
- **Piper**: fast and reliable locally, but too robotic for DJ's production weekly digest.
- **Edge TTS**: easy fallback and somewhat better than Piper in places, but still not natural enough.
- **Kokoro**: local option now under active calibration; `af_heart` was judged good for Maya/expert, and alternate Sam/interlocutor voices are being tested.
- **Chatterbox**: installable locally, but CPU synthesis was too slow for weekly production use in this environment.

## Practical recommendation
For production-quality weekly audio, prefer a truly natural voice stack. If premium credentials/gateway are available, test ElevenLabs/OpenAI/Gemini/xAI/Mistral before spending more time tweaking Piper/Edge. If staying local, continue Kokoro calibration first.

## Working Piper recipe
1. Create or use an isolated Python 3.11 environment for TTS tooling.
2. Install `piper-tts` into that environment.
3. Download voices with `python -m piper.download_voices <voice> --download-dir <dir>`.
4. Prefer distinct voices for MAYA/SAM rather than relying on rate/pitch changes alone.
5. Render to WAV, then concatenate/encode to Opus for Telegram delivery.

- Useful local voices
- Kokoro MAYA/expert: `af_heart` (approved as good by DJ)
- Kokoro SAM/interlocutor: `am_eric` (chosen by DJ)
- Weekly podcast default local voice backend: Kokoro with MAYA=`af_heart`, SAM=`am_eric`, rendered as native Telegram Opus audio with output tempo 1.5x (`PODCAST_WEEKLY_OUTPUT_SPEED=1.5`).
- Piper voices below are fallback/testing only, not production-approved:
  - `en_US-hfc_female-medium`
  - `en_US-hfc_male-medium`
  - `en_US-lessac-medium`

## Notes
- Chatterbox may require patching around its watermarking dependency if used as a local experiment.
- Kokoro's quality is decent, but its CPU workflow was too slow for the weekly show compared with Piper.
- If a future environment has a stronger GPU-backed local voice stack, re-evaluate, but do not assume heavier models are better for production cost/performance.
