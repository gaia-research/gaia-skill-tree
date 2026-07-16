# Yggdrasil II Design-Run — Asset & Decision Ledger

**Purpose:** the single durable record of every asset created/modified and every design decision made during the "Full Gas" end-to-end design run (2026-07-17, EPIC #1002 · #998). Complements the private MEMORY snapshot and the public EPIC proof-of-work. The runbook is `founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md` §7; this file is the append-only outcome log.

**Branch:** `dev/yggdrasil-ii-staging` · **Commit identity:** `mbtiongson1` (Marcus Rafael B. Tiongson `<153011150+mbtiongson1@users.noreply.github.com>`) · **Target:** design fully integrated into staging, no follow-ups, zero Ygg-I legacy design.

---

## Ratified decisions (locked)

| # | Decision | Rationale |
|---|---|---|
| R1 | `--tier-unique` (#7c3aed violet) promoted to a first-class token family in `tokens.css` (`-rgb/-bg/-border/-edge/-symbol`). It already existed as an inline-hex-fallback value; the run canonicalizes it. Unique = the darker plaque hue. | Uniques need a distinct identity for the dark-plaque directive; no hex fallbacks (CI guard). |
| R2 | Correctness + design bundled per surface, BUT the shared resolver + token land as step 1 of Wave 0 (the plaque PR); everything imports it. One-agent-first, then fan. | The branch-derivation defect has one root; fixing it once prevents 16 re-implementations. |
| R3 | Mobile-first (N-12 deliverable 2) is INSIDE #998, not a spun-off EPIC. | Sprint-completeness ("no follow-ups"): mobile-first is #998's own remainder. |
| R4 | /impeccable design items (OG card, footer, reports, wreath) are reviewer-agent-gated, no founder gate — but reviewer prompts are adversarial (reject-by-default). | Founder chose velocity; the adversarial reviewer is the quality bar. |
| D1 | Gold-wreath frame authored as an SVG (`docs/assets/origin-wreath-gold.svg`), not raster. Replaces the honor-red `#origin-badge` sprite. | Scales cleanly, tokenizable gold, no image-gen dependency. |
| D2 | AOV4 asset set (C1–C6 suite, D4–D6 unique × badge/card/hero) is COMPLETE and reused as-is for plaques/OG/badges. No new rank art generated. | Verified present in `docs/assets/ascension-overdrive/`. |
| D3 | N-3 "frozen profile pages" fixed at the GENERATOR (`generateProfilePages.py` L197/L375), not by hand-editing `docs/u/*/index.html`. About stars likewise. | The pages are generated; source-fix propagates to all handles. |
| D4 | MCP canonical = `@gaia-registry/mcp@0.1.0` + `research.gaiaskilltree.com/mcp`. N-9 also fixes the stale `@gaia-registry/mcp-server` refs (main README is internally inconsistent). Sweep: `docs/index.html`×2, `docs/en/index.html`, `docs/en/mcp-server.html`, `docs/agent.md`, `README.md`×4. | Confirmed against `origin/main:README.md` L245. |
| D5 | N-11 skill-fuse CTA links to `https://github.com/gaia-research/skill-fuse` (verified PUBLIC) + the Research fuse page. Folded with N-9/N-10 into one shared cross-brand "Research product" component (Rimuru-Blue #38bdf8 bridge). | Cross-repo rule governs content, not hyperlinks. |
| D6 | Badge `_assets/*/` SVG regeneration lands on a SEPARATE `infra/badge-*` PR, not the design PR. | CLAUDE.md badge invariant: auto-sync never touches `docs/badges/`; regen is human-reviewed infra. |

---

## Assets created / modified (append per wave)

| Asset | Path | Wave | Status |
|---|---|---|---|
| _(pending W0)_ gold-wreath frame | `docs/assets/origin-wreath-gold.svg` | W0 | pending |
| _(pending W0)_ shared resolver | `docs/js/skill-semantics.js` | W0 | pending |

---

## PR / commit ledger (append per merge)

| Wave | Branch | PR | Merge SHA | Reviewer verdict |
|---|---|---|---|---|
| _(pending)_ | | | | |

---

## Token-spend log (append per push, per CLAUDE.md directive)

Format: `<date> <model> <effort>: <in>k in, <out>k out. ~$<cost>`

- _(pending — logged at each wave close)_
