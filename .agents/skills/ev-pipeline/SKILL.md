---
name: ev-pipeline
description: >
  Top-level orchestrator for the Gaia Skill Tree evidence verification pipeline. Run this when you want to do a full evidence pass — collecting raw sources, verifying live GitHub star counts, adversarially auditing for quality/formatting issues, and checking that every URL is reachable — all in one coordinated sequence. Trigger phrases: "run the evidence pipeline", "full evidence pass", "verify evidence", "evidence verification pipeline", "run ev-pipeline", "check all evidence", "audit the data lake", "evidence quality sweep", "refresh evidence", "validate evidence sources". Also aliased as /evidence-verification-pipeline. Use the individual sub-skills (ev-collection, ev-star-verification, ev-adversarial-audit, ev-link-validation) only when you need to re-run one phase in isolation; for end-to-end work, always start here.
---

# Evidence Verification Pipeline (ev-pipeline)

Orchestrates the four evidence verification phases that take the raw data lake from "collected" to "audited and link-checked." Run this before ingesting any evidence into the canonical registry — it is a pre-flight step, not a post-flight one.

> **Scope:** This pipeline operates on the evidence data lake (`evidence/`) only. It does not touch `registry/nodes/` or `registry/named/`. Think of it as quality-gating the raw material before promotion.

```mermaid
graph TD
    Phase0[Phase 0: ev-discovery (skippable)] -->|Append discovered rows| A
    A[Phase 1: ev-collection] -->|Compile Index| B[Phase 2: ev-star-verification]
    B -->|Partition Tiers| C[Phase 3: ev-adversarial-audit]
    C -->|Audit Contexts| D[Phase 4: ev-link-validation]
    D -->|Validate Statuses| E[Master Source Report & HTML Update]
```

> **Continuous additive loop, no green gate.** Phase 0 only *appends* freshly
> discovered rows to the collector channels; the four verification phases then
> process them like any other evidence. There is no pass/fail wall — the only
> human gate is L4 at ingestion.

---

## Why this order matters

Each phase produces output that the next phase consumes. Running them out of order corrupts the audit trail:

- (Optional) Discovery appends new Stage-2 rows to the collectors before collection compiles them.
- Collection builds the index that star-verification partitions against.
- Star-verification assigns tier labels that adversarial reviewers use to prioritise their scan.
- Adversarial audit flags broken URLs that link-validation then formally checks.
- Link-validation closes the loop with live HTTP status codes, which feed the final report.

---

## Phase 0 — Evidence Discovery (`ev-discovery`) — skippable

Searches the web (via the `firecrawl` skill) for **new** Stage-2 evidence
(`benchmark-result`, `arxiv`, `peer-review`, richer `social-signal`) and appends
the discovered sources as fresh rows into `evidence/collectors/technical|social/`.
It runs **only on declared need** — a promotion candidate, or a skill that
`/gaia-meta-sweep` flags as under-evidenced — and is otherwise **skipped** to
keep the common ingest path cheap. It appends unmarked rows so Phase 1 picks
them up; it never gates the pipeline. Requires `FIRECRAWL_API_KEY` and skips
gracefully if unset.

```
/ev-discovery
```

---

## Phase 1 — Evidence Collection (`ev-collection`)

Aggregates raw sources from `evidence/collectors/` and compiles the master `unified_evidence_lake.md` index. This is the foundation — nothing downstream runs correctly without an up-to-date index.

```
/ev-collection
```

---

## Phase 2 — Live Star Verification (`ev-star-verification`)

Queries the GitHub API for stargazer counts, cross-references them against `registry/named/` Markdown files, and writes tiered partition files under `evidence/`. Star counts determine Trust Magnitude scores, so stale counts produce inaccurate rankings.

```
/ev-star-verification
```

---

## Phase 3 — Adversarial Audit (`ev-adversarial-audit`)

Fans out parallel reviewer agents that scan the data lake for evaluative noise, `tree/` vs `blob/` URL errors, and proxy/source mismatches. Adversarial review catches systematic problems that a single-pass scan misses — two reviewers arguing about the same entry surfaces edge cases.

```
/ev-adversarial-audit
```

---

## Phase 4 — Link Validation (`ev-link-validation`)

Uses Firecrawl to scrape every unique URL in the data lake and confirm a 200 OK response. Dead links degrade TM scores and mislead registry consumers; this phase makes bad links visible before they get promoted.

```
/ev-link-validation
```

---

## Post-Run Outputs

After all four phases complete, save these artifacts in order:

1. **Validation report** — written automatically by `ev-link-validation` to `evidence/collectors/verification/firecrawl_validation_report_YYYY_MM_DD.md`
2. **Master source report** — accumulated across phases into `evidence/source_report_YYYY_MM_DD.md` (star-verification writes the base; adversarial-audit and link-validation append their sections)
3. **Visual dashboard stats patch** — run the deterministic script:
   ```bash
   python3 scripts/ev_stats_patch.py \
     --date YYYY-MM-DD \
     --skills-processed N \
     --new-rows N \
     --live-urls N \
     --dead-urls N
   ```
   This patches cumulative stat-cards and appends a run-history row to `evidence/verification_process.html`. Do not hand-edit the HTML stats block.
4. **Ingestion handoff** — for L4-approved intake, pass the reviewed manifest to `/gaia-ingest-batch`.

## Additive loop — no green gate (RFC2 §3.5)

Ingest is **never gated by "green."** The ev-pipeline is a **continuous additive
loop**: it keeps aggregating new evidence rows (appending to the per-type
partitions) and discarding rejected ones — evidence is additive, not pass/fail.
New rows arrive two ways: Stage 1 writes cheap minimum-effort rows
(`github-stars-own` + `repo-own` + `self-attestation`) at curation, and a
skippable Firecrawl **Phase 0** discovers richer rows (`benchmark-result`,
`arxiv`, `peer-review`, richer `social-signal`) on declared need.

There is **no structured GREEN wall** gating ingest. The **only human gate is
L4** (topology ratification, on the intake issue). After L4, the evidence-seed
(`gaia dev evidence-seed`, partitioned by evidence type) materializes the
intake's raw sources into this pipeline's collector inputs, evidence accumulates
additively, and **Trust Magnitude + rank are recomputed at appraisal time** —
rising to the skill's proper rank as Phase 0 evidence lands. Do not design or
re-introduce a pass/fail green gate; the strategy is human gate + additive
evidence.

---

## Ingestion Handoff

For L4-approved intake rows, successful Phase 4 is the boundary between the
raw evidence lake and canonical registry mutation. Create a reviewed evidence
manifest from only live, correctly scoped rows, then hand it to
`/gaia-ingest-batch`. That wrapper uses `/gaia-ingest` for every CLI-only
`gaia dev evidence` write, appraises TM, and presents calibration proposals.
Do not import evidence by hand or treat requested intake stars as evidence.

Use today's date (`currentDate` from memory) for all `YYYY_MM_DD` placeholders.
