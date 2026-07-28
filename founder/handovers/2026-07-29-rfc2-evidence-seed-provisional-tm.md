# RFC2 — Two-stage evidence: minimum-effort seed + Firecrawl discovery (Phase 0)

One-line summary: Bridge curation to the evidence lake with a **two-stage evidence model** — Stage 1 writes **minimum-effort REAL evidence** (GitHub stars + contributors + repo-own, cheap-fetched from the repo already in hand) at curation, then a **skippable Firecrawl-driven discovery Phase 0** does a full evidence search to raise Trust Magnitude to its proper rank. Plus a **packet→intake-YAML adapter** so curation feeds `gaia push`, and **evidence-seed emission** partitioned by evidence type — feeding a **continuous additive** ev-pipeline with NO green gate.

Status: BUILD-READY (depends #1148)
Date: 2026-07-29
Branch: `dev/gaia-curate-v2-pipeline`
Milestone: Program 5 — Gaia Skill Tree Core (#16)
Covers: the curation→evidence bridge; depends on #1148 (evidence-lake type-partitioning)

---

## 1. Problem / Motivation

RFC1 makes `/gaia-curate` produce review-ready `discovery-packet-v2` files under `registry-for-review/discovery-packets/`. But the path from a review-ready packet to actual evidence collection has three breaks:

1. **No trust signal at L4.** The L4 human ratifies topology blind to any strength estimate. `CURATION-CORE.md` forbids the worker from touching evidence/TM/grades entirely — correct as a canonical boundary, but the reviewer sees no strength signal even though the cheapest signals (stars, contributors) are already in hand from the crawl.
2. **Gap B — no packet→intake-YAML adapter.** Nothing feeds `gaia push --from-file` / the `new_skill_intake.yml` from curation. The review-ready packet is a dead end.
3. **Gap C (BIGGEST) — no intake→evidence-collection materialization.** Per the #1148 archive handover: an L4-approved intake is routed to `/ev-pipeline`, but the pipeline only **compiles collector inputs** — it does NOT materialize an intake's raw source rows into those inputs. The #1148 §2 "Intake handoff" item is unbuilt.
4. **Gap D — the ev-pipeline never SEARCHES for new evidence.** Confirmed by reading the skills (2026-07-29): `ev-pipeline` is a "pre-flight" step that only **aggregates** what already sits in `evidence/collectors/` and **verifies** it (ev-collection aggregates; ev-star-verification refreshes GitHub star counts; ev-adversarial-audit + ev-link-validation quality-check). No phase does evidence *discovery*. The `firecrawl` skill exists as a capability wrapper (`firecrawl search`/`scrape`) but nothing orchestrates it into an evidence-discovery pass — this is the "forgotten pipeline" absence. So a skill can never rise above its minimum-effort seed today: there is no mechanism to find the benchmarks/arXiv/peer-review/showcase evidence that lifts TM to its proper rank.

RFC2 closes all four with a **two-stage evidence model**, aligned to the #1148 Target Flow, and locks in that ingest is **never gated by "green"** — the ev-pipeline is a continuous additive loop.

---

## 2. Locked Decisions (founder rulings — not open questions)

- **TWO-STAGE EVIDENCE MODEL (founder ruling, corrects the earlier provisional-only draft).**
  - **Stage 1 — minimum-effort REAL evidence, written at curation.** Not a deliberately-weak non-canonical estimate: the crawler already holds the repo, so it fetches the *cheap* signals and writes them as REAL evidence rows — **`github-stars-own` (stargazer count) + `repo-own` (commits/contributors) + `self-attestation`**. No web search. This is "minimum-**effort**," not "minimum": stars carry full weight (`social-signal`/stars weight 1.0 in `meta.json`), so Stage 1 already produces a real, if incomplete, Trust Magnitude — the skill enters at whatever rank these cheap signals justify.
  - **Stage 2 — full evidence search (Firecrawl), skippable Phase 0.** A discovery pass searches the web for the evidence Stage 1 can't cheaply get (`benchmark-result`, `arxiv`, `peer-review`, richer `social-signal` showcases) and **appends** it, raising TM to its **proper** rank via the additive loop. It is **SKIPPABLE** and **triggers only when higher-quality evidence is DECLARED needed** (not on every ingest).
  - Consequence: there is **no non-canonical "provisional TM report column."** Stage 1 evidence is canonical (ingested), just partial. The reviewer at L4 sees the real Stage-1 TM, not a throwaway estimate.
- **Gap D — build the skippable Firecrawl discovery Phase 0.** The ev-pipeline has no evidence-*discovery* search (confirmed). Build an evidence-discovery orchestration ON TOP OF the existing `firecrawl` skill's `firecrawl search`/`scrape` primitives, inserted as a **skippable Phase 0 BEFORE `ev-collection`**, writing found sources into `evidence/collectors/` so the existing four phases then aggregate + verify them. Phase 0 runs only when higher-quality evidence is declared needed. **First check whether a forgotten evidence-discovery skill already exists** and reuse it rather than building fresh. This is the "raise to proper rank" mechanism.
- **CURATION-CORE.md carve-out (Stage 1 only).** `CURATION-CORE.md` today forbids the worker from touching evidence/TM/grades. Amend to permit — and ONLY permit — writing the Stage-1 minimum-effort evidence set (stars + contributors + repo-own) that the crawler already holds. No search, no scoring beyond what those cheap rows imply, no grade/class assignment by the worker; TM is still derived canonically at appraisal time.
- **Evidence-seed = the #1148 "evidence-seed" artifact.** gaia-curate PRODUCES the seed; the #1148 evidence bridge CONSUMES it. NOT nova-gaia `sourceProposal` (separate disconnected pipeline, out of scope).
  - Per the #1148 Target Flow: L4-approved intake → evidence seed (`skill ID`, `source URL`, `claimed evidence type`, `attribution scope`) → collector input partitioned by evidence type.
  - **Attribution scope = the suite axis**: `standalone` / `suite-component` / `suite-wide`. A **suite-wide source MUST NOT be copied as full-strength proof for every component** (the Firecrawl learning from the #1148 archive).
- **Gap B — build the packet→intake-YAML adapter.** review-ready `discovery-packet-v2` (from RFC1's output dir) → intake YAML → `gaia push` opens the intake issue.
- **Gap C — build evidence-seed emission after L4 approval** that materializes raw source rows **partitioned by evidence type** (the #1148 §2 "Intake handoff" item). Do NOT carry a requested star level/tier/grade/class as authoritative.
- **GREEN is NOT a gate.** Ingest is never gated by "green." The ev-pipeline is a **CONTINUOUS ADDITIVE LOOP** — it keeps finding new evidence and discarding rejected ones; evidence is additive. Loose is the strategy (fits a Haiku dynamic-workflow loop). **DROP any structured-GREEN-gate design.** Human gate + additive evidence, not a pass/fail green wall.

---

## 3. Design detail

### 3.1 The pipeline narrative (the full picture)

```
/gaia-curate
  → review-ready discovery-packet-v2   [registry-for-review/discovery-packets/]
  → STAGE 1: minimum-effort REAL evidence written at curation
             (github-stars-own + repo-own contributors + self-attestation — cheap, no search)
  → packet→intake-YAML adapter (Gap B)
  → gaia push --from-file  → intake issue opened   [new_skill_intake.yml]
  → L4 HUMAN GATE  (ratifies topology; sees the REAL Stage-1 Trust Magnitude)
  → evidence-seed emitted, partitioned by evidence type (Gap C)   [evidence-seed artifact]
  → [SKIPPABLE] STAGE 2 / PHASE 0: Firecrawl evidence-discovery search (Gap D)
             — triggers only when higher-quality evidence is DECLARED needed;
               writes found sources into evidence/collectors/
  → /ev-pipeline  CONTINUOUS ADDITIVE collection / source-verification / adversarial-audit / link-validation
  → Trust Magnitude appraisal + derived rank   (REPORT-TIME ONLY — now at its PROPER rank)
  → maintainer CLI promotion
  → intake-close(skill)
  → skill enters tree
```

**Where the markers lie / where audits begin:**

| Marker | Artifact | State |
|---|---|---|
| Packet lifecycle states | `discovery-packet-v2` `lifecycle[]` | `…→ mapped → review-ready` (RFC1) |
| Stage-1 evidence | `github-stars-own` + `repo-own` + `self-attestation` rows | REAL evidence (ingested), written at curation; cheap-fetched, no search |
| Intake issue | GitHub issue via `gaia push` | intake opened; L4 gate lives here; L4 sees the real Stage-1 TM |
| Evidence-seed artifact | emitted post-L4, partitioned by evidence type | raw source rows; TM/rank derived at appraisal time, never carried as authoritative |
| Phase 0 discovery (skippable) | Firecrawl-found sources → `evidence/collectors/` | Stage 2; runs only when higher-quality evidence is declared needed |
| Provenance sidecar | `registry/provenance/<skill-id>.json` | written at ingest (**RFC3** owns this) |

Audits begin **post-L4** today; extending audit coverage to the discovery→ingest phase is **RFC3** (deferred, blocked).

### 3.2 Two-stage evidence — Stage 1 (curation) + the CURATION-CORE.md carve-out

**Stage 1 is REAL, ingested, minimum-EFFORT evidence — not a non-canonical estimate.** The crawler already holds the source repo, so it writes the cheap-to-fetch rows directly:

- **`github-stars-own`** — the stargazer count (already fetched during discovery; the one live signal `ev-star-verification` also refreshes later).
- **`repo-own`** — commits + contributors from the source repo.
- **`self-attestation`** — the flat baseline.

These enter as canonical evidence rows (partitioned by type per §3.4). Because `github-stars-own`/`social-signal` carry weight 1.0 in `meta.json`, Stage 1 already yields a **real Trust Magnitude at whatever rank those cheap signals justify** — the skill is not parked at a throwaway C-floor. It is simply *incomplete* until Stage 2 runs.

Add a bounded carve-out to `.claude/skills/gaia-curate/CURATION-CORE.md`. The existing boundary reads (§ Lifecycle and boundary): *"Do not collect evidence, score evidence, assign grades/classes, calculate Trust Magnitude…"*. Amend to permit — and ONLY permit — writing the Stage-1 minimum-effort set:

- The worker MAY record `github-stars-own` + `repo-own` + `self-attestation` rows the crawler already holds. **No web search** at this stage (that is Stage 2 / Phase 0).
- The worker still MUST NOT assign a grade/class, MUST NOT set a star level, and MUST NOT hand-compute a final TM — TM is derived canonically at appraisal time from the evidence rows.
- Everything else in the boundary stays: no registry mutation beyond the evidence rows, no docs regen, no commit/push/PR, stop at L4.

This is the only relaxation. The worker still emits exactly one bounded decision (RFC1).

### 3.2b Stage 2 / Phase 0 — skippable Firecrawl evidence-discovery (Gap D)

The ev-pipeline confirmed (2026-07-29) has **no evidence-discovery search** — it only aggregates + verifies what already sits in `evidence/collectors/`. Build the discovery pass:

- **Reuse first.** Before building, check for a **forgotten/existing evidence-discovery skill** and reuse it. If none, build on top of the existing `firecrawl` skill's `firecrawl search` / `firecrawl scrape` primitives — do NOT write a new web tool.
- **Position: a skippable Phase 0 BEFORE `ev-collection`.** It searches the web for the evidence Stage 1 can't cheaply get — `benchmark-result`, `arxiv`, `peer-review`, richer `social-signal` showcases — and writes found sources into `evidence/collectors/` (the channel dirs `technical/`, `social/`, `verification/`) so the existing four phases then aggregate + verify them exactly as today.
- **Trigger: declared need only.** Phase 0 does NOT run on every ingest. It fires when higher-quality evidence is *declared* needed (e.g. a skill is a promotion candidate, or `gaia-meta-sweep` flags it as under-evidenced). This keeps the common path cheap (Stage 1 only) and reserves Firecrawl spend for skills that warrant a proper-rank push.
- **Effect: raises TM to its proper rank** by appending real discovered evidence to the additive loop (§3.5).

Naming: no underscores in new public names (repo style) — e.g. a `/ev-discovery` skill or a `gaia dev evidence-search` verb, TBD against the existing `ev-*` surface.

### 3.3 Gap B — packet→intake-YAML adapter

Build an adapter (propose `src/gaia_cli/intakeAdapter.py`, wired behind `gaia push --from-file`) that reads a review-ready `discovery-packet-v2` from `registry-for-review/discovery-packets/` and emits intake YAML consumable by `new_skill_intake.yml` / `gaia push`. Mapping:

- `decision.value == MAP` → intake references the existing `decision.genericId` (Axis A satisfied).
- `decision.value == NEW_GENERIC` → intake carries `proposal.{name,description,type}` and, when `type == fusion`, `proposal.prerequisites` (Axis B) for L4 topology ratification.
- `suite` block (RFC1) → intake carries `suiteId` + `role` + `componentCandidateIds` so the fan-out (component packets + capstone) is reconstructable; `attributionScope` seeded from `role` (`capstone`/component → `suite-wide`/`suite-component`, else `standalone`).
- Stage-1 minimum-effort evidence (§3.2) is already written as real rows; the adapter carries the intake reference, not a throwaway estimate.

`gaia push` then opens the intake issue (the L4 gate surface). No underscores in new public names (repo style) — e.g. `buildIntakeYaml`.

### 3.4 Gap C — evidence-seed emission (the #1148 §2 Intake handoff)

After L4 approval, emit a raw **evidence-seed** artifact that materializes the intake's source rows into collector inputs **partitioned by evidence type**. Per the #1148 Target Flow, each seed row carries:

- `skillId`
- `sourceUrl`
- `claimedEvidenceType` — one of the `meta.json` evidence type ids (`repo-own`, `github-stars-own`, `social-signal`, `benchmark-result`, `arxiv`, `peer-review`, `proxy-containment`, `verifier-attestation`, `fusion-recipe`, `self-attestation`).
- `attributionScope` — `standalone` | `suite-component` | `suite-wide`. **A `suite-wide` source is NOT copied as full-strength proof for every component** (Firecrawl learning: suite-wide repo adoption ≠ per-endpoint proof).

Partition the emitted rows into per-evidence-type collector inputs (the #1148 lake structure, keyed by skill id + evidence type — replacing the stale `tier_N.md` partitioning). **Do NOT carry a requested star level/tier/grade/class as authoritative** — the seed is raw sources only; TM + rank are derived at appraisal time.

Emission is the handoff from the L4-approved intake to `/ev-pipeline`. This is the biggest missing seam and the direct implementation of #1148 §2.

### 3.5 The additive loop — NO green gate

The ev-pipeline runs as a **continuous additive loop**: it keeps **aggregating** new evidence rows (appending to the per-type partitions) and discarding rejected ones. New rows arrive two ways — Stage 1 writes cheap rows at curation, and the skippable Phase 0 (§3.2b) discovers richer rows on declared need. There is **no pass/fail "green" wall** gating ingest. The only human gate is L4 (topology ratification); after that, evidence accumulates additively and TM/rank are recomputed at appraisal time, rising to the skill's proper rank as Phase 0 evidence lands. This loose strategy fits a Haiku dynamic-workflow loop (`/ev-pipeline`, `gaia-meta-sweep`). Any earlier draft describing a structured GREEN gate is **dropped**.

---

## 4. Gaps closed

- **Gap B** — packet→intake-YAML adapter (`discovery-packet-v2` → intake YAML → `gaia push`).
- **Gap C** — evidence-seed emission partitioned by evidence type with attribution scope (the #1148 §2 Intake handoff), the biggest seam.
- **Gap D** — the ev-pipeline had no evidence-*discovery* search; the skippable Firecrawl Phase 0 (§3.2b) adds it, so a skill can rise past its cheap Stage-1 signals to its proper rank.
- **No trust signal at L4** — Stage 1 writes real minimum-effort evidence (stars + contributors + repo-own) so L4 sees a real TM, via the `CURATION-CORE.md` carve-out.

---

## 5. Acceptance criteria

- [ ] `CURATION-CORE.md` carve-out permits ONLY the Stage-1 minimum-effort set (`github-stars-own` + `repo-own` + `self-attestation`), written as real evidence rows, no web search at this stage, no grade/class/star assigned by the worker (TM derived at appraisal time).
- [ ] Stage 1 fires during curation from signals the crawler already holds; the skill enters at whatever rank those cheap real signals justify (not a throwaway floor).
- [ ] **Gap D** — a skippable **Phase 0** evidence-discovery pass exists (reusing a forgotten/existing skill if found, else built on the `firecrawl` skill's `search`/`scrape`), positioned BEFORE `ev-collection`, writing found sources into `evidence/collectors/`; triggers only on declared need for higher-quality evidence; raises TM to proper rank.
- [ ] Packet→intake-YAML adapter reads `registry-for-review/discovery-packets/` and emits YAML for `gaia push --from-file`; handles `MAP` / `NEW_GENERIC` (incl. `proposal.prerequisites` for fusions) and the `suite` fan-out.
- [ ] Evidence-seed emission after L4 approval, partitioned by evidence type, each row carrying `skillId`, `sourceUrl`, `claimedEvidenceType` (from `meta.json` types), `attributionScope` (`standalone`/`suite-component`/`suite-wide`).
- [ ] Suite-wide source NOT copied as full-strength proof for every component.
- [ ] `/ev-pipeline` consumes the evidence-seed (materialized rows land in per-type collector inputs).
- [ ] NO green gate anywhere; loop is continuous + additive; only L4 is a human gate.
- [ ] No requested star/tier/grade/class carried as authoritative.
- [ ] Consolidation notes vs #1148 explicit (this RFC implements #1148 §2 "Intake handoff"; §1/§3/§4 lake-script + migration remain #1148's own scope).

---

## 6. Out of scope / non-goals

- **The dropped GREEN gate** — explicitly abandoned; do not design a structured pass/fail green wall.
- **#1148 §1/§3/§4** — lake-script rewrite (tier files → evidence-type outputs), ev-pipeline skill/doc rewrites, tier-file migration are #1148's own scope; RFC2 only builds the §2 Intake handoff (evidence-seed emission) that feeds them.
- **RF/SHAP trust appraisal** — the ML-**v3** study (gaia-research #129 / PR #128). Decoupled.
- **nova-gaia (`sourceProposal.schema.json`)** — separate pipeline for already-named skills; out of scope (may converge later pending founder review — no design here).
- **Provenance sidecar, stage timeline events, status ladder, schema enum reconciliation, audit coverage, `validate --intake` re-enable** — RFC3.
- **The embedding fix, prefill, discovery-packet-v2 schema, thresholds** — RFC1.

---

## 7. Cross-references

- #1148 — evidence-lake type-partitioning (dependency; this RFC builds its §2 Intake handoff).
- `founder/handovers/archive/2026-07-13-evidence-lake-type-partitioning.md` — Target Flow (lines 15-22), §2 Intake handoff, attribution-scope + Firecrawl learning, "do not carry star/tier/grade as authoritative."
- **RFC1 (gaia-curate v2 named-first)** — produces the `registry-for-review/discovery-packets/` input this RFC consumes; #1244.
- **RFC3 (pipeline continuity umbrella)** — restates the additive loop at the umbrella level; owns provenance/timeline/status/audit.
- `registry/schema/meta.json` — evidence type ids + `selfProducibleTypes` + grade thresholds (report-time appraisal only).
- gaia-research #129 / PR #128 — RF/SHAP v3 study (decoupled).
