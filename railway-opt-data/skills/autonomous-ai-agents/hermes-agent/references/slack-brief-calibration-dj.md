# DJ Slack brief calibration notes

Use these notes when building or tuning Flow Slack business briefings for DJ.

## Core standard

A brief item is only useful if DJ can understand it without clicking Slack. Before including any item, verify the collected context can answer:

1. What happened?
2. Who said what? Include names when quoting or paraphrasing.
3. Why does this matter to DJ / Flow?
4. Does DJ need to act? If yes, what action? If no, label it as awareness only.
5. What is the source channel? Source lines must include `#channel-name — link`.

If the answer requires more Slack context, fetch surrounding history/thread context. If context is still insufficient, omit the item instead of writing a caveat.

## Common failure modes to suppress

- Single-message snippets such as “Can you advocate for me?” without preceding context.
- Vague updates like “Updated here” without what was updated.
- “Someone needs approval” when the approver and object of approval are unclear.
- Keyword-only hits: MENA, finance, legal, board, cash, approval, degraded, etc. are not sufficient by themselves.
- Low-level ops snippets: cleaning, housekeeping, move-ins, cashier checks, routine facilities, unless repeated/severe or tied to executive business impact.
- Small dollar finance/admin requests unless material, policy-relevant, or explicitly DJ-owned.
- Technical alerts unless translated into customer/production/business impact.
- MENA chatter unless it involves a real blocker, decision, meaningful fix, launch/revenue/ops impact, or escalation.

## Positive example characteristics

The first calibration item DJ marked “VERY GOOD” was the June launch / occupancy workstream because it had:

- concrete initiatives,
- dates/deadlines,
- named owners or tagged teams,
- clear revenue/launch/occupancy relevance,
- source channel and link.

Use this as the bar for future brief items.

## Collection requirement

The collector should enrich high-signal candidates with surrounding context before synthesis:

- For threads: fetch `conversations.replies` for the thread root.
- For standalone messages/DMs: fetch recent `conversations.history` around the target message.
- Resolve user IDs to display names when possible.
- Preserve raw message link and channel name.

The briefing model should receive enough context to make a judgment, not a raw firehose.

## Output style

Prefer concise, legible sections over long prose. For each item:

```markdown
### Plain-English headline

What happened: ...
Why it matters: ...
DJ action: ... / Awareness only.
Source: #channel-name — https://...
```

Keep the brief short. It is better to send 2 useful items than 12 speculative ones.
