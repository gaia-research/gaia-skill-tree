"""Lightweight papers crawler — finds Class A evidence for existing skills.

This crawler does NOT propose new skills. It searches for academic papers
that can upgrade evidence on existing skills in the graph (the '20% effort'
paper-hunting workflow).
"""

import json
import os
import sys
import time
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests

from common.candidate_builder import build_evidence_upgrade
from common.proposer import write_evidence_upgrades

MIN_CITATIONS = 10
MAX_AGE_YEARS = 3
BATCH_SIZE = 25
CURRENT_YEAR = 2026
REQUEST_TIMEOUT = 15


def load_upgrade_candidates(graph_path: str = None) -> list[dict]:
    """Find skills in the graph that could benefit from better evidence.

    Targets:
      - Skills at 2★+ with only Class C evidence (need B/A)
      - Skills at 0★★/1★ with no evidence at all
      - Skills with status "provisional"
    """
    if graph_path is None:
        graph_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "graph", "gaia.json"
        )

    graph_path = os.path.abspath(graph_path)
    if not os.path.exists(graph_path):
        print(f"  Graph not found: {graph_path}")
        return []

    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    candidates = []
    for skill in graph.get("skills", []):
        evidence = skill.get("evidence", [])
        evidence_classes = {e.get("class") for e in evidence}
        level = skill.get("level", "0★")
        status = skill.get("status", "")

        is_upgrade_candidate = False

        # No evidence at all
        if not evidence:
            is_upgrade_candidate = True

        # Only Class C evidence but at a level that needs B/A
        elif evidence_classes == {"C"} and level in ("2★", "3★", "4★", "5★", "6★"):
            is_upgrade_candidate = True

        # Provisional status (could be validated with better evidence)
        elif status == "provisional":
            is_upgrade_candidate = True

        # Has no Class A evidence (paper search could add one)
        elif "A" not in evidence_classes and level in ("3★", "4★", "5★", "6★"):
            is_upgrade_candidate = True

        if is_upgrade_candidate:
            candidates.append({
                "id": skill["id"],
                "name": skill.get("name", skill["id"]),
                "description": skill.get("description", ""),
                "level": level,
                "current_evidence": [e.get("class") for e in evidence],
            })

    return candidates[:BATCH_SIZE]


def search_semantic_scholar(query: str, limit: int = 5) -> list[dict]:
    """Search Semantic Scholar for papers matching the query."""
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "fields": "title,year,citationCount,url,openAccessPdf",
        "limit": limit,
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 429:
            print("    Semantic Scholar rate limited — backing off")
            time.sleep(10)
            return []
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("data", [])
    except requests.RequestException:
        return []


def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv API as fallback for paper discovery."""
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers = []

        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns)
            published = entry.find("atom:published", ns)
            arxiv_id = entry.find("atom:id", ns)

            if title is None or arxiv_id is None:
                continue

            year = None
            if published is not None and published.text:
                year = int(published.text[:4])

            papers.append({
                "title": title.text.strip().replace("\n", " "),
                "year": year,
                "citationCount": 0,
                "url": arxiv_id.text.strip(),
            })

        return papers
    except (requests.RequestException, ET.ParseError):
        return []


def score_paper(paper: dict) -> int:
    """Score a paper for relevance and quality."""
    score = 0
    citations = paper.get("citationCount", 0)
    year = paper.get("year")

    if citations >= 100:
        score += 40
    elif citations >= 50:
        score += 30
    elif citations >= 20:
        score += 20
    elif citations >= MIN_CITATIONS:
        score += 10

    if year and year >= CURRENT_YEAR - 1:
        score += 30
    elif year and year >= CURRENT_YEAR - 2:
        score += 20
    elif year and year >= CURRENT_YEAR - MAX_AGE_YEARS:
        score += 10

    if paper.get("openAccessPdf"):
        score += 10

    return score


def build_search_query(skill: dict) -> str:
    """Build an effective search query from a skill's metadata."""
    name = skill["name"].replace("-", " ")
    description = skill.get("description", "")

    # Take key terms from description (first 5 words)
    desc_terms = " ".join(description.split()[:5]) if description else ""
    return f"{name} AI agent {desc_terms}".strip()


def main():
    """Main crawler entry point."""
    print("Papers Crawler — finding Class A evidence for existing skills")
    print(f"  Min citations: {MIN_CITATIONS}, Max age: {MAX_AGE_YEARS} years")
    print(f"  Batch size: {BATCH_SIZE}")
    print()

    candidates = load_upgrade_candidates()
    print(f"  Found {len(candidates)} upgrade candidates in the graph")

    if not candidates:
        print("  No upgrade candidates found.")
        return

    upgrades = []

    for skill in candidates:
        query = build_search_query(skill)
        print(f"  Searching for: {skill['id']} (query: '{query[:50]}...')")

        # Try Semantic Scholar first
        papers = search_semantic_scholar(query)
        source = "semantic_scholar"

        # Fallback to arXiv
        if not papers:
            papers = search_arxiv(query)
            source = "arxiv"

        best_paper = None
        best_score = 0

        for paper in papers:
            paper_score = score_paper(paper)
            year = paper.get("year")

            # Filter: must meet minimum criteria
            if paper.get("citationCount", 0) < MIN_CITATIONS and source == "semantic_scholar":
                continue
            if year and year < CURRENT_YEAR - MAX_AGE_YEARS:
                continue

            if paper_score > best_score:
                best_score = paper_score
                best_paper = paper

        if best_paper and best_score >= 20:
            paper_url = best_paper.get("url", "")
            # Normalize arXiv URLs to abs format
            _parsed_url = urlparse(paper_url)
            if _parsed_url.netloc in ("arxiv.org", "www.arxiv.org") and "/abs/" not in paper_url:
                arxiv_id = paper_url.rstrip("/").split("/")[-1]
                paper_url = f"https://arxiv.org/abs/{arxiv_id}"

            upgrade = build_evidence_upgrade(
                skill_id=skill["id"],
                evidence_class="A",
                source_url=paper_url,
                source_type=source,
                score=best_score,
                notes=f"{best_paper.get('title', '')} ({best_paper.get('year', 'n/a')}, {best_paper.get('citationCount', 0)} citations)",
            )
            upgrades.append(upgrade)
            print(f"    Found: {best_paper.get('title', '')[:60]}...")

        time.sleep(3)

    print(f"\n  Evidence upgrades found: {len(upgrades)}")

    if upgrades:
        output = write_evidence_upgrades(upgrades, "papers")
        print(f"  Output: {output}")
    else:
        print("  No papers met the quality threshold.")


if __name__ == "__main__":
    main()
