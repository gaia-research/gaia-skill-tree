# L4 Marketplace Crawl — Handover for Founder Review

**Branch:** `review/intake/marketplace-crawl`
**Source crawl:** 8 clusters (SkillsMP, SkillKit, MCP.so, Smithery, npm, + source repos obra/superpowers, google-deepmind/science-skills, NousResearch/hermes-agent, intelligentcode-ai/skills, sickn33/antigravity-awesome-skills)
**Ledger used for attribution:** sickn33/agentic-awesome-skills `docs/sources/sources.md` (fetched via gh API)

## Provenance & honesty notes
- 1084 skills passed the L4 gate (real SKILL.md with valid `name`+`description` + verified `blob/` URL).
- **Attribution is ledger-first**: 88 skills matched the sickn33 sources ledger (authoritative upstream owner + license + URL). The remaining 996 are attributed to the real git commit author and flagged `[git-author]` — the ledger does NOT cover them, so those are inferred, not verified.
- **IDs are canonical kebab-case capability slugs** (distinct from `name`), matching gaia.json convention. They are NOT the repo dir and NOT the literal skill name.
- **Excluded**: VS Code Marketplace & HuggingFace (not skill marketplaces; 0 L4). obra/deepmind are contributor repos, not marketplaces.
- **Grade is NOT asserted** anywhere — evidence signals (commits/contributors/stars + blob URL) are carried so the verifier computes Trust Magnitude at promotion time.
- This is a plan-only inventory. No skills were promoted to registry/nodes/. Promotion requires the `gaia dev add` curate flow on a review/meta/ branch.


# L4 — Faithful Skill Inventory (ledger-attributed)

_Gen: plan-only crawl. 1084 legit skills, each with a real SKILL.md (valid `name`+`description`) and verified blob URL._

- **Attribution:** 88 skills matched to the sickn33 sources ledger (authoritative upstream owner); 996 attributed to the real git commit author (flagged `[git-author]` — not in the ledger).

- **ID** = canonical kebab-case capability slug (distinct from `name`); matches gaia.json ID convention. **Not** the repo dir, not the literal name.

- **VS Code Marketplace & HuggingFace** excluded (not skill marketplaces; 0 L4).

- **obra/superpowers & google-deepmind/science-skills** are contributor repos, not marketplaces — listed with real git authors.


## NousResearch/hermes-agent — 14 skills

| canonical id | name | attributed to | via | license | upstream / blob | cites |
|---|---|---|---|---|---|---|
| `agentmail-teknium1` | agentmail | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/email/agentmail/SKILL.md | agentmail-to/agentmail-mcp |
| `antigravity-cli` | antigravity-cli | namredips | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/autonomous-ai-agents/antigravity-cli/SKILL.md | — |
| `apple-notes` | apple-notes | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/apple/apple-notes/SKILL.md | — |
| `baoyu-article-illustrator` | baoyu-article-illustrator | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/creative/baoyu-article-illustrator/SKILL.md | JimLiu/baoyu-skills |
| `code-wiki` | code-wiki | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/software-development/code-wiki/SKILL.md | — |
| `codebase-inspection` | codebase-inspection | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/github/codebase-inspection/SKILL.md | — |
| `dogfood` | dogfood | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/dogfood/SKILL.md | — |
| `gif-search` | gif-search | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/media/gif-search/SKILL.md | — |
| `huggingface-accelerate` | huggingface-accelerate | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/optional-skills/mlops/accelerate/SKILL.md | huggingface/accelerate |
| `jupyter-live-kernel` | jupyter-live-kernel | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/data-science/jupyter-live-kernel/SKILL.md | hamelsmu/hamelnb.git |
| `obsidian` | obsidian | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/note-taking/obsidian/SKILL.md | — |
| `openhue` | openhue | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/smart-home/openhue/SKILL.md | openhue/openhue-cli |
| `xurl` | xurl | helix4u | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/social-media/xurl/SKILL.md | openclaw/openclaw, xdevplatform/xurl |
| `yuanbao` | yuanbao | teknium1 | git-author | — | https://github.com/NousResearch/hermes-agent/blob/main/skills/yuanbao/SKILL.md | — |

## google-deepmind/science-skills — 38 skills

| canonical id | name | attributed to | via | license | upstream / blob | cites |
|---|---|---|---|---|---|---|
| `alphafold-database-fetch-and-analyze` | alphafold-database-fetch-and-analyze | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/alphafold_database_fetch_and_analyze/SKILL.md | — |
| `alphagenome-single-variant-analysis` | alphagenome-single-variant-analysis | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/alphagenome_single_variant_analysis/SKILL.md | — |
| `chembl-database` | chembl-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md | — |
| `clinical-trials-database` | clinical-trials-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/clinical_trials_database/SKILL.md | — |
| `clinvar-database` | clinvar-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/clinvar_database/SKILL.md | — |
| `credentials` | credentials | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/credentials/SKILL.md | — |
| `dbsnp-database` | dbsnp-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/dbsnp_database/SKILL.md | — |
| `embl-ebi-ols` | embl-ebi-ols | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/embl_ebi_ols/SKILL.md | — |
| `encode-ccres-database` | encode-ccres-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/encode_ccres_database/SKILL.md | — |
| `ensembl-database` | ensembl-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/ensembl_database/SKILL.md | Ensembl/ensembl-rest |
| `foldseek-structural-search` | foldseek-structural-search | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/foldseek_structural_search/SKILL.md | steineggerlab/foldseek |
| `gnomad-database` | gnomad-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md | — |
| `gtex-database` | gtex-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/gtex_database/SKILL.md | — |
| `human-protein-atlas-database` | human-protein-atlas-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/human_protein_atlas_database/SKILL.md | — |
| `interpro-database` | interpro-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/interpro_database/SKILL.md | — |
| `jaspar-database` | jaspar-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md | — |
| `literature-search-arxiv` | literature-search-arxiv | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md | — |
| `literature-search-biorxiv` | literature-search-biorxiv | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_biorxiv/SKILL.md | — |
| `literature-search-europepmc` | literature-search-europepmc | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_europepmc/SKILL.md | — |
| `literature-search-openalex` | literature-search-openalex | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md | — |
| `ncbi-sequence-fetch` | ncbi-sequence-fetch | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/ncbi_sequence_fetch/SKILL.md | — |
| `openfda-database` | openfda-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/openfda_database/SKILL.md | — |
| `opentargets-database` | opentargets-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/opentargets_database/SKILL.md | — |
| `pdb-database` | pdb-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/pdb_database/SKILL.md | — |
| `predictingthepast` | predictingthepast | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/predictingthepast/SKILL.md | google-deepmind/predictingthepast, sdam-au/EDCS |
| `protein-sequence-msa` | protein-sequence-msa | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_msa/SKILL.md | — |
| `protein-sequence-similarity-search` | protein-sequence-similarity-search | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_similarity_search/SKILL.md | — |
| `pubchem-database` | pubchem-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/pubchem_database/SKILL.md | — |
| `pubmed-database` | pubmed-database | K-Dense-AI/claude-scientific-skills | ledger | Compatible | https://github.com/K-Dense-AI/claude-scientific-skills | — |
| `pymol` | pymol | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md | — |
| `quickgo-database` | quickgo-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/quickgo_database/SKILL.md | — |
| `reactome-database` | reactome-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/reactome_database/SKILL.md | — |
| `string-database` | string-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md | — |
| `ucsc-conservation-and-tfbs` | ucsc-conservation-and-tfbs | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/ucsc_conservation_and_tfbs/SKILL.md | — |
| `unibind-database` | unibind-database | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md | — |
| `uniprot-database` | uniprot-database | K-Dense-AI/claude-scientific-skills | ledger | Compatible | https://github.com/K-Dense-AI/claude-scientific-skills | — |
| `uv` | uv | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md | — |
| `workflow-skill-creator` | workflow-skill-creator | artsobolev | git-author | — | https://github.com/google-deepmind/science-skills/blob/main/skills/workflow_skill_creator/SKILL.md | — |

## intelligentcode-ai/skills — 44 skills

| canonical id | name | attributed to | via | license | upstream / blob | cites |
|---|---|---|---|---|---|---|
| `agent-browser` | agent-browser | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/agent-browser/SKILL.md | — |
| `ai-engineer-ksamasch` | ai-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/ai-engineer/SKILL.md | — |
| `architect` | architect | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/architect/SKILL.md | — |
| `autonomy` | autonomy | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/autonomy/SKILL.md | — |
| `backend-tester` | backend-tester | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/backend-tester/SKILL.md | — |
| `best-practices` | best-practices | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/best-practices/SKILL.md | — |
| `branch-protection` | branch-protection | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/branch-protection/SKILL.md | — |
| `commit-pr` | commit-pr | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/commit-pr/SKILL.md | — |
| `create-work-items` | create-work-items | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/create-work-items/SKILL.md | — |
| `database-engineer` | database-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md | — |
| `developer` | developer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/developer/SKILL.md | — |
| `devops-engineer` | devops-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md | — |
| `file-placement` | file-placement | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/file-placement/SKILL.md | — |
| `git-privacy` | git-privacy | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/git-privacy/SKILL.md | — |
| `github-issues-planning` | github-issues-planning | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/github-issues-planning/SKILL.md | — |
| `github-state-tracker` | github-state-tracker | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/github-state-tracker/SKILL.md | — |
| `ica-bootstrap` | ica-bootstrap | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/ica-bootstrap/SKILL.md | intelligentcode-ai/skills.git |
| `ica-cli` | ica-cli | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/ica-cli/SKILL.md | intelligentcode-ai/skills.git |
| `ica-get-setting` | ica-get-setting | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/ica-get-setting/SKILL.md | — |
| `infrastructure-protection` | infrastructure-protection | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/infrastructure-protection/SKILL.md | — |
| `mcp-client` | mcp-client | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md | — |
| `mcp-common` | mcp-common | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-common/SKILL.md | — |
| `mcp-config` | mcp-config | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-config/SKILL.md | — |
| `mcp-proxy` | mcp-proxy | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-proxy/SKILL.md | — |
| `memory` | memory | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/memory/SKILL.md | — |
| `plan-work-items` | plan-work-items | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/plan-work-items/SKILL.md | — |
| `pm` | pm | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/pm/SKILL.md | — |
| `pr-automerge` | pr-automerge | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/pr-automerge/SKILL.md | — |
| `process` | process | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/process/SKILL.md | — |
| `qa-engineer` | qa-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/qa-engineer/SKILL.md | — |
| `release` | release | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md | OWNER/REPO |
| `requirements-engineer` | requirements-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/requirements-engineer/SKILL.md | — |
| `reviewer` | reviewer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/reviewer/SKILL.md | — |
| `run-work-items` | run-work-items | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/run-work-items/SKILL.md | — |
| `security-engineer` | security-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md | — |
| `skill-creator` | skill-creator | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/skill-creator/SKILL.md | — |
| `skill-writer` | skill-writer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/skill-writer/SKILL.md | — |
| `suggest` | suggest | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/suggest/SKILL.md | — |
| `system-engineer` | system-engineer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/system-engineer/SKILL.md | — |
| `tdd` | tdd | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/tdd/SKILL.md | — |
| `thinking` | thinking | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/thinking/SKILL.md | — |
| `user-tester` | user-tester | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md | — |
| `validate` | validate | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/validate/SKILL.md | — |
| `web-designer` | web-designer | ksamaschke | git-author | — | https://github.com/intelligentcode-ai/skills/blob/main/skills/web-designer/SKILL.md | — |

## obra/superpowers — 2 skills

| canonical id | name | attributed to | via | license | upstream / blob | cites |
|---|---|---|---|---|---|---|
| `using-superpowers` | using-superpowers | obra | git-author | — | https://github.com/obra/superpowers/blob/main/skills/using-superpowers/SKILL.md | — |
| `writing-skills` | writing-skills | obra | git-author | — | https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md | — |

## sickn33/antigravity-awesome-skills — 986 skills

| canonical id | name | attributed to | via | license | upstream / blob | cites |
|---|---|---|---|---|---|---|
| `ab-test-setup` | ab-test-setup | specterslient95-lgtm | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ab-test-setup/SKILL.md | — |
| `ab-testing` | ab-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ab-testing/SKILL.md | coreyhaines31/marketingskills |
| `acceptance-orchestrator` | acceptance-orchestrator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/acceptance-orchestrator/SKILL.md | — |
| `accessibility-compliance-accessibility-audit` | accessibility-compliance-accessibility-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accessibility-compliance-accessibility-audit/SKILL.md | — |
| `accesslint-audit` | accesslint-audit | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accesslint-audit/SKILL.md | AccessLint/skills |
| `accesslint-diff` | accesslint-diff | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accesslint-diff/SKILL.md | AccessLint/skills |
| `accesslint-scan` | accesslint-scan | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accesslint-scan/SKILL.md | AccessLint/skills |
| `accint-commitments` | accint-commitments | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accint-commitments/SKILL.md | maxbaluev/accreted-intelligence |
| `accint-frames` | accint-frames | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accint-frames/SKILL.md | maxbaluev/accreted-intelligence |
| `accint-solve` | accint-solve | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/accint-solve/SKILL.md | maxbaluev/accreted-intelligence |
| `active-directory-attacks` | active-directory-attacks | HackTricks | ledger | MIT / CC-BY-SA | https://book.hacktricks.xyz/ | — |
| `activecampaign-automation` | activecampaign-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/activecampaign-automation/SKILL.md | — |
| `ad-creative` | ad-creative | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ad-creative/SKILL.md | coreyhaines31/marketingskills |
| `add-app-clip` | add-app-clip | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/add-app-clip/SKILL.md | EvanBacon/expo-apple-targets, expo/skills |
| `address-github-comments` | address-github-comments | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/address-github-comments/SKILL.md | — |
| `adhx` | adhx | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/adhx/SKILL.md | itsmemeworks/adhx |
| `advanced-evaluation` | advanced-evaluation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/advanced-evaluation/SKILL.md | — |
| `advogado-criminal` | advogado-criminal | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/advogado-criminal/SKILL.md | — |
| `advogado-especialista` | advogado-especialista | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/advogado-especialista/SKILL.md | — |
| `aegisops-ai` | aegisops-ai | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aegisops-ai/SKILL.md | Champbreed/AegisOps-AI, Champbreed/AegisOps-AI.git |
| `agent-creator` | agent-creator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-creator/SKILL.md | — |
| `agent-evaluation` | agent-evaluation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-evaluation/SKILL.md | — |
| `agent-framework-azure-ai-py` | agent-framework-azure-ai-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-framework-azure-ai-py/SKILL.md | — |
| `agent-manager-skill` | agent-manager-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-manager-skill/SKILL.md | fractalmind-ai/agent-manager-skill.git |
| `agent-memory` | agent-memory | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-memory/SKILL.md | webzler/agentMemory |
| `agent-memory-mcp` | agent-memory-mcp | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-memory-mcp/SKILL.md | webzler/agentMemory.git |
| `agent-memory-systems` | agent-memory-systems | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-memory-systems/SKILL.md | — |
| `agent-orchestration-improve-agent` | agent-orchestration-improve-agent | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-orchestration-improve-agent/SKILL.md | — |
| `agent-orchestration-multi-agent-optimize` | agent-orchestration-multi-agent-optimize | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-orchestration-multi-agent-optimize/SKILL.md | — |
| `agent-orchestrator` | agent-orchestrator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-orchestrator/SKILL.md | — |
| `agent-self-scheduling` | agent-self-scheduling | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-self-scheduling/SKILL.md | davidondrej/skills |
| `agent-squad` | agent-squad | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-squad/SKILL.md | — |
| `agent-tool-builder` | agent-tool-builder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agent-tool-builder/SKILL.md | — |
| `agentflow` | agentflow | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agentflow/SKILL.md | UrRhb/agentflow, UrRhb/agentflow.git |
| `agentfolio` | agentfolio | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agentfolio/SKILL.md | — |
| `agentic-actions-auditor` | agentic-actions-auditor | trailofbits/skills | ledger | Compatible | https://github.com/trailofbits/skills | owner/repo |
| `agentmail-sickn33` | agentmail | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agentmail/SKILL.md | — |
| `agentphone` | agentphone | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agentphone/SKILL.md | — |
| `agents-md` | agents-md | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agents-md/SKILL.md | — |
| `agents-v2-py` | agents-v2-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agents-v2-py/SKILL.md | — |
| `agenttrace-session-audit` | agenttrace-session-audit | luoyuctl | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/agenttrace-session-audit/SKILL.md | luoyuctl/agenttrace |
| `ai-agent-development` | ai-agent-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-agent-development/SKILL.md | — |
| `ai-agents-architect` | ai-agents-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-agents-architect/SKILL.md | — |
| `ai-analyzer` | ai-analyzer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-analyzer/SKILL.md | — |
| `ai-dev-jobs-mcp` | ai-dev-jobs-mcp | unitedideas | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-dev-jobs-mcp/SKILL.md | — |
| `ai-engineer-sickn33` | ai-engineer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-engineer/SKILL.md | — |
| `ai-engineering-toolkit` | ai-engineering-toolkit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-engineering-toolkit/SKILL.md | viliawang-pm/ai-engineering-toolkit, viliawang-pm/ai-engineering-toolkit.git |
| `ai-loop` | ai-loop | PzocikErwin | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-loop/SKILL.md | — |
| `ai-md` | ai-md | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-md/SKILL.md | — |
| `ai-ml` | ai-ml | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-ml/SKILL.md | — |
| `ai-native-cli` | ai-native-cli | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-native-cli/SKILL.md | ChaosRealmsAI/agent-cli-spec |
| `ai-product` | ai-product | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-product/SKILL.md | — |
| `ai-seo` | ai-seo | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-seo/SKILL.md | coreyhaines31/marketingskills |
| `ai-studio-image` | ai-studio-image | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-studio-image/SKILL.md | — |
| `ai-wrapper-product` | ai-wrapper-product | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ai-wrapper-product/SKILL.md | — |
| `airflow-dag-patterns` | airflow-dag-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/airflow-dag-patterns/SKILL.md | — |
| `airtable-automation` | airtable-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/airtable-automation/SKILL.md | — |
| `akf-trust-metadata` | akf-trust-metadata | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/akf-trust-metadata/SKILL.md | HMAKT99/AKF |
| `algolia-search` | algolia-search | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/algolia-search/SKILL.md | — |
| `algorithmic-art` | algorithmic-art | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/algorithmic-art/SKILL.md | — |
| `ally-health` | claude-ally-health | huifer | ledger | Compatible | https://github.com/huifer/Claude-Ally-Health | huifer/Claude-Ally-Health |
| `alpha-vantage` | alpha-vantage | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/alpha-vantage/SKILL.md | — |
| `alternatives-pages` | alternatives-pages | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/alternatives-pages/SKILL.md | jonathimer/devmarketing-skills |
| `amazon-alexa` | amazon-alexa | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/amazon-alexa/SKILL.md | alexa/alexa-skills-kit-sdk-for-python |
| `amplitude-automation` | amplitude-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/amplitude-automation/SKILL.md | — |
| `analytics` | analytics | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/analytics/SKILL.md | coreyhaines31/marketingskills |
| `analytics-product` | analytics-product | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/analytics-product/SKILL.md | — |
| `analytics-tracking` | analytics-tracking | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/analytics-tracking/SKILL.md | — |
| `analyze-project` | analyze-project | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/analyze-project/SKILL.md | — |
| `andrej-karpathy` | andrej-karpathy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/andrej-karpathy/SKILL.md | multica-ai/andrej-karpathy-skills |
| `android-cli` | android-cli | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/android-cli/SKILL.md | — |
| `android-dev` | android-dev | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/android-dev/SKILL.md | — |
| `android-jetpack-compose-expert` | android-jetpack-compose-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/android-jetpack-compose-expert/SKILL.md | — |
| `android-ui-journey-testing` | android-ui-journey-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/android-ui-journey-testing/SKILL.md | — |
| `android-ui-verification` | android_ui_verification | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/android_ui_verification/SKILL.md | — |
| `angular` | angular | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/angular/SKILL.md | — |
| `angular-best-practices` | angular-best-practices | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/angular-best-practices/SKILL.md | — |
| `angular-migration` | angular-migration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/angular-migration/SKILL.md | — |
| `angular-state-management` | angular-state-management | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/angular-state-management/SKILL.md | — |
| `angular-ui-patterns` | angular-ui-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/angular-ui-patterns/SKILL.md | — |
| `animejs-animation` | animejs-animation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/animejs-animation/SKILL.md | — |
| `anti-deception` | anti-deception | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/anti-deception/SKILL.md | ejentum/ejentum-mcp |
| `anti-reversing-techniques` | anti-reversing-techniques | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/anti-reversing-techniques/SKILL.md | — |
| `anti-sleep` | anti-sleep | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/anti-sleep/SKILL.md | davidondrej/skills |
| `anti-sycophancy` | anti-sycophancy | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/anti-sycophancy/SKILL.md | mskadu/opencode-agent-skills |
| `antigravity-agent-manager` | antigravity-agent-manager | PzocikErwin | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/antigravity-agent-manager/SKILL.md | — |
| `antigravity-design-expert` | antigravity-design-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/antigravity-design-expert/SKILL.md | — |
| `antigravity-skill-orchestrator` | antigravity-skill-orchestrator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/antigravity-skill-orchestrator/SKILL.md | — |
| `antigravity-workflows` | antigravity-workflows | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/antigravity-workflows/SKILL.md | — |
| `aomi-transact` | aomi-transact | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aomi-transact/SKILL.md | aomi-labs/skills |
| `api` | claude-api | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-api/SKILL.md | anthropics/skills |
| `api-analyzer` | api-analyzer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-analyzer/SKILL.md | LambdaTest/agent-skills |
| `api-and-interface-design` | api-and-interface-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-and-interface-design/SKILL.md | addyosmani/agent-skills |
| `api-design-principles` | api-design-principles | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-design-principles/SKILL.md | — |
| `api-designer` | api-designer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-designer/SKILL.md | LambdaTest/agent-skills |
| `api-dev` | gemini-api-dev | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gemini-api-dev/SKILL.md | google-gemini/gemini-skills |
| `api-documentation` | api-documentation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-documentation/SKILL.md | — |
| `api-documentation-generator` | api-documentation-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-documentation-generator/SKILL.md | — |
| `api-documenter` | api-documenter | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-documenter/SKILL.md | — |
| `api-endpoint-builder` | api-endpoint-builder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-endpoint-builder/SKILL.md | — |
| `api-fuzzing-bug-bounty` | api-fuzzing-bug-bounty | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-fuzzing-bug-bounty/SKILL.md | API-Security/APIKit, BBVA/apicheck |
| `api-integration-sickn33` | api-integration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-integration/SKILL.md | LambdaTest/agent-skills |
| `api-integration-sickn33-2` | gemini-api-integration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gemini-api-integration/SKILL.md | — |
| `api-onboarding` | api-onboarding | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-onboarding/SKILL.md | jonathimer/devmarketing-skills |
| `api-patterns` | api-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-patterns/SKILL.md | — |
| `api-sdk-generator` | api-sdk-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-sdk-generator/SKILL.md | LambdaTest/agent-skills |
| `api-security-best-practices` | api-security-best-practices | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-security-best-practices/SKILL.md | shieldfy/API-Security-Checklist |
| `api-security-testing` | api-security-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-security-testing/SKILL.md | — |
| `api-testing-observability-api-mock` | api-testing-observability-api-mock | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/api-testing-observability-api-mock/SKILL.md | — |
| `apify-actor-development` | apify-actor-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-actor-development/SKILL.md | — |
| `apify-actorization` | apify-actorization | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-actorization/SKILL.md | — |
| `apify-audience-analysis` | apify-audience-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-audience-analysis/SKILL.md | — |
| `apify-brand-reputation-monitoring` | apify-brand-reputation-monitoring | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-brand-reputation-monitoring/SKILL.md | — |
| `apify-competitor-intelligence` | apify-competitor-intelligence | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-competitor-intelligence/SKILL.md | — |
| `apify-content-analytics` | apify-content-analytics | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-content-analytics/SKILL.md | — |
| `apify-ecommerce` | apify-ecommerce | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-ecommerce/SKILL.md | — |
| `apify-influencer-discovery` | apify-influencer-discovery | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-influencer-discovery/SKILL.md | — |
| `apify-lead-generation` | apify-lead-generation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-lead-generation/SKILL.md | — |
| `apify-market-research` | apify-market-research | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-market-research/SKILL.md | — |
| `apify-trend-analysis` | apify-trend-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-trend-analysis/SKILL.md | — |
| `apify-ultimate-scraper` | apify-ultimate-scraper | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apify-ultimate-scraper/SKILL.md | — |
| `app-builder` | app-builder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/app-builder/SKILL.md | — |
| `app-store-changelog` | app-store-changelog | Dimillian/Skills | ledger | MIT | https://github.com/Dimillian/Skills | — |
| `app-store-optimization` | app-store-optimization | skiffer | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/app-store-optimization/SKILL.md | — |
| `appdeploy` | appdeploy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/appdeploy/SKILL.md | — |
| `appium-skill` | appium-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/appium-skill/SKILL.md | LambdaTest/agent-skills |
| `apple-notes-search` | apple-notes-search | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/apple-notes-search/SKILL.md | RafalWilinski/mcp-apple-notes, connerkward/mcp-apple-notes |
| `application-performance-performance-optimization` | application-performance-performance-optimization | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/application-performance-performance-optimization/SKILL.md | — |
| `applicationinsights-web-ts` | applicationinsights-web-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/applicationinsights-web-ts/SKILL.md | microsoft/ApplicationInsights-JS, microsoft/skills |
| `architect-review` | architect-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/architect-review/SKILL.md | — |
| `architecture` | architecture | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/architecture/SKILL.md | — |
| `architecture-decision-records` | architecture-decision-records | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/architecture-decision-records/SKILL.md | npryce/adr-tools |
| `architecture-patterns` | architecture-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/architecture-patterns/SKILL.md | — |
| `arm-cortex-expert` | arm-cortex-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/arm-cortex-expert/SKILL.md | — |
| `arrowspace` | arrowspace | genefold-ai | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/arrowspace/SKILL.md | Genefold/arrowspace-skills |
| `article-illustrations` | article-illustrations | vssinghh | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/article-illustrations/SKILL.md | vipin-si/article-illustrations |
| `asana-automation` | asana-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/asana-automation/SKILL.md | — |
| `ask` | ask-copilot | cshara1 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ask-copilot/SKILL.md | — |
| `ask-matt` | ask-matt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ask-matt/SKILL.md | mattpocock/skills |
| `ask-questions-if-underspecified` | ask-questions-if-underspecified | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ask-questions-if-underspecified/SKILL.md | — |
| `astro` | astro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/astro/SKILL.md | — |
| `astropy` | astropy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/astropy/SKILL.md | astropy/astropy |
| `async-python-patterns` | async-python-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/async-python-patterns/SKILL.md | — |
| `atlas-contract` | atlas-contract | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/atlas-contract/SKILL.md | wede-wx/atlas |
| `atlas-ledger` | atlas-ledger | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/atlas-ledger/SKILL.md | wede-wx/atlas |
| `attack-tree-construction` | attack-tree-construction | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/attack-tree-construction/SKILL.md | — |
| `audio-transcriber` | audio-transcriber | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/audio-transcriber/SKILL.md | — |
| `audit-context-building` | audit-context-building | trailofbits/skills | ledger | Compatible | https://github.com/trailofbits/skills | — |
| `audit-skills` | audit-skills | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/audit-skills/SKILL.md | — |
| `auri-core` | auri-core | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/auri-core/SKILL.md | alexa/alexa-skills-kit-sdk-for-python |
| `auth-implementation-patterns` | auth-implementation-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/auth-implementation-patterns/SKILL.md | — |
| `automated-triage` | automated-triage | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/automated-triage/SKILL.md | monte-carlo-data/mc-agent-toolkit |
| `autonomous-agent-patterns` | autonomous-agent-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/autonomous-agent-patterns/SKILL.md | cline/cline, openai/codex |
| `autonomous-agents` | autonomous-agents | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/autonomous-agents/SKILL.md | — |
| `avalonia-layout-zafiro` | avalonia-layout-zafiro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/avalonia-layout-zafiro/SKILL.md | — |
| `avalonia-viewmodels-zafiro` | avalonia-viewmodels-zafiro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/avalonia-viewmodels-zafiro/SKILL.md | — |
| `avalonia-zafiro-development` | avalonia-zafiro-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/avalonia-zafiro-development/SKILL.md | — |
| `avoid-ai-writing` | avoid-ai-writing | conorbronsdon | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/avoid-ai-writing/SKILL.md | conorbronsdon/avoid-ai-writing |
| `awareness-stage-mapper` | awareness-stage-mapper | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/awareness-stage-mapper/SKILL.md | — |
| `aws-agentic-ai` | aws-agentic-ai | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-agentic-ai/SKILL.md | zxkane/aws-skills |
| `aws-cdk-development` | aws-cdk-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-cdk-development/SKILL.md | cdklabs/cdk-nag, zxkane/aws-skills |
| `aws-cost-cleanup` | aws-cost-cleanup | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-cost-cleanup/SKILL.md | — |
| `aws-cost-operations` | aws-cost-operations | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-cost-operations/SKILL.md | zxkane/aws-skills |
| `aws-cost-optimizer` | aws-cost-optimizer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-cost-optimizer/SKILL.md | — |
| `aws-mcp-setup` | aws-mcp-setup | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-mcp-setup/SKILL.md | aws/mcp-proxy-for-aws, zxkane/aws-skills |
| `aws-penetration-testing` | aws-penetration-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-penetration-testing/SKILL.md | NetSPI/aws_consoler, RhinoSecurityLabs/pacu |
| `aws-serverless` | aws-serverless | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-serverless/SKILL.md | alexcasalboni/aws-lambda-power-tuning |
| `aws-serverless-eda` | aws-serverless-eda | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-serverless-eda/SKILL.md | zxkane/aws-skills |
| `aws-skills` | aws-skills | zxkane | ledger | Compatible | https://github.com/zxkane/aws-skills | zxkane/aws-skills |
| `aws-sst-development` | aws-sst-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/aws-sst-development/SKILL.md | zxkane/aws-skills |
| `awt-e2e-testing` | awt-e2e-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/awt-e2e-testing/SKILL.md | ksgisang/AI-Watch-Tester, ksgisang/awt-skill |
| `ax-extract-workflow` | ax-extract-workflow | Necmttn | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ax-extract-workflow/SKILL.md | Necmttn/ax |
| `axiom` | axiom | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/axiom/SKILL.md | — |
| `azd-deployment` | azd-deployment | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azd-deployment/SKILL.md | — |
| `azure-ai-agents-persistent-dotnet` | azure-ai-agents-persistent-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-agents-persistent-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-ai-agents-persistent-java` | azure-ai-agents-persistent-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-agents-persistent-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-ai-anomalydetector-java` | azure-ai-anomalydetector-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-anomalydetector-java/SKILL.md | — |
| `azure-ai-contentsafety-java` | azure-ai-contentsafety-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-contentsafety-java/SKILL.md | — |
| `azure-ai-contentsafety-py` | azure-ai-contentsafety-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-contentsafety-py/SKILL.md | — |
| `azure-ai-contentsafety-ts` | azure-ai-contentsafety-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-contentsafety-ts/SKILL.md | — |
| `azure-ai-contentunderstanding-py` | azure-ai-contentunderstanding-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-contentunderstanding-py/SKILL.md | — |
| `azure-ai-document-intelligence-dotnet` | azure-ai-document-intelligence-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-document-intelligence-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-ai-document-intelligence-ts` | azure-ai-document-intelligence-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-document-intelligence-ts/SKILL.md | — |
| `azure-ai-dotnet` | azure-ai-openai-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-openai-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-ai-formrecognizer-java` | azure-ai-formrecognizer-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-formrecognizer-java/SKILL.md | — |
| `azure-ai-language-conversations-py` | azure-ai-language-conversations-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-language-conversations-py/SKILL.md | microsoft/skills |
| `azure-ai-ml-py` | azure-ai-ml-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-ml-py/SKILL.md | — |
| `azure-ai-projects-dotnet` | azure-ai-projects-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-projects-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-ai-projects-java` | azure-ai-projects-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-projects-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-ai-projects-py` | azure-ai-projects-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-projects-py/SKILL.md | — |
| `azure-ai-projects-ts` | azure-ai-projects-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-projects-ts/SKILL.md | — |
| `azure-ai-textanalytics-py` | azure-ai-textanalytics-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-textanalytics-py/SKILL.md | — |
| `azure-ai-transcription-py` | azure-ai-transcription-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-transcription-py/SKILL.md | — |
| `azure-ai-translation-document-py` | azure-ai-translation-document-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-translation-document-py/SKILL.md | — |
| `azure-ai-translation-text-py` | azure-ai-translation-text-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-translation-text-py/SKILL.md | — |
| `azure-ai-translation-ts` | azure-ai-translation-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-translation-ts/SKILL.md | — |
| `azure-ai-vision-imageanalysis-java` | azure-ai-vision-imageanalysis-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-vision-imageanalysis-java/SKILL.md | — |
| `azure-ai-vision-imageanalysis-py` | azure-ai-vision-imageanalysis-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-vision-imageanalysis-py/SKILL.md | — |
| `azure-ai-voicelive-dotnet` | azure-ai-voicelive-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-voicelive-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-ai-voicelive-java` | azure-ai-voicelive-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-voicelive-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-ai-voicelive-py` | azure-ai-voicelive-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-voicelive-py/SKILL.md | — |
| `azure-ai-voicelive-ts` | azure-ai-voicelive-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-ai-voicelive-ts/SKILL.md | Azure/azure-sdk-for-js |
| `azure-appconfiguration-java` | azure-appconfiguration-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-appconfiguration-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-appconfiguration-py` | azure-appconfiguration-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-appconfiguration-py/SKILL.md | — |
| `azure-appconfiguration-ts` | azure-appconfiguration-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-appconfiguration-ts/SKILL.md | — |
| `azure-communication-callautomation-java` | azure-communication-callautomation-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-communication-callautomation-java/SKILL.md | — |
| `azure-communication-callingserver-java` | azure-communication-callingserver-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-communication-callingserver-java/SKILL.md | — |
| `azure-communication-chat-java` | azure-communication-chat-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-communication-chat-java/SKILL.md | — |
| `azure-communication-common-java` | azure-communication-common-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-communication-common-java/SKILL.md | — |
| `azure-communication-sms-java` | azure-communication-sms-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-communication-sms-java/SKILL.md | — |
| `azure-compute-batch-java` | azure-compute-batch-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-compute-batch-java/SKILL.md | Azure/azure-sdk-for-java, azure/azure-batch-samples |
| `azure-containerregistry-py` | azure-containerregistry-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-containerregistry-py/SKILL.md | — |
| `azure-cosmos-db-py` | azure-cosmos-db-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-cosmos-db-py/SKILL.md | — |
| `azure-cosmos-java` | azure-cosmos-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-cosmos-java/SKILL.md | Azure-Samples/azure-cosmos-java-sql-api-samples |
| `azure-cosmos-py` | azure-cosmos-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-cosmos-py/SKILL.md | — |
| `azure-cosmos-rust` | azure-cosmos-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-cosmos-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-cosmos-ts` | azure-cosmos-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-cosmos-ts/SKILL.md | — |
| `azure-data-tables-java` | azure-data-tables-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-data-tables-java/SKILL.md | — |
| `azure-data-tables-py` | azure-data-tables-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-data-tables-py/SKILL.md | — |
| `azure-eventgrid-dotnet` | azure-eventgrid-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventgrid-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-eventgrid-java` | azure-eventgrid-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventgrid-java/SKILL.md | — |
| `azure-eventgrid-py` | azure-eventgrid-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventgrid-py/SKILL.md | — |
| `azure-eventhub-dotnet` | azure-eventhub-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventhub-dotnet/SKILL.md | — |
| `azure-eventhub-java` | azure-eventhub-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventhub-java/SKILL.md | — |
| `azure-eventhub-py` | azure-eventhub-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventhub-py/SKILL.md | — |
| `azure-eventhub-rust` | azure-eventhub-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventhub-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-eventhub-ts` | azure-eventhub-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-eventhub-ts/SKILL.md | — |
| `azure-functions` | azure-functions | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-functions/SKILL.md | — |
| `azure-identity-dotnet` | azure-identity-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-identity-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-identity-java` | azure-identity-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-identity-java/SKILL.md | — |
| `azure-identity-py` | azure-identity-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-identity-py/SKILL.md | — |
| `azure-identity-rust` | azure-identity-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-identity-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-identity-ts` | azure-identity-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-identity-ts/SKILL.md | — |
| `azure-keyvault-certificates-rust` | azure-keyvault-certificates-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-certificates-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-keyvault-keys-rust` | azure-keyvault-keys-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-keys-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-keyvault-keys-ts` | azure-keyvault-keys-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-keys-ts/SKILL.md | — |
| `azure-keyvault-py` | azure-keyvault-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-py/SKILL.md | — |
| `azure-keyvault-secrets-rust` | azure-keyvault-secrets-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-secrets-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-keyvault-secrets-ts` | azure-keyvault-secrets-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-keyvault-secrets-ts/SKILL.md | — |
| `azure-maps-search-dotnet` | azure-maps-search-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-maps-search-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-messaging-webpubsub-java` | azure-messaging-webpubsub-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-messaging-webpubsub-java/SKILL.md | — |
| `azure-messaging-webpubsubservice-py` | azure-messaging-webpubsubservice-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-messaging-webpubsubservice-py/SKILL.md | — |
| `azure-mgmt-apicenter-dotnet` | azure-mgmt-apicenter-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-apicenter-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-apicenter-py` | azure-mgmt-apicenter-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-apicenter-py/SKILL.md | — |
| `azure-mgmt-apimanagement-dotnet` | azure-mgmt-apimanagement-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-apimanagement-dotnet/SKILL.md | — |
| `azure-mgmt-apimanagement-py` | azure-mgmt-apimanagement-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-apimanagement-py/SKILL.md | — |
| `azure-mgmt-applicationinsights-dotnet` | azure-mgmt-applicationinsights-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-applicationinsights-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-arizeaiobservabilityeval-dotnet` | azure-mgmt-arizeaiobservabilityeval-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-arizeaiobservabilityeval-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-botservice-dotnet` | azure-mgmt-botservice-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-botservice-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-botservice-py` | azure-mgmt-botservice-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-botservice-py/SKILL.md | — |
| `azure-mgmt-fabric-dotnet` | azure-mgmt-fabric-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-fabric-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-fabric-py` | azure-mgmt-fabric-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-fabric-py/SKILL.md | — |
| `azure-mgmt-mongodbatlas-dotnet` | azure-mgmt-mongodbatlas-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-mongodbatlas-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-mgmt-weightsandbiases-dotnet` | azure-mgmt-weightsandbiases-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-mgmt-weightsandbiases-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-microsoft-playwright-testing-ts` | azure-microsoft-playwright-testing-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-microsoft-playwright-testing-ts/SKILL.md | — |
| `azure-monitor-ingestion-java` | azure-monitor-ingestion-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-ingestion-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-monitor-ingestion-py` | azure-monitor-ingestion-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-ingestion-py/SKILL.md | — |
| `azure-monitor-opentelemetry-exporter-java` | azure-monitor-opentelemetry-exporter-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-opentelemetry-exporter-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-monitor-opentelemetry-exporter-py` | azure-monitor-opentelemetry-exporter-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-opentelemetry-exporter-py/SKILL.md | — |
| `azure-monitor-opentelemetry-py` | azure-monitor-opentelemetry-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-opentelemetry-py/SKILL.md | — |
| `azure-monitor-opentelemetry-ts` | azure-monitor-opentelemetry-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-opentelemetry-ts/SKILL.md | — |
| `azure-monitor-query-java` | azure-monitor-query-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-query-java/SKILL.md | Azure/azure-sdk-for-java |
| `azure-monitor-query-py` | azure-monitor-query-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-monitor-query-py/SKILL.md | — |
| `azure-postgres-ts` | azure-postgres-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-postgres-ts/SKILL.md | brianc/node-postgres |
| `azure-resource-manager-cosmosdb-dotnet` | azure-resource-manager-cosmosdb-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-cosmosdb-dotnet/SKILL.md | — |
| `azure-resource-manager-durabletask-dotnet` | azure-resource-manager-durabletask-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-durabletask-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-resource-manager-mysql-dotnet` | azure-resource-manager-mysql-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-mysql-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-resource-manager-playwright-dotnet` | azure-resource-manager-playwright-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-playwright-dotnet/SKILL.md | — |
| `azure-resource-manager-postgresql-dotnet` | azure-resource-manager-postgresql-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-postgresql-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-resource-manager-redis-dotnet` | azure-resource-manager-redis-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-redis-dotnet/SKILL.md | — |
| `azure-resource-manager-sql-dotnet` | azure-resource-manager-sql-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-resource-manager-sql-dotnet/SKILL.md | — |
| `azure-search-documents-dotnet` | azure-search-documents-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-search-documents-dotnet/SKILL.md | — |
| `azure-search-documents-py` | azure-search-documents-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-search-documents-py/SKILL.md | — |
| `azure-search-documents-ts` | azure-search-documents-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-search-documents-ts/SKILL.md | — |
| `azure-security-keyvault-keys-dotnet` | azure-security-keyvault-keys-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-security-keyvault-keys-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-security-keyvault-keys-java` | azure-security-keyvault-keys-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-security-keyvault-keys-java/SKILL.md | — |
| `azure-security-keyvault-secrets-java` | azure-security-keyvault-secrets-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-security-keyvault-secrets-java/SKILL.md | — |
| `azure-servicebus-dotnet` | azure-servicebus-dotnet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-servicebus-dotnet/SKILL.md | Azure/azure-sdk-for-net |
| `azure-servicebus-py` | azure-servicebus-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-servicebus-py/SKILL.md | — |
| `azure-servicebus-rust` | azure-servicebus-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-servicebus-rust/SKILL.md | Azure/azure-sdk-for-rust, microsoft/skills |
| `azure-servicebus-ts` | azure-servicebus-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-servicebus-ts/SKILL.md | — |
| `azure-speech-to-text-rest-py` | azure-speech-to-text-rest-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-speech-to-text-rest-py/SKILL.md | — |
| `azure-storage-blob-java` | azure-storage-blob-java | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-blob-java/SKILL.md | — |
| `azure-storage-blob-py` | azure-storage-blob-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-blob-py/SKILL.md | — |
| `azure-storage-blob-rust` | azure-storage-blob-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-blob-rust/SKILL.md | Azure/azure-sdk-for-rust |
| `azure-storage-blob-ts` | azure-storage-blob-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-blob-ts/SKILL.md | — |
| `azure-storage-file-datalake-py` | azure-storage-file-datalake-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-file-datalake-py/SKILL.md | — |
| `azure-storage-file-share-py` | azure-storage-file-share-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-file-share-py/SKILL.md | — |
| `azure-storage-file-share-ts` | azure-storage-file-share-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-file-share-ts/SKILL.md | — |
| `azure-storage-queue-py` | azure-storage-queue-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-queue-py/SKILL.md | — |
| `azure-storage-queue-rust` | azure-storage-queue-rust | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-queue-rust/SKILL.md | Azure/azure-sdk-for-rust, microsoft/skills |
| `azure-storage-queue-ts` | azure-storage-queue-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-storage-queue-ts/SKILL.md | — |
| `azure-web-pubsub-ts` | azure-web-pubsub-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/azure-web-pubsub-ts/SKILL.md | — |
| `backend-architect` | backend-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/backend-architect/SKILL.md | — |
| `backend-dev-guidelines` | backend-dev-guidelines | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/backend-dev-guidelines/SKILL.md | — |
| `backend-development-feature-development` | backend-development-feature-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/backend-development-feature-development/SKILL.md | — |
| `backend-security-coder` | backend-security-coder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/backend-security-coder/SKILL.md | — |
| `backtesting-frameworks` | backtesting-frameworks | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/backtesting-frameworks/SKILL.md | — |
| `bamboohr-automation` | bamboohr-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bamboohr-automation/SKILL.md | — |
| `base` | base | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/plugins/agentic-awesome-skills-claude/skills/libreoffice/base/SKILL.md | — |
| `basecamp-automation` | basecamp-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/basecamp-automation/SKILL.md | — |
| `baseline-ui` | baseline-ui | ibelick/ui-skills | ledger | Compatible | https://github.com/ibelick/ui-skills | ibelick/ui-skills |
| `bash-defensive-patterns` | bash-defensive-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bash-defensive-patterns/SKILL.md | — |
| `bash-linux` | bash-linux | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bash-linux/SKILL.md | — |
| `bash-pro` | bash-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bash-pro/SKILL.md | awesome-lists/awesome-bash, bats-core/bats-core |
| `bash-scripting` | bash-scripting | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bash-scripting/SKILL.md | — |
| `bats-testing-patterns` | bats-testing-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bats-testing-patterns/SKILL.md | — |
| `bazel-build-optimization` | bazel-build-optimization | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bazel-build-optimization/SKILL.md | aspect-build/rules_js, bazelbuild/rules_python |
| `bdi-mental-states` | bdi-mental-states | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bdi-mental-states/SKILL.md | — |
| `bdistill-behavioral-xray` | bdistill-behavioral-xray | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bdistill-behavioral-xray/SKILL.md | — |
| `bdistill-knowledge-extraction` | bdistill-knowledge-extraction | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bdistill-knowledge-extraction/SKILL.md | — |
| `beautiful-prose` | beautiful-prose | SHADOWPR0 | ledger | Compatible | https://github.com/SHADOWPR0/beautiful_prose | — |
| `before-you-build` | before-you-build | bin1874 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/before-you-build/SKILL.md | bin1874/before-you-build-skill |
| `behavioral-modes` | behavioral-modes | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/behavioral-modes/SKILL.md | — |
| `bevy-ecs-expert` | bevy-ecs-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bevy-ecs-expert/SKILL.md | — |
| `bilig-workpaper` | bilig-workpaper | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bilig-workpaper/SKILL.md | proompteng/bilig |
| `bill-gates` | bill-gates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bill-gates/SKILL.md | — |
| `billing-automation` | billing-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/billing-automation/SKILL.md | — |
| `binary-analysis-patterns` | binary-analysis-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/binary-analysis-patterns/SKILL.md | — |
| `biopython` | biopython | K-Dense-AI/claude-scientific-skills | ledger | Compatible | https://github.com/K-Dense-AI/claude-scientific-skills | biopython/biopython |
| `bitbucket-automation` | bitbucket-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bitbucket-automation/SKILL.md | — |
| `blockchain-developer` | blockchain-developer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/blockchain-developer/SKILL.md | — |
| `blockrun` | blockrun | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/blockrun/SKILL.md | — |
| `blog-writing-guide` | blog-writing-guide | xiaolai | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/blog-writing-guide/SKILL.md | — |
| `blueprint` | blueprint | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/blueprint/SKILL.md | antbotlab/blueprint, antbotlab/blueprint.git |
| `box-automation` | box-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/box-automation/SKILL.md | — |
| `brain-to-docs` | brain-to-docs | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brain-to-docs/SKILL.md | davidondrej/skills |
| `brand-guidelines-community` | brand-guidelines-community | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brand-guidelines-community/SKILL.md | — |
| `brand-guidelines-sickn33` | brand-guidelines-anthropic | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brand-guidelines-anthropic/SKILL.md | — |
| `brand-guidelines-sickn33-2` | brand-guidelines | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brand-guidelines/SKILL.md | — |
| `brand-perception-psychologist` | brand-perception-psychologist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brand-perception-psychologist/SKILL.md | — |
| `brave-man` | brave-man | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brave-man/SKILL.md | — |
| `brevo-automation` | brevo-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brevo-automation/SKILL.md | — |
| `broken-authentication` | broken-authentication | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/broken-authentication/SKILL.md | — |
| `brooks-audit` | brooks-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-audit/SKILL.md | hyhmrright/brooks-lint |
| `brooks-debt` | brooks-debt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-debt/SKILL.md | hyhmrright/brooks-lint |
| `brooks-harness` | brooks-harness | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-harness/SKILL.md | hyhmrright/brooks-lint |
| `brooks-lint` | brooks-lint | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-lint/SKILL.md | hyhmrright/brooks-lint, hyhmrright/logic-lens |
| `brooks-review` | brooks-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-review/SKILL.md | hyhmrright/brooks-lint |
| `brooks-sweep` | brooks-sweep | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-sweep/SKILL.md | hyhmrright/brooks-lint |
| `brooks-test` | brooks-test | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/brooks-test/SKILL.md | hyhmrright/brooks-lint |
| `browser-extension-builder` | browser-extension-builder | specterslient95-lgtm | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/browser-extension-builder/SKILL.md | — |
| `browser-harness` | browser-harness | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/browser-harness/SKILL.md | davidondrej/skills |
| `browser-testing-with-devtools` | browser-testing-with-devtools | addyosmani/agent-skills | ledger | MIT | https://github.com/addyosmani/agent-skills | addyosmani/agent-skills |
| `bug-hunt-swarm` | bug-hunt-swarm | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bug-hunt-swarm/SKILL.md | Dimillian/Skills |
| `bug-hunter` | bug-hunter | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bug-hunter/SKILL.md | — |
| `bugs-are-annoying` | bugs-are-annoying | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bugs-are-annoying/SKILL.md | — |
| `build` | build | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/build/SKILL.md | — |
| `building-native-ui` | building-native-ui | expo/skills | ledger | MIT | https://github.com/expo/skills | expo/skills |
| `bulletmind` | bulletmind | tejasashinde | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bulletmind/SKILL.md | — |
| `bullmq-specialist` | bullmq-specialist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bullmq-specialist/SKILL.md | — |
| `bumblebee` | bumblebee | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bumblebee/SKILL.md | mycelos-ai/bumblebee-skill, perplexityai/bumblebee |
| `bun-development` | bun-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/bun-development/SKILL.md | oven-sh/bun, user/repo.git |
| `burp-suite-testing` | burp-suite-testing | PortSwigger | ledger | N/A | https://portswigger.net/burp | — |
| `burpsuite-project-parser` | burpsuite-project-parser | trailofbits/skills | ledger | Compatible | https://github.com/trailofbits/skills | BuffaloWill/burpsuite-project-file-parser |
| `business-analyst` | business-analyst | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/business-analyst/SKILL.md | — |
| `busybox-on-windows` | busybox-on-windows | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/busybox-on-windows/SKILL.md | — |
| `buywhere-product-catalog` | buywhere-product-catalog | BuyWhere | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/buywhere-product-catalog/SKILL.md | BuyWhere/buywhere-cursor-plugin, BuyWhere/buywhere-mcp |
| `c-pro` | c-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c-pro/SKILL.md | — |
| `c4-architecture-c4-architecture` | c4-architecture-c4-architecture | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c4-architecture-c4-architecture/SKILL.md | — |
| `c4-code` | c4-code | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c4-code/SKILL.md | — |
| `c4-component` | c4-component | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c4-component/SKILL.md | — |
| `c4-container` | c4-container | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c4-container/SKILL.md | — |
| `c4-context` | c4-context | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/c4-context/SKILL.md | — |
| `cal-com-automation` | cal-com-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cal-com-automation/SKILL.md | — |
| `calendly-automation` | calendly-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/calendly-automation/SKILL.md | — |
| `canva-automation` | canva-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/canva-automation/SKILL.md | — |
| `canvas-design` | canvas-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/canvas-design/SKILL.md | — |
| `carrier-relationship-management` | carrier-relationship-management | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/carrier-relationship-management/SKILL.md | ai-evos/agent-skills |
| `cc-skill-backend-patterns` | cc-skill-backend-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-backend-patterns/SKILL.md | — |
| `cc-skill-clickhouse-io` | cc-skill-clickhouse-io | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-clickhouse-io/SKILL.md | — |
| `cc-skill-coding-standards` | cc-skill-coding-standards | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-coding-standards/SKILL.md | — |
| `cc-skill-continuous-learning` | cc-skill-continuous-learning | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-continuous-learning/SKILL.md | — |
| `cc-skill-frontend-patterns` | cc-skill-frontend-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-frontend-patterns/SKILL.md | — |
| `cc-skill-project-guidelines-example` | cc-skill-project-guidelines-example | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-project-guidelines-example/SKILL.md | — |
| `cc-skill-security-review` | cc-skill-security-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-security-review/SKILL.md | — |
| `cc-skill-strategic-compact` | cc-skill-strategic-compact | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cc-skill-strategic-compact/SKILL.md | — |
| `cdk-patterns` | cdk-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cdk-patterns/SKILL.md | — |
| `changelog-automation` | changelog-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/changelog-automation/SKILL.md | — |
| `changelog-updates` | changelog-updates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/changelog-updates/SKILL.md | jonathimer/devmarketing-skills |
| `chat-widget` | chat-widget | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/chat-widget/SKILL.md | — |
| `chrome-extension-developer` | chrome-extension-developer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/chrome-extension-developer/SKILL.md | — |
| `churn-prevention` | churn-prevention | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/churn-prevention/SKILL.md | coreyhaines31/marketingskills |
| `ci-cd-and-automation` | ci-cd-and-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ci-cd-and-automation/SKILL.md | addyosmani/agent-skills |
| `cicd-automation-workflow-automate` | cicd-automation-workflow-automate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cicd-automation-workflow-automate/SKILL.md | — |
| `circleci-automation` | circleci-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/circleci-automation/SKILL.md | — |
| `cirq` | cirq | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cirq/SKILL.md | quantumlib/Cirq, quantumlib/ReCirq |
| `citation-management` | citation-management | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/citation-management/SKILL.md | — |
| `ckw-design` | ckw-design | connerkward | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ckw-design/SKILL.md | connerkward/ckw-design-skill |
| `claimable-postgres` | claimable-postgres | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claimable-postgres/SKILL.md | neondatabase/agent-skills |
| `clarity-gate` | clarity-gate | frmoretto/clarity-gate | ledger | Compatible | https://github.com/frmoretto/clarity-gate | frmoretto/clarity-gate, frmoretto/source-of-truth-creator |
| `clarvia-aeo-check` | clarvia-aeo-check | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/clarvia-aeo-check/SKILL.md | example/my-mcp-server, example/new-tool |
| `clean-code` | clean-code | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/clean-code/SKILL.md | jackjin1997/ClawForge |
| `clerk-auth` | clerk-auth | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/clerk-auth/SKILL.md | — |
| `clickup-automation` | clickup-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/clickup-automation/SKILL.md | — |
| `close-automation` | close-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/close-automation/SKILL.md | — |
| `closed-loop-delivery` | closed-loop-delivery | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/closed-loop-delivery/SKILL.md | — |
| `cloud-architect` | cloud-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cloud-architect/SKILL.md | — |
| `cloud-devops` | cloud-devops | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cloud-devops/SKILL.md | — |
| `cloud-penetration-testing` | cloud-penetration-testing | HackTricks | ledger | MIT / CC-BY-SA | https://book.hacktricks.xyz/ | — |
| `cloudflare-workers-expert` | cloudflare-workers-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cloudflare-workers-expert/SKILL.md | — |
| `cloudformation-best-practices` | cloudformation-best-practices | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cloudformation-best-practices/SKILL.md | — |
| `cmux` | cmux | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cmux/SKILL.md | davidondrej/skills |
| `co-marketing` | co-marketing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/co-marketing/SKILL.md | coreyhaines31/marketingskills |
| `coda-automation` | coda-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/coda-automation/SKILL.md | — |
| `code-documentation-code-explain` | code-documentation-code-explain | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-documentation-code-explain/SKILL.md | — |
| `code-documentation-doc-generate` | code-documentation-doc-generate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-documentation-doc-generate/SKILL.md | — |
| `code-expert` | claude-code-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-code-expert/SKILL.md | anthropics/claude-code, modelcontextprotocol/sdk |
| `code-guide` | claude-code-guide | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-code-guide/SKILL.md | zebbern/claude-code-guide |
| `code-polish` | code-polish | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-polish/SKILL.md | — |
| `code-refactoring-context-restore` | code-refactoring-context-restore | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-refactoring-context-restore/SKILL.md | — |
| `code-refactoring-refactor-clean` | code-refactoring-refactor-clean | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-refactoring-refactor-clean/SKILL.md | — |
| `code-refactoring-tech-debt` | code-refactoring-tech-debt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-refactoring-tech-debt/SKILL.md | — |
| `code-review-ai-ai-review` | code-review-ai-ai-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-review-ai-ai-review/SKILL.md | — |
| `code-review-and-quality` | code-review-and-quality | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-review-and-quality/SKILL.md | addyosmani/agent-skills |
| `code-review-checklist` | code-review-checklist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-review-checklist/SKILL.md | thoughtbot/guides |
| `code-review-excellence` | code-review-excellence | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-review-excellence/SKILL.md | — |
| `code-reviewer` | code-reviewer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-reviewer/SKILL.md | — |
| `code-showcase-core-components` | code-showcase-core-components | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-showcase-core-components/SKILL.md | ChrisWiles/claude-code-showcase |
| `code-showcase-react-ui-patterns` | code-showcase-react-ui-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-showcase-react-ui-patterns/SKILL.md | ChrisWiles/claude-code-showcase |
| `code-showcase-systematic-debugging` | code-showcase-systematic-debugging | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-showcase-systematic-debugging/SKILL.md | ChrisWiles/claude-code-showcase |
| `code-showcase-testing-patterns` | code-showcase-testing-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-showcase-testing-patterns/SKILL.md | ChrisWiles/claude-code-showcase |
| `code-simplification` | code-simplification | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-simplification/SKILL.md | addyosmani/agent-skills, anthropics/claude-plugins-official |
| `code-simplifier` | code-simplifier | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/code-simplifier/SKILL.md | anthropics/claude-plugins-official |
| `codebase-audit-pre-push` | codebase-audit-pre-push | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-audit-pre-push/SKILL.md | — |
| `codebase-cleanup-deps-audit` | codebase-cleanup-deps-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-cleanup-deps-audit/SKILL.md | — |
| `codebase-cleanup-refactor-clean` | codebase-cleanup-refactor-clean | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-cleanup-refactor-clean/SKILL.md | — |
| `codebase-cleanup-tech-debt` | codebase-cleanup-tech-debt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-cleanup-tech-debt/SKILL.md | — |
| `codebase-design` | codebase-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-design/SKILL.md | mattpocock/skills |
| `codebase-to-wordpress-converter` | codebase-to-wordpress-converter | WHOISABHISHEKADHIKARI | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codebase-to-wordpress-converter/SKILL.md | — |
| `cold-email` | cold-email | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cold-email/SKILL.md | coreyhaines31/marketingskills |
| `comfyui-gateway` | comfyui-gateway | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/comfyui-gateway/SKILL.md | — |
| `commit` | commit | Sentry | ledger | Compatible | https://github.com/getsentry/skills | — |
| `community-building` | community-building | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/community-building/SKILL.md | jonathimer/devmarketing-skills |
| `competitive-landscape` | competitive-landscape | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/competitive-landscape/SKILL.md | — |
| `competitor-alternatives` | competitor-alternatives | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/competitor-alternatives/SKILL.md | — |
| `competitor-analysis` | competitor-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/competitor-analysis/SKILL.md | browserbase/skills, exa-labs/exa-py |
| `competitor-profiling` | competitor-profiling | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/competitor-profiling/SKILL.md | coreyhaines31/marketingskills |
| `competitor-tracking` | competitor-tracking | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/competitor-tracking/SKILL.md | jonathimer/devmarketing-skills |
| `complexity-cuts` | complexity-cuts | morsechimwai | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/complexity-cuts/SKILL.md | morsechimwai/lemmaly |
| `composition-patterns` | composition-patterns | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/composition-patterns/SKILL.md | vercel-labs/agent-skills |
| `comprehensive-review-full-review` | comprehensive-review-full-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/comprehensive-review-full-review/SKILL.md | — |
| `comprehensive-review-pr-enhance` | comprehensive-review-pr-enhance | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/comprehensive-review-pr-enhance/SKILL.md | — |
| `computer-use-agents` | computer-use-agents | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/computer-use-agents/SKILL.md | — |
| `computer-vision-expert` | computer-vision-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/computer-vision-expert/SKILL.md | — |
| `concise-planning` | concise-planning | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/concise-planning/SKILL.md | — |
| `conductor-implement` | conductor-implement | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-implement/SKILL.md | — |
| `conductor-manage` | conductor-manage | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-manage/SKILL.md | — |
| `conductor-new-track` | conductor-new-track | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-new-track/SKILL.md | — |
| `conductor-revert` | conductor-revert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-revert/SKILL.md | — |
| `conductor-setup` | conductor-setup | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-setup/SKILL.md | — |
| `conductor-status` | conductor-status | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-status/SKILL.md | — |
| `conductor-validator` | conductor-validator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conductor-validator/SKILL.md | — |
| `confluence-automation` | confluence-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/confluence-automation/SKILL.md | — |
| `constant-time-analysis` | constant-time-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/constant-time-analysis/SKILL.md | veorq/cryptocoding |
| `container-security-hardening` | container-security-hardening | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/container-security-hardening/SKILL.md | org/repo, sigstore/cosign |
| `content-creator` | content-creator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/content-creator/SKILL.md | — |
| `content-marketer` | content-marketer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/content-marketer/SKILL.md | — |
| `content-strategy` | content-strategy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/content-strategy/SKILL.md | coreyhaines31/marketingskills |
| `context-agent` | context-agent | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-agent/SKILL.md | — |
| `context-degradation` | context-degradation | muratcankoylan | ledger | Compatible | https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering | — |
| `context-driven-development` | context-driven-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-driven-development/SKILL.md | — |
| `context-engineering` | context-engineering | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-engineering/SKILL.md | addyosmani/agent-skills |
| `context-fundamentals` | context-fundamentals | muratcankoylan | ledger | Compatible | https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering | — |
| `context-guardian` | context-guardian | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-guardian/SKILL.md | — |
| `context-kit` | context-kit | JDDavenport | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-kit/SKILL.md | JDDavenport/context-kit.git |
| `context-management-context-restore` | context-management-context-restore | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-management-context-restore/SKILL.md | — |
| `context-management-context-save` | context-management-context-save | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-management-context-save/SKILL.md | — |
| `context-manager` | context-manager | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-manager/SKILL.md | — |
| `context-optimization` | context-optimization | muratcankoylan | ledger | Compatible | https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering | — |
| `context-window-management` | context-window-management | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context-window-management/SKILL.md | — |
| `context7-auto-research` | context7-auto-research | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/context7-auto-research/SKILL.md | BenedictKing/context7-auto-research |
| `conversation-memory` | conversation-memory | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/conversation-memory/SKILL.md | — |
| `convertkit-automation` | convertkit-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/convertkit-automation/SKILL.md | — |
| `convex` | convex | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/convex/SKILL.md | get-convex/convex-backend |
| `copy-editing` | copy-editing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/copy-editing/SKILL.md | — |
| `copywriting` | copywriting | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/copywriting/SKILL.md | — |
| `copywriting-psychologist` | copywriting-psychologist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/copywriting-psychologist/SKILL.md | — |
| `core-components` | core-components | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/core-components/SKILL.md | — |
| `cost-optimization` | cost-optimization | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cost-optimization/SKILL.md | — |
| `cpp-pro` | cpp-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cpp-pro/SKILL.md | — |
| `cqrs-implementation` | cqrs-implementation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cqrs-implementation/SKILL.md | — |
| `create-branch` | create-branch | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/create-branch/SKILL.md | — |
| `create-issue-gate` | create-issue-gate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/create-issue-gate/SKILL.md | — |
| `create-pr` | create-pr | Sentry | ledger | Compatible | https://github.com/getsentry/skills | — |
| `cred-omega` | cred-omega | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cred-omega/SKILL.md | — |
| `crewai` | crewai | CrewAI | ledger | MIT | https://github.com/joaomdmoura/crewAI | — |
| `cro` | cro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cro/SKILL.md | coreyhaines31/marketingskills |
| `cron-doctor` | cron-doctor | takeaseatventure | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cron-doctor/SKILL.md | takeaseatventure/devops-skills |
| `crossframe` | crossframe | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-casebook` | crossframe-casebook | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-casebook/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-critical` | crossframe-critical | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-critical/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-debate` | crossframe-debate | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-debate/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-dialogue` | crossframe-dialogue | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-dialogue/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-essay` | crossframe-essay | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-essay/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-notebook` | crossframe-notebook | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-notebook/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-org` | crossframe-org | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-org/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-public` | crossframe-public | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-public/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-review` | crossframe-review | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-review/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-suite` | crossframe-suite | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-suite/SKILL.md | xi-kari/crossframe-skill |
| `crossframe-teach` | crossframe-teach | xi-kari | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crossframe-teach/SKILL.md | xi-kari/crossframe-skill |
| `crypto-bd-agent` | crypto-bd-agent | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/crypto-bd-agent/SKILL.md | buzzbysolcex/buzz-bd-agent |
| `csharp-pro` | csharp-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/csharp-pro/SKILL.md | — |
| `cucumber-skill` | cucumber-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cucumber-skill/SKILL.md | LambdaTest/agent-skills |
| `customer-psychographic-profiler` | customer-psychographic-profiler | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/customer-psychographic-profiler/SKILL.md | — |
| `customer-research` | customer-research | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/customer-research/SKILL.md | coreyhaines31/marketingskills |
| `customer-support` | customer-support | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/customer-support/SKILL.md | — |
| `customs-trade-compliance` | customs-trade-compliance | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/customs-trade-compliance/SKILL.md | ai-evos/agent-skills |
| `cv-generator` | cv-generator | WHOISABHISHEKADHIKARI | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cv-generator/SKILL.md | — |
| `cyber-audit` | cyber-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cyber-audit/SKILL.md | davidondrej/skills |
| `cypress-skill` | cypress-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/cypress-skill/SKILL.md | LambdaTest/agent-skills |
| `d3js-skill` | claude-d3js-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-d3js-skill/SKILL.md | — |
| `daily` | daily | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/daily/SKILL.md | — |
| `daily-gift` | daily-gift | jiawei248 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/daily-gift/SKILL.md | — |
| `daily-news-report` | daily-news-report | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/daily-news-report/SKILL.md | — |
| `data-engineer` | data-engineer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-engineer/SKILL.md | — |
| `data-engineering-data-driven-feature` | data-engineering-data-driven-feature | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-engineering-data-driven-feature/SKILL.md | — |
| `data-engineering-data-pipeline` | data-engineering-data-pipeline | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-engineering-data-pipeline/SKILL.md | — |
| `data-quality-frameworks` | data-quality-frameworks | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-quality-frameworks/SKILL.md | — |
| `data-scientist` | data-scientist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-scientist/SKILL.md | — |
| `data-storytelling` | data-storytelling | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-storytelling/SKILL.md | — |
| `data-structure-protocol` | data-structure-protocol | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/data-structure-protocol/SKILL.md | k-kolomeitsev/data-structure-protocol |
| `database` | database | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database/SKILL.md | — |
| `database-admin` | database-admin | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-admin/SKILL.md | — |
| `database-architect` | database-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-architect/SKILL.md | — |
| `database-cloud-optimization-cost-optimize` | database-cloud-optimization-cost-optimize | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-cloud-optimization-cost-optimize/SKILL.md | — |
| `database-design` | database-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-design/SKILL.md | — |
| `database-migration` | database-migration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-migration/SKILL.md | — |
| `database-migrations-migration-observability` | database-migrations-migration-observability | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-migrations-migration-observability/SKILL.md | — |
| `database-migrations-sql-migrations` | database-migrations-sql-migrations | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-migrations-sql-migrations/SKILL.md | — |
| `database-optimizer` | database-optimizer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/database-optimizer/SKILL.md | — |
| `datadog-automation` | datadog-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/datadog-automation/SKILL.md | — |
| `dbos-golang` | dbos-golang | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dbos-golang/SKILL.md | dbos-inc/dbos-transact-golang |
| `dbos-python` | dbos-python | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dbos-python/SKILL.md | dbos-inc/dbos-transact-py |
| `dbos-typescript` | dbos-typescript | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dbos-typescript/SKILL.md | dbos-inc/dbos-transact-ts |
| `dbt-transformation-patterns` | dbt-transformation-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dbt-transformation-patterns/SKILL.md | — |
| `ddd-context-mapping` | ddd-context-mapping | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ddd-context-mapping/SKILL.md | — |
| `ddd-strategic-design` | ddd-strategic-design | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ddd-strategic-design/SKILL.md | — |
| `ddd-tactical-patterns` | ddd-tactical-patterns | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ddd-tactical-patterns/SKILL.md | — |
| `debug-buttercup` | debug-buttercup | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debug-buttercup/SKILL.md | — |
| `debugger` | debugger | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugger/SKILL.md | — |
| `debugging-and-error-recovery` | debugging-and-error-recovery | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugging-and-error-recovery/SKILL.md | addyosmani/agent-skills |
| `debugging-code` | debugging-code | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugging-code/SKILL.md | AlmogBaku/debug-skill |
| `debugging-strategies` | debugging-strategies | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugging-strategies/SKILL.md | — |
| `debugging-toolkit` | debugging-toolkit | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugging-toolkit/SKILL.md | — |
| `debugging-toolkit-smart-debug` | debugging-toolkit-smart-debug | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/debugging-toolkit-smart-debug/SKILL.md | — |
| `decision-navigator` | decision-navigator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/decision-navigator/SKILL.md | — |
| `deep-research` | deep-research | sanjay3290 | ledger | Compatible | https://github.com/sanjay3290/ai-skills | sanjay3290/ai-skills |
| `deepapi` | deepapi | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deepapi/SKILL.md | davidondrej/skills |
| `defi-protocol-templates` | defi-protocol-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/defi-protocol-templates/SKILL.md | — |
| `defuddle` | defuddle | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/defuddle/SKILL.md | kepano/obsidian-skills |
| `delegating-to-agents` | delegating-to-agents | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/delegating-to-agents/SKILL.md | davidondrej/skills |
| `dependency-management-deps-audit` | dependency-management-deps-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dependency-management-deps-audit/SKILL.md | — |
| `dependency-upgrade` | dependency-upgrade | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dependency-upgrade/SKILL.md | — |
| `deploy-to-vercel` | deploy-to-vercel | FrancoStino | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deploy-to-vercel/SKILL.md | vercel-labs/agent-skills |
| `deployment-engineer` | deployment-engineer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deployment-engineer/SKILL.md | — |
| `deployment-pipeline-design` | deployment-pipeline-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deployment-pipeline-design/SKILL.md | — |
| `deployment-procedures` | deployment-procedures | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deployment-procedures/SKILL.md | — |
| `deployment-validation-config-validate` | deployment-validation-config-validate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deployment-validation-config-validate/SKILL.md | — |
| `deprecation-and-migration` | deprecation-and-migration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deprecation-and-migration/SKILL.md | addyosmani/agent-skills |
| `design-it` | design-it | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-it/SKILL.md | — |
| `design-md` | design-md | Google Labs (Stitch) | ledger | Compatible | https://github.com/google-labs-code/stitch-skills | google-labs-code/stitch-skills |
| `design-orchestration` | design-orchestration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-orchestration/SKILL.md | — |
| `design-philosophy` | design-philosophy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-philosophy/SKILL.md | connerkward/ckw-design-skill |
| `design-spatial` | design-spatial | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-spatial/SKILL.md | connerkward/ckw-design-skill |
| `design-spells` | design-spells | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-spells/SKILL.md | — |
| `design-system` | design-system | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-system/SKILL.md | connerkward/ckw-design-skill |
| `design-taste-frontend` | design-taste-frontend | Leonxlnx/taste-skill | ledger | Not declared upstream | https://github.com/Leonxlnx/taste-skill | — |
| `design-thinking` | design-thinking | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-thinking/SKILL.md | connerkward/ckw-design-skill |
| `design-ux` | design-ux | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/design-ux/SKILL.md | connerkward/ckw-design-skill |
| `deterministic-design` | deterministic-design | connerkward | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/deterministic-design/SKILL.md | connerkward/deterministic-design-skill |
| `dev-to-hashnode` | dev-to-hashnode | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dev-to-hashnode/SKILL.md | jonathimer/devmarketing-skills |
| `devcontainer-setup` | devcontainer-setup | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/devcontainer-setup/SKILL.md | — |
| `developer-advocacy` | developer-advocacy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-advocacy/SKILL.md | jonathimer/devmarketing-skills |
| `developer-audience-context` | developer-audience-context | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-audience-context/SKILL.md | jonathimer/devmarketing-skills |
| `developer-churn` | developer-churn | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-churn/SKILL.md | jonathimer/devmarketing-skills |
| `developer-listening` | developer-listening | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-listening/SKILL.md | jonathimer/devmarketing-skills |
| `developer-newsletter` | developer-newsletter | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-newsletter/SKILL.md | jonathimer/devmarketing-skills |
| `developer-onboarding` | developer-onboarding | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-onboarding/SKILL.md | jonathimer/devmarketing-skills |
| `developer-sandbox` | developer-sandbox | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-sandbox/SKILL.md | jonathimer/devmarketing-skills |
| `developer-seo` | developer-seo | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-seo/SKILL.md | jonathimer/devmarketing-skills |
| `developer-signup-flow` | developer-signup-flow | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/developer-signup-flow/SKILL.md | jonathimer/devmarketing-skills |
| `development` | development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/development/SKILL.md | — |
| `devops-deploy` | devops-deploy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/devops-deploy/SKILL.md | — |
| `devops-troubleshooter` | devops-troubleshooter | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/devops-troubleshooter/SKILL.md | — |
| `devrel-content` | devrel-content | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/devrel-content/SKILL.md | jonathimer/devmarketing-skills |
| `diagnosing-bugs` | diagnosing-bugs | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/diagnosing-bugs/SKILL.md | mattpocock/skills |
| `diary` | diary | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/diary/SKILL.md | — |
| `differential-review` | differential-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/differential-review/SKILL.md | — |
| `discord-automation` | discord-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/discord-automation/SKILL.md | — |
| `discord-bot-architect` | discord-bot-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/discord-bot-architect/SKILL.md | — |
| `dispatch` | dispatch | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dispatch/SKILL.md | sparklingneuronics/sparkling-skills |
| `distribute-skill-to-all-agents` | distribute-skill-to-all-agents | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/distribute-skill-to-all-agents/SKILL.md | davidondrej/skills |
| `distributed-debugging-debug-trace` | distributed-debugging-debug-trace | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/distributed-debugging-debug-trace/SKILL.md | — |
| `distributed-tracing` | distributed-tracing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/distributed-tracing/SKILL.md | jaegertracing/jaeger-operator |
| `django-access-review` | django-access-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/django-access-review/SKILL.md | — |
| `django-perf-review` | django-perf-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/django-perf-review/SKILL.md | — |
| `django-pro` | django-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/django-pro/SKILL.md | — |
| `doc-coauthoring` | doc-coauthoring | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/doc-coauthoring/SKILL.md | — |
| `doc2math` | doc2math | KyleMillion | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/doc2math/SKILL.md | thebrierfox/doc2math-skill |
| `docker-expert` | docker-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/docker-expert/SKILL.md | — |
| `docs-architect` | docs-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/docs-architect/SKILL.md | — |
| `docs-as-marketing` | docs-as-marketing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/docs-as-marketing/SKILL.md | jonathimer/devmarketing-skills |
| `documentation` | documentation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/documentation/SKILL.md | — |
| `documentation-and-adrs` | documentation-and-adrs | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/documentation-and-adrs/SKILL.md | addyosmani/agent-skills |
| `documentation-generation-doc-generate` | documentation-generation-doc-generate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/documentation-generation-doc-generate/SKILL.md | — |
| `documentation-templates` | documentation-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/documentation-templates/SKILL.md | — |
| `docusign-automation` | docusign-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/docusign-automation/SKILL.md | — |
| `docx-official` | docx-official | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/docx-official/SKILL.md | — |
| `domain-driven-design` | domain-driven-design | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/domain-driven-design/SKILL.md | — |
| `dos-verify-done-claims` | dos-verify-done-claims | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dos-verify-done-claims/SKILL.md | anthony-chaudhary/dos-kernel |
| `dotnet-architect` | dotnet-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dotnet-architect/SKILL.md | — |
| `dotnet-backend` | dotnet-backend | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dotnet-backend/SKILL.md | — |
| `dotnet-backend-patterns` | dotnet-backend-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dotnet-backend-patterns/SKILL.md | — |
| `doubt-driven-development` | doubt-driven-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/doubt-driven-development/SKILL.md | addyosmani/agent-skills |
| `drizzle-migration-conflict` | drizzle-migration-conflict | chaunsin/agent-skills | ledger | Apache-2.0 | https://github.com/chaunsin/agent-skills | chaunsin/agent-skills |
| `drizzle-orm-expert` | drizzle-orm-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/drizzle-orm-expert/SKILL.md | — |
| `dropbox-automation` | dropbox-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dropbox-automation/SKILL.md | — |
| `dwarf-expert` | dwarf-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dwarf-expert/SKILL.md | davea42/libdwarf-code |
| `dx-optimizer` | dx-optimizer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/dx-optimizer/SKILL.md | — |
| `e2e-testing-patterns` | e2e-testing-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/e2e-testing-patterns/SKILL.md | — |
| `earllm-build` | earllm-build | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/earllm-build/SKILL.md | — |
| `eas-update-insights` | eas-update-insights | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/eas-update-insights/SKILL.md | expo/skills |
| `ecl-harness-engineer` | ecl-harness-engineer | qinghui316 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ecl-harness-engineer/SKILL.md | qinghui316/ecl-harness-engineer |
| `effective-agent-skills` | effective-agent-skills | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/effective-agent-skills/SKILL.md | davidondrej/skills |
| `efficient-web-research` | efficient-web-research | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/efficient-web-research/SKILL.md | user/repo |
| `ejentum-reasoning-harness` | ejentum-reasoning-harness | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ejentum-reasoning-harness/SKILL.md | ejentum/ejentum-mcp |
| `electron-development` | electron-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/electron-development/SKILL.md | — |
| `elixir-pro` | elixir-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/elixir-pro/SKILL.md | — |
| `elon-musk` | elon-musk | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/elon-musk/SKILL.md | — |
| `email-sequence` | email-sequence | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/email-sequence/SKILL.md | — |
| `email-systems` | email-systems | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/email-systems/SKILL.md | — |
| `embedding-strategies` | embedding-strategies | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/embedding-strategies/SKILL.md | — |
| `emblemai-crypto-wallet` | emblemai-crypto-wallet | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/emblemai-crypto-wallet/SKILL.md | EmblemCompany/Agent-skills |
| `emergency-card` | emergency-card | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/emergency-card/SKILL.md | — |
| `emil-design-eng` | emil-design-eng | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/emil-design-eng/SKILL.md | emilkowalski/skills |
| `emotional-arc-designer` | emotional-arc-designer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/emotional-arc-designer/SKILL.md | — |
| `employment-contract-templates` | employment-contract-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/employment-contract-templates/SKILL.md | — |
| `energy-procurement` | energy-procurement | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/energy-procurement/SKILL.md | ai-evos/agent-skills |
| `enhance-prompt` | enhance-prompt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/enhance-prompt/SKILL.md | — |
| `environment-setup-guide` | environment-setup-guide | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/environment-setup-guide/SKILL.md | nvm-sh/nvm, pyenv/pyenv |
| `error-debugging-error-analysis` | error-debugging-error-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-debugging-error-analysis/SKILL.md | — |
| `error-debugging-error-trace` | error-debugging-error-trace | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-debugging-error-trace/SKILL.md | — |
| `error-debugging-multi-agent-review` | error-debugging-multi-agent-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-debugging-multi-agent-review/SKILL.md | — |
| `error-detective` | error-detective | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-detective/SKILL.md | — |
| `error-diagnostics-error-analysis` | error-diagnostics-error-analysis | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-diagnostics-error-analysis/SKILL.md | — |
| `error-diagnostics-error-trace` | error-diagnostics-error-trace | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-diagnostics-error-trace/SKILL.md | — |
| `error-diagnostics-smart-debug` | error-diagnostics-smart-debug | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-diagnostics-smart-debug/SKILL.md | — |
| `error-handling-patterns` | error-handling-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/error-handling-patterns/SKILL.md | — |
| `ethical-hacking-methodology` | ethical-hacking-methodology | xiaolai | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ethical-hacking-methodology/SKILL.md | — |
| `evaluation` | evaluation | muratcankoylan | ledger | — | https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering | muratcankoylan/Agent-Skills-for-Context-Engineering |
| `event-sourcing-architect` | event-sourcing-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/event-sourcing-architect/SKILL.md | — |
| `event-staffing-compliance` | event-staffing-compliance | kissmyabs32 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/event-staffing-compliance/SKILL.md | — |
| `event-staffing-ordering` | event-staffing-ordering | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/event-staffing-ordering/SKILL.md | — |
| `event-store-design` | event-store-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/event-store-design/SKILL.md | — |
| `evolution` | evolution | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/evolution/SKILL.md | ZhangHanDong/makepad-skills, makepad/makepad |
| `exa-search` | exa-search | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/exa-search/SKILL.md | BenedictKing/exa-search |
| `examprep-ai` | examprep-ai | WHOISABHISHEKADHIKARI | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/examprep-ai/SKILL.md | — |
| `explain-like-socrates` | explain-like-socrates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/explain-like-socrates/SKILL.md | — |
| `expo-api-routes` | expo-api-routes | expo/skills | ledger | MIT | https://github.com/expo/skills | expo/skills |
| `expo-brownfield` | expo-brownfield | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/expo-brownfield/SKILL.md | expo/skills |
| `expo-cicd-workflows` | expo-cicd-workflows | expo/skills | ledger | MIT | https://github.com/expo/skills | expo/skills |
| `expo-deployment` | expo-deployment | Expo | ledger | Compatible | https://github.com/expo/skills | expo/skills |
| `expo-dev-client` | expo-dev-client | expo/skills | ledger | MIT | https://github.com/expo/skills | expo/skills |
| `expo-examples` | expo-examples | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/expo-examples/SKILL.md | expo/examples, expo/examples.git |
| `expo-module` | expo-module | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/expo-module/SKILL.md | expo/skills |
| `expo-observe` | expo-observe | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/expo-observe/SKILL.md | expo/skills |
| `expo-tailwind-setup` | expo-tailwind-setup | expo/skills | ledger | MIT | https://github.com/expo/skills | expo/skills |
| `expo-ui` | expo-ui | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/expo-ui/SKILL.md | expo/skills |
| `expo-ui-jetpack-compose` | expo-ui-jetpack-compose | expo/skills | ledger | MIT | https://github.com/expo/skills | — |
| `expo-ui-swift-ui` | expo-ui-swift-ui | expo/skills | ledger | MIT | https://github.com/expo/skills | — |
| `fable-safe-prompt` | fable-safe-prompt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fable-safe-prompt/SKILL.md | davidondrej/skills |
| `fable5` | codex-fable5 | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codex-fable5/SKILL.md | baskduf/FableCodex |
| `faf-context` | faf-context | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/faf-context/SKILL.md | Wolfe-Jam/faf-skills |
| `faf-expert` | faf-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/faf-expert/SKILL.md | — |
| `faf-go` | faf-go | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/faf-go/SKILL.md | Wolfe-Jam/faf-skills |
| `faf-wizard` | faf-wizard | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/faf-wizard/SKILL.md | — |
| `fal-audio` | fal-audio | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `fal-generate` | fal-generate | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `fal-image-edit` | fal-image-edit | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `fal-platform` | fal-platform | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `fal-upscale` | fal-upscale | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `fal-workflow` | fal-workflow | fal.ai Community | ledger | Compatible | https://github.com/fal-ai-community/skills | fal-ai-community/skills |
| `family-health-analyzer` | family-health-analyzer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/family-health-analyzer/SKILL.md | — |
| `fastapi-pro` | fastapi-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fastapi-pro/SKILL.md | — |
| `fastapi-router-py` | fastapi-router-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fastapi-router-py/SKILL.md | — |
| `fastapi-templates` | fastapi-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fastapi-templates/SKILL.md | — |
| `favicon` | favicon | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/favicon/SKILL.md | — |
| `fda-food-safety-auditor` | fda-food-safety-auditor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fda-food-safety-auditor/SKILL.md | — |
| `fda-medtech-compliance-auditor` | fda-medtech-compliance-auditor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fda-medtech-compliance-auditor/SKILL.md | — |
| `ffuf-skill` | ffuf-claude-skill | jthack | ledger | Compatible | https://github.com/jthack/ffuf_claude_skill | jthack/ffuf_claude_skill |
| `ffuf-web-fuzzing` | ffuf-web-fuzzing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ffuf-web-fuzzing/SKILL.md | danielmiessler/SecLists, ffuf/ffuf |
| `figma-automation` | figma-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/figma-automation/SKILL.md | — |
| `file-organizer` | file-organizer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/file-organizer/SKILL.md | — |
| `file-path-traversal` | file-path-traversal | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/file-path-traversal/SKILL.md | — |
| `file-uploads` | file-uploads | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/file-uploads/SKILL.md | — |
| `filesystem-context` | filesystem-context | muratcankoylan | ledger | Compatible | https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering | — |
| `find-bugs` | find-bugs | Sentry | ledger | Compatible | https://github.com/getsentry/skills | — |
| `firebase` | firebase | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/firebase/SKILL.md | — |
| `firecrawl-scraper` | firecrawl-scraper | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/firecrawl-scraper/SKILL.md | BenedictKing/firecrawl-scraper |
| `firmware-analyst` | firmware-analyst | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/firmware-analyst/SKILL.md | — |
| `fitness-analyzer` | fitness-analyzer | huifer/Claude-Ally-Health | ledger | Compatible | https://github.com/huifer/Claude-Ally-Health | — |
| `fix-review` | fix-review | Trail of Bits | ledger | Compatible | https://github.com/trailofbits/skills | trailofbits/skills |
| `fixing-accessibility` | fixing-accessibility | ibelick/ui-skills | ledger | Compatible | https://github.com/ibelick/ui-skills | ibelick/ui-skills |
| `fixing-metadata` | fixing-metadata | ibelick/ui-skills | ledger | Compatible | https://github.com/ibelick/ui-skills | ibelick/ui-skills |
| `fixing-motion-performance` | fixing-motion-performance | ibelick/ui-skills | ledger | Compatible | https://github.com/ibelick/ui-skills | ibelick/ui-skills |
| `flowhunt-skill` | flowhunt-skill | konradbachowski | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/flowhunt-skill/SKILL.md | heyneuron/flowhunt-skill |
| `flutter-expert` | flutter-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/flutter-expert/SKILL.md | — |
| `folder-specific-and-agents-md` | folder-specific-claude-and-agents-md | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/folder-specific-claude-and-agents-md/SKILL.md | davidondrej/skills |
| `food-database-query` | food-database-query | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/food-database-query/SKILL.md | — |
| `form-cro` | form-cro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/form-cro/SKILL.md | — |
| `formik-patterns` | formik-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/formik-patterns/SKILL.md | ChrisWiles/claude-code-showcase |
| `fp-async` | fp-async | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-async/SKILL.md | — |
| `fp-backend` | fp-backend | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-backend/SKILL.md | — |
| `fp-data-transforms` | fp-data-transforms | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-data-transforms/SKILL.md | — |
| `fp-either-ref` | fp-either-ref | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-either-ref/SKILL.md | — |
| `fp-errors` | fp-errors | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-errors/SKILL.md | — |
| `fp-option-ref` | fp-option-ref | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-option-ref/SKILL.md | — |
| `fp-pipe-ref` | fp-pipe-ref | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-pipe-ref/SKILL.md | — |
| `fp-pragmatic` | fp-pragmatic | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-pragmatic/SKILL.md | — |
| `fp-react` | fp-react | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-react/SKILL.md | colinhacks/zod, devexperts/remote-data-ts |
| `fp-refactor` | fp-refactor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-refactor/SKILL.md | — |
| `fp-taskeither-ref` | fp-taskeither-ref | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-taskeither-ref/SKILL.md | — |
| `fp-ts-errors` | fp-ts-errors | whatiskadudoing/fp-ts-skills | ledger | Compatible | https://github.com/whatiskadudoing/fp-ts-skills | whatiskadudoing/fp-ts-skills |
| `fp-ts-pragmatic` | fp-ts-pragmatic | whatiskadudoing/fp-ts-skills | ledger | Compatible | https://github.com/whatiskadudoing/fp-ts-skills | whatiskadudoing/fp-ts-skills |
| `fp-ts-react` | fp-ts-react | whatiskadudoing/fp-ts-skills | ledger | Compatible | https://github.com/whatiskadudoing/fp-ts-skills | colinhacks/zod, devexperts/remote-data-ts |
| `fp-types-ref` | fp-types-ref | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fp-types-ref/SKILL.md | — |
| `framework-migration-code-migrate` | framework-migration-code-migrate | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/framework-migration-code-migrate/SKILL.md | — |
| `framework-migration-deps-upgrade` | framework-migration-deps-upgrade | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/framework-migration-deps-upgrade/SKILL.md | — |
| `framework-migration-legacy-modernize` | framework-migration-legacy-modernize | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/framework-migration-legacy-modernize/SKILL.md | — |
| `free-tier-strategy` | free-tier-strategy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/free-tier-strategy/SKILL.md | jonathimer/devmarketing-skills |
| `free-tool-strategy` | free-tool-strategy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/free-tool-strategy/SKILL.md | — |
| `freshdesk-automation` | freshdesk-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/freshdesk-automation/SKILL.md | — |
| `freshservice-automation` | freshservice-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/freshservice-automation/SKILL.md | — |
| `frontend-api-integration-patterns` | frontend-api-integration-patterns | avij1109 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-api-integration-patterns/SKILL.md | — |
| `frontend-architecture` | frontend-architecture | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-architecture/SKILL.md | stareezy-1/frontend-architecture-skill |
| `frontend-data-contracts` | frontend-data-contracts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-data-contracts/SKILL.md | stareezy-1/frontend-architecture-skill |
| `frontend-design` | frontend-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-design/SKILL.md | — |
| `frontend-dev-guidelines` | frontend-dev-guidelines | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-dev-guidelines/SKILL.md | — |
| `frontend-developer` | frontend-developer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-developer/SKILL.md | — |
| `frontend-lighthouse` | frontend-lighthouse | stareezy-1/frontend-architecture-skill | ledger | MIT | https://github.com/stareezy-1/frontend-architecture-skill | stareezy-1/frontend-architecture-skill |
| `frontend-mobile-development-component-scaffold` | frontend-mobile-development-component-scaffold | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-mobile-development-component-scaffold/SKILL.md | — |
| `frontend-mobile-security-xss-scan` | frontend-mobile-security-xss-scan | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-mobile-security-xss-scan/SKILL.md | — |
| `frontend-observability` | frontend-observability | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-observability/SKILL.md | stareezy-1/frontend-architecture-skill |
| `frontend-optimistic-mutations` | frontend-optimistic-mutations | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-optimistic-mutations/SKILL.md | stareezy-1/frontend-architecture-skill |
| `frontend-security-coder` | frontend-security-coder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-security-coder/SKILL.md | — |
| `frontend-seo` | frontend-seo | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-seo/SKILL.md | stareezy-1/frontend-architecture-skill |
| `frontend-slides` | frontend-slides | zarazhangrui | ledger | Compatible | https://github.com/zarazhangrui/frontend-slides | zarazhangrui/frontend-slides |
| `frontend-slides-frontend-slides` | frontend-slides-frontend-slides | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-slides-frontend-slides/SKILL.md | zarazhangrui/frontend-slides |
| `frontend-ui-dark-ts` | frontend-ui-dark-ts | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-ui-dark-ts/SKILL.md | — |
| `frontend-ui-engineering` | frontend-ui-engineering | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/frontend-ui-engineering/SKILL.md | addyosmani/agent-skills |
| `fsi-compliance-checker` | fsi-compliance-checker | timwukp | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/fsi-compliance-checker/SKILL.md | timwukp/agent-skills-best-practice |
| `full-output-enforcement` | full-output-enforcement | Leonxlnx/taste-skill | ledger | Not declared upstream | https://github.com/Leonxlnx/taste-skill | — |
| `full-stack-orchestration-full-stack-feature` | full-stack-orchestration-full-stack-feature | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/full-stack-orchestration-full-stack-feature/SKILL.md | — |
| `game-development` | game-development | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/game-development/SKILL.md | — |
| `gcp-cloud-run` | gcp-cloud-run | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gcp-cloud-run/SKILL.md | — |
| `gdb-cli` | gdb-cli | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gdb-cli/SKILL.md | Cerdore/gdb-cli, Cerdore/gdb-cli.git |
| `gdpr-data-handling` | gdpr-data-handling | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gdpr-data-handling/SKILL.md | — |
| `geminiignore-finops` | geminiignore-finops | iradoweck | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/geminiignore-finops/SKILL.md | iradoweck/antigravity-awesome-skills |
| `geo-fundamentals` | geo-fundamentals | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/geo-fundamentals/SKILL.md | — |
| `geoffrey-hinton` | geoffrey-hinton | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/geoffrey-hinton/SKILL.md | — |
| `gh-image` | gh-image | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gh-image/SKILL.md | drogers0/gh-image, user-attachments/assets |
| `gh-review-requests` | gh-review-requests | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gh-review-requests/SKILL.md | getsentry/ops |
| `gha-security-review` | gha-security-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gha-security-review/SKILL.md | — |
| `git-advanced-workflows` | git-advanced-workflows | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-advanced-workflows/SKILL.md | — |
| `git-hooks-automation` | git-hooks-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-hooks-automation/SKILL.md | astral-sh/ruff-pre-commit, compilerla/conventional-pre-commit |
| `git-pr-review` | git-pr-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-pr-review/SKILL.md | — |
| `git-pr-workflows-git-workflow` | git-pr-workflows-git-workflow | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-pr-workflows-git-workflow/SKILL.md | — |
| `git-pr-workflows-onboard` | git-pr-workflows-onboard | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-pr-workflows-onboard/SKILL.md | — |
| `git-pr-workflows-pr-enhance` | git-pr-workflows-pr-enhance | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-pr-workflows-pr-enhance/SKILL.md | — |
| `git-pushing` | git-pushing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-pushing/SKILL.md | — |
| `git-workflow-and-versioning` | git-workflow-and-versioning | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/git-workflow-and-versioning/SKILL.md | addyosmani/agent-skills |
| `github` | github | Dimillian/Skills | ledger | MIT | https://github.com/Dimillian/Skills | — |
| `github-actions-advanced` | github-actions-advanced | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-actions-advanced/SKILL.md | — |
| `github-actions-debugger` | github-actions-debugger | GeekLuffy | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-actions-debugger/SKILL.md | — |
| `github-actions-templates` | github-actions-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-actions-templates/SKILL.md | — |
| `github-automation` | github-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-automation/SKILL.md | — |
| `github-issue-creator` | github-issue-creator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-issue-creator/SKILL.md | — |
| `github-presence` | github-presence | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-presence/SKILL.md | jonathimer/devmarketing-skills, org/repo |
| `github-workflow-automation` | github-workflow-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/github-workflow-automation/SKILL.md | en/actions, en/repositories |
| `gitlab-automation` | gitlab-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gitlab-automation/SKILL.md | — |
| `gitlab-ci-patterns` | gitlab-ci-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gitlab-ci-patterns/SKILL.md | — |
| `gitops-workflow` | gitops-workflow | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gitops-workflow/SKILL.md | org/gitops-repo, org/my-app |
| `global-chat-agent-discovery` | global-chat-agent-discovery | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/global-chat-agent-discovery/SKILL.md | — |
| `gmail-automation` | gmail-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `go-concurrency-patterns` | go-concurrency-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/go-concurrency-patterns/SKILL.md | — |
| `go-in-depth` | go-in-depth | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/go-in-depth/SKILL.md | — |
| `go-playwright` | go-playwright | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/go-playwright/SKILL.md | playwright-community/playwright-go |
| `go-rod-master` | go-rod-master | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/go-rod-master/SKILL.md | go-rod/rod, go-rod/stealth |
| `goal-analyzer` | goal-analyzer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/goal-analyzer/SKILL.md | — |
| `goal-loop` | goal-loop | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/goal-loop/SKILL.md | davidondrej/skills |
| `godot-4-migration` | godot-4-migration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/godot-4-migration/SKILL.md | — |
| `godot-gdscript-patterns` | godot-gdscript-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/godot-gdscript-patterns/SKILL.md | — |
| `golang-pro` | golang-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/golang-pro/SKILL.md | — |
| `google-analytics-automation` | google-analytics-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/google-analytics-automation/SKILL.md | — |
| `google-calendar-automation` | google-calendar-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `google-docs-automation` | google-docs-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `google-drive-automation` | google-drive-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `google-sheets-automation` | google-sheets-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `google-slides-automation` | google-slides-automation | sanjay3290/ai-skills | ledger | Compatible | https://github.com/sanjay3290/ai-skills | — |
| `googlesheets-automation` | googlesheets-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/googlesheets-automation/SKILL.md | — |
| `grafana-dashboards` | grafana-dashboards | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/grafana-dashboards/SKILL.md | — |
| `graphql` | graphql | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/graphql/SKILL.md | — |
| `graphql-architect` | graphql-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/graphql-architect/SKILL.md | — |
| `graphql-schema` | graphql-schema | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/graphql-schema/SKILL.md | ChrisWiles/claude-code-showcase |
| `grilling` | grilling | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/grilling/SKILL.md | mattpocock/skills |
| `growth-engine` | growth-engine | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/growth-engine/SKILL.md | — |
| `grpc-golang` | grpc-golang | sck000 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/grpc-golang/SKILL.md | org/repo |
| `handoff` | handoff | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/handoff/SKILL.md | mattpocock/skills |
| `hasdata` | hasdata | HasData CLI | ledger | MIT | https://github.com/HasData/hasdata-cli | HasData/hasdata-cli |
| `hasdata-cli` | hasdata-cli | HasData CLI | ledger | MIT | https://github.com/HasData/hasdata-cli | HasData/hasdata-cli |
| `haskell-pro` | haskell-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/haskell-pro/SKILL.md | — |
| `headline-psychologist` | headline-psychologist | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/headline-psychologist/SKILL.md | — |
| `health-trend-analyzer` | health-trend-analyzer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/health-trend-analyzer/SKILL.md | — |
| `helium-mcp` | helium-mcp | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/helium-mcp/SKILL.md | connerlambden/helium-mcp |
| `helm-chart-scaffolding` | helm-chart-scaffolding | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/helm-chart-scaffolding/SKILL.md | — |
| `helpdesk-automation` | helpdesk-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/helpdesk-automation/SKILL.md | — |
| `hf-mcp` | hf-mcp | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hf-mcp/SKILL.md | huggingface/skills |
| `hf-mem` | hf-mem | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hf-mem/SKILL.md | huggingface/skills |
| `hierarchical-agent-memory` | hierarchical-agent-memory | kromahlusenii-ops | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hierarchical-agent-memory/SKILL.md | kromahlusenii-ops/ham |
| `hig-components-content` | hig-components-content | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-content/SKILL.md | — |
| `hig-components-controls` | hig-components-controls | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-controls/SKILL.md | — |
| `hig-components-dialogs` | hig-components-dialogs | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-dialogs/SKILL.md | — |
| `hig-components-layout` | hig-components-layout | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-layout/SKILL.md | — |
| `hig-components-menus` | hig-components-menus | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-menus/SKILL.md | — |
| `hig-components-search` | hig-components-search | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-search/SKILL.md | — |
| `hig-components-status` | hig-components-status | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-status/SKILL.md | — |
| `hig-components-system` | hig-components-system | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-components-system/SKILL.md | — |
| `hig-foundations` | hig-foundations | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-foundations/SKILL.md | — |
| `hig-inputs` | hig-inputs | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-inputs/SKILL.md | — |
| `hig-patterns` | hig-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-patterns/SKILL.md | — |
| `hig-platforms` | hig-platforms | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-platforms/SKILL.md | — |
| `hig-project-context` | hig-project-context | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-project-context/SKILL.md | — |
| `hig-technologies` | hig-technologies | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hig-technologies/SKILL.md | — |
| `high-end-visual-design` | high-end-visual-design | Leonxlnx/taste-skill | ledger | Not declared upstream | https://github.com/Leonxlnx/taste-skill | — |
| `hono` | hono | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hono/SKILL.md | — |
| `hosted-agents` | hosted-agents | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hosted-agents/SKILL.md | sst/opencode |
| `hosted-agents-v2-py` | hosted-agents-v2-py | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hosted-agents-v2-py/SKILL.md | — |
| `hr-pro` | hr-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hr-pro/SKILL.md | — |
| `html-injection-testing` | html-injection-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/html-injection-testing/SKILL.md | — |
| `hubspot-automation` | hubspot-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hubspot-automation/SKILL.md | — |
| `hubspot-integration` | hubspot-integration | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hubspot-integration/SKILL.md | — |
| `hugging-face-cli` | hugging-face-cli | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/hf-mount, huggingface/skills |
| `hugging-face-community-evals` | hugging-face-community-evals | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-dataset-viewer` | hugging-face-dataset-viewer | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-datasets` | hugging-face-datasets | huggingface/skills | ledger | Compatible | https://github.com/huggingface/skills | — |
| `hugging-face-evaluation` | hugging-face-evaluation | huggingface/skills | ledger | Compatible | https://github.com/huggingface/skills | huggingface/lighteval |
| `hugging-face-gradio` | hugging-face-gradio | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-jobs` | hugging-face-jobs | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-model-trainer` | hugging-face-model-trainer | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills, huggingface/trl |
| `hugging-face-paper-publisher` | hugging-face-paper-publisher | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-papers` | hugging-face-papers | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills, org/repo |
| `hugging-face-tool-builder` | hugging-face-tool-builder | huggingface/skills | ledger | Compatible | https://github.com/huggingface/skills | — |
| `hugging-face-trackio` | hugging-face-trackio | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `hugging-face-vision-trainer` | hugging-face-vision-trainer | Hugging Face | ledger | Compatible | https://github.com/huggingface/skills | huggingface/skills |
| `huggingface-best` | huggingface-best | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-best/SKILL.md | huggingface/skills |
| `huggingface-local-models` | huggingface-local-models | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-local-models/SKILL.md | ggml-org/llama.cpp, huggingface/skills |
| `huggingface-lora-space-builder` | huggingface-lora-space-builder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-lora-space-builder/SKILL.md | huggingface/diffusers, huggingface/skills |
| `huggingface-spaces` | huggingface-spaces | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-spaces/SKILL.md | huggingface/skills |
| `huggingface-tool-builder` | huggingface-tool-builder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-tool-builder/SKILL.md | huggingface/skills |
| `huggingface-zerogpu` | huggingface-zerogpu | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/huggingface-zerogpu/SKILL.md | huggingface/skills |
| `hugo-to-markdown` | hugo-to-markdown | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hugo-to-markdown/SKILL.md | chaunsin/agent-skills |
| `humanize-chinese` | humanize-chinese | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/humanize-chinese/SKILL.md | — |
| `hybrid-cloud-architect` | hybrid-cloud-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hybrid-cloud-architect/SKILL.md | — |
| `hybrid-cloud-networking` | hybrid-cloud-networking | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hybrid-cloud-networking/SKILL.md | — |
| `hybrid-search-implementation` | hybrid-search-implementation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hybrid-search-implementation/SKILL.md | — |
| `hyperexecute-skill` | hyperexecute-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/hyperexecute-skill/SKILL.md | LambdaTest/agent-skills |
| `i18n-localization` | i18n-localization | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/i18n-localization/SKILL.md | — |
| `iconsax-library` | iconsax-library | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/iconsax-library/SKILL.md | — |
| `idea-darwin` | idea-darwin | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/idea-darwin/SKILL.md | warmskull/idea-darwin |
| `idea-os` | idea-os | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/idea-os/SKILL.md | Slashworks-biz/idea-os, Slashworks-biz/idea-os. |
| `idea-refine` | idea-refine | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/idea-refine/SKILL.md | addyosmani/agent-skills |
| `identity-mirror` | identity-mirror | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/identity-mirror/SKILL.md | — |
| `idor-testing` | idor-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/idor-testing/SKILL.md | — |
| `ii-commons` | ii-commons | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ii-commons/SKILL.md | Intelligent-Internet/II-Commons-Skills |
| `ilya-sutskever` | ilya-sutskever | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ilya-sutskever/SKILL.md | — |
| `image-generator` | image-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/image-generator/SKILL.md | dair-ai/dair-academy-plugins |
| `image-studio` | image-studio | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/image-studio/SKILL.md | — |
| `imagen` | imagen | sanjay3290 | ledger | Compatible | https://github.com/sanjay3290/ai-skills | sanjay3290/ai-skills |
| `implement` | implement | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/implement/SKILL.md | mattpocock/skills |
| `improve-codebase-architecture` | improve-codebase-architecture | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/improve-codebase-architecture/SKILL.md | mattpocock/skills |
| `in-chrome-troubleshooting` | claude-in-chrome-troubleshooting | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-in-chrome-troubleshooting/SKILL.md | — |
| `incident-responder` | incident-responder | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/incident-responder/SKILL.md | — |
| `incident-response-incident-response` | incident-response-incident-response | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/incident-response-incident-response/SKILL.md | — |
| `incident-response-smart-fix` | incident-response-smart-fix | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/incident-response-smart-fix/SKILL.md | — |
| `incident-runbook-templates` | incident-runbook-templates | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/incident-runbook-templates/SKILL.md | — |
| `incremental-implementation` | incremental-implementation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/incremental-implementation/SKILL.md | addyosmani/agent-skills |
| `indexing-issue-auditor` | indexing-issue-auditor | WHOISABHISHEKADHIKARI | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/indexing-issue-auditor/SKILL.md | — |
| `industrial-brutalist-ui` | industrial-brutalist-ui | Leonxlnx/taste-skill | ledger | Not declared upstream | https://github.com/Leonxlnx/taste-skill | — |
| `infinite-gratitude` | infinite-gratitude | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/infinite-gratitude/SKILL.md | sstklen/infinite-gratitude |
| `infinity` | infinity | Prince-1652 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/infinity/SKILL.md | — |
| `ingest-youtube` | ingest-youtube | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ingest-youtube/SKILL.md | adelaidasofia/ai-brain-starter |
| `inngest` | inngest | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/inngest/SKILL.md | — |
| `instagram` | instagram | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/instagram/SKILL.md | — |
| `instagram-automation` | instagram-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/instagram-automation/SKILL.md | — |
| `interactions-api` | gemini-interactions-api | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gemini-interactions-api/SKILL.md | google-gemini/gemini-skills, my-org/backend |
| `interactive-portfolio` | interactive-portfolio | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/interactive-portfolio/SKILL.md | — |
| `intercom-automation` | intercom-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/intercom-automation/SKILL.md | — |
| `internal-comms-community` | internal-comms-community | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/internal-comms-community/SKILL.md | — |
| `internal-comms-sickn33` | internal-comms-anthropic | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/internal-comms-anthropic/SKILL.md | — |
| `internal-comms-sickn33-2` | internal-comms | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/internal-comms/SKILL.md | anthropics/skills |
| `interview-coach` | interview-coach | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/interview-coach/SKILL.md | dbhat93/job-search-os |
| `interview-style-doc-building` | interview-style-doc-building | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/interview-style-doc-building/SKILL.md | davidondrej/skills |
| `invariant-guard` | invariant-guard | morsechimwai | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/invariant-guard/SKILL.md | morsechimwai/lemmaly |
| `inventory-demand-planning` | inventory-demand-planning | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/inventory-demand-planning/SKILL.md | ai-evos/agent-skills |
| `ios-debugger-agent` | ios-debugger-agent | Dimillian/Skills | ledger | MIT | https://github.com/Dimillian/Skills | — |
| `ios-developer` | ios-developer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/ios-developer/SKILL.md | — |
| `issues` | issues | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/issues/SKILL.md | — |
| `istio-traffic-management` | istio-traffic-management | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/istio-traffic-management/SKILL.md | — |
| `it-manager-hospital` | it-manager-hospital | edudeftones-cloud | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/it-manager-hospital/SKILL.md | — |
| `it-manager-pro` | it-manager-pro | edudeftones-cloud | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/it-manager-pro/SKILL.md | — |
| `iterate-pr` | iterate-pr | Sentry | ledger | Compatible | https://github.com/getsentry/skills | — |
| `itil-expert` | itil-expert | edudeftones-cloud | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/itil-expert/SKILL.md | — |
| `java-pro` | java-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/java-pro/SKILL.md | — |
| `javascript-mastery` | javascript-mastery | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/javascript-mastery/SKILL.md | getify/You-Dont-Know-JS, leonardomso/33-js-concepts |
| `javascript-pro` | javascript-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/javascript-pro/SKILL.md | — |
| `javascript-testing-patterns` | javascript-testing-patterns | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/javascript-testing-patterns/SKILL.md | — |
| `javascript-typescript-typescript-scaffold` | javascript-typescript-typescript-scaffold | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/javascript-typescript-typescript-scaffold/SKILL.md | — |
| `jest-skill` | jest-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/jest-skill/SKILL.md | LambdaTest/agent-skills |
| `jira-automation` | jira-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/jira-automation/SKILL.md | — |
| `jobgpt` | jobgpt | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/jobgpt/SKILL.md | 6figr-com/jobgpt-mcp-server, 6figr-com/skills |
| `jobs-to-be-done-analyst` | jobs-to-be-done-analyst | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/jobs-to-be-done-analyst/SKILL.md | — |
| `jq` | jq | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/jq/SKILL.md | repos/owner |
| `json-canvas` | json-canvas | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/json-canvas/SKILL.md | kepano/obsidian-skills, obsidianmd/jsoncanvas |
| `julia-pro` | julia-pro | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/julia-pro/SKILL.md | — |
| `junit-5-skill` | junit-5-skill | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/junit-5-skill/SKILL.md | LambdaTest/agent-skills |
| `junta-leiloeiros` | junta-leiloeiros | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/junta-leiloeiros/SKILL.md | — |
| `k6-load-testing` | k6-load-testing | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/k6-load-testing/SKILL.md | grafana/k6 |
| `k8s-manifest-generator` | k8s-manifest-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/k8s-manifest-generator/SKILL.md | — |
| `k8s-security-policies` | k8s-security-policies | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/k8s-security-policies/SKILL.md | — |
| `kaizen` | kaizen | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kaizen/SKILL.md | — |
| `keyword-extractor` | keyword-extractor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/keyword-extractor/SKILL.md | — |
| `klaviyo-automation` | klaviyo-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/klaviyo-automation/SKILL.md | — |
| `kotler-macro-analyzer` | kotler-macro-analyzer | justmiroslav | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kotler-macro-analyzer/SKILL.md | — |
| `kotlin-coroutines-expert` | kotlin-coroutines-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kotlin-coroutines-expert/SKILL.md | — |
| `kpi-dashboard-design` | kpi-dashboard-design | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kpi-dashboard-design/SKILL.md | — |
| `kubernetes-architect` | kubernetes-architect | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kubernetes-architect/SKILL.md | — |
| `kubernetes-deployment` | kubernetes-deployment | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kubernetes-deployment/SKILL.md | — |
| `kubestellar-console` | kubestellar-console | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/kubestellar-console/SKILL.md | kubestellar/console |
| `lambda-lang` | lambda-lang | voidborne-d | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lambda-lang/SKILL.md | voidborne-d/lambda-lang |
| `lambdatest-agent-skills` | lambdatest-agent-skills | tanveer-farooq | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lambdatest-agent-skills/SKILL.md | LambdaTest/agent-skills |
| `landing-page-generator` | landing-page-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/landing-page-generator/SKILL.md | — |
| `langchain-architecture` | langchain-architecture | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/langchain-architecture/SKILL.md | — |
| `langfuse` | langfuse | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/langfuse/SKILL.md | — |
| `langgraph` | langgraph | LangGraph | ledger | MIT | https://github.com/langchain-ai/langgraph | — |
| `laravel-expert` | laravel-expert | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/laravel-expert/SKILL.md | — |
| `laravel-security-audit` | laravel-security-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/laravel-security-audit/SKILL.md | — |
| `last30days` | last30days | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/last30days/SKILL.md | — |
| `latex-paper-conversion` | latex-paper-conversion | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/latex-paper-conversion/SKILL.md | — |
| `launch-strategy` | launch-strategy | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/launch-strategy/SKILL.md | — |
| `lead-magnets` | lead-magnets | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lead-magnets/SKILL.md | coreyhaines31/marketingskills |
| `learn` | learn | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/learn/SKILL.md | dair-ai/dair-academy-plugins |
| `legacy-modernizer` | legacy-modernizer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/legacy-modernizer/SKILL.md | — |
| `legal-advisor` | legal-advisor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/legal-advisor/SKILL.md | — |
| `leiloeiro-avaliacao` | leiloeiro-avaliacao | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-avaliacao/SKILL.md | — |
| `leiloeiro-edital` | leiloeiro-edital | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-edital/SKILL.md | — |
| `leiloeiro-ia` | leiloeiro-ia | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-ia/SKILL.md | — |
| `leiloeiro-juridico` | leiloeiro-juridico | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-juridico/SKILL.md | — |
| `leiloeiro-mercado` | leiloeiro-mercado | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-mercado/SKILL.md | — |
| `leiloeiro-risco` | leiloeiro-risco | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/leiloeiro-risco/SKILL.md | — |
| `lemmaly` | lemmaly | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lemmaly/SKILL.md | morsechimwai/lemmaly, morsechimwai/lemmaly.git |
| `lesson-generator` | lesson-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lesson-generator/SKILL.md | dair-ai/dair-academy-plugins |
| `lex` | lex | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lex/SKILL.md | — |
| `lightning-architecture-review` | lightning-architecture-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lightning-architecture-review/SKILL.md | 8144225309/SuperScalar |
| `lightning-channel-factories` | lightning-channel-factories | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lightning-channel-factories/SKILL.md | 8144225309/SuperScalar |
| `lightning-factory-explainer` | lightning-factory-explainer | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/lightning-factory-explainer/SKILL.md | 8144225309/SuperScalar |
| `linear-automation` | linear-automation | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/linear-automation/SKILL.md | — |
| `linear-skill` | linear-claude-skill | wrsmith108 | ledger | — | https://github.com/wrsmith108/linear-claude-skill | wrsmith108/linear-claude-skill |
| `live-api-dev` | gemini-live-api-dev | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gemini-live-api-dev/SKILL.md | google-gemini/gemini-skills |
| `monitor` | claude-monitor | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-monitor/SKILL.md | — |
| `omni-flash-api` | gemini-omni-flash-api | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/gemini-omni-flash-api/SKILL.md | google-gemini/gemini-skills |
| `profiles` | codex-profiles | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codex-profiles/SKILL.md | Ducksss/codex-profiles |
| `review` | codex-review | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codex-review/SKILL.md | BenedictKing/codex-review |
| `scientific-skills` | claude-scientific-skills | K-Dense-AI | ledger | Compatible | https://github.com/K-Dense-AI/claude-scientific-skills | K-Dense-AI/claude-scientific-skills |
| `sdk` | copilot-sdk | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/copilot-sdk/SKILL.md | en/copilot, github/copilot-sdk |
| `settings-audit` | claude-settings-audit | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/claude-settings-audit/SKILL.md | — |
| `skill-00-andruia-consultant` | 00-andruia-consultant | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/00-andruia-consultant/SKILL.md | — |
| `skill-007` | 007 | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/007/SKILL.md | — |
| `skill-10-andruia-skill-smith` | 10-andruia-skill-smith | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/10-andruia-skill-smith/SKILL.md | — |
| `skill-20-andruia-niche-intelligence` | 20-andruia-niche-intelligence | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/20-andruia-niche-intelligence/SKILL.md | — |
| `skill-2slides-ppt-generator` | 2slides-ppt-generator | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/2slides-ppt-generator/SKILL.md | 2slides/slides-generation-2slides-skills |
| `skill-3d-web-experience` | 3d-web-experience | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/3d-web-experience/SKILL.md | — |
| `speed-reader` | claude-speed-reader | SeanZoR | ledger | Compatible | https://github.com/SeanZoR/claude-speed-reader | SeanZoR/claude-speed-reader |
| `subagent` | codex-subagent | sickn33 | git-author | — | https://github.com/sickn33/antigravity-awesome-skills/blob/main/skills/codex-subagent/SKILL.md | davidondrej/skills |
| `taste` | gpt-taste | Leonxlnx/taste-skill | ledger | Not declared upstream | https://github.com/Leonxlnx/taste-skill | — |
| `win11-speckit-update-skill` | claude-win11-speckit-update-skill | NotMyself | ledger | Compatible | https://github.com/NotMyself/claude-win11-speckit-update-skill | NotMyself/claude-win11-speckit-update-skill |