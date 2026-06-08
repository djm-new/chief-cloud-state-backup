# Hermes Model Routing Register

Living draft for what model we use for which work. Organize by *usage / purpose*, not by provider.

## How to use this register

- Pick the row that matches the task intent.
- Use the listed primary model first.
- If that model is unavailable, use the fallback.
- If a task changes shape, update this file so the routing stays explicit.

## Daily brain dump / thought capture

Use cheap models for ingestion, tagging, and filing. Escalate only when we need real synthesis.

- **Reading random thoughts:** `gpt-5.4-mini`
- **Categorizing random thoughts:** `gpt-5.4-mini`
- **Filing markdown docs:** `gpt-5.4-mini`
- **Cleaning up notes / lightweight editing:** `gpt-5.4-mini`
- **Weekly synthesis across many notes:** DeepSeek first, `sonnet` if needed
- **Structuring the overall brain from many notes:** `gpt-5.5` when quality matters most; otherwise DeepSeek for cost-efficient thinking

## Daily business briefing

Use a staged pipeline: cheap extraction first, stronger synthesis later.

- **Raw capture / message reading:** `gpt-5.4-mini` or DeepSeek V4 Pro
- **Categorizing items / tagging actions:** `gpt-5.4-mini`
- **Condensing into a clean briefing draft:** DeepSeek or `sonnet`
- **Final executive-style synthesis:** `gpt-5.5` for best output; `opus` for maximum polish
- **Action list consolidation:** lightweight model first, then stronger reasoning only if the action list needs judgment

## Coding projects

Use the strongest OpenAI model by default, with a clean Anthropic fallback.

- **Default:** `gpt-5.5`
- **Fallback:** Anthropic `sonnet`
- **Trivial cleanup / formatting / quick inspection:** `gpt-5.4-mini` is acceptable

## Open-source reasoning work

Use these when we explicitly want open-source or open-weight models.

- **Primary open-source thinking model:** DeepSeek
- **Secondary open-source generalist:** Qwen
- **When to prefer DeepSeek:** deeper reasoning, synthesis, coding-adjacent thinking
- **When to prefer Qwen:** broad general-purpose work, alternate style, or when DeepSeek is not the best fit

## High-polish writing / editorial synthesis

Use the best model when wording quality matters more than cost.

- **Best polish:** `opus`
- **Strong but slightly cheaper:** `gpt-5.5`
- **Use case examples:** final briefing polish, executive summary wording, delicate synthesis

## Cheap extraction / transform tasks

Use low-cost models for tasks that mostly extract, compress, or transform without deep reasoning.

- **Best cheap OpenAI choice:** `gpt-5.4-mini`
- **Best cheap DeepSeek choice:** DeepSeek V4 Pro
- **Use case examples:** label extraction, sorting, formatting, short summaries, file filing

## Decision rules

If the work is mostly:

- **capture / sorting / filing** -> `gpt-5.4-mini` or DeepSeek V4 Pro
- **reasoning / synthesis / cross-note connection** -> DeepSeek or `gpt-5.5`
- **coding** -> `gpt-5.5`, fallback `sonnet`
- **polish / final wording** -> `opus` or `gpt-5.5`

## Notes

- This is a living register, not a fixed law.
- When a task changes, update the register first, then use the new default going forward.
- If a model is unavailable or underperforming, revise the register rather than silently drifting.
