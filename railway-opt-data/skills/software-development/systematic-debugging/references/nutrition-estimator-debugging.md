# Debugging Nutrition/Food Estimation Engines

Use when a user reports food macros/calories are obviously wrong, especially for branded or restaurant items.

## Investigation pattern

1. **Trace the estimation path before changing prompts.** Identify UI payload → API route → estimator function → model/provider/fallback → persisted fields/source metadata.
2. **Check production configuration.** Confirm whether the intended model key/model env vars are actually present. If absent, inspect fallback behavior; bad fallbacks can be the real engine even when the database says `estimationSource: llm`.
3. **Reproduce with the exact user phrase.** Use the same endpoint the UI uses, with a temporary meal if necessary, then delete it immediately after verification.
4. **Classify the food input:**
   - Quantified simple ingredients (e.g. `4 oz almond milk, 25g whey isolate`) → parse quantities conservatively in fallback; never add a generic meal baseline.
   - Branded/restaurant item (e.g. `Sweetgreen Crispy Rice Bowl`) → prefer official published nutrition over model estimates.
   - Free-form mixed meal → cheap structured-output model is acceptable, with visible editable fields.
5. **Add regression tests** for the exact incorrect case and for the source-priority behavior.

## Durable fixes

- **Source priority should be:** official branded-food database/override → configured cheap model → conservative fallback.
- **Fallbacks should be low-confidence and conservative.** Avoid broad rules like `default 450 kcal + protein keyword bonus`; they create plausible-looking but wrong numbers.
- **Model prompt should forbid invented baselines.** Tell the model to use stated quantities exactly, not infer an entire meal around a keyword.
- **Persist source metadata** such as `official_branded_override`, model name, or `conservative_fallback` so wrong estimates can be audited.

## Verification recipe

- For API-backed apps, log in programmatically, create a temporary meal using `/api/meals/estimate-and-log`, inspect returned macros, then call the delete endpoint.
- Verify both:
  - the new code/config deployed, and
  - the exact production endpoint returns expected macros.

## Example official override

For Sweetgreen Crispy Rice Bowl, Sweetgreen's menu has shown approximately: `640 kcal / 28P / 61C / 30F`. If an LLM returns materially different protein/fat, prefer the official menu value.