# Telegram thoughts-routing pitfall

This session exposed a useful routing lesson for Hermes Telegram setups:

- A topic configured as the `thoughts` capture channel can intercept ordinary messages before the normal LLM conversation.
- That is fine for a dedicated ingest thread, but it is wrong for an interactive Daily Brain Dump topic if DJ expects normal replies there.
- The safe pattern is to split the duties:
  - one Telegram topic for **interactive chat**
  - one separate topic or channel for **capture-only ingestion**

## Two valid behaviors

1. **Capture-only thread**
   - capture the message
   - keep success silent or minimally acknowledged
   - do not forward to the normal conversation loop

2. **Interactive capture thread**
   - capture the message first
   - reply with a lightweight `✓` ack
   - let the message fall through so the normal Hermes LLM still answers
   - reserve direct-thoughts retrieval queries for the repo/search path

## What to check

- `thoughts.enabled` in `/opt/data/config.yaml`
- `thoughts.telegram.chat_id` and `thoughts.telegram.thread_id`
- whether the topic name in Telegram matches the capture semantics
- whether the integration returns a sentinel/ack that the gateway interprets as “reply and continue” rather than “consume and stop”

## Rule of thumb

If DJ says “this topic should talk back,” do not keep capture-only interception on that same thread. Make capture non-blocking instead of disabling thoughts globally.
