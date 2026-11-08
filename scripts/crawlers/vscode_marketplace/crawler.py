"""Crawls VS Code Marketplace for AI/agent extensions."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from common.taxonomy_mapper import map_to_skills
from common.evidence_scorer import compute_score
from common.candidate_builder import build_candidate, normalize_id
from common.dedup import deduplicate
from common.proposer import write_proposals

MARKETPLACE_API = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"

SEARCH_FILTERS = [
    {"criteria": [{"filterType": 10, "value": "ai"}, {"filterType": 12, "value": "4096"}]},
    {"criteria": [{"filterType": 10, "value": "mcp"}, {"filterType": 12, "value": "4096"}]},
    {"criteria": [{"filterType": 10, "value": "agent"}, {"filterType": 12, "value": "4096"}]},
]


def crawl_marketplace(search_filter: dict, batch_size: int = 20) -> list[dict]:
    """Query VS Code Marketplace for extensions."""
    candidates = []
    try:
        payload = {
            "filters": [search_filter],
            "assetTypes": [],
            "flags": 914,
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json;api-version=6.1-preview.1",
        }
        res = requests.post(MARKETPLACE_API, json=payload, headers=headers, timeout=30)
        if res.status_code != 200:
            print(f"VS Code Marketplace returned {res.status_code}")
            return []

        data = res.json()
        results = data.get("results", [{}])
        extensions = results[0].get("extensions", []) if results else []

        for ext in extensions[:batch_size]:
            name = ext.get("displayName", ext.get("extensionName", ""))
            description = ext.get("shortDescription", "")
            publisher = ext.get("publisher", {}).get("displayName", "")

            stats = {s["statisticName"]: s["value"] for s in ext.get("statistics", [])}
            installs = int(stats.get("install", 0))

            if installs < 1000:
                continue

            updated = ext.get("lastUpdated", "")
            ext_id = ext.get("extensionId", "")
            url = f"https://marketplace.visualstudio.com/items?itemName={publisher}.{ext.get('extensionName', '')}"

            skills = map_to_skills(name, description)
            if not skills:
                skill_id = normalize_id(name)
                if not skill_id:
                    continue
                score_val = compute_score(installs, 0, updated, has_readme=True)
                if score_val < 30:
                    continue
                candidates.append(build_candidate(
                    id=skill_id,
                    name=name,
                    description=description[:200] or f"VS Code extension: {name}",
                    source_url=url,
                    source_type="vscode-marketplace",
                    score=score_val,
                ))
    except Exception as e:
        print(f"Error crawling VS Code Marketplace: {e}")

    return candidates


def main():
    print("Crawling VS Code Marketplace...")
    candidates = []
    for search_filter in SEARCH_FILTERS:
        candidates.extend(crawl_marketplace(search_filter))

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
        write_proposals(candidates, source_name="vscode")


if __name__ == "__main__":
    main()
