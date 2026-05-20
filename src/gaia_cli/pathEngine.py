"""Compute and persist available progression paths for a user."""

import json
import os
from collections import deque
from datetime import datetime, timezone

from gaia_cli.registry import registry_graph_path, resolve_registry_path
from gaia_cli.resolver import resolve_skills
from gaia_cli.scanner import load_config, scan_repo_detailed
from gaia_cli.treeManager import load_tree
from gaia_cli.leveling import level_summary

PATHS_FILE = ".gaia/paths.json"
MAX_BFS_DISTANCE = 5


def compute_paths(graph_data: dict, owned_ids: list, detected_ids: list) -> dict:
    """
    Compute progression paths from current state.

    Args:
        graph_data: parsed gaia.json
        owned_ids: list of skill IDs the user has unlocked
        detected_ids: list of skill IDs detected in the repo (resolved from scanner)

    Returns dict with:
        - nearUnlocks: skills whose ALL prerequisites are in (owned | detected), not already owned
        - oneAway: skills missing exactly 1 prerequisite
        - availablePaths: BFS forward from owned through derivatives, with distance
        - computedAt: ISO timestamp
    """
    available = set(owned_ids) | set(detected_ids)
    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}

    near_unlocks = []
    one_away = []

    for skill in graph_data.get("skills", []):
        if skill.get("type") not in ("extra", "ultimate"):
            continue
        sid = skill["id"]
        if sid in available:
            continue
        prereqs = skill.get("prerequisites", [])
        missing = [p for p in prereqs if p not in available]
        if len(missing) == 0:
            summary = level_summary(skill)
            near_unlocks.append({
                "skillId": sid,
                "name": skill.get("name", sid),
                "type": skill.get("type"),
                "levelFloor": summary["effectiveLevel"],
                "baseLevelFloor": summary["baseLevel"],
                "effectiveLevelFloor": summary["effectiveLevel"],
                "levelMeta": summary,
                "satisfiedPrereqs": prereqs,
            })
        elif len(missing) == 1:
            summary = level_summary(skill)
            one_away.append({
                "skillId": sid,
                "name": skill.get("name", sid),
                "type": skill.get("type"),
                "levelFloor": summary["effectiveLevel"],
                "baseLevelFloor": summary["baseLevel"],
                "effectiveLevelFloor": summary["effectiveLevel"],
                "levelMeta": summary,
                "missingPrereq": missing[0],
                "satisfiedPrereqs": [p for p in prereqs if p in available],
            })

    # BFS forward from owned through derivatives
    available_paths = {}
    owned_set = set(owned_ids)
    queue = deque()

    for sid in owned_ids:
        if sid in skill_map:
            for deriv in skill_map[sid].get("derivatives", []):
                if deriv not in owned_set and deriv in skill_map:
                    if deriv not in available_paths:
                        available_paths[deriv] = 1
                        queue.append((deriv, 1))

    while queue:
        current_id, dist = queue.popleft()
        if dist >= MAX_BFS_DISTANCE:
            continue
        current_skill = skill_map.get(current_id)
        if not current_skill:
            continue
        for deriv in current_skill.get("derivatives", []):
            if deriv not in owned_set and deriv in skill_map:
                new_dist = dist + 1
                if deriv not in available_paths or available_paths[deriv] > new_dist:
                    available_paths[deriv] = new_dist
                    queue.append((deriv, new_dist))

    # Convert to list format
    paths_list = [
        {
            "skillId": sid,
            "name": skill_map[sid].get("name", sid),
            "distance": d,
        }
        for sid, d in sorted(available_paths.items(), key=lambda x: x[1])
        if sid in skill_map
    ]

    return {
        "nearUnlocks": near_unlocks,
        "oneAway": one_away,
        "availablePaths": paths_list,
        "computedAt": datetime.now(timezone.utc).isoformat(),
    }


def regenerate_paths(registry_path: str) -> dict:
    """
    Full pipeline: load config, load user tree, scan+resolve, compute paths,
    save to .gaia/paths.json. Returns the computed paths dict.
    """
    config = load_config()
    if not config:
        raise RuntimeError("No .gaia/config.json found. Run 'gaia init' first.")

    username = config.get("gaiaUser")
    if not username:
        raise RuntimeError("No gaiaUser set in .gaia/config.json.")

    # Load user's skill tree
    tree_data = load_tree(username, registry_path)
    owned_ids = []
    if tree_data:
        for entry in tree_data.get("unlockedSkills", []):
            owned_ids.append(entry.get("skillId"))

    # Scan repo and resolve skill tokens
    scan_result = scan_repo_detailed()
    tokens = {t.lstrip('/') for t in scan_result.get("tokens", set())}
    graph_path = registry_graph_path(registry_path)
    detected_ids = resolve_skills(list(tokens), graph_path)

    # Load graph data
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    # Compute paths
    paths = compute_paths(graph_data, owned_ids, detected_ids)
    paths["userId"] = username

    # Save
    save_paths(paths)
    return paths


def load_paths() -> dict | None:
    """Load .gaia/paths.json, return None if doesn't exist."""
    if not os.path.exists(PATHS_FILE):
        return None
    with open(PATHS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_paths(paths: dict) -> None:
    """Write .gaia/paths.json with proper encoding."""
    os.makedirs(os.path.dirname(PATHS_FILE), exist_ok=True)
    with open(PATHS_FILE, "w", encoding="utf-8") as f:
        json.dump(paths, f, indent=2, ensure_ascii=False)


def diff_paths(old_paths: dict | None, new_paths: dict) -> dict:
    """
    Compare old vs new paths.

    Returns:
        {
            "new_near_unlocks": [skill_ids newly in nearUnlocks],
            "new_one_away": [skill_ids newly in oneAway],
            "promotions_available": [skill_ids whose derivatives just got near-unlocked]
        }
    """
    new_near_ids = {e["skillId"] for e in new_paths.get("nearUnlocks", [])}
    new_one_away_ids = {e["skillId"] for e in new_paths.get("oneAway", [])}

    if old_paths is None:
        old_near_ids = set()
        old_one_away_ids = set()
    else:
        old_near_ids = {e["skillId"] for e in old_paths.get("nearUnlocks", [])}
        old_one_away_ids = {e["skillId"] for e in old_paths.get("oneAway", [])}

    newly_near = new_near_ids - old_near_ids
    newly_one_away = new_one_away_ids - old_one_away_ids

    # promotions_available: owned skills whose derivatives just appeared in nearUnlocks
    # We need owned skill info from the new_paths context; use userId to infer,
    # but since we don't store owned_ids in paths, we check which skills
    # have derivatives in the newly_near set by looking at availablePaths distance=1
    # Actually, we can infer from the nearUnlocks satisfiedPrereqs:
    # any prerequisite that is satisfied (i.e., owned or detected) and whose
    # derivative just appeared in nearUnlocks means that prereq is promotion-eligible.
    promotions = set()
    for entry in new_paths.get("nearUnlocks", []):
        if entry["skillId"] in newly_near:
            for prereq in entry.get("satisfiedPrereqs", []):
                promotions.add(prereq)

    return {
        "new_near_unlocks": sorted(newly_near),
        "new_one_away": sorted(newly_one_away),
        "promotions_available": sorted(promotions),
    }
