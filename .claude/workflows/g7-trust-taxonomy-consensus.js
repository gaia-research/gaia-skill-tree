
export const meta = {
  name: 'g7-trust-taxonomy-consensus',
  description: 'Multi-stage consensus on GAIA Trust Magnitude formula: 3 surveyors → 4 proposers (distinct stances) → 12 adversarial judges (3 lenses × 4 proposals) → synthesis → final RFC at founder/handovers/G7_TRUST_TAXONOMY_RFC.md',
  phases: [
    { title: 'Survey', detail: '3 parallel surveyors map calibration corpus + edge cases' },
    { title: 'Propose', detail: '4 parallel Opus xhigh proposers, distinct tunings' },
    { title: 'Judge', detail: '12 adversarial judges: 3 lenses × 4 proposals' },
    { title: 'Synthesize', detail: 'Winner + graft best ideas, produce final calibration' },
    { title: 'Draft RFC', detail: 'Write G7_TRUST_TAXONOMY_RFC.md to disk' },
  ],
}

const REPO_ROOT = 'C:/Users/C5396183/gaia-skill-tree'

const TAXONOMY_CONTEXT = `
# GAIA Trust Magnitude — Marco-approved baseline (subject to your tuning)

## Naming (FINAL)
- Per-skill aggregate: **Trust Magnitude** (replaces "trustNumber"/"trustScore")
- Per-evidence: **artifact score**
- Mental model: evidence as "artifacts/equipment" stacking onto a skill's base power. Unbounded. Soft-capped ~500 for display.

## Aggregation
- Trust Magnitude(skill) = Σ artifactScore(e) for all e in evidence
- Per-evidence: artifactScore = magnitude(type, raw) × weight(type) × freshness(type)
- Per-evidence "evidence-tier" (post-weight): S ≥ 90, A 50-89, B 20-49, C 5-19, ungraded < 5

## Per-evidence types (10 total) — baseline formulas

| Type | Magnitude | Weight | Freshness | Cap | S-capable? |
|---|---|---|---|---|---|
| fusion-recipe | 20 × origins | 1.5 | 1.0 (intrinsic) | — | YES @ 5+ origins (mandatory for Ultimate) |
| github-stars-own | stars/1000 (cap 200) | 1.0 | refresh quarterly | 200 | YES @ 100k+ |
| proxy-containment | (external_stars/1000) × 0.8 (cap 160) | 1.0 | quarterly | 160 | YES @ 125k+ external |
| verifier-attestation | 30 × verifiers (4★+) | 1.5 | flag-only-on-derank, no decay | — | YES @ 3+ verifiers |
| benchmark-result | percentile (cap 100) | 1.4 | 50%/year | 100 | YES @ 95th+ |
| arxiv | citations/5 (cap 100) | 1.0 | quarterly | 100 | reaches A-cap |
| peer-review | 25 × reviewers (4★+) | 1.2 | 25%/2yr | — | reaches A-cap |
| repo-own | commits/200 + contributors² × 2 (cap 60) | 0.6 | quarterly | 60 | reaches B-cap |
| self-attestation | flat 10 | 0.5 | static | 10 | C-cap |
| social-signal | log10(views) × 8 × creator_mult × engagement_ratio | 1.0 | 50%/year | 80 (HARD A-CAP) | NO — A-cap by design |

### social-signal sub-rules (Marco-approved defaults)
- creator_multiplier: 0× same-as-author / 0.3× anon / 0.6× established / 1.0× topical authority / 1.4× recognized voice (ceiling)
- engagement_ratio = min(1.5, (likes + comments × 5) / views × 50)
- Plateau on multiple entries: 1.0× / 0.5× / 0.25×, max 3 entries
- Same-creator dedup: 2nd content from same creator at 0.5×, 3rd at 0.25×
- 30-day publish cooldown before counting
- Cross-platform same-content = ONE entry (primary platform)
- Self-promotion (same human as skill author) → 0× → rejected

### proxy-containment sub-rules (Marco-approved)
- Max 3 entries
- Plateau: 1.0× / 0.5× / 0.25×
- External repo must be ≥10k stars to count at all

## Overall-grade thresholds (BASELINE — proposers tune)

| Grade | Min Trust Magnitude | Min distinct types | Plus rule |
|---|---|---|---|
| S | ≥ 250 | ≥ 3 | ≥1 S-tier evidence OR ≥3 A-tier of distinct types |
| A | ≥ 100 | ≥ 1 | ≥1 A-tier evidence (Marco: pure-stars-only at A is OK if magnitude ≥100) |
| B | ≥ 50 | ≥ 1 | ≥1 B-tier or higher |
| C | ≥ 20 | — | — |
| ungraded | < 20 | — | — |

## Marco's explicit calls (HARD CONSTRAINTS — do not override)
1. Pure github-stars CAN reach A (4-6★ unique with stars-only is valid)
2. Ultimate **hard-requires** fusion-recipe evidence (no fusion → cannot be Ultimate regardless of Trust Magnitude)
3. Proxy-containment: max 3 entries, plateau 1.0×/0.5×/0.25×, external ≥10k stars threshold
4. Verifier attestation: flag on derank, NO decay
5. Naming: "Trust Magnitude" (skill aggregate), "artifact score" (per-evidence) — final
6. No tenures for migration. Major PR re-grades all evidence under new formula. Old entries preserved. Stamp report for June 2026.
7. social-signal hard A-cap (80 max magnitude)
8. fusion-recipe is mandatory inherent evidence — every fused/Ultimate skill auto-gets one

## Calibration corpus — what to test against
- registry/named/ — read named-skills.json index, then sample contributors' .md files
- registry/gaia.json — canonical graph with current ranks
- Focus 4★+ named skills (Apex/Ultimate tier) — these are the calibration anchors
- Drift up to ±1 grade tier acceptable (new system more robust than old class system); ±2 tier drift requires explicit justification

## Hard rule for proposers
Show your work. Every threshold change must come with: (a) corpus impact, (b) which skill(s) drift and why, (c) what gameability vector it closes/opens.
`.trim()

const SURVEY_SCHEMA = {
  type: 'object',
  required: ['summary', 'keyFindings', 'corpusSamples'],
  properties: {
    summary: { type: 'string' },
    keyFindings: { type: 'array', items: { type: 'string' }, minItems: 3 },
    corpusSamples: {
      type: 'array',
      minItems: 8,
      items: {
        type: 'object',
        required: ['skillId', 'currentRank', 'evidenceTypes', 'notes'],
        properties: {
          skillId: { type: 'string' },
          contributor: { type: 'string' },
          currentRank: { type: 'string' },
          evidenceTypes: { type: 'array', items: { type: 'string' } },
          evidenceCount: { type: 'number' },
          baselineTrustMagnitude: { type: 'number' },
          baselineGrade: { type: 'string' },
          notes: { type: 'string' },
        },
      },
    },
    driftPredictions: { type: 'array', items: { type: 'string' } },
    edgeCases: { type: 'array', items: { type: 'string' } },
    gameabilityVectors: { type: 'array', items: { type: 'string' } },
  },
}

const PROPOSAL_SCHEMA = {
  type: 'object',
  required: ['stanceName', 'stanceDescription', 'thresholds', 'calibrationTable', 'tradeoffs'],
  properties: {
    stanceName: { type: 'string' },
    stanceDescription: { type: 'string' },
    formulaTuning: {
      type: 'object',
      properties: {
        typeWeights: { type: 'object' },
        magnitudeAdjustments: { type: 'array', items: { type: 'string' } },
        socialSignalTuning: { type: 'object' },
        diversityRules: { type: 'object' },
      },
    },
    thresholds: {
      type: 'object',
      required: ['S', 'A', 'B', 'C'],
      properties: {
        S: { type: 'number' },
        A: { type: 'number' },
        B: { type: 'number' },
        C: { type: 'number' },
      },
    },
    calibrationTable: {
      type: 'array',
      minItems: 10,
      items: {
        type: 'object',
        required: ['skillId', 'currentRank', 'proposedTrustMagnitude', 'proposedOverallGrade', 'driftDirection'],
        properties: {
          skillId: { type: 'string' },
          currentRank: { type: 'string' },
          proposedTrustMagnitude: { type: 'number' },
          proposedOverallGrade: { type: 'string' },
          driftDirection: { type: 'string', enum: ['up', 'down', 'same'] },
          rationale: { type: 'string' },
        },
      },
    },
    tradeoffs: { type: 'array', items: { type: 'string' }, minItems: 3 },
    gameabilityClosed: { type: 'array', items: { type: 'string' } },
    gameabilityOpened: { type: 'array', items: { type: 'string' } },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['proposalId', 'lens', 'score', 'refuted', 'reasoning'],
  properties: {
    proposalId: { type: 'string' },
    lens: { type: 'string' },
    score: { type: 'number', minimum: 0, maximum: 10 },
    refuted: { type: 'boolean' },
    reasoning: { type: 'string' },
    strengths: { type: 'array', items: { type: 'string' } },
    weaknesses: { type: 'array', items: { type: 'string' } },
    recommendedFixes: { type: 'array', items: { type: 'string' } },
  },
}

const SYNTHESIS_SCHEMA = {
  type: 'object',
  required: ['winnerStance', 'winnerJustification', 'finalThresholds', 'finalCalibration'],
  properties: {
    winnerStance: { type: 'string' },
    winnerJustification: { type: 'string' },
    runnersUp: { type: 'array', items: { type: 'string' } },
    graftedIdeas: { type: 'array', items: { type: 'string' } },
    finalFormulaSummary: { type: 'string' },
    finalThresholds: {
      type: 'object',
      required: ['S', 'A', 'B', 'C'],
      properties: {
        S: { type: 'number' },
        A: { type: 'number' },
        B: { type: 'number' },
        C: { type: 'number' },
      },
    },
    finalTypeWeights: { type: 'object' },
    finalDiversityRules: { type: 'object' },
    finalSocialRules: { type: 'object' },
    finalCalibration: {
      type: 'array',
      minItems: 10,
      items: {
        type: 'object',
        properties: {
          skillId: { type: 'string' },
          currentRank: { type: 'string' },
          finalTrustMagnitude: { type: 'number' },
          finalOverallGrade: { type: 'string' },
          driftDirection: { type: 'string' },
          rationale: { type: 'string' },
        },
      },
    },
    knownDrifts: { type: 'array', items: { type: 'string' } },
    openQuestions: { type: 'array', items: { type: 'string' } },
    migrationNotes: { type: 'array', items: { type: 'string' } },
  },
}

phase('Survey')
log('Phase 1: 3 parallel surveyors mapping calibration corpus...')

const surveyors = await parallel([
  () => agent(
    `${TAXONOMY_CONTEXT}

# YOUR ROLE: SURVEYOR-A (CORPUS ANCHORS)

Read the GAIA registry at ${REPO_ROOT}. Specifically:
1. Read registry/named-skills.json (the index)
2. Sample 12-15 named skills at 4★+ ranks across multiple contributors (mattpocock, anthropic, garrytan, etc.)
3. For each, read the .md file and inspect any evidence array
4. Score each under the BASELINE formula above. Report:
   - skillId, contributor, currentRank
   - what evidence types exist today
   - rough baseline Trust Magnitude (sum of artifact scores under baseline formula)
   - what overall grade that would translate to under baseline thresholds (S=250/A=100/B=50/C=20)
   - whether the drift is up/down/same vs. current rank
5. Identify the top 5 drift PREDICTIONS — which skills would drift hardest under the new system, and why?
6. Spotlight 3-5 EDGE CASES — skills where the formula seems to break down or produce a counterintuitive result.

Return raw analysis grounded in actual file reads. Cite skillId paths.`,
    { label: 'survey:corpus-anchors', phase: 'Survey', schema: SURVEY_SCHEMA, effort: 'high' }
  ),
  () => agent(
    `${TAXONOMY_CONTEXT}

# YOUR ROLE: SURVEYOR-B (EVIDENCE-TYPE DISTRIBUTION)

Read ${REPO_ROOT}/registry/. Audit:
1. Across all named skills (registry/named/) and generic nodes (registry/nodes/), what is the actual distribution of evidence TYPES today? E.g., how many entries are arxiv vs. github-stars vs. repo, etc.
2. Which evidence types are RARE or ABSENT? (e.g., are there any verifier-attestation entries today? any benchmark-result entries?)
3. Of skills currently at 4★+ rank, what fraction have ZERO of each S-capable evidence type? This tells us how aggressive the migration drift will be.
4. Identify skills where the current rank seems UNDERSUPPORTED by current evidence (rank earned legacy, no real evidence trail).
5. Identify skills where current rank seems OVERSUPPORTED (rich evidence, but capped at low rank because old class system didn't credit fusion-recipe or proxy).

Return findings as 12+ corpus samples with evidence-type breakdowns. Cite paths.`,
    { label: 'survey:evidence-distribution', phase: 'Survey', schema: SURVEY_SCHEMA, effort: 'high' }
  ),
  () => agent(
    `${TAXONOMY_CONTEXT}

# YOUR ROLE: SURVEYOR-C (GAMEABILITY & EDGE CASE HUNTER)

Read ${REPO_ROOT}/registry/. Then, by inspecting both the formula and the actual corpus, identify:
1. Top 5 GAMEABILITY VECTORS — concrete attack scenarios where someone could spoof their way to a higher grade than deserved under the baseline formula. For each: (a) attack steps, (b) which evidence types are exploited, (c) max grade reachable by the attack, (d) what countermeasure is needed.
2. Top 5 EDGE CASES — real or plausible skills where the formula produces a result that violates intuition. Examples:
   - "skill with 5-origin fusion but zero stars and zero arxiv" — should this really be S?
   - "skill with 200k stars but 0-origin (not fused)" — Marco said S-capable via stars, but Ultimate-incapable; what's the actual rank?
   - "skill with 3 verifiers but no other signal" — does 135 magnitude alone hit A or S?
3. Audit the diversity rule. Find a corpus sample where a skill has 5 evidence entries of the same type — does the diversity gate correctly stop it from reaching S?

Return at least 12 corpus samples + named gameability vectors. Pick samples that stress-test the formula.`,
    { label: 'survey:gameability', phase: 'Survey', schema: SURVEY_SCHEMA, effort: 'high' }
  ),
])

const surveysOk = surveyors.filter(Boolean)
log(`Survey complete: ${surveysOk.length}/3 reports`)

const surveyContext = surveysOk.map((s, i) => `## SURVEYOR ${'ABC'[i]} REPORT
${s.summary}

KEY FINDINGS:
${(s.keyFindings || []).map(k => `- ${k}`).join('\n')}

CORPUS SAMPLES (${(s.corpusSamples || []).length}):
${(s.corpusSamples || []).slice(0, 10).map(c => `  - ${c.skillId} (${c.currentRank || '?'}, types: ${(c.evidenceTypes || []).join(',')}) — ${c.notes || ''}`).join('\n')}

DRIFT PREDICTIONS:
${(s.driftPredictions || []).map(d => `- ${d}`).join('\n')}

EDGE CASES:
${(s.edgeCases || []).map(e => `- ${e}`).join('\n')}

GAMEABILITY VECTORS:
${(s.gameabilityVectors || []).map(g => `- ${g}`).join('\n')}
`).join('\n---\n')

phase('Propose')
log('Phase 2: 4 parallel proposers, distinct tunings...')

const STANCES = [
  { id: 'P1-strict-S', name: 'Strict-S Defender', brief: `STANCE: S-tier should be HARD to reach. Raise S threshold higher than baseline 250 (try 300-350). Require ≥4 distinct types for S (not 3). Lower individual evidence caps slightly. Goal: make S a true beyond-reasonable-doubt grade. Acceptable if 70-80% of current 5★+ skills drift DOWN one tier — that's the system getting honest.` },
  { id: 'P2-attainable-S', name: 'Attainable-S Pragmatist', brief: `STANCE: S-tier should be reachable for genuinely strong skills today. Lower S threshold to 200-225. Keep ≥3 distinct types. Slightly increase fusion-recipe weight (1.5 → 1.8) to reward structural evidence more. Goal: when the migration runs, ~30-50% of current 5★+ skills earn S immediately, demonstrating the system works without forcing everyone into a re-evidencing scramble.` },
  { id: 'P3-fusion-heavy', name: 'Fusion-Heavy Structuralist', brief: `STANCE: Fusion-recipe is the most honest evidence we have because it's intrinsic to the skill graph and unspoofable. Raise fusion-recipe weight to 2.0. Add a multi-tier fusion bonus: 5+ origins → 25 each (not 20), 7+ origins → 30 each. Allow Ultimate-only skills with massive fusion (7+ origins) to reach S even with diversity ≥ 2 (not 3). Other types stay baseline. Goal: reward structural maturity above community signal.` },
  { id: 'P4-community-heavy', name: 'Community-Heavy Pragmatist', brief: `STANCE: GitHub stars + proxy-containment + social-signal are how the dev world ACTUALLY measures importance today. Increase github-stars-own cap to 250 (1k → 250k uses full range). Loosen proxy-containment plateau to 1.0/0.7/0.4. Allow social-signal to reach mid-A (70 instead of hard 80 cap) but keep S-incapability. Lower S threshold modestly (220) to make star-rich skills reachable. Goal: reflect how real reputation works in 2026 dev communities.` },
]

const proposals = await parallel(
  STANCES.map(stance => () => agent(
    `${TAXONOMY_CONTEXT}

# SURVEY FINDINGS (CORPUS CONTEXT)
${surveyContext}

# YOUR ROLE: PROPOSER ${stance.id} — ${stance.name}

${stance.brief}

# YOUR DELIVERABLE
1. Tune the formula per your stance. Explicitly state every weight, threshold, magnitude, and rule you change vs. baseline. EVERY change requires justification.
2. Apply your tuned formula to AT LEAST 12 corpus samples (use the surveyors' samples — pick the most informative). For each, compute proposedTrustMagnitude, proposedOverallGrade, and driftDirection vs. current rank.
3. Honor Marco's HARD CONSTRAINTS (listed in the context — pure-stars hits A allowed, Ultimate hard-requires fusion, social hard-A-cap at 80, naming "Trust Magnitude", proxy max 3 plateau, verifier flag-no-decay).
4. Be explicit about tradeoffs your stance creates. List ≥3 honest tradeoffs.
5. List gameability vectors your stance CLOSES and any new ones it OPENS.

Return strict structured output per the schema. Be quantitative. Show your work.`,
    { label: `propose:${stance.id}`, phase: 'Propose', schema: PROPOSAL_SCHEMA, effort: 'xhigh' }
  ))
)

const proposalsOk = proposals.filter(Boolean)
log(`Proposal phase complete: ${proposalsOk.length}/4 proposals`)

if (proposalsOk.length < 2) {
  log(`ERROR: Only ${proposalsOk.length} proposals survived. Cannot run consensus with < 2.`)
  return { error: 'insufficient-proposals', proposals: proposalsOk }
}

phase('Judge')
log(`Phase 3: ${proposalsOk.length * 3} adversarial judges (3 lenses × ${proposalsOk.length} proposals)...`)

const LENSES = [
  { id: 'gameability', brief: `LENS: GAMEABILITY. Try to BREAK this proposal. How would a malicious skill author exploit it to reach S unfairly? List concrete attack steps. Default to refuted=true if you find any S-reachable attack with cost < $5k or < 2 weeks of effort. Strengths only count if proposal CLOSES known attack vectors that baseline left open.` },
  { id: 'corpus-fit', brief: `LENS: CORPUS FIT. Look at the calibration table. Do the proposed grades MATCH human intuition for those skills? Skills that everyone agrees are S-tier should land at S. Skills nobody respects should land at C. If the table has 4★+ skills landing below B, or 1-2★ skills landing above B, refute. Honest drift is OK; nonsense drift is refuted.` },
  { id: 'drift-severity', brief: `LENS: DRIFT SEVERITY. How chaotic would the migration be? If >40% of current 4★+ skills drift down by ≥2 tiers, that's a community-trust catastrophe. If <10% of skills drift at all, the formula isn't doing real work. Sweet spot is 20-35% of skills drifting by 1 tier with clear rationale. Refute if drift is too chaotic OR too anodyne.` },
]

const judgeTasks = []
for (const proposal of proposalsOk) {
  for (const lens of LENSES) {
    judgeTasks.push({ proposal, lens })
  }
}

const verdicts = await parallel(
  judgeTasks.map(({ proposal, lens }) => () => agent(
    `${TAXONOMY_CONTEXT}

# THE PROPOSAL UNDER REVIEW
PROPOSAL ID: ${proposal.stanceName}
${proposal.stanceDescription || ''}

THRESHOLDS: S=${proposal.thresholds.S} A=${proposal.thresholds.A} B=${proposal.thresholds.B} C=${proposal.thresholds.C}

FORMULA TUNING:
${JSON.stringify(proposal.formulaTuning || {}, null, 2)}

CALIBRATION TABLE (sample):
${(proposal.calibrationTable || []).slice(0, 12).map(c => `  - ${c.skillId} (${c.currentRank}) → magnitude ${c.proposedTrustMagnitude}, grade ${c.proposedOverallGrade}, drift ${c.driftDirection}`).join('\n')}

TRADEOFFS (per proposer):
${(proposal.tradeoffs || []).map(t => `- ${t}`).join('\n')}

# YOUR ROLE: JUDGE-${lens.id.toUpperCase()}

${lens.brief}

# OUTPUT
- score (0-10) — 0 means proposal is broken under this lens; 10 means proposal is excellent
- refuted (true/false) — refute by default if uncertain
- reasoning — concrete, specific
- strengths / weaknesses / recommendedFixes — actionable

Be skeptical. Refute by default. Praise must come with citation.`,
    { label: `judge:${proposal.stanceName}:${lens.id}`, phase: 'Judge', schema: VERDICT_SCHEMA, effort: 'high' }
  ))
)

const verdictsOk = verdicts.filter(Boolean)
log(`Judge phase complete: ${verdictsOk.length}/${judgeTasks.length} verdicts`)

const verdictsByProposal = {}
for (const v of verdictsOk) {
  if (!verdictsByProposal[v.proposalId]) verdictsByProposal[v.proposalId] = []
  verdictsByProposal[v.proposalId].push(v)
}

const proposalScores = proposalsOk.map(p => {
  const vs = verdictsByProposal[p.stanceName] || []
  const avgScore = vs.length ? vs.reduce((a, b) => a + b.score, 0) / vs.length : 0
  const refuteCount = vs.filter(v => v.refuted).length
  return { proposal: p, avgScore, refuteCount, verdicts: vs }
}).sort((a, b) => b.avgScore - a.avgScore || a.refuteCount - b.refuteCount)

log('Score tally:')
for (const ps of proposalScores) {
  log(`  ${ps.proposal.stanceName}: avg ${ps.avgScore.toFixed(2)}, refuted ${ps.refuteCount}/${ps.verdicts.length}`)
}

phase('Synthesize')
log('Phase 4: synthesizing winner with grafts from runners-up...')

const synthesisInput = `
# PROPOSALS SCORED (HIGH→LOW)
${proposalScores.map(ps => `
## ${ps.proposal.stanceName} — avg ${ps.avgScore.toFixed(2)}, refuted ${ps.refuteCount}/${ps.verdicts.length}

DESCRIPTION: ${ps.proposal.stanceDescription}
THRESHOLDS: S=${ps.proposal.thresholds.S} A=${ps.proposal.thresholds.A} B=${ps.proposal.thresholds.B} C=${ps.proposal.thresholds.C}

FORMULA TUNING:
${JSON.stringify(ps.proposal.formulaTuning || {}, null, 2)}

JUDGE VERDICTS:
${ps.verdicts.map(v => `  [${v.lens}] score ${v.score}, refuted ${v.refuted} — ${v.reasoning}
    strengths: ${(v.strengths || []).join('; ')}
    weaknesses: ${(v.weaknesses || []).join('; ')}
    fixes: ${(v.recommendedFixes || []).join('; ')}`).join('\n')}

CALIBRATION:
${(ps.proposal.calibrationTable || []).slice(0, 12).map(c => `  - ${c.skillId} (${c.currentRank}) → ${c.proposedTrustMagnitude} ${c.proposedOverallGrade} (${c.driftDirection})`).join('\n')}
`).join('\n---\n')}
`.trim()

const synthesis = await agent(
  `${TAXONOMY_CONTEXT}

# CONSENSUS INPUT
${synthesisInput}

# YOUR ROLE: SYNTHESIZER

You see all 4 proposals + 12 judge verdicts. Your job:
1. Pick the WINNER (highest avg score with lowest refute count is the default; you may override if a runner-up's grafted ideas resolve the winner's weaknesses).
2. Identify which IDEAS from runners-up are worth grafting onto the winner.
3. Produce the FINAL formula — single coherent system, no hedging. State every threshold, weight, magnitude, and rule.
4. Produce the FINAL calibration table — apply final formula to the same 12+ samples used in proposals; if any sample's grade changed under the synthesis, flag it.
5. Document KNOWN DRIFTS (skills that change rank under migration, with rationale).
6. List OPEN QUESTIONS the RFC must flag for future review.
7. Provide MIGRATION NOTES — what the major migration PR will do.

Honor Marco's HARD CONSTRAINTS without exception. Be opinionated. The output is a load-bearing decision, not a survey.`,
  { label: 'synthesize:final', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'xhigh' }
)

if (!synthesis) {
  log('ERROR: synthesis failed. Aborting RFC drafting.')
  return { error: 'synthesis-failed', proposalScores }
}

log(`Synthesis complete. Winner: ${synthesis.winnerStance}`)

phase('Draft RFC')
log('Phase 5: drafting G7_TRUST_TAXONOMY_RFC.md...')

const rfcDraftPrompt = `${TAXONOMY_CONTEXT}

# SYNTHESIS RESULT (THIS IS THE FINAL DECISION)

WINNER: ${synthesis.winnerStance}
JUSTIFICATION: ${synthesis.winnerJustification}

GRAFTED IDEAS: ${(synthesis.graftedIdeas || []).join(' | ')}

FINAL FORMULA SUMMARY: ${synthesis.finalFormulaSummary}

FINAL THRESHOLDS:
- S: ${synthesis.finalThresholds.S}
- A: ${synthesis.finalThresholds.A}
- B: ${synthesis.finalThresholds.B}
- C: ${synthesis.finalThresholds.C}

FINAL TYPE WEIGHTS: ${JSON.stringify(synthesis.finalTypeWeights || {}, null, 2)}

FINAL DIVERSITY RULES: ${JSON.stringify(synthesis.finalDiversityRules || {}, null, 2)}

FINAL SOCIAL RULES: ${JSON.stringify(synthesis.finalSocialRules || {}, null, 2)}

FINAL CALIBRATION:
${(synthesis.finalCalibration || []).map(c => `  - ${c.skillId} (${c.currentRank}) → magnitude ${c.finalTrustMagnitude}, grade ${c.finalOverallGrade}, drift ${c.driftDirection}: ${c.rationale || ''}`).join('\n')}

KNOWN DRIFTS: ${(synthesis.knownDrifts || []).join(' | ')}
OPEN QUESTIONS: ${(synthesis.openQuestions || []).join(' | ')}
MIGRATION NOTES: ${(synthesis.migrationNotes || []).join(' | ')}

# YOUR ROLE: RFC DRAFTER

Write the FINAL RFC markdown to disk at:
\`C:/Users/C5396183/gaia-skill-tree/founder/handovers/G7_TRUST_TAXONOMY_RFC.md\`

Use the Write tool. Length: 12-20 pages of markdown (substantial — this is a load-bearing spec).

# REQUIRED SECTIONS

1. **Header** — title "G7 — Trust Taxonomy & Magnitude Formula RFC", status "Draft v1 — consensus output, awaiting Marco approval", date "2026-06-16".
2. **§0 Executive Summary** — one page. The one-paragraph version of what this RFC decides.
3. **§1 Mental Model** — artifacts/equipment metaphor. Trust Magnitude as accumulated power. Why this replaces "trustNumber" / 0-100 percentage thinking.
4. **§2 Evidence Taxonomy** — full table of 10 evidence types with magnitude formulas, weights, freshness, caps, and S-capability. Include social-signal sub-rules in detail.
5. **§3 Aggregation — Trust Magnitude** — the sum formula. Soft-cap 500. How per-evidence artifact tier interacts with overall grade.
6. **§4 Overall Grade Thresholds & Diversity Gates** — final S/A/B/C numbers + distinct-type requirements + plus-rules. Worked examples (at minimum: a real Ultimate, a stars-only A, a fusion-only S, a community-heavy A, an edge case).
7. **§5 Reranking Cadence** — hybrid: event-driven for skill-level (every evidence change), quarterly batch for structural rerank reports. Notification + appeal path.
8. **§6 Migration Plan (June 2026)** — major PR. Re-grade all evidence under new formula. Old entries preserved (no destructive deletion). Stamp report. Drift expectations from synthesis.knownDrifts.
9. **§7 Calibration Table** — actual 12+ skills from synthesis with current rank, final Trust Magnitude, final overall grade, drift direction, rationale.
10. **§8 Marco's Hard Constraints (Honored)** — explicit checklist showing each of Marco's 8 hard constraints is satisfied in the final spec.
11. **§9 Known Drifts & Acceptance** — what drifts the system, why it's acceptable, what's NOT acceptable.
12. **§10 Open Questions** — for future review (e.g. mid-July recalibration RFC).
13. **§11 Implementation Hooks** — list the code changes G2/G3/G4 PRs need to make to bring this RFC live (e.g., update grading.py thresholds, add fusion-recipe magnitude function, etc.).
14. **§12 Appendix: Worked Calculations** — show 3-5 detailed evidence-by-evidence Trust Magnitude calculations for prominent skills.

# STYLE
- Tight prose. No filler. Every paragraph must do work.
- Use tables liberally for taxonomy and calibration.
- Show formulas as inline math or fenced code blocks.
- Cross-reference sections (§3, §4, etc.).
- Match the GAIA project tone (terse, decision-oriented, no rarity references).
- Token spend log at the bottom (per Marco's PR #695 directive).

After writing, return ONLY a one-paragraph summary of what you wrote and the file path. Do not paste the RFC content into your response — the file is the deliverable.`

const draftSummary = await agent(rfcDraftPrompt, {
  label: 'draft:rfc-final',
  phase: 'Draft RFC',
  effort: 'xhigh',
})

log('RFC draft complete.')

return {
  status: 'complete',
  winnerStance: synthesis.winnerStance,
  winnerJustification: synthesis.winnerJustification,
  finalThresholds: synthesis.finalThresholds,
  proposalScores: proposalScores.map(ps => ({
    stance: ps.proposal.stanceName,
    avgScore: ps.avgScore.toFixed(2),
    refuteCount: ps.refuteCount,
  })),
  knownDrifts: synthesis.knownDrifts,
  openQuestions: synthesis.openQuestions,
  rfcPath: 'C:/Users/C5396183/gaia-skill-tree/founder/handovers/G7_TRUST_TAXONOMY_RFC.md',
  draftSummary,
}
