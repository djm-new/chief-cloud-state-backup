# Redacted session export layer

Use this when the goal is to preserve conversational history in GitHub without copying raw `sessions/` JSON files.

## Purpose
- Export session transcripts into a cloud-backed, LLM-readable markdown corpus.
- Keep the raw session store local, while publishing a redacted derivative into the GitHub backup.

## Layout
- Source: `/opt/data/sessions/`
- Export target: `/opt/data/thoughts-repo/exports/sessions-redacted/`
- Index: `/opt/data/thoughts-repo/exports/sessions-redacted/index.md`

## Exporter
- Script: `/opt/data/scripts/export_redacted_sessions.py`
- Run it before the cloud-state snapshot so the repo always contains the newest redacted history.

## Redaction rules
- Remove obvious secrets/tokens/keys.
- Keep message order, timestamps, roles, tool-call structure, and topic context.
- Omit encrypted/internal reasoning items.
- Bound oversized tool outputs so the archive stays readable.

## Verification
- Confirm the exported directory contains markdown files for recent sessions.
- Check the index for session IDs, models, platforms, topics, and paths.
- Push the backup repo after the export step succeeds.
