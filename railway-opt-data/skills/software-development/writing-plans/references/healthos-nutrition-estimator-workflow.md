# HealthOS Nutrition Estimator Workflow

## Trigger

Use this when planning, building, or debugging HealthOS meal logging / macro estimation.

## Core user correction

DJ's old Replit/manual workflow worked because he entered each meal into a capable LLM like ChatGPT and the LLM returned macros, including searching/using official data for restaurant/branded foods. HealthOS must not degrade accuracy versus that workflow by using a cheap no-search guesser.

The correct product behavior is not “hard-code a known restaurant item after a bad estimate.” The correct behavior is to preserve the workflow:

1. User enters short meal text.
2. If it is branded, packaged, or restaurant food, the estimator uses an LLM with web search.
3. The estimator prioritizes official brand/restaurant/menu/nutrition sources over third-party calorie mirrors.
4. It returns macros plus source metadata.
5. If official lookup fails, do not silently downgrade to a confident cheap guess. Return conservative/low-confidence editable values or make uncertainty visible.
6. Simple non-branded foods can use a cheap no-search model with strict quantity instructions.

## Recommended architecture

- Route meal creation through a dedicated estimator module, not inline API-route logic.
- Use a brand/restaurant detector for common terms: Sweetgreen, Cava, Chipotle, Starbucks, packaged protein brands, etc.
- For detected branded/restaurant meals:
  - Use OpenAI Responses API with hosted web search, e.g. `tools: [{ type: 'web_search' }]`.
  - Use a search-capable model such as `gpt-4.1-mini` for this path.
  - Prompt official-source-first: official brand website/menu/nutrition calculator beats third-party mirrors.
  - Require output JSON: `calories`, `proteinG`, `carbsG`, `fatG`, `sourceUrl`, `sourceName`, `sourceType`, `confidence`.
  - Validate source domain against known official domains when a brand is recognized.
  - Reject known-brand results that cite third-party mirrors when official source is expected.
- For simple non-branded meals:
  - Use cheap no-search model such as `gpt-4.1-nano`.
  - Prompt: use stated quantities exactly; do not invent extra ingredients or default meal baselines; return strict JSON.
- Fallback:
  - Conservative quantity parser for obvious quantities (e.g. almond milk ounces, whey grams).
  - No fake high baseline like “450 kcal meal + protein add-on.”

## Implementation pitfalls

- A generic LLM without search may hallucinate restaurant macros.
- A search-enabled LLM may still pick third-party mirrors unless the prompt explicitly prefers official domains.
- Even with strict prompts, output shape can be odd, e.g. `{ "640": { ...macros } }`; normalize a single nested object before schema parsing.
- Do not hard-code restaurant overrides as the primary solution. They are acceptable only as temporary guardrails or fixtures; the class-level fix is search + official-source validation.
- Do not silently fall back from failed official branded lookup to a cheap no-search estimate. That recreates the accuracy regression DJ objected to.
- Persist `llmRawResponse` / source metadata where possible so future debugging can tell whether a value came from web search, cheap model, or fallback.

## Regression examples

- `4 oz almond milk, 25g of Isopure Zero Carb 100% Pure Whey Isolate`
  - Should be around 100–130 kcal, high protein, near-zero carbs/fat.
  - Must not become 670 kcal from a fake meal baseline.
- `Sweetgreen Crispy Rice Bowl`
  - Must use Sweetgreen official menu when available.
  - Expected official-menu-era value observed in session: `640 kcal / 28P / 61C / 30F` from `sweetgreen.com/menu`.
  - Reject third-party mirror values when source is not official.

## Verification pattern

1. Unit-test estimator routing:
   - Branded restaurant text calls Responses API `/v1/responses` with `web_search`.
   - Simple food text calls chat completions with cheap model.
   - Fallback handles quantified protein/almond-milk case without fake baseline.
2. Production verification:
   - Log in through the app/API.
   - Create a temporary meal with target description.
   - Assert returned macros and source behavior.
   - Delete the temporary meal immediately.
3. If possible, inspect stored raw response/source metadata for `openai_web_search` vs `openai_cheap_model` vs fallback.
