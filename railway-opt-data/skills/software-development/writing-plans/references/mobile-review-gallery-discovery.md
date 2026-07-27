# Mobile Review/Gallery App Discovery

Use this when a user wants a phone-first app for reviewing many images/items one by one, especially when each item can be marked with a simple decision.

## Core questions to lock quickly

- What is the unit being reviewed? (photo, book, crop, product, document)
- What are the decisions? (keep/discard, approve/reject, etc.)
- Should the review UI be grid, list, or carousel?
- What is the primary touch pattern on mobile?
- How should duplicates be handled?
- What is the export/output artifact?
- Should uncertain items stay blank, or receive an auto-suggestion?
- Is the app private, public, or secret-link?

## Default mobile UX assumptions

- Use a responsive gallery that fits 2–4 columns on phone, not a desktop-centric table.
- Put the primary decision actions directly on the tile/card, ideally in corners.
- Make the center of the card open an enlarged preview.
- Keep tap targets large enough for thumbs.
- Show count badges when a detected item appears multiple times.
- Let one decision apply to all duplicate copies unless the user explicitly wants per-copy control.

## Output shape

Prefer a simple final artifact:

- keep list
- discard list
- optional undecided list
- export as JSON plus a plain-text summary for sharing

## Useful phrasing in discovery

- “If the app is uncertain, should it stay blank or give a category suggestion?”
- “When duplicates appear, should one tap mark all copies or just one?”
- “Should the gallery feel like a photos app with corner actions?”

## Pitfalls

- Don’t overbuild search, accounts, or collaboration before the review flow works.
- Don’t hide the key decision action in a menu if the app is meant for fast thumb use.
- Don’t assume perfect detection; plan a manual review/override step.
- For photographed physical items, do not claim detection/cropping quality from code alone; inspect actual crops/contact sheets and verify the live user route. See `photographed-item-crop-and-review-qa.md`.
