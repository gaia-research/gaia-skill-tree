export const meta = {
  name: 'ygg2-wave15-medallion',
  description: 'Yggdrasil II Wave 1.5 — N-13 medallion propagation. Single Opus subagent VERIFIES current state of 7 medallion items against merged Wave-1, then remediates each (already-done → confirm w/ Playwright evidence; miss → fix). Wreath-art redraw + profile generator + heroes + named + skill-graph load-fix. Homepage untouched. Recoverable.',
  whenToUse: 'After Wave 1 fully closes (W1a/W1b merged); before Wave 2.',
  phases: [
    { title: 'Verify', detail: 'opus SOLO — audit 7 medallion items against merged staging, capture Playwright evidence', model: 'opus' },
    { title: 'Remediate', detail: 'opus SOLO — fix the misses (wreath art, profile gen, heroes badge, named medallion, skill-graph load)', model: 'opus' },
    { title: 'Review', detail: 'sonnet — adversarial verification of the remediation', model: 'sonnet' },
  ],
}

const BASE = 'dev/yggdrasil-ii-staging'
const IDENT = 'git -c user.name="Marcus Rafael B. Tiongson" -c user.email="153011150+mbtiongson1@users.noreply.github.com"'
const BRANCH = 'design/ygg2-w15-medallion'

const PREAMBLE = `
## Worktree rules — READ BEFORE EDITING ANY FILE
isolation:"worktree" — separate checkout, edits invisible until pushed.
1. Branch FROM ORIGIN: \`git checkout -b ${BRANCH} origin/${BASE}\`.
2. COMMIT IDENTITY EXACT: every commit \`${IDENT} commit -m "..."\`. Audit \`git log --format='%ae'\` before push — every line MUST be 153011150+mbtiongson1@users.noreply.github.com.
3. Commit+push after each logical unit: \`git push origin ${BRANCH}\`.
4. Report each SHA + push status.
5. Revert Class-P timestamp side-effects EXCEPT the profile/og output this lane legitimately regenerates.

## The merged Yggdrasil II medallion foundation (already on ${BASE})
- \`docs/js/plaque.js\` _fieldAvatar path = the CANONICAL medallion: GitHub avatar (https://github.com/<handle>.png) + gold wreath frame (docs/assets/origin-wreath-gold.svg) + GitHub-blank identicon fallback + AOV4 rank badge stamp. This is the SINGLE source; do NOT re-implement per surface — ROUTE each surface through it (or mirror it exactly if server-rendered in Python).
- \`docs/js/skill-semantics.js\` → window.GaiaSemantics.{computeBranch, rankWord, rankLabel}.
- Tokens only, no hex. Gold origin = --apex-gold #fbbf24. Red #ef4444 origin is DEPRECATED.
- AOV4 badge stamps: docs/assets/ascension-overdrive/ aov4-c{1..6}-suite-* (suite), aov4-d{4..6}-unique-* (unique), 3 sizes each — COMPLETE, reuse.
- Python medallion path: scripts/generateProfilePages.py already emits data-branch + medallion on server-rendered plaques (W1e). REUSE gaia_cli.trustMagnitude.computeBranch + gaia_cli.formatting.rank_word; sys.path.insert(0, str(Path(__file__).parent.parent / "src")).
`

const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['items', 'skillGraphLoads', 'summary'],
  properties: {
    skillGraphLoads: { type: 'boolean', description: 'Does docs/js/skill-graph.js render real skills on a clean serve, or fall back to FALLBACK_SKILLS?' },
    summary: { type: 'string' },
    items: {
      type: 'array',
      description: 'One entry per N-13 item 1-7.',
      items: {
        type: 'object', additionalProperties: false,
        required: ['item', 'state', 'evidence', 'action'],
        properties: {
          item: { type: 'string', description: 'e.g. "1 wreath-art", "2 name-badge-swap", "3 profile-wreath-avatar", "4 profile-hero-centered", "5 heroes-badge", "6 named-medallion", "7 skill-graph"' },
          state: { type: 'string', enum: ['done', 'partial', 'missing', 'broken'] },
          evidence: { type: 'string', description: 'Playwright/grep proof of current state on merged staging.' },
          action: { type: 'string', description: 'confirm | fix-what' },
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
    selfCheck: { type: 'string' },
  },
}
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
        required: ['item', 'surface', 'detail'],
        properties: { item: { type: 'string' }, surface: { type: 'string' }, detail: { type: 'string' } },
      },
    },
  },
}

// ── Phase 1: VERIFY (opus solo) ──────────────────────────────────────────
phase('Verify')
const audit = await agent(
  `${PREAMBLE}

LANE Wave 1.5 N-13 — VERIFICATION PASS (opus, solo). Do NOT edit yet — AUDIT only, on a fresh worktree checkout of origin/${BASE}. Serve docs (python -m http.server 8097 --directory docs &) and use Playwright (1280 + 390) + grep to establish the CURRENT state of each of the 7 medallion items against the MERGED Wave-1 result. The founder's note: "these COULD have been implemented already — if so take this as review + nitpick." So your job is to classify each item done|partial|missing|broken WITH EVIDENCE.

The 7 items:
1. **Wreath art** — docs/assets/origin-wreath-gold.svg: do the laurel leaves read as recognizable leaves (paired/veined/curving), or minimal shapes? (state=partial if minimal.)
2. **Profile name↔badge swap + size** — docs/u/<handle>/ (served by scripts/generateProfilePages.py): is the profile name still above/before the badge, or swapped? Is the badge slightly larger?
3. **Profile wreath+avatar** — do docs/u/ pages show a gold-wreath-framed GitHub avatar (the medallion)?
4. **Profile hero centered avatar** — is the (wreathed) avatar centered in each profile's hero section?
5. **/heroes/ badge** — Hall of Heroes cards: W1a added avatars+wreath; did it also land the AOV4 rank BADGE/medallion stamp? (Check the merged W1a result now on staging.)
6. **Named contributors** — docs/named/: still old red origin / no wreath / no badge / no avatars, or does it now carry the medallion? (W1c touched named — verify vs remediate.)
7. **Skill graph** — docs/js/skill-graph.js: does it LOAD and render real skills on a clean serve, or silently fall back to FALLBACK_SKILLS? (Known issue: null overlay-button querySelector(...).addEventListener at bootstrap aborts the IIFE. Do NOT recreate the stale skills/ root dir.) Also: does it carry the medallion system?

Set skillGraphLoads accordingly. Return the structured audit — NO commits.`,
  { label: 'verify:N-13', phase: 'Verify', schema: VERIFY_SCHEMA, model: 'opus', effort: 'high', isolation: 'worktree' }
)

// ── Phase 2: REMEDIATE (opus solo) ───────────────────────────────────────
phase('Remediate')
const build = await agent(
  `${PREAMBLE}

LANE Wave 1.5 N-13 — REMEDIATION (opus, solo). Branch \`${BRANCH}\` (create from origin/${BASE}). The verification pass classified the 7 items as follows:
${JSON.stringify(audit && audit.items, null, 2)}
Skill graph loads cleanly: ${audit ? audit.skillGraphLoads : 'unknown'}.
Auditor summary: ${audit ? audit.summary : 'n/a'}

For each item marked partial|missing|broken, FIX it. For items marked done, no action (the reviewer will confirm). Fix guidance:
- Item 1 (wreath art): redraw docs/assets/origin-wreath-gold.svg laurel leaves as recognizable paired/veined/curving leaf forms — token-tinted gold, scalable, lightweight. This ART revision lands in THIS PR. Since plaque.js/generators reference it by path, the redraw propagates everywhere automatically.
- Items 2-4 (profile): fix in scripts/generateProfilePages.py (do NOT hand-edit docs/u/*/index.html) — name↔badge swap, badge larger, gold-wreath avatar medallion, centered hero avatar. Then regenerate and COMMIT the docs/u/*/index.html output this lane owns.
- Item 5 (/heroes/ badge): if W1a didn't land the AOV4 badge stamp, add it — route through the shared plaque medallion path, don't re-implement.
- Item 6 (named): if named still lacks the medallion, route docs/js/named-skills.js card render through the shared plaque _fieldAvatar path.
- Item 7 (skill-graph): if it doesn't load, fix the bootstrap (null-check the overlay-button querySelector before addEventListener) FIRST; then propagate the medallion. Investigate-first — confirm the root cause before editing.
ROOT PRINCIPLE: route ALL surfaces through the shared plaque/medallion path (or mirror it exactly in Python), never bespoke per-surface re-implementation. Homepage UNTOUCHED.
Commit+push per logical unit. Return the build manifest.`,
  { label: 'remediate:N-13', phase: 'Remediate', schema: BUILD_SCHEMA, model: 'opus', effort: 'high', isolation: 'worktree' }
)

// ── Phase 3: REVIEW (sonnet adversarial) ─────────────────────────────────
phase('Review')
let verdict = null
if (build) {
  verdict = await agent(
    `ADVERSARIAL design reviewer (reject-by-default). Wave 1.5 N-13 medallion, branch \`${build.branch}\`.
Builder summary: ${build.summary}
Files touched: ${(build.filesTouched || []).join(', ')}
Original audit: ${JSON.stringify(audit && audit.items)}

PROCEDURE: fetch+checkout the branch, serve docs, Playwright 1280+390 screenshots, grep. Confirm EACH of the 7 N-13 items is now done (recognizable laurel leaves; profile name↔badge swapped + badge larger; profile gold-wreath avatar medallion present + hero avatar centered; /heroes/ badge present; named medallion present; skill graph LOADS real skills + carries medallion). Verify no bespoke re-implementation (surfaces route through the shared plaque/medallion path). Verify homepage untouched, no banned words, no hex, gold not red origin, identity mbtiongson1 only. Absence of evidence = FAIL. Return structured verdict.`,
    { label: 're-review:N-13', phase: 'Review', schema: VERDICT_SCHEMA, model: 'sonnet', effort: 'high', isolation: 'worktree' }
  )
}

log(`Wave 1.5 N-13 complete: build=${build ? build.branch : 'died'} verdict=${verdict ? (verdict.pass ? 'PASS' : 'needs-attention') : 'n/a'}`)
return { wave: '1.5', base: BASE, branch: BRANCH, audit, build, verdict }
