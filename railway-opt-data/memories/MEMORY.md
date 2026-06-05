Podcast prefs: labels not read aloud; distinct high-quality voices. Podcast intel: daily text + weekly 15–20m two-host audio; discover beyond subscriptions. Focus top money managers/CEOs/AI leaders/frontier thinkers; reference tastes include Dwarkesh, Invest Like the Best, Conversations w/ Tyler, Acquired/All-In/Marc&Ben. Skip news/politics/energy/climate/celebrity/VC fluff; select for actions/frameworks/toolkit.
§
Env: python3-pip and edge-tts are installed; /root/.local/bin/edge-tts supports selectable neural voices.
§
Health app design prefs: PWA+login, Today dashboard, fast LLM meal logging, custom lifting, 7-day calories/weight/sleep/workouts, Google Sheets backup.
§
User's production Hermes environment runs on Railway/Chief with a persistent /opt/data Railway volume and Railway env/secrets; do not treat local/session /opt/data as canonical for persistent integrations. The chief-cloud-state-backup repo selectively snapshots Railway /opt/data and intentionally excludes secrets, auth.json, OAuth/token JSON files, Google credential/token JSON files, sessions, logs, and caches.
§
Railway Chief Google Workspace is configured for three account slots on the persistent volume: personal -> /opt/data/google-accounts/personal (dj.mauch@gmail.com), 166-2nd -> /opt/data/google-accounts/166-2nd (dj@1662nd.com), flow -> /opt/data/google-accounts/flow (dj@flow.life). Use /opt/data/scripts/google-account {personal|166-2nd|flow} ... to access the corresponding Google APIs.
§
DJ's Google security policy: Google actions may read/search/summarize and may create/edit/delete Calendar events, Docs, Sheets, and Drive files when requested, but Hermes must never send Gmail/reply/forward or trigger external notifications (calendar guest invite emails, Drive share notifications, Docs/Sheets comment notifications). Outbound email/share/invite content is draft-only unless DJ explicitly changes the policy.
§
Google Doc “DM Running Daily ToM” is DJ’s daily rolling todo source of truth: latest block near top; sections Professional/MENA/Others/Personal; [n:id], **/*** priority; x/[x]→✅, >/[>]→↗️; new-day style date=Heading 2/body=Normal text; sync 5AM ET to Telegram alerts topic 5.