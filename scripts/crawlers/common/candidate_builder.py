"""Builds valid Gaia skill node candidates from crawler output."""

from datetime import datetime


def build_candidate(
    id: str,
    name: str,
    description: str,
    skill_type: str = "basic",
    source_url: str = "",
    source_type: str = "manual",
    evaluator: str = "gaiabot",
    evidence_class: str = "C",
    score: int = 0,
) -> dict:
    """Build a skill candidate matching registry/schema/skill.schema.json."""
    return {
        "id": id,
        "name": name,
        "type": skill_type,
        "description": description,
        "prerequisites": [],
        "derivatives": [],
        "conditions": "",
        "evidence": [
            {
                "class": evidence_class,
                "source": source_url,
                "evaluator": evaluator,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "notes": f"Auto-discovered from {source_type}. Evidence score: {score}/100.",
                "source_type": source_type,
            }
        ],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": datetime.now().strftime("%Y-%m-%d"),
        "updatedAt": datetime.now().strftime("%Y-%m-%d"),
        "version": "0.1.0",
    }


def normalize_id(name: str) -> str:
    """Convert a display name to a kebab-case skill ID."""
    import re
    cleaned = re.sub(r"[^a-z0-9\s-]", "", name.lower())
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned[:64]


def build_evidence_upgrade(
    skill_id: str,
    evidence_class: str,
    source_url: str,
    source_type: str = "manual",
    evaluator: str = "gaiabot",
    score: int = 0,
    notes: str = "",
) -> dict:
    """Build an evidence upgrade proposal for an existing skill.

    Unlike build_candidate, this does not create a new skill node —
    it proposes adding evidence to an existing skill in the graph.
    """
    return {
        "skill_id": skill_id,
        "action": "add_evidence",
        "evidence": {
            "class": evidence_class,
            "source": source_url,
            "evaluator": evaluator,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "notes": notes or f"Auto-discovered from {source_type}. Evidence score: {score}/100.",
        },
    }
