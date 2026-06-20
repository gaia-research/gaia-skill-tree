export const meta = {
  name: 'june-2026-meta-post',
  description: 'Compose the comprehensive June 2026 GAIA meta-shift report — pre-Phase-1 baseline through current Phase 1.5 progress, technical-paper format with show-not-tell hero, ASCII figures, formulas, complete appendix.',
  phases: [
    { title: 'Research', detail: 'Six parallel readers each map one era/sub-system to facts' },
    { title: 'FactCheck', detail: 'Adversarial verifier per section, refute-default' },
    { title: 'Figures', detail: 'ASCII figures + appendix tables built from registry data' },
    { title: 'Synthesize', detail: 'Stitch sections + figures into single ~400-line technical paper' },
    { title: 'Render', detail: 'Final compose pass — frontmatter, headings, references' },
  ],
}

const SECTION_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    body: { type: 'string', description: 'Markdown body of this section, 200-600 words. Use tables, ASCII figures, fenced code as needed. NO frontmatter (added later).' },
    citations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          source: { type: 'string', description: 'PR number, commit SHA, file path, or issue number that supports the claim' },
        },
        required: ['claim', 'source'],
      },
    },
  },
  required: ['title', 'body', 'citations'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean', description: 'Default to refuted=true if uncertain. Mark refuted=false ONLY if every cited source verifies.' },
    badClaims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          issue: { type: 'string', description: 'Why the claim is wrong, unverifiable, or misleading' },
          fix: { type: 'string', description: 'Specific edit to make the claim correct' },
        },
        required: ['claim', 'issue', 'fix'],
      },
    },
    overallNotes: { type: 'string' },
  },
  required: ['refuted', 'badClaims'],
}

const FIGURE_SCHEMA = {
  type: 'object',
  properties: {
    label: { type: 'string', description: 'Figure 1, Figure 2, etc.' },
    caption: { type: 'string' },
    ascii: { type: 'string', description: 'The ASCII figure body, ready to drop inside a fenced code block' },
  },
  required: ['label', 'caption', 'ascii'],
}

phase('Research')
log('Six parallel readers mapping the timeline to verifiable facts')

const SECTIONS = [
  {
    key: 'pre-phase-1',
    label: 'pre-Phase-1 baseline',
    prompt: `You are writing Section II of a technical-paper-style meta-shift report titled "GAIA Trust Infrastructure: A Six-Week Retrospective (May–June 2026)". Your section is "Pre-Phase-1 Baseline (May 2026 — 2026-06-09)". Audience: GAIA contributors. Voice: half-merged technical (truthful labels per docs/trust/index.html, occasional ceremonial verbs per DESIGN.md "Hunter's Atlas"). Show-not-tell — concrete numbers over adjectives.

Read these sources:
- docs/meta/MAY_2026_AUDIT_REPORT.md
- docs/meta/2026-05-31-starless-skills-update.md
- docs/meta/2026-06-02-june-week-1-meta-update.md
- docs/meta/2026-06-03-chained-curation-thirteen-starless-references-and-a-unique-reclassification.html
- founder/handovers/done/PHASE1_FINAL_REPORT.md if present
- founder/MEMORY.md (search for May 2026 + early June)

Cover:
1. The 2026-05-25 Meta-Shift report — rarity axis deprecated, evidence numbers introduced.
2. Starless skills update 2026-05-31 — what generic-vs-named meant pre-G7.
3. Chained Curation 2026-06-03 — 13 starless refs + unique reclassification.
4. The deployed legacy trust model: 3 evidence types (arxiv/repo/github-stars), 4 letter grades from registry/meta.json legacy thresholds (S≥90 / A≥80 / B≥60 / C≥40 — per-row trust numbers, not skill aggregates), no apex gate, 'class A/B/C' field on rows. Two skills already at 6★ pre-Phase-1 (mattpocock/skills, ruvnet/ruflo).
5. Tooling: 'gaia dev evidence' was append-only, 'gaia validate', 'gaia promote', fusion-recipes & suite components. Auth was just landing (PR #669 device flow, merged 2026-06-14).

Hard rules:
- NO frontmatter / NO H1 — start with H2 "## II. Pre-Phase-1 baseline (May → 2026-06-09)"
- Quantify with numbers, not adjectives.
- Tables for distributions.
- 250-450 words.`,
  },
  {
    key: 'phase-1',
    label: 'Phase 1 G1-G7',
    prompt: `You are writing Section III "Phase 1: Trust Infrastructure (2026-06-10 → 2026-06-16)" of a technical-paper meta-shift report.

Source files:
- founder/handovers/done/PHASE1_MASTER.md
- founder/MEMORY.md § "Decisions Log" + State Snapshots from sessions 1-8
- founder/handovers/done/00_PHASE1_COMPLETION_PLAN.md
- founder/handovers/HYGIENE_BATCH_2026-06-16.md
- docs/meta/2026-06-1*.html files

Cover:
1. The 2026-06-10 trust-model decisions: ranks-only signal, evidence GRADES separate from TYPES, S/A/B/C with Platinum/Gold/Silver/Bronze.
2. The 2026-06-16 hygiene pass — milestone #4 reorganization to 1:1 with G1–G7. List H1–H9 outcomes briefly.
3. The G1–G7 implementation arc — what each PR shipped. Use 'gh pr view' or git log to verify the SHAs and PR numbers (G1 CI path filter, G2 #704, G3 #705 security scanner, G4 #709 verification 4-tier, G5 share static, G6 #642 narrow-tree, G7 trust magnitude RFC kicked off).
4. The 2026-06-15 trust methodology report (per-row 0–100, S≥90/A≥80/B≥60/C≥40, 4-tier verification badge).
5. The 2026-06-16 multi-stage workflow that produced G7 RFC: workflow wf_6e5a4374 (21 agents, 1.12M subagent tokens). Four proposals: P1 Strict-S, P2 Attainable-S, P3 Fusion-Heavy, P4 Community-Heavy. Synthesis: P4 base + P1+P3 grafts; thresholds reverted to S=250/A=100/B=50/C=20.
6. Honest framing: G7 was DESIGNED in Phase 1 but NOT propagated — Phase 1.5 is what carries it from RFC to production.

Hard rules:
- Section opens with "## III. Phase 1: Trust Infrastructure (2026-06-10 → 2026-06-16)"
- 350-550 words.
- One table mapping G# → PR → status.
- Cite each PR number; cite each MEMORY.md session-snapshot date for narrative claims.`,
  },
  {
    key: 'g7-rfc-v2',
    label: 'G7 Trust Magnitude RFC v2',
    prompt: `You are writing Section IV "The G7 Trust Magnitude RFC" — the technical heart of the meta-shift report.

Source files:
- founder/handovers/G7_TRUST_TAXONOMY_RFC.md (v2 ratified 2026-06-18) — read §0, §2.1, §2.14, §3, §4, §10, §11.12.
- founder/handovers/G7_HANDOVER_DELTA_2026-06-17.md
- founder/MEMORY.md § "State Snapshot 2026-06-18 session 9 day-2/day-3"
- src/gaia_cli/trustMagnitude.py — verify formula constants
- registry/meta.json — verify type weights/caps

Cover:
1. The two-scale ladder. Per-row Evidence Grade (0–100, S≥90/A≥80/B≥60/C≥40) vs skill Trust Magnitude (0–500+, S≥250/A≥100/B≥50/C≥20). Same letters, different thresholds.
2. The aggregation formula:
   artifact_score = magnitude × type_weight × freshness × mothership × creator × engagement × inheritMultiplier
   TM = sum(artifact_scores) — with social-signal capped at 80.
3. The 10-type taxonomy table: type | weight | cap | allowedLayers | inheritMultiplier. Verify against trustMagnitude.py + .agents/skills/gaia-tm-inspect/SKILL.md.
4. The v2 inheritance contract (ratified 2026-06-18): allowedLayers per type, per-type inheritMultiplier as last term. The 5 ratified multipliers: arxiv 0.70 / peer-review 0.30 / social-signal 0.35 / proxy-containment 0.25 / benchmark-result 0.15. Mention the adversarial workflow that ratified them (3×5 stances + 5 synthesizers, 696k tokens, all 5 nudged DOWN from drafts).
5. The 6-predicate apex gate: was 9, dropped crossOrgVerifierGte2 + systemWideCapRespected to feature-flag. depth-2 originally suite-excluded per RFC §11.12.3, then amended 2026-06-20 in I12 to INCLUDE suiteComponents (v3-incoming).
6. Anti-auto-mint clause §10.14 — phantom rows from suiteComponents/fusionRecipes count zero. Cite the mattpocock/skills audit motivating it.
7. v3-incoming adjustments: depth-2 semantics ratification (#749), apex_pr_signed enum value, sourceTenure under partial-signal.

Hard rules:
- "## IV. The G7 Trust Magnitude RFC"
- Formula in fenced code block.
- 10-type taxonomy as a table.
- 5 ratified multipliers as a small inline table.
- 500-700 words.
- Cite every formula constant with a source (file path or line).`,
  },
  {
    key: 'phase-1.5',
    label: 'Phase 1.5 I1-I12',
    prompt: `You are writing Section V "Phase 1.5: Implementation (2026-06-17 → 2026-06-20)" of a technical-paper meta-shift report.

Source files:
- founder/handovers/G7_IMPLEMENTATION_HANDOVER.md
- founder/handovers/phase-1.5/issues/ (per-issue specs)
- founder/MEMORY.md § sessions 9 day-2 through 15
- The PR list from 'gh pr list --state all'

Cover Phase 1.5 in chronological / dependency order:
1. Lane A — Schema + CLI: I1 #726 (schema) + I2 #728 (CLI computation). Merged 2026-06-18, v4.10.0 + v4.11.0 auto-released. 904+ lines trustMagnitude.py, 56/56 tests.
2. Lane B — Migration + CI: I3 #733 + I4 #732.
3. Lane C — Cutover + Display: I5 #735 + I6 #736 + I7 #734.
4. The Inspection Tool: scripts/inspectTrustMagnitude.py (--skill / --leaderboard / --html / --json) + /gaia-tm-inspect skill. Show command-line example.
5. I8 Trust Grade notch (#743, design/trust-grade-notch).
6. I9 Evidence Backfill (#744, review/meta/g7-evidence-backfill) — 25 new evidence rows, scorer alias repo→repo-own, 14 mattpocock v1.0.1 skills registered.
7. I10 Public Leaderboard (#747, design/trust-leaderboard) — /trust/leaderboard/ page, 249 skills, fetch-driven.
8. I11 Source Curation (#753, review/meta/i11-floor-curation) — 58 TM updates, 19/20 floor skills upgraded, peer-review on google-deepmind cluster, sourceStartedAt populated.
9. I12 Apex Gate Fixes (#748, cli/apex-gate-fixes) — depth2 includes suiteComponents, --source-started-at flag, 4 apex skills stamped apexPromotionPrSigned: true. garrytan/gstack apex 2/6 → 4/6.

Hard rules:
- "## V. Phase 1.5: Implementation"
- Phase 1.5 dependency table: issue → branch → PR → status.
- 500-700 words.
- Cite every PR number and SHA. Use 'gh pr view <n>' if needed.
- Honest framing: I3, I4, I5, I6, I7 still OPEN issues — Phase 1.5 NOT complete; only I1, I2, I8, I9, I10, I11, I12 have shipped.
- Mention RFC v3 follow-ups: #749 (depth-2 ratification), timeline-action enum gap.`,
  },
  {
    key: 'leaderboard-state',
    label: 'Current state — leaderboard + apex gate',
    prompt: `You are writing Section VI "Current State (2026-06-20)" of a technical-paper meta-shift report.

Concrete numbers. Source data:
- registry/named-skills.json (legacy threshold bug: index uses S≥90/A≥80, frontmatter is canonical S≥250/A≥100; see MEMORY.md decisions 2026-06-19)
- registry/named/<contributor>/<skill>.md frontmatter trustMagnitude + overallTrustGrade
- I11 agent's reported final distribution: S=4, A=42, B=56, C=76, ungraded=71 (249 named skills)
- I12 inspect output for garrytan/gstack: 4/6 active predicates pass

Cover:
1. Grade distribution table — before-Phase-1.5 baseline (S=4, A=20, B=31, C=93, ungraded=101 from MEMORY.md session 14) vs current (S=4, A=42, B=56, C=76, ungraded=71). Compute deltas. Σ(graded) moved from 148 to 178.
2. Top 15 leaderboard — show columns: rank, skillId, TM, grade. Honest note about generateNamedIndex.py threshold bug (legacy S≥90 vs canonical S≥250).
3. Apex gate status — for the 4 S-grade skills (gstack, ruflo, mattpocock/skills, superpowers), list which of the 6 active predicates pass. Use I12 inspect output. §11.12.5 (aGradedOriginsGte5) and §11.12.7 (sourceTenureDaysGte180AorS) still FAIL pending more data; §11.12.6 (cross-org verifier) and §11.12.9 (system-wide-cap) feature-flagged OFF.
4. Notable movements: 19/20 floor skills upgraded from TM=36 via I11 github-stars-own. The google-deepmind cluster of 22 skills jumped 10.82 → 100.82 (peer-review, A grade). Identify 3-4 standouts with before/after TM.
5. What's still unmoved: 71 ungraded skills (mostly TM=0 — newly-registered v1.0.1 mattpocock, intelligentcode-ai/, huggingface/, langgenius/) — slated for next curation pass.

Hard rules:
- "## VI. Current state (2026-06-20)"
- One large grade-distribution table (5 rows × 3 cols).
- One top-15 leaderboard table.
- One 4×6 apex-gate matrix.
- 400-600 words.
- Every claim has a number behind it.

Note: workflow passed leaderboard data via args.leaderboard_summary — refer to that.`,
  },
  {
    key: 'tooling',
    label: 'Tooling, agent skills, workflows',
    prompt: `You are writing Section VII "Tooling and Process" of a technical-paper meta-shift report.

Source files:
- .agents/skills/ directory — list each, read SKILL.md
- founder/CLAUDE.md § "Dispatching coding agents — cutoff safeguards", § GitHub hygiene, § Worktree warmup boilerplate
- founder/MEMORY.md § Session 9 day-3 cutoff lesson, § Session 15 worktree warmup
- The actual workflows that ran this month (cite token spend from MEMORY.md):
  - wf_6e5a4374 G7 RFC consensus (1.12M subagent, ~$5)
  - wf_f14f7317 6★ apex audit (595k, 7 agents)
  - wf_7cbe217f multiplier ratification (696k, 20 agents)
  - wf_ce280cfc ev-pipeline I9 curation (3.67M, ~$3.70)
  - I11 ev-pipeline (~200k in / 60k out, ~$3-4)

Cover:
1. The agent-skill registry. Brief table: /gaia-curate, /gaia-curate-chain, /gaia-curate-dynamic, /ev-pipeline, /gaia-tm-inspect, /impeccable, /gaia-fuse-full-suite, /meta-post. Two-line description each.
2. The multi-agent workflow pattern: proposer → adversarial-judge → synthesizer. Cite the four canonical workflows above.
3. The cutoff-safeguard playbook (founder/CLAUDE.md) — 7-rule worktree pattern. Why it matters: the 2026-06-18 Opus dispatch died at 105k tokens with 151 lines uncommitted; recovered only via worktree isolation.
4. The GitHub-hygiene checklist added 2026-06-20 — every issue + PR gets milestone + functional label + Resolves body. Existing functional labels: backend, frontend, infrastructure, CLI, docs, schema, RFC, tech-debt.
5. CLI surface added this month: 'gaia trust explain <skill>' (I2), 'gaia dev evidence --stars/--views/--citations/--reviewers/--commits/--contributors/--skill-count-in-repo/--source-started-at' (I9 + I12).

Hard rules:
- "## VII. Tooling and process"
- 400-550 words.
- One table of agent skills.
- Cite every workflow ID + token figure with the MEMORY.md entry.
- Honest about open CLI gaps: timeline write-to-named, action enum, Windows cp1252 ★ glyph corruption.`,
  },
]

const sectionResults = await pipeline(
  SECTIONS,
  (s, sec, i) => agent(sec.prompt, { label: 'write:' + sec.key, phase: 'Research', schema: SECTION_SCHEMA }).then(r => r ? { ...sec, write: r } : null),
  (prev, sec, i) => {
    if (!prev || !prev.write) return null
    return agent('You are adversarially fact-checking section "' + prev.write.title + '" of a GAIA meta-shift report. The author claims:\n\n---SECTION BODY---\n' + prev.write.body + '\n---END---\n\nThe author cites these sources:\n' + prev.write.citations.map((c, j) => (j+1) + '. CLAIM: ' + c.claim + '\n   SOURCE: ' + c.source).join('\n') + '\n\nYour job: verify EACH claim. Use Read, Grep, Bash (gh issue view <n>, git log, git show) to confirm.\n\nDEFAULT TO refuted=true. Only refuted=false if every numeric claim, every PR number, every SHA, and every formula constant verifies. List EVERY claim that is wrong, unverifiable, or ambiguous, with a fix.\n\nBe strict about: PR numbers, token spend (founder/MEMORY.md), formula constants (src/gaia_cli/trustMagnitude.py), TM grade thresholds (registry/meta.json), apex gate predicate count (6 active, 2 OFF — verify against trustMagnitude.py and RFC §11.12), issue numbers.', { label: 'verify:' + sec.key, phase: 'FactCheck', schema: VERDICT_SCHEMA }).then(v => ({ ...prev, verdict: v }))
  },
  async (prev, sec, i) => {
    if (!prev || !prev.write || !prev.verdict) return prev
    if (!prev.verdict.refuted) return prev
    if (!prev.verdict.badClaims || prev.verdict.badClaims.length === 0) return prev
    const fixed = await agent('The fact-checker found these issues with your section "' + prev.write.title + '":\n\n' + prev.verdict.badClaims.map((b, j) => (j+1) + '. CLAIM: ' + b.claim + '\n   ISSUE: ' + b.issue + '\n   FIX: ' + b.fix).join('\n') + '\n\nNotes: ' + (prev.verdict.overallNotes || '(none)') + '\n\nApply ALL fixes. Do NOT change unrelated content. Keep the same structure, headings, tables, figures.\n\nOriginal body:\n---\n' + prev.write.body + '\n---\n\nReturn the corrected section in the same schema.', { label: 'rewrite:' + sec.key, phase: 'FactCheck', schema: SECTION_SCHEMA })
    return fixed ? { ...prev, write: fixed, rewritten: true } : prev
  }
)

const validSections = sectionResults.filter(Boolean).filter(r => r && r.write)
log('Sections written + verified: ' + validSections.length + '/' + SECTIONS.length)

phase('Figures')

const FIGURES = [
  { key: 'aggregation-flow', prompt: 'Build an ASCII figure for "Aggregation flow: per-row evidence → skill Trust Magnitude". Show 3-4 evidence rows feeding into a TM compute step → Overall Trust Grade. Borrow style from docs/meta/2026-06-17-g7-trust-magnitude-supersession.md "From a row to a skill — the aggregation flow" but adapt for v2 multipliers (include inheritMultiplier in chain). Fits 78-char-wide page in fenced code block. Caption: "Figure 1 — Aggregation flow with v2 inheritance".' },
  { key: 'apex-gate-matrix', prompt: 'Build an ASCII figure showing the 6-predicate apex gate matrix for the 4 S-grade skills (garrytan/gstack, ruvnet/ruflo, mattpocock/skills, obra/superpowers). Use I12 inspect output: gstack now passes 4/6 (PASS: 11.12.2, 11.12.3, 11.12.4, 11.12.8 / FAIL: 11.12.5, 11.12.7). Same shape for the other 3 (assume same 4/6 unless verified — be honest). Tight 6×4 matrix with PASS/FAIL cells. 78 chars wide. Caption: "Figure 2 — Apex gate status post-I12".' },
  { key: 'grade-distribution', prompt: 'Build an ASCII bar chart showing grade distribution before-Phase-1.5 (S=4, A=20, B=31, C=93, ungraded=101) and after-I11 (S=4, A=42, B=56, C=76, ungraded=71). Horizontal bars, one row per grade with two bars (before / after). Each bar labeled with count. Total = 249 named skills. 78 chars wide. Caption: "Figure 3 — Grade distribution: pre-Phase-1.5 → post-I11".' },
]

const figures = await parallel(FIGURES.map(f => () => agent(f.prompt, { label: 'figure:' + f.key, phase: 'Figures', schema: FIGURE_SCHEMA })))
const validFigures = figures.filter(Boolean)
log('Figures built: ' + validFigures.length + '/' + FIGURES.length)

phase('Synthesize')

const sectionMarkdown = validSections.map(s => s.write.body).join('\n\n')
const figureMarkdown = validFigures.map(f => '### ' + f.label + '\n\n*' + f.caption + '*\n\n```\n' + f.ascii + '\n```').join('\n\n')

const synthOut = await agent('You are composing the final June 2026 GAIA meta-shift report. You have 6 fact-checked sections + 3 figures. You write 4 bridge pieces (Hero/show-not-tell, Section I "Headlines", Section VIII "Whats next", Section IX "Appendix A — schema additions", Section X "Appendix B — token-spend ledger", Section XI "References").\n\nThe ratified sections (in order, joined verbatim — DO NOT alter their content):\n\n' + sectionMarkdown + '\n\nThe figures:\n\n' + figureMarkdown + '\n\nCompose the report:\n\n1. **Frontmatter** (YAML, between --- markers):\n   - title: "GAIA Trust Infrastructure: A June 2026 Retrospective"\n   - author: "Marcus Rafael Tiongson, Maintainer"\n   - summary: One sentence on what changed in June 2026.\n   - abstract: |  3-5 sentence abstract describing the trajectory pre-Phase-1 → Phase 1 → G7 RFC ratification → Phase 1.5 implementation → current state.\n   - label: "Trust Model"\n\n2. **## Abstract** (after frontmatter — academic-paper style)\n\n3. **## I. Headlines (show, dont tell)** — write a NEW section. ~200-300 words. Bullet list of 6-8 headlines, each a concrete number + before/after. Examples:\n   - "Grade distribution: 148 graded → 178 graded (+30 named skills crossed the C floor)"\n   - "S-grade ladder: 4 skills, none yet apex-eligible (4/6 predicates max so far)"\n   - "Phase 1.5 milestone: 13 of 18 issues closed/PRd; v4.10.0 + v4.11.0 auto-released"\n   - "Adversarial workflow ratified the v2 inheritance multipliers (5 stances × 5 multipliers + 5 synth, 696k subagent tokens)"\n   - "I12 amended apex depth-2 to include suiteComponents — 4 S-grade skills moved 2/6 → 4/6"\n   - "Agent-skills registry now includes /gaia-tm-inspect, /ev-pipeline, /meta-post, /impeccable"\n   Place **Figure 3** at end of this section.\n\n4. Insert **Section II (pre-Phase-1)** verbatim.\n\n5. Insert **Section III (Phase 1)** verbatim. Place **Figure 1** at end of section III as transition into Section IV.\n\n6. Insert **Section IV (G7 RFC)** verbatim.\n\n7. Insert **Section V (Phase 1.5)** verbatim.\n\n8. Insert **Section VI (current state)** verbatim. Place **Figure 2** mid-section before the apex-gate prose.\n\n9. Insert **Section VII (tooling)** verbatim.\n\n10. **## VIII. Whats next: G7 v3 incoming** — ~150-250 words. Cover: issue #749 RFC v3 ratification (depth-2 semantics, apex_pr_signed enum, sourceTenure under partial-signal); remaining Phase 1.5 issues (I3 #721, I4 #722, I5 #723, I6 #724, I7 #725); 71 ungraded skills slated for next curation pass; honest framing: this report is mid-flight retrospective, not final.\n\n11. **## IX. Appendix A — Schema additions (Phase 1.5)** — ~100-150 words. List frontmatter fields added: trustMagnitude, overallTrustGrade, apexGateStatus (sub-keys: apexPromotionPrSigned, apexPromotionPrSignedBy, apexPromotionPrSignedAt), provisional, provisionalUntil, evidence[].grade, evidence[].sourceStartedAt, links.canonicalRepo, cosigners. Plus: meta.json gained trustMagnitudeThresholds + 10-type taxonomy + apexGate block.\n\n12. **## X. Appendix B — Token-spend ledger** — table summing this months spend per MEMORY.md per-session entries. Approximate cumulative G7 spend ~$35-40 across 15 sessions. One row per major workflow (G7 RFC consensus ~$5, apex audit ~$2, multiplier ratification ~$2.30, ev-pipeline I9 ~$8, ev-pipeline I11 ~$4, etc.). Final row: cumulative.\n\n13. **## XI. References** — formal academic-paper style:\n    [1] G7 Trust Taxonomy RFC, v2. founder/handovers/G7_TRUST_TAXONOMY_RFC.md\n    [2] G7 Implementation Handover. founder/handovers/G7_IMPLEMENTATION_HANDOVER.md\n    [3] G7 Handover Delta 2026-06-17. founder/handovers/G7_HANDOVER_DELTA_2026-06-17.md\n    [4] Phase 1 Master Plan. founder/handovers/done/PHASE1_MASTER.md\n    [5] Trust Methodology, 2026-06-15. docs/meta/2026-06-15-the-gaia-trust-methodology-evidence-types-grades-and-inherited-standing.html\n    [6] G7 Supersession Visual Walkthrough, 2026-06-17. docs/meta/2026-06-17-g7-trust-magnitude-supersedes-the-2026-06-15-methodology.html\n    [7] Issue tracker: #719, #720, #721–#725, #729, #730, #739–#742, #746–#753.\n\nHard rules:\n- Output the ENTIRE final markdown file as your response (5000-9000 words).\n- Frontmatter at top, then ## Abstract, then sections in order I-XI.\n- Verbatim sections: do NOT modify body of sections II-VII (only insert figures around them).\n- No marketing copy. No hype. Quantify everything.\n- Honest about whats not done.\n- One blank line between every section header and the next paragraph.', { label: 'synthesize', phase: 'Synthesize', effort: 'high' })

phase('Render')

if (!synthOut) {
  log('Synthesis failed — returning sections + figures so orchestrator can hand-render')
  return { sections: validSections, figures: validFigures, error: 'synth-died' }
}

return {
  fullMarkdown: synthOut,
  sectionCount: validSections.length,
  figureCount: validFigures.length,
  rewriteCount: validSections.filter(s => s.rewritten).length,
}
