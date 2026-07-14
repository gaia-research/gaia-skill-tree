#!/usr/bin/env python3
"""Gaia Skill Registry — Named Skill Index Generator.

Scans all registry/named/*/*.md files, parses YAML frontmatter, validates each
named skill, groups them by genericSkillRef, and writes registry/named-skills.json.

Validation rules:
  - Each named skill has all required fields.
  - genericSkillRef resolves to a skill ID in registry/gaia.json.
  - At most one origin: true per genericSkillRef bucket.
  - level is a valid star rating (1★–6★; 1★ indicates a demoted/uninstallable skill).

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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from gaia_cli.redaction import is_redacted, level_num  # noqa: E402  single source of truth

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
    "installable",
    "tags",
    "links",
    "evidence",
    "createdAt",
    "updatedAt",
    "timeline",
    "type",
    "suiteRef",
    "suiteComponents",
    # G7 trust fields — frontmatter values are canonical (written by the migration
    # with full named-skill-map context); the index propagates them as-is.
    # Including them here means _inject_trust_grades() reads them via fm_tm/fm_grade
    # and skips the recompute path, which without the context-dependent fix would
    # diverge for suite skills (e.g. gstack: frontmatter 589 → recompute 109).
    # See Issue #755.
    "trustMagnitude",
    "overallTrustGrade",
    "trustMagnitudeInputHash",
    "apexGateStatus",
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

        level = fm.get("level", "")
        if level not in VALID_LEVELS:
            errors.append(
                f"{rel}: 'level' must be one of {sorted(VALID_LEVELS)} (got '{level}')."
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

    # Per META § 1/4.1: Origin standing belongs to a *Named* (2★+) skill. A
    # pre-named/demoted (≤1★) entry cannot be Origin, so clear any author-
    # declared origin flag on such entries (this also stops a 1★ from being
    # picked as a bucket's champion and shown with the bucket's effective star).
    # Then order each bucket champion-first (rank desc, origin first, id) so
    # every consumer that takes the first/origin entry maps to a ranked skill.
    for ref, entries in buckets.items():
        for e in entries:
            if e.get("origin") and is_redacted(e.get("level", "")):
                e["origin"] = False
                e["role"] = "variant"
        entries.sort(key=lambda e: (
            -level_num(e.get("level", "")),
            0 if e.get("origin") else 1,
            e.get("id", ""),
        ))

    # Origin uniqueness per bucket (named only)
    for ref, entries in buckets.items():
        origins = [e for e in entries if e.get("origin") is True]
        if len(origins) > 1:
            origin_ids = [e.get("id", "?") for e in origins]
            errors.append(
                f"genericSkillRef '{ref}': more than one origin:true — {origin_ids}"
            )

    return errors, buckets, awaiting_classification, by_contributor


def _inject_trust_grades(buckets, generic_skills_map, gate_config):
    """Annotate each named-skill bucket entry with overallTrustGrade, trustMagnitude,
    and apexGateStatus.

    A named skill's *effective* evidence is its own implementation-specific
    evidence unioned with the capability evidence inherited from its generic
    ref (``inherited_evidence``).  The Overall Trust Grade is derived from that
    combined pool, so a child can match the inherited floor or exceed it with
    its own stronger (repo-specific) evidence.

    For ultimate-type entries, ``ultimateGateStatus`` is computed from a
    component lookup keyed by *named* skill id (``contributor/skill``) — the
    same ids that appear in ``suiteComponents`` — each resolving to that
    component's effective (inherited) evidence.  Generic ids remain resolvable
    too, so mixed suites still work.  Without this, named component ids miss the
    generic-keyed map and every suite reads "0/3".

    ``trustMagnitude`` (float) and ``apexGateStatus`` (dict of predicate ->
    True/False/None) are added alongside overallTrustGrade so the display layer
    (report.html, skill-explorer.js) can render TM cards without re-computing.

    Mutates entries in-place; no fields are stored in registry nodes.
    """
    from gaia_cli.grading import overall_trust_grade, check_ultimate_gate
    from gaia_cli.evidence import inherited_evidence
    from gaia_cli.trustMagnitude import computeTrustMagnitude, passesSuiteApexGate

    def _effective(entry):
        generic_node = generic_skills_map.get(entry.get("genericSkillRef"))
        return inherited_evidence(entry, generic_node)

    # Component lookup: start from generic nodes (own evidence, no parent), then
    # overlay every named skill keyed by its full id with its effective pool.
    component_lookup = dict(generic_skills_map)
    for _ref, entries in buckets.items():
        for entry in entries:
            component_lookup[entry["id"]] = {
                "id": entry["id"],
                "type": entry.get("type"),
                "evidence": _effective(entry),
                "suiteComponents": entry.get("suiteComponents"),
            }

    # Build a named-skill lookup for apex gate predicate resolution
    named_skill_map = {}
    for _ref, entries in buckets.items():
        for entry in entries:
            named_skill_map[entry["id"]] = entry

    for _ref, entries in buckets.items():
        for entry in entries:
            effective = _effective(entry)

            # Frontmatter values written by the migration are CANONICAL — they
            # are computed once with the full named-skill-map context, signed by
            # the trustMagnitudeInputHash, and reflect suite-fusion sqrt-softening
            # correctly. Only recompute when the frontmatter is missing or when the
            # input hash mismatches (i.e. the migration hasn't caught up to a
            # registry change yet). See Issue #755.
            fm_tm = entry.get("trustMagnitude")
            fm_grade = entry.get("overallTrustGrade")

            skill_with_effective = {**entry, "evidence": effective}
            if fm_tm is not None and fm_grade is not None:
                # Trust the frontmatter — propagate to index unchanged.
                entry["trustMagnitude"] = round(float(fm_tm), 2)
                entry["overallTrustGrade"] = fm_grade
            else:
                # Missing frontmatter values — recompute via G7 path.
                tm = computeTrustMagnitude(skill_with_effective, generic_skills_map)
                entry["trustMagnitude"] = round(tm, 2)
                grade = overall_trust_grade(
                    effective,
                    skill=skill_with_effective,
                    generic_skill_map=generic_skills_map,
                )
                if grade is not None:
                    entry["overallTrustGrade"] = grade

            # Compute apex gate predicate status for each named skill.
            registry_state = {
                "genericSkillMap": generic_skills_map,
                "namedSkillMap": named_skill_map,
            }
            apex_status = passesSuiteApexGate(skill_with_effective, registry_state)
            entry["apexGateStatus"] = apex_status

            if entry.get("type") == "ultimate":
                # Score the gate on effective evidence: components via the
                # named-id lookup, non-suite direct evidence via the entry's
                # own ∪ inherited pool.
                gate_skill = {**entry, "evidence": effective}
                gate = check_ultimate_gate(gate_skill, component_lookup, gate_config)
                entry["ultimateGateStatus"] = {
                    "passes": gate["passes"],
                    "reason": gate["reason"],
                }


def write_index(buckets, awaiting_classification, by_contributor, output_path, today,
                generic_skills_map=None, gate_config=None):
    """Write the named skill index JSON file."""
    if generic_skills_map is not None:
        _inject_trust_grades(buckets, generic_skills_map, gate_config or {})

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

    # Build generic skills map for trust grade injection
    generic_skills_map = {s["id"]: s for s in graph_data.get("skills", [])}

    # Load ultimate gate config from meta.json
    try:
        meta_path = os.path.join(repo_root, "registry", "schema", "meta.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            gate_config = json.load(f).get("evidence", {}).get("ultimateGate", {})
    except Exception:
        gate_config = {}

    write_index(buckets, awaiting_classification, by_contributor, output_path, today,
                generic_skills_map=generic_skills_map, gate_config=gate_config)
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
