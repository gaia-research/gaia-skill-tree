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

## Candidate decision matrix — Lane 02B final adjudication

Lane 02's first-pass proposals have been adjudicated for the 31 escalated rows. **These decisions are not approval to mutate the registry**. All 95 release-pinned upstream `SKILL.md` files resolved at their raw GitHub URLs (1,120,899 source bytes in total); all have a nonempty description and a frontmatter `name` matching the candidate slug. The four GitHub source repositories are public, not archived, and their current owners match the cited upstream accounts (`addyosmani`, `obra`, `heygen-com`, `garrytan`); the Gaia handle `addy-osmani` differs intentionally from upstream account `addyosmani`. GBrain’s four exceptions (#1893, #1896, #1898, #1902) exist only under the release-pinned `skills/` path, not `plugin/skills/`; the other 67 GBrain source blobs are byte-identical at both locations. Source URLs below point to the inspected file. The named registry and existing generic references were compared with the sources; proposed ranks are conservative 2★ entry estimates, **not** TM-calibrated grades. No upstream claim or popularity number has been treated as verified scoring evidence.

**Gate:** Lane 02B resolved all 31 previously escalated rows; `ESCALATE = 0`. These are final *curation dispositions*, not implementation approval: `accepted` remains a candidate for later verified intake, and `deferred` explicitly excludes implementation until its stated question is resolved. `mapped` points to an existing named skill and/or existing starless generic reference; it does not create a named implementation. No new generic or fusion topology is authorized by this pass. **Suite membership is not implied by an accepted named-skill proposal:** adding components to an existing suite would materially change fusion topology and requires a separate explicit reviewer decision; do not blindly ingest watcher-proposed component lists.

| Issue | Candidate / inspected source | Disposition | Mapping / target (`genericSkillRef` for accepted) | Star proposal | Escalate? | Reason / exact review question |
|---|---|---|---|---|---|---|
| [#1551](https://github.com/gaia-research/gaia-skill-tree/issues/1551) | [`addy-osmani/api-and-interface-design`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/api-and-interface-design/SKILL.md) | accepted | software-design | 2 | no | Stable API contract and interface design procedure; distinct Addy implementation. |
| [#1552](https://github.com/gaia-research/gaia-skill-tree/issues/1552) | [`addy-osmani/browser-testing-with-devtools`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/browser-testing-with-devtools/SKILL.md) | accepted | browser-control | 2 | no | Concrete Chrome DevTools MCP debugging and browser-verification procedure. |
| [#1553](https://github.com/gaia-research/gaia-skill-tree/issues/1553) | [`addy-osmani/ci-cd-and-automation`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/ci-cd-and-automation/SKILL.md) | accepted | deployment-automation | 2 | no | Quality-gate CI pipeline and deployment workflow, distinct from existing launch skill. |
| [#1554](https://github.com/gaia-research/gaia-skill-tree/issues/1554) | [`addy-osmani/context-engineering`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/context-engineering/SKILL.md) | accepted | agent-environment-setup | 2 | no | Lane 02B: rules-file scaffolding, specs, and session setup are the central procedure; agent-environment-setup fits, unlike large-output routing or token compression. Distinct reusable setup workflow; 2★ only, subject to normal intake evidence. |
| [#1555](https://github.com/gaia-research/gaia-skill-tree/issues/1555) | [`addy-osmani/debugging-and-error-recovery`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/debugging-and-error-recovery/SKILL.md) | mapped | obra/systematic-debugging; systematic-debugging | — | no | Broad stop-the-line root-cause protocol overlaps existing systematic-debugging implementations. |
| [#1556](https://github.com/gaia-research/gaia-skill-tree/issues/1556) | [`addy-osmani/deprecation-and-migration`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/deprecation-and-migration/SKILL.md) | deferred | proposed deprecation/migration generic (not yet in registry) | — | no | Lane 02B changed accepted → deferred: lifecycle sunsetting, API compatibility, and expand/contract migration are neither framework-version upgrading nor connecting subsystems. Maintainer must decide whether a dedicated migration generic is warranted and its boundary before admission. |
| [#1557](https://github.com/gaia-research/gaia-skill-tree/issues/1557) | [`addy-osmani/documentation-and-adrs`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/documentation-and-adrs/SKILL.md) | accepted | write-report | 2 | no | Lane 02B: deliverable is decision/API documentation with alternatives and upkeep, not implementation of module interfaces; write-report is the closest existing generic. Distinct ADR-first writing procedure; conservative 2★. |
| [#1558](https://github.com/gaia-research/gaia-skill-tree/issues/1558) | [`addy-osmani/doubt-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/doubt-driven-development/SKILL.md) | deferred | design-review / self-critique / auto-review (unresolved) | — | no | Lane 02B changed accepted → deferred: a fresh-context, cross-model in-flight reviewer is not self-critique, design questioning, or auto-review's executable acceptance script. Maintainer must settle cross-artifact adversarial-review ownership and its relation to existing review skills. |
| [#1559](https://github.com/gaia-research/gaia-skill-tree/issues/1559) | [`addy-osmani/frontend-ui-engineering`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/frontend-ui-engineering/SKILL.md) | accepted | design-generation | 2 | no | Lane 02B: concrete UI-component generation with design-system fidelity is primary; accessibility and state/performance checks are quality constraints, not separate generic memberships. Do not claim full-stack implementation or automatic fusion topology; conservative 2★. |
| [#1560](https://github.com/gaia-research/gaia-skill-tree/issues/1560) | [`addy-osmani/git-workflow-and-versioning`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/git-workflow-and-versioning/SKILL.md) | mapped | obra/using-git-worktrees; git-integration | — | no | General git branching and versioning guidance overlaps existing workflow implementations. |
| [#1561](https://github.com/gaia-research/gaia-skill-tree/issues/1561) | [`addy-osmani/idea-refine`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/idea-refine/SKILL.md) | mapped | obra/brainstorming; brainstorming | — | no | Diverge/converge idea shaping already implemented by brainstorming. |
| [#1563](https://github.com/gaia-research/gaia-skill-tree/issues/1563) | [`addy-osmani/interview-me`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/interview-me/SKILL.md) | mapped | mattpocock/grill-me; grill-me | — | no | One-question-at-a-time intent interview already represented by grill-me. |
| [#1564](https://github.com/gaia-research/gaia-skill-tree/issues/1564) | [`addy-osmani/observability-and-instrumentation`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/observability-and-instrumentation/SKILL.md) | deferred | proposed system-observability/instrumentation generic (not yet in registry) | — | no | Lane 02B changed accepted → deferred: producing logs, metrics, traces, and alerting is not detecting anomalies or tracking LLM token cost. Maintainer must define an instrumentation generic and its boundary with existing monitoring nodes before accepting this implementation. |
| [#1565](https://github.com/gaia-research/gaia-skill-tree/issues/1565) | [`addy-osmani/security-and-hardening`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/security-and-hardening/SKILL.md) | accepted | security-audit | 2 | no | Threat modeling and OWASP hardening protocol, distinct source implementation of security-audit. |
| [#1566](https://github.com/gaia-research/gaia-skill-tree/issues/1566) | [`addy-osmani/source-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/source-driven-development/SKILL.md) | accepted | grounding | 2 | no | Explicit official-source citation and verification before implementation; distinct grounding workflow. |
| [#1567](https://github.com/gaia-research/gaia-skill-tree/issues/1567) | [`addy-osmani/using-agent-skills`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/using-agent-skills/SKILL.md) | mapped | vercel/find-skills; skill-discovery | — | no | Agent skill discovery and invocation already represented by find-skills. |
| [#1653](https://github.com/gaia-research/gaia-skill-tree/issues/1653) | [`addy-osmani/constraint-driven-development`](https://github.com/addyosmani/agent-skills/blob/0.6.10/skills/constraint-driven-development/SKILL.md) | accepted | guardrails | 2 | no | Written CONSTRAINTS.md quality floor with change-detection gate; distinct implementation of guardrails. |
| [#1571](https://github.com/gaia-research/gaia-skill-tree/issues/1571) | [`obra/test-driven-development`](https://github.com/obra/superpowers/blob/v6.4.1/skills/test-driven-development/SKILL.md) | accepted | test-driven-development | 2 | no | Obra red-green-refactor implementation with explicit failure-first checks; existing generic and Addy/Matt variants. |
| [#1572](https://github.com/gaia-research/gaia-skill-tree/issues/1572) | [`obra/using-superpowers`](https://github.com/obra/superpowers/blob/v6.4.1/skills/using-superpowers/SKILL.md) | mapped | obra/superpowers; superpowers | — | no | Bootstrap skill router belongs to existing Superpowers suite, not a new named capability. |
| [#1573](https://github.com/gaia-research/gaia-skill-tree/issues/1573) | [`obra/writing-skills`](https://github.com/obra/superpowers/blob/v6.4.1/skills/writing-skills/SKILL.md) | accepted | skill-authoring | 2 | no | TDD-based skill writing and verification method; distinct from generic authoring variants. |
| [#1910](https://github.com/gaia-research/gaia-skill-tree/issues/1910) | [`obra/diagnosing-superpowers`](https://github.com/obra/superpowers/blob/v6.4.1/skills/diagnosing-superpowers/SKILL.md) | omitted | — | — | no | Lane 02B changed accepted → omitted: this gathers path:line session evidence for Superpowers maintainers, explicitly refuses to diagnose/fix, and depends on its proprietary transcript templates; not a standalone general debugger or benchmark implementation. |
| [#1824](https://github.com/gaia-research/gaia-skill-tree/issues/1824) | [`heygen-com/general-video`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/general-video/SKILL.md) | accepted | video-composition | 2 | no | Distinct long/multi-scene freeform composition method when specialized HyperFrames workflows do not fit; existing video-composition generic. |
| [#1825](https://github.com/gaia-research/gaia-skill-tree/issues/1825) | [`heygen-com/hyperframes`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/hyperframes/SKILL.md) | mapped | heygen-com/hyperframes | — | no | Existing named skill already represents the exact same upstream entrypoint; update its provenance/version instead. |
| [#1911](https://github.com/gaia-research/gaia-skill-tree/issues/1911) | [`heygen-com/hyperframes-studio`](https://github.com/heygen-com/hyperframes/blob/v0.8.60/skills/hyperframes-studio/SKILL.md) | omitted | — | — | no | HyperFrames Studio-only track-index, sub-composition and safe-zone conventions; no standalone portable editing workflow. |
| [#1836](https://github.com/gaia-research/gaia-skill-tree/issues/1836) | [`garrytan/academic-verify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/academic-verify/SKILL.md) | accepted | grounding | 2 | no | Lane 02B: verifies an existing research claim through methodology, data, and independent replication; retrieval is a means, not the capability. Grounding fits the claim-verdict output; GBrain storage is incidental, not scoring evidence. 2★. |
| [#1837](https://github.com/gaia-research/gaia-skill-tree/issues/1837) | [`garrytan/archive-crawler`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/archive-crawler/SKILL.md) | accepted | knowledge-harvest | 2 | no | Lane 02B: allowlisted inventory, gold filtering, manifest, and trial ingestion across archive sources form a reusable harvesting method. Personal-vault filing is an adapter; explicit scope/consent boundary must survive implementation. 2★. |
| [#1838](https://github.com/gaia-research/gaia-skill-tree/issues/1838) | [`garrytan/article-enrichment`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/article-enrichment/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Article summaries and quotations are a narrow source-enrichment stage of existing brain-ops. |
| [#1839](https://github.com/gaia-research/gaia-skill-tree/issues/1839) | [`garrytan/ask-user`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/ask-user/SKILL.md) | mapped | mattpocock/grill-me; questionnaire-generation | — | no | Human decision gating with choices is a small interaction pattern rather than distinct named implementation. |
| [#1840](https://github.com/gaia-research/gaia-skill-tree/issues/1840) | [`garrytan/blog-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/blog-ingest/SKILL.md) | accepted | knowledge-harvest | 2 | no | Lane 02B: feed discovery is only the input; pagination, canonical-URL dedup, trial, and source-page ingestion are knowledge harvesting rather than update monitoring. Distinct whole-publication method; 2★. |
| [#1841](https://github.com/gaia-research/gaia-skill-tree/issues/1841) | [`garrytan/book-mirror`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/book-mirror/SKILL.md) | deferred | document-analyst / personal-knowledge-management (unresolved) | — | no | Lane 02B changed accepted → deferred: chapter analysis plus intimate user-memory mirroring requires the GBrain book-mirror CLI and private context. Maintainer must establish a portable non-GBrain procedure, user-consent boundary, and rights-safe book handling before choosing a generic. |
| [#1842](https://github.com/gaia-research/gaia-skill-tree/issues/1842) | [`garrytan/brain-ingest-gate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-ingest-gate/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | GBrain-specific prewrite dedup/entity gate belongs to existing brain-ops implementation. |
| [#1843](https://github.com/gaia-research/gaia-skill-tree/issues/1843) | [`garrytan/brain-link-discipline`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-link-discipline/SKILL.md) | omitted | — | — | no | Brain-page link-delivery convention relies on GBrain path/remote; too narrow as standalone skill. |
| [#1844](https://github.com/gaia-research/gaia-skill-tree/issues/1844) | [`garrytan/brain-pdf`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-pdf/SKILL.md) | mapped | garrytan/make-pdf; format-output | — | no | PDF export is already covered by the same author's make-pdf skill. |
| [#1845](https://github.com/gaia-research/gaia-skill-tree/issues/1845) | [`garrytan/brain-taxonomist`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/brain-taxonomist/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Active GBrain schema-pack filing gate is part of brain-ops, not independent general taxonomy. |
| [#1846](https://github.com/gaia-research/gaia-skill-tree/issues/1846) | [`garrytan/briefing`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/briefing/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Lane 02B changed accepted → mapped: read-only GBrain pulls for daily meetings/deals with citations are a brain-ops synthesis/report route, not a second general report-writing named skill; existing suite target is concrete, without adding topology. |
| [#1847](https://github.com/gaia-research/gaia-skill-tree/issues/1847) | [`garrytan/bulk-ingestion`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/bulk-ingestion/SKILL.md) | accepted | knowledge-harvest | 2 | no | Lane 02B: schema → access → trial → improvement → manifested bulk ingest is a transferable corpus-harvesting protocol; job orchestration is a mechanism. Keep GBrain write paths out of the generic claim; 2★. |
| [#1848](https://github.com/gaia-research/gaia-skill-tree/issues/1848) | [`garrytan/chat-connectors`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/chat-connectors/SKILL.md) | omitted | — | — | no | Lane 02B changed accepted → omitted: raw ChatGPT/Claude cookie/sessionKey extraction and GBrain-specific sync commands are sensitive product connector operations, not a portable independent skill; do not market private-account scraping as generic PKM. |
| [#1849](https://github.com/gaia-research/gaia-skill-tree/issues/1849) | [`garrytan/citation-fixer`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-fixer/SKILL.md) | mapped | cite-sources | — | no | GBrain citation-format sweeper is a local repair stage of source citation. |
| [#1850](https://github.com/gaia-research/gaia-skill-tree/issues/1850) | [`garrytan/citation-graph-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/citation-graph-ingest/SKILL.md) | accepted | knowledge-graph-build | 2 | no | Typed inter-document reference graph extraction adds a distinct graph-building procedure. |
| [#1851](https://github.com/gaia-research/gaia-skill-tree/issues/1851) | [`garrytan/cold-start`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cold-start/SKILL.md) | mapped | garrytan/setup-gbrain; agent-environment-setup | — | no | Day-one GBrain connector bootstrap overlaps existing setup-gbrain and broad suite onboarding. |
| [#1852](https://github.com/gaia-research/gaia-skill-tree/issues/1852) | [`garrytan/company-brainify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/company-brainify/SKILL.md) | deferred | guardrails / personal-knowledge-management (unresolved) | — | no | Lane 02B upheld deferred: sanitizing pages, embedded facts/takes, backlinks, and git history before team sharing is valuable but fail-open leakage is costly. Require privacy threat model, independently verified redaction/rollback tests, and explicit ownership of governance vs PKM before intake. |
| [#1853](https://github.com/gaia-research/gaia-skill-tree/issues/1853) | [`garrytan/context-audit`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/context-audit/SKILL.md) | accepted | context-compression | 2 | no | Audits always-loaded agent context for redundancy and contradictions, distinct from session-save skills. |
| [#1854](https://github.com/gaia-research/gaia-skill-tree/issues/1854) | [`garrytan/conversation-archive`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/conversation-archive/SKILL.md) | accepted | personal-knowledge-management | 2 | no | Lane 02B: user-supplied export parsing, mandatory pre-write PII/secret scrub, trial import, and validation are an offline archive pipeline, distinct from live account-cookie sync. Reusable with consent and local-only storage; no implied third-party transcript sharing. 2★. |
| [#1855](https://github.com/gaia-research/gaia-skill-tree/issues/1855) | [`garrytan/correction-pipeline`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/correction-pipeline/SKILL.md) | mapped | garrytan/brain-ops; systematic-debugging | — | no | Factual error remediation is GBrain-specific source-repair within brain-ops. |
| [#1856](https://github.com/gaia-research/gaia-skill-tree/issues/1856) | [`garrytan/cron-scheduler`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cron-scheduler/SKILL.md) | mapped | workflow-automation | — | no | Thin GBrain cron and quiet-hours wrapper lacks distinct portable implementation. |
| [#1857](https://github.com/gaia-research/gaia-skill-tree/issues/1857) | [`garrytan/cross-modal-review`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/cross-modal-review/SKILL.md) | mapped | disler/auto-review; auto-review | — | no | Different-model review of a diff overlaps existing auto-review and code-review-pipeline. |
| [#1858](https://github.com/gaia-research/gaia-skill-tree/issues/1858) | [`garrytan/daily-task-manager`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/daily-task-manager/SKILL.md) | mapped | project-management | — | no | GBrain page-backed task CRUD is a local implementation of routine task management. |
| [#1859](https://github.com/gaia-research/gaia-skill-tree/issues/1859) | [`garrytan/daily-task-prep`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/daily-task-prep/SKILL.md) | mapped | garrytan/brain-ops; write-report | — | no | Morning calendar/tasks preparation is a short briefing variant, not a standalone capability. |
| [#1860](https://github.com/gaia-research/gaia-skill-tree/issues/1860) | [`garrytan/data-loss-gate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/data-loss-gate/SKILL.md) | mapped | garrytan/careful; guardrails | — | no | Recoverability confirmation before destructive actions overlaps existing careful guardrails. |
| [#1861](https://github.com/gaia-research/gaia-skill-tree/issues/1861) | [`garrytan/data-research`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/data-research/SKILL.md) | accepted | research | 2 | no | Lane 02B: recipe-driven source search, structured extraction, dedup, and cited tracker updates are information gathering rather than SQL/statistical analysis. Research covers the multi-source inquiry; brain-page storage is an adapter. 2★. |
| [#1862](https://github.com/gaia-research/gaia-skill-tree/issues/1862) | [`garrytan/db-repair`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/db-repair/SKILL.md) | omitted | — | — | no | Hardcoded gbrain db-repair incident ladder is an internal product maintenance wrapper. |
| [#1863](https://github.com/gaia-research/gaia-skill-tree/issues/1863) | [`garrytan/draft-in-voice`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/draft-in-voice/SKILL.md) | accepted | ghostwrite | 2 | no | Voice-profile-grounded drafts with fidelity check implement existing ghostwrite generic. |
| [#1864](https://github.com/gaia-research/gaia-skill-tree/issues/1864) | [`garrytan/eiirp`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/eiirp/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Seven-phase brain filing closeout and schema check is suite-local organizer. |
| [#1865](https://github.com/gaia-research/gaia-skill-tree/issues/1865) | [`garrytan/enrich`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/enrich/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Person/company page enrichment is GBrain-specific existing brain-ops behavior. |
| [#1866](https://github.com/gaia-research/gaia-skill-tree/issues/1866) | [`garrytan/fact-check`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/fact-check/SKILL.md) | accepted | grounding | 2 | no | Lane 02B: claim-by-claim source hierarchy and confidence verdict verify factual assertions; citations are supporting artifacts, not the primary capability. Grounding is the exact existing generic; distinct desk-style procedure. 2★. |
| [#1867](https://github.com/gaia-research/gaia-skill-tree/issues/1867) | [`garrytan/frontmatter-guard`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/frontmatter-guard/SKILL.md) | omitted | — | — | no | GBrain frontmatter CLI validator/repair is an internal schema hygiene tool. |
| [#1868](https://github.com/gaia-research/gaia-skill-tree/issues/1868) | [`garrytan/functional-area-resolver`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/functional-area-resolver/SKILL.md) | accepted | route-intent | 2 | no | Lane 02B: grouped dispatchers preserve correct skill routing, with token reduction as a side effect. Route-intent owns it, not text summarization. Upstream n=5 saturated held-out and single-vendor results are claims, NOT independently verified benchmark evidence or a higher-star basis; 2★. |
| [#1869](https://github.com/gaia-research/gaia-skill-tree/issues/1869) | [`garrytan/gbrain-advisor`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/gbrain-advisor/SKILL.md) | omitted | — | — | no | Hardcoded gbrain advisor checkup is product-specific maintenance rather than transferable method. |
| [#1870](https://github.com/gaia-research/gaia-skill-tree/issues/1870) | [`garrytan/gbrain-upgrade`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/gbrain-upgrade/SKILL.md) | omitted | — | — | no | Hardcoded gbrain self-upgrade notification/auto mode is product-specific maintenance. |
| [#1871](https://github.com/gaia-research/gaia-skill-tree/issues/1871) | [`garrytan/google-loops`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/google-loops/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Lane 02B changed accepted → mapped: setup of GBrain Gmail/Calendar/Contacts connector plus `gbrain waiting` operational wrapper is specific to existing brain-ops knowledge flow; no independent cross-provider task-management method. |
| [#1872](https://github.com/gaia-research/gaia-skill-tree/issues/1872) | [`garrytan/idea-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/idea-ingest/SKILL.md) | mapped | garrytan/capture; personal-knowledge-management | — | no | Link/article idea capture to brain already represented by capture. |
| [#1873](https://github.com/gaia-research/gaia-skill-tree/issues/1873) | [`garrytan/idea-lineage`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/idea-lineage/SKILL.md) | accepted | concept-synthesis | 2 | no | Single-idea historical lineage and reversal tracing distinguishes this from broad concept maps. |
| [#1874](https://github.com/gaia-research/gaia-skill-tree/issues/1874) | [`garrytan/ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/ingest/SKILL.md) | mapped | garrytan/brain-ops; knowledge-management | — | no | Dispatcher of GBrain ingestion skills belongs to existing brain-ops suite. |
| [#1875](https://github.com/gaia-research/gaia-skill-tree/issues/1875) | [`garrytan/maintain`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/maintain/SKILL.md) | mapped | garrytan/brain-ops; registry-health-scan | — | no | GBrain backlink/staleness health check is suite maintenance, not distinct generic implementation. |
| [#1876](https://github.com/gaia-research/gaia-skill-tree/issues/1876) | [`garrytan/measure-before-you-fix`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/measure-before-you-fix/SKILL.md) | accepted | systematic-debugging | 2 | no | Timed measurement-before-fix protocol is a distinct systematic-debugging implementation. |
| [#1877](https://github.com/gaia-research/gaia-skill-tree/issues/1877) | [`garrytan/media-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/media-ingest/SKILL.md) | mapped | garrytan/capture; personal-knowledge-management | — | no | Media/PDF/video capture into brain overlaps capture and ingestion umbrella. |
| [#1878](https://github.com/gaia-research/gaia-skill-tree/issues/1878) | [`garrytan/meeting-ingestion`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/meeting-ingestion/SKILL.md) | accepted | personal-knowledge-management | 2 | no | Lane 02B: normalizes recorder output, splits meetings, resolves speakers, deduplicates, and files decisions/actions; it is not an audio transcription engine. Transferable PKM ingestion with user consent and private transcript handling; 2★. |
| [#1879](https://github.com/gaia-research/gaia-skill-tree/issues/1879) | [`garrytan/migrate`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/migrate/SKILL.md) | mapped | garrytan/setup-gbrain; knowledge-management | — | no | Wiki/notes migration is GBrain import variant, not an independent methodology. |
| [#1880](https://github.com/gaia-research/gaia-skill-tree/issues/1880) | [`garrytan/minion-orchestrator`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/minion-orchestrator/SKILL.md) | accepted | multi-agent-orchestration-v | 2 | no | Lane 02B: task routing, durable LLM-worker lifecycle, steering, and result review dominate; deterministic shell jobs are a secondary lane, not grounds for a new generic. The named implementation is GBrain-specific but the orchestration protocol is reusable; no new fusion topology; 2★. |
| [#1881](https://github.com/gaia-research/gaia-skill-tree/issues/1881) | [`garrytan/perplexity-research`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/perplexity-research/SKILL.md) | mapped | mvanhorn/last30days; autonomous-web-research | — | no | Perplexity-backed research with brain context overlaps existing autonomous-web-research implementations. |
| [#1882](https://github.com/gaia-research/gaia-skill-tree/issues/1882) | [`garrytan/postgres-adopt`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/postgres-adopt/SKILL.md) | omitted | — | — | no | GBrain PGLite-to-Postgres engine migration wrapper is product-local installer maintenance. |
| [#1883](https://github.com/gaia-research/gaia-skill-tree/issues/1883) | [`garrytan/publish`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/publish/SKILL.md) | mapped | garrytan/document-generate; document-editing | — | no | GBrain-specific share-page HTML output overlaps existing document generation/export. |
| [#1884](https://github.com/gaia-research/gaia-skill-tree/issues/1884) | [`garrytan/query`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/query/SKILL.md) | mapped | garrytan/brain-ops; question-answer | — | no | Brain MCP three-layer search/citation answer is core GBrain query method. |
| [#1885](https://github.com/gaia-research/gaia-skill-tree/issues/1885) | [`garrytan/repo-architecture`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/repo-architecture/SKILL.md) | omitted | — | — | no | Short GBrain directory-placement reference is not a standalone transferable implementation. |
| [#1886](https://github.com/gaia-research/gaia-skill-tree/issues/1886) | [`garrytan/reports`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/reports/SKILL.md) | mapped | garrytan/brain-ops; write-report | — | no | GBrain timestamped report storage and retrieval is a local storage wrapper. |
| [#1887](https://github.com/gaia-research/gaia-skill-tree/issues/1887) | [`garrytan/research-compendium`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/research-compendium/SKILL.md) | deferred | autonomous-web-research / research (unresolved) | — | no | Lane 02B changed accepted → deferred: public-source verbatim archiving as default plus full-book branches needs a lawful-retention/licensing policy, alongside consent/privacy gates; maintainer must determine whether portable output is web research, general research, or GBrain-only archive before admission. |
| [#1888](https://github.com/gaia-research/gaia-skill-tree/issues/1888) | [`garrytan/resolve-before-asking`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/resolve-before-asking/SKILL.md) | mapped | garrytan/brain-ops; question-answer | — | no | GBrain identity lookup before asking user is a local query quality rule. |
| [#1889](https://github.com/gaia-research/gaia-skill-tree/issues/1889) | [`garrytan/schema-author`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/schema-author/SKILL.md) | omitted | — | — | no | GBrain schema-pack authoring and backfill command wrapper is local product administration. |
| [#1890](https://github.com/gaia-research/gaia-skill-tree/issues/1890) | [`garrytan/schema-unify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/schema-unify/SKILL.md) | omitted | — | — | no | Named gbrain-base-v2 taxonomy migration is one product/version-specific operation. |
| [#1891](https://github.com/gaia-research/gaia-skill-tree/issues/1891) | [`garrytan/setup`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/setup/SKILL.md) | mapped | garrytan/setup-gbrain; agent-environment-setup | — | no | Existing same-author setup-gbrain already handles GBrain onboarding. |
| [#1892](https://github.com/gaia-research/gaia-skill-tree/issues/1892) | [`garrytan/signal-detector`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/signal-detector/SKILL.md) | deferred | knowledge-harvest / personal-knowledge-management (unresolved) | — | no | Lane 02B upheld deferred: explicit opt-in is present, but background capture of user messages still needs a verifiable consent/revocation/scope contract and independent cross-harness portability evidence before generic ownership is settled. |
| [#1893](https://github.com/gaia-research/gaia-skill-tree/issues/1893) | [`garrytan/skill-autobench`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skill-autobench/SKILL.md) | deferred | skill-performance-benchmarking (candidate; no approved named implementation) | — | no | Lane 02B changed accepted → deferred: source lives under root skills/ and requires private conversation/transcript substrate; verify a runnable installation path and reproducible, consented redacted eval on non-private fixtures before promoting its otherwise distinct usage-grounded benchmark method. |
| [#1894](https://github.com/gaia-research/gaia-skill-tree/issues/1894) | [`garrytan/skill-creator`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skill-creator/SKILL.md) | mapped | anthropic/skill-creator; skill-authoring | — | no | Thin GBrain scaffold generator duplicates existing skill-authoring implementations; gstack/skillify is a different scrape-to-script workflow, not its target. |
| [#1895](https://github.com/gaia-research/gaia-skill-tree/issues/1895) | [`garrytan/skill-optimizer`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skill-optimizer/SKILL.md) | accepted | prompt-optimization | 2 | no | Lane 02B: measured SKILL.md body iteration against train/selection/test tasks is optimizing instructions, not unbounded agent self-modification. Distinct GBrain SkillOpt wrapper with human benchmark gate; paper citation and benchmark claims are upstream provenance, NOT independent trust evidence; 2★. |
| [#1896](https://github.com/gaia-research/gaia-skill-tree/issues/1896) | [`garrytan/skillify`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skillify/SKILL.md) | deferred | garrytan/skillify (existing gstack identity) / skill-authoring (unresolved) | — | no | Lane 02B upheld deferred: existing `garrytan/skillify` points to gstack's scrape-to-script implementation; GBrain's 15-step authoring/eval workflow is not its update or the same install URL. Maintainer must decide a collision-free canonical name and whether this adds substance beyond existing skill-authoring variants; never overwrite the gstack record. |
| [#1897](https://github.com/gaia-research/gaia-skill-tree/issues/1897) | [`garrytan/skillpack-check`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/skillpack-check/SKILL.md) | omitted | — | — | no | One gbrain skillpack-check command wrapper, internal installation health probe. |
| [#1898](https://github.com/gaia-research/gaia-skill-tree/issues/1898) | [`garrytan/skillpack-harvest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/skillpack-harvest/SKILL.md) | omitted | — | — | no | GBrain skillpack harvest manifest/CLI wrapper is internal packaging utility. |
| [#1899](https://github.com/gaia-research/gaia-skill-tree/issues/1899) | [`garrytan/smoke-test`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/smoke-test/SKILL.md) | omitted | — | — | no | GBrain/OpenClaw service health script wrapper and machine repair are product-local maintenance. |
| [#1900](https://github.com/gaia-research/gaia-skill-tree/issues/1900) | [`garrytan/soul-audit`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/soul-audit/SKILL.md) | mapped | agent-environment-setup | — | no | Identity interview and bootstrap file rendering are GBrain-specific setup variation. |
| [#1901](https://github.com/gaia-research/gaia-skill-tree/issues/1901) | [`garrytan/strategic-reading`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/strategic-reading/SKILL.md) | accepted | document-analyst | 2 | no | Lane 02B: reads one supplied text against a specified decision and produces a section-by-section applied playbook; document analysis is primary, not multi-source research. Distinct source-to-problem protocol despite GBrain output adapter; 2★. |
| [#1902](https://github.com/gaia-research/gaia-skill-tree/issues/1902) | [`garrytan/testing`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/skills/testing/SKILL.md) | mapped | automated-testing | — | no | Generic skill-conformance/project test-suite checking exists; GBrain test command wrapper adds no distinct portable implementation. |
| [#1903](https://github.com/gaia-research/gaia-skill-tree/issues/1903) | [`garrytan/two-tier-extraction`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/two-tier-extraction/SKILL.md) | accepted | knowledge-harvest | 2 | no | Lane 02B: privacy wall → cheap triage → gated deep read → durable source-page write is a reusable corpus harvesting pipeline; classification alone is just its gate. No new fusion topology; privacy wall must remain fail-closed. 2★. |
| [#1904](https://github.com/gaia-research/gaia-skill-tree/issues/1904) | [`garrytan/voice-note-ingest`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/voice-note-ingest/SKILL.md) | mapped | garrytan/capture; personal-knowledge-management | — | no | Lane 02B changed accepted → mapped: this files already-transcribed notes verbatim with contextual analysis under GBrain's brain paths; no audio recognition is performed. Existing same-author capture represents the PKM behavior without a duplicate named skill. |
| [#1905](https://github.com/gaia-research/gaia-skill-tree/issues/1905) | [`garrytan/webhook-transforms`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/webhook-transforms/SKILL.md) | omitted | — | — | no | Short GBrain-specific webhook-to-brain transform wiring lacks distinct portable substance. |
| [#1913](https://github.com/gaia-research/gaia-skill-tree/issues/1913) | [`garrytan/remote-mcp`](https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md) | deferred | mcp-server-creation / mcp-integration (neither fits server exposure) | — | no | Lane 02B changed accepted → deferred: Tailscale Serve/Funnel, per-client scoped grants, and client round-trip deploy an EXISTING GBrain MCP server; they neither build a new server nor merely consume one. Maintainer must decide if remote MCP hosting deserves its own generic or remains within GBrain suite, and verify public-Funnel auth/threat model before any named intake. |

### Lane 02B final counts

| Disposition / gate | Count |
|---|---:|
| accepted | 30 |
| mapped | 39 |
| deferred | 10 |
| omitted | 16 |
| ESCALATE (cross-cutting flag) | 0 |

Lane 02B changed **12 of the 31** escalated disposition proposals: #1556, #1558, #1564, #1910, #1841, #1846, #1848, #1871, #1887, #1893, #1904, and #1913. **No non-escalated row changed.** Maintainer decisions still needed for deferred generic ownership (#1556, #1558, #1564, #1913), privacy/retention/portability (#1841, #1852, #1887, #1892, #1893), and the `garrytan/skillify` canonical ID collision (#1896). Final dispositions do not authorize new generics, fusion/suite changes, or Lane 03 registry implementation.

The release-pinned source URLs are attribution/source pointers, not independent scoring evidence. A final reviewer must verify installability, canonical upstream authorship and current link liveness again before CLI ingestion; 3★+ requires a verified blob and 4★+ requires live evidence plus TM gate. The implementation checklist above remains open and requires separate approval.
