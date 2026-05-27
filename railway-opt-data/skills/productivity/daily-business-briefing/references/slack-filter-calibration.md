# Slack Filter Calibration — DJ Mauch / Flow workspace

Validated through iterative briefing feedback, session 2026-05-26/27.
These are DJ's explicit corrections to the filter. Update this file as further feedback comes in.

---

## Channel classification

### Hard-exclude (suppress regardless of content)
| Channel pattern | Reason |
|---|---|
| `plattest-012n3` | Duplicate bot noise channel |
| `test-android-results` | CI test results only |
| `waves-dev-test-automation` | Automated test smoke results |
| `backend-dev-testify-automation` | Automated test results |
| `application-status` | Bot-only status channel |
| `*-cleaning` / `*-housekeeping` | Ops-level, below DJ |

### Always include (content passes regardless of keyword weakness)
| Channel pattern | Reason |
|---|---|
| `proj-society-wynwood-acquisition` | Active deal DJ cares about |
| `proj-mena` / `*-mena` | MENA is top-priority block |
| `proj-easton` | Active deal |
| Any `mpdm-*` (group DM) | DJ is a participant |
| Any direct DM to DJ | Always relevant |

### Include with signal — leasing channels
| Channel pattern | Include when... |
|---|---|
| `*-leasing-renewals` | Tour/prospect/staffing signals present |
| `*-fx-leasing-*` | People waiting, no-show staff, prospect issues |
| `support-waves-leasing` | Only with money/legal/Yardi-system signal |

**Key lesson:** "leasing" is a WEAK keyword for Flow because it's everywhere. Don't include leasing channel content just because it mentions leasing. Include it when there's a TOUR, PROSPECT, OCCUPANCY, WAIT TIME, CONVERSION, or STAFFING signal.

### Include with entity — engineering
| Condition | Include when... |
|---|---|
| `#engineering` + ToM entity | Product naming, blocker, entity-linked decision |
| `#engineering` no entity | Exclude (charge code logic, identity ops, color fixes, PR merges) |

---

## User signals → DJ relevance scoring

### Signals that always justify executive awareness
- `approve`, `approval`, `decision`, `urgent`, `asap`, `blocked`, `blocker`, `stuck`
- `escalat`, `deadline`, `today`, `tomorrow`
- `contract`, `legal`, `signature`, `wire`, `payment`, `invoice`, `drawdown`, `capital`
- `$`, `revenue`, `budget`, `cash`, `pricing`, `churn`
- `customer escalation`, `board`, `investor`
- `dd `, `due diligence`, `data room`, `access agreement`, `loan`
- `security`, `permission`

### Weak keywords — do NOT independently elevate content
These appear constantly at Flow and should NOT trigger inclusion on their own:
- `leasing`, `renewal`, `test`, `data`, `build`, `tool`, `future`, `head`
- `results`, `request`, `feature`, `roadmap`, `comp`, `program`, `launch`, `complete`, `close`

### Tour/prospect keywords (valid in leasing channels only)
- `tour`, `tours`, `prospect`, `prospective`, `showing`, `walkthrough`
- `visitor`, `occupancy`, `vacancy`, `traffic`, `conversion`
- `move-in`, `available unit`, `waiting`, `no one here`, `people waiting`

---

## Hard exclusions by content

### App install requests — HARD EXCLUDE
`USLACKBOT` messages like "X would like to install the app Y on workspace Flow"
- DJ is super admin; receives these automatically.
- **These are IT's responsibility, not DJ's.**
- They were previously being scored as "workspace app governance" — **this is wrong.**
- Remove `install the app` from exec signals; add to hard-exclude list.

---

## Briefing anti-patterns (learned from feedback)

1. **Connecting unrelated items:** Vercel access approval ≠ MENA KPI work unblocked. Don't infer causation across unrelated sources.
2. **Asserting resolved state:** A Google Slides comment being "resolved" ≠ the underlying business question answered. Leave it open unless explicitly confirmed closed.
3. **Quoting DMs out of context:** "great. let's wind him down" without context → don't guess who. State what's known (participants, instruction), what's unknown (subject), and provide the link.
4. **Neutral presentation:** Don't just list that something exists. Tell DJ what to do about it.
5. **Conductor / app install in briefing:** Never include. Already filtered; if it slips through, drop it.

---

## Filter threshold (as of v3)

Score threshold for inclusion: **≥ 105**
- DM/MPIM: +95 base
- Direct DJ mention: +130 base
- ToM entity match: +90 base (+ per-entity bonus up to +35)
- Exec signal: +45 base (+ per-signal bonus up to +40)
- Priority deal/project channel: +40
- Engineering × ToM entity: +30
- Leasing/tour signal: +120
- Collector score cap: min(score, 35)
- Bot/test noise (no DM/mention/entity): -200
- Cleaning channel: -150
- Generic weak keyword only: -70
- Low substance (<25 chars): -60

Max items passed to synthesis: 22 (raised from 18 to allow more leasing/deal context)
Max context lines per DM item: 8 (raised from 3 — DMs need context to be interpretable)
