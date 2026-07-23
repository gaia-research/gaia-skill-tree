# CLI Alignment to Yggdrasil II Meta Schema — Plan (PR #1248)

## Context

**Why:** `dev/yggdrasil-ii-staging` will merge to main soon. It already ratified the Yggdrasil II
(Ygg II) meta model and migrated the heavy pieces. This PR (`cli/yggdrasil-ii-meta-schema-alignment`,
base = staging) is a **second-pass sweep** ensuring NO CLI path silently prefers retired Ygg I
logic before staging drops. Today the composite-detection filters still key on the removed
`extra`/`ultimate` type names, so fusion detection and unlock-path resolution silently return
empty against the ratified `{basic, fusion}` schema.

**Authoritative model — META.md §1.2 (Ygg II, 2026-07-07):**
- **Type axis** (starless `registry/nodes/` only): `basic` = 0 prereqs, `fusion` = ≥1 prereq.
  Legacy `extra`/`ultimate`/`unique` are **all retired → `fusion`**. Type is PURE STRUCTURE.
- **Branch axis** (named skills, DERIVED at read-time, never declared): suiteComponents present →
  `suite` (any rank); else rank 4–6 → `unique`; else `standard`. Orthogonal to type.

**Single source of truth = `src/gaia_cli/taxonomy.py`** (already on staging; verified clear runway —
no active sibling branch touches it or our target files). It ported + DELETED the four legacy
resolvers. `normalize(entry, metaEpoch)` is the ONLY meta-version-aware function and already handles
the Ygg I↔II fork. It is **deliberately type-independent** ("do NOT consult `type`"). **No new
resolvers** — consume it; add small helpers only where noted.

**Design tokens (consume only — DESIGN.md staging):** color source of truth =
`formatting.py::TIER_COLORS`/`RANK_COLORS` (already meta.json-driven on staging) →
`scripts/generateCssTokens.py` → `docs/css/tokens.css`. Legacy `--tier-extra/-unique/-ultimate`
survive as **color aliases only**, NOT taxonomy types. Never author token values.

## Out of scope (staging already did this — do not touch)
`registry/nodes/` dirs (`basic/`+`fusion/`), `promotion.py` (branch-based), `impl.py` argparse
(`choices=("basic","fusion")`), `formatting.py` (meta.json-driven type maps + rank-word helpers),
`cardRenderer.render_fusion_diagram` default, frontend `docs/js/skill-graph.js` +
`world-tree-layout.js` (also outside `cli/` branch scope). New staging tests
(`test_taxonomy.py`, `test_taxonomy_contract.py`, etc.).

## Fusion-detection rule (decided)
`fusion` is **structural**: a node is composite iff `len(prerequisites) >= 1`. This honors
taxonomy.py's type-independent stance AND keeps legacy Ygg I data working automatically (retired
`extra`/`ultimate`/`unique` nodes all carry prereqs). The Batch-1 predicate encodes exactly this.

---

## Batches & Gates (this PR set = 3 batches; each a separate PR, one human gate, merged into the
CLI branch before it merges to staging)

### BATCH 1 — Composite-detection LOGIC (highest severity; the silent breakage)
Filters keyed on `('extra','ultimate')` now match nothing → fusion/path detection returns empty.

| File | Need | Kind |
|---|---|---|
| `src/gaia_cli/taxonomy.py` | definitely | **HELPER-ADD** — add `isFusion(entry)` predicate: structural `len(entry.get("prerequisites") or []) >= 1` (no `type` read). Single predicate, no new resolver. |
| `src/gaia_cli/combinator.py` (L22, L58, L89 + stale docstrings L5–10/L49–52) | definitely | **LOGIC** — replace 3 `type in ('extra','ultimate')` filters with `isFusion`; update docstrings. |
| `src/gaia_cli/pathEngine.py` (L220) | definitely | **LOGIC** — same predicate for near/one-away unlocks. |
| `src/gaia_cli/cardRenderer.py` (L765) | slightly | **LOGIC (small)** — stray `.get("type","extra")` default → `"fusion"`. |

- **Reviewer subagent verifies:** all legacy `('extra','ultimate')` composite filters in `cli/` scope gone; `isFusion` is the sole gate; `basic` (0-prereq) NOT treated as composite; no new resolver; docstrings updated.
- **Stopping point:** predicate + 4 consumers only; no display/test-fixture changes.
- **Tested by:** `pytest tests/` (combinator/pathEngine — add fusion fixtures); manual `gaia scan` in a checkout with a `fusion` skill whose prereqs are owned → fusion prompt + near-unlocks reappear.

### BATCH 2 — `gaia stats` DISPLAY (token/label consume)
| File | Need | Kind |
|---|---|---|
| `src/gaia_cli/commands/stats.py` (L27–32 `TYPE_LABELS`, L45 `TYPE_ORDER`) | definitely | **DISPLAY-token-consume** — drop hardcoded extra/ultimate/unique; consume `formatting.py` (meta.json-driven TYPE_LABELS/TYPE_SYMBOLS/TIER_COLORS) so buckets are `basic`/`fusion`. |

- **Reviewer subagent verifies:** no `extra`/`ultimate`/`unique` TYPE-key literals remain in stats.py; labels/order derived from `formatting.py` (not re-authored); only `basic`/`fusion` buckets; no locally-authored token/hex.
- **Stopping point:** stats.py only.
- **Tested by:** `pytest tests/test_stats*.py` (or existing stats test); manual `gaia stats` → type breakdown shows basic/fusion, no empty extra/ultimate rows.

### BATCH 3 — `gaia graph` SVG DISPLAY + its tests + `scripts/validate.py`
Graph display rekey ships WITH its own test-fixture updates (green-per-PR). validate.py rides here
since it's test-harness correctness and shares the reviewer's "isolated validation" focus.

| File | Need | Kind |
|---|---|---|
| `src/gaia_cli/graph.py` (L29–50: `_STROKE_TINTS`, `_TYPE_LABELS`, `PALETTE`, `TYPE_ORDER`, `RADIUS_BY_TYPE`, `NODE_RADIUS`; render loops L105/119/322/330/372/388) | definitely | **DISPLAY-token-consume** — rekey extra/ultimate/unique → basic/fusion; fills via `tier_hex` (no raw hex); legacy tier tokens = color aliases only. |
| `tests/test_graph.py` (L63 fixture `type:extra`, L129 edge assertion, L372–385 PALETTE drift test) | definitely | **TEST** — fixtures → `fusion`; drift test asserts basic/fusion via token source, not legacy hex. |
| `scripts/validate.py` (`validate_named_skills` default ~L536; `main()` L849) | definitely | **LOGIC (infra)** — add `--named-dir`; default derived from `--graph` dir; wire in `main()` so a mock `--graph` validates the mock's named dir, not real `registry/named` (#1223). |

- **Reviewer subagent verifies:** all six L29–50 dicts + six render loops rekeyed to basic/fusion; no raw hex authored (fills via `tier_hex`; stroke tints are sanctioned local accents per #332); `test_graph.py` green and asserting basic/fusion; `validate.py --graph <mock>` emits zero spurious missing-ID errors; real-repo default behavior unchanged when no flag given.
- **Stopping point:** graph.py + test_graph.py + validate.py.
- **Tested by:** `pytest tests/test_graph.py` (green); manual `gaia graph`; `python scripts/validate.py --graph <mock>` → clean; `python scripts/validate.py` on real repo → unchanged.

### Deferred to FAST-FOLLOW PR (same sprint, its own gate) — NOT in this PR set
`gaia init` Ygg I→II **migration** + Ygg I **detection/warnings** (the "don't prefer legacy / harden"
posture). Lands in `src/gaia_cli/impl.py` (`init_command` L573) and `taxonomy.py` (add a Ygg-I
detection helper reusing `EPOCH_YGG_I`/`EPOCH_YGG_II`; migration reuses existing
`normalize(entry, EPOCH_YGG_I)` — no second normalizer). **Writes an explicit
`metaEpoch = "yggdrasil-ii"` marker into `.gaia/config.toml`** (none exists today) for robust
detection + idempotent re-init. Old `.gaia` files stay consumable via `normalize(..., EPOCH_YGG_I)`;
where staging already removed back-compat, emit a clear upfront error, never a silent legacy fallback.

## Branch-scope note
`scripts/validate.py` is outside the `cli/` allowlist (`src/`, `packages/`, `tests/`, `*.md`).
**Decision: keep in the cli/ PR (Batch 3) with the `skip-scope-check` label**, as the PR body
already proposes — one cohesive Ygg II sprint. Document the bypass at the Batch-3 gate.

## Definition of Done (this PR set)
1. No `cli/`-scope path filters/keys on retired `extra`/`ultimate`/`unique` type literals; the
   only skill-type values the CLI logic recognizes are `basic`/`fusion` (legacy data still
   consumable structurally via `isFusion` / `taxonomy.normalize`).
2. Fusion detection (`combinator`) and unlock-path resolution (`pathEngine`) work against Ygg II
   `fusion` nodes — verified by fixtures + a manual `gaia scan`.
3. Display surfaces (`gaia stats`, `gaia graph`) render `basic`/`fusion` sourcing colors/labels
   from the meta.json-driven token source — no locally-authored tokens/hex.
4. `scripts/validate.py --graph <mock>` validates in isolation (no spurious real-`registry/named`
   errors); real-repo default unchanged.
5. Full `pytest tests/` green (including staging's `test_taxonomy_contract.py`); every PR in the set
   is green on its own.
6. Closes #1220, #1221, #1222, #1223, #1224. Migration/warnings tracked as the fast-follow (keeps
   the sprint complete — no unfinished sprint work filed as generic follow-ups).

## Verification (end-to-end)
- **Unit:** `pytest tests/` — combinator/pathEngine fusion fixtures, `test_graph.py`, taxonomy contract.
- **Composite logic:** in a checkout, own the prereqs of a `fusion` node → `gaia scan` shows the
  fusion prompt and near-unlock card (regression proof for #1220/#1221).
- **Display:** `gaia stats` and `gaia graph` → basic/fusion only, tokens from source.
- **Validate isolation:** `python scripts/validate.py --graph <mock-graph>` clean; real-repo run unchanged.
- **Token spend:** log input/output per model+date as a PR comment on push (workspace rule).
