#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from datetime import datetime, timezone
import argparse

AUTHOR_MAP = {
    "Claude": "claude",
    "Juno": "juno",
    "Marco Tiongson": "mbtiongson1",
    "Marcus Rafael Tiongson": "mbtiongson1",
    "Marcus Rafael Tiongson (Marco)": "mbtiongson1",
    "Marcus Tiongson": "mbtiongson1",
    "Rico Tiongson": "mbtiongson1",
    "mbtiongson1": "mbtiongson1",
    "cloudflare-workers-and-pages[bot]": "gaiabot",
    "dependabot[bot]": "dependabot",
    "github-actions[bot]": "gaiabot",
    "google-labs-jules[bot]": "jules",
    "kriptoburak": "kriptoburak",
    "pexp13": "pexp13"
}

def map_author(author_name):
    return AUTHOR_MAP.get(author_name, author_name.lower().replace(" ", "-"))

def format_iso_utc(date_str):
    # Parse git strict ISO 8601 (e.g. 2026-05-25T12:44:23+08:00)
    # and convert to UTC Zulu (e.g., 2026-05-25T04:44:23Z)
    try:
        dt = datetime.fromisoformat(date_str)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return date_str

def get_git_file_content(commit_hash, file_path, skill_id=None):
    try:
        # Try direct retrieval
        cmd = ["git", "show", f"{commit_hash}:{file_path}"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout
    except subprocess.CalledProcessError:
        # If renamed, search tree for [skill_id].json
        if skill_id:
            try:
                list_cmd = ["git", "ls-tree", "-r", "--name-only", commit_hash]
                tree_res = subprocess.run(list_cmd, capture_output=True, text=True, check=True)
                for path in tree_res.stdout.splitlines():
                    if path.endswith(f"/{skill_id}.json") or path == f"{skill_id}.json":
                        show_cmd = ["git", "show", f"{commit_hash}:{path}"]
                        show_res = subprocess.run(show_cmd, capture_output=True, text=True, check=True)
                        return show_res.stdout
            except Exception:
                pass
    return None

def parse_stars(level_str):
    if not level_str:
        return 0
    # Count star characters
    stars = level_str.count("★")
    if stars > 0:
        return stars
    # Try digit
    for char in level_str:
        if char.isdigit():
            return int(char)
    return 0

def analyze_history(file_path):
    skill_id = os.path.splitext(os.path.basename(file_path))[0]
    
    # 1. Get commit history
    # Format: hash|author_name|author_date_iso
    cmd = ["git", "log", "--follow", "--format=%H|%an|%aI", "--", file_path]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    commits = []
    for line in res.stdout.splitlines():
        if "|" in line:
            parts = line.split("|", 2)
            commits.append({
                "hash": parts[0],
                "author": map_author(parts[1]),
                "timestamp": format_iso_utc(parts[2])
            })
    
    # Reverse to process chronologically (oldest to newest)
    commits.reverse()
    
    timeline_events = []
    prev_state = None
    
    for idx, commit in enumerate(commits):
        raw_content = get_git_file_content(commit["hash"], file_path, skill_id)
        if not raw_content:
            continue
        
        try:
            state = json.loads(raw_content)
        except json.JSONDecodeError:
            continue
        
        # Determine status/level details
        current_level = state.get("level", "0★")
        current_status = state.get("status", "provisional")
        current_type = state.get("type", "basic")
        
        # Handle evidence list comparison
        current_evidence_urls = set()
        evidence_list = state.get("evidence", [])
        if isinstance(evidence_list, list):
            for ev in evidence_list:
                if isinstance(ev, dict) and "source" in ev:
                    current_evidence_urls.add(ev["source"])
        
        if prev_state is None:
            # Chronologically first commit: proposal/creation
            action = "propose" if current_status == "provisional" else "add"
            details = f"Skill created as {current_level} ({current_status})"
            timeline_events.append({
                "timestamp": commit["timestamp"],
                "action": action,
                "contributor": commit["author"],
                "details": details,
                "previousValue": None,
                "newValue": current_level
            })
        else:
            prev_level = prev_state.get("level", "0★")
            prev_status = prev_state.get("status", "provisional")
            prev_type = prev_state.get("type", "basic")
            
            # 1. Level change
            if prev_level != current_level:
                prev_rank = parse_stars(prev_level)
                curr_rank = parse_stars(current_level)
                if curr_rank > prev_rank:
                    action = "rank_up"
                    details = f"Upgraded rank from {prev_level} to {current_level}"
                else:
                    action = "demote"
                    details = f"Calibrated/demoted rank from {prev_level} to {current_level}"
                
                timeline_events.append({
                    "timestamp": commit["timestamp"],
                    "action": action,
                    "contributor": commit["author"],
                    "details": details,
                    "previousValue": prev_level,
                    "newValue": current_level
                })
            
            # 2. Status change
            if prev_status != current_status:
                action = None
                if current_status == "validated":
                    action = "verified"
                    details = "Skill status verified and validated"
                elif current_status == "disputed":
                    action = "disputed"
                    details = "Skill status marked as disputed"
                
                if action:
                    timeline_events.append({
                        "timestamp": commit["timestamp"],
                        "action": action,
                        "contributor": commit["author"],
                        "details": details,
                        "previousValue": prev_status,
                        "newValue": current_status
                    })
            
            # 3. Type change
            if prev_type != current_type:
                timeline_events.append({
                    "timestamp": commit["timestamp"],
                    "action": "type_change",
                    "contributor": commit["author"],
                    "details": f"Type adjusted from {prev_type} to {current_type}",
                    "previousValue": prev_type,
                    "newValue": current_type
                })
            
            # 4. Evidence added
            prev_evidence_list = prev_state.get("evidence", [])
            prev_urls = set()
            if isinstance(prev_evidence_list, list):
                for ev in prev_evidence_list:
                    if isinstance(ev, dict) and "source" in ev:
                        prev_urls.add(ev["source"])
            
            new_sources = current_evidence_urls - prev_urls
            if new_sources:
                details = f"Added evidence: {', '.join(list(new_sources)[:2])}"
                if len(new_sources) > 2:
                    details += f" and {len(new_sources)-2} more"
                
                timeline_events.append({
                    "timestamp": commit["timestamp"],
                    "action": "evidence_added",
                    "contributor": commit["author"],
                    "details": details,
                    "previousValue": None,
                    "newValue": current_level
                })
        
        prev_state = state
    
    return timeline_events

def process_file(file_path):
    print(f"Analyzing {file_path}...", flush=True)
    generated_events = analyze_history(file_path)
    if not generated_events:
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    existing_events = data.get("timeline", [])
    
    # Merge events by timestamp + action to avoid duplicates
    event_map = {}
    for ev in existing_events:
        key = (ev["timestamp"], ev["action"])
        event_map[key] = ev
        
    for ev in generated_events:
        key = (ev["timestamp"], ev["action"])
        if key not in event_map:
            event_map[key] = ev
            
    # Sort merged timeline by timestamp ascending
    sorted_events = sorted(event_map.values(), key=lambda x: x["timestamp"])
    
    data["timeline"] = sorted_events
    
    # Save back
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Backfill timeline logs from git history.")
    parser.add_argument("files", nargs="*", help="Files to process. If empty, processes all registry nodes/named skills.")
    args = parser.parse_args()
    
    files = args.files
    if not files:
        # Find all files in nodes and named directories
        files = []
        for root_dir in ["registry/nodes", "registry/named"]:
            if os.path.exists(root_dir):
                for root, _, filenames in os.walk(root_dir):
                    for f in filenames:
                        if f.endswith(".json") and f != "named-skills.json":
                            files.append(os.path.join(root, f))
    
    print(f"Found {len(files)} files to process.")
    for idx, f in enumerate(files):
        try:
            process_file(f)
        except Exception as e:
            print(f"Error processing {f}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
