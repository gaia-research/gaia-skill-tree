# PR #1235 Review — Load-Bearing Issue Checklist (2026-07-19)

Preview session over `dev/ygg2-consume-frontend` (Ygg II taxonomy-authority oracle cut). Marco eyeballed the live preview; 7 issues found. Scouts classified each **ORACLE** (deleted-derivation completeness gap — in-scope for #1235 by Sprint Completeness) vs **DESIGN** (defer to a design cherry-pick pass on approved #1227 work).

## FINAL STATE (2026-07-19) — 7 fixes landed on dev/ygg2-consume-frontend

| # | Fix | Commit | Verdict |
|---|---|---|---|
| 1 | Graph filters read emitted branch | `12d343968` | ORACLE ✅ |
| 2 | Named grid clusters Unique-before-Suite per rank | `101d2cf42` | ORACLE ✅ |
| 6 | Badge picker + SAMPLER_RANKS §8 order | `a25b7b026` | ORACLE ✅ |
| 7 | Timeline suite color → --tier-fusion (was --apex-gold/--tier-ultimate) | `d5fd5c564` | ORACLE ✅ |
| 4 | HoH plaque rows tint by rank+branch (gold/purple) | `8147ea326` | DESIGN (Marco: fold in) ✅ |
| 5 | /heroes reads named index, all rank>=4, no cap (firecrawl restored) | `4b850ce71` | ORACLE ✅ (verified: 11 heroes) |
| 8 | Homepage 'ultimates' stat → 5 true (5★ Suite named), was 15 | `6c8388ecc` | ORACLE ✅ (verified: 5) |

**Rebased onto remote tip 8571da778 at start (branch was 8 commits behind — prior session's JSON-LD/API regen).**

**DEFERRED:**
- Item 3 (plaque avatar/medallion) — design cherry-pick, hand-port `e31f58077` (D6/D8) when approved.
- Item 9 (~40 more --apex-gold/--tier-ultimate in plaque.css) — dedicated token-migration PR.
- Gold-★ graph mark — hand-port `4801e0c13` (D3/D18), design pass.
- Guard-hole audit (skill-graph.js type-read passed grep-guard) — Marco: audit after fixes.

---

## Ledger

| # | Issue | Surface | Verdict | Scope | Root cause / fix |
|---|---|---|---|---|---|
| 1 | Filters (Fusion/Unique/Suite) don't filter | Graph | 🔴 ORACLE | #1235 | `skill-graph.js:1357/1353` predicate `skill.type === state.legendFilterType`; buttons `2429-2431` set dead Ygg-I enum `extra`/`unique`/`ultimate`. Nodes carry `type∈{basic,fusion}` + emitted `branch∈{standard,suite,unique}`. Fix: key on `skill.branch`; Fusion→`type==='fusion'`. |
| 2 | 4★ Unique piled into 4★ Extra | Named grid | 🔴 ORACLE | #1235 | `named-skills.js:727-731` groups by `levelNum(ns.level)` only; `withinGroupSort` 628-634 never reads branch. Emitted `ns.branch` available. Fix: branch tiebreaker unique-before-suite (§8). |
| 5 | /heroes firecrawl missing (~7 shown) | /heroes/ | 🔴 ORACLE | #1235 | `heroes.js:636-641` `topSkill.level≥4` filter (§8-named DEFECT: cap-of-1 + rankless). Build blob `buildApiProjection.py:235,268` emits `topSkill={id,level,TM}`, no branch/rank. **Fix (Option A, client-side):** heroes.js already fetches `named/index.json` (L26) — select from ALL buckets `rank≥4`, no cap, order rank-desc unique-before-suite (mirror `page-ia.js:228-247`). Also deletes read-time `computeBranch` (heroes.js:77-85). |
| 6 | Unique not prioritized over Suite | Badges | 🔴 ORACLE | #1235 | `badges/index.html` picker `1797/1621` unsorted (registry order); `SAMPLER_RANKS` `1302-1312` appends Uniques at tail (inverse of §8). Fix: comparator rank-desc + unique-before-suite; reorder SAMPLER_RANKS to §8 interleave. |
| 7 | Progression chart / previous-type tokens | Timeline | 🔴 ORACLE | #1235 | Founder ruling: token-migration scope, same category as graph. Chart step-line reads emitted branch→TIER_HEX correctly (601-602); flat-blue = correct `--tier-basic` for all-standard profile. RE-SCOUT running to pin the exact "previous type" token (suspect `--apex-gold` vs `--tier-fusion` inconsistency, missing `.ptl2__delta-badge` CSS, or a surviving raw-type surface). |
| 3 | Plaque avatar + medallion pos/size | Named plaque | 🎨 DESIGN | defer | Plumbing correct (reads emitted branch/rankWord). Only visual unfinished. Source: **`e31f58077` (D6/D8), HAND-PORT** — plaque.js rewired by #1235; tip still orb-before-avatar (L663-664); plaque.css D6/D8 rules absent. No oracle regression (pure layout). |
| 4 | Hall tokens (gold ults / purple uniques) | Hall | ✅ ON-SPEC | none | Already gold-suite + purple-unique, selected from emitted branch+rank (`page-ia.js:238-245,310-312`, `plaque.js:119-128`, `plaque.css:734-763`). If wrong color live = missing `.webp` → `[data-stamp-fail]` gradient (still branch-correct). No fix. |

## Oracle cluster shared signature
Items 1, 2, 5, 6 (and likely 7) all = **consumers ignore the emitted `branch`/`rank` and read the dead `type` enum or don't sort by branch.** This is the completeness the oracle cut promised. Item 1's live `skill.type ===` read **survived the grep-guard** → suspected guard hole (Marco: note now, audit after fixes).

## #1227 cherry-pick viability (design pass, NOT now)
- **Item 3 plaque** → `e31f58077` D6/D8, SURVIVES, **HAND-PORT** (plaque.js + plaque.css). Only genuine outstanding #1227 design item.
- **Gold-★ graph mark** → `4801e0c13` D3/D18, SURVIVES, **HAND-PORT** (~30 lines, skill-graph.js; tip still has ORIGIN_PATHS laurel).
- **D15 prev-week** → `55a62ac13`, clean cherry-pick (weekly-report `.py`/`.j2`, outside JS rewire zone).
- **D12 badges-words** → `332736ab0`: **REDUNDANT** — #1235 already has identical fix + more. Skip.
- **D74 /heroes** → `3555c40da`: **DISCARD — DO NOT PICK** (re-adds `type` read-time computeBranch + 8-cap = oracle regression). §8 behavior already on tip.
- Hall tokens / timeline tokens → **no #1227 source** (consume-frontend/#1235 work already on tip).

## Guard-hole note (audit after fixes)
`skill-graph.js:1357` reads `skill.type ===` against branch-word-adjacent values and passed the taxonomy grep-guard. Check whether the guard scoped skill-graph.js out or whether `skill.type === state.legendFilterType` (variable RHS, not a branch-word literal) dodged the pattern. If holed, tighten as oracle debt.

## Decisions (Marco, this session)
- Fix all 4 confirmed oracle bugs (1/2/6 + 5) NOW, one commit each, verify in preview. (Item 7 added after ruling.)
- Segregation = ONE canonical rule everywhere (unique before suite; never co-mingled).
- /heroes = scout-first → confirmed ORACLE → in-scope.
- Guard hole = note now, audit after fixes.
- Item 7 = in-scope (token-migration scope).
- Cherry-picks return full viability + SHAs; NO staging of design work yet.
