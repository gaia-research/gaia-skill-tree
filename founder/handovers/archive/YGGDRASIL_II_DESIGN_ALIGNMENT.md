# Yggdrasil II — Design-Pass Alignment Handover (#998)

**For:** the Yggdrasil II frontend design pass (EPIC #1002 · sub-issue #998)
**Author:** Founder Orchestrator (restored from closed PR #1171 + extended for the live design pass)
**Original date:** 2026-07-14 · **Restored + refreshed:** 2026-07-17
**Scope:** frontend / asset / design surface only (DESIGN.md, `docs/**/*.html`, `docs/js/**`, `docs/css/**`, AOV, plus the rank-name script maps). The prose docs (META.md, CONTEXT.md, trust-methodology) are handled separately by #994 (LANDED). The CI guard by #999.

> **Provenance note.** This file is the content of PR #1171, which was **closed unmerged** on 2026-07-15 when the aggregate PR was rebuilt during the binary-master history purge. The doc itself never landed on the branch. Its dependency gate (#995 + #996 + #997) has since **fully landed**, so the work it describes — which IS #998 — is now unblocked. Restored here as the living spine for the design pass.

> **Guard-safe notation (Rank Vocabulary Guard, #999).** This handover is a hard-fail surface for the banned-synonym guard, so it names the two deprecated Ygg-I rank words *obliquely* — the literal strings must not appear here. Notation used below: **`[dep-4★]`** = the deprecated 4★ rank word (now **Extra** on the suite branch / **Unique** on the unique branch); **`[dep-5★]`** = the deprecated 5★ rank word (now **Ultimate** / **Unique Ultimate**); **`[dep-6★]`** = its 6★ star-suffixed form (now **Apex** / **Unique Impossible**). A middle dot in **`Basic·Skill`** / **`Fusion·Skill`** marks the banned type-word-plus-`Skill` bigram (type words stand bare: `Basic`, `Fusion`). These are notation only; the historical meaning of every line is unchanged. The literal deprecated forms live in `CONTEXT.md` § Banned synonyms.

---

## 0. Design-pass operating contract (2026-07-17 session)

This design pass runs under an explicit workflow ratified with Marcus:

1. **Target `dev/yggdrasil-ii-staging`. One pass. CI-green is NOT required** — the sprint batches to green under #999 before staging → main.
2. **Catch the PATTERN, not the surgical fix.** Every reported nitpick is first checked for recurrence: does the same language / layout / logic live elsewhere? If so, the fix sweeps all instances, not the one screenshot.
3. **Commit + push frequently.** Small, logical commits.
4. **Worker concurrency: 2 (sonnet) / 1 (opus).** Fan-out planned per §7 below.
5. **Plan first, execute on ratification.** Scouts map; orchestrator plans; Marcus drips images/policies; nothing is written until the plan is ratified.

The **live nitpick log is §8** — every reported issue lands there with its pattern generalization and planned fix.

### 0.1 Ratified rulings (2026-07-17, founder) — build the fan-out on these

| # | Question | RULING | Consequence |
|---|---|---|---|
| R1 | `--tier-unique` color token | **New violet `--tier-unique` design token** | A-schema-core defines it; every unique surface (dark plaques, badges, OG, About) reads it. No hex fallbacks (CI guard). Uniques get a distinct hue, not just "the bg color." |
| R2 | Correctness-first vs bundle | **Bundle correctness + design per surface** | Each surface-PR fixes schema-read AND redesigns together. **BUT** the shared `computeBranch`/`rankWord` resolver + violet token still land as **step 1 of the FIRST bundled PR** (the plaque PR) — everything else imports it. One-agent-first, THEN fan. Non-negotiable ordering. |
| R3 | Mobile-first (N-12 deliv. 2) scope | **INSIDE #998** | Sprint-completeness (CLAUDE.md "no follow-ups"): mobile-first across non-homepage surfaces is #998's own remainder, NOT a spun-off EPIC. #998 doesn't close until non-homepage surfaces are mobile-first. Homepage FROZEN except N-1/N-2. |
| R4 | /impeccable design gate | **No founder gate — trust /impeccable + reviewer agent** | N-8 OG, N-10 footer, N-7 reports, N-4 wreath: /impeccable produces, reviewer agent grades + picks, no founder sign-off between. MITIGATION: reviewer prompts must be **adversarial** (grade vs the design standard, reject-by-default) so "no gate" ≠ "no quality bar." |

**Load-bearing ordering from R2:** the dependency isn't gone, it moved. Sequence = **PR-1 (plaque + shared computeBranch/rankWord + violet token)** lands → then A-heroes, A-leaderboard, D-named, N-5, N-6, N-8 fan out in parallel (each imports the shared resolver). Never run two resolver-writing agents concurrently.

---

## 1. Purpose + when to act

The ratified **Yggdrasil II v2** model splits the old single `type`/rank taxonomy into two orthogonal axes and renames the 4★–6★ ladder. This doc tells you *exactly* what to change on the design surface so the site renders the v2 model correctly.

**Dependency gate — ALL THREE HAVE LANDED on `dev/yggdrasil-ii-staging` (gate open):**

| Blocked-by | What it lands | Status |
|---|---|---|
| **#995** | schema: `type ∈ {basic, fusion}`, `suiteComponents`, no `branch` field on nodes | ✅ MERGED |
| **#996** | CLI `computeBranch(named)` → `standard`/`suite`/`unique` | ✅ MERGED |
| **#997** | registry migration (`extra`→`fusion`, `ultimate`→`fusion`, `unique`→`basic`; backfill `suiteComponents`) | ✅ MERGED |

### The v2 model (yardstick)

- **TYPE axis** (starless/generic nodes only): `basic` | `fusion`. Pure structure — `fusion` iff the node has prerequisites. **Never consulted for branch.**
- **`suiteComponents`**: presence on the **Named Skill** drives the branch fork; also feeds Trust Magnitude. Independent of `type`. **`suiteComponents` is a Named-Skill-only field — it never lives on the starless/generic parent.**
- **BRANCH axis** (named skills only, *derived at read-time, never declared*): `branch = f(the Named Skill's suiteComponents present?, rank)`.
  > **[SUPERSEDED 2026-07-18 — branch is EMITTED at BUILD time by src/gaia_cli/taxonomy.py onto every named entry; consumers READ it. "Never declared on the source node" still holds; "derived at read-time" does not. Exception: the starless graph (docs/graph/gaia.json) still derives client-side. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
  > **[SUPERSEDED 2026-07-18 — the `rank ≥ 4 AND` conjunct is wrong for MEMBERSHIP. Membership is suiteComponents-first from any rank: suiteComponents present → suite (at ANY rank); else rank ≥ 4 → unique; else standard. A 2★/3★ suite-component skill is already `suite`. Only DECORATION/ladder-word forks at 4★+. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**
  - rank 1–3 → **standard** (no branch fork)
  - rank ≥ 4 AND the Named Skill has `suiteComponents` → **suite**
  - rank ≥ 4 AND the Named Skill has **no** `suiteComponents` → **unique**
- **Ladders:**
  - standard: 1★ **Awakened** · 2★ **Named** · 3★ **Evolved**
  - suite: 4★ **Extra** · 5★ **Ultimate** · 6★ **Apex**
  - unique: 4★ **Unique** · 5★ **Unique Ultimate** · 6★ **Unique Impossible**
- **`[dep-5★]` and `[dep-4★]` are BANNED.** `Ultimate` is the universal 5★ word. **The "Skill" suffix attaches to RANK words** — `Extra Skill` / `Unique Skill` / `Ultimate Skill` / `Apex Skill` are valid rank phrasings. **Type words stand bare** (`Basic`, `Fusion`) — `Basic·Skill` / `Fusion·Skill` are BANNED (guard-enforced). 1★–3★ ladder words (Awakened/Named/Evolved) are always star-qualified.
- Type & branch are orthogonal. Evidence Floor is removed; **TM is the sole gate.**

---

## 2. File-by-file checklist (taxonomy alignment)

| File | What's stale | Required v2 change | Blocked-by |
|---|---|---|---|
| `DESIGN.md` | `[dep-4★]`/`[dep-5★]` rank words; `type === 'extra'\|'unique'\|'ultimate'` glyph rules; `Extra Skill`/`Ultimate Skill` type labels; glow/animation tokens named for old ranks | Retitle rank sequence to Awakened→Named→Evolved→(Extra/Unique)→(Ultimate/Unique Ultimate)→(Apex/Unique Impossible); rewrite glyph mapping to branch-derived; rename `Ultimate Skill Cycle`/`Extra Skill Cycle` sections | ✅ unblocked |
| `docs/js/skill-graph.js` | reads `type==='unique'`, `type==='ultimate'`; `type==='basic'` isolation heuristic | replace `type`-based branch/rank inference with `suiteComponents`+rank branch logic mirroring `computeBranch` | ✅ unblocked |
| `docs/css/tokens.css` | ~~no `--tier-fusion` token~~ | **✅ DONE — `--tier-fusion` + `-rgb`/`-bg`/`-border`/`-edge`/`-symbol` already added (L17-22).** Remaining: decide retirement of legacy `--tier-extra/unique/ultimate` aliases | ✅ unblocked |
| `docs/css/plaque.css` | `--tier-extra`/`--tier-ultimate`/`--tier-unique` refs; "[dep-5★]"/"[dep-4★]" glow comments; "rank IV ([dep-4★])" comment | map to branch tokens; scrub [dep-5★]/[dep-4★] from comments | ✅ unblocked |
| `docs/css/ascension-overdrive-v2.css` | `[data-tier="hardened"]` selectors; "[dep-4★]..Awakened" comment | rename `hardened`→`extra` (or branch-aware `data-branch`); scrub comments | ✅ unblocked |
| `docs/samples/tree.html` | legend "Extra Skill"/"Ultimate Skill"; tree lines "4★ [dep-4★]"/"5★ [dep-5★]"/"6★ [dep-6★]" | **Fusion** legend (bare type word); branch-correct rank labels | ✅ unblocked |
| `docs/samples/foundation.html` | medallion `[dep-4★]`/`[dep-5★]` | Extra/Ultimate (suite) or branch-aware labels | ✅ unblocked |
| `docs/badges/index.html` | rank table "[dep-4★]", "[dep-5★]", "Origin 5★ [dep-5★]"; JS labels `4:"[dep-4★] · 4★"`/`5:"[dep-5★] · 5★"`; `s.type==="unique"` | branch-aware rank labels; drop [dep-5★]/[dep-4★]; replace `type==="unique"` read | ✅ unblocked |
| `docs/audits/ruflo-curation.html` | badges "4★ [dep-4★]"/"5★ [dep-5★]" | Extra/Ultimate per branch | ✅ unblocked |
| `docs/codex/trust-methodology.html` | "6★ [dep-6★] (Apex)"; `--tier-extra/ultimate` refs | "6★ Apex"; branch tokens | ✅ unblocked |
| `docs/en/faq.html` | rank table "[dep-4★]"/"[dep-5★]" | Extra/Ultimate | ✅ unblocked |
| `docs/en/skill-hierarchy.html` | "[dep-4★]"/"[dep-5★]" (10 hits) | Extra/Ultimate | ✅ unblocked |
| `docs/samples/ranks.html` | "[dep-6★] · 6★" | "Apex · 6★" (or Unique Impossible if unique-branch sample) | ✅ unblocked |
| `docs/samples/index.html` | SVG text "[dep-4★]" | Extra | ✅ unblocked |
| `docs/index.html` | Ascension asset-planning comment referencing `rank-5-transcendent.png` etc. | rename asset stems to `-ultimate`; regenerate rank-5/6 art | ✅ unblocked |
| `docs/u/index.html` | AOV medallion surface | ensure medallion rank labels use v2 names | ✅ unblocked |
| `docs/agent.md` | `◇ Extra Skills`/`◆ Ultimate Skills` defs; `4★+ ([dep-4★]/[dep-5★])`; `6★ ([dep-6★] / Apex)` | Fusion type; branch-aware rank names — **⚠ Hermes-managed; coordinate before editing** | prose track |
| `DEV.md` | `reclassify` doc: `type ∈ basic\|extra\|ultimate\|unique` | `type ∈ basic\|fusion` | prose track |
| `CONTRIBUTING.md` | "Skill types in graph: `basic`, `extra`, `ultimate`" | `basic`, `fusion` | prose track |
| `GOVERNANCE.md` | "4★ ([dep-4★])"; "Basic/Extra Skills"/"Ultimate Skills" approval rules; "reclassified to `extra` tier" | branch/type-correct wording | prose track |

> `DEV.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, `docs/agent.md` are prose and were on #994's radar. Only touch them from this pass if #994 explicitly left them; otherwise leave to the prose track to avoid double-editing.

> **Scout-verified line numbers supersede this table.** The anchors above are pre-migration exemplars from PR #1171. The four scouts dispatched 2026-07-17 (JS enum readers, docs copy, script maps, CSS/AOV) re-verify every line and find ADDITIONAL occurrences the pre-migration doc missed. Their inventories become the authoritative fix list — merged into §2.1 below on return.

### 2.1 Scout-verified inventory (populated on scout return)

**SCOUT #2 — docs copy sweep, VERIFIED 2026-07-17.**

**Guard status is the organizing principle (from `docs/guard-topology.md`):**
- **HARD-FAIL** (Rank Vocabulary Guard exits 1): `registry/**`, root `*.md`, `docs/**/*.md`, `founder/handovers/**/*.md`.
- **WARN-only allowlist (tracked #994):** `GOVERNANCE.md`, `CONTEXT.md`, `PRODUCT.md`.
- **HARD-EXCLUDED (CI never scans):** `scripts/**`, `docs/assets/**`, `docs/badges/**`, `**/*.html`, `registry/schema/**`.
- **Consequence:** every `docs/**/*.html` hit below is **copy-quality only** — no CI gate. The guard-enforced surfaces that MUST be clean are `DESIGN.md` and (post-#994-allowlist-removal) `GOVERNANCE.md`.

**Sweep patterns (fix by pattern, not file):**

| # | Pattern | Files | Priority |
|---|---|---|---|
| **F** | **JS label-map objects** — `'4':'[dep-4★]','5':'[dep-5★]'` render at RUNTIME | `docs/named/report.html` L631; `docs/badges/index.html` L1283-84 (SAMPLER_RANKS) | **1 — highest (runtime, not just copy)** |
| **A** | **6-row rank-ladder table/list** — identical structure repeated | skill-hierarchy.html (8), getting-started.html (3), faq.html (3), badges/index.html (5), samples/foundation.html (3), samples/tree.html (3), named/report.html (1) | 2 (one template fix sweeps 7 files) |
| **J** | **Root-MD guard-enforced** | `DESIGN.md` L38-40/313/330/348 (`Extra/Ultimate Skill` type words + `…Cycle` section names); `GOVERNANCE.md` L28/37/38/64/66 | 3 (only hard-fail surfaces) |
| **D** | **Prose in docs/en/** — functional copy (Verifier threshold) | evidence-classes.html L576, named-skills.html L787, skill-hierarchy.html L690/733/844/927, getting-started.html L847/876 | 4 |
| **H** | **"Evidence floor" column header** — retired concept (TM is sole gate) | badges/index.html L1089 `<th>Evidence floor</th>` | 5 |
| **B/C** | **Tier-card / legend TYPE-WORD** + fusion.html type prose | skill-hierarchy.html L659-698, samples/tree.html L181-190, samples/index.html L530-532, **fusion.html ~16 hits** L7/639-700/848/860 | 6 |
| **E** | **OG-card mock medallion** | samples/ranks.html L342 `[dep-6★] · 6★` | 7 |
| **G** | **SVG/TUI compact strip** (script-generated) | samples/index.html L247-258, samples/tui-preview.html L102 (← from `render_tui_preview.py`, fix at script) | 7 |
| **I** | **ARCHIVAL reports** — historical record | `docs/audits/ruflo-curation.html` (5), `docs/meta/reports/2026-*.html` (several) | **8 — FLAG, do not blindly change** |

**Critical distinctions:**
- **TYPE-WORD vs RANK-PHRASING:** `Basic·Skill` / `Fusion·Skill` are ALWAYS banned (type words stand bare). But `Extra Skill` / `Unique Skill` / `Ultimate Skill` / `Apex Skill` are VALID **rank** phrasings (per `docs/rank-vocabulary-guard.md` L40-48). The violation is using Extra/Ultimate as *type/tier section labels* (e.g. `<div class="tier-card-name">Extra Skill</div>` naming the taxonomy), not as rank names. Don't over-correct valid rank phrasings.
- **Pattern F is functional, not cosmetic** — those JS maps render the wrong rank name live. Highest fix priority alongside the JS enum work (Lane A).
- **Archival (Pattern I):** dated reports/audits describe ranks *as they were at the time*. A 2026-05 report saying "5★ [dep-5★]" is historically accurate. Options: leave as-is, or add a one-line archival banner. Do NOT rewrite history silently — surface as a ratification micro-decision.
- **`tui-preview.html` (Pattern G) is generated** by `scripts/render_tui_preview.py` — fixing the HTML directly gets overwritten; fix the script (Lane C). Same for any `SAMPLER_RANKS`/`LEVEL_LABELS` that turn out to be generated.

> **[SUPERSEDED 2026-07-18 — STALE EXCEPT FOR THE STARLESS GRAPH. TRUE only for `docs/graph/gaia.json` (still derives branch client-side). FALSE for `named/index.json`, which now carries the emitted `branch` field written at BUILD time by src/gaia_cli/taxonomy.py (#1232–1234). Consumers of named/index.json read the emitted branch; only the starless graph derives client-side. See founder/handovers/archive/YGGDRASIL_II_SUPERSEDED_2026-07-18.md]**

**Scout #1 (JS enum readers) — RETURNED 2026-07-17. VERDICT: browser data carries NO `branch` field.** `docs/graph/gaia.json` + `named/index.json` ship `type: "basic"|"fusion"` and `suiteComponents`/`level` only. JS MUST derive branch client-side. Canonical implementation already exists in `docs/js/world-tree-layout.js` `resolveSemantics()` (L356-413) — extract as shared helper; **no other JS file has a `computeBranch` equivalent.** Client formula:
```js
function computeBranch(ns){var r=parseInt((ns.level||'').replace(/\D/g,''),10)||0;var s=Array.isArray(ns.suiteComponents)&&ns.suiteComponents.length>0;if(r>=4&&!s)return'unique';if(s)return'suite';return'standard';}
```

**Four dead/broken patterns across 7 JS files (full table in Scout #1 return — recap):**
1. **TYPE-BASED BUCKET ASSIGNMENT** — dicts keyed `{basic,extra,ultimate,unique}` bucketed via `skill.type`; `extra/ultimate/unique` buckets now ALWAYS empty. Files: skill-graph.js L404-414, named-skills.js L141-152/L694, page-ia.js.
2. **DEAD TYPE-EQUALITY CHECKS** — `x.type==='unique'|'ultimate'|'extra'` always `false`. Files: skill-graph.js L43/1106/1553/1588/1704, skill-explorer.js L1368/1445/1482/2149/2398-2424, named-skills.js L185, page-ia.js L102/107/299.
3. **FLAT TYPE→DISPLAY MAP** — 4-entry glyph/label/sort dicts, partly dead + missing `fusion` key. Files: skill-graph.js L1739/1797/2370-2372, skill-explorer.js L16/2133, named-skills.js L530, page-ia.js L400, plaque.js L642/L715, profile-filter.js L266.
4. **CSS-VAR / DOM-ATTR TIER NAMES** — `var(--tier-unique|ultimate|extra)` + `data-type="unique"` reads return empty (tokens undefined — see §3.3). Files: skill-graph.js L105-107/167-169/1719, skill-explorer.js L2143/2398-2399, named-skills.js L214, plaque.js L659/785, profile-timeline.js L153-155/274-276.

**Single-point fix:** add `branch: computeBranch(skill)` in `skill-graph.js` `normalizeSkills()` (L256-276, the central normalization) and propagate. `skill-explorer.js` two-IIFE gotcha: IIFE 1 (L1-2679) holds ALL stale reads; **IIFE 2 (L2682-3110) has ZERO** (parses tree.md glyph chars, not `type`) — helper needed only in IIFE 1. Structural note SE-3: `isUlt = ns.level==='5★'` (L819) conflates suite-5★ with unique-5★ ("Unique Ultimate") → `--ultimate` install flag mis-applies to Unique; guard with `suiteComponents.length>0`. **No `[dep-5★]`/`[dep-4★]` in any JS file; `levelLabels["5★"]="Ultimate"` in gaia.json is CORRECT (universal 5★ word).**

---

## 3. Specific call-outs

### 3.1 DESIGN.md — the big one
- legacy short tokens `--extra`/`--ultimate` + canonical `--tier-extra`/`--tier-ultimate`: `--tier-fusion` now exists; decide whether Unique-branch keeps its own violet token or reuses `--tier-basic` (v2: unique-branch skills sit on `basic` generics).
- tier color table rows `extra ◇ Extra Skill` / `ultimate ◆ Ultimate Skill` — collapse to a single `fusion ◇ Fusion` row (type word stands bare — no "Skill" suffix).
- rank sequence still reads `… → [dep-4★] (4★) → [dep-5★] (5★) → Apex (6★)`. Replace with the branch-forked ladder.
- rank→token table maps `[dep-4★] → --rank-4`, `[dep-5★] → --rank-5`. Rename rank labels; tokens can stay numeric (`--rank-4/5/6`).
- glyph mapping still leads with `type === 'extra'`/`'unique'`/`'ultimate'`. Post-migration, drop the Ygg I clauses entirely.
- evidence-tint mapping uses `--tier-ultimate/unique/extra`. Re-key to fusion + branch tokens.
- glow tokens `--glow-IV`/`--glow-V` labelled "[dep-4★]"/"[dep-5★]"; scrub the labels (keep the numeric tier meaning).
- animation-cycle section titles `Ultimate Skill Cycle` / `Extra Skill Cycle` and tree dialog labels `◆ Ultimate Skill:` / `◇ Extra Skill:` — rename to Fusion / branch-rank wording.

### 3.2 `docs/js/skill-graph.js` — legacy `type` reads
Rank-inference-from-type (`if (type === 'unique') rank = 5;`), type-based bucket assignment (`if (skill.type === 'unique') satellite.unique.push`), graph-isolation heuristic (`type === 'basic' && !prereqs`), count filters (`s.type === 'unique'`), and dead value checks (`type === 'ultimate' || type === 'unique'`) all read enum values that no longer exist. Replace with a client-side branch resolver mirroring `computeBranch` (branch from `suiteComponents` + rank). **Scout #1 confirms whether the browser's data (`docs/graph/*.json`) carries `suiteComponents`/`branch` — determines if JS can derive locally or needs a data change.**

### 3.3 `--tier-fusion` CSS token — ✅ DONE (+ scout #4 correction)
`docs/css/tokens.css` L17-22 defines `--tier-fusion` + all six variants (`-rgb/-bg/-border/-edge/-symbol`) — complete, no `-border` gap. L72 aliases `--fusion`.

**SCOUT #4 CORRECTION to #1171's assumption:** `--tier-extra`, `--tier-unique`, `--tier-ultimate` are **NOT defined in `tokens.css` at all** (tokens.css is auto-generated from `registry/gaia.json`, which no longer emits them). They are consumed **site-wide** (plaque.css, styles.css 70+ refs, ascension-overdrive-v2.css, 6 JS files, most `docs/**/*.html`) purely via **inline fallback hex** — `var(--tier-extra, #c084fc)`. Two consequences:
1. The "retire the aliases" task from #1171 §3.3 is moot — there are no alias *definitions* to retire; the work is migrating **consumers** off the undefined token names onto `--tier-fusion` / branch tokens.
2. **CI-guard hazard:** CLAUDE.md bans hex-color fallbacks (`Avoid hex color fallbacks; use design tokens only`). Every `var(--tier-extra, #hex)` is technically a latent guard trip. The migration should replace these with defined tokens, not perpetuate the fallback pattern.
3. `data-tier="hardened"` selectors live in `docs/css/ascension-overdrive-v2.css` L1248/L1252/L1607 (no `transcendent` selector exists). Comments carrying banned words: plaque.css L260-261/L568, ascension-overdrive-v2.css L1091.

> **Decision needed (for the plan):** define `--tier-unique` (violet) as a real token in the pipeline, OR fold unique-branch onto `--tier-basic`/a new branch token, OR keep a curated set of design tokens for the branch ramp. This is a token-architecture call, not a mechanical swap — surface as a ratification item.

### 3.4 HTML branch-definition copy
Where copy explains the *taxonomy*, say **Fusion** (bare type word). Where copy explains *ranks*, use the branch-forked names. Recurring structures (scout #2 confirms count): the 6-row rank-ladder table, medallion name spans, legend labels.

### 3.5 AOV medallion rank labels
The Ascension-Overdrive medallion must use **Extra / Ultimate / Apex** (suite) and **Unique / Unique Ultimate / Unique Impossible** (unique) and **drop [dep-5★]** entirely. Touch points map via scout #4.

---

## 4. Script rank-name maps — BRANCH-AWARE (all unblocked, #996 landed)

These scripts hard-code a `rank → name` map. That mapping is **no longer valid** at 4★+ because the name forks by branch (Suite vs Unique). They need `computeBranch(named)` from #996 to pick the right ladder per skill — **do NOT do a flat string swap** (`[dep-4★]→Extra`), which silently mislabels every Unique-branch skill.

| Script | Stale map |
|---|---|
| `scripts/generateBadges.py` | rank map `4:"[dep-4★]", 5:"[dep-5★]", 6:"Apex"` (+ glow colors) |
| `scripts/generateOgCards.py` | `4:"HARDENED", 5:"TRANSCENDENT", 6:"TRANSCENDENT ★"`; plate copy `type="ultimate"` |
| `scripts/inspectTrustMagnitude.py` | `4★:[dep-4★], 5★:[dep-5★], 6★:[dep-6★]` |
| `scripts/generate_ruflo_curation.py` | `4★:[dep-4★], 5★:[dep-5★]` |

The correct pattern: resolve the skill's branch, then index into the branch-specific ladder — a single shared source everything imports, not a flat per-script dict.

### 4.1 Canonical source (scout #3 — VERIFIED 2026-07-17)

**All rank/branch resolution converges on `gaia_cli`. Scripts must import, never re-declare:**

```python
from gaia_cli.trustMagnitude import computeBranch   # trustMagnitude.py L1283; 'standard'|'suite'|'unique'
from gaia_cli.formatting import rank_word, format_rank_label, rank_color_for, RANK_COLORS
```

- `computeBranch(named, genericSkillMap)` — `<4★`→standard; `≥4★`+suiteComponents→suite; `≥4★` no suiteComponents→unique. **Never consults `type`.**
- `formatting.py`: `LEVEL_LABELS_SUITE` (L215, from meta.json), `LEVEL_LABELS_UNIQUE` (L216 `{4:Unique,5:Unique Ultimate,6:Unique Impossible}`), `rank_word(level, branch)` (L384), `format_rank_label` (L404), `rank_color_for` (L414, Unique gets violet ramp `RANK_COLORS_UNIQUE`).
- **`branch` MUST flow from `computeBranch` — never from `skill["type"]`.** For call sites holding only a level string (no named dict), thread branch from the data source or default `"suite"` (safe for non-Unique).

### 4.2 Full script inventory (scout #3 — supersedes #1171's 4-script list)

**FLAT-RANK-MAP + BANNED-WORD (4 scripts duplicate the same dict — the core sweep):**
| Script | Class | Offender |
|---|---|---|
| `scripts/generateBadges.py` | **Class S (badges)** | L53-57 `RANK_NAMES` ([dep-4★]/[dep-5★]); + `type=="unique"` reads L641/664/777/780; glow `load_rank_colors` L109 misses Unique violet |
| `scripts/generateOgCards.py` | **Class S (OG cards)** | L652-658 `rank_words` (HARDENED/TRANSCENDENT ★ into SVG text); plate dispatch on `type` L731/788-792 → should use `computeBranch` |
| `scripts/inspectTrustMagnitude.py` | dev inspector | L49-57 `STARS_TO_RANK_NAME`; inline banned L205/L327 |
| `scripts/generate_ruflo_curation.py` | dev audit HTML | L28-34 `LEVEL_LABEL`; `TYPE_SYMBOL` 4-value enum L36-41 |

**BANNED-WORD in strings/symbols (lower severity, dev-only):**
- `scripts/render_tui_preview.py` L94-96 (label comments)
- `scripts/compress-assets.py` L164-194 (`rank-4-hardened` asset stem — vendor filename map)
- `src/gaia_cli/tui/tokens.py` L94-117 (`RANK_HARDENED`/`RANK_TRANSCENDENT` **symbol names** + `RANK_BY_STAR` — renaming is a breaking change for TUI importers; treat carefully)
- `src/gaia_cli/formatting.py` L8 stale comment `6★ [dep-6★] accent` — **inside the CLI, may be guard-enforced; scrub**

**TYPE-ENUM-READ only (no banned words; fix if touched):**
- `scripts/generateProjections.py` L109/158-172/492-523 (4-value `type` glyph + section dispatch)
- `scripts/generateNamedIndex.py` L498 (`type=="ultimate"` gate)
- `scripts/build_docs.py` L295 (`type=="unique"` count → feeds `uniqueSkills` stat on homepage)
- `scripts/validate.py` L242 (`type=="unique"` prerequisite rule — legitimate schema read, likely leave)

> **Note the guard tension:** `src/gaia_cli/tui/tokens.py` and `formatting.py` L8 are inside `src/` — NOT in the `scripts/**` guard exclusion. A banned-word scrub there may be needed for the #999 guard AND may collide with the CLI lane. Flag for the plan: decide whether TUI symbol renames belong in this design pass or defer to a CLI-scoped follow-up (symbol renames are breaking).

---

## 5. AOV V4 — Asset C + Asset D into the new skill plaques (FOUNDER DIRECTIVE)

**Standing directive carried from the 2026-07-16 session handoff:** *"Ascension Overdrive V4 assets MUST be incorporated into the new skill plaques — specifically Asset C and Asset D."*

**SCOUT #4 — VERIFIED 2026-07-17:**

- The branch `design/yggdrasil-ii-aov-v3` **does NOT exist** (local or remote). The V4 45-reference WebP set is **already on `dev/yggdrasil-ii-staging`** under `docs/assets/ascension-overdrive/` (110 files). No branch merge needed — the assets are in hand.
- **Asset C = Suite rank stamps** (`aov4-c*`), 6 ranks × 3 sizes (badge/card/hero):
  - `aov4-c1-suite-awakened`, `-c2-suite-named`, `-c3-suite-evolved`, `-c4-suite-extra`, `-c5-suite-ultimate`, `-c6-suite-apex` — each `{-badge,-card,-hero}.webp`.
- **Asset D = Unique branch stamps** (`aov4-d*`), 3 ranks × 3 sizes:
  - `aov4-d4-unique`, `-d5-unique-ultimate`, `-d6-unique-impossible` — each `{-badge,-card,-hero}.webp` (portrait ~916×1072).
- **Commission intent (`founder/handovers/design-v6.1.1-ascension-overdrive-commissions-v3.md` L56):** *"Asset C v3 doubles as the foundation for skill plaques used elsewhere on the site (skill-explorer plaques, badge OG cards, contributor-profile rank marks, potentially README badges)."* — This is the ratified basis for the directive.

**Current plaque reality (blocks naive integration):** `docs/css/plaque.css` plaques carry **ZERO `<img>` rank/type art** — identity is CSS gradient orbs only (`.plaque-orb--basic/extra/unique/ultimate`, radial-gradient off `--tier-*` tokens, L617-656). The only raster in a plaque today is the `.plaque--hall` blurred OG-art backdrop (8% opacity) + contributor avatar. So slotting Asset C/D in is **net-new markup**, not a swap.

**Integration plan (candidate, unratified):** the three sizes map to plaque scales —
- `*-hero.webp` (2048²) → `.plaque--detail` / `.plaque--og` / full-surface;
- `*-card.webp` (~800²) → `.plaque--tile` / `.plaque--settled` / `.plaque--hall`;
- `*-badge.webp` (~240²) → `.plaque--mini` / rank chip / `.plaque-orb` context.

Add a `<picture>` inside `.plaque__header` (or replace `.plaque-orb`'s gradient with a `background-image`) keyed by `data-level` + branch. **Branch selection MUST use `computeBranch` semantics** — Suite ranks → C series, Unique ranks → D series. `object-fit: contain` handles the portrait D aspect (precedent: `.aov-ucard__plate img`, v2.css L686). This is a distinct **design workstream (Lane D)** layered on top of taxonomy alignment.

> **Homepage AOV note:** the `#ascension` section in `index.html` already wires the full C/D set via `<picture>` (three breakpoints/scene). One inconsistency scout #4 flagged: paired-4/5 suite scenes still pull **v3** field plates (`aov3-suite-plate-*`) and haze (`aov3-haze-*.webp`) while everything else is v4 — candidate cleanup. The plaque work is the *skill-explorer/badge/profile* surfaces, which have none yet.

---

## 6. Do NOT do

- **Do not do a flat rank-map swap** (`[dep-4★]→Extra`) in the four scripts — mislabels every Unique-branch skill. Use `computeBranch`.
- **Do not retire the legacy `--tier-extra/unique/ultimate` tokens** until every consumer migrates; add/keep aliases, migrate, then retire in a follow-up commit.
- **Do not edit META.md, CONTEXT.md, or `docs/meta/2026-06-trust-methodology.md`** — prose track (#994, landed). Editing re-triggers the #999 guard.
- **Do not touch Hermes-managed files** (`docs/agent.md` and siblings per CLAUDE.md) without coordinating.
- **Do not delete/rename banned words inside deprecation notices** on guard-enforced surfaces — keep migration references in guard-excluded surfaces (`docs/**/*.html`, `scripts/**`) or coordinate an allowlist entry.
- **Archival reports** under `docs/meta/reports/` and dated `docs/audits/` are historical record — flag before changing; a dated report describing the old taxonomy at the time is not necessarily wrong.

---

## 7. Worker fan-out plan — RATIFIED EXECUTION ARCHITECTURE (2026-07-17, "Full Gas")

**Mode:** end-to-end autonomous implementation via recoverable dynamic `/workflows`. Goal: design fully integrated into `dev/yggdrasil-ii-staging`, **no follow-ups**, no Ygg-I legacy design surviving (new plaques + avatars everywhere, zero red-origin icons, zero `extra`/`ultimate`/`unique` type-enum reads).

### Global execution invariants
- **Commit identity:** `mbtiongson1` — every worker sets `git -c user.name="Marcus Rafael B. Tiongson" -c user.email="153011150+mbtiongson1@users.noreply.github.com"`. Verify `git log --format='%ae'` before every push. **Nothing else.**
- **Concurrency:** **Wave 0–1:** MAX 2 concurrent workers; MAX 1 if opus (batch `parallel([a,b])` pairs, opus stages solo). **Wave 2 onward (founder ruling 2026-07-17):** MAX 4 concurrent sonnet; MAX 2 concurrent opus (opus only if needed). Never mix so that >2 opus or >4 sonnet run at once; a mixed batch counts opus against the 2-cap first. The workflow concurrency cap is min(16, cores-2), so 4-wide sonnet fans are within the engine limit.
- **Worktrees:** every implementation agent runs `isolation: "worktree"`, branches from `origin/dev/yggdrasil-ii-staging`, commits+pushes its feature branch per logical unit, reports SHAs. Never batches pushes.
- **Review-gate:** every lane is followed by an **adversarial reviewer agent** (reject-by-default, grades against `DESIGN.md` §"Yggdrasil II Enforcement Rubric"). Fail → ONE bounded remediation retry → re-review. Structured verdict returned.
- **PR lifecycle stays in orchestrator hands (recoverable):** workflows implement + push + review-gate + return a manifest. **The orchestrator opens each PR → `dev/yggdrasil-ii-staging` and merges** between waves (idempotent GitHub mutations; a crashed workflow never leaves a half-merged PR). Merge order = dependency order (foundation first).
- **Recoverability:** one workflow per WAVE. Each is resumable via `resumeFromRunId` (same script+args → cache hit on completed agents). Anticipate a lane dying mid-run; the worktree + pushed commits survive, and the workflow journal (`journal.jsonl`) records every agent return. On failure: resume the wave workflow, or re-dispatch a continuation agent pinned to the surviving worktree.
- **Inspect always:** Playwright 1.61.1 is available. Reviewer agents serve `docs/` locally (`python -m http.server`) and screenshot the target surface at desktop (1280) + mobile (390) before returning a verdict.
- **Assets:** use existing AOV4 (C1–C6 suite, D4–D6 unique, ×badge/card/hero — COMPLETE). Author the missing **gold-wreath frame SVG** in W0. Every created/modified asset + every decision logged to `founder/YGGDRASIL_II_DESIGN_LEDGER.md`.
- **Regen policy:** prefer the Python design scripts (`generateBadges.py`, `generateOgCards.py`, `generateProfilePages.py`, `build_docs.py`) over hand-editing generated output. Revert Class-P timestamp noise before committing.

### Wave sequence (dependency-ordered)

**WAVE 0 — Foundation (opus, effort high, SOLO). Keystone; everything imports it.**
- Promote `--tier-unique` (#7c3aed) to a full token family in `docs/css/tokens.css` (+`-rgb/-bg/-border/-edge/-symbol`), via `generateCssTokens.py` if it sources the value, else direct. Kill hex fallbacks at usage sites.
- Extract shared client resolver `computeBranch(node, effRank)` + `rankWord(level, branch)` into a new `docs/js/skill-semantics.js` (source: `world-tree-layout.js resolveSemantics` L356-413). Load it before all consumers.
- Author gold-wreath frame SVG (`docs/assets/origin-wreath-gold.svg`) — replaces the honor-red `#origin-badge`.
- Rewrite `docs/js/plaque.js`: stamp derived `data-branch`; `_fieldOrb`→AOV `<picture>` (C/D by branch, rank→index, size→badge/card/hero); add avatar + gold-wreath + medallion with **GitHub-blank identicon fallback**; dark(unique)/gold(suite) split re-keyed to `data-branch`; drop the standalone GitHub button (avatar links to repo); remove red origin mark. Fixes 8 of 16 surfaces.
- Reviewer (opus, adversarial) → orchestrator merges PR-0 to dev.

**WAVE 1 — Surface fixes (import foundation; sonnet 2-at-a-time, Python lane opus-solo). Each own PR, review-gated.**
- **W1a (sonnet, med):** `docs/heroes/heroes.js` — kill live `[dep-5★]`/`[dep-4★]` (`getTierMarkLabel`/`classifyTier`/`TIER_LABEL` L44-118); branch-fork 4-6★ ladder via shared resolver; avatar GitHub-blank fallback; HoH `/heroes` shows correct 4-6★.
- **W1b (sonnet, med):** `docs/trust/leaderboard/leaderboard.js` — `RANK_NAMES` L47-49 + tooltip L2350 banned words; `TYPE_COLORS` L153-157; origin laurel glyph L326/1091/1548/1751 → gold.
- **W1c (sonnet, med):** `docs/named/index.html` filter tabs L96-99 → Fusion/Basic; `docs/js/named-skills.js` rank-grouping (buckets L141/151/256/530 → rank integers; branch = C/D visual variant within group).
- **W1d (sonnet, med):** `docs/js/skill-explorer.js` — N-5 flow suite/ultimate tabs (reuse existing tab affordance) + plaque z-index overlap; SE-3 install-flag fix (L827 `level==='5★'` conflation); **N-11** shared "Research product CTA" (skill-fuse page + `github.com/gaia-research/skill-fuse` repo, Rimuru-Blue bridge) on every fuse/suite section.
- **W1e (opus, high, SOLO):** Python design scripts branch-aware — `generateBadges.py` (`RANK_NAMES` L54-57 + honor-red→gold), `generateOgCards.py` (dispatch L157-170 on computeBranch+rank, banned words L652-658, all-rank×2-branch plates), `generateProfilePages.py` (kills N-3 frozen `data-type`/`data-level` + branch aria). Regenerate outputs. **Badge `_assets/` regen is a SEPARATE `infra/badge-*` PR** per invariant.
- **W1f (sonnet, low):** copy/CSS — **N-9** MCP sweep (`@gaia-registry/mcp-server`→`@gaia-registry/mcp@0.1.0` + `research.gaiaskilltree.com/mcp` across `docs/index.html`×2, `docs/en/index.html`, `docs/en/mcp-server.html`, `docs/agent.md`, README); **N-1** shared `.aov-terminal-art` edge treatment (both terminals); **N-2** hero install-card grid alignment.

**WAVE 2 — /impeccable design items (reviewer-gated, no founder gate per R4). Concurrency: up to 2 opus concurrent (new ruling).**
- **W2a (opus, high):** N-8 OG card `/impeccable` composition on top of W1e's fixed dispatch — embed AOV `-hero` art, reshape, all-rank. Reviewer picks shape.
- **W2b (opus, high):** N-10 footer redesign + Gaia Research CTA cross-brand ("one house, two rooms," Rimuru-Blue #38bdf8 bridge) in `docs/js/site-footer.js` + `styles.css`.
- **W2c (opus, high):** N-7 `docs/reports/` + `docs/named/report.html` shared report design system. **NOT `docs/meta/reports/`.**
- **Run shape:** W2a+W2b as one opus pair (both independent surfaces); W2c opus-solo after (or paired if a 4th sonnet-class item joins). Each own PR, adversarial-reviewer-gated (reviewers may be sonnet, so a review pass can run 4-wide if batched).

**WAVE 3 — Capstone N-12 (mixed; critique fans 4-wide sonnet, remediation opus-as-needed, DESIGN.md opus-solo).**
- Critique scout inventories mobile/responsive state of all non-homepage surfaces.
- Adversarial critique agents grade each non-homepage surface vs DESIGN.md rubric — **up to 4 sonnet concurrent (new ruling)**.
- Remediation agents make flagged surfaces mobile-first (homepage FROZEN except N-1/N-2) — sonnet 4-wide, opus ≤2 only for the hardest layout reworks.
- Finalize `DESIGN.md` as the solidified impeccable-init standard; complete `founder/YGGDRASIL_II_DESIGN_LEDGER.md`.

### Workflow files
- Per-wave scripts persisted under the session dir; `scriptPath` recorded in the ledger for resume.
- Args carry the base branch + commit identity so scripts stay `Date.now()`-free and resumable.

---

## 8. LIVE NITPICK LOG (2026-07-17 design pass)

Every reported issue lands here with: source anchor, pattern check, planned fix. **No fix is written until the plan is ratified.**

### N-1 · Homepage — "Unique Impossible" AOV terminal renders a hard black rectangle
- **Source:** `docs/index.html` L1069-1093 (the `aov-rail--unique aov-rail--terminal` article); CSS `docs/css/ascension-overdrive-v4.css` `.aov-terminal-art--impossible` (L547-550), `.aov-terminal-art` (L532-545).
- **Diagnosis:** the terminal art is a full-bleed raster webp (`aov4-unique-impossible-terminal.webp`, 3840×2160 = 16:9) of light nebula on a **black canvas**, forced into an `aspect-ratio:1.5` box with `object-fit:contain`. On the dark section the webp's own black background reads as a hard-edged rectangle/seam — the screenshot's "black rectangle."
- **PATTERN (confirmed):** this is NOT a one-off. The **sibling Suite Apex terminal** (`docs/index.html` L1045, `aov-rail--suite aov-rail--terminal`) uses the same `.aov-terminal-art` mechanism with its own raster art. Any fix (edge mask / radial-gradient fade / `mix-blend-mode: screen` to drop the black onto the dark bg / crop via `object-fit: cover`) MUST be applied to the shared `.aov-terminal-art` rule so both terminals resolve, not just the impossible card. Also verify the responsive dupes at v4.css L865-878, L1017-1052, L1129-1163.
- **Planned fix (candidate, unratified):** apply a soft edge treatment on the shared `.aov-terminal-art` (radial/linear alpha mask feathering the raster into the section bg) so no card shows a hard rectangle; if the art is truly black-backed, `mix-blend-mode: screen` or `lighten` may be the cleaner kill since the section is dark. Decide against both terminals together. Marcus said "you decide how" → orchestrator to recommend one approach in the ratified plan.

### N-2 · Homepage — Hero "Install the Gaia CLI" card mis-aligned
- **Source:** `docs/index.html` L359-374 (`.hero-tree-action--primary .hero-tree-install`); CSS `docs/css/world-tree-hero.css` `.hero-tree-install-copy` (L372-377: `grid-template-columns: minmax(0,1fr) auto`), `.hero-tree-action--primary` (L333-343), `.hero-tree-install-platforms` (L385-388).
- **Diagnosis (to confirm in plan):** `.hero-tree-install-copy` is a 2-col grid but holds THREE children (`<strong>` title, `.hero-tree-install-platforms` toggle, `.hero-tree-install-command`). The title and the curl/iex toggle land on the same row via auto-placement, and the toggle (right-aligned `auto` col) sits at a different baseline than the title — the screenshot shows the title and toggle not sharing a clean baseline / the toggle floating high-right. Needs explicit grid-area placement or an aligned flex row for title+toggle.
- **PATTERN check:** the primary action card is unique (only one `--primary`), but the sibling action cards (`Submit a skill`, `Get a README badge`, L375-388) share `.hero-tree-action` grid DNA. Confirm the fix is scoped to the primary card's internal grid and does NOT regress the two ghost cards' glyph/label alignment. Also check the mobile breakpoints (world-tree-hero.css L916+, L962+, L1160+).
- **Planned fix (candidate, unratified):** give `.hero-tree-install-copy` explicit rows (title+toggle on row 1 sharing a baseline via `align-items:center`, command on row 2 spanning both cols) OR restructure title+toggle into their own flex row. Ratify exact approach after reading the responsive rules.

### N-8 · Share / OG card (`docs/og/<handle>/<slug>.svg` via `generateOgCards.py`) — /impeccable reshape + AOV assets + all-rank logic
- **Source:** `scripts/generateOgCards.py` (915 lines) generates `docs/og/{handle}/{skillId}.svg`; loaded into the fullscreen modal by `docs/heroes/hero-share.js` L33 (`ogPath: 'og/'+handle+'/'+slug+'.svg'`). The screenshot's chrome — protractor RA/Dec ticks `+20° +10° 0° −10° −20°` (`_radec_ticks` L252-257), "Cataloged by @ruvnet · ORIGIN · 2026", `MAG 482.3 · GRADE S · ★★★★★ · GAIA · 2026` footer, bare **"Basic·Skill"** label top-right — is this SVG. The red arrow points at the **empty art region** (the vast dead center-right zone).
- **Three founder directives:**
  1. **`/impeccable` reshape.** Run the `/impeccable` skill (project skill, confirmed at `.claude/skills/impeccable/`) to redesign the card shape/composition; a reviewer inspects the shape and decides. This is a design-quality pass, not a mechanical edit.
  2. **In line with new AOV assets.** The empty art region should carry the AOV V4 stamp (Asset C suite / Asset D unique) matching the skill's branch+rank — same asset set as N-4 plaques and the homepage `#ascension` rail. Ties the card into the unified visual language.
  3. **Logic for ALL ranks.** Currently `generateOgCards.py` has only **4 plate compositions** (L11-14): Plate VI Apex Supernova (6★), Plate V Stellar (5★ `type="ultimate"`), Plate IV Singularity (`type=unique`), and a **minimal default fallback for basic/extra** — the screenshot IS that barren fallback (ruflo is rendered "Basic·Skill" with no art). Every rank 1-6 across BOTH branches (suite + unique) needs a proper composition, not a fallback dead-zone.
- **PATTERN (this is the SAME defect cluster as §4.2 + N-6, now on the OG surface — highest-leverage single fix):**
  - **Type-dispatch bug:** plate selection keys on `resolve_type_for_og()` (L157-170) which returns the DEPRECATED enum `basic/extra/ultimate/unique`. Post-migration canonical `type` is only `basic/fusion` → `ultimate`/`unique`/`extra` **never resolve**, so EVERY named skill now falls to the minimal "basic/extra" fallback plate — that's exactly why a MAG-482 GRADE-S 5★ skill like ruflo renders as a bare "Basic·Skill" with an empty card. **This is not just ruflo — every OG card is currently broken to the fallback.** Fix: dispatch on `computeBranch` + rank (§4.1 canonical source), not `type`.
  - **Banned-word bug (already logged §4.2):** `rank_words` L652-658 bakes `HARDENED`/`TRANSCENDENT ★` into SVG `<text>`. Same branch-aware ladder fix as N-6/§4.
  - **"Basic·Skill" bare label:** top-right type label uses the type word — must become the branch-forked rank label (a 5★ suite reads "Ultimate", a 4★ unique reads "Unique"), never "Basic·Skill" for a graded skill.
- **All-rank asset coverage:** Asset C = 6 suite ranks × 3 sizes, Asset D = 3 unique ranks × 3 sizes (§5). The OG card is a large surface → `-hero.webp` size. Map `computeBranch`→C/D series, rank→index. Note: OG SVGs embed art via `<image xlink:href>` or inline; embedding an external `.webp` in a standalone SVG needs either a data-URI (large) or a same-origin relative href (works when served from Pages) — decide in the /impeccable pass.
- **Guard/branch-scope note:** `generateOgCards.py` is `scripts/**` (guard-excluded, Lane C) and its output `docs/og/**` is tracked. Like N-6 badges, regenerating all `docs/og/*/*.svg` is a bulk artifact commit — decide whether it rides the script PR or a separate regen commit. Per CLAUDE.md, `docs/og/**` PNGs are an exempt tracked-binary path.
- **Planned fix (candidate, unratified):** (1) `/impeccable` design pass on the card composition (reviewer-gated per founder); (2) rewrite plate dispatch in `generateOgCards.py` to `computeBranch`+rank with a composition for all 6 ranks × 2 branches (kills the fallback dead-zone); (3) embed AOV C/D `-hero` art in the art region; (4) branch-aware rank labels + kill banned words (folds N-6/§4.2). **Largest functional+design item.** Its own Lane (D-ogcard), sequenced after §4.1 resolver + §5 asset mapping. Recommend the /impeccable pass produces a single reference plate for reviewer sign-off BEFORE generating all ranks.

### N-9 · MCP relocated to adjacent `gaia-research/gaia-mcp` — stale install instructions site-wide
- **Source (the flagged surface):** `docs/index.html` L697-703 — homepage Quick Start step IV "Bond your agent": command `claude mcp add gaia -- npx @gaia-registry/mcp-server` + tip linking `packages/mcp` (`https://github.com/gaia-research/gaia-skill-tree/tree/main/packages/mcp`).
- **Ground truth (Discipline B — canonical is `origin/main:README.md`, NOT this staging branch):** `origin/main` README §4 (L242-248) already carries the NEW shape:
  - Command: **`claude mcp add gaia -- npx -y @gaia-research/mcp@0.1.0`** (was `npx @gaia-registry/mcp-server`)
  - Package: **`@gaia-research/mcp`** in the **adjacent `gaia-research/gaia-mcp` repo** (was `@gaia-registry/mcp-server` bundled in this repo's `packages/mcp/`)
  - Docs link: **`https://research.gaiaskilltree.com/mcp`** (was `packages/mcp/` config examples)
  - ⚠️ **staging's own README is BEHIND main here** (still shows `@gaia-registry/mcp-server`) — a merge-main-into-staging concern, NOT this nitpick. Use `origin/main` as the copy source.
- **PATTERN (confirmed — site-wide, not one homepage line):** `@gaia-registry/mcp-server` + `packages/mcp` references are scattered across the whole docs surface, ALL stale:
  - `docs/index.html` L697-703 (the flagged step IV) — command + `packages/mcp` link.
  - `docs/en/mcp-server.html` — **~15 hits**: page-badge L547 (`@gaia-registry/mcp-server · v6.4.12`), intro L560/578/588, all config JSON blocks L612-777 (`"args":["@gaia-registry/mcp-server"]` ×7 for Claude/Cursor/VS Code/etc.).
  - `docs/en/index.html` L486-489 (docs-card → `mcp-server.html`, describes `@gaia-registry/mcp-server`).
  - `docs/en/faq.html` L297/900, `docs/en/timeline-audit.html` L1019, `docs/js/site-nav.js` L171 (nav label → `mcp-server.html`).
  - `docs/en/cli-reference.html` L1738 (`cd packages/mcp && npm run build` — now an external repo, this build step is wrong).
  - **Decision for the plan:** does `docs/en/mcp-server.html` stay as an on-site page (rewritten to point at `@gaia-research/mcp` + the adjacent repo + `research.gaiaskilltree.com/mcp`), or does it become a redirect to the new external docs? The homepage `packages/mcp` link and cli-reference build step definitely change; the standalone MCP doc page is the open question.
- **Branch-scope/ownership:** all touch points are `docs/**/*.html` + `docs/js/` → Lane B (copy sweep), design-branch-legal. README itself is founder-owned (superadmin) but is a SEPARATE concern — staging README should get main's MCP content via the normal merge-main-into-staging, not hand-patched in this design pass.
- **Planned fix (candidate, unratified):** (1) `docs/index.html` step IV → new command + link to `research.gaiaskilltree.com/mcp` (or the adjacent repo); (2) sweep all `@gaia-registry/mcp-server` → `@gaia-research/mcp` and `packages/mcp` → adjacent-repo/new-docs across the docs surface; (3) rewrite or redirect `docs/en/mcp-server.html`; (4) fix `cli-reference.html` build step; (5) cache-bust touched HTML pages. Lane B. FLAG the mcp-server.html keep-vs-redirect decision for ratification.

### N-10 · Footer redesign + Gaia Research CTA — cross-brand reconciliation (/impeccable, reviewer-picks-variation)
- **Source:** `docs/js/site-footer.js` (120 lines, single source of truth, mounts into `#site-footer-mount` on every page). Brand col L29-37 (`footer-brand-mark` seal + `Gaia` wordmark + tagline "An evidence-backed atlas of agent capabilities"). Six nav cols L41-99 (Registry/Discover/Evidence/Docs/Contribute/About). Bottom strip L107-115 ("Gaia Registry · GitHub · Privacy"). Styles: `docs/css/styles.css` (`.footer-v2`/`.footer-brand-*`). The red box in the screenshot targets the brand col (bland, under-designed).
- **Two founder directives:**
  1. **Gaia Research CTA — "find a place where we can put this nicely."** Add a visible CTA to **research.gaiaskilltree.com**. **Framing (verified from adjacent `../gaia-research/`):** Gaia Research is *"the open research collective behind the Gaia Skill Tree"* (PRODUCT.md L25); the Skill Tree is its **flagship**. Currently the ONLY reference on-site is a `"name":"Gaia Research"` string in index.html's **JSON-LD (L264)** — invisible schema.org metadata, no user-facing link. The CTA must express the parent→flagship relationship.
  2. **Footer /impeccable — "highlight Gaia AND Gaia Research somehow where it is obvious that both are Gaia."** Run `/impeccable`; a reviewer agent checks the shape and picks the variation. The footer brand col should visually bind the two brands as one family.
- **CROSS-BRAND RECONCILIATION (the hard part — two DISTINCT design languages, verified in both DESIGN.md files):**
  - **gaia-skill-tree = "The Hunter's Atlas"** — scholarly serif (EB Garamond) + retro pixel (Departure Mono), amber/gold diamond seal `#fbbf24`, obsidian bg. (This repo's DESIGN.md.)
  - **gaia-research = "The Cyber-Slime Laboratory"** (`../gaia-research/DESIGN.md`) — **Bebas Neue** (ultra-condensed display) + **Syne** (expanded brand wordmark) + **Manrope** (body) + **DM Mono**; **Milim Pink `#ec4899`** + **Rimuru Blue `#38bdf8`** on deep obsidian `#05060a`; sharp 1px grids, 2px/0px corners, LED spark lights, offset-shadow tactical buttons.
  - **Shared DNA to lean on:** both use obsidian-midnight backgrounds; Rimuru Blue `#38bdf8` == this repo's `--tier-basic` `#38bdf8` (exact match — a natural bridge color); both are "premium streetwear portal" energy. The seal/hex-lens motif is common ground.
  - **The reconciliation:** the footer should read as "one house, two rooms." Candidate approach — keep the Atlas footer in its serif/gold language, but introduce a **Gaia Research brand lockup** rendered in ITS OWN language (Syne wordmark + Milim-Pink/Rimuru-Blue accent) as a distinct-but-sibling block, with connective copy ("Gaia Skill Tree is the flagship registry of **Gaia Research**"). The `/impeccable` pass produces 2-3 variations of how the two brand marks coexist; the reviewer picks. Do NOT wholesale-import Cyber-Slime tokens into every footer element (that would break the Atlas identity) — the point is *legible kinship*, not merger.
- **Cross-repo rule (respect it):** `../gaia-research/README.md` L54 — *"Nothing from gaia-research is committed directly into gaia-skill-tree."* That governs **content/schema** flow, not a hyperlink or a sibling brand lockup on our own footer. We may reference the brand, link the portal, and echo its wordmark styling; we do NOT copy its content files in. If we need its exact font stack, load the same Google Fonts (Syne) in our own CSS rather than importing their files.
- **PATTERN:** `site-footer.js` renders on EVERY page (fallback dir-list L11-15 mirrors `mounts.js`) → one edit propagates site-wide, no per-page work. The CTA placement choice (footer brand col vs a dedicated footer row vs the bottom strip) is the design decision. Also consider: a subtle Research CTA could live on the homepage hero/`#ascension` end too, but the footer is the "logical, always-present" home the founder pointed at.
- **Planned fix (candidate, unratified):** (1) `/impeccable` pass on `site-footer.js` brand col + `styles.css` `.footer-v2`, producing 2-3 variations of the Gaia⇄Gaia-Research lockup + a `research.gaiaskilltree.com` CTA; (2) reviewer agent (`/design-review` or a scout+opus judge) inspects shapes and picks; (3) load Syne (+ optionally Bebas Neue) webfont for the Research wordmark; use `#38bdf8` as the bridge accent (already `--tier-basic`); (4) connective tagline naming the flagship relationship; (5) cache-bust. Lane D (its own footer sub-lane). Design-branch legal (all `docs/`). Reviewer-gated per founder.

_Further nitpicks appended below as Marcus sends them._

### N-3 · About page — stale star counts + missing Unique branch styling
- **Source:** `docs/about.html` — three `.rank-slot` spans with hardcoded `data-level`: L1054 pbakaus/Impeccable `data-level="4"`, L1069 mattpocock `data-level="6"` (`data-aria="Apex, rank 6 of 6"`), L1084 garrytan/gstack `data-level="5"` (`data-aria="Ultimate Skill, rank 5 of 6"`).
- **Ground truth (verified against canonical badge assets):** `docs/badges/_assets/mattpocock/rank.svg` renders **"[dep-5★] · 5★"** → mattpocock is canonically **5★**, so L1069 `data-level="6"` is a **stale hardcode**, not a data question. Fix: `6→5`. Impeccable (pbakaus) is already `data-level="4"` — the ask is it must read as **4★ Unique** (branch label + violet styling), the number is already right. garrytan/gstack at 5★ suite is correct.
- **PATTERN (confirmed):** the About cards are hand-authored static HTML with `data-level` + `data-aria` frozen at authoring time — they do NOT read the registry, so any canon rank change silently drifts. Same frozen-HTML pattern likely on other narrative pages (`docs/heroes/index.html`, `docs/u/*/index.html` profile pages). Fix scope: correct the numbers on About, AND grep every hand-authored `data-level`/`data-aria="…rank…"` across `docs/**/*.html` for other frozen values that disagree with canon. Also: `data-aria="Apex, rank 6 of 6"` / `"Ultimate Skill, rank 5 of 6"` embed the RANK WORD in the aria label — those must match the branch-forked ladder (a 4★ Unique's aria must say "Unique", not "Extra").
- **Data-file caution (CLAUDE.md):** star levels live in slots, not skill objects; About's numbers are display copy, NOT a data file — safe to edit directly. Do NOT touch `skill-trees/` or registry data to "fix" this.
- **Planned fix (candidate, unratified):** (1) `docs/about.html` L1069 `data-level="6"→"5"` + aria "Apex, rank 6 of 6"→"Ultimate, rank 5 of 6"; (2) pbakaus card gets Unique-branch treatment (violet token + "Unique" aria) — depends on §3.3 token decision; (3) sweep other frozen `data-level` pages for drift. Lane B (copy) + coordinates with Lane D (branch tokens).

### N-4 · Named Skills (`docs/named/`) — deprecated filters, branch-grouping, plaque redesign
- **Source:** `docs/named/index.html` L96-99 filter tabs `data-type="ultimate|unique|extra|basic"` (glyphs ◆◉◇○); `docs/js/skill-explorer.js` + `docs/js/named-skills.js` grouping (Scout #1 NS-2/NS-4/NS-9); `docs/css/plaque.css` `.plaque-orb--*` gradient orbs (L617-656); plaque header markup.
- **Four sub-directives (all confirmed patterns, not one-offs):**
  1. **Filter chips → new schema.** L96-99 expose deprecated `ultimate/unique/extra` as filter facets. New TYPE axis is **Fusion / Basic** only. Replace the four `data-type` tabs with two (Fusion, Basic). NOTE: this conflicts with a pure rank-grouping (see #2) — if we group by rank, the *type* filter and the *rank* grouping are orthogonal; likely keep All + Fusion + Basic as type filters, and rank as the grouping axis.
  2. **Group by RANK not branch.** Currently `named-skills.js` buckets by `type` into `{apex,ultimate,unique,extra,basic}` (NS-2 L141, NS-4 L151, NS-9 L694). New grouping is **by rank tier: 6★ / 5★ / 4★ … regardless of branch** (a 6★ Apex suite and a 6★ Unique Impossible sit in the same "6★" group). Re-key buckets to rank integers; within a rank group, branch is a visual variant (Asset C vs D), not a separate bucket.
  3. **Plaque orb → Asset C/D image.** Replace `.plaque-orb--basic/extra/unique/ultimate` CSS gradient (plaque.css L617-656) with the actual `aov4-c*` (suite) / `aov4-d*` (unique) WebP stamps — this is the **§5 Lane D integration**, now with an explicit surface. Branch picks C vs D via `computeBranch`; rank picks the `-cN`/`-dN` index; size picks `-badge/-card/-hero`.
  4. **GitHub avatar + GOLD origin wreath, avatar links to repo, REMOVE GitHub button.** Add a fetched GitHub avatar image for the contributor; wrap it in an "origin wreath" ornament rendered in **GOLD** (honor-red `#ef4444` is DEPRECATED for origin — see N-6, same deprecation). Clicking the avatar navigates to the repo (`links.github`). Delete the standalone "GitHub" button from the plaque.
- **PATTERN (explicit founder directive):** *"find patterns that use the plaque in every area — these should acquire the same language."* The plaque is rendered/referenced across **40+ surfaces** (grep: `docs/about.html`, `docs/badges/`, `docs/codex.html`, `docs/evidence/`, `docs/heroes/`, `docs/index.html`, `docs/js/{plaque,named-skills,skill-explorer,skill-graph,profile-*,atlas-helpers,hoh-modal,page-ia}.js`, `docs/named/`, `docs/samples/*`, `docs/trust/leaderboard/`, `docs/u/*/`, `docs/starless.html`). The canonical renderer is **`docs/js/plaque.js`** (`renderMiniStack` L621, `renderHall` L693) — fixing the plaque there propagates to most surfaces. Orb→asset, avatar-wreath, and button-removal must land in the shared renderer, then audit each consuming surface.
- **Planned fix (candidate, unratified):** central `plaque.js` rewrite (orb→`<picture>` Asset C/D, add avatar+gold-wreath, drop GitHub button) + `named-skills.js` rank-grouping + `named/index.html` two-facet filter. Largest single workstream — its own Lane (D-plaque), sequenced after the §3.3 token decision + §5 asset-size mapping ratify. Avatar fetch: decide static-cache vs runtime `https://github.com/<handle>.png` (runtime is simplest; static avoids GitHub rate-limit and works offline).

#### N-4 EXPANSION (Scout #2, 2026-07-17) — full cross-surface inventory

The directive widened: **every** skill-rendering surface must (a) read the new schema correctly, (b) show a GitHub avatar with a GOLD wreath frame + medallion, falling back to GitHub blanks, (c) deprecate the red origin mark, (d) distinguish unique (DARK plaque) from suite (GOLD plaque), and (e) HoH `/heroes` must show 6★→4★ with correct ladder. Scout #2 mapped 16 surfaces. Key structural finding:

- **`docs/js/rank-badge.js` is 100% CLEAN** — renders only `N★` chips + star glyphs, no rank words, no `type` reads. Every banned-word / dead-enum bug lives in CALLERS that bypass it or feed it stale `tier`/`type`, or in bespoke label maps. Keep rank-badge.js as the sole star-glyph authority; route all rank-WORD text through a new shared branch-aware `rankWord(level, branch)` helper.
- **`docs/js/world-tree-layout.js resolveSemantics()` (~L356-413) is the ONLY correct client branch resolver.** No other file has it. It must be extracted into a shared client helper (`computeBranch`) that plaque.js, heroes.js, named-skills.js, leaderboard.js, skill-explorer.js all import. This is the single-point fix for the whole schema-read defect class.

**Surface inventory (16 surfaces):**

| Surface | File:line | Avatar | Schema-read | Rank display | Unique/suite |
|---|---|---|---|---|---|
| HoH hero card | `heroes.js` renderStage L215-269 | Y `github.com/<h>.png` no-blank-fallback | **BUG** `topSkill.type` dead enum | **BANNED, LIVE** `getTierMarkLabel` emits [dep-5★]/[dep-4★] | by dead `type` |
| HoH ledger rail | `heroes.js` renderLedgerRail L294-305 | Y no-blank-fallback | **BUG** `topSkill.type` | glyph via dead type; `level` text OK | no |
| HoH hall plate | `plaque.js` renderHallPlate L690-812 | Y `.png?size=160` onerror→ring, no identicon | **BUG** `TYPE_RANK`/`TIER_GLYPH` dead keys | stars correct (rankBadge) | CSS `[data-type=unique]` dead |
| Explorer modal hero | `plaque.js` renderDetail L473-540 | **N** | orb `plaque-orb--<type>` dead | stars correct | orb dead `type` |
| Explorer grid tile | `plaque.js` renderTile L427-445 | **N** | `_fieldOrb(ns.type)` dead | chip correct | orb dead |
| Explorer list row | `plaque.js` renderRow L450-468 | **N** | `ns.type` | chip correct | orb dead |
| Profile trophy card | `plaque.js` renderSettled L544-571 | **N** | `ns.type` | chip+stars correct | orb dead |
| OG HTML mock | `plaque.js` renderOg L585-605 | **N** (seal glyph) | `ns.type` | full correct | orb dead |
| HoH mini-stack | `plaque.js` renderMiniStack L618-677 | **N** | **BUG** `TYPE_RANK`/`TIER_GLYPH` dead | stars correct | glyph dead |
| Named filter tabs | `named/index.html` L95-99 | n/a | **BUG** `data-type="ultimate"\|unique\|extra\|basic` deprecated facets | tab labels dead enums | exposes dead enums |
| Named grouping | `named-skills.js` L141/151/256/530 | via plaque | **BUG** buckets `{apex,ultimate,unique,extra,basic}` empty post-migration | groups by dead type | by dead type |
| Skill flowchart | `skill-explorer.js` L1368/1445/1482/1819 | N | **BUG** `type==='unique'` dead | dots by `--tier-*`; isApex via level OK | `--tier-unique` dead |
| Explorer install flag | `skill-explorer.js` L827-828 | n/a | **BUG (SE-3)** `level==='5★'` conflates suite-5★ w/ Unique Ultimate | `◆ ultimate suite` mislabels Unique | mislabels |
| Leaderboard charts | `trust/leaderboard/leaderboard.js` | Y SVG `<image>` no-blank-fallback | **BUG** `RANK_NAMES` L47-49 [dep-4★]/[dep-5★]; `type` pills | **BANNED, LIVE** tooltip L2350 | type-color gradients dead |
| Profile timeline | `profile-timeline.js` L152-160/273-294 | N | **BUG** `.ptl2__dot--extra/unique/ultimate` + hex fallbacks | chips | `--unique` dark vs others, dead |
| About name cards | `about.html` L1054/1069/1084 | N (text link) | frozen `data-level` (N-3); L1069 stale | rankBadge correct; aria embeds words | none |

**B. Avatar propagation pattern (reusable):** cleanest is `plaque.js` renderHallPlate L723-725 — `'https://github.com/'+handle.replace(/^@/,'')+'.png?size=160'`, `referrerpolicy="no-referrer"`, `onerror`→`data-crest-fail`. **GAP: NO surface falls back to a GitHub blank/identicon** — every `onerror` HIDES the img (empty hole). Directive wants a real GitHub-blank silhouette fallback. Surfaces MISSING avatars entirely: renderDetail (the primary modal!), renderTile, renderRow, renderSettled, renderOg, renderMiniStack, profile-timeline.

**C. Red-origin kill list:** the "origin" mark = `icon('origin-badge')` laurel sprite (`docs/assets/icons.svg` L180-181) rendered honor-red via currentColor. Kill points: `plaque.js` `_fieldOriginBadge` L172-180; `icons.svg` `#origin-badge` L180-181; leaderboard laurel glyph L326/1091/1548/1751; `about.html` honor-red L132/535/846-855; `badges/index.html` `#ef4444` L233/304/347/495/537-538. **CAUTION:** `--honor-red` (styles.css) has 70+ consumers for links/emphasis — the kill is ONLY the origin mark → GOLD, NOT a blanket honor-red purge.

**D. Wreath + medallion assets — MISSING, must be created:** `find -iname '*wreath*'` = **0 files**. No golden-wreath frame asset exists. No CSS composes a wreath over an avatar. Medallion = pure CSS orb gradients (plaque.css L617-656), zero raster. **BUT** AOV V4 stamp set IS present + unused: `docs/assets/ascension-overdrive/` has Asset C (`aov4-c1..c6-suite-*`) + Asset D (`aov4-d4/d5/d6-unique-*`) × badge/card/hero — the intended medallion art, not yet wired into any plaque. Net-new work: (1) create a gold-wreath frame SVG/WebP; (2) CSS to compose wreath-over-avatar everywhere; (3) wire AOV C/D into the orb slot.

**E. HoH `/heroes` rank ladder — BANNED words rendered LIVE** (`heroes.js getTierMarkLabel` L89-116): 5★→`[dep-5★]` (L108), 4★→`[dep-4★]` (L115), plus `Ultimate · [dep-5★]`/`Extra · [dep-5★]`/`[dep-4★] · Extra` composites. `classifyTier` L76 returns `'transcendent'`; `TIER_LABEL.transcendent` L47. HoH filters level≥4 so only 4/5/6 rows show — **all wrong for at least one branch.** Correct ladder: suite {6 Apex, 5 Ultimate, 4 Extra}; unique {6 Unique Impossible, 5 Unique Ultimate, 4 Unique}. Also `leaderboard.js` tooltip L2350 renders the same banned `RANK_NAMES` on hover.

**F. Unique-vs-suite visual gap:** the dark/gold distinction EXISTS in CSS but is keyed on the dead `type` enum so it never activates: `plaque.css` L641-648 `.plaque-orb--unique` (dark) vs L633-640 ultimate (gold); L1302-1322 hall rows; `profile-timeline.js` L154; `heroes.css` L529/535. Must re-key to derived branch → `data-branch="unique|suite|standard"`, replacing every `[data-type=unique|ultimate|extra]` selector. renderTile/Row/Settled/Detail currently render 4★ Unique and 4★ Extra IDENTICALLY.

**G. Single-point-fix concentration (ratified target):**
1. **Extract shared `computeBranch`** from `world-tree-layout.js resolveSemantics()` → import everywhere. Kills the schema-read defect class at the root.
2. **`plaque.js` `_shell` (L362-388)** — stamp derived `data-branch`; **`_fieldOrb` (L90-96)** → AOV `<picture>`; add avatar+gold-wreath+medallion here → propagates to 8 of 16 surfaces.
3. **`heroes.js` (L44-118)** — standalone banned-word source, NOT routed through plaque.js for hero-card/ledger; fix `getTierMarkLabel`/`classifyTier`/`TIER_LABEL` directly.
4. **`leaderboard.js` (L47-49, L153-157, L2350)** — standalone `RANK_NAMES`/`TYPE_COLORS`; own fix.
5. **rank-badge.js stays clean**; stop feeding it `tier: type` (plaque.js L150/659/785); add shared `rankWord(level, branch)`.

**Lane assignment:** this is the biggest workstream — split into **D-plaque** (plaque.js central: avatar/wreath/medallion/orb→AOV/data-branch), **A-heroes** (heroes.js ladder + avatar fallback), **A-leaderboard** (leaderboard.js RANK_NAMES + origin glyph), **A-schema-core** (extract shared computeBranch + rankWord — MUST land FIRST, everything depends on it), **D-named** (named/index.html filters + named-skills.js rank-grouping). Sequence: A-schema-core → then the rest fan out. Gated on §3.3 `--tier-unique` token + gold-wreath asset creation + §5 AOV size mapping.

### N-5 · Skill Flowcharts (skill-explorer flow view) — suite/ultimate tabs + plaque overlap
- **Source:** `docs/js/skill-explorer.js` flow renderer (suite synthesis L393-397, rank-row logic L1445-1500, SVG edge coloring L1819); `docs/js/named-skills.js` DAG layout (`TIER_ORDER` L151, rank rows L185+).
- **Two nitpicks:**
  1. **Suites & ultimates shown all-at-once → use TABS.** The flow view currently renders suite components and ultimate/fusion rows in one composite. Founder wants a **tab switcher** ("suites" vs "ultimates") so only one is shown at a time. Net-new UI control on the flow panel.
  2. **Plaque covers the flowchart (overlap).** High z-index / absolute-positioned plaque overlaps the DAG. Fix the stacking/layout so the plaque and flowchart don't collide.
- **PATTERN check:** overlap is a layout/z-index issue in the flow container — verify it's not the same plaque-positioning bug on other embedded-plaque surfaces (`docs/samples/skill-flowchart.html`, `docs/samples/flowchart.html`, `docs/named/report.html`). The tab-switcher is flow-view-specific but should reuse the existing tab component pattern already in skill-explorer (the About/Install/Docs tabs, `isHostTab` L479) rather than a new bespoke control.
- **Planned fix (candidate, unratified):** (1) add suite/ultimate tab toggle to the flow panel reusing the existing tab affordance; (2) resolve plaque z-index/positioning so it docks beside (not over) the DAG; check the sample flowchart pages for the same overlap. Lane A (skill-explorer JS) + coordinates with Lane D-plaque.

### N-6 · Badges — deprecated rank names ([dep-4★]/[dep-5★]) + honor-red origin
- **Source:** `scripts/generateBadges.py` L54-57 `RANK_NAMES = {4:"[dep-4★]", 5:"[dep-5★]", 6:"Apex"}`; L47 `HONOR_RED = "#ef4444"`. Generated output: `docs/badges/index.html` L1124/1138/1148/1283-1284 (rank-sampler table + JS `label` array), and **every** `docs/badges/_assets/<handle>/rank.svg` + `rank-seal.svg` + `docs/badges/samples/rank-{4,5}*.svg` with "[dep-4★] · 4★" / "[dep-5★] · 5★" baked into SVG `<text>`.
- **Founder directive:** [dep-4★], [dep-5★] are DEPRECATED → **Extra (4★), Ultimate (5★)**. Align to new schema + new design tokens + honor-red deprecation.
- **PATTERN (major — this is the SAME banned-word pattern as the scripts sweep §4, now on the badge surface):** `generateBadges.py`'s `RANK_NAMES` is a **flat rank→name dict identical to the four §4.2 scripts** — and it has the **same branch-blindness bug**: a flat `4:"Extra"` swap would mislabel every **Unique-branch** contributor's badge (a 4★ Unique's badge must read "Unique", not "Extra"). Must use `computeBranch` + the branch-forked ladder (§4.1 canonical source), NOT a string swap. This badge script is **guard-excluded** (`scripts/**` + `docs/badges/**` both hard-excluded from Rank Vocabulary Guard), which is exactly why the banned words survived here — the guard never scanned it. Regenerating badges also re-emits all `_assets/*/` SVGs.
- **Honor-red deprecation ties to N-4.4:** `HONOR_RED = "#ef4444"` on badge handles is the same honor-red the plaque avatar-wreath directive deprecates in favor of GOLD. Treat as one deprecation across badges + plaques.
- **Badge invariants (CLAUDE.md — do not break):** 1★ badges do not exist (2★ cutover, `is_redacted()` enforces); auto-sync NEVER touches `docs/badges/` (badge regen lands only via human-reviewed `infra/badge-*` PRs). So the *script fix* (Lane C) and the *badge asset regen* are **separate PRs on separate branches** — the design pass fixes `generateBadges.py` + `badges/index.html` copy; the `_assets/*/` SVG regeneration is an `infra/badge-*` follow-up. FLAG this branch-scope split in the plan.
- **Planned fix (candidate, unratified):** (1) `generateBadges.py` `RANK_NAMES` → branch-aware resolver (import `computeBranch`+`format_rank_label` per §4.1); recolor honor-red→gold token; (2) `docs/badges/index.html` L1124/1138/1148/1283-1284 rank-sampler copy → Extra/Ultimate + branch note; (3) regenerate `_assets/*/` + `samples/` SVGs on an `infra/badge-*` branch (separate PR per badge invariant). Lanes C + B, with an infra follow-up.

### N-7 · Reports (`docs/reports/` + `docs/named/report.html`) — impeccable presentation
- **Source:** `docs/reports/` (has `index.html`, `2026-28/index.html`, `DRAFT/2026-29.md`); `docs/named/report.html` (46KB single named-skill report template).
- **SCOPE CORRECTION (founder, 2026-07-17):** N-7 touches **`docs/reports/` ONLY — NOT `docs/meta/reports/`**. The dated `docs/meta/reports/*.html` archives are explicitly OUT of scope for this design pass; leave them entirely alone (do not restyle, do not touch). The in-scope report surfaces are `docs/reports/` (the weekly/dated public report index) and `docs/named/report.html`.
- **Founder directive:** *"Impeccable design for reports/ to show the actual report in a nice way."* Presentation/design upgrade for the `docs/reports/` surface — render the report content beautifully.
- **PATTERN check:** in-scope surfaces are `docs/reports/index.html` + `docs/reports/2026-28/index.html` (dated report pages) + `docs/named/report.html`. Determine if they share a stylesheet/layout or each rolls its own; an "impeccable" pass should establish ONE report design language applied across the `docs/reports/` set + `named/report.html`, not style one page. The `DRAFT/2026-29.md` is a markdown draft (likely rendered into a future `2026-29/index.html`) — the design system should cover the render target. Do NOT cross into `docs/meta/reports/` or `docs/audits/`.
- **Planned fix (candidate, unratified):** scope a shared report design system (typography scale, section cards, metadata header, evidence tables) applied to `docs/reports/*` + `named/report.html`. Needs a design-consultation pass to define the language before implementation. Its own Lane (D-reports); recommend a `/design-consultation` or sample mock before coding. FLAG: is this in-scope for #998 or a sibling design issue? (It's a genuine new surface, arguably its own issue rather than taxonomy-alignment remainder.)

### N-11 · Fuse sections in Skill Explorer — add Research CTA + repo link for skill-fuse
- **Source:** `docs/js/skill-explorer.js` fuse/suite surfaces — the fusion synthesis rows (L393-403), the flow panel fusion/suite buttons (`seFlowShowFusion` L1311, suite toggle L1314-1323), the suiteComponents install block (L832), and the fusion-recipe evidence tiles (L938-953). Any section that surfaces a **fusion** (skill-fuse) concept.
- **Founder directive:** *"all fuse sections in skill explorer should have a CTA towards the research page about skill-fuse so that people can install it. Repo link as well towards gaia-research/skill-fuse."* Two links per fuse section: (1) CTA → the Research page explaining skill-fuse (likely `research.gaiaskilltree.com/skill-fuse` or similar — VERIFY exact URL with founder / check `../gaia-research/` for the page slug); (2) repo link → `github.com/gaia-research/skill-fuse` so users can install it.
- **PATTERN (confirmed — this is the SAME cross-brand Research-bridge as N-10):** skill-fuse lives in the **gaia-research** org (Cyber-Slime Lab brand), same as the MCP relocation (N-9) and the footer Research CTA (N-10). All three are instances of one pattern: **the flagship Skill Tree surfaces should link OUT to the parent Research collective's products** (MCP, skill-fuse, research site). Reconcile the CTA visual language with N-10's cross-brand decision (Rimuru-Blue `#38bdf8` bridge). The fuse CTA is NOT a one-off button — it should be a reusable "Research product" link component shared with N-9 (MCP) + N-10 (footer/research CTA). Every fuse-related surface in the explorer gets it, not just one.
- **Cross-repo rule (README.md L54):** governs CONTENT/schema flow, NOT hyperlinks. A CTA + repo link out to gaia-research/skill-fuse is a hyperlink — allowed. Do NOT import skill-fuse code/schema into this repo.
- **Open ratification:** exact Research skill-fuse page URL (confirm slug); whether the repo is public `github.com/gaia-research/skill-fuse` (verify it exists / is public before linking — a 404 CTA is worse than none).
- **Planned fix (candidate, unratified):** define a shared "Research product CTA" component (folds N-9 MCP + N-10 research-CTA + N-11 skill-fuse into one cross-brand link affordance in the Rimuru-Blue bridge language); wire it into every fuse/suite section of skill-explorer.js. Lane A (skill-explorer JS) + coordinates with N-10 cross-brand decision. Gated on URL/repo verification.

### N-12 · Impeccable `/init` — codify the new design language as the standard, then critique-gated mobile-first pass
- **Founder directive (phase transition):** *"I need an impeccable /init, regarding these design choices as the standard. The final pass will then utilize critique agents — checking and verifying the new design language in ALL web assets, then regrading or coloring or even changing the layout of all website surfaces to be mobile-first — specifically the non-homepage pages. Homepage is final after the minor changes. Utilize sub-agents in implementation."* This is the **capstone**: ratify a canonical design-language document, then run a critique→remediate sweep across every non-homepage surface for mobile-first.
- **Two distinct deliverables:**
  1. **`/init` design-standard doc.** Produce a single canonical design-language spec (the "impeccable /init") that encodes ALL ratified N-1..N-11 choices as THE standard: the Yggdrasil II taxonomy vocabulary (branch-forked ladders), the AOV asset system (C suite / D unique), the avatar+gold-wreath+medallion pattern, the dark-plaque(unique)/gold-plaque(suite) split, the honor-red→gold origin deprecation, the two-brand reconciliation (Hunter's Atlas + Cyber-Slime Lab bridge), the fixed-nav clearance ladder, design-token-only (no hex), and the report design system. This becomes the reference every critique agent grades against. Likely lands as `docs/DESIGN.md` (or extends the existing one) + `founder/` canonical ref.
  2. **Critique-gated mobile-first remediation.** After the standard is set, fan out critique agents to audit ALL web assets against it, then a remediation wave that regrades/recolors/re-lays-out **non-homepage** surfaces to be mobile-first. **Homepage is FROZEN** except the N-1/N-2 minor fixes — critique agents must NOT propose homepage layout changes.
- **PATTERN (this is the meta-pattern over the whole pass):** N-1..N-11 are the *inputs* to the design standard; N-12 is the *standardization + enforcement* layer. The critique pass is the review leg of Discipline D (scout-gathers → opus-judges) applied site-wide. Mobile-first is a NEW cross-cutting axis not yet audited in any prior nitpick — needs its own scout to inventory current responsive/breakpoint state per non-homepage surface before remediation.
- **Sequencing (hard dependency):** N-12 deliverable #1 (the standard) depends on N-1..N-11 being RATIFIED (not just logged). Deliverable #2 (critique+mobile-first) depends on #1 existing AND the taxonomy/plaque/asset work (N-4 A-schema-core etc.) having LANDED — you can't grade surfaces against a standard while they're mid-migration. So: ratify N-1..N-11 → author design standard → implement N-1..N-11 via subagents → critique sweep → mobile-first remediation wave. N-12 is the LAST phase.
- **Scope flag:** the mobile-first remediation across all non-homepage surfaces is almost certainly LARGER than #998 — it's plausibly its own EPIC sub-issue (or a Yggdrasil III). Surface this to founder: does mobile-first ride #998 or split into a dedicated issue?
- **Planned approach (candidate, unratified):** (1) after N-1..N-11 ratify, author the canonical design-language doc (orchestrator superadmin — it's founder/root-md territory, authored not delegated); (2) scout current mobile/responsive state of non-homepage surfaces; (3) fan critique agents (2 sonnet / 1 opus per concurrency rule) to grade each surface vs the standard; (4) remediation subagents fix flagged surfaces; (5) final reviewer pass. This is the terminal phase of the whole design pass.

### N-13 · Medallion system (avatar + gold wreath + badge) not propagating to all surfaces + wreath art too minimal + skill graph not loading
- **Founder directive (2026-07-17, mid-Wave-1):** *"golden wreath laurel leaves needs refinement — leaves do not look like leaves, too minimal. Switch profile name with badge — badge should be a little bit bigger. docs/u/ are missing the wreath and avatar. Hero of docs/u/ per profile should show the avatar in the middle. HoH in /heroes/ are missing the wreath and the badge. Named contributors page still showing the old origin, no wreath, no badge, and no avatars. Possibly even the skill graph is missing these things — in fact the skill graph itself does not load on my view. Review after wave 1 if fully implemented on a single subagent Opus. Note, these COULD have been implemented already — if so take this as a review+nitpick changes."*
- **Cluster (7 items):**
  1. **Wreath art refinement:** `docs/assets/origin-wreath-gold.svg` laurel leaves read as minimal shapes, not leaves. Redraw with recognizable laurel-leaf forms (paired, veined, curving) — still token-tinted gold, still scalable, still lightweight. This is an ART revision to the W0 asset.
  2. **Profile (`docs/u/<handle>/`) name↔badge swap + size:** swap the profile name and the badge/medallion positions; the badge should render slightly LARGER. Generator = `scripts/generateProfilePages.py` (do NOT hand-edit `docs/u/*/index.html`).
  3. **`docs/u/` missing wreath + avatar:** profile pages show no gold-wreath-framed avatar. Add the medallion system to the profile generator.
  4. **`docs/u/` hero = centered avatar:** each profile's hero section should show the (wreathed) avatar in the MIDDLE.
  5. **`/heroes/` (HoH) missing wreath + badge:** Hall of Heroes cards show neither the gold wreath nor the badge/medallion. (W1a was scoped to avatars+wreath on heroes — VERIFY whether it landed the badge too; if not, this is the remediation.)
  6. **Named contributors page — full miss:** still shows the OLD red origin, no wreath, no badge, no avatars. Needs the complete medallion system. (Overlaps W1c named lane — VERIFY vs remediate.)
  7. **Skill graph:** may be missing the medallion system AND **does not load at all on founder's view** — investigate `docs/js/skill-graph.js` load failure (per CLAUDE.md known-issue: a null overlay-button `querySelector(...).addEventListener` at bootstrap silently aborts the IIFE → falls back to FALLBACK_SKILLS; also do not recreate the stale `skills/` root dir). Confirm whether it renders on a clean serve; if broken, fix the bootstrap; then propagate avatar/wreath/badge.
- **PATTERN:** this is the SAME medallion system from W0 plaque.js (`_fieldAvatar` = GitHub avatar + gold wreath + identicon fallback; AOV4 badge stamp) failing to propagate to three read surfaces (`docs/u/` profiles, `/heroes/`, named contributors) + the skill graph. Root question for the review: did the W0 `_fieldAvatar` path get REUSED by these surfaces, or did each surface keep a bespoke render that never got the medallion? The fix is to route ALL of them through the shared plaque/medallion path, not to re-implement per surface.
- **Handling per founder:** HOLD for a **single post-Wave-1 Opus subagent** that first VERIFIES current state of each of the 7 items against the merged Wave-1 result, then treats each as either "already done (confirm with Playwright evidence)" or "nitpick remediation (fix)." Skill-graph load failure is investigate-first. This runs as a Wave-1.5 review+remediation lane BEFORE Wave 2. Wreath-art redraw (item 1) is an asset revision that lands in the same PR. Profile generator changes (items 2-4) prefer the Python script (regen output). Homepage untouched.
