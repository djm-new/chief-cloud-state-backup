# Meeting Prep Memos — DJ Standard

Use this when preparing DJ for an upcoming meeting from calendar + prior notes + Slack/docs context.

## Core lesson

Do not generate a polished memo from weak context. A prep memo is useful only if it makes DJ sharper in the room. Never infer the agenda from a stale/weak match just because a name appears in old notes.

## Required sequence

1. **Identify the actual meeting**
   - exact calendar event, date/time in ET, duration
   - attendees by email, not just display names
   - organizer and description/agenda links
   - whether it is recurring (`recurringEventId`) or a one-off
   - same-day meetings with the same people so background is not repeated unnecessarily

2. **If recurring, start with the prior occurrence**
   - find the prior calendar instance and matching prior meeting note
   - extract to-dos, follow-ups, unresolved decisions, and important highlights
   - verify whether those were actioned using later meeting notes, Slack, or other live context

3. **Resolve participant identity**
   - internal vs external
   - role/title/team/manager/start date if internal
   - recent org/roster/headcount docs when relevant
   - prior direct meetings with DJ, if any
   - recent Slack/email/meeting-note mentions tied to the topic

4. **Resolve the meeting topic**
   - use title, description, agenda link, attendees, adjacent same-day meetings, and related docs/notes
   - search topic-specific context, not generic person history
   - if agenda is gated or unavailable, say so and avoid guessing

5. **Draft only after context is grounded**
   - prioritize what changes DJ's behavior in this meeting
   - if evidence is weak, provide a concise uncertainty-aware card with a sharp opening question
   - never present stale context as the likely agenda

## Preferred output shape

```markdown
## [time ET] Meeting name

**Bottom line:** [what this meeting likely is / what DJ should do, with uncertainty if needed]

**Know walking in**
- [most relevant fact about the meeting/person/topic]
- [prior follow-up or recent context]
- [risk, gap, or missing context]

**DJ should**
- [specific action/question/posture]
- [optional second action]

**Ask**
“[single sharp question]”
```

## Pitfalls

- Do not overfit to a name match in an old note.
- Do not treat a stale note as the meeting agenda.
- Do not give generic biography repeatedly if DJ has multiple meetings with the same person that day.
- Do not use a consumer-proxy review loop that only reviews form; the review must inspect whether actual context was used correctly.
- Do not make DJ ask for obvious enrichment steps such as “who is this person?” or “has this meeting happened before?”

## Example correction from session

For `DJ x Sami x Zaid`, the wrong move was to infer an external Florentina/Zaid real-estate agenda from an old MENA note. The correct move was to resolve the attendee email `z.shreim@flow.life`, find current roster/Slack context, and identify Zaid as a recent Flow MENA B2B Sales Manager, likely tied to Granada/B2B revenue and role clarity.