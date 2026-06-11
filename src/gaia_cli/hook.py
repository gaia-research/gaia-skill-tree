"""Claude Code hook integration for Gaia skill scanning.

Entry point invoked by Claude Code PostToolUse hook after file edits.
Orchestrates scan → path computation → unlock/promotion notifications.
"""

import json
import os

from gaia_cli.scanner import load_config, scan_repo_detailed
from gaia_cli.resolver import resolve_skills
from gaia_cli.registry import registry_graph_path, resolve_registry_path
from gaia_cli.treeManager import load_tree
from gaia_cli.pathEngine import compute_paths, load_paths, save_paths, diff_paths
from gaia_cli.cardRenderer import render_unlock_card, render_path_summary, render_promotion_prompt


def should_trigger(changed_files: list[str] | None, config: dict) -> bool:
    """Check if changed files overlap with configured scan paths."""
    if not changed_files:
        return True  # No file info — trigger anyway (safe default)
    scan_paths = config.get("scanPaths", [])
    if not scan_paths:
        return True
    for f in changed_files:
        normalized = f.replace("\\", "/")
        for sp in scan_paths:
            if normalized.startswith(sp.replace("\\", "/")):
                return True
    return False


def hook_entry(event: str = "file_edit", registry_path: str | None = None) -> None:
    """
    Entry point called by Claude Code hook or `gaia _hook`.

    1. Checks .gaia/config.json exists
    2. Loads previous paths
    3. Runs scan + resolve + compute
    4. Diffs old vs new paths
    5. If new nearUnlocks: prints unlock card(s)
    6. If promotions available: prints promotion prompt
    7. Saves updated paths
    """
    config = load_config()
    if not config:
        return  # Not a Gaia-initialized repo

    registry = resolve_registry_path(registry_path)
    username = config.get("gaiaUser")
    if not username:
        return

    # Load previous state
    old_paths = load_paths()

    # Run scan pipeline
    try:
        scan_result = scan_repo_detailed()
    except Exception:
        return  # Scan failure shouldn't crash the hook

    tokens = {t.lstrip('/') for t in scan_result.get("tokens", set())}
    graph_path = registry_graph_path(registry)
    if not os.path.exists(graph_path):
        return

    detected_ids = resolve_skills(list(tokens), graph_path)

    # Load user tree
    tree_data = load_tree(username, registry)
    owned_ids = []
    if tree_data:
        owned_ids = [s.get("skillId") for s in tree_data.get("unlockedSkills", [])]

    # Load graph
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    # Compute new paths
    new_paths = compute_paths(graph_data, owned_ids, detected_ids)
    new_paths["userId"] = username

    # Diff
    changes = diff_paths(old_paths, new_paths)

    # Build skill lookup
    skill_map = {s["id"]: s for s in graph_data.get("skills", [])}

    # Render unlock cards for new near-unlocks
    if changes.get("new_near_unlocks"):
        for skill_id in changes["new_near_unlocks"]:
            skill = skill_map.get(skill_id)
            if skill:
                # Find newly opened paths from this unlock
                opened = [
                    p for p in new_paths.get("availablePaths", [])
                    if p.get("distance", 99) <= 2
                ]
                print(render_unlock_card(skill, opened[:3]))
                print()

    # Show path summary if anything changed
    if changes.get("new_near_unlocks") or changes.get("new_one_away"):
        print(render_path_summary(new_paths))
        print()

    # Show promotion prompts
    if changes.get("promotions_available"):
        from gaia_cli.promotion import check_promotion_eligibility
        if tree_data:
            eligible = check_promotion_eligibility(graph_data, tree_data)
            for promo in eligible[:2]:
                skill = skill_map.get(promo["skillId"])
                if skill:
                    print(render_promotion_prompt(skill, promo.get("nextLevel", "2★")))

    # Persist
    save_paths(new_paths)
