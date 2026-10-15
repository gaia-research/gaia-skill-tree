---
name: trust-appraise-all
description: >
  Use this skill when the user wants the full existing-registry Trust Magnitude inspector: understand why a named Gaia skill has a particular
  star rank, what its Trust Magnitude (TM) score is, which evidence rows are contributing
  (or dead), how far it is from the next grade, or what evidence to add to move the needle.
  Also use when asked for a full leaderboard of all named skills ranked by TM.
  Triggers: "why does X have 3 stars", "what's the TM for X", "inspect TM",
  "explain the score for X", "what evidence would rank up X", "show leaderboard",
  "rank all skills by TM", "what's dragging down X's score", "dead evidence rows",
  "how close is X to grade A/S".
version: "1.2.0"
genericSkillRef: registry-inspection
---

# /trust-appraise-all

Breaks down the Trust Magnitude (TM) score for any named Gaia skill, or produces a full ranked leaderboard. TM is the composite evidence score that gates star promotions — understanding it tells you exactly why a skill is ranked where it is and what would change that.

**Scope (authority map §2):** inspect mode reports the **effective named** TM, which sums own
rows plus resolved generic inheritance. If the `genericSkillRef` node does not resolve, say
"generic: not evaluated" and do not call the total final.

## Two Modes

### Inspect Mode — single skill deep-dive

```
/trust-appraise-all <skillId>
```

`<skillId>` is the `contributor/name` path (e.g. `garrytan/gstack`, `mattpocock/grill-me`, `obra/superpowers`).

**Output includes:**

- Each evidence row with the full score chain:
  `base magnitude → min(cap) → × type weight → × freshness → × creator/engagement (social-signal only) → × inheritMultiplier (inherited rows only) → × plateau → final score`
- Dead rows (score = 0.0) and why (missing views, stars below threshold, deranked verifier, etc.)
- Fusion-recipe summary if `suiteComponents` is present: component count, graded origins, Fusion Score (informational, 0 TM)
- Total TM, overall grade, and exact points to the next grade threshold
- Most efficient evidence type to add for the next TM jump

### Leaderboard Mode — all skills ranked

```
/trust-appraise-all --leaderboard
```

Full ranked table grouped by Overall Trust Grade band (floors and the S diversity gate:
authority map §3).

Columns: Rank, Skill ID, TM, Grade, Level, Contributor.

## How to Run It

```bash
# Inspect a single skill
GAIA_OPERATOR_OVERRIDE=1 python scripts/inspectTrustMagnitude.py --skill <skillId>

# Full leaderboard
GAIA_OPERATOR_OVERRIDE=1 python scripts/inspectTrustMagnitude.py --leaderboard
```

The script loads named skills from `registry/named/`, resolves fusion recipes from `registry/nodes/`, and calls `explainTrustMagnitude()` in `src/gaia_cli/trustMagnitude.py`.

## Agent Instructions

**For `/trust-appraise-all <skillId>`:**

1. Run the inspect command for the requested skill.
2. Present a concise table of evidence rows: type, source, and final score. Group live rows above dead rows.
3. Call out dead rows and explain the specific reason each one contributes 0 (e.g. "social-signal: 820 views — below 1k floor").
4. State the next-grade gap plainly: "needs X more TM to reach grade Y (currently Z)".
5. Recommend the single highest-impact evidence type to add, with reasoning (e.g. "one peer-review with 3 reviewers adds ~90 TM — more than doubling current score").

**For `/trust-appraise-all --leaderboard`:**

1. Run the leaderboard command.
2. Present the output grouped by grade band.
3. Flag any skills with many evidence rows but low TM — dead rows are likely culprits worth a follow-up inspect.

## Trust Magnitude reference

Formulas, weights, caps, dedup, inheritance, grade floors, star gates and appraisal scope
live in one canonical place: [`docs/agents/curation-authority-map.md`](../../../docs/agents/curation-authority-map.md).
This skill does not restate them. Cite the map section when you explain a score. If the
map and `src/gaia_cli/trustMagnitude.py` ever disagree, the engine wins and the map is
the bug.

> **fusion-recipe scores 0 TM.** Structure is reported by the informational **Fusion
> Score** (META.md §2.1e). Over `N` distinct non-variant nodes in the resolved structural
> closure: `FS = 0` when `N = 0`; `FS = 20 × N` when `1 ≤ N ≤ 10`;
> `FS = 200 + 20 × √(N − 10)` when `N > 10`. Fusion Score gates no star, rank or Trust
> Grade. When you report one, also state that
> published TM fell for suites and fusions because this row went to 0 TM. **No evidence
> row, star count, or rank was edited** (META.md §2.1e).

### Common dead-row causes (engine-verified, map §1)

- `social-signal` with views < 1000 → 0.
- `github-stars-own` with stars ≤ 10 → 0. Only one `github-stars-own` row scores (plateau max 1).
- `benchmark-result` that is not catalog-eligible (unknown or rejected `benchmarkId`, or a non-scoring lane) → excluded.
- A second row of the **same** type at the same canonical URL → collapsed. Dedup is within type: `github-stars-own` + `repo-own` at one URL **both** count.
- Rows beyond a stackable type's plateau max-rows → 0.
- Shared suite-root repository evidence on a suite component → capped at 50.0 TM per component.
- A verifier-attestation from a deranked verifier → excluded (null).
- `skillCountInRepo` never reduces a score. There is no repository-count divisor.
