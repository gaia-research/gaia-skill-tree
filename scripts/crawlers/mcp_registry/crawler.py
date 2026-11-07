"""Crawls MCP server registries (mcp.so, smithery.ai) for agent skills."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from common.taxonomy_mapper import map_to_skills
from common.evidence_scorer import compute_score
from common.candidate_builder import build_candidate, normalize_id
from common.dedup import deduplicate
from common.proposer import write_proposals


def crawl_mcp_so() -> list[dict]:
    """Crawl mcp.so for MCP servers."""
    candidates = []
    try:
        res = requests.get("https://mcp.so/api/servers", timeout=30)
        if res.status_code != 200:
            print(f"mcp.so returned {res.status_code}")
            return []

        servers = res.json()
        if isinstance(servers, dict):
            servers = servers.get("servers", servers.get("data", []))

        for server in servers[:50]:
            name = server.get("name", "")
            description = server.get("description", "")
            downloads = server.get("downloads", server.get("installs", 0))
            stars = server.get("stars", server.get("github_stars", 0))
            updated = server.get("updated_at", server.get("last_updated", ""))
            url = server.get("url", server.get("homepage", f"https://mcp.so/server/{name}"))

            skills = map_to_skills(name, description)
            if not skills:
                skill_id = normalize_id(name)
                if not skill_id:
                    continue
                score_val = compute_score(downloads, stars, updated, has_readme=bool(description))
                if score_val < 30:
                    continue
                candidates.append(build_candidate(
                    id=skill_id,
                    name=name,
                    description=description[:200] or f"MCP server: {name}",
                    source_url=url,
                    source_type="mcp-registry",
                    score=score_val,
                ))
    except Exception as e:
        print(f"Error crawling mcp.so: {e}")

    return candidates


def crawl_smithery() -> list[dict]:
    """Crawl smithery.ai for MCP servers."""
    candidates = []
    try:
        res = requests.get("https://registry.smithery.ai/servers", timeout=30)
        if res.status_code != 200:
            print(f"smithery.ai returned {res.status_code}")
            return []

        data = res.json()
        servers = data if isinstance(data, list) else data.get("servers", data.get("items", []))

        for server in servers[:50]:
            name = server.get("name", server.get("title", ""))
            description = server.get("description", "")
            downloads = server.get("downloads", server.get("usage_count", 0))
            stars = server.get("stars", 0)
            updated = server.get("updated_at", "")
            url = server.get("url", server.get("homepage", f"https://smithery.ai/server/{name}"))

            skills = map_to_skills(name, description)
            if not skills:
                skill_id = normalize_id(name)
                if not skill_id:
                    continue
                score_val = compute_score(downloads, stars, updated, has_readme=bool(description))
                if score_val < 30:
                    continue
                candidates.append(build_candidate(
                    id=skill_id,
                    name=name,
                    description=description[:200] or f"MCP server: {name}",
                    source_url=url,
                    source_type="mcp-registry",
                    score=score_val,
                ))
    except Exception as e:
        print(f"Error crawling smithery.ai: {e}")

    return candidates


def main():
    print("Crawling MCP registries...")
    candidates = crawl_mcp_so() + crawl_smithery()
    print(f"Found {len(candidates)} raw candidates")

    candidates = deduplicate(candidates)
    print(f"After dedup: {len(candidates)} new candidates")

    if candidates:
        write_proposals(candidates, source_name="mcp-registry")


if __name__ == "__main__":
    main()
