# Model Routing Taxonomy

Purpose-first routing for DJ’s workflows.

## Global defaults

- **Default lightweight OpenAI model:** `gpt-5.4-mini`
- **Highest-end OpenAI model:** `gpt-5.5`
- **Best open-source thinking model:** DeepSeek V4 Pro
- **Open-source alternate/generalist:** Qwen
- **Anthropic coding fallback:** `sonnet`
- **Anthropic polish / highest-end:** `opus`
- **Do not use `haiku` in the default routing taxonomy; prefer DeepSeek V4 Pro instead for lightweight/open-source work.**

## Purpose map

### Daily brain dump / thought capture
- Reading random thoughts: `gpt-5.4-mini`
- Categorizing random thoughts: `gpt-5.4-mini`
- Filing markdown docs: `gpt-5.4-mini`
- Cleaning notes / light editing: `gpt-5.4-mini`
- Weekly synthesis across many notes: DeepSeek V4 Pro first, `sonnet` if needed
- Structuring the overall brain from many notes: `gpt-5.5` when quality matters most; otherwise DeepSeek V4 Pro

### Daily business briefing
- Raw capture / message reading: `gpt-5.4-mini` or DeepSeek V4 Pro
- Categorizing items / tagging actions: `gpt-5.4-mini`
- Condensing into a clean briefing draft: DeepSeek V4 Pro or `sonnet`
- Final executive-style synthesis: `gpt-5.5` for best output; `opus` for maximum polish
- Action list consolidation: lightweight model first; escalate only if judgment is needed

### Coding projects
- Default: `gpt-5.5`
- Fallback: Anthropic `sonnet`
- Trivial cleanup / formatting / quick inspection: `gpt-5.4-mini` is acceptable

### Open-source reasoning work
- Primary thinking model: DeepSeek V4 Pro
- Secondary generalist: Qwen
- Prefer DeepSeek for deeper reasoning, synthesis, and coding-adjacent thinking
- Prefer Qwen when a different style or broad general-purpose open-source model is desirable

### High-polish writing / editorial synthesis
- Best polish: `opus`
- Strong but slightly cheaper: `gpt-5.5`

## Routing principles

- Route by **purpose**, not by provider.
- Use the cheapest model that is still good enough for the task.
- Escalate only when the task requires deeper synthesis, polish, or coding reliability.
- Keep a living register of activity → model mappings and revise it when preferences change.
- If a model becomes unavailable or underperforms, update the taxonomy rather than silently drifting.
