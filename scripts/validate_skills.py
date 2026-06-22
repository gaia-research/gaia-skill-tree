#!/usr/bin/env python3
import os
import sys
import yaml
import re
from pathlib import Path

def get_skill_dirs(base_dir):
    """Return all directories under base_dir that contain a SKILL.md file."""
    skill_dirs = []
    base_path = Path(base_dir)
    if not base_path.exists():
        return skill_dirs
    for p in base_path.rglob("SKILL.md"):
        skill_dirs.append(p.parent)
    return skill_dirs

def validate_skill(skill_dir):
    """Validate a single skill directory."""
    errors = []
    warnings = []
    
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        return [f"SKILL.md does not exist in {skill_dir}"], []

    # 1. Read file and check lines
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read SKILL.md: {e}"], []

    lines = content.splitlines()
    line_count = len(lines)
    if line_count > 800:
        errors.append(f"SKILL.md exceeds line limit (has {line_count} lines, maximum allowed is 800)")

    # 2. Parse frontmatter
    # Frontmatter is expected to be enclosed in --- at the very start of the file
    if not content.startswith("---"):
        errors.append("SKILL.md does not start with YAML frontmatter delimiter '---'")
        return errors, warnings

    parts = content.split("---", 2)
    if len(parts) < 3:
        errors.append("SKILL.md has mismatched or missing YAML frontmatter delimiters")
        return errors, warnings

    frontmatter_text = parts[1]
    body_text = parts[2]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except Exception as e:
        errors.append(f"Failed to parse YAML frontmatter: {e}")
        return errors, warnings

    if not isinstance(frontmatter, dict):
        errors.append("YAML frontmatter is not a dictionary/object")
        return errors, warnings

    # 3. Check name and description fields
    if "name" not in frontmatter or not frontmatter["name"]:
        errors.append("YAML frontmatter is missing the 'name' field")
    
    if "description" not in frontmatter or not frontmatter["description"]:
        errors.append("YAML frontmatter is missing the 'description' field")
    else:
        desc = str(frontmatter["description"])
        if len(desc) > 1024:
            errors.append(f"Description field exceeds limit ({len(desc)} characters, max allowed is 1024)")

    # 4. Orphan detection
    # Find all files in the skill directory recursively (excluding SKILL.md, and hidden files)
    all_files = []
    for root, dirs, files in os.walk(skill_dir):
        # Skip hidden directories like .git
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.startswith("."):
                continue
            full_path = Path(root) / file
            rel_path = full_path.relative_to(skill_dir)
            if rel_path == Path("SKILL.md"):
                continue
            all_files.append(rel_path)

    if all_files:
        # Collect all text content from all markdown files in the skill folder
        # to search for references to other files.
        md_contents = []
        for root, dirs, files in os.walk(skill_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                if file.endswith(".md"):
                    try:
                        md_contents.append((Path(root) / file).read_text(encoding="utf-8"))
                    except Exception:
                        pass
        
        combined_md_content = "\n".join(md_contents)

        for rel_file in all_files:
            file_str = str(rel_file)
            file_name = rel_file.name
            
            # Check if the filename or its string representation is referenced in the markdown content.
            # We look for:
            # 1. Exact relative path: e.g. path/to/file.md
            # 2. Filename: e.g. file.md
            # We match if either is found in the text.
            is_referenced = (file_str in combined_md_content) or (file_name in combined_md_content)
            
            if not is_referenced:
                is_in_root = len(rel_file.parts) == 1
                is_md_or_media = rel_file.suffix.lower() in (".md", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")
                msg = f"Orphaned asset detected: '{file_str}' is not referenced in any markdown file in the skill folder"
                if is_in_root and is_md_or_media:
                    errors.append(msg)
                else:
                    warnings.append(msg)

    return errors, warnings

def main():
    base_dir = ".agents/skills"
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]

    skill_dirs = get_skill_dirs(base_dir)
    if not skill_dirs:
        print(f"No skills found in {base_dir}")
        sys.exit(0)

    print(f"Validating {len(skill_dirs)} skills under {base_dir}...")
    total_errors = 0
    total_warnings = 0

    for skill_dir in sorted(skill_dirs):
        errors, warnings = validate_skill(skill_dir)
        skill_name = skill_dir.name
        
        if errors or warnings:
            print(f"\n[{skill_name}] ({skill_dir})")
            for err in errors:
                print(f"  ❌ ERROR: {err}")
                total_errors += 1
            for warn in warnings:
                print(f"  ⚠️  WARNING: {warn}")
                total_warnings += 1

    print("\n--- Validation Summary ---")
    print(f"Skills scanned: {len(skill_dirs)}")
    print(f"Total Errors: {total_errors}")
    print(f"Total Warnings: {total_warnings}")

    if total_errors > 0:
        print("\n❌ Skill validation FAILED.")
        sys.exit(1)
    else:
        print("\n✅ Skill validation PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    main()
