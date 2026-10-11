---
name: gaia-badge-provision
description: >
  Procedure for controlled, human-gated outbound README badge provisioning PRs (Issue #1817).
  Preflights upstream repositories, ensures single-badge placement with deep links, and records
  campaign outcomes without automated retries or multi-badge noise.
---

# gaia-badge-provision

Standardized agent procedure for provisioning **one canonical Gaia README badge** to recognized
upstream open-source repositories (Campaign #1817).

> **Core Principle:** Outbound Gaia is opinionated and minimal. Inbound Gaia is expressive and customizable.
> **Gaia offers the seal. Upstream decides whether to wear it.**

---

## Non-Negotiable Invariants

1. **One repo $\rightarrow$ one PR $\rightarrow$ one canonical Named Skill badge $\rightarrow$ one exact deep link**.
   - Never provision multiple skill badges to one repo.
   - Never provision handle, rank-word, or total-skill-count badges outbound.
   - Never install entire badge stacks.
2. **Explicit Human Gate**:
   - Neither `PILOT_CANDIDATE` nor `READY` in the campaign manifest authorizes outbound dispatch.
   - Outbound dispatch is strictly human-gated: every target repository must be explicitly authorized by human maintainers (recorded via `--status APPROVED` or `--approved-by`) before any branch, fork, or PR is created.
3. **README-Only Diff**:
   - Diff must touch `README.md` only (or designated documentation index).
   - Zero modifications to source files, dependencies, workflows, or config.
4. **Idempotence & Terminal States**:
   - `ADOPTED` / `ALREADY_ADOPTED`: An existing Gaia badge is present and valid $\rightarrow$ record success, stop.
   - `DECLINED`: Maintainer closes or rejects PR $\rightarrow$ record declined, terminal stop. Never re-contact or argue.
   - `OPTED_OUT`: Maintainer or repository is in the opt-out list $\rightarrow$ skip unconditionally.
   - `NO_RESPONSE`: PR unmerged without reply $\rightarrow$ do not follow up, bump, or ping.
5. **No Recurring Crawler**:
   - This procedure is a finite campaign protocol, never a background daemon.
6. **Serving Contract & No False Ownership Claims**:
   - Badges are served via static Honesty Mode (`https://gaiaskilltree.com/badges/_assets/<handle>/<filename>.svg?repo=<owner>/<repo>`).
   - The `?repo=` parameter is retained for CDN / GitHub Camo cache isolation only.
   - Static SVG badges do **not** authenticate repository ownership (OAuth hardening is deferred to #494). Never claim or imply to maintainers that static badges prove repository ownership.

---

## Preflight Verification (Per Target Repository)

Before creating any branch or fork:

1. **Manifest Validation**:
   - Read `campaigns/badge-provisioning/manifest.json`.
   - Confirm target repository has been approved by human maintainers (`status == "APPROVED"`). Neither `PILOT_CANDIDATE` nor `READY` alone authorizes dispatch.
   - Confirm `canonical_skill`, `badge_url`, and `deep_link` are populated.
2. **Upstream Health & Policy**:
   - Inspect upstream README and check `CONTRIBUTING.md`, `AGENTS.md`, or README header immediately before any dispatch.
   - Check if the repository is archived or deleted.
   - If PRs for badges/docs are explicitly forbidden, record `OPTED_OUT` via CLI and stop.
3. **Existing Badge Detection** (superseded by the reconciler, Issue #2069):
   - Do not hand-grep READMEs. Run the read-only reconciler and the mandatory pre-dispatch gate below.
   - If the receipt shows `ADOPTED` / `ALREADY_ADOPTED`, a lead reviews and records the outcome via CLI; stop.

---

## Upstream Reconciliation (read-only, Issue #2069)

`scripts/plan_badge_provisioning.py reconcile` observes GitHub and compares it with the ledger.
It never mutates `manifest.json`, upstream repositories, or GitHub state. It writes only
`receipt.json` and `receipt.md`.

```bash
# One or more repositories, or the whole campaign (safe for Flash / Flash-Lite recon routines)
python3 scripts/plan_badge_provisioning.py reconcile --repo pbakaus/impeccable --repo trailhq/Graft
python3 scripts/plan_badge_provisioning.py reconcile --all --max-workers 4 \
  --out-dir campaigns/badge-provisioning/receipts/<UTC-timestamp>
```

Observed states (independent of the ledger lifecycle): `PR_OPEN`, `ADOPTED`, `ALREADY_ADOPTED`,
`PARTIAL_COVERAGE`, `CLOSED_UNMERGED`, `READY_TO_APPROVE`, `NEEDS_REVIEW`, `UNKNOWN`.
`DECLINED` / `OPTED_OUT` / `NO_RESPONSE` remain terminal outreach restrictions shown beside the state.

Reviewer rules:
- `UNKNOWN` (rate limit, 403, truncated search, unresolved identity) means *retry later*. It is never ready.
- A merged PR without the badge on the current default-branch README is `NEEDS_REVIEW`, not adoption.
- A contributor-level badge (handle / rank / skills) never proves Named Skill coverage.
- Only `READY_TO_APPROVE` may be put in front of a human for approval. Held repos
  (Graphify, #2067) are never recommended for approval.
- Routines may run `reconcile`; only the lead reviews anomalies and authorizes any ledger mutation.

---

## Mandatory Pre-Dispatch Gate (immediately before any upstream PR)

```bash
python3 scripts/plan_badge_provisioning.py predispatch --repo <owner>/<repo> --worker <id>
```

Exit `0` prints `RESERVATION_TOKEN=...`; exit `2` prints the refusal reasons. The gate takes a
per-repo reservation, refreshes upstream PR and README evidence, then checks ledger history and
human approval. It refuses duplicates, existing badges, terminal restrictions, holds, ambiguous
state and incomplete evidence. Create the PR **immediately** afterwards and record it with the
token (the token is required for `PR_OPEN`):

```bash
python3 scripts/plan_badge_provisioning.py record-outcome --repo <owner>/<repo> --status PR_OPEN \
  --pr-url <url> --reservation-token <token>
python3 scripts/plan_badge_provisioning.py release-reservation --repo <owner>/<repo> --token <token>  # if you abort
```

Residual risk: reservations are local files (`campaigns/badge-provisioning/.reservations/`), so they
serialize workers on one checkout/machine only. GitHub offers no atomic compare-and-create for PRs, so a
maintainer or another machine can still open a PR between the final check and creation. Run the
single dispatcher per campaign, and re-run `reconcile` right after dispatch (duplicate open PRs surface as
the `duplicate_open_prs` anomaly). Details: `campaigns/badge-provisioning/README.md`.

---

## README Placement Guidelines

- **Style Concordance**:
  - If the README has an existing badge row (e.g. Shields.io, Trendshift, CI badges), append the Gaia badge to that row.
  - If badges are arranged in a centered `<p align="center">` or `<div>`, conform to HTML formatting if markdown would break layout.
  - If no badge row exists, place the badge immediately beneath the primary `# <Title>` heading and description.
- **Badge Markdown Syntax**:
  ```markdown
  [![Gaia Skill: <Skill Name>](https://gaiaskilltree.com/badges/_assets/<handle>/<filename>.svg?repo=<owner>/<repo>)](https://gaiaskilltree.com/named/#explorer/<handle>/<slug>)
  ```
- **Preview & Verify**:
  - Test that the badge URL returns HTTP 200 with `content-type: image/svg+xml`.
  - Test that the deep link navigates to the specific skill in the explorer.

---

## Pull Request Framing & Etiquette

- **Branch Name**: `gaia/badge-<skill-slug>`
- **PR Title**: `docs: add Gaia Skill Tree recognition badge for <Skill Name>`
- **PR Body Template**:
  ```markdown
  Hello! 👋

  [<Skill Name>](<deep_link>) is recognized in the [Gaia Skill Tree](https://gaiaskilltree.com/) registry.

  This PR adds a minimal, verifiable README badge linking directly to the skill's evidence certificate and capability profile:

  [<badge_preview>]

  - **One badge, README-only:** No dependencies, workflows, or other files modified.
  - **Optional:** You are completely welcome to merge, relocate, restyle, or close this PR.

  Thank you for building great tools!
  ```

---

## Recording Outcomes in Manifest

After human review, PR submission, or terminal resolution, update the campaign manifest using `scripts/plan_badge_provisioning.py record-outcome`:

```bash
# 1. Record human approval before dispatch:
python3 scripts/plan_badge_provisioning.py record-outcome \
  --repo "<owner>/<repo>" \
  --status APPROVED \
  --approved-by "@mbtiongson1" \
  --notes "Human-approved for Phase 1 pilot dispatch"

# 2. Record PR submission (records PR URL, increments attempt counter, prevents duplicate dispatch):
python3 scripts/plan_badge_provisioning.py record-outcome \
  --repo "<owner>/<repo>" \
  --status PR_OPEN \
  --pr-url "https://github.com/<owner>/<repo>/pull/<number>"

# 3. Record outcome when resolved:
# If adopted/merged upstream:
python3 scripts/plan_badge_provisioning.py record-outcome \
  --repo "<owner>/<repo>" \
  --status ADOPTED \
  --notes "Merged by maintainer"

# If declined or closed without merge:
python3 scripts/plan_badge_provisioning.py record-outcome \
  --repo "<owner>/<repo>" \
  --status DECLINED \
  --notes "Maintainer declined badge PR"

# If repo policy prohibits badges or maintainer requests opt-out:
python3 scripts/plan_badge_provisioning.py record-outcome \
  --repo "<owner>/<repo>" \
  --status OPTED_OUT \
  --notes "Repository policy prohibits badge PRs"
```
