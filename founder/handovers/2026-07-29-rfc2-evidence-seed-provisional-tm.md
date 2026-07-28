# RFC2 — Evidence-seed emission + provisional Trust Magnitude at L4

One-line summary: Bridge curation to the evidence lake — a clearly-marked **non-canonical provisional TM** at L4 (report-column only), a **packet→intake-YAML adapter** so curation feeds `gaia push`, and **evidence-seed emission** partitioned by evidence type after L4 approval — feeding a **continuous additive** ev-pipeline with NO green gate.

Status: BUILD-READY (depends #1148)
Date: 2026-07-29
Branch: `dev/gaia-curate-v2-pipeline`
Milestone: Program 5 — Gaia Skill Tree Core (#16)
Covers: the curation→evidence bridge; depends on #1148 (evidence-lake type-partitioning)

---

## 1. Problem / Motivation

RFC1 makes `/gaia-curate` produce review-ready `discovery-packet-v2` files under `registry-for-review/discovery-packets/`. But the path from a review-ready packet to actual evidence collection has three breaks:

1. **No provisional trust signal at L4.** The L4 human ratifies topology blind to any strength estimate. `CURATION-CORE.md` forbids the worker from touching evidence/TM/grades entirely — correct as a canonical boundary, but it means the reviewer sees no "how strong might this be" hint even as a non-authoritative estimate.
2. **Gap B — no packet→intake-YAML adapter.** Nothing feeds `gaia push --from-file` / the `new_skill_intake.yml` from curation. The review-ready packet is a dead end.
3. **Gap C (BIGGEST) — no intake→evidence-collection materialization.** Per the #1148 archive handover: an L4-approved intake is routed to `/ev-pipeline`, but the pipeline only **compiles collector inputs** — it does NOT materialize an intake's raw source rows into those inputs. The #1148 §2 "Intake handoff" item is unbuilt.

RFC2 closes all three, aligned to the #1148 Target Flow, and locks in that ingest is **never gated by "green"** — the ev-pipeline is a continuous additive loop.

---

## 2. Locked Decisions (founder rulings — not open questions)

- **Provisional TM at L4 is NON-CANONICAL.** The discovery/curation phase MAY compute a provisional Trust Magnitude, carried as `provisional: true`, `ingested: false`, shown as an **L4 REPORT COLUMN ONLY**. It is NEVER written to the registry node as authoritative.
  - **Minimum evidence for the provisional estimate**: `repo-own` + `self-attestation`, plus a `youtube`/`social-signal` source if found during discovery.
  - This requires a **CARVE-OUT** in `CURATION-CORE.md` (which today forbids the worker from touching evidence/TM/grades). The carve-out permits a clearly-marked provisional, non-canonical estimate for the L4 report, and ONLY that.
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
  → packet→intake-YAML adapter (Gap B)
  → gaia push --from-file  → intake issue opened   [new_skill_intake.yml]
  → L4 HUMAN GATE  (ratifies topology; sees provisional-TM report column)
  → evidence-seed emitted, partitioned by evidence type (Gap C)   [evidence-seed artifact]
  → /ev-pipeline  CONTINUOUS ADDITIVE collection / source-verification / adversarial-audit / link-validation
  → Trust Magnitude appraisal + derived rank   (REPORT-TIME ONLY)
  → maintainer CLI promotion
  → intake-close(skill)
  → skill enters tree
```

**Where the markers lie / where audits begin:**

| Marker | Artifact | State |
|---|---|---|
| Packet lifecycle states | `discovery-packet-v2` `lifecycle[]` | `…→ mapped → review-ready` (RFC1) |
| Intake issue | GitHub issue via `gaia push` | intake opened; L4 gate lives here |
| Evidence-seed artifact | emitted post-L4, partitioned by evidence type | `provisional:true`/`ingested:false` provisional TM travels here as report metadata, never as authoritative rank |
| Provenance sidecar | `registry/provenance/<skill-id>.json` | written at ingest (**RFC3** owns this) |

Audits begin **post-L4** today; extending audit coverage to the discovery→ingest phase is **RFC3** (deferred, blocked).

### 3.2 Provisional TM — the CURATION-CORE.md carve-out

Add a bounded carve-out to `.claude/skills/gaia-curate/CURATION-CORE.md`. The existing boundary reads (§ Lifecycle and boundary): *"Do not collect evidence, score evidence, assign grades/classes, calculate Trust Magnitude…"*. Amend to permit — and ONLY permit — a clearly-marked provisional estimate for the L4 report:

- The provisional TM is computed from the **minimum evidence set**: `repo-own` (commits/contributors from the source repo) + `self-attestation` (flat 10) + optionally one `social-signal` (`youtube`) source if found during discovery. These are exactly the `selfProducible` types in `meta.json` (`repo-own`, `self-attestation`) plus one discoverable social signal — deliberately weak, deliberately non-authoritative.
- It is carried with `provisional: true` and `ingested: false` and rendered ONLY as an L4 report column.
- It MUST NOT be written to any registry node, MUST NOT set/imply a star level, grade, or class, and MUST NOT be consumed as evidence by the ev-pipeline (the seed carries raw source rows; the ev-pipeline recomputes TM canonically at appraisal time — REPORT-TIME ONLY).
- Everything else in the boundary stays: no grades/classes assigned, no registry mutation, no docs regen, no commit/push/PR, stop at L4.

This is the only relaxation. The worker still emits exactly one bounded decision (RFC1).

### 3.3 Gap B — packet→intake-YAML adapter

Build an adapter (propose `src/gaia_cli/intakeAdapter.py`, wired behind `gaia push --from-file`) that reads a review-ready `discovery-packet-v2` from `registry-for-review/discovery-packets/` and emits intake YAML consumable by `new_skill_intake.yml` / `gaia push`. Mapping:

- `decision.value == MAP` → intake references the existing `decision.genericId` (Axis A satisfied).
- `decision.value == NEW_GENERIC` → intake carries `proposal.{name,description,type}` and, when `type == fusion`, `proposal.prerequisites` (Axis B) for L4 topology ratification.
- `suite` block (RFC1) → intake carries `suiteId` + `role` + `componentCandidateIds` so the fan-out (component packets + capstone) is reconstructable; `attributionScope` seeded from `role` (`capstone`/component → `suite-wide`/`suite-component`, else `standalone`).
- Provisional TM (§3.2) rides along as report metadata only (`provisional:true`, `ingested:false`).

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

The ev-pipeline runs as a **continuous additive loop**: it keeps discovering new evidence rows (appending to the per-type partitions) and discarding rejected ones. There is **no pass/fail "green" wall** gating ingest. The only human gate is L4 (topology ratification); after that, evidence accumulates additively and TM/rank are recomputed at appraisal time. This loose strategy fits a Haiku dynamic-workflow loop (`/ev-pipeline`, `gaia-meta-sweep`). Any earlier draft describing a structured GREEN gate is **dropped**.

---

## 4. Gaps closed

- **Gap B** — packet→intake-YAML adapter (`discovery-packet-v2` → intake YAML → `gaia push`).
- **Gap C** — evidence-seed emission partitioned by evidence type with attribution scope (the #1148 §2 Intake handoff), the biggest seam.
- **Provisional-TM absence at L4** — non-canonical report-column estimate via the `CURATION-CORE.md` carve-out.

---

## 5. Acceptance criteria

- [ ] `CURATION-CORE.md` provisional-TM carve-out: clearly non-canonical (`provisional:true`, `ingested:false`), min-evidence spec (`repo-own` + `self-attestation` + optional `social-signal`), report-column only, never written to a node, never consumed as ev-pipeline evidence.
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
