# Gaia Triage Tasks

This file tracks the status of open issues during the 2026-05-24 triage session.

| Issue | Title | Status | Notes |
| :--- | :--- | :--- | :--- |
| #411 | Refactor: Migrate skill-graph.js from innerHTML... | **Resolved** | Fix committed and draft PR #435 opened. |
| #356 | Remove deprecated `rarity` axis... | **Auditing** | Valid tech-debt: `rarity` is still a required field in `skill.schema.json` and present in all registry skills. |
| #347 | Add ML-based layouts for the skill graph... | Pending | RFC/Enhancement. |
| #346 | plaques in canon flowchart tree view... "flickering" | Pending | Visual bug. |
| #341 | (design) COLLECTION should stay "maximized"... | Pending | UX enhancement. |
| #338 | [CLI] Fix aggressive gaia push scanning... | **Closed** | Duplicate of #337; already fixed in `c55038a`. |
| #335 | [RFC/mcp] Unified Advisor Interface... | Pending | Architectural RFC. |
| #334 | [codex] Align Registry Prerequisites... | Pending | Codex enhancement. |
| #333 | [CLI] Decouple Heavyweight Dependencies... | Pending | CLI enhancement. |
| #332 | [CLI] Centralize Design System and Formatting... | Pending | CLI enhancement. |
| #321 | create mattpocock/skills suite... | **Done** | `mattpocock/skills` already exists as a capstone suite. |
| #316 | Discrepancy between gstack installation... | **Auditing** | Valid: gstack suite docs use `/connect-chrome`, but registry has `/open-gstack-browser`. |
| #254 | Docs: Clarify lifecycle of Unnamed vs. Named... | Pending | Documentation task. |
| #252 | ruvnet/flow-nexus-swarm to ruvnet/flow-nexus/swarm | **Auditing** | Valid: Renaming task pending. |
| #250 | /gaia-fuse skill inside your repo | Pending | Enhancement proposal. |
| #235 | design (Search skills in svg issues) | **Auditing** | Confirmed: SVG labels/titles only use `name`. Should include `id` (slash skill) for better searchability. |
| #213 | mcp: GITHUB_TOKEN not wired into .mcp.json... | **Stale/Reverted** | Audited; fix reverted per user request as it's an old issue. |
| #212 | mcp: identity resolution uses process.cwd()... | **Auditing** | Confirmed: `identity.ts` relies on `process.cwd()`, which can fail in MCP host environments. |
| #185 | Add Security Scanning for skills automatically | Pending | Long-term enhancement. |
| #174 | Meta audit: Level IV+ evidence hygiene follow-up | Pending | Registry audit. |
| #165 | DAG Similarity + Embedding Clustering | Pending | Enhancement. |
| #155 | NEW UI - sign in to github | Pending | CLI/UI feature. |
| #141 | Instructions for agent to "set this mcp up"... | Pending | Documentation. |
| #139 | gaia graph issue | **Auditing** | Confirmed bug: `gaia graph` only shows canonical graph, ignores local tree/scan. HTML labels limited to ultimates. |
| #131 | Fusion, not Promotion | **Partially Done** | `gaia fuse` command and plaque implemented; `gaia promote` still exists. |
| #128 | NEW gaia push / repo export workflow | Pending | Workflow enhancement. |
| #119 | Multiple skills of the same name with different ranks | **Auditing** | Valid bug: Duplicates with different ranks should be consolidated. |
| #118 | Promotion title issues | **Partially Done** | Card uses "Fusion" and `/skill-id`, but "Rename?" line is missing and card width is static. |
| #79 | RFC: governance model | Pending | Governance RFC. |
| #78 | RFC: skill conditions | Pending | Schema RFC. |
| #77 | RFC: skill aliases | Pending | Schema RFC. |
| #75 | RFC: skill versioning | Pending | Lifecycle RFC. |
| #74 | RFC: skill deprecation and retirement lifecycle | Pending | Lifecycle RFC. |
| #71 | Display all bucket variants in CLI... | **Partially Done** | CLI `gaia lookup` command exists, but docs UI changes and `role` tagging might be incomplete. |
| #70 | Named skill duplicates should join the bucket... | **Auditing** | Valid: 54 skills stuck in `awaitingClassification` and hidden from `gaia lookup`. |
| #69 | CLI: — show what it takes to unlock any skill | Pending | CLI feature. |
| #66 | Propose a skill you use that is missing... | **Stale?** | Many skills added recently; needs re-evaluation of coverage. |
| #64 | CLI: add `gaia browse` — interactive explorer | Pending | CLI feature. |
| #63 | Collect real-world evidence for atomic skills | **Active** | 211 evidence entries found; coverage is improving but many skills still at Level I. |
| #62 | Submit your personal skill tree | **Active** | Ongoing community task. |
| #61 | Name a skill you actually use — 53 slots open | **Stale** | Audit found 204 eligible skills, 92 unclaimed in buckets, 54 awaiting classification. Count is outdated. |
| #11 | Add missing fusion recipes | **Active** | Ongoing enhancement task. |
