---
name: writing-plans
description: "Write implementation plans: bite-sized tasks, paths, code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

**Discovery mode reference:** For low-friction product/spec interviews before implementation, see `references/product-discovery-interview.md`. For DJ's health/fitness app discovery notes, see `references/health-fitness-app-discovery-dj.md`. For the reusable pattern of turning an approved PWA plan into a locally verified Next.js/Railway scaffold, see `references/nextjs-railway-pwa-bootstrap.md`. For HealthOS workout logging UX, see `references/healthos-workout-ux.md`: workout flows should be plan-first and exception-only, not per-rep/per-set data entry. For workout history/progression drill-downs, see `references/healthos-workout-history-drilldown.md`: keep the live workout logger unchanged, derive the drill-down from completed sessions, slugify exercise names for stable URLs, and fall back gracefully when a summary is missing. For HealthOS dashboard/meals/history UX, see `references/healthos-daily-ledger-ux.md`: the app should behave like a date-driven daily ledger with editable grouped meal tables and next-day review/finalization. For HealthOS meal macro estimation, see `references/healthos-nutrition-estimator-workflow.md`: preserve DJ's old LLM+lookup workflow, use web search for branded/restaurant foods, prefer official nutrition sources, and avoid confident cheap guesses when official lookup fails.

## When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via subagent-driven-development

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Before the Plan: Product Discovery Interview

When the user wants to design/align before implementation, do **not** jump directly to a full implementation plan or a giant questionnaire. Run an interactive discovery interview first:

- Ask one short question at a time.
- Prefer multiple-choice options plus room for freeform answers.
- After each answer, restate the decision in one concise sentence and ask the next most informative question.
- Keep momentum; avoid making the user scroll back and answer a long list.
- If the user asks for "BMAD-style" or interview mode, use fast pitter-patter questions until requirements are crisp.
- Only synthesize into a PRD/spec after enough answers are collected.
- Only write an implementation plan after the user approves the product direction.

See `references/product-discovery-interview.md` for the reusable interview pattern and DJ's current health/exercise app decisions.

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

#### Product-discovery interview mode

When requirements are still being shaped with the user, do **not** dump a long questionnaire. Use a fast interview cadence instead:

- Ask one short, high-leverage question at a time.
- Offer compact choices (A/B/C/D) when useful, but accept fragments or free-form answers.
- Summarize each decision in 1-2 lines, then immediately ask the next question.
- Stop after enough alignment and synthesize into a spec; do not chase every edge case forever.
- If the user asks for “BMAD style” or complains that scrolling through questions is high friction, switch to this interview mode.
- Do not implement while still in alignment mode unless the user explicitly approves moving from design to build.

For a reusable checklist and spec shape from a health/dashboard app discovery session, see `references/product-discovery-interview-pattern.md`. For phone-first review/gallery apps with corner actions and center-tap enlarge, see `references/mobile-review-gallery-discovery.md`. For apps that crop/review photographed physical items, use `references/photographed-item-crop-and-review-qa.md` for the background-segmentation crop workflow and QA gates.

### Step 2: Explore the Codebase

### Step 2: Explore the Codebase

Use Hermes tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied

### Step 7: Save the Plan

```bash
mkdir -p docs/plans
# Save plan to docs/plans/YYYY-MM-DD-feature-name.md
git add docs/plans/
git commit -m "docs: add implementation plan for [feature]"
```

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Execution Handoff

After saving the plan, offer the execution approach:

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**

### DJ active-project mode

**DJ's explicit standing instruction:** "Don't make me prompt you. If we're on a project, keep pushing until we're done." He has expressed this multiple times with increasing frustration ("why do you keep stopping? just go"). Treat any session where an active build project is in flight as being in this mode by default — you should not need to be told twice.

When DJ explicitly says to "go forward," "keep going," or that he should not have to keep prompting during an active project, switch from interview/plan-only mode into active execution:

- **Never end a turn mid-project asking "what's next?" or "shall I continue?" if safe local actions remain.** Just do them.
- Continue making concrete progress until the current phase is complete and verified, or until an external blocker requires credentials/approval.
- Do not end a turn with only "next steps" if safe local actions remain (write spec, scaffold repo, run tests, commit, update status docs).
- Keep a compact status file in the project (e.g. `PROJECT_STATUS.md`) with completed work, verification commands, local commits, and external blockers so future sessions resume without rediscovery.
- Still ask before live external side effects that need explicit approval or credentials (deployments, recurring jobs, external notifications, account changes), but keep doing local/reversible implementation work when scope is clear.
- Verify before summarizing: typecheck/tests/build or the project-appropriate equivalent, then commit in small chunks.
- When a phase ends (tests green, build clean, committed), immediately identify the next phase and start it in the same turn.
- Only surface a summary/checkpoint to DJ when: (a) a real external blocker is hit (auth, credentials, remote service), (b) a destructive/irreversible action is about to happen, or (c) the entire project is done.

When executing, use the `subagent-driven-development` skill:
- Fresh `delegate_task` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
```

**A good plan makes implementation obvious.**
