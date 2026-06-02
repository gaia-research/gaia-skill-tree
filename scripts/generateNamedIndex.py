#!/usr/bin/env python3
"""Gaia Skill Registry — Named Skill Index Generator.

Scans all registry/named/*/*.md files, parses YAML frontmatter, validates each
named skill, groups them by genericSkillRef, and writes registry/named-skills.json.

Validation rules:
  - Each named skill has all required fields.
  - genericSkillRef resolves to a skill ID in registry/gaia.json.
  - At most one origin: true per genericSkillRef bucket.
  - level is 2★ or above (not 1★).

Usage:
    python scripts/generateNamedIndex.py [--named-dir PATH] [--graph PATH]

Exit codes:
    0 — Index generated (with or without warnings).
    1 — Fatal validation errors (index not written).
"""

import json
import os
import sys
import glob
import argparse
import datetime

REQUIRED_FIELDS = [
    "id",
    "name",
    "contributor",
    "origin",
    "genericSkillRef",
    "status",
    "level",
    "description",
]

VALID_LEVELS = {"1★", "2★", "3★", "4★", "5★", "6★"}

def _extract_md_section(body, heading):
    """Extract the text content of a markdown ## section."""
    import re as _re
    m = _re.search(
        r'(?:^|\n)##\s+' + _re.escape(heading) + r'\s*\n(.*?)(?=\n##\s|\Z)',
        body, _re.DOTALL
    )
    return m.group(1) if m else ""


INDEX_SKILL_FIELDS = [
    "id",
    "name",
    "contributor",
    "origin",
    "genericSkillRef",
    "status",
    "level",
    "description",
    "title",
    "catalogRef",
    "tags",
    "links",
    "evidence",
    "createdAt",
    "updatedAt",
    "timeline",
    "type",
    "suiteRef",
    "suiteComponents",
]


def role_for_entry(entry):
    """Return the display role for a named skill bucket entry."""
    return "origin" if entry.get("origin") is True else "variant"


def parse_frontmatter(text):
    """Parse YAML frontmatter from a markdown string.

    Returns (frontmatter_dict, body_str) or raises ValueError on malformed input.
    Uses a real YAML parser so nested mappings and block sequences of mappings
    (e.g. the ``evidence:`` list-of-dicts) round-trip correctly.
    """
    import yaml

    if not text.startswith("---"):
        raise ValueError("File does not start with '---' frontmatter delimiter.")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Frontmatter closing '---' not found.")
    _, fm_text, body = parts
    try:
        data = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}")
    if not isinstance(data, dict):
        raise ValueError("Frontmatter is not a mapping.")
    return data, body.lstrip("\n")


def load_named_skills(named_dir):
    """Scan named_dir for *.md files and parse each one.

    Returns list of (filepath, frontmatter_dict) tuples.
    """
    pattern = os.path.join(named_dir, "**", "*.md")
    md_files = glob.glob(pattern, recursive=True)
    results = []
    for fp in sorted(md_files):
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read()
        try:
            fm, _ = parse_frontmatter(text)
            results.append((fp, fm))
        except ValueError as exc:
            results.append((fp, {"_parse_error": str(exc)}))
    return results


def load_gaia_skill_ids(graph_path):
    """Return the set of all skill IDs from gaia.json."""
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {s["id"] for s in data.get("skills", [])}


def load_suite_mappings(suites_dir):
    """Scan registry/suites/ for *.json files and map constituent skills to suite refs."""
    skill_to_suite = {}
    suite_to_components = {}

    if not os.path.isdir(suites_dir):
        return skill_to_suite, suite_to_components

    pattern = os.path.join(suites_dir, "**", "*.json")
    suite_files = glob.glob(pattern, recursive=True)

    for fp in sorted(suite_files):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            suite_id = data.get("id")
            capstone = data.get("capstone")
            if not suite_id:
                continue

            # Collect all constituents (members from all sub-suites + standalones)
            constituents = []
            for sub_suite in data.get("suites", []):
                members = sub_suite.get("members", [])
                constituents.extend(members)
                
                fusion = sub_suite.get("fusion")
                if fusion:
                    constituents.append(fusion)
                    # Map the fusion skill to its members
                    suite_to_components[fusion] = sorted(list(set(members)))
                    for m in members:
                        skill_to_suite[m] = fusion

            standalones = data.get("standalones", [])
            constituents.extend(standalones)

            # Deduplicate and sort constituents (excluding the capstone itself)
            constituents = sorted(list(set(constituents)))
            if capstone in constituents:
                constituents.remove(capstone)

            suite_to_components[suite_id] = constituents

            for skill in constituents:
                # Only map if not already mapped to a more specific sub-suite
                if skill not in skill_to_suite:
                    skill_to_suite[skill] = suite_id
        except Exception as exc:
            print(f"Warning: Failed to load suite file {fp}: {exc}")

    return skill_to_suite, suite_to_components


def _write_frontmatter_updates(filepath, updates):
    """Safely write updates back to the frontmatter of a markdown file, preserving custom layout/formatting."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return

    fm_block = parts[1]
    body = parts[2]

    lines = fm_block.splitlines()
    new_lines = []
    skip_list = False

    for line in lines:
        stripped = line.strip()

        if skip_list:
            if stripped.startswith("- ") or stripped.startswith("-") or stripped == "":
                continue
            else:
                skip_list = False

        matched_key = None
        for key in updates.keys():
            if stripped.startswith(f"{key}:") or stripped == f"{key}:":
                matched_key = key
                break

        if matched_key:
            rest = line.partition(":")[2].strip()
            if rest == "" or rest.startswith("["):
                skip_list = True
            continue

        new_lines.append(line)

    while new_lines and not new_lines[-1].strip():
        new_lines.pop()

    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, list):
            new_lines.append(f"{key}:")
            for item in value:
                new_lines.append(f"  - {item}")
        else:
            new_lines.append(f"{key}: \"{value}\"")

    new_fm_block = "\n".join(new_lines) + "\n"
    new_content = f"---{new_fm_block}---{body}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)


def update_markdown_files_with_suite_metadata(named_skills, skill_to_suite, suite_to_components):
    """Automatically update the frontmatter of named skill markdown files to sync suiteRef and suiteComponents."""
    for fp, fm in named_skills:
        if "_parse_error" in fm:
            continue

        skill_id = fm.get("id")
        if not skill_id:
            continue

        expected_suite_ref = skill_to_suite.get(skill_id)
        expected_suite_components = suite_to_components.get(skill_id)

        current_suite_ref = fm.get("suiteRef")
        current_suite_components = fm.get("suiteComponents")

        needs_update = False
        updates = {}

        if expected_suite_ref != current_suite_ref:
            needs_update = True
            updates["suiteRef"] = expected_suite_ref

        if expected_suite_components != current_suite_components:
            needs_update = True
            updates["suiteComponents"] = expected_suite_components

        if needs_update:
            print(f"  Syncing suite fields in {os.path.basename(fp)}")
            _write_frontmatter_updates(fp, updates)


def validate_and_group(named_skills, graph_data, skill_to_suite=None, suite_to_components=None):
    """Validate all named skills and group by status and genericSkillRef.

    Returns (errors, buckets, awaiting_classification, by_contributor) where:
      - buckets: genericSkillRef -> list of skill dicts (status: named only)
      - awaiting_classification: list of skill dicts (status: awakened)
      - by_contributor: contributor -> list of skill id strings
    """
    if skill_to_suite is None:
        skill_to_suite = {}
    if suite_to_components is None:
        suite_to_components = {}

    valid_ids = {s["id"] for s in graph_data.get("skills", [])}
    id_to_type = {s["id"]: s.get("type", "basic") for s in graph_data.get("skills", [])}

    errors = []
    buckets = {}  # genericSkillRef -> list of dicts (named only)
    awaiting_classification = []  # awakened skills waiting for reviewer action
    by_contributor = {}  # contributor -> [namedSkillId, ...]

    for fp, fm in named_skills:
        rel = os.path.relpath(fp)

        if "_parse_error" in fm:
            errors.append(f"{rel}: parse error — {fm['_parse_error']}")
            continue

        # Required fields
        missing = [f for f in REQUIRED_FIELDS if f not in fm or fm[f] is None or fm[f] == ""]
        if missing:
            errors.append(f"{rel}: missing required field(s): {', '.join(missing)}")

        # level >= 2★
        level = fm.get("level", "")
        if level not in VALID_LEVELS:
            errors.append(
                f"{rel}: 'level' must be 2★ or above (got '{level}'). "
                f"Valid values: {sorted(VALID_LEVELS)}"
            )

        # genericSkillRef resolves
        ref = fm.get("genericSkillRef", "")
        if ref and ref not in valid_ids:
            errors.append(
                f"{rel}: 'genericSkillRef' value '{ref}' does not match any skill "
                f"ID in gaia.json."
            )

        if missing or level not in VALID_LEVELS:
            continue  # don't add to buckets if fundamentally broken

        entry = {field: fm.get(field) for field in INDEX_SKILL_FIELDS}
        # Strip None values for optional fields to keep output clean
        entry = {k: v for k, v in entry.items() if v is not None}

        # Lookup type from generic skill if not explicitly in named skill
        if "type" not in entry and ref in id_to_type:
            entry["type"] = id_to_type[ref]

        # Dynamically inject suiteRef and suiteComponents based on loaded suite mappings
        skill_id = fm.get("id", "")
        if skill_id in skill_to_suite:
            entry["suiteRef"] = skill_to_suite[skill_id]
        if skill_id in suite_to_components:
            entry["suiteComponents"] = suite_to_components[skill_id]

        if os.path.isfile(fp):
            try:
                with open(fp, "r", encoding="utf-8") as _f:
                    _, body = parse_frontmatter(_f.read())
                install_section = _extract_md_section(body, "Installation")
                if install_section:
                    entry["installBody"] = install_section.strip()
            except (OSError, ValueError):
                pass

        # Route by status: named → buckets (real variants); awakened → awaiting
        status = fm.get("status", "awakened")
        if status == "named":
            entry["role"] = role_for_entry(entry)
            bucket_key = ref or "__unknown__"
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append(entry)
        else:
            awaiting_classification.append(entry)

        # Always track in byContributor index
        contributor = fm.get("contributor", "")
        skill_id_fm = fm.get("id", "")
        if contributor and skill_id_fm:
            if contributor not in by_contributor:
                by_contributor[contributor] = []
            by_contributor[contributor].append(skill_id_fm)

    # Origin uniqueness per bucket (named only)
    for ref, entries in buckets.items():
        origins = [e for e in entries if e.get("origin") is True]
        if len(origins) > 1:
            origin_ids = [e.get("id", "?") for e in origins]
            errors.append(
                f"genericSkillRef '{ref}': more than one origin:true — {origin_ids}"
            )

    return errors, buckets, awaiting_classification, by_contributor


def write_index(buckets, awaiting_classification, by_contributor, output_path, today):
    """Write the named skill index JSON file."""
    index = {
        "generatedAt": today,
        "buckets": buckets,
        "awaitingClassification": awaiting_classification,
        "byContributor": by_contributor,
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Generate registry/named-skills.json.")
    parser.add_argument("--named-dir", default=None, help="Path to registry/named/")
    parser.add_argument("--graph", default=None, help="Path to gaia.json")
    parser.add_argument("--out", default=None, help="Output path for index.json")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    named_dir = args.named_dir or os.path.join(repo_root, "registry", "named")
    graph_path = args.graph or os.path.join(repo_root, "registry", "gaia.json")
    output_path = args.out or os.path.join(repo_root, "registry", "named-skills.json")
    suites_dir = os.path.join(repo_root, "registry", "suites")

    if not os.path.isdir(named_dir):
        print(f"Named skills directory not found: {named_dir}")
        sys.exit(1)

    if not os.path.isfile(graph_path):
        print(f"Graph file not found: {graph_path}")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    graph_timestamp = graph_data.get("generatedAt", "")
    if graph_timestamp:
        today = graph_timestamp.split("T")[0] if "T" in graph_timestamp else graph_timestamp

    print(f"Scanning: {named_dir}")
    named_skills = load_named_skills(named_dir)
    # Filter out index.json if accidentally included
    named_skills = [(fp, fm) for fp, fm in named_skills
                    if not fp.endswith("index.json")]

    print(f"Loading skill IDs from: {graph_path}")
    valid_ids = {s["id"] for s in graph_data.get("skills", [])}

    print(f"Loading suite mappings from: {suites_dir}")
    skill_to_suite, suite_to_components = load_suite_mappings(suites_dir)

    print("Syncing named skill frontmatters with suite definitions...")
    update_markdown_files_with_suite_metadata(named_skills, skill_to_suite, suite_to_components)

    # Reload named skills to ensure validation and index reflect the newly synced files
    named_skills = load_named_skills(named_dir)
    named_skills = [(fp, fm) for fp, fm in named_skills
                    if not fp.endswith("index.json")]

    print(f"Found {len(named_skills)} named skill file(s). Validating...")
    errors, buckets, awaiting_classification, by_contributor = validate_and_group(
        named_skills, graph_data, skill_to_suite, suite_to_components
    )

    if errors:
        print(f"\n{len(errors)} validation error(s):")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)

    write_index(buckets, awaiting_classification, by_contributor, output_path, today)
    total_named = sum(len(v) for v in buckets.values())
    total_awaiting = len(awaiting_classification)
    print(f"\nWrote {output_path}")
    print(f"  Buckets (named): {len(buckets)}, Named skills: {total_named}")
    print(f"  Awaiting classification (awakened): {total_awaiting}")
    print(f"  Contributors: {len(by_contributor)}")
    for ref, entries in sorted(buckets.items()):
        origin_marker = next(
            (" [origin]" for e in entries if e.get("origin")), ""
        )
        print(f"  {ref}: {len(entries)} skill(s){origin_marker}")


if __name__ == "__main__":
    main()
