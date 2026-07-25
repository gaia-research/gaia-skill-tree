---
name: gaia-intake-close
description: >
  Post-merge intake closing skill. After a review/meta PR that closes intake issues
  is merged (or is CI-green and approved), run this skill to post standardized,
  personalized closing comments on the PR and each intake issue. Comments include:
  full evidence pipeline findings with /trust-appraise TM output, per-row artifact
  scores, decisions rationale, path-to-promotion guidance, and a badge status note.
  Use after /gaia-curate-chain completes and before or immediately after merge.
version: "1.0.0"
---

# /gaia-intake-close

Posts standardized, human-readable closing comments on a merged (or approved) intake PR and its linked issues. Run this after the evidence pipeline and L4 review are complete.

## What it posts

### On the PR

A summary comment covering all skills in the PR:
- Full adversarial evidence audit findings table (per entry: type, verdict, action taken, reason)
- `/trust-appraise` output with TM, grade, and per-row artifact scores
- Final calibration decision for each named skill
- Badge status note (see below)

### On each intake issue

A personalized closing comment addressed to the contributor (@handle) covering:
- Final decision (accepted/rejected/deferred)
- Calibrated star level and TM grade
- Which evidence entries were kept, corrected, or removed — and why
- Concrete path-to-promotion: what evidence type and threshold would push them to the next grade
- Link to the merged PR

### Badge status note (always on PR, optionally on issue)

Explains the 2★ floor for badge generation, what unlocks at 2★, and links to `gaiaskilltree.com/badges/` for self-service generation. If the contributor IS at 2★+, embed their actual badge SVG Markdown directly in the comment.

---

## Inputs needed

Before running, have ready:
- The PR number (e.g. `1021`)
- The list of intake issue numbers closed by the PR (e.g. `#677 #993`)
- The `/trust-appraise --skill` output for each new skill (run it inline if not already done)
- The adversarial audit findings (from `/ev-pipeline` or inline adversarial review)

## Procedure

### Step 1 — Gather skill data

For each new skill in the PR, run:
```bash
PYTHONPATH=src python3 scripts/trust_appraise.py --skill contributor/skill-id
```

Read the named skill file to get final star level:
```bash
cat registry/named/<contributor>/<skill-id>.md | head -20
```

### Step 2 — Fetch issue metadata

```bash
gh issue view <issue-number> --comments
```

Note the original contributor handle from the issue body (`**User:**` field in the batch summary).

### Step 3 — Build the PR comment

Structure:
```
## Evidence Pipeline Findings — #<issue> [+ #<issue>...]

[For each skill:]
### #<issue> — `<skill-id>` (<contributor>)

**Final TM: X.X | Grade: <grade> | Calibrated: <N>★ (<status>)**

| Entry | Type | Verdict | Reason |
|---|---|---|---|
| ... | ... | KEPT/REMOVED/CORRECTED | ... |

### /trust-appraise
\`\`\`
TM: X.X  Grade: <grade>
<type>  score=X.X  trust=XX  <source>
\`\`\`

---

## Badges — Status for Newly Onboarded Contributors
[badge section — see below]
```

### Step 4 — Build per-issue comments

Structure:
```
## Pipeline Review Complete — Final Decision

**Skill:** `<skill-id>`
**Contributor:** @<handle>
**Status: <Accepted/Rejected/Deferred> at <N>★ (<status>)**

### Evidence Pipeline Findings
[table]

### /trust-appraise
[output block]

### Path to <next level>
[concrete guidance: what evidence type, what threshold, example sources]

Thank you for the submission @<handle> — [one personalized sentence about the skill concept].
```

### Step 5 — Badge section logic

```python
# Pseudo-logic for badge section
if contributor_star_level >= 2:
    # Embed actual badge SVGs
    post: "Your badges are live: ![skill](https://gaiaskilltree.com/badges/_assets/<handle>/<skill>.svg)"
else:
    # Explain the floor
    post: "Both contributors are at 1★ Awakened — below the 2★ floor for badge generation.
           Visit gaiaskilltree.com/badges/ to generate your own once you reach 2★.
           Path to 2★: [concrete guidance]"
```

### Step 6 — Post comments

```bash
gh pr comment <pr-number> --body "..."
gh issue comment <issue-number> --body "..."
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

---

## Notes

- Always tag the contributor @handle in both the PR and issue comments — this builds transparency and trust
- Keep the "Path to promotion" section concrete: name the evidence type, the TM threshold, and an example source
- For `arxiv` entries with 0 citations: always note "0 citations = 0 TM contribution per registry formula" so it's clear why they were removed/downgraded regardless of stated trust value
- For fabricated view counts: always note "view count not publicly available on source page" — do not guess or estimate
- The badge section is mandatory on every PR comment — it sets expectations for contributors who will look for their badge and find nothing
