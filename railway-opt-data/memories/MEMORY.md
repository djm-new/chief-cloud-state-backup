Podcast prefs: labels not read aloud; distinct high-quality voices. Daily text + weekly 15–20m two-host audio. Focus top money managers/CEOs/AI leaders/frontier thinkers; skip news/politics/celebrity/VC fluff.
§
Env: python3-pip and edge-tts are installed; /root/.local/bin/edge-tts supports selectable neural voices.
§
Health app design prefs: PWA+login, Today dashboard, fast LLM meal logging, custom lifting, 7-day calories/weight/sleep/workouts, Google Sheets backup.
§
Production Hermes uses a persistent /opt/data volume on Railway/Chief; chief-cloud-state-backup is runtime-state backup, and thoughts-repo has its own private remote.
§
Railway Chief Google Workspace uses three persistent account slots (personal, 166-2nd, flow); access them via /opt/data/scripts/google-account {personal|166-2nd|flow} ...
§
DJ's Google policy: read/search/summarize OK; create/edit/delete Calendar/Docs/Sheets/Drive files when requested; never send Gmail/reply/forward or trigger external notifications. Outbound email/share/invite content is draft-only unless DJ changes policy. ToM: fix thoughts-system Google Calendar integration later, not now.
§
Telegram Chief topics: General (1), Archive (3), Briefings (4), Alerts (5), Brain Dump (6), Coding (7), General/ad-hoc (8). Models: default gpt-5.4-mini; topic 7 (Coding) gpt-5.5; topic 8 varies by session request. Fallback OpenRouter DeepSeek V4 Pro → Anthropic. Topic overrides in config.yaml persist across /new — must be manually removed to revert.
§
User prefers GitHub as the source of truth for code; Railway is runtime/deployment only, and Railway console containers should not be assumed to contain the editable repository checkout.
§
HealthOS Railway deploys require the GitHub repo to be linked in Railway Settings before push-to-deploy works.
§
Persistent automation auth is stored in /opt/data/.env, and GitHub git authentication is persisted via /opt/data/.git-credentials with git credential.helper pointing there.
§
Persistent automation auth lives in /opt/data/.env and /opt/data/.git-credentials and is intended for all projects, not just HealthOS.