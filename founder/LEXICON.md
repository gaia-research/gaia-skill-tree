# LEXICON — vocabulary of record

<!-- GENERATED FROM scripts/lexicon/lexicon.json and its namespace files — DO NOT EDIT BY HAND. -->
<!-- Regenerate: npx tsx scripts/lexicon/check-lexicon.ts --emit -->
<!-- lexicon-allow -->

> Schema `2` · HQ `gaia-skill-tree` · 20 terms across 2 namespace(s) · updated **2026-08-10**.
>
> **One term, one owner.** A term is defined in **exactly one** file, ever. A
> namespace file **adds** terms in its own namespace and may never redefine a
> term another namespace owns — inside this HQ the merge rejects it, across HQs
> the name-only foreign mirror does.

| Namespace | Owned by | File | Terms |
|---|---|---|---|
| `gaia.skills` | `gaia-skill-tree` | `scripts/lexicon/lexicon.json` | 11 |
| `gaia.trust` | `gaia-skill-tree` | `scripts/lexicon/lexicon.gaia.trust.json` | 9 |

Terms owned by **gaia-research/gaia-research** are listed name-only in `scripts/lexicon/lexicon.foreign.json` and are
defined there, never here:

- `/skill-heaven` → `gaia.heaven`
- `/skill-hell` → `gaia.heaven`
- `/skill-ultra` → `gaia.heaven`
- `/skill-zero` → `gaia.zero`
- `add-ons` → `gaia.zero`
- `budget` → `gaia.research`
- `claude-zero` → `gaia.zero`
- `clean-room` → `gaia.zero`
- `codex-zero` → `gaia.zero`
- `context source` → `gaia.zero`
- `curated` → `gaia.zero`
- `CURRENT` → `core`
- `door` → `gaia.zero`
- `dose` → `gaia.research`
- `eviction` → `gaia.zero`
- `firebreak` → `gaia.zero`
- `floor` → `gaia.zero`
- `gaia_inspect` → `gaia.mcp`
- `gaia_search` → `gaia.mcp`
- `gaia_status` → `gaia.mcp`
- `gauge` → `gaia.research`
- `grok-zero` → `gaia.zero`
- `harness dose` → `gaia.research`
- `heat` → `gaia.research`
- `heaven` → `gaia.heaven`
- `Heaven-0` → `gaia.zero`
- `Heaven-1` → `gaia.zero`
- `hell` → `gaia.heaven`
- `hell lane` → `gaia.heaven`
- `hermes-zero` → `gaia.zero`
- `HH Index` → `gaia.research`
- `INVARIANT` → `core`
- `invocation dose` → `gaia.research`
- `ladder` → `gaia.heaven`
- `launcher` → `gaia.zero`
- `lean` → `gaia.zero`
- `level` → `gaia.zero`
- `meter` → `gaia.research`
- `Milim` → `gaia.brand`
- `mode` → `gaia.heaven`
- `native` → `gaia.zero`
- `notch` → `gaia.zero`
- `own-placebo` → `gaia.research`
- `pi-zero` → `gaia.zero`
- `picker` → `gaia.zero`
- `polarity` → `gaia.heaven`
- `posture` → `gaia.zero`
- `product-floor` → `gaia.zero`
- `project-only` → `gaia.zero`
- `purge` → `gaia.zero`
- `resident` → `gaia.zero`
- `restraint` → `gaia.zero`
- `router` → `gaia.heaven`
- `rung` → `gaia.heaven`
- `scalpel` → `gaia.zero`
- `seed` → `gaia.research`
- `skill-heaven` → `gaia.heaven`
- `skill-zero` → `gaia.zero`
- `slider` → `gaia.zero`
- `stamp` → `gaia.research`
- `standing dose` → `gaia.research`
- `summon` → `gaia.heaven`
- `summonable` → `gaia.heaven`
- `tier` → `gaia.research`
- `ultra` → `gaia.heaven`

| State | Meaning | Where allowed |
|---|---|---|
| ✅ `canonical` | The word. Use this. | everywhere |
| ⛔ `banned` | The oracle retired it. CI fails. | nowhere (except `**/archived/**`) |
| 🅿️ `parked` | Coined but unchosen. | `docs/` only — never user-facing copy or code |
| 🧊 `frozen` | Meant something specific once. | `**/archived/**` only |

**A term is `banned` only when the HQ's oracle of record already retired it.** A term
this project is still arguing about is `parked`. Writing a linter is not a way
to make a decision.

## `gaia.skills`

### names

| Term | State | Oracle | Definition |
|---|---|---|---|
| `Gaia Skill Tree` | ✅ canonical | CONTEXT.md § Nomenclature decisions | The product name, in headline, title and OG copy. The org is Gaia Research; "the registry" (lower-case, no Gaia prefix) is the data-layer term only. |
| `Gaia Registry` | ⛔ banned | CONTEXT.md § Banned synonyms (issue #1258) | Retired as a product name / proper noun. The same ruling names the v5 namespace `gaia.skills` rather than `gaia.registry`. **Use `Gaia Skill Tree`.** Matched case-insensitively, so this also catches lower-case "gaia registry" — the plain common noun "registry" (no "Gaia" prefix, any case) is still correct for the data layer; only a Gaia+registry construction is retired. |
| `Gaia Skill Registry` | ⛔ banned | CONTEXT.md § Banned synonyms (issue #1258) | Retired as a product name / proper noun — same ruling as "Gaia Registry". Needs its own term: the three-word phrase is not a substring match of the two-word "Gaia Registry" term (the gate matches literal adjacent words, not arbitrary interior words), so without this entry the three-word form would slip past the gate untouched. **Use `Gaia Skill Tree`.** Matched case-insensitively, so this also catches "gaia skill registry" and any mixed-case form. |

### taxonomy

| Term | State | Oracle | Definition |
|---|---|---|---|
| `named skill` | ✅ canonical | — | A skill with a contributor-authored implementation in `registry/named/`, as opposed to a generic skill, which is a catalogue entry with no implementation attached. |
| `generic skill` | ✅ canonical | — | A catalogue node in `registry/nodes/` describing a capability with no contributor implementation attached. Its named forms are separate terms. |
| `Fusion` | ✅ canonical | CONTEXT.md § Taxonomy v6 (Yggdrasil II) | The structural type (`type=fusion`) for a skill composed from prerequisites. Stands bare — the "Skill" suffix is a rank-word convention, not a type-word one. |
| `Extra skill` | ⛔ banned | CONTEXT.md § Banned synonyms | Legacy Yggdrasil I taxonomy word for the composed type, along with `type=extra`. **Use `Fusion`.** |
| `Atomic skill` | ⛔ banned | CONTEXT.md § Banned synonyms | Retired tier synonym for the uncomposed type. **Use `Basic`.** |
| `top-tier skill` | ⛔ banned | CONTEXT.md § Banned synonyms | Retired synonym for the 5★ rank name. **Use `Ultimate`.** |
| `mythic` | ⛔ banned | CONTEXT.md § Banned synonyms | Retired synonym for the 5★ rank name. Scoped to copy and code: it is a word an internal note may legitimately quote while explaining why it is gone. **Use `Ultimate`.** |

### mechanics

| Term | State | Oracle | Definition |
|---|---|---|---|
| `slot` | ✅ canonical | — | Where a user's skill level actually lives. Levels are stored in slots on `skill-trees/<user>/skill-tree.json`, never on the skill object — anything computing stats, trees or breakdowns must read the slot. |

## `gaia.trust`

### trust

| Term | State | Oracle | Definition |
|---|---|---|---|
| `Trust Magnitude` | ✅ canonical | CONTEXT.md § Evidence and trust | The score a rank-up gates on. Computed from graded evidence; the public label for the scoring engine is TM Index, versioned by calendar quarter. |
| `TM Index` | ✅ canonical | CONTEXT.md § Evidence and trust | The public-facing, quarter-versioned name for the Trust Magnitude scoring engine — TM Index (2026 Q2), TM Index (2026 Q3). The G-series (G7, G8, …) is the internal engineering codename and stays internal. |
| `Fusion Score` | ✅ canonical | META.md § 2.1e Fusion Score (Yggdrasil III structural scalar) | The structural reading ratified by Yggdrasil III: how much distinct capability a skill composes, derived from canonical prerequisites, suite components, and origin structure. A peer of Trust Magnitude, never an input to it — informational in V1, gating no star, rank, or Trust Grade. |
| `fusion magnitude` | ⛔ banned | META.md § 2.1e Fusion Score (Yggdrasil III structural scalar) | The retired Yggdrasil II term for structure scored INSIDE Trust Magnitude. Yggdrasil III fixed that contribution at 0 TM and moved the reading out to Fusion Score; reusing the old word re-implies the coupling that was removed. **Use `Fusion Score`.** |
| `Evidence Grade` | ✅ canonical | CONTEXT.md § Evidence and trust | The graded quality of one evidence row. Every star above 1★ requires graded evidence. |
| `Evidence Class` | ⛔ banned | CONTEXT.md § Relationships | The deprecated axis Evidence Grade replaces. **Use `Evidence Grade`.** |
| `Evidence Floor` | ⛔ banned | CONTEXT.md § Relationships (Yggdrasil II) | The retired per-star minimum-evidence column. Ranking up gates on Trust Magnitude now, not on a per-star floor. **Use `Trust Magnitude`.** |
| `star bar` | ✅ canonical | — | The per-skill star display, and the gate behind it: promoting a skill to 3★ or above requires a verified `links.github` blob URL. Named in META.md § 2.4. |
| `rank up` | ✅ canonical | CONTEXT.md § Verbs | The verb for moving a skill up the star axis. "Level up" is synonymous; `upgrade` and `promote-up` are not. |

