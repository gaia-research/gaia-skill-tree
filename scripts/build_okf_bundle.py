#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAIA_JSON_PATH = ROOT / "registry" / "gaia.json"
OKF_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / "docs" / "okf")

def main():
    print("🚀 Generating OKF (Open Knowledge Format) Bundle...")
    
    if not GAIA_JSON_PATH.exists():
        print(f"❌ Error: gaia.json not found at {GAIA_JSON_PATH}")
        return

    with open(GAIA_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    skills = data.get("skills", [])
    print(f"📊 Loaded {len(skills)} skills from registry.")

    # Build skill ID to type map
    skill_types = {}
    skill_names = {}
    for s in skills:
        sid = s.get("id")
        stype = s.get("type", "basic")
        sname = s.get("name", sid)
        skill_types[sid] = stype
        skill_names[sid] = sname

    # Create directories
    os.makedirs(OKF_DIR, exist_ok=True)

    # Helper to generate links
    def make_link(sid):
        stype = skill_types.get(sid)
        name = skill_names.get(sid, sid)
        if stype:
            return f"[{name}](/skills/{stype}/{sid}.md)"
        return f"[{name}](#{sid})"

    # Generate individual concepts
    for s in skills:
        sid = s.get("id")
        stype = s.get("type", "basic")
        name = s.get("name", sid)
        summary = s.get("summary", s.get("description", ""))
        # Normalize summary to one line
        summary_clean = re.sub(r'\s+', ' ', summary).strip()
        description = s.get("description", "")
        use_case = s.get("useCase", "")
        directives = s.get("directives", "")
        prereqs = s.get("prerequisites", [])
        derivs = s.get("derivatives", [])
        updated_at = s.get("updatedAt", s.get("createdAt", "2026-06-29"))

        # Format timestamp
        if "T" not in updated_at:
            timestamp = f"{updated_at}T00:00:00Z"
        else:
            timestamp = updated_at

        # Frontmatter (JSON dumps protects colons and quotes!)
        title_esc = json.dumps(name)
        summary_esc = json.dumps(summary_clean)

        frontmatter = f"""---
type: "AI Agent Skill"
title: {title_esc}
description: {summary_esc}
resource: "https://gaia.tiongson.co/codex.html#{sid}"
tags: ["gaia-skill-tree", "{stype}-skill"]
timestamp: "{timestamp}"
---
"""

        # Body
        body = f"# {name}\n\n"
        if description:
            body += f"## Description\n\n{description}\n\n"
        if use_case:
            body += f"## Use Case\n\n{use_case}\n\n"
        if directives:
            body += f"## Directives\n\n{directives}\n\n"

        if prereqs:
            body += "## Prerequisites\n\n"
            body += "\n".join([f"- {make_link(p)}" for p in prereqs]) + "\n\n"
        if derivs:
            body += "## Derivatives\n\n"
            body += "\n".join([f"- {make_link(d)}" for d in derivs]) + "\n\n"

        # Ensure the subdirectory exists before writing the file
        type_dir = OKF_DIR / "skills" / stype
        os.makedirs(type_dir, exist_ok=True)

        file_path = type_dir / f"{sid}.md"
        with open(file_path, "w", encoding="utf-8") as f_out:
            f_out.write(frontmatter + "\n" + body)

    # Generate folder indexes for subdirectories (skills/basic/, skills/extra/, etc.)
    for stype in ["basic", "extra", "ultimate", "unique"]:
        type_skills = [s for s in skills if s.get("type") == stype]
        if type_skills:
            sub_index_md = f"""# {stype.capitalize()} Skills

"""
            for s in sorted(type_skills, key=lambda x: x.get("name", "")):
                sid = s.get("id")
                name = s.get("name", sid)
                desc = s.get("summary", s.get("description", ""))
                desc_clean = re.sub(r'\s+', ' ', desc).strip()
                sub_index_md += f"* [{name}](/{sid}.md) - {desc_clean}\n"
                
            with open(OKF_DIR / "skills" / stype / "index.md", "w", encoding="utf-8") as f_sub_index:
                f_sub_index.write(sub_index_md)

    # Generate root index.md (with okf_version frontmatter)
    index_md = """---
okf_version: "0.1"
---

# Gaia Skill Tree OKF Bundle

Welcome to the agent-readable Open Knowledge Format (OKF) bundle of the Gaia Skill Tree registry.

## Registry Index

"""
    for stype in ["ultimate", "extra", "basic"]:
        type_skills = [s for s in skills if s.get("type") == stype]
        if type_skills:
            index_md += f"### {stype.capitalize()} Skills ({len(type_skills)})\n\n"
            for s in sorted(type_skills, key=lambda x: x.get("name", "")):
                sid = s.get("id")
                name = s.get("name", sid)
                desc = s.get("summary", s.get("description", ""))
                desc_clean = re.sub(r'\s+', ' ', desc).strip()
                index_md += f"* [{name}](/skills/{stype}/{sid}.md) - {desc_clean}\n"
            index_md += "\n"

    with open(OKF_DIR / "index.md", "w", encoding="utf-8") as f_index:
        f_index.write(index_md)

    # ── emit index.json for the /skills/ aggregated index page (W5) ──────────
    _build_okf_index(skills, OKF_DIR)

    print("[OK] OKF Bundle generated successfully in docs/okf/!")


def _build_okf_index(skills: list, okf_dir):
    """Emit docs/okf/index.json — machine-readable index consumed by docs/skills/index.js.

    Shape::
        {
          "schemaVersion": "1.0.0",
          "generatedAt": null,     # frozen null to avoid timestamp drift
          "families": [
            {"id": "basic",    "count": N, "skills": [{"id": "...", "name": "...", "summary": "..."}, ...]},
            {"id": "extra",    ...},
            {"id": "ultimate", ...}
          ]
        }
    """
    from pathlib import Path as _Path
    import json as _json

    families = []
    for stype in ["basic", "extra", "ultimate"]:
        type_skills = sorted(
            [s for s in skills if s.get("type") == stype],
            key=lambda x: x.get("name", ""),
        )
        family_skills = [
            {
                "id": s.get("id"),
                "name": s.get("name", s.get("id")),
                "summary": re.sub(r'\s+', ' ', s.get("summary", s.get("description", ""))).strip(),
            }
            for s in type_skills
        ]
        families.append({
            "id": stype,
            "count": len(type_skills),
            "skills": family_skills,
        })

    payload = {
        "schemaVersion": "1.0.0",
        "generatedAt": None,
        "families": families,
    }

    out_path = _Path(okf_dir) / "index.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        _json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
if __name__ == "__main__":
    main()
