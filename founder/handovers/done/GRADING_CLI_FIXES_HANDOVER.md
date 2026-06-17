# Pre-PR-3 Patch: Grading CLI + Schema fixes (blocker for the #646 backfill)

**Status:** Blocker documented 2026-06-14 (Marco). Must land **before** PR-3 (evidence backfill).
**Refs #646.** Governing specs: `handovers/TRUST_IMPL_HANDOVER.md`, `handovers/TRUST_MODEL_RFC.md` v2.

## Why this exists (the blocker)

Two gaps in merged PR-2 (#686, `e6ef540c`) make PR-3's "re-grade existing evidence via the PR-2 CLI flow" non-executable as written. Both verified against `main` 2026-06-14:

| # | Gap | Evidence (verified) | Impact |
|---|---|---|---|
| 1 | `gaia dev evidence` is **append-only** — no way to set `type`/`grade`/`trustNumber` on an *existing* entry | `meta_evidence_command` in `src/gaia_cli/commands/dev.py` does `evidence.append(evidence)` for both named (md frontmatter) and generic (node JSON); no `--index`/`--source` match, no dedup | Running it over the ~220 existing entries **doubles** them (~440, duplicate `source`s) instead of re-grading in place + keeping `class` — the exact opposite of PR-3's DoD |
| 2 | `evidence_graded` is fired but **not in the schema's timeline `action` enum** | The enum in `registry/schema/skill.schema.json` (≈L218) and `registry/schema/namedSkill.schema.json` lists `…evidence_added, evidence_removed, type_change, verified, disputed` — **`evidence_graded` is absent (count 0 in both)**; PR-2's `dev.py` fires `append_skill_event(..., "evidence_graded", …)` | **Live regression on `main`:** any `gaia dev evidence --trust N` today writes an `evidence_graded` event that **fails `gaia validate`**. PR-3's DoD requires validate green |

Gap 2 is independent of PR-3 — it breaks the grading flow for everyone *right now*. Treat it as urgent.

## Decision / recommendation — fix the CLI first

The repo's **Programmatic-First / "Close the Gap — fix the CLI first"** policy (both `CLAUDE.md`s) beats PR-3's direct-edit escape hatch here: 220 canonical entries, each needing an auditable `evidence_graded` timeline event, is exactly the case the policy is for. Direct-editing 220 records by hand is error-prone, un-auditable, and would still trip the validate bug.

**Recommended: two small patch PRs precede PR-3.** This also *resolves* the tension Marco flagged — because the CLI changes live in their own PRs, **PR-3 stays pure `review/meta/` data with no CLI changes**, honoring the "no CLI changes on the review/meta branch" rule cleanly.

> Branch-scope note: Fix 2 touches `registry/schema/` (**must** be a `schema/` branch) and Fix 1 touches `src/` (**must** be a `cli/` branch). CI `branch-scope.yml` won't allow both in one branch — so split, or use a single branch with the `skip-scope-check` label. Splitting is recommended (the schema fix is trivial and urgent on its own).

---

## Patch A — schema enum (`schema/` branch, e.g. `schema/evidence-graded-action`) — URGENT

Add `"evidence_graded"` to the timeline `action` enum in **both**:

- `registry/schema/skill.schema.json` (the `timeline.items.properties.action.enum`, ≈L218–234)
- `registry/schema/namedSkill.schema.json` (the matching enum, ≈L252–268)

Place it next to `evidence_added` / `evidence_removed` for readability. This is **additive and non-breaking** (no existing data invalidated). Update `CONTEXT.md` only if timeline actions are enumerated there.

- **Acceptance:** `gaia validate` passes on a tree that contains an `evidence_graded` event; full suite green.
- **Versioning:** bump via `gaia release patch --sync` (schema/cli-npm/mcp/gaia.json lockstep; pre-commit hook enforces). This is **not** the `class` removal (that's still next-major).
- `Refs #646`.

## Patch B — in-place re-grade for `gaia dev evidence` (`cli/` branch, e.g. `cli/evidence-regrade`)

Make grading an existing entry idempotent instead of additive. Recommended shape:

- Add an **update mode** to `gaia dev evidence`: when an entry with the same `source` already exists on the target skill, **update it in place** — set `type`, `trustNumber`, and derived `grade`, **preserving the existing `class`** and any other fields — rather than appending.
- Make the intent explicit and back-compatible: a `--update` (or `--regrade`) flag, with `--source URL` (and optional `--index N` for disambiguation) to select the entry. **Mirror the selection semantics already in `gaia dev rm-evidence`** (`--index | --source`). Without `--update`, keep today's append behavior so nothing else changes.
- **Idempotent:** re-running the same command produces no duplicate and no second timeline spam.
- Fire `evidence_added` only on a genuine new add; fire **`evidence_graded`** on the in-place grade (the action Patch A legalizes — reuse it, don't invent a new enum value).
- **Keep `class` intact** on updated entries (PR-3 DoD).

- **Acceptance / tests:** in-place update writes type/grade/trustNumber without duplicating the entry; `class` preserved; re-run is a no-op (idempotent); `--source` not-found errors cleanly; `evidence_graded` event recorded; full suite green; Verifier gate unchanged.
- `Refs #646`.

## After both patches land

PR-3 (`handovers/PR3_BACKFILL_HANDOVER.md`) becomes executable as **pure data**: iterate the ~220 entries, `gaia dev evidence --update --source <url> --type <t> --trust <n>` each one (re-grade in place, `class` retained), every change carrying an `evidence_graded` event, and `gaia validate` green at the end.

## Optional follow-up

Worth a one-line heads-up on #686 or #646 that PR-2 shipped a latent `evidence_graded`/validate bug, fixed in Patch A — so the history is honest. (Orchestrator to draft + post on Marco's approval, per the draft-first rule.)
