# DESIGN.md — Gaia Visual Design Language

## Repository Layout

The visual system below applies to the public site, generated registry pages, and skill tree renders. Source files now live in the refactored Gaia layout:

| Zone | Path | Purpose |
|---|---|---|
| Curated registry | `registry/` | Maintainer-reviewed graph, named skills, schemas, and public generated catalog artifacts |
| Review intake | `registry-for-review/` | Draft skill batches created by `gaia push` |
| User skill trees | `skill-trees/` | Durable per-user `skill-tree.json` records |
| Local output | `generated-output/` | Gitignored scan artifacts and personal tree renders |
| Python CLI | `src/gaia_cli/` | Core lifecycle behavior and path resolution |
| npm wrapper | `packages/cli-npm/` | Thin Node wrapper around the Python CLI |
| MCP server | `packages/mcp/` | Agent-native integration package |

Public curated outputs, such as `registry/gaia.svg`, `registry/gaia.gexf`, `registry/real-skills.html`, and `registry/combinations.md`, inherit this design language. `docs/graph/*` remains a generated GitHub Pages mirror so the docs site can load graph assets when served from the `docs/` directory.

## Color Palette

CSS custom properties defined in `docs/index.html`:

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#030712` | Page background |
| `--surface` | `#0f172a` | Card / panel background |
| `--border` | `#1e293b` | Dividers, card borders |
| `--text` | `#e2e8f0` | Primary text |
| `--muted` | `#64748b` | Secondary / subdued text |
| `--basic`     | `#38bdf8` | Basic tier accent (sky blue) — alias of `--tier-basic` |
| `--extra`     | `#c084fc` | Extra Skill tier accent (purple) — alias of `--tier-extra` |
| `--unique`    | `#7c3aed` | Unique Skill tier accent (deep violet) — alias of `--tier-unique` |
| `--ultimate`  | `#f59e0b` | Ultimate Skill tier accent (amber) — alias of `--tier-ultimate` |

> **Source of truth.** As of Stage 1 of the Frontend Cohesion Overhaul, all four tier hexes live in `registry/gaia.json.meta.typeColors` and are emitted to `docs/css/tokens.css` by `scripts/generateCssTokens.py`. The legacy short tokens above are kept as aliases so older selectors keep working; the canonical token names are `--tier-basic`, `--tier-extra`, `--tier-unique`, `--tier-ultimate` (plus `-rgb`, `-bg`, `-border`, `-symbol` variants). Never hardcode the hex in CSS or JS.

---

## Skill Tiers

Four tiers, each with a fixed color identity and symbolic glyph. (The Unique tier was added after the original three-tier design and is the standalone-mastery branch — a Basic Skill that reached elite rank without ever fusing.)

| Tier | Symbol | Display Name | Hex | RGB |
|---|---|---|---|---|
| `basic`     | ○ | Basic Skill    | `#38bdf8` | `56,189,248`  |
| `extra`     | ◇ | Extra Skill    | `#c084fc` | `192,132,252` |
| `unique`    | ◉ | Unique Skill   | `#7c3aed` | `124,58,237`  |
| `ultimate`  | ◆ | Ultimate Skill | `#f59e0b` | `245,158,11`  |

Badge styles follow a consistent formula: `rgba({rgb}, .15)` background, `rgba({rgb}, .3)` border, solid hex text.

Card glow per tier (radial gradient, 35% opacity):
- Basic: `rgba(56,189,248,.4)`
- Extra: `rgba(192,132,252,.4)`
- Unique: `rgba(124,58,237,.4)`
- Ultimate: `rgba(245,158,11,.4)`

---

## Rank System

Skills level up from 0 → VI. Each rank has a distinct RPG-inspired color.

| Level | Class | Rank | Color | Hex | Background tint |
|---|---|---|---|---|---|
| `0` | F | Unawakened | Slate | `#94a3b8` | `rgba(100,116,139,.12)` |
| `I` | D | Awakened | Sky blue | `#38bdf8` | `rgba(56,189,248,.12)` |
| `II` | C | Named | Teal | `#63cab7` | `rgba(99,202,183,.12)` |
| `III` | B | Evolved | Violet | `#a78bfa` | `rgba(167,139,250,.12)` |
| `IV` | A | Hardened | Fuchsia | `#e879f9` | `rgba(232,121,249,.12)` |
| `V` | S | Transcendent | Amber | `#fbbf24` | `rgba(251,191,36,.12)` |
| `VI ★` | SS | Transcendent ★ | Amber (bright) | `#fbbf24` | `rgba(251,191,36,.20)` |

The rank color sequence intentionally mirrors an RPG rarity ramp: neutral → cold → teal → violet → pink → gold, with the apex doubling its background opacity.

> **Note on the Class column.** The letter values (D / C / B / A / S / SS) are retained here as historical/internal reference only — they predate the current evidence-class vocabulary in `CONTEXT.md`. The visitor-facing tier label is the **rank name + star count** (e.g. "Hardened · 4★"). Generated surfaces no longer emit the letter suffixes (`· SS`, `· V`, `· IV`, etc.) — see `plaque-reveal.js`, `generateProfilePages.py`, `generateOgCards.py`.

---

## Level VI — Transcendent ★ Special Rendering

VI nodes bypass `drawNode` entirely and use `drawNodeVI`, which runs every animation frame using the shared `state.t` clock:

| Layer | Description |
|---|---|
| Outer glow | `createRadialGradient` from `r×0.5` to `r×(4.8 + 0.3·sin(t·1.8))` — hue cycles at 45°/s, with a 90° offset second stop and a fixed gold fade |
| Core node | Radial gradient with three rainbow stops (hue, hue+200, hue+60) converging to `hsl(45,100%,45%)` gold at the rim |
| Orbit sparkles | 6 dots, each rotating at 0.4 rad/s, distance pulsing with `sin(t·2.1 + i)`, each a different hue 60° apart, alpha pulsing at 3 rad/s |
| Specular | Same white highlight as standard nodes, boosted to 85% alpha |

The hue cycle formula: `hue = (t × 45) % 360` (full rainbow every ~8 s).  
Gold dominates the outer fringe (`hsl(45,…)`) so the node reads as amber at a glance but shimmers through the full spectrum up close.

---

## Graph Canvas

Node radii (before depth/projection scale):

| Type | Base radius |
|---|---|
| `ultimate`  | 12.5 |
| `unique`    | 9.5  |
| `extra`     | 6.9  |
| `basic`     | 3.5  |

Edge line width:

| Condition | Ultimate | Other |
|---|---|---|
| Highlighted (hover neighbor) | 2.2 px | 1.4 px |
| Default | 1.55 px | 0.92 px |

Sphere layout radii (at scale 1.25):
- Basic: 250 × scale = **312 px**
- Extra: 145 × scale = **181 px**
- Ultimate: 44 × scale = **55 px** (innermost)

---

## Typography

The Hunter's Atlas type stack is **Scholar's Plate** — a 19th-century natural-history atlas serif for display, a humanist grotesque for body, and an OFL pixel mono for HUD/code. All three faces are OFL/free.

| Context | Stack |
|---|---|
| Body | `Bricolage Grotesque, Inter, system-ui, sans-serif` |
| Display | `EB Garamond, Georgia, serif` — hero titles, plate headings, section h2 only |
| Code / HUD | `Departure Mono, JetBrains Mono, ui-monospace, monospace` |

Type scale:
- Hero h1: `clamp(2.4rem, 6vw, 4rem)`, `font-family: var(--font-display)`, weight 600, line-height 1.1
- Section h2: `clamp(1.6rem, 4vw, 2.2rem)`, `font-family: var(--font-display)`, weight 600 (EB Garamond is heavier at 600 than Inter is at 700, so the visual weight matches without going to 800)
- Body: 1rem / 1.65, `var(--font-body)`
- Small / badge: 0.72–0.82rem, `var(--font-mono)` for ledger strips and numeric HUD elements

Syntax highlighting in `<pre>` blocks:
- `.comment` — `#4b6378`
- `.cmd` — `#38bdf8` (sky / basic)
- `.str` — `#86efac` (green)
- `.kw` — `#a78bfa` (violet)

---

## Key UI Patterns

**Nav** — sits on a 1px hairline divider in `var(--border)` over `var(--bg)`. No glassmorphism on the main nav (the previous frosted-glass treatment is retired here). Diamond Seal mark + wordmark on the left, destination links on the right.

**Hero titles** — solid `var(--text)` in EB Garamond at weight 600 (`var(--font-display)`). No gradient text. Emphasis words (e.g., "rare", "earned") may carry a single hairline gold underline using `border-bottom: 1px solid var(--apex-gold)` or an equivalent inline `<span>` underline accent. The previous three-stop tier-gradient sweep on titles is retired.

**Hero tier gradient (retained, scoped)** — the three-stop sweep
```
linear-gradient(135deg, #38bdf8 0%, #c084fc 50%, #f59e0b 100%)
```
is retained ONLY as the background fill for the floating hero CTA pills (`◆ Open full graph`, `⇄ Field view`). It is no longer used on titles or body copy.

**Buttons**
- Primary: solid `var(--apex-gold)` background on a midnight (`var(--bg)`) border, white-on-midnight text (`color: var(--text)`), `box-shadow: 0 0 24px rgba(var(--apex-gold-rgb), .3)`. Used only for Apex affordances.
- Ghost: transparent bg, `var(--border)` outline → `var(--basic)` on hover.

**Cards** — `var(--surface)` background, `var(--border)` 1 px hairline border, 14 px radius. The per-tier radial glow overlay (see Skill Tiers above) is no longer applied by default; it appears **on hover only**, reinforcing that the tier glow is an affordance, not decoration.

**Callout** — dual-gradient tint: `linear-gradient(135deg, rgba(56,189,248,.08), rgba(167,139,250,.08))`, `--extra` title.

**Graph dialog** — `border: 1px solid rgba(56,189,248,.35)`, `box-shadow: 0 30px 100px rgba(0,0,0,.72), 0 0 55px rgba(56,189,248,.16)`, backdrop `rgba(0,0,0,.72) blur(6px)`. (The graph dialog is the one place glassmorphism earns its place — it is preserved here.)

---

## Skill Explorer

The skill explorer overlay (`#skillExplorer`) introduces per-level glow tokens, a shimmer animation for Level VI nodes, and a pulse animation for Level V nodes. These augment the rank colors defined above.

### Glow Tokens

| Token | Value | Level | Rank |
|---|---|---|---|
| `--glow-II`  | `0 0 8px #63cab7, 0 0 22px rgba(99,202,183,.35)`   | II  | Named |
| `--glow-III` | `0 0 10px #a78bfa, 0 0 26px rgba(167,139,250,.4)` | III | Evolved |
| `--glow-IV`  | `0 0 14px #e879f9, 0 0 32px rgba(232,121,249,.45)`| IV  | Hardened |
| `--glow-V`   | `0 0 18px #fbbf24, 0 0 40px rgba(251,191,36,.5)`  | V   | Transcendent |
| `--glow-VI`  | `0 0 20px #fbbf24, 0 0 50px rgba(251,191,36,.6), 0 0 80px rgba(56,189,248,.3)` | VI | Transcendent ★ |

Glow tokens use the same base colors as the rank system above. Tokens are applied as `box-shadow` values on `.flow-node[data-level="X"]` and `.se-hero-card[data-level="X"]`.

### Animations

| Animation | Element | Behavior |
|---|---|---|
| `se-pulse` / `flow-pulse-V` | Level V nodes | Gold `box-shadow` oscillates between `--glow-V` and a brighter `0 0 28px #fbbf24, 0 0 60px rgba(251,191,36,.65)` on a 2.4s loop |
| `se-shimmer` / `flow-shimmer-VI` | Level VI nodes | `border-color` cycles through cyan → purple → amber → fuchsia on a 3s loop, combined with the pulse |

### Explorer UI Tokens

Additional tokens used only in the explorer overlay (not added to `:root` — defined inline):

| Color | Hex | Use |
|---|---|---|
| Skill Explorer background | `rgba(3,7,18,.88)` | Topbar background (matches `--bg` + blur) |
| Install recommended border | `rgba(56,189,248,.35)` | Gaia install block highlight |
| Evidence class color | `#f59e0b` (`--ultimate`) | Evidence class labels (A/B/C) |
| Flowchart edge stroke | `rgba(56,189,248,.22)` | SVG bezier curves connecting flowchart rows |

---

## Rarity (computed)

Rarity is derived from real agent prevalence by `scripts/computeRarity.py` — never declared by contributors. It does not have a fixed color in the UI; rarity labels are rendered in `var(--muted)` text within skill pages and tree views.

---

## Skill Type Color Cycling

Skill types (Ultimate, Extra) get animated color-cycling effects wherever they appear. Basic skills remain static.

### Ultimate Skill Cycle (6-stop, ~4s loop)

Sequence: **blue → purple → gold → red → purple → green → (loop)**

```css
@keyframes tree-rainbow-glow{
  0%,100% { color:#38bdf8 }   /* blue */
  18%     { color:#a78bfa }   /* purple */
  36%     { color:#f59e0b }   /* gold */
  54%     { color:#ef4444 }   /* red */
  72%     { color:#c084fc }   /* purple */
  90%     { color:#34d399 }   /* green */
}
```

Each color step also carries a matching `text-shadow` glow at 80% opacity inner / 40% outer.

### Extra Skill Cycle (5-stop, ~4s loop, NO gold)

Sequence: **blue → purple → red → purple → green → (loop)**

```css
@keyframes tree-extra-glow{
  0%,100% { color:#38bdf8 }   /* blue */
  20%     { color:#a78bfa }   /* purple */
  40%     { color:#ef4444 }   /* red */
  60%     { color:#c084fc }   /* purple */
  80%     { color:#34d399 }   /* green */
}
```

### Application Rules

| Area | Ultimate | Extra | Basic |
|------|----------|-------|-------|
| Tree dialog lines | `tree-rainbow-glow` on `◆ Ultimate Skill:` label | `tree-extra-glow` on `◇ Extra Skill:` label | Static cyan glyph |
| Named Skills cards | Name text cycles `tree-rainbow-glow` | Name text cycles `tree-extra-glow` | No animation |
| Skill Graph labels | Canvas `cycleColor()` with `ULT_STOPS` | Canvas `cycleColor()` with `EXTRA_STOPS` | Static `PALETTE.basic` |
| Skill Graph nodes | Existing `drawNodeVI` (rainbow hue rotation) | New `drawNodeExtra` (subtle cycling glow) | Standard `drawNode` |

### Naming Conventions

- **Contributor names** (e.g., `karpathy`, `anthropic`): always red `#ef4444` everywhere
- **Skill names** after the slash: colored by rank level from `meta.json` level colors
- **Stagger**: each skill instance gets a unique `animation-delay` offset to avoid lockstep cycling

### Canvas Implementation (Skill Graph)

For canvas-drawn elements, a `cycleColor(stops, t)` utility interpolates between color-stop arrays using the shared `state.t` animation clock plus per-node phase offset:

```
ULT_STOPS  = [[56,189,248],[167,139,250],[245,158,11],[239,68,68],[192,132,252],[52,211,153]]
EXTRA_STOPS = [[56,189,248],[167,139,250],[239,68,68],[192,132,252],[52,211,153]]
```

Canvas glow via `ctx.shadowColor` / `ctx.shadowBlur = 8` on ultimate/extra labels.

### Implementation Branch

This design ships on branch **`design/skill-color-cycling`** (per branch naming convention: `design/` prefix for website design changes touching `docs/` HTML/CSS/JS).

---

## Brand Voice Tokens

These role tokens layer on top of the locked tier and rank colour tables. They define **brand-voice** roles — what carries meaning across every page — without re-allocating any tier/rank slot. Declared in `docs/css/styles.css` `:root`.

| Token | Value | Role / where used |
|---|---|---|
| `--honor-red` | `#ef4444` | Contributor handle colour. Used wherever a real contributor name appears (graph labels, plaques, named-skills cards, nav `Named` link). Never decorative. |
| `--honor-red-rgb` | `239, 68, 68` | RGB triplet for composing `rgba(var(--honor-red-rgb), α)` overlays and shadows. |
| `--apex-gold` | `#fbbf24` | 6★ / Ultimate / Diamond Seal mark accent. Used for Apex affordances only — the seal mark, the apex CTA pill, the Hall of Heroes apex glyph. Never decorative; never as a paragraph-level accent. |
| `--apex-gold-rgb` | `251, 191, 36` | RGB triplet for composing `rgba(var(--apex-gold-rgb), α)` glows, button shadows, ledger-strip highlights. |
| `--font-display` | `'EB Garamond', Georgia, serif` | Display face. Hero titles, plate headings, section h2 only. |
| `--font-body` | `'Bricolage Grotesque', Inter, system-ui, sans-serif` | Body face. All paragraph and UI text. |
| `--font-mono` | `'Departure Mono', 'JetBrains Mono', ui-monospace, monospace` | HUD / code face. Ledger strip, command blocks, Departure-Mono numerals, Plate-numbering. |
| `--diamond-seal-stroke` | `1.5` | Stroke-width unit for the Diamond Seal brand mark. Unitless multiplier applied at render time. |

Honor Red and Apex Gold are the **two carry-everything brand roles**. Tier tokens (`--basic`, `--extra`, `--ultimate`) remain reserved for their tier roles in the graph, badge, and rank plate — they are not repurposed as decorative accents anywhere on the new surfaces.

---

## Hunter's Atlas Brand Lane

Gaia's public surface (`gaia.tiongson.co`) is the **Hunter's Atlas**: a Sacred-Atlas × Solo-Leveling guild registry where contributing devs feel their repo is a main character earning evidence-based rank, and where claiming an Ultimate carries the prestige of going on the permanent record. The voice register is **Half-Merged** — primary labels stay truthful (commands, schema, evidence, named contributors) while section titles and ornamental copy carry ceremonial verbs (Initiate's Rite, Ascension Cycle, Hall of Heroes, The Codex).

On top of the locked tier and rank colour tokens, two brand-voice tokens do the carry-everything work: **Honor Red (`--honor-red`)** is reserved for contributor handles; **Apex Gold (`--apex-gold`)** is reserved for 6★/Ultimate/Diamond-Seal moments and Apex-only affordances. Tier and rank colour tokens, Level VI shimmer, the graph canvas geometry, the Skill Explorer glow tokens, and the Ultimate/Extra cycling animations are all hard-locked and survive unchanged into this lane.

The 3D canvas (`canvas3d`) is **preserved** as a secondary view — repurposed as an ambient parallax background behind the 2D graph hero, and reachable as the primary view via a `⇄ Field view` toggle. The 2D skill graph is the primary hero. The Diamond Seal mark (`◇G` lock-up) is the brand mark; the apex `◆` glyph remains free for its tier role. Per `CONTEXT.md:137-139`, "HUD" is internal-only nomenclature (used in code class names like `.hud-trigger` and file names like `hud-toggle.js`); user-facing copy uses **Field view** for the toggle and **Registry** for any view of the public skill graph.
