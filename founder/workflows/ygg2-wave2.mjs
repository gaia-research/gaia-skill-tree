export const meta = {
  name: 'ygg2-wave2',
  description: 'Yggdrasil II Wave 2 — /impeccable design-quality passes on three surfaces: N-8 OG share card (generateOgCards.py dispatch + AOV art + all-rank), N-10 footer redesign + cross-brand Gaia Research CTA (Rimuru-Blue #38bdf8 bridge), N-7 reports design system (docs/reports/ + named/report.html ONLY). Each lane: /impeccable build in worktree -> adversarial reviewer (Playwright E1-E7, reject-by-default) -> one bounded remediation -> re-review. Concurrency Wave-2: max 2 opus. W2a+W2b opus pair, then W2c opus solo. Recoverable via resumeFromRunId.',
  whenToUse: 'After Wave 1.5 (N-13 medallion) closes; before Wave 3 capstone.',
  phases: [
    { title: 'W2ab', detail: 'opus pair — N-8 OG card dispatch+AOV+all-rank, N-10 footer + Research CTA', model: 'opus' },
    { title: 'W2c', detail: 'opus solo — N-7 reports design system (docs/reports/ + named/report.html)', model: 'opus' },
  ],
}

const BASE = 'dev/yggdrasil-ii-staging'
const IDENT = 'git -c user.name="Marcus Rafael B. Tiongson" -c user.email="153011150+mbtiongson1@users.noreply.github.com"'

// ── Shared worktree / identity / foundation preamble ──────────────────────
const PREAMBLE = `
## Worktree rules — READ BEFORE EDITING ANY FILE
You run with isolation:"worktree" — a SEPARATE checkout. Edits are invisible to anyone until pushed.
1. Branch FROM ORIGIN: \`git checkout -b <branch> origin/${BASE}\` (NOT a local ref — local may be stale).
2. COMMIT IDENTITY IS MANDATORY AND EXACT. Every commit: \`${IDENT} commit -m "..."\`. Nothing else. Audit \`git log --format='%ae'\` before pushing — every line MUST read 153011150+mbtiongson1@users.noreply.github.com.
3. Commit + push after EACH logical unit; never batch. \`git push origin <branch>\` immediately after each commit. A pushed commit survives cutoff; a local commit dies with the worktree.
4. Report each commit SHA + push status as you finish it.
5. If you hit ~80k tokens before done, commit+push what you have and report — do not cram the rest into one dispatch.
6. Revert Class-P timestamp side-effects (registry/gaia.json, docs/graph/*, docs/css/tokens.css if regen-only) before committing. EXCEPTION: the W2a OG lane owns its regenerated docs/og output; commit those.

## /impeccable design skill — USE IT
This is a design-QUALITY pass, not a mechanical edit. Run the project's /impeccable skill discipline:
- Read \`.claude/skills/impeccable/SKILL.md\` + the matching register reference (brand.md for the OG card + footer marketing surfaces; product.md for reports). Read DESIGN.md and the existing tokens/CSS before designing — identity-preservation wins, do NOT reinvent the wheel.
- Verify contrast (body ≥4.5:1), typography ceilings (hero clamp ≤6rem, display letter-spacing ≥-0.04em, ≤3 font families), semantic z-index scale, motion with prefers-reduced-motion fallback.
- Produce ready-to-ship production code, screenshot-verified at 1280 desktop AND 390 mobile with Playwright. No prototypes.

## The merged Yggdrasil II foundation you MUST honor (already on ${BASE})
- \`docs/js/skill-semantics.js\` → \`window.GaiaSemantics = { computeBranch(node, effRank), rankWord(level, branch), rankLabel(level, branch) }\`. Python equivalent: \`gaia_cli.trustMagnitude.computeBranch\` + \`gaia_cli.formatting.rank_word\` (merged PyPI #996 — REUSE via sys.path.insert(0, str(Path(__file__).parent.parent / "src"))).
  - computeBranch returns 'standard'|'suite'|'unique'. Read order (do NOT reorder): unique = type==='basic' && rank>=4 && !suiteComponents; suite = suiteComponents present; else standard.
  - rankWord ladders: shared {1 Awakened,2 Named,3 Evolved}; suite {4 Extra,5 Ultimate,6 Apex}; unique {4 Unique,5 Unique Ultimate,6 Unique Impossible}.
- BANNED words anywhere in output/copy/labels/CSS-selectors/SVG-text: 'Transcendent','Hardened'. Only valid \`type\` values: 'basic','fusion'. The old enum (extra/ultimate/unique) is DEAD — any read of it is a defect.
- Tokens: NO hex literals in docs/js or docs/css design paths (CI Guard A rejects raw hex — use var(--token)). \`--tier-unique\` is a full family; \`--apex-gold\` #fbbf24 is the gold origin (red #ef4444 is DEPRECATED). \`--tier-basic\` == #38bdf8 == Rimuru-Blue (the cross-brand bridge accent).
- AOV V4 asset set (COMPLETE, reuse — no new rank art): \`docs/assets/ascension-overdrive/\` aov4-c{1..6}-suite-* (suite) + aov4-d{4..6}-unique-* (unique), 3 sizes each (-badge/-card/-hero).
- Gold-wreath avatar frame SVG: \`docs/assets/origin-wreath-gold.svg\` (the shared medallion frame).

## Rubric you will be graded against (DESIGN.md §"Yggdrasil II Enforcement Rubric", clauses E1-E7)
E1 no dead enum (use computeBranch). E2 branch-forked rank words, no banned words. E3 plaque/medallion/avatar. E4 red origin → gold. E5 cross-brand Research bridge = Rimuru-Blue #38bdf8 (token var). E6 mobile-first non-homepage. E7 tokens & regen hygiene (no hex, prefer Python scripts).
`

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['pass', 'failures', 'severity', 'evidence'],
  properties: {
    pass: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'blocker'] },
    evidence: { type: 'string', description: 'What was served, screenshotted (1280+390), and grep-verified.' },
    failures: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['clause', 'surface', 'detail'],
        properties: {
          clause: { type: 'string', description: 'E1..E7 or a design-quality note' },
          surface: { type: 'string' },
          detail: { type: 'string' },
        },
      },
    },
  },
}

const BUILD_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['branch', 'shas', 'filesTouched', 'summary'],
  properties: {
    branch: { type: 'string' },
    shas: { type: 'array', items: { type: 'string' } },
    filesTouched: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    selfCheck: { type: 'string', description: 'grep proof of no banned words / no dead-enum / no hex; screenshot observations' },
  },
}

// ── Lane definitions ──────────────────────────────────────────────────────
const LANES = {
  W2a: {
    branch: 'design/ygg2-w2a-ogcard',
    model: 'opus', effort: 'high',
    label: 'W2a:ogcard',
    task: `LANE W2a (OPUS) — N-8 Share / OG card /impeccable reshape. Surface: \`scripts/generateOgCards.py\` (915 lines) → \`docs/og/<handle>/<slug>.svg\`, loaded into the fullscreen share modal by \`docs/heroes/hero-share.js\` L33.
THREE founder directives (all must land):
1. **/impeccable composition reshape.** The card's vast center-right art region is currently a dead zone. Redesign the card SHAPE/composition to /impeccable standard. Produce ONE reference plate first (screenshot it) for the reviewer, then generalize.
2. **In line with AOV assets.** The art region carries the AOV V4 stamp matching the skill's branch+rank — Asset C (suite) / Asset D (unique), \`-hero\` size (OG is a large surface). Map computeBranch→C/D series, rank→index. Embed via same-origin relative href (works when served from Pages) OR data-URI — decide in the pass.
3. **Logic for ALL ranks.** THE CORE BUG: plate dispatch keys on \`resolve_type_for_og()\` (L157-170) which returns the DEAD enum basic/extra/ultimate/unique → post-migration canonical \`type\` is only basic/fusion, so EVERY named skill falls to the barren "Basic Skill" fallback plate (a MAG-482 GRADE-S 5★ like ruflo renders as a bare "Basic Skill" with an empty card). Rewrite dispatch on \`computeBranch\`+rank (import the Python computeBranch from gaia_cli.trustMagnitude — REUSE, do NOT re-derive) so all 6 ranks × 2 branches (suite+unique) get a proper composition. Kill the fallback dead-zone.
Also: \`rank_words\` L652-658 bakes HARDENED/TRANSCENDENT into SVG <text> → branch-forked ladder (gaia_cli.formatting.rank_word). Top-right bare "Basic Skill" label → branch-forked rank label (a 5★ suite reads "Ultimate", a 4★ unique reads "Unique") — never "Basic Skill" for a graded skill.
Regenerate ALL \`docs/og/*/*.svg\` and COMMIT them (this lane owns that output). Do NOT touch docs/badges/_assets/ (separate infra PR).
Set sys.path.insert(0, str(Path(__file__).parent.parent / "src")) for the import.
Verify: run the script clean; spot-check regenerated ruflo (5★ suite) + a unique-branch skill + a basic — was "Basic Skill" fallback → now correct branch+rank plate with AOV art. grep the script + a sample of regenerated SVGs for 'Transcendent'/'Hardened'/'#ef4444'/'Basic Skill'(on graded skills) → zero. Open the share modal via Playwright, screenshot desktop+mobile.`,
  },
  W2b: {
    branch: 'design/ygg2-w2b-footer',
    model: 'opus', effort: 'high',
    label: 'W2b:footer',
    task: `LANE W2b (OPUS) — N-10 Footer redesign + cross-brand Gaia Research CTA. Surface: \`docs/js/site-footer.js\` (120 lines, single source, mounts into #site-footer-mount on EVERY page) + \`docs/css/styles.css\` (.footer-v2 / .footer-brand-*).
TWO founder directives (/impeccable, reviewer picks the variation):
1. **Gaia Research CTA — "find a place where we can put this nicely."** Add a visible, user-facing CTA to **research.gaiaskilltree.com**. Currently the ONLY on-site reference is an invisible JSON-LD string (index.html L264). The CTA must express the parent→flagship relationship: "Gaia Skill Tree is the flagship registry of **Gaia Research**."
2. **Footer /impeccable — "highlight Gaia AND Gaia Research somehow where it is obvious that both are Gaia."** The footer brand col should visually bind the two brands as ONE FAMILY — "one house, two rooms."
CROSS-BRAND RECONCILIATION (the hard part — two DISTINCT design languages):
  - gaia-skill-tree = "The Hunter's Atlas": EB Garamond serif + Departure Mono pixel, amber/gold diamond seal #fbbf24, obsidian bg.
  - gaia-research = "The Cyber-Slime Laboratory": Bebas Neue + Syne + Manrope, Milim-Pink #ec4899 + Rimuru-Blue #38bdf8, sharp 1px grids.
  - SHARED DNA: both obsidian bg; **Rimuru-Blue #38bdf8 == this repo's --tier-basic token (EXACT match — the natural bridge color)**; seal/hex-lens motif common ground.
  - RECONCILIATION: keep the Atlas footer in its serif/gold language, introduce a **Gaia Research brand lockup rendered in ITS OWN language (Syne wordmark + Rimuru-Blue/Milim-Pink accent)** as a distinct-but-sibling block, with connective copy naming the flagship relationship. Do NOT wholesale-import Cyber-Slime tokens into every footer element (that breaks the Atlas identity) — the point is *legible kinship*, not merger. Load the Syne webfont in our own CSS (do NOT import gaia-research files — cross-repo content rule).
  - Produce 2-3 variations of how the two brand marks coexist; the reviewer picks the strongest. Use #38bdf8 via the \`--tier-basic\` token var (NO raw hex — CI Guard A).
Since site-footer.js renders on EVERY page, one edit propagates site-wide — no per-page work. Cache-bust touched pages if needed.
Verify: serve docs, screenshot the footer at 1280 + 390 on the homepage AND a deep page (/named/), confirm the Research CTA is visible + links to research.gaiaskilltree.com, the two brand marks read as one family, contrast passes, no raw hex, no layout regression. grep site-footer.js + styles.css for raw hex in the new rules → zero.`,
  },
  W2c: {
    branch: 'design/ygg2-w2c-reports',
    model: 'opus', effort: 'high',
    label: 'W2c:reports',
    task: `LANE W2c (OPUS) — N-7 Reports design system. /impeccable "show the actual report in a nice way."
SCOPE (HARD — founder correction 2026-07-17): touch \`docs/reports/\` ONLY — NOT \`docs/meta/reports/\`. The dated \`docs/meta/reports/*.html\` archives are EXPLICITLY OUT OF SCOPE; do not restyle, do not touch them. Also do NOT cross into docs/audits/.
In-scope surfaces: \`docs/reports/index.html\`, \`docs/reports/2026-28/index.html\` (dated report pages), and \`docs/named/report.html\` (46KB single named-skill report template). \`docs/reports/DRAFT/2026-29.md\` is a markdown draft rendered into a FUTURE 2026-29/index.html — the design system must cover the render target.
Founder directive: establish ONE shared report design LANGUAGE (typography scale, section cards used sparingly, metadata header, evidence tables) applied ACROSS the docs/reports/ set + named/report.html — NOT one page styled in isolation. First determine if they share a stylesheet/layout or each rolls its own; unify onto one report design system.
/impeccable discipline: read DESIGN.md + existing report CSS first (identity-preservation); production-grade, contrast-verified, mobile-first (E6 — this is a non-homepage surface so mobile-first is IN SCOPE here), fixed-nav clearance (every page-level container clears ~58px: base 5rem, desktop 6rem thin / 8rem full shell — no global body padding-top), semantic z-index, motion with reduced-motion fallback.
If any report surface renders skill plaques/rank words, route them through the shared plaque/GaiaSemantics path (E1/E2/E3) — no dead enum, no banned words.
Entrypoints: if this establishes a new report index nav item, ensure it is reachable (mounts.js / nav) — PR body must note entrypoints touched or waived.
Verify: serve docs, screenshot docs/reports/index.html + docs/reports/2026-28/index.html + docs/named/report.html at 1280 + 390, confirm one coherent design language, fixed-nav clearance, contrast, no raw hex, no banned words. grep confirms clean. Confirm docs/meta/reports/ is UNTOUCHED (git diff shows zero changes there).`,
  },
}

// ── One lane: /impeccable build (worktree) → adversarial review → 1 bounded remediation → re-review ──
async function runLane(key, ph) {
  const L = LANES[key]
  const build = await agent(
    `${PREAMBLE}\n\nBranch name for THIS lane: \`${L.branch}\` (create from origin/${BASE}).\n\n${L.task}\n\nReturn the build manifest.`,
    { label: L.label, phase: ph, schema: BUILD_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
  )
  if (!build) return { lane: key, branch: L.branch, status: 'died', verdict: null }

  let verdict = await agent(
    `You are an ADVERSARIAL design reviewer (reject-by-default). Lane ${key} pushed branch \`${build.branch}\`.\nFiles touched: ${(build.filesTouched || []).join(', ')}.\nBuilder summary: ${build.summary}\n\nPROCEDURE: in your worktree, \`git fetch origin ${build.branch} && git checkout ${build.branch}\`. Serve docs locally (\`python -m http.server 8096 --directory docs &\`) and load the target surface with Playwright at 1280 (desktop) AND 390 (mobile); screenshot both. grep the touched files for banned words ('Transcendent','Hardened'), dead-enum reads (type==='ultimate'|'unique'|'extra'), and raw hex literals in JS/CSS/SVG design paths.\nGrade against DESIGN.md rubric E1-E7 AND /impeccable design quality (contrast ≥4.5:1, hero clamp ≤6rem, ≤3 font families, semantic z-index, mobile-first for non-homepage, fixed-nav clearance, motion with reduced-motion). For W2a: confirm the OG dispatch no longer falls to the "Basic Skill" fallback for graded skills, all ranks × both branches get proper plates with AOV art, branch-forked labels. For W2b: confirm the Research CTA is visible + links research.gaiaskilltree.com, the two brands read as one family via the #38bdf8 bridge token, Atlas identity preserved. For W2c: confirm ONE coherent report design language across docs/reports/* + named/report.html, docs/meta/reports/ UNTOUCHED. Absence of evidence of compliance is a FAIL, not a pass. Return the structured verdict.`,
    { label: `review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
  )
  if (!verdict) return { lane: key, branch: L.branch, status: 'review-died', build }

  if (!verdict.pass) {
    const remediation = await agent(
      `${PREAMBLE}\n\nLANE ${key} REMEDIATION (bounded, ONE pass). Branch \`${build.branch}\` already exists on origin — \`git fetch origin ${build.branch} && git checkout ${build.branch}\` in your worktree and CONTINUE it (do not start over).\nThe adversarial reviewer FAILED it. Fix EXACTLY these:\n${JSON.stringify(verdict.failures, null, 2)}\nReviewer evidence: ${verdict.evidence}\nCommit+push each fix under the mbtiongson1 identity. Return the updated build manifest.`,
      { label: `remediate:${key}`, phase: ph, schema: BUILD_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
    )
    if (remediation) {
      verdict = await agent(
        `ADVERSARIAL re-review (reject-by-default) of lane ${key}, branch \`${build.branch}\` after remediation. Same procedure: fetch+checkout, serve docs, Playwright 1280+390, grep. Grade E1-E7 + /impeccable quality. Prior failures were: ${JSON.stringify(verdict.failures)}. Confirm each is resolved and no regression introduced. Return structured verdict.`,
        { label: `re-review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
      )
    }
  }

  return { lane: key, branch: L.branch, status: verdict && verdict.pass ? 'pass' : 'needs-attention', build, verdict }
}

// ── Orchestration: opus pair (max 2 concurrent opus), then W2c opus solo ──
const results = []

phase('W2ab')
results.push(...await parallel([
  () => runLane('W2a', 'W2ab'),
  () => runLane('W2b', 'W2ab'),
]))

phase('W2c')
results.push(await runLane('W2c', 'W2c'))

log(`Wave 2 complete: ${results.map(r => `${r.lane}=${r.status}`).join(', ')}`)
return { wave: 2, base: BASE, lanes: results }
