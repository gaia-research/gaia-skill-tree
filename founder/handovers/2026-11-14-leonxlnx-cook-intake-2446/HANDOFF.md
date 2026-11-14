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

## Update 2026-11-14 — ruling A received; trusted route unavailable
Reviewer replied `A` (see `FOUNDER-RULING.md`). The protected-authorization verifier is intentionally disabled in code, so no envelope can be issued by anyone today; ratify/trusted push stay fail-closed. Status remains BLOCKED: L4 PENDING (authorization infrastructure), not a topology question.

## Routes
1. **Wait** for the protected authorization workflow to be wired, then resume at Resume step 3 (unchanged).
2. **Unreviewed-proposal route** (documented in CURATION-CORE: ordinary YAML/issue-form submissions are proposals, not trusted post-L4 intake): submit one intake carrying ruling-A topology via the intake template/`gaia push --from-file skills.yml`; the maintainer-only `intake:topology-approved` label is then the human gate. Needs the reviewer's explicit OK because it departs from the "trusted L4 packet" requirement and must not duplicate any later trusted submission.

## Update 2026-11-14 (late) — lightweight L4 route taken
Ruling 4 recorded. Intake opened via `gaia push --from-file intake-skills.yml --yes`: **#2452**, batch `content-4bf605e8…-from-file`, carrier `review/meta/leonxlnx--cook` @ `c2fde76` (Batch Branch row matches; keep branch alive). L4 decision recorded as an additive comment on #2452 (body untouched). Status: awaiting maintainer `intake:topology-approved`; not self-applied. Resume steps 3–4 above are superseded; next = Phase 4 `/ev-pipeline` after the label. Do not push a second intake.
