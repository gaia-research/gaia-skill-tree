# Plan: Firecrawl Skills Suite Integration & Promotion

This plan outlines the step-by-step procedure to promote the Firecrawl skill batch from the newly created intake issue (#1132), fuse the components into a consolidated `firecrawl-skills` ultimate suite, and bootstrap upstream version tracking.

---

## 1. Intake Status

- **Intake Issue:** https://github.com/gaia-research/gaia-skill-tree/issues/1132
- **Proposed Components (6 skills):**
  1. `web-scrape-integration` (named: `firecrawl/web-scrape-integration`)
  2. `web-search-integration` (named: `firecrawl/web-search-integration`)
  3. `browser-interaction-integration` (named: `firecrawl/browser-interaction-integration`)
  4. `agent-environment-auth` (named: `firecrawl/agent-environment-auth`)
  5. `api-call-orchestration` (named: `firecrawl/api-call-orchestration`)
  6. `academic-literature-retrieval` (named: `firecrawl/academic-literature-retrieval`)

---

## 2. Step 1: Promote Component Skills (Maintainer Only)

Once the intake batch is approved, run the following programmatic mutations to register the generic and named nodes.

### A. Register Generic Skills (Starless)
```bash
# Add generic nodes
gaia dev add "Web Scrape Integration" --id web-scrape-integration --type basic --description "Integrate programmatic web scraping APIs to convert dynamic page URLs into clean, LLM-ready markdown or structured JSON schemas in application code."
gaia dev add "Web Search Integration" --id web-search-integration --type basic --description "Integrate programmable search endpoints to discover relevant pages and extract content based on natural language queries inside product codebase."
gaia dev add "Browser Interaction Integration" --id browser-interaction-integration --type basic --description "Integrate headless browser control (clicks, form inputs, dynamic navigation) to scrape dynamic or authenticated web pages programmatically in product code."
gaia dev add "Agent Environment Authentication" --id agent-environment-auth --type basic --description "Programmatically handle API key retrieval, browser-based OAuth flow setup, and SDK initialization for AI agent tools."
gaia dev add "API Call Orchestration" --id api-call-orchestration --type basic --description "Orchestrate multiple web endpoints (such as search, scrape, and interact) via unified client wrappers, handling failures, token counting, and caching."
gaia dev add "Academic Literature Retrieval" --id academic-literature-retrieval --type basic --description "Retrieve, index, and query scientific literature papers (such as arXiv publications) alongside code repositories to support deep research loops."
```

### B. Register Named Skills (Status: Awakened)
```bash
# Add named implementation mappings
gaia dev add "Web Scrape Integration" --id firecrawl/web-scrape-integration --named --contributor firecrawl --generic-ref web-scrape-integration --status awakened
gaia dev add "Web Search Integration" --id firecrawl/web-search-integration --named --contributor firecrawl --generic-ref web-search-integration --status awakened
gaia dev add "Browser Interaction Integration" --id firecrawl/browser-interaction-integration --named --contributor firecrawl --generic-ref browser-interaction-integration --status awakened
gaia dev add "Agent Environment Authentication" --id firecrawl/agent-environment-auth --named --contributor firecrawl --generic-ref agent-environment-auth --status awakened
gaia dev add "API Call Orchestration" --id firecrawl/api-call-orchestration --named --contributor firecrawl --generic-ref api-call-orchestration --status awakened
gaia dev add "Academic Literature Retrieval" --id firecrawl/academic-literature-retrieval --named --contributor firecrawl --generic-ref academic-literature-retrieval --status awakened
```

### C. Populate Evidence
```bash
# Web Scrape Integration evidence
gaia dev evidence firecrawl/web-scrape-integration "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-build-scrape/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/web-scrape-integration "https://github.com/firecrawl/firecrawl" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/web-scrape-integration "https://spider.cloud/blog/firecrawl-vs-crawl4ai-vs-spider-honest-benchmark/" --class A --type benchmark-result --evaluator gaia-research
gaia dev evidence firecrawl/web-scrape-integration "https://www.youtube.com/watch?v=kY0hN5-xK8U" --class C --type social-signal --evaluator gaia-research

# Web Search Integration evidence
gaia dev evidence firecrawl/web-search-integration "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-build-search/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/web-search-integration "https://github.com/firecrawl/firecrawl" --class B --type repo --evaluator gaia-research

# Browser Interaction Integration evidence
gaia dev evidence firecrawl/browser-interaction-integration "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-build-interact/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/browser-interaction-integration "https://github.com/firecrawl/firecrawl" --class B --type repo --evaluator gaia-research

# Agent Environment Authentication evidence
gaia dev evidence firecrawl/agent-environment-auth "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-build-onboarding/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/agent-environment-auth "https://github.com/firecrawl/skills" --class B --type repo --evaluator gaia-research

# API Call Orchestration evidence
gaia dev evidence firecrawl/api-call-orchestration "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-build/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/api-call-orchestration "https://github.com/firecrawl/skills" --class B --type repo --evaluator gaia-research

# Academic Literature Retrieval evidence
gaia dev evidence firecrawl/academic-literature-retrieval "https://github.com/firecrawl/skills/blob/main/skills/firecrawl-research-index/SKILL.md" --class B --type repo --evaluator gaia-research
gaia dev evidence firecrawl/academic-literature-retrieval "https://www.firecrawl.dev/blog/research-index-launch" --class A --type benchmark-result --evaluator gaia-research
gaia dev evidence firecrawl/academic-literature-retrieval "https://arxiv.org/abs/2508.10152" --class A --type arxiv --evaluator gaia-research
```

---

## 3. Step 2: Promote Named Skills & Calibrate
Promote all 6 awakened named skills to standard standard tier mapping (4★) once verified:
```bash
gaia dev update-named firecrawl/web-scrape-integration --status named
gaia dev calibrate firecrawl/web-scrape-integration "4★"

gaia dev update-named firecrawl/web-search-integration --status named
gaia dev calibrate firecrawl/web-search-integration "4★"

gaia dev update-named firecrawl/browser-interaction-integration --status named
gaia dev calibrate firecrawl/browser-interaction-integration "4★"

gaia dev update-named firecrawl/agent-environment-auth --status named
gaia dev calibrate firecrawl/agent-environment-auth "4★"

gaia dev update-named firecrawl/api-call-orchestration --status named
gaia dev calibrate firecrawl/api-call-orchestration "4★"

gaia dev update-named firecrawl/academic-literature-retrieval --status named
gaia dev calibrate firecrawl/academic-literature-retrieval "4★"
```

---

## 4. Step 3: Programmatic Fusion into Suite (`/gaia-fuse-full-suite`)

Once the individual component skills have been registered and named, create the generic ultimate node and fuse the components under `firecrawl/firecrawl-skills`.

### Run `gaia dev fuse` Command:
```bash
gaia dev fuse firecrawl-skills --name "Firecrawl Skills Suite" --type ultimate \
  --prereqs web-scrape-integration,web-search-integration,browser-interaction-integration,agent-environment-auth,api-call-orchestration,academic-literature-retrieval \
  --named-capstone firecrawl/firecrawl-skills \
  --suite-components firecrawl/web-scrape-integration,firecrawl/web-search-integration,firecrawl/browser-interaction-integration,firecrawl/agent-environment-auth,firecrawl/api-call-orchestration,firecrawl/academic-literature-retrieval
```

This creates:
- Generic Ultimate Skill: `firecrawl-skills`
- Named Capstone Suite: `firecrawl/firecrawl-skills` (promoted to 5★ based on Class A benchmark evidence and 149k star repo)
- Component links recorded in `registry/suites/firecrawl/firecrawl-skills.json`
- Back-linked derivatives on all 6 basic components pointing to the ultimate

---

## 5. Step 4: Bootstrap Upstream Version Tracking

To track the `firecrawl/skills` repository versioning, open a bootstrap issue to register `v1.19.24` as the initial baseline.

### Proposed Bootstrap Issue
- **Title:** `[upstream:bootstrap] firecrawl/firecrawl-skills — baseline at current upstream version v1.19.24`
- **Labels:** `upstream:bootstrap`, `needs-triage`
- **Body:**
  ```markdown
  We've never tracked this suite. Approve to baseline at current upstream version `v1.19.24`.
  No component diff proposed.

  **Actions:**
  Applying `upstream:approved` label will trigger the sync workflow:
  ```bash
  gaia dev sync-upstream firecrawl/firecrawl-skills --tag v1.19.24 --source-url https://github.com/firecrawl/skills/releases/tag/v1.19.24 --bootstrap
  ```
  This registers:
  - Repo: `firecrawl/skills`
  - Version: `v1.19.24`
  - Source URL: `https://github.com/firecrawl/skills/releases/tag/v1.19.24`
  ```
