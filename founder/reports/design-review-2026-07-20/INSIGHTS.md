# Yggdrasil II UI Polish Analysis

## The Connection: Marooned Commits are the Missing "Taxonomy" UI Layer
Many of the items in the `CHECKLIST.md` (especially the Ship Blockers and Overhaul items) stem from one core architectural shift in Yggdrasil II: the transition from the old hard-coded `type` enum to the new dynamic `branch` taxonomy (e.g., distinguishing between Suite vs Unique). 

The staging branch clearly has the new data structure from the Python/backend, but its UI is still trying to perform "dead reads" against the old system. The marooned commits represent the exact UI polish layer needed to bridge that gap. 

For example:
- **Ship Blocker 4 (SB4) & Overhaul 5 (O5)**: The checklist flags that the `/named/` catalog incorrectly groups everything using the hard-wired `SUITE_LADDER` (e.g., calling a Unique skill "Extra"). It was marked as "DEFERRED". However, marooned commit **`ecd4f7186`** (`named grid group header/segregation reads emitted branch, not hard-wired suite ladder`) was specifically written to fix this. 
- **Graph and Type reads**: The checklist mentions issues with dead-token reads (like "0 ultimates" or node coloring). Marooned commits like **`8aa300702`** (`DAG node dot color reads emitted branch, not dead type enum`), **`c0def6d62`** (`derive branch at read-time in 3D graph`), and **`3555c40da`** (`homepage '0 ultimates' dead-type read`) are explicitly designed to fix these UI-layer data consumption bugs.
- **Rank Vocabulary**: The checklist mentions updating token aliases and naming. Marooned commits **`1006e5d75`** and **`332736ab0`** systematically kill the old "Hardened/Transcendent" vocabulary on the badges pages.

## What Likely Happened (Verified from PR Comments)
The Yggdrasil II update was massive and split across multiple branches. The core backend/taxonomy update was merged in **PR #1235** (`dev/ygg2-consume-frontend`) on 2026-07-18. 

During that PR, Marco explicitly commented that the design fixes (like the plaque rebalance and graph gold-star mark) were **"Deferred (design cherry-pick, not oracle)"** to keep the PR focused on backend logic.

However, over on **PR #1227** (`design/ygg2-fixforward-superadmin`), which actually contained all the D1-D18 design fixes, Marco closed the PR without merging it. His closing comment reveals the critical disconnect: 
> *"Closing as superseded... the deferred design items (D6/D8 plaque avatar→medallion order, D3/D18 gold-★ graph mark...) landed on the #1235 stack... No work is lost — see #1235 for the folded design fixes."*

**The resulting state:** Marco deferred them in PR 1235, but then closed PR 1227 because he thought they *had already landed* in PR 1235. The commits were completely orphaned in the crossfire.

## Proposed Remediation Strategy
1. **Merge the "Deferred Polish" Branch:** Because PR 1227 was noted as "stale against the oracle cut," a blind merge of `ygg2-fixforward-superadmin` might cause conflicts. However, `origin/design/ygg2-deferred-polish` appears to be the freshly "re-cut" branch intended for exactly this phase. We should attempt a direct merge of `origin/design/ygg2-deferred-polish`.
2. **Execute the O1 Token Migration:** Manually execute the O1 migration (extra → fusion, ultimate → 5★-suite gold) if not fully covered by the branches.
3. **Regenerate Artifacts:** Run `gaia dev docs` / the content-engine scripts to ensure the HTML surfaces fully ingest the merged logic. 
4. **Re-Verify the Checklist:** After applying the marooned batch, we would strike out SB4, the graph rendering issues, and the badge vocabulary issues, leaving only true functional blockers.

## Expected Impact of Merging the "Deferred Polish" Branch

### Likely Remediated Right Away (For Skim Review)
Merging the marooned branches will directly hit the new taxonomy UI strategy—forcing the frontend to read dynamic `branch` data instead of legacy `type` enums.
- **SB4 (and O5) — `/named/` catalog grouping:** Addressed by `ecd4f7186`. It explicitly wires the named grid group headers to read the emitted branch rather than the hard-wired suite ladder, fulfilling the taxonomy strategy.
- **P14 & 3D Explorer Graph issues:** Addressed by `8aa300702` (node dot colors) and `c0def6d62` (deriving branch at read-time in the 3D graph). These ensure the graph respects the true suite/unique distributions.
- **D74 — Homepage "0 ultimates" bug:** Addressed by `3555c40da`, which corrects the dead-type reading on the homepage hero.
- **Badge rank vocabulary issues (P7, P8 context):** Addressed by `1006e5d75` and `332736ab0`. These kill the legacy "Hardened/Transcendent" rank words, aligning the UI with the final taxonomy.
- **D15 — Reports navigation polish:** Addressed by `55a62ac13`, which greys out '← Previous week' gracefully when no prior report exists.

### Likely NOT Affected (Requires New Work)
These items represent genuine structural HTML/CSS rebuilds or isolated bugs that are not covered by the `D1-D18` or `fix(ygg2)` taxonomy commits.
- **SB1 (O2) — Skill Explorer Mobile Reflow:** There is no commit in the batch addressing the responsive single-column layout rebuild for the overlay. This requires actual new UI structural work.
- **SB2 — `/reports/2026-28/` Pinning Old `site-nav.js`:** This is a Jinja template generator issue pinning `?v=6.0.1`. The marooned commits don't appear to touch the build-time HTML cache-busting pipeline.
- **P18, SB3, P9 (O1 Token Migration):** While Marco merged a partial fix in PR 1235 (13 instances), the CHECKLIST notes there are still ~90 dead consumers of `--tier-ultimate` and `--tier-extra`. Since the 6★ Apex is still reading cyan (P18), a dedicated CSS sweep is still required to map these to fusion/gold.
- **P1 — Site Nav Rainbow Colors:** An isolated CSS reserved-color rule bug not covered by the taxonomy/graph UI fixes.
- **P3 — 1★ Cards `@[anonymous]` fallback:** Rendering the raw placeholder instead of the empty state. This requires a targeted JS string template fix.
- **Mechanical layout bugs (P4, P5, P6, P10, P11, P12, P13, P15, P16, P17, P19, P20):** These are overlapping fixed headers, missing nav mounts, and overflow bugs. They are standard CSS/layout defect fixes that need manual attention beyond the scope of the taxonomy alignment.
