export const meta = {
  name: 'intake-ev-seed-pipeline',
  description: 'Evidence seed pipeline for 10 queued intake named skills — Phase 0 Firecrawl discovery + Phase 1-4 verification',
  phases: [
    { title: 'Phase 0: Discovery', detail: 'Firecrawl search for new Stage-2 evidence per skill (benchmark-result, arxiv, peer-review, social-signal)' },
    { title: 'Phase 1: Suite Appraisal', detail: 'trust_appraise --repo for agent-fusion (suite, no SKILL.md); fusion-recipe TM baseline' },
    { title: 'Phase 2: Collection', detail: 'Compile discovered rows into collector channels (technical/social)' },
    { title: 'Phase 3: Adversarial Audit', detail: 'Parallel adversarial review — URL format, source quality, tree/ vs blob/, proxy mismatches' },
    { title: 'Phase 4: Link Validation', detail: 'Firecrawl live HTTP status on all discovered URLs' },
    { title: 'Synthesis', detail: 'Per-skill evidence manifests + master source report + HTML dashboard update' },
  ],
}

// ─── CLI helpers (injected into every agent prompt that needs them) ──────────

const PYTHON_PREAMBLE = `
## Environment

The \`gaia\` binary is NOT available. Use:
  PYTHONPATH=src python3 -m gaia_cli.main <subcommand>

Firecrawl: use the \`firecrawl\` CLI (installed, authenticated via stored credentials).
  firecrawl search "<query>" --limit 5
  firecrawl scrape "<url>" --formats markdown

For trust_appraise:
  PYTHONPATH=src python3 scripts/trust_appraise.py --repo <owner/repo> --components <N>

Rate limit guidance: add a 2-second sleep between firecrawl calls to avoid 429s.
  python3 -c "import time; time.sleep(2)"
Run searches sequentially, not in rapid bursts. If a 429 is returned, wait 10s then retry once.
`

// ─── Skill definitions ───────────────────────────────────────────────────────

// Standard named-skill candidates (have a SKILL.md blob URL)
const STANDARD_SKILLS = [
  {
    id: 'token-observability',
    namedSlug: 'gaia-research/skill-cost',
    stars: '2★',
    issue: 1123,
    repo: 'gaia-research/skill-cost',
    skillMdUrl: 'https://github.com/gaia-research/skill-cost/blob/main/SKILL.md',
    decision: 'MAP',
  },
  {
    id: 'format-output',
    namedSlug: 'ayghri/format-output',
    stars: '2★',
    issue: 1252,
    repo: 'ayghri/i-have-adhd',
    skillMdUrl: 'https://github.com/ayghri/i-have-adhd/blob/main/skills/i-have-adhd/SKILL.md',
    decision: 'MAP',
  },
  {
    id: 'ux-audit',
    namedSlug: 'nextlevelbuilder/ux-audit',
    stars: '2★',
    issue: 1251,
    repo: 'nextlevelbuilder/ui-ux-pro-max-skill',
    skillMdUrl: 'https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md',
    decision: 'MAP',
  },
  {
    id: 'scroll-world',
    namedSlug: 'oso95/scroll-world',
    stars: '3★',
    issue: 1266,
    repo: 'oso95/scroll-world',
    skillMdUrl: 'https://github.com/oso95/scroll-world/blob/main/skills/scroll-world/SKILL.md',
    decision: 'NEW_GENERIC',
    note: 'Gated on Ygg II landing on main before ingest',
  },
  {
    id: 'agent-reach',
    namedSlug: 'Panniantong/agent-reach',
    stars: '2★',
    issue: 1332,
    repo: 'Panniantong/Agent-Reach',
    skillMdUrl: 'https://github.com/Panniantong/Agent-Reach/blob/main/agent_reach/skill/SKILL_en.md',
    decision: 'MAP',
    note: 'Curator override expected: MAP to agent-eval rejected on semantics; likely NEW_GENERIC',
  },
  {
    id: 'react-performance-optimization',
    namedSlug: 'vercel-labs/vercel-react-best-practices',
    stars: '2★',
    issue: 1379,
    repo: 'vercel-labs/agent-skills',
    skillMdUrl: 'https://github.com/vercel-labs/agent-skills/blob/main/skills/react-best-practices/SKILL.md',
    decision: 'NEW_GENERIC',
  },
  {
    id: 'static-artwork-design',
    namedSlug: 'anthropics/canvas-design',
    stars: '2★',
    issue: 1380,
    repo: 'anthropics/skills',
    skillMdUrl: 'https://github.com/anthropics/skills/blob/main/skills/canvas-design/SKILL.md',
    decision: 'MAP',
    note: 'Reviewer must confirm MAP fit vs agentic-workflow-design (0.73); fallback NEW_GENERIC',
  },
]

// disler Pass-1 skills (NEW_GENERIC, have SKILL.md-equivalent blobs)
const DISLER_PASS1_SKILLS = [
  {
    id: 'opinion',
    namedSlug: 'disler/opinion',
    stars: '2★',
    issue: 1243,
    repo: 'disler/fusion-harness',
    skillMdUrl: 'https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_OPINION.md',
    decision: 'NEW_GENERIC',
  },
  {
    id: 'plan-synthesis',
    namedSlug: 'disler/merged-plan',
    stars: '2★',
    issue: 1243,
    repo: 'disler/fusion-harness',
    skillMdUrl: 'https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_FUSION_MERGE.md',
    decision: 'NEW_GENERIC',
    note: 'Named slug /merged-plan intentionally differs from generic ID plan-synthesis',
  },
  {
    id: 'auto-review',
    namedSlug: 'disler/auto-validate',
    stars: '2★',
    issue: 1243,
    repo: 'disler/fusion-harness',
    skillMdUrl: 'https://github.com/disler/fusion-harness/blob/main/extensions/fusion-harness/USER_PROMPT_VALIDATOR.md',
    decision: 'NEW_GENERIC',
    note: 'Named slug /auto-validate intentionally differs from generic ID auto-review',
  },
]

// agent-fusion: skill-suite, no SKILL.md — TM via fusion-recipe + trust_appraise --repo
const AGENT_FUSION = {
  id: 'agent-fusion',
  namedSlug: 'disler/agent-fusion',
  stars: '2★',
  issue: 1243,
  repo: 'disler/fusion-harness',
  skillMdUrl: null, // intentionally null — this is a suite with no standalone SKILL.md
  isSuite: true,
  suiteComponents: ['disler/opinion', 'disler/merged-plan', 'disler/auto-validate'],
  componentCount: 3, // Pass-1 prereqs — opinion, plan-synthesis, auto-review
  decision: 'NEW_GENERIC',
  note: 'Skill-suite: TM derived from fusion-recipe (componentCount=3) + github-stars-own + repo-own. No SKILL.md — treat as suite, not uninstallable. Evidence discovery focuses on repo-level signals, YouTube/blog coverage of fusion-harness as a whole, and academic references to fusion/multi-agent orchestration patterns.',
}

const ALL_STANDARD = [...STANDARD_SKILLS, ...DISLER_PASS1_SKILLS]
const ALL_SKILLS = [...ALL_STANDARD, AGENT_FUSION]

// ─── Evidence type search queries per skill ──────────────────────────────────

function buildSearchQueries(skill) {
  const name = skill.namedSlug.split('/')[1]
  const repo = skill.repo
  const baseQueries = [
    // benchmark / technical
    `"${name}" benchmark evaluation agent skill performance`,
    `site:arxiv.org "${name}" OR "${repo.split('/')[1]}" agent skill`,
    `"${repo}" peer review audit evaluation`,
    // social signals
    `"${repo}" OR "${name}" developer blog article 2025 2026`,
    `site:youtube.com "${name}" OR "${repo.split('/')[1]}" agent demo tutorial`,
    `site:dev.to OR site:medium.com "${name}" agent skill`,
  ]
  if (skill.isSuite) {
    // Suite-specific: repo-wide signals, fusion pattern references
    return [
      ...baseQueries,
      `"${repo.split('/')[1]}" multi-agent fusion orchestration benchmark`,
      `site:youtube.com "${repo.split('/')[0]}" fusion harness agent 2025 2026`,
      `"fusion-harness" OR "${repo.split('/')[1]}" agent composition review`,
    ]
  }
  return baseQueries
}

// ─── Schemas ─────────────────────────────────────────────────────────────────

const DISCOVERY_SCHEMA = {
  type: 'object',
  properties: {
    skillId: { type: 'string' },
    namedSlug: { type: 'string' },
    technicalFindings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          evidenceType: { type: 'string', enum: ['benchmark-result', 'arxiv', 'peer-review', 'repo-own', 'github-stars-own'] },
          url: { type: 'string' },
          title: { type: 'string' },
          notes: { type: 'string' },
          grade: { type: 'string', enum: ['S', 'A', 'B', 'C', 'D'] },
          isNew: { type: 'boolean', description: 'True if this was not in the existing data lake' },
        },
        required: ['evidenceType', 'url', 'title', 'notes', 'grade', 'isNew'],
      },
    },
    socialFindings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          evidenceType: { type: 'string', enum: ['social-signal', 'self-attestation'] },
          url: { type: 'string' },
          title: { type: 'string' },
          notes: { type: 'string' },
          grade: { type: 'string', enum: ['S', 'A', 'B', 'C', 'D'] },
          estimatedViews: { type: 'number', description: 'For social-signal: verifiable view/read count. 0 if not verifiable.' },
          isNew: { type: 'boolean' },
        },
        required: ['evidenceType', 'url', 'title', 'notes', 'grade', 'isNew'],
      },
    },
    suiteAppraisalResult: {
      type: 'string',
      description: 'For suite skills only: raw output of trust_appraise --repo. Empty string for non-suites.',
    },
    searchQueriesRun: { type: 'array', items: { type: 'string' } },
    discoveryNotes: { type: 'string' },
  },
  required: ['skillId', 'namedSlug', 'technicalFindings', 'socialFindings', 'suiteAppraisalResult', 'searchQueriesRun', 'discoveryNotes'],
}

const ADVERSARIAL_SCHEMA = {
  type: 'object',
  properties: {
    skillId: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          issue: { type: 'string', enum: ['tree-not-blob', 'proxy-mismatch', 'evaluative-noise', 'source-mismatch', 'duplicate', 'fabricated-metric', 'clean'] },
          severity: { type: 'string', enum: ['block', 'warn', 'ok'] },
          note: { type: 'string' },
        },
        required: ['url', 'issue', 'severity', 'note'],
      },
    },
    cleanRowCount: { type: 'number' },
    blockedRowCount: { type: 'number' },
    warnRowCount: { type: 'number' },
    verdict: { type: 'string', enum: ['pass', 'pass-with-warnings', 'has-blocks'] },
  },
  required: ['skillId', 'findings', 'cleanRowCount', 'blockedRowCount', 'warnRowCount', 'verdict'],
}

const LINK_VALIDATION_SCHEMA = {
  type: 'object',
  properties: {
    skillId: { type: 'string' },
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          url: { type: 'string' },
          httpStatus: { type: 'number' },
          live: { type: 'boolean' },
          note: { type: 'string' },
        },
        required: ['url', 'httpStatus', 'live'],
      },
    },
    liveCount: { type: 'number' },
    deadCount: { type: 'number' },
  },
  required: ['skillId', 'results', 'liveCount', 'deadCount'],
}

// ─── Workflow ─────────────────────────────────────────────────────────────────

// ── Phase 0: Discovery (Firecrawl) — fan out per skill ───────────────────────
phase('Phase 0: Discovery')
log(`Discovering new Stage-2 evidence for ${ALL_SKILLS.length} skills (${STANDARD_SKILLS.length} standard + ${DISLER_PASS1_SKILLS.length} disler Pass-1 + 1 suite)`)

const discoveryResults = await pipeline(
  ALL_SKILLS,
  async (skill) => {
    const queries = buildSearchQueries(skill)
    const isSuite = !!skill.isSuite

    const prompt = `You are running Phase 0 evidence discovery for the Gaia skill registry.
${PYTHON_PREAMBLE}

Skill: ${skill.namedSlug} (generic ID: ${skill.id})
Issue: #${skill.issue}
Repo: https://github.com/${skill.repo}
${skill.skillMdUrl ? `SKILL.md: ${skill.skillMdUrl}` : `SUITE SKILL — no standalone SKILL.md. This is a skill-suite whose TM comes from fusion-recipe evidence (componentCount=${skill.componentCount}) plus repo-level signals.`}
Decision path: ${skill.decision}
${skill.note ? `Curator note: ${skill.note}` : ''}

${isSuite ? `SUITE HANDLING INSTRUCTIONS:
- This is a skill-suite (like gsd-build/get-shit-done, mattpocock/skills). It has NO standalone SKILL.md.
- Do NOT flag it as uninstallable — suite skills are installable via their component network.
- Evidence focus: repo-level signals (github-stars-own, repo-own), fusion-recipe (auto-derived from components), and broader coverage signals for the fusion-harness repo as a whole.
- Run suite TM appraisal with the Python CLI:
    PYTHONPATH=src python3 scripts/trust_appraise.py --repo ${skill.repo} --components ${skill.componentCount}
  Capture the full stdout as suiteAppraisalResult.
- For discovery queries, focus on: YouTube demos of fusion-harness, blog/dev.to articles about multi-agent fusion patterns, any academic work on agent composition/orchestration that references this approach.
- Social-signal evidenceType requires verifiable view counts — do NOT fabricate numbers. If count is not visible on the page, set estimatedViews: 0 and note "count not verifiable".
` : `STANDARD SKILL HANDLING INSTRUCTIONS:
- Scrape the SKILL.md artifact to understand what capability this skill documents:
    firecrawl scrape "${skill.skillMdUrl}" --formats markdown
- Run Firecrawl searches to discover new Stage-2 evidence. Run each query sequentially with a 2s sleep between calls.
- Stage-2 evidence types to hunt: benchmark-result, arxiv, peer-review, richer social-signal (blogs, YouTube, dev.to, medium.com).
- Stage-1 evidence (github-stars-own, repo-own, self-attestation) is already captured by gaia push — only report these if you find something substantively new.
- social-signal REQUIRES verifiable view counts. If count not visible, set estimatedViews: 0.
`}

Search queries to run via firecrawl CLI (sequentially, 2s sleep between each):
${queries.map((q, i) => `${i + 1}. firecrawl search "${q}" --limit 5`).join('\n')}

For each promising search result, scrape it:
  firecrawl scrape "<url>" --formats markdown
(sleep 2s between scrape calls)
- Is it genuinely about this skill/repo? (not just keyword noise)
- Is the evidence type one of: benchmark-result, arxiv, peer-review, social-signal?
- Is any SKILL.md link a blob/ path, not tree/?
- Is the metric verifiable (for benchmark-result: actual numbers; for social-signal: actual view counts)?

Check existing data lake first to avoid duplicates — read the first 60 lines of each:
- evidence/collectors/technical/benchmark_results.md
- evidence/collectors/technical/academic_papers.md
- evidence/collectors/social/blogs_newsletters.md
- evidence/collectors/social/youtube_showcases.md

Mark isNew: true only for rows not already in those files.

Return structured output only. Do not invent metrics.`

    return agent(prompt, {
      label: `discover:${skill.id}`,
      phase: 'Phase 0: Discovery',
      schema: DISCOVERY_SCHEMA,
    })
  }
)

const validDiscovery = discoveryResults.filter(Boolean)
log(`Discovery complete: ${validDiscovery.length}/${ALL_SKILLS.length} skills processed`)

// ── Phase 1: Suite TM Appraisal (agent-fusion specifically) ─────────────────
phase('Phase 1: Suite Appraisal')

// agent-fusion suite appraisal is embedded in the discovery agent above,
// but we surface it explicitly here for the synthesis report.
const agentFusionDiscovery = validDiscovery.find(d => d.skillId === 'agent-fusion')
const suiteAppraisalText = agentFusionDiscovery?.suiteAppraisalResult || '(not captured)'

log(`agent-fusion suite appraisal: ${suiteAppraisalText.slice(0, 200)}`)

// ── Phase 2: Collection — compile discovered rows into collector channels ────
phase('Phase 2: Collection')

const collectionResult = await agent(
  `You are running Phase 2 (Collection) of the Gaia evidence verification pipeline.
${PYTHON_PREAMBLE}

You have discovery results for ${validDiscovery.length} skills. Your job is to:
1. Compile ALL new rows (isNew: true) from the discovery results into the correct collector channels
2. Append them to the appropriate files in evidence/collectors/technical/ and evidence/collectors/social/
3. Report what was appended

Discovery results (skill-level summaries):
${JSON.stringify(validDiscovery.map(d => ({
  skillId: d.skillId,
  namedSlug: d.namedSlug,
  newTechnicalRows: d.technicalFindings.filter(f => f.isNew).length,
  newSocialRows: d.socialFindings.filter(f => f.isNew).length,
  technicalFindings: d.technicalFindings.filter(f => f.isNew),
  socialFindings: d.socialFindings.filter(f => f.isNew),
})), null, 2)}

Files to append to:
- evidence/collectors/technical/benchmark_results.md — for benchmark-result rows
- evidence/collectors/technical/academic_papers.md — for arxiv and peer-review rows
- evidence/collectors/social/blogs_newsletters.md — for social-signal (blog/article) rows
- evidence/collectors/social/youtube_showcases.md — for social-signal (YouTube) rows

Read each file first to confirm the exact table column headers and row style, then append matching rows.

After appending, attempt to refresh the unified lake:
  PYTHONPATH=src python3 scripts/ev_collection.py 2>&1 | head -30
If that script does not exist, manually append the new rows to evidence/unified_evidence_lake.md in the existing table format.

Report: how many rows appended per file, any errors.`,
  { label: 'collection', phase: 'Phase 2: Collection' }
)

log(`Collection phase complete`)

// ── Phase 3: Adversarial Audit — parallel per skill ─────────────────────────
phase('Phase 3: Adversarial Audit')

const adversarialResults = await parallel(
  validDiscovery.map(discovery => async () => {
    const allUrls = [
      ...discovery.technicalFindings.map(f => f.url),
      ...discovery.socialFindings.map(f => f.url),
    ].filter(Boolean)

    if (allUrls.length === 0) {
      return {
        skillId: discovery.skillId,
        findings: [],
        cleanRowCount: 0,
        blockedRowCount: 0,
        warnRowCount: 0,
        verdict: 'pass',
      }
    }

    return agent(
      `You are Adversarial Reviewer A for skill "${discovery.skillId}" (${discovery.namedSlug}).

A second independent reviewer will also assess these URLs. Your job is to argue AGAINST each row — try to find problems. Be skeptical.

URLs to audit:
${allUrls.map((u, i) => `${i + 1}. ${u}`).join('\n')}

Check each URL for:
1. tree/ vs blob/ — any SKILL.md or source file link using tree/ instead of blob/ is a BLOCK
2. Proxy mismatch — does the URL actually point to the skill's own repo, or is it a tangential source?
3. Evaluative noise — is the metric fabricated or unverifiable? (benchmark numbers with no methodology = WARN; fabricated view counts = BLOCK)
4. Duplicate — is this URL already in evidence/collectors/ for this skill?
5. Source mismatch — does the URL domain/content match the claimed evidence type?

For each URL, return a finding with severity: 'block', 'warn', or 'ok'.
A 'block' prevents the row from entering the registry. A 'warn' is a flag for human review. 'ok' is clean.

Be strict. A URL that LOOKS fine but can't be independently verified should be 'warn' not 'ok'.`,
      {
        label: `adversarial:${discovery.skillId}`,
        phase: 'Phase 3: Adversarial Audit',
        schema: ADVERSARIAL_SCHEMA,
      }
    )
  })
)

const validAdversarial = adversarialResults.filter(Boolean)
const totalBlocked = validAdversarial.reduce((sum, r) => sum + r.blockedRowCount, 0)
const totalWarned = validAdversarial.reduce((sum, r) => sum + r.warnRowCount, 0)
log(`Adversarial audit: ${totalBlocked} blocked, ${totalWarned} warned across ${validAdversarial.length} skills`)

// ── Phase 4: Link Validation — Firecrawl HTTP status on all live URLs ────────
phase('Phase 4: Link Validation')

// Collect all non-blocked URLs across all skills
const urlsToValidate = validDiscovery.flatMap(d => {
  const skillAudit = validAdversarial.find(a => a.skillId === d.skillId)
  const blockedUrls = new Set(
    (skillAudit?.findings || []).filter(f => f.severity === 'block').map(f => f.url)
  )
  return [
    ...d.technicalFindings.map(f => f.url),
    ...d.socialFindings.map(f => f.url),
  ].filter(u => u && !blockedUrls.has(u))
})

const uniqueUrls = [...new Set(urlsToValidate)]
log(`Link validation: checking ${uniqueUrls.length} unique URLs via Firecrawl`)

const linkValidationResults = await parallel(
  ALL_SKILLS.map(skill => async () => {
    const discovery = validDiscovery.find(d => d.skillId === skill.id)
    const audit = validAdversarial.find(a => a.skillId === skill.id)
    if (!discovery) return null

    const blockedUrls = new Set(
      (audit?.findings || []).filter(f => f.severity === 'block').map(f => f.url)
    )
    const skillUrls = [
      ...discovery.technicalFindings.map(f => f.url),
      ...discovery.socialFindings.map(f => f.url),
      skill.skillMdUrl,
    ].filter(u => u && !blockedUrls.has(u))

    if (skillUrls.length === 0) {
      return { skillId: skill.id, results: [], liveCount: 0, deadCount: 0 }
    }

    return agent(
      `You are running Phase 4 (Link Validation) for skill "${skill.id}" (${skill.namedSlug}).
${PYTHON_PREAMBLE}

Use the firecrawl CLI to check each URL. Run sequentially with 2s sleep between calls:
  firecrawl scrape "<url>" --formats markdown

A non-empty markdown response = live: true, httpStatus: 200.
An error / empty response = live: false, httpStatus: 404 (or 0 if connection failed).

${skill.isSuite ? `NOTE: Suite skill — no standalone SKILL.md. Validate https://github.com/${skill.repo} (repo root). No SKILL.md URL to check.` : ''}

URLs to validate:
${skillUrls.map((u, i) => `${i + 1}. ${u}`).join('\n')}

For each URL report: url, httpStatus, live (bool), note.`,
      {
        label: `linkval:${skill.id}`,
        phase: 'Phase 4: Link Validation',
        schema: LINK_VALIDATION_SCHEMA,
      }
    )
  })
)

const validLinkVal = linkValidationResults.filter(Boolean)
const totalDead = validLinkVal.reduce((sum, r) => sum + r.deadCount, 0)
const totalLive = validLinkVal.reduce((sum, r) => sum + r.liveCount, 0)
log(`Link validation complete: ${totalLive} live, ${totalDead} dead`)

// ── Synthesis — per-skill manifests + master report + HTML dashboard ─────────
phase('Synthesis')

const synthesis = await agent(
  `You are synthesizing the evidence seed pipeline run for the Gaia intake queue.

Date: 2026-07-30

## Skills processed
${ALL_SKILLS.map(s => `- ${s.namedSlug} (${s.id}) — issue #${s.issue}${s.isSuite ? ' [SUITE]' : ''}`).join('\n')}

## Discovery results
${JSON.stringify(validDiscovery.map(d => ({
  skillId: d.skillId,
  namedSlug: d.namedSlug,
  newTechnical: d.technicalFindings.filter(f => f.isNew).length,
  newSocial: d.socialFindings.filter(f => f.isNew).length,
  discoveryNotes: d.discoveryNotes,
  suiteAppraisalResult: d.suiteAppraisalResult || null,
})), null, 2)}

## Adversarial audit results
${JSON.stringify(validAdversarial.map(a => ({
  skillId: a.skillId,
  verdict: a.verdict,
  blocked: a.blockedRowCount,
  warned: a.warnRowCount,
  clean: a.cleanRowCount,
})), null, 2)}

## Link validation results
${JSON.stringify(validLinkVal.map(v => ({
  skillId: v.skillId,
  live: v.liveCount,
  dead: v.deadCount,
  deadUrls: v.results.filter(r => !r.live).map(r => r.url),
})), null, 2)}

## agent-fusion suite appraisal (from discovery phase)
${suiteAppraisalText}

Your tasks:
1. Write evidence/source_report_2026_07_30.md — master source report covering:
   - Pipeline run summary (skills processed, new rows discovered, blocked/warned/dead URLs)
   - Per-skill section: new evidence rows found, adversarial flags, link status
   - agent-fusion suite TM interpretation (fusion-recipe=90 base, component count=3, Grade B) and what additional evidence would push it to Grade A
   - Recommendations for the /gaia-ingest-batch step (which skills are evidence-ready, which need rework)

2. Write evidence/collectors/verification/firecrawl_validation_report_2026_07_30.md — link validation report:
   - All URLs checked, live/dead status, any 404s to action

3. Update evidence/verification_process.html — patch the statistics block to reflect:
   - Today's date (2026-07-30)
   - New pipeline run entry
   - Skills processed count
   (Read the file first to understand the existing format; make a minimal, targeted update to the stats/run-history section only.)

4. Return a concise summary (under 300 words) of:
   - Headline numbers
   - Top 3 new evidence finds
   - Any skills that need rework before ingest
   - agent-fusion suite readiness verdict`,
  { label: 'synthesis', phase: 'Synthesis' }
)

return {
  skillsProcessed: ALL_SKILLS.length,
  discoveryComplete: validDiscovery.length,
  suiteAppraisalResult: suiteAppraisalText,
  adversarialSummary: { blocked: totalBlocked, warned: totalWarned },
  linkValidationSummary: { live: totalLive, dead: totalDead },
  synthesis,
}
