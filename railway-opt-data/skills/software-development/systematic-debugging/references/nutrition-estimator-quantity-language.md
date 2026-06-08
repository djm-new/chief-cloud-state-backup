# Nutrition estimator: quantity-language pitfall

Use when quantified supplement descriptions are estimated incorrectly even though the brand is recognized.

## Symptom

Examples:
- `one serving Isopure...` gets treated as if the powder is absent.
- `1 scoop`, `2 servings`, or `half serving` are not captured by the fallback parser.
- The estimate looks like it only counted side ingredients (e.g. almond milk) and ignored the branded protein powder.

## Root cause pattern

The fallback path only matched gram-based quantities, e.g. `25g whey`. It did not parse natural serving words such as:
- serving / servings
- scoop / scoops
- one / two / three ...

## Fix pattern

1. Add a quantity parser for serving-language, not just grams.
2. Map common words to numbers conservatively (`one` → `1`, etc.).
3. Keep the gram path intact; serving language and gram language should both resolve to the same branded supplement branch.
4. Add a regression test with a mixed meal string that contains both a side ingredient and a serving-based supplement.

## Verification

For a meal like `4 oz almond milk, one serving Isopure Zero Carb 100% Pure Whey Isolate`, the fallback should produce a result close to:
- ~115 kcal
- ~26g protein
- low carbs/fat

and the metadata should show the conservative fallback path rather than a silent default baseline.