"""Add reviewed Hermes Agent skills to the Gaia registry."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

REGISTRY_PATH = Path("registry/gaia.json")
TODAY = "2026-05-06"
EVALUATOR = "openai-codex"
VERSION = "0.1.0"

NEW_SKILLS = [
    {
        "id": "feed-monitoring",
        "name": "Feed Monitoring",
        "type": "basic",
        "level": "4★",
        "description": "Monitors RSS, Atom, blog, or other recurring content feeds, discovers updates, tracks read state, and surfaces new signals for downstream agent workflows.",
        "prerequisites": [],
        "derivatives": [],
        "conditions": "Requires configured feed sources and a repeatable polling or discovery mechanism.",
        "evidence": [
            {
                "class": "B",
                "source": "https://github.com/NousResearch/hermes-agent/blob/main/skills/research/blogwatcher/SKILL.md",
                "evaluator": EVALUATOR,
                "date": TODAY,
                "notes": "Hermes Agent blogwatcher skill monitors blogs and RSS/Atom feeds with feed discovery, scraping fallback, OPML import, and read/unread article management.",
            }
        ],
        "knownAgents": ["NousResearch/hermes-agent"],
        "status": "provisional",
        "createdAt": TODAY,
        "updatedAt": TODAY,
        "version": VERSION,
    },
    {
        "id": "wiki-search",
        "name": "Wiki Search",
        "type": "extra",
        "level": "4★",
        "description": "Builds, maintains, and queries an interlinked markdown or wiki-style knowledge base so an agent can retrieve durable local context across research sessions.",
        "prerequisites": ["retrieve", "embed-text", "summarize"],
        "derivatives": [],
        "conditions": "Requires an accessible local wiki or markdown knowledge-base directory and a consistent linking or indexing convention.",
        "evidence": [
            {
                "class": "B",
                "source": "https://github.com/NousResearch/hermes-agent/blob/main/skills/research/llm-wiki/SKILL.md",
                "evaluator": EVALUATOR,
                "date": TODAY,
                "notes": "Hermes Agent llm-wiki skill documents a persistent interlinked markdown knowledge base pattern for compounding research notes and retrieval.",
            }
        ],
        "knownAgents": ["NousResearch/hermes-agent"],
        "status": "provisional",
        "createdAt": TODAY,
        "updatedAt": TODAY,
        "version": VERSION,
    },
    {
        "id": "prediction-market-analysis",
        "name": "Prediction Market Analysis",
        "type": "extra",
        "level": "4★",
        "description": "Queries prediction-market data, compares market probabilities and price history, and summarizes probabilistic signals for forecasting or decision-support workflows.",
        "prerequisites": ["data-analysis", "web-search", "statistical-analysis"],
        "derivatives": [],
        "conditions": "Requires read-only market data sources and clear separation between analysis output and financial advice or trade execution.",
        "evidence": [
            {
                "class": "B",
                "source": "https://github.com/NousResearch/hermes-agent/blob/main/skills/research/polymarket/SKILL.md",
                "evaluator": EVALUATOR,
                "date": TODAY,
                "notes": "Hermes Agent polymarket skill queries markets, prices, order books, and historical prediction-market data through public read-only APIs.",
            }
        ],
        "knownAgents": ["NousResearch/hermes-agent"],
        "status": "provisional",
        "createdAt": TODAY,
        "updatedAt": TODAY,
        "version": VERSION,
    },
    {
        "id": "humanize-prose",
        "name": "Humanize Prose",
        "type": "extra",
        "level": "4★",
        "description": "Audits and rewrites prose to remove generic AI-writing patterns, preserve author intent, and adapt tone toward a more natural human voice.",
        "prerequisites": ["document-editing", "audience-model", "format-output"],
        "derivatives": [],
        "conditions": "Requires explicit user permission to revise voice, tone, and stylistic markers without changing factual claims.",
        "evidence": [
            {
                "class": "B",
                "source": "https://github.com/NousResearch/hermes-agent/blob/main/skills/creative/humanizer/SKILL.md",
                "evaluator": EVALUATOR,
                "date": TODAY,
                "notes": "Hermes Agent humanizer skill identifies AI-generated writing patterns and rewrites text to sound more natural while retaining meaning.",
            }
        ],
        "knownAgents": ["NousResearch/hermes-agent"],
        "status": "provisional",
        "createdAt": TODAY,
        "updatedAt": TODAY,
        "version": VERSION,
    },
    {
        "id": "architecture-diagram",
        "name": "Architecture Diagram",
        "type": "extra",
        "level": "4★",
        "description": "Generates technical architecture, infrastructure, or cloud diagrams as structured visual artifacts from natural-language system descriptions.",
        "prerequisites": ["data-visualize", "format-output", "write-report"],
        "derivatives": [],
        "conditions": "Requires enough system context to identify components, relationships, boundaries, and rendering constraints.",
        "evidence": [
            {
                "class": "B",
                "source": "https://github.com/NousResearch/hermes-agent/blob/main/skills/creative/architecture-diagram/SKILL.md",
                "evaluator": EVALUATOR,
                "date": TODAY,
                "notes": "Hermes Agent architecture-diagram skill generates standalone HTML files with inline SVG architecture diagrams from system descriptions.",
            }
        ],
        "knownAgents": ["NousResearch/hermes-agent"],
        "status": "provisional",
        "createdAt": TODAY,
        "updatedAt": TODAY,
        "version": VERSION,
    },
]

NEW_EDGES = []
for skill in NEW_SKILLS:
    for prereq in skill["prerequisites"]:
        NEW_EDGES.append(
            {
                "sourceSkillId": prereq,
                "targetSkillId": skill["id"],
                "edgeType": "prerequisite",
                "condition": skill["conditions"],
                "levelFloor": "2★",
                "evidenceRefs": [f"{skill['id']}#evidence[0]"],
            }
        )
    for derivative in skill["derivatives"]:
        NEW_EDGES.append(
            {
                "sourceSkillId": skill["id"],
                "targetSkillId": derivative,
                "edgeType": "enhances",
                "condition": "",
                "levelFloor": skill["level"],
                "evidenceRefs": [f"{skill['id']}#evidence[0]"],
            }
        )


def main() -> None:
    with REGISTRY_PATH.open(encoding="utf-8") as fh:
        registry = json.load(fh)

    existing_ids = {skill["id"] for skill in registry["skills"]}
    duplicate_ids = existing_ids.intersection(skill["id"] for skill in NEW_SKILLS)
    if duplicate_ids:
        raise SystemExit(f"Refusing to add duplicate skills: {sorted(duplicate_ids)}")

    skill_by_id = {skill["id"]: skill for skill in registry["skills"]}
    for skill in NEW_SKILLS:
        registry["skills"].append(skill)
        for prereq in skill["prerequisites"]:
            parent = skill_by_id[prereq]
            if skill["id"] not in parent["derivatives"]:
                parent["derivatives"].append(skill["id"])
                parent["updatedAt"] = TODAY
        skill_by_id[skill["id"]] = skill

    existing_edges = {
        (edge["sourceSkillId"], edge["targetSkillId"], edge["edgeType"])
        for edge in registry.get("edges", [])
    }
    for edge in NEW_EDGES:
        key = (edge["sourceSkillId"], edge["targetSkillId"], edge["edgeType"])
        if key not in existing_edges:
            registry.setdefault("edges", []).append(edge)
            existing_edges.add(key)

    registry["generatedAt"] = f"{TODAY}T00:00:00Z"

    with REGISTRY_PATH.open("w", encoding="utf-8") as fh:
        json.dump(registry, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
