---
name: gaia-tm-inspect
description: >
  Live Trust Magnitude breakdown and ranked leaderboard for all named GAIA skills.
  Inspect mode shows per-evidence artifact scores, multiplier chains, dead rows, and
  the next-grade gap. Leaderboard mode ranks all 249+ skills by TM grouped by grade band.
version: "1.0.0"
genericSkillRef: registry-inspection
---

# /gaia-tm-inspect

Instantly view the live Trust Magnitude breakdown for any named GAIA skill,
or generate a ranked leaderboard of all skills.

## Two Modes

### Inspect Mode — single skill deep-dive

```
/gaia-tm-inspect <skillId>
```

Where `<skillId>` is the contributor/name path (e.g. `garrytan/gstack`,
`mattpocock/grill-me`, `obra/superpowers`).

**Output includes:**
- Each evidence row: type, source URL, and the full contribution chain:
  `base magnitude → × weight → × freshness → × mothership/creator/engagement → × inheritMultiplier → × plateau → final score`
- Dead rows (zero contribution) and the reason why (missing views, stars below
  10k threshold, deranked verifier, etc.)
- Auto-derived fusion-recipe info if `suiteComponents` is present: component
  count, graded origin count, raw fusion magnitude
- Total TM, overall grade, and the exact points needed to reach the next grade
- Most efficient evidence type to add for the next TM jump

**Example:**
```
/gaia-tm-inspect obra/superpowers
```

### Leaderboard Mode — all skills ranked

```
/gaia-tm-inspect --leaderboard
```

Generates a full ranked table grouped by grade band:

| Band | Threshold |
|---|---|
| S grade | TM >= 250 |
| A grade | TM >= 100 |
| B grade | TM >= 50  |
| C grade | TM >= 20  |
| Ungraded | TM < 20  |

Columns: Rank, Skill ID, TM, Grade, Level, Contributor.

## Implementation

The skill runs `scripts/inspectTrustMagnitude.py` in the repo root:

```bash
# Inspect a single skill
GAIA_OPERATOR_OVERRIDE=1 python scripts/inspectTrustMagnitude.py --skill <skillId>

# Full leaderboard
GAIA_OPERATOR_OVERRIDE=1 python scripts/inspectTrustMagnitude.py --leaderboard
```

The script:
1. Loads the genericSkillMap from `registry/nodes/` (for fusion-recipe resolution)
2. Finds the named skill in `registry/named/<contributor>/<name>.md`
3. Calls `explainTrustMagnitude()` from `src/gaia_cli/trustMagnitude.py`
4. Prints the full factor chain for every evidence row in the effective pool
5. For leaderboard: loads all 249+ named skills, recomputes live TM, sorts descending

## Agent Instructions

When invoked as `/gaia-tm-inspect <skillId>`:

1. Run the inspect command for the requested skill.
2. Parse the output and present a concise summary table of evidence rows with
   their final scores.
3. Highlight any dead rows (score = 0.0) and explain why.
4. State the next-grade gap clearly: "needs X more TM to reach grade Y".
5. Suggest the single most efficient evidence type to add.

When invoked as `/gaia-tm-inspect --leaderboard`:

1. Run the leaderboard command.
2. Present the full output grouped by grade band.
3. Note any surprising scores — skills with many evidence rows but low TM
   may have dead rows worth investigating.

## Trust Magnitude Formula Reference

```
artifact_score = magnitude × type_weight × freshness × mothership × creator × engagement
TM = sum(artifact_scores) × [social-signal capped at 80]
```

### Per-type magnitude formulas

| Type | Magnitude Formula | Weight | Cap |
|---|---|---|---|
| fusion-recipe | 20×N (N<=10); 200+20√(N-10) (N>10) | 1.5 | — |
| github-stars-own | stars / 1000 | 1.0 | 200 |
| proxy-containment | (externalStars/1000)×0.8 (min 10k) | 1.0 | 160 |
| verifier-attestation | 30 × verifiers | 1.5 | — |
| benchmark-result | percentile | 1.4 | 100 |
| arxiv | citations / 5 | 1.0 | 100 |
| peer-review | 25 × reviewers | 1.2 | — |
| repo-own | commits/200 + contributors²×2 | 0.6 | 60 |
| self-attestation | 10 | 0.5 | 10 |
| social-signal | log10(views)×8 (min 1k views) | 1.0 | 80 (sum) |

### Grade thresholds

| Grade | TM Floor | Additional Gates |
|---|---|---|
| S | 250 | distinctTypes >= 3 AND has non-self-producible evidence |
| A | 100 | — |
| B | 50 | — |
| C | 20 | — |
| ungraded | < 20 | — |
