# Verifier Signoffs — Benchmark Attestations

**Sprint D W2b (#905)** — this directory holds machine-checkable Verifier
attestations for benchmark scores. It is the alternative promotion path when
CI reproduction is not viable (private test sets, human graders, hardware
lock-in): a 4★+ Verifier co-signs the score and stamps their handle on the
evidence row.

## Layout

```
docs/verifier-signoffs/
├── README.md
└── YYYY-MM/
    └── <benchmark>-<contributor>-<slug>.md
```

The `YYYY-MM` bucket is the attestation month (calendar UTC). One file per
(benchmark, skill, run) tuple — a rerun produces a new file.

## File format

Free-form markdown that **must** open with a YAML frontmatter block. Every
key is validated by `scripts/check_verifier_signoffs.py --check-attestations`
(wired into the main sign-off check).

```markdown
---
verifier: some-github-handle
skill: contributor/slug
benchmark: humaneval@v1.0
score: 0.84
datasetHash: <64-char lowercase hex sha256>
attestedAt: 2026-07-05T18:00:00Z
---

# Verifier attestation — HumanEval, contributor/slug, 0.84 pass@1

Free-form justification: which run, why the harness output should be
trusted, any hardware/model context the reader needs. Reviewers use this
text; CI ignores it. The frontmatter is the authorization surface.
```

## Invariants (CI-enforced)

* `verifier` MUST resolve to a 4★+ named-skill contributor in
  `registry/named-skills.json`. An unknown handle fails CI.
* `skill` MUST match an existing `contributor/slug` in the registry.
* `benchmark` MUST be versioned as `<name>@<version>` (e.g. `humaneval@v1.0`).
* `datasetHash` MUST be a 64-char lowercase hex SHA-256.
* `attestedAt` MUST be ISO 8601 with timezone.
* `score` MUST be numeric.

If ANY attestation file fails these checks, the CI job fails — even if the
PR otherwise has enough approvals.

## When to use verifier attestation vs CI reproduction

| Path                     | When                                                                 |
| ------------------------ | -------------------------------------------------------------------- |
| `provenance: ci-reproduced` | Public dataset, deterministic harness, runnable in GitHub Actions |
| `provenance: verifier-attested` | Private/gated test set, human grading, hardware lock-in       |

Both are valid. Both contribute to Trust Magnitude at the same weight. But
verifier-attested rows are strictly rarer — CI reproduction is the default
because it does not require a human's time.

## Cadence

New month → new bucket. Do not backdate frontmatter `attestedAt` to shove a
signoff into a prior month's bucket. The directory name is filesystem
convenience; the timestamp is authoritative.
