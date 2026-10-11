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

1. **One repo $\rightarrow$ one approved outreach attempt $\rightarrow$ one PR $\rightarrow$ one or more eligible Named Skill badges**.
   - Enumerate the full eligible skill set from `skillsByRepo[repo]`.
   - Resolve each skill against contributor metadata and deduplicate by Named Skill ID.
   - Verify rank, attribution, SVG asset, and skill deep link.
   - Distinguish separate Named Skills from alternate badge styles: seals are alternative presentations of recognition, not separate earned skills.
   - Never provision handle, rank-word, or total-skill-count badges outbound.
   - README presentation adapts to eligible skill count:
     - **1 skill**: One Named Skill badge.
     - **2–4 skills**: Compact row of distinct skill badges.
     - **5–8 skills**: Small labeled badge section (`### Gaia Skill Tree Recognition`).
     - **9+ skills**: Concise curated display and link to the full recognized collection (the outreach message notes displayed badges are a curated selection).
   - Store exact offered skill IDs and chosen badge presentation in the campaign manifest and ledger history.
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
3. **Existing Badge Detection**:
   - Fetch upstream README (`raw.githubusercontent.com` or via GitHub API).
   - Search for `gaiaskilltree.com/badges/`.
   - If already present, record `ADOPTED` via CLI and stop.

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
