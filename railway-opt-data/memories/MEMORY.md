Podcast prefs: labels not read aloud; distinct natural voices; Piper/Edge too robotic. Daily text + weekly 15–20m two-host audio. Focus top money managers/CEOs/AI leaders/frontier thinkers; skip news/politics/celebrity/VC fluff.
§
DJ's Google policy: read/search/summarize OK; create/edit/delete Calendar/Docs/Sheets/Drive files when requested; never send Gmail/reply/forward or trigger external notifications. Outbound email/share/invite content is draft-only unless DJ changes policy.
§
Chief group topics: General, Archive, Briefings, Alerts, Brain Dump, Coding, and General/ad-hoc; topic overrides persist across /new unless removed.
§
Use GitHub as source of truth and treat Railway as runtime/deployment only; for repeat app work, check the existing repo/service and rerun the proven pipeline before proposing anything new.
§
Hermes spend reconciliation uses mixed-provider, per-call attribution. The podcast OpenRouter zero-cost bug in openrouter_spend.py was fixed and backfilled from raw_usage_json.
§
Podcast weekly pipeline has a local STT venv at /opt/data/venvs/podcast-stt with faster-whisper/ctranslate2 installed; /opt/data/scripts/podcast_weekly_audio.py can download/transcribe audio-only finalists and condense transcript chunks before scripting.
§
This environment has multiple connected Google Workspace accounts under /opt/data/google-accounts; when looking for docs/Drive items, check all relevant accounts instead of assuming the default token.
§
For review/gallery apps, DJ prefers mobile-first grid (3x3/3x4), green check/red X corner actions, center tap enlarge, server-side shared decisions/activity tracking, Google Sheet decision log with date/who, one item per crop, no floor-only, readable upright; verify live output.
§
Google Workspace scripts should use /opt/data/google-accounts/.venv/bin/python; the system shell has Python 3.13 and no node/npm.
§
User prefers onboarding/role docs to drive actual behavior with specific deliverables and cadence, not just polished wording or generic objectives.
§
Hermes CLI in this environment is run from /opt/hermes/.venv/bin/hermes, and the live config file is /opt/data/config.yaml with secrets in /opt/data/.env.