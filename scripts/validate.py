#!/usr/bin/env python3
"""Gaia Skill Registry — Canonical Graph Validator.

Validates registry/gaia.json against:
1. JSON Schema validation for all skill nodes and edges.
2. Unique skill IDs and edge declarations.
3. DAG cycle detection (DFS from all root nodes).
4. Reference integrity (every parent ID resolves to an existing node).
5. Prerequisite minimums by skill type.
6. Named skill evidence floors (inherited generic + own evidence; non-blocking).
7. Ultimate approval count check (placeholder).
8. Unique skill constraints.
9. Named skill frontmatter consistency.
10. Skill suites validation.

Generic skill refs are rank-less — stars live only on named skills — so there is
no generic level/demerit validation.

Usage:
    python scripts/validate.py [--graph PATH]

Exit codes:
    0 — All checks passed.
    1 — One or more validation errors.
"""

import json
import sys
import os
import glob
import argparse

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from collections import defaultdict

# Optional: jsonschema for full schema validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def _load_meta():
    """Load registry/schema/meta.json relative to this script's location."""
    meta_path = os.path.join(os.path.dirname(__file__), "..", "registry", "schema", "meta.json")
    meta_path = os.path.normpath(meta_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


_META = _load_meta()
EVIDENCE_FLOOR = {k: set(v) if v else None for k, v in _META["levels"]["evidenceFloors"].items()}
MIN_PREREQS = _META["types"]["minPrereqs"]
DEMERIT_IDS = set(_META.get("demerits", {}).get("order", []))
DEMERIT_ELIGIBLE_LEVELS = set(_META.get("demerits", {}).get("eligibleLevels", []))


def load_graph(path):
    """Load and parse the canonical graph JSON (or aggregate from a directory)."""
    if os.path.isdir(path):
        skills = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".json"):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        skills.append(json.load(f))

        # Load meta.json
        meta_path = os.path.join(os.path.dirname(path), "schema", "meta.json")
        if not os.path.exists(meta_path):
            meta_path = os.path.join(os.path.dirname(__file__), "..", "registry", "schema", "meta.json")

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Virtual edges for validation
        edges = []
        for skill in skills:
            target_id = skill["id"]
            for source_id in skill.get("prerequisites", []):
                edges.append({
                    "sourceSkillId": source_id,
                    "targetSkillId": target_id,
                    "edgeType": "prerequisite"
                })

        return {
            "version": "source-modular",
            "meta": meta,
            "skills": skills,
            "edges": edges
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(schema_path):
    """Load a JSON Schema file."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_schema(graph, schema_dir):
    """Validate all skill nodes against skill.schema.json."""
    errors = []
    if not HAS_JSONSCHEMA:
        print("⚠  jsonschema not installed — skipping schema validation.")
        print("   Install with: pip install jsonschema")
        return errors

    skill_schema = load_schema(os.path.join(schema_dir, "skill.schema.json"))
    combo_schema = load_schema(os.path.join(schema_dir, "combination.schema.json"))

    for skill in graph.get("skills", []):
        try:
            jsonschema.validate(instance=skill, schema=skill_schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema error in skill '{skill.get('id', '?')}': {e.message}")

    for edge in graph.get("edges", []):
        try:
            jsonschema.validate(instance=edge, schema=combo_schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema error in edge '{edge.get('sourceSkillId', '?')}->{edge.get('targetSkillId', '?')}': {e.message}")

    return errors


def validate_unique_ids(graph):
    """Check that skill IDs and edges are unique within the graph."""
    errors = []

    seen_skill_ids = set()
    duplicate_skill_ids = set()
    for skill in graph.get("skills", []):
        skill_id = skill.get("id")
        if skill_id in seen_skill_ids:
            duplicate_skill_ids.add(skill_id)
        seen_skill_ids.add(skill_id)

    for skill_id in sorted(duplicate_skill_ids):
        errors.append(f"Duplicate skill id '{skill_id}' found in skills.")

    seen_edges = set()
    duplicate_edges = set()
    for edge in graph.get("edges", []):
        edge_key = (
            edge.get("sourceSkillId"),
            edge.get("targetSkillId"),
            edge.get("edgeType", "prerequisite"),
        )
        if edge_key in seen_edges:
            duplicate_edges.add(edge_key)
        seen_edges.add(edge_key)

    for source, target, edge_type in sorted(duplicate_edges):
        errors.append(
            f"Duplicate edge '{source}->{target}' with edgeType '{edge_type}' found in edges."
        )

    return errors


def validate_dag(graph):
    """Check for cycles using DFS. Returns list of errors."""
    errors = []
    skill_ids = {s["id"] for s in graph.get("skills", [])}

    # Build adjacency list (parent -> children)
    children = defaultdict(list)
    for edge in graph.get("edges", []):
        children[edge["sourceSkillId"]].append(edge["targetSkillId"])

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in skill_ids}

    def dfs(node, path):
        color[node] = GRAY
        for child in children.get(node, []):
            if child not in color:
                continue  # reference integrity catches this
            if color[child] == GRAY:
                cycle_path = path + [node, child]
                errors.append(f"Cycle detected: {' -> '.join(cycle_path)}")
                return
            if color[child] == WHITE:
                dfs(child, path + [node])
        color[node] = BLACK

    for sid in skill_ids:
        if color[sid] == WHITE:
            dfs(sid, [])

    return errors


def validate_references(graph):
    """Check that all prerequisite and derivative IDs resolve to existing nodes."""
    errors = []
    skill_ids = {s["id"] for s in graph.get("skills", [])}

    for skill in graph.get("skills", []):
        for prereq in skill.get("prerequisites", []):
            if prereq not in skill_ids:
                errors.append(f"Skill '{skill['id']}' references missing prerequisite '{prereq}'.")
        for deriv in skill.get("derivatives", []):
            if deriv not in skill_ids:
                errors.append(f"Skill '{skill['id']}' references missing derivative '{deriv}'.")

    for edge in graph.get("edges", []):
        if edge["sourceSkillId"] not in skill_ids:
            errors.append(f"Edge references missing source skill '{edge['sourceSkillId']}'.")
        if edge["targetSkillId"] not in skill_ids:
            errors.append(f"Edge references missing target skill '{edge['targetSkillId']}'.")

    return errors


def validate_prerequisites_count(graph):
    """Check that each skill type has the minimum required number of prerequisites."""
    errors = []
    for skill in graph.get("skills", []):
        min_req = MIN_PREREQS.get(skill["type"], 0)
        actual = len(skill.get("prerequisites", []))
        if skill["type"] == "basic" and actual > 0:
            errors.append(f"Basic skill '{skill['id']}' must have 0 prerequisites (has {actual}).")
        elif skill["type"] == "unique" and actual > 0:
            errors.append(f"Unique skill '{skill['id']}' must have 0 prerequisites (has {actual}).")
        elif actual < min_req:
            errors.append(f"{skill['type'].title()} skill '{skill['id']}' needs ≥{min_req} prerequisites (has {actual}).")
    return errors


def validate_named_evidence(graph, named_dir=None):
    """Check named skills meet the evidence floor for their level.

    Generic skill refs are rank-less and hold capability-level (inherited)
    evidence. A named skill's effective evidence pool is its own evidence plus
    the evidence on the generic skill it points at via ``genericSkillRef``.
    """
    errors = []
    if named_dir is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        named_dir = os.path.join(repo_root, "registry", "named")
    if not os.path.isdir(named_dir):
        return errors

    generic_evidence = {s["id"]: (s.get("evidence") or []) for s in graph.get("skills", [])}

    for fp in sorted(glob.glob(os.path.join(named_dir, "**", "*.md"), recursive=True)):
        if fp.endswith("index.json"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                fm = _parse_named_frontmatter(f.read())
        except (OSError, ValueError):
            continue  # parse errors surfaced by validate_named_skills
        level = fm.get("level", "")
        required_classes = EVIDENCE_FLOOR.get(level)
        if required_classes is None:
            continue  # no floor below 2★ / unknown level handled elsewhere

        pool = list(fm.get("evidence") or [])
        pool += generic_evidence.get(fm.get("genericSkillRef", ""), [])
        has_qualifying = any(e.get("class") in required_classes for e in pool)
        if not has_qualifying:
            rel = os.path.relpath(fp)
            errors.append(
                f"Named skill {rel} at Level {level} needs evidence class "
                f"{sorted(required_classes)} (own or inherited) but pool has: "
                f"{[e.get('class') for e in pool]}."
            )
    return errors


def validate_ultimate(graph):
    """Check ultimate-specific constraints."""
    errors = []
    for skill in graph.get("skills", []):
        if skill["type"] != "ultimate":
            continue

        # Provisional ultimate stubs are allowed without evidence
        if skill["status"] == "provisional":
            continue

        # Validated ultimates need 3+ Class A/B evidence
        if skill["status"] == "validated":
            ab_evidence = [e for e in skill.get("evidence", []) if e.get("class") in ("A", "B")]
            if len(ab_evidence) < 3:
                errors.append(
                    f"Validated ultimate '{skill['id']}' needs ≥3 Class A/B evidence "
                    f"sources (has {len(ab_evidence)})."
                )
    return errors


def validate_unique_skills(graph):
    """Check unique-type-specific constraints: 0 prerequisites, graph-isolated, has named impl.

    (Generic refs are rank-less; the star comes from the named implementation,
    so there is no generic-level floor to check here anymore.)
    """
    errors = []
    all_prereq_refs = set()
    for skill in graph.get("skills", []):
        for pid in skill.get("prerequisites", []):
            all_prereq_refs.add(pid)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    named_index_path = os.path.join(repo_root, "registry", "named-skills.json")
    named_buckets = {}
    if os.path.isfile(named_index_path):
        with open(named_index_path, "r", encoding="utf-8") as f:
            named_buckets = json.load(f).get("buckets", {})

    for skill in graph.get("skills", []):
        if skill["type"] != "unique":
            continue

        if skill.get("prerequisites", []):
            errors.append(
                f"Unique skill '{skill['id']}' must have 0 prerequisites "
                f"(has {len(skill['prerequisites'])})."
            )

        if skill["id"] in all_prereq_refs:
            errors.append(
                f"Unique skill '{skill['id']}' is referenced as a prerequisite "
                f"by another skill — unique skills must be graph-isolated."
            )

        if skill["id"] not in named_buckets or not named_buckets[skill["id"]]:
            errors.append(
                f"Unique skill '{skill['id']}' has no named implementation — "
                f"unique skills require at least one entry in named-skills.json."
            )

    return errors


def compute_stats(graph):
    """Compute and print summary statistics."""
    skills = graph.get("skills", [])
    by_type = defaultdict(int)
    by_rarity = defaultdict(int)
    by_status = defaultdict(int)

    for s in skills:
        by_type[s["type"]] += 1
        by_rarity[s["rarity"]] += 1
        by_status[s["status"]] += 1

    # Compute max lineage depth
    children = defaultdict(list)
    parents = defaultdict(list)
    for edge in graph.get("edges", []):
        children[edge["sourceSkillId"]].append(edge["targetSkillId"])
        parents[edge["targetSkillId"]].append(edge["sourceSkillId"])

    skill_ids = {s["id"] for s in skills}
    roots = [sid for sid in skill_ids if not parents.get(sid)]

    max_depth = 0
    def depth_dfs(node, d):
        nonlocal max_depth
        max_depth = max(max_depth, d)
        for child in children.get(node, []):
            depth_dfs(child, d + 1)

    for root in roots:
        depth_dfs(root, 0)

    # Find orphaned composites
    orphaned = []
    for s in skills:
        if s["type"] in ("extra", "ultimate") and len(s.get("prerequisites", [])) < 2:
            orphaned.append(s["id"])

    print("\n📊 Graph Statistics")
    print(f"   Total skills: {len(skills)}")
    print(f"   By type: {dict(by_type)}")
    print(f"   By rarity: {dict(by_rarity)}")
    print(f"   By status: {dict(by_status)}")
    print(f"   Total edges: {len(graph.get('edges', []))}")
    print(f"   Max lineage depth: {max_depth}")
    print(f"   Root nodes (basics): {len(roots)}")
    if orphaned:
        print(f"   ⚠ Orphaned extras: {orphaned}")


_NAMED_REQUIRED_FIELDS = [
    "id",
    "name",
    "contributor",
    "origin",
    "genericSkillRef",
    "status",
    "level",
    "description",
]

_NAMED_VALID_LEVELS = {"1★", "2★", "3★", "4★", "5★", "6★"}


def _parse_named_frontmatter(text):
    """Parse YAML frontmatter from a named skill markdown file.

    Returns a dict of the frontmatter fields, or raises ValueError on malformed
    input. Uses a real YAML parser so block sequences of mappings (e.g. the
    ``evidence:`` list-of-dicts) round-trip correctly.
    """
    import yaml

    if not text.startswith("---"):
        raise ValueError("File does not begin with '---' frontmatter delimiter.")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Frontmatter closing '---' not found.")
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}")
    if not isinstance(data, dict):
        raise ValueError("Frontmatter is not a mapping.")
    return data


def validate_named_skills(graph, named_dir=None, catalog_path=None):
    """Validate all named skill .md files in registry/named/.

    Checks:
      - All required fields are present.
      - level is 2★ or above.
      - genericSkillRef resolves to a skill ID in graph (gaia.json).
      - At most one origin: true per genericSkillRef bucket.
      - status 'named' requires title OR catalogRef (reviewer gate).
      - title/catalogRef requires status 'named' (prevents contributor bypassing).
      - catalogRef (if set) resolves to an item id in real_skill_catalog.json.

    Returns a list of error strings.
    """
    errors = []

    if named_dir is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        named_dir = os.path.join(repo_root, "registry", "named")

    if catalog_path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        catalog_path = os.path.join(repo_root, "registry", "real-skills.json")

    if not os.path.isdir(named_dir):
        # Not an error — directory simply doesn't exist yet.
        return errors

    # Load catalog item IDs for catalogRef resolution check
    catalog_ids = set()
    if os.path.isfile(catalog_path):
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog_data = json.load(f)
            catalog_ids = {item["id"] for item in catalog_data.get("items", []) if "id" in item}
        except (OSError, json.JSONDecodeError):
            pass  # Catalog missing or malformed — skip resolution checks

    valid_ids = {s["id"] for s in graph.get("skills", [])}

    pattern = os.path.join(named_dir, "**", "*.md")
    md_files = sorted(glob.glob(pattern, recursive=True))
    # Exclude any generated index file that might be .md (unlikely but safe)
    md_files = [f for f in md_files if not f.endswith("index.json")]

    buckets = defaultdict(list)  # genericSkillRef -> list of parsed fm dicts

    for fp in md_files:
        rel = os.path.relpath(fp)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            fm = _parse_named_frontmatter(text)
        except (OSError, ValueError) as exc:
            errors.append(f"Named skill {rel}: cannot parse — {exc}")
            continue

        # Required fields
        missing = [field for field in _NAMED_REQUIRED_FIELDS
                   if field not in fm or fm[field] is None or fm[field] == ""]
        if missing:
            errors.append(
                f"Named skill {rel}: missing required field(s): {', '.join(missing)}"
            )

        # Level >= 1★ (1★ = Awakened hard-demote penalty per META §2.4)
        level = fm.get("level", "")
        if level not in _NAMED_VALID_LEVELS:
            errors.append(
                f"Named skill {rel}: 'level' must be 1★ or above (got '{level}')."
            )

        # genericSkillRef resolves
        ref = fm.get("genericSkillRef", "")
        if ref and ref not in valid_ids:
            errors.append(
                f"Named skill {rel}: 'genericSkillRef' value '{ref}' "
                f"does not match any skill ID in gaia.json."
            )

        # Reviewer gate: status 'named' requires title OR catalogRef
        status = fm.get("status", "")
        has_title = bool(fm.get("title", "").strip() if isinstance(fm.get("title"), str) else fm.get("title"))
        has_catalog_ref = bool(fm.get("catalogRef", "").strip() if isinstance(fm.get("catalogRef"), str) else fm.get("catalogRef"))
        if status == "named" and not has_title and not has_catalog_ref:
            errors.append(
                f"Named skill {rel}: status 'named' requires a reviewer-assigned "
                f"'title' or 'catalogRef'. Submit with status: awakened first."
            )
        # Inverse: title/catalogRef are only valid on named status
        if (has_title or has_catalog_ref) and status != "named":
            errors.append(
                f"Named skill {rel}: 'title' and 'catalogRef' are only valid on "
                f"status: named skills (got '{status}'). These fields are reviewer-only."
            )
        # catalogRef must resolve to a known catalog item
        catalog_ref = fm.get("catalogRef", "")
        if catalog_ref and catalog_ids and catalog_ref not in catalog_ids:
            errors.append(
                f"Named skill {rel}: 'catalogRef' value '{catalog_ref}' does not "
                f"match any item id in real_skill_catalog.json."
            )

        # links.github URL casing check
        links = fm.get("links")
        if isinstance(links, dict):
            github_url = links.get("github")
            if isinstance(github_url, str):
                url_lower = github_url.lower()
                if url_lower.endswith("/skill.md") and not github_url.endswith("/SKILL.md"):
                    errors.append(
                        f"Named skill {rel}: 'links.github' URL '{github_url}' "
                        f"has invalid casing. Project convention requires uppercase 'SKILL.md'."
                    )

        if not missing and level in _NAMED_VALID_LEVELS:
            buckets[ref].append(fm)

    # Origin uniqueness per bucket
    for ref, entries in buckets.items():
        origins = [e for e in entries if e.get("origin") is True]
        if len(origins) > 1:
            ids = [e.get("id", "?") for e in origins]
            errors.append(
                f"Named skills: genericSkillRef '{ref}' has more than one "
                f"origin:true — {ids}"
            )

    return errors


def validate_suites(graph, suites_dir=None, named_dir=None, schema_dir=None):
    """Validate all skill suite JSON files in registry/suites/.

    Checks:
      - Valid JSON syntax.
      - Conformance to registry/schema/skillSuite.schema.json (using jsonschema).
      - Suite ID exists in the named skills list.
      - Capstone ID matches the suite ID.
      - Every listed named skill in members, fusion, and standalones exists in the registry.
      - No duplicate named skill references within the suite.

    Returns a list of error strings.
    """
    errors = []
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if suites_dir is None:
        suites_dir = os.path.normpath(os.path.join(repo_root, "registry", "suites"))
    if named_dir is None:
        named_dir = os.path.normpath(os.path.join(repo_root, "registry", "named"))
    if schema_dir is None:
        schema_dir = os.path.normpath(os.path.join(repo_root, "registry", "schema"))

    if not os.path.isdir(suites_dir):
        return errors

    # Load named skill IDs to check reference integrity
    named_ids = set()
    pattern = os.path.join(named_dir, "**", "*.md")
    md_files = glob.glob(pattern, recursive=True)
    for fp in md_files:
        if fp.endswith("index.json"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            fm = _parse_named_frontmatter(text)
            skill_id = fm.get("id")
            if skill_id:
                named_ids.add(skill_id)
        except Exception:
            pass

    # Load skillSuite schema if jsonschema is available
    suite_schema = None
    if HAS_JSONSCHEMA:
        suite_schema_path = os.path.join(schema_dir, "skillSuite.schema.json")
        if os.path.isfile(suite_schema_path):
            with open(suite_schema_path, "r", encoding="utf-8") as f:
                suite_schema = json.load(f)

    suite_pattern = os.path.join(suites_dir, "**", "*.json")
    suite_files = sorted(glob.glob(suite_pattern, recursive=True))

    for fp in suite_files:
        rel = os.path.relpath(fp)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            errors.append(f"Suite file {rel}: cannot parse JSON — {exc}")
            continue

        if suite_schema:
            try:
                jsonschema.validate(instance=data, schema=suite_schema)
            except jsonschema.ValidationError as exc:
                errors.append(f"Suite file {rel}: schema error — {exc.message}")
                continue

        suite_id = data.get("id")
        capstone = data.get("capstone")

        if suite_id not in named_ids:
            errors.append(f"Suite file {rel}: suite ID '{suite_id}' does not match any existing named skill ID in registry/named/")

        if capstone != suite_id:
            errors.append(f"Suite file {rel}: 'capstone' ('{capstone}') must match the suite 'id' ('{suite_id}')")

        # Track all constituents in the suite to check existence and uniqueness
        constituents = []
        for suite_obj in data.get("suites", []):
            members = suite_obj.get("members", [])
            for m in members:
                constituents.append((m, f"suites[{suite_obj.get('id', '')}].members"))
            fusion = suite_obj.get("fusion")
            if fusion:
                constituents.append((fusion, f"suites[{suite_obj.get('id', '')}].fusion"))

        standalones = data.get("standalones", [])
        for s in standalones:
            constituents.append((s, "standalones"))

        seen_constituents = set()
        for skill_id, source in constituents:
            if skill_id not in named_ids:
                errors.append(f"Suite file {rel}: referenced named skill '{skill_id}' in '{source}' does not exist in registry/named/")
            if skill_id in seen_constituents:
                errors.append(f"Suite file {rel}: duplicate named skill reference '{skill_id}' in '{source}'")
            seen_constituents.add(skill_id)

    return errors


def check_meta_sync():
    """Verify meta.json is in sync with gaia.json and bundled copies."""
    import filecmp

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meta_path = os.path.join(repo_root, "registry", "schema", "meta.json")
    gaia_path = os.path.join(repo_root, "registry", "gaia.json")

    errors = []

    # Load meta.json
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Load gaia.json
    with open(gaia_path, "r", encoding="utf-8") as f:
        gaia = json.load(f)

    gaia_meta = gaia.get("meta", {})

    # Check levelLabels match
    meta_level_labels = meta.get("levels", {}).get("labels", {})
    gaia_level_labels = gaia_meta.get("levelLabels", {})
    for key, value in gaia_level_labels.items():
        if key not in meta_level_labels:
            errors.append(f"gaia.json meta.levelLabels has key '{key}' not in meta.json levels.labels")
        elif meta_level_labels[key] != value:
            errors.append(
                f"levelLabels mismatch for '{key}': gaia.json has '{value}', "
                f"meta.json has '{meta_level_labels[key]}'"
            )

    # Check typeLabels match (gaia.json may be a subset)
    meta_type_labels = meta.get("types", {}).get("labels", {})
    gaia_type_labels = gaia_meta.get("typeLabels", {})
    for key, value in gaia_type_labels.items():
        if key not in meta_type_labels:
            errors.append(f"gaia.json meta.typeLabels has key '{key}' not in meta.json types.labels")
        elif meta_type_labels[key] != value:
            errors.append(
                f"typeLabels mismatch for '{key}': gaia.json has '{value}', "
                f"meta.json has '{meta_type_labels[key]}'"
            )

    # Check demeritLabels match (gaia.json may be a subset)
    meta_demerit_labels = meta.get("demerits", {}).get("labels", {})
    gaia_demerit_labels = gaia_meta.get("demeritLabels", {})
    for key, value in gaia_demerit_labels.items():
        if key not in meta_demerit_labels:
            errors.append(f"gaia.json meta.demeritLabels has key '{key}' not in meta.json demerits.labels")
        elif meta_demerit_labels[key] != value:
            errors.append(
                f"demeritLabels mismatch for '{key}': gaia.json has '{value}', "
                f"meta.json has '{meta_demerit_labels[key]}'"
            )

    # Check bundled schema copies match canonical
    bundled_dir = os.path.join(repo_root, "src", "gaia_cli", "data", "registry", "schema")
    canonical_dir = os.path.join(repo_root, "registry", "schema")
    if os.path.isdir(bundled_dir):
        for fname in os.listdir(bundled_dir):
            bundled_file = os.path.join(bundled_dir, fname)
            canonical_file = os.path.join(canonical_dir, fname)
            if not os.path.isfile(bundled_file):
                continue
            if not os.path.isfile(canonical_file):
                errors.append(f"Bundled file '{fname}' has no canonical counterpart in registry/schema/")
            elif not filecmp.cmp(bundled_file, canonical_file, shallow=False):
                errors.append(f"Bundled file '{fname}' differs from canonical registry/schema/{fname}")

    if errors:
        print(f"❌ Meta sync check failed with {len(errors)} error(s):")
        for i, err in enumerate(errors, 1):
            print(f"   {i}. {err}")
        sys.exit(1)
    else:
        print("✅ Meta sync check passed.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Validate the Gaia canonical graph.")
    parser.add_argument("--graph", default=None, help="Path to gaia.json")
    parser.add_argument("--schema-dir", default=None, help="Path to schema directory")
    parser.add_argument(
        "--check-meta-sync", action="store_true",
        help="Verify meta.json is in sync with gaia.json and bundled copies"
    )
    args = parser.parse_args()

    if args.check_meta_sync:
        check_meta_sync()
        return

    # Resolve paths
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_dir = os.path.join(repo_root, "registry", "nodes")

    # Default to nodes_dir if it exists, otherwise gaia.json
    if not args.graph and os.path.isdir(nodes_dir):
        graph_path = nodes_dir
    else:
        graph_path = args.graph or os.path.join(repo_root, "registry", "gaia.json")

    schema_dir = args.schema_dir or os.path.join(repo_root, "registry", "schema")

    if not os.path.exists(graph_path):
        print(f"❌ Graph file not found: {graph_path}")
        sys.exit(1)

    print(f"🔍 Validating: {graph_path}")
    graph = load_graph(graph_path)

    all_errors = []

    # 1. Schema validation
    print("   [1/10] Schema validation...")
    all_errors.extend(validate_schema(graph, schema_dir))

    # 2. Unique identifiers
    print("   [2/10] Unique identifiers...")
    all_errors.extend(validate_unique_ids(graph))

    # 3. DAG cycle detection
    print("   [3/10] DAG cycle detection...")
    all_errors.extend(validate_dag(graph))

    # 4. Reference integrity
    print("   [4/10] Reference integrity...")
    all_errors.extend(validate_references(graph))

    # 5. Prerequisite count
    print("   [5/10] Prerequisite count...")
    all_errors.extend(validate_prerequisites_count(graph))

    # 6. Named skill evidence floors (inherited generic + own evidence).
    #    Non-blocking for now: generic refs are rank-less and the per-named
    #    evidence-floor enforcement is the next meta step. Surfaced as warnings.
    print("   [6/10] Named evidence thresholds (warn)...")
    evidence_warnings = validate_named_evidence(graph)

    # 7. Ultimate constraints
    print("   [7/10] Ultimate constraints...")
    all_errors.extend(validate_ultimate(graph))

    # 8. Unique skill constraints
    print("   [8/10] Unique skill constraints...")
    all_errors.extend(validate_unique_skills(graph))

    # 9. Named skills validation (includes reviewer gate + catalog cross-refs)
    print("   [9/10] Named skills validation...")
    all_errors.extend(validate_named_skills(graph))

    # 10. Skill suites validation
    print("   [10/10] Skill suites validation...")
    all_errors.extend(validate_suites(graph))

    # Stats
    compute_stats(graph)

    if evidence_warnings:
        print(f"\n⚠  {len(evidence_warnings)} named evidence warning(s) "
              f"(non-blocking — per-named evidence floors land in the next meta step):")
        for i, warn in enumerate(evidence_warnings, 1):
            print(f"   {i}. {warn}")

    if all_errors:
        print(f"\n❌ {len(all_errors)} validation error(s):")
        for i, err in enumerate(all_errors, 1):
            print(f"   {i}. {err}")
        sys.exit(1)
    else:
        print("\n✅ All validation checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
