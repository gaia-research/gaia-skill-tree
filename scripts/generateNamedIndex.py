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

VALID_LEVELS = {"2★", "3★", "4★", "5★", "6★"}

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
    "createdAt",
    "updatedAt",
    "timeline",
]


def role_for_entry(entry):
    """Return the display role for a named skill bucket entry."""
    return "origin" if entry.get("origin") is True else "variant"


def parse_frontmatter(text):
    """Parse YAML frontmatter from a markdown string.

    Returns (frontmatter_dict, body_str) or raises ValueError on malformed input.
    Supports scalar values, quoted strings, booleans, inline arrays, and one level
    of nested mappings (e.g. links:).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("File does not start with '---' frontmatter delimiter.")

    # Find closing ---
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("Frontmatter closing '---' not found.")

    fm_lines = lines[1:end]
    body = "\n".join(lines[end + 1:])
    data = {}
    current_key = None
    current_nested = None  # dict being built for a nested block

    def _parse_scalar(raw):
        """Convert a raw string value to bool/string."""
        stripped = raw.strip().strip('"').strip("'")
        if raw.strip().lower() == "true":
            return True
        if raw.strip().lower() == "false":
            return False
        return stripped

    def _parse_inline_array(raw):
        """Parse a YAML inline array like [a, b, c]."""
        inner = raw.strip()[1:-1]  # strip [ ]
        if not inner.strip():
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]

    for line in fm_lines:
        # Blank line in frontmatter
        if not line.strip():
            continue

        # Continuation of a block sequence (list under a key)
        if line.startswith("  - ") or line.startswith("    - "):
            item = line.strip()[2:].strip().strip('"').strip("'")
            if current_nested is not None:
                # This shouldn't normally happen in our schema, ignore gracefully
                pass
            elif current_key and isinstance(data.get(current_key), list):
                data[current_key].append(item)
            continue

        # Nested mapping continuation (2-space indent, key: value, no leading -)
        if (line.startswith("  ") and not line.startswith("  -")
                and ":" in line and current_nested is not None):
            sub_key, _, sub_val = line.strip().partition(":")
            current_nested[sub_key.strip()] = _parse_scalar(sub_val)
            continue

        # Flush nested block when we hit a top-level key
        if current_nested is not None:
            current_nested = None

        if ":" not in line:
            continue

        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest == "":
            # Could be a block sequence start or nested mapping start
            # We'll decide based on what follows; mark key as current
            current_key = key
            # Peek ahead handled by next iteration
            data[key] = None
            current_nested = None
            continue

        # Inline array
        if rest.startswith("["):
            data[key] = _parse_inline_array(rest)
            current_key = key
            current_nested = None
            continue

        # Regular scalar
        data[key] = _parse_scalar(rest)
        current_key = key
        current_nested = None

        # If value was empty string after stripping, treat as nested map start
        # (handles "links:" with no value on same line — already caught above)

    # Second pass: fix None values that should have been block sequences or nested maps.
    # Any key left as None and not overwritten gets an empty default.
    for k, v in list(data.items()):
        if v is None:
            data[k] = {}

    # Special handling: "tags" and "links" may still be None if lines came later.
    # Re-parse with awareness of nesting.
    data, _ = _parse_frontmatter_full(fm_lines)

    return data, body


def _parse_frontmatter_full(fm_lines):
    """Full two-pass parser handling nested maps and block sequences."""
    data = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        if not line.strip():
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue

        # Top-level key
        key, _, rest = line.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest == "":
            # Could be block sequence or nested mapping — look at next lines
            nested_dict = {}
            nested_list = []
            j = i + 1
            while j < len(fm_lines):
                nline = fm_lines[j]
                if not nline.strip():
                    j += 1
                    continue
                if not nline.startswith(" "):
                    break  # back to top-level
                stripped = nline.strip()
                if stripped.startswith("- "):
                    nested_list.append(stripped[2:].strip().strip('"').strip("'"))
                    j += 1
                elif ":" in stripped:
                    sub_key, _, sub_val = stripped.partition(":")
                    nested_dict[sub_key.strip()] = _coerce(sub_val.strip())
                    j += 1
                else:
                    j += 1
            if nested_list:
                data[key] = nested_list
                i = j
            elif nested_dict:
                data[key] = nested_dict
                i = j
            else:
                data[key] = {}
                i += 1
        elif rest.startswith("["):
            inner = rest.strip()[1:-1]
            if not inner.strip():
                data[key] = []
            else:
                data[key] = [item.strip().strip('"').strip("'") for item in inner.split(",")]
            i += 1
        else:
            data[key] = _coerce(rest)
            i += 1

    return data, ""


def _coerce(value):
    """Coerce a raw string to bool or string."""
    stripped = value.strip().strip('"').strip("'")
    if value.strip().lower() == "true":
        return True
    if value.strip().lower() == "false":
        return False
    return stripped


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


def validate_and_group(named_skills, valid_ids):
    """Validate all named skills and group by status and genericSkillRef.

    Returns (errors, buckets, awaiting_classification, by_contributor) where:
      - buckets: genericSkillRef -> list of skill dicts (status: named only)
      - awaiting_classification: list of skill dicts (status: awakened)
      - by_contributor: contributor -> list of skill id strings
    """
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
        skill_id = fm.get("id", "")
        if contributor and skill_id:
            if contributor not in by_contributor:
                by_contributor[contributor] = []
            by_contributor[contributor].append(skill_id)

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
    named_skills = [(fp, fm, body) for fp, fm, body in named_skills
                    if not fp.endswith("index.json")]

    print(f"Loading skill IDs from: {graph_path}")
    valid_ids = {s["id"] for s in graph_data.get("skills", [])}

    print(f"Found {len(named_skills)} named skill file(s). Validating...")
    errors, buckets, awaiting_classification, by_contributor = validate_and_group(named_skills, valid_ids)

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
