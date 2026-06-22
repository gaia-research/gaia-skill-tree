import os
import json
from gaia_cli.registry import registry_graph_path, named_skills_index_path


def meta_list_command(args):
    registry_path = args.registry
    graph_path = registry_graph_path(registry_path)
    named_index_path = named_skills_index_path(registry_path)

    results = []

    if getattr(args, "generic", False) or not getattr(args, "named", False):
        if os.path.exists(graph_path):
            with open(graph_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            for skill in graph_data.get("skills", []):
                item = {"id": skill["id"], "name": skill.get("name"), "kind": "generic"}
                if getattr(args, "description", False):
                    item["description"] = skill.get("description")
                # Generic refs are rank-less — only named skills carry a level.
                if getattr(args, "level", False) and skill.get("level"):
                    item["level"] = skill.get("level")
                if getattr(args, "evidence", False):
                    item["evidence_count"] = len(skill.get("evidence", []))

                if getattr(args, "extra", None):
                    for field in args.extra:
                        if field in skill:
                            item[field] = skill[field]
                results.append(item)

    if getattr(args, "named", False):
        if os.path.exists(named_index_path):
            with open(named_index_path, "r", encoding="utf-8") as f:
                named_data = json.load(f)
            for bucket_id, bucket_items in named_data.get("buckets", {}).items():
                for skill in bucket_items:
                    item = {
                        "id": skill["id"],
                        "name": skill.get("name"),
                        "kind": "named",
                        "genericSkillRef": bucket_id,
                    }
                    if getattr(args, "description", False):
                        item["description"] = skill.get("description")
                    if getattr(args, "level", False):
                        item["level"] = skill.get("level")
                    if getattr(args, "contributor", False):
                        item["contributor"] = skill.get("contributor")

                    if getattr(args, "extra", None):
                        for field in args.extra:
                            if field in skill:
                                item[field] = skill[field]
                    results.append(item)

    if not results:
        print("No skills found.")
        return

    # Output formatting
    if getattr(args, "json", False):
        print(json.dumps(results, indent=2))
    else:
        for item in results:
            kind_prefix = "[G] " if item["kind"] == "generic" else "[N] "
            line = f"{kind_prefix}/{item['id']} - {item.get('name')}"
            if "level" in item:
                line += f" ({item['level']})"
            if "contributor" in item:
                line += f" by {item['contributor']}"
            if "evidence_count" in item:
                line += f" [{item['evidence_count']} evidence]"

            if "description" in item:
                line += f"\n    {item['description']}"

            if getattr(args, "extra", None):
                for field in args.extra:
                    if field in item and field not in (
                        "id",
                        "name",
                        "kind",
                        "description",
                    ):
                        line += f"\n    {field}: {item[field]}"
            print(line)
