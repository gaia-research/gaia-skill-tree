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
| RFC1 — named-first curation + embeddings fix + prefill | #1244 | `cli/gaia-curate-v2-rfc1` (+ `schema/…`) | — | in progress |
| RFC2 — two-stage evidence bridge | #1351 | `cli/gaia-curate-v2-rfc2` | — | blocked on RFC1 |
| RFC3 — pipeline continuity umbrella | #1352 | `cli/gaia-curate-v2-rfc3` | — | blocked on RFC1+RFC2 |
| GAP9 audit coverage | #1353 | — | — | DEFERRED / blocked (out of scope) |

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

## Token spend log

_(appended per push — `<date> <model> <effort>: Nk in, Nk out. ~$X`)_
