# Yggdrasil II — Design-Branch Alignment Handover

**For:** whoever works `design/yggdrasil-ii-aov-v3`
**Author:** Planner/Reviewer, `docs/yggdrasil-ii-design-alignment`
**Date:** 2026-07-14
**Scope:** frontend / asset / design surface only (DESIGN.md, `docs/**/*.html`, `docs/js/**`, `docs/css/**`, AOV, plus the rank-name script maps). The prose docs (META.md, CONTEXT.md, trust-methodology) are handled separately by #994 / PR #1170; the CI guard by #999 / PR #1169. **Do not touch prose or the guard from the design branch.**

---

## 1. Purpose + when to act

The ratified **Yggdrasil II v2** model splits the old single `type`/rank taxonomy into two orthogonal axes and renames the 4★–6★ ladder. This doc tells you *exactly* what to change on the design surface so the site renders the v2 model correctly.

**Dependency gate — do NOT start until all three have landed on `dev/yggdrasil-ii-staging`:**

| Blocked-by | What it lands | Why the design branch needs it |
|---|---|---|
| **#995** | schema: `type ∈ {basic, fusion}`, `suiteComponents`, no `branch` field on nodes | JS must stop reading `type==='unique'`/`'ultimate'`/`'extra'` — those values won't exist |
| **#996** | CLI `computeBranch(named)` → `standard`/`suite`/`unique` | scripts + JS need a canonical branch resolver; you cannot map rank→name locally anymore (4★+ forks by branch) |
| **#997** | registry migration (`extra`→`fusion`, `ultimate`→`fusion`, `unique`→`basic`; backfill `suiteComponents`) | the live graph data must already be v2-shaped before the renderer assumes it |

Acting before these land = churn against data/assets still in flight. See §5.

### The v2 model (yardstick)

- **TYPE axis** (starless/generic nodes only): `basic` | `fusion`. Pure structure — `fusion` iff the node has prerequisites. **Never consulted for branch.**
- **`suiteComponents`**: presence on the **Named Skill** drives the branch fork; also feeds Trust Magnitude. Independent of `type`. **`suiteComponents` is a Named-Skill-only field — it never lives on the starless/generic parent.**
- **BRANCH axis** (named skills only, *derived at read-time, never declared*): `branch = f(the Named Skill's suiteComponents present?, rank)`.
  - rank 1–3 → **standard** (no branch fork)
  - rank ≥ 4 AND the Named Skill has `suiteComponents` → **suite**
  - rank ≥ 4 AND the Named Skill has **no** `suiteComponents` → **unique**
- **Ladders:**
  - standard: 1★ **Awakened** · 2★ **Named** · 3★ **Evolved**
  - suite: 4★ **Extra** · 5★ **Ultimate** · 6★ **Apex**
  - unique: 4★ **Unique** · 5★ **Unique Ultimate** · 6★ **Unique Impossible**
- **`Transcendent` and `Hardened` are BANNED.** `Ultimate` is the universal 5★ word. **The "Skill" suffix attaches to RANK words** — `Extra Skill` / `Unique Skill` / `Ultimate Skill` / `Apex Skill` are valid rank phrasings. **Type words stand bare** (`Basic`, `Fusion`) — `Basic Skill` / `Fusion Skill` are BANNED (guard-enforced). 1★–3★ ladder words (Awakened/Named/Evolved) are always star-qualified.
- Type & branch are orthogonal. Evidence Floor is removed; **TM is the sole gate.**

---

## 2. File-by-file checklist

| File | What's stale | Required v2 change | Blocked-by |
|---|---|---|---|
| `DESIGN.md` | `Hardened`/`Transcendent` rank words; `type === 'extra'\|'unique'\|'ultimate'` glyph rules; `Extra Skill`/`Ultimate Skill` type labels; glow/animation tokens named for old ranks | Retitle rank sequence to Awakened→Named→Evolved→(Extra/Unique)→(Ultimate/Unique Ultimate)→(Apex/Unique Impossible); rewrite glyph mapping to branch-derived; rename `Ultimate Skill Cycle`/`Extra Skill Cycle` sections | #995/#996 |
| `docs/js/skill-graph.js` | reads `type==='unique'` (L43, L409, L736) and `type==='ultimate'` (L1106); `type==='basic'` isolation heuristic (L410) | replace `type`-based branch/rank inference with `suiteComponents`+rank branch logic mirroring `computeBranch` | #995/#996 |
| `docs/css/tokens.css` | defines `--tier-basic/extra/unique/ultimate` (L10/17/24/31); **no `--tier-fusion`** | add `--tier-fusion` token (+ `-rgb`/`-bg`/`-border`); keep old tokens as aliases during migration | #995 |
| `docs/css/plaque.css` | `--tier-extra`/`--tier-ultimate`/`--tier-unique` refs; L260-261 "Transcendent ★"/"Transcendent" glow comments; L568 "rank IV (Hardened)" comment | map to branch tokens; scrub Transcendent/Hardened from comments | #995/#996 |
| `docs/css/ascension-overdrive-v2.css` | `[data-tier="hardened"]` selectors (L1248/L1252/L1607); "Hardened..Awakened" comment (L1091) | rename `hardened`→`extra` (or branch-aware `data-branch`); scrub comments | #995/#996 |
| `docs/samples/tree.html` | legend "Extra Skill"/"Ultimate Skill" (L184/L190); tree lines "4★ Hardened"/"5★ Transcendent"/"6★ Transcendent ★" (L253-255) | **Fusion** legend (bare type word); branch-correct rank labels | #995/#996 |
| `docs/samples/foundation.html` | medallion `<span class="name">Hardened</span>`/`Transcendent` (L362/L371) | Extra/Ultimate (suite) or branch-aware labels | #996 |
| `docs/badges/index.html` | rank table "Hardened" (L1124), "Transcendent" (L1138, L1148 "Origin 5★ Transcendent"), JS labels `4:"Hardened · 4★"`/`5:"Transcendent · 5★"` (L1283-1284); `s.type==="unique"` (L1598) | branch-aware rank labels; drop Transcendent/Hardened; replace `type==="unique"` read | #996 |
| `docs/audits/ruflo-curation.html` | badges "4★ Hardened"/"5★ Transcendent" (L127/159/193/227/308) | Extra/Ultimate per branch | #996 |
| `docs/codex/trust-methodology.html` | "6★ Transcendent ★ (Apex)" (L941); many `--tier-extra/ultimate` refs | "6★ Apex"; branch tokens | #995/#996 |
| `docs/en/faq.html` | rank table "Hardened"/"Transcendent" (L511/L516) | Extra/Ultimate | #996 |
| `docs/en/skill-hierarchy.html` | "Hardened"/"Transcendent" (L770/L775) | Extra/Ultimate | #996 |
| `docs/samples/ranks.html` | "Transcendent ★ · 6★" (L342) | "Apex · 6★" (or Unique Impossible if unique-branch sample) | #996 |
| `docs/samples/index.html` | SVG text "Hardened" (L250) | Extra | #996 |
| `docs/index.html` | asset-planning comment block referencing `rank-5-transcendent.png` etc. (L871-899) — **already partly annotated** ("Rank 5 renamed Transcendent → Ultimate") | rename asset stems to `-ultimate`; regenerate rank-5/6 art | #995 + asset regen |
| `docs/u/index.html` | AOV medallion surface (branch scenes already present) | ensure medallion rank labels use v2 names | #996 |
| `docs/agent.md` | `◇ Extra Skills`/`◆ Ultimate Skills` defs (L13-14); `4★+ (Hardened/Transcendent)` (L80); `6★ (Transcendent ★ / Apex)` (L81) | Fusion type; branch-aware rank names — **⚠ Hermes-managed; coordinate before editing** | #994 (prose) |
| `DEV.md` | `reclassify` doc: `type ∈ basic\|extra\|ultimate\|unique` (L160) | `type ∈ basic\|fusion` | #994/#996 |
| `CONTRIBUTING.md` | "Skill types in graph: `basic`, `extra`, `ultimate`" (L180); Ultimate-skills link (L203) | `basic`, `fusion` | #994 |
| `GOVERNANCE.md` | "4★ (Hardened)" (L28); "Basic/Extra Skills"/"Ultimate Skills" approval rules (L37-38, L66); "reclassified to `extra` tier" (L73) | branch/type-correct wording | #994 |

> `DEV.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, `docs/agent.md` are prose and are on #994's radar (see PR #1170 "Deferred" list). Only touch them from the design branch if #994 explicitly hands them over; otherwise leave to the prose track to avoid double-editing.

---

## 3. Specific call-outs

### 3.1 DESIGN.md — the big one
- **L25**: legacy short tokens `--extra`/`--ultimate` + canonical `--tier-extra`/`--tier-ultimate`. Add `--tier-fusion`; decide whether Unique-branch keeps its own violet token or reuses `--tier-basic` (v2: unique-branch skills sit on `basic` generics).
- **L36/L38**: tier color table rows `extra ◇ Extra Skill` / `ultimate ◆ Ultimate Skill` — collapse to a single `fusion ◇ Fusion` row (type word stands bare — no "Skill" suffix).
- **L54**: rank sequence still reads `… → Hardened (4★) → Transcendent (5★) → Apex (6★)`. Replace with the branch-forked ladder.
- **L85-86**: rank→token table maps `Hardened → --rank-4`, `Transcendent → --rank-5`. Rename rank labels; tokens can stay numeric (`--rank-4/5/6`).
- **L100-102**: glyph mapping already carries dual Ygg I/II notes but still leads with `type === 'extra'`/`'unique'`/`'ultimate'`. Post-migration, drop the Ygg I clauses entirely.
- **L139-142**: evidence-tint mapping uses `--tier-ultimate/unique/extra`. Re-key to fusion + branch tokens.
- **L255, L263-264, L273**: glow tokens `--glow-IV`/`--glow-V` labelled "Hardened"/"Transcendent"; scrub the labels (keep the numeric tier meaning).
- **L299 / L316 / L334**: animation-cycle section titles `Ultimate Skill Cycle` / `Extra Skill Cycle` and tree dialog labels `◆ Ultimate Skill:` / `◇ Extra Skill:` — rename to Fusion / branch-rank wording.

### 3.2 `docs/js/skill-graph.js` — legacy `type` reads
- **L43**: `if (type === 'unique') rank = 5;` — a rank *inference* from type. Under v2, rank is data-driven, not type-derived. Remove or re-base on `computeBranch`.
- **L409**: `if (skill.type === 'unique') { satellite.unique.push(skill); }` — the classic Ygg I bucket. Replace with `computeBranch(skill) === 'unique'`.
- **L410**: `skill.type === 'basic' && !prereqs && !allPrereqRefs.has(id)` — graph-isolation heuristic; under v2, unique-branch is a **Named Skill** at 4★+ whose own `suiteComponents` is absent (independent of the generic's `type`), so fold this into the branch resolver.
- **L736**: `skills.filter(s => s.type === 'unique')` count — same fix.
- **L1106**: `return skill.type === 'ultimate' || skill.type === 'unique';` — neither value exists post-migration. Rewrite against `suiteComponents`/branch.

### 3.3 Missing `--tier-fusion` CSS token
`git grep -- '--tier-fusion'` returns **nothing** today. `docs/css/tokens.css` only defines `basic/extra/unique/ultimate`. Add `--tier-fusion` (+ `-rgb/-bg/-border`) so any `type=fusion` render path has a canonical color. Keep the old tokens as back-compat aliases until every consumer is migrated.

### 3.4 HTML branch-definition copy
`docs/samples/tree.html` (L184/190 legend, L253-255 tree lines), `docs/en/faq.html`, `docs/en/skill-hierarchy.html`, `docs/badges/index.html`, `docs/samples/foundation.html` all still print `Extra Skill`/`Ultimate Skill` type labels and `Hardened`/`Transcendent` rank words. Where copy explains the *taxonomy*, say **Fusion** (bare type word, `type=fusion`). Where copy explains *ranks*, use the branch-forked names. (`faq.html`/`fusion.html` at the repo root had no hits — the localized `docs/en/faq.html` is the one that needs work.)

### 3.5 AOV medallion rank labels
The Ascension-Overdrive medallion must use **Extra / Ultimate / Apex** (suite) and **Unique / Unique Ultimate / Unique Impossible** (unique) and **drop Transcendent** entirely. Touch points: `docs/css/ascension-overdrive-v2.css` `[data-tier="hardened"]` selectors (L1248/L1252/L1607 — rename to `extra` or a `data-branch` scheme), `docs/samples/foundation.html` medallion names (L362/L371), and the AOV surface in `docs/u/index.html`. The AOV scene JS (`docs/js/ascension-overdrive-v2.js`) already speaks `apex`/`unique` scene names — align the medallion *labels* to match.

---

## 4. Script rank-name maps — BRANCH-AWARE, blocked by #996

These four scripts hard-code a `rank → name` map. That mapping is **no longer valid** at 4★+ because the name forks by branch (Suite vs Unique). You cannot fix them with a simple string swap — they need `computeBranch(named)` from #996 to pick the right ladder per skill. **All four are blocked by #996** and are correctly excluded from the #999 guard scan (`scripts/**` hard-excluded) until then.

| Script | Stale map | Note |
|---|---|---|
| `scripts/generateBadges.py` | L57 `4:"Hardened", 5:"Transcendent", 6:"Apex"` (+ glow colors L114) | badge right-panel text; needs branch to choose Extra/Unique at 4★, Ultimate/Unique Ultimate at 5★, Apex/Unique Impossible at 6★ |
| `scripts/generateOgCards.py` | L655-657 `4:"HARDENED", 5:"TRANSCENDENT", 6:"TRANSCENDENT ★"`; plate copy L11-12 `Ultimate Skill … type=ultimate` | OG card plates; both the rank map and the `type=ultimate` plate logic are dead post-migration |
| `scripts/inspectTrustMagnitude.py` | L54-56 `4★:Hardened, 5★:Transcendent, 6★:Transcendent ★`; L205 "Apex gate (6-star Transcendent)" | TM inspector output strings |
| `scripts/generate_ruflo_curation.py` | L31-32 `4★:Hardened, 5★:Transcendent` | curation-report generator |

The correct pattern once #996 lands: resolve the skill's branch, then index into the branch-specific ladder — do **not** keep a flat `rank→name` dict.

---

## 5. Do NOT do yet

- **Do not start any of §2–§4 before #995 + #996 + #997 land on staging.** The renderer/scripts will read data that hasn't migrated, and asset regeneration (rank-5/6 art rename `-transcendent` → `-ultimate`/`-apex`) is in flight — editing now guarantees churn and merge conflicts.
- **Do not edit META.md, CONTEXT.md, or `docs/meta/2026-06-trust-methodology.md`** — owned by #994 / PR #1170. Editing them from the design branch will collide and re-trigger the #999 guard.
- **Do not remove the legacy `--tier-extra/unique/ultimate` tokens** in the same pass you add `--tier-fusion`. Add the new token, migrate consumers, *then* retire aliases in a follow-up so nothing renders un-themed mid-migration.
- **Do not hand-edit the four scripts' rank maps into a flat swap** (e.g. `Hardened→Extra`). That silently mislabels every Unique-branch skill. Wait for `computeBranch` (#996).
- **Do not touch Hermes-managed files** (see `docs/agent.md` "Agent-Managed Files") without coordinating — `docs/agent.md` itself is on that boundary.
- **Do not delete or rename banned words inside deprecation notices** if any design doc documents the migration — the #999 guard treats bare `Transcendent`/`Hardened` as failures, so keep such references in guard-excluded surfaces (`docs/**/*.html`, `scripts/**`) or coordinate an allowlist entry.
