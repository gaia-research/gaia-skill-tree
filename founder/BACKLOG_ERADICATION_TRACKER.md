# Backlog Eradication Tracker — Post-#1185 Clean-State Plan

> **⚠️ STATUS — PR #1185 is still OPEN (draft) as of generation.** This tracker **activates once PR #1185 (v7.0.0, Yggdrasil II staging → main) merges.** Nothing here has been executed: **no issues have been closed, tagged, commented, or relabeled.** Every "close", "fold", and "tag" below is a **drafted action awaiting the merge + founder approval** (per `founder/CLAUDE.md`: all GitHub writes are drafted first, executed only after Marco approves). Where the triage prose reads as if #1185 already landed, treat it as **conditional**: "resolved by #1185" means "expected to be resolved once #1185 merges — verify before closing."
>
> **Single authoritative tracker.** This document drives the founder's one-by-one, ambitious staging of the entire open-issue backlog to a clean state.
>
> **Generated:** 2026-07-21 · **Source:** `gaia-backlog-triage` workflow (7 Haiku triage agents → 1 Opus synthesis; cached/resumable — see footer) · **Scope:** 97 triaged open issues (98 open minus EPIC #1002 itself).

---

## Executive Summary

> **Revised 2026-07-21 per founder review.** CLI polish promoted to the queue (CLI is a known weak link). Infra refactors brushed early before destructive work; MCP extraction promoted (adjacent `gaia-mcp` repo now exists with new plans). Frontend: plaque flicker (#346) + pet-companion shell (#1183) confirmed done → close; remaining pet work is the chat boxes (#1184, assets ready) → staged. TM chart (#1194) possibly done in EPIC → verify+close. Evidence-lake repartition (#1148) pulled **ahead of the intake batch**. Curation candidate #752 → intake. Dependency-blocked issues grouped for a **future EPIC umbrella** created with `GAIA_ROADMAP_v5` after this sprint.

| Metric | Count |
|---|---|
| **Total open issues (triaged)** | **97** |
| Close — resolved by #1185 (verify, then close) | **10** |
| Close — founder-confirmed done (verify, then close) | **3** |
| EPIC 1002 (Yggdrasil II) — related total | **22** |
| — of which fold-into-1002 (close/relabel, do NOT stage) | **17** |
| — of which stay independent (staged/deferred) | **5** |
| **Stage-as-PR** (7 intake + 28 other; CLI/infra/MCP/pet/data promoted) | **35** |
| Future-EPIC umbrella (dependency-blocked; absorbed by roadmap-v5 EPIC) | **4** |
| Needs founder decision | **11** |
| Merge into another issue (#455 → #1183) | **1** |
| Backlog-defer (parked this pass) | **16** |

**Bucket math check:** 10 close-#1185 + 3 close-founder + 17 fold + 1 merge + 11 decision + 35 stage + 4 future-EPIC + 16 defer = **97** ✔

### Priorities (fixed)

- **PRIORITY 1 — EPIC #1002 (Yggdrasil II):** founder's separate top priority. **OUT OF SCOPE for this document's active plan.** Section 2 only *catalogs* the tied issues and flags which need an epic/schema tag applied.
- **PRIORITY 2 — INTAKE issues:** their own top staging section (Section 4). **Note:** evidence-lake repartition (#1148) is staged **before** the intake batch per founder call.
- **PRIORITY 3 — everything else:** ordered P0→P3 then effort, grouped by theme (Section 5). CLI polish elevated.

### Recommended Order of Attack

1. **Close — #1185-resolved (10) + founder-confirmed (3)** — Sections 3 & 3b. Zero-cost backlog shrink after verify; do first. Backlog: 97 → 84.
2. **Fold into EPIC 1002 (17)** — Section 6. Close/relabel as 1002 sub-work; apply `epic-1002` tag where flagged. 84 → 67 independent.
3. **Merge #455 → #1183 (1)** — Section 7. 67 → 66.
4. **Brush infra early (#1060, #1191)** — Section 5, *before* destructive/schema-churning work. MCP extraction (#1191) coordinates with the new `gaia-mcp` repo.
5. **Data repartition #1148 → THEN intake (7)** — Sections 5 & 4. #1148 PR lands before the intake batch.
6. **Priority 3 stage-as-PR incl. CLI polish (28)** — Section 5, queue order. Security #1147 (P0) heads the queue.
7. **Needs-decision (11)** — Section 8. Founder call before any enters the queue.
8. **Future-EPIC umbrella (4)** — Section 8b. NOT worked now; surfaced so you know which issues the roadmap-v5 EPIC will "eat" in one line.
9. **Backlog-defer (16)** — Section 9. Parked with rationale; revisit next cycle.

---

## Section 1 — ORDERED STAGING QUEUE (the checklist)

Stage each row **one-by-one, ambitiously**, top to bottom. This queue is the union of Priority-2 intake and Priority-3 stage-as-PR issues, ordered **P0 → P1 → P2 → P3, then by effort (XS→S→M→L)**. Intake P0/P1 are interleaved by priority since Priority 2 outranks Priority-3 non-intake at equal priority.

Legend: **Eff** = effort (XS/S/M/L/XL). **Br** = suggested branch prefix.

| # | Issue | Title | Prio | Eff | Category | Recommended action | Br | Definition of done (one-line) |
|---|---|---|---|---|---|---|---|---|
| 1 | #1147 | [security] Fix DOM-XSS / innerHTML in static pages | P0 | S | bug/security | stage-as-PR | `infra/` | CodeQL-flagged lines sanitized (DOMPurify/safe alt); re-check passes. |
| 2 | #1191 | Extract Gaia MCP into standalone `gaia-mcp` | P1 | L | infra | stage-as-PR (**brush early**) | `infra/` | Coordinate w/ existing `gaia-research/gaia-mcp`; parity reached; monorepo copy retired. |
| 3 | #1060 | Prune node_modules + bloated binaries from git history | P1 | L | infra | stage-as-PR (**brush early, before destructive schema work**) | `infra/` | History rewritten; fetch payload reduced; verified clean. Sequence w/ #1185 purge. |
| 4 | #1201 | Live graph JSON `$schema` points to dead 404 path | P1 | S | bug | stage-as-PR | `schema/` | `$schema` pointer resolves to correct registry schema URL. |
| 5 | #991 | infra: permit `founder/handovers/**` on design/* branches | P1 | XS | infra | stage-as-PR | `infra/` | branch-scope guard allows vendor handovers on design branches. |
| 6 | #727 | infra: widen schema/ scope to bundled mirror | P1 | S | infra | stage-as-PR | `infra/` | schema/ branches may update `src/gaia_cli/data/registry/schema/`. |
| 7 | #1202 | Schema↔feed↔source field-set mismatch (invalid gaia.json) | P1 | M | bug | stage-as-PR | `schema/` | gaia.json validates against skill.schema.json; feed/source field-sets in sync. |
| 8 | #139 | `gaia graph` only shows legendary skills locally | P1 | M | cli | stage-as-PR | `cli/` | `gaia graph` renders full local tree; fusions linked; pushable skills highlighted. |
| 9 | #1148 | Partition evidence lake by type, not rank tier | P1 | L | data | stage-as-PR (**BEFORE intake batch**) | `review/meta/` | Evidence lake repartitioned by evidence type; audit paths updated; **lands before intake**. |
| 10 | #1243 | [intake] disler/fusion-harness (4 skills) | P0 | M | intake | stage-as-PR | none | 4 skills added via `gaia dev add`; disler named impls registered; evidence verified in gaia.json. |
| 11 | #1123 | [intake] gaia-research/skill-cost (token-observability) | P0 | S | intake | stage-as-PR | none | Named skill registered; token-observability promoted provisional→active; docs regenerated. |
| 12 | #1137 | [intake] single: ponytail (DietrichGebert) | P1 | S | intake | stage-as-PR | none | Named skill linked to `context-compression`; evidence row added; docs regenerated. |
| 13 | #1117 | [intake] daily-patterns-pack (2 generics) | P1 | M | intake | stage-as-PR | none | Both skills added; aplaceforallmystuff impls registered; fusion dep verified; docs regenerated. |
| 14 | #752 | [intake] firecrawl skills as 4/5★ suite candidate | P2 | M | intake | stage-as-PR | `review/meta/` | Evidence collected for firecrawl suite; components graded; suite candidacy resolved. |
| 15 | #1244 | [RFC] gaia-curate: named-first intake path | P1 | M | intake | stage-as-PR | `design/` | RFC ratified; /gaia-curate flow inverted to named-first, derive generic on demand. |
| 16 | #977 | Propose generic: prompt caching / KV-cache reuse | P1 | M | curation | stage-as-PR | `review/meta/` | Generic node created; Anthropic/OpenAI/benchmark evidence; floor met. |
| 17 | #978 | Propose generic: agent checkpoint & resume | P1 | M | curation | stage-as-PR | `review/meta/` | Generic node created; LangGraph/LangChain evidence; floor met. |
| 18 | #1184 | Context-aware chat boxes for Milim & Gaia companion | P2 | S | frontend | stage-as-PR | `design/` | Companion shell done (#1183); add contextual chat boxes — **assets ready**; per-page guidance renders. |
| 19 | #1028 | Extract scripts/lib into shared installable package | P2 | M | cli | stage-as-PR | `cli/` | `packages/gaia-registry-lib` created; scripts/lib + src/gaia_cli import from it; dup eliminated. |
| 20 | #1154 | cli: add `gaia dev rename-named <old> <new>` | P2 | M | cli | stage-as-PR | `cli/` | Command works end-to-end with file moves + id-field updates. |
| 21 | #1158 | cli: `gaia scan` for nonstandard SKILL.md layouts | P2 | M | cli | stage-as-PR | `cli/` | scan auto-discovers SKILL.md from arbitrary repo-native folders; tests added. |
| 22 | #332 | [CLI] Centralize design system + formatting tokens | P3 | M | cli | stage-as-PR | `cli/` | `src/gaia_cli/theme.py` created; all renderers import from it; no duplication. |
| 23 | #1004 | Update surfaces to point to skill-fuse repo | P2 | S | docs | stage-as-PR | `docs/` | skill-fuse registered; docs/README updated. |
| 24 | #741 | Firecrawl skill evidence: verified benchmark | P2 | S | evidence | stage-as-PR | `review/meta/` | firecrawl-research-index added; arXivQA/MRR benchmark attached; floor met. |
| 25 | #1124 | Add root AGENTS.md for agent-discovery of intake | P2 | S | docs | stage-as-PR | `docs/` | AGENTS.md created + linked from README; covers intake/submission/roles. |
| 26 | #982 | Propose generic: diff-based file editing | P2 | M | curation | stage-as-PR | `review/meta/` | Generic node created; Aider/Claude Code/structured-edit evidence; floor met. |
| 27 | #981 | Propose generic: context-window compaction | P2 | M | curation | stage-as-PR | `review/meta/` | Generic node created; Claude Code/Cursor/Aider evidence; floor met. |
| 28 | #980 | Propose generic: cost attribution / spend accounting | P2 | M | curation | stage-as-PR | `review/meta/` | Generic node created; Helicone/Langfuse/OpenRouter evidence; floor met. |
| 29 | #979 | Propose generic: rate-limit backoff & retry | P2 | M | curation | stage-as-PR | `review/meta/` | Generic node created; backoff-lib/production-pattern evidence; floor met. |
| 30 | #923 | Evidence request: Addy Osmani seven-skill suite | P2 | M | evidence | stage-as-PR | `review/meta/` | Independent evidence for each of 7 components; floor met. |
| 31 | #922 | Evidence request: independent signals for GSD suite | P2 | M | evidence | stage-as-PR | `review/meta/` | Independent peer-review/attestation for suite + 5 components; TM bumped. |
| 32 | #868 | feat(leaderboard): Trust Leaderboard SVG redesign | P2 | M | frontend | stage-as-PR | `design/` | SVG chart + dark CSS + animation/tooltip; #863 dependency confirmed merged. |
| 33 | #636 | Include Xcode skills/rules when scanning in CLI | P3 | S | cli | stage-as-PR | `cli/` | `.xcode/rules` + `.xcode/skills` added to scanner search dirs; tests added. |
| 34 | #118 | Promotion title issues (truncation, rename prompt) | P3 | S | cli | stage-as-PR | `cli/` | Promotion card no truncation; rename prompt shows slash-name; redundancy audited. |
| 35 | #813 | Curation batch: 21 new AI agent skills | P2 | L | curation | stage-as-PR (`/gaia-curate-chain`) | `review/meta/` | Batch run through curate-chain; qualifying skills landed; rest triaged out. |

**Queue depth: 35.** **Brush-early infra** (rows 2–3: #1191 MCP extraction, #1060 history prune) runs *before* destructive/schema-churning work. **#1148 (row 9) lands before the intake batch** (rows 10–15) per founder call. Intake items: rows 10–15 (#1243, #1123, #1137, #1117, #752, #1244). **CLI polish elevated:** #139, #1028, #1154, #1158, #332, #636, #118 (CLI is a known weak link). Row 1 (#1147, P0 security) heads the queue.

---

## Section 2 — EPIC 1002 (Yggdrasil II) — Catalog Only, NOT Staged Here

> **PRIORITY 1. Do NOT schedule this work in the active plan.** This section exists solely to inventory every issue within or tied to EPIC #1002 and flag tagging gaps. All 22 `epic1002Related` issues appear here. The 17 marked *fold* are also close/relabel targets (Section 6); the remaining 5 live in the queue or defer list as noted.

### (a) Already tagged epic/schema — no tag action needed

These are Yggdrasil II core deliverables already resolved by #1185 or explicitly closed on the clean-state pass:

| Issue | Title | Disposition |
|---|---|---|
| #994 | Docs ratification (META, trust-methodology, DESIGN, CONTEXT) | Close (Section 3) |
| #997 | Migration script `migrate_taxonomy_v6.py` | Close (Section 3) |
| #998 | Frontend readers / Ascension copy / badges | Close (Section 3) |
| #999 | CI guards (banned-synonym, meta-sync, timeline pairing) | Close (Section 3) |
| #1000 | Agent-skill prompt refresh for new taxonomy | Close (Section 3) |
| #1174 | CLI auto-derive `type`; deprecate `gaia dev reclassify` | Close (Section 3) |
| #1189 | Structured migration provenance (metaEpoch/migrationBatch) | Close (Section 3) |
| #1001 | TM Index Q3 — branch-aware TM formula rebuild | Backlog-defer (unblocked by #1185; scheduled under 1002 follow-through) |
| #1103 | RFC: Fusion → Workflows/Plugins grading | Fold-into-1002 (Section 6) |

### (b) NEEDS an epic/schema tag applied — `suggestTagEpic1002` set

Apply the `epic-1002` (and/or `schema`) label to each of these 13 before/at fold time so the epic's true scope is visible. **None are staged independently** — all fold into 1002 (Section 6).

| Issue | Title | Tag to apply |
|---|---|---|
| #1220 | Obsolete type checks 'extra'/'ultimate' in combinator.py | `epic-1002` |
| #1221 | Obsolete type check in pathEngine.py | `epic-1002` |
| #1222 | Obsolete type checks/ordering in stats.py | `epic-1002` |
| #1223 | validate.py cross-validates real named skills on mock graphs | `epic-1002` |
| #1224 | Obsolete assertions in test_validate/test_promotion/test_graph | `epic-1002` |
| #1225 | CLI Alignment to Ygg II Meta Schema (umbrella, #1220–#1224) | `epic-1002` |
| #1228 | Two divergent branch resolvers (strict TM vs topological) | `epic-1002` |
| #1229 | Class S projection omits suiteComponents on fusions | `epic-1002` |
| #1230 | Dead type-enum reads/writes persist in shared scripts + CLI | `epic-1002` |
| #1231 | Taxonomy logic triplicated across client/projection/CLI | `epic-1002` |
| #975 | Ascension Cycle overdrive redesign (new rank taxonomy) | `epic-1002` |
| #746 | Apex gate: depth2/tenure/A-origins not curated for S-grade | `epic-1002` |
| #601 | CLI support for removing/demoting a skill from user trees | `epic-1002` |

---

## Section 3 — CLOSE ON CLEAN-STATE PASS (10) — fastest wins first

> **Deferred per founder decision ("run now, defer closes").** Do NOT close these yet — #1185 is still open. **After #1185 merges, verify each is actually resolved on `main`, then close** in one pass. Draft close comment for each: _"Resolved by #1185 (v7.0.0). Closed on the backlog clean-state pass — see `founder/BACKLOG_ERADICATION_TRACKER.md`."_ Backlog 97 → 87 once done.

| Issue | Title | Close reason |
|---|---|---|
| #994 | Ygg II · Docs ratification | #1185 landed all canonical docs ratification (CONTEXT/META/trust-methodology/DESIGN). 100% resolved. |
| #997 | Ygg II · Migration script | Merged in #1185; migration executed, all named skills re-evaluated with timeline provenance. |
| #998 | Ygg II · Frontend readers/badges | PR #1227 (design reset) landed all frontend fixes; merged in #1185. |
| #999 | Ygg II · CI guards | Timeline pairing replaced by #1189 schema; banned-synonym guards deployed; cohesion checks green. |
| #1000 | Ygg II · Agent-skill prompts | Prompt copies updated to new taxonomy; mirrored in `.claude/` + `.agents/`; landed in #1185. |
| #1174 | Ygg II · CLI auto-derive type | Shipped v7.0.0; type is structural; `gaia dev reclassify` deprecated/removed. |
| #1189 | Ygg II · Structured migration provenance | Schema updated in #1185; metaEpoch/migrationBatch added; timeline invariant codified. |
| #1152 | Document `gaia dev fuse` timeline + repair | #1185 includes migration #997 + fuse timeline repair; documentation work landed with it. |
| #1130 | Discuss disabling Weekly Report + Benchmarks Leaderboard | Temporary disable already shipped in main; re-enable deferred post-EPIC-1002. |
| #917 | docs: drop deprecated Evidence Classes from skill-hierarchy.html | Cleanup of stale A/B/C references superseded by Ygg II schema; resolved on clean-state pass. |

---

## Section 3b — CLOSE: FOUNDER-CONFIRMED DONE (3) — verify, then close

> **Founder-confirmed complete 2026-07-21** (not tracked in issue comments — knowledge from Marco directly). Verify on the live surface, then close. These are NOT tied to #1185.

| Issue | Title | Close reason (founder-confirmed) |
|---|---|---|
| #346 | Named Skills Explorer plaque flicker | **Done** — plaque flicker/z-index fixed. Verify at `gaiaskilltree.com/named/` hover, then close. |
| #1183 | Draggable Milim & Gaia companion (shell) | **Done** — companion shell ships (draggable/minimizable). Remaining chat-box work split to #1184 (staged, queue row 18). Close #1183 once shell verified. |
| #1194 | Trust Magnitude timeline (TM-over-time chart) | **Possibly done in EPIC** — verify the TM-over-time chart renders on profile pages; if present, close; if not, move to queue. |

---

## Section 4 — PRIORITY 2: INTAKE (6) — top staging section

Well-formed, high-value adds. Ship the P0s first. **#1148 (evidence-lake repartition) lands as a PR BEFORE this batch** per founder call — see queue row 9. All intake items also appear in the numbered queue (Section 1) at the row shown.

| Queue row | Issue | Title | Prio | Eff | Definition of done |
|---|---|---|---|---|---|
| 10 | #1243 | disler/fusion-harness — 4 skills (opinion + 3 fusions) | P0 | M | All 4 added via `gaia dev add`; disler named impls registered; evidence verified HTTP-200 in gaia.json post-regen. |
| 11 | #1123 | gaia-research/skill-cost — token-observability | P0 | S | Named skill registered; evidence rows added; generic promoted provisional→active; docs regenerated. |
| 12 | #1137 | single: ponytail (DietrichGebert) | P1 | S | Named impl linked to `context-compression`; Grade-B evidence row; docs regenerated. |
| 13 | #1117 | daily-patterns-pack — session-journaling + work-pattern-mining | P1 | M | Both added; aplaceforallmystuff impls registered; fusion dep verified in graph; docs regenerated. |
| 14 | #752 | firecrawl skills as 4/5★ suite candidate | P2 | M | Evidence collected for firecrawl suite; components graded; suite candidacy resolved. |
| 15 | #1244 | [RFC] gaia-curate named-first intake path | P1 | M | RFC ratified; /gaia-curate inverted to named-first, derive/link generic on demand. |

---

## Section 5 — STAGED WORK — by theme

The 35 stage-as-PR issues, grouped by theme. Master queue ordering (Section 1) is P0→P3 then effort, with **brush-early infra** and **#1148-before-intake** overrides; here they are themed for reviewer context.

### Security / Bug (P0–P1)
- **#1147** (P0, S, `infra/`) — DOM-XSS sanitization; **queue row 1**, blocks release confidence.
- **#1201** (P1, S, `schema/`) — fix dead `$schema` 404 pointer; queue row 4.
- **#1202** (P1, M, `schema/`) — reconcile schema↔feed↔source field-set mismatch; queue row 7.

### Infra — brush EARLY, before destructive work (P1)
- **#1191** (L, `infra/`) — **extract Gaia MCP → standalone `gaia-mcp`**; adjacent repo now exists w/ new plans; queue row 2.
- **#1060** (L, `infra/`) — prune node_modules/binaries from git history; sequence with #1185's PNG purge; queue row 3.
- **#991** (XS, `infra/`) — permit `founder/handovers/**` on design branches; queue row 5.
- **#727** (S, `infra/`) — widen schema/ scope to bundled mirror; queue row 6.

### CLI polish — elevated (weak-link investment) (P1–P3)
- **#139** (P1, M) `gaia graph` full local tree; queue row 8.
- **#1028** (P2, M) extract scripts/lib → shared package · **#1154** (P2, M) `gaia dev rename-named` · **#1158** (P2, M) scan nonstandard SKILL.md — queue rows 19–21.
- **#332** (P3, M) centralize design/formatting tokens (`theme.py`) · **#636** (P3, S) Xcode skill scanning · **#118** (P3, S) promotion title fixes — queue rows 22, 33–34.

### Data (P1) — lands BEFORE intake
- **#1148** (L, `review/meta/`) — partition evidence lake by type not rank; **queue row 9, before the intake batch**.

### Curation — new generics (P1–P2)
- **#977** (P1, M) prompt caching · **#978** (P1, M) checkpoint & resume — queue rows 16–17.
- **#982** (P2, M) diff-based editing · **#981** (P2, M) context-window compaction · **#980** (P2, M) cost attribution · **#979** (P2, M) rate-limit backoff — queue rows 26–29.

### Curation — batch intake (P2)
- **#813** (L, `review/meta/`) — 21-skill batch via `/gaia-curate-chain`; queue row 35.

### Evidence (P2)
- **#741** (S) firecrawl benchmark · **#923** (M) Addy Osmani suite · **#922** (M) GSD suite — queue rows 24, 30, 31.

### Docs (P2)
- **#1124** (S) root AGENTS.md · **#1004** (S) skill-fuse repo surfaces — queue rows 25, 23.

### Frontend (P2)
- **#1184** (S, `design/`) — **context-aware chat boxes** for the Milim & Gaia companion; shell (#1183) done, **assets ready**; queue row 18.
- **#868** (M, `design/`) Trust Leaderboard SVG redesign — queue row 32 (confirm #863 merged first).

> **Intake (Priority 2)** items (#1243, #1123, #1137, #1117, #752, #1244) are detailed in Section 4; they occupy queue rows 10–15.


---

## Section 6 — FOLD INTO EPIC 1002 (17) — close/relabel as sub-work, do NOT stage independently

These belong under EPIC #1002 and must not enter the active queue. Close or relabel each as 1002 sub-work; apply `epic-1002` tag (all except #925 carry `suggestTagEpic1002`; #925 and #757/#762 fold on scope grounds).

| Issue | Title | Eff | Fold rationale |
|---|---|---|---|
| #1225 | CLI Alignment to Ygg II schema (umbrella) | L | Aggregates #1220–#1224; becomes the 1002 CLI-alignment epic child. |
| #1220 | Obsolete type checks in combinator.py | S | Dead 'extra'/'ultimate' reads post-#997; 1002 cleanup. |
| #1221 | Obsolete type check in pathEngine.py | S | Blocks near/one-away unlock; 1002 cleanup. |
| #1222 | Obsolete type checks/ordering in stats.py | S | TYPE_LABELS/ORDER lack fusion support; 1002 cleanup. |
| #1223 | validate.py reads real named on mock graphs | M | `--graph-only` flag; 1002 test-infra. |
| #1224 | Obsolete assertions in test suite | M | Pre-Ygg II assertions fail post-migration; 1002 test fix. |
| #1228 | Two divergent branch resolvers | M | Root of homepage overshoot; 1002 resolver unification. |
| #1229 | Class S projection omits suiteComponents | M | D74 (0 ultimates) root cause; partially fixed in #1227; finish under 1002. |
| #1230 | Dead type-enum reads/writes in scripts + CLI | M | Silent empty results post-#997; 1002 cleanup. |
| #1231 | Taxonomy logic triplicated (client/projection/CLI) | L | Single-source-of-truth extraction; umbrella for #1228–#1230; 1002. |
| #975 | Ascension Cycle overdrive redesign | M | Frontend manifestation of Ygg II rank/type model. |
| #1103 | RFC: Fusion → Workflows/Plugins grading | M | Directly grades type=fusion vs components; 1002 scope; absorbs #526. |
| #746 | Apex gate depth2/tenure/A-origins not curated | L | Apex-gate predicates block S-grade; 1002 evidence-model follow-through. |
| #601 | CLI remove/demote skill from user trees | M | Known CLI gap (CLAUDE.md); needed for 1002 timeline integrity. |
| #925 | Sprint D: harden fusion-recipe TM scoring | L | Feeds 1002 branch-aware TM rebuild (#1001); ratification Q10. |
| #762 | Automate source curation (graduate /ev-pipeline) | L | Supports TM Index Q3 refresh (#1001); evidence automation for 1002. |
| #757 | ~71 ungraded named skills need evidence backfill | L | TM completeness required by 1002 branch-aware scoring. |

---

## Section 7 — MERGE INTO ANOTHER ISSUE (1)

| Issue | Title | Action |
|---|---|---|
| #455 | Github Badges (parent epic) | **Merge/close in favor of tracking under #1183** (companion / badge surface work). Vague scope; concrete sub-tasks #494/#495 now sit in the **future-EPIC umbrella** (Section 8b, roadmap-v5 badges track). Close #455, point to #1183 + the v5 badges track. |

---

## Section 8 — NEEDS DECISION (11) — founder call before staging

Triage these in one sitting; each is blocked on a scope/authority call and cannot enter the queue until resolved.

| Issue | Title | Prio | Eff | Decision required |
|---|---|---|---|---|
| #990 | infra(security): unverified worker commit authorship | P0 | M | Accept risk / require signed commits / change delegation model? |
| #1101 | RFC (umbrella): Evidence Model & Integrity | P1 | XL | Cherry-pick high-impact items vs full 2026-07 redesign; which sprint absorbs which. |
| #1104 | RFC (umbrella): Governance of the Canonical Graph | P1 | M | Ratify GOVERNANCE.md merge-authority/quorum/dispute rules. |
| #924 | Validate installability of archived GSD command-doc skills | P2 | M | Keep installable vs archive to evidence-only; v2 migration source. |
| #1178 | RFC: extract skill-trees/ to separate repo | P2 | M | Monorepo vs separate-repo strategy sign-off. |
| #874 | NEW ORGANIZATION (audit old links post org-move) | P2 | M | Define scope of post-org-move link audit. |
| #843 | 404 skill (devin-ai/autonomous-swe broken) | P2 | M | Demote to 0★ vs relink vs remove — data change needs approval. |
| #814 | reverse-skill (zhaoxuya520) curation | P2 | M | Accept/reject curation of the repo. |
| #1058 | Plan documentation for Gaia Discovery Call | P2 | S | Assign scope + owner. |
| #775 | Need better documentation | P3 | M | Define concrete scope from vague offer. |
| #1134 | RFC: SkillOpt integration into Gaia Skill Bench | P3 | XL | Research feasibility/priority; ratify or defer. |

---

## Section 8b — FUTURE-EPIC UMBRELLA (4) — to be "eaten" by the roadmap-v5 EPIC

> **Founder directive:** these dependency-blocked issues are NOT worked this pass. When **`GAIA_ROADMAP_v5`** is created (after this sprint), an **umbrella EPIC issue** absorbs all four in **one line** — they close as sub-work of that EPIC rather than individually. Surfaced here (not buried in defer) so you can see exactly which issues the v5 EPIC will consume.

| Issue | Title | Prio | Eff | Blocked by | Fate |
|---|---|---|---|---|---|
| #692 | [Crawler Rework] Document architecture + improvement plan | P2 | M | needs arch review | → roadmap-v5 EPIC (crawler track) |
| #684 | Infrastructure Simplification & CI Optimization | P2 | L | #692 | → roadmap-v5 EPIC (crawler track) |
| #494 | [badges] Server-rendered OAuth-bound badge endpoint | P2 | M | #155 (sign-in UI) | → roadmap-v5 EPIC (badges track) |
| #495 | [badges] Workers Analytics Engine + admin dashboard | P3 | L | #455/#494 direction | → roadmap-v5 EPIC (badges track) |

**Action when v5 lands:** file one EPIC issue (e.g. "EPIC · roadmap-v5 deferred-dependency sweep"), reference all four with `Resolves #692 #684 #494 #495`, then close them pointing at the EPIC.

---

## Section 9 — BACKLOG-DEFER (16) — parked this pass, revisit next cycle

Kept open with rationale; genuinely lower-priority or scope-undefined, and **not** dependency-blocked (those went to Section 8b). Grouped by theme.

**EPIC-1002 follow-through (1):** #1001 TM Index Q3 (unblocked by #1185; scheduled under the 1002 follow-through track, not staged independently).

**Good-first-issue / evergreen community (6):** #984 scavenger-hunt broken links · #983 claim a named skill · #845 write a SKILL.md · #848 improve a description · #847 add evidence (uses deprecated class names) · #844 add yourself / create tree. *(These are standing community calls — closing them defeats the purpose.)*

**Curation / parking (2):** #565 name-drafts for 7 starless skills (awaits naming meta) · #638 custom-skill scoping overlay (deferred per founder).

**RFC / architecture — undefined scope (2):** #1102 CLI local-first defaults & lite dist (umbrella) · #858 OKF Format (early-stage).

**Docs / research (2):** #952 docs/en user-facing vs dev-mode split (arch refactor) · #334 [codex] align prerequisites with inferred code relationships (low signal).

**Reports / bench / graph (3):** #973 per-report leaderboard rendering (Sprint F, 2026-10+) · #964 bootstrap gaia-skill-bench repo (post-1002) · #652 Skill Graph Evolution View (vague v2).

**Count check:** 1+6+2+2+2+3 = **16** ✔

---

## Section 10 — Full Accounting Ledger (every issue exactly once)

| Disposition | Count | Issues |
|---|---|---|
| Close — resolved by #1185 | 10 | 917, 994, 997, 998, 999, 1000, 1130, 1152, 1174, 1189 |
| Close — founder-confirmed done | 3 | 346, 1183, 1194 |
| Fold into EPIC 1002 | 17 | 601, 746, 757, 762, 925, 975, 1103, 1220, 1221, 1222, 1223, 1224, 1225, 1228, 1229, 1230, 1231 |
| Merge → #1183 | 1 | 455 |
| Needs decision | 11 | 775, 814, 843, 874, 924, 990, 1058, 1101, 1104, 1134, 1178 |
| Stage-as-PR (queue: 6 intake + 29 other) | 35 | 118, 139, 332, 636, 727, 741, 752, 813, 868, 922, 923, 977, 978, 979, 980, 981, 982, 991, 1004, 1028, 1060, 1117, 1123, 1124, 1137, 1147, 1148, 1154, 1158, 1184, 1191, 1201, 1202, 1243, 1244 |
| Future-EPIC umbrella (roadmap-v5) | 4 | 494, 495, 684, 692 |
| Backlog-defer | 16 | 334, 565, 638, 652, 844, 845, 847, 848, 858, 952, 964, 973, 983, 984, 1001, 1102 |
| **TOTAL** | **97** | — |

---

## Section 11 — Drafted GitHub Actions (execute post-merge, after approval)

> All commands below are **drafted, not run.** Per `founder/CLAUDE.md`, every GitHub write is executed only after Marco approves. Run them **after #1185 merges** and after a quick verify pass. The `epic-1002` label does not exist yet — create it first (or substitute the existing `epic` + `schema` labels).

**Step 0 — create the tag (once):**
```bash
gh label create epic-1002 --description "Yggdrasil II (EPIC #1002) scope" --color 5319e7 || true
```

**Step 1 — tag the 13 untagged EPIC-1002 issues** (`suggestTagEpic1002` set):
```bash
for n in 1220 1221 1222 1223 1224 1225 1228 1229 1230 1231 975 746 601; do
  gh issue edit "$n" --add-label epic-1002
done
```

**Step 2 — close the 10 #1185-resolved issues** (VERIFY each is resolved on `main` first):
```bash
for n in 917 994 997 998 999 1000 1130 1152 1174 1189; do
  gh issue close "$n" --comment "Resolved by #1185 (v7.0.0). Closed on the backlog clean-state pass — see founder/BACKLOG_ERADICATION_TRACKER.md."
done
```

**Step 2b — close the 3 founder-confirmed-done issues** (verify the live surface, then close):
```bash
# #346 plaque flicker (verify gaiaskilltree.com/named hover) · #1183 companion shell (chat boxes → #1184) · #1194 TM chart (verify profile pages)
for n in 346 1183 1194; do
  gh issue close "$n" --comment "Confirmed complete. Closed on the backlog clean-state pass — see founder/BACKLOG_ERADICATION_TRACKER.md §3b. (#1183: remaining chat-box work tracked in #1184.)"
done
```

**Step 3 — fold the 17 into EPIC 1002** (tag + comment; keep open as sub-work OR close with pointer per your call):
```bash
for n in 601 746 757 762 925 975 1103 1220 1221 1222 1223 1224 1225 1228 1229 1230 1231; do
  gh issue edit "$n" --add-label epic-1002
  gh issue comment "$n" --body "Folded into EPIC #1002 (Yggdrasil II) as in-scope sub-work — see founder/BACKLOG_ERADICATION_TRACKER.md §6. Not staged independently."
done
```

**Step 4 — merge #455 into #1183:**
```bash
gh issue comment 455 --body "Superseded — badge work now tracked under #1183 (companion/badge surfaces); sub-tasks #494/#495 moved to the roadmap-v5 future-EPIC umbrella. Closing per founder/BACKLOG_ERADICATION_TRACKER.md §7."
gh issue close 455
```

> **Staging queue (Section 1)** is worked one-by-one as PRs on the suggested branch prefixes; no bulk command — each row is its own PR with `Resolves #<n>` in the body (per `founder/GIT.md`).

---

## How to re-run this tracker

This tracker is generated by the **`gaia-backlog-triage`** workflow, which is **cached and resumable** — re-runs reuse per-issue triage from the batch cache and only re-triage changed/new issues.

- **Re-run cadence:** re-run **post-merge** (after PR #1185 lands, and after each subsequent backlog-moving merge) to refresh dispositions, close counts, and the staging queue.
- **What refreshes:** the executive-summary counts, the close list (issues newly resolved by merges), EPIC-1002 fold/tag membership, and the ordered queue re-sort (P0→P3 then effort).
- **Idempotency:** dispositions are deterministic from triage data; re-running does not reshuffle already-staged rows unless their priority/effort/close-eligibility changed.
- **Output path:** `founder/BACKLOG_ERADICATION_TRACKER.md` (this file, overwritten verbatim on each run).

### Exact re-run commands

The workflow script and batch data live under `generated-output/issue-tracker/` (gitignored):

1. **Refresh the issue snapshot** (re-pull open issues + rebuild batches):
   ```bash
   # from repo root — regenerates issues_full.jsonl + batches_slim.json
   gh issue list --state open --limit 500 --json number --jq '.[].number' | while read n; do \
     gh issue view "$n" --json number,title,labels,createdAt,updatedAt,body,comments \
     | jq -c '{number,title,labels:[.labels[].name],createdAt:.createdAt[0:10],updatedAt:.updatedAt[0:10],commentCount:(.comments|length),body:(.body//""|.[0:1600])}'; \
   done > generated-output/issue-tracker/issues_full.jsonl
   # then re-run the Python batcher block that emitted batches_slim.json
   ```

2. **Fresh run** (new triage): invoke the `gaia-backlog-triage` workflow with
   `scriptPath: generated-output/issue-tracker/triage-workflow.js` and
   `args: { file: "<abs>/batches_slim.json", batchNames: ["A_intake","B_yggII_scope","C_curation_evidence","D_frontend_design","E_rfc_roadmap","F_cli_techdebt","G_misc"] }`.

3. **Resume after an error/edit** (reuses cached per-agent triage): re-invoke with the same `scriptPath` + `args` plus `resumeFromRunId: "wf_7a5f0b10-609"` (the original run). Unchanged agents replay instantly from cache; only edited/new agents re-run.
