---
target: website conversion paths to 3 CTAs
total_score: 26
p0_count: 0
p1_count: 3
timestamp: 2026-06-05T18-20-55Z
slug: docs-index-html-conversion-paths
---
# Gaia Conversion-Path Audit — Three Priority CTAs

## Big finding
On-page prominence is inverted vs stated priority. Contribute (#1) has the weakest affordance and a broken CTA; Badges (#2) is strongest; Install (#3) is most omnipresent (printed on every tile).

## Heuristics: 26/40 (Acceptable). Strong craft, weak conversion routing. Not AI slop.

## CTA #1 Contribute (priority 1)
- [P1] codex.html:59 + how-we-do-things.html:45 "Submit a Skill" -> index.html#start = BROKEN (no #start; section is #paths).
- [P1] No dominant contribute affordance; both hero doors equal-weight ghosts (styles.css:7401).
- [P2] Verb sprawl: Register/Submit/Push/Propose/Claim for one act. Popup uses `gaia propose` vs Path A `gaia push`.
- [P2] Path A bloated 5->3 steps; says "Four steps" but shows five (IV MCP, V TUI are post-contribution).
- Idea: restructure two doors as Contribute (primary, gold-weighted) vs Explore (ghost).

## CTA #2 Badges/OG (priority 2)
- [P1] profile-claim.js dead-end "Add to README" button (localStorage, "coming soon" profile-claim.js:67). Two same-label affordances do different things.
- [P2] Hero copy 106 words; para 2 (badges/index.html:893-894) pure prestige + banned aphoristic cadence.
- [P2] "Preview" button vague -> "Generate my badges".
- [P2] Confirm pill "Are you @handle?" gates README every open.
- [P3] Repo-register jargon wall ~95 words (badges/index.html:1812-1815).
- [P3] Validating note ~110 words below copy buttons (badges/index.html:997-1021).

## CTA #3 Install (priority 3)
- Good: install command on tiles, 0 clicks after scroll (plaque.js:184).
- [P2] No named install entry point; "Browse all named skills" hides intent.
- [P2] Install row missing on profile settled cards (plaque.js renderSettled) + list/flow views.
- [P3] Modal cold-load up to 6s spinner; render install string immediately.

## Prune
- Delete how-we-do-things.html (unlinked dup of codex.html).
- Remove/finish dead-end claim button.
- Demote Path A steps IV+V.
- Nav 7 links+search over Miller's 5; group Starless+Meta Reports.

## Text-bloat targets
- Badges hero 106->~50; validating note 110->1 line+disclosure; repo-register 95->~25; Path A 5->3 steps.

## Focus order
1 Fix broken contribute button + Door A primary. 2 Collapse Path A + unify verb. 3 Resolve dup claim button. 4 Name install entry + install row on profile cards. 5 Trim badges hero+note.
No locked visual tokens touched.
