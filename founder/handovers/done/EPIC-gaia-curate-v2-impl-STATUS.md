# EPIC — gaia-curate v2 named-first pipeline (RFC1/2/3)

**Integration branch:** `dev/gaia-curate-v2-impl` (off `main` @ `4dd538212`)
**Milestone:** Program 5 — Gaia Skill Tree Core
**Dispatch:** `founder/handovers/2026-07-29-DISPATCH-gaia-curate-v2-impl.md`
**Human gate:** after RFC3 lands on the integration branch, before merge to `main`.

This is the running status ledger for the EPIC. Feature PRs target the integration
branch; this branch opens one draft PR → `main` (the aggregate).

## Workstreams

| RFC | Issue | Feature branch | PR → integration | Status |
|---|---|---|---|---|
| RFC1 — named-first curation + embeddings fix + prefill | #1244 | `schema/gaia-curate-v2` + `cli/gaia-curate-v2` | #1356 + #1357 (merged) | ✅ LANDED (embeddings 530/284 named; verified) |
| RFC2 — two-stage evidence bridge | #1351 | 2A/2B/2C stacked | #1358 #1359 #1360 (all merged) | ✅ LANDED — all 3 adversarially verified |
| RFC3 — pipeline continuity umbrella | #1352 | `dev/gaia-curate-v2-rfc3` (unrestricted) | #1364 (+#1365 schema fix) merged | ✅ LANDED — 14/14 verified; CLI gap #1363 filed (pre-ingest node-timeline) |
| GAP9 audit coverage | #1353 | — | — | DEFERRED / blocked (out of scope) |

## End-to-end verification (2026-07-29 — at the human gate)

Full suite + RFC-specific acceptance signals verified against the integration HEAD
(`2a7a10287`) on a fresh venv. Local Windows box has 8 pre-existing env failures
(`I/O operation on closed file` capture bug, local-registry/scanner/timeline fixtures)
that fail **identically on untouched `origin/main` v7.1.14** — confirmed NOT EPIC
regressions by running the same set on a baseline worktree. All feature PRs + the
integration branch passed full Linux CI green.

- **EPIC-owned tests:** 105/105 pass (prefill, timeline, evidence-seed, intake-adapter, provenance, skillbatch-intake, stage-one, validate-intake-packets).
- **RFC1 root cause:** `graph/embeddings.json` = 530 entries, **284 named** (was 211/0). `gaia dev prefill` embeds live via all-MiniLM-L6-v2, ranks named+generic, emits schema-valid `discovery-packet-v2` with `similarity`+`matchTier`+matched-id (L4 WHY surface). Below-`weakMap` options dropped correctly.
- **RFC2:** Stage-1 types `(github-stars-own, repo-own, self-attestation)`; evidence-seed partitions by 10 meta.json types, suite-wide dedup present, `FORBIDDEN_STRENGTH_KEYS` guard enforced.
- **RFC3:** provenance build-path persists all back-links (node→packet/batch/issue/seed/generic-ref); `--from-packet` lifts `crawlerOrigin` (GAP11); `--stage-event` appends to ledger timeline (GAP1/GAP3, not node frontmatter). Pre-flight validation **refuses** invalid ledgers (rejected fake sha256 — CLI Pre-Flight Rule working). Status ladder enum + timeline action enum reconciled. `gaia dev validate --intake` re-enabled AND wired to both skill-batch + discovery-packet-v2 validators (exit 0).
- **Schema lockstep:** all 4 mirrors (`meta`, `provenance`, `skill`, `skillBatch`) byte-identical.
- **Skill mirrors:** all 7 EPIC-touched skills byte-identical across `.claude/` + `.agents/`.
- **Aggregate PR #1355 diff:** clean — no scratch/venv; `registry-for-review` change is only `discovery-packets/.gitkeep`; one `.github` change is `validate.yml`.

## Locked decisions (do not re-litigate)

- Named-first is a REORDER, not a decouple. `genericSkillRef` REQUIRED for every skill.
- ML layer = embedding similarity (all-MiniLM-L6-v2 cosine), NOT random forest.
- Two-stage evidence: Stage 1 = cheap real rows at curation; Stage 2 = skippable Firecrawl Phase 0 on declared need.
- NO green gate — continuous additive loop; only human gate is L4.
- Programmatic-First + CLI Pre-Flight; never fabricate timeline events.

## Ground truth verified (2026-07-29)

- RFC1 root cause confirmed: `graph/embeddings.json` = 211 entries, **0 named** (no `/`-scoped ids);
  `embeddings.py::load_skills()` reads `registry/named/*.json` while named skills are `.md` frontmatter.
- #1148 OPEN — RFC2 Gap C implements its §2 "Intake handoff."

## Carried findings (for later RFCs)

- **RFC3 wiring gap:** `gaia dev validate --intake` currently routes to `scripts/validate_intake.py`
  (validates skill-batches against `skillBatch.schema.json`), NOT the discovery-packet validator.
  RFC3 §3.5 "re-enable validate --intake to resolve discovery-packet-v2" must add that wiring, not
  just un-comment the CI block.
- The discovery-packet validator (`.claude/skills/gaia-curate/scripts/validate_discovery_packet.py`)
  is hand-rolled (no JSON-schema load); RFC1 added a v2 code path via `SUPPORTED_CONTRACT_VERSIONS`.

## Token spend log

_(appended per push — `<date> <model> <effort>: Nk in, Nk out. ~$X`)_
