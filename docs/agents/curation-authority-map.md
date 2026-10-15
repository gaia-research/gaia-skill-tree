# Curation Authority Map — Trust Magnitude, effective evidence, gates, appraisal scope

This file is the one place where agent skills and curation docs get Trust Magnitude (TM)
facts. Skills link here and do **not** restate formulas. Each fact below names the code or
policy that owns it. When this map and an owner disagree, **the owner wins**, and this
file is wrong. `tests/test_curation_authority_map.py` checks the tables below against the
live engine and fails on any disagreement. It also fails if a mirrored trust skill brings
back a claim this map has retired.

| Concern | Owner (canonical) | Notes |
|---|---|---|
| TM computation, weights, caps, dedup, plateau, inheritance | `src/gaia_cli/trustMagnitude.py` | `computeTrustMagnitude`, `_scoredEvidenceRows`, `_effectivePool`, `TYPE_WEIGHTS`, `TYPE_CAPS`, `EVIDENCE_TYPE_LAYER_CONTRACT` |
| Benchmark lanes and catalog eligibility | `src/gaia_cli/benchmarkCatalog.py` | `isBenchmarkScoringEligible`, `benchmarkFinalMagnitude` |
| Star levels and their TM gates | `META.md` §1.1, §2, §4 | Enforced in `src/gaia_cli/promotion.py` (`_UNIQUE_GATE_BY_LEVEL`) and the grade-ceiling clamp in `scripts/generateNamedIndex.py` (`GRADE_MAX_STARS`) |
| Review process, L4 human approval | `GOVERNANCE.md` | |
| Mutation surface | `gaia dev` verbs and their playbooks (`.agents/skills/dev-calibrate/`) | No hand edits (CLAUDE.md § Programmatic-First Policy) |

## 1. Per-type scoring (engine constants)

`artifact_score = min(raw magnitude, cap) × weight × freshness [× creator × engagement for social-signal] × inherit multiplier (inherited rows only) × plateau factor`.
TM is the sum of artifact scores. Social-signal is hard-capped at 80 in total.

The probe column holds one synthetic row scored on its own, with no generic context. The
values are checked live.

| Evidence Type | Weight | Cap | Inherit multiplier | Raw magnitude | Probe row | Probe TM |
|---|---|---|---|---|---|---|
| github-stars-own | 1.0 | 175.0 | pinned-named | `min(175, 35 × log10(stars/10))`, 0 when stars ≤ 10 | `{"stars": 1000}` | 70.0 |
| repo-own | 0.6 | 60.0 | pinned-named | `commits/200 + contributors² × 2` | `{"commits": 816, "contributors": 2}` | 7.248 |
| arxiv | 1.0 | 100.0 | 0.70 | `citations / 5` | `{"citations": 100}` | 20.0 |
| peer-review | 1.2 | none | 0.30 | `25 × reviewers` | `{"reviewers": 3}` | 90.0 |
| social-signal | 1.0 | 80.0 | 0.35 | `log10(views) × 8`, 0 when views < 1000 | `{"views": 10000}` | 32.0 |
| self-attestation | 0.5 | 10.0 | pinned-named | `10` | `{}` | 5.0 |
| proxy-containment | 1.0 | 160.0 | 0.25 | `externalStars/1000 × 0.8`, 0 when < 10000 | `{"externalStars": 20000}` | 16.0 |
| verifier-attestation | 1.5 | none | pinned-named | `30 × verifiers`; deranked verifier → excluded (null) | `{"verifiers": 1}` | 45.0 |
| npm-downloads | 0.9 | 150.0 | pinned-named | `min(150, 30 × log10(downloads/100))`, 0 when ≤ 100 | `{"downloads": 10000}` | 54.0 |
| engagement | 0.7 | 60.0 | 0.25 | `min(60, 15 × log10(likes + 3 × comments))`, 0 when ≤ 1 | `{"likes": 100}` | 21.0 |
| benchmark-result | 1.4 | 100.0 | 0.15 | catalog-gated: percentile or normalized score × lane (verified 2×, reported 1×, else 0) | catalog-gated | n/a |
| fusion-recipe | 0.0 | none | pinned-named | structural only, always 0 TM (Fusion Score is separate and informational) | `{"gradedOriginCount": 5}` | 0.0 |

Rules the engine applies and skills must not contradict:

- **Same-source dedup is within type.** `_dedupeSameSource` keys rows on `(evidence type, canonical URL)`. A `github-stars-own` row and a `repo-own` row at the same URL are different keys, and **both count**. Two rows of the *same* type at the same URL collapse, and the higher one wins.
- **There is no repository-count divisor.** `skillCountInRepo` is recorded provenance and part of `computeTrustMagnitudeInputHash`. It never divides a score; the old repository-count discount retired with the #1705 logarithmic curve.
- **Suite-component repository cap.** A component's shared suite-root `github-stars-own` + `repo-own` contributions are bounded to 50.0 TM together (`SUITE_COMPONENT_REPOSITORY_CAP`).
- **Plateau.** A stackable type scores its rows in descending order, at factors such as 1.0 / 0.5 / 0.25. Rows past the type's max-row count score 0 (`_PLATEAU_CONFIG`).
- **Freshness** decays only `benchmark-result`, `social-signal` and `peer-review` with `lastVerified`.

## 2. Effective evidence and appraisal scope

A named skill's TM is computed over its **effective pool**: its own rows plus the eligible
generic-layer rows of its `genericSkillRef` node (`_effectivePool`). Flexible types are
inherited at their multiplier. Pinned-named types are never inherited.

Every appraisal states its scope and generic-resolution status:

| Scope | What was summed | Generic resolution | May be called final? |
|---|---|---|---|
| `named-own/proposal` | only the proposal's own rows (e.g. `trust_appraise.py --repo`) | `not evaluated` | **No.** It is a partial total, never the effective named TM |
| `generic` | a generic node's own rows | `not applicable` | Yes, for the generic node |
| `effective named` | own rows plus resolved generic inheritance | `resolved` | Yes |
| `named-own` (generic ref unresolved) | own rows; the `genericSkillRef` did not resolve | `not evaluated` | **No** |

Missing generic context reads **"not evaluated"**. Never write "inheritance disallowed". Later
generic academic backing still counts when it is inherited, even though it does not prove
implementation usage.

Worked examples (synthetic and offline; checked live):

| Scenario | TM |
|---|---|
| named `example/tool`, own `repo-own` (commits 816, contributors 2), scope `named-own` | 7.248 |
| same skill, generic `arxiv` (citations 100, layer generic) resolved, scope `effective named` | 21.248 |
| `github-stars-own` (stars 1000) and `repo-own` at the same repository URL (cross-type) | 77.248 |
| `github-stars-own` (stars 1000) with `skillCountInRepo` 50 | 70.0 |

## 3. Grades and star gates

| Overall Trust Grade | TM floor | Extra condition | Max star level (clamp) |
|---|---|---|---|
| S | 250.0 | ≥ 3 distinct scoring types and an eligible independent witness (`benchmark-result`, `verifier-attestation`, or `peer-review` graded ≥ A) | 6 |
| A | 100.0 | — | 4 |
| B | 50.0 | — | 3 |
| C | 20.0 | — | 2 |
| ungraded | below 20.0 | — | 1 |

- **4★ strictly requires grade A (TM ≥ 100).** B is not enough at 4★, even "in practice". It caps a skill at 3★ (META.md §1.1). 5★ requires S (TM ≥ 250). 6★ adds the Apex gate (Suite, §4.3) or the Unique Impossible gate (Unique, §4.4).
- TM is the only numeric promotion gate; there is no per-star evidence-class floor. The Star Bar (verified `links.github` blob at 3★+, live non-seed evidence at 4★+) is checked separately in META.md §2.

## 4. Persistence: computed, not hand-written

- TM and the Overall Trust Grade are **computed** by the engine.
- `trustMagnitude`, `overallTrustGrade` and `trustMagnitudeInputHash` may appear in named-skill frontmatter. They are a **hash-signed cache** written only by `gaia dev calibrate-trust-magnitude` (playbook: `.agents/skills/dev-calibrate/`). `scripts/generateNamedIndex.py` trusts the cache only when the stored hash matches the current inputs; otherwise it recomputes.
- Never hand-edit those fields, and never add or recommend a separate write-back helper. A stale cache is refreshed through the CLI verb.
- Raw inputs (`stars`, `commits`, `contributors`, `citations`, `views`, `reviewers`, `percentile`, …) are the persisted evidence inventory.

## 5. Metric provenance and claim status

- **`repo-own` measures the repository.** It uses repository-wide metrics at the repository root URL. Installability (a verified `links.github` skill-file `blob/` URL) is a separate fact. Path-specific history may be added as context, and it never silently replaces repository-wide metrics.
- **A contributor-contribution sum is not a unique-commit count.** GitHub's `repos/{repo}/contributors` returns per-contributor `contributions` on the default branch. Their sum is one measurement; unique reachable commits on a ref are another. A report that feeds the sum into the engine's `repo-own.commits` input labels it as `contributorContributionSum` with status `inferred`, and never as plain "commits".
- Every reported metric or draft assertion carries a status:

| Status | Meaning | Required provenance |
|---|---|---|
| `verified` | observed in this run by a reproducible method | `method` and `repro` (command or fixture) plus collection time |
| `reported` | stated by a source that was not re-observed | `source` |
| `inferred` | derived from another measurement (e.g. contribution sum used as a commit input) | `method` naming the derivation |
| `unknown` | none of the above | — |

A claim without `repro` provenance cannot be exported as `verified`; export downgrades it
(`gaia_cli.curationCheckpoint.exportClaims`).

## 6. Resumed curation: current-state checkpoint

A resumed curation run reads a compact checkpoint, not raw history:
- active blockers
- resolved blockers, each with its resolution evidence
- source revisions

`gaia_cli.curationCheckpoint.activeBlockers` applies the rule:
- An open blocker stays active.
- A resolved blocker that has resolution evidence stays resolved, unless a **fresh failing check** with the same `checkId` re-raises it. It then comes back as `regressed`, carrying the fresh evidence.
- A resolved blocker without resolution evidence is not trusted and stays active.

## Banned claims (retired; the agreement test rejects them)

- "`github-stars-own` and `repo-own` at the same URL are deduped."
- "`skill_count_in_repo` / `skillCountInRepo` divides" a score; "mothership discount".
- "4★ may hold at B / TM ≥ 50", or "A is merely the norm" for 4★.
- Any helper that writes `trustMagnitude` / `overallTrustGrade` outside `gaia dev calibrate-trust-magnitude`.
- An own-only proposal total presented as final effective named TM.
