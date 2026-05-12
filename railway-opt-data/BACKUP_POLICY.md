# Railway `/opt/data` backup policy

This folder is a selective snapshot from Railway Chief's persistent `/opt/data` volume.

It intentionally includes runtime state that is useful for restoring Chief:

- cron job definitions
- sync/maintenance scripts
- curated memory markdown files
- installed/learned skills
- `SOUL.md` if present

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
