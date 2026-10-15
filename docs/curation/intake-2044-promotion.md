# Intake #2044 promotion receipt

Promotion PR: [#2054](https://github.com/gaia-research/gaia-skill-tree/pull/2054), based on `dev/2044-intake`. No merge or issue closure performed.

## Authority and identity recovery

- Topology approval: [maintainer comment 6068151323](https://github.com/gaia-research/gaia-skill-tree/issues/2044#issuecomment-6068151323).
- Corrected nine-row evidence and 3★/2★ calibration approval: [maintainer comment 6069381386](https://github.com/gaia-research/gaia-skill-tree/issues/2044#issuecomment-6069381386).
- Recovered immutable intake: `registry-for-review/skill-batches/20261008203029-mbtiongson1-from-file.json`; unchanged by this promotion.
- Original evidence manifest: `final-ingestion-manifest.json` from the corrected verification pass. Its candidate-only designation describes the pre-approval artifact; approval is the separate maintainer reference above, not a rewritten manifest.

| Original approved identity | CLI canonical identity | Generic parent |
|---|---|---|
| `Hikari9/auto-office` | `hikari9/auto-office` | `autonomous-engineering-platform` |
| `Hikari9/office-submit` | `hikari9/office-submit` | `verification-before-completion` |

Contributor lowercasing is the documented `gaia-review-meta-close` contract, not an identity substitution. Exact upstream slugs and display attribution `upstream_author: Hikari9` are retained. Evidence targets and suite references were projected to canonical IDs at CLI invocation; neither the immutable intake nor original evidence recommendation was rewritten. #2055 tracks the separate ratify/add mismatch; no schema relaxation or global CLI change is included.

Both discovery packets were re-ratified with `--contributor hikari9`, existing human approval reference, and `--acknowledge-human-review`. The existing principles assessments passed ratify's live catalog/source/digest freshness validation before evidence mutation. Assessments are pre-ingestion receipts, not claims that they remain fresh after the catalog changes below. No additional generic-only conversion was run: the existing schema-valid platform fusion conversion was preserved.

## Source verification and scope

GitHub APIs freshly reconfirmed upstream HEAD `da6aa9a93dbab98c03d2fbb3593f994acf85d7a7` and one repository star. Both pinned content responses reproduced the discovery digests:

- Root SKILL.md: `b3ca7a9a64002a384acdb2e8c35ed01335e431f218a2a4987babd85f2f6dad5b`.
- Office Submit SKILL.md: `261a30a5bc0b1b5c9211634bd96ab3e2b497255cb3336b924b55a91d0ecd7ea2`.

The approved dated snapshot is 826 unique commits, four contributor accounts, one star, 21 skills. Office Submit's repository rows are shared baseline, not independent component usage. Its combined repository baseline is 21.678 TM, below the existing 50-TM cap.

Nine rows were ingested individually through `gaia dev evidence --no-build`: two named repository rows for each implementation, four platform research rows (MetaGPT 156, published ChatDev 396, OpenHands 15, Agentless 19 record-specific citations), and one narrowly applicable Agentless verification-parent row. ChatDev's preprint count was not added. No peer-review counts, benchmarks, attestations or adoption boosts were invented. Existing legacy parent rows remain zero-contribution context. Prior Firecrawl rate limits remain disclosed; primary API fallback verification is not a wholly successful scraper crawl.

## Canonical results

| Skill | Repository subtotal | Inherited research | Exact TM | Grade | Stored stars |
|---|---:|---:|---:|---|---|
| `hikari9/auto-office` | 21.678 | 67.2875 | 88.9655 | B | 3★ |
| `hikari9/office-submit` | 21.678 shared | 2.66 | 24.338 | C | 2★ |

The exceptional one-component suite was established through `gaia dev fuse --named-capstone hikari9/auto-office --suite-components hikari9/office-submit --no-build`. The manifest survives regeneration. Suite structure contributes zero TM. Calibration used the approved bands and CLI timeline events; independent post-calibration inspection confirmed both stored levels.

Adding generic Agentless evidence also changes existing consumers: Obra verification-before-completion 95.15 → 97.81/B, Ruvnet verification-quality 36 → 38.66/C, and GSD verify-work 50 → 52.66/B. No rank changes were authorized or applied to those consumers. The first validation exposed stale cached values for Obra/Ruvnet; `calibrate-trust-magnitude --skill ... --no-build --yes` refreshed only those derived caches with CLI timeline logging. The subsequent validator reports all TM surfaces agree.

Custom installation content for both implementations was applied only with supported `update-named --installation-file --no-build`: upstream uv/pipx installation followed by `office install` and `office doctor`. The documented commands follow current upstream; packaging verification was at the pinned commit. No global harness installation was performed.

## Execution and validation

Source CLI environment: `GAIA_OPERATOR_OVERRIDE=1 PYTHONPATH=src python3 -m gaia_cli.main`; doctor reported dependencies/artifact ready and retrieval fresh, optional Jev credential absent. No live Jev advice was claimed.

Executed verbs: re-ratify twice; add twice; evidence nine times; suite fuse once; calibrate to 3★ and 2★; update-named installation sections; build; scoped dependent TM cache refresh; docs regeneration. Recovery regeneration was necessary after the dependent cache refresh and installation section correction.

`build_docs.py` write mode did not publish updated API files; its check correctly caught API drift. The supported `python3 scripts/buildApiProjection.py --out-dir docs/api/v1` regenerated those surfaces without hand-editing JSON.

Final gates:

- `gaia dev validate`: all validation checks passed; redaction, transparency, migration provenance and Trust Magnitude consistency passed.
- `python3 scripts/build_docs.py --check`: exit 0, documentation up to date; rolling trending drift is warn-only.
- `python3 scripts/review_meta_close.py check`: clean preflight.
- Exact merged-map `computeTrustMagnitude` independently reproduced 88.9655 and 24.338 after build.

## Entrypoints

Generated contributor profile, badges, graph, API and sitemap only; no bespoke navigation, mount or layout change. Founder review remains required before merge. The issue and PR remain open.
