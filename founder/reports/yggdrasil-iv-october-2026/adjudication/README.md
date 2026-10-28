# Adjudication / consequence ledger (EPIC #2189 outcome 4)

Complete for the provisional-2026-10-28 snapshot. **Nothing here is a decision: approved = 0, every candidate is `held`.**

| File | What |
|---|---|
| `ledger.json` | Candidates (one per target): `before` (stored + every public surface), `proposed` (Gaia-code recompute on an in-memory copy, or `needs-decision`), `affectedDependents`, `evidence` (finding keys, votes, verdict reasons), `recheck`, `requiredDecision`, `approved: null`, `status: held` |
| `LEDGER.md` | Summary tables and one row per candidate: before -> proposed -> approved |
| `DECISIONS.md` | Founder decision packets FD-7, FD-9 .. FD-18 (FD-9+ continue after FD-8) |
| `observations.json` | One-off manual probes (links, witness URL) read by the builder; the builder itself is offline |
| `tools/adjcore.py` | Deterministic core: load registry, apply hypothetical corrections to a copy, recompute with Gaia code; clock pinned to the registry commit time |
| `tools/build_adjudication.py` | Builds all of the above |

Regenerate (from the repo root, `python3`, Class P files `registry/gaia.json` and `registry/named-skills.json` present; otherwise run `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main dev docs` first):

    python3 founder/reports/yggdrasil-iv-october-2026/adjudication/tools/build_adjudication.py
    python3 founder/reports/yggdrasil-iv-october-2026/adjudication/tools/build_adjudication.py --check   # rebuild + byte-compare, exit 1 on drift

Rules: uses only `survives: true` findings in the eleven adjudication dimensions plus P0s, the D6 set (stored level above the TM-grade ceiling) and the named specials. No lowering from age, outages, competitor existence, model confidence or audit findings alone; IDs and hashes are not authentication. A raise or lowering is never applied; Gaia recomputes TM, grade and gates but does not assign levels. After the 2026-10-31T23:59:59Z cutoff refresh, rerun the builder against the refreshed sweep.
