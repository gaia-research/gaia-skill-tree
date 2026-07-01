---
name: ev-collection
description: >
  Phase 1 of the Gaia evidence verification pipeline. Use this skill whenever
  you need to gather, consolidate, or refresh raw evidence for named skills in
  the Gaia registry. Trigger phrases: "collect evidence", "populate the data
  lake", "gather sources", "run ev-collection", "Phase 1", "compile the
  evidence index", "refresh the unified lake", "aggregate skill evidence",
  "build the evidence database". Also invoke as the first step before running
  ev-star-verification, ev-adversarial-audit, or ev-link-validation — nothing
  downstream is meaningful without a fresh, compiled index. Covers GitHub repo
  links, stargazer signals, YouTube showcases, arXiv papers, peer reviews,
  benchmark results, blog/newsletter posts, and self-attestation artifacts.
---

# Evidence Collection (ev-collection)

Phase 1 of the evidence verification pipeline. This skill compiles raw proof
vectors from all active collector channels into the master unified index
(`evidence/unified_evidence_lake.md`) and the per-tier files
(`evidence/tier_1.md` through `evidence/tier_6.md`). Everything downstream
— star verification, adversarial auditing, link validation — reads from this
index, so it must be current before any other phase runs.

> **Pipeline position:** Run this before `/ev-star-verification` (Phase 2),
> `/ev-adversarial-audit` (Phase 3), and `/ev-link-validation` (Phase 4).

---

## Evidence Channels

Evidence is drawn from four primary channels, mapped to the 10 canonical
evidence types the registry recognises:

| Channel | Canonical types covered |
|---|---|
| GitHub repos and star counts | `github-stars-own`, `repo-own`, `proxy-containment` |
| Academic publications | `arxiv`, `benchmark-result`, `peer-review` |
| Social / community content | `social-signal`, `self-attestation`, `verifier-attestation` |
| Workflow composition rules | `fusion-recipe` |

Source files for each channel live under `evidence/collectors/`:

- `technical/` — academic papers, benchmark results, peer reviews / audits
- `social/` — blog posts, newsletters, YouTube showcases
- `verification/` — chronological link-check logs

---

## Workflow

### Step 1 — Read active collector files

Scan the four collector subdirectories and pull every evidence entry that has
not yet been flagged as injected. An entry is considered already imported when
it carries a trailing comment of the form:

```
<!-- injected: YYYY-MM-DD | skillId: ... | type: ... | layer: ... -->
```

Skip flagged rows; they are already in the registry.

### Step 2 — Compile the unified index

Run the compiler script to merge all collector output into the master database
and regenerate the per-tier files:

```bash
.venv/bin/python evidence/scripts/compile_data_lake.py
```

The script writes:
- `evidence/unified_evidence_lake.md` — master consolidated index
- `evidence/tier_1.md` through `evidence/tier_6.md` — tier-partitioned files

### Step 3 — Validate layer routing before finalising

Before treating the index as ready, confirm each entry is routed to the correct
layer. The distinction matters because inheritance multipliers differ:

- `layer: named` — evidence that references **this specific named skill**
  (contributor, repo, or demonstration of the named implementation)
- `layer: generic` — evidence that supports the **underlying technique**
  (papers, benchmarks, community posts about the concept in general)

Routing errors cause Trust Magnitude scores to be computed against the wrong
multiplier table. Wrong layer = wrong grade.

### Step 4 — Flag injected rows

After a successful compile, mark each evidence row in the source collector
files with the injection comment so future passes skip them:

```
<!-- injected: YYYY-MM-DD | skillId: <id> | type: <type> | layer: <layer> -->
```

---

## Key Curation Rules

These exist to prevent silent downstream failures — not arbitrary style:

- **Use `blob/` not `tree/`** for all GitHub links. The installer at
  `src/gaia_cli/install.py` only parses `blob/<branch>/<path>` URLs. A `tree/`
  link makes the skill uninstallable without any visible error.
- **Suite components need subpaths.** A suite link pointing to the bare repo
  root installs a symlink with no `SKILL.md` at the top level and silently
  breaks discovery.
- **No evaluative noise.** Strip subjective language ("elite", "high-quality",
  "verified live") from descriptions. Evidence entries must be factual so
  the adversarial audit phase does not immediately flag them for removal.
- **`github-stars-own` dedup.** If a skill already has a `repo-own` entry at
  URL `X`, adding `github-stars-own` at the same URL will be deduped — only
  the higher-scoring entry counts. Use the specific `SKILL.md` blob URL for
  `github-stars-own` to avoid the collision.

---

## Output

On completion, the following files are current and ready for Phase 2:

- `evidence/unified_evidence_lake.md`
- `evidence/tier_1.md` — `evidence/tier_6.md`
- Collector files flagged with injection comments
