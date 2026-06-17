# Handover: gaia share / install (CLI half) — Issue #128

**Status:** Ready for a Claude Code session / coding agent. Decision comment posted on #128 (2026-06-10).
**Decision (Marco, 2026-06-10):** CLI-first, then hosting option (a) — static copy-link page under `docs/share/` as a fast follow. OAuth-bound variant deferred until #155.
**Marco's amendments (2026-06-10):** install is ALREADY implemented (`gaia skills install`) — reuse it, don't rebuild. Related: #642 (skill-tree.md renders full taxonomy instead of the user's narrow path; `scripts/generateProjections.py`) — the share bundle's tree snapshot could feed that narrow-path rendering, but the tree generation has bugs. Handle as a follow-up backlog PR after the CLI half ships, not in this PR.

## Spec source

The full design lives in [#128's design-note comment (2026-05-31)](https://github.com/mbtiongson1/gaia-skill-tree/issues/128#issuecomment) — share-bundle JSON (local tree snapshot + batch-install manifest + tree.md re-render metadata), `gaia share` producer, `gaia install <bundle>` guided flowchart (All / Pick / View / Quit). Implement that note as written; this handover adds repo-rule constraints only.

## Constraints for the implementer

- Scope = CLI half only. No `docs/share/` page in this PR (fast follow, separate `design/` branch).
- Branch: `cli/...` (touches `src/`, `packages/`, `tests/`, `*.md`). PR description: `Resolves #128`... wait — the CLI half alone does not close the issue; the static page remains. Use `Refs #128`, and only the fast-follow page PR closes it. Flag this in the PR description.
- Install resolution must reuse the existing `links.github` `blob/branch/subpath` path (`src/gaia_cli/install.py::_parse_github_url`) — convert `tree/` URLs to `blob/`. Suites iterate `suiteComponents`; never require `links.github` on suites.
- Any change to a user's `skill-tree.json` during install must go through CLI verbs that write timeline events (Strict CLI-Only policy). Bundles must not hand-edit consumer trees.
- Vocabulary from `CONTEXT.md`; no rarity-axis references.
- Milestone: Phase 1 — Trust Infrastructure (#4). Move the issue to In Progress on board #2 when work starts.

## Definition of done (CLI half)

- `gaia share` emits a self-contained bundle JSON + copy-pastable one-liner.
- `gaia install <bundle|url>` renders the sharer's tree preview and walks the A/P/V/Q prompt flow.
- Summary output: installed / skipped / unresolved.
- Tests cover bundle round-trip and multi-repo bundles.
