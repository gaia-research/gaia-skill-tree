---
name: gaia-curate
description: >-
  Discovery-only Gaia curation for one manually selected source page. Fetches and
  normalizes up to five real SKILL.md candidates, deduplicates and maps them for
  human L4 review, then stops without evidence scoring or registry mutation.
version: 2.0.0
argument-hint: "<source-page-url>"
---

# Gaia Curate

Read [CURATION-CORE.md](CURATION-CORE.md). This skill is discovery-only and processes one manually selected source page with at most five candidates.

1. Fetch the page and record its canonical URL, retrieval time, source lane, and source-native trend signals. Do not treat popularity as trust.
2. For each candidate, fetch a real upstream `SKILL.md`. Reject/defer a listing that cannot resolve to one. Parse non-empty `name` and `description` frontmatter; preserve host repository, cited origin/attribution, commit SHA when available, and SHA-256 content hash.
3. Normalize one candidate, exact-dedupe by canonical URL/content hash, then query `gaia dev list --generic --json`. Offer at most three mapping options plus the bounded `NEW_GENERIC` and `UNSURE` paths; `UNSURE` is recorded as `DEFER`.
4. Emit one `discovery-packet-v1` decision using `MAP`, `NEW_GENERIC`, `DUPLICATE`, `NOT_A_SKILL`, or `DEFER`, and validate it with [scripts/validate_discovery_packet.py](scripts/validate_discovery_packet.py). Use Yggdrasil II `basic|fusion` only for an L4-reviewable proposal; do not ask workers for legacy branches or stars.
5. Present the L4 human shortlist and stop. A shortlist is not registry acceptance. After L4, hand accepted rows to a separate intake/evidence workflow.

Never gather or score evidence, assign manual grades/classes, calculate TM, calibrate stars, mutate registry files, regenerate docs, commit, push, or open a PR.
