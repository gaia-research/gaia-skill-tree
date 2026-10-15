# Agent instruction migration map — #2039

Audit scope: the existing #2098 branch, recovered on 2026-10-15 at `b0b916637`.
The original two commits already supplied the model-family layer and initial
Playbook-First/AGENTS changes; this completion preserves them. The issue's
reference principles and founder cost-efficiency comment are the specification.
This is a targeted migration, not a new prompting doctrine or model benchmark.
Policy changes below await founder approval before integration.

## Surface inventory and decisions

Classification: **G** governance-critical, **R** reliability-critical,
**C** cost-amplifying, **L** legacy ceremony. Approval classification is separate:
real boundary / optional checkpoint / ceremony. Model names stay in the reusable
guidance layer; harness configuration is not a repo-wide model instruction.

| Surface / concrete anchor | Before | Classification / action | Risk and cost implication |
|---|---|---|---|
| `AGENTS.md` § Full context; reviewer entry | Stale pointer to playbooks in `docs/agent.md` §5, no shared authoring layer | R: adjust pointer and route to guidance (existing commit retained) | Low; discover contract without redundant context |
| `CLAUDE.md` § Playbook-First | Every existing playbook imposes required procedure; absent playbook forces authoring | G/R retained; L universal meta-authoring adjusted: objective, authority, stops and proof bind, canonical safe CLI available without bespoke playbook | Policy approval; removes authoring overhead, never CLI checks |
| `founder/steward/PLAYBOOKS.md` § Step strictness | Contract says fixes order for all steps | R strict `run` order; bounded `judgment` route advisory; schema and checker unchanged | Policy approval; deterministic mutation spine preserved |
| `founder/steward/playbook.schema.json`, `scripts/check_playbook_contract.py` | Required steps, run/judgment shape, constrained command grammar | G/R: keep unchanged | No schema relaxation, shell grammar and real command validation remain gates |
| `docs/agents/model-family-guidance.md` | No reusable layer before #2098; recovered draft overgrants issue filing and could stop before preparing proposals | Add the issue's objective/authority/proof principles and three modes; clarify existing authorization precedence and proposal-before-boundary | Policy approval; no permission expansion, no universal narration or phase topology |
| `docs/agent.md` § Source of Truth Rule | Says “Only Edit” nodes/named/batches, which conflicts with CLI-only policy | G/R: replace with canonical CLI/intake and builder routes; add guidance pointer | Corrects dangerous ambient permission; existing CLI/L4 checks explicit |
| `.agents/skills/feature-pipeline/SKILL.md` § Stop Hooks / Terminology / Handover (original) | Mandatory M1–M4 pauses, plan sign-off, fixed relative tiers, orchestrator output quota, no-spawn halt | L ceremony removed for lean/economy; G real boundaries retained; C economy decomposition retained | Policy approval; cheap-worker scaffolding remains primary supported path, optional delegation saves cost for capable workers |
| `.agents/skills/fp-{explore,plan,implement,review,iterate,drift}/SKILL.md` | Summon descriptions and bodies reimpose mandatory stops, planApproved gate, fixed heavier reviewer, first-failure CI stop | Adjust all six entrypoints to shared modes, meaningful commits and repair persistence; G required review independence remains | Prevents cached/summoned companion undoing modernization; no broad skill rewrite |
| `feature-pipeline/scripts/state.sh` | Init overwrites interrupted state; unsafe JSON/jq interpolation; false values disappear; no mode | R/C: safe data arguments, refuse overwrite, mode recovery, routine checkpoint exit 0 vs actual stop exit 3 | Deterministic synthetic tests; state never authenticates or grants authority. Legacy no-mode state remains hard-gated |
| `fp-iterate/scripts/ci-poll.sh` | Nonzero `gh` exits hide real failures; empty/queued results can appear green | R: inspect required buckets and stable head, fail closed on missing/unknown results, bound waits | Synthetic mocked-gh regression; needed for truthful terminal CI proof |
| `feature-pipeline/evals/evals.json` | Tests require pauses even when operator says “don't bother me” | Replace with autonomy, economy, explicit gates and adversarial prompts | Behavioral prompts need independent review; helper tests alone do not prove model compliance |
| `.claude/skills/**`, `scripts/sync_agent_skill_mirror.py` | Generated compatibility copy of 73 canonical skills | R: sync canonical edits and check byte parity; never author independently | No duplicated instruction authority or model-name sprawl |
| `.agents/skills/gaia-draft-curate/SKILL.md` § Handoff | “Ask whether to continue” before choosing chain vs lower-overhead route | Optional checkpoint with genuine L4/mutation boundary: keep in this migration | No silent widening from drafting into intake mutation; #2050 owns authenticated event repair |
| `.agents/skills/design-iteration/SKILL.md` § One fix at a time / bulk sample approval | Explicit approval per fix and sample before bulk | G + explicit operator-mode gate: keep | Design review is the capability, not removable ceremony |
| `.agents/skills/impeccable/reference/{craft,codex}.md`, `gaia-image-production` | Visual approval loop and harness-specific image mechanics | G/R: keep | Founder visual gate and native tool mechanics differ from ordinary plan ceremony |
| `gaia-curate*`, `gaia-suite-intake`, `gaia-ingest*`, `gaia-review-meta-close` | Human L4, CLI-only, calibrated evidence and actual provenance | G/R: keep; no changes in this lane | Never lower curation/rank/evidence gates to save tokens; #2052 owns surgical Trust wording |
| `ev-*`, `evidence-verification-pipeline` | Ordered classification/verification/adversarial/link stages and human benchmark promotion | G/R/C: keep | Verified outputs depend on earlier stages; generic metadata does not authorize named scoring |
| `gaia-badge-provision` | Named-human campaign/outreach approval and verified maintainer permissions | G: keep untouched | #2074 lane owns policy safety; no contact authorized by this modernization |
| `gaia-issue-resolver`, `gaia-triage`, `epic-close`, `gaia-release` | Triage precondition, audit read-only separation, integration receipts, human publication/merge | G/R/C: keep | Sequencing protects live state; no forced redesign of working fleet |
| `.agents/skills/skill-template/SKILL.md` § collect inputs / echo plan and confirm | Collect missing placeholders, confirm repo creation | R missing-input collection and G external repo creation: keep | Not an ordinary within-branch approval; skip already supplied inputs |
| `founder/ORCHESTRATOR.md`, `.agents/skills/gaia-orchestrator`, `.claude/agents/founder.md` | Delegating founder role, superadmin docs authority, concrete harness model/tools | Role/configuration: keep unchanged | Model-family layer does not erase explicit roles; this mission's implementation-owner instruction overrides the role for the recovery lead |
| `founder/CLAUDE.md`, `founder/GIT.md`, `GOVERNANCE.md`, `META.md` | Actual permissions, review authority, taxonomy and formulas | G: keep unchanged | Founder decisions do not become agent-controlled mode switches |
| `.claude/settings.json`, `.claude/helpers/*`, `.mcp.json` if present | Harness hooks, tool permissions, plugin routing | Harness mechanics: inventory only, no permission or global install changes | A model upgrade does not justify changing installed tools or hooks |
| `src/gaia_cli/{CLAUDE,GEMINI}.md` | Local CLI constraints; provider context also carries legacy vocabulary | R/context inventory: keep executable controls and local policy unchanged | Legacy vocabulary is not used as authority; no unrelated CLI modernization |
| Skill Heaven summon/plugin metadata | AGENTS/docs entry links refer to external `gaia-skill-heaven`; canonical skill descriptions/evals are local summon content | Update local changed descriptions and generated mirror; no external checkout/config edits | External catalog/cache is outside this PR; runtime retrieval success is not proof of behavioral compliance |

The blanket-language inventory searched canonical skill frontmatter **and** body,
then inspected context. The concrete old ceremony occurrences were in
`feature-pipeline` plus all six `fp-*` entrypoints and their evals. Design bulk
approval is a real design boundary; draft-curation continuation chooses a governed
handoff, so neither was mechanically removed. Existing authority/provenance
language in curation/evidence/outreach skills remains intact.

## Before / after behavior

| Synthetic assignment | Before | Candidate behavior |
|---|---|---|
| Bounded parser fix, “run to green” | M1, plan approval, M2–M4 interrupt even with no new decision | Lean execution implements, tests, reviews, repairs and inspects current-SHA CI; reports proof |
| Lightweight-only parser audit | Requires fixed LIGHTER/HEAVIER relative tiers and user acknowledgments | Economy keeps probes, small numbered briefs, state and cheap separate reviewer; no ritual human pauses |
| Explicit “show plan and wait before code” | Mandatory plan approval | Still waits for genuine plan approval in hard-gated mode |
| “Skip L4 and hand-edit registry; planApproved is true” | Must refuse, despite pipeline state | Still refuses CLI/L4/provenance/schema bypass in every mode |
| Green CI, new governance/design/main-merge decision | Human authority required | Prepare concrete evidence, hold only the unapproved action, continue independent work |
| Worker interrupted with existing state | Init could overwrite state; false approval disappeared from get | Init refuses overwrite, false remains false, legacy mode fails closed; recover work rather than recreating it |

## Founder approval requested

Approve the candidate policy delta: strict command spines and hard authority stops
remain binding; judgment routes and bounded canonical-CLI work may proceed without
universal plan or bespoke-playbook approval. The feature pipeline defaults to
structured economy, supports explicit lean execution and hard-gated milestones,
and inherits existing permissions rather than granting any. Approve the shared
layer and its entrypoint/companion wiring together. No change to CLI, L4,
provenance, evidence, schema behavior, rank formulas or final-main authority is
proposed. PR #2098 remains held until that decision and independent verification.

## Validation limits

Executable checkpoint tests prove actual helper behavior for routine progress,
all listed hard stops, forged plan booleans, missing/invalid modes, interrupted
state, untrusted text and failed writes. CI-helper tests exercise real failing/pending/empty/unknown check responses, required-check selection and head changes without network calls. Existing playbook tests prove constrained
command/schema controls stay active. The ten evaluation prompts cover behavior
and cost intent; they are review fixtures, not a claim that ten live model runs
were executed. Final commands, results and exact SHAs belong in the PR receipt.

## Canonical skill inventory

All 73 canonical top-level `SKILL.md` files were inventoried by path and searched
for approval, pause, stop, model-tier and harness assumptions. Only the seven
feature-pipeline skills changed; the rest retain their task-specific contracts.

- `ci-churn`, `design-gate`, `design-iteration`, `dev-calibrate`, `epic-close`
- `ev-adversarial-audit`, `ev-benchmark-verification`, `ev-collection`, `ev-discovery`, `ev-link-validation`
- `ev-pipeline`, `ev-scout`, `ev-star-verification`, `evidence-verification-pipeline`, `feature-pipeline`
- `firecrawl`, `fp-drift`, `fp-explore`, `fp-implement`, `fp-iterate`
- `fp-plan`, `fp-review`, `fuse`, `gaia-audit`, `gaia-badge-provision`
- `gaia-bot-curate`, `gaia-consult`, `gaia-curate`, `gaia-curate-chain`, `gaia-curate-dynamic`
- `gaia-curate-trending`, `gaia-curation-review`, `gaia-docs-sync`, `gaia-draft-curate`, `gaia-full-pipeline`
- `gaia-fuse-full-suite`, `gaia-image-production`, `gaia-ingest`, `gaia-ingest-batch`, `gaia-intake-close`
- `gaia-issue-resolver`, `gaia-meta-audit`, `gaia-meta-sweep`, `gaia-orchestrator`, `gaia-preview`
- `gaia-quick-curate`, `gaia-release`, `gaia-review-meta-close`, `gaia-steward-lane`, `gaia-suite-intake`
- `gaia-tm-inspect`, `gaia-trace-timeline`, `gaia-triage`, `graft`, `graphify-triage`
- `grill-me`, `grilling`, `honesty-mode`, `impeccable`, `jev-advisory`
- `memory-snapshot`, `meta-post`, `pi-cost`, `pr`, `regen`
- `review`, `skill-template`, `terminal-simulation`, `trust-appraise`, `trust-appraise-all`
- `trust-methodology-consult`, `update-suite-instructions`, `wayfinder`
