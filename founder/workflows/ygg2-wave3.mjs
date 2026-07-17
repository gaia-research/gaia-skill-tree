export const meta = {
  name: 'ygg2-wave3',
  description: 'Yggdrasil II Wave 3 — CAPSTONE. (1) Scout inventories mobile-first state across all non-homepage surfaces (2 sonnet, split). (2) 4-wide sonnet critique+remediation sweep: convert max-width→min-width breakpoints (mobile-first E6), fold the carried Wave-1/Wave-2 findings (E3 leaderboard chart-avatar medallion, W2c .report-back-row fixed-nav clearance, W2a unique violet-kicker contrast in generateOgCards.py), each lane build→adversarial review→1 bounded remediation→re-review. (3) Opus-solo finalize DESIGN.md as the solidified /impeccable-init Yggdrasil II standard + clean the inherited Guard-B rank-vocab violations that fail CI on every lane + complete the founder ledger. Homepage FROZEN (only N-1/N-2 already landed in W1f). Recoverable via resumeFromRunId.',
  whenToUse: 'After Wave 2 closes (W2a/W2b/W2c merged). This is the LAST wave — after it, #998 is design-complete, no follow-ups.',
  phases: [
    { title: 'Scout', detail: '2 sonnet — inventory mobile-first + carried-finding state across non-homepage surfaces' },
    { title: 'Sweep', detail: '4-wide sonnet — mobile-first conversion + carried-finding remediation, per-lane review-gated' },
    { title: 'Finalize', detail: 'opus SOLO — solidify DESIGN.md /impeccable standard + clean inherited Guard-B + complete ledger', model: 'opus' },
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
6. Revert Class-P timestamp side-effects (registry/gaia.json, docs/graph/*, docs/css/tokens.css if regen-only) before committing. EXCEPTION: a lane that legitimately regenerates docs/u/ or docs/og/ output (Python-generator lanes) commits that output.

## The merged Yggdrasil II foundation you MUST honor (already on ${BASE} — do NOT reinvent)
- \`docs/js/skill-semantics.js\` → \`window.GaiaSemantics.{computeBranch(node,effRank), rankWord(level,branch), rankLabel(level,branch)}\`. Python: \`gaia_cli.trustMagnitude.computeBranch\` + \`gaia_cli.formatting.rank_word\` (REUSE via sys.path.insert(0, str(Path(__file__).parent.parent / "src"))).
- \`docs/js/plaque.js\` _fieldAvatar = the CANONICAL medallion (GitHub avatar + gold wreath docs/assets/origin-wreath-gold.svg + identicon fallback + AOV4 rank stamp). ROUTE surfaces through it; never re-implement per-surface.
- BANNED words anywhere in NEW output/copy/labels/CSS-selectors/SVG-text: 'Transcendent','Hardened'. Only valid \`type\`: 'basic','fusion'. Dead enum (extra/ultimate/unique reads) is a defect.
- Tokens: NO hex literals in docs/js or docs/css design paths (Guard A). \`--tier-unique\` full family; \`--apex-gold\` #fbbf24 gold origin (red #ef4444 DEPRECATED); \`--tier-basic\`==#38bdf8==Rimuru-Blue cross-brand bridge.
- AOV V4 assets COMPLETE (reuse, no new art): docs/assets/ascension-overdrive/ aov4-c{1..6}-suite-* + aov4-d{4..6}-unique-*, 3 sizes each.

## MOBILE-FIRST is the theme of this wave (E6)
Most Yggdrasil surfaces were authored desktop-first with \`@media (max-width: Npx)\` overrides. Mobile-first means the BASE rule is the mobile layout and \`@media (min-width: Npx)\` PROGRESSIVELY ENHANCES to desktop. Convert the load-bearing breakpoints on your surface from max-width to min-width WITHOUT visual regression at either end (screenshot 390 AND 1280 before/after). Fixed-nav clearance invariant holds: every page-level container under <body> clears ~58px — base 5rem (80px), desktop 6rem (96px) thin / 8rem (128px) full shell; no global body padding-top; no invented values.

## Rubric (DESIGN.md §"Yggdrasil II Enforcement Rubric" E1-E7)
E1 no dead enum. E2 branch-forked rank words, no banned words. E3 plaque/medallion/avatar. E4 red origin→gold. E5 cross-brand Research bridge #38bdf8 (token var). E6 mobile-first non-homepage. E7 tokens & regen hygiene (no hex, prefer Python scripts).

## HOMEPAGE IS FROZEN. Do NOT touch docs/index.html or the homepage-only CSS (world-tree-hero.css hero rules, ascension-overdrive-v4.css terminal rules) beyond what W1f already landed (N-1 terminal edge, N-2 hero card). Non-homepage surfaces ONLY.
`

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['pass', 'failures', 'severity', 'evidence'],
  properties: {
    pass: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'blocker'] },
    evidence: { type: 'string', description: 'What was served, screenshotted (1280+390), and grep-verified.' },
    failures: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
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
  type: 'object', additionalProperties: false,
  required: ['branch', 'shas', 'filesTouched', 'summary'],
  properties: {
    branch: { type: 'string' },
    shas: { type: 'array', items: { type: 'string' } },
    filesTouched: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    selfCheck: { type: 'string', description: 'grep proof of no banned words / no dead-enum / no hex; before/after 390+1280 screenshot observations' },
  },
}

const INVENTORY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['shardFindings', 'summary'],
  properties: {
    summary: { type: 'string' },
    shardFindings: {
      type: 'object', additionalProperties: false,
      description: 'Per-shard inventory of mobile-first + carried-finding state.',
      properties: {
        W3a: { type: 'array', items: { type: 'string' } },
        W3b: { type: 'array', items: { type: 'string' } },
        W3c: { type: 'array', items: { type: 'string' } },
        W3d: { type: 'array', items: { type: 'string' } },
      },
    },
  },
}

// ── Scout definitions (2 sonnet, split the surface list) ──────────────────
const SCOUTS = {
  scoutAB: {
    label: 'scout:trust+discovery',
    task: `SCOUT PASS (sonnet, AUDIT ONLY — no edits, no branch). Fresh worktree checkout of origin/${BASE}. Serve docs (python -m http.server 8101 --directory docs &) and use Playwright at 390 (mobile) AND 1280 (desktop) + grep to inventory the CURRENT mobile-first state and carried-finding state of the TRUST + DISCOVERY surfaces. Classify each concrete defect with a file:line-ish anchor.

Cover these surfaces and populate shardFindings.W3a (trust) and shardFindings.W3b (discovery):
W3a TRUST surfaces:
- docs/heroes/ (index.html + heroes.css + heroes.js): find every \`@media (max-width: ...)\` breakpoint (desktop-first) that should be min-width mobile-first; note fixed-nav clearance on the top container; note any 390px overflow/clipping.
- docs/trust/leaderboard/ (leaderboard.css + leaderboard.js): same max-width audit. ALSO the CARRIED E3 finding — do the leaderboard chart/row avatars carry the gold-wreath medallion (route through plaque _fieldAvatar), or are they bare avatars/initials? Note where the medallion is missing.
W3b DISCOVERY surfaces:
- docs/named/ (index.html) + docs/js/named-skills.js + docs/js/skill-explorer.js consumers: max-width breakpoints, 390px card grid behavior, modal/explorer mobile usability.
- skill-graph (docs/js/skill-graph.js + its host page): mobile rendering + does it load real skills (not FALLBACK_SKILLS).

For each surface list concrete strings like "docs/heroes/heroes.css L512: @media(max-width:768px) — convert to min-width base-mobile" or "leaderboard row avatars L1548 bare, no wreath medallion". Return the structured inventory. NO commits, NO branch.`,
  },
  scoutCD: {
    label: 'scout:profiles+content',
    task: `SCOUT PASS (sonnet, AUDIT ONLY — no edits, no branch). Fresh worktree checkout of origin/${BASE}. Serve docs (python -m http.server 8102 --directory docs &) and use Playwright at 390 (mobile) AND 1280 (desktop) + grep to inventory the CURRENT mobile-first + carried-finding state of the PROFILE/REPORT + CONTENT surfaces. Classify each concrete defect.

Cover these surfaces and populate shardFindings.W3c (profiles+reports) and shardFindings.W3d (content/utility):
W3c PROFILE + REPORT surfaces:
- docs/u/<handle>/ profile pages (GENERATED by scripts/generateProfilePages.py — fix the generator, not the html): max-width breakpoints, 390px hero/medallion layout.
- docs/reports/index.html + docs/reports/2026-28/index.html + docs/named/report.html + scripts/contentEngine/templates/report.html.j2: max-width audit. ALSO the CARRIED W2c finding — the \`.report-back-row\` fixed-nav clearance (it sits under the fixed nav; needs base 5rem / desktop 6rem clearance).
- CARRIED W2a finding — scripts/generateOgCards.py: the unique-branch violet kicker text renders at ~3.36:1 contrast (below 4.5:1). Note the exact rank-label/kicker color path so the sweep can lift contrast (token, not raw hex) while keeping the violet unique identity.
W3d CONTENT/UTILITY surfaces:
- docs/en/mcp-server.html, docs/en/index.html, docs/badges/index.html (badges is a CORE page — mobile audit only, do NOT break renderRows), and any other non-homepage docs/<section>/index.html with desktop-first max-width breakpoints.

For each surface list concrete anchors. Return the structured inventory. NO commits, NO branch.`,
  },
}

// ── Sweep lane definitions (4-wide sonnet) ────────────────────────────────
const LANES = {
  W3a: {
    branch: 'design/ygg2-w3a-trust-mobile',
    label: 'W3a:trust-mobile',
    task: (findings) => `LANE W3a (SONNET) — mobile-first sweep of the TRUST surfaces: docs/heroes/ + docs/trust/leaderboard/.
Scout inventory for this shard:
${JSON.stringify(findings || [], null, 2)}
DO:
1. Convert the load-bearing desktop-first \`@media (max-width: Npx)\` breakpoints on docs/heroes/heroes.css + docs/trust/leaderboard/leaderboard.css to mobile-first (base = mobile layout, \`@media (min-width: Npx)\` enhances). No visual regression at 390 or 1280.
2. CARRIED E3: give the leaderboard chart/row avatars the gold-wreath medallion — route through the shared plaque _fieldAvatar medallion path (docs/js/plaque.js), do NOT re-implement. Bare avatars/initials → framed medallion with identicon fallback; ≤1★ redaction rules respected.
3. Fixed-nav clearance holds on the top container of each page (base 5rem / desktop 6rem-8rem).
Homepage untouched. No banned words, no dead enum, no raw hex (token vars only).
Verify: serve docs, Playwright 390 + 1280 on /heroes/ and the leaderboard, screenshot before/after, confirm mobile-first base renders correctly, leaderboard avatars carry the wreath medallion, nav clearance clean. grep touched files for max-width count reduced / no banned words / no hex.`,
  },
  W3b: {
    branch: 'design/ygg2-w3b-discovery-mobile',
    label: 'W3b:discovery-mobile',
    task: (findings) => `LANE W3b (SONNET) — mobile-first sweep of the DISCOVERY surfaces: docs/named/ + skill-explorer + skill-graph.
Scout inventory for this shard:
${JSON.stringify(findings || [], null, 2)}
DO:
1. Convert desktop-first max-width breakpoints on docs/named/ CSS + the explorer/graph consumer CSS to mobile-first. The /named/ card grid must be a single readable column at 390 and progressively enhance.
2. skill-explorer modal + skill-graph must be usable/legible at 390 (respect skill-explorer.js two-IIFE structure; respect skill-graph.js bootstrap null-check invariant — do NOT recreate stale skills/ root dir, do NOT break the IIFE).
3. Fixed-nav clearance on the top container.
Homepage untouched. No banned words, no dead enum, no raw hex.
Verify: serve docs, Playwright 390 + 1280 on /named/ → open a 2★+ skill (explorer) and the graph, screenshot before/after, confirm mobile-first single-column + usable modal/graph at 390, all five explorer sections still render, no regression at 1280. grep confirms clean.`,
  },
  W3c: {
    branch: 'design/ygg2-w3c-profiles-reports-mobile',
    label: 'W3c:profiles-reports',
    task: (findings) => `LANE W3c (SONNET) — mobile-first sweep of PROFILE + REPORT surfaces + the two carried generator findings. NOTE: this lane touches scripts/generateProfilePages.py + scripts/generateOgCards.py (Python generators) — a design/ branch touching scripts/ trips branch-scope CI; the orchestrator will apply the pre-authorized skip-scope-check label. Fix the GENERATOR, never hand-edit docs/u/*/index.html or docs/og/*.
Scout inventory for this shard:
${JSON.stringify(findings || [], null, 2)}
DO:
1. Mobile-first: convert desktop-first max-width breakpoints on the profile page CSS (via scripts/generateProfilePages.py) + docs/reports/ CSS + docs/named/report.html + scripts/contentEngine/templates/report.html.j2 to mobile-first base.
2. CARRIED W2c: raise .report-back-row (and any report page-level container) to the fixed-nav clearance ladder (base 5rem / desktop 6rem). No global body padding-top.
3. CARRIED W2a: in scripts/generateOgCards.py, lift the unique-branch violet kicker/rank-label text contrast to >=4.5:1 (brighten the violet toward --tier-unique-symbol or add a lighter token; NO raw hex) while keeping the unique identity. Regenerate + COMMIT docs/og/*/*.svg output this lane owns. Reuse gaia_cli computeBranch/rank_word (sys.path.insert). Revert pure-timestamp Class-P noise; do NOT touch docs/badges/_assets/.
Confirm docs/meta/reports/ stays UNTOUCHED. Homepage untouched. No banned words, no dead enum, no raw hex.
Verify: run generators clean; serve docs, Playwright 390 + 1280 on a docs/u/ profile + docs/reports/2026-28/ + docs/named/report.html, screenshot before/after; confirm mobile-first, .report-back-row clears the nav, a regenerated unique OG card kicker passes contrast. grep the scripts + a sample of regenerated SVGs for banned words / #ef4444 / dead-enum → zero.`,
  },
  W3d: {
    branch: 'design/ygg2-w3d-content-mobile',
    label: 'W3d:content-mobile',
    task: (findings) => `LANE W3d (SONNET) — mobile-first sweep of the CONTENT/UTILITY surfaces: docs/en/mcp-server.html, docs/en/index.html, docs/badges/index.html (CORE page — mobile audit + safe fixes only), and any remaining non-homepage docs/<section>/index.html with desktop-first breakpoints.
Scout inventory for this shard:
${JSON.stringify(findings || [], null, 2)}
DO:
1. Convert load-bearing desktop-first max-width breakpoints on these pages' CSS to mobile-first base. 390 must read as a clean single-column/stacked layout; 1280 unchanged.
2. docs/badges/index.html: mobile layout ONLY — do NOT alter renderRows()/currentState destructuring (a missing var blanks all badges). Verify the badge preview still renders after any CSS edit.
3. Fixed-nav clearance on each page's top container.
Homepage untouched. No banned words, no dead enum, no raw hex.
Verify: serve docs, Playwright 390 + 1280 on each touched page, screenshot before/after; confirm mobile-first, badges still render, nav clearance, no 1280 regression. grep confirms clean.`,
  },
}

// ── One sweep lane: build (worktree) → adversarial review → 1 bounded remediation → re-review ──
async function runLane(key, findings, ph) {
  const L = LANES[key]
  const build = await agent(
    `${PREAMBLE}\n\nBranch name for THIS lane: \`${L.branch}\` (create from origin/${BASE}).\n\n${L.task(findings)}\n\nReturn the build manifest.`,
    { label: L.label, phase: ph, schema: BUILD_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
  )
  if (!build) return { lane: key, branch: L.branch, status: 'died', verdict: null }

  let verdict = await agent(
    `You are an ADVERSARIAL design reviewer (reject-by-default). Lane ${key} pushed branch \`${build.branch}\`.\nFiles touched: ${(build.filesTouched || []).join(', ')}.\nBuilder summary: ${build.summary}\nScout inventory this lane addressed: ${JSON.stringify(findings || [])}\n\nPROCEDURE: in your worktree, \`git fetch origin ${build.branch} && git checkout ${build.branch}\`. Serve docs (\`python -m http.server 8103 --directory docs &\`) and load each touched surface with Playwright at 390 (mobile) AND 1280 (desktop); screenshot both. grep touched files for banned words ('Transcendent','Hardened'), dead-enum reads, raw hex.\nGrade against E1-E7 + /impeccable quality, with EMPHASIS on E6 mobile-first (base rule = mobile; min-width enhances; single readable column at 390; no 1280 regression) and fixed-nav clearance. Confirm the CARRIED findings for this lane are resolved (W3a: leaderboard avatar wreath medallion present; W3c: .report-back-row nav clearance + unique OG kicker contrast >=4.5:1). Absence of evidence of compliance is a FAIL. Return the structured verdict.`,
    { label: `review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
  )
  if (!verdict) return { lane: key, branch: L.branch, status: 'review-died', build }

  if (!verdict.pass) {
    const remediation = await agent(
      `${PREAMBLE}\n\nLANE ${key} REMEDIATION (bounded, ONE pass). Branch \`${build.branch}\` already exists on origin — \`git fetch origin ${build.branch} && git checkout ${build.branch}\` and CONTINUE it (do not start over).\nThe adversarial reviewer FAILED it. Fix EXACTLY these:\n${JSON.stringify(verdict.failures, null, 2)}\nReviewer evidence: ${verdict.evidence}\nCommit+push each fix under the mbtiongson1 identity. Return the updated build manifest.`,
      { label: `remediate:${key}`, phase: ph, schema: BUILD_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
    )
    if (remediation) {
      verdict = await agent(
        `ADVERSARIAL re-review (reject-by-default) of lane ${key}, branch \`${build.branch}\` after remediation. Same procedure: fetch+checkout, serve docs, Playwright 390+1280, grep. Grade E1-E7 with mobile-first emphasis. Prior failures were: ${JSON.stringify(verdict.failures)}. Confirm each is resolved and no regression introduced. Return structured verdict.`,
        { label: `re-review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
      )
    }
  }

  return { lane: key, branch: L.branch, status: verdict && verdict.pass ? 'pass' : 'needs-attention', build, verdict }
}

// ── Phase 1: SCOUT (2 sonnet, split) ──────────────────────────────────────
phase('Scout')
const scouts = await parallel([
  () => agent(`${PREAMBLE}\n\n${SCOUTS.scoutAB.task}`, { label: SCOUTS.scoutAB.label, phase: 'Scout', schema: INVENTORY_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }),
  () => agent(`${PREAMBLE}\n\n${SCOUTS.scoutCD.task}`, { label: SCOUTS.scoutCD.label, phase: 'Scout', schema: INVENTORY_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }),
])

const INV = { W3a: [], W3b: [], W3c: [], W3d: [] }
for (const s of scouts.filter(Boolean)) {
  const sf = s.shardFindings || {}
  for (const k of ['W3a', 'W3b', 'W3c', 'W3d']) {
    if (Array.isArray(sf[k])) INV[k].push(...sf[k])
  }
}
log(`Scout complete: W3a=${INV.W3a.length} W3b=${INV.W3b.length} W3c=${INV.W3c.length} W3d=${INV.W3d.length} findings`)

// ── Phase 2: SWEEP (4-wide sonnet, max 4 concurrent) ──────────────────────
phase('Sweep')
const sweep = await parallel([
  () => runLane('W3a', INV.W3a, 'Sweep'),
  () => runLane('W3b', INV.W3b, 'Sweep'),
  () => runLane('W3c', INV.W3c, 'Sweep'),
  () => runLane('W3d', INV.W3d, 'Sweep'),
])

// ── Phase 3: FINALIZE (opus solo) — DESIGN.md standard + Guard-B cleanup + ledger ──
phase('Finalize')
const finalize = await agent(
  `${PREAMBLE}

LANE W3-FINALIZE (OPUS, SOLO) — the capstone. Branch \`design/ygg2-w3z-finalize\` (create from origin/${BASE}; the sweep lanes are separate branches the orchestrator merges before this runs — but if they are not yet merged, base off origin/${BASE} anyway and the orchestrator will sequence).
THREE deliverables:
1. **Solidify DESIGN.md** as the definitive /impeccable-init Yggdrasil II design standard. It currently holds the §"Yggdrasil II Enforcement Rubric" (E1-E7). Finalize it: (a) confirm E1-E7 are complete + precise; (b) add a concise "Yggdrasil II — what shipped" section summarizing the taxonomy (type basic|fusion; branch standard|suite|unique derived via computeBranch), the rank ladders (shared 1-3 Awakened/Named/Evolved; suite 4-6 Extra/Ultimate/Apex; unique 4-6 Unique/Unique Ultimate/Unique Impossible), the medallion system (plaque _fieldAvatar: avatar+gold wreath+AOV4 stamp), the gold origin (#fbbf24, red deprecated), and the cross-brand Rimuru-Blue #38bdf8==--tier-basic bridge to Gaia Research; (c) document the shared resolvers (window.GaiaSemantics + gaia_cli.trustMagnitude.computeBranch/formatting.rank_word) as the single source both client + Python read.
2. **Clean the inherited Guard-B rank-vocab violations.** The design-system lint Guard B (banned-synonym) has failed CI on EVERY Wave-1/2 lane — the hits are pre-existing 'Transcendent'/'Hardened'/rarity-word occurrences in the design/handover DOCS themselves (DESIGN.md, founder/handovers/YGGDRASIL_II_DESIGN_ALIGNMENT.md, docs/agents/guard-topology.md ~L85, and any other doc the guard greps). Run the guard locally (inspect .github/workflows/ design-system lint step to find the exact grep + file globs), find every hit, and REWRITE the offending prose to compliant vocabulary (describe the OLD word as "the deprecated rank word, now X" rather than using it bare) so Guard B passes clean — WITHOUT changing any historical meaning. This is the wave that finally turns Guard B green. Do NOT touch data files or registry.
3. **Complete the founder ledger** — append the Wave 3 rows to founder/YGGDRASIL_II_DESIGN_LEDGER.md (scout + 4 sweep lanes + this finalize), a "WAVE 3 CLOSED / #998 DESIGN-COMPLETE" marker, and the Wave 3 token-spend row.
/impeccable discipline; commit+push per deliverable under the mbtiongson1 identity; report each SHA. Return the build manifest.`,
  { label: 'W3z:finalize', phase: 'Finalize', schema: BUILD_SCHEMA, model: 'opus', effort: 'high', isolation: 'worktree' }
)

log(`Wave 3 complete: sweep=[${sweep.filter(Boolean).map(r => `${r.lane}=${r.status}`).join(', ')}] finalize=${finalize ? finalize.branch : 'died'}`)
return { wave: 3, base: BASE, scouts, inventory: INV, sweep, finalize }
