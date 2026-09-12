# Handover — PR #1792, G1 (#1784) implementation in progress

**Session ran out of tokens mid-G1.** Nothing broken is on disk — an in-progress
edit to `src/gaia_cli/prefill.py` was reverted before this checkpoint (it
referenced a `ReasonCodes` class that hadn't been added to `intakeAdapter.py`
yet). Working tree is clean; `tests/test_dev_prefill.py` and
`tests/test_validate_intake_packets.py` pass (24 passed) at HEAD.

## State

- **Branch**: `fix/pipeline-friction-findings-graft-intake`
- **PR**: #1792 (draft), body has the full 45-step HEAVIER plan approved by the
  user ("proceed.")
- **Pushed through G4** (#1786, evidence lake candidate ingestion) — commit
  `c6e36acfe`. G2, G3, G6, G7 were completed in earlier turns of this same PR
  (see PR body / commit log for the full list).
- **Remaining**: G1 (#1784) — in-progress research, no code changes yet
  committed. G5 (#1787) — not started at all.
- **HEAVIER's approved plan** for G1 (steps 1–9, paraphrased from the PR body
  `## Plan` section — read that section verbatim before resuming, it's the
  actual source of truth):
  1. Stamp `artifactGate` in `gaia dev prefill` after actually fetching/parsing
     the candidate's upstream `SKILL.md` (currently a no-op / always null).
  2. Populate all v2 packet fields prefill currently omits: `source.hostRepository`,
     `source.fetchedAt`, `source.contentSha256`, `source.frontmatter`,
     `genericSnapshot` (+`mappingOptionsSha256`), before lifecycle can honestly
     advance past `discovered`.
  3. Advance prefill's emitted lifecycle from the bogus `["discovered","deferred"]`
     (not even a valid subsequence of the canonical ladder) to the real
     stages prefill actually completes:
     `["discovered","fetched","parsed","normalized","deduped","mapped","deferred"]`
     — or short-circuit to `["discovered","fetched","rejected"]` +
     `decision.value=NOT_A_SKILL` when the fetched artifact isn't a real
     skill (`artifactGate != "valid-skill"`), per CURATION-CORE precedence rule 1.
  4. Make `selfValidatePacket` failures fatal end-to-end — note: `prefillCommand`
     ALREADY does `if errors: return 1`, so this checkbox is arguably closed by
     construction; the real gap is that `selfValidatePacket(packet)` is called
     with `trusted_generics=None`, which will now *always* fail
     (`UNTRUSTED_GENERIC_SNAPSHOT`) once step 3 lands, because the validator's
     `mapped` block unconditionally requires a list. Fix: thread
     `trustedGenerics=(packet.get("genericSnapshot") or {}).get("generics")`
     through both `prefill.selfValidatePacket` (new optional param) and
     `prefill.validateDiscoveryPackets` (used by `gaia dev validate --intake`,
     covered by `tests/test_validate_intake_packets.py` — **do not break this
     file**, it currently expects `trusted_generics=None` semantics for a
     packet whose lifecycle has NO `mapped` stage at all, so it's unaffected
     as long as the fix is "use the packet's own snapshot when present," not
     "always require a snapshot").
  5. Add a `REASON_CODES` enum/class to `src/gaia_cli/intakeAdapter.py` (referenced
     but not yet added) covering both the CURATION-CORE worker-side codes
     (`NOT_A_SKILL`, `DUPLICATE_EXACT`, `DEFER_AMBIGUOUS_BUNDLE`,
     `NEW_GENERIC_NO_MATCH`, `MAP_EXISTING_GENERIC`, `DEFER_WEAK_ADJUDICATION`,
     `DEFER_INVALID_PACKET`, `PREFILL_AWAITING_WORKER`) and two new L4-side codes
     (`L4_RATIFIED_MAP`, `L4_RATIFIED_NEW_GENERIC`) — replacing the currently
     hand-invented `L4_RATIFIED_NEW_GENERIC` string operators were typing by hand.
  6. New CLI verb `gaia dev ratify <packet-path> --decision {MAP,NEW_GENERIC}
     --generic-id ... --generic-name ... --generic-description ...
     --generic-type {basic,fusion} [--prereqs a,b,c] --contributor ...
     --skill-name ... --skill-file-url ...` — turns a `deferred`+`mapped`
     packet into a `review-ready` packet carrying `l4Resolution`, using
     `intakeAdapter.validateL4Resolution` + `prefill.selfValidatePacket`
     (fatal on any error, nothing written on failure). This closes the "operator
     hand-edits lifecycle/decision/reasonCode" footgun from the issue.
  7. Register `ratify` as a **mutating** dev verb: add to the `MUTATING_DEV_COMMANDS`
     local set inside `DevCommand.execute()` in
     `src/gaia_cli/commands/dev/__init__.py` (⚠ **this is the live dispatcher** —
     `discover_commands()` in `main.py` wires `Command` subclasses; the
     `MUTATING_DEV_COMMANDS` frozenset + old `elif args.command == "dev":` block
     in `impl.py` around line 254/4269 is DEAD CODE not reachable from `main()`,
     confirmed by reading `main.py`'s `get_parser()` — don't bother editing it,
     it'd be scope creep on unreachable code). Wire `add_parser("ratify", ...)`
     next to `dev_prefill` in `DevCommand.configure()`, add the dispatch
     `elif dev_cmd == "ratify":` in `execute()`, and mention it in `DEV_USAGE`.
  8. New file `src/gaia_cli/commands/dev/ratify.py` with `ratifyCommand(args)`
     implementing the above.
  9. Tests: extend `tests/test_dev_prefill.py` (already exists — has extensive
     coverage of `rankGenericOptions`/`buildPrefillPacket`/etc; **the existing
     `TestBuildPacketSelfValidates` and `TestDeterminism` classes call
     `buildPrefillPacket(...)` without a `registryPath` and call
     `selfValidatePacket(packet)` with no second arg** — these WILL need
     updating once `buildPrefillPacket` gains a `registryPath` param (needed to
     build `genericSnapshot` from the real `registry/gaia.json`) and
     `selfValidatePacket` gains an optional `trustedGenerics` param. This is an
     explicitly-flagged `⚠ breaking` step in the approved plan — updating the
     existing tests to the new contract is expected, not a regression to avoid.
     Also add `tests/test_dev_ratify.py` covering: MAP ratification, NEW_GENERIC
     ratification (basic + fusion prereqs), rejection when `--generic-id` isn't
     in the packet's own `mappingOptions` (MAP path), rejection when the packet
     isn't `deferred`+`mapped` yet, and that `gaia dev ratify` is gated by
     `require_operator()` (same pattern as other mutating dev verbs' tests —
     grep `GAIA_OPERATOR_OVERRIDE` usage in existing dev-verb tests for the
     idiom).

## Key research already done (don't re-derive)

- `validate_discovery_packet.py`'s `mapped` block (triggered whenever `"mapped"
  in lifecycle`) unconditionally requires `trusted_generics` to be a list, else
  appends `UNTRUSTED_GENERIC_SNAPSHOT`. This is the crux of why advancing
  prefill's lifecycle to include `"mapped"` will break self-validation unless
  `trustedGenerics` is threaded through from the packet's own frozen
  `genericSnapshot.generics` — i.e. prefill validates itself for *internal
  consistency*, not against the live registry (matches the existing docstring
  on `validateDiscoveryPackets`).
- `genericSnapshot.generics` entries need a literal `"kind": "generic"` field —
  the validator filters on it (`generic.get("kind") == "generic"`) when
  computing `generic_ids` for the `option_ids <= generic_ids` subset check. Any
  test fixture / synthetic `registry/gaia.json` used to build a snapshot must
  produce ids that are a superset of whatever ids `mappingOptions` carries (i.e.
  the same ids the embeddings fixture uses), or self-validation will fail with
  `INVALID_GENERIC_SNAPSHOT`.
- `intakeAdapter._canonicalDigest(value)` (sha256 of
  `json.dumps(value, sort_keys=True, separators=(",",":"))`) is the exact
  digest function to reuse for both `genericSnapshot.contentSha256` and
  `genericSnapshot.mappingOptionsSha256` — don't reimplement it in prefill.py,
  import it.
- GitHub blob URL → raw fetch: no existing helper in the repo for this; will
  need a small regex
  `^https://(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/blob/(?P<branch>[^/]+)/(?P<path>.+)$`
  to derive both `hostRepository` (`https://github.com/<owner>/<repo>`) and the
  raw-content URL (`https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>`).
  `fetchCandidateSource(canonicalUrl, fetcher=None)` should take an injectable
  `fetcher: str -> bytes` callable (default = a plain `urllib.request.urlopen`)
  so tests never hit the network.
- Frontmatter parsing: no path-based helper reusable as-is (`_parse_md` in
  `commands/dev/helpers.py` takes a `Path`, not a string) — write a small
  string-based YAML-frontmatter parser in `prefill.py` (`yaml.safe_load` on the
  text between the first two `---` delimiters).
- `CURATION-CORE.md` (`.claude/skills/gaia-curate/CURATION-CORE.md`, mirrored
  under `.agents/`) is the authoritative contract for lifecycle stages,
  precedence rules, and reason codes — already fully read this session, quoted
  above. Read it again if anything is unclear rather than guessing.
- The real subcommand dispatcher is the `Command` class registry
  (`src/gaia_cli/commands/dev/__init__.py` → `DevCommand`), NOT the legacy
  `elif` chains in `impl.py`. Confirmed via `main.py`'s `discover_commands()` +
  `get_parser()`. Don't waste time wiring the dead `impl.py` path.

## Next step for the resuming agent

Re-read the PR #1792 body's `## Plan` section (`gh pr view 1792 --json body`)
for the verbatim approved wording, then implement G1 steps 1–9 above in
`src/gaia_cli/prefill.py`, `src/gaia_cli/intakeAdapter.py`,
`src/gaia_cli/commands/dev/ratify.py` (new), `src/gaia_cli/commands/dev/__init__.py`,
`tests/test_dev_prefill.py` (extend), and `tests/test_dev_ratify.py` (new). Run
`env -u PYTHONPATH python3 -m pytest tests/test_dev_prefill.py
tests/test_validate_intake_packets.py tests/test_dev_ratify.py -q` before
committing. Commit as one atomic step (or a couple, per plan-step granularity),
push to `fix/pipeline-friction-findings-graft-intake`, then move on to G5
(#1787) — entirely unstarted (evidence type gaps: curation-guidelines dedup
correction, canonical-URL-per-type table, `npm-downloads` evidence type in
BOTH schema copies + `trustMagnitude.py` scoring lockstep, `engagement` lane,
new CLI flags, TM regression tests).

After all 45 steps land: run `python3 scripts/build_docs.py --check` (must
exit 0), then print the STOP HOOK M2 banner and end the turn per
`.claude/skills/feature-pipeline/SKILL.md` — do not skip straight to Phase 3.
