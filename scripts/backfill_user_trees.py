#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAIA_JSON = REPO_ROOT / "registry" / "gaia.json"
NAMED_JSON = REPO_ROOT / "registry" / "named-skills.json"
TREES_DIR = REPO_ROOT / "skill-trees"

def main():
    if not GAIA_JSON.exists() or not NAMED_JSON.exists():
        print("Missing gaia.json or named-skills.json")
        return

    with open(GAIA_JSON, "r", encoding="utf-8") as f:
        gaia_data = json.load(f)
    
    with open(NAMED_JSON, "r", encoding="utf-8") as f:
        named_data = json.load(f)
        
    by_contributor = named_data.get("byContributor", {})
    named_buckets = named_data.get("buckets", {})
    
    # Map named skill ID to its data
    named_skills_map = {}
    for ref, entries in named_buckets.items():
        for entry in entries:
            named_skills_map[entry["id"]] = entry

    # Extract all timeline events from canonical skills
    canonical_timelines = []
    for skill in gaia_data.get("skills", []):
        skill_id = skill.get("id")
        for ev in skill.get("timeline", []):
            ev_copy = ev.copy()
            ev_copy["skillId"] = skill_id
            canonical_timelines.append(ev_copy)
            
    for contributor, skill_ids in by_contributor.items():
        tree_dir = TREES_DIR / contributor
        tree_dir.mkdir(parents=True, exist_ok=True)
        tree_path = tree_dir / "skill-tree.json"
        
        if tree_path.exists():
            with open(tree_path, "r", encoding="utf-8") as f:
                try:
                    tree = json.load(f)
                except Exception:
                    tree = {}
        else:
            tree = {}
            
        tree["userId"] = contributor
        tree["updatedAt"] = tree.get("updatedAt", "2026-05-25")
        
        unlocked_skills = tree.get("unlockedSkills", [])
        unlocked_map = {u.get("skillId"): u for u in unlocked_skills}
        
        # Add named skills they own
        for skill_id in skill_ids:
            ns = named_skills_map.get(skill_id, {})
            # We use the named skill ID
            if skill_id not in unlocked_map:
                created_at = ns.get("createdAt", "2026-05-25T00:00:00Z")
                if "T" not in created_at:
                    created_at += "T00:00:00Z"
                
                lvl = ns.get("level", "2★")
                unlocked_map[skill_id] = {
                    "skillId": skill_id,
                    "level": lvl,
                    "unlockedAt": created_at,
                    "unlockedIn": f"{contributor}/gaia-skill-tree",
                    "combinedFrom": [],
                    "levelHistory": [
                        {
                            "level": lvl,
                            "achievedAt": created_at,
                            "source": "promotion"
                        }
                    ]
                }
                
        # Also grab canonical events for this contributor
        user_events = [ev for ev in canonical_timelines if ev.get("contributor") == contributor]
        
        # Ensure canonical skills they contributed to are in unlockedSkills
        for ev in user_events:
            canonical_id = ev.get("skillId")
            
            # Check if they already have a named variant for this canonical ID
            has_named_variant = any(ns_id.endswith(f"/{canonical_id}") for ns_id in unlocked_map)
            
            target_id = canonical_id
            if has_named_variant:
                # Map event to the named variant
                target_id = next(ns_id for ns_id in unlocked_map if ns_id.endswith(f"/{canonical_id}"))
                ev["skillId"] = target_id
            
            if target_id not in unlocked_map:
                unlocked_map[target_id] = {
                    "skillId": target_id,
                    "level": "2★", # Will be updated by history
                    "unlockedAt": ev.get("timestamp"),
                    "unlockedIn": f"{contributor}/gaia-skill-tree",
                    "combinedFrom": [],
                    "levelHistory": []
                }
                
            # Synthesize levelHistory from canonical events if not present
            if "newValue" in ev and ev["action"] in ["propose", "add", "rank_up", "fuse", "demote", "ascend"]:
                lvl = ev["newValue"]
                achievedAt = ev["timestamp"]
                
                lh = unlocked_map[target_id].get("levelHistory", [])
                # Avoid duplicates
                if not any(h.get("achievedAt") == achievedAt and h.get("level") == lvl for h in lh):
                    lh.append({
                        "level": lvl,
                        "achievedAt": achievedAt,
                        "source": "promotion"
                    })
                unlocked_map[target_id]["levelHistory"] = sorted(lh, key=lambda x: x["achievedAt"])
                unlocked_map[target_id]["level"] = unlocked_map[target_id]["levelHistory"][-1]["level"]

        tree["unlockedSkills"] = list(unlocked_map.values())
        
        # Merge timeline events
        existing_timeline = tree.get("timeline", [])
        existing_keys = {(e.get("timestamp"), e.get("action"), e.get("skillId")) for e in existing_timeline}
        
        # Add canonical events
        for ev in user_events:
            key = (ev.get("timestamp"), ev.get("action"), ev.get("skillId"))
            if key not in existing_keys:
                ev_copy = {k: v for k, v in ev.items() if k != "contributor"} # Remove contributor field for tree
                existing_timeline.append(ev_copy)
                existing_keys.add(key)
                
        # Synthesize timeline events for named skills if they don't have canonical events
        for skill_id, u in unlocked_map.items():
            if not any(e.get("skillId") == skill_id for e in existing_timeline):
                ts = u.get("unlockedAt", "2026-05-25T00:00:00Z")
                lvl = u.get("level", "2★")
                ev = {
                    "timestamp": ts,
                    "action": "register",
                    "skillId": skill_id,
                    "details": f"Registered named skill {skill_id}",
                    "previousValue": None,
                    "newValue": lvl
                }
                key = (ev["timestamp"], ev["action"], ev["skillId"])
                if key not in existing_keys:
                    existing_timeline.append(ev)
                    existing_keys.add(key)
                    
        # Sort timeline by timestamp
        tree["timeline"] = sorted(existing_timeline, key=lambda x: x.get("timestamp", ""))
        
        # Ensure stats exist
        if "stats" not in tree:
            tree["stats"] = {
                "totalUnlocked": len(tree["unlockedSkills"]),
                "deepestLineage": 1
            }
        else:
            tree["stats"]["totalUnlocked"] = len(tree["unlockedSkills"])
            
        tree["pendingCombinations"] = tree.get("pendingCombinations", [])

        with open(tree_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
            f.write("\n")
            
    print(f"Backfilled skill trees for {len(by_contributor)} contributors.")

if __name__ == "__main__":
    main()
