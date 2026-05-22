Podcast/audio generation preference: character labels in scripts are speaker directions and must not be read aloud; use distinct voices per character; prefer ElevenLabs or similarly high-quality TTS; output should feel like a real conversation, not one narrator reading labels.
§
Environment: python3-pip and edge-tts are installed; /root/.local/bin/edge-tts can synthesize selectable Edge neural voices for multi-speaker podcast assembly when ElevenLabs is unavailable.
§
Environment: xurl is installed at /usr/local/bin/xurl, but no X app/OAuth credentials are registered; unauthenticated reads via xurl return 401 until user completes xurl auth setup.