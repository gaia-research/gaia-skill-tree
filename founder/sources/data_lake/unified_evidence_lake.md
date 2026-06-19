# Gaia Trust Methodology: Unified Evidence Data Lake

This unified data lake compiles all evidence dumps (Tiers 1★ to 6★) and specialized collector findings into a single source of truth indexed by skill ID.

## Table of Contents

- [mattpocock/skills (Tier 6★)](#skill-mattpocockskills)
- [ruvnet/ruflo (Tier 6★)](#skill-ruvnetruflo)
- [garrytan/gstack (Tier 5★)](#skill-garrytangstack)
- [mattpocock/engineering (Tier 5★)](#skill-mattpocockengineering)
- [obra/superpowers (Tier 5★)](#skill-obrasuperpowers)
- [ruvnet/agentdb (Tier 5★)](#skill-ruvnetagentdb)
- [garrytan/benchmark (Tier 4★)](#skill-garrytanbenchmark)
- [garrytan/canary (Tier 4★)](#skill-garrytancanary)
- [garrytan/cso (Tier 4★)](#skill-garrytancso)
- [garrytan/design-consultation (Tier 4★)](#skill-garrytandesign-consultation)
- [garrytan/design-html (Tier 4★)](#skill-garrytandesign-html)
- [garrytan/design-shotgun (Tier 4★)](#skill-garrytandesign-shotgun)
- [garrytan/document-generate (Tier 4★)](#skill-garrytandocument-generate)
- [garrytan/garrytan (Tier 4★)](#skill-garrytangarrytan)
- [garrytan/investigate (Tier 4★)](#skill-garrytaninvestigate)
- [garrytan/land-and-deploy (Tier 4★)](#skill-garrytanland-and-deploy)
- [garrytan/office-hours (Tier 4★)](#skill-garrytanoffice-hours)
- [garrytan/plan-ceo-review (Tier 4★)](#skill-garrytanplan-ceo-review)
- [garrytan/plan-design-review (Tier 4★)](#skill-garrytanplan-design-review)
- [garrytan/plan-devex-review (Tier 4★)](#skill-garrytanplan-devex-review)
- [garrytan/plan-eng-review (Tier 4★)](#skill-garrytanplan-eng-review)
- [garrytan/qa (Tier 4★)](#skill-garrytanqa)
- [garrytan/review (Tier 4★)](#skill-garrytanreview)
- [garrytan/ship (Tier 4★)](#skill-garrytanship)
- [garrytan/skillify (Tier 4★)](#skill-garrytanskillify)
- [google-deepmind/alphafold_database_fetch_and_analyze (Tier 4★)](#skill-google-deepmindalphafold_database_fetch_and_analyze)
- [mattpocock/grill-me (Tier 4★)](#skill-mattpocockgrill-me)
- [mattpocock/handoff (Tier 4★)](#skill-mattpocockhandoff)
- [mattpocock/personal (Tier 4★)](#skill-mattpocockpersonal)
- [mattpocock/productivity (Tier 4★)](#skill-mattpocockproductivity)
- [mattpocock/ubiquitous-language (Tier 4★)](#skill-mattpocockubiquitous-language)
- [obra/dispatching-parallel-agents (Tier 4★)](#skill-obradispatching-parallel-agents)
- [obra/subagent-driven-development (Tier 4★)](#skill-obrasubagent-driven-development)
- [pbakaus/impeccable (Tier 4★)](#skill-pbakausimpeccable)
- [ruvnet/flow-nexus (Tier 4★)](#skill-ruvnetflow-nexus)
- [ruvnet/github-suite (Tier 4★)](#skill-ruvnetgithub-suite)
- [ruvnet/hive-mind-coordination (Tier 4★)](#skill-ruvnethive-mind-coordination)
- [ruvnet/ruflo-v3 (Tier 4★)](#skill-ruvnetruflo-v3)
- [xquik-dev/hermes-tweet (Tier 4★)](#skill-xquik-devhermes-tweet)
- [0xdarkmatter/pytest-patterns (Tier 3★)](#skill-0xdarkmatterpytest-patterns)
- [addy-osmani/performance-optimization (Tier 3★)](#skill-addy-osmaniperformance-optimization)
- [addy-osmani/test-driven-development (Tier 3★)](#skill-addy-osmanitest-driven-development)
- [garrytan/benchmark-models (Tier 3★)](#skill-garrytanbenchmark-models)
- [garrytan/browse (Tier 3★)](#skill-garrytanbrowse)
- [garrytan/codex (Tier 3★)](#skill-garrytancodex)
- [garrytan/design-review (Tier 3★)](#skill-garrytandesign-review)
- [garrytan/devex-review (Tier 3★)](#skill-garrytandevex-review)
- [garrytan/guard (Tier 3★)](#skill-garrytanguard)
- [garrytan/health (Tier 3★)](#skill-garrytanhealth)
- [garrytan/learn (Tier 3★)](#skill-garrytanlearn)
- [garrytan/make-pdf (Tier 3★)](#skill-garrytanmake-pdf)
- [garrytan/pair-agent (Tier 3★)](#skill-garrytanpair-agent)
- [garrytan/retro (Tier 3★)](#skill-garrytanretro)
- [garrytan/scrape (Tier 3★)](#skill-garrytanscrape)
- [google-deepmind/alphagenome_single_variant_analysis (Tier 3★)](#skill-google-deepmindalphagenome_single_variant_analysis)
- [google-deepmind/protein_sequence_msa (Tier 3★)](#skill-google-deepmindprotein_sequence_msa)
- [huggingface/huggingface-llm-trainer (Tier 3★)](#skill-huggingfacehuggingface-llm-trainer)
- [huggingface/huggingface-vision-trainer (Tier 3★)](#skill-huggingfacehuggingface-vision-trainer)
- [karpathy/autoresearch (Tier 3★)](#skill-karpathyautoresearch)
- [mattpocock/caveman (Tier 3★)](#skill-mattpocockcaveman)
- [mattpocock/grill-with-docs (Tier 3★)](#skill-mattpocockgrill-with-docs)
- [mattpocock/improve-codebase-architecture (Tier 3★)](#skill-mattpocockimprove-codebase-architecture)
- [mattpocock/obsidian-vault (Tier 3★)](#skill-mattpocockobsidian-vault)
- [mattpocock/prototype (Tier 3★)](#skill-mattpocockprototype)
- [mattpocock/setup-matt-pocock-skills (Tier 3★)](#skill-mattpococksetup-matt-pocock-skills)
- [mattpocock/to-issues (Tier 3★)](#skill-mattpocockto-issues)
- [mattpocock/triage (Tier 3★)](#skill-mattpococktriage)
- [mattpocock/write-a-skill (Tier 3★)](#skill-mattpocockwrite-a-skill)
- [obra/requesting-code-review (Tier 3★)](#skill-obrarequesting-code-review)
- [obra/systematic-debugging (Tier 3★)](#skill-obrasystematic-debugging)
- [ruvnet/dual-mode (Tier 3★)](#skill-ruvnetdual-mode)
- [ruvnet/reasoningbank (Tier 3★)](#skill-ruvnetreasoningbank)
- [santifer/career-ops (Tier 3★)](#skill-santifercareer-ops)
- [sickn33/mcp-builder (Tier 3★)](#skill-sickn33mcp-builder)
- [Manavarya09/design-extract (Tier 2★)](#skill-Manavarya09design-extract)
- [Taoidle/plan-decompose-gh-plan-cascade (Tier 2★)](#skill-Taoidleplan-decompose-gh-plan-cascade)
- [anthropic/pptx (Tier 2★)](#skill-anthropicpptx)
- [anthropic/skill-creator (Tier 2★)](#skill-anthropicskill-creator)
- [bradautomates/claude-video (Tier 2★)](#skill-bradautomatesclaude-video)
- [browser-use/browser-harness (Tier 2★)](#skill-browser-usebrowser-harness)
- [browserbase/stagehand (Tier 2★)](#skill-browserbasestagehand)
- [changkun/plan-decompose-gh-wallfacer (Tier 2★)](#skill-changkunplan-decompose-gh-wallfacer)
- [firecrawl/firecrawl (Tier 2★)](#skill-firecrawlfirecrawl)
- [gaiabot/gaia-triage (Tier 2★)](#skill-gaiabotgaia-triage)
- [gaiabot/repo-docs-before-pr (Tier 2★)](#skill-gaiabotrepo-docs-before-pr)
- [garrytan/careful (Tier 2★)](#skill-garrytancareful)
- [garrytan/context-restore (Tier 2★)](#skill-garrytancontext-restore)
- [garrytan/context-save (Tier 2★)](#skill-garrytancontext-save)
- [garrytan/document-release (Tier 2★)](#skill-garrytandocument-release)
- [garrytan/freeze (Tier 2★)](#skill-garrytanfreeze)
- [garrytan/gstack-upgrade (Tier 2★)](#skill-garrytangstack-upgrade)
- [garrytan/landing-report (Tier 2★)](#skill-garrytanlanding-report)
- [garrytan/open-gstack-browser (Tier 2★)](#skill-garrytanopen-gstack-browser)
- [garrytan/plan-tune (Tier 2★)](#skill-garrytanplan-tune)
- [garrytan/qa-only (Tier 2★)](#skill-garrytanqa-only)
- [garrytan/setup-browser-cookies (Tier 2★)](#skill-garrytansetup-browser-cookies)
- [garrytan/setup-deploy (Tier 2★)](#skill-garrytansetup-deploy)
- [garrytan/setup-gbrain (Tier 2★)](#skill-garrytansetup-gbrain)
- [garrytan/sync-gbrain (Tier 2★)](#skill-garrytansync-gbrain)
- [garrytan/unfreeze (Tier 2★)](#skill-garrytanunfreeze)
- [getagentseal/codeburn (Tier 2★)](#skill-getagentsealcodeburn)
- [glincker/readme-generator (Tier 2★)](#skill-glinckerreadme-generator)
- [google-deepmind/chembl_database (Tier 2★)](#skill-google-deepmindchembl_database)
- [google-deepmind/clinical_trials_database (Tier 2★)](#skill-google-deepmindclinical_trials_database)
- [google-deepmind/clinvar_database (Tier 2★)](#skill-google-deepmindclinvar_database)
- [google-deepmind/dbsnp_database (Tier 2★)](#skill-google-deepminddbsnp_database)
- [google-deepmind/embl_ebi_ols (Tier 2★)](#skill-google-deepmindembl_ebi_ols)
- [google-deepmind/encode_ccres_database (Tier 2★)](#skill-google-deepmindencode_ccres_database)
- [google-deepmind/ensembl_database (Tier 2★)](#skill-google-deepmindensembl_database)
- [google-deepmind/foldseek_structural_search (Tier 2★)](#skill-google-deepmindfoldseek_structural_search)
- [google-deepmind/gnomad_database (Tier 2★)](#skill-google-deepmindgnomad_database)
- [google-deepmind/gtex_database (Tier 2★)](#skill-google-deepmindgtex_database)
- [google-deepmind/human_protein_atlas_database (Tier 2★)](#skill-google-deepmindhuman_protein_atlas_database)
- [google-deepmind/interpro_database (Tier 2★)](#skill-google-deepmindinterpro_database)
- [google-deepmind/jaspar_database (Tier 2★)](#skill-google-deepmindjaspar_database)
- [google-deepmind/literature_search_arxiv (Tier 2★)](#skill-google-deepmindliterature_search_arxiv)
- [google-deepmind/literature_search_biorxiv (Tier 2★)](#skill-google-deepmindliterature_search_biorxiv)
- [google-deepmind/literature_search_europepmc (Tier 2★)](#skill-google-deepmindliterature_search_europepmc)
- [google-deepmind/literature_search_openalex (Tier 2★)](#skill-google-deepmindliterature_search_openalex)
- [google-deepmind/ncbi_sequence_fetch (Tier 2★)](#skill-google-deepmindncbi_sequence_fetch)
- [google-deepmind/openfda_database (Tier 2★)](#skill-google-deepmindopenfda_database)
- [google-deepmind/opentargets_database (Tier 2★)](#skill-google-deepmindopentargets_database)
- [google-deepmind/pdb_database (Tier 2★)](#skill-google-deepmindpdb_database)
- [google-deepmind/protein_sequence_similarity_search (Tier 2★)](#skill-google-deepmindprotein_sequence_similarity_search)
- [google-deepmind/pubchem_database (Tier 2★)](#skill-google-deepmindpubchem_database)
- [google-deepmind/pubmed_database (Tier 2★)](#skill-google-deepmindpubmed_database)
- [google-deepmind/pymol (Tier 2★)](#skill-google-deepmindpymol)
- [google-deepmind/quickgo_database (Tier 2★)](#skill-google-deepmindquickgo_database)
- [google-deepmind/reactome_database (Tier 2★)](#skill-google-deepmindreactome_database)
- [google-deepmind/science_skills_common (Tier 2★)](#skill-google-deepmindscience_skills_common)
- [google-deepmind/string_database (Tier 2★)](#skill-google-deepmindstring_database)
- [google-deepmind/ucsc_conservation_and_tfbs (Tier 2★)](#skill-google-deepminducsc_conservation_and_tfbs)
- [google-deepmind/unibind_database (Tier 2★)](#skill-google-deepmindunibind_database)
- [google-deepmind/uniprot_database (Tier 2★)](#skill-google-deepminduniprot_database)
- [google-deepmind/uv (Tier 2★)](#skill-google-deepminduv)
- [google-deepmind/workflow_skill_creator (Tier 2★)](#skill-google-deepmindworkflow_skill_creator)
- [huggingface/hf-cli (Tier 2★)](#skill-huggingfacehf-cli)
- [huggingface/huggingface-datasets (Tier 2★)](#skill-huggingfacehuggingface-datasets)
- [huggingface/huggingface-papers (Tier 2★)](#skill-huggingfacehuggingface-papers)
- [huggingface/transformers-js (Tier 2★)](#skill-huggingfacetransformers-js)
- [intelligentcode-ai/database-engineer (Tier 2★)](#skill-intelligentcode-aidatabase-engineer)
- [intelligentcode-ai/devops-engineer (Tier 2★)](#skill-intelligentcode-aidevops-engineer)
- [intelligentcode-ai/mcp-client (Tier 2★)](#skill-intelligentcode-aimcp-client)
- [intelligentcode-ai/parallel-execution (Tier 2★)](#skill-intelligentcode-aiparallel-execution)
- [intelligentcode-ai/release (Tier 2★)](#skill-intelligentcode-airelease)
- [intelligentcode-ai/requirements-engineer (Tier 2★)](#skill-intelligentcode-airequirements-engineer)
- [intelligentcode-ai/security-engineer (Tier 2★)](#skill-intelligentcode-aisecurity-engineer)
- [intelligentcode-ai/user-tester (Tier 2★)](#skill-intelligentcode-aiuser-tester)
- [langgenius/backend-code-review (Tier 2★)](#skill-langgeniusbackend-code-review)
- [langgenius/component-refactoring (Tier 2★)](#skill-langgeniuscomponent-refactoring)
- [langgenius/e2e-cucumber-playwright (Tier 2★)](#skill-langgeniuse2e-cucumber-playwright)
- [langgenius/frontend-code-review (Tier 2★)](#skill-langgeniusfrontend-code-review)
- [langgenius/frontend-testing (Tier 2★)](#skill-langgeniusfrontend-testing)
- [laravel/upgrade-laravel-v13 (Tier 2★)](#skill-laravelupgrade-laravel-v13)
- [martin-stepanoski/nielsen-heuristics-audit (Tier 2★)](#skill-martin-stepanoskinielsen-heuristics-audit)
- [mattpocock/diagnose (Tier 2★)](#skill-mattpocockdiagnose)
- [mattpocock/edit-article (Tier 2★)](#skill-mattpocockedit-article)
- [mattpocock/to-prd (Tier 2★)](#skill-mattpocockto-prd)
- [mattpocock/zoom-out (Tier 2★)](#skill-mattpocockzoom-out)
- [mbtiongson1/gaia-audit (Tier 2★)](#skill-mbtiongson1gaia-audit)
- [mbtiongson1/gaia-bot-curate (Tier 2★)](#skill-mbtiongson1gaia-bot-curate)
- [mbtiongson1/gaia-curate (Tier 2★)](#skill-mbtiongson1gaia-curate)
- [mbtiongson1/gaia-curation-review (Tier 2★)](#skill-mbtiongson1gaia-curation-review)
- [mbtiongson1/gaia-docs-sync (Tier 2★)](#skill-mbtiongson1gaia-docs-sync)
- [mbtiongson1/gaia-draft-curate (Tier 2★)](#skill-mbtiongson1gaia-draft-curate)
- [mbtiongson1/gaia-integrity (Tier 2★)](#skill-mbtiongson1gaia-integrity)
- [mbtiongson1/gaia-meta-audit (Tier 2★)](#skill-mbtiongson1gaia-meta-audit)
- [mbtiongson1/gaia-preview (Tier 2★)](#skill-mbtiongson1gaia-preview)
- [mbtiongson1/gaia-triage (Tier 2★)](#skill-mbtiongson1gaia-triage)
- [mbtiongson1/gaia-wiki-sync (Tier 2★)](#skill-mbtiongson1gaia-wiki-sync)
- [mbtiongson1/graphify-triage (Tier 2★)](#skill-mbtiongson1graphify-triage)
- [obra/brainstorming (Tier 2★)](#skill-obrabrainstorming)
- [obra/executing-plans (Tier 2★)](#skill-obraexecuting-plans)
- [obra/finishing-a-development-branch (Tier 2★)](#skill-obrafinishing-a-development-branch)
- [obra/receiving-code-review (Tier 2★)](#skill-obrareceiving-code-review)
- [obra/using-git-worktrees (Tier 2★)](#skill-obrausing-git-worktrees)
- [obra/verification-before-completion (Tier 2★)](#skill-obraverification-before-completion)
- [obra/writing-plans (Tier 2★)](#skill-obrawriting-plans)
- [openai/few-shot-learning (Tier 2★)](#skill-openaifew-shot-learning)
- [openai/self-consistency (Tier 2★)](#skill-openaiself-consistency)
- [pexp13/sentiment-analysis (Tier 2★)](#skill-pexp13sentiment-analysis)
- [ruvnet/agentdb-memory-patterns (Tier 2★)](#skill-ruvnetagentdb-memory-patterns)
- [ruvnet/agentdb-optimization (Tier 2★)](#skill-ruvnetagentdb-optimization)
- [ruvnet/agentdb-vector-search (Tier 2★)](#skill-ruvnetagentdb-vector-search)
- [ruvnet/agentic-jujutsu (Tier 2★)](#skill-ruvnetagentic-jujutsu)
- [ruvnet/browser (Tier 2★)](#skill-ruvnetbrowser)
- [ruvnet/dual-collect (Tier 2★)](#skill-ruvnetdual-collect)
- [ruvnet/dual-coordinate (Tier 2★)](#skill-ruvnetdual-coordinate)
- [ruvnet/dual-spawn (Tier 2★)](#skill-ruvnetdual-spawn)
- [ruvnet/github-multi-repo (Tier 2★)](#skill-ruvnetgithub-multi-repo)
- [ruvnet/github-project-management (Tier 2★)](#skill-ruvnetgithub-project-management)
- [ruvnet/hooks-automation (Tier 2★)](#skill-ruvnethooks-automation)
- [ruvnet/pair-programming (Tier 2★)](#skill-ruvnetpair-programming)
- [ruvnet/performance-analysis (Tier 2★)](#skill-ruvnetperformance-analysis)
- [ruvnet/reasoningbank-agentdb (Tier 2★)](#skill-ruvnetreasoningbank-agentdb)
- [ruvnet/skill-builder (Tier 2★)](#skill-ruvnetskill-builder)
- [ruvnet/stream-chain (Tier 2★)](#skill-ruvnetstream-chain)
- [ruvnet/v3-cli-modernization (Tier 2★)](#skill-ruvnetv3-cli-modernization)
- [ruvnet/v3-core-implementation (Tier 2★)](#skill-ruvnetv3-core-implementation)
- [ruvnet/v3-ddd-architecture (Tier 2★)](#skill-ruvnetv3-ddd-architecture)
- [ruvnet/v3-integration-deep (Tier 2★)](#skill-ruvnetv3-integration-deep)
- [ruvnet/v3-mcp-optimization (Tier 2★)](#skill-ruvnetv3-mcp-optimization)
- [ruvnet/v3-memory-unification (Tier 2★)](#skill-ruvnetv3-memory-unification)
- [ruvnet/v3-performance-optimization (Tier 2★)](#skill-ruvnetv3-performance-optimization)
- [ruvnet/v3-security-overhaul (Tier 2★)](#skill-ruvnetv3-security-overhaul)
- [ruvnet/verification-quality (Tier 2★)](#skill-ruvnetverification-quality)
- [ruvnet/worker-benchmarks (Tier 2★)](#skill-ruvnetworker-benchmarks)
- [ruvnet/worker-integration (Tier 2★)](#skill-ruvnetworker-integration)
- [sickn33/ai-dev-jobs-mcp (Tier 2★)](#skill-sickn33ai-dev-jobs-mcp)
- [sickn33/n8n-mcp-tools-expert (Tier 2★)](#skill-sickn33n8n-mcp-tools-expert)
- [spring-ai/readme-generate (Tier 2★)](#skill-spring-aireadme-generate)
- [upsonic/unittest-generator (Tier 2★)](#skill-upsonicunittest-generator)
- [vercel/find-skills (Tier 2★)](#skill-vercelfind-skills)
- [yundu-ai/mcp-tool-developer (Tier 2★)](#skill-yundu-aimcp-tool-developer)
- [devin-ai/autonomous-swe (Tier 1★)](#skill-devin-aiautonomous-swe)
- [gooseworks/notte-browser (Tier 1★)](#skill-gooseworksnotte-browser)
- [huggingface/semantic-cache (Tier 1★)](#skill-huggingfacesemantic-cache)
- [nexu-io/open-design (Tier 1★)](#skill-nexu-ioopen-design)
- [nousresearch/feed-monitoring (Tier 1★)](#skill-nousresearchfeed-monitoring)
- [ruvnet/agentdb-advanced (Tier 1★)](#skill-ruvnetagentdb-advanced)
- [ruvnet/agentdb-learning (Tier 1★)](#skill-ruvnetagentdb-learning)
- [ruvnet/flow-nexus-neural (Tier 1★)](#skill-ruvnetflow-nexus-neural)
- [ruvnet/flow-nexus-platform (Tier 1★)](#skill-ruvnetflow-nexus-platform)
- [ruvnet/flow-nexus-swarm (Tier 1★)](#skill-ruvnetflow-nexus-swarm)
- [ruvnet/github-code-review (Tier 1★)](#skill-ruvnetgithub-code-review)
- [ruvnet/github-workflow-automation (Tier 1★)](#skill-ruvnetgithub-workflow-automation)
- [ruvnet/reasoningbank-intelligence (Tier 1★)](#skill-ruvnetreasoningbank-intelligence)
- [ruvnet/sparc-methodology (Tier 1★)](#skill-ruvnetsparc-methodology)
- [ruvnet/swarm-advanced (Tier 1★)](#skill-ruvnetswarm-advanced)
- [ruvnet/swarm-orchestration (Tier 1★)](#skill-ruvnetswarm-orchestration)
- [ruvnet/v3-swarm-coordination (Tier 1★)](#skill-ruvnetv3-swarm-coordination)
- [safishamsi/graphify (Tier 1★)](#skill-safishamsigraphify)
- [stanfordnlp/dspy (Tier 1★)](#skill-stanfordnlpdspy)
- [yonatangross/orchestkit-rag (Tier 1★)](#skill-yonatangrossorchestkit-rag)

---

## Skill: <a name="skill-mattpocockskills"></a>`mattpocock/skills`

- **Name:** Matt Pocock Skills
- **Contributor:** `mattpocock`
- **Tier:** 6★
- **Primary Repository:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** The ultimate Matt Pocock skill suite capstone. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/352](https://github.com/mbtiongson1/gaia-skill-tree/pull/352)
- **Date:** 2026-05-22
- **Verified Stars:** 6 stars
- **Description:** Peer-reviewed ultimate capstone suite consolidation. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [mattpocock/skills](https://github.com/mattpocock/skills)
* **Benchmark:** Process Adherence & Safety Constraints
* **Score:** Qualitative improvement in model drift reduction
* **Date:** Mid-2026
* **Setup Description:** Evaluated on how effectively it structures agent behavior. It forces strict verticals (TDD, issue-triage, PRD generation, and zoom-out map creation), preventing models from hallucinating large parallel changes and keeping code generation within tight test feedback loops.

### Peer Reviews & Audits

* **Target Repository:** [mattpocock/skills](https://github.com/mattpocock/skills)
* **Review URL:** [G7 Trust Taxonomy Audit - mattpocock/skills Re-Score](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/g7-mattpocock-audit/_issue_comment.md)
* **Author:** G7 Trust Taxonomy Audit (Orchestrator Phase 1 Closeout)
* **Date:** June 17, 2026
* **Summary of Findings:**
  * **High Adoption:** Clear S-grade on Trust Magnitude (132k stars, 4.7M npm weekly downloads, composites like Composio).
  * **Apex Gate Failure:** Demoted from 6★ to 5★ provisional under G7 cutover. Failed 5 of 9 apex predicates: lack of tenure (26 days old vs. 180 required), depth-2 reachability, and missing cross-org verifier attestations.
  * **Fusion Refinement:** The audit recommended filtering out `role: variant` components from the fusion score to avoid suite-padding games.

---

### Academic Papers & Preprints

*   **Paper Title:** SoK: Agentic Skills — Beyond Tool Use in LLM Agents
*   **Authors:** Yanna Jiang, Delong Li, Haiyu Deng, Baihe Ma, Xu Wang, Qin Wang, and Guangsheng Yu
*   **Publication URL:** [https://arxiv.org/abs/2602.20867](https://arxiv.org/abs/2602.20867)
*   **Publication Date:** February 24, 2026
*   **Citation Count:** ~52 citations
*   **Summary & Relevance:** 
    This Systematization of Knowledge (SoK) paper investigates the shift from simple raw tool calls to "agentic skills"—packaged procedural expertise (such as Matt Pocock's skills framework). It formalizes how skills structure agent workflows, allow multi-turn planning, decouple execution from raw prompts, and enhance consistency.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills) (reviewed extensively on Medium under "Real Engineering Claude Code Skills")
*   **Author/Publisher:** Matt Pocock
*   **Publication Date:** Early 2026
*   **Metrics:** Extremely high viral traction in the Claude Code community.
*   **Description:** A library of 19 engineering skills (installed via `npx skills@latest add mattpocock/skills`). It includes `/grill-me` and `/grill-with-docs` designed to force AI agents to pause and perform deep structural question-and-answer interviews before coding. It also handles Test-Driven Development (TDD) cycles, architectural reviews, and maintains project files like `CONTEXT.md` and ADRs.

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **mattpocock/skills** | [mattpocock/skills Repo](https://github.com/mattpocock/skills) | **Active (200)** | Verified repository |

---

## Skill: <a name="skill-ruvnetruflo"></a>`ruvnet/ruflo`

- **Name:** Ruflo
- **Contributor:** `ruvnet`
- **Tier:** 6★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. Meets Class A threshold: ≥5 named skills registered across 6 generic buckets in Gaia. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [ruvnet/ruflo](https://github.com/ruvnet/ruflo) (rebranded from Claude Flow)
* **Benchmark:** SWE-bench (Swarm Solve Rate) & cost-routing
* **Score:** 84.8% solve rate (vendor claim); up to 75% API cost savings
* **Date:** February 2026
* **Setup Description:** Tested using multi-agent swarms with SONA adaptive memory routing. Simpler tasks are routed to lightweight models, and complex coding bugs are solved by fanning out specialized sub-agents with graph-based pathfinding, yielding high resolve rates on SWE-bench tasks.

### Peer Reviews & Audits

* **Target Repository:** [ruvnet/ruflo](https://github.com/ruvnet/ruflo)
* **Review URL:** [G7 Trust Taxonomy RFC](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/G7_TRUST_TAXONOMY_RFC.md)
* **Author:** G7 Trust Taxonomy Audit Group
* **Date:** June 16, 2026
* **Summary of Findings:**
  * **Swarm Orchestration:** Massive 47-component fusion capstone (TM = 489, Grade S).
  * **Apex Demotion:** Failed the 9-predicate Apex Gate due to lack of S-diversity in the descendant closure (its components topped out at A-grade, causing overall grade-bubbling to fail) and zero cross-org verifier signatures. Demoted to 5★ A-provisional.

---

### Academic Papers & Preprints

*   **Paper Title:** "Do Not Mention This to the User": Detecting and Understanding Malicious Agent Skills in the Wild (USENIX Security 2026)
*   **Authors:** Yi Liu, Zhihao Chen, Yanjun Zhang, Gelei Deng, Yuekang Li, Jianting Ning, and Leo Yu Zhang
*   **Publication URL:** [https://arxiv.org/abs/2602.06547](https://arxiv.org/abs/2602.06547)
*   **Publication Date:** February 2026 (v3 updated June 2026)
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Ruflo is a multi-agent swarm platform featuring the **Flow Nexus** workflow system. This security audit paper specifically studies and references Ruflo's Flow Nexus skill platform (`flow-nexus`) as a case study for evaluating malicious behaviors in third-party agent skill ecosystems. The authors analyze how layered permissions and credential harvesting are modeled inside agent skills.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code](https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code) (formerly Claude Flow)
*   **Author/Publisher:** Reuven Cohen (@ruvnet)
*   **Publication Date:** Mid 2025 / Updated WASM release early 2026
*   **Metrics:** Highlighted in multi-agent orchestration publications.
*   **Description:** Explores Ruflo (previously Claude Flow), a Rust/WASM-based multi-agent orchestration harness. It coordinates 60-100+ specialized agents in parallel (Architect, QA, Coder) via a high-performance shared memory layer (HNSW-indexed vector memory) to execute complex, multi-module software tasks using the SPARC methodology.

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **ruvnet/ruflo** | [ruvnet/ruflo Repo](https://github.com/ruvnet/ruflo) | **Active (200)** | Verified repository |
| | [Dev.to: Ruflo Blog](https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code) | **Broken (404)** | Missing/deleted article |
*   **`ruvnet/ruflo` Dev.to Article**:
    *   **URL**: `https://dev.to/ruvnet/ruflo-multi-agent-orchestration-for-claude-code`
*   **`ruvnet/ruflo` (Reddit and Dev.to links)**:
*   **`ruvnet/ruflo` Academic Paper Citation (`arxiv:2602.06547`)**:

---

## Skill: <a name="skill-garrytangstack"></a>`garrytan/gstack`

- **Name:** Founder Mode
- **Contributor:** `garrytan`
- **Tier:** 5★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/SKILL.md](https://github.com/garrytan/gstack/blob/main/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack](https://github.com/garrytan/gstack)
- **Date:** 2026-05-18
- **Verified Stars:** 110,930 stars
- **Description:** garrytan/gstack — 19 named garrytan skills registered in Gaia across 16 generic skill buckets; meets the >=5 named-skills threshold for Class A designation. Additionally: 98.9k GitHub stars, multi-platform adoption across 8+ runtimes (Claude Code, OpenAI Codex CLI, OpenCode, Cursor, Factory Droid, Slate, Kiro, Hermes). (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [garrytan/gstack](https://github.com/garrytan/gstack)
* **Benchmark:** gstack-model-benchmark & CWV metrics (GitHub: 108,000+ stars)
* **Score:** Qualitative LLM speed/cost/layout comparison; Core Web Vitals regression checks
* **Date:** March 2026
* **Setup Description:** Employs a CLI comparison tool (`gstack-model-benchmark`) that runs the same code prompts across models (GPT, Gemini, Claude) to compare cost, latency, and layout. Also integrates a `/benchmark` QA command tracking page speed and regression metrics.

### Peer Reviews & Audits

* **Target Repository:** [garrytan/gstack](https://github.com/garrytan/gstack)
* **Review URL:** [G7 Trust Taxonomy RFC](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/G7_TRUST_TAXONOMY_RFC.md)
* **Author:** G7 Trust Taxonomy Audit Group
* **Date:** June 16, 2026
* **Summary of Findings:**
  * **S-Grade Calibration:** Rated Grade S with TM = 318. Passed the S-diversity gate cleanly using 4 distinct evidence types: fusion-recipe (components), github-stars-own, peer-review, and founder-attested social-signal.
  * **Gold Standard:** Highlighted as a model implementation for how a highly-fused suite should justify its trust level via diverse external signals.

---

### Academic Papers & Preprints

*   **Paper Title:** Agentic Social Affordance Framework (ASAF): Agent Identity Design as a Collaboration Interface in Multi-Agent Systems
*   **Authors:** Meng-Han Lee
*   **Publication URL:** [https://arxiv.org/abs/2606.09832](https://arxiv.org/abs/2606.09832)
*   **Publication Date:** June 2026
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Garry Tan's `gstack` is a multi-agent startup builder utilizing defined personas (CEO, Designer, EM, QA). ASAF explores the "social affordance layer" of multi-agent networks, identifying `gstack` as a prime example of "roleplaying clusters." The study demonstrates how identity signaling and defined social personas improve collaborative governance and structure human-agent expectations.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/garrytan/gstack](https://github.com/garrytan/gstack) (featured in startup developer newsletters)
*   **Author/Publisher:** Garry Tan
*   **Publication Date:** March 2026
*   **Metrics:** Massive viral growth, exceeding 100,000 GitHub stars within weeks.
*   **Description:** GStack introduces a "Virtual Engineering Team" for Claude Code using 23+ persona-based slash commands (PM, QA, CEO, Release Manager). It enforces a strict startup iteration workflow (Think → Plan → Build → QA → Ship → Retro). It includes a automated QA capability using Playwright to run headless browser validation tests.

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **garrytan/gstack** | [garrytan/gstack Repo](https://github.com/garrytan/gstack) | **Active (200)** | Verified repository |
| | [garrytan/gstack SKILL.md](https://github.com/garrytan/gstack/blob/main/SKILL.md) | **Active (200)** | Verified skill definition file |

---

## Skill: <a name="skill-mattpocockengineering"></a>`mattpocock/engineering`

- **Name:** Engineering
- **Contributor:** `mattpocock`
- **Tier:** 5★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Consolidated engineering suite for Matt Pocock's skills. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-obrasuperpowers"></a>`obra/superpowers`

- **Name:** Superpowers
- **Contributor:** `obra`
- **Tier:** 5★
- **Primary Repository:** [https://github.com/obra/superpowers](https://github.com/obra/superpowers) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers](https://github.com/obra/superpowers)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers v5.1.0 — 196k+ GitHub stars, 17.5k forks, multi-platform adoption (Claude Code, Codex CLI, Factory Droid, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI). Most widely adopted AI agent discipline framework; confirms landmark methodology status. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [obra/superpowers](https://github.com/obra/superpowers)
* **Benchmark:** Framework Adoption (GitHub: 170,000+ stars)
* **Score:** v5.1.0 landmark adoption across Claude Code, Codex CLI, Cursor, and Gemini CLI
* **Date:** October 2025 (First release), updated Mid-2026
* **Setup Description:** Evaluated on the execution of complex multi-file codebase changes. Enforces a 7-stage development process (brainstorming, writing-plans, executing-plans, TDD, worktrees, code-review, and validation-before-completion) to eliminate agent path loops and code degradation.

### Peer Reviews & Audits

* **Target Repository:** [obra/superpowers](https://github.com/obra/superpowers)
* **Review URL:** [G7 Trust Taxonomy RFC](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/handovers/G7_TRUST_TAXONOMY_RFC.md)
* **Author:** Jesse Vincent (obra) / G7 Trust Taxonomy Audit Group
* **Date:** June 16, 2026
* **Summary of Findings:**
  * **Multi-Platform Support:** Upgraded from legacy B to S-grade (TM = 287) based on 196k stars, 3 cross-org verifier attestations, and an 11-origin fusion recipe.
  * **Enforced Discipline:** Enforces red-green-refactor TDD and planning phases on agents. Critiques note that the 7-stage workflow can introduce excessive process bloat and token consumption for small bug fixes.

---

### Academic Papers & Preprints

*   **Paper Title:** From Runnable to Shippable: Multi-Agent Test-Driven Development for Generating Full-Stack Web Applications from Requirements
*   **Authors:** Yuxuan Wan, Tingshuo Liang, Jiakai Xu, Jingyu Xiao, Yintong Huo, and Michael R. Lyu
*   **Publication URL:** [https://arxiv.org/abs/2605.17242](https://arxiv.org/abs/2605.17242)
*   **Publication Date:** May 17, 2026
*   **Citation Count:** ~0-6 citations
*   **Summary & Relevance:** 
    Superpowers by Jesse Vincent enforces strict planning, testing, and git branch discipline. This study introduces **TDDev**, a multi-agent framework implementing test-driven development (TDD) and verification loops. TDDev mirrors the core cycle of Superpowers by mandating a requirements-to-test specification phase, running sandboxed testing, and performing plan-driven refactoring before code is shipped.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/obra/superpowers](https://github.com/obra/superpowers) (detailed in DEV.to developer guides)
*   **Author/Publisher:** Jesse Vincent (@obra)
*   **Publication Date:** Early 2026
*   **Metrics:** Top-tier developer tool for agentic workflows.
*   **Description:** Details Superpowers, an opinionated framework that organizes development workflows for agents. It guides the model through brainstorming, planning, and TDD cycles before executing code. It is designed to prevent "context rot" and ensure the AI remains aligned with the human developer's specifications.

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **obra/superpowers** | [obra/superpowers Repo](https://github.com/obra/superpowers) | **Active (200)** | Verified repository |
| | [superpowers-marketplace Repo](https://github.com/obra/superpowers-marketplace) | **Active (200)** | Verified repository |

---

## Skill: <a name="skill-ruvnetagentdb"></a>`ruvnet/agentdb`

- **Name:** AgentDB
- **Contributor:** `ruvnet`
- **Tier:** 5★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-garrytanbenchmark"></a>`garrytan/benchmark`

- **Name:** Benchmark
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md](https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md](https://github.com/garrytan/gstack/blob/main/benchmark/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Web performance benchmarking that captures baseline metrics, compares current performance against those baselines, and identifies regressions in… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytancanary"></a>`garrytan/canary`

- **Name:** Canary
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/canary/SKILL.md](https://github.com/garrytan/gstack/blob/main/canary/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/canary/SKILL.md](https://github.com/garrytan/gstack/blob/main/canary/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Post-deployment monitoring that captures pre-release baseline screenshots, then continuously watches pages for console errors, performance… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2007.02500](https://arxiv.org/abs/2007.02500)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** Deep Learning for Anomaly Detection survey (Pang et al., ACM CSUR) â€” comprehensive benchmark of 30+ methods across fraud, intrusion, and medical anomaly detection. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytancso"></a>`garrytan/cso`

- **Name:** CSO
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/cso/SKILL.md](https://github.com/garrytan/gstack/blob/main/cso/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/cso/SKILL.md](https://github.com/garrytan/gstack/blob/main/cso/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Infrastructure-first security audit focusing on secrets archaeology, dependency supply chain, and CI/CD security. Includes OWASP Top 10, STRIDE… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/microsoft/PromptKit](https://github.com/microsoft/PromptKit)
- **Date:** 2026-04-30
- **Verified Stars:** 64 stars
- **Description:** microsoft/PromptKit (42 stars) — composable prompt components for security audits, code review, and bug investigation with any LLM. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandesign-consultation"></a>`garrytan/design-consultation`

- **Name:** Design Consultation
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/design-consultation/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-consultation/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/design-consultation/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-consultation/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Builds a complete design system by researching the product and competitors, then proposing a coherent package of typography, colours, spacing,… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandesign-html"></a>`garrytan/design-html`

- **Name:** Design HTML
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/design-html/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-html/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/design-html/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-html/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Generates production-quality, Pretext-native HTML/CSS with real text reflow and dynamic layout from approved design mockups, CEO plans, or user… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandesign-shotgun"></a>`garrytan/design-shotgun`

- **Name:** Design Shotgun
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-shotgun/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Rapid design exploration that generates multiple AI design variants, opens a comparison board for the user, collects structured feedback, and… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Production interactive design-grilling skill; walks decision tree with recommended answers, one question at a time. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Extended implementation with domain-model awareness: challenges language against CONTEXT.md, cross-references code, writes ADRs inline. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandocument-generate"></a>`garrytan/document-generate`

- **Name:** Document Generate
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md](https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md](https://github.com/garrytan/gstack/blob/main/document-generate/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Generates structured documentation using the Diataxis framework — tutorials, how-to guides, reference materials, and explanations — by thoroughly… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytangarrytan"></a>`garrytan/garrytan`

- **Name:** Autoplan
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/autoplan/SKILL.md](https://github.com/garrytan/gstack/blob/main/autoplan/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/autoplan/SKILL.md](https://github.com/garrytan/gstack/blob/main/autoplan/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). The definitive autonomous "Founder mode" review and decision suite. An auto-review pipeline that reads the full CEO, design, engineering, and DX… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytaninvestigate"></a>`garrytan/investigate`

- **Name:** Investigate
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md](https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md](https://github.com/garrytan/gstack/blob/main/investigate/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Systematic root-cause debugging enforcing an Iron Law — no fix without first identifying root cause — guiding through four phases: investigation,… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanland-and-deploy"></a>`garrytan/land-and-deploy`

- **Name:** Land and Deploy
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md](https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md](https://github.com/garrytan/gstack/blob/main/land-and-deploy/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Automates the final production shipping stages — merging a PR, monitoring CI/deploy completion, and verifying live site health through canary… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanoffice-hours"></a>`garrytan/office-hours`

- **Name:** Office Hours
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md](https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md](https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). YC-style startup and builder brainstorming. Startup mode uses six forcing questions (demand reality, status quo, desperate specificity, narrowest… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/1806.03822](https://arxiv.org/abs/1806.03822)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** SQuAD 2.0 — reading comprehension benchmark with 150K questions; modern LLMs exceed human F1 (90.9), providing rigorous reproducible evaluation. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/registry/named/garrytan/office-hours.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/registry/named/garrytan/office-hours.md)
- **Date:** 2026-04-30
- **Verified Stars:** 6 stars
- **Description:** Garry Tan /office-hours -- Q&A skill grounded in specific document sets and founder context. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanplan-ceo-review"></a>`garrytan/plan-ceo-review`

- **Name:** Plan CEO Review
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Rigorous product strategy and scope review in four modes — SCOPE EXPANSION, SELECTIVE EXPANSION, HOLD SCOPE, and SCOPE REDUCTION — evaluating… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanplan-design-review"></a>`garrytan/plan-design-review`

- **Name:** Plan Design Review
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Interactive, designer-led audit of UI/UX plans rating seven dimensions — information architecture, interaction states, user journey, AI slop risk,… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanplan-devex-review"></a>`garrytan/plan-devex-review`

- **Name:** Plan DevEx Review
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Interactive multi-pass DX review for developer-facing products — APIs, CLIs, SDKs, and libraries — scoring eight UX dimensions from onboarding to… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanplan-eng-review"></a>`garrytan/plan-eng-review`

- **Name:** Plan Eng Review
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Comprehensive, interactive architecture and implementation review before coding begins, systematically evaluating scope, architecture, code… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.09095](https://arxiv.org/abs/2203.09095)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** CodeReviewer (Microsoft) â€” pre-trained model for code review tasks; 28.7% BLEU improvement on comment generation and change quality prediction. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanqa"></a>`garrytan/qa`

- **Name:** QA
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/qa/SKILL.md](https://github.com/garrytan/gstack/blob/main/qa/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/qa/SKILL.md](https://github.com/garrytan/gstack/blob/main/qa/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Browser-driven web application testing that explores pages as a real user, documents bugs with annotated screenshots, fixes issues with atomic… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/zachblume/autospec](https://github.com/zachblume/autospec)
- **Date:** 2026-04-30
- **Verified Stars:** 61 stars
- **Description:** autospec — AI agent that takes a web app URL and autonomously QAs it, saving passing specs as E2E test code (59 stars, active). (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanreview"></a>`garrytan/review`

- **Name:** Review
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/review/SKILL.md](https://github.com/garrytan/gstack/blob/main/review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/review/SKILL.md](https://github.com/garrytan/gstack/blob/main/review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Pre-landing code review combining structured checklist analysis with specialist subagents covering testing, security, and performance — plus… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.09095](https://arxiv.org/abs/2203.09095)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** CodeReviewer (Microsoft) â€” pre-trained model for code review tasks; 28.7% BLEU improvement on comment generation and change quality prediction. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanship"></a>`garrytan/ship`

- **Name:** Ship
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/ship/SKILL.md](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/ship/SKILL.md](https://github.com/garrytan/gstack/blob/main/ship/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Automated end-to-end deployment workflow that merges the base branch, runs tests, reviews the diff, bumps the VERSION file, updates the CHANGELOG,… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanskillify"></a>`garrytan/skillify`

- **Name:** Skillify
- **Contributor:** `garrytan`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md](https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md](https://github.com/garrytan/gstack/blob/main/skillify/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Converts a freeform prompt, repo pattern, or workflow description into a complete, registry-ready named skill: writes the SKILL.md definition,… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2602.08004](https://arxiv.org/abs/2602.08004)
- **Date:** 2026-05-10
- **Trust Metric:** 85.0
- **Description:** Agent Skills data-driven analysis characterizes SKILL.md packages as an emerging infrastructure layer and quantifies common design, reuse, and safety patterns. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic skill-creator provides a reproducible workflow for creating, editing, evaluating, benchmarking, and optimizing agent skills. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-google-deepmindalphafold_database_fetch_and_analyze"></a>`google-deepmind/alphafold_database_fetch_and_analyze`

- **Name:** Alphafold-Database-Fetch-And-Analyze
- **Contributor:** `google-deepmind`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/alphafold_database_fetch_and_analyze/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/alphafold_database_fetch_and_analyze/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/alphafold_database_fetch_and_analyze/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/alphafold_database_fetch_and_analyze/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind alphafold_database_fetch_and_analyze science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Computational Biology Workflows. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mattpocockgrill-me"></a>`mattpocock/grill-me`

- **Name:** Grill Me
- **Contributor:** `mattpocock`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md)
- **Date:** 2026-05-15
- **Verified Stars:** 133,210 stars
- **Description:** Original implementation by Matt Pocock; viral engineering pattern for disciplined agent alignment. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockhandoff"></a>`mattpocock/handoff`

- **Name:** Handoff
- **Contributor:** `mattpocock`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff](https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** High-fidelity agent handoff and context compaction skill. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockpersonal"></a>`mattpocock/personal`

- **Name:** Personal
- **Contributor:** `mattpocock`
- **Tier:** 4★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Consolidated personal suite for Matt Pocock's skills. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockproductivity"></a>`mattpocock/productivity`

- **Name:** Productivity
- **Contributor:** `mattpocock`
- **Tier:** 4★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Consolidated productivity suite for Matt Pocock's skills. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockubiquitous-language"></a>`mattpocock/ubiquitous-language`

- **Name:** Ubiquitous Language
- **Contributor:** `mattpocock`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/ubiquitous-language/SKILL.md)
- **Date:** 2026-05-15
- **Verified Stars:** 133,210 stars
- **Description:** Original implementation by Matt Pocock; formalizes DDD principles for AI agent contexts. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-obradispatching-parallel-agents"></a>`obra/dispatching-parallel-agents`

- **Name:** Dispatching Parallel Agents
- **Contributor:** `obra`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/dispatching-parallel-agents/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrasubagent-driven-development"></a>`obra/subagent-driven-development`

- **Name:** Subagent-Driven Development
- **Contributor:** `obra`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-pbakausimpeccable"></a>`pbakaus/impeccable`

- **Name:** Impeccable
- **Contributor:** `pbakaus`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/SKILL.md](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/SKILL.md) (39,158 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable)
- **Date:** 2026-05-14
- **Verified Stars:** 39,158 stars
- **Description:** Paul Bakaus /impeccable -- Elite design vocabulary and audit tool with 23 specialized polishing commands. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
* **Benchmark:** UI polishing success & rule audit (GitHub: 38,000+ stars)
* **Score:** +59% layout/typography consistency improvement (qualitative user testing)
* **Date:** May 2026
* **Setup Description:** Runs an agentic design checker executing 23 specialized commands (e.g., `/audit`, `/polish`, `/typeset`) against generated frontend code. Audits code compliance against 44 deterministic rules (such as OKLCH color spacing, typographic hierarchy, and anti-slop guidelines).

### Peer Reviews & Audits

* **Target Repository:** [pbakaus/impeccable](https://github.com/pbakaus/impeccable)
* **Review URL:** [G7 Trust Source Report](file:///Users/marcotiongson/Documents/gaia-skill-tree/founder/sources/tier_4.md)
* **Author:** Paul Bakaus / G7 Trust Group
* **Date:** June 18, 2026
* **Summary of Findings:**
  * **UI Polishing:** Elite design and UX auditing tool (39k stars) that supersedes old Nielsen checklist audits. Uses 23 steering commands (like `/audit`, `/critique`, `/polish`) referencing OKLCH color and spatial rules to fight "AI slop."
  * **Model Limitations:** While the instructions steer agents effectively, reviews note that the final UI quality is still bounded by the capabilities of the agent's layout engine.

---

### Academic Papers & Preprints

*   **Paper Title:** DesignRepair: Dual-Stream Design Guideline-Aware Frontend Repair with Large Language Models (ICSE 2025)
*   **Authors:** Mingyue Yuan, Jieshan Chen, Zhenchang Xing, Aaron Quigley, Yuyu Luo, Tianqi Luo, Gelareh Mohammadi, Qinghua Lu, and Liming Zhu
*   **Publication URL:** [https://arxiv.org/abs/2411.01606](https://arxiv.org/abs/2411.01606)
*   **Publication Date:** November 2024
*   **Citation Count:** ~19 citations
*   **Summary & Relevance:** 
    Impeccable is a visual auditing and frontend polishing tool for AI agents. DesignRepair provides the theoretical backing for guideline-aware frontend repair. It introduces a dual-stream architecture (combining visual design rules and code structure) to automatically fix UI layout inconsistencies, color contrast errors, and design violations in generated frontend code, validating the efficacy of automated UX audits.

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable) (published on DEV.to and designer-developer blogs)
*   **Author/Publisher:** Paul Bakaus
*   **Publication Date:** Early 2026
*   **Metrics:** Widely adopted by frontend AI developers.
*   **Description:** Impeccable is a design-first skill library for AI coding assistants. Created by jQuery UI's founder, it aims to prevent generic AI designs. It provides rules to avoid common anti-patterns (system-default typography, nested cards, pure grays) and introduces commands like `/polish`, `/audit`, and `/critique` to ensure clean, customized layout and styling decisions.

### YouTube Showcase Videos

*   **Video Title:** [Every AI Website Looks the Same | Here's the Fix](https://www.youtube.com/watch?v=k5f2uP33u5g)
*   **Video URL:** `https://www.youtube.com/watch?v=k5f2uP33u5g`
*   **Channel Name:** Full Stack (Validated Third-Party Walkthrough)
*   **Description:** This video details the "Impeccable" design steering skill built by Paul Bakaus. It showcases how to use Impeccable's design vocabulary modules (colors, typography, responsive design, spatial layout) to steer AI coding assistants like Claude Code away from generic "AI slop" frontends.

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **pbakaus/impeccable** | [pbakaus/impeccable Repo](https://github.com/pbakaus/impeccable) | **Active (200)** | Verified repository |

---

## Skill: <a name="skill-ruvnetflow-nexus"></a>`ruvnet/flow-nexus`

- **Name:** Flow Nexus
- **Contributor:** `ruvnet`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetgithub-suite"></a>`ruvnet/github-suite`

- **Name:** GitHub Suite
- **Contributor:** `ruvnet`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnethive-mind-coordination"></a>`ruvnet/hive-mind-coordination`

- **Name:** Hive Mind Coordination
- **Contributor:** `ruvnet`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/ruvnet/ruflo/blob/main/.agents/skills/hive-mind/SKILL.md](https://github.com/ruvnet/ruflo/blob/main/.agents/skills/hive-mind/SKILL.md) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetruflo-v3"></a>`ruvnet/ruflo-v3`

- **Name:** Ruflo V3
- **Contributor:** `ruvnet`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-xquik-devhermes-tweet"></a>`xquik-dev/hermes-tweet`

- **Name:** Hermes Tweet
- **Contributor:** `xquik-dev`
- **Tier:** 4★
- **Primary Repository:** [https://github.com/Xquik-dev/hermes-tweet/blob/master/skills/hermes-tweet/SKILL.md](https://github.com/Xquik-dev/hermes-tweet/blob/master/skills/hermes-tweet/SKILL.md) (10 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/Xquik-dev/hermes-tweet](https://github.com/Xquik-dev/hermes-tweet)
- **Date:** 2026-05-15
- **Verified Stars:** 10 stars
- **Description:** Hermes Tweet provides an installable Hermes Agent X/Twitter skill and plugin for searching tweets, reading replies, looking up users, monitoring tweets, exporting followers, and gating post, reply, and DM actions. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-0xdarkmatterpytest-patterns"></a>`0xdarkmatter/pytest-patterns`

- **Name:** Pytest Patterns
- **Contributor:** `0xdarkmatter`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/aiskillstore/marketplace/blob/main/skills/0xdarkmatter/python-pytest-patterns/SKILL.md](https://github.com/aiskillstore/marketplace/blob/main/skills/0xdarkmatter/python-pytest-patterns/SKILL.md) (364 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/princeton-nlp/SWE-bench](https://github.com/princeton-nlp/SWE-bench)
- **Date:** 2026-04-28
- **Verified Stars:** 5,200 stars
- **Description:** SWE-bench Verified â€” open-source evaluation harness where agents fix GitHub issues by generating and passing test suites; full execution logs archived. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-addy-osmaniperformance-optimization"></a>`addy-osmani/performance-optimization`

- **Name:** Performance Optimization
- **Contributor:** `addy-osmani`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md) (62,101 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/performance-optimization/SKILL.md)
- **Date:** 2026-05-31
- **Verified Stars:** 62,101 stars
- **Description:** Addy Osmani's performance-optimization SKILL.md in agent-skills repo (47.2k stars, verified 2026-05-31). Defines a measurement-driven 5-step workflow (Measure → Identify → Fix → Verify → Guard) with explicit Core Web Vitals thresholds. Qualifies for Class A per META §2.1 large-scale adoption criterion. (backfilled — class-to-type migration)

#### E2: `github-stars`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-addy-osmanitest-driven-development"></a>`addy-osmani/test-driven-development`

- **Name:** Test-Driven Development
- **Contributor:** `addy-osmani`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md) (62,101 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md](https://github.com/addyosmani/agent-skills/blob/main/skills/test-driven-development/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 62,101 stars
- **Description:** Addy Osmani /test-driven-development slash command -- forces strict TDD workflow, stopping agents from skipping tests. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Matt Pocock /tdd -- Vertical-slice TDD enforcement with anti-horizontal-slicing rules. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-garrytanbenchmark-models"></a>`garrytan/benchmark-models`

- **Name:** Benchmark Models
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md](https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md](https://github.com/garrytan/gstack/blob/main/benchmark-models/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Runs a standardised prompt suite across multiple model versions, records latency and quality scores, and produces a ranked comparison table to… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.02176](https://arxiv.org/abs/2603.02176)
- **Date:** 2026-05-10
- **Trust Metric:** 85.0
- **Description:** AgentSkillOS paper introduces ecosystem-scale organization, orchestration, and benchmarking with a 30-task suite spanning data computation, documents, video, design, and web interaction. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic skill-creator explicitly includes measuring skill performance, benchmarking with variance analysis, and optimizing skill descriptions for triggering accuracy. (backfilled — class-to-type migration)

#### E4: `repo`
- **Source:** [https://github.com/ynulihao/AgentSkillOS](https://github.com/ynulihao/AgentSkillOS)
- **Date:** 2026-05-10
- **Verified Stars:** 428 stars
- **Description:** AgentSkillOS repository provides the reproducible retrieval/orchestration framework and benchmark implementation for 30 artifact-rich agent-skill tasks with Bradley-Terry scoring. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanbrowse"></a>`garrytan/browse`

- **Name:** Browse
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/browse/SKILL.md](https://github.com/garrytan/gstack/blob/main/browse/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/browse/SKILL.md](https://github.com/garrytan/gstack/blob/main/browse/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Drives a browser to a target URL, navigates multi-step user journeys, and captures screenshots or structured observations for downstream… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytancodex"></a>`garrytan/codex`

- **Name:** Codex
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/codex/SKILL.md](https://github.com/garrytan/gstack/blob/main/codex/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/codex/SKILL.md](https://github.com/garrytan/gstack/blob/main/codex/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Spins up a structured Claude-versus-Codex debate over a proposed implementation, with each agent mounting adversarial critiques, to surface hidden… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2305.14325](https://arxiv.org/abs/2305.14325)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Du et al. (2023) -- Improving Factuality and Reasoning through Multi-Agent Debate; +14% truthfulness on TruthfulQA and +6% on MMLU Reasoning over single-model greedy decoding baselines. (backfilled — class-to-type migration)

#### E3: `arxiv`
- **Source:** [https://arxiv.org/abs/2308.07201](https://arxiv.org/abs/2308.07201)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** ChatEval (Chan et al., 2023) -- role-play multi-agent debate framework for open-ended text quality evaluation; outperforms single LLM judges on correlation with human ratings across MT-Bench and Vicuna benchmarks. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandesign-review"></a>`garrytan/design-review`

- **Name:** Design Review
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/design-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/design-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/design-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Runs a structured UX audit over a product interface, scoring layout clarity, affordance, and accessibility against the Gstack design rubric to… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandevex-review"></a>`garrytan/devex-review`

- **Name:** DevEx Review
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/devex-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/devex-review/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/devex-review/SKILL.md](https://github.com/garrytan/gstack/blob/main/devex-review/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Audits CLI ergonomics, API surface clarity, and onboarding friction from a developer perspective, producing a scored report with prioritised fixes. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanguard"></a>`garrytan/guard`

- **Name:** Guard
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/guard/SKILL.md](https://github.com/garrytan/gstack/blob/main/guard/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/guard/SKILL.md](https://github.com/garrytan/gstack/blob/main/guard/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Applies configurable content and output guardrails to agent responses, flagging or blocking unsafe outputs and logging violations with structured… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.25176](https://arxiv.org/abs/2603.25176)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Prompt Attack Detection with LLM-as-a-Judge (2026) -- guardrail deployment framework for detecting jailbreaks and prompt injections under production latency constraints. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- **Date:** 2026-04-30
- **Verified Stars:** 6,463 stars
- **Description:** NeMo Guardrails -- open-source toolkit for adding programmable safety rails to LLM-based conversational systems; actively maintained. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanhealth"></a>`garrytan/health`

- **Name:** Health
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/health/SKILL.md](https://github.com/garrytan/gstack/blob/main/health/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/health/SKILL.md](https://github.com/garrytan/gstack/blob/main/health/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Executes the full automated test suite, collects pass/fail counts and coverage deltas, and surfaces any newly introduced failures with concise… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/princeton-nlp/SWE-bench](https://github.com/princeton-nlp/SWE-bench)
- **Date:** 2026-04-28
- **Verified Stars:** 5,200 stars
- **Description:** SWE-bench Verified â€” open-source evaluation harness where agents fix GitHub issues by generating and passing test suites; full execution logs archived. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanlearn"></a>`garrytan/learn`

- **Name:** Learn
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/learn/SKILL.md](https://github.com/garrytan/gstack/blob/main/learn/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/learn/SKILL.md](https://github.com/garrytan/gstack/blob/main/learn/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Reads the active memory store, consolidates new observations from the current session, deduplicates stale entries, and writes back an updated,… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** MemGPT â€” virtual context management system enabling LLMs to handle unbounded memory; benchmarked on multi-session dialogue and document QA. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanmake-pdf"></a>`garrytan/make-pdf`

- **Name:** Make PDF
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/make-pdf/SKILL.md](https://github.com/garrytan/gstack/blob/main/make-pdf/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/make-pdf/SKILL.md](https://github.com/garrytan/gstack/blob/main/make-pdf/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Converts markdown or structured data into a polished PDF document with consistent heading styles, table formatting, and page layout ready for… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanpair-agent"></a>`garrytan/pair-agent`

- **Name:** Pair Agent
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/pair-agent/SKILL.md](https://github.com/garrytan/gstack/blob/main/pair-agent/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/pair-agent/SKILL.md](https://github.com/garrytan/gstack/blob/main/pair-agent/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Wires a new MCP server into the Gstack agent environment, validates the tool manifest, and demonstrates round-trip invocation through a test prompt. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanretro"></a>`garrytan/retro`

- **Name:** Retro
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/retro/SKILL.md](https://github.com/garrytan/gstack/blob/main/retro/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/retro/SKILL.md](https://github.com/garrytan/gstack/blob/main/retro/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Synthesises commit history, PR comments, and issue notes into a written sprint retrospective covering wins, misses, root causes, and action items. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanscrape"></a>`garrytan/scrape`

- **Name:** Scrape
- **Contributor:** `garrytan`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md](https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md](https://github.com/garrytan/gstack/blob/main/scrape/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Fetches target URLs with a headless browser, parses structured data from rendered HTML, and returns clean JSON or markdown ready for downstream… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-google-deepmindalphagenome_single_variant_analysis"></a>`google-deepmind/alphagenome_single_variant_analysis`

- **Name:** Alphagenome-Single-Variant-Analysis
- **Contributor:** `google-deepmind`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/alphagenome_single_variant_analysis/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/alphagenome_single_variant_analysis/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/alphagenome_single_variant_analysis/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/alphagenome_single_variant_analysis/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind alphagenome_single_variant_analysis science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Computational Biology Workflows. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindprotein_sequence_msa"></a>`google-deepmind/protein_sequence_msa`

- **Name:** Protein-Sequence-Msa
- **Contributor:** `google-deepmind`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_msa/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_msa/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_msa/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_msa/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind protein_sequence_msa science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Computational Biology Workflows. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacehuggingface-llm-trainer"></a>`huggingface/huggingface-llm-trainer`

- **Name:** Hugging Face LLM Trainer
- **Contributor:** `huggingface`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/huggingface-llm-trainer/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/huggingface-llm-trainer/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2604.22783](https://arxiv.org/abs/2604.22783)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LARS (2026) -- Parameter Efficiency Is Not Memory Efficiency: Rethinking Fine-Tuning on-Device LLM Adaptation; reduces GPU memory footprint 33.54% vs LoRA. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/huggingface/peft](https://github.com/huggingface/peft)
- **Date:** 2026-04-30
- **Verified Stars:** 21,278 stars
- **Description:** HuggingFace PEFT -- state-of-the-art LoRA/QLoRA/IA3 fine-tuning; 100k+ stars, CI, active maintenance. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory)
- **Date:** 2026-04-30
- **Verified Stars:** 72,265 stars
- **Description:** LlamaFactory (ACL 2024) -- unified efficient fine-tuning of 100+ LLMs and VLMs; 50k+ stars, reproducible benchmarks. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacehuggingface-vision-trainer"></a>`huggingface/huggingface-vision-trainer`

- **Name:** Hugging Face Vision Trainer
- **Contributor:** `huggingface`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/huggingface-vision-trainer/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/huggingface-vision-trainer/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2005.12872](https://arxiv.org/abs/2005.12872)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** DETR (Carion et al., 2020) -- end-to-end object detection with transformers; eliminates hand-crafted anchor design and achieves COCO AP 42.0 with ResNet-50, matching Faster R-CNN with simplified pipeline. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/ultralytics/ultralytics](https://github.com/ultralytics/ultralytics)
- **Date:** 2026-04-30
- **Verified Stars:** 58,522 stars
- **Description:** Ultralytics YOLOv8 -- production real-time detection library; COCO AP 50.2 at 8ms inference, 25k+ GitHub stars, reproducible training and evaluation scripts for detection and segmentation. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-karpathyautoresearch"></a>`karpathy/autoresearch`

- **Name:** AutoResearch
- **Contributor:** `karpathy`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill/blob/main/SKILL.md](https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill/blob/main/SKILL.md) (136 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- **Date:** 2026-06-02
- **Verified Stars:** 87,404 stars
- **Description:** Karpathy's autoresearch repo serving as the evidence/inspiration for the skill. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/firecrawl/firecrawl-mcp-server](https://github.com/firecrawl/firecrawl-mcp-server)
- **Date:** 2026-05-14
- **Verified Stars:** 6,613 stars
- **Description:** Firecrawl's Map and Crawl logic combined with the firecrawl_agent tool enables autonomous multi-source web research. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill](https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill)
- **Date:** 2026-04-30
- **Verified Stars:** 136 stars
- **Description:** Community reproduction of Karpathy's autoresearch pattern as a universal agent skill, demonstrating generalizability beyond the original repo. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mattpocockcaveman"></a>`mattpocock/caveman`

- **Name:** Caveman Mode
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/caveman](https://github.com/mattpocock/skills/blob/main/skills/productivity/caveman) (133,210 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2403.12968](https://arxiv.org/abs/2403.12968)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMLingua-2 (ACL 2024 Findings) — data-distillation for efficient task-agnostic prompt compression; 3x-6x speed-up, BERT-base token classifier; demonstrates measurable perplexity-based faithfulness. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/microsoft/LLMLingua](https://github.com/microsoft/LLMLingua)
- **Date:** 2026-04-30
- **Verified Stars:** 6,309 stars
- **Description:** Microsoft LLMLingua — reproducible open-source implementation of LLMLingua-1/2/LongLLMLingua; CI, README, Apache-2.0 license. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://skillsmp.com/api/v1/skills/search?q=context-compression](https://skillsmp.com/api/v1/skills/search?q=context-compression)
- **Date:** 2026-04-30
- **Trust Metric:** 70.0
- **Description:** SkillsMP top hit: sickn33/antigravity-awesome-skills (35k+ stars), multiple community variants including context-compression-v2. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockgrill-with-docs"></a>`mattpocock/grill-with-docs`

- **Name:** Grill With Docs
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md)
- **Date:** 2026-05-15
- **Verified Stars:** 133,210 stars
- **Description:** Production implementation of the Grill With Docs pattern. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockimprove-codebase-architecture"></a>`mattpocock/improve-codebase-architecture`

- **Name:** Improve Codebase Architecture
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.06770](https://arxiv.org/abs/2310.06770)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** SWE-bench â€” 2294 real GitHub issues benchmark; agents that resolve issues must safely refactor code while passing existing test suites. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockobsidian-vault"></a>`mattpocock/obsidian-vault`

- **Name:** Obsidian Vault Manager
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault](https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/personal/obsidian-vault/SKILL.md)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Obsidian vault management and PKM automation. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockprototype"></a>`mattpocock/prototype`

- **Name:** Prototype
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype](https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/prototype/SKILL.md)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Production interactive prototyping skill. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpococksetup-matt-pocock-skills"></a>`mattpocock/setup-matt-pocock-skills`

- **Name:** Setup Matt Pocock Skills
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills](https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md)
- **Date:** 2026-05-22
- **Verified Stars:** 133,210 stars
- **Description:** Scaffolding skill for Matt Pocock's engineering workspace. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockto-issues"></a>`mattpocock/to-issues`

- **Name:** To Issues
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/to-issues/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Production skill implementing tracer-bullet vertical slicing with HITL/AFK classification and issue-tracker publication. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpococktriage"></a>`mattpocock/triage`

- **Name:** Triage
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/triage/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Production triage skill with state-machine workflow, HITL/AFK routing, and structured agent-brief output. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2501.18908](https://arxiv.org/abs/2501.18908)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** CASEY system: LLMs automate CWE identification (68% accuracy) and severity assessment (73.6%) for security bug triage. (backfilled — class-to-type migration)

#### E3: `arxiv`
- **Source:** [https://arxiv.org/abs/2504.18804](https://arxiv.org/abs/2504.18804)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMs transform unstructured bug reports into high-quality structured formats; fine-tuned Qwen 2.5 achieves 77% CTQRS. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockwrite-a-skill"></a>`mattpocock/write-a-skill`

- **Name:** Write a Skill
- **Contributor:** `mattpocock`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2305.17126](https://arxiv.org/abs/2305.17126)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Cai et al. (2023) â€” Large Language Models as Tool Makers (LATM); LLM-generated tools reused across problem instances achieve +8.7% on BigBench Hard vs per-instance CoT. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/ctlllll/LLM-ToolMaker](https://github.com/ctlllll/LLM-ToolMaker)
- **Date:** 2026-04-29
- **Verified Stars:** 1,061 stars
- **Description:** LATM repo â€” reproducible tool-maker/tool-user pipeline with evaluation on BigBench Hard tasks and tool reuse across problem batches. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-obrarequesting-code-review"></a>`obra/requesting-code-review`

- **Name:** Requesting Code Review
- **Contributor:** `obra`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrasystematic-debugging"></a>`obra/systematic-debugging`

- **Name:** Systematic Debugging
- **Contributor:** `obra`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/systematic-debugging/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-ruvnetdual-mode"></a>`ruvnet/dual-mode`

- **Name:** Dual Mode
- **Contributor:** `ruvnet`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetreasoningbank"></a>`ruvnet/reasoningbank`

- **Name:** ReasoningBank
- **Contributor:** `ruvnet`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-santifercareer-ops"></a>`santifer/career-ops`

- **Name:** Career-Ops
- **Contributor:** `santifer`
- **Tier:** 3★
- **Primary Repository:** [https://github.com/santifer/career-ops/blob/main/.agents/skills/career-ops/SKILL.md](https://github.com/santifer/career-ops/blob/main/.agents/skills/career-ops/SKILL.md) (54,446 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/santifer/career-ops](https://github.com/santifer/career-ops)
- **Date:** 2026-05-14
- **Verified Stars:** 54,446 stars
- **Description:** Career-Ops -- AI-powered job search system with CV tailoring and dashboard. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-sickn33mcp-builder"></a>`sickn33/mcp-builder`

- **Name:** sickn33 MCP Builder
- **Contributor:** `sickn33`
- **Tier:** 3★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/mcp-builder/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic mcp-builder skill gives a reproducible guide for building high-quality MCP servers in Python FastMCP or the Node/TypeScript MCP SDK. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- **Date:** 2026-05-10
- **Verified Stars:** 23,358 stars
- **Description:** Official MCP Python SDK is active and provides FastMCP server examples for exposing tools, resources, prompts, structured outputs, transports, and inspector-based testing. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://raw.githubusercontent.com/sickn33/antigravity-awesome-skills/main/skills/mcp-builder/SKILL.md](https://raw.githubusercontent.com/sickn33/antigravity-awesome-skills/main/skills/mcp-builder/SKILL.md)
- **Date:** 2026-05-27
- **Trust Metric:** 70.0
- **Description:** (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) (skill: `mcp-builder`)
* **Benchmark:** Library Scale & Stars
* **Score:** Over 1,500+ skills in the collection (no standalone quantitative score)
* **Date:** May 2026
* **Setup Description:** Evaluated qualitatively within the `antigravity-awesome-skills` directory for Claude Code, Cursor, and Gemini CLI. The skill provides step-by-step guidance for tools definition, schema modeling, and connection handling in Python/Node.js MCP setups.

### Peer Reviews & Audits

* **Target Repository:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
* **Review URL:** [sickn33 Awesome Skills Directory](https://github.com/sickn33/antigravity-awesome-skills)
* **Author:** Awesome Skills Community & Security Audits
* **Date:** June 2026
* **Summary of Findings:**
  * **MCP Scaffolding:** Guides agents to build FastMCP and Node SDK servers through structured template prompts.
  * **Zero Binary Risk:** Labeled "Verified/Scanned" in registries because it is a documentation-only skill (contains no compiled binaries), carrying zero execution-time security risks.

---

### Academic Papers & Preprints

*   **Paper Title:** Model Context Protocol (MCP) at First Glance: Studying the Security and Maintainability of MCP Servers
*   **Authors:** Mohammed Mehedi Hasan, Hao Li, Emad Fallahzadeh, Gopi Krishnan Rajbahadur, Bram Adams, and Ahmed E. Hassan
*   **Publication URL:** [https://arxiv.org/abs/2506.13538](https://arxiv.org/abs/2506.13538)
*   **Publication Date:** June 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    MCP Builder creates Model Context Protocol (MCP) servers in Python and Node.js. This empirical study conducts a security and maintainability review of the emergent MCP ecosystem. It evaluates server health, tool schemas, and maintainability pitfalls developers face when building and deploying MCP servers, outlining key best practices.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) (tracked via developer registries and the Antigravity skill tree)
*   **Author/Publisher:** @sickn33
*   **Publication Date:** May 27, 2026
*   **Metrics:** Cured into the Gaia skill catalog; marked as non-installable in June 2026.
*   **Description:** Represents a community skill implementation of the Model Context Protocol (MCP) server builder. It automates the generation of MCP servers in Python and Node.js. It manages the registration of tool functions, translates standard code interfaces to MCP schemas, and handles endpoint dispatch.

### YouTube Showcase Videos

*   **Link:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
*   **Project URL:** `https://github.com/sickn33/antigravity-awesome-skills`
*   **Channel/Community Name:** sickn33 / Antigravity Awesome Skills
*   **Description:** While there is no official video by the creator, community tutorials highlight this repository of over 1,500+ agentic skills (such as MCP Builder and n8n MCP tools) designed to extend AI coding tools (Claude Code, Cursor) using structured instructions.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **sickn33/mcp-builder** | [sickn33/antigravity-awesome-skills Repo](https://github.com/sickn33/antigravity-awesome-skills) | **Active (200)** | Verified repository |
*   **`sickn33/mcp-builder`**:
2. **Update Subdirectory Link Formats**: Re-stamp the `sickn33/mcp-builder` and `anthropic/skill-creator` subpath URLs to use `blob/` instead of `tree/` to satisfy Gaia Curation Rule #1.

---

## Skill: <a name="skill-Manavarya09design-extract"></a>`Manavarya09/design-extract`

- **Name:** Design Extract
- **Contributor:** `Manavarya09`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/Manavarya09/design-extract](https://github.com/Manavarya09/design-extract) (3,271 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/Manavarya09/design-extract](https://github.com/Manavarya09/design-extract)
- **Date:** 2026-05-14
- **Verified Stars:** 3,271 stars
- **Description:** Design Extract -- extracts complete design systems (Tailwind, Figma variables, etc.) from any URL. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-Taoidleplan-decompose-gh-plan-cascade"></a>`Taoidle/plan-decompose-gh-plan-cascade`

- **Name:** Plan Cascade
- **Contributor:** `Taoidle`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/changkun/wallfacer](https://github.com/changkun/wallfacer)
- **Date:** 2026-05-23
- **Verified Stars:** 72 stars
- **Description:** Auto-discovered from github. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/Taoidle/plan-cascade](https://github.com/Taoidle/plan-cascade)
- **Date:** 2026-05-23
- **Verified Stars:** 86 stars
- **Description:** Auto-discovered from github. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-anthropicpptx"></a>`anthropic/pptx`

- **Name:** PPTX Editor
- **Contributor:** `anthropic`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md) (152,231 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic /pptx slash command -- extracts, edits, packs, and applies design principles to PowerPoint files using markitdown. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How To Use Anthropic's Model Context Protocol (MCP) | Setup Tutorial](https://www.youtube.com/watch?v=KiNyvT02HJM)
*   **Video URL:** `https://www.youtube.com/watch?v=KiNyvT02HJM`
*   **Channel Name:** TechWithMladen (Validated Third-Party Developer Tutorial)
*   **Description:** A step-by-step setup tutorial on Anthropic's Model Context Protocol (MCP), showing how to connect Claude Desktop to external tools and database environments, using the MCP standard to extend the agent's capabilities (skills).

---

---

## Skill: <a name="skill-anthropicskill-creator"></a>`anthropic/skill-creator`

- **Name:** Skill Creator
- **Contributor:** `anthropic`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) (152,231 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2305.17126](https://arxiv.org/abs/2305.17126)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Cai et al. (2023) â€” Large Language Models as Tool Makers (LATM); LLM-generated tools reused across problem instances achieve +8.7% on BigBench Hard vs per-instance CoT. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/ctlllll/LLM-ToolMaker](https://github.com/ctlllll/LLM-ToolMaker)
- **Date:** 2026-04-29
- **Verified Stars:** 1,061 stars
- **Description:** LATM repo â€” reproducible tool-maker/tool-user pipeline with evaluation on BigBench Hard tasks and tool reuse across problem batches. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [anthropics/skills](https://github.com/anthropics/skills) (plugin: `skill-creator`)
* **Benchmark:** Skill Eval Pass Rate (Dynamic A/B testing)
* **Score:** Variable based on developer prompt (results saved to local `benchmark.json`)
* **Date:** April 2026
* **Setup Description:** Includes a built-in evaluation harness that dynamically generates synthetic test prompts for a drafted skill, runs parallel baseline versus skill-enabled sessions, and uses grading agents to output win-rates, execution time, and token counts.

### Peer Reviews & Audits

* **Target Repository:** [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
* **Review URL:** [Claude Code Skill-Creator Documentation](https://github.com/anthropics/skills/tree/main/skills/skill-creator)
* **Author:** Claude Code Community & Technical Authors
* **Date:** Mid 2026
* **Summary of Findings:**
  * **Engineering Discipline:** Establishes a software-testing framework for agent prompts by using assertions, test cases, and trigger optimization to ensure agents invoke skills correctly.
  * **Anti-Prompt Bloat:** Helps developers design specific `SKILL.md` files that disclosures instructions progressively.
  * **Overhead:** Local evaluation runs are heavy and depend on active LLM api keys, which can accumulate token costs during long refinement loops.

---

### Academic Papers & Preprints

*   **Paper Title:** Large Language Models as Tool Makers (LATM)
*   **Authors:** Tianle Cai, Xuezhi Wang, Tengyu Ma, Xinyun Chen, and Denny Zhou
*   **Publication URL:** [https://arxiv.org/abs/2305.17126](https://arxiv.org/abs/2305.17126)
*   **Publication Date:** May 2023
*   **Citation Count:** ~300+ citations
*   **Summary & Relevance:** 
    Skill Creator acts as a meta-agent that interviews users to generate ready-to-use skill files (`SKILL.md`). This process maps directly to the **Large Language Models as Tool Makers (LATM)** paradigm. LATM splits agent architectures into a "tool maker" phase (where a powerful LLM designs and verifies reusable tools) and a "tool user" phase (where a cheaper LLM deploys them). This serves as the underlying methodology for automated skill/tool authoring.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator](https://dev.to/anthropic/eval-driven-skill-creation-with-anthropics-skill-creator)
*   **Author/Publisher:** Anthropic / Claude Code Community
*   **Publication Date:** Early 2026
*   **Metrics:** Shipped natively as a core developer utility in Claude Code plugins.
*   **Description:** Highlights Anthropic's Skill Creator meta-skill, which introduces software engineering rigor to prompt engineering. It helps authors design `SKILL.md` instruction files by conducting intake interviews, generating A/B evaluation test suites (comparing output quality with and without the skill), optimizing trigger instructions in the YAML frontmatter, and compiling benchmarks.

### YouTube Showcase Videos

*   **Video Title:** [How To Use Anthropic's Model Context Protocol (MCP) | Setup Tutorial](https://www.youtube.com/watch?v=KiNyvT02HJM)
*   **Video URL:** `https://www.youtube.com/watch?v=KiNyvT02HJM`
*   **Channel Name:** TechWithMladen (Validated Third-Party Developer Tutorial)
*   **Description:** A step-by-step setup tutorial on Anthropic's Model Context Protocol (MCP), showing how to connect Claude Desktop to external tools and database environments, using the MCP standard to extend the agent's capabilities (skills).

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **anthropic/skill-creator** | [anthropics/skills Repo](https://github.com/anthropics/skills) | **Active (200)** | Verified repository |
*   **`anthropic/skill-creator` Blog Post**:
*   **`anthropic/skill-creator`**:
2. **Update Subdirectory Link Formats**: Re-stamp the `sickn33/mcp-builder` and `anthropic/skill-creator` subpath URLs to use `blob/` instead of `tree/` to satisfy Gaia Curation Rule #1.

---

## Skill: <a name="skill-bradautomatesclaude-video"></a>`bradautomates/claude-video`

- **Name:** Claude Video
- **Contributor:** `bradautomates`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/bradautomates/claude-video/blob/main/SKILL.md](https://github.com/bradautomates/claude-video/blob/main/SKILL.md) (2,149 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/bradautomates/claude-video](https://github.com/bradautomates/claude-video)
- **Date:** 2026-05-14
- **Verified Stars:** 2,149 stars
- **Description:** Claude Video -- enables AI agents to watch videos by downloading, frame extraction, and transcription. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-browser-usebrowser-harness"></a>`browser-use/browser-harness`

- **Name:** Browser Harness
- **Contributor:** `browser-use`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/browser-use/browser-harness/blob/main/SKILL.md](https://github.com/browser-use/browser-harness/blob/main/SKILL.md) (15,008 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/browser-use/browser-harness](https://github.com/browser-use/browser-harness)
- **Date:** 2026-05-14
- **Verified Stars:** 15,008 stars
- **Description:** Browser Harness -- self-healing harness connecting LLMs to browser via CDP. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [browser-use/browser-harness](https://github.com/browser-use/browser-harness)
* **Benchmark:** BU Bench V1 (100 verified tasks) & Online-Mind2Web
* **Score:** 78% - 97% task success using Browser Use Cloud (`bu-ultra/max`); 80% using Claude Fable 5
* **Date:** Mid-2026
* **Setup Description:** Evaluated on 100 hard, verified-completable tasks originating from WebArena, Mind2Web, and BrowseComp. Success is judged by an LLM (Gemini 2.5 Flash) checking DOM and screenshot state changes. It tests how well the CDP-based harness handles selectors, rate-limits, and self-heals by runtime script generation.

### Peer Reviews & Audits

* **Target Repository:** [browser-use/browser-harness](https://github.com/browser-use/browser-harness)
* **Review URL:** [browser-use/browser-harness Repository & Readme](https://github.com/browser-use/browser-harness)
* **Author:** AI Agent Developer Community
* **Date:** Mid 2026
* **Summary of Findings:**
  * **Minimalist Approach:** Commended as a lightweight WebSocket CDP (Chrome DevTools Protocol) bridge that bypasses heavy selector abstractions, allowing agents to manipulate tabs, DOM, and JavaScript directly.
  * **Self-Healing:** Built around a core design where the AI writes its own runtime helper functions (`agent_helpers.py`) to adapt to dynamic layout changes.
  * **Steep Learning Curve:** Noted to be harder to implement than high-level browser automation libraries, but significantly more robust for handling dynamic frames and shadow roots.

---

### Academic Papers & Preprints

*   **Paper Title:** When Bots Take the Bait: Exposing and Mitigating the Emerging Social Engineering Attack in Web Automation Agent
*   **Authors:** Xinyi Wu, Geng Hong, Yueyue Chen, MingXuan Liu, Feier Jin, Xudong Pan, Jiarun Dai, and Baojun Liu
*   **Publication URL:** [https://arxiv.org/abs/2601.07263](https://arxiv.org/abs/2601.07263)
*   **Publication Date:** January 12, 2026
*   **Citation Count:** ~2 citations
*   **Summary & Relevance:** 
    `browser-use` is a mainstream open-source web-interaction and browser control framework. This paper evaluates the security of `browser-use` and related agentic browsers against a social engineering threat paradigm called **AgentBait**. The authors demonstrate how adversarial inducement prompts embedded in web interfaces can manipulate the agent's browser-harness reasoning. They propose **SUPERVISOR**, a consistency verification layer to mitigate these exploits.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://github.com/browser-use/browser-harness](https://github.com/browser-use/browser-harness) (covered in detail on Dev.to and Medium articles regarding thin browser harnesses)
*   **Author/Publisher:** Browser Use Team
*   **Publication Date:** Early 2026
*   **Metrics:** Part of the trending "thin agent infrastructure" movement in early 2026.
*   **Description:** Discusses Browser Harness as a lightweight, low-level browser automation solution. Operating in about 600 lines of Python, it interacts directly with Chrome via Chrome DevTools Protocol (CDP) WebSocket commands rather than bundling heavy frameworks like Playwright or Selenium. Crucially, the AI agent is given runtime self-healing capabilities to dynamically generate and rewrite its own local helper functions (`agent_helpers.py`) when it runs into custom elements or page-blocking steps.

### YouTube Showcase Videos

*   **Video Title:** [Debug web apps with browser use in Codex](https://www.youtube.com/watch?v=XQn6yGq6oN8)
*   **Video URL:** `https://www.youtube.com/watch?v=XQn6yGq6oN8`
*   **Channel Name:** Codex Developer (Validated Third-Party Developer Showcase)
*   **Description:** This video demonstrates how to use the browser-use Python library with the Chrome DevTools Protocol (CDP) to inspect network requests, capture console logs, and profile performance of web applications programmatically through an AI agent.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **browser-use/browser-harness**| [browser-use/browser-use Repo](https://github.com/browser-use/browser-use) | **Active (200)** | Verified repository |
| | [browser-use/browser-harness Repo](https://github.com/browser-use/browser-harness) | **Active (200)** | Verified repository |

---

## Skill: <a name="skill-browserbasestagehand"></a>`browserbase/stagehand`

- **Name:** Stagehand
- **Contributor:** `browserbase`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/browserbase/stagehand](https://github.com/browserbase/stagehand) (23,152 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2401.13919](https://arxiv.org/abs/2401.13919)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** WebVoyager (He et al., 2024) â€” end-to-end web agent with GPT-4V; 59.1% task success on real-world web tasks across 15 popular websites. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/web-arena-x/webarena](https://github.com/web-arena-x/webarena)
- **Date:** 2026-04-28
- **Verified Stars:** 1,517 stars
- **Description:** WebArena â€” self-hosted web environment with 812 realistic tasks; reproducible benchmark with ground-truth evaluation scripts. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-changkunplan-decompose-gh-wallfacer"></a>`changkun/plan-decompose-gh-wallfacer`

- **Name:** Wallfacer
- **Contributor:** `changkun`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/changkun/wallfacer](https://github.com/changkun/wallfacer)
- **Date:** 2026-05-23
- **Verified Stars:** 72 stars
- **Description:** Auto-discovered from github. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/Taoidle/plan-cascade](https://github.com/Taoidle/plan-cascade)
- **Date:** 2026-05-23
- **Verified Stars:** 86 stars
- **Description:** Auto-discovered from github. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-firecrawlfirecrawl"></a>`firecrawl/firecrawl`

- **Name:** Firecrawl
- **Contributor:** `firecrawl`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/firecrawl/firecrawl](https://github.com/firecrawl/firecrawl) (134,215 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)
- **Date:** 2026-06-10
- **Verified Stars:** 134,215 stars
- **Description:** Origin repository — open-source web search/scrape/crawl API for LLM agents; reproducible public implementation with documented usage. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)
* **Benchmark:** scrape-content-dataset-v1 (1,000 URLs) & Latency
* **Score:** >95% dynamic page scrape success; P95 Latency of ~3.4s
* **Date:** May 2026
* **Setup Description:** Run against a public test dataset of 1,000 distinct URLs comprising JS-heavy SPAs and sites protected by anti-bot measures. Evaluated on markdown output schema fidelity, truth-recall (comparing content against crawler ground truths), and P50/P90/P99 latency distribution.

### Peer Reviews & Audits

* **Target Repository:** [firecrawl/firecrawl](https://github.com/firecrawl/firecrawl)
* **Review URL:** [Firecrawl vs Crawl4AI Audits](https://github.com/firecrawl/firecrawl)
* **Author:** Zack Proser (and general RAG pipeline practitioners)
* **Date:** Mid 2026
* **Summary of Findings:**
  * **Structured Markdown Output:** Praised for its ability to cleanly convert JavaScript-heavy websites into RAG-ready Markdown/JSON through a single API endpoint.
  * **Anti-Bot & Proxy Handling:** Excellent handling of rotating proxies and bypasses rate limits out of the box, removing infrastructure overhead.
  * **Cost Scaling:** Critiques note the credit-based pricing model scales poorly for large-scale operations and lacks the localized low-level control of open-source crawlers.

---

### Academic Papers & Preprints

*   **Paper Title:** Improving and Evaluating Open Deep Research Agents
*   **Authors:** Doaa Allabadi, Kyle Bradbury, and Jordan M. Malof
*   **Publication URL:** [https://arxiv.org/abs/2508.10152](https://arxiv.org/abs/2508.10152)
*   **Publication Date:** August 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Firecrawl converts websites into LLM-ready markdown or structured data. This paper evaluates Deep Research Agents (DRAs) that perform autonomous web navigation to answer multifaceted queries. The authors analyze the reliance of open agents on advanced scraping and crawling pipelines—including Firecrawl—for robust context extraction and search-guided question decomposition.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://medium.com/firecrawl/the-death-of-the-brittle-scraper](https://medium.com/firecrawl/the-death-of-the-brittle-scraper) (also covered in DEV.to tutorials)
*   **Author/Publisher:** Firecrawl Team / AI Engineering Community
*   **Publication Date:** Mid 2025
*   **Metrics:** Thousands of stars on GitHub and standard integration in RAG tools.
*   **Description:** Details Firecrawl's role in converting entire sites or individual pages into clean, LLM-ready formats (chiefly Markdown and structured JSON schemas). It discusses bypassing rate limits, reverse proxies, and anti-bot checks. It also introduces the `/scrape` and `/crawl` endpoints which serve as RAG feeds for modern AI coding frameworks.

### YouTube Showcase Videos

*   **Video Title:** [Firecrawl Full Beginner Course | Let's Scrape EVERYTHING](https://www.youtube.com/watch?v=kY0hN5-xK8U)
*   **Video URL:** `https://www.youtube.com/watch?v=kY0hN5-xK8U`
*   **Channel Name:** Tyler AI (Validated Third-Party Tutorial)
*   **Description:** A comprehensive course taking developers through the basics of web scraping, crawling, mapping, searching, and LLM-powered structured data extraction utilizing Firecrawl API endpoints and SDKs.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **firecrawl/firecrawl** | [firecrawl/firecrawl Repo](https://github.com/firecrawl/firecrawl) | **Active (200)** | Verified repository |
| | [mendableai/firecrawl Repo](https://github.com/mendableai/firecrawl) | **Active (200)** | Verified redirect to firecrawl/firecrawl |

---

## Skill: <a name="skill-gaiabotgaia-triage"></a>`gaiabot/gaia-triage`

- **Name:** Gaia Triage (Internal)
- **Contributor:** `gaiabot`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2501.18908](https://arxiv.org/abs/2501.18908)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** CASEY system: LLMs automate CWE identification (68% accuracy) and severity assessment (73.6%) for security bug triage. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2504.18804](https://arxiv.org/abs/2504.18804)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMs transform unstructured bug reports into high-quality structured formats; fine-tuned Qwen 2.5 achieves 77% CTQRS. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-gaiabotrepo-docs-before-pr"></a>`gaiabot/repo-docs-before-pr`

- **Name:** Repo Docs Before PR
- **Contributor:** `gaiabot`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-06-10
- **Verified Stars:** 6 stars
- **Description:** Exercised in this repository's own CI: the docs drift check (gaia docs build --check) gates every PR, demonstrating the skill in production. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-garrytancareful"></a>`garrytan/careful`

- **Name:** Careful
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/careful/SKILL.md](https://github.com/garrytan/gstack/blob/main/careful/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/careful/SKILL.md](https://github.com/garrytan/gstack/blob/main/careful/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Activates a conservative execution profile that pauses before irreversible actions, requests explicit confirmation for destructive operations, and… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.25176](https://arxiv.org/abs/2603.25176)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Prompt Attack Detection with LLM-as-a-Judge (2026) -- guardrail deployment framework for detecting jailbreaks and prompt injections under production latency constraints. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- **Date:** 2026-04-30
- **Verified Stars:** 6,463 stars
- **Description:** NeMo Guardrails -- open-source toolkit for adding programmable safety rails to LLM-based conversational systems; actively maintained. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytancontext-restore"></a>`garrytan/context-restore`

- **Name:** Context Restore
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md](https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md](https://github.com/garrytan/gstack/blob/main/context-restore/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Reads a saved context snapshot and reconstructs a warm session state, surfacing the last decision point and pending tasks so work can resume… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2403.12968](https://arxiv.org/abs/2403.12968)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMLingua-2 (ACL 2024 Findings) — data-distillation for efficient task-agnostic prompt compression; 3x-6x speed-up, BERT-base token classifier; demonstrates measurable perplexity-based faithfulness. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/microsoft/LLMLingua](https://github.com/microsoft/LLMLingua)
- **Date:** 2026-04-30
- **Verified Stars:** 6,309 stars
- **Description:** Microsoft LLMLingua — reproducible open-source implementation of LLMLingua-1/2/LongLLMLingua; CI, README, Apache-2.0 license. (backfilled — class-to-type migration)

#### E4: `repo`
- **Source:** [https://skillsmp.com/api/v1/skills/search?q=context-compression](https://skillsmp.com/api/v1/skills/search?q=context-compression)
- **Date:** 2026-04-30
- **Trust Metric:** 70.0
- **Description:** SkillsMP top hit: sickn33/antigravity-awesome-skills (35k+ stars), multiple community variants including context-compression-v2. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytancontext-save"></a>`garrytan/context-save`

- **Name:** Context Save
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/context-save/SKILL.md](https://github.com/garrytan/gstack/blob/main/context-save/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/context-save/SKILL.md](https://github.com/garrytan/gstack/blob/main/context-save/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Compresses the current session context into a compact summary file that can be restored later, enabling long-running workflows to survive… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2403.12968](https://arxiv.org/abs/2403.12968)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMLingua-2 (ACL 2024 Findings) — data-distillation for efficient task-agnostic prompt compression; 3x-6x speed-up, BERT-base token classifier; demonstrates measurable perplexity-based faithfulness. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/microsoft/LLMLingua](https://github.com/microsoft/LLMLingua)
- **Date:** 2026-04-30
- **Verified Stars:** 6,309 stars
- **Description:** Microsoft LLMLingua — reproducible open-source implementation of LLMLingua-1/2/LongLLMLingua; CI, README, Apache-2.0 license. (backfilled — class-to-type migration)

#### E4: `repo`
- **Source:** [https://skillsmp.com/api/v1/skills/search?q=context-compression](https://skillsmp.com/api/v1/skills/search?q=context-compression)
- **Date:** 2026-04-30
- **Trust Metric:** 70.0
- **Description:** SkillsMP top hit: sickn33/antigravity-awesome-skills (35k+ stars), multiple community variants including context-compression-v2. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytandocument-release"></a>`garrytan/document-release`

- **Name:** Document Release
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/document-release/SKILL.md](https://github.com/garrytan/gstack/blob/main/document-release/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/document-release/SKILL.md](https://github.com/garrytan/gstack/blob/main/document-release/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Reads the diff between two version tags and drafts concise, user-facing release notes following the Gstack changelog format. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanfreeze"></a>`garrytan/freeze`

- **Name:** Freeze
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md](https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md](https://github.com/garrytan/gstack/blob/main/freeze/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Sets a change-freeze flag that blocks non-critical commits and PR merges until explicitly lifted, protecting release branches or post-incident… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.25176](https://arxiv.org/abs/2603.25176)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Prompt Attack Detection with LLM-as-a-Judge (2026) -- guardrail deployment framework for detecting jailbreaks and prompt injections under production latency constraints. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- **Date:** 2026-04-30
- **Verified Stars:** 6,463 stars
- **Description:** NeMo Guardrails -- open-source toolkit for adding programmable safety rails to LLM-based conversational systems; actively maintained. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytangstack-upgrade"></a>`garrytan/gstack-upgrade`

- **Name:** GStack Upgrade
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md](https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md](https://github.com/garrytan/gstack/blob/main/gstack-upgrade/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Scans the workspace for outdated dependencies, runs upgrades within semver-compatible bounds, re-runs tests, and commits a clean dependency bump PR. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Hermes Skills Hub: Google Workspace integration for unified email, calendar, and drive access. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanlanding-report"></a>`garrytan/landing-report`

- **Name:** Landing Report
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/landing-report/SKILL.md](https://github.com/garrytan/gstack/blob/main/landing-report/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/landing-report/SKILL.md](https://github.com/garrytan/gstack/blob/main/landing-report/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Generates a one-page project landing report from open issues, recent commits, and milestone progress, giving stakeholders a quick read on health… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Hermes Skills Hub: Linear integration for issue and project management. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanopen-gstack-browser"></a>`garrytan/open-gstack-browser`

- **Name:** Open GStack Browser
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/open-gstack-browser/SKILL.md](https://github.com/garrytan/gstack/blob/main/open-gstack-browser/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/open-gstack-browser/SKILL.md](https://github.com/garrytan/gstack/blob/main/open-gstack-browser/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Launches a new headless or headed browser session with the Gstack environment variables and extension profile pre-loaded, ready for automation… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanplan-tune"></a>`garrytan/plan-tune`

- **Name:** Plan Tune
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/plan-tune/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-tune/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/plan-tune/SKILL.md](https://github.com/garrytan/gstack/blob/main/plan-tune/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Takes a draft plan or system prompt, identifies vague or ambiguous instructions, and rewrites them to reduce hallucination and improve task… (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.03714](https://arxiv.org/abs/2310.03714)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Khattab et al. (2023) â€” DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines; automated prompt tuning matches or exceeds hand-crafted prompts on GSM8K, HotPotQA, and FEVER. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/stanfordnlp/dspy](https://github.com/stanfordnlp/dspy)
- **Date:** 2026-04-29
- **Verified Stars:** 35,104 stars
- **Description:** DSPy â€” Stanford NLP library for programmable LM pipelines; 18k+ GitHub stars, supports multiple optimizers (BootstrapFewShot, MIPRO, COPRO) across any LM. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanqa-only"></a>`garrytan/qa-only`

- **Name:** QA Only
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/qa-only/SKILL.md](https://github.com/garrytan/gstack/blob/main/qa-only/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/qa-only/SKILL.md](https://github.com/garrytan/gstack/blob/main/qa-only/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Runs the scoped end-to-end test suite for a single feature or route without launching the full QA pipeline, for fast targeted regression checks. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/zachblume/autospec](https://github.com/zachblume/autospec)
- **Date:** 2026-04-30
- **Verified Stars:** 61 stars
- **Description:** autospec — AI agent that takes a web app URL and autonomously QAs it, saving passing specs as E2E test code (59 stars, active). (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytansetup-browser-cookies"></a>`garrytan/setup-browser-cookies`

- **Name:** Setup Browser Cookies
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/setup-browser-cookies/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-browser-cookies/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/setup-browser-cookies/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-browser-cookies/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Injects pre-authenticated session cookies into the browser context so subsequent automation steps can access gated pages without a manual login flow. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytansetup-deploy"></a>`garrytan/setup-deploy`

- **Name:** Setup Deploy
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-deploy/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Provisions the deployment environment by creating secrets, configuring environment variables, and running infrastructure-as-code init steps before… (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytansetup-gbrain"></a>`garrytan/setup-gbrain`

- **Name:** Setup GBrain
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/setup-gbrain/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-gbrain/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/setup-gbrain/SKILL.md](https://github.com/garrytan/gstack/blob/main/setup-gbrain/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Bootstraps the GBrain knowledge store for a new project: creates the index structure, ingests seed documents, and validates retrieval with a… (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Hermes Skills Hub: Notion integration for structured notes and databases. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytansync-gbrain"></a>`garrytan/sync-gbrain`

- **Name:** Sync GBrain
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/sync-gbrain/SKILL.md](https://github.com/garrytan/gstack/blob/main/sync-gbrain/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/sync-gbrain/SKILL.md](https://github.com/garrytan/gstack/blob/main/sync-gbrain/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Incrementally syncs new documents and updated pages into the GBrain index, deduplicates embeddings, and reports ingestion counts and any errors. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Hermes Skills Hub: Notion integration for structured notes and databases. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-garrytanunfreeze"></a>`garrytan/unfreeze`

- **Name:** Unfreeze
- **Contributor:** `garrytan`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md](https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md) (110,930 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md](https://github.com/garrytan/gstack/blob/main/unfreeze/SKILL.md)
- **Date:** 2026-06-03
- **Verified Stars:** 110,930 stars
- **Description:** Public SKILL.md in the garrytan/gstack suite repo (verified live). Clears the active change-freeze flag and restores normal merge permissions, logging the unfreeze event with a timestamp and justification. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.25176](https://arxiv.org/abs/2603.25176)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Prompt Attack Detection with LLM-as-a-Judge (2026) -- guardrail deployment framework for detecting jailbreaks and prompt injections under production latency constraints. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
- **Date:** 2026-04-30
- **Verified Stars:** 6,463 stars
- **Description:** NeMo Guardrails -- open-source toolkit for adding programmable safety rails to LLM-based conversational systems; actively maintained. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [How to Make Claude Code Your AI Engineering Team](https://www.youtube.com/watch?v=wkv2ifxPpF8)
*   **Video URL:** `https://www.youtube.com/watch?v=wkv2ifxPpF8`
*   **Channel Name:** Y Combinator (Official Channel / Garry Tan Showcase)
*   **Description:** Garry Tan, CEO of Y Combinator, demonstrates Gstack, his open-source configuration toolkit that enables Claude Code to operate as an entire engineering team. He walks through running Claude Code with specialized slash commands representing roles like EM, Designer, QA, and CEO Reviewer, showcaseing "Founder Mode" in software development.

---

---

## Skill: <a name="skill-getagentsealcodeburn"></a>`getagentseal/codeburn`

- **Name:** CodeBurn
- **Contributor:** `getagentseal`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/getagentseal/codeburn](https://github.com/getagentseal/codeburn) (8,071 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/getagentseal/codeburn](https://github.com/getagentseal/codeburn)
- **Date:** 2026-05-14
- **Verified Stars:** 8,071 stars
- **Description:** CodeBurn -- provides cost and token observability for AI coding tools; integrated with 20 AI tools. Includes TUI dashboard, macOS menubar, optimization and yield analysis commands. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-glinckerreadme-generator"></a>`glincker/readme-generator`

- **Name:** README Generator
- **Contributor:** `glincker`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md](https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md) (32 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md](https://github.com/GLINCKER/claude-code-marketplace/blob/main/skills/documentation/readme-generator/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 32 stars
- **Description:** Published implementation in the GLINCKER Claude Code Marketplace; reproducible from SKILL.md. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindchembl_database"></a>`google-deepmind/chembl_database`

- **Name:** Chembl-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/chembl_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind chembl_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Molecular Databases. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindclinical_trials_database"></a>`google-deepmind/clinical_trials_database`

- **Name:** Clinical-Trials-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/clinical_trials_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/clinical_trials_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/clinical_trials_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/clinical_trials_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind clinical_trials_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Clinical Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindclinvar_database"></a>`google-deepmind/clinvar_database`

- **Name:** Clinvar-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/clinvar_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/clinvar_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/clinvar_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/clinvar_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind clinvar_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Clinical Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepminddbsnp_database"></a>`google-deepmind/dbsnp_database`

- **Name:** Dbsnp-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/dbsnp_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/dbsnp_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/dbsnp_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/dbsnp_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind dbsnp_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindembl_ebi_ols"></a>`google-deepmind/embl_ebi_ols`

- **Name:** Embl-Ebi-Ols
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/embl_ebi_ols/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/embl_ebi_ols/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/embl_ebi_ols/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/embl_ebi_ols/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind embl_ebi_ols science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Pathway Ontology Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindencode_ccres_database"></a>`google-deepmind/encode_ccres_database`

- **Name:** Encode-Ccres-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/encode_ccres_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/encode_ccres_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/encode_ccres_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/encode_ccres_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind encode_ccres_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindensembl_database"></a>`google-deepmind/ensembl_database`

- **Name:** Ensembl-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ensembl_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ensembl_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ensembl_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ensembl_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind ensembl_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindfoldseek_structural_search"></a>`google-deepmind/foldseek_structural_search`

- **Name:** Foldseek-Structural-Search
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/foldseek_structural_search/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/foldseek_structural_search/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/foldseek_structural_search/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/foldseek_structural_search/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind foldseek_structural_search science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Protein Structure Analysis. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindgnomad_database"></a>`google-deepmind/gnomad_database`

- **Name:** Gnomad-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/gnomad_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind gnomad_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindgtex_database"></a>`google-deepmind/gtex_database`

- **Name:** Gtex-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/gtex_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/gtex_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/gtex_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/gtex_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind gtex_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindhuman_protein_atlas_database"></a>`google-deepmind/human_protein_atlas_database`

- **Name:** Human-Protein-Atlas-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/human_protein_atlas_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/human_protein_atlas_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/human_protein_atlas_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/human_protein_atlas_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind human_protein_atlas_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Proteomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindinterpro_database"></a>`google-deepmind/interpro_database`

- **Name:** Interpro-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/interpro_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/interpro_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/interpro_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/interpro_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind interpro_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Proteomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindjaspar_database"></a>`google-deepmind/jaspar_database`

- **Name:** Jaspar-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/jaspar_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind jaspar_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindliterature_search_arxiv"></a>`google-deepmind/literature_search_arxiv`

- **Name:** Literature-Search-Arxiv
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_arxiv/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind literature_search_arxiv science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Literature Search. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindliterature_search_biorxiv"></a>`google-deepmind/literature_search_biorxiv`

- **Name:** Literature-Search-Biorxiv
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_biorxiv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_biorxiv/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_biorxiv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_biorxiv/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind literature_search_biorxiv science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Literature Search. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindliterature_search_europepmc"></a>`google-deepmind/literature_search_europepmc`

- **Name:** Literature-Search-Europepmc
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_europepmc/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_europepmc/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_europepmc/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_europepmc/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind literature_search_europepmc science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Literature Search. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindliterature_search_openalex"></a>`google-deepmind/literature_search_openalex`

- **Name:** Literature-Search-Openalex
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/literature_search_openalex/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind literature_search_openalex science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Literature Search. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindncbi_sequence_fetch"></a>`google-deepmind/ncbi_sequence_fetch`

- **Name:** Ncbi-Sequence-Fetch
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ncbi_sequence_fetch/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ncbi_sequence_fetch/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ncbi_sequence_fetch/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ncbi_sequence_fetch/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind ncbi_sequence_fetch science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindopenfda_database"></a>`google-deepmind/openfda_database`

- **Name:** Openfda-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/openfda_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/openfda_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/openfda_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/openfda_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind openfda_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Clinical Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindopentargets_database"></a>`google-deepmind/opentargets_database`

- **Name:** Opentargets-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/opentargets_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/opentargets_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/opentargets_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/opentargets_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind opentargets_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Clinical Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindpdb_database"></a>`google-deepmind/pdb_database`

- **Name:** Pdb-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pdb_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pdb_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pdb_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pdb_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind pdb_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Protein Structure Analysis. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindprotein_sequence_similarity_search"></a>`google-deepmind/protein_sequence_similarity_search`

- **Name:** Protein-Sequence-Similarity-Search
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_similarity_search/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_similarity_search/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Bioinformatic Sequence Analysis. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_similarity_search/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/protein_sequence_similarity_search/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind protein_sequence_similarity_search science-skill implementation. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindpubchem_database"></a>`google-deepmind/pubchem_database`

- **Name:** Pubchem-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pubchem_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pubchem_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pubchem_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pubchem_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind pubchem_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Molecular Databases. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindpubmed_database"></a>`google-deepmind/pubmed_database`

- **Name:** Pubmed-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pubmed_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind pubmed_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Literature Search. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindpymol"></a>`google-deepmind/pymol`

- **Name:** Pymol
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/pymol/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind pymol science-skill implementation. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindquickgo_database"></a>`google-deepmind/quickgo_database`

- **Name:** Quickgo-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/quickgo_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/quickgo_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/quickgo_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/quickgo_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind quickgo_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Pathway Ontology Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindreactome_database"></a>`google-deepmind/reactome_database`

- **Name:** Reactome-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/reactome_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/reactome_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/reactome_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/reactome_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind reactome_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Pathway Ontology Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindscience_skills_common"></a>`google-deepmind/science_skills_common`

- **Name:** Science-Skills-Common
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common](https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/science_skills_common/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind science_skills_common science-skill implementation. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindstring_database"></a>`google-deepmind/string_database`

- **Name:** String-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/string_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind string_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Proteomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepminducsc_conservation_and_tfbs"></a>`google-deepmind/ucsc_conservation_and_tfbs`

- **Name:** Ucsc-Conservation-And-Tfbs
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ucsc_conservation_and_tfbs/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ucsc_conservation_and_tfbs/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/ucsc_conservation_and_tfbs/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/ucsc_conservation_and_tfbs/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind ucsc_conservation_and_tfbs science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindunibind_database"></a>`google-deepmind/unibind_database`

- **Name:** Unibind-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/unibind_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind unibind_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Genomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepminduniprot_database"></a>`google-deepmind/uniprot_database`

- **Name:** Uniprot-Database
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/uniprot_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/uniprot_database/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/uniprot_database/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/uniprot_database/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind uniprot_database science-skill implementation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Foundational canonical generic skill for Proteomic Data Retrieval. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepminduv"></a>`google-deepmind/uv`

- **Name:** Uv
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/uv/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind uv science-skill implementation. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-google-deepmindworkflow_skill_creator"></a>`google-deepmind/workflow_skill_creator`

- **Name:** Workflow-Skill-Creator
- **Contributor:** `google-deepmind`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/google-deepmind/science-skills/blob/main/skills/workflow_skill_creator/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/workflow_skill_creator/SKILL.md) (1,934 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/google-deepmind/science-skills/blob/main/skills/workflow_skill_creator/SKILL.md](https://github.com/google-deepmind/science-skills/blob/main/skills/workflow_skill_creator/SKILL.md)
- **Date:** 2026-05-23
- **Verified Stars:** 1,934 stars
- **Description:** Official Google DeepMind workflow_skill_creator science-skill implementation. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2602.08004](https://arxiv.org/abs/2602.08004)
- **Date:** 2026-05-10
- **Trust Metric:** 85.0
- **Description:** Agent Skills data-driven analysis characterizes SKILL.md packages as an emerging infrastructure layer and quantifies common design, reuse, and safety patterns. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic skill-creator provides a reproducible workflow for creating, editing, evaluating, benchmarking, and optimizing agent skills. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacehf-cli"></a>`huggingface/hf-cli`

- **Name:** HF CLI
- **Contributor:** `huggingface`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/hf-cli/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/hf-cli/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2305.15334](https://arxiv.org/abs/2305.15334)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** Gorilla (Patil et al.) â€” LLM that generates accurate API calls across TorchHub, TensorFlow Hub, and HuggingFace; 20.43% AST accuracy improvement over GPT-4. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacehuggingface-datasets"></a>`huggingface/huggingface-datasets`

- **Name:** Hugging Face Datasets
- **Contributor:** `huggingface`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/huggingface-datasets/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/huggingface-datasets/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/Sinaptik-AI/pandas-ai](https://github.com/Sinaptik-AI/pandas-ai)
- **Date:** 2026-04-28
- **Verified Stars:** 23,587 stars
- **Description:** pandas-ai â€” open-source agent for natural-language data analysis over pandas DataFrames; reproducible demos with logging and output artifacts. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacehuggingface-papers"></a>`huggingface/huggingface-papers`

- **Name:** Hugging Face Papers
- **Contributor:** `huggingface`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2501.05468](https://arxiv.org/abs/2501.05468)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Rouzrokh et al. (2025) — LatteReview: multi-agent framework for systematic review automation; modular agents for title/abstract screening, relevance scoring, and structured data extraction with RAG and multimodal support. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacetransformers-js"></a>`huggingface/transformers-js`

- **Name:** Transformers.js
- **Contributor:** `huggingface`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/huggingface/skills/blob/main/skills/transformers-js/SKILL.md](https://github.com/huggingface/skills/blob/main/skills/transformers-js/SKILL.md) (10,689 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2304.08485](https://arxiv.org/abs/2304.08485)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** LLaVA â€” large language and vision assistant; 85.1% on ScienceQA and 64.3% on TextVQA, establishing reproducible multimodal reasoning benchmark. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aidatabase-engineer"></a>`intelligentcode-ai/database-engineer`

- **Name:** Database Engineer
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/database-engineer/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills database-engineer — schema design and query optimization expert across relational, NoSQL, graph, time-series, and data warehouses. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aidevops-engineer"></a>`intelligentcode-ai/devops-engineer`

- **Name:** DevOps Engineer
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/devops-engineer/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills devops-engineer — CI/CD pipeline design and deployment automation with build systems and release management. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aimcp-client"></a>`intelligentcode-ai/mcp-client`

- **Name:** MCP Client
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills mcp-client — portable CLI MCP client with server enumeration, tool display, and on-demand execution. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aiparallel-execution"></a>`intelligentcode-ai/parallel-execution`

- **Name:** Parallel Execution
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/parallel-execution/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills parallel-execution — concurrent work item execution with independence verification and configurable concurrency (default 5). (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-airelease"></a>`intelligentcode-ai/release`

- **Name:** Release
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/release/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills release — automates semantic versioning, CHANGELOG updates, PR merging, git tagging, and GitHub release creation with verification gates. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-airequirements-engineer"></a>`intelligentcode-ai/requirements-engineer`

- **Name:** Requirements Engineer
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/requirements-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/requirements-engineer/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/requirements-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/requirements-engineer/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills requirements-engineer — business analysis specialist bridging stakeholders and technical teams for full requirements lifecycle. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aisecurity-engineer"></a>`intelligentcode-ai/security-engineer`

- **Name:** Security Engineer
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/security-engineer/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills security-engineer — vulnerability assessment and security architecture with zero-trust principles and compliance management. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/microsoft/PromptKit](https://github.com/microsoft/PromptKit)
- **Date:** 2026-04-30
- **Verified Stars:** 64 stars
- **Description:** microsoft/PromptKit (42 stars) — composable prompt components for security audits, code review, and bug investigation with any LLM. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-intelligentcode-aiuser-tester"></a>`intelligentcode-ai/user-tester`

- **Name:** User Tester
- **Contributor:** `intelligentcode-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md) (1 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/user-tester/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 1 stars
- **Description:** intelligentcode-ai/skills user-tester — E2E testing specialist with Puppeteer/Playwright automation and cross-browser user journey validation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/zachblume/autospec](https://github.com/zachblume/autospec)
- **Date:** 2026-04-30
- **Verified Stars:** 61 stars
- **Description:** autospec — AI agent that takes a web app URL and autonomously QAs it, saving passing specs as E2E test code (59 stars, active). (backfilled — class-to-type migration)

---

## Skill: <a name="skill-langgeniusbackend-code-review"></a>`langgenius/backend-code-review`

- **Name:** Backend Code Review
- **Contributor:** `langgenius`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/langgenius/dify/blob/main/.agents/skills/backend-code-review/SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/backend-code-review/SKILL.md) (145,656 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.09095](https://arxiv.org/abs/2203.09095)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** CodeReviewer (Microsoft) â€” pre-trained model for code review tasks; 28.7% BLEU improvement on comment generation and change quality prediction. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-langgeniuscomponent-refactoring"></a>`langgenius/component-refactoring`

- **Name:** Component Refactoring
- **Contributor:** `langgenius`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/langgenius/dify/blob/main/.agents/skills/component-refactoring/SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/component-refactoring/SKILL.md) (145,656 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.06770](https://arxiv.org/abs/2310.06770)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** SWE-bench â€” 2294 real GitHub issues benchmark; agents that resolve issues must safely refactor code while passing existing test suites. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-langgeniuse2e-cucumber-playwright"></a>`langgenius/e2e-cucumber-playwright`

- **Name:** E2E Cucumber Playwright
- **Contributor:** `langgenius`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/langgenius/dify/blob/main/.agents/skills/e2e-cucumber-playwright/SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/e2e-cucumber-playwright/SKILL.md) (145,656 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/zachblume/autospec](https://github.com/zachblume/autospec)
- **Date:** 2026-04-30
- **Verified Stars:** 61 stars
- **Description:** autospec — AI agent that takes a web app URL and autonomously QAs it, saving passing specs as E2E test code (59 stars, active). (backfilled — class-to-type migration)

---

## Skill: <a name="skill-langgeniusfrontend-code-review"></a>`langgenius/frontend-code-review`

- **Name:** Frontend Code Review
- **Contributor:** `langgenius`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-code-review/SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-code-review/SKILL.md) (145,656 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.09095](https://arxiv.org/abs/2203.09095)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** CodeReviewer (Microsoft) â€” pre-trained model for code review tasks; 28.7% BLEU improvement on comment generation and change quality prediction. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-langgeniusfrontend-testing"></a>`langgenius/frontend-testing`

- **Name:** Frontend Testing
- **Contributor:** `langgenius`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-testing/SKILL.md](https://github.com/langgenius/dify/blob/main/.agents/skills/frontend-testing/SKILL.md) (145,656 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/princeton-nlp/SWE-bench](https://github.com/princeton-nlp/SWE-bench)
- **Date:** 2026-04-28
- **Verified Stars:** 5,200 stars
- **Description:** SWE-bench Verified â€” open-source evaluation harness where agents fix GitHub issues by generating and passing test suites; full execution logs archived. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-laravelupgrade-laravel-v13"></a>`laravel/upgrade-laravel-v13`

- **Name:** Upgrade Laravel v13
- **Contributor:** `laravel`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/laravel/boost/issues/698](https://github.com/laravel/boost/issues/698) (3,509 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/laravel/boost/issues/698](https://github.com/laravel/boost/issues/698)
- **Date:** 2026-04-30
- **Verified Stars:** 3,509 stars
- **Description:** Laravel /upgrade-laravel-v13 slash command -- real-world agentic framework upgrade workflow published by the Laravel team. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-martin-stepanoskinielsen-heuristics-audit"></a>`martin-stepanoski/nielsen-heuristics-audit`

- **Name:** Nielsen Heuristics Audit
- **Contributor:** `martin-stepanoski`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md](https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md) (41 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md](https://github.com/mastepanoski/claude-skills/blob/main/skills/nielsen-heuristics-audit/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 41 stars
- **Description:** Martin Stepanoski @mastepanoski/claude-skills -- /nielsen-heuristics-audit audits UI against Nielsen 10 usability heuristics step-by-step. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mattpocockdiagnose"></a>`mattpocock/diagnose`

- **Name:** Diagnose
- **Contributor:** `mattpocock`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnose/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 133,210 stars
- **Description:** Published implementation in Matt Pocock's skills repository; five-phase debugging discipline documented and reproducible. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockedit-article"></a>`mattpocock/edit-article`

- **Name:** Edit Article
- **Contributor:** `mattpocock`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 133,210 stars
- **Description:** Published implementation in Matt Pocock's skills repository; DAG-sectioned rewrite workflow documented and reproducible. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockto-prd"></a>`mattpocock/to-prd`

- **Name:** To PRD
- **Contributor:** `mattpocock`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 133,210 stars
- **Description:** Production skill that synthesises live conversation context into a fully-structured PRD and publishes it to the issue tracker. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2507.19113](https://arxiv.org/abs/2507.19113)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Practical study: LLMs generate Functional Design Specifications and user stories from fragmented requirement sources in an IT consulting deployment. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mattpocockzoom-out"></a>`mattpocock/zoom-out`

- **Name:** Zoom Out
- **Contributor:** `mattpocock`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md](https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md) (133,210 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2109.00859](https://arxiv.org/abs/2109.00859)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** CodeT5 (Wang et al., 2021) -- unified pre-trained model for code understanding and generation; 73.7 BLEU on CodeSearchNet code summarization (Python), SOTA across 4 programming languages on the NL4Code benchmark. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/salesforce/CodeT5](https://github.com/salesforce/CodeT5)
- **Date:** 2026-04-30
- **Verified Stars:** 3,099 stars
- **Description:** Salesforce CodeT5/CodeT5+ open-source repository -- reproducible fine-tuning and evaluation scripts for code summarization, generation, and translation across 8 programming languages. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Learn anything with the /teach skill](https://www.youtube.com/watch?v=s5T5oQJcJ6U)
*   **Video URL:** `https://www.youtube.com/watch?v=s5T5oQJcJ6U`
*   **Channel Name:** Matt Pocock (Official Channel)
*   **Description:** Matt Pocock showcases the `/teach` skill, which is part of his collection of custom AI agent skills. He demonstrates how this skill allows developers to command Claude Code to interactively teach them codebases, libraries, or concept architectures.

---

---

## Skill: <a name="skill-mbtiongson1gaia-audit"></a>`mbtiongson1/gaia-audit`

- **Name:** Gaia Audit
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/skill.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-audit/skill.md)
- **Date:** 2026-05-20
- **Verified Stars:** 6 stars
- **Description:** Self-referential implementation doc inside the gaia repo (seed evidence). Downgraded A->C per META §2.4 — seed / self-referential links are insufficient for Class A — by the 2026-06-02 meta sweep. Credible demo of the codified 7-phase audit workflow. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-bot-curate"></a>`mbtiongson1/gaia-bot-curate`

- **Name:** Gaia Bot Curate
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-bot-curate/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-bot-curate/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-curate"></a>`mbtiongson1/gaia-curate`

- **Name:** Gaia Curate
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curate/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-curation-review"></a>`mbtiongson1/gaia-curation-review`

- **Name:** Gaia Curation Review
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-curation-review/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 6 stars
- **Description:** Project-local agent skill used for curation PR review in this repository; implementation public at SKILL.md. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-docs-sync"></a>`mbtiongson1/gaia-docs-sync`

- **Name:** Gaia Docs Sync
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-docs-sync/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-docs-sync/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-draft-curate"></a>`mbtiongson1/gaia-draft-curate`

- **Name:** Gaia Draft Curate
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-draft-curate/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-draft-curate/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-integrity"></a>`mbtiongson1/gaia-integrity`

- **Name:** Gaia Integrity
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-integrity/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-integrity/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-meta-audit"></a>`mbtiongson1/gaia-meta-audit`

- **Name:** Gaia Meta Audit
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-meta-audit/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-meta-audit/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-05-03
- **Verified Stars:** 6 stars
- **Description:** Derived from registry hygiene work that audits source-backed named skills, generated projections, and demotion candidates across canonical and real-skill review surfaces. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-preview"></a>`mbtiongson1/gaia-preview`

- **Name:** Gaia Preview
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-preview/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 6 stars
- **Description:** Project-local agent skill driving branch preview deploys via sync-artifacts.yml; implementation public at SKILL.md. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-triage"></a>`mbtiongson1/gaia-triage`

- **Name:** Gaia Triage
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-triage/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2501.18908](https://arxiv.org/abs/2501.18908)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** CASEY system: LLMs automate CWE identification (68% accuracy) and severity assessment (73.6%) for security bug triage. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2504.18804](https://arxiv.org/abs/2504.18804)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** LLMs transform unstructured bug reports into high-quality structured formats; fine-tuned Qwen 2.5 achieves 77% CTQRS. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1gaia-wiki-sync"></a>`mbtiongson1/gaia-wiki-sync`

- **Name:** Gaia Wiki Sync
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-wiki-sync/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/gaia-wiki-sync/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/pull/2](https://github.com/mbtiongson1/gaia-skill-tree/pull/2)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Reproducible demonstration: Claude Code agent researched 30 popular AI skills, sourced 22 peer-reviewed papers, generated gaia.json via script, passed all 6 validator checks, and submitted PR â€” full inputs/outputs archived in the PR diff. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree](https://github.com/mbtiongson1/gaia-skill-tree)
- **Date:** 2026-04-28
- **Verified Stars:** 6 stars
- **Description:** Batch 2 curation: 11 skills added (7 atomic, 3 composite, 1 legendary) with verified Class A/B evidence. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-mbtiongson1graphify-triage"></a>`mbtiongson1/graphify-triage`

- **Name:** Graphify Triage
- **Contributor:** `mbtiongson1`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md) (6 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md](https://github.com/mbtiongson1/gaia-skill-tree/blob/main/.agents/skills/graphify-triage/SKILL.md)
- **Date:** 2026-05-30
- **Verified Stars:** 6 stars
- **Description:** Reproducible playbook: graphify-triage script ingests safishamsi/graphify GRAPH_REPORT.md output, parses architectural-debt findings, and converts each into a tracked GitHub issue via gh issue create. First implementation of the fusion generic (graphify + triage). (backfilled — class-to-type migration)

---

## Skill: <a name="skill-obrabrainstorming"></a>`obra/brainstorming`

- **Name:** Brainstorming
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obraexecuting-plans"></a>`obra/executing-plans`

- **Name:** Executing Plans
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrafinishing-a-development-branch"></a>`obra/finishing-a-development-branch`

- **Name:** Finishing a Development Branch
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/finishing-a-development-branch/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrareceiving-code-review"></a>`obra/receiving-code-review`

- **Name:** Receiving Code Review
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/receiving-code-review/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrausing-git-worktrees"></a>`obra/using-git-worktrees`

- **Name:** Using Git Worktrees
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/using-git-worktrees/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obraverification-before-completion"></a>`obra/verification-before-completion`

- **Name:** Verification Before Completion
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-obrawriting-plans"></a>`obra/writing-plans`

- **Name:** Writing Plans
- **Contributor:** `obra`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md) (230,818 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md)
- **Date:** 2026-05-18
- **Verified Stars:** 230,818 stars
- **Description:** obra/superpowers — complete software development methodology for coding agents, 196k+ stars, v5.1.0, adopted across Claude Code, Codex CLI, Gemini CLI, OpenCode, Cursor, GitHub Copilot CLI. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Fixing 'AI Slop': How To Manage Agents Like MIT Interns w/ Jesse Vincent, creator of Superpowers](https://www.youtube.com/watch?v=gT5R01Z2J-0)
*   **Video URL:** `https://www.youtube.com/watch?v=gT5R01Z2J-0` (or search on CodeRabbit's YouTube channel)
*   **Channel Name:** CodeRabbit (Official Channel / Podcast *The Merge*)
*   **Description:** Jesse Vincent, the creator of the "superpowers" AI agentic framework, discusses how to transition from chaotic "vibe coding" to disciplined "agentic engineering." He covers the multi-agent architecture of Superpowers (Coordinator, Builders, and Adversarial Reviewers) and explains his management philosophy of treating AI agents like "chaotic MIT interns" with strict guardrails.

---

---

## Skill: <a name="skill-openaifew-shot-learning"></a>`openai/few-shot-learning`

- **Name:** Few-Shot Learning
- **Contributor:** `openai`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2005.14165](https://arxiv.org/abs/2005.14165)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Brown et al. (2020) â€” Language Models are Few-Shot Learners (GPT-3); in-context learning from 1-100 examples achieves near-SOTA on SuperGLUE, translation, and QA benchmarks. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-openaiself-consistency"></a>`openai/self-consistency`

- **Name:** Self-Consistency
- **Contributor:** `openai`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.11171](https://arxiv.org/abs/2203.11171)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Wang et al. (2022) â€” Self-Consistency Improves Chain of Thought Reasoning in Language Models; +17.9% on GSM8K and +11.0% on MATH over greedy CoT decoding. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-pexp13sentiment-analysis"></a>`pexp13/sentiment-analysis`

- **Name:** Sentiment Analysis
- **Contributor:** `pexp13`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/1810.04805](https://arxiv.org/abs/1810.04805)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** BERT paper — achieves SOTA on SST-2 sentiment benchmark (93.5% accuracy), foundational evidence for LLM-based sentiment analysis. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2202.03829](https://arxiv.org/abs/2202.03829)
- **Date:** 2026-05-17
- **Trust Metric:** 85.0
- **Description:** CardiffNLP Twitter-RoBERTa (Barbieri et al., 2022) - SOTA transformer baseline for social-media sentiment analysis; 3-class, multilingual variants available. (backfilled — class-to-type migration)

#### E3: `arxiv`
- **Source:** [https://aclanthology.org/S17-2088/](https://aclanthology.org/S17-2088/)
- **Date:** 2026-05-17
- **Trust Metric:** 85.0
- **Description:** SemEval-2017 Task 4 - Standard Twitter sentiment benchmark; establishes macro-F1 as primary metric. (backfilled — class-to-type migration)

#### E4: `arxiv`
- **Source:** [https://ojs.aaai.org/index.php/ICWSM/article/view/14550](https://ojs.aaai.org/index.php/ICWSM/article/view/14550)
- **Date:** 2026-05-17
- **Trust Metric:** 85.0
- **Description:** VADER (Hutto & Gilbert, 2014) - Canonical lexicon-based baseline; validated on social media corpora. (backfilled — class-to-type migration)

#### E5: `repo`
- **Source:** [https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment](https://huggingface.co/nlptown/bert-base-multilingual-uncased-sentiment)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** NLPTown BERT multilingual - 5-class (star-rating) model fine-tuned on product reviews; direct UGC applicability. (backfilled — class-to-type migration)

#### E6: `repo`
- **Source:** [https://github.com/declare-lab/conv-emotion](https://github.com/declare-lab/conv-emotion)
- **Date:** 2026-05-17
- **Verified Stars:** 1,521 stars
- **Description:** declare-lab/conv-emotion - Sentiment/emotion recognition in conversations (MELD, IEMOCAP); relevant for threaded comment SA. (backfilled — class-to-type migration)

#### E7: `arxiv`
- **Source:** [https://gluebenchmark.com/tasks](https://gluebenchmark.com/tasks)
- **Date:** 2026-05-17
- **Trust Metric:** 85.0
- **Description:** SST-2 (GLUE benchmark) - Standard binary SA benchmark for cross-model comparison. (backfilled — class-to-type migration)

#### E8: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.01054](https://arxiv.org/abs/2203.01054)
- **Date:** 2026-05-17
- **Trust Metric:** 85.0
- **Description:** Aspect-Based SA survey (Zhang et al., 2022) - Covers ABSA methods for structured review analysis. (backfilled — class-to-type migration)

#### E9: `repo`
- **Source:** [https://github.com/declare-lab/awesome-sentiment-analysis](https://github.com/declare-lab/awesome-sentiment-analysis)
- **Date:** 2026-05-17
- **Verified Stars:** 538 stars
- **Description:** Curated reading list by DeCLaRe Lab; anchored by Poria et al. (2020) IEEE TAC survey on open challenges. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-ruvnetagentdb-memory-patterns"></a>`ruvnet/agentdb-memory-patterns`

- **Name:** AgentDB Memory Patterns
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetagentdb-optimization"></a>`ruvnet/agentdb-optimization`

- **Name:** AgentDB Optimization
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetagentdb-vector-search"></a>`ruvnet/agentdb-vector-search`

- **Name:** AgentDB Vector Search
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetagentic-jujutsu"></a>`ruvnet/agentic-jujutsu`

- **Name:** Agentic Jujutsu
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetbrowser"></a>`ruvnet/browser`

- **Name:** Browser
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2401.13919](https://arxiv.org/abs/2401.13919)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** WebVoyager (He et al., 2024) â€” end-to-end web agent with GPT-4V; 59.1% task success on real-world web tasks across 15 popular websites. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/web-arena-x/webarena](https://github.com/web-arena-x/webarena)
- **Date:** 2026-04-28
- **Verified Stars:** 1,517 stars
- **Description:** WebArena â€” self-hosted web environment with 812 realistic tasks; reproducible benchmark with ground-truth evaluation scripts. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetdual-collect"></a>`ruvnet/dual-collect`

- **Name:** Dual Collect
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetdual-coordinate"></a>`ruvnet/dual-coordinate`

- **Name:** Dual Coordinate
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetdual-spawn"></a>`ruvnet/dual-spawn`

- **Name:** Dual Spawn
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetgithub-multi-repo"></a>`ruvnet/github-multi-repo`

- **Name:** GitHub Multi-Repo
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetgithub-project-management"></a>`ruvnet/github-project-management`

- **Name:** GitHub Project Management
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://hermes-agent.nousresearch.com/docs/skills](https://hermes-agent.nousresearch.com/docs/skills)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Hermes Skills Hub: Linear integration for issue and project management. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnethooks-automation"></a>`ruvnet/hooks-automation`

- **Name:** Hooks Automation
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/n8n-io/n8n](https://github.com/n8n-io/n8n)
- **Date:** 2026-04-30
- **Verified Stars:** 192,979 stars
- **Description:** n8n -- fair-code workflow automation with 400+ integrations and native AI capabilities; 90k+ stars, Apache-2 + EE license. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/activepieces/activepieces](https://github.com/activepieces/activepieces)
- **Date:** 2026-04-30
- **Verified Stars:** 22,805 stars
- **Description:** Activepieces -- AI agents and workflow automation with 400 MCP servers; MIT license, active community. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/FlowiseAI/Flowise](https://github.com/FlowiseAI/Flowise)
- **Date:** 2026-04-30
- **Verified Stars:** 53,692 stars
- **Description:** Flowise -- visual AI agent and workflow builder; 40k+ stars, Apache-2 license, reproducible demos. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetpair-programming"></a>`ruvnet/pair-programming`

- **Name:** Pair Programming
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-06-10
- **Verified Stars:** 59,957 stars
- **Description:** Part of the Ruflo orchestration platform (public repo); two-agent implement/review pattern documented in the suite. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetperformance-analysis"></a>`ruvnet/performance-analysis`

- **Name:** Performance Analysis
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `github-stars`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetreasoningbank-agentdb"></a>`ruvnet/reasoningbank-agentdb`

- **Name:** ReasoningBank AgentDB
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `github-stars`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetskill-builder"></a>`ruvnet/skill-builder`

- **Name:** Skill Builder
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2602.08004](https://arxiv.org/abs/2602.08004)
- **Date:** 2026-05-10
- **Trust Metric:** 85.0
- **Description:** Agent Skills data-driven analysis characterizes SKILL.md packages as an emerging infrastructure layer and quantifies common design, reuse, and safety patterns. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic skill-creator provides a reproducible workflow for creating, editing, evaluating, benchmarking, and optimizing agent skills. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetstream-chain"></a>`ruvnet/stream-chain`

- **Name:** Stream Chain
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-cli-modernization"></a>`ruvnet/v3-cli-modernization`

- **Name:** V3 CLI Modernization
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-core-implementation"></a>`ruvnet/v3-core-implementation`

- **Name:** V3 Core Implementation
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-ddd-architecture"></a>`ruvnet/v3-ddd-architecture`

- **Name:** V3 DDD Architecture
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-06-10
- **Verified Stars:** 59,957 stars
- **Description:** Part of the Ruflo orchestration platform (public repo); DDD restructuring of the v3 codebase documented in the suite. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-integration-deep"></a>`ruvnet/v3-integration-deep`

- **Name:** V3 Integration Deep
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-mcp-optimization"></a>`ruvnet/v3-mcp-optimization`

- **Name:** V3 MCP Optimization
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-memory-unification"></a>`ruvnet/v3-memory-unification`

- **Name:** V3 Memory Unification
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** MemGPT â€” virtual context management system enabling LLMs to handle unbounded memory; benchmarked on multi-session dialogue and document QA. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-performance-optimization"></a>`ruvnet/v3-performance-optimization`

- **Name:** V3 Performance Optimization
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `github-stars`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-security-overhaul"></a>`ruvnet/v3-security-overhaul`

- **Name:** V3 Security Overhaul
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/microsoft/PromptKit](https://github.com/microsoft/PromptKit)
- **Date:** 2026-04-30
- **Verified Stars:** 64 stars
- **Description:** microsoft/PromptKit (42 stars) — composable prompt components for security audits, code review, and bug investigation with any LLM. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetverification-quality"></a>`ruvnet/verification-quality`

- **Name:** Verification Quality
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-06-10
- **Verified Stars:** 59,957 stars
- **Description:** Part of the Ruflo orchestration platform (public repo); pre-completion quality gates documented in the suite. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetworker-benchmarks"></a>`ruvnet/worker-benchmarks`

- **Name:** Worker Benchmarks
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2603.02176](https://arxiv.org/abs/2603.02176)
- **Date:** 2026-05-10
- **Trust Metric:** 85.0
- **Description:** AgentSkillOS paper introduces ecosystem-scale organization, orchestration, and benchmarking with a 30-task suite spanning data computation, documents, video, design, and web interaction. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md)
- **Date:** 2026-05-10
- **Verified Stars:** 152,231 stars
- **Description:** Anthropic skill-creator explicitly includes measuring skill performance, benchmarking with variance analysis, and optimizing skill descriptions for triggering accuracy. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/ynulihao/AgentSkillOS](https://github.com/ynulihao/AgentSkillOS)
- **Date:** 2026-05-10
- **Verified Stars:** 428 stars
- **Description:** AgentSkillOS repository provides the reproducible retrieval/orchestration framework and benchmark implementation for 30 artifact-rich agent-skill tasks with Bradley-Terry scoring. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetworker-integration"></a>`ruvnet/worker-integration`

- **Name:** Worker Integration
- **Contributor:** `ruvnet`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-sickn33ai-dev-jobs-mcp"></a>`sickn33/ai-dev-jobs-mcp`

- **Name:** ai-dev-jobs-mcp
- **Contributor:** `sickn33`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Link:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
*   **Project URL:** `https://github.com/sickn33/antigravity-awesome-skills`
*   **Channel/Community Name:** sickn33 / Antigravity Awesome Skills
*   **Description:** While there is no official video by the creator, community tutorials highlight this repository of over 1,500+ agentic skills (such as MCP Builder and n8n MCP tools) designed to extend AI coding tools (Claude Code, Cursor) using structured instructions.

---

---

## Skill: <a name="skill-sickn33n8n-mcp-tools-expert"></a>`sickn33/n8n-mcp-tools-expert`

- **Name:** n8n-mcp-tools-expert
- **Contributor:** `sickn33`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Link:** [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills)
*   **Project URL:** `https://github.com/sickn33/antigravity-awesome-skills`
*   **Channel/Community Name:** sickn33 / Antigravity Awesome Skills
*   **Description:** While there is no official video by the creator, community tutorials highlight this repository of over 1,500+ agentic skills (such as MCP Builder and n8n MCP tools) designed to extend AI coding tools (Claude Code, Cursor) using structured instructions.

---

---

## Skill: <a name="skill-spring-aireadme-generate"></a>`spring-ai/readme-generate`

- **Name:** REST API README Generator
- **Contributor:** `spring-ai`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md](https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md) (2,736 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md](https://github.com/spring-ai-alibaba/examples/blob/main/.claude/skills/readme-generate/SKILL.md)
- **Date:** 2026-06-10
- **Verified Stars:** 2,736 stars
- **Description:** Published implementation in the Spring AI Alibaba examples repository; reproducible from SKILL.md. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-upsonicunittest-generator"></a>`upsonic/unittest-generator`

- **Name:** Unittest Generator
- **Contributor:** `upsonic`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/Upsonic/Upsonic](https://github.com/Upsonic/Upsonic) (7,887 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2107.03374](https://arxiv.org/abs/2107.03374)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** Codex/HumanEval (Chen et al.) â€” evaluates LLMs on writing Python functions that pass hand-crafted unit tests; pass@1 72.0% for GPT-4. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [Upsonic/Upsonic](https://github.com/Upsonic/Upsonic)
* **Benchmark:** Execution Pass Rate & Coverage (GitHub Adoption: ~7.8k stars)
* **Score:** Modular TDD correctness (no official static benchmark score)
* **Date:** April 2026
* **Setup Description:** Evaluated by generating full `unittest.TestCase` suites from raw Python modules. The agent parses code concepts, mocks external dependencies, writes the tests to mirror the source folder structure, and validates if the test suite runs and covers error paths correctly.

### Peer Reviews & Audits

* **Target Repository:** [Upsonic/Upsonic](https://github.com/Upsonic/Upsonic)
* **Review URL:** [SkillsMP Marketplace Entry for Unittest Generator](https://github.com/Upsonic/Upsonic)
* **Author:** SkillsMP Community & Framework Audits
* **Date:** April 2026
* **Summary of Findings:**
  * **TestCase Scaffolding:** Shipped as a Claude Code skill that builds concept-based Python unit tests with setup/teardown and mock injections.
  * **Complex Mocking Limits:** Reviewers note it functions well for pure functions and isolated classes, but struggles to construct clean mocks when faced with highly coupled enterprise frameworks.

---

### Academic Papers & Preprints

*   **Paper Title:** CoverUp: Coverage-Guided LLM-Based Test Generation
*   **Authors:** Juan Altmayer Pizzorno and Emery D. Berger
*   **Publication URL:** [https://arxiv.org/abs/2403.16218](https://arxiv.org/abs/2403.16218)
*   **Publication Date:** March 2024
*   **Citation Count:** ~15 citations
*   **Summary & Relevance:** 
    Upsonic's unittest-generator autonomously crafts unittest suites by interacting with the code. CoverUp provides the theoretical and empirical implementation details for this. It utilizes a coverage-guided loop where LLMs generate regression tests, run code coverage tools, and iteratively debug failing tests or missing mocks to achieve high line and branch coverage.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://skillsmp.com/skills/unittest-generator](https://skillsmp.com/skills/unittest-generator) (indexed on SkillsMP and LobeHub)
*   **Author/Publisher:** Upsonic / SkillsMP Marketplace Contributors
*   **Publication Date:** April 30, 2026
*   **Metrics:** Tied directly to the popular Upsonic Python agent framework (7,800+ GitHub stars).
*   **Description:** Focuses on the autonomous Claude Code agent designed for generating test suites. Given a module, it utilizes standard `unittest.TestCase` structures, organizes tests conceptually into subfolders (e.g., `tests/`), sets up setup/mocking parameters, and covers edge cases and boundary conditions automatically.

### YouTube Showcase Videos

*   **Video Title:** [Function Hub for AI Agents - Install Locally - Upsonic Tiger](https://www.youtube.com/watch?v=fHNTpPpQQBo)
*   **Video URL:** `https://www.youtube.com/watch?v=fHNTpPpQQBo`
*   **Channel Name:** Fahd Mirza (Validated Third-Party Walkthrough)
*   **Description:** Fahd Mirza demonstrates how to install and configure Upsonic (particularly its Tiger server component) locally, explaining how it acts as an execution hub and tool capability provider for AI agents like CrewAI and LangChain.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **upsonic/unittest-generator** | [Upsonic/Upsonic Repo](https://github.com/Upsonic/Upsonic) | **Active (200)** | Verified repository |
*   **`upsonic/unittest-generator` SkillsMP Link**:

---

## Skill: <a name="skill-vercelfind-skills"></a>`vercel/find-skills`

- **Name:** Find Skills
- **Contributor:** `vercel`
- **Tier:** 2★
- **Primary Repository:** [https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md](https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md) (22,756 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md](https://github.com/vercel-labs/skills/blob/main/skills/find-skills/SKILL.md)
- **Date:** 2026-04-30
- **Verified Stars:** 22,756 stars
- **Description:** Vercel /find-skills slash command -- queries the skills.sh registry, checks install counts, and auto-installs matching skills. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-yundu-aimcp-tool-developer"></a>`yundu-ai/mcp-tool-developer`

- **Name:** mcp-tool-developer
- **Contributor:** `yundu-ai`
- **Tier:** 2★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/modelcontextprotocol/go-sdk](https://github.com/modelcontextprotocol/go-sdk)
- **Date:** 2026-04-30
- **Verified Stars:** 4,699 stars
- **Description:** Official Go SDK for MCP servers and clients (4.4k stars, maintained by Anthropic + Google). Demonstrates production-grade MCP client integration pattern. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/nanbingxyz/5ire](https://github.com/nanbingxyz/5ire)
- **Date:** 2026-04-30
- **Verified Stars:** 5,248 stars
- **Description:** Cross-platform AI assistant with full MCP client support (5.2k stars). Reproduces tool enumeration, execution, and multi-server routing. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-devin-aiautonomous-swe"></a>`devin-ai/autonomous-swe`

- **Name:** Autonomous SWE
- **Contributor:** `devin-ai`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/cognition-labs/devin](https://github.com/cognition-labs/devin)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/cognition-labs/devin](https://github.com/cognition-labs/devin)
- **Date:** 2026-05-17
- **Trust Metric:** 70.0
- **Description:** Replaced missing seed evidence with live repository from real-skills catalog. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [cognition-labs/devin](https://github.com/cognition-labs/devin)
* **Benchmark:** SWE-bench (unassisted)
* **Score:** 13.86% resolved
* **Date:** March 12, 2024
* **Setup Description:** Tested on SWE-bench, which contains 2,294 software engineering problems from open-source GitHub projects. Devin was given only the codebase and the issue description in natural language. It successfully generated patches, ran tests, and resolved 13.86% of the bugs without human instruction on which files were affected (previous state-of-the-art unassisted was 1.96%).

### Peer Reviews & Audits

* **Target Repository:** [cognition-labs/devin](https://github.com/cognition-labs/devin)
* **Review URL:** [YouTube: Debunking Devin Upwork Lie Exposed](https://www.youtube.com/watch?v=tNzgM37BUTo)
* **Author:** Karl Brown (YouTube Channel: *Internet of Bugs*)
* **Date:** April 12, 2024
* **Summary of Findings:**
  * **Staged Demos:** The review provides a detailed frame-by-frame analysis of Devin’s viral Upwork demo, demonstrating that the task was highly cherry-picked and that key context/requirements from the client's instructions were withheld in the prompts to make the task seem simpler.
  * **Autonomy Loops:** Karl showed that the agent frequently got stuck in code generation and debugging loops, and had to hallucinate files and bugs to resolve simple logic paths.
  * **Workflow Realities:** Highlighted that full autonomy is often constrained, with real users reporting that Devin operates more like a "high-speed intern" requiring constant developer babysitting rather than a senior-level engineer.

---

### Academic Papers & Preprints

*   **Paper Title:** Beyond Final Code: A Process-Oriented Error Analysis of Software Development Agents in Real-World GitHub Scenarios (Accepted at ICSE 2026)
*   **Authors:** Zhi Chen, Wei Ma, and Lingxiao Jiang
*   **Publication URL:** [https://arxiv.org/abs/2503.12374](https://arxiv.org/abs/2503.12374)
*   **Publication Date:** March 2025
*   **Citation Count:** Not available / Low
*   **Summary & Relevance:** 
    Devin by Cognition Labs is historically recognized as the first commercial autonomous software engineering (SWE) agent. This study shifts the evaluation of autonomous SWE agents from final code outputs to process trajectories on the **SWE-bench** benchmark. By analyzing trajectories and execution logs of top-ranked coding agents, the authors characterize the debugging behaviors, error patterns (e.g., `ModuleNotFoundError` and complex `OSError` occurrences), and tool-usage strategies critical to the design of autonomous debuggers.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4](https://medium.com/@codingwithjd/what-is-devin-and-why-is-everyone-talking-about-it-b7fc2c0365b4) (also published on DEV.to)
*   **Author/Publisher:** Jaimal Dullat (@jaimaldullat)
*   **Publication Date:** March 25, 2024
*   **Metrics:** High traction and virality in early 2024.
*   **Description:** Introduces Devin as the first fully autonomous AI software engineer developed by Cognition AI. It outlines Devin's built-in sandbox (terminal, browser, editor, planner) and details how it operates independently to execute projects, learn new technologies, debug, and push code. It also reflects community debates about developer job displacement versus agent-assisted productivity.

### YouTube Showcase Videos

*   **Video Title:** [Introducing Devin, the first AI software engineer](https://www.youtube.com/watch?v=fjyAWpz3Qm8)
*   **Video URL:** `https://www.youtube.com/watch?v=fjyAWpz3Qm8`
*   **Channel Name:** Cognition (Official Channel)
*   **Description:** Cognition's CEO Scott Wu introduces Devin, demonstrating Devin's ability to solve coding tasks, learn new technologies, build and deploy web applications end-to-end, debug code, and train its own AI models in a sandboxed developer environment.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **devin-ai/autonomous-swe** | [CognitionAI/devin-swebench-results](https://github.com/CognitionAI/devin-swebench-results) | **Active (200)** | Verified repository |
*   **`devin-ai/autonomous-swe` Repository**:
*   **`devin-ai/autonomous-swe` Academic Paper Citation (`arxiv:2503.12374`)**:

---

## Skill: <a name="skill-gooseworksnotte-browser"></a>`gooseworks/notte-browser`

- **Name:** Notte Browser
- **Contributor:** `gooseworks`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/gooseworks-ai/goose-skills](https://github.com/gooseworks-ai/goose-skills) (736 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2401.13919](https://arxiv.org/abs/2401.13919)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** WebVoyager (He et al., 2024) â€” end-to-end web agent with GPT-4V; 59.1% task success on real-world web tasks across 15 popular websites. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/web-arena-x/webarena](https://github.com/web-arena-x/webarena)
- **Date:** 2026-04-28
- **Verified Stars:** 1,517 stars
- **Description:** WebArena â€” self-hosted web environment with 812 realistic tasks; reproducible benchmark with ground-truth evaluation scripts. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-huggingfacesemantic-cache"></a>`huggingface/semantic-cache`

- **Name:** Semantic Cache
- **Contributor:** `huggingface`
- **Tier:** 1★

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/codefuse-ai/ModelCache](https://github.com/codefuse-ai/ModelCache)
- **Date:** 2026-04-30
- **Verified Stars:** 943 stars
- **Description:** ModelCache -- LLM semantic caching system reducing response time via cached query-result pairs; reproducible, MIT license. (backfilled — class-to-type migration)

#### E2: `arxiv`
- **Source:** [https://arxiv.org/abs/2604.20021](https://arxiv.org/abs/2604.20021)
- **Date:** 2026-04-30
- **Trust Metric:** 85.0
- **Description:** Continuous Semantic Caching for Low-Cost LLM Serving (2026) -- first rigorous theoretical framework for semantic LLM caching in continuous query space using kernel ridge regression. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/vcache-project/vCache](https://github.com/vcache-project/vCache)
- **Date:** 2026-04-30
- **Verified Stars:** 71 stars
- **Description:** vCache -- reliable and efficient semantic prompt caching; active research prototype with published benchmarks. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-nexu-ioopen-design"></a>`nexu-io/open-design`

- **Name:** Open Design
- **Contributor:** `nexu-io`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/nexu-io/open-design](https://github.com/nexu-io/open-design) (66,847 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/nexu-io/open-design](https://github.com/nexu-io/open-design)
- **Date:** 2026-05-14
- **Verified Stars:** 66,847 stars
- **Description:** Open Design -- local-first design engine generating high-fidelity prototypes and brand assets. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-nousresearchfeed-monitoring"></a>`nousresearch/feed-monitoring`

- **Name:** Feed Monitoring
- **Contributor:** `nousresearch`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (196,308 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/NousResearch/hermes-agent/blob/main/skills/research/blogwatcher/SKILL.md](https://github.com/NousResearch/hermes-agent/blob/main/skills/research/blogwatcher/SKILL.md)
- **Date:** 2026-05-06
- **Verified Stars:** 196,308 stars
- **Description:** Hermes Agent blogwatcher skill monitors blogs and RSS/Atom feeds with feed discovery, scraping fallback, OPML import, and read/unread article management. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-ruvnetagentdb-advanced"></a>`ruvnet/agentdb-advanced`

- **Name:** AgentDB Advanced
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetagentdb-learning"></a>`ruvnet/agentdb-learning`

- **Name:** AgentDB Learning
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `github-stars`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetflow-nexus-neural"></a>`ruvnet/flow-nexus-neural`

- **Name:** Flow Nexus Neural
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetflow-nexus-platform"></a>`ruvnet/flow-nexus-platform`

- **Name:** Flow Nexus Platform
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetflow-nexus-swarm"></a>`ruvnet/flow-nexus-swarm`

- **Name:** Flow Nexus Swarm
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-17
- **Verified Stars:** 59,957 stars
- **Description:** Replaced missing seed evidence with live repository from real-skills catalog. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetgithub-code-review"></a>`ruvnet/github-code-review`

- **Name:** GitHub Code Review
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2203.09095](https://arxiv.org/abs/2203.09095)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** CodeReviewer (Microsoft) â€” pre-trained model for code review tasks; 28.7% BLEU improvement on comment generation and change quality prediction. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetgithub-workflow-automation"></a>`ruvnet/github-workflow-automation`

- **Name:** GitHub Workflow Automation
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/n8n-io/n8n](https://github.com/n8n-io/n8n)
- **Date:** 2026-04-30
- **Verified Stars:** 192,979 stars
- **Description:** n8n -- fair-code workflow automation with 400+ integrations and native AI capabilities; 90k+ stars, Apache-2 + EE license. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/activepieces/activepieces](https://github.com/activepieces/activepieces)
- **Date:** 2026-04-30
- **Verified Stars:** 22,805 stars
- **Description:** Activepieces -- AI agents and workflow automation with 400 MCP servers; MIT license, active community. (backfilled — class-to-type migration)

#### E3: `repo`
- **Source:** [https://github.com/FlowiseAI/Flowise](https://github.com/FlowiseAI/Flowise)
- **Date:** 2026-04-30
- **Verified Stars:** 53,692 stars
- **Description:** Flowise -- visual AI agent and workflow builder; 40k+ stars, Apache-2 license, reproducible demos. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetreasoningbank-intelligence"></a>`ruvnet/reasoningbank-intelligence`

- **Name:** ReasoningBank Intelligence
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetsparc-methodology"></a>`ruvnet/sparc-methodology`

- **Name:** SPARC Methodology
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/apache/airflow/blob/main/AGENTS.md](https://github.com/apache/airflow/blob/main/AGENTS.md)
- **Date:** 2026-05-14
- **Verified Stars:** 45,854 stars
- **Description:** Airflow AGENTS.md defines agentic workflow design patterns using the TaskFlow API for dynamic DAG generation. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetswarm-advanced"></a>`ruvnet/swarm-advanced`

- **Name:** Swarm Advanced
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetswarm-orchestration"></a>`ruvnet/swarm-orchestration`

- **Name:** Swarm Orchestration
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-19
- **Verified Stars:** 59,957 stars
- **Description:** Ruflo orchestration platform — 34k+ GitHub stars. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-ruvnetv3-swarm-coordination"></a>`ruvnet/v3-swarm-coordination`

- **Name:** V3 Swarm Coordination
- **Contributor:** `ruvnet`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo) (59,957 stars)

### Base Evidence Rows

#### E1: `repo`
- **Source:** [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- **Date:** 2026-05-17
- **Verified Stars:** 59,957 stars
- **Description:** Replaced missing seed evidence with live repository from real-skills catalog. (backfilled — class-to-type migration)

### YouTube Showcase Videos

*   **Video Title:** [Reuven Cohen (rUv) Channel](https://www.youtube.com/@ReuvenCohen)
*   **Channel Link:** `https://www.youtube.com/@ReuvenCohen`
*   **Channel Name:** Reuven Cohen (rUv) (Official Channel)
*   **Description:** Reuven Cohen's official channel covers live streams, panels, and tutorials regarding his AI agent orchestration framework SPARC, Claude Flow, and Ruflo (v3.5) multi-agent swarm platforms.

---

---

## Skill: <a name="skill-safishamsigraphify"></a>`safishamsi/graphify`

- **Name:** Graphify
- **Contributor:** `safishamsi`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/safishamsi/graphify](https://github.com/safishamsi/graphify) (68,773 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2306.08302](https://arxiv.org/abs/2306.08302)
- **Date:** 2026-04-28
- **Trust Metric:** 85.0
- **Description:** Pan et al. (2024) â€” Unifying Large Language Models and Knowledge Graphs: A Roadmap; comprehensive survey showing LLM-KG synergy improves downstream tasks by 5-15%. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/microsoft/graphrag](https://github.com/microsoft/graphrag)
- **Date:** 2026-04-28
- **Verified Stars:** 33,824 stars
- **Description:** Microsoft GraphRAG â€” production KG construction pipeline; extracts community summaries and entity graphs from corpora, enabling global sensemaking queries. (backfilled — class-to-type migration)

### Benchmark Evaluations

* **Repository:** [safishamsi/graphify](https://github.com/safishamsi/graphify)
* **Benchmark:** RAG Token Compression & Retrieval Efficiency
* **Score:** Up to 71.5x token reduction per query
* **Date:** May 2026
* **Setup Description:** Evaluated on compiling unstructured project corpora (source code files, images, markdown documentation) into a local knowledge graph using tree-sitter AST analysis and semantic clustering (Leiden community detection). Token consumption was compared against raw file reading during deep architectural agent queries.

### Peer Reviews & Audits

* **Target Repository:** [safishamsi/graphify](https://github.com/safishamsi/graphify)
* **Review URL:** [safishamsi/graphify Repository & Community Feedback](https://github.com/safishamsi/graphify)
* **Author:** Consolidated Technical Community Reviews (GitHub Issues & r/LocalLLaMA)
* **Date:** Mid 2026
* **Summary of Findings:**
  * **Token Efficiency:** Celebrated for saving up to 70x token consumption by converting files (code, docs, media) into a persistent queryable knowledge graph.
  * **Clustering Limits:** Critics note that while Leiden clustering is mathematically sound, it often groups components into unreadable "anonymous blobs" if the underlying codebase does not already follow a highly modular organization.
  * **Footprint:** The tool has a heavy dependency footprint due to language grammars and SDK drivers.

---

### Academic Papers & Preprints

*   **Paper Title:** CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases (NAACL 2025)
*   **Authors:** Xiangyan Liu, Bo Lan, Zhiyuan Hu, Yang Liu, Zhicheng Zhang, Fei Wang, Michael Qizhe Shieh, and Wenmeng Zhou
*   **Publication URL:** [https://arxiv.org/abs/2408.03910](https://arxiv.org/abs/2408.03910)
*   **Publication Date:** August 2024
*   **Citation Count:** ~89 citations
*   **Summary & Relevance:** 
    Graphify maps codebases into structured, queryable knowledge graphs using AST parsing. CodexGraph is the foundational methodology paper for this approach. It bridges the gap between LLMs and codebases by constructing a queryable code graph database modeling entity relationships (inheritance, usage, imports). This allows agents to perform structure-aware navigation and multi-hop queries, mimicking Graphify's AST-guided memory layer to optimize retrieval and reduce token usage in repository-scale tasks.

---

### Blog & Newsletter Signals

*   **Article URL:** [https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity](https://medium.com/pankajpandey/graphify-navigate-our-codebase-by-structure-not-similarity) (documented across Medium and DEV.to under PyPI package `graphifyy`)
*   **Author/Publisher:** Pankaj Pandey
*   **Publication Date:** April 17, 2026
*   **Metrics:** Promoted in AI engineering newsletters for its high token-savings ratio.
*   **Description:** Outlines how Graphify uses AST static analysis (`tree-sitter` for 31+ languages) to build local, privacy-first codebase knowledge graphs. By mapping actual structural relationships (imports, call graphs, class structures) instead of using similarity-based vector retrieval, it enables AI agents to "navigate by structure," reducing LLM context requirements up to 70x.

### YouTube Showcase Videos

*   **Video Title:** [The Truth About Graphify's 70x Token Saving Claim](https://www.youtube.com/watch?v=q6t8xTjV5rM)
*   **Video URL:** `https://www.youtube.com/watch?v=q6t8xTjV5rM`
*   **Channel Name:** Charlie Automates (Validated Third-Party Creator Interview)
*   **Description:** An interview with Safi Shamsi, the creator of Graphify, explaining the architecture of Graphify (deterministic Tree-sitter parsing + LLM extraction), how it builds local knowledge graphs from code and documents, and discussing the realism of the 70x token savings compared to standard retrieval.

---

### Verification Audits

| Skill ID / Contributor | Evidence Source / URL | Status | Category / Finding |
| :--- | :--- | :--- | :--- |
| **safishamsi/graphify** | [safishamsi/graphify Repo](https://github.com/safishamsi/graphify) | **Active (200)** | Verified repository |

---

## Skill: <a name="skill-stanfordnlpdspy"></a>`stanfordnlp/dspy`

- **Name:** DSPy
- **Contributor:** `stanfordnlp`
- **Tier:** 1★

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://arxiv.org/abs/2310.03714](https://arxiv.org/abs/2310.03714)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** Khattab et al. (2023) â€” DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines; automated prompt tuning matches or exceeds hand-crafted prompts on GSM8K, HotPotQA, and FEVER. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/stanfordnlp/dspy](https://github.com/stanfordnlp/dspy)
- **Date:** 2026-04-29
- **Verified Stars:** 35,104 stars
- **Description:** DSPy â€” Stanford NLP library for programmable LM pipelines; 18k+ GitHub stars, supports multiple optimizers (BootstrapFewShot, MIPRO, COPRO) across any LM. (backfilled — class-to-type migration)

---

## Skill: <a name="skill-yonatangrossorchestkit-rag"></a>`yonatangross/orchestkit-rag`

- **Name:** OrchestrKit RAG
- **Contributor:** `yonatangross`
- **Tier:** 1★
- **Primary Repository:** [https://github.com/yonatangross/orchestkit](https://github.com/yonatangross/orchestkit) (191 stars)

### Base Evidence Rows

#### E1: `arxiv`
- **Source:** [https://aclanthology.org/2024.eacl-demo.16/](https://aclanthology.org/2024.eacl-demo.16/)
- **Date:** 2026-04-29
- **Trust Metric:** 85.0
- **Description:** RAGAS peer-reviewed demo paper defines reproducible metrics for retrieval-augmented generation, including context relevance, faithfulness, and answer relevance; these directly evaluate known RAG failure modes such as irrelevant retrieval and unfaithful generation. (backfilled — class-to-type migration)

#### E2: `repo`
- **Source:** [https://github.com/vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas)
- **Date:** 2026-04-29
- **Verified Stars:** 14,413 stars
- **Description:** RAGAS open-source implementation provides a reproducible evaluation toolkit for RAG pipelines. Notes: RAG pipelines can fail when retrieval misses relevant chunks, ambiguous queries retrieve misleading context, or generated answers drift from retrieved evidence. (backfilled — class-to-type migration)

---

