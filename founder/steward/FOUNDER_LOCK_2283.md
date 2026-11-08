# Founder lock implementation boundaries — #2283

Authority: [founder lock](https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640916880),
[hygiene receipt](https://github.com/gaia-research/gaia-skill-tree/issues/2283#issuecomment-6640982938).
These decisions are final. Implementation and independent verification are distinct.

## Issue families

The four `decisions/issue-question-q-*.json` records bind the original question and
source debt IDs using the existing schema. See `decisions/README.md` for actual
sensor/CLI/executor consumption. C1 is bounded technical work, not release
acceptance. C2/C3/C4 are holds, not new founder questions. All issue and child
payloads/history remain preserved. No live ledger or GitHub write is part of this
patch, and closure authority and the writing kill switch remain unchanged.

C2's next permitted work is an independent migration plan/compatibility audit:

- named record paths/IDs and contributor attribution; generic references;
- `suiteRef`, `suiteComponents`, umbrella payloads and child suggested IDs/sources;
- user-tree unlocked IDs and immutable timeline provenance;
- graph/named projections, contributor/skill API paths, profiles, badges and links;
- install, summon, share and other clients resolving published identifiers;
- old-to-new aliases/redirects, collision/dedup checks and round-trip compatibility
  tests proving both old and canonical handle resolution before approval.

No surface is renamed by this record. Canonical `addyosmani` does not imply that
published `addy-osmani/*` identifiers have already migrated.

C3 preserves every GBrain child and its L4 gate for the founder curation session.
Removing stale approval and skip labels is not completed intake.

## C4: source hardened, compiled synchronization deliberately gated

All eight existing `steward-{build,verify}-{claude,codex,copilot,pi}.lock.yml`
wrappers are manual `workflow_dispatch` only and have `activation.if: false`.
This is an internal pause, **not** GitHub API `disabled_manually` state. A read-only
workflow listing on 2026-11-04 reported these API entries as `active`. Do not use
that pause as false A5 closure evidence. #2126 remains GitHub-managed and open.

Verified dormant noncompliance: locks compiled with gh-aw v0.92.6 use default
warn-mode detection; the pinned `conclude_threat_detection.sh` converts missing
execution / parse failures to `warning` with exit 0 unless
`GH_AW_DETECTION_CONTINUE_ON_ERROR=false`. A successful detection job therefore
is not affirmative threat clearance. The custom `steward_outcome` persistence
steps previously checked neither the conclusion nor reason.

`.github/workflows/shared/steward-agent.md` now explicitly requests enabled,
strict (`continue-on-error: false`) threat detection and independently requires
`RUN_DETECTION=true`, conclusion `success` and an empty reason before persisting
an outcome. Offline tests execute the real source shell with synthetic inputs:
unknown, skipped, failed, warning and incomplete cases cannot persist output.
This does not prove deployed enforcement: **compiled locks are intentionally
unchanged**, still paused, and currently do not contain this source hardening.

Precise synchronization/activation gate:

1. Fresh independent Terra review of source and tests; no security sensor edits.
2. A separately authorized environment with the established **release** gh-aw
   compiler matching the reviewed gh-aw-actions tag must compile the sources,
   verify strict detection in every generated lock and preserve the founder
   pause. `gh aw` is not installed in this worker's environment; no extension was
   installed and no compilation was attempted. The wrapper generator does not
   itself encode the current manually applied activation pause, so a normal
   regeneration must not be published blindly.
3. Audit generated diff, default-disabled/manual-only invariants, detection
   engine credentials and mandatory unknown/failure denial. A compiled-source
   synchronization receipt is required; passing source tests is not that receipt.
4. Future activation needs explicit founder authorization and a verified
   non-Copilot engine with proper authorization. No Copilot billing/credential
   workaround, schedule enablement, tracker closure or activation is authorized.

Pinned upstream evidence (read-only, v0.92.6):
- `github/gh-aw` → `docs/src/content/docs/reference/threat-detection.md`
  (`safe-outputs.threat-detection.continue-on-error` contract).
- `github/gh-aw-actions` → `setup/sh/conclude_threat_detection.sh`
  (default warn mode and unavailable/parse handling).
- `github/gh-aw-actions` → `setup/js/parse_threat_detection_results.cjs`
  (affirmative no-threat conclusion is `success` with empty reason).

No workflow was compiled, enabled, dispatched or provided credentials by this
patch. No release, registry governance change or campaign completion is claimed.

## C4 synchronization (founder ruling F7, 2026-11-08)

The eight locks were recompiled from source with the release compiler gh-aw v0.92.6, and the founder pause is now encoded in source (generator `FOUNDERPAUSE`, top-level `if: ${{ false }}`, compiled to `activation.if: false`). The C4 strict-detection hardening is now in every lock. Activation is still not authorized (step 4 unchanged). Receipt and line-by-line audit: `founder/reports/steward-campaign-2026-11-05/F7_GHAW_RECOMPILE_RECEIPT.md`. The 24 missing job timeouts (activation, conclusion, steward_outcome) have no source setting in v0.92.6 and stay open as a gh-aw limitation.
