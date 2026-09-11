---
name: gaia-intake-close
description: >
  Post-review intake closing skill. After an intake is resolved (whether accepted
  via review/meta PR merge or rejected/deferred at triage/evidence review), run this
  skill to post standardized, personalized closing comments on the PR (if any) and
  each intake issue. Comments include: evidence pipeline findings with /trust-appraise
  TM output, per-row artifact scores, decisions rationale, path-to-promotion/acceptance
  guidance, and a mandatory badge status note including the universal Powered by Gaia badge.
  Use after curation completes, before or immediately after merge for accepted intakes,
  or immediately upon rejection.
version: "1.2.0"
---

# /gaia-intake-close

Posts standardized, human-readable closing comments on an intake issue and its linked PR (when accepted) or directly on the intake issue (when rejected or deferred). Run this after the evidence pipeline and review gates are complete, or immediately upon a triage/review rejection decision.

## What it posts

### On the PR (Accepted intakes only)

A summary comment covering all skills in the PR:
- Full adversarial evidence audit findings table (per entry: type, verdict, action taken, reason)
- `/trust-appraise` output with TM, grade, and per-row artifact scores
- Final calibration decision for each named skill
- Badge status note with live rendered badges for newly onboarded contributors at ≥2★
- Universal **Powered by Gaia** badge snippet

### On each intake issue (All outcomes: Accepted, Rejected, Deferred)

A personalized closing comment addressed to the contributor (@handle) covering:
- Final decision (accepted/rejected/deferred)
- Calibrated star level and TM grade (for accepted), or rejection/deferral basis (for rejected/deferred)
- Which evidence entries were kept, corrected, or removed — and why (or triage findings if rejected before evidence review)
- Concrete path-to-promotion (for accepted) or path-to-acceptance (for rejected/deferred): what changes or evidence types would clear the bar
- **Mandatory Badge Status Note**: Explains the badge status for the contributor, embeds live badges (for accepted ≥2★), explains the 2★ floor and links to `gaiaskilltree.com/badges/`, AND always includes the universal **Powered by Gaia** badge snippet
- Link to the merged PR (if accepted)

### Badge status note (Mandatory on every closing comment)

Every closing comment — whether accepted, rejected, or deferred — **must** include a `### Badges` section:
- **Universal Powered by Gaia badge (Every submitter gets this):** Anyone submitting an intake to Gaia is entitled to display the universal **Powered by Gaia** badge in their repository, even if their submission was rejected or deferred:
  ```markdown
  [![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)
  ```
- **Accepted at ≥2★:** In addition to the universal badge, embed their actual named skill badge SVG image using Markdown image syntax (`![alt](url)` — never a bare link), provide a copy-paste Markdown embed snippet for their README, and link to self-service generation at `gaiaskilltree.com/badges/?u=<handle>&s=<skill>`.
- **Accepted at 1★ (below 2★ floor):** Explain the 2★ Named floor for skill/rank badge generation ("1★ skills exist, 1★ badges do not"), provide the universal **Powered by Gaia** badge, and link to `gaiaskilltree.com/badges/`.
- **Rejected or Deferred:** Explain that named skill and rank badges are reserved for accepted skills that reach the 2★ Named floor with verified evidence, provide the universal **Powered by Gaia** badge for their repo, and explain how resubmission reaching 2★ unlocks named badges.

---

## Inputs needed

Before running, have ready:
- The intake issue number(s) (e.g. `#1793`, `#1766`)
- The outcome: `accepted`, `rejected`, or `deferred`
- If accepted: The PR number (e.g. `#1800`), `/trust-appraise --skill` output, calibrated star level, adversarial audit findings
- If rejected/deferred: The triage/audit findings, specific reasons (e.g. non-generalizable, missing attribution, unresolvable evidence), and constructive path to acceptance

## Procedure

### Step 1 — Gather skill data (Accepted intakes)

For each new skill in the PR, run:
```bash
PYTHONPATH=src python3 scripts/trust_appraise.py --skill contributor/skill-id
```

Read the named skill file to get final star level:
```bash
cat registry/named/<contributor>/<skill-id>.md | head -20
```

*(For rejected intakes, gather the rejection reasons and actionable generalization/attribution guidance instead.)*

### Step 2 — Fetch issue metadata

```bash
gh issue view <issue-number> --comments
```

Note the original contributor handle from the issue body (`**User:**` or `contributor:` field in the batch summary).
Check if the contributor already has existing badges:
```bash
ls docs/badges/_assets/<handle>/ 2>/dev/null
```

### Step 3 — Build the PR comment (Accepted intakes)

Structure:
```markdown
## Evidence Pipeline Findings — #<issue> [+ #<issue>...]

[For each skill:]
### #<issue> — `<skill-id>` (<contributor>)

**Final TM: X.X | Grade: <grade> | Calibrated: <N>★ (<status>)**

| Entry | Type | Verdict | Reason |
|---|---|---|---|
| ... | ... | KEPT/REMOVED/CORRECTED | ... |

### /trust-appraise
```
TM: X.X  Grade: <grade>
<type>  score=X.X  trust=XX  <source>
```

---

## Badges — Status for Newly Onboarded Contributors

@<handle> is at <N>★ — badges are live now:

![@<handle>/<skill-id>](https://gaiaskilltree.com/badges/_assets/<handle>/<skill-id>.svg)

Visit `gaiaskilltree.com/badges/?u=<handle>&s=<skill-id>` to generate the seal variant and any additional badge types.

Universal **Powered by Gaia** badge:
```markdown
[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)
```
```

### Step 4 — Build per-issue comments

#### Variant A: Accepted Intake
```markdown
## Pipeline Review Complete — Final Decision

**Skill:** `<skill-id>`
**Contributor:** @<handle>
**Status: Accepted at <N>★ (<status>)**

### Evidence Pipeline Findings
[table]

### /trust-appraise
[output block]

### Path to <next level>
[concrete guidance: what evidence type, what threshold, example sources]

### Badges
[badge section — see Step 5]

---

Thank you for the submission @<handle> — [one personalized sentence about the skill concept].

Merged in #<pr>.
```

#### Variant B: Rejected / Deferred Intake
```markdown
## Pipeline Review Complete — Final Decision

**Skills:** `<skill-id-1>`, `<skill-id-2>`
**Contributor:** @<handle>
**Status: Rejected** (or Deferred) — [brief summary, e.g. "no evidence pipeline was run since this didn't clear intake triage; nothing to calibrate"]

### Findings

| Skill | Verdict | Reason |
|---|---|---|
| `<skill-id>` | REJECTED / DEFERRED | [Specific, falsifiable reason: e.g. tool dispatch without attribution, product-specific coupling] |

### Path to acceptance — `<promising-skill-id>`

[Actionable, constructive guidance: e.g. generalize the capability name and flow, credit upstream author, provide reproducible benchmarks]

### Badges
[badge section for rejected/deferred — see Step 5]

---

Thanks again for the batch, @<handle> — [encouraging closing sentence acknowledging effort and inviting revised resubmission].
```

### Step 5 — Badge section logic (Mandatory for ALL comments)

```python
if outcome == "accepted" and contributor_star_level >= 2:
    # Contributor is at or above the 2★ badge floor — EMBED LIVE BADGE IMAGE + POWERED BY GAIA
    # CRITICAL: Always use Markdown image syntax ![alt](url) — NEVER a bare link [text](url)
    post: """### Badges

`<contributor>/<skill-id>` is at <N>★ (<status>), so your badges are live:

![@<contributor>/<skill-id>](https://gaiaskilltree.com/badges/_assets/<contributor>/<skill-id>.svg)

Embed in your `README.md`:
```markdown
[![Gaia](https://gaiaskilltree.com/badges/_assets/<contributor>/<skill-id>.svg)](https://gaiaskilltree.com/u/<contributor>/)
```

Self-service badge generation, rank badge, and seal variants are at [gaiaskilltree.com/badges/?u=<contributor>&s=<skill-id>](https://gaiaskilltree.com/badges/?u=<contributor>&s=<skill-id>).

You can also use the universal **Powered by Gaia** badge:

[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)

```markdown
[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)
```"""

elif outcome == "accepted" and contributor_star_level < 2:
    # 1★ Awakened — below the 2★ badge floor, but gets Powered by Gaia badge
    post: """### Badges

`<contributor>/<skill-id>` is at 1★ Awakened — below the 2★ Named floor for skill-specific badge generation ("1★ skills exist, 1★ badges do not").

However, you can use the universal **Powered by Gaia** badge in your repository right now:

[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)

```markdown
[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)
```

Skill-specific badges (handle, rank, `<skill-id>`) unlock at 2★ Named. Visit [gaiaskilltree.com/badges/](https://gaiaskilltree.com/badges/) to preview them.
Path to 2★: [concrete guidance on evidence needed to reach TM 20]."""

else:
    # Rejected or Deferred intake — gets the universal Powered by Gaia badge
    post: """### Badges

Skill-specific and rank badges unlock at 2★ Named with verified evidence, so no named skill badge was generated for this batch. However, as an intake participant, you can use the universal **Powered by Gaia** badge in your repository right now:

[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)

```markdown
[![Powered by Gaia](https://gaiaskilltree.com/badges/powered-by-gaia.svg)](https://gaiaskilltree.com)
```

Once a generalized resubmission addressing the findings above is accepted and calibrated to 2★+, automated badges (skill badge, rank badge, and seal variants) will unlock and become live at [gaiaskilltree.com/badges/](https://gaiaskilltree.com/badges/)."""
```

### Step 6 — Post comments and close issues

**For Accepted Intakes:**
```bash
gh pr comment <pr-number> --body-file /tmp/pr-close-comment.md
gh issue comment <issue-number> --body-file /tmp/issue-close-comment.md
gh issue close <issue-number>
```

**For Rejected Intakes:**
```bash
# Ensure intake:rejected is applied
gh issue edit <issue-number> --add-label "intake:rejected"
# Post the comprehensive closing comment
gh issue comment <issue-number> --body-file /tmp/issue-close-comment.md
# Close the intake issue
gh issue close <issue-number>
# Clean up any staged review branch if pushed
git push origin --delete review/meta/<handle>--<skill> 2>/dev/null || true
```

---

## Evidence pipeline verdict taxonomy

Use these exact verdict labels in the findings table for consistency:

| Verdict | Meaning |
|---|---|
| **KEPT** | Entry passes all checks — URL live, metadata accurate, relevant |
| **KEPT (corrected)** | Entry kept but metadata was wrong — note what was fixed |
| **REMOVED** | Entry removed — note primary reason |
| **DEFERRED** | Entry not yet verifiable (e.g. SKILL.md not yet published) — note when it can be added |
| **REJECTED** | Entry or skill rejected — does not meet criteria (unattributed, product-coupled, etc.) |

---

## Notes

- Always tag the contributor @handle in both the PR and issue comments — this builds transparency and trust
- Keep the "Path to promotion" / "Path to acceptance" section concrete: name the evidence type, the TM threshold, or specific generalization steps
- **The `### Badges` section is MANDATORY on EVERY closing comment** — accepted, rejected, and deferred alike. Contributors look for their badges or want to know what unlocks them; never leave them guessing
- **Every intake participant receives the universal Powered by Gaia badge (`powered-by-gaia.svg`)**, including rejected and 1★ submissions. Never omit it
- **Always format live badges as Markdown images `![alt](url)`**, NEVER bare hyperlinks `[text](url)`. Bare links do not render the SVG visual in GitHub comments
- For `arxiv` entries with 0 citations: always note "0 citations = 0 TM contribution per registry formula" so it's clear why they were removed/downgraded regardless of stated trust value
- For fabricated view counts: always note "view count not publicly available on source page" — do not guess or estimate
