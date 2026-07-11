# DESIGN.md — Gaia Visual Design Language

> Brand personality, anti-references, and the accessibility baseline live in [`PRODUCT.md`](PRODUCT.md). This document is the visual-token + motion spec layer; the canonical glossary and banned-synonyms lint live in [`CONTEXT.md`](CONTEXT.md).

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

Canonical token values are emitted by `scripts/generateCssTokens.py` to `docs/css/tokens.css` from `registry/gaia.json.meta.typeColors`. See that file for the authoritative CSS custom property definitions. The tier/rank names and semantic roles are documented in the sections below.

> **Never hardcode hex in CSS or JS.** The legacy short tokens (`--basic`, `--extra`, `--unique`, `--ultimate`) are kept as aliases so older selectors keep working; the canonical names are `--tier-basic`, `--tier-extra`, `--tier-unique`, `--tier-ultimate` (plus `-rgb`, `-bg`, `-border`, `-symbol` variants).

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

Skills level up from 0★ → 6★. Each rank has a distinct RPG-inspired color. Canonical hex values and background tints are defined in `src/gaia_cli/formatting.py::RANK_COLORS` (Python source of truth) and in `docs/css/tokens.css` (`--rank-0` … `--rank-6`). For rank labels and significance, see `META.md §1.1`.

Rank sequence: **Basic (0★) → Awakened (1★) → Named (2★) → Evolved (3★) → Hardened (4★) → Transcendent (5★) → Apex (6★)**. The color sequence intentionally mirrors an RPG rarity ramp: neutral → cold → teal → violet → pink → gold, with the Apex level doubling its background opacity.

> **Class column deprecated.** The legacy letter suffixes (D / C / B / A / S / SS) are retained in old code paths only. Generated surfaces no longer emit them — see `plaque-reveal.js`, `generateProfilePages.py`, `generateOgCards.py`. Evidence `class` is fully deprecated per the ratified G7 Trust Taxonomy RFC (`META.md §2.1`); new evidence carries `type` + `grade` instead. The visitor-facing label is **rank name + star count** (e.g. "Hardened · 4★").

---

## Starless (generic) references

Generic skill references are **starless** — rank-less taxonomy nodes that carry no stars of their own (stars live only on their named-skill children; see `CONTEXT.md` § Starless). Because they hold no rank, they get no rank colour and no glow token. Instead, wherever a starless reference appears in the UI it renders as *generic* in **italic, greyed-out** styling:

- Font style: italic.
- Colour: `var(--muted)` (`#64748b`) — the secondary / subdued text token, never a tier or rank colour.
- The word "generic" is retained as the technical descriptor alongside the *starless* brand noun.

A starless ref's *effective rank* (the top star among its named variants) may be shown beside it for context, but the reference glyph and label themselves stay muted and italic so the eye reads them as taxonomy, not as an earned rank.

---

## Evidence Grades

Evidence items are evaluated and assigned quality grades. The grade palette now exposes semantic token labels in `docs/css/tokens.css` (`--evidence-platinum`, `--evidence-gold`, `--evidence-silver`, `--evidence-bronze`) while preserving the legacy `--grade-S` / `--grade-A` / `--grade-B` / `--grade-C` aliases for existing UI hooks.

Their visual representations use horizontal metric bars with the following styling rules:

| Grade | Label | Background Texture | Text Color |
|---|---|---|---|
| S | Platinum | Stylized tempered blue-iridescent titanium (`#ecf4ff` to `#a5c7eb`) with radial highlights and animated shimmer sweep | `#0b2545` (Deep navy contrast) |
| A | Gold | `var(--grade-A)` base with fine linear brush and static polished reflection | `#451a03` (Deep brown) |
| B | Silver | Darker matte steel/slate grey (`#8a99ad` to `#475569`) with coarser linear brush and matte reflection | `#0f172a` (Dark slate) |
| C | Bronze | `var(--grade-C)` base with rough linear texture and tarnished, minimal reflection | `#fffbeb` (Light warm) |
| - | Ungraded | `transparent` with `var(--border)` stroke (no texture) | `var(--muted)` |

> **Note:** The grades utilize multi-layered CSS repeating gradients (radial for Platinum, linear for others) and horizontal SVG fractal noise overlays to achieve a metallic texture that descends in polish and detail according to the grade. Platinum adds an iridescent tempered look (violet, cyan, and gold hints) and an animated shimmer sweep for the highest hierarchy, while Silver is deliberately darkened to maximize contrast against Platinum, and Bronze carries a tarnished, rougher appearance. Evidence bars use `var(--font-mono)` to emphasize their role as metric ledgers.
>
> **Design Quirk:** Evidence grade visual elements are strictly rectangular (e.g., metric bars, rectangular badges, or linear tracks) and must **never** be rendered as circular grade badges or circular graphs (such as doughnut charts). This rule applies to all visual representations of evidence, including the main library metrics, individual report badges, and overall distribution charts.

---

## Evidence Type Pills

`.ev-type-pill` chips label each evidence entry by type. All `color:` values must use CSS tokens — never hardcode hex. Background and border `rgba()` values are intentionally retained as raw rgba (the token `-bg` and `-border` variants use different opacities and would not be drop-in replacements).

| Evidence type | `color:` token | Semantic mapping |
|---|---|---|
| `repo`, `peer-review`, `repo-own` | `var(--tier-basic)` | Basic-tier blue (`#38bdf8`) |
| `github-stars`, `fusion-recipe`, `github-stars-own` | `var(--tier-ultimate)` | Ultimate amber (`#f59e0b`) |
| `proxy-containment` | `var(--tier-unique)` | Unique deep violet (`#7c3aed`) |
| `verifier-attestation` | `var(--rank-4)` | Rank-4 fuchsia (`#e879f9`) |
| `benchmark-result`, `arxiv` | `var(--tier-extra)` | Extra purple (`#c084fc`) |
| `self-attestation` | `var(--rank-0)` | Slate / unawakened (`#94a3b8`) |
| `social-signal` | `#34d399` | Emerald green — not in the banned-hex set; no current token alias |

The `social-signal` green (`#34d399`) is not in `tokens.css` and is not on the Guard A banned-hex list. If a token is added later, update this table and the selector in `docs/css/styles.css`.

---

## Level 6★ — Apex Special Rendering

6★ (Apex) nodes bypass `drawNode` entirely and use `drawNodeVI`, which runs every animation frame using the shared `state.t` clock:

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

**Hero titles** — solid `var(--text)` in EB Garamond at weight 600 (`var(--font-display)`). No gradient text. Emphasis words (e.g., "rare", "earned") may carry a single hairline gold underline using `border-bottom: 1px solid var(--apex-gold)` or an equivalent inline `<span>` underline accent. The homepage's exact `Gaia Skill Tree` title may set `Skill Tree` in solid Apex Gold as part of the World Tree brand lock-up. The previous three-stop tier-gradient sweep on titles is retired.

**World Tree brand-mark exception** — the homepage World Tree is Gaia's living brand mark, generated from the canonical DAG rather than added as decoration. In its front-facing hero pose, every real node and edge may use one tonal gold family built from low-alpha `--apex-gold` / `--apex-gold-rgb` values. Root, trunk, ordinary branches, and buds stay antique or muted; full-strength `--apex-gold`, larger diamond geometry, and rings remain reserved for Ultimate/Apex emphasis. The fine sakura branch attached to the `Gaia Skill Tree` title is a decorative typesetting cue only, visually lighter than the graph and never counted as a skill or prerequisite edge. This exception applies only to the complete World Tree silhouette and does not license gold paragraph copy, generic gold UI, or removal of non-colour rank signals. When the same objects enter **Tree Explorer**, they recover the current canonical tier/rank colours through the visual-role adapter while Ultimate and Apex identities remain explicit by label and geometry.

**Hero tier gradient (retained, scoped)** — the three-stop sweep
```
linear-gradient(135deg, #38bdf8 0%, #c084fc 50%, #f59e0b 100%)
```
is retained only on legacy graph surfaces that already use it. The homepage World Tree, its `Explore in 3D` control, titles, and body copy do not use this sweep.

**Buttons**
- Primary: solid `var(--apex-gold)` background on a midnight (`var(--bg)`) border, white-on-midnight text (`color: var(--text)`), `box-shadow: 0 0 24px rgba(var(--apex-gold-rgb), .3)`. Used only for Apex affordances.
- Ghost: transparent bg, `var(--border)` outline → `var(--basic)` on hover.

**Cards** — `var(--surface)` background, `var(--border)` 1 px hairline border, 14 px radius. The per-tier radial glow overlay (see Skill Tiers above) is no longer applied by default; it appears **on hover only**, reinforcing that the tier glow is an affordance, not decoration.

**Callout** — dual-gradient tint: `linear-gradient(135deg, rgba(56,189,248,.08), rgba(167,139,250,.08))`, `--extra` title.

**Graph dialog** — `border: 1px solid rgba(56,189,248,.35)`, `box-shadow: 0 30px 100px rgba(0,0,0,.72), 0 0 55px rgba(56,189,248,.16)`, backdrop `rgba(0,0,0,.72) blur(6px)`. (The graph dialog is the one place glassmorphism earns its place — it is preserved here.)

**Hall of Heroes homepage band** (`docs/index.html`) — the homepage Hall is a full-width prestige proof immediately after the hero, before the Trust leaderboard and contributor paths. It uses a two-column atlas composition: left-side ceremony (`Registry honors`, oversized EB Garamond title, short ledger pills, Hall/Named/Contributor links) and right-side generated plaque rail (`#hohPlates`). The section is not a generic card grid: it is a dark ledger band with gold/red atmospheric fields, a thin vertical rail, and asymmetric spacing. Apex Gold is permitted here only for the mark, rail, primary Hall link, and 6★/Ultimate emphasis; Honor Red remains reserved for contributor identity.

**Hall of Heroes gallery page** (`docs/heroes/index.html`) — the dedicated Hall page is a theatrical scroll gallery, not a list page. The first viewport is a single centered title stage, followed by one full-viewport `.hero-stage` per contributor. Each stage centers a crest/card composition with avatar art inside a square front plate, a rotated diamond backplate, a rank/tier seal, and Trust Magnitude metadata. The fixed left ledger rail is the navigation model: avatar, glyph, contributor name, byline, active progress, and prev/next controls. Level 4 uses rank-4 fuchsia accents; 5★/6★ use Apex Gold; named contributor handles still inherit Honor Red via plaque and modal primitives.

**Hall share modal** — the Hall share/download modal is shared between the homepage and `/heroes/` page. It renders the OG plaque in a fullscreen stage with compact icon controls, an identity confirmation pill, optional README badge overlay, and PNG/SVG download choices. Treat this as a production component family, not a decorative overlay: focus states, `aria-label`s, reduced-motion behavior, and path-depth differences (`assets/icons.svg` vs `../assets/icons.svg`) must remain intact.

**Deferred-surface WIP banner** — when a user-visible surface ships in an intentional bridge state that a later sprint will replace (per `founder/GAIA_ROADMAP v*.md`), disclose the state with a `.wip-banner` element between `<nav>` and `<main>`. Uses `--font-mono` at `0.78rem`, a subtle `rgba(var(--evidence-gold-rgb), 0.06)` tint on `rgba(var(--evidence-gold-rgb), 0.28)` border, one uppercase `.wip-tag` label (`◇ Interim rendering` or equivalent), and one prose `.wip-body` sentence linking to the tracking issue and naming what is frozen (typically the JSON contract) versus what is provisional (the rendering layer). Full policy in `CLAUDE.md` § Deferred-surface convention; reference implementation in `scripts/contentEngine/templates/report.html.j2`. The banner is removed by the port; do not treat it as permanent chrome.

**Fixed-nav clearance** — the site nav is `position: fixed` at ~58px tall (rule at `docs/css/styles.css` L299–315). Every top-level page container that sits directly under `<body>` provides its own top clearance using the value ladder `padding-top: 5rem` at base and `6rem` (thin strips) or `8rem` (full page shells) at `>= 768px`. Nothing offsets automatically. Reference implementations: `.bench-shell`, `.reports-shell`, `.trending-main`, `.wip-banner`. Full policy in `CLAUDE.md` § Fixed-nav clearance. Anti-pattern: the `margin-top: -Npx + padding-top: calc(... + Npx)` trick on `.profile-back-row`; do not extend it to new surfaces.

---

## Skill Explorer

The skill explorer overlay (`#skillExplorer`) introduces per-level glow tokens, a shimmer animation for 6★ (Apex) nodes, and a pulse animation for 5★ (Transcendent) nodes. These augment the rank colors defined above.

### Glow Tokens

| Token | Value | Level | Rank |
|---|---|---|---|
| `--glow-II`  | `0 0 8px #63cab7, 0 0 22px rgba(99,202,183,.35)`   | 2★  | Named |
| `--glow-III` | `0 0 10px #a78bfa, 0 0 26px rgba(167,139,250,.4)` | 3★  | Evolved |
| `--glow-IV`  | `0 0 14px #e879f9, 0 0 32px rgba(232,121,249,.45)`| 4★  | Hardened |
| `--glow-V`   | `0 0 18px #fbbf24, 0 0 40px rgba(251,191,36,.5)`  | 5★  | Transcendent |
| `--glow-VI`  | `0 0 20px #fbbf24, 0 0 50px rgba(251,191,36,.6), 0 0 80px rgba(56,189,248,.3)` | 6★ | Apex |

Glow tokens use the same base colors as the rank system above. Tokens are applied as `box-shadow` values on `.flow-node[data-level="X"]` and `.se-hero-card[data-level="X"]`.

### Animations

| Animation | Element | Behavior |
|---|---|---|
| `se-pulse` / `flow-pulse-V` | 5★ (Transcendent) nodes | Gold `box-shadow` oscillates between `--glow-V` and a brighter `0 0 28px #fbbf24, 0 0 60px rgba(251,191,36,.65)` on a 2.4s loop |
| `se-shimmer` / `flow-shimmer-VI` | 6★ (Apex) nodes | `border-color` cycles through cyan → purple → amber → fuchsia on a 3s loop, combined with the pulse |

### Explorer UI Tokens

Additional tokens used only in the explorer overlay (not added to `:root` — defined inline):

| Color | Hex | Use |
|---|---|---|
| Skill Explorer background | `rgba(3,7,18,.88)` | Topbar background (matches `--bg` + blur) |
| Install recommended border | `rgba(56,189,248,.35)` | Gaia install block highlight |
| Evidence class color | `#f59e0b` (`--ultimate`) | Evidence grade labels (S/A/B/C) — see `META.md §2.1` |
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
| `--apex-gold` | `#fbbf24` | 6★ / Ultimate / Diamond Seal mark accent. Used at full strength for Apex affordances only — the seal mark, apex CTA, Hall glyph, and Ultimate/Apex marks inside the World Tree. Lower World Tree structure may use alpha-derived values under the narrow brand-mark exception above. Never decorative; never as a paragraph-level accent. |
| `--apex-gold-rgb` | `251, 191, 36` | RGB triplet for composing `rgba(var(--apex-gold-rgb), α)` glows, button shadows, ledger-strip highlights. |
| `--font-display` | `'EB Garamond', Georgia, serif` | Display face. Hero titles, plate headings, section h2 only. |
| `--font-body` | `'Bricolage Grotesque', Inter, system-ui, sans-serif` | Body face. All paragraph and UI text. |
| `--font-mono` | `'Departure Mono', 'JetBrains Mono', ui-monospace, monospace` | HUD / code face. Ledger strip, command blocks, Departure-Mono numerals, Plate-numbering. |
| `--diamond-seal-stroke` | `1.5` | Stroke-width unit for the Diamond Seal brand mark. Unitless multiplier applied at render time. |

Honor Red and Apex Gold are the **two carry-everything brand roles**. Tier tokens (`--basic`, `--extra`, `--ultimate`) remain reserved for their tier roles in the graph, badge, and rank plate — they are not repurposed as decorative accents anywhere on the new surfaces.

---

## Hunter's Atlas Brand Lane

Gaia's public surface (`gaiaskilltree.com`) is the **Hunter's Atlas**: a Sacred-Atlas × Solo-Leveling guild registry where contributing devs feel their repo is a main character earning evidence-based rank, and where claiming an Ultimate carries the prestige of going on the permanent record. The voice register is **Half-Merged** — primary labels stay truthful (commands, schema, evidence, named contributors) while section titles and ornamental copy carry ceremonial verbs (Initiate's Rite, Ascension Cycle, Hall of Heroes, The Codex).

On top of the locked tier and rank colour tokens, two brand-voice tokens do the carry-everything work: **Honor Red (`--honor-red`)** is reserved for contributor handles; **Apex Gold (`--apex-gold`)** is reserved for 6★/Ultimate/Diamond-Seal moments and Apex-only affordances. Tier and rank colour tokens, 6★ Apex shimmer, the graph canvas geometry, the Skill Explorer glow tokens, and the Ultimate/Extra cycling animations are all hard-locked and survive unchanged into this lane.

The World Tree uses one `canvas3d` and one stable set of graph objects. Its default hero pose is front-facing, visually 2D, and gold. **Explore in 3D** expands that same canvas to fullscreen while the objects gain depth, canonical tier/rank colour, orbit controls, hover states, and collection tools; exit reverses the morph to the exact hero pose. **Field view is deprecated**: `?tree=1` is canonical, while `?field=1` and `?hud=1` may remain compatibility aliases to Tree Explorer. The explorer is tree-only—no semantic/spectral constellation mode or crossfade to a second renderer. The Diamond Seal mark (`◇G` lock-up) remains the brand mark; the apex `◆` glyph remains free for its tier role. "HUD" may survive only as internal legacy nomenclature in class and file names.

## Anti-references & accessibility (see PRODUCT.md)

Visual guardrails — generic AI-startup dark mode, SaaS hero-metric dashboards, gamification-as-product, decorative glassmorphism, gradient text, and hype-heavy marketing copy — are enumerated in [`PRODUCT.md`](PRODUCT.md#anti-references). The accessibility baseline (WCAG AA; never symbol-alone or color-alone tier signal; `prefers-reduced-motion` for 6★ Apex shimmer, the Naming Reveal cinematic, and the Ascension Cycle diagram; screen-reader-friendly CLI renders) lives in [`PRODUCT.md`](PRODUCT.md#accessibility--inclusion). Don't restate them here — link only, so the spec doesn't drift.

---

## Motion — Parallax and Scroll Animation

### Parallax (continuous scroll)

Use for background image layers on signature sections only. The primary use case is a dark-tinted asset layer behind a content-heavy panel that benefits from depth.

**Spec:**
- Speed ratio: 0.45× (background moves at 45% of scroll speed)
- Implementation: `requestAnimationFrame` + `translateY` — never `background-attachment: fixed` (breaks on iOS Safari)
- Background element: absolutely positioned, `inset: -30% 0` to allow vertical travel without white-edge gaps, `will-change: transform`
- Overlay: `rgba(3,7,18, 0.82)` minimum for text readability; `0.88` on mobile
- Disable below 768px: use `window.matchMedia('(min-width: 768px) and (prefers-reduced-motion: no-preference)')` guard
- `prefers-reduced-motion`: skip the scroll listener entirely when reduced motion is preferred

### Scroll-triggered entrance (one-shot)

Use for card grids and tile lists where items appear on first scroll into view. Not continuous — fires once.

**Spec:**
- Animation: `opacity: 0 → 1` + `translateY(12px) → 0`, duration `0.35s ease-out`
- Stagger: `0.08s` delay per item
- Default state: `opacity: 0` in CSS so items are invisible before animation fires
- `prefers-reduced-motion`: reset to `opacity: 1; animation: none`

### What does NOT get parallax

- Hero sections (the text IS the content; parallax would compete)
- Navigation and footer
- Form elements or interactive controls
- Any element the user is actively scrolling to read

---

## Mobile-First Construction

All new CSS is written from the 320px baseline upward. `min-width` breakpoints only. `max-width` queries are reserved for component-level overrides (not layout).

### Breakpoint scale (project-wide)

| Token | Value | Use |
|---|---|---|
| `sm` | `480px` | 2-column card grids |
| `md` | `768px` | Full-width → constrained layout, parallax enable |
| `lg` | `1024px` | Sidebar patterns, wide grids |
| `xl` | `1280px` | Max-content column widths |

### Mobile-specific rules

- Cards and panels with `border-radius` become full-bleed on `< 480px` (no radius, negative margin to escape padding, no left/right border)
- Parallax disabled on mobile (static background, overlay lifted)
- Font sizes use `clamp()` with a floor that works at 320px
- Touch targets minimum 44×44px
- No `position: fixed` for decorative elements on mobile (performance)
