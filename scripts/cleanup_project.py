import subprocess
import json
import sys

PROJECT_NUMBER = 2
PROJECT_ID = "PVT_kwHOCR7Dzs4BaPP0"
OWNER = "mbtiongson1"

# Dates mapping
DATES = {
    "Immediate Next 30 Days": ("2026-06-10", "2026-07-10"),
    "Phase 1 — Trust Infrastructure": ("2026-06-10", "2026-09-10"),
    "Phase 2 — Product Moat": ("2026-07-10", "2026-11-10"),
    "Phase 3 — Growth Engine": ("2026-08-10", "2026-12-10"),
}

FIELD_IDS = {
    "Start date": "PVTF_lAHOCR7Dzs4BaPP0zhVIRNg",
    "Target date": "PVTF_lAHOCR7Dzs4BaPP0zhVIRNk",
}

def run_gh(args):
    result = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running gh {' '.join(args)}: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout

def main():
    # Get all items in project
    items_json = run_gh(["project", "item-list", str(PROJECT_NUMBER), "--owner", OWNER, "--format", "json"])
    if not items_json:
        return
    items = json.loads(items_json)["items"]

    for item in items:
        item_id = item["id"]
        labels = item.get("labels", [])
        title = item.get("title", "Unknown")
        
        # 1. Prune unrelated
        if "v2-unrelated" in labels:
            print(f"Pruning unrelated item: {title}")
            run_gh(["project", "item-delete", str(PROJECT_NUMBER), "--owner", OWNER, "--id", item_id])
            continue

        # 2. Update dates for roadmap items
        milestone = item.get("milestone")
        if milestone:
            m_title = milestone.get("title")
            if m_title in DATES:
                start, target = DATES[m_title]
                print(f"Updating dates for {title} (Milestone: {m_title})")
                run_gh(["project", "item-edit", "--project-id", PROJECT_ID, "--id", item_id, "--field-id", FIELD_IDS["Start date"], "--date", start])
                run_gh(["project", "item-edit", "--project-id", PROJECT_ID, "--id", item_id, "--field-id", FIELD_IDS["Target date"], "--date", target])

    # 3. Add missing roadmap issues (646-652)
    # First get all issues with v2-roadmap label
    roadmap_issues_json = run_gh(["issue", "list", "--label", "v2-roadmap", "--json", "number,url"])
    if roadmap_issues_json:
        roadmap_issues = json.loads(roadmap_issues_json)
        # Refresh items after potential deletions
        items_json = run_gh(["project", "item-list", str(PROJECT_NUMBER), "--owner", OWNER, "--format", "json"])
        items = json.loads(items_json)["items"]
        existing_urls = {item["content"].get("url") for item in items if "content" in item}
        
        for issue in roadmap_issues:
            if issue["url"] not in existing_urls:
                print(f"Adding missing roadmap issue: {issue['url']}")
                run_gh(["project", "item-add", str(PROJECT_NUMBER), "--owner", OWNER, "--url", issue["url"]])

if __name__ == "__main__":
    main()
