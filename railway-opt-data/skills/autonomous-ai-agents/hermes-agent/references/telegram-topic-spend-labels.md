# Telegram topic spend labels

Use this when reporting Hermes spend for Telegram. The goal is to show *human topic names*, not raw thread ids or the generic `topic N` placeholders.

## Mapping sources

Prefer these in order:
1. `telegram_topic_model_overrides` and topic routing config in `/opt/data/config.yaml` when it already names the topic.
2. `channel_directory.json` when it contains `Chief Group - Hermes / topic N` entries.
3. Gateway logs (`gateway.log`, `agent.log`) to recover `session_id -> thread_id` when spend rows are backfilled and the ledger row is missing topic metadata.

## Human topic names for Chief Group

For chat `-1003956828149` use these names:
- `1` → `General/home`
- `3` → `Archive/Old Chief`
- `4` → `Briefings`
- `5` → `Alerts`
- `6` → `Daily Brain Dump`
- `7` → `Coding`
- `8` → `General (ad-hoc/conversational)`

## Reporting rule

If the ledger row has empty `thread_id`, `chat_name`, or `channel_label`, recover the thread from logs before rendering the briefing. If you still cannot recover it, prefer `unlabeled` over inventing a label.

## Output shape

For Telegram-heavy spend reports, include a dedicated section:
- By Telegram topic — last 24h
- By Telegram topic — last 7d

Then keep the generic `By topic/channel` section for the full multi-platform view.
