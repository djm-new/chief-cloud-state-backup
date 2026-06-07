# Purpose-first model routing

Use this as the living model-selection map for DJ's work. Keep it organized by *what the task is*, not by provider family.

## Current defaults

- **Cheap/light OpenAI:** `gpt-5.4-mini`
- **Strongest OpenAI:** `gpt-5.5`
- **Open-source lightweight/default alt:** DeepSeek V4 Pro
- **Open-source secondary:** Qwen
- **High-polish editorial:** `opus`
- **Coding default:** `gpt-5.5`
- **Coding fallback:** Anthropic `sonnet`

## Preferred usage buckets

### Daily brain dump / thought capture
- Reading random thoughts → `gpt-5.4-mini`
- Categorizing random thoughts → `gpt-5.4-mini`
- Filing markdown docs → `gpt-5.4-mini`
- Weekly synthesis / cross-note structure → DeepSeek V4 Pro
- High-level "brain" structuring across many notes → `gpt-5.5` if quality matters most

### Daily business briefing
- Raw capture / message reading → `gpt-5.4-mini` or DeepSeek V4 Pro
- Categorizing items / tagging actions → `gpt-5.4-mini`
- Condensing into a briefing draft → DeepSeek V4 Pro or `sonnet`
- Final executive synthesis → `gpt-5.5`
- Polished wording / final pass → `opus`

### Coding projects
- Default → `gpt-5.5`
- Fallback → Anthropic `sonnet`
- Trivial cleanup only → `gpt-5.4-mini`

### Open-source reasoning work
- Primary thinking model → DeepSeek V4 Pro
- Alternate/generalist → Qwen
- Use DeepSeek when the task needs deeper reasoning or synthesis
- Use Qwen when you want a different style or broader general-purpose behavior

## Routing rules

- Prefer the cheapest model that is still clearly good enough.
- Escalate when synthesis quality matters, the output is externally visible, or the problem is genuinely hard.
- If the user says they want "best thinking," move to the strongest model in the bucket.
- If the user says they want "cheap mode" or explicitly wants to avoid token burn, switch immediately to the lightweight choice.
- Do not use Haiku in the default routing taxonomy; use DeepSeek V4 Pro instead for lightweight/open-source work.

## Maintenance rule

When a workflow changes, update the routing register immediately instead of letting the live behavior drift silently.