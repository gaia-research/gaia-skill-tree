# Challenge-receipt issuer for dev (single operator) — design of record

Founder rulings 2026-10-28: "approved issuer for dev"; "Right now only me ... Don't overcomplicate
the issuer approval. I'm leaning towards steward automating this". Opus design, live-verified.

- Trigger: tag push `challenge-receipt/<case>-r<n>` (only trigger that runs from dev before main).
- Workflow `.github/workflows/challenge-receipt-issuer.yml`: `prepare` (build receipt from
  `evidence/frontier-challenges/<case>/admission-request.json`, digest in step summary) → `issue`
  in environment `challenge-receipt-issuer` (founder click), inline `gh api …/runs/{id}/approvals`
  requires exactly one `approved` by user id 153011150, none rejected, attempt 1 → sealed
  `issuer-approval.json`, both files attested with SHA-pinned `actions/attest-build-provenance`.
- Verifier pins the workflow file's git blob SHA (committed config
  `src/gaia_cli/data/trust/challenge-receipt-issuer.json`). `prevent_self_review` allowed False
  (one operator). Receipt verifier must still differ from builder/contributor.
- `GitHubActionsSource.fetch` (online, at admission) + new `CommittedAttestedReceiptSource`
  (offline, every docs build, from committed `receipt/`: artifact.zip, issuer-approval.json,
  attestation.jsonl, trusted_root.jsonl). Probe: not-configured | misconfigured | offline-only | available
  (never "admitted").
- Steward plug point: a future `AuthenticatedApprovalSource` subclass replaces only
  `_authenticate_approval`; admission without the founder click needs a new founder ruling.
- Slices: `dev/yggiv-challenge-issuer` (adapter+workflow+pin+tests) → `dev/yggiv-challenge-admit-ports`
  (admit command, committed ChallengeSource, ports in generateNamedIndex, parity test) →
  `review/meta/yggiv-challenge-<case>-admission`.
- Founder settings: environment `challenge-receipt-issuer`: reviewer mbtiongson1, prevent self-review
  off, admin bypass off, deployment rule tags `challenge-receipt/*`, no secrets. Approve in web UI.
- FD-6: does the attested sealed approval snapshot count as offline approval proof? (Recommended yes:
  it is the only durable record; GitHub's approval record has unknown retention.)
- Residual: credential equivalence (this Mac's `gh` = mbtiongson1 repo+workflow scope can approve via
  API); squash dev→main breaks blob/history check (fails closed); builds need `gh` + full history;
  founder cannot admit challenges against own skills.
