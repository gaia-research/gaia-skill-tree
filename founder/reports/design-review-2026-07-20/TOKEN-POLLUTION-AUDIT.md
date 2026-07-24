# Token Pollution Audit — `--tier-*` used as rank substitutes

> **RESOLVED 2026-07-25.** All three buckets migrated on `design/ygg2-checklist-fixes-t6`
> (commit `0f4d7e27f`, PR #1246). `--ev-type-*` token definitions added to the generator on
> `infra/ev-type-tokens` (PR #1269). Decisions: Bucket A → `--rank-4`/`--rank-5`/`--rank-6`;
> directory-tier[1-4] → `--rank-1..4`; Bucket B → dedicated `--ev-type-*` axis (per-type hues
> from `/evidence/`); Bucket C → `--tier-extra`/`--extra` → `--rank-4`, `--tier-ultimate`/
> `--ultimate` → `--rank-5` (fuse action → `--rank-4`). Also swept the 23 bare `--extra`/
> `--ultimate` alias consumers. tokens.css NOT regenerated in-branch (stale local Class-P
> gaia.json); staging regen materializes both the retired-type cleanup and `--ev-type-*`.


**Ground truth:** META.md §1.1 (rank ladder) + `/badges/` (faithful rank colors).

| Rank | Suite word | Unique word | Color token | Hex |
|---|---|---|---|---|
| 4★ | **Extra** ◆ | Unique ◉ | `--rank-4` | `#e879f9` fuchsia |
| 5★ | **Ultimate** ◆ | Unique Ultimate ◉ | `--rank-5` | `#fbbf24` amber gold |
| 6★ | **Apex** ◆ | Unique Impossible ◉ | `--apex-gold` / `--rank-6` | apex gold |

**The pollution:** `--tier-extra` (undefined → falls back to `#c084fc`) and `--tier-ultimate`
(undefined → falls back to `#f59e0b`) are being used as stand-ins for the **4★/5★ rank
colors**. They are *type* tokens (or dead tokens), not rank tokens. Where a surface names a
**rank** (Extra=4★, Ultimate=5★) it must use `--rank-4` / `--rank-5`.

`--tier-fusion` (#f59e0b, gold) and `--tier-unique` (#7c3aed, violet) are **legitimate
type/branch tokens** and stay where a surface genuinely means the *fusion type* or *unique
branch* — NOT rank.

Note `--tier-ultimate` ≈ gold #f59e0b but `--rank-5` = #fbbf24 — **different golds**. Real fix,
not cosmetic.

---

## Bucket A — RANK surfaces → migrate to rank tokens (APPROVED)

"Extra"/"Ultimate" name a rank. `--tier-extra → --rank-4`, `--tier-ultimate → --rank-5`
(+ matching `-rgb`).

| File:Line | Selector | Now | → |
|---|---|---|---|
| styles.css:3776 | `.skill-tooltip-type-extra` | `--tier-extra` | `--rank-4` |
| styles.css:3784 | `.skill-tooltip-type-ultimate` | `--tier-ultimate` | `--rank-5` |
| styles.css:5864 | `.tier-glyph[data-type="extra"]` | `--tier-extra` | `--rank-4` |
| styles.css:5872 | `.tier-glyph[data-type="ultimate"]` | `--tier-ultimate` | `--rank-5` |
| styles.css:7291 | `.se-node-orb--extra` | `--tier-extra` | `--rank-4` |
| styles.css:7296 | `.se-node-orb--ultimate` | `--tier-ultimate` | `--rank-5` |
| styles.css:7306 | `.se-node-orb--vi` (6★) | `--tier-ultimate` | `--rank-6` / `--apex-gold` |
| plaque.css:3122 | `.ptl2__tooltip-tier--extra` | `--tier-extra` | `--rank-4` |
| plaque.css:3124 | `.ptl2__tooltip-tier--ultimate` | `--tier-fusion` | `--rank-5` |
| plaque.css:2508-10 | `profile-filter-chip[data-value="extra"]` | `--tier-extra(-bg)` | `--rank-4(-bg)` |
| plaque.css:753-756 | `.se-node-orb--extra` (plaque copy) | `--tier-extra` | `--rank-4` |
| plaque.css:4088 | `.directory-tier[data-tier="2"]` title | `--tier-extra` | `--rank-4`? †|
| plaque.css:4086 | `.directory-tier[data-tier="4"]` title | `--tier-fusion` | `--rank-?` †|

† **directory-tier open question** — `data-tier="1..4"` maps basic/extra/unique/fusion. Is
`data-tier` a **rank** (1★–4★ → `--rank-1..4`) or a **branch**? If rank, all four titles should
be `--rank-N`. Needs your call — see Questions.

---

## Bucket B — EVIDENCE pills → separate evidence palette (APPROVED, palette TBD)

`.ev-type-pill.type-*` are **Evidence Types** (provenance), not ranks. Some already wrongly
borrow rank tokens. **Decision: give evidence its own palette, stop borrowing rank/tier.**
Current state (all in styles.css ~12455-12470):

| Pill | Now (polluted) |
|---|---|
| `type-github-stars` | `--tier-ultimate` (gold) |
| `type-fusion-recipe` | `--tier-ultimate` (gold) |
| `type-github-stars-own` | `--tier-ultimate` (gold) |
| `type-benchmark-result` | `--tier-extra` (purple) |
| `type-arxiv` | `--tier-extra` (purple) |
| `type-verifier-attestation` | `--rank-4` (borrowed rank) |
| `type-self-attestation` | `--rank-0` (borrowed rank) |
| `type-repo` / `-own` | `--tier-basic` |
| `type-peer-review` | `--tier-basic` |
| `type-proxy-containment` | `--tier-unique` |
| `type-social-signal` | `#34d399` hardcoded |

An `--evidence-*` grade palette already exists in tokens.css (platinum/gold/silver/bronze) but
that's *grade*, not *type*. **Need a defined evidence-TYPE palette** (see Questions).

---

## Bucket C — DECORATIVE UI accents (needs per-surface call, NOT rank)

These use `--tier-extra`/`--tier-ultimate` as a generic accent with **no rank meaning**.
Blanket rank-swapping would miscolor them. Proposed: route to a neutral UI-accent token, or
leave as the intended semantic. Listed for your review.

| File:Line | Selector | Role | Proposed |
|---|---|---|---|
| styles.css:1403/1414 | `.hero-audit-btn:hover` | hover accent | UI accent (not rank) |
| styles.css:1934,2371,2695,5928,6281,7619 | `*:focus-visible` outlines | focus ring | UI accent token |
| styles.css:2822 | `.codex-toc__list a:hover` | link hover | UI accent |
| styles.css:3483 | `.tree-glyph-fusion` | fusion *glyph* | `--tier-fusion` (type, gold) |
| styles.css:4557-63,4684,4804-05 | `*.copied` cmd feedback | "copied" flash | UI accent / success |
| styles.css:5746 | `.ns-chip-deriv` | derivative chip | ? (deriv≠rank) |
| styles.css:5752 | `.ns-chip-variant` | variant chip | ? (variant≠rank) |
| styles.css:7672-73 | `.se-tab-btn.active` | active tab | UI accent |
| styles.css:7723 | `.se-hosts-dropdown:hover` | hover border | UI accent |
| styles.css:10037 | `.agent-skill-label checkbox` | accent-color | UI accent |
| styles.css:12583 | `.se-ev-freshness--stale` | stale warn | warn color (not rank) |
| plaque.css:508,4147 | focus outlines | focus ring | UI accent |
| plaque.css:824 | apex keyframe box-shadow | 6★ apex glow | `--rank-6`/`--apex-gold`? |
| plaque.css:2743-48 | Instagram share action | brand-ish accent | UI accent (keep) |
| plaque.css:2821 | `profile-activity-action[data-action="fuse"]` | fuse *action* | `--tier-fusion` (action, gold) ‡|
| plaque.css:3071 | highlighted plaque border | highlight | ? |
| plaque.css:4073 | `.directory-search:focus` | focus ring | UI accent |

‡ sits beside `rank_up`=--rank-3, `ascend`=--apex-gold — action family, but "fuse" is gold-typed.

---

## Open questions for Marco

1. **directory-tier** (`data-tier="1..4"`): rank ladder (→ `--rank-1..4`) or branch? (Bucket A †)
2. **Evidence-type palette**: define a new `--ev-*` family in the token source, or map each
   evidence type to an existing non-rank semantic color? What are the 4-5 hues?
3. **Decorative accents** (Bucket C): introduce a single `--ui-accent` token (what hex?), or
   keep each as its nearest real semantic? Focus rings especially want ONE consistent color.
4. **Persistence**: rank/tier tokens live in `registry/gaia.json meta` → `tokens.css` (regen).
   `--rank-*` already exist, so Bucket A only edits *consumers* (safe, no regen). Bucket B/C
   may need NEW tokens → that's a `gaia.json meta` + `generateCssTokens.py` regen (data-file
   change, needs approval).
