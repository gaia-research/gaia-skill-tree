# Handoff — Leonxlnx `/cook` full pipeline (tracking #2446)

**Status: BLOCKED: L4 PENDING** (2026-11-14). Phases 0–1 done; Phase 2 awaits a human.

## Done
- Phase 0 ev-scout (Haiku worker): `ev-scout-packet.md` — repo facts, unverified literature leads, counterevidence, safety observations. Context only.
- Phase 1 /gaia-curate (Strategy A): `gaia dev prefill` → `registry-for-review/discovery-packets/leonxlnx-cook-4043b9f0….json` (validator: VALID discovery-packet-v2) + `assessment-receipt.json` (advisory). Packet intentionally left as unmodified prefill output (`DEFER / PREFILL_AWAITING_WORKER`); `gaia dev ratify` converts deferred→review-ready itself, and editing it would invalidate freshness binding.
- Pre-checks: no existing `leonxlnx/cook` named entry, no duplicate/pending intake (open `intake` issues scanned; none for cook), no `cook` branch/PR. Existing Leonxlnx skills reviewed (`unlazy`→task-depth-enforcement 3★, `taste-skill`→design-generation 4★, `image-to-code-skill`→vision-qa 2★).
- Upstream pinned at `b23cac6fd9439dfddcab61b14808e7bf72549b46` (single commit), MIT. No upstream command was executed.

## Not done (by design)
No ratify, no `gaia push`, no intake issue/batch, no label changes, no registry/evidence/TM/star changes, no PR. `gaia dev ratify` requires `--authorization-envelope` from an independent human ceremony; none exists and agents must not mint one.

## Resume
1. Human decides per `L4-REVIEW.md` (A recommended) and issues the trusted authorization envelope.
2. Re-check drift: `gaia dev list --generic --json` unchanged for the 3 prereqs / no generic id collision; if catalog or source drifted, rerun `gaia dev prefill` (same args as status.json source) — receipt digest binds catalog.
3. `GAIA_OPERATOR_OVERRIDE=1 gaia dev ratify <packet> --decision NEW_GENERIC --generic-id reference-guided-visual-iteration --generic-name … --generic-description … --generic-type fusion --prereqs code-generation,vision-qa,evaluate-output --contributor leonxlnx --skill-name cook --assessment <receipt> --reviewed-by <human> --approval-ref <ref> --reason … --authorization-envelope <env> --acknowledge-human-review`
4. `python3 .claude/skills/gaia-curate/scripts/validate_discovery_packet.py --generic-snapshot <fresh snapshot> <packet>`; `git checkout -b review/meta/leonxlnx--cook`; `gaia push --from-file <packet> --dry-run`; then real push; commit/push carrier branch. One intake only; no hand-cut PR.
5. Maintainer applies `intake:topology-approved` → Phase 4 (/ev-pipeline: collection, star verification for the 386★ claim, adversarial audit, link validation — note the missing `color_check.py`) → `intake:evidence-ready/approved` (maintainer) → canonical `review/meta/intake-<N>` PR → /gaia-ingest, /trust-appraise, human calibration approval → independent fresh-Sonnet review → merge → /gaia-intake-close → close #2446.

## Notes
Scratch upstream copy (untrusted, not committed): session scratchpad `cook-src/`; re-fetch with `gh api repos/Leonxlnx/cook/contents/<path>?ref=b23cac6f…`. Pi subagent preflight is not applicable in this Claude Code harness; the scout ran as a Haiku subagent (model override `haiku`) with no fallback. `generated-output/` is gitignored; tracked copies of status/scout/assessment live in this directory. `status.json` here mirrors `generated-output/curate-discovery/20261114-leonxlnx-cook/status.json`.
