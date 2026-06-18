# June 2026 Trust Regrade (G7 Cutover)

> Migration: `scripts/migrateTrustMagnitude.py`
> Date: 2026-06-18 (Phase 1.5 I3)
> Skills processed: 235 named skills across `registry/named/`

This is the cutover stamp for the **G7 Trust Magnitude** model (Phase 1.5 I1
schema + I2 compute pipeline). The migration script ran the I2 trust pipeline
over every named skill and stamped four new fields per file:
`trustMagnitude`, `overallTrustGrade`, `apexGateStatus`, and
`trustMagnitudeInputHash`. A `migrate_trust_magnitude` event was appended to
each skill's timeline.

## 1. Apex Demotions

The 6-predicate Apex Gate (see § 5) was applied to the two skills carrying
6★ apex status pre-G7. Both fail every active predicate at cutover.

### `mattpocock/skills`

| Predicate                     | Result |
|-------------------------------|--------|
| `aGradedOriginsGte5`          | FAIL   |
| `sourceTenureDaysGte180AorS`  | FAIL   |
| `directNestedSuiteGte1`       | FAIL   |
| `depth2OnlyReachableGte1`     | FAIL   |
| `overallGradeS`               | FAIL   |
| `apexPromotionPrSigned`       | FAIL   |
| `crossOrgVerifier`            | OFF    |
| `systemWideCap`               | OFF    |

`isApex = false`. TM = 0.0. Grade = `ungraded`.

### `ruvnet/ruflo`

| Predicate                     | Result |
|-------------------------------|--------|
| `aGradedOriginsGte5`          | FAIL   |
| `sourceTenureDaysGte180AorS`  | FAIL   |
| `directNestedSuiteGte1`       | FAIL   |
| `depth2OnlyReachableGte1`     | FAIL   |
| `overallGradeS`               | FAIL   |
| `apexPromotionPrSigned`       | FAIL   |
| `crossOrgVerifier`            | OFF    |
| `systemWideCap`               | OFF    |

`isApex = false`. TM = 0.0. Grade = `ungraded`.

### Summary

| Metric                                | Pre-G7 | Post-G7 |
|---------------------------------------|--------|---------|
| System-wide effective apex skills (6★)| 2      | 0       |
| Apex re-application bar               | n/a    | All 6 active predicates must pass |

Note: the I3 migration **does not** mutate the `level` field on either
record; level demotion is I5's scope. What changes here is the *effective*
trust posture (`apexGateStatus.isApex`), which downstream consumers (graph,
explorer, badges) will use as the source of truth post-G7.

## 2. Aggregate Drift

Trust Magnitude distribution after migration (all 235 skills):

| Bucket   | Count |
|----------|-------|
| TM = 0.0 | 235   |
| 0.0 < TM < 1.0 | 0 |
| 1.0 ≤ TM < 5.0 | 0 |
| TM ≥ 5.0 | 0     |

**Top 10 TM drops:** every skill in the registry transitioned from `null`
(no TM field) to `0.0`. There is no positive-magnitude skill at this
cutover — the I2 pipeline requires graded rows of the new 10-type evidence
taxonomy (Phase 1.5 I1), and no skill yet carries one. Every existing
evidence row pre-dates the new taxonomy and contributes 0 to the effective
pool.

**Top 10 TM gains:** none. No skill increased from `null`.

Implication: the entire registry now sits at the `ungraded` trust floor
until evidence is upgraded to the 10-type taxonomy with explicit grades.

## 3. Grade Migration

| Transition          | Count |
|---------------------|-------|
| `ungraded → ungraded` | 235 |

Pre-G7 there was no `overallTrustGrade` field; every skill is `ungraded`
post-migration as well, because `computeOverallTrustGradeFromSkill` returns
`ungraded` when no graded evidence rows survive `enforceAntiAutoMint` and
`_dedupeSameSource`. Once contributors begin landing typed evidence, this
table will populate with `ungraded → C/B/A/S` transitions on subsequent
recompute passes (the input-hash idempotency guard ensures only changed
skills are touched).

## 4. Phantom-Row Removals

Phantom-row removals at cutover: **0**.

Anti-auto-mint (`enforceAntiAutoMint`) strips evidence rows that look
auto-minted (e.g. a `community-verified` row with no `eventClass`, or a
contradictory `falsified` shadow on the same source). The legacy registry
has no rows in those shapes — every existing evidence row is either the
old free-form schema or already typed correctly. No skills had rows
silently stripped.

| skillId | evidenceUrl | evidenceType |
|---------|-------------|--------------|
| _(none)_ | _(none)_ | _(none)_ |

## 5. Apex-Gate Methodology

The 6-predicate Apex Gate (`passesApexGate` in
`src/gaia_cli/trustMagnitude.py:1048`) is the single gate that decides
*effective* 6★ apex status post-G7. All six **active** predicates must
return `True` for `isApex` to be `True`. Predicates returning `None` are
feature-flagged OFF and skipped.

### Active predicates (6)

1. **`aGradedOriginsGte5`** — at least 5 origin contributors of the skill
   (or its suite components, walked transitively) must hold an A or S
   grade across the registry. Prevents single-author apex.
2. **`sourceTenureDaysGte180AorS`** — at least one A or S graded evidence
   row must have `sourceStartedAt` ≥ 180 days before the apex check.
   Prevents fresh-source apex.
3. **`directNestedSuiteGte1`** — the skill must `suiteComponents` at least
   one other suite (depth ≥ 1 nested suite). Prevents flat-suite apex.
4. **`depth2OnlyReachableGte1`** — at least one component must be reachable
   only via depth ≥ 2 nesting. Prevents shallow nesting apex.
5. **`overallGradeS`** — `computeOverallTrustGradeFromSkill` must return
   `"S"`. Prevents apex without top-tier composite trust.
6. **`apexPromotionPrSigned`** — the skill's record must include a signed
   apex-promotion PR reference (a `apex_promotion_pr` event in the
   timeline with `signed: true`). Prevents apex without governance trail.

### Feature-flagged OFF until 2026-Q4

- **`crossOrgVerifier`** — at least one verifier from a different
  organization signs off. Pending the cross-org verifier registry.
- **`systemWideCap`** — caps total system-wide apex count at N. Pending
  the system-wide cap policy.

## 6. Provisional Grades

Provisional skills (A/S graded row missing `sourceStartedAt`): **0**.

Because no skill yet carries an A or S graded row of the new taxonomy, the
provisional flag is unused at this cutover. Once contributors land A/S
evidence, any row missing `sourceStartedAt` will set
`frontmatter.provisional: true` with a 6-month grace period from the
migration date (2026-06-18 → 2026-12-18).

## 7. Calibration Table

Three exemplar skills with full before/after stamp:

| Skill | TM (pre/post) | Grade (pre/post) | Apex predicates passed (post) |
|-------|---------------|------------------|------------------------------|
| `mattpocock/skills` | `null` / `0.0` | `ungraded` / `ungraded` | 0/6 (was 6★ pre-G7) |
| `ruvnet/ruflo`      | `null` / `0.0` | `ungraded` / `ungraded` | 0/6 (was 6★ pre-G7) |
| `anthropic/skill-creator` | `null` / `0.0` | `ungraded` / `ungraded` | 0/6 |

All three skills converge on the same `ungraded` floor at cutover because
no skill in the registry has a single graded row of the new 10-type
evidence taxonomy. Each skill's `trustMagnitudeInputHash` is now stamped,
so re-running the migration over an unchanged record is a no-op
(idempotency confirmed — second-run `git diff --stat` is empty).

## 8. Migration Shape

```
named skill .md files (registry/named/**/*.md)
      │
      ▼
enforceAntiAutoMint() → strips phantom evidence rows
      │
      ▼
computeTrustMagnitude() → TM float (effective pool walk, anti-auto-mint,
                          same-source dedup, optional fusion-recipe row,
                          per-row scores × inherit multipliers)
      │
      ▼
computeOverallTrustGradeFromSkill() → S / A / B / C / ungraded
      │
      ▼
passesApexGate() → per-predicate pass / fail / None dict
      │
      ▼
write back to frontmatter:
  trustMagnitude, overallTrustGrade, apexGateStatus,
  trustMagnitudeInputHash, provisional?, verification.firstEvidenceAt?
      │
      ▼
append migrate_trust_magnitude timeline event
      │
      ▼
registry/named-skills.json regenerated (scripts/generateNamedIndex.py)
```

### Idempotency

The script computes a stable `trustMagnitudeInputHash` over
`(skillId, sorted(url|type|grade) per evidence row)`. On re-run, any skill
whose hash matches the stamped value is skipped before any computation.
Verified: second run reports `processed=0, skipped=235` and `git diff
--stat` is empty.

### Re-running

```bash
GAIA_OPERATOR_OVERRIDE=1 python scripts/migrateTrustMagnitude.py
python scripts/generateNamedIndex.py
```

Re-runs are safe and only touch skills whose evidence has changed.
