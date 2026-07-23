# Handoff — Ygg II CLI Alignment: Batches 2 & 3 (PR #1248 / umbrella #1225)

**For the next agent picking up `cli/yggdrasil-ii-meta-schema-alignment` (base `dev/yggdrasil-ii-staging`).**

## State as of 2026-07-23 (read this first)
- **Batch 1 ✅ MERGED** (`0377495d0`) — structural `taxonomy.isFusion` (`len(prerequisites) >= 1`), consumed by `combinator.py` / `pathEngine.py` / `cardRenderer.py`.
- **Batch 0 ✅ MERGED** (PR #1255, merge commit `5067b7f4a`) — "no self-promote": `gaia promote` + bulk `--all` deleted; scan card is now a **levelless fusion/awaken card** (`render_fusion_awaken_card`); custom `gaia fuse` writes `type:"fusion"` with no `level`; 5 self-promote fns excised from `promotion.py` (4 canon helpers kept). Verified invariant: no non-dev CLI path writes rank/level into `skill-trees/<user>/skill-tree.json` except the sanctioned canon-tied combo mirror (`impl.py:1913`).
- **CLI branch HEAD:** `5067b7f4a`. Branch off `origin/cli/yggdrasil-ii-meta-schema-alignment`, NOT local, NOT staging.
- **Remaining: Batches 2 and 3.** Neither started.

## Your task
Execute **Batch 2, then Batch 3**, from the authoritative spec `docs/agents/ygg2-cli-alignment-plan.md`
(§ BATCH 2 and § BATCH 3). Read it in full first. Each batch is its OWN PR into
`cli/yggdrasil-ii-meta-schema-alignment`, each with a **human gate + a reviewer-subagent assurance
pass** before moving on. Do NOT re-plan; do NOT widen scope.

### BATCH 2 — `gaia stats` DISPLAY (small; token/label consume)
- **File:** `src/gaia_cli/commands/stats.py` — L27–32 `TYPE_LABELS`, L45 `TYPE_ORDER` still hardcode
  `basic/extra/unique/ultimate`.
- **Do:** drop the hardcoded extra/unique/ultimate entries; consume the meta.json-driven maps from
  `formatting.py` (`TYPE_LABELS`/`TYPE_SYMBOLS`/`TIER_COLORS`) so buckets are `basic`/`fusion` only.
- **Reviewer verifies:** no `extra`/`unique`/`ultimate` TYPE-key literals remain; labels/order derived
  from `formatting.py` (not re-authored); only basic/fusion buckets; no locally-authored token/hex.
- **Test:** `pytest tests/test_stats*.py`; manual `gaia stats` → type breakdown shows basic/fusion,
  no empty extra/ultimate rows.

### BATCH 3 — `gaia graph` SVG DISPLAY + its tests + `scripts/validate.py`
- **`src/gaia_cli/graph.py`** L29–50 (`_STROKE_TINTS`, `_TYPE_LABELS`, `PALETTE`, `TYPE_ORDER`,
  `RADIUS_BY_TYPE`, `NODE_RADIUS`) + render loops L105/119/322/330/372/388 — rekey
  extra/unique/ultimate → basic/fusion; fills via `tier_hex` (NO raw hex — CI Guard A rejects it);
  legacy tier tokens survive as color aliases only.
- **`tests/test_graph.py`** — the legacy-`extra` fixture (~L63), edge assertion (~L129), and the
  PALETTE drift test (~L372–385). **NOTE:** the drift test currently asserts
  `PALETTE["extra"]["fill"] == "#c084fc"` and FAILS on the base branch (it's `#38bdf8` now). That
  failure is EXPECTED and is Batch 3's to fix — update the fixture/assertions to basic/fusion via the
  token source, not legacy hex. Ships in the SAME PR as the graph.py rekey (green-per-PR).
- **`scripts/validate.py`** (`validate_named_skills` ~L536; `main()` ~L849) — add `--named-dir`,
  default derived from `--graph` dir, wire in `main()` so a mock `--graph` validates the mock's named
  dir, not real `registry/named` (#1223).
- **Branch-scope:** `scripts/validate.py` is outside the `cli/` allowlist — this PR needs
  **`skip-scope-check`** (founder standing pre-approval covers the label; note it at the gate).
- **Reviewer verifies:** all six L29–50 dicts + six render loops rekeyed; no raw hex authored;
  `test_graph.py` green asserting basic/fusion; `validate.py --graph <mock>` emits zero spurious
  missing-ID errors; real-repo default unchanged when no flag given.
- **Test:** `pytest tests/test_graph.py`; manual `gaia graph`; `python scripts/validate.py --graph
  <mock>` clean; `python scripts/validate.py` on real repo unchanged.

## Known base-branch CI reality (do NOT chase these — they are NOT yours)
Merging into staging happens later; the maintainer (Marco) is handling final CI at the staging→main
gate. On the CLI branch today, three checks fail for reasons OUTSIDE Batches 2/3:
1. `test_graph::TestPaletteFromRegistry` PALETTE drift — **this is Batch 3's fix**; expected red until
   you land Batch 3.
2. `test_promotion::TestGradeTranslation` (×2, `_meets_evidence_floor` always True) — **FOUNDER
   DECISION NEEDED** (see below). A `schema/`-scope regression, untouchable from `cli/`.
Get your OWN batch's tests green per PR; do not try to make the whole suite green (the two evidence-
floor failures can't be fixed from a `cli/` branch).

## FOUNDER DECISIONS NEEDED (surface to Marco; do not resolve solo)
1. **`evidenceFloors` dropped in staging.** `registry/schema/meta.json` has `evidenceFloors` on `main`
   but it was dropped in `dev/yggdrasil-ii-staging` → `promotion._meets_evidence_floor` returns True
   for every level (no floor configured) → 2 pre-existing `TestGradeTranslation` failures. This is a
   `schema/`-scope data condition, out of `cli/` reach. **Decision:** file a `schema/` follow-up to
   restore the block from `main`, or ratify the removal and update the two tests? Marco said he'd
   handle CI at staging/main — confirm this is on his radar. (Flagged at the Batch 0 gate; unresolved.)
2. **`select_promotion_candidate` (interactive.py)** is now unused dead code after Batch 0 (the plan
   didn't scope its deletion; its tests in `test_interactive.py` still pass). Leave it, or delete in a
   cleanup commit? Low stakes — default: leave it unless Marco wants the tidy.

## Non-negotiable constraints (unchanged from the original handoff)
1. **Single source of truth is `taxonomy.py`. NO new resolvers.** Consume its API.
2. **Design tokens: consume only, never author.** Colors via `formatting.py::TIER_COLORS` / `tier_hex`
   (meta.json-driven). No raw hex.
3. **Green per PR** — Batch 3 folds `test_graph.py` in with the `graph.py` rekey.
4. **Migration + Ygg I warnings remain OUT** — deferred fast-follow, its own gate (see the plan).

## Housekeeping
- Work ON `cli/yggdrasil-ii-meta-schema-alignment` (feature branch per batch → PR into it), NOT a new
  `claude/` branch, NOT staging.
- Dispatch pattern that worked for Batch 0: Opus subagent, `isolation: "worktree"`, front-load the
  founder/CLAUDE.md worktree boilerplate, commit+push per logical unit, set git identity
  (`Marco Tiongson <mbtiongson1@users.noreply.github.com>`). Then INDEPENDENTLY verify the pushed tree
  (grep the invariants) before presenting the gate — don't take the subagent's self-report at face
  value.
- Avoid `_` in NEW function/variable names (dunders excepted); match each file's local convention.
- Log token spend (input/output by model + date) as a comment on umbrella #1225 on every push.
- Umbrella issue: **#1225**. Batch PRs reference it (`Umbrella: #1225`); do NOT falsely `Closes` the
  type-check issues #1220–1224 unless the batch actually resolves that specific issue (Batch 2 =
  #1222; Batch 3 = #1223 + #1224).
- Read `CLAUDE.md` §Programmatic-First and §Testing before mutating.

## Provenance
- Plan: `docs/agents/ygg2-cli-alignment-plan.md`. Batch 0 blast map:
  `founder/handovers/ygg2-batch0-no-self-promote-HANDOFF.md`. Original handoff (Batches 1→3):
  `founder/handovers/ygg2-cli-alignment-HANDOFF.md`.
- Batch 0 landed: PR #1255, merge `5067b7f4a`. Batch 1: `0377495d0`.
