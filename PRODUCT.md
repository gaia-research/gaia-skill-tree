# PRODUCT.md

> See `CONTEXT.md` for the canonical glossary and banned-synonym list, and `DESIGN.md` for visual tokens and motion specs. This document owns audience, product purpose, brand personality, anti-references, design principles, and the accessibility baseline.

## Register

brand

## Users

**Primary:** AI agent developers using Claude Code, Codex, Cursor, Devin, and similar
tool-calling frameworks. They're builders running agents day-to-day. They come to the
Atlas to discover unclaimed Ultimate skills, verify named contributors, and register
their repos to claim origin status on skills they've demonstrated. Technically fluent;
they distrust hype; they respond to evidence and provenance.

**Secondary:** Open-source contributors wanting to claim a Named Skill — earning origin
status and a permanent plaque in the registry. Attribution matters to them: their
handle should appear in Honor Red, permanently.

**Tertiary:** Curious technologists evaluating whether Gaia is worth adopting — exploring
the Registry and Ascension Cycle before committing.

**Emotional goal:** The Atlas should feel like arriving at a guild ledger kept with
obsessive care. Not a SaaS dashboard. Not a portfolio. A public record that outlasts
any individual contributor. Visitors should feel the weight of Apex — genuinely rare,
permanently attributed, verifiably earned.

## Product Purpose

Gaia is the open, evidence-backed skill graph for AI agents. It exists because there
is no canonical registry of what agents can do — capabilities are scattered,
undocumented, and unverified. Gaia provides a DAG where every capability is catalogued by
tier (Basic / Extra / Unique / Ultimate) as a **starless** generic reference — rank-less
taxonomy that carries no stars of its own — and each named implementation hanging off it is
ranked by evidence (0★–6★), attributed to the Origin Contributor who first demonstrated it,
and composable into emergent fusions. A starless reference's effective rank is the top star
among its named children; in the UI it reads as *generic* in italic, greyed-out styling.

The Hunter's Atlas is Gaia's public surface: a visual ledger of that graph — a
discovery layer (what can agents do?), an attribution layer (who demonstrated it
first?), and an invitation layer (what's available to claim?).

Success: the Atlas becomes the public record AI agent developers cite when making
capability claims — the way pkg.go.dev is cited for Go packages.

## Brand Personality

**Voice:** Half-Merged — truthful primary labels (Registry, Skill Tree, Intake,
Evidence, Named Contributors) carry the page; ceremonial section titles (Hall of
Heroes, The Initiate's Rite, Ascension Cycle, The Codex) and fantasy verbs (claim,
ascend, name, fuse, bond) carry the swagger. Never full-guild voice; never pure
documentation voice.

**Tone:** Confident, precise, and quietly ceremonial. The ledger has been kept
meticulously. The data speaks. The prose doesn't oversell it.

**3-word personality:** Evidence. Permanence. Craft.

**References:**
- 19th-century natural history atlas print — the typographic register that inspired
  Scholar's Plate: plate numbers, ledger strips, EB Garamond display, pixel mono for
  HUD numerals. Serious and beautiful simultaneously.
- Linear — a serious developer tool that trusts whitespace and restrained type.
  Zero ornamentation not earned by function.
- pkg.go.dev — a registry where the index IS the experience. Minimal chrome.
- Solo Leveling guild registry — ceremonial weight around ranking up, main-character
  energy around contribution. Fantasy verbs without full anime UI.

## Anti-references

- **Generic AI startup dark mode:** navy/teal background, neon gradient accents,
  floating abstract blobs. Gaia is not a vibe product; the registry is the substance.
- **SaaS hero-metric dashboards:** big KPI numbers, identical card grids with icon +
  heading + body text, rainbow accent bars. The hero-metric template is banned.
- **Gamification-as-product:** leaderboards designed to feel like mobile-game
  achievements. The tier system must feel weighty and earned, not dopamine-loop.
- **Glassmorphism as decoration:** blurs and frosted glass everywhere. The only earned
  glassmorphism is the graph dialog (preserved by spec). Everywhere else it's banned.
- **Gradient text:** banned. The registry's evidence is the credential, not visual
  effect.
- **Hype-heavy marketing copy:** "The #1 skill registry," vague superlatives, social
  proof padding. The Atlas shows the actual graph.

## Design Principles

1. **The ledger precedes the interface.** `registry/gaia.json` is ground truth. Every
   screen is a window into it. Design should feel like the UI came second, not first.

2. **Evidence is the credential.** Wherever a star rank appears, its Evidence Class
   and source must be reachable. A 5★ skill with no visible provenance is a failure.

3. **Apex must feel genuinely rare.** The visual distance between 0★ and 6★
   Transcendent ★ must be unmistakable. Level VI shimmer, orbit sparkles, and Apex
   Gold are hard-locked to that tier only — never repurposed as decoration elsewhere.

4. **Attribution is structural, not decorative.** Origin Contributor handles always
   render in Honor Red, always at the same visual weight as the tier itself. The most
   permanent thing on the page.

5. **Half-Merged voice, all the way down.** Every copy surface — headers, CTAs,
   tooltips, empty states — must pass the Half-Merged test: canonical primary labels,
   ceremonial overlay only in section titles and swagger verbs.

## Accessibility & Inclusion

- WCAG AA minimum across all text, interactive states, and focus indicators.
- Unicode tier symbols (○ ◇ ◉ ◆ ★) carry meaning — every use needs an accessible
  text alternative (aria-label or adjacent visible label). Never symbol alone.
- No color-only tier differentiation: tier color + symbol + label together convey the
  information. Color-blind users must distinguish all four tiers without hue.
- Reduced motion: Level VI shimmer, the Naming Reveal cinematic, and the Ascension
  Cycle diagram must respect `prefers-reduced-motion`. Tier identity survives without
  animation.
- CLI TUI and tree renders should be screen-reader compatible. Art-only ASCII layouts
  for critical information are prohibited.
