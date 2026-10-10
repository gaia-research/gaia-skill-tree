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
   - `READY` in the campaign manifest **never** authorizes outbound dispatch.
   - Every batch must be explicitly authorized by human maintainers.
3. **README-Only Diff**:
   - Diff must touch `README.md` only (or designated documentation index).
   - Zero modifications to source files, dependencies, workflows, or config.
4. **Idempotence & Terminal States**:
   - `ALREADY_ADOPTED`: An existing Gaia badge is present and valid $\rightarrow$ record success, stop.
   - `DECLINED`: Maintainer closes or rejects PR $\rightarrow$ record declined, terminal stop. Never re-contact or argue.
   - `OPTED_OUT`: Maintainer or repository is in the opt-out list $\rightarrow$ skip unconditionally.
   - `NO_RESPONSE`: PR unmerged without reply $\rightarrow$ do not follow up, bump, or ping.
5. **No Recurring Crawler**:
   - This procedure is a finite campaign protocol, never a background daemon.

---

## Preflight Verification (Per Target Repository)

Before creating any branch or fork:

1. **Manifest Validation**:
   - Read `campaigns/badge-provisioning/manifest.json`.
   - Confirm status is `PILOT_CANDIDATE` or human-approved `READY`.
   - Confirm `canonical_skill`, `badge_url`, and `deep_link` are populated.
2. **Upstream Health & Policy**:
   - Check if the repository is archived or deleted.
   - Inspect `CONTRIBUTING.md`, `AGENTS.md`, or README header for contribution restrictions.
   - If PRs for badges/docs are explicitly forbidden, mark `OPTED_OUT` and stop.
3. **Existing Badge Detection**:
   - Fetch upstream README (`raw.githubusercontent.com` or via GitHub API).
   - Search for `gaiaskilltree.com/badges/`.
   - If already present, mark `ALREADY_ADOPTED` in manifest and stop.

---

## README Placement Guidelines

- **Style Concordance**:
  - If the README has an existing badge row (e.g. Shields.io, Trendshift, CI badges), append the Gaia badge to that row.
  - If badges are arranged in a centered `<p align="center">` or `<div>`, conform to HTML formatting if markdown would break layout.
  - If no badge row exists, place the badge immediately beneath the primary `# <Title>` heading and description.
- **Badge Markdown Syntax**:
  ```markdown
  [![Gaia Skill: <Skill Name>](https://gaiaskilltree.com/badges/<handle>/<filename>.svg?repo=<owner>/<repo>)](https://gaiaskilltree.com/named/#explorer/<handle>/<slug>)
  ```
- **Preview & Verify**:
  - Test that the badge URL returns HTTP 200 with `x-gaia-badge-state: valid`.
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

After PR submission or terminal resolution, run:

```bash
# Update manifest state using scripts/plan_badge_provisioning.py
```

Update `repositories[<repo>]["provisioning"]` with:
- `pr_url`: Pull request URL
- `attempted_at`: ISO 8601 timestamp
- `outcome`: `OPEN` | `ADOPTED` | `DECLINED` | `OPTED_OUT`
