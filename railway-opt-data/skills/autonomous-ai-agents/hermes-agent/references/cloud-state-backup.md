# Cloud-state backup pattern

DJ wants the Chief cloud-state GitHub backup to preserve essentially all durable work and context so other LLMs can inspect it later in the cloud.

## Include
- `config.yaml` and other durable runtime config
- routing notes / model register files
- `scripts/`
- `skills/`
- `memories/`
- `cron/jobs.json`
- `health/`
- `SOUL.md`
- selected Hermes gateway source files when they carry live behavior
- podcast workflow configs and generated digest artifacts when they are durable reference material
- redacted session exports when the goal is to preserve conversational history without raw secret-bearing session files

## Exclude
- secrets and auth material
- OAuth/token JSON
- `.env`
- SQLite state databases
- `sessions/`
- `logs/`
- caches and build artifacts
- raw session transcripts; export them into a redacted corpus instead

## Implementation notes
- Prefer a selective snapshot, not a blind copy of all data.
- Keep the backup repo human/auditable and safe for other LLMs to read.
- If the backup policy changes, update the policy file in the repo and the sync script together.
