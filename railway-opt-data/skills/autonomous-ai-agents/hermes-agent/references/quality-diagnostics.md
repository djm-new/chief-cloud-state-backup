# Hermes quality-diagnostics checklist

Use when Hermes feels meaningfully worse than the OpenAI browser or another direct chat surface on the same nominal model.

## First checks
- Confirm the live model config, not just the UI label:
  - `hermes config`
  - `hermes config path`
- Inspect whether `model.default` is truly the strongest intended model.
- Check whether `display.personality` is adding stylistic distortion.
- Check `compression.enabled`, `compression.threshold`, and whether the session is being summarized too aggressively.
- Check helper routing for hidden degraders: `auxiliary.compression`, `auxiliary.title_generation`, `auxiliary.session_search`, and any other model used in the background.

## Diagnostic questions
- Is the answer worse on every task class, or only on long-context / writing / reasoning tasks?
- Did the session get compressed or reset before the bad response?
- Are you comparing the browser to Hermes with the exact same prompt, or with a richer browser conversation?
- Is the model path actually using the intended provider, or silently falling back?

## Immediate fixes to try
- Set the main chat model to the strongest intended model.
- Switch `display.personality` to a neutral/technical style.
- Temporarily disable compression if you need a clean A/B test.
- Re-run in a fresh session after config changes.

## Verification
- Compare the same prompt in a new Hermes session and the browser.
- If Hermes still loses, inspect gateway logs for fallback or compression events around the turn.
- Treat wrapper/config mismatch as a first-class suspect before blaming the base model.