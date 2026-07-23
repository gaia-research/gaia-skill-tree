# Batch 0 Handoff — "No Self-Promote" ratification + fuse/scan reshape

**For the planner replanning [`docs/agents/ygg2-cli-alignment-plan.md`](../../docs/agents/ygg2-cli-alignment-plan.md).**
This document does NOT change the plan — it feeds the replanning session. Fold its ratification +
blast map into the single authoritative plan as a new **Batch 0** that lands *before* Batch 2/3
(Batch 1 is already merged: `0377495d0`). Then resume the batch sequence.

## Why this exists

The 4★-fusion dry-run during Batch 1 surfaced that the "Promotion Available" card mislabels a
unique-branch fusion. Chasing it revealed the card is a symptom of a deeper contradiction: the
non-dev CLI has a **fully-wired, ungated self-promote mechanic** that writes rank directly into the
user's `skill-tree.json`. Marco ratified the correct model in this session (see Decisions).

## RATIFIED DECISIONS (Marco, 2026-07-23 — do not re-litigate)

1. **No user-facing self-promote.** Rank/level is assigned ONLY by the canon tree's curation
   pipeline (dev-gated, out of scope for this non-dev sweep). The local CLI's job ends at *propose*.
   The player loop is:
   ```
   gaia scan   → discover fusions you have the components for
   gaia fuse   → declare/structure LOCALLY (ties to gaia-research/skill-fuse)
   gaia push   → propose the structure to canon; curation "awakens" it (→ assigns rank)
   ```
2. **`gaia promote` is DEAD.** Ratified for removal. It self-assigns rank with no dev gate — the
   core violation. (Fate — full delete vs. redirect-alias — is a planning decision; Marco said
   "dead", lean delete.)
3. **The bulk auto-promote (`gaia promote --all` → `promote_all_candidates`) dies too.** There is no
   *real* `--auto-promote` flag in code — it is phantom doc drift in `docs/en/cli-reference.html`
   (L1077/1101/1121). The actual bulk mechanic is `--all`; kill it.
4. **The scan card always shows the fusion** (so the user sees a real skill exists), regardless of
   whether it has a named implementation. The **"awaken" message** (`gaia fuse` + `gaia push`) only
   appears when the **generic parent is empty** (no named implementation claimed yet).
5. **No star level / no Extra·Unique·medallion decoration on the card.** Suite/unique is a canon 4★+
   concept — irrelevant at proposal time. The card quotes no level. (This dissolves the original 4★
   mislabel bug — there is no level line left to mislabel.)
6. **`gaia fuse` level nuance (double-checked, confirmed):**
   - **Canon-tied fusion** (a detected fusion mapped to a canon skill, `ctx.is_origin(sid)`): may
     **inherit the canon levelFloor** — this mirrors canon, it is NOT self-declaration. Keep.
   - **Custom / starless fusion** (the interactive "new" flow, `ctx.novel_ids`): **NO level added.**
     Currently `impl.py:2022-2027` writes `type:"extra"` + `level: max_stars_str` to
     `.gaia/custom_state.json` — strip the level; also rekey `type:"extra"` → `"fusion"`.
   - **The `fuse` → `promote_from_candidates` short-circuit** (`impl.py:2089-2101`) dies with promote.
7. **Schema backing:** `registry/schema/meta.json → types.minPrereqs = {basic:0, fusion:1}` is the
   idempotent structural definition of a fusion — matches Batch 1's `taxonomy.isFusion`
   (`len(prereqs) >= 1`). The bucket concept is schema-codified; consume it, don't re-author.

## OPEN DESIGN QUESTION — resolve IN the planning session (not decided here)

`promotion.py`'s `LEVEL_NAMES` / `check_promotion_eligibility` / `write_promotion_candidates` /
`load_promotion_candidates` machinery is imported on the **scan path** (`hook.py:111-119`,
`cardRenderer.py:772`) — NOT dev-gated. When self-promote is stripped, these lose their consumer.
**Fork the planner must decide:**
- **(a) Delete outright** — scan stops emitting a candidate file; the new awaken-card is computed
  fresh from owned-prereqs + empty-parent signal.
- **(b) Repurpose** the candidate file into "fusion-proposal candidates" that feed the new
  awaken-card.
This choice determines how much of `promotion.py` survives. **Keep regardless:** the canon-side
gate/grade helpers `checkUniqueBranchGate`, `_passes_rank_floor`, `effectiveGrade` (used by
`verification.py:70` and `scripts/migrate_taxonomy_v6.py:60`).

## BLAST MAP (verified read-only, 2026-07-23) — Batch 0 surface

| Action | File:line |
|---|---|
| Kill `gaia promote` command (class + registration) | `commands/progression.py:21-39,66` |
| Kill legacy argparse + dispatch for promote | `impl.py:3701-3712`, `impl.py:4458-4459` |
| Remove `promote` from PUBLIC_COMMANDS + usage text | `impl.py:248`, `impl.py:154` |
| Kill bulk `--all` auto-promote | `impl.py:1203` (`promote_all_candidates`), `impl.py:1469`, `commands/progression.py:30`, `selector.py:86` |
| `promote_command` implementation | `impl.py:1436-1516` |
| Excise self-promote fns; keep canon helpers | `promotion.py` (`promote_from_candidates`:413, `promote_skill`:469, `write_promotion_candidates`:360, `check_promotion_eligibility`:156) |
| Reshape `fuse_command` (decisions #6) | `impl.py:1960-2110` (esp. 2022-2027 custom levelless+`fusion`; 2057-2067 canon mirror; 2089-2101 kill short-circuit) |
| Reshape scan card → fusion/awaken card (decisions #4,#5) | `cardRenderer.py:757-824` (`render_promotion_prompt`), `hook.py:111-119` |
| Scan: stop emitting promote-candidates as a promote trigger | `impl.scan_command`, `write_promotion_candidates` |
| appraise: drop "promotable to Level N" hint | `impl.py:1427-1431`, `cardRenderer.py:475` |
| Phantom `--auto-promote` doc drift | `docs/en/cli-reference.html:1077,1101,1121` |
| Docs | `README.md:283,306`; `DESIGN.md:116-117,177-178,356,361,490`; `CLAUDE.md:162,175,192,237`; `src/gaia_cli/CLAUDE.md` (Authorization section — "promote … never gated"); `DEV.md:92,122`; `skill-trees/README.md:50` |
| Tests | `tests/test_promotion.py` (37 refs), `tests/test_card_renderer.py:15,366-404`, `tests/test_cli_core.py:229` |

**Aligned / no change:** `gaia push`, `gaia propose` (proposal-to-canon), `gaia dev fuse` (dev-gated,
never mutates user trees). `packages/cli-npm/cli/` is a stale partial copy with no promote wiring.

## Sequencing note

Batch 0 reshapes the same `gaia scan` surface Batch 1 touched, so it lands next (before Batch 2's
`gaia stats` and Batch 3's `graph`/validate work). Batch 1 (`0377495d0`, structural `isFusion`)
stays — Batch 0 builds on it (the awaken-card uses `isFusion` + empty-parent signal). This widens
the PR set beyond the original pre-approval; the planner should re-scope the plan's batch table and
Definition of Done accordingly, and confirm the `gaia promote` fate (delete vs. redirect) with Marco.

## Provenance

- Batch 1 landed: commit `0377495d0`, PR #1248 (base `dev/yggdrasil-ii-staging`).
- Blast radius mapped by a read-only Explore agent this session; findings verified against the
  source before writing this doc.
- Original plan: `docs/agents/ygg2-cli-alignment-plan.md`. Original handoff:
  `founder/handovers/ygg2-cli-alignment-HANDOFF.md`.
