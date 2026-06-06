Podcast prefs: labels not read aloud; distinct high-quality voices. Podcast intel: daily text + weekly 15–20m two-host audio; discover beyond subscriptions. Focus top money managers/CEOs/AI leaders/frontier thinkers; reference tastes include Dwarkesh, Invest Like the Best, Conversations w/ Tyler, Acquired/All-In/Marc&Ben. Skip news/politics/energy/climate/celebrity/VC fluff; select for actions/frameworks/toolkit.
§
Env: python3-pip and edge-tts are installed; /root/.local/bin/edge-tts supports selectable neural voices.
§
Health app design prefs: PWA+login, Today dashboard, fast LLM meal logging, custom lifting, 7-day calories/weight/sleep/workouts, Google Sheets backup.
§
User's production Hermes environment runs on Railway/Chief with a persistent /opt/data Railway volume and Railway env/secrets; do not treat local/session /opt/data as canonical for persistent integrations. The chief-cloud-state-backup repo (djm-new/chief-cloud-state-backup) selectively snapshots scripts/skills/cron/memories — operational state only. thoughts-repo is intentionally excluded; it has its own private remote: djm-new/hermes-thoughts. GITHUB_TOKEN is a Railway env var (not in filesystem).
§
Railway Chief Google Workspace is configured for three account slots on the persistent volume: personal -> /opt/data/google-accounts/personal (dj.mauch@gmail.com), 166-2nd -> /opt/data/google-accounts/166-2nd (dj@1662nd.com), flow -> /opt/data/google-accounts/flow (dj@flow.life). Use /opt/data/scripts/google-account {personal|166-2nd|flow} ... to access the corresponding Google APIs.
§
DJ's Google policy: read/search/summarize OK; create/edit/delete Calendar/Docs/Sheets/Drive files when requested; never send Gmail/reply/forward or trigger external notifications. Outbound email/share/invite content is draft-only unless DJ changes policy. ToM: fix thoughts-system Google Calendar integration later, not now.
§
Telegram “Chief Group - Hermes” chat -1003956828149 topics: 1 General/home, 3 Archive/Old Chief, 4 Briefings, 5 Alerts, 6 Daily Brain Dump, 7 Coding 1, 8 Coding 2. Briefings cron delivers to 4; Alerts/health/cron success to 5.