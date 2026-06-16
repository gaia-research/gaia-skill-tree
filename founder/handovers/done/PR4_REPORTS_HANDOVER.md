# Handover: PR-4 — Actionable Per-Skill Reports (#648)

**Type:** Website / design · **Branch:** `design/...` (e.g. `design/actionable-reports`) · **Resolves #648**
**Milestone:** Immediate Next 30 Days (#7), due Jul 10 2026.
**Governing spec:** `handovers/TRUST_IMPL_HANDOVER.md` §PR-4 and `handovers/TRUST_MODEL_RFC.md` v2. This is the execution brief; the master handover wins on any conflict.
**Model:** Opus or Sonnet for the data/logic of Deliverable A; the report (Deliverable B) is content-ready and only needs a careful publish.
**Scope note (expanded 2026-06-14):** PR-4 now carries **two** deliverables — (A) the per-skill actionable report page, and (B) publishing the official **Trust Methodology** meta report (Marco's request). They're independent and may ship as one `design/` PR or two.

## Context — the data this consumes is now fully live

The whole grading flow is merged on main: PR-1 (#659, schema), PR-2 (#686, pipeline), and **#690** (in-place re-grade + 220 starless + 173 named backfill + grade **inheritance**). The catalogs now carry, per skill:

- Evidence **Grade** (S/A/B/C), **Evidence Type**, **trustNumber**, **Overall Trust Grade**, and **`ultimateGateStatus`** (`registry/named-skills.json`, `docs/graph/named/index.json`).
- **Effective grade = own ∪ inherited evidence** — a named skill inherits its starless parent's capability evidence, then adds its own. Surface the inherited floor vs. the child's own contribution where it helps the reader.
- Real suite-gate reasons (the "0/3 components" artifact is fixed): **182/183 named skills carry an Overall Trust Grade; all six suite ultimates report a real gap** (none `passes:true` yet — by design; S is the editorial Verifier call).
- Grade colors (Platinum/Gold/Silver/Bronze) in `src/gaia_cli/formatting.py` `GRADE_COLORS` — mirror as CSS tokens; **do not fork** hex values.

The data is populated, so no graceful-degrade phase is needed. The one legitimate empty state to design for is `ruvnet/github-release-management` (no evidence → ungraded).

## Deliverable A — a per-skill actionable report on the static site

For each skill, render:

1. **Current rank + tenure** — "held [rank] since [date]", derived from the skill's timeline events (tenure is **display-only, no regression** per the RFC). Remember the data model: **skill levels are stored in slots, not on the skill object** (repo `CLAUDE.md`) — compute rank/tenure accordingly.
2. **Evidence inventory** — each entry's **type**, **grade** (color-coded via the grade tokens), and **verified / disputed** flags.
3. **Overall Trust Grade** — the skill's aggregate grade (from the catalog). Note the current implementation is the **highest single grade** (a max), pending the recalibration-RFC decision on accumulation semantics — render whatever the catalog provides; don't recompute a different definition here.
4. **The actionable gap** — the explicit "what would raise this" line: the gap to the next **grade** and/or **rank** (e.g. "needs one more A-graded source to clear the ultimate gate", or "2 ranks below its evidence ceiling"). This is the core of #648's shift from "scores" to **actionable reports**.
5. **Staleness + dead-link flags** — surface stale evidence and dead links (the liveness checker already flags these; reuse its output rather than re-implementing).

## Deliverable B — publish the Trust Methodology meta report

Publish the official trust-methodology report to the Gaia site with the **`/meta-post`** skill (`.agents/skills/meta-post`), **report** type. The source is drafted and ready in the Orchestrator workspace and already carries the frontmatter the script needs (`title`, `author`, `summary`, `abstract`, `label`):

- **Source:** `handovers/TRUST_METHODOLOGY_REPORT.md` (gaia-roadmap) → copy into the repo as `docs/meta/2026-06-trust-methodology.md`.
- **Publish:**
  ```bash
  python scripts/add_post.py report \
    "The GAIA Trust Methodology: Evidence Types, Grades, and Inherited Standing" \
    "How GAIA replaced evidence classes and numeric scores with Types, Grades, and inherited standing." \
    --source docs/meta/2026-06-trust-methodology.md \
    --author "Marco Tiongson, Maintainer" --label "Trust Model" --hero
  ```
  Renders `docs/meta/reports/<date>-slug.html`, prepends to `docs/meta/posts.json`, and patches the `gaia-posts` + `gaia-hero-post` zones in `docs/index.html` — no hand-editing HTML.
- **Optional chart (`--chart`):** a grade-distribution snapshot (counts of S/A/B/C/ungraded across the 393 graded entries, or the six suites' gate status) as `docs/meta/reports/<date>-trust-chart-data.json` (mirrors `may-2026-timeline.json` shape).
- **Vocabulary:** the report already conforms to `CONTEXT.md` (stars vs rank-name, Evidence Type/Grade, trust number not "score", starless inheritance, no rarity) — keep it clean if you edit.
- **Commit:** `git add docs/meta/posts.json docs/meta/reports/ docs/index.html && git commit -m "post: report — GAIA trust methodology [skip-gen]"`.

Ships in the same `design/` PR as Deliverable A or as its own small post PR — it has no dependency on the per-skill page.

## ⚠️ Known traps (from repo `CLAUDE.md` — do not relearn the hard way)

- **`docs/js/skill-graph.js` bootstrap guard (PR #365):** any `querySelector(...).addEventListener(...)` at module-bootstrap level **silently aborts the whole IIFE** if the selector is null, dropping the canvas back to the ~18-node `FALLBACK_SKILLS`. **Null-check every overlay selector** before wiring events. Grep `_graphCloseOverlay.querySelector` if the 3D graph regresses to fallback.
- **`docs/badges/index.html` `renderRows()` destructuring (PR #675, #674):** if this report reuses any badge-rendering path, every field read inside `renderRows()` **must** be in the `currentState` destructuring (or defined with a default) — a missing var throws a silent `ReferenceError` that blanks the entire output. After any edit there, verify `https://gaia.tiongson.co/badges/?u=mattpocock&s=grill-me` still renders.
- **`docs/badges/index.html` and the badge scripts are Hermes-owned-adjacent / core** — badge generation is user-facing and must work at all times.

## Cross-cutting constraints

- **Vocabulary:** `CONTEXT.md` is the source of truth; **no rarity-axis references** anywhere in the copy. Use the grade/type/Overall-Trust-Grade/tenure terms PR-1 added.
- **Never touch Hermes-owned files** (`docs/ADOPTION.html`, `docs/SHOWCASE.html`, `docs/WHY-GAIA.md`, `docs/QUICKSTART.md`, and the `scripts/` Hermes set — see master handover / repo `CLAUDE.md`).
- **Static-site rule:** the page hosts **canon only** — no server-side user state, no hosting of local trees (GAIA_AUTH_PRD §3). Reports render from the committed generated catalogs.
- **`design/` branch scope** covers `docs/` (HTML/CSS/JS) + `*.md`. Don't mix CLI/source changes in.
- **Testing:** run the docs build + `--check` (`scripts/build_docs.py`) and the full suite; verify the page renders against a real skill with graded evidence and one with none (graceful-degrade path). Take a screenshot for the PR.
- **PR hygiene:** `Resolves #648` (this one closes its issue). Move #648 to **In Progress** on board #2 when work starts.

## Definition of Done

**Deliverable A:** the site shows a per-skill report with rank+tenure, evidence inventory (type/grade/verified/disputed), Overall Trust Grade, the explicit gap-to-next-grade/rank, and staleness/dead-link flags; grade colors from the shared tokens; the 3D graph still loads real data (no `FALLBACK_SKILLS` regression). **Deliverable B:** the Trust Methodology report is published — renders at `docs/meta/reports/...`, appears in the landing-page feed and hero badge. Both: docs `--check` + full suite green; `Resolves #648`.

## After PR-4

This is the last of the four trust PRs. The PR that completes the end-to-end model (whichever lands last among the grading flow) should say **`Resolves #646`**. Post-ship: the Orchestrator opens the **recalibration RFC** (~1 month out) to revisit the pillar thresholds **and** the Overall-Trust-Grade aggregation (max vs. accumulation — flagged on #686).
