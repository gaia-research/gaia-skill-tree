# Whole-Registry EV Supplement — Emil Kowalski Intake

- **Run date:** 2026-10-14 UTC
- **Registry snapshot:** `review/meta/emilkowalski-ev-2026-10-13` based on `f00b3606b355a5c86de6d08190995dbd9ac8aab5`
- **Scope:** Full registry plus the 12 Emil candidate rows from `evidence/collectors/emilkowalski-ev-candidates.json`; this is not an Emil-only evidence lake.
- **Boundary:** Read-only whole-registry verification. No star values, evidence rows, skill nodes, TM grades, ranks, or calibrations were changed.

## Phase 1 — collection

The whole-registry type-first lake contains **410 skills, 365 with active sources, and 880 raw evidence entries**. The 12 Emil candidates were loaded with the existing candidate manifest. Exactly three candidate `social-signal` rows appear: `emilkowalski/animate`, `emilkowalski/prototype`, and `emilkowalski/review-animations`. They retain separate transcript spans and exposure/demo-only wording. The other nine eligible candidates have no skill-specific evidence rows. No Emil candidate has a `repo-own`, `github-stars-own`, benchmark, arXiv, peer-review, proxy-containment, or self-attestation row; `animation-vocabulary` appears in no scoring/evidence partition.

No suite or parent-repository popularity was assigned to a named candidate. The candidate video URL is present once in the type-first lake with three individually attributed rows.

## Phase 2 — live star verification

`stargazerHeartbeat.py --dry-run` scanned **101** current `github-stars-own` evidence rows: **98** differed from live repository counts and **3** were unchanged. No files were updated. These are whole-registry follow-up discrepancies; the Emil candidates have no per-skill star rows.

## Phase 2B — benchmark-source verification

The canonical catalog at `registry/benchmark-sources.json` was used. Four existing benchmark rows were scanned: **one scoring-eligible, three citation-only legacy rows, zero hard blockers, and zero Emil candidate benchmark rows**. No catalog or evidence rows were modified. See the run report for row-level classification.

## Phase 3 — adversarial review

Three read-only partition reviews confirmed no Emil/support leakage beyond the three expected social-signal rows. They flagged unrelated pre-existing registry issues, including non-arXiv URLs in the arXiv partition, stale/wrong star-source URL shapes, broad social/peer-review attribution, and unsupported subjective wording. No unrelated registry fixes were applied.

One `juliusbrussee/caveman` row's notes said its source URL returned 404; the whole-lake Phase 4 run later returned HTTP 200 for that URL, so the row's 404 note is stale rather than a confirmed current broken link.

### Phase 3 finding summary (read-only; unrelated to Emil candidates)

- Some `github-stars-own` rows cite skill-file blob URLs instead of a repository star endpoint; `gsd-build/gsd-discuss-phase` also uses a command-file URL as its star source.
- `pexp13/sentiment-analysis` has ACL Anthology and AAAI/ICWSM URLs typed as `arxiv`; `gaiabot/gaia-triage` E2 uses unsupported subjective wording.
- Firecrawl and Ruflo benchmark rows have no catalog benchmark ID and remain citation-only per Phase 2B; no scoring change was made.
- Some `mattpocock` self-attestation rows have mismatched or directory-shaped paths; broad social/peer-review attributions were flagged for human review.
- The whole-registry review confirmed unrelated contributor rows are expected; no Emil candidate/support leakage beyond the three approved-scope social rows was found.

No global finding was edited as part of this intake.

## Phase 4 — URL validation

- **Whole evidence lake:** **610 unique URLs** checked with the canonical Firecrawl validator and a serialized, checkpointed rate-limited driver. **609 validated, 0 confirmed broken links, 1 validation error.** The one unresolved URL is `https://doi.org/10.1039/c7sc02664a` (attributed to `k-dense-ai/deepchem`). Firecrawl could not scrape it; a direct `curl -I -L` followed a 302 redirect to the RSC publisher, which returned 403 behind a Cloudflare challenge. This is not reported as a confirmed 404, but the content remains unverified by Firecrawl.
- **Emil source blobs:** all **12** pinned `SKILL.md` URLs returned HTTP 200; zero broken links or API errors.
- **Support-only source:** the pinned `animation-vocabulary/SKILL.md` URL returned HTTP 200; this is source-liveness validation only, not an evidence row.
- **Shared demo video:** the YouTube URL returned HTTP 200.

Detailed URL receipts are in `firecrawl_validation_report_2026_10_13.md`, `candidate_source_validation_2026_10_14.md`, and `whole_registry_url_validation_2026_10_14.md`. The separate `support_source_validation_2026_10_14.md` receipt covers only the non-scoring support URL.

## Gate status

The three Emil evidence rows remain unapproved candidates. No evidence was ingested; no Trust Magnitude, grade, rank, or calibration was calculated. The nine sparse candidates remain sparse. Canonical multi-packet intake is still blocked on independent review/merge of PR #2089 into the integration branch. No intake issue was created, and no production support manifest/edges were added. Support target confirmation remains pending under #2084; #2086 remains untouched.
