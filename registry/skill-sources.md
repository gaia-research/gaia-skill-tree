# Gaia Skill Sources

Authoritative list of known skill sources and marketplaces. `gaia-curate` agents read this file at the start of every curation run and append new sources as they are discovered.

**Format:** one row per source. Columns: Name | URL | Type | Search method | Notes

---

## Registries & Marketplaces

| Name | URL | Type | Search |
|---|---|---|---|
| SkillsMP | https://skillsmp.com | marketplace | `GET /api/v1/skills/search?q=<skill>` — 50 req/day unauthenticated |
| SkillKit | https://skillkit.io | marketplace | browse directory pages for SKILL.md packages and source links |
| GLINCKER Claude Marketplace | https://github.com/GLINCKER/claude-code-marketplace | github-repo | `gh api repos/GLINCKER/claude-code-marketplace/contents/skills` |
| MCP.so Registry | https://mcp.so | mcp-registry | `WebFetch /servers` — list all MCP servers as skill evidence candidates |
| Smithery MCP Registry | https://smithery.ai | mcp-registry | `WebFetch /` — browse MCP tool listings |
| Official MCP Registry | https://registry.modelcontextprotocol.io | mcp-registry | `WebFetch /` — search and discover official/community MCP servers |
| MCP Directory | https://mcp.directory | marketplace | browse and discover MCP servers and agent skills |
| Glama MCP Registry | https://glama.ai/mcp/servers | mcp-registry | browse Model Context Protocol servers, tools, and integrations |
| MCP Market | https://mcpmarket.com | marketplace | browse database of MCP servers and tool integrations |
| AI Agents Directory | https://aiagentsdirectory.com | marketplace | discover and compare top AI agents, frameworks, and skills |

## GitHub Orgs / Repos with Skill Collections

| Name | URL | Type | Search |
|---|---|---|---|
| anthropics/skills | https://github.com/anthropics/skills | github-repo | `gh api repos/anthropics/skills/contents/skills` |
| mattpocock/skills | https://github.com/mattpocock/skills | github-repo | `gh api repos/mattpocock/skills/contents/skills` |
| addyosmani/agent-skills | https://github.com/addyosmani/agent-skills | github-repo | `gh api repos/addyosmani/agent-skills/contents/skills` |
| intelligentcode-ai/skills | https://github.com/intelligentcode-ai/skills | github-repo | `gh api repos/intelligentcode-ai/skills/contents/skills` |
| ruvnet/ruflo | https://github.com/ruvnet/ruflo | github-repo | orchestration platform; check `/skills` and `/.claude/skills` |
| karpathy/autoresearch | https://github.com/karpathy/autoresearch | github-repo | origin implementation of autonomous-research-agent |
| spring-ai-alibaba/examples | https://github.com/spring-ai-alibaba/examples | github-repo | `gh api repos/spring-ai-alibaba/examples/contents/.claude/skills` |
| balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill | https://github.com/balukosuri/Andrej-Karpathy-s-Autoresearch-As-a-Universal-Skill | github-repo | community reproduction of autoresearch as a general agent skill |
| NousResearch/hermes-agent | https://github.com/NousResearch/hermes-agent | github-repo | `gh api repos/NousResearch/hermes-agent/contents/skills` and `gh api repos/NousResearch/hermes-agent/contents/optional-skills` |
| obra/superpowers | https://github.com/obra/superpowers | github-repo | `gh api repos/obra/superpowers/contents/skills` |
| google-deepmind/science-skills | https://github.com/google-deepmind/science-skills | github-repo | `gh api repos/google-deepmind/science-skills/contents/skills` |
| sickn33/antigravity-awesome-skills | https://github.com/sickn33/antigravity-awesome-skills | github-repo | `gh api repos/sickn33/antigravity-awesome-skills/contents/skills` |

## Academic / Evidence Sources

| Name | URL | Type | Search |
|---|---|---|---|
| arXiv (cs.AI / cs.CL) | https://arxiv.org | paper-index | `WebSearch "<skill> arxiv 2024 2025 2026 agent benchmark"` — Class A evidence |
| Papers With Code | https://paperswithcode.com | paper-index | `WebSearch "<skill> site:paperswithcode.com"` — benchmarks + code links |

## Package / Extension Registries

| Name | URL | Type | Search |
|---|---|---|---|
| npm | https://www.npmjs.com | package-registry | crawled by `scripts/crawlers/crawl_npm.py`; topics: `ai-agent`, `llm-tool` |
| VS Code Marketplace | https://marketplace.visualstudio.com | extension-registry | crawled by `scripts/crawlers/crawl_vscode.py`; tag: `ai-agent` |
| HuggingFace | https://huggingface.co | model-hub | crawled by `scripts/crawlers/crawl_huggingface.py`; spaces tagged `agent` |

## GitHub Topic Searches (ad-hoc)

Run these during every curation pass to surface new repos:

```bash
gh search repos --topic="ai-agent-skills" --sort=stars --limit=20
gh search repos --topic="claude-skills" --sort=stars --limit=20
gh search repos --topic="llm-agent" --sort=stars --limit=20
gh search repos "<skill-name> agent" --sort=stars --limit=10
```

---

## How to add a new source

When `gaia-curate` discovers a new marketplace, registry, or skill collection repo not already listed:

1. Add a row to the appropriate table above.
2. Include the URL, type, and a one-line search instruction.
3. Commit the change in the same PR as the skill additions that led to its discovery.

_Never remove a source; mark it stale with a `<!-- stale: <reason> -->` comment if it goes offline._
