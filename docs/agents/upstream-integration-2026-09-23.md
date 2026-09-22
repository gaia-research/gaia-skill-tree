# Gaia Skill Tree upstream integration triage

**Snapshot:** 2026-09-23
**Repository:** `gaia-research/gaia-skill-tree`
**Target integration branch:** `dev/upstream-integration-2026-09-23`
**Target integration PR:** draft PR from that branch to `main`

## Current state

Live repo audit on 2026-09-23 found:

- **5 active upstream release umbrellas**
- **95 open watcher child-intake issues**
- **0 open upstream-sync PRs**
- **0 existing `dev/upstream-integration-*` branches**
- **#1908 is still the original placeholder**
- Current unrelated open PRs:
  - #1912 `feat(content-engine): weekly report 2026-39`
  - #1834 `docs(en): routine 053 — gaia fuse flag table completeness`
- Branch `feat/steward-sensor-1580-upstream` exists but is unrelated to this integration

Do not retarget or fold #1912, #1834, or `feat/steward-sensor-1580-upstream` into this work.

## What changed since the 2026-09-19 handoff

### Hyperframes moved again

#1823 is now:

`heygen-com/hyperframes v0.8.34 -> v0.8.60`

Current component candidates:

- `general-video`
- `hyperframes`
- `hyperframes-studio`

New child since the old handoff:

- #1911 `heygen-com/hyperframes-studio`

The watcher has repeatedly refreshed the same umbrella rather than opening a new one. Treat #1823 as the canonical Hyperframes release thread.

### GBrain moved again

#1835 is now:

`garrytan/gbrain v0.50.0.0 -> v0.51.6.0`

Current component candidates: **71**

New child since the old handoff:

- #1913 `garrytan/remote-mcp`

The watcher refreshed the existing umbrella rather than opening another release issue.

### Everything else is still pending

- #1909 `obra/superpowers -> v6.4.1`
- #1907 `addyosmani/agent-skills -> 0.6.10`
- #1833 `ruvnet/ruflo -> v3.42.4`
- #1908 remains a placeholder and should become the integration map

## Keep these 5 release umbrellas

| Issue | Upstream | Current target | Priority | Triage action |
|---|---|---:|---|---|
| #1909 | `obra/superpowers` | `v6.4.1` | P2 | approve release sync, use `skip-child-gate`, consolidate child review |
| #1907 | `addy-osmani/agent-skills` | `0.6.10` | P2 | approve release sync, use `skip-child-gate`, curate accumulated backlog once |
| #1823 | `heygen-com/hyperframes` | `v0.8.60` | P2 | approve release sync, use `skip-child-gate`, review 3 candidates |
| #1833 | `ruvnet/agentdb` via `ruflo` | `v3.42.4` | P2 | approve narrow version/provenance sync |
| #1835 | `garrytan/gbrain` | `v0.51.6.0` | P3 | approve version sync, use `skip-child-gate`, aggressively curate/dedupe 71 candidates |

### Labels to apply

For #1909, #1907, and #1823:

- `upstream:release`
- `upstream:approved`
- `skip-child-gate`
- `ready-for-agent`
- `P2`

For #1833:

- `upstream:release`
- `upstream:approved`
- `ready-for-agent`
- `P2`

For #1835:

- `upstream:release`
- `upstream:approved`
- `skip-child-gate`
- `ready-for-agent`
- `P3`

Remove `needs-triage` from all five once those labels are applied.

## Convert #1908 into the integration map

Rename #1908 to:

`[integration] upstream watcher backlog — 2026-09-23`

Apply:

- `wayfinder:map`
- `ready-for-agent`
- `P2`

Replace its placeholder body with a short integration summary pointing to:

`docs/agents/upstream-integration-2026-09-23.md`

The issue should state that individual watcher-child tickets are being consolidated into the integration frontier. Closing those tickets does **not** mean their skills were accepted.

## Consolidate and close the 95 watcher child issues

For every watcher child listed below:

- preserve `intake`
- preserve `upstream:child`
- add `P3`
- remove `needs-triage`
- close with `state_reason=completed`

Closure meaning:

> The individual review packet has been consolidated into the integration frontier. The candidate is still undecided until the integration PR records it as accepted, mapped, deferred, or omitted.

### Addy Osmani: 17 candidates

The first 16 came from closed umbrella #1550; `constraint-driven-development` came from closed umbrella #1652. The current active umbrella #1907 references the combined set.

- [ ] #1551 `addy-osmani/api-and-interface-design`
- [ ] #1552 `addy-osmani/browser-testing-with-devtools`
- [ ] #1553 `addy-osmani/ci-cd-and-automation`
- [ ] #1554 `addy-osmani/context-engineering`
- [ ] #1555 `addy-osmani/debugging-and-error-recovery`
- [ ] #1556 `addy-osmani/deprecation-and-migration`
- [ ] #1557 `addy-osmani/documentation-and-adrs`
- [ ] #1558 `addy-osmani/doubt-driven-development`
- [ ] #1559 `addy-osmani/frontend-ui-engineering`
- [ ] #1560 `addy-osmani/git-workflow-and-versioning`
- [ ] #1561 `addy-osmani/idea-refine`
- [ ] #1563 `addy-osmani/interview-me`
- [ ] #1564 `addy-osmani/observability-and-instrumentation`
- [ ] #1565 `addy-osmani/security-and-hardening`
- [ ] #1566 `addy-osmani/source-driven-development`
- [ ] #1567 `addy-osmani/using-agent-skills`
- [ ] #1653 `addy-osmani/constraint-driven-development`

### Obra: 4 candidates

Three are carry-over from closed umbrella #1570. `diagnosing-superpowers` is the new item attached to #1909.

- [ ] #1571 `obra/test-driven-development`
- [ ] #1572 `obra/using-superpowers`
- [ ] #1573 `obra/writing-skills`
- [ ] #1910 `obra/diagnosing-superpowers`

### Hyperframes: 3 candidates

#1911 is new since the previous triage.

- [ ] #1824 `heygen-com/general-video`
- [ ] #1825 `heygen-com/hyperframes`
- [ ] #1911 `heygen-com/hyperframes-studio`

### GBrain: 71 candidates

#1913 `remote-mcp` is new since the previous triage.

- [ ] #1836 `garrytan/academic-verify`
- [ ] #1837 `garrytan/archive-crawler`
- [ ] #1838 `garrytan/article-enrichment`
- [ ] #1839 `garrytan/ask-user`
- [ ] #1840 `garrytan/blog-ingest`
- [ ] #1841 `garrytan/book-mirror`
- [ ] #1842 `garrytan/brain-ingest-gate`
- [ ] #1843 `garrytan/brain-link-discipline`
- [ ] #1844 `garrytan/brain-pdf`
- [ ] #1845 `garrytan/brain-taxonomist`
- [ ] #1846 `garrytan/briefing`
- [ ] #1847 `garrytan/bulk-ingestion`
- [ ] #1848 `garrytan/chat-connectors`
- [ ] #1849 `garrytan/citation-fixer`
- [ ] #1850 `garrytan/citation-graph-ingest`
- [ ] #1851 `garrytan/cold-start`
- [ ] #1852 `garrytan/company-brainify`
- [ ] #1853 `garrytan/context-audit`
- [ ] #1854 `garrytan/conversation-archive`
- [ ] #1855 `garrytan/correction-pipeline`
- [ ] #1856 `garrytan/cron-scheduler`
- [ ] #1857 `garrytan/cross-modal-review`
- [ ] #1858 `garrytan/daily-task-manager`
- [ ] #1859 `garrytan/daily-task-prep`
- [ ] #1860 `garrytan/data-loss-gate`
- [ ] #1861 `garrytan/data-research`
- [ ] #1862 `garrytan/db-repair`
- [ ] #1863 `garrytan/draft-in-voice`
- [ ] #1864 `garrytan/eiirp`
- [ ] #1865 `garrytan/enrich`
- [ ] #1866 `garrytan/fact-check`
- [ ] #1867 `garrytan/frontmatter-guard`
- [ ] #1868 `garrytan/functional-area-resolver`
- [ ] #1869 `garrytan/gbrain-advisor`
- [ ] #1870 `garrytan/gbrain-upgrade`
- [ ] #1871 `garrytan/google-loops`
- [ ] #1872 `garrytan/idea-ingest`
- [ ] #1873 `garrytan/idea-lineage`
- [ ] #1874 `garrytan/ingest`
- [ ] #1875 `garrytan/maintain`
- [ ] #1876 `garrytan/measure-before-you-fix`
- [ ] #1877 `garrytan/media-ingest`
- [ ] #1878 `garrytan/meeting-ingestion`
- [ ] #1879 `garrytan/migrate`
- [ ] #1880 `garrytan/minion-orchestrator`
- [ ] #1881 `garrytan/perplexity-research`
- [ ] #1882 `garrytan/postgres-adopt`
- [ ] #1883 `garrytan/publish`
- [ ] #1884 `garrytan/query`
- [ ] #1885 `garrytan/repo-architecture`
- [ ] #1886 `garrytan/reports`
- [ ] #1887 `garrytan/research-compendium`
- [ ] #1888 `garrytan/resolve-before-asking`
- [ ] #1889 `garrytan/schema-author`
- [ ] #1890 `garrytan/schema-unify`
- [ ] #1891 `garrytan/setup`
- [ ] #1892 `garrytan/signal-detector`
- [ ] #1893 `garrytan/skill-autobench`
- [ ] #1894 `garrytan/skill-creator`
- [ ] #1895 `garrytan/skill-optimizer`
- [ ] #1896 `garrytan/skillify`
- [ ] #1897 `garrytan/skillpack-check`
- [ ] #1898 `garrytan/skillpack-harvest`
- [ ] #1899 `garrytan/smoke-test`
- [ ] #1900 `garrytan/soul-audit`
- [ ] #1901 `garrytan/strategic-reading`
- [ ] #1902 `garrytan/testing`
- [ ] #1903 `garrytan/two-tier-extraction`
- [ ] #1904 `garrytan/voice-note-ingest`
- [ ] #1905 `garrytan/webhook-transforms`
- [ ] #1913 `garrytan/remote-mcp`

## Integration topology

1. Create `dev/upstream-integration-2026-09-23` from current `main`.
2. Add this file at `docs/agents/upstream-integration-2026-09-23.md`.
3. Open a **draft PR**: `dev/upstream-integration-2026-09-23 -> main`.
4. Convert #1908 into the integration map and link the draft PR + this file.
5. Apply the approval labels above to the five release umbrellas.
6. The watcher may then create draft `review/meta/upstream-*` PRs.
7. For every upstream-sync PR linked to #1909, #1907, #1823, #1833, or #1835:
   - change its base from `main`
   - base it on `dev/upstream-integration-2026-09-23`
8. Do not merge those PRs independently to `main`.
9. Integrate/review them into the draft integration PR.
10. The integration PR is the only intended path from this upstream batch to `main`.

## Curation rules

### Obra / Superpowers

Review all four current candidates once.

Carry-over:
- `test-driven-development`
- `using-superpowers`
- `writing-skills`

New:
- `diagnosing-superpowers`

Do not treat the old three as fresh discoveries.

### Addy Osmani / agent-skills

The active #1907 release points at an accumulated 17-candidate set originating across prior releases. Do not recreate release-by-release intake history. Curate the current 17 once.

### Hyperframes

Review:
- `general-video`
- `hyperframes`
- `hyperframes-studio`

Use the current #1823 payload only.

### GBrain

Do **not** bulk-admit all 71 directories.

For every candidate:
- inspect the actual upstream `SKILL.md`
- determine whether the behavior is reusable outside GBrain
- dedupe against existing named Gaia skills
- dedupe/map against generic skills
- reject thin repo-local maintenance helpers as standalone named skills
- verify canonical name / contributor
- verify `links.github`
- assign `genericSkillRef`
- assign star level per `META.md`
- preserve attribution
- only add candidates that improve the tree as distinct reusable skills

`remote-mcp` deserves explicit overlap checking against Gaia's existing MCP-related skills before admission.

### Ruflo / AgentDB

#1833 has:
- no component adds
- no component removals
- healthy links
- no name drift

Keep the resulting change narrow: version/provenance sync only unless fresh source inspection reveals a real structural delta.

## Final decision vocabulary

Every one of the 95 child candidates must end the integration pass with exactly one disposition:

- **accepted** — add/update a named skill
- **mapped** — represented by an existing named/generic skill instead of creating a duplicate
- **deferred** — worth revisiting later, intentionally not part of this integration
- **omitted** — duplicate, too repo-local, too thin, or otherwise not valuable enough for Gaia

Record the complete decision matrix in `docs/agents/upstream-integration-2026-09-23.md`; summarize totals in the draft PR body.

## Implementation checklist

- [ ] Create `dev/upstream-integration-2026-09-23` from current `main`
- [ ] Commit this Markdown to `docs/agents/upstream-integration-2026-09-23.md`
- [ ] Open draft integration PR to `main`
- [ ] Convert #1908 into the integration map
- [ ] Label #1909, #1907, #1823, #1833, #1835 as specified
- [ ] Remove `needs-triage` from those five umbrellas
- [ ] Close all 95 watcher child issues as consolidated
- [ ] Add `P3` to those child issues
- [ ] Remove `needs-triage` from those child issues
- [ ] Trigger / collect generated upstream-sync PRs
- [ ] Retarget every batch upstream-sync PR to the integration branch
- [ ] Confirm no batch upstream-sync PR targets `main`
- [ ] Curate all 95 child candidates
- [ ] Record accepted / mapped / deferred / omitted for each
- [ ] Apply accepted registry changes on the integration branch
- [ ] Regenerate required Class S / docs outputs
- [ ] Run registry/schema validation
- [ ] Run install/parity checks
- [ ] Run docs checks
- [ ] Update the draft PR with final counts and decisions
- [ ] Mark the integration PR ready only after the whole batch is coherent

## Guardrails

- Do not touch PR #1912.
- Do not touch PR #1834.
- Do not use `feat/steward-sensor-1580-upstream` as the integration branch.
- Do not bulk-accept watcher children.
- Do not merge watcher-generated upstream PRs directly to `main`.
- Do not use historical release payloads when the active umbrella has already been refreshed to a newer version.
- Preserve human review at the final `dev/upstream-integration-2026-09-23 -> main` merge boundary.

## Snapshot totals

| Bucket | Count |
|---|---:|
| Active upstream umbrellas | 5 |
| Open watcher child issues | 95 |
| Addy candidates | 17 |
| Obra candidates | 4 |
| Hyperframes candidates | 3 |
| GBrain candidates | 71 |
| Upstream-sync PRs currently open | 0 |
| Existing upstream integration branches | 0 |

## Candidate decision matrix — Lane 02

First-pass proposals, **not approval to mutate the registry**. Each source was fetched and inspected from its release-pinned `SKILL.md` (GBrain’s four exceptions use the release-pinned `skills/` path rather than `plugin/skills/`). All 95 source files resolved; source URLs below point to the inspected file. Existing named implementations and generic references were compared with the local registry; proposed ranks are conservative 2★ entry estimates, **not** TM-calibrated grades. No evidence or benchmark claim has been promoted by this matrix.

**Gate:** 30 rows are marked `ESCALATE`; an independent stronger-model/human topology and safety review must resolve each exact question before final integration or any corresponding accepted-row mutation. `accepted` is a proposal only. `mapped` points to an existing named skill and/or existing starless generic reference; it does not create a named implementation. No new generic or fusion topology is authorized by this pass.

| Issue | Candidate / inspected source | Disposition | Mapping / target (`genericSkillRef` for accepted) | Star proposal | Escalate? | Reason / exact review question |
|---|---|---|---|---|---|---|
| [#1551](https://github.com/gaia-research/gaia-skill-tree/issues/1551) | [`addy-osmani/api-and-interface-design`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/api-and-interface-design/SKILL.md) | accepted | software-design | 2 | no | Stable API contract and interface design procedure; distinct Addy implementation. |
| [#1552](https://github.com/gaia-research/gaia-skill-tree/issues/1552) | [`addy-osmani/browser-testing-with-devtools`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/browser-testing-with-devtools/SKILL.md) | accepted | browser-control | 2 | no | Concrete Chrome DevTools MCP debugging and browser-verification procedure. |
| [#1553](https://github.com/gaia-research/gaia-skill-tree/issues/1553) | [`addy-osmani/ci-cd-and-automation`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/ci-cd-and-automation/SKILL.md) | accepted | deployment-automation | 2 | no | Quality-gate CI pipeline and deployment workflow, distinct from existing launch skill. |
| [#1554](https://github.com/gaia-research/gaia-skill-tree/issues/1554) | [`addy-osmani/context-engineering`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/context-engineering/SKILL.md) | accepted | context-safe-execution | 2 | ESCALATE | Context hierarchy and agent rules are reusable; choose context-safe-execution vs context-compression vs agent-environment-setup before admission. |
| [#1555](https://github.com/gaia-research/gaia-skill-tree/issues/1555) | [`addy-osmani/debugging-and-error-recovery`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/debugging-and-error-recovery/SKILL.md) | mapped | obra/systematic-debugging; systematic-debugging | — | no | Broad stop-the-line root-cause protocol overlaps existing systematic-debugging implementations. |
| [#1556](https://github.com/gaia-research/gaia-skill-tree/issues/1556) | [`addy-osmani/deprecation-and-migration`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/deprecation-and-migration/SKILL.md) | accepted | framework-upgrade | 2 | ESCALATE | Expand/contract API and schema migrations may instead fit system-integration; decide generic and scope. |
| [#1557](https://github.com/gaia-research/gaia-skill-tree/issues/1557) | [`addy-osmani/documentation-and-adrs`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/documentation-and-adrs/SKILL.md) | accepted | write-report | 2 | ESCALATE | ADR and API documentation may fit write-report or software-design; resolve generic ownership. |
| [#1558](https://github.com/gaia-research/gaia-skill-tree/issues/1558) | [`addy-osmani/doubt-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/doubt-driven-development/SKILL.md) | accepted | design-review | 2 | ESCALATE | Adversarial doubt protocol may instead be self-critique or auto-review; decide canonical mapping. |
| [#1559](https://github.com/gaia-research/gaia-skill-tree/issues/1559) | [`addy-osmani/frontend-ui-engineering`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/frontend-ui-engineering/SKILL.md) | accepted | design-generation | 2 | ESCALATE | Frontend engineering spans design-generation, web-accessibility, and full-stack-developer; pick taxonomy before intake. |
| [#1560](https://github.com/gaia-research/gaia-skill-tree/issues/1560) | [`addy-osmani/git-workflow-and-versioning`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/git-workflow-and-versioning/SKILL.md) | mapped | obra/using-git-worktrees; git-integration | — | no | General git branching and versioning guidance overlaps existing workflow implementations. |
| [#1561](https://github.com/gaia-research/gaia-skill-tree/issues/1561) | [`addy-osmani/idea-refine`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/idea-refine/SKILL.md) | mapped | obra/brainstorming; brainstorming | — | no | Diverge/converge idea shaping already implemented by brainstorming. |
| [#1563](https://github.com/gaia-research/gaia-skill-tree/issues/1563) | [`addy-osmani/interview-me`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/interview-me/SKILL.md) | mapped | mattpocock/grill-me; grill-me | — | no | One-question-at-a-time intent interview already represented by grill-me. |
| [#1564](https://github.com/gaia-research/gaia-skill-tree/issues/1564) | [`addy-osmani/observability-and-instrumentation`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/observability-and-instrumentation/SKILL.md) | accepted | detect-anomaly | 2 | ESCALATE | Logging metrics tracing and alerts could fit detect-anomaly, token-observability, or a new observability generic; decide topology. |
| [#1565](https://github.com/gaia-research/gaia-skill-tree/issues/1565) | [`addy-osmani/security-and-hardening`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/security-and-hardening/SKILL.md) | accepted | security-audit | 2 | no | Threat modeling and OWASP hardening protocol, distinct source implementation of security-audit. |
| [#1566](https://github.com/gaia-research/gaia-skill-tree/issues/1566) | [`addy-osmani/source-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/source-driven-development/SKILL.md) | accepted | grounding | 2 | no | Explicit official-source citation and verification before implementation; distinct grounding workflow. |
| [#1567](https://github.com/gaia-research/gaia-skill-tree/issues/1567) | [`addy-osmani/using-agent-skills`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/using-agent-skills/SKILL.md) | mapped | vercel/find-skills; skill-discovery | — | no | Agent skill discovery and invocation already represented by find-skills. |
| [#1653](https://github.com/gaia-research/gaia-skill-tree/issues/1653) | [`addy-osmani/constraint-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/constraint-driven-development/SKILL.md) | accepted | guardrails | 2 | no | Written CONSTRAINTS.md quality floor with change-detection gate; distinct implementation of guardrails. |
| [#1571](https://github.com/gaia-research/gaia-skill-tree/issues/1571) | [`obra/test-driven-development`](https://github.com/obra/superpowers/blob/v6.4.1/skills/test-driven-development/SKILL.md) | accepted | test-driven-development | 2 | no | Obra red-green-refactor implementation with explicit failure-first checks; existing generic and Addy/Matt variants. |
| [#1572](https://github.com/gaia-research/gaia-skill-tree/issues/1572) | [`obra/using-superpowers`](https://github.com/obra/superpowers/blob/v6.4.1/skills/using-superpowers/SKILL.md) | mapped | obra/superpowers; superpowers | — | no | Bootstrap skill router belongs to existing Superpowers suite, not a new named capability. |
| [#1573](https://github.com/gaia-research/gaia-skill-tree/issues/1573) | [`obra/writing-skills`](https://github.com/obra/superpowers/blob/v6.4.1/skills/writing-skills/SKILL.md) | accepted | skill-authoring | 2 | no | TDD-based skill writing and verification method; distinct from generic authoring variants. |
| [#1910](https://github.com/gaia-research/gaia-skill-tree/issues/1910) | [`obra/diagnosing-superpowers`](https://github.com/obra/superpowers/blob/v6.4.1/skills/diagnosing-superpowers/SKILL.md) | accepted | systematic-debugging | 2 | ESCALATE | Postmortem of Superpowers session failures may be systematic-debugging or skill-performance-benchmarking; decide canonical mapping. |
| [#1824](https://github.com/gaia-research/gaia-skill-tree/issues/1824) | [`heygen-com/general-video`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/general-video/SKILL.md) | mapped | heygen-com/hyperframes; video-composition | — | no | Freeform video composition is an entry workflow of existing HyperFrames video-composition suite. |
| [#1825](https://github.com/gaia-research/gaia-skill-tree/issues/1825) | [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/hyperframes/SKILL.md) | mapped | heygen-com/hyperframes | — | no | Existing named skill already represents the exact same upstream entrypoint; update its provenance/version instead. |
| [#1911](https://github.com/gaia-research/gaia-skill-tree/issues/1911) | [`heygen-com/hyperframes-studio`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/hyperframes-studio/SKILL.md) | accepted | video-preview | 2 | ESCALATE | Studio timeline organization may map to video-preview or timeline-animation, or remain a suite component; decide topology. |
| [#1836](https://github.com/gaia-research/gaia-skill-tree/issues/1836) | [`garrytan/academic-verify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/academic-verify/SKILL.md) | accepted | scientific-literature-retrieval | 2 | ESCALATE | Publication-to-replication verification crosses literature retrieval, cite-sources and grounding; determine canonical generic. |
| [#1837](https://github.com/gaia-research/gaia-skill-tree/issues/1837) | [`garrytan/archive-crawler`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/archive-crawler/SKILL.md) | accepted | knowledge-harvest | 2 | ESCALATE | Personal archive allowlist crawler crosses knowledge-harvest and personal-knowledge-management; decide scope and source portability. |
| [#1838](https://github.com/gaia-research/gaia-skill-tree/issues/1838) | [`garrytan/article-enrichment`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/article-enrichment/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Article summaries and quotations are a narrow source-enrichment stage of existing brain-ops. |
| [#1839](https://github.com/gaia-research/gaia-skill-tree/issues/1839) | [`garrytan/ask-user`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/ask-user/SKILL.md) | mapped | mattpocock/grill-me; questionnaire-generation | — | no | Human decision gating with choices is a small interaction pattern rather than distinct named implementation. |
| [#1840](https://github.com/gaia-research/gaia-skill-tree/issues/1840) | [`garrytan/blog-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md) | accepted | feed-monitoring | 2 | ESCALATE | Full-publication ingestion differs from feed-monitoring and knowledge-harvest; choose proper generic or new node. |
| [#1841](https://github.com/gaia-research/gaia-skill-tree/issues/1841) | [`garrytan/book-mirror`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/book-mirror/SKILL.md) | accepted | document-analyst | 2 | ESCALATE | Personalized book mirror crosses document analysis and personal-knowledge-management; decide taxonomy and privacy boundary. |
| [#1842](https://github.com/gaia-research/gaia-skill-tree/issues/1842) | [`garrytan/brain-ingest-gate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-ingest-gate/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | GBrain-specific prewrite dedup/entity gate belongs to existing brain-ops implementation. |
| [#1843](https://github.com/gaia-research/gaia-skill-tree/issues/1843) | [`garrytan/brain-link-discipline`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-link-discipline/SKILL.md) | omitted | — | — | no | Brain-page link-delivery convention relies on GBrain path/remote; too narrow as standalone skill. |
| [#1844](https://github.com/gaia-research/gaia-skill-tree/issues/1844) | [`garrytan/brain-pdf`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-pdf/SKILL.md) | mapped | garrytan/make-pdf; format-output | — | no | PDF export is already covered by the same author's make-pdf skill. |
| [#1845](https://github.com/gaia-research/gaia-skill-tree/issues/1845) | [`garrytan/brain-taxonomist`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-taxonomist/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Active GBrain schema-pack filing gate is part of brain-ops, not independent general taxonomy. |
| [#1846](https://github.com/gaia-research/gaia-skill-tree/issues/1846) | [`garrytan/briefing`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/briefing/SKILL.md) | accepted | write-report | 2 | ESCALATE | Daily briefing combining meetings, deals, and citations may fit project-management rather than write-report; decide mapping. |
| [#1847](https://github.com/gaia-research/gaia-skill-tree/issues/1847) | [`garrytan/bulk-ingestion`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md) | accepted | knowledge-harvest | 2 | ESCALATE | Manifested bulk corpus lifecycle spans knowledge-harvest and workflow-automation; decide reusable boundary. |
| [#1848](https://github.com/gaia-research/gaia-skill-tree/issues/1848) | [`garrytan/chat-connectors`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/chat-connectors/SKILL.md) | accepted | personal-knowledge-management | 2 | ESCALATE | Account-cookie connectors and incremental conversation sync are GBrain-specific and security-sensitive; verify portability/attribution before admission. |
| [#1849](https://github.com/gaia-research/gaia-skill-tree/issues/1849) | [`garrytan/citation-fixer`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-fixer/SKILL.md) | mapped | cite-sources | — | no | GBrain citation-format sweeper is a local repair stage of source citation. |
| [#1850](https://github.com/gaia-research/gaia-skill-tree/issues/1850) | [`garrytan/citation-graph-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md) | accepted | knowledge-graph-build | 2 | no | Typed inter-document reference graph extraction adds a distinct graph-building procedure. |
| [#1851](https://github.com/gaia-research/gaia-skill-tree/issues/1851) | [`garrytan/cold-start`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cold-start/SKILL.md) | mapped | garrytan/setup-gbrain; agent-environment-setup | — | no | Day-one GBrain connector bootstrap overlaps existing setup-gbrain and broad suite onboarding. |
| [#1852](https://github.com/gaia-research/gaia-skill-tree/issues/1852) | [`garrytan/company-brainify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/company-brainify/SKILL.md) | deferred | guardrails / personal-knowledge-management | — | ESCALATE | Sanitized company export is powerful but privacy-sensitive and spans governance and knowledge management; decide safe reusable scope and tests. |
| [#1853](https://github.com/gaia-research/gaia-skill-tree/issues/1853) | [`garrytan/context-audit`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/context-audit/SKILL.md) | accepted | context-compression | 2 | no | Audits always-loaded agent context for redundancy and contradictions, distinct from session-save skills. |
| [#1854](https://github.com/gaia-research/gaia-skill-tree/issues/1854) | [`garrytan/conversation-archive`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md) | accepted | personal-knowledge-management | 2 | ESCALATE | Importing private chat exports into brain has distinct workflow but may duplicate chat-connectors; privacy/portability decision needed. |
| [#1855](https://github.com/gaia-research/gaia-skill-tree/issues/1855) | [`garrytan/correction-pipeline`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/correction-pipeline/SKILL.md) | mapped | garrytan/brain-ops; systematic-debugging | — | no | Factual error remediation is GBrain-specific source-repair within brain-ops. |
| [#1856](https://github.com/gaia-research/gaia-skill-tree/issues/1856) | [`garrytan/cron-scheduler`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cron-scheduler/SKILL.md) | mapped | workflow-automation | — | no | Thin GBrain cron and quiet-hours wrapper lacks distinct portable implementation. |
| [#1857](https://github.com/gaia-research/gaia-skill-tree/issues/1857) | [`garrytan/cross-modal-review`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cross-modal-review/SKILL.md) | mapped | disler/auto-review; auto-review | — | no | Different-model review of a diff overlaps existing auto-review and code-review-pipeline. |
| [#1858](https://github.com/gaia-research/gaia-skill-tree/issues/1858) | [`garrytan/daily-task-manager`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/daily-task-manager/SKILL.md) | mapped | project-management | — | no | GBrain page-backed task CRUD is a local implementation of routine task management. |
| [#1859](https://github.com/gaia-research/gaia-skill-tree/issues/1859) | [`garrytan/daily-task-prep`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/daily-task-prep/SKILL.md) | mapped | garrytan/brain-ops; write-report | — | no | Morning calendar/tasks preparation is a short briefing variant, not a standalone capability. |
| [#1860](https://github.com/gaia-research/gaia-skill-tree/issues/1860) | [`garrytan/data-loss-gate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/data-loss-gate/SKILL.md) | mapped | garrytan/careful; guardrails | — | no | Recoverability confirmation before destructive actions overlaps existing careful guardrails. |
| [#1861](https://github.com/gaia-research/gaia-skill-tree/issues/1861) | [`garrytan/data-research`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/data-research/SKILL.md) | accepted | data-analysis | 2 | ESCALATE | YAML-recipe structured-source research may fit data-analysis, research or knowledge-harvest; choose one. |
| [#1862](https://github.com/gaia-research/gaia-skill-tree/issues/1862) | [`garrytan/db-repair`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/db-repair/SKILL.md) | omitted | — | — | no | Hardcoded gbrain db-repair incident ladder is an internal product maintenance wrapper. |
| [#1863](https://github.com/gaia-research/gaia-skill-tree/issues/1863) | [`garrytan/draft-in-voice`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/draft-in-voice/SKILL.md) | accepted | ghostwrite | 2 | no | Voice-profile-grounded drafts with fidelity check implement existing ghostwrite generic. |
| [#1864](https://github.com/gaia-research/gaia-skill-tree/issues/1864) | [`garrytan/eiirp`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/eiirp/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Seven-phase brain filing closeout and schema check is suite-local organizer. |
| [#1865](https://github.com/gaia-research/gaia-skill-tree/issues/1865) | [`garrytan/enrich`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/enrich/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Person/company page enrichment is GBrain-specific existing brain-ops behavior. |
| [#1866](https://github.com/gaia-research/gaia-skill-tree/issues/1866) | [`garrytan/fact-check`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/fact-check/SKILL.md) | accepted | grounding | 2 | ESCALATE | Claim-level fact check can fit grounding, cite-sources or verification-before-completion; choose canonical mapping. |
| [#1867](https://github.com/gaia-research/gaia-skill-tree/issues/1867) | [`garrytan/frontmatter-guard`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/frontmatter-guard/SKILL.md) | omitted | — | — | no | GBrain frontmatter CLI validator/repair is an internal schema hygiene tool. |
| [#1868](https://github.com/gaia-research/gaia-skill-tree/issues/1868) | [`garrytan/functional-area-resolver`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/functional-area-resolver/SKILL.md) | accepted | route-intent | 2 | ESCALATE | Functional-area routing-file compression spans route-intent and context-compression; choose target; inspect claimed held-out eval before using it as evidence. |
| [#1869](https://github.com/gaia-research/gaia-skill-tree/issues/1869) | [`garrytan/gbrain-advisor`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/gbrain-advisor/SKILL.md) | omitted | — | — | no | Hardcoded gbrain advisor checkup is product-specific maintenance rather than transferable method. |
| [#1870](https://github.com/gaia-research/gaia-skill-tree/issues/1870) | [`garrytan/gbrain-upgrade`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/gbrain-upgrade/SKILL.md) | omitted | — | — | no | Hardcoded gbrain self-upgrade notification/auto mode is product-specific maintenance. |
| [#1871](https://github.com/gaia-research/gaia-skill-tree/issues/1871) | [`garrytan/google-loops`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/google-loops/SKILL.md) | accepted | personal-knowledge-management | 2 | ESCALATE | Google OAuth connector and open-loop tracking crosses PKM and project-management; decide reusable boundary. |
| [#1872](https://github.com/gaia-research/gaia-skill-tree/issues/1872) | [`garrytan/idea-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/idea-ingest/SKILL.md) | mapped | garrytan/capture; personal-knowledge-management | — | no | Link/article idea capture to brain already represented by capture. |
| [#1873](https://github.com/gaia-research/gaia-skill-tree/issues/1873) | [`garrytan/idea-lineage`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/idea-lineage/SKILL.md) | accepted | concept-synthesis | 2 | no | Single-idea historical lineage and reversal tracing distinguishes this from broad concept maps. |
| [#1874](https://github.com/gaia-research/gaia-skill-tree/issues/1874) | [`garrytan/ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/ingest/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Dispatcher of GBrain ingestion skills belongs to existing brain-ops suite. |
| [#1875](https://github.com/gaia-research/gaia-skill-tree/issues/1875) | [`garrytan/maintain`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/maintain/SKILL.md) | mapped | garrytan/brain-ops; registry-health-scan | — | no | GBrain backlink/staleness health check is suite maintenance, not distinct generic implementation. |
| [#1876](https://github.com/gaia-research/gaia-skill-tree/issues/1876) | [`garrytan/measure-before-you-fix`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/measure-before-you-fix/SKILL.md) | accepted | systematic-debugging | 2 | no | Timed measurement-before-fix protocol is a distinct systematic-debugging implementation. |
| [#1877](https://github.com/gaia-research/gaia-skill-tree/issues/1877) | [`garrytan/media-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/media-ingest/SKILL.md) | mapped | garrytan/capture; personal-knowledge-management | — | no | Media/PDF/video capture into brain overlaps capture and ingestion umbrella. |
| [#1878](https://github.com/gaia-research/gaia-skill-tree/issues/1878) | [`garrytan/meeting-ingestion`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md) | accepted | personal-knowledge-management | 2 | ESCALATE | Recorder-agnostic transcript ingestion has reusable stages but GBrain-specific writes; choose PKM vs speech-to-text and privacy scope. |
| [#1879](https://github.com/gaia-research/gaia-skill-tree/issues/1879) | [`garrytan/migrate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/migrate/SKILL.md) | mapped | garrytan/setup-gbrain; knowledge-management | — | no | Wiki/notes migration is GBrain import variant, not an independent methodology. |
| [#1880](https://github.com/gaia-research/gaia-skill-tree/issues/1880) | [`garrytan/minion-orchestrator`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/minion-orchestrator/SKILL.md) | accepted | multi-agent-orchestration-v | 2 | ESCALATE | Durable shell jobs plus LLM workers spans worker-agent-dispatch and multi-agent-orchestration-v; decide safe generic mapping. |
| [#1881](https://github.com/gaia-research/gaia-skill-tree/issues/1881) | [`garrytan/perplexity-research`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/perplexity-research/SKILL.md) | mapped | mvanhorn/last30days; autonomous-web-research | — | no | Perplexity-backed research with brain context overlaps existing autonomous-web-research implementations. |
| [#1882](https://github.com/gaia-research/gaia-skill-tree/issues/1882) | [`garrytan/postgres-adopt`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/postgres-adopt/SKILL.md) | omitted | — | — | no | GBrain PGLite-to-Postgres engine migration wrapper is product-local installer maintenance. |
| [#1883](https://github.com/gaia-research/gaia-skill-tree/issues/1883) | [`garrytan/publish`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/publish/SKILL.md) | mapped | garrytan/document-generate; document-editing | — | no | GBrain-specific share-page HTML output overlaps existing document generation/export. |
| [#1884](https://github.com/gaia-research/gaia-skill-tree/issues/1884) | [`garrytan/query`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/query/SKILL.md) | mapped | garrytan/brain-ops; question-answer | — | no | Brain MCP three-layer search/citation answer is core GBrain query method. |
| [#1885](https://github.com/gaia-research/gaia-skill-tree/issues/1885) | [`garrytan/repo-architecture`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/repo-architecture/SKILL.md) | omitted | — | — | no | Short GBrain directory-placement reference is not a standalone transferable implementation. |
| [#1886](https://github.com/gaia-research/gaia-skill-tree/issues/1886) | [`garrytan/reports`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/reports/SKILL.md) | mapped | garrytan/brain-ops; write-report | — | no | GBrain timestamped report storage and retrieval is a local storage wrapper. |
| [#1887](https://github.com/gaia-research/gaia-skill-tree/issues/1887) | [`garrytan/research-compendium`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/research-compendium/SKILL.md) | accepted | autonomous-web-research | 2 | ESCALATE | Archived source-by-source compendium crosses literature-review and autonomous-web-research; retention/copyright gate needs reviewer. |
| [#1888](https://github.com/gaia-research/gaia-skill-tree/issues/1888) | [`garrytan/resolve-before-asking`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/resolve-before-asking/SKILL.md) | mapped | garrytan/brain-ops; question-answer | — | no | GBrain identity lookup before asking user is a local query quality rule. |
| [#1889](https://github.com/gaia-research/gaia-skill-tree/issues/1889) | [`garrytan/schema-author`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/schema-author/SKILL.md) | omitted | — | — | no | GBrain schema-pack authoring and backfill command wrapper is local product administration. |
| [#1890](https://github.com/gaia-research/gaia-skill-tree/issues/1890) | [`garrytan/schema-unify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/schema-unify/SKILL.md) | omitted | — | — | no | Named gbrain-base-v2 taxonomy migration is one product/version-specific operation. |
| [#1891](https://github.com/gaia-research/gaia-skill-tree/issues/1891) | [`garrytan/setup`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/setup/SKILL.md) | mapped | garrytan/setup-gbrain; agent-environment-setup | — | no | Existing same-author setup-gbrain already handles GBrain onboarding. |
| [#1892](https://github.com/gaia-research/gaia-skill-tree/issues/1892) | [`garrytan/signal-detector`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/signal-detector/SKILL.md) | deferred | knowledge-harvest / personal-knowledge-management | — | ESCALATE | Ambient capture of inbound messages may be useful but privacy/consent and cross-platform reusability need explicit reviewer decision. |
| [#1893](https://github.com/gaia-research/gaia-skill-tree/issues/1893) | [`garrytan/skill-autobench`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md) | accepted | skill-performance-benchmarking | 2 | no | Grounded per-skill eval-contract and failure-improvement benchmark loop is distinct from existing benchmark-models. |
| [#1894](https://github.com/gaia-research/gaia-skill-tree/issues/1894) | [`garrytan/skill-creator`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skill-creator/SKILL.md) | mapped | garrytan/skillify; skill-authoring | — | no | Thin scaffold generator duplicates same author's existing skillify and authoring tools. |
| [#1895](https://github.com/gaia-research/gaia-skill-tree/issues/1895) | [`garrytan/skill-optimizer`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skill-optimizer/SKILL.md) | accepted | prompt-optimization | 2 | ESCALATE | SkillOpt skill-text optimization may fit prompt-optimization or recursive-self-improvement; check source/paper and benchmark before admission. |
| [#1896](https://github.com/gaia-research/gaia-skill-tree/issues/1896) | [`garrytan/skillify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skillify/SKILL.md) | mapped | garrytan/skillify | — | no | Existing named skill already implements same upstream SKILL.md at a different path; reconcile links/version instead. |
| [#1897](https://github.com/gaia-research/gaia-skill-tree/issues/1897) | [`garrytan/skillpack-check`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skillpack-check/SKILL.md) | omitted | — | — | no | One gbrain skillpack-check command wrapper, internal installation health probe. |
| [#1898](https://github.com/gaia-research/gaia-skill-tree/issues/1898) | [`garrytan/skillpack-harvest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skillpack-harvest/SKILL.md) | omitted | — | — | no | GBrain skillpack harvest manifest/CLI wrapper is internal packaging utility. |
| [#1899](https://github.com/gaia-research/gaia-skill-tree/issues/1899) | [`garrytan/smoke-test`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/smoke-test/SKILL.md) | omitted | — | — | no | GBrain/OpenClaw service health script wrapper and machine repair are product-local maintenance. |
| [#1900](https://github.com/gaia-research/gaia-skill-tree/issues/1900) | [`garrytan/soul-audit`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/soul-audit/SKILL.md) | mapped | agent-environment-setup | — | no | Identity interview and bootstrap file rendering are GBrain-specific setup variation. |
| [#1901](https://github.com/gaia-research/gaia-skill-tree/issues/1901) | [`garrytan/strategic-reading`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/strategic-reading/SKILL.md) | accepted | document-analyst | 2 | ESCALATE | Strategic reading applies source to a live decision; could fit document-analyst or research; resolve target. |
| [#1902](https://github.com/gaia-research/gaia-skill-tree/issues/1902) | [`garrytan/testing`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/testing/SKILL.md) | mapped | garrytan/health; automated-testing | — | no | Skill conformance and test-suite health overlap existing health/testing implementation. |
| [#1903](https://github.com/gaia-research/gaia-skill-tree/issues/1903) | [`garrytan/two-tier-extraction`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md) | accepted | classify | 2 | ESCALATE | Tiered corpus extraction spans classify, extract-entities, and workflow-automation; determine meaningful target. |
| [#1904](https://github.com/gaia-research/gaia-skill-tree/issues/1904) | [`garrytan/voice-note-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/voice-note-ingest/SKILL.md) | accepted | speech-to-text | 2 | ESCALATE | Verbatim voice-note archiving differs from transcription alone and may instead be personal-knowledge-management; choose target. |
| [#1905](https://github.com/gaia-research/gaia-skill-tree/issues/1905) | [`garrytan/webhook-transforms`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/webhook-transforms/SKILL.md) | omitted | — | — | no | Short GBrain-specific webhook-to-brain transform wiring lacks distinct portable substance. |
| [#1913](https://github.com/gaia-research/gaia-skill-tree/issues/1913) | [`garrytan/remote-mcp`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md) | accepted | mcp-integration | 2 | ESCALATE | Tailscale/Funnel publishing of own GBrain MCP is more than MCP client integration; compare mcp-server-creation, mcp-integration, existing ruvnet/agentdb and sickn33/mcp-builder; decide security and ownership. |

### Lane 02 counts

| Disposition / gate | Count |
|---|---:|
| accepted | 42 |
| mapped | 38 |
| deferred | 2 |
| omitted | 13 |
| ESCALATE (cross-cutting flag) | 30 |

The release-pinned source URLs are attribution/source pointers, not independent scoring evidence. A final reviewer must verify installability, canonical upstream authorship and current link liveness again before CLI ingestion; 3★+ requires a verified blob and 4★+ requires live evidence plus TM gate. Until every ESCALATE row is resolved, the implementation checklist above remains open.
