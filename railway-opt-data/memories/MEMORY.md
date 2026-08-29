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
This environment has multiple connected Google Workspace accounts under /opt/data/google-accounts; when looking for docs/Drive items, check all relevant accounts instead of assuming the default token.
§
For review/gallery apps, DJ prefers mobile-first grid (3x3/3x4), green check/red X corner actions, center tap enlarge, server-side shared decisions/activity tracking, Google Sheet decision log with date/who, one item per crop, no floor-only, readable upright; verify live output.
§
Google Workspace scripts should use /opt/data/google-accounts/.venv/bin/python; the system shell has Python 3.13 and no node/npm.
§
User prefers onboarding/role docs to drive actual behavior with specific deliverables and cadence, not just polished wording or generic objectives.
§
Hermes CLI in this environment is run from /opt/hermes/.venv/bin/hermes, and the live config file is /opt/data/config.yaml with secrets in /opt/data/.env.
§
Podcast weekly pipeline cost/disk hygiene: keep local STT lightweight at /opt/data/venvs/podcast-stt with faster-whisper/ctranslate2; do not casually recreate heavyweight /opt/data/venvs/podcast-tts GPU/Torch stacks on Railway.
§
DJ wants Granola meeting-note exports saved to H:\My Drive\Meeting_Notes on his Windows machine.
§
Chief Group - Hermes Telegram topic map includes Podcast Digest = message_thread_id 7703 in chat -1003956828149.
§
Telegram Chief topics include General, Archive, Briefings, Alerts, Brain Dump, Coding, General/ad-hoc, and Podcast Digest/Podcast Updates. Podcast digest delivery target is the dedicated podcast topic, not Briefings.
§
DJ's 166-2nd Google Drive account has canonical AI/agentic professional work folder named beast at Drive folder ID 1d1lKeWF9OObyRHc63vZhazCosAg3p2MI; use account profile /opt/data/google-accounts/166-2nd for access.
§
Granola Windows automation context: DJ uses free Granola on Windows; local files are encrypted (.enc), granola-cli 0.2.0 expects plaintext supabase.json and failed. Target workflow is open meeting → hotkey → keyboard/UIAutomation export, avoiding coordinate clicks; copied notes include title/date; naming convention is "Meeting Title YYYY_MM_DD.txt".
§
Meeting prep briefs for DJ should deliver to Telegram Chief Group - Hermes topic Meeting Briefs: target telegram:-1003956828149:8289.
§
Chief Group - Hermes Telegram topic map includes Meeting Briefs = message_thread_id 8289 in chat -1003956828149. Pre-meeting briefing generator should deliver to telegram:-1003956828149:8289.
§
Ben Bot project convention: repo is djm-new/ben-bot under /opt/data/projects/ben-bot; user wants the product named “Ben Bot” everywhere and responses to feel like a direct first-person conversation with Ben while retaining grounding/disclaimer guardrails.
§
Ben Bot production app is https://ben-bot-production.up.railway.app/chat/ui; repo is /opt/data/projects/ben-bot. Its product interaction eval script takes the chat URL as the first positional argument, e.g. `/opt/hermes/.venv/bin/python scripts/run_product_interaction_eval.py https://ben-bot-production.up.railway.app/chat`.