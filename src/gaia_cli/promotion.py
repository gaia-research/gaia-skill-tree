"""Skill-tree level promotion logic.

Provides helpers to check promotion eligibility, advance a skill's level,
and inspect the current promotion state for a given skill.
"""

import json
import os
from datetime import date, datetime, timezone

from .treeManager import load_tree, save_tree
from .registry import promotion_candidates_path, registry_graph_path
from .leveling import level_index, effective_level


def _load_meta():
    """Load registry/schema/meta.json from repo root or bundled fallback."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for p in candidates:
        resolved = os.path.normpath(p)
        if os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Cannot find registry/schema/meta.json")


_META = _load_meta()
LEVEL_ORDER = _META["levels"]["order"]
LEVEL_NAMES = _META["levels"]["labels"]
EVIDENCE_FLOOR = {k: set(v) if v else None for k, v in _META["levels"]["evidenceFloors"].items()}


def next_level(current: str) -> str | None:
    """Return the next level string, or None if already at max."""
    try:
        idx = LEVEL_ORDER.index(current)
    except ValueError:
        return None
    if idx >= len(LEVEL_ORDER) - 1:
        return None
    return LEVEL_ORDER[idx + 1]


def _get_skill_from_graph(graph_data: dict, skill_id: str) -> dict | None:
    """Look up a skill node by ID in the graph data."""
    for skill in graph_data.get("skills", []):
        if skill["id"] == skill_id:
            return skill
    return None


def _get_skill_from_tree(tree_data: dict, skill_id: str) -> dict | None:
    """Look up a skill entry by ID in the user's tree."""
    for entry in tree_data.get("unlockedSkills", []):
        if entry["skillId"] == skill_id:
            return entry
    return None


def _meets_evidence_floor(graph_skill: dict, target_level: str) -> bool:
    """Check whether the graph skill has evidence meeting the floor for target_level."""
    required_classes = EVIDENCE_FLOOR.get(target_level)
    if required_classes is None:
        return True
    evidence_list = graph_skill.get("evidence", [])
    for ev in evidence_list:
        if ev.get("class") in required_classes:
            return True
    return False


def check_promotion_eligibility(graph_data: dict, tree_data: dict) -> list[dict]:
    """Return a list of skills eligible for promotion.

    Each entry is a dict with keys:
        - skillId: the skill identifier
        - currentLevel: the level in the user's tree
        - nextLevel: the level it would be promoted to
        - name: display name from the graph
    """
    eligible = []
    for entry in tree_data.get("unlockedSkills", []):
        skill_id = entry["skillId"]
        current = entry["level"]
        target = next_level(current)
        if target is None:
            continue
        graph_skill = _get_skill_from_graph(graph_data, skill_id)
        if graph_skill is None:
            continue
        # Demerits define an explicit progression ceiling for this skill.
        if graph_skill.get("demerits") and level_index(target) > level_index(effective_level(graph_skill)):
            continue
        if _meets_evidence_floor(graph_skill, target):
            eligible.append({
                "skillId": skill_id,
                "currentLevel": current,
                "nextLevel": target,
                "suggestedLevel": target,
                "name": graph_skill.get("name", skill_id),
                "evidence": graph_skill.get("evidence", []),
            })
    return eligible


def top_named_level(named_buckets: dict, skill_id: str) -> str | None:
    """Return the highest named-variant star for a generic id (or None).

    Stars live only on named skills now, so a generic ref's effective rank is
    the maximum star across its named implementations.
    """
    entries = named_buckets.get(skill_id) or []
    levels = [e.get("level") for e in entries if e.get("level") in LEVEL_ORDER]
    if not levels:
        return None
    return max(levels, key=level_index)


def detect_unique_candidates(graph_data: dict, named_index: dict) -> list[dict]:
    """Detect basic skills eligible for promotion to 'unique' type.

    Criteria:
      1. type == "basic"
      2. top named-variant star >= 4★ (generic refs are rank-less)
      3. prerequisites == [] (orphan)
      4. Not referenced as a prerequisite by any other skill (graph-isolated)
      5. Has at least one named implementation in named_index
    """
    all_prereq_refs = set()
    for skill in graph_data.get("skills", []):
        for pid in skill.get("prerequisites", []):
            all_prereq_refs.add(pid)

    named_buckets = named_index.get("buckets", {})
    candidates = []

    for skill in graph_data.get("skills", []):
        if skill.get("type") != "basic":
            continue
        if skill.get("prerequisites", []):
            continue
        if skill["id"] in all_prereq_refs:
            continue
        if skill["id"] not in named_buckets or not named_buckets[skill["id"]]:
            continue
        star = top_named_level(named_buckets, skill["id"])
        if star is None or level_index(star) < 4:
            continue

        candidates.append({
            "skillId": skill["id"],
            "name": skill.get("name", skill["id"]),
            "currentLevel": star,
            "currentType": "basic",
            "promotionType": "unique",
            "namedImplementations": [ns.get("id", "") for ns in named_buckets[skill["id"]]],
        })

    return candidates


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_scanned_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def write_promotion_candidates(registry_path: str, username: str, candidates: list[dict],
                               unique_candidates: list[dict] | None = None) -> str:
    path = promotion_candidates_path(registry_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    normalized = []
    for candidate in candidates:
        suggested = candidate.get("suggestedLevel") or candidate.get("nextLevel")
        normalized.append({
            "skillId": candidate.get("skillId"),
            "currentLevel": candidate.get("currentLevel"),
            "suggestedLevel": suggested,
            "evidence": candidate.get("evidence", []),
        })
    payload = {
        "scannedAt": _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "username": username,
        "candidates": normalized,
        "uniqueCandidates": unique_candidates or [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return path


def load_promotion_candidates(registry_path: str, max_age_hours: int = 24) -> dict:
    path = promotion_candidates_path(registry_path)
    if not os.path.exists(path):
        raise ValueError("Run `gaia scan` first before promoting skills.")
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    scanned_at = _parse_scanned_at(payload.get("scannedAt", ""))
    if scanned_at is None:
        raise ValueError("Run `gaia scan` again before promoting skills.")
    age_seconds = (_utc_now() - scanned_at).total_seconds()
    if age_seconds > max_age_hours * 60 * 60:
        raise ValueError("Run `gaia scan` again before promoting skills.")
    return payload


def _candidate_for(payload: dict, skill_id: str) -> dict | None:
    for candidate in payload.get("candidates", []):
        if candidate.get("skillId") != skill_id:
            continue
        return candidate
    return None


def promotable_candidates(registry_path: str, username: str | None = None) -> list[dict]:
    payload = load_promotion_candidates(registry_path)
    if username and payload.get("username") != username:
        raise ValueError("Run `gaia scan` first for the current user before promoting skills.")
    return payload.get("candidates", [])


def promote_from_candidates(
    username: str,
    skill_id: str,
    registry_path: str,
    new_display_name: str | None = None,
) -> dict:
    payload = load_promotion_candidates(registry_path)
    if payload.get("username") != username:
        raise ValueError("Run `gaia scan` first for the current user before promoting skills.")
    candidate = _candidate_for(payload, skill_id)
    if candidate is None:
        raise ValueError("Only skills listed as promotion candidates can be promoted. Run `gaia scan` first.")
    suggested_level = candidate.get("suggestedLevel")
    if suggested_level not in LEVEL_ORDER:
        raise ValueError("Run `gaia scan` again before promoting skills.")

    tree_data = load_tree(username, registry_path)
    if tree_data is None:
        raise ValueError(f"No skill tree found for user '{username}'.")
    entry = _get_skill_from_tree(tree_data, skill_id)
    if entry is None:
        raise ValueError("Only skills listed as promotion candidates can be promoted. Run `gaia scan` first.")
    if entry.get("level") != candidate.get("currentLevel"):
        raise ValueError("Run `gaia scan` again before promoting skills.")

    previous = entry.get("level")
    entry["level"] = suggested_level
    tree_data["updatedAt"] = date.today().isoformat()
    save_tree(username, tree_data, registry_path)

    from gaia_cli.timeline import append_skill_tree_event
    append_skill_tree_event(
        username,
        skill_id,
        "ascend" if suggested_level == "6★" else "rank_up",
        f"Leveled up from {previous} to {suggested_level}",
        registry_path
    )

    display_name = new_display_name
    if display_name is None:
        graph_path = registry_graph_path(registry_path)
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            graph_skill = _get_skill_from_graph(graph_data, skill_id)
            if graph_skill:
                display_name = graph_skill.get("name", skill_id)
    return {
        "skillId": skill_id,
        "previousLevel": previous,
        "newLevel": suggested_level,
        "displayName": display_name or skill_id,
    }


def promote_skill(
    username: str,
    skill_id: str,
    registry_path: str,
    new_display_name: str | None = None,
) -> dict:
    """Promote a skill to the next level in the user's tree.

    Args:
        username: GitHub username.
        skill_id: The skill ID to promote.
        registry_path: Path to the registry root (where skill-trees/ lives).
        new_display_name: Optional new display name (unused in tree storage
            but returned in the result dict for downstream consumers).

    Returns:
        A dict with keys: skillId, previousLevel, newLevel, displayName.

    Raises:
        ValueError: If the skill is not found in the tree or is already at max level.
    """
    tree_data = load_tree(username, registry_path)
    if tree_data is None:
        raise ValueError(f"No skill tree found for user '{username}'.")

    entry = _get_skill_from_tree(tree_data, skill_id)
    if entry is None:
        raise ValueError(f"Skill '{skill_id}' not found in {username}'s tree.")

    current = entry["level"]
    target = next_level(current)
    if target is None:
        raise ValueError(
            f"Skill '{skill_id}' is already at maximum level ({current})."
        )

    # Update the level in-place
    entry["level"] = target

    # Update the tree's updatedAt timestamp
    tree_data["updatedAt"] = date.today().isoformat()

    save_tree(username, tree_data, registry_path)

    from gaia_cli.timeline import append_skill_tree_event
    append_skill_tree_event(
        username,
        skill_id,
        "ascend" if target == "6★" else "rank_up",
        f"Leveled up from {current} to {target}",
        registry_path
    )

    # Load graph to get display name if not provided
    display_name = new_display_name
    if display_name is None:
        graph_path = registry_graph_path(registry_path)
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            graph_skill = _get_skill_from_graph(graph_data, skill_id)
            if graph_skill:
                display_name = graph_skill.get("name", skill_id)
        if display_name is None:
            display_name = skill_id

    return {
        "skillId": skill_id,
        "previousLevel": current,
        "newLevel": target,
        "displayName": display_name,
    }


def promote_to_unique(skill_id: str, registry_path: str) -> dict:
    """Promote a basic skill to 'unique' type in gaia.json.

    Validates the skill meets all unique eligibility criteria before modifying
    the registry graph file. Returns a result dict on success.

    Raises:
        ValueError: If the skill is not eligible for unique promotion.
    """
    graph_path = registry_graph_path(registry_path)
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    graph_skill = _get_skill_from_graph(graph_data, skill_id)
    if graph_skill is None:
        raise ValueError(f"Skill '{skill_id}' not found in registry graph.")
    if graph_skill.get("type") != "basic":
        raise ValueError(f"Skill '{skill_id}' is type '{graph_skill.get('type')}', not 'basic'.")
    if graph_skill.get("prerequisites", []):
        raise ValueError(f"Skill '{skill_id}' has prerequisites — must be graph-isolated.")

    all_prereq_refs = set()
    for skill in graph_data.get("skills", []):
        for pid in skill.get("prerequisites", []):
            all_prereq_refs.add(pid)
    if skill_id in all_prereq_refs:
        raise ValueError(f"Skill '{skill_id}' is referenced as a prerequisite — must be graph-isolated.")

    from .graph import load_named_skills
    named_index = load_named_skills(registry_path)
    named_buckets = named_index.get("buckets", {})
    if skill_id not in named_buckets or not named_buckets[skill_id]:
        raise ValueError(f"Skill '{skill_id}' has no named implementation — required for unique promotion.")

    star = top_named_level(named_buckets, skill_id)
    if star is None or level_index(star) < 4:
        raise ValueError(f"Skill '{skill_id}' needs a 4★+ named implementation for unique promotion.")

    graph_skill["type"] = "unique"
    graph_skill["updatedAt"] = date.today().isoformat()

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    from gaia_cli.timeline import append_skill_event
    append_skill_event(
        skill_id,
        "rank_up",
        None,
        "Promoted to unique skill",
        registry_path
    )

    return {
        "skillId": skill_id,
        "previousType": "basic",
        "newType": "unique",
        "level": star,
        "displayName": graph_skill.get("name", skill_id),
    }


def promotion_state(skill_id: str, tree_data: dict, graph_data: dict) -> str:
    """Return the promotion state for a skill.

    Possible return values:
        - "not_unlocked" — skill is not in the user's tree
        - "max_level" — skill is already at max level (6★)
        - "eligible" — skill can be promoted (evidence requirement met)
        - "blocked" — next level requires evidence the graph skill lacks
    """
    entry = _get_skill_from_tree(tree_data, skill_id)
    if entry is None:
        return "not_unlocked"

    current = entry["level"]
    target = next_level(current)
    if target is None:
        return "max_level"

    graph_skill = _get_skill_from_graph(graph_data, skill_id)
    if graph_skill is None:
        return "blocked"

    if _meets_evidence_floor(graph_skill, target):
        return "eligible"

    return "blocked"
