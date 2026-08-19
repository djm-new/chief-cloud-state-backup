# Cloud-state GitHub backup sync pattern

Use this for cron jobs that snapshot Chief/Hermes durable state into a separate GitHub repo.

## What the sync must do

- generate redacted session exports before snapshotting when conversational history is part of the backup
- copy only allowlisted durable state
- keep secrets out of the snapshot
- use explicit GitHub auth from `GITHUB_TOKEN` (or a similarly named approved token) in the clone/push URL
- fail loudly on clone/push errors so cron output explains the cause

## Pitfalls

- Do not bury auth failures behind `set -e` and a silent redirect; print a clear reason and exit nonzero.
- Do not hardcode placeholder URLs like `https://x-access-token:***@...` in the live script. Build the remote URL from the live `GITHUB_TOKEN` (`https://x-access-token:${GITHUB_TOKEN}@github.com/...`) and keep the secret out of logs.
- Do not treat a missing token as success; tell DJ the backup did not run.
- Keep the snapshot selective: configs, scripts, skills, routing notes, durable artifacts, and redacted exports; exclude `.env`, auth JSON, SQLite DBs, raw sessions, logs, and raw media/audio/video artifacts.
- If GitHub rejects a push with `GH001: Large files detected`, fix both the snapshot filter and local git history. Reset the backup checkout to `origin/<branch>` before rebuilding so a previously failed local commit containing large blobs does not keep poisoning future pushes.
- If GitHub reports `Invalid username or token`, validate the exact token with the GitHub `/user` API before changing code. A `GITHUB_TOKEN` can be present but expired/revoked; script changes will not fix a 401 credential.

## Verification

- `bash -n` the wrapper
- run the redaction export step on its own before the snapshot
- confirm `git status` is clean or only contains the intended snapshot changes
- confirm clone/push failure messages mention the missing token or repo access explicitly
