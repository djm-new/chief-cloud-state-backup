---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, writing-plans, subagent-driven-development]
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find root cause before attempting fixes. Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**
- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

**Important interaction rule:** if the user says the product is broken or a bug is obvious, do *not* ask permission to fix it. Start investigation and repair immediately. Only ask a clarifying question when the scope is genuinely ambiguous or the action would be destructive.

## The Four Phases

You MUST complete each phase before proceeding to the next.

---

## Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

### 1. Read Error Messages Carefully

- Don't skip past errors or warnings
- They often contain the exact solution
- Read stack traces completely
- Note line numbers, file paths, error codes

**Action:** Use `read_file` on the relevant source files. Use `search_files` to find the error string in the codebase.

### 2. Reproduce Consistently

- Can you trigger it reliably?
- What are the exact steps?
- Does it happen every time?
- If not reproducible → gather more data, don't guess

**Action:** Use the `terminal` tool to run the failing test or trigger the bug:

```bash
# Run specific failing test
pytest tests/test_module.py::test_name -v

# Run with verbose output
pytest tests/test_module.py -v --tb=long
```

### 3. Check Recent Changes

- What changed that could cause this?
- Git diff, recent commits
- New dependencies, config changes

**Action:**

```bash
# Recent commits
git log --oneline -10

# Uncommitted changes
git diff

# Changes in specific file
git log -p --follow src/problematic_file.py | head -100
```

### 4. Gather Evidence in Multi-Component Systems

**WHEN system has multiple components (API → service → database, CI → build → deploy):**

**BEFORE proposing fixes, add diagnostic instrumentation:**

For EACH component boundary:
- Log what data enters the component
- Log what data exits the component
- Verify environment/config propagation
- Check state at each layer

Run once to gather evidence showing WHERE it breaks.
THEN analyze evidence to identify the failing component.
THEN investigate that specific component.

### 5. Trace Data Flow

**WHEN error is deep in the call stack:**

- Where does the bad value originate?
- What called this function with the bad value?
- Keep tracing upstream until you find the source
- Fix at the source, not at the symptom

**Action:** Use `search_files` to trace references:

```python
# Find where the function is called
search_files("function_name(", path="src/", file_glob="*.py")

# Find where the variable is set
search_files("variable_name\\s*=", path="src/", file_glob="*.py")
```

### 6. For Web Apps, Verify the Deployed Client Code

When the symptom is "button does nothing", "form submits nowhere", or a browser-side action appears inert:

- First confirm whether the backend/API works with a direct request.
- Then inspect the deployed HTML/JS assets to verify the expected client handler is actually deployed.
- Do not infer client interactivity from server-rendered HTML alone; React/Next event handlers are in JS chunks, not literal `onSubmit` attributes in the HTML.
- Check for uncommitted/staged-only local changes if production is missing code you expected to be live.
- For gallery/crop apps, explicitly check whether bundled sample/demo assets are being routed through a hardcoded special-case branch. If the sample images are just inputs, they usually should use the same detector path as uploads.
- If a demo layout was copied from a previous photo set, treat it as suspect until verified against the new images.
- If a demo layout was copied from a previous photo set, treat it as suspect until verified against the new images.
- For static crop galleries, create a contact sheet of every crop and inspect it before shipping: it catches sideways covers, mostly-background/wood tiles, and partial-book boxes that a simple count check misses.

See `references/book-sorter-sample-segmentation.md` for a concrete example, including contact-sheet verification.

Example probe:

```bash
python3 - <<'PY'
import re, urllib.request
base='https://example.app'
html=urllib.request.urlopen(base+'/login', timeout=30).read().decode('utf-8','replace')
for src in re.findall(r'<script[^>]+src="([^"]+\.js)"', html):
    js=urllib.request.urlopen(base+src, timeout=30).read().decode('utf-8','replace')
    if '/api/auth/login' in js or 'window.location.assign' in js:
        print('found login handler in', src)
PY
```

### 7. For DB-Backed API 500s, Inspect Provider Logs and Normalize Payloads

When a form displays a generic save failure but the API returns a blank 500:

- Reproduce the exact API request with an authenticated session and record status/body.
- Pull provider/runtime logs before patching; ORMs often put the real validation error there when the HTTP response is empty.
- Compare frontend payload shape, validation schema, and ORM model field types.
- Do not pass raw validated browser payloads directly into ORM `create`/`update` if they contain presentation-format fields (for example `YYYY-MM-DD` date strings for `DateTime` columns). Build a DB-specific data object instead.
- For upserts, check both `create` and `update` branches; it is common to normalize one branch but accidentally leave the raw value in the other.

### Phase 1 Completion Checklist

When a browser form shows a generic failure but the API returns 500:

- Reproduce the request directly with the same session/cookies and a minimal payload matching the UI action.
- Pull server logs before patching; Prisma/ORM validation errors often identify the exact field/value mismatch.
- Trace transformations at every boundary: form values → JSON payload → validation schema → ORM `create`/`update` data.
- Do not pass raw validated client data directly to an ORM write if it contains fields that need normalization, derived values, or should not be writable. Destructure/normalize first and use a sanitized `data` object.
- In upserts, check both `create` and `update`; it is common for `create` to normalize a field correctly while `update` still receives the raw client value.

Example: for a DateTime column, a date input may send `YYYY-MM-DD`. Convert once (`new Date(`${dateString}T00:00:00.000Z`)`) and ensure neither `create` nor `update` receives the raw date-only string.

### 8. For Mobile UI Bugs, Inspect Layout at the Component/CSS Level

When the symptom is "inputs are smushed," "values are clipped," "horizontal scroll exists but is unusable," or a mobile screenshot shows a table/form that technically renders but is illegible:

- Identify the exact component and CSS/layout rules producing the mobile view.
- Do not treat `overflow-x: auto` as sufficient for mobile editing UX; table auto-layout can shrink input controls until values are hidden.
- Check whether the bug is a data issue, a rendering issue, or a responsive breakpoint issue.
- Prefer a minimal responsive fix: stacked editable cards on mobile and the dense table only above a tablet/desktop breakpoint.
- Verify production by checking the actual route HTML plus linked CSS/JS for unique new classes/copy, not only by hitting `/api/health`.

### 9. For Wrong AI/Estimator Outputs, Debug the Workflow, Not Just the Value

When a user says an AI-derived output is wrong (nutrition estimates, extraction, classification, summaries, scoring, etc.):

- Trace the whole pipeline: UI text → API payload → model/provider path → prompt/tool availability → fallback path → stored raw response/source metadata.
- Compare the implemented workflow against the user's trusted manual workflow. If the product replaced "ask a capable LLM that can look things up" with "cheap no-search guess," that is a workflow regression, not a single bad answer.
- Do not treat a one-off hardcoded override as the class-level fix. Use it only as a temporary guardrail while fixing routing/source validation.
- For branded/official-source domains (restaurant nutrition, product specs, prices, legal terms), verify whether the model can and did search authoritative sources. Prefer official sources over third-party mirrors and reject/flag low-confidence sources when official data is expected.
- If a fallback fires, make that visible in raw/source metadata and keep it conservative; avoid fake high-confidence baselines.
- Add regression tests for both routing (which model/tool path is called) and representative output values.

### Phase 1 Completion Checklist
### 9. For AI/Heuristic Estimation Bugs, Identify the Real Engine

When the symptom is "this estimate seems wrong" or a user compares an AI-generated value against an authoritative source:

- Trace UI payload → API route → estimator → model/provider/fallback → persisted metadata before changing prompts.
- Check production env/config to see whether the intended model is actually active; a fallback heuristic may be the real engine.
- Reproduce with the exact user phrase through the same API endpoint the UI uses.
- For branded/restaurant items, prefer official published nutrition/data over model guesses.
- For quantified simple inputs, parse quantities conservatively in fallback and never add a generic default baseline.
- Add regression tests for the exact bad estimate and for source-priority behavior.
- See `references/nutrition-estimator-debugging.md` for the food/nutrition estimator pattern.

### 10. For Model Usage / Spend Mismatches, Trace the Side-Channel

When a usage dashboard or spend report undercounts Hermes model usage:

- Trace both the main session path *and* auxiliary paths such as compression, title generation, session search, vision, or web extraction.
- Compare the visible session ledger against any event-level spend store; main sessions often miss auxiliary Anthropic/Codex calls if they are not explicitly recorded.
- Inspect config and logs together: `config.yaml` auxiliary provider/model overrides often explain why Sonnet/Haiku appears even when the chat session model is different.
- Treat ledger writes as best-effort instrumentation, but make the capture path explicit so side-channel usage is not lost.
- Add a regression test or probe that proves the auxiliary call writes a spend event.

### Phase 1 Completion Checklist

- [ ] Error messages fully read and understood
- [ ] Issue reproduced consistently
- [ ] Recent changes identified and reviewed
- [ ] Evidence gathered (logs, state, data flow)
- [ ] Problem isolated to specific component/code
- [ ] Root cause hypothesis formed

**STOP:** Do not proceed to Phase 2 until you understand WHY it's happening.

---

## Phase 2: Pattern Analysis

**Find the pattern before fixing:**

### 1. Find Working Examples

- Locate similar working code in the same codebase
- What works that's similar to what's broken?

**Action:** Use `search_files` to find comparable patterns:

```python
search_files("similar_pattern", path="src/", file_glob="*.py")
```

### 2. Compare Against References

- If implementing a pattern, read the reference implementation COMPLETELY
- Don't skim — read every line
- Understand the pattern fully before applying

### 3. Identify Differences

- What's different between working and broken?
- List every difference, however small
- Don't assume "that can't matter"

### 4. Understand Dependencies

- What other components does this need?
- What settings, config, environment?
- What assumptions does it make?

---

## Phase 3: Hypothesis and Testing

**Scientific method:**

### 1. Form a Single Hypothesis

- State clearly: "I think X is the root cause because Y"
- Write it down
- Be specific, not vague

### 2. Test Minimally

- Make the SMALLEST possible change to test the hypothesis
- One variable at a time
- Don't fix multiple things at once

### 3. Verify Before Continuing

- Did it work? → Phase 4
- Didn't work? → Form NEW hypothesis
- DON'T add more fixes on top

### 4. When You Don't Know

- Say "I don't understand X"
- Don't pretend to know
- Ask the user for help
- Research more

---

## Phase 4: Implementation

**Fix the root cause, not the symptom:**

### 1. Create Failing Test Case

- Simplest possible reproduction
- Automated test if possible
- MUST have before fixing
- Use the `test-driven-development` skill

### 2. Implement Single Fix

- Address the root cause identified
- ONE change at a time
- No "while I'm here" improvements
- No bundled refactoring

### 3. Verify Fix

```bash
# Run the specific regression test
pytest tests/test_module.py::test_regression -v

# Run full suite — no regressions
pytest tests/ -q
```

### 4. If Fix Doesn't Work — The Rule of Three

- **STOP.**
- Count: How many fixes have you tried?
- If < 3: Return to Phase 1, re-analyze with new information
- **If ≥ 3: STOP and question the architecture (step 5 below)**
- DON'T attempt Fix #4 without architectural discussion

### 5. If 3+ Fixes Failed: Question Architecture

**Pattern indicating an architectural problem:**
- Each fix reveals new shared state/coupling in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Are we "sticking with it through sheer inertia"?
- Should we refactor the architecture vs. continue fixing symptoms?

**Discuss with the user before attempting more fixes.**

This is NOT a failed hypothesis — this is a wrong architecture.

---

## Red Flags — STOP and Follow Process

If you catch yourself thinking:
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** Question the architecture (Phase 4 step 5).

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence, trace data flow | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare, identify differences | Know what's different |
| **3. Hypothesis** | Form theory, test minimally, one variable at a time | Confirmed or new hypothesis |
| **4. Implementation** | Create regression test, fix root cause, verify | Bug resolved, all tests pass |

## Hermes Agent Integration

### Investigation Tools

Use these Hermes tools during Phase 1:

- **`search_files`** — Find error strings, trace function calls, locate patterns
- **`read_file`** — Read source code with line numbers for precise analysis
- **`terminal`** — Run tests, check git history, reproduce bugs
- **`web_search`/`web_extract`** — Research error messages, library docs

### With delegate_task

For complex multi-component debugging, dispatch investigation subagents:

```python
delegate_task(
    goal="Investigate why [specific test/behavior] fails",
    context="""
    Follow systematic-debugging skill:
    1. Read the error message carefully
    2. Reproduce the issue
    3. Trace the data flow to find root cause
    4. Report findings — do NOT fix yet

    Error: [paste full error]
    File: [path to failing code]
    Test command: [exact command]
    """,
    toolsets=['terminal', 'file']
)
```

### With test-driven-development

When fixing bugs:
1. Write a test that reproduces the bug (RED)
2. Debug systematically to find root cause
3. Fix the root cause (GREEN)
4. The test proves the fix and prevents regression

## References

- `references/nextjs-prisma-api-500.md` — minimal reproduction and fix pattern for Next.js API routes whose form payload validates but Prisma/ORM writes fail, especially date-only strings sent to DateTime fields or raw parsed data used in upsert updates.
- `references/nextjs-app-router-server-refresh.md` — fix pattern for client-side mutations that save successfully but leave server-rendered App Router dashboard cards stale until `router.refresh()` or a full reload.
- `references/app-day-timezone-debugging.md` — debugging and fix pattern for apps that show/log the wrong day because server UTC date keys are used instead of the product timezone/app day.
- `references/nutrition-estimator-debugging.md` — debugging and fix pattern for food/nutrition estimator bugs.
- `references/nutrition-estimator-quantity-language.md` — serving/scoop language pitfall for protein powders and supplements.


From debugging sessions:
- Systematic approach: 15-30 minutes to fix
- Random fixes approach: 2-3 hours of thrashing
- First-time fix rate: 95% vs 40%
- New bugs introduced: Near zero vs common

**No shortcuts. No guessing. Systematic always wins.**
