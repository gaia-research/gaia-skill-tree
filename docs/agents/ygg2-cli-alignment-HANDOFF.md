# Handoff — Ygg II CLI Alignment (PR #1248)

**For the next agent picking up `cli/yggdrasil-ii-meta-schema-alignment` (base `dev/yggdrasil-ii-staging`).**

## Your task
Execute the batch plan in [`ygg2-cli-alignment-plan.md`](./ygg2-cli-alignment-plan.md) (same directory).
Read it in full first — it is the authoritative spec, approved by the user. Do NOT re-plan; do NOT
re-explore scope that's already settled there. Implement **Batches 1 → 2 → 3 in order**, each as its
own PR into this CLI integration branch, each with a human gate + a reviewer-subagent assurance pass
before you move to the next.

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
   it's outside the `cli/` allowlist; document the bypass at the gate.
6. **Green per PR** — Batch 3 folds `test_graph.py` fixture updates in with the `graph.py` rekey so
   no PR is left red. Run full `pytest tests/` (incl. staging's `test_taxonomy_contract.py`) before
   each gate.

## Exact remaining surface (verified on staging — do not widen without asking)
- **Batch 1 (LOGIC, high sev):** `taxonomy.py` (+`isFusion`), `combinator.py` L22/L58/L89 + stale
  docstrings, `pathEngine.py` L220, `cardRenderer.py` L765.
- **Batch 2 (DISPLAY):** `commands/stats.py` L27–32 `TYPE_LABELS`, L45 `TYPE_ORDER` → consume formatting.py.
- **Batch 3 (DISPLAY + tests + validate):** `graph.py` L29–50 dicts + render loops L105/119/322/330/372/388;
  `tests/test_graph.py` L63/L129/L372–385; `scripts/validate.py` (`validate_named_skills` ~L536, `main()` L849 —
  add `--named-dir`, derive from `--graph`, wire in main).

## Already done on staging — DO NOT touch
`registry/nodes/` dirs, `promotion.py`, `impl.py` argparse choices, `formatting.py`,
`cardRenderer.render_fusion_diagram` default, frontend `docs/js/*` (also outside cli/ scope).

## Definition of done + verification
See the plan's "Definition of Done" and "Verification" sections. Regression proof for #1220/#1221:
in a checkout, own the prereqs of a `fusion` node → `gaia scan` must show the fusion prompt + near-unlock
card again. Closes #1220–#1224; migration tracked as the fast-follow.

## Housekeeping
- Work ON this branch (`cli/yggdrasil-ii-meta-schema-alignment`), not a new `claude/` branch.
- Per workspace rules: avoid `_` in new function/variable names (dunders excepted) — note taxonomy.py
  uses camelCase public fns (`isFusion`, matching `branchFor`/`resolveDisplayBranch`).
- Log token spend (input/output by model + date) as a PR comment on every push.
- Read `CLAUDE.md` §Programmatic-First and §Testing before mutating anything.
