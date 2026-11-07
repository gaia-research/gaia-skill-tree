"""Crawls npm registry for AI/agent-related packages."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from common.taxonomy_mapper import map_to_skills
from common.evidence_scorer import compute_score
from common.candidate_builder import build_candidate, normalize_id
from common.dedup import deduplicate
from common.proposer import write_proposals

SEARCH_KEYWORDS = [
    "mcp-server",
    "ai-agent-tool",
    "langchain-tool",
    "llm-tool",
    "rag",
    "embedding",
]

NPM_SEARCH_URL = "https://registry.npmjs.org/-/v1/search"


def search_npm(keyword: str, size: int = 30) -> list[dict]:
    """Search npm for packages matching a keyword."""
    candidates = []
    try:
        res = requests.get(
            NPM_SEARCH_URL,
            params={"text": keyword, "size": size, "quality": 0.5, "popularity": 0.5},
            timeout=30,
        )
        if res.status_code != 200:
            print(f"npm search for '{keyword}' returned {res.status_code}")
            return []

        data = res.json()
        packages = data.get("objects", [])

        for pkg in packages:
            info = pkg.get("package", {})
            name = info.get("name", "")
            description = info.get("description", "")
            keywords = info.get("keywords", [])
            updated = info.get("date", "")
            url = f"https://www.npmjs.com/package/{name}"

            # Get download count from npm API
            downloads = 0
            try:
                dl_res = requests.get(
                    f"https://api.npmjs.org/downloads/point/last-week/{name}",
                    timeout=10,
                )
                if dl_res.status_code == 200:
                    downloads = dl_res.json().get("downloads", 0)
            except Exception:
                pass

            if downloads < 100:
                continue

            skills = map_to_skills(name, description, keywords)
            if not skills:
                skill_id = normalize_id(name)
                if not skill_id:
                    continue
                score_val = compute_score(downloads, 0, updated, has_readme=True)
                if score_val < 30:
                    continue
                candidates.append(build_candidate(
                    id=skill_id,
                    name=name,
                    description=description[:200] or f"npm package: {name}",
                    source_url=url,
                    source_type="npm",
                    score=score_val,
                ))
    except Exception as e:
        print(f"Error searching npm for '{keyword}': {e}")

    return candidates


def main():
    print("Crawling npm registry...")
    candidates = []
    for keyword in SEARCH_KEYWORDS:
        print(f"  Searching: {keyword}")
        candidates.extend(search_npm(keyword))

    seen_ids = set()
    unique = []
    for c in candidates:
        if c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            unique.append(c)
    candidates = unique

    print(f"Found {len(candidates)} raw candidates")

    candidates = deduplicate(candidates)
    print(f"After dedup: {len(candidates)} new candidates")

    if candidates:
        write_proposals(candidates, source_name="npm")


if __name__ == "__main__":
    main()
