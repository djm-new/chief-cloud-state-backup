# Barbell Plate Loading

Use this reference when adding or changing a feature that translates a target total weight into plates per side on a standard barbell.

## Core assumptions

- Standard bar weight: **45 lb** unless the user explicitly chooses another bar.
- Plates are loaded symmetrically: the result is always **per side**.
- Output should prefer the **fewest plates** by taking the largest available plate first.
- Treat **2.5 lb** plates as valid when supported by the UI/data model.
- Show a clear explanation when the target cannot be loaded exactly.

## Recommended calculation model

1. Validate the input is a finite number.
2. Reject totals below the bar weight.
3. Reject totals that are not representable by the available plate increments.
4. Convert the remaining load into **per-side weight**.
5. Greedily allocate plates from largest to smallest.
6. Return both:
   - machine-readable counts per plate size
   - a human-readable summary string

## Example outputs

- **185 lb total** → 45 lb bar + **70 lb per side** → `1 × 45`, `1 × 25` each side
- **225 lb total** → 45 lb bar + **90 lb per side** → `2 × 45` each side
- **135 lb total** → 45 lb bar + **45 lb per side** → `1 × 45` each side

## UX notes

- Keep the result legible in two layers:
  - a compact plate stack / chip list
  - a text line like `45 lb bar + 70 lb per side = 185 lb total`
- When invalid, prefer a short fix-it message over a generic failure.
- If the calculator lives inside workouts, make it read like a utility, not a coach.

## Pitfalls

- Don’t assume every gym has the same plate set; keep the supported plate list configurable.
- Don’t hide the bar weight in the result — users care about the full total.
- Don’t round silently to a different total; if exact loading fails, say so.
- Don’t hardcode imperial-only assumptions into shared math if the app may later support metric.
