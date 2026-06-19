# G7 RFC v3 — Ratification Delta (2026-06-20)

This document ratifies the v3 amendments to the G7 Trust Taxonomy RFC, building on the v2 (ratified 2026-06-18) and the 2026-06-17 delta (9→6 active apex predicates). Issue #749 tracked the ratification queue; this document closes it.

## Status

- **v1**: Original 9-predicate apex gate, `trustNumber` aggregate (deprecated 2026-06-15).
- **v2**: 10 evidence types, sqrt-softening fusion, dual-axis Type+Grade. Ratified 2026-06-16; recalibrated 2026-06-18.
- **2026-06-17 delta**: Apex 9→6 active predicates. `crossOrgVerifierGte2` and `systemWideCapRespected` moved to feature flags. Ratified 2026-06-17.
- **v3 (this document)**: Depth-2 amendment, `apex_pr_signed` enum, `sourceStartedAt` formalization. **Ratified 2026-06-20.**

## Amendment 1 — §11.12.3 Depth-2 walker now permits suiteComponent overlap with depth-1

### Original (v2)
> The transitive walk MUST visit at least one node at depth 2 that is NOT also a direct (depth-1) component of the apex. Formal predicate: `∃ s ∈ closure(apex) : minDepth(s, apex) = 2`.

### v3 amendment
The "not also a direct component" exclusion is **lifted**. The depth-2 walker now visits all nodes reachable through nesting, including those that ALSO appear as direct components of the apex (with cycle-self guard retained). Formal predicate becomes:

```
∃ s ∈ closure(apex) : ∃ path apex → c → s such that c ∈ suiteComponents(apex) AND s ∈ suiteComponents(c) AND s ≠ apex
```

### Rationale

The strict-no-overlap rule in v2 was designed to prevent the `mattpocock/skills` failure mode where every grandchild was also a direct child (cosmetic nesting under §10.11 dedup). In practice, the rule produced false negatives: legitimate suites like `garrytan/gstack` have direct components that are themselves suites containing skills also exposed at the top level — this is **good design** (consumers see top-level skills immediately, with the suite breakdown for those who want it), not gaming.

Marco's call (mid-I12 dispatch, 2026-06-20): "Depth 2 will include it even if it is included in their own skill suite." Cycle-self guard retained: an apex cannot count itself in its own depth-2 walk.

### Impact

- `garrytan/gstack`, `ruvnet/ruflo`, `mattpocock/skills`, `obra/superpowers` all now pass §11.12.3 (was previously failing for `mattpocock/skills`).
- Implementation: `src/gaia_cli/trustMagnitude.py::checkDepth2OnlyReachableGte1` already includes the relaxed walker as of I12 commit `a734beca`.

## Amendment 2 — `apex_pr_signed` timeline action ratified

### Original (v2)
The §11.12.8 PR-gated promotion predicate had no canonical timeline action; agents were instructed to use `verified` as a fallback (see #749 for the gap).

### v3 ratification
The timeline action enum gains `apex_pr_signed`. Both:

- `registry/schema/skill.schema.json`
- `registry/schema/namedSkill.schema.json`
- `src/gaia_cli/main.py` (`gaia dev timeline --action` choices)

now accept `apex_pr_signed`.

### Semantics

| Field | Value |
|---|---|
| `action` | `apex_pr_signed` |
| `actor` | The verifier signing the apex-promotion PR (typically the registry maintainer). |
| `details` | Free-form note; conventionally `"Apex Promotion PR signed by <handle> on <YYYY-MM-DD> for <skillId>"`. |
| Effect | Sets `frontmatter.apexGateStatus.apexPromotionPrSigned: true`, `apexPromotionPrSignedBy: <handle>`, `apexPromotionPrSignedAt: <ISO date>` on the named skill. |
| Reverses | `demote` (no separate "unsign" action; demotion implicitly clears the signed flag during recalibration). |

### Backfill

I12 (2026-06-20) signed gstack/ruflo/skills/superpowers via direct frontmatter edit (CLI gap). With v3 ratified, the four backfilled stamps remain valid; no re-emit required. Future signs use `gaia dev timeline <skill> --user mbtiongson1 --action apex_pr_signed --notes "..."`.

## Amendment 3 — `sourceStartedAt` formalized

### Original (v2)
§11.12.7 tenure check referenced "earliest evidence row's age" but did not specify the field. Most evidence rows had no explicit start date, so the predicate fell back to the row's added-to-registry timestamp — a poor proxy that resets when evidence is re-added or migrated.

### v3 ratification

Each evidence row may carry a `sourceStartedAt: YYYY-MM-DD` field. The §11.12.7 tenure predicate uses:

```
tenureDays = (today - min({row.sourceStartedAt | row in evidence}))
```

If no row has `sourceStartedAt`, fall back to the row's `addedAt` (existing field). Once any row carries `sourceStartedAt`, the fallback is no longer used — set the field for at least one row to anchor tenure.

Populated via `gaia dev evidence --source-started-at YYYY-MM-DD <skill> ...` (added I12 commit `7e0755a0`).

### Backfill plan

I11's curation pass (2026-06-20) populated `sourceStartedAt` on the new evidence rows it added (~58 rows). The historical evidence rows on the top-4 S-grade skills still need backfill — tracked as a fast-follow under issue #746 (apex gate origin curation).

## Amendment 4 — Recap of feature-flagged predicates

For clarity (no change from 2026-06-17 delta):

- **§11.12.5 cross-org verifier ≥ 2** — flag: `crossOrgVerifierGte2`. Awaits Verifier-Signoff sub-system. Default: off.
- **§11.12.6 system-wide cap of 5 concurrent 6★** — flag: `systemWideCapRespected`. Default: off (system-wide count enforced advisorily).

These remain feature-flagged in v3 and are not enforced.

## Schema migration

No data migration required. Schemas are extended (new enum value), not changed:

```
+ "apex_pr_signed"
```

Existing `evidence.sourceStartedAt` field is opt-in; no NULL migration needed.

## Effective date

**2026-06-20** — applies on merge of `dev/phase-1.5-inspection` to `main`.

## Closes

- Issue #749 (RFC v3 ratification queue)
- Phase 1.5 RFC follow-ups documented in `founder/MEMORY.md` Session 15 snapshot.

---

*Authored: 2026-06-20, end of Phase 1.5 consolidation. Ratifier: mbtiongson1.*
