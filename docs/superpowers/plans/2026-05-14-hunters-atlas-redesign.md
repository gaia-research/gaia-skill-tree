# Hunter's Atlas — Gaia Site Redesign Plan

> **For agentic workers:** This plan is the output of an `/impeccable shape` discovery grilled with `grill-with-docs`. Use `/impeccable craft` or sub-agent-driven execution to implement. The canonical glossary lives at `/CONTEXT.md`; design tokens and locked schema sit in `/DESIGN.md` and must not be moved without an ADR.

**Goal:** Full visual overhaul of the public Gaia site (`docs/`) at gaiaskilltree.com. Re-anchor the brand from "dev-tool SaaS landing page" to **Hunter's Atlas** — a sacred-atlas × Solo-Leveling guild-registry surface where contributing devs feel their repo is a main character earning evidence-based rank, and where claiming an Ultimate carries the prestige of going on the permanent record next to Karpathy and Pocock.

**Branch:** Implementation on `design/hunters-atlas` (per CLAUDE.md `design/` prefix for `docs/` HTML/CSS/JS work). This planning artifact + glossary land on `docs/hunters-atlas-plan` first.

**Tech stack:** Static HTML/CSS/JS in `docs/`. No build step. Typography pulled from Google Fonts: EB Garamond, Bricolage Grotesque, Departure Mono — all OFL/free, all off the impeccable reflex-reject list. Site is GitHub-Pages-served from `docs/`.

---

## 0. Decisions locked through grilling

| Axis | Lock | Source |
|---|---|---|
| Register | Brand (gaiaskilltree.com is a marketing surface; design IS the product). | `/impeccable` setup |
| Lane | **Hunter's Atlas** — Sacred Atlas × Solo Leveling guild registry. | User Q1 |
| Voice register | **Half-Merged** — truthful primary labels; fantasy verbs and ornamental section titles. | User Q2 |
| Typography | **Scholar's Plate** — EB Garamond (display) · Bricolage Grotesque (body) · Departure Mono (HUD/code). All OFL/free. | User Q3 |
| Brand mark | **Diamond Seal Monogram** — `◇G` lock-up. Apex `◆` glyph stays free for tier role. | User Q4 |
| Homepage IA | **Two Doors** — graph hero (2D primary, 3D HUD secondary), two CTA doors, dual-path columns reconverging at Hall of Heroes → Ascension Cycle. | User Q5 (revised from Graph-IS-The-Site) |
| Plaque artifact | **Priority D > B > C**: animated naming reveal first, contributor profile page second, OG share card third. README badge dropped. | User Q6 |

**Carry-overs (hard-locked, must survive):**

1. Rank / tier color tokens (DESIGN.md Color Palette + Skill Tiers + Rank System tables).
2. Level VI Transcendent ★ "black-hole" rainbow shimmer (`drawNodeVI` canvas implementation + `--glow-VI` token).
3. The canonical skill graph SVG (`registry/gaia.svg`) and interactive canvas (`registry/gaia.json` driven).
4. **The 3D HUD** — the existing `canvas3d` rotating-dots hero canvas. NOT REMOVED. Repurposed as secondary view (ambient parallax behind 2D primary, or accessible via a toggle that swaps prominence). May be recoloured to muted gold-on-midnight when ambient.
5. Ultimate / Extra cycling animations (`tree-rainbow-glow`, `tree-extra-glow`, `cycleColor()` canvas util).

**Net-new visual primitives:**

- Diamond Seal Monogram mark (favicon, nav, OG).
- Honor Red (`#ef4444`) and Apex Gold (`#fbbf24`) brand-role tokens (on top of existing tier tokens).
- Hall of Heroes plate strip.
- Ascension Cycle circular diagram.
- 2D ↔ 3D HUD toggle interaction.
- The Plaque visual system (three render modes: animated naming reveal · profile page surface · OG share card).

## 1. Feature summary

The redesign reframes Gaia from "dev-tool landing page" into a **hunter's guild registry**: a serious, ledger-faithful surface where devs see their repo as a main character earning evidence-based rank, and where claiming an Ultimate carries the prestige of going on the permanent record next to Karpathy and Pocock. Schema (tier/rank colors, graph rendering, Level-VI shimmer, the 3D HUD canvas) is preserved untouched; everything else — typography, layout, copy voice, mark, motion, page IA — is replaced.

## 2. Primary user action

**Pick a door.** A visitor lands and resolves one of two motivations within 10 seconds:

- *"I want my repo on the map"* → **Register your repo** (Path A: Initiate's Rite).
- *"I want one of those unclaimed Ultimates with my name on it"* → **Claim an Ultimate** (Path B: Available Ultimates).

Both routes converge on the same end-state: contributor handle in honor red on the canonical registry, eventually a Plaque earned, eventually Apex.

## 3. Design direction

**Color strategy: Committed.** Midnight ink ground (`--bg #030712`, preserved) is the stage. Two carry-everything brand roles do the work: **Honor Red `#ef4444`** for contributor handles, **Apex Gold `#fbbf24`** for 6★/Ultimate moments. Tier colors (sky/teal/violet/fuchsia/amber) remain strictly reserved for their tier roles in the graph and the Hunter Ranks plate — never repurposed as decorative accents. No gradient text. No frosted glass as decoration (kept only on the graph-dialog chrome where it earns its place).

**Scene sentence:** *A junior dev at 11pm on a 27-inch monitor, scrolling through the Hunters Association ranking board, weighing whether they've earned the right to claim an Ultimate yet, the apex glyph glowing somewhere in the periphery.* Forces dark theme (preserved), forces ceremoniousness over playfulness, forces a HUD-like persistent chrome.

**Named anchor references:**

1. **Solo Leveling Hunters Association rank board** — gravity of a public ledger that confers status; system-UI moments for naming reveals.
2. **19th-century natural-history atlas plates** — typographic seriousness, ornamental rule, plate numbering language ("Plate XXXVII"), engraved ink quality.
3. **Hades / Returnal HUD chrome** — gold-on-midnight ledger stats, Departure Mono numerals, persistent peripheral information that feels earned not gamified.

## 4. Scope

| Dimension | Decision |
|---|---|
| Fidelity | **Production-ready.** Ships to gaiaskilltree.com. |
| Breadth | Home page (full replacement) · `how-we-do-things.html` → renamed **The Codex** (reskinned, content preserved) · existing graph dialog (chrome reskinned, mechanics identical) · favicon · OG card · Plaque system (Priority D, B, C). |
| Interactivity | Shipped-quality. All interactions wired to real data from `registry/gaia.json` and `registry/named-skills.json`. |
| Time intent | Polish until ships. |
| Out of scope | README badge plaques (dropped from scope); CLI changes; new registry schema; mobile app; analytics infra. |

## 5. Layout strategy

```
┌──────────────────────────────────────────────────────────────────┐
│ ◇G GAIA           Registry · Hall of Heroes · The Codex · Tree   │  sticky nav, midnight + 1px hairline
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│       ┌──────── 3D HUD (canvas3d) ────────┐                     │  ambient parallax layer
│       │  ·  ·   recoloured: muted gold     │                     │  slow rotation, low opacity
│       │ ·     · on midnight, low opacity   │                     │
│       │  ·  ·                              │                     │
│       └────────────────────────────────────┘                     │
│                                                                  │
│              [ 2D skill graph, 70vh, panning ]                   │  primary layer, interactive
│           apex glow at centre · nodes reactive                   │  graph dialog mechanic kept
│                                       [ ◆ Open full graph ]      │  floating pill, bottom-right
│                                       [ ⇄ View as HUD ]          │  toggle to swap primary/secondary
│                                                                  │
│       Skills are catalogued. Names are earned. Apex is rare.     │  EB Garamond display, 3-beat
│                                                                  │
│       An evidence-backed atlas of agent capabilities.            │  Bricolage Grotesque subhead
│       Bring your repo, claim your name.                          │
│                                                                  │
│        ┌───────────────────┐    ┌───────────────────┐           │
│        │ → Register your   │    │ ◆ Claim an        │           │  two doors, equal weight
│        │   repo            │    │   Ultimate        │           │  midnight cards + hairline
│        │ 3 commands · 5min │    │ 6 currently       │           │  tier-glow ring on hover
│        └───────────────────┘    └───────────────────┘           │
│                                                                  │
│   ── 133 SKILLS · 32 NAMED · 1 APEX · UPDATED 14 MAY 2026 ──    │  Departure Mono ledger strip
│                                                                  │  each stat clickable, filters
│                                                                  │  graph dialog
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ── PATH A ─────────────────┐  ┌──────────────── PATH B ──      │
│   The Initiate's Rite        │  │  Available Ultimates           │
│                              │  │                                │
│   I.   pip install gaia-cli  │  │  ◆ /autonomous-research        │
│   II.  gaia init             │  │  ◆ /full-stack-developer       │
│   III. gaia scan             │  │  ◆ /multi-agent-orchestration  │
│                              │  │  ◆ /recursive-self-improvement │
│   Bond your agent (MCP) →    │  │  ◆ ...                         │
│                              │  │  [ propose a new ultimate ]    │
└──────────────────────────────┴──┴────────────────────────────────┘

                    ── HALL OF HEROES ──
        [ plaque ] [ plaque ] [ plaque ] [ plaque ] [ plaque ]
          karpathy   pocock    anthropic  ...      ...

                  ── ASCENSION CYCLE ──

         Register → Scan → Rank up → Name → Fuse → Apex
              (circular diagram, hoverable stages)

                       ── footer ──
       github · MIT · v3.9.2 · The Codex · Your Tree
```

**Rhythm:** generous vertical breathing room (clamp 6vw–10vw between sections), tight clustering inside cards (12–16px). Hero is composed asymmetrically — graph dominates, copy and doors anchor below. No centered-stack hero. Path columns are deliberately unequal weight: Path A is wider (more common journey); Path B narrower but its tier-glow ring on hover and gold apex glyphs make it the more magnetic.

**Sticky nav** sits on a 1px hairline divider in `var(--border)`; no glassmorphism. Mark + wordmark at left, four destinations at right. Mobile collapses to a sheet menu.

## 6. Hero composition (specific to HUD lock)

- **Layer 1 (back, ambient):** the existing 3D HUD (`#canvas3d`) — kept as the ambient parallax background, recoloured to muted gold-on-midnight when ambient. Rotation slowed to ~0.1 rad/s. Opacity 0.18. Reads as a slowly drifting constellation.
- **Layer 2 (front, primary):** the 2D decision-tree graph — interactive, panning at 0.5°/s idle, hoverable, clickable. The existing `skill-graph.js` canvas drawing is the source of truth.
- **Toggle:** the `⇄ View as HUD` pill (Departure Mono, gold-on-midnight) swaps the two layers' prominence. When activated, 3D HUD takes the front layer with its original tier-colored saturation, 2D fades to back at 0.2 opacity. Reverts on second click or Esc. This preserves the existing 3D work without burying it.
- **Mobile:** only the 2D graph as a static SVG; the 3D HUD does not run.

## 7. Key states

| Surface | States |
|---|---|
| Hero (default) | 2D primary + 3D ambient back; idle pan; Level VI shimmer continuous |
| Hero (HUD mode) | 3D primary saturated + 2D faded back; toggle pill shows active state |
| Graph node hover | mini-tooltip with skill name + tier glyph + contributor (honor red if named) |
| Graph node click | opens existing graph dialog at that node |
| CTA doors | default · hover (tier glow ring + 1px gold border) · pressed · keyboard-focused |
| Ledger stats | default · hover (underline) · click → graph dialog filtered to that bucket |
| Path A rite | pristine · command-copied (micro-flash + "copied" toast) |
| Path B unclaimed | ≥1 unclaimed (default) · all claimed (graceful "propose a new one" empty state) |
| Hall of Heroes | ≥5 heroes (default) · <5 (larger plate sizes fill row) |
| Plaque (naming reveal) | trigger (skill just named) → 4s cinematic → static plate at rest |
| Ascension Cycle | static default · hover stage (halo + caption) · reduced-motion (no motion) |
| First load | 3s skippable reveal sequence (cookie-gated to play once per session) |
| Reduced motion | reveal disabled · idle pan disabled · Level VI shimmer kept (locked) · cycling glows paused |
| Mobile | linear scroll of every section · graph as static SVG · doors stack · 3D HUD disabled |

## 8. Interaction model

- **Idle:** 2D graph pans 0.5°/s around apex; 3D HUD drifts at 0.1 rad/s behind it; Level VI shimmer continuous (locked); Extra Skill labels cycle per locked `tree-extra-glow`.
- **First load:** optional 3s reveal — 3D HUD rotates into view, 2D nodes fade up, two display lines reveal in sequence, then CTAs and ledger strip appear. Skippable on any click. Cookie-gated to play once per session.
- **Scroll reveals:** staggered fade-up of sections (ease-out-quart, 600ms, 80ms stagger). Disabled under reduced motion.
- **Hover graph node:** dock-style tooltip 16px from cursor; Named handles in honor red.
- **Click graph node:** graph dialog opens centred on that node.
- **Click `◆ Open full graph`:** graph dialog opens full-bleed; Level VI shimmer reads through more strongly.
- **Click `⇄ View as HUD`:** layers swap; 3D becomes primary at full saturation; 2D fades to background.
- **Click CTA door:** smooth scroll (ease-out-quart, 700ms) to its path column with brief gold underline pulse on column title.
- **Click ledger stat:** graph dialog opens pre-filtered to that bucket (`?filter=named`, etc.).
- **Copy command:** clipboard write + micro-flash on `pre` block + Departure Mono "copied" pill (~1.2s).
- **Hover Path B Ultimate:** tier-glow ring pulses once; reveals `Claim →` button on right.
- **Hover Hall of Heroes plate:** plate elevates (transform-only); contributor's named skill name reads in honor red after 200ms delay.
- **Hover Ascension Cycle stage:** stage halo + Bricolage caption beneath circle explains what happens.

## 9. Content requirements

| Surface | Content |
|---|---|
| Hero display | "Skills are catalogued. Names are earned. Apex is rare." (3-beat ledger cadence, EB Garamond, line-height 1.1, "rare" carries a thin gold underline) |
| Hero subhead | "An evidence-backed atlas of agent capabilities. Bring your repo, claim your name." (Bricolage Grotesque) |
| Door 1 | Label: "Register your repo" · caption: "3 commands · 5 minutes" |
| Door 2 | Label: "Claim an Ultimate" · caption: live ("6 currently unclaimed" from `registry/gaia.json`) |
| Ledger stats | Live, derived: `{N} SKILLS · {M} NAMED · {K} APEX · UPDATED {ISO date}`. Departure Mono, all-caps, tracked +6%. |
| Path A copy | "I. Install" / "II. Initialise" / "III. Scan" — Roman numerals in Departure Mono, headings in EB Garamond, body in Bricolage. Existing commands preserved. |
| Path B list | Tier glyph + skill ID + `Claim →` button per row. Empty state: "All Ultimates currently claimed. Propose a new one →" |
| Hall of Heroes | Five plates; each renders contributor handle in honor red + apex glyph + named skill name. Live from `registry/named-skills.json`, ranked by stars then origin date. |
| Ascension Cycle | Six stage labels in Bricolage caps, tracked: Register · Scan · Rank up · Name · Fuse · Apex. Stage 6 (Apex) carries the gold ring. |
| Footer | github link · MIT · v3.9.2 (live from `pyproject.toml`) · The Codex · Your Tree. Single row, minimal. |
| The Codex page | Existing `how-we-do-things.html` content, retypeset in Scholar's Plate, plate-style ornamental headings. |
| Imagery | The skill graph IS the imagery. No stock photos. Diamond Seal mark + graph SVG + Plaques carry the visual load. |

## 10. The Plaque visual system (Priority D > B > C)

One design language, three render modes.

### Priority D — The Naming Reveal (highest)

Triggered when a skill is named (or by a "preview" affordance on the Hall of Heroes). 4s cinematic:

1. **t=0.0s:** Graph centres and zooms to the named node. Surrounding nodes fade to 0.2 opacity.
2. **t=0.8s:** A blank plate emerges from below the node (480×600 portrait), midnight ink with a thin hairline border.
3. **t=1.4s:** Gold ink pours into the plate's engraving — skill name, tier glyph at top — letter by letter in EB Garamond.
4. **t=2.4s:** Contributor handle resolves in honor red beneath the name.
5. **t=2.8s:** Stars ignite one at a time, each with a soft Departure Mono "click" cadence.
6. **t=3.4s:** Evidence Class chip stamps in (small wax-seal animation).
7. **t=4.0s:** Plate settles at rest; gold underline pulses once; if 6★, the locked Level VI rainbow shimmer ignites at the plate's edge.

Implementation: SVG + CSS animation primarily (no Lottie dependency unless we hit physics limits); respects `prefers-reduced-motion` (instant settle to final plate).

### Priority B — The Contributor Profile Page

Route: `gaiaskilltree.com/u/{handle}/` (pre-generated static page).

Layout:

```
┌────────────────────────────────────────────────────────┐
│ ◇G GAIA            Registry · Hall of Heroes · ...    │
├────────────────────────────────────────────────────────┤
│                                                        │
│                  karpathy                              │  display name in honor red
│                  Origin contributor                    │
│                  Joined 14 Sep 2025                    │
│                                                        │
│     ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│     │ plaque  │ │ plaque  │ │ plaque  │ │ plaque  │  │  plate grid, ≥1 plaque per named skill
│     │ /auto…  │ │ /know…  │ │ /ghost… │ │ /eval-… │  │
│     └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
│                                                        │
│     Ascension log:                                     │  Departure Mono ledger
│     2026-05-12  rank up   /autoresearch  4★ → 5★      │
│     2026-04-30  named     /ghostwrite    1★ → 2★      │
│     ...                                                │
└────────────────────────────────────────────────────────┘
```

Static plates are the settled final frame of the naming reveal at portrait dimensions.

### Priority C — The OG Share Card

When a profile page or named-skill page is shared (Twitter, LinkedIn, Discord), the OG card is the static plaque at 1200×630 (landscape variant), centred on a midnight ground with the Diamond Seal at top-left and contributor handle in honor red.

Pre-generated at build time via a node script that reads from `registry/named-skills.json` and writes to `docs/og/{handle}/{skillId}.png`.

## 11. File map

### Modify

- `docs/index.html` — full re-template into Two Doors IA, keeping `<canvas id="canvas3d">` for the HUD.
- `docs/css/styles.css` — full restyle: new typography stack, palette role tokens (`--honor-red`, `--apex-gold`), plate components, dual-path layout, removed gradient text, kept tier colors.
- `docs/js/skill-graph.js` — keep all existing canvas rendering; add 2D-vs-HUD toggle and ambient-mode coloring for the 3D layer.
- `docs/js/skill-explorer.js` — restyle as Hall of Heroes promoted view + secondary "browse all" entry.
- `docs/js/ui.js` — first-load reveal sequence, scroll reveals, copy-to-clipboard micro-flash, ledger-stat click → dialog routing.
- `docs/how-we-do-things.html` → rename `docs/codex.html` (set a redirect or 301 from old URL if needed).
- `docs/index.md` — update GitHub Pages markdown index for parity.
- `DESIGN.md` — replace Typography section, add Brand Voice section, add Honor Red and Apex Gold role tokens, add plaque token block, add Two Doors layout section. Schema sections (tier colors, rank colors, Level VI rendering, skill type cycling) preserved untouched.

### Create

- `docs/js/hud-toggle.js` — 2D ↔ 3D HUD prominence swap.
- `docs/js/plaque-reveal.js` — naming reveal animation engine.
- `docs/js/profile.js` — contributor profile page logic (router + plate grid + ascension log).
- `docs/css/plaque.css` — plaque visual-system tokens and layout.
- `docs/css/scholar.css` (optional) — EB Garamond / Bricolage / Departure Mono `@font-face` block and modular type scale.
- `docs/assets/marks/diamond-seal.svg` — Diamond Seal Monogram mark, single source for nav + favicon.
- `docs/assets/marks/diamond-seal.ico` — favicon export.
- `docs/og/{handle}/{skillId}.png` — pre-generated OG share cards (build step).
- `scripts/generateOgCards.py` (or `.mjs`) — OG card pre-render script.
- `docs/u/{handle}/index.html` — profile page route (generated).
- `scripts/generateProfilePages.py` — profile page pre-render script.

### Out of scope (explicit)

- No README badge plaque renderer (Priority A dropped).
- No CLI changes.
- No `registry/schema/**` changes.
- No new test infra beyond existing `tests/test_docs_site.py` coverage of `docs/` HTML validity.

## 12. Execution phases (checkpoints for implementation)

**Phase 1 — Foundation**

- [ ] Create branch `design/hunters-atlas`.
- [ ] Update DESIGN.md typography + add Brand Voice section + add Honor Red / Apex Gold tokens (preserving schema sections).
- [ ] Pull EB Garamond, Bricolage Grotesque, Departure Mono via Google Fonts `@import` in `docs/css/styles.css`.
- [ ] Add palette role tokens in `:root`.
- [ ] Draw `docs/assets/marks/diamond-seal.svg` and export favicon.

**Phase 2 — Home page Two Doors IA**

- [ ] Re-template `docs/index.html` to the layout in §5.
- [ ] Wire 3D HUD as ambient layer (recoloured, low opacity, slow rotation).
- [ ] Build the two CTA doors with tier-glow hover.
- [ ] Build the ledger stats strip wired to live registry data.
- [ ] Build Path A column (Initiate's Rite) with copy-to-clipboard micro-flash.
- [ ] Build Path B column (Available Ultimates list, live data).
- [ ] Build Hall of Heroes plate strip (static plates initially; reveal animation in Phase 3).
- [ ] Build Ascension Cycle circular diagram.
- [ ] Update sticky nav with Diamond Seal lock-up.

**Phase 3 — HUD toggle and graph integration**

- [ ] `docs/js/hud-toggle.js` — 2D ↔ 3D prominence swap.
- [ ] `⇄ View as HUD` floating pill.
- [ ] `◆ Open full graph` pill wired to existing graph dialog (kept).
- [ ] Mobile fallback: disable 3D HUD, render 2D as static SVG.

**Phase 4 — Plaque system**

- [ ] `docs/css/plaque.css` — plaque tokens (sizes, spacing, plate hairline, gold rule, honor-red label).
- [ ] `docs/js/plaque-reveal.js` — naming reveal animation (Priority D).
- [ ] Contributor profile pages (Priority B): generator script + route.
- [ ] OG share card generator (Priority C).

**Phase 5 — Polish**

- [ ] `prefers-reduced-motion` paths across all animations.
- [ ] Mobile sheet menu nav.
- [ ] First-load reveal cookie-gating.
- [ ] Rename `how-we-do-things.html` → `codex.html` and reskin.
- [ ] Validate via `python scripts/build_docs.py --check` and `python -m pytest` (only `tests/test_docs_site.py` should care).

## 13. Open questions (resolve during implementation, not blockers to commit)

1. **3D HUD recoloured ambient palette:** muted gold-on-midnight (`#fbbf24` @ 0.18 opacity) vs midnight-blue dust (`#1e293b` @ 0.4 opacity). Recommendation: muted gold — it preserves the apex-gold brand role even in the ambient layer.
2. **Codex page route:** rename `how-we-do-things.html` → `codex.html` with a 301-style meta-refresh on the old URL, or keep both URLs alive. Recommendation: rename and refresh — voice consistency matters more than old-URL stability for a docs page.
3. **Profile page route:** `gaiaskilltree.com/u/{handle}/` vs `gaiaskilltree.com/heroes/{handle}/`. Recommendation: `/u/` — short, GitHub-pattern-familiar, doesn't over-commit voice.
4. **Naming reveal implementation:** pure SVG+CSS (preferred for filesize), Lottie JSON (if motion gets too complex), or canvas (if pixel-level effects are needed). Recommendation: try SVG+CSS first; escalate only if blocked.
5. **Build-time OG card generation:** Python `cairosvg` vs Node `@vercel/og` vs Playwright headless screenshots. Recommendation: defer — pick once OG card design is final.

## 14. Slop-test self-check

- **First-order category reflex** (could someone guess theme + palette from "AI agent skill registry"?): the default is dark-navy + sky-blue gradient. We're keeping midnight ink but rejecting sky-blue gradients in favor of honor red + apex gold. ✅ Avoided.
- **Second-order aesthetic reflex** (could someone guess the aesthetic family from category + anti-references?): the second-tier trap is editorial-magazine (Klim/Stripe). We rejected it explicitly and committed to Sacred Atlas × Solo Leveling. EB Garamond is plate-faithful, not magazine-faithful; Bricolage is voiced, not anonymous; Departure Mono is system-UI, not editorial caption. ✅ Avoided.
- **Absolute bans check:**
  - No side-stripe borders ✅
  - No gradient text on hero ✅ (replaced with EB Garamond solid + thin gold underline on "rare")
  - No glassmorphism as default ✅ (kept only on graph dialog where it earns its place)
  - No hero-metric template ✅ (ledger strip is clickable functional data, not big-number-small-label decoration)
  - No identical card grids ✅ (tier cards collapse into graph node tooltips; Hall of Heroes plates differ by contributor)
  - No modal as first thought ✅ (only the graph dialog uses a modal, and only behind an explicit CTA)
- **Em dashes in user-facing copy:** review pass during implementation (none in §9 content as written).
