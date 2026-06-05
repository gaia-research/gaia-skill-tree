export const meta = {
  name: 'gaia-wiki-sync',
  description: 'Sync Gaia GitHub wiki — parallel source-readers, parallel page-drafters, bounded cross-check',
  phases: [
    { title: 'Discovery',    detail: 'Read commit range, emit SyncPlan' },
    { title: 'Source-Read',  detail: 'Parallel domain readers → SourceDigests' },
    { title: 'Page-Draft',   detail: 'Parallel page drafters → PageDrafts' },
    { title: 'Cross-Check',  detail: 'Terminology refuter, bounded 2-loop' },
    { title: 'Apply',        detail: 'Write files, commit, push wiki' },
    { title: 'Ledger-Close', detail: 'Finalize ledger, return summary' },
  ],
}

// ── constants ─────────────────────────────────────────────────────────────────

const MAX_CONVERGENCE_ITERATIONS = 2
const LEDGER_STALENESS_HOURS = 24

const DOMAIN_MAP = {
  cli:    { files: ['src/gaia_cli/main.py', 'src/gaia_cli/formatting.py', 'README.md (gaia:cli region)'], affects: ['CLI-Reference', 'Initiates-Rite'] },
  schema: { files: ['registry/schema/*.json', 'CONTEXT.md'],                                              affects: ['Schema-Reference', 'Stars-and-Ranks', 'Skill-Types'] },
  named:  { files: ['registry/named-skills.json', 'registry/named/'],                                     affects: ['Named-Skills', 'Ascension-Cycle'] },
  policy: { files: ['CONTRIBUTING.md', 'CLAUDE.md', 'META.md'],                                           affects: ['Contributing', 'FAQ', 'Stars-and-Ranks'] },
  mcp:    { files: ['packages/mcp/src/', 'packages/mcp/package.json'],                                    affects: ['MCP-Server', 'FAQ'] },
}

const CI_OWNED_REGIONS = [
  { page: 'CLI-Reference', startMarker: '<!-- gaia:cli-start -->', endMarker: '<!-- gaia:cli-end -->', policy: 'preserve-verbatim' },
]

// ── schemas ───────────────────────────────────────────────────────────────────

const SYNC_PLAN_SCHEMA = {
  type: 'object',
  required: ['syncWindow', 'sourceDomains', 'stalePages', 'skipPages', 'ciOwnedRegions'],
  properties: {
    syncWindow:     { type: 'object', required: ['since', 'until'], properties: { since: { type: 'string' }, until: { type: 'string' } } },
    sourceDomains:  { type: 'object' },
    stalePages:     { type: 'array', items: { type: 'string' } },
    skipPages:      { type: 'array', items: { type: 'string' } },
    ciOwnedRegions: { type: 'array' },
    commitSummary:  { type: 'string' },
  },
}

const SOURCE_DIGEST_SCHEMA = {
  type: 'object',
  required: ['domain', 'filesRead', 'facts', 'renames', 'deprecations'],
  properties: {
    domain:       { type: 'string' },
    filesRead:    { type: 'array', items: { type: 'string' } },
    facts:        { type: 'array', items: { type: 'object', required: ['id', 'claim', 'evidence'] } },
    renames:      { type: 'array', items: { type: 'object', required: ['from', 'to', 'since'] } },
    deprecations: { type: 'array', items: { type: 'string' } },
  },
}

const PAGE_DRAFT_SCHEMA = {
  type: 'object',
  required: ['pageName', 'newContent', 'citedFactIds', 'unresolvedFacts', 'changed'],
  properties: {
    pageName:        { type: 'string' },
    newContent:      { type: 'string' },
    citedFactIds:    { type: 'array', items: { type: 'string' } },
    unresolvedFacts: { type: 'array', items: { type: 'string' } },
    changed:         { type: 'boolean' },
    changeReason:    { type: 'string' },
  },
}

const CONFLICTS_SCHEMA = {
  type: 'object',
  required: ['conflicts'],
  properties: {
    conflicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['page', 'issue', 'factId'],
        properties: { page: { type: 'string' }, issue: { type: 'string' }, factId: { type: 'string' } },
      },
    },
  },
}

// ── helpers ───────────────────────────────────────────────────────────────────

function domainsForPage(pageName, sourceDomains) {
  return Object.entries(sourceDomains)
    .filter(([, info]) => info.affects && info.affects.includes(pageName))
    .map(([domain]) => domain)
}

function ciMarkersForPage(pageName) {
  return CI_OWNED_REGIONS.filter(r => r.page === pageName)
}

// ── phase 1: discovery ────────────────────────────────────────────────────────

phase('Discovery')

const sinceArg = typeof args === 'string' && args.includes('--since')
  ? args.match(/--since\s+(\S+)/)?.[1]
  : null

const plan = await agent(
  `You are the Wiki Sync Planner. Your ONLY job is to emit a SyncPlan JSON object. Do not edit files.

Steps:
1. Run: git log --oneline $(cd ../gaia-wiki && git log -1 --format="%H") ..HEAD
   If that fails, use git log --oneline --since="30 days ago"
   ${sinceArg ? `Alternatively, the user specified --since ${sinceArg}` : ''}
2. Run: git diff --name-only $(cd ../gaia-wiki && git log -1 --format="%H") HEAD
3. Classify each changed path into one of these domains: cli, schema, named, policy, mcp
   Domain→file mapping reference: ${JSON.stringify(DOMAIN_MAP, null, 2)}
4. For each domain, list which wiki pages are affected (use the "affects" arrays above).
5. List wiki pages that are ALREADY up-to-date and can be skipped.
6. Note any CI-owned regions: ${JSON.stringify(CI_OWNED_REGIONS)}
7. Emit the SyncPlan. Use empty arrays if nothing changed for a domain/page.

IMPORTANT: stalePages must only include pages that actually need updating based on the diff.
Do not list pages that haven't changed. Return ONLY the JSON object, no commentary.`,
  { label: 'planner', phase: 'Discovery', schema: SYNC_PLAN_SCHEMA }
)

log(`Discovery complete: ${plan.stalePages.length} stale pages across ${Object.keys(plan.sourceDomains).length} domains`)
log(`Stale pages: ${plan.stalePages.join(', ')}`)

if (plan.stalePages.length === 0) {
  log('All wiki pages are up to date. Nothing to do.')
  return { status: 'up-to-date', message: 'No wiki pages needed updating.' }
}

// Check for --check dry-run mode
const isDryRun = typeof args === 'string' && args.includes('--check')
if (isDryRun) {
  log('--check mode: stopping after discovery (no writes).')
  return { status: 'check-complete', plan }
}

// ── phase 2: source-read ──────────────────────────────────────────────────────

phase('Source-Read')

const domainNames = Object.keys(plan.sourceDomains)

const digests = await parallel(
  domainNames.map(domain => () => agent(
    `You are the ${domain.toUpperCase()} Domain Reader. Read the source files for the "${domain}" domain and produce a SourceDigest.

Files to read: ${JSON.stringify(plan.sourceDomains[domain]?.files || DOMAIN_MAP[domain]?.files || [])}

Your task:
- Read every file listed (use Read tool, Grep tool to find symbols/flags).
- Extract discrete FACTS — specific, verifiable claims about the current state of the codebase.
  Assign each fact a unique id like "${domain}.cmd.scan" or "${domain}.schema.level".
  Include the exact file path and line number or section as evidence.
- Extract RENAMES — things that were renamed since the wiki was last updated.
  Format: { from: "old name", to: "new name", since: "v3.28.0" }
- Extract DEPRECATIONS — terms, flags, axes, or commands that no longer exist.
  Always include: "rarity axis" (deprecated per CONTEXT.md).
  Also check CONTEXT.md banned-synonym list and include all entries.

Be thorough. A missed rename will cause the cross-check phase to catch drift.
Return ONLY the SourceDigest JSON object.`,
    { label: `source-read:${domain}`, phase: 'Source-Read', schema: SOURCE_DIGEST_SCHEMA }
  ))
)

const validDigests = digests.filter(Boolean)
log(`Source-Read complete: ${validDigests.length}/${domainNames.length} domains read`)

// Build lookup maps for cross-check phase
const allRenames = validDigests.flatMap(d => d.renames)
const allDeprecations = validDigests.flatMap(d => d.deprecations)
const digestsByDomain = Object.fromEntries(validDigests.map(d => [d.domain, d]))

// ── phase 3: page-draft ───────────────────────────────────────────────────────

phase('Page-Draft')

const draftPage = async (pageName, conflictsForPage = []) => {
  const relevantDomains = domainsForPage(pageName, plan.sourceDomains)
  const relevantDigests = relevantDomains.map(d => digestsByDomain[d]).filter(Boolean)
  const ciMarkers = ciMarkersForPage(pageName)
  const conflictContext = conflictsForPage.length > 0
    ? `\n\nCONFLICTS TO FIX FROM PREVIOUS PASS:\n${conflictsForPage.map(c => `- ${c.issue} (factId: ${c.factId})`).join('\n')}`
    : ''

  return agent(
    `You are the ${pageName} page drafter. Your job is to produce an updated version of this wiki page.

STEP 1 — Read the current page:
File: ../gaia-wiki/${pageName}.md
Read it completely before writing anything.

STEP 2 — Consume these SourceDigests (your source of truth):
${JSON.stringify(relevantDigests, null, 2)}

STEP 3 — Write the updated page:
- Every claim you make MUST be traceable to a fact.id from the digests above.
- If you need a fact that isn't in the digests, add it to unresolvedFacts — do NOT invent.
- Preserve the existing structure, heading hierarchy, and tone.
- Do NOT modify content between these CI-owned markers (copy verbatim):
  ${JSON.stringify(ciMarkers)}
- Do NOT use deprecated terms: ${allDeprecations.join(', ')}
- Use current names for renamed things: ${allRenames.map(r => `"${r.from}" → "${r.to}"`).join(', ')}
- Use star notation (0★–6★), never Roman numerals.
- Only change what actually changed. If a section is still accurate, keep it.
${conflictContext}

STEP 4 — Set changed: true only if you actually changed something meaningful.

Return ONLY the PageDraft JSON object.`,
    { label: `draft:${pageName}`, phase: 'Page-Draft', schema: PAGE_DRAFT_SCHEMA }
  )
}

let drafts = await parallel(
  plan.stalePages.map(pageName => () => draftPage(pageName))
)

drafts = drafts.filter(Boolean)
log(`Page-Draft complete: ${drafts.filter(d => d.changed).length} pages changed, ${drafts.filter(d => d.unresolvedFacts?.length > 0).length} with unresolved facts`)

// Flag pages with unresolved facts for human review
const unresolvedPages = drafts.filter(d => d.unresolvedFacts?.length > 0)
if (unresolvedPages.length > 0) {
  log(`⚠ Pages with unresolved facts (will not be applied): ${unresolvedPages.map(d => d.pageName).join(', ')}`)
}

// Only apply pages with no unresolved facts
const applyDrafts = drafts.filter(d => d.changed && d.unresolvedFacts?.length === 0)

// ── phase 4: cross-check ──────────────────────────────────────────────────────

if (applyDrafts.length > 1) {
  phase('Cross-Check')

  let convergenceIteration = 0
  let pendingDrafts = applyDrafts

  while (convergenceIteration < MAX_CONVERGENCE_ITERATIONS) {
    const conflictsResult = await agent(
      `You are the Terminology Refuter. Your ONLY job is to find terminology conflicts across these wiki page drafts.

Page drafts to check:
${pendingDrafts.map(d => `### ${d.pageName}\n${d.newContent.slice(0, 3000)}...`).join('\n\n')}

Global renames (old → new): ${JSON.stringify(allRenames)}
Deprecated terms (must not appear): ${JSON.stringify(allDeprecations)}

Check for:
1. Any draft using a deprecated term or old command name from the renames list
2. Factual contradictions between pages (e.g. two pages claim different values for the same thing)
3. Any reintroduction of the "rarity" axis (explicitly deprecated in CONTEXT.md)

Do NOT comment on style, completeness, or tone. Only report mechanical conflicts.
Return ONLY the Conflicts JSON object. If no conflicts found, return { "conflicts": [] }`,
      { label: `refuter:iter${convergenceIteration}`, phase: 'Cross-Check', schema: CONFLICTS_SCHEMA }
    )

    if (!conflictsResult || conflictsResult.conflicts.length === 0) {
      log(`Cross-check passed (iteration ${convergenceIteration + 1})`)
      break
    }

    log(`Cross-check found ${conflictsResult.conflicts.length} conflicts — re-drafting affected pages (iteration ${convergenceIteration + 1})`)

    // Group conflicts by page
    const conflictsByPage = {}
    for (const c of conflictsResult.conflicts) {
      if (!conflictsByPage[c.page]) conflictsByPage[c.page] = []
      conflictsByPage[c.page].push(c)
    }

    // Re-draft only affected pages
    const affectedPageNames = Object.keys(conflictsByPage)
    const reDrafts = await parallel(
      affectedPageNames.map(pageName => () => draftPage(pageName, conflictsByPage[pageName]))
    )

    // Merge re-drafts back into pendingDrafts
    for (const reDraft of reDrafts.filter(Boolean)) {
      const idx = pendingDrafts.findIndex(d => d.pageName === reDraft.pageName)
      if (idx >= 0) pendingDrafts[idx] = reDraft
    }

    convergenceIteration++

    if (convergenceIteration >= MAX_CONVERGENCE_ITERATIONS) {
      log(`⚠ Cross-check did not converge after ${MAX_CONVERGENCE_ITERATIONS} iterations. Halting — human review required.`)
      return {
        status: 'needs-human-review',
        message: `Terminology conflicts persisted after ${MAX_CONVERGENCE_ITERATIONS} convergence iterations.`,
        conflicts: conflictsResult.conflicts,
        plan,
      }
    }
  }
}

// ── phase 5: apply ────────────────────────────────────────────────────────────

phase('Apply')

const changedPageNames = applyDrafts.map(d => d.pageName)

const applyResult = await agent(
  `You are the Wiki Applier. Write updated wiki pages, commit, and push.

Wiki repo path: ../gaia-wiki

Pages to write (${changedPageNames.length} total):
${applyDrafts.map(d => `### ${d.pageName}\nNew content length: ${d.newContent.length} chars\nCited facts: ${d.citedFactIds?.join(', ')}`).join('\n\n')}

FULL PAGE DRAFTS (write these exactly):
${JSON.stringify(applyDrafts.map(d => ({ pageName: d.pageName, newContent: d.newContent })))}

Instructions:
1. For EACH page in the list above:
   a. Read the current file at ../gaia-wiki/<pageName>.md
   b. Check for CI-owned regions: ${JSON.stringify(CI_OWNED_REGIONS)}
      If a CI-owned region exists in the current file, extract its content verbatim.
      In the new content, replace the region between the markers with the extracted content.
      ABORT this page (do not write it) if the markers exist in the current file but are missing from the draft.
   c. Write the new content to ../gaia-wiki/<pageName>.md

2. Stage all changed files:
   cd ../gaia-wiki && git add <files>

3. Commit with this message format:
   docs: sync wiki pages — <one-line summary of what changed>

   <bullet list of pages changed and why, grouped by topic>

   Auto-generated by gaia-wiki-sync v2.0.0.

4. Push:
   git push origin master

5. Report: the commit SHA, which pages were written, and whether any pages were skipped (with reason).

Return a plain text summary of what was committed.`,
  { label: 'applier', phase: 'Apply' }
)

log('Apply complete')

// ── phase 6: ledger-close ─────────────────────────────────────────────────────

phase('Ledger-Close')

return {
  status: 'complete',
  pagesUpdated: changedPageNames,
  pagesSkipped: plan.skipPages,
  pagesWithUnresolvedFacts: unresolvedPages.map(d => d.pageName),
  syncWindow: plan.syncWindow,
  applyResult,
}
