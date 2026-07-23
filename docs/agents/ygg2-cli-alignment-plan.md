# CLI Alignment to Yggdrasil II Meta Schema — Plan (PR #1248)

## Context

**Why:** `dev/yggdrasil-ii-staging` will merge to main soon. It already ratified the Yggdrasil II
(Ygg II) meta model and migrated the heavy pieces. This PR (`cli/yggdrasil-ii-meta-schema-alignment`,
base = staging) is a **second-pass sweep** ensuring NO CLI path silently prefers retired Ygg I
logic before staging drops — AND that the non-dev CLI reflects the ratified **"no self-promote"**
player model. Two problem classes:

1. **Composite-detection drift (Batch 1 — merged):** filters keyed on the removed
   `extra`/`ultimate` type names → fusion detection and unlock-path resolution silently returned
   empty against the ratified `{basic, fusion}` schema. Fixed structurally by `isFusion`.
2. **Self-promote violation (Batch 0 — next to land):** the non-dev CLI ships a fully-wired,
   ungated `gaia promote` that writes rank directly into the user's `skill-tree.json`. Under Ygg II
   rank is assigned ONLY by canon curation; the local CLI's job ends at *propose*. This whole
   mechanic — command, bulk `--all`, the scan "Promotion Available" card, the promote-candidate
   file — is retired here.

**Authoritative model — META.md §1.2 (Ygg II, 2026-07-07):**
- **Type axis** (starless `registry/nodes/` only): `basic` = 0 prereqs, `fusion` = ≥1 prereq.
  Legacy `extra`/`ultimate`/`unique` are **all retired → `fusion`**. Type is PURE STRUCTURE.
  Schema-backed: `registry/schema/meta.json → types.minPrereqs = {basic:0, fusion:1}`.
- **Branch axis** (named skills, DERIVED at read-time, never declared): suiteComponents present →
  `suite` (any rank); else rank 4–6 → `unique`; else `standard`. Orthogonal to type.

**Player loop (ratified — the model Batch 0 enforces):**
```
gaia scan   → discover fusions you have the components for
gaia fuse   → declare/structure LOCALLY (ties to gaia-research/skill-fuse)
gaia push   → propose the structure to canon; curation "awakens" it (→ assigns rank)
```
Rank/level is **never** self-assigned locally. The local CLI proposes; canon curation grades.

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
`registry/nodes/` dirs (`basic/`+`fusion/`), `impl.py` argparse `add`/`fuse` type
`choices=("basic","fusion")`, `formatting.py` (meta.json-driven type maps + rank-word helpers),
`cardRenderer.render_fusion_diagram` default, frontend `docs/js/skill-graph.js` +
`world-tree-layout.js` (also outside `cli/` branch scope). New staging tests
(`test_taxonomy.py`, `test_taxonomy_contract.py`, etc.). Canon-side / dev-gated flows:
`gaia push`, `gaia propose`, `gaia dev fuse` (never mutate user trees).

## Fusion-detection rule (decided, shipped in Batch 1)
`fusion` is **structural**: a node is composite iff `len(prerequisites) >= 1`. This honors
taxonomy.py's type-independent stance AND keeps legacy Ygg I data working automatically (retired
`extra`/`ultimate`/`unique` nodes all carry prereqs). The Batch-1 predicate `taxonomy.isFusion`
encodes exactly this and matches the schema `minPrereqs` definition. Batch 0's awaken-card
reuses this predicate + an empty-parent signal.

## Ratified decisions carried into Batch 0 (Marco, 2026-07-23 — do not re-litigate)
1. **No user-facing self-promote.** Rank is assigned ONLY by canon curation. Local CLI ends at *propose*.
2. **`gaia promote` is DEAD** → **clean delete** (planning decision, below).
3. **Bulk auto-promote (`gaia promote --all` → `promote_all_candidates`) dies too.** No real
   `--auto-promote` flag exists in code — that is phantom doc drift in `docs/en/cli-reference.html`
   (L1077/1101/1121); the real bulk mechanic is `--all`. Kill both.
4. **Scan card always shows the fusion** (a real skill exists). The **"awaken" message**
   (`gaia fuse` + `gaia push`) appears only when the **generic parent is empty** (no named
   implementation claimed yet).
5. **No star level / no Extra·Unique·medallion decoration on the card.** Suite/unique is a canon 4★+
   concept, irrelevant at proposal time. The card quotes NO level. (This dissolves the original 4★
   mislabel bug — there is no level line left to mislabel.)
6. **`gaia fuse` level nuance:** canon-tied fusion (`ctx.is_origin(sid)`) may inherit the canon
   `levelFloor` (mirrors canon, not self-declaration — keep). Custom/starless fusion
   (`ctx.novel_ids`, interactive "new" flow) gets **NO level** — strip the `level` write at
   `impl.py:2022-2027` and rekey its `type:"extra"` → `"fusion"`. The `fuse` →
   `promote_from_candidates` short-circuit (`impl.py:2089-2101`) dies with promote.
7. **Schema backing** for the fusion bucket is `meta.json.types.minPrereqs` — consume, don't re-author.

## Planning decisions resolved this session (the two forks the handoff deferred)
- **`gaia promote` fate → CLEAN DELETE.** Remove the command class, argparse, dispatch, and
  `PUBLIC_COMMANDS`/usage entry. Typing `gaia promote` falls to argparse's `invalid choice` error.
  **No shim / no redirect-alias** — an alias would keep the retired mental model alive in help text,
  and `promote` (skill-id + `--label`) has no drop-in successor (`fuse`/`push` are different verbs).
  This is pre-1.0 churn on a staging branch, not a public-API break requiring a deprecation cycle.
- **`promotion.py` fork → DELETE the self-promote machinery; compute the awaken-card FRESH.**
  The candidate-file handshake (`write_promotion_candidates` / `load_promotion_candidates` /
  `check_promotion_eligibility`) exists *to gate self-promotion* — a 24h-freshness contract between
  `scan` (writes) and `promote` (consumes). With `promote` dead the second half is gone;
  repurposing the file into "fusion-proposal candidates" would keep a stale-able persistence layer
  the display-only awaken-card doesn't need. The card needs only *owned-prereqs + empty-parent* at
  render time, which `pathEngine.compute_paths` already yields (`nearUnlocks`). **KEEP** the
  canon-side helpers `checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade`, and
  `LEVEL_NAMES` (consumed by `verification.py:70`, `scripts/migrate_taxonomy_v6.py:60`, and the
  card's level-name lookup — none are self-promote).

---

## Batches & Gates (PR set = 4 batches; each a separate PR, one human gate, reviewer-subagent
assurance pass, merged into the CLI branch before it merges to staging)

**Landing order:** Batch 1 (merged) → **Batch 0** (next; reshapes the same scan surface) →
Batch 2 → Batch 3. Batch 0 is numbered 0 because it is a behavioral correction, not a taxonomy
rekey — but it lands *after* Batch 1 (whose `isFusion` it consumes) and *before* the display batches.

### BATCH 1 — Composite-detection LOGIC ✅ MERGED (`0377495d0`)
Filters keyed on `('extra','ultimate')` matched nothing → fusion/path detection returned empty.
Shipped: `taxonomy.isFusion(entry)` (structural `len(prerequisites) >= 1`, no `type` read);
`combinator.py`, `pathEngine.py:220`, `cardRenderer.py:765` now gate on `isFusion`. No display or
test-fixture changes. **Batch 0 builds directly on this predicate.**

### BATCH 0 — "No self-promote": retire `gaia promote`, reshape scan card → awaken-card (BEHAVIORAL — highest severity remaining)
The non-dev CLI self-assigns rank into `skill-tree.json` with no dev gate — the core Ygg II
violation. Retire the whole mechanic and replace the "Promotion Available" card with a levelless
fusion/awaken card.

| Action | File:line | Kind |
|---|---|---|
| Delete `gaia promote` command (class + registration) | `commands/progression.py:21-39,66` | **LOGIC (delete)** |
| Delete legacy argparse + dispatch for promote | `impl.py:3701-3712`, `impl.py:4458-4459` | **LOGIC (delete)** |
| Remove `promote` from `PUBLIC_COMMANDS` + usage text | `impl.py:248`, `impl.py:154` | **LOGIC (delete)** |
| Delete bulk `--all` auto-promote | `impl.py:1203` (`promote_all_candidates`), `impl.py:1469`, `commands/progression.py:30`, `selector.py:86` | **LOGIC (delete)** |
| Delete `promote_command` impl | `impl.py:1436-1516` | **LOGIC (delete)** |
| Excise self-promote fns from `promotion.py`; KEEP canon helpers | `promotion.py` (`promote_from_candidates`:413, `promote_skill`:469, `write_promotion_candidates`:360, `load_promotion_candidates`, `check_promotion_eligibility`:156) — keep `checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade`, `LEVEL_NAMES` | **LOGIC (delete + keep)** |
| Reshape scan card → levelless fusion/awaken card (decisions #4,#5); drop the "can rank up to Level N" + "Run: gaia promote" rows; show `gaia fuse`+`gaia push` awaken message ONLY when generic parent empty | `cardRenderer.py:757-824` (`render_promotion_prompt` → rename to an awaken/fusion renderer) | **LOGIC + DISPLAY** |
| Rewire scan path: stop importing/calling `check_promotion_eligibility`; compute awaken-card fresh from `nearUnlocks` (owned-prereqs) + empty-parent signal; stop emitting the promote-candidate file | `hook.py:111-119`, `impl.scan_command` | **LOGIC** |
| Reshape `fuse_command` (decision #6): custom/starless → strip `level`, rekey `type:"extra"`→`"fusion"`; keep canon-tied `levelFloor` mirror; delete the `promote_from_candidates` short-circuit | `impl.py:1960-2110` (esp. 2022-2027, 2057-2067, 2089-2101) | **LOGIC** |
| appraise: drop "promotable to Level N" hint | `impl.py:1427-1431`, `cardRenderer.py:475` | **DISPLAY** |
| Phantom `--auto-promote` doc drift | `docs/en/cli-reference.html:1077,1101,1121` | **DOC** |
| Docs sweep | `README.md:283,306`; `DESIGN.md:116-117,177-178,356,361,490`; `CLAUDE.md:162,175,192,237`; `src/gaia_cli/CLAUDE.md` (Authorization "promote … never gated" line); `DEV.md:92,122`; `skill-trees/README.md:50` | **DOC** |
| Tests | `tests/test_promotion.py` (37 refs — delete self-promote coverage, keep canon-helper coverage), `tests/test_card_renderer.py:15,366-404`, `tests/test_cli_core.py:229` | **TEST** |

- **Reviewer subagent verifies:** `gaia promote` is fully gone (no class, argparse, dispatch,
  `PUBLIC_COMMANDS`, usage, or docs reference); `--all`/`promote_all_candidates` gone; NO code path
  writes rank/level into `skill-trees/<user>/skill-tree.json` outside canon curation; the scan card
  quotes NO level and shows the awaken message ONLY on empty generic parent; `promotion.py` retains
  ONLY the canon-side helpers (`checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade`,
  `LEVEL_NAMES`) and their importers (`verification.py`, `migrate_taxonomy_v6.py`) still resolve;
  custom fuse writes no `level` and `type:"fusion"`; canon-tied fuse still mirrors `levelFloor`;
  no `check_promotion_eligibility` import remains on the scan path.
- **Stopping point:** promote retirement + card reshape + fuse nuance + docs/tests. No stats/graph
  rekey (Batch 2/3), no migration (fast-follow).
- **Tested by:** `pytest tests/` (promotion/card_renderer/cli_core green after deletions); manual —
  (a) `gaia promote research` → `invalid choice` error; (b) `gaia scan` in a checkout owning a
  fusion's prereqs → levelless fusion card + awaken hint when parent empty, no "rank up to Level N"
  line; (c) `gaia fuse` custom flow → `.gaia/custom_state.json` has `type:"fusion"`, no `level`;
  (d) grep confirms `skill-tree.json` untouched by any non-dev command.

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
| `tests/test_graph.py` (L63 legacy-`extra` fixture, L129 edge assertion, L372–385 PALETTE drift test) | definitely | **TEST** — fixtures → `fusion`; drift test asserts basic/fusion via token source, not legacy hex. |
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
already proposes — one cohesive Ygg II sprint. Document the bypass at the Batch-3 gate. Batch 0's
`docs/en/cli-reference.html` edit is also outside the `cli/` `*.md` glob (it's `.html`); Batch 0
carries `skip-scope-check` for that one doc file — note it at the Batch-0 gate.

## Definition of Done (this PR set)
1. **No self-promote:** `gaia promote` (and bulk `--all`) is fully removed; NO non-dev CLI path
   writes rank/level into `skill-trees/<user>/skill-tree.json`. The scan card is levelless and shows
   the awaken hint only on an empty generic parent. `promotion.py` retains only canon-side helpers.
2. **No legacy type literals:** no `cli/`-scope path filters/keys on retired
   `extra`/`ultimate`/`unique` type literals; the only skill-type values CLI logic recognizes are
   `basic`/`fusion` (legacy data still consumable structurally via `isFusion` / `normalize`).
3. Fusion detection (`combinator`) and unlock-path resolution (`pathEngine`) work against Ygg II
   `fusion` nodes — verified by fixtures + a manual `gaia scan` (Batch 1, merged).
4. Display surfaces (`gaia stats`, `gaia graph`) render `basic`/`fusion` sourcing colors/labels
   from the meta.json-driven token source — no locally-authored tokens/hex.
5. `scripts/validate.py --graph <mock>` validates in isolation (no spurious real-`registry/named`
   errors); real-repo default unchanged.
6. Full `pytest tests/` green (including staging's `test_taxonomy_contract.py`); every PR in the set
   is green on its own.
7. Closes #1220, #1221, #1222, #1223, #1224 (+ the self-promote-violation issue Batch 0 addresses).
   Migration/warnings tracked as the fast-follow (keeps the sprint complete — no unfinished sprint
   work filed as generic follow-ups).

## Verification (end-to-end)
- **Unit:** `pytest tests/` — promotion (canon helpers only), card_renderer, cli_core,
  combinator/pathEngine fusion fixtures, `test_graph.py`, taxonomy contract.
- **No self-promote (Batch 0):** `gaia promote …` → `invalid choice`; `gaia scan` on owned fusion
  prereqs → levelless card + awaken hint on empty parent; `gaia fuse` custom → no `level`,
  `type:"fusion"`; grep proves `skill-tree.json` untouched by non-dev commands.
- **Composite logic (Batch 1):** own the prereqs of a `fusion` node → `gaia scan` shows the fusion
  card and near-unlock (regression proof for #1220/#1221).
- **Display:** `gaia stats` and `gaia graph` → basic/fusion only, tokens from source.
- **Validate isolation:** `python scripts/validate.py --graph <mock-graph>` clean; real-repo run unchanged.
- **Token spend:** log input/output per model+date as a PR comment on push (workspace rule).
