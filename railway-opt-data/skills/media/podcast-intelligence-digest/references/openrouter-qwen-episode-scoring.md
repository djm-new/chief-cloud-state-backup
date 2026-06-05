# OpenRouter Qwen Episode Scoring Notes

Use when DJ wants the podcast filter evaluated on an open-weight model rather than Codex/Anthropic.

## Model/backend

- Preferred calibration model used in this session: `qwen/qwen3-235b-a22b` via OpenRouter.
- For deterministic/compact scoring, ask for a short JSON object per episode and keep output small.
- Qwen can sometimes enter thinking/garbled output modes when `response_format: {type: json_object}` is used against some endpoints. If JSON-mode output is strange, remove `response_format` and prefix the user message with `/no_think` plus `Return only JSON`.
- The `qwen/qwen3-235b-a22b-07-25` endpoint behaved cleanly in a smoke test and maps to the instruct/no-thinking variant; `qwen/qwen3-235b-a22b` may route to an older 04-28 endpoint but worked with `/no_think`.

## Railway/Hermes env quirk

When a Railway variable is newly added, the live gateway process may have it while terminal subprocesses inherit a stale snapshot. Before telling DJ the key is missing, check the gateway process env:

```python
from pathlib import Path
key = None
for item in Path('/proc/1/environ').read_bytes().split(b'\0'):
    if item.startswith(b'OPENROUTER_API_KEY='):
        key = item.split(b'=', 1)[1].decode()
        break
print(bool(key))
```

Do not print the key. Use this only to bridge the stale subprocess environment during the current run.

## Compact episode scoring schema

For wide daily calibration, score every episode with exactly:

```json
{
  "score": 0,
  "tier": "skip | scan | digest | listen",
  "reason": "one short sentence",
  "confidence": "low | medium | high"
}
```

Guidance:

- Score episodes, not shows. Source shows are priors only.
- Daily text digest should cast a wider net; weekly audio digest should be much more selective.
- Keep `reason` under ~24 words to control cost and make calibration legible.
- Run a cheap smoke test before scoring the full batch.

## Cost observed

A 100-episode metadata scoring pass with Qwen 235B used about:

- input: 31,919 tokens
- output: 7,605 tokens
- total: 39,524 tokens
- estimated listed-rate cost: about $0.03

This is cheap enough for iterative calibration, but output verbosity remains the main cost lever.
