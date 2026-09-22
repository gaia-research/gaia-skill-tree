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
