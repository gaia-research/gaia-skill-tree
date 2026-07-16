export const meta = {
  name: 'ygg2-wave1',
  description: 'Yggdrasil II Wave 1 — 6 surface lanes import the merged foundation (skill-semantics.js, --tier-unique, gold wreath, plaque.js). Each lane: builder in worktree → adversarial reviewer (Playwright, E1-E7) → bounded remediation. Concurrency honored: sonnet lanes 2-at-a-time, opus Python lane SOLO.',
  whenToUse: 'After Wave 0 (foundation) merged to dev/yggdrasil-ii-staging.',
  phases: [
    { title: 'W1e-python', detail: 'opus SOLO — branch-aware badges/og/profile scripts', model: 'opus' },
    { title: 'W1ab', detail: 'sonnet pair — heroes ladder+avatar, leaderboard banned-words+origin' },
    { title: 'W1cd', detail: 'sonnet pair — named filters/grouping, skill-explorer flow+N-11 fuse CTA' },
    { title: 'W1f', detail: 'sonnet — N-9 MCP sweep, N-1 terminal edge, N-2 hero card' },
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
6. Revert Class-P timestamp side-effects (registry/gaia.json, docs/graph/*, docs/css/tokens.css if regen-only) before committing — those belong to a separate infra PR, not your design commit. EXCEPTION: the W1e Python lane owns its regenerated docs/og and docs/u output; commit those.

## The merged Yggdrasil II foundation you MUST import (already on ${BASE})
- \`docs/js/skill-semantics.js\` exposes \`window.GaiaSemantics = { computeBranch(node, effRank), rankWord(level, branch), rankLabel(level, branch) }\`.
  - computeBranch returns 'standard' | 'suite' | 'unique'. Read order (do NOT reorder): unique = type==='basic' && rank>=4 && !suiteComponents; suite = suiteComponents present; else standard.
  - rankWord ladders: shared {1 Awakened, 2 Named, 3 Evolved}; suite {4 Extra, 5 Ultimate, 6 Apex}; unique {4 Unique, 5 Unique Ultimate, 6 Unique Impossible}.
- BANNED words anywhere in output/copy/labels: 'Transcendent', 'Hardened'. Use rankWord/rankLabel — never a stored type/tier/branch field, never skill.type==='ultimate'|'unique'|'extra'.
- Only valid \`type\` values are 'basic' and 'fusion'. The old enum (extra/ultimate/unique) is DEAD — any read of it is a defect to remove.
- Tokens: \`--tier-unique\` is now a full family in docs/css/tokens.css (#7c3aed, -rgb/-bg/-border/-edge/-symbol '◉'). Unique = DARKER plaque; suite = GOLD. NO hex fallbacks (CI guard rejects hex in CSS/JS design tokens — use var(--...)).
- Gold-wreath avatar frame SVG: \`docs/assets/origin-wreath-gold.svg\`. Red origin mark (#ef4444) is DEPRECATED → gold.
- If your surface loads consumer JS via <script>, ensure skill-semantics.js is loaded BEFORE it (add the <script src> if the HTML host page is yours to edit).

## Rubric you will be graded against (DESIGN.md §"Yggdrasil II Enforcement Rubric", clauses E1-E7)
E1 no dead enum (use computeBranch). E2 branch-forked rank words, no banned words. E3 plaque/medallion/avatar (GitHub avatar + gold wreath + identicon fallback + AOV4 stamp; unique DARKER, suite GOLD; no standalone GitHub button). E4 red origin → gold. E5 cross-brand Research bridge = Rimuru-Blue #38bdf8 (token var). E6 mobile-first non-homepage. E7 tokens & regen hygiene (no hex, prefer Python scripts).
`

// ── Reviewer verdict schema ───────────────────────────────────────────────
const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['pass', 'failures', 'severity', 'evidence'],
  properties: {
    pass: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'blocker'] },
    evidence: { type: 'string', description: 'What was served, screenshotted, and grep-verified; desktop 1280 + mobile 390 observations.' },
    failures: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['clause', 'surface', 'detail'],
        properties: {
          clause: { type: 'string', description: 'E1..E7' },
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
    selfCheck: { type: 'string', description: 'grep results proving no banned words / no dead-enum reads remain in touched files' },
  },
}

// ── Lane definitions ──────────────────────────────────────────────────────
const LANES = {
  W1a: {
    branch: 'design/ygg2-w1a-heroes',
    model: 'sonnet', effort: 'high',
    label: 'W1a:heroes',
    task: `LANE W1a — docs/heroes/heroes.js (Hall of Heroes).
Targets:
- KILL live banned words: getTierMarkLabel / classifyTier / TIER_LABEL around L44-118 emit 'Transcendent'/'Hardened'. Replace the whole tier-labelling path with window.GaiaSemantics.rankWord/rankLabel driven by computeBranch(node, effRank). No stored tier reads.
- Branch-fork the 4★-6★ ladder so HoH /heroes correctly displays ranks 4→6 per branch (suite: Extra/Ultimate/Apex; unique: Unique/Unique Ultimate/Unique Impossible).
- Avatar: every hero card shows a GitHub avatar framed by the gold wreath (docs/assets/origin-wreath-gold.svg), with a GitHub-blank identicon fallback when no avatar. Redact ≤1★ per existing redaction rules.
- Remove any red origin mark; if plaque.js renders the cards, reuse its _fieldAvatar path rather than duplicating.
Ensure heroes.html loads skill-semantics.js before heroes.js.
Verify: serve docs, open /heroes/, confirm 4-6★ heroes read correct branch words, avatars+wreaths present, zero 'Transcendent'/'Hardened' in DOM. grep the file for the banned words and for skill.type ==='ultimate'|'unique'|'extra' — must be zero live reads.`,
  },
  W1b: {
    branch: 'design/ygg2-w1b-leaderboard',
    model: 'sonnet', effort: 'high',
    label: 'W1b:leaderboard',
    task: `LANE W1b — docs/trust/leaderboard/leaderboard.js.
Targets:
- RANK_NAMES ~L47-49 and the rank tooltip ~L2350 carry banned words → replace with branch-forked GaiaSemantics.rankWord/rankLabel.
- TYPE_COLORS ~L153-157 keys on the dead enum → rekey to branch (standard/suite/unique) using tokens: suite=--tier gold family, unique=--tier-unique. No hex literals.
- Origin laurel glyph at ~L326 / ~L1091 / ~L1548 / ~L1751 is honor-RED → switch to gold (token var), or reuse the gold wreath. No #ef4444.
Ensure the leaderboard HTML host loads skill-semantics.js before leaderboard.js.
Verify: serve docs, open the leaderboard, screenshot desktop+mobile, confirm rank names correct per branch, laurels gold not red, zero banned words in DOM/source. grep confirms.`,
  },
  W1c: {
    branch: 'design/ygg2-w1c-named',
    model: 'sonnet', effort: 'high',
    label: 'W1c:named',
    task: `LANE W1c — docs/named/index.html (filter tabs L96-99) + docs/js/named-skills.js (rank grouping, buckets L141/151/256/530).
Targets:
- Filter tabs currently key on dead type enum → change to the canonical axis: TYPE = Basic / Fusion (generic node type). Do NOT expose extra/ultimate/unique as type filters.
- Rank grouping in named-skills.js: buckets must group by rank INTEGER (1..6), and within a rank≥4 group the branch (suite vs unique, via computeBranch) is a VISUAL VARIANT (suite=gold plaque, unique=dark plaque) — not a separate bucket.
- All rank labels via GaiaSemantics.rankWord/rankLabel. Zero banned words. Zero skill.type==='ultimate'|'unique'|'extra' reads.
Ensure index.html loads skill-semantics.js before named-skills.js.
Verify: serve docs, open /named/, exercise filters, confirm Basic/Fusion tabs, rank groups 1-6 correct, suite/unique visual split within 4★+ groups, avatars+wreaths on cards. grep confirms clean.`,
  },
  W1d: {
    branch: 'design/ygg2-w1d-explorer',
    model: 'sonnet', effort: 'high',
    label: 'W1d:explorer',
    task: `LANE W1d — docs/js/skill-explorer.js.
Targets:
- N-5 flow suite/ultimate tabs: reuse the existing tab affordance; ensure the fusion/suite flow panels (seFlowShowFusion ~L1311, suite toggle ~L1314-1323) render correct branch-forked rank words via GaiaSemantics.
- Plaque z-index overlap bug: fix plaques overlapping in the flow/synthesis view.
- SE-3 install-flag: L827 conflates level==='5★' — fix so install availability is not tied to a hard-coded star string; derive from the skill's installable/links.github state.
- Dead read at ~L2398: type==='unique' + hex literal — remove, derive via computeBranch + token var.
- **N-11 Research-product CTA (shared cross-brand component, Rimuru-Blue #38bdf8 bridge):** on EVERY fuse/suite section (fusion synthesis rows ~L393-403, flow fusion/suite buttons ~L1311-1323, suiteComponents install block ~L832, fusion-recipe evidence tiles ~L938-953) add a reusable "Research product" CTA affordance with TWO links:
    (1) CTA → the live Gaia Research fusion product: https://research.gaiaskilltree.com/labs/infinite-skill-craft  (label e.g. "Fuse skills on Gaia Research →")
    (2) Repo → https://github.com/gaia-research/skill-fuse  (verified PUBLIC; label e.g. "gaia-research/skill-fuse")
  Style it in the Rimuru-Blue bridge language (#38bdf8 == --tier-basic token; prefer the token var). It is a hyperlink-out only — do NOT import skill-fuse code/schema. Make it a single shared helper (e.g. _researchProductCta(...)) reused across all fuse sections, not copy-pasted buttons.
Ensure the explorer host page loads skill-semantics.js before skill-explorer.js. Respect the file's two-IIFE structure (L1-1862, L1864-end don't share scope — re-declare or hang shared bits off window).
Verify: serve docs, open /named/ → click a 2★+ / fusion skill → confirm all five explorer sections render, flow tabs work, no plaque overlap, CTA appears on every fuse section with both working links, zero banned words / dead enum. grep confirms.`,
  },
  W1e: {
    branch: 'design/ygg2-w1e-python',
    model: 'opus', effort: 'high',
    label: 'W1e:python',
    solo: true,
    task: `LANE W1e (OPUS, SOLO) — Python design scripts made branch-aware. This is the highest-correctness lane.
Targets (fix the GENERATOR, then regenerate outputs):
- scripts/generateBadges.py: RANK_NAMES ~L54-57 carries banned words → branch-forked ladder (mirror skill-semantics.js exactly: shared 1-3, suite 4-6 Extra/Ultimate/Apex, unique 4-6 Unique/Unique Ultimate/Unique Impossible). HONOR_RED ~L47 → gold. Dispatch rank/branch via a Python computeBranch equivalent (type==='basic' && rank>=4 && !suiteComponents = unique; suiteComponents = suite; else standard). NOTE: PyPI already merged a Python computeBranch in #996 — REUSE it if importable (search src/gaia_cli for compute_branch/computeBranch) rather than re-deriving.
- scripts/generateOgCards.py: resolve_type_for_og dispatch ~L157-170 keys on the dead enum so EVERY named skill currently falls to the barren "Basic Skill" fallback plate — rewrite dispatch on computeBranch+rank so all 6 ranks × 2 branches get a proper composition. rank_words ~L652-658 bakes HARDENED/TRANSCENDENT into SVG <text> → branch-forked. Top-right bare "Basic Skill" label → branch-forked rank label. (Full /impeccable art reshape is Wave 2 W2a — here just make dispatch+labels CORRECT and kill the fallback dead-zone; embed the matching AOV4 -hero asset if straightforward, else leave the art hook for W2a.)
- scripts/generateProfilePages.py: L197/L375 emit frozen data-type/data-level from the dead enum (N-3 frozen profile pages) → derive data-branch + correct data-level via computeBranch; add branch aria labels.
- **teach scripts/generateCssTokens.py to emit the --tier-unique family** so a future \`gaia dev docs\` regen does NOT drop it / re-expose hex fallbacks. If the source value lives in registry/schema/meta.json (meta.typeColors), add the unique entry there too (schema change — that's fine on this unrestricted-scope PR).
Regenerate: run the scripts, commit the regenerated docs/og/*/*.svg and docs/u/*/index.html + docs/badges/index.html output THIS lane owns. Do NOT touch docs/badges/_assets/*/ SVGs — that regen is a SEPARATE infra/badge-* PR (badge invariant); leave _assets alone.
Set sys.path.insert(0, str(Path(__file__).parent.parent / "src")) if importing from src/gaia_cli.
Verify: run each script clean, spot-check a regenerated ruflo/mattpocock OG card (was "Basic Skill" fallback → now correct branch+rank plate), a profile page (correct data-branch/data-level), a badge (correct rank word, gold not red). grep the scripts + regenerated output for 'Transcendent'/'Hardened'/'HONOR_RED'/#ef4444 — zero. Run \`python scripts/build_docs.py\` if needed to keep cache-busting consistent; revert pure-timestamp Class-P noise.`,
  },
  W1f: {
    branch: 'design/ygg2-w1f-copy',
    model: 'sonnet', effort: 'medium',
    label: 'W1f:copy',
    task: `LANE W1f — copy/CSS sweep.
Targets:
- **N-9 MCP sweep:** replace stale MCP package/endpoint refs with the canonical ones: package \`@gaia-registry/mcp@0.1.0\` (the main README currently has inconsistent \`@gaia-registry/mcp-server\` refs) and endpoint \`research.gaiaskilltree.com/mcp\`. Sweep these files: docs/index.html (2 occurrences), docs/en/index.html, docs/en/mcp-server.html, docs/agent.md, README.md (4 occurrences). Read each occurrence in context before editing — some are code blocks, some prose. Keep internal consistency.
- **N-1 homepage terminal edge (homepage MINOR change — allowed):** the shared .aov-terminal-art rule (docs/css/ascension-overdrive-v4.css ~L532-545, .aov-terminal-art--impossible ~L547-550) renders a hard black rectangle because the raster webp is black-backed forced into aspect-ratio:1.5. Apply ONE soft edge treatment to the SHARED .aov-terminal-art rule (recommend mix-blend-mode: screen OR a radial/linear alpha mask feathering into the dark section bg) so BOTH terminals (suite Apex ~L1045 and unique Impossible ~L1069-1093 in docs/index.html) resolve with no hard seam. Also check responsive dupes at v4.css ~L865-878, L1017-1052, L1129-1163.
- **N-2 hero install card alignment (homepage MINOR change — allowed):** docs/index.html ~L359-374 .hero-tree-install-copy is a 2-col grid holding 3 children so title+toggle share a row at mismatched baselines. Fix via explicit grid rows (title+toggle row1 sharing baseline via align-items:center, command row2 spanning both cols) OR a flex title+toggle row. Scope to the primary card; do NOT regress the two ghost sibling cards (Submit a skill / Get a README badge, ~L375-388). Check mobile breakpoints world-tree-hero.css ~L916/L962/L1160.
No hex literals in new CSS — use design tokens. Homepage is otherwise FROZEN: touch only N-1 and N-2.
Verify: serve docs, screenshot homepage desktop+mobile (both terminals seam-free, hero install card aligned), grep the MCP files to confirm no stale @gaia-registry/mcp-server refs remain.`,
  },
}

// ── One lane: build (worktree) → adversarial review → 1 bounded remediation → re-review ──
// ph = explicit phase string (passed to every agent to avoid races inside parallel()).
async function runLane(key, ph) {
  const L = LANES[key]
  const build = await agent(
    `${PREAMBLE}\n\nBranch name for THIS lane: \`${L.branch}\` (create from origin/${BASE}).\n\n${L.task}\n\nReturn the build manifest.`,
    { label: L.label, phase: ph, schema: BUILD_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
  )
  if (!build) return { lane: key, branch: L.branch, status: 'died', verdict: null }

  let verdict = await agent(
    `You are an ADVERSARIAL design reviewer (reject-by-default). Lane ${key} pushed branch \`${build.branch}\`.\nFiles touched: ${(build.filesTouched || []).join(', ')}.\nBuilder summary: ${build.summary}\n\nPROCEDURE: in your worktree, \`git fetch origin ${build.branch} && git checkout ${build.branch}\`. Serve docs locally (\`python -m http.server 8099 --directory docs &\`) and load the target surface with Playwright at 1280 (desktop) AND 390 (mobile); screenshot both. Also grep the touched files for banned words ('Transcendent','Hardened'), dead-enum reads (type==='ultimate'|'unique'|'extra'), and hex literals (#ef4444 and other raw hex in JS/CSS design paths).\nGrade against DESIGN.md rubric clauses E1-E7 (schema-read correctness, branch-forked rank words, plaque/medallion/avatar+wreath, red→gold origin, Rimuru-Blue #38bdf8 Research bridge, mobile-first, token/regen hygiene). Absence of evidence of compliance is a FAIL, not a pass. Return the structured verdict.`,
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
        `ADVERSARIAL re-review (reject-by-default) of lane ${key}, branch \`${build.branch}\` after remediation. Same procedure: fetch+checkout, serve docs, Playwright 1280+390, grep. Grade E1-E7. Prior failures were: ${JSON.stringify(verdict.failures)}. Confirm each is resolved and no regression introduced. Return structured verdict.`,
        { label: `re-review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: L.model, effort: L.effort, isolation: 'worktree' }
      )
    }
  }

  return { lane: key, branch: L.branch, status: verdict && verdict.pass ? 'pass' : 'needs-attention', build, verdict }
}

// ── Orchestration: opus lane SOLO first, then sonnet lanes in pairs (max 2) ──
const results = []

// W1e — opus, SOLO. Nothing else runs concurrently.
phase('W1e-python')
results.push(await runLane('W1e', 'W1e-python'))

// Sonnet pairs (max 2 concurrent, both sonnet — honors "max 1 if opus").
phase('W1ab')
results.push(...await parallel([
  () => runLane('W1a', 'W1ab'),
  () => runLane('W1b', 'W1ab'),
]))

phase('W1cd')
results.push(...await parallel([
  () => runLane('W1c', 'W1cd'),
  () => runLane('W1d', 'W1cd'),
]))

phase('W1f')
results.push(await runLane('W1f', 'W1f'))

log(`Wave 1 complete: ${results.map(r => `${r.lane}=${r.status}`).join(', ')}`)
return { wave: 1, base: BASE, lanes: results }
