"""Crawls SkillsMP.com for skill definitions (Class C evidence)."""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from common.taxonomy_mapper import KEYWORD_TO_SKILL, map_to_skills
from common.evidence_scorer import compute_skillsmp_score
from common.candidate_builder import build_candidate, normalize_id
from common.dedup import deduplicate
from common.proposer import write_proposals

BASE_URL = "https://skillsmp.com/api/v1"
DAILY_BUDGET = 50
RESERVE_REQUESTS = 10
SCORE_THRESHOLD = 30
REQUEST_TIMEOUT = 15


class BudgetExhausted(Exception):
    pass


class SkillsMPClient:
    """Rate-limit-aware client for SkillsMP API."""

    def __init__(self):
        self.requests_made = 0
        self.max_requests = DAILY_BUDGET - RESERVE_REQUESTS

    def search(self, query: str) -> list[dict]:
        if self.requests_made >= self.max_requests:
            raise BudgetExhausted(f"Budget exhausted ({self.requests_made}/{DAILY_BUDGET})")

        url = f"{BASE_URL}/skills/search"
        try:
            resp = requests.get(url, params={"q": query}, timeout=REQUEST_TIMEOUT)
            self.requests_made += 1

            remaining = resp.headers.get("X-RateLimit-Daily-Remaining")
            if remaining:
                print(f"    API budget remaining: {remaining}")

            if resp.status_code == 429:
                print("    Rate limited by SkillsMP — stopping.")
                raise BudgetExhausted("429 received")

            if resp.status_code != 200:
                print(f"    HTTP {resp.status_code} for query '{query}'")
                return []

            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("skills", data.get("results", []))

        except requests.RequestException as e:
            print(f"    Request failed: {e}")
            self.requests_made += 1
            return []


def extract_skill_info(result: dict) -> dict | None:
    """Extract relevant fields from a SkillsMP search result."""
    name = result.get("name") or result.get("title", "")
    if not name:
        return None

    return {
        "name": name,
        "description": result.get("description", "")[:200],
        "stars": result.get("stars", result.get("starCount", 0)),
        "categories": result.get("categories", []),
        "url": result.get("url", result.get("link", "")),
        "has_content": bool(result.get("content") or result.get("skillMd")),
    }


def main():
    """Main crawler entry point."""
    print("SkillsMP Crawler — searching for AI agent skill definitions")
    print(f"  Budget: {DAILY_BUDGET - RESERVE_REQUESTS} requests (reserving {RESERVE_REQUESTS})")
    print(f"  Score threshold: {SCORE_THRESHOLD}")
    print()

    client = SkillsMPClient()
    all_candidates = []

    # Use top keywords from taxonomy mapper as search queries
    keywords = list(KEYWORD_TO_SKILL.keys())[:40]

    for keyword in keywords:
        print(f"  Searching: '{keyword}'")
        try:
            results = client.search(keyword)
        except BudgetExhausted as e:
            print(f"  {e}")
            break

        for result in results:
            info = extract_skill_info(result)
            if not info:
                continue

            score = compute_skillsmp_score(
                stars=info["stars"],
                category_count=len(info["categories"]),
                has_content=info["has_content"],
            )

            if score < SCORE_THRESHOLD:
                continue

            skill_ids = map_to_skills(
                info["name"],
                info["description"],
                keywords=info["categories"],
            )

            skill_id = skill_ids[0] if skill_ids else normalize_id(info["name"])

            source_url = info["url"] or f"https://skillsmp.com/skills/{normalize_id(info['name'])}"

            candidate = build_candidate(
                id=normalize_id(f"{skill_id}-smp-{info['name'][:20]}"),
                name=info["name"],
                description=info["description"] or f"SkillsMP skill: {info['name']}",
                skill_type="basic",
                source_url=source_url,
                source_type="skillsmp",
                evidence_class="C",
                score=score,
            )
            all_candidates.append(candidate)

        time.sleep(1)

    print(f"\n  Requests used: {client.requests_made}/{DAILY_BUDGET}")
    print(f"  Raw candidates: {len(all_candidates)}")

    # Deduplicate within batch
    seen_ids = set()
    unique_candidates = []
    for c in all_candidates:
        if c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            unique_candidates.append(c)

    # Deduplicate against graph
    final = deduplicate(unique_candidates)
    print(f"  After dedup: {len(final)}")

    if final:
        output = write_proposals(final, "skillsmp")
        print(f"\n  Output: {output}")
    else:
        print("\n  No new candidates to propose.")


if __name__ == "__main__":
    main()
