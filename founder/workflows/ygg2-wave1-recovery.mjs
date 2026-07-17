export const meta = {
  name: 'ygg2-wave1-recovery',
  description: 'Yggdrasil II Wave 1 RECOVERY — W1a (heroes) + W1b (leaderboard) each exhausted their in-workflow remediation retry. Re-remediate the GENUINE Wave-1 defects (E7 dev-artifact, E2 banned-word CSS selectors, E7 fixed-nav clearance) then adversarial re-review scoped correctly: E6 mobile-first rolls to Wave 3, E3 leaderboard-medallion rolls to Wave 1.5 — neither blocks Wave 1. Recoverable via resumeFromRunId.',
  whenToUse: 'After the 4 PASS Wave-1 lanes merged; W1a/W1b still need-attention.',
  phases: [
    { title: 'Recover', detail: 'sonnet pair — surgical Wave-1 defect fixes on the two stalled lanes' },
  ],
}

const BASE = 'dev/yggdrasil-ii-staging'
const IDENT = 'git -c user.name="Marcus Rafael B. Tiongson" -c user.email="153011150+mbtiongson1@users.noreply.github.com"'

const PREAMBLE = `
## Worktree rules — READ BEFORE EDITING ANY FILE
You run with isolation:"worktree" — a SEPARATE checkout. Edits are invisible until pushed.
1. The branch ALREADY EXISTS on origin. Start: \`git fetch origin <branch> && git checkout <branch>\` — CONTINUE it, do not restart.
2. COMMIT IDENTITY IS MANDATORY AND EXACT. Every commit: \`${IDENT} commit -m "..."\`. Audit \`git log --format='%ae'\` before pushing — every line MUST read 153011150+mbtiongson1@users.noreply.github.com.
3. Commit + push after each logical unit: \`git push origin <branch>\` immediately.
4. Report each commit SHA + push status.
5. Revert Class-P timestamp side-effects (registry/gaia.json, docs/graph/*) before committing.

## The merged Yggdrasil II foundation (already on ${BASE})
- \`docs/js/skill-semantics.js\` → window.GaiaSemantics.{computeBranch(node,effRank), rankWord(level,branch), rankLabel(level,branch)}.
- Ladders: shared {1 Awakened,2 Named,3 Evolved}; suite {4 Extra,5 Ultimate,6 Apex}; unique {4 Unique,5 Unique Ultimate,6 Unique Impossible}.
- BANNED anywhere in shipped output/copy/labels/CSS-selectors: 'Transcendent','Hardened'. Only valid type values: 'basic','fusion'.
- Tokens: no hex literals — use var(--token). --tier-unique is a full family; --apex-gold #fbbf24 is the gold origin.
- Gold-wreath SVG: docs/assets/origin-wreath-gold.svg. Red origin (#ef4444) is DEPRECATED → gold.

## SCOPE DISCIPLINE — THIS IS A SURGICAL RECOVERY, NOT A REDESIGN
Fix ONLY the enumerated Wave-1 defects below. Do NOT attempt E6 mobile-first max-width→min-width conversion (that is Wave 3's cross-surface critique sweep) and do NOT attempt E3 leaderboard chart-avatar wreath frames (that is Wave 1.5 N-13 medallion propagation). Those are deliberately owned by later waves and will sweep this surface then. Touching them here risks regression and double-work. Stay in your lane.
`

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['pass', 'failures', 'severity', 'evidence'],
  properties: {
    pass: { type: 'boolean' },
    severity: { type: 'string', enum: ['none', 'minor', 'major', 'blocker'] },
    evidence: { type: 'string' },
    failures: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['clause', 'surface', 'detail'],
        properties: { clause: { type: 'string' }, surface: { type: 'string' }, detail: { type: 'string' } },
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
    selfCheck: { type: 'string' },
  },
}

const LANES = {
  W1a: {
    branch: 'design/ygg2-w1a-heroes',
    label: 'recover:W1a',
    fix: `LANE W1a RECOVERY — docs/heroes/. TWO genuine Wave-1 defects remain (prior remediation stalled with 0 commits):
1. **E7 dev artifact** — docs/heroes/index.html L204-206 contains a committed local-dev live-reload script:
     <!-- impeccable-live-start -->
     <script src="http://localhost:8400/live.js"></script>
     <!-- impeccable-live-end -->
   DELETE all three lines (the two comment markers + the script tag). This is a localhost dev tool that must never ship.
2. **E2 banned word in CSS** — docs/heroes/heroes.css has 4 \`.hero-stage--transcendent\` class selectors (~L523, L937, L944, L952). The JS stageTierClass() no longer emits this class (dead), but the banned word 'transcendent' survives in the shipped stylesheet. RENAME the selector to a compliant branch word — use \`.hero-stage--apex\` (the 6★ suite rank) since these crest/diamond styles are the top-stage treatment. Update ALL 4 selector occurrences consistently. If heroes.js has any matching classList reference, update it too (grep for 'transcendent' in docs/heroes/*.js and fix any live emitter to the same --apex class).
Verify: grep -rni transcendent docs/heroes/ → ZERO. grep localhost:8400 docs/heroes/ → ZERO. Serve docs, open /heroes/, confirm the top-rank hero stage still renders styled (crest/diamond visible), avatars+wreaths intact, no console errors. Do NOT touch the max-width media queries (Wave 3) or restructure layout.`,
  },
  W1b: {
    branch: 'design/ygg2-w1b-leaderboard-remediate',
    label: 'recover:W1b',
    fix: `LANE W1b RECOVERY — docs/trust/leaderboard/leaderboard.css. ONE genuine Wave-1 defect remains:
1. **E7 fixed-nav clearance** — the \`.lb-shell\` base rule (~L15) sets padding-top: 2.5rem (~40px). Per CLAUDE.md "Fixed-nav clearance" invariant, every page-level container directly under <body> MUST clear the ~58px fixed nav. lb-shell is the first layout container and site-nav is position:fixed (takes no flow), so the hero breadcrumb/title is clipped under the nav.
   FIX: raise the .lb-shell base padding-top to **5rem (80px)** (the base value in the value ladder), and add a desktop bump to **6rem (96px)** inside the existing min-width desktop context if one exists, or leave base 5rem if there's no desktop media block to hook (do NOT invent new max-width queries). Use rem units, no hex, no other layout change.
Verify: serve docs, open the leaderboard at 1280 desktop AND 390 mobile, screenshot both, confirm the hero title/breadcrumb is fully BELOW the fixed nav (not clipped) at both widths. grep confirms padding-top >= 5rem on .lb-shell base. Do NOT convert max-width→min-width breakpoints (Wave 3) and do NOT add wreath frames to chart avatars (Wave 1.5 N-13).`,
  },
}

async function recoverLane(key, ph) {
  const L = LANES[key]
  const build = await agent(
    `${PREAMBLE}\n\nBranch for THIS lane (already on origin — fetch+checkout+continue): \`${L.branch}\`.\n\n${L.fix}\n\nReturn the build manifest.`,
    { label: L.label, phase: ph, schema: BUILD_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
  )
  if (!build) return { lane: key, branch: L.branch, status: 'died', verdict: null }

  const verdict = await agent(
    `You are an ADVERSARIAL design reviewer (reject-by-default), but SCOPED to Wave-1 recovery only. Lane ${key}, branch \`${build.branch}\`.
Builder summary: ${build.summary}
Self-check: ${build.selfCheck || 'n/a'}

PROCEDURE: in your worktree, \`git fetch origin ${build.branch} && git checkout ${build.branch}\`. Serve docs (\`python -m http.server 8098 --directory docs &\`), load the target surface with Playwright at 1280 AND 390, screenshot both. grep the touched files.

GRADE ONLY THESE (the enumerated Wave-1 defects for this lane):
${key === 'W1a'
  ? '- E7: docs/heroes/index.html must have ZERO localhost:8400 / live.js / impeccable-live markers.\n- E2: docs/heroes/*.css and *.js must have ZERO occurrences of the banned word "transcendent" (case-insensitive). The top-rank hero stage must still render styled (crest/diamond visible) — confirm no regression from the selector rename.'
  : '- E7: docs/trust/leaderboard/leaderboard.css .lb-shell base padding-top must be >= 5rem (80px); the leaderboard hero title/breadcrumb must render fully below the fixed nav (not clipped) at both 1280 and 390.'}

EXPLICITLY OUT OF SCOPE — do NOT fail the lane on these (they are owned by later waves and will be swept then):
- E6 mobile-first (max-width vs min-width breakpoints) → Wave 3 critique sweep.
- E3 leaderboard chart-avatar gold-wreath frames → Wave 1.5 N-13 medallion propagation.
If you observe those, note them in evidence as "deferred (Wave 3 / Wave 1.5)" but they MUST NOT set pass=false.

Return the structured verdict.`,
    { label: `re-review:${key}`, phase: ph, schema: VERDICT_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
  )

  return { lane: key, branch: L.branch, status: verdict && verdict.pass ? 'pass' : 'needs-attention', build, verdict }
}

phase('Recover')
const results = await parallel([
  () => recoverLane('W1a', 'Recover'),
  () => recoverLane('W1b', 'Recover'),
])

log(`Wave 1 recovery complete: ${results.filter(Boolean).map(r => `${r.lane}=${r.status}`).join(', ')}`)
return { wave: '1-recovery', base: BASE, lanes: results }
