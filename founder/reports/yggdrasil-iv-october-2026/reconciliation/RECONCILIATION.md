# October 2026 upstream / PR / intake reconciliation ledger (Yggdrasil IV launch, EPIC #2189 outcome 2)

- Generated: 2026-10-27T21:34:57Z (PROVISIONAL snapshot; cutoff 2026-10-31; re-run at cutoff, upstream tags and PR states move daily).
- Dev baseline: `origin/dev/yggdrasil-iv` @ `43797a441e99b34cdf7e19be3af863a2e3bdbed0`. `origin/main` is fully contained in dev (0 main-only commits; dev is 176 ahead).
- Read-only: nothing was merged, closed, labeled, commented or pushed. Machine-readable ledger: `ledger.json` (313 items, each listed individually).

## Counts by disposition and kind

| kind | verified-merged-to-dev | reconciled-already-equivalent | held-for-governance | rejected | duplicate | not-applicable | needs-action-for-dev | pending-curation | total |
|---|---|---|---|---|---|---|---|---|---|
| branch | 25 | 4 | 3 | 0 | 6 | 1 | 1 | 0 | 40 |
| evidence-candidate | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 |
| evidence-record | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 2 |
| intake-batch | 1 | 4 | 0 | 0 | 0 | 3 | 0 | 0 | 8 |
| intake-issue | 5 | 39 | 1 | 0 | 0 | 2 | 0 | 64 | 111 |
| intake-record | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| pr | 75 | 3 | 5 | 0 | 6 | 18 | 0 | 2 | 109 |
| upstream-issue | 1 | 1 | 0 | 0 | 1 | 2 | 0 | 9 | 14 |
| upstream-skill | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 12 | 14 |
| **total** | **111** | **53** | **9** | **0** | **13** | **27** | **1** | **99** | **313** |

Method: PRs found by `gh` search and cross-checked against the REST API (91 merged and 9 closed-unmerged since 2026-10-01, plus 9 open = 109). In-dev proof = `git merge-base --is-ancestor <merge commit> origin/dev/yggdrasil-iv`; branches by ancestry, `git cherry`, and per-file diff. Steward PRs are not-applicable ("Steward excluded by EPIC #2189"). PRs merged into `dev/pr-queue-2026-10-23` (#2128, #2136, #2140) are not in dev and are carried by draft #2139.

## needs-action-for-dev

- **dev/yggdrasil-iv-execution-continued** (branch): Open a PR dev/yggdrasil-iv-execution-continued -> dev/yggdrasil-iv (merge commit, docs-only, no Class S/registry/schema paths so no schema or visual gate) after a read-only skim that its handover text still matches current refs (it predates #2186-#2188 landing); do not squash. Resolve overlap with the new October report folder founder/reports/yggdrasil-iv-october-2026/ (no path collisions expected).
  - Evidence: tip 2e05a8bfa (2026-10-28); ahead of dev by 12 commit(s), 12 not patch-equivalent in dev, 98 changed file(s) differ from dev. 12 commits (2026-10-27/28) NOT in dev and with no PR: 98 files, all documentation/proof: founder/handovers/yggdrasil-iv/ (10 files), founder/reports/yggdrasil-iv-evidence/ (83 files incl. committed proof set + hash manifest + schema-proposal copies), founder/MEMORY.md, founder/README.md, founder/ORCHESTRATOR.md, founder/YGGDRASIL_IV_EXECUTION.md, CONTEXT.md. Base 7098cac1f (older than dev tip). git merge-tree against dev tip reports a clean merge. This is the "latest execution-control branch" the EPIC says to read; dev baseline lacks founder/handovers/yggdrasil-iv/.

## pending-curation (needs a review/meta curation PR or the intake path; not a dev-merge action)

### Upstream sync PRs awaiting review (2)
- #2170 [upstream sync] garrytan/garrytan -> v1.91.242.0: Human reviewer completes the PR checklist (version, frozen components installable:false, Class S sanity), then merges to main via the normal review/meta path; dev picks it up by main->dev sync. Do not hand-edit upstream: blocks. Expect Class S conflicts with #2171 (both rewrite docs/graph/gaia.json and named/index.json): land one, regenerate the other with gaia dev docs.
- #2171 [upstream sync] garrytan/gstack -> v1.91.242.0: As #2170; sequence after or before #2170 and regenerate Class S on the second.

### Registry upstream deltas (gaia dev sync-upstream) (12)
- addy-osmani/agent-skills addy-osmani/agent-skills upstream addyosmani/agent-skills: review/meta curation PR: gaia dev sync-upstream addy-osmani/agent-skills --tag 0.6.13 --source-url https://github.com/addyosmani/agent-skills/releases/tag/0.6.13 --released-at 2026-10-13T20:21:58Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- garrytan/gbrain garrytan/gbrain upstream garrytan/gbrain: review/meta curation PR: gaia dev sync-upstream garrytan/gbrain --tag v0.60.474.0 --source-url https://github.com/garrytan/gbrain/releases/tag/v0.60.474.0 --released-at 2026-10-27T21:20:11Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- heygen-com/hyperframes heygen-com/hyperframes upstream heygen-com/hyperframes: review/meta curation PR: gaia dev sync-upstream heygen-com/hyperframes --tag v0.8.209 --source-url https://github.com/heygen-com/hyperframes/releases/tag/v0.8.209 --released-at 2026-10-27T15:10:55Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- mattpocock/skills mattpocock/skills upstream mattpocock/skills: review/meta curation PR: gaia dev sync-upstream mattpocock/skills --tag v1.3.1 --source-url https://github.com/mattpocock/skills/releases/tag/v1.3.1 --released-at 2026-10-04T12:48:18Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- obra/superpowers obra/superpowers upstream obra/superpowers: review/meta curation PR: gaia dev sync-upstream obra/superpowers --tag v7.0.1 --source-url https://github.com/obra/superpowers/releases/tag/v7.0.1 --released-at 2026-10-21T21:05:11Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/agentdb ruvnet/agentdb upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/agentdb --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/dual-mode ruvnet/dual-mode upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/dual-mode --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/flow-nexus ruvnet/flow-nexus upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/flow-nexus --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/github-suite ruvnet/github-suite upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/github-suite --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/reasoningbank ruvnet/reasoningbank upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/reasoningbank --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/ruflo-v3 ruvnet/ruflo-v3 upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/ruflo-v3 --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)
- ruvnet/ruflo ruvnet/ruflo upstream ruvnet/ruflo: review/meta curation PR: gaia dev sync-upstream ruvnet/ruflo --tag v3.63.5 --source-url https://github.com/ruvnet/ruflo/releases/tag/v3.63.5 --released-at 2026-10-27T19:12:42Z (use --dry-run first; re-resolve the tag at the 2026-10-31 cutoff; component adds/removes handled via intake children / freeze per umbrella)

### Upstream umbrella / bootstrap issues (9)
- #1823 [upstream] heygen-com/hyperframes → v0.8.207: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item heygen-com/hyperframes); freeze the removed components (installable:false), and process component-add children.
- #1833 [upstream] ruvnet/ruflo → v3.63.4: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item ruvnet/agentdb); and process component-add children.
- #1835 [upstream] garrytan/gbrain → v0.60.472.0: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item garrytan/gbrain); and process component-add children.
- #2002 [upstream] addyosmani/agent-skills → 0.6.13: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item addy-osmani/agent-skills); and process component-add children.
- #2020 [upstream] obra/superpowers → v7.0.1: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item obra/superpowers); and process component-add children.
- #2040 [upstream] mattpocock/skills → v1.3.1: Curate via gaia dev sync-upstream on a review/meta branch (see upstream-skill item mattpocock/skills); and process component-add children.
- #2091 [upstream:bootstrap] leonxlnx/taste-skill -> baseline at v2.1.5: gaia dev sync-upstream leonxlnx/taste-skill --bootstrap --tag v2.1.5 --source-url https://github.com/Leonxlnx/taste-skill/releases/tag/v2.1.5 --released-at 2026-10-24T23:44:17Z on a review/meta branch (dry-run first); confirm the case-insensitive preflight from #2154 resolves the Leonxlnx/leonxlnx mismatch.
- #2168 [upstream:bootstrap] garrytan/garrytan -> baseline at v1.91.242.0: Review and land PR #2170 (see PR item).
- #2169 [upstream:bootstrap] garrytan/gstack -> baseline at v1.91.242.0: Review and land PR #2171 (see PR item).

### Intake issues: upstream-child:obra (2)
Ids: #2023, #2021

Action: Run the intake path: topology approval -> evidence (Stage-1/Phase-0, ev-scout) -> evidence approval -> single review/meta/intake-<N> promotion PR via gaia dev; or close with rationale if the maintainer declines the component.

### Intake issues: upstream-child:addy-osmani (5)
Ids: #2019, #2015, #2014, #2013, #2008

Action: Run the intake path: topology approval -> evidence (Stage-1/Phase-0, ev-scout) -> evidence approval -> single review/meta/intake-<N> promotion PR via gaia dev; or close with rationale if the maintainer declines the component.

### Intake issues: upstream-child:garrytan (48)
Ids: #1997, #1993, #1992, #1990, #1988, #1987, #1986, #1985, #1982, #1979, #1978, #1977, #1976, #1974, #1973, #1971, #1970, #1969, #1968, #1966, #1964, #1962, #1961, #1959, #1958, #1957, #1956, #1954, #1952, #1951, #1949, #1947, #1946, #1945, #1944, #1943, #1942, #1939, #1938, #1936, #1935, #1933, #1932, #1931, #1930, #1929, #1926, #1925

Action: Run the intake path: topology approval -> evidence (Stage-1/Phase-0, ev-scout) -> evidence approval -> single review/meta/intake-<N> promotion PR via gaia dev; or close with rationale if the maintainer declines the component.

### Intake issues: upstream-child:heygen-com (1)
Ids: #1996

Action: Run the intake path: topology approval -> evidence (Stage-1/Phase-0, ev-scout) -> evidence approval -> single review/meta/intake-<N> promotion PR via gaia dev; or, if the maintainer declines the component, close with rationale. (Heygen general-video/hyperframes-studio: payload v0.8.207 no longer lists these as adds, so first confirm the component still exists upstream.)

### Intake issues: direct-intake (8)
- #2081 [intake] Timestamped spoken quote retrieval — Arcmira find-quotes: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #2082 [intake] single: qml-code-review — TheQtCompanyRnD qt-qml-review: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #2083 [intake] single: branded-diagram-authoring — cathrynlavery diagram-design: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #2137 [intake] single: bounded-product-execution-review — UX3 complete MIT source: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #1832 intake #1832: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #1541 intake #1541: Intake triage then the standard topology -> evidence -> single promotion PR flow (gaia dev prefill/assess/ratify requires actual human L4 approval).
- #814 reverse-skill: Finish component-level evidence research, then suite intake (gaia-suite-intake) or close with rationale.
- #565 [meta-parking] Name drafts for 7 Class B-backed starless skills: Re-grade the 7 skills under the current (Yggdrasil III/IV) TM engine before any promotion; not a dev blocker.

### Emil Kowalski candidates (12)
Ids: emilkowalski/animate, emilkowalski/animate-expo, emilkowalski/animation-performance, emilkowalski/apple-design, emilkowalski/break-ui, emilkowalski/emil-design-eng, emilkowalski/find-animation-opportunities, emilkowalski/improve-animations, emilkowalski/mobile-native, emilkowalski/prototype, emilkowalski/review-animations, emilkowalski/write-swift

Action: Human-approved generic mapping, then intake path (gaia dev prefill/assess/ratify with actual L4 approval) and evidence ingestion; ev-scout for the 9 evidence-less candidates.

## held-for-governance

- pr #2151 [integration] Yggdrasil IV: trust degradation, challenge, and recovery | gate: founder final merge of #2151 -> main, production publish and launch (EPIC #2189 gate)
- pr #2157 feat(content-engine): weekly report 2026-44 | gate: founder visual review (visitor-facing weekly report pages, CLAUDE.md frontend gate)
- pr #2164 docs(en): routine 064 — document gaia dev discovery verbs | gate: founder visual review (new cards/sidebar/TOC in docs/en/cli-reference.html) and draft status
- pr #2176 proposal(schema): evidence lifecycle definitions — Core approval and a | gate: schema two-Core Maintainer approval + adoption (registry/schema evidence lifecycle definitions)
- pr #2177 proposal(evidence): lifecycle preparation core — held on schema adopti | gate: schema two-Core Maintainer approval + adoption (depends on #2176; base dev/yggdrasil-iv-evidence-schema-final)
- intake-issue #1512 [intake investigation] Lark/Larksuite skills.sh leaderboard cluster | gate: curator (L4 human) topology decision on dual source identities
- branch dev/yggdrasil-iv-evidence-core-final dev/yggdrasil-iv-evidence-core-final | gate: schema two-Core Maintainer approval + adoption (stacked on #2176)
- branch dev/yggdrasil-iv-evidence-schema-final dev/yggdrasil-iv-evidence-schema-final | gate: schema two-Core Maintainer approval + adoption
- branch recovery/yggdrasil-iv-pause-canonical-fixtures-96d329995 recovery/yggdrasil-iv-pause-canonical-fixtures-96d329995 | gate: schema two-Core approval (carries proposed namedSkill/skillTree schema copies under tests/fixtures) and review of unreviewed WIP

## Already in dev or reconciled (summary)

- verified-merged-to-dev (111): PR merge commits, fully merged branches, fixes for #2050/#2088/#2152, intake #2044/#2162/#2163, the October skill batch and evidence receipts.
- reconciled-already-equivalent (53): closed PRs #2087/#2122/#2123 (via #2147); 40 open upstream:child intake issues whose named skill already exists in registry (see `group` in ledger.json); 3 patch-equivalent branches; pre-October skill batches whose nodes exist; upstream-skill items with no delta (firecrawl, gsd).
- duplicate (13): closed PRs #2028 (of #2036), #2032 (of #2146), #2056 (of #2057), #2090, #2116, #2141; issue #2135 (of #1981); superseded evidence-iteration branches (evidence-schema-contract shares a tip with evidence-schema-final).
- rejected: none. All October closures were supersessions.

## Could not determine / caveats

- Mergeability of #2157, #2164, #2170, #2171 against main is UNKNOWN per GitHub; #2170 and #2171 will conflict with each other on Class S files (regenerate after the first lands).
- #2056 (closed unmerged, no comment): supersession by #2057 is inferred from matching bodies, not stated by the closer.
- Eight proposed skill ids in pre-October batches have no registry node or named file (web-scrape-integration, web-search-integration, browser-interaction-integration, agent-environment-auth, api-call-orchestration, academic-literature-retrieval, frontend-design-judgment, html-video-composition). Five appear textually in firecrawl-build-*/research-index named skills, but realisation was not confirmed. Outcome undetermined.
- Only 14 registry skills (8 repos) carry an upstream: block; for all others there is no upstream provenance record, so October upstream changes cannot be computed from the registry. Six ruvnet siblings (dual-mode, flow-nexus, github-suite, reasoningbank, ruflo-v3, ruflo) track ruvnet/ruflo at v3.41.2 with no umbrella issue of their own (#1833 is keyed to ruvnet/agentdb).
- Upstream "latest" values were queried 2026-10-28 and are already past the issue payloads (gbrain .472 -> .474, hyperframes .207 -> .209, ruflo 3.63.4 -> 3.63.5). Re-resolve every tag at the 2026-10-31 cutoff.
- evidence/seeds/ does not exist on any inspected ref, so "seed items modified in October" is an empty set. Only evidence/collectors/* (Emil Kowalski) and registry-for-review/* changed in October.
- #2050 and #2088 are marked verified-merged-to-dev because their fix PRs are in dev; full acceptance criteria were not re-verified (#2088 MAP-override half in particular).
- Intake candidate evidence quality was not assessed; this is disposition accounting, not appraisal.
- #2151 shows CLEAN merge state and green checks but no recorded review decision; exact-SHA independent reviews were not re-verified here.
- The worktree had uncommitted modifications to docs/badges/registry.json and docs/graph/ledger/data.json before this task; untouched.
