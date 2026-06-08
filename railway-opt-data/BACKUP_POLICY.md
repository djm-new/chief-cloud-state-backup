# Railway `/opt/data` backup policy

This folder is a selective snapshot from Railway Chief's persistent state and a few
critical app files used to run and explain the system.

It intentionally includes durable state that is useful for restoring or auditing Chief:

- cron job definitions
- sync/maintenance scripts
- curated memory markdown files
- installed/learned skills
- `SOUL.md` if present
- core Hermes config and routing notes
- podcast workflow configs and generated digest artifacts
- selected Hermes gateway source files that carry live behavior

It intentionally excludes secrets and raw private history:

- `.env`
- `auth.json`
- OAuth/token JSON files
- Google credential/token JSON files
- SQLite state databases
- `sessions/`
- `logs/`
- cache files
- platform pairing files

Do not replace this selective sync with a blind copy of all `/opt/data`.
