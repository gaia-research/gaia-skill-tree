## Lane B independent review: REJECTED — do not merge or migrate

Fresh independent **`openai-codex/gpt-6.1-terra`, high** reviewer completed normally (`stopReason: stop`) and **rejected exact candidate `598e45b01a848f45be100b06b094e99b5a9f4938`** in draft #2287. This reviewer route executed; it was not blocked like the OpenAI Sol/Luna implementation routes. No provider substitution for those implementation assignments occurred.

### Critical reproduced defect

`src/gaia_cli/steward/archive.py:243–269`: unbundled-artifact eligibility is not fail-closed for ordinary relative paths. A settled synthetic run with phase fields such as `receipt: receipts/proof.bin` and `evidence: evidence/build-output` passes `phase_hold` and is selected/migrated. Hot phases become empty, while archive retrieval returns only the strings; referenced bytes were never opened or bundled. The defect also concerns arbitrary extensions and unknown reference-bearing keys.

**Reproduction used a disposable bare Git remote only. No actual shared migration or evidence loss occurred.** Content-addressed JSON is not proof of external artifact-byte portability. Required remedy is a conservative schema-aware allowlist/explicit hold for unknown or nonportable phase fields, or safe bounded byte bundling with hash/readback verification—not an expanded filename-extension blacklist.

### Independent evidence and limits

- **429 selected tests passed independently** (288 archive/ledger/fullrun + 141 CLI/scenario/coverage/report-input), diff-check passed; tracked review worktree clean.
- These successes include useful V1/V2 compatibility, hydration/unknown-coverage, >2 MiB, provenance, rollback, CAS and corruption regressions, but do **not** cure the new counterexample.
- Full Steward suite was **not** run. Actual shared archive migration, fresh-host evidence retrieval and forward rollback were **not** performed.
- Actual original baseline independently confirmed **0 of 13 terminal runs eligible**. Some immutable historical sensor/observation fields are over-broadly treated as lifecycle holds, but an in-process diagnostic bypass of that phase predicate **still left all 13 ineligible under other checks**. Thus phase over-conservatism alone does not justify making any real baseline run eligible. Pending decisions/work must stay protected.

### Status and next gate

#2287 remains draft, **REJECTED / DO NOT MERGE**. Exact implementation history is preserved. Sol implementation and C1–C4/D1–D3/CI repairs remain quota-blocked; no corrective patch or new acceptance is fabricated. Resume requires quota reset or explicit operator approval of another implementation auth/provider route, then repair + fresh independent exact-SHA review + actual authorized migration evidence. A no-op preview is not completion.

Full review saved as `.gaia/steward/campaigns/2026-11-05/ledger-recovery/lane-b-independent-final-review.md`. Existing independently verified Lane A persistence and accepted one-line Class B correction are separate; the latter is still awaiting integration/CI resolution, not marked closed. No main merge, issue closure, Class C adjudication, trust/rank mutation, workflow activation, deployment, history deletion or live archival write occurred.
