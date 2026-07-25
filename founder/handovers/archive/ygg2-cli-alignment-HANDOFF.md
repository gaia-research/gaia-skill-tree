# Handoff — Ygg II CLI Alignment (PR #1248)

**For the next agent picking up `cli/yggdrasil-ii-meta-schema-alignment` (base `dev/yggdrasil-ii-staging`).**

## Your task
Execute the batch plan in [`docs/agents/ygg2-cli-alignment-plan.md`](../../docs/agents/ygg2-cli-alignment-plan.md).
Read it in full first — it is the authoritative spec, approved by the user. Do NOT re-plan; do NOT
re-explore scope that's already settled there.

**Landing order (re-sequenced 2026-07-23): Batch 1 ✅ MERGED (`0377495d0`) → Batch 0 (NEXT) →
Batch 2 → Batch 3.** Each unmerged batch is its own PR into this CLI integration branch, each with a
human gate + a reviewer-subagent assurance pass before you move to the next.

**Start with Batch 0** — "no self-promote": delete `gaia promote` + bulk `--all`, reshape the scan
"Promotion Available" card into a **levelless fusion/awaken card**, and strip the level write from
the custom `gaia fuse` flow. It reshapes the same scan surface Batch 1 touched and consumes Batch 1's
`isFusion`. Two forks the earlier handoff deferred are now RESOLVED in the plan: `gaia promote` =
**clean delete** (no shim); `promotion.py` = **delete self-promote fns, compute the awaken-card
fresh, KEEP canon-side helpers** (`checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade`,
`LEVEL_NAMES`). See the plan's "Ratified decisions" + "Planning decisions resolved this session"
sections and the Batch 0 blast table. Full blast map:
[`founder/handovers/ygg2-batch0-no-self-promote-HANDOFF.md`](./ygg2-batch0-no-self-promote-HANDOFF.md).

## Non-negotiable constraints (from the user, already decided)
1. **Single source of truth is `src/gaia_cli/taxonomy.py`. NO new resolvers.** Consume its API
   (`normalize`, `resolveDisplayBranch`, `branchFor`, `rankWord`, `medallion`, `EPOCH_YGG_*`).
   You may ADD the small `isFusion(entry)` predicate in Batch 1 — and it MUST be **structural**
   (`len(entry.get("prerequisites") or []) >= 1`), NOT `type == "fusion"`. taxonomy.py is
   deliberately type-independent ("do NOT consult `type`").
2. **Don't prefer legacy code.** Remove every `type in ('extra','ultimate','unique')` filter in
   `cli/` scope. Legacy Ygg I data stays consumable structurally (via `isFusion` / `normalize`), but
   no code path should key on the retired type literals.
3. **Design tokens: consume only, never author.** Colors come from `formatting.py::TIER_COLORS` /
   `tier_hex` (meta.json-driven, already on staging). No raw hex (CI Guard A rejects it). Legacy
   `--tier-extra/-unique/-ultimate` are color aliases only, not types.
4. **Migration + Ygg I warnings are OUT of this PR set** — deferred to a fast-follow PR (its own gate).
   Do not build the `gaia init` migration here.
5. **`scripts/validate.py` stays in the cli/ PR (Batch 3) with the `skip-scope-check` label** —
   it's outside the `cli/` allowlist; document the bypass at the gate. Batch 0's
   `docs/en/cli-reference.html` edit is likewise outside the `cli/` `*.md` glob (`.html`) — carry
   `skip-scope-check` for that one file and note it at the Batch-0 gate.
6. **Green per PR** — Batch 3 folds `test_graph.py` fixture updates in with the `graph.py` rekey so
   no PR is left red. Batch 0 deletes ~37 self-promote refs in `tests/test_promotion.py` — keep the
   canon-helper coverage green. Run full `pytest tests/` (incl. staging's `test_taxonomy_contract.py`)
   before each gate.
7. **No self-promote (Batch 0):** NO non-dev CLI path may write rank/level into
   `skill-trees/<user>/skill-tree.json`. Rank is canon-curation-only. The scan card is levelless;
   the awaken hint (`gaia fuse`+`gaia push`) shows ONLY when the generic parent is empty.

## Exact remaining surface (verified on staging — do not widen without asking)
- **Batch 1 — ✅ MERGED (`0377495d0`):** `taxonomy.isFusion` + `combinator.py`/`pathEngine.py:220`/
  `cardRenderer.py:765` consumers. DONE; Batch 0 builds on it.
- **Batch 0 (BEHAVIORAL, high sev — NEXT):** delete `gaia promote` (`commands/progression.py:21-39,66`;
  `impl.py:3701-3712`,`4458-4459`,`248`,`154`,`1436-1516`) + bulk `--all`
  (`impl.py:1203`,`1469`; `selector.py:86`); excise self-promote fns from `promotion.py`
  (`promote_from_candidates`, `promote_skill`, `write_promotion_candidates`,
  `load_promotion_candidates`, `check_promotion_eligibility`) but KEEP `checkUniqueBranchGate` /
  `_passes_rank_floor` / `effectiveGrade` / `LEVEL_NAMES`; reshape `render_promotion_prompt`
  (`cardRenderer.py:757-824`) → levelless awaken-card; rewire scan (`hook.py:111-119`,
  `impl.scan_command`) to compute the card fresh (no candidate file); reshape `fuse_command`
  (`impl.py:1960-2110`, esp. 2022-2027 strip level + `type:"fusion"`; kill 2089-2101 short-circuit);
  appraise hint (`impl.py:1427-1431`, `cardRenderer.py:475`); docs + `docs/en/cli-reference.html`
  phantom `--auto-promote` (L1077/1101/1121); tests (`test_promotion.py`, `test_card_renderer.py:15,366-404`,
  `test_cli_core.py:229`). See the plan's Batch 0 table for the full list.
- **Batch 2 (DISPLAY):** `commands/stats.py` L27–32 `TYPE_LABELS`, L45 `TYPE_ORDER` → consume formatting.py.
- **Batch 3 (DISPLAY + tests + validate):** `graph.py` L29–50 dicts + render loops L105/119/322/330/372/388;
  `tests/test_graph.py` L63/L129/L372–385; `scripts/validate.py` (`validate_named_skills` ~L536, `main()` L849 —
  add `--named-dir`, derive from `--graph`, wire in main).

## Already done on staging — DO NOT touch
`registry/nodes/` dirs, `impl.py` argparse choices, `formatting.py`,
`cardRenderer.render_fusion_diagram` default, frontend `docs/js/*` (also outside cli/ scope).
**Note:** `promotion.py` is NO LONGER fully hands-off — Batch 0 excises its self-promote fns and
KEEPS only the canon-side helpers (`checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade`,
`LEVEL_NAMES`). Do not touch those four; do not touch their importers `verification.py:70` /
`scripts/migrate_taxonomy_v6.py:60`.

## Definition of done + verification
See the plan's "Definition of Done" and "Verification" sections. Regression proof for #1220/#1221:
in a checkout, own the prereqs of a `fusion` node → `gaia scan` must show the fusion card + near-unlock
again. Batch-0 proof: `gaia promote …` → `invalid choice`; scan card quotes no level; `gaia fuse`
custom writes no `level`; grep proves `skill-tree.json` untouched by non-dev commands.
Closes #1220–#1224 (+ the self-promote-violation issue); migration tracked as the fast-follow.

## Housekeeping
- Work ON this branch (`cli/yggdrasil-ii-meta-schema-alignment`), not a new `claude/` branch.
- Per workspace rules: avoid `_` in new function/variable names (dunders excepted) — note taxonomy.py
  uses camelCase public fns (`isFusion`, matching `branchFor`/`resolveDisplayBranch`).
- Log token spend (input/output by model + date) as a PR comment on every push.
- Read `CLAUDE.md` §Programmatic-First and §Testing before mutating anything.
