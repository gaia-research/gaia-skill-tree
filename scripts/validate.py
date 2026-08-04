#!/usr/bin/env python3
"""Gaia Skill Tree — Canonical Graph Validator.

Validates registry/gaia.json against:
1. JSON Schema validation for all skill nodes and edges.
2. Unique skill IDs and edge declarations.
3. DAG cycle detection (DFS from all root nodes).
4. Reference integrity (every parent ID resolves to an existing node).
5. Prerequisite minimums by skill type (meta.json types.minPrereqs).
6. Named skill frontmatter consistency.
7. Skill suites validation.
8. Benchmark source catalog validation (issue #1419).
9. Benchmark-result provenance gate (Sprint D W2a, #904).
10. Verifier benchmark attestation format & authorization (Sprint D W2b, #905).

Generic skill refs are rank-less — stars live only on named skills — so there is
no generic level/demerit validation.

Yggdrasil II (#997/#1002) retired THREE former steps from this pipeline, all of
which had become checks that could never fire:

  * "Named evidence thresholds" — the Evidence Floor, superseded by Trust
    Magnitude as the sole gate (#995 dropped levels.evidenceFloors).
  * "Ultimate constraints" and "Unique skill constraints" — both filtered on the
    retired `extra`/`unique`/`ultimate` skill TYPES. The type enum is now exactly
    {basic, fusion}, so both matched zero nodes post-migration and always
    returned clean while the pipeline still printed a step for them.

The latter two are deleted rather than re-targeted; the rationale for each is
recorded inline where they used to live (above
validate_verifier_benchmark_attestations). `Ultimate`, `Apex` and `Extra`
survive only as RANK WORDS on named skills, and Suite / Unique are read-time-
derived BRANCHES resolved TYPE-BLIND by src/gaia_cli/taxonomy.py — neither is
addressable from a canonical graph node.

Usage:
    python scripts/validate.py [--graph PATH] [--strict]

    --strict is auto-enabled on push-to-main and PR-into-main runs (via
    GITHUB_BASE_REF / GITHUB_REF); it turns pending-provenance benchmark rows
    into hard errors instead of warnings.

Exit codes:
    0 — All checks passed.
    1 — One or more validation errors.
"""

import json
import sys
import os
import glob
import argparse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

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
    """Check that each skill type meets its meta.json ``minPrereqs`` floor.

    Yggdrasil II collapsed the type axis to ``{basic, fusion}`` — basic = 0
    prerequisites, fusion = ≥1 (``meta.json types.minPrereqs``). The retired
    ``unique`` type had its own "must have 0 prerequisites" rule; that rule is
    gone with the type. ``unique`` is now a read-time-derived BRANCH (rank ≥4
    with no ``suiteComponents``), and a unique-branch named skill maps back to
    a ``fusion`` generic node that legitimately carries prerequisites.
    """
    errors = []
    for skill in graph.get("skills", []):
        min_req = MIN_PREREQS.get(skill["type"], 0)
        actual = len(skill.get("prerequisites", []))
        if skill["type"] == "basic" and actual > 0:
            errors.append(f"Basic skill '{skill['id']}' must have 0 prerequisites (has {actual}).")
        elif actual < min_req:
            errors.append(f"{skill['type'].title()} skill '{skill['id']}' needs ≥{min_req} prerequisites (has {actual}).")
    return errors


# ---------------------------------------------------------------------------
# RETIRED under Yggdrasil II (see module docstring):
#
#   validate_ultimate()      — filtered on `type == "ultimate"` and required
#       ≥3 Class A/B evidence rows on validated nodes. Both halves are retired:
#       (a) `ultimate` is no longer a type — it is the 5★ SUITE rank WORD, and
#           ranks live on named skills, never on canonical graph nodes
#           ("generic skill refs are rank-less"). No canonical node can be
#           identified as an ultimate, so the filter matched nothing.
#       (b) The Class-A/B COUNT floor it enforced was superseded by Trust
#           Magnitude. META.md §"Suite 5★ Ultimate pathway": "TM is the sole
#           numeric gate" (TM ≥ 250 / S-grade); #995 dropped
#           `levels.evidenceFloors` from meta.json for the same reason, and
#           `evidence.class` is marked DEPRECATED in skill.schema.json.
#       Re-targeting it at `type == "fusion"` would have imposed a brand-new
#       Class-A/B floor on all 130 fusion nodes — a constraint that was never
#       ratified and that contradicts the "TM is the sole numeric gate" ruling.
#
#   validate_unique_skills() — filtered on `type == "unique"` and required 0
#       prerequisites + graph isolation + a named implementation. `unique` is
#       no longer a type; it is a read-time-derived BRANCH (rank ≥4 AND no
#       `suiteComponents` — src/gaia_cli/taxonomy.py resolveDisplayBranch).
#       Neither input exists on a canonical node: `skill.schema.json` is
#       `additionalProperties: false` and defines neither `rank`/`level` nor
#       `suiteComponents` (suiteComponents lives on namedSkill.schema.json).
#       The branch is therefore unresolvable at this layer, and its old
#       constraints actively contradict Yggdrasil II — a unique-branch named
#       skill resolves back to a `fusion` node that has prerequisites and is
#       referenced by other nodes. "Has a named implementation" is likewise
#       tautological now: rank comes from `namedMaxLevel`, so rank ≥4 cannot
#       hold without one.
# ---------------------------------------------------------------------------


def validate_benchmark_source_catalog():
    """Validate registry/benchmark-sources.json against its schema and policy."""
    try:
        from gaia_cli.benchmarkCatalog import BenchmarkCatalogError, loadBenchmarkCatalog
    except Exception as exc:
        return [f"benchmark source catalog helper import failed: {exc}"]
    try:
        loadBenchmarkCatalog(_REPO_ROOT, validate=True)
    except BenchmarkCatalogError as exc:
        return [f"benchmark source catalog invalid: {exc}"]
    return []


def validate_verifier_benchmark_attestations():
    """Sprint D W2b (#905) — delegate to scripts/check_verifier_signoffs.py.

    Every file under docs/verifier-signoffs/YYYY-MM/*.md must have a
    well-formed YAML frontmatter block whose ``verifier`` handle resolves
    to a 4★+ named-skill contributor. Unauthorized or malformed
    attestations fail validation — and therefore fail CI — even if the
    PR otherwise has enough reviewer sign-offs.
    """
    try:
        import importlib.util
        script_path = _REPO_ROOT / "scripts" / "check_verifier_signoffs.py"
        if not script_path.exists():
            return []
        spec = importlib.util.spec_from_file_location("_gaia_signoffs", script_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover — defensive
        return [f"Could not load check_verifier_signoffs.py: {exc}"]

    signoffs_dir = _REPO_ROOT / "docs" / "verifier-signoffs"
    verifiers = module.loadVerifiers()
    known_skills = module.loadKnownSkills()
    return module.checkBenchmarkAttestations(signoffs_dir, verifiers, known_skills)


def validate_benchmark_provenance(graph, strict=False):
    """Benchmark-result provenance/lane gate (#1419).

    Reject self-attested rows always. Legacy ``pending`` rows are no-scoring;
    strict mode keeps the old main-merge protection unless a later verified-lane
    row exists for the same skill + benchmarkId. ``reported`` (and legacy
    ``mirrored``) rows are valid 1.0x benchmark evidence after human gate
    approval. ``rejected`` rows are audit history and score zero.

    Returns a list of error strings; the caller merges these into all_errors.
    Prints lane notices directly to stdout.
    """
    errors = []
    lane_notices = []
    skills = graph.get("skills", []) if isinstance(graph, dict) else graph
    for skill in skills:
        skill_id = skill.get("id", "<unknown>")
        evidence_list = skill.get("evidence") or []
        
        for idx, row in enumerate(evidence_list):
            if row.get("type") != "benchmark-result":
                continue
            provenance = row.get("provenance")
            if provenance == "self-attested":
                errors.append(
                    f"Skill '{skill_id}' evidence[{idx}] has provenance='self-attested' "
                    f"— FOREVER rejected for benchmark-result rows. Use verified, "
                    f"reported, or rejected (legacy aliases: ci-reproduced, "
                    f"verifier-attested, mirrored, pending)."
                )
            elif provenance == "pending":
                # Superseded-pending carve-out (Sprint D W2b #905): a pending row is
                # allowed on main if a later row for the same skill + benchmarkId exists
                # with provenance in ('ci-reproduced', 'verifier-attested').
                benchmark_id = row.get("benchmarkId")
                is_superseded = False
                if benchmark_id:
                    for later_row in evidence_list[idx+1:]:
                        if (later_row.get("type") == "benchmark-result" and
                            later_row.get("benchmarkId") == benchmark_id and
                            later_row.get("provenance") in ("verified", "ci-reproduced", "verifier-attested")):
                            is_superseded = True
                            break
                
                if not is_superseded:
                    message = (
                        f"Skill '{skill_id}' evidence[{idx}] has provenance='pending' "
                        f"— must be promoted to verified/reported or rejected "
                        f"before landing on main."
                    )
                    if strict:
                        errors.append(message)
                    else:
                        lane_notices.append("(pending) " + message)
            elif provenance == "rejected":
                lane_notices.append(
                    f"Skill '{skill_id}' evidence[{idx}] is rejected — no Trust Magnitude score."
                )
    if lane_notices:
        print(f"   ℹ  {len(lane_notices)} benchmark provenance notice(s):")
        for w in lane_notices:
            print(f"      - {w}")
    return errors


def compute_stats(graph):
    """Compute and print summary statistics."""
    skills = graph.get("skills", [])
    by_type = defaultdict(int)
    by_status = defaultdict(int)

    for s in skills:
        by_type[s["type"]] += 1
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

    # Find orphaned composites — a composite node that does not actually
    # compose anything. Yggdrasil II collapsed the composite types
    # (`extra`/`ultimate`) into `fusion`, so the old `type in ("extra",
    # "ultimate")` filter matched nothing. The threshold is read from
    # meta.json rather than hard-coded: the retired literal `2` was Ygg I's
    # `extra` floor, and Ygg II ratified `fusion: 1`.
    fusion_floor = MIN_PREREQS.get("fusion", 1)
    orphaned = []
    for s in skills:
        if s["type"] == "fusion" and len(s.get("prerequisites", [])) < fusion_floor:
            orphaned.append(s["id"])

    print("\n📊 Graph Statistics")
    print(f"   Total skills: {len(skills)}")
    print(f"   By type: {dict(by_type)}")
    print(f"   By status: {dict(by_status)}")
    print(f"   Total edges: {len(graph.get('edges', []))}")
    print(f"   Max lineage depth: {max_depth}")
    print(f"   Root nodes (basics): {len(roots)}")
    if orphaned:
        print(f"   ⚠ Orphaned fusions: {orphaned}")


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
        "--named-dir", default=None,
        help=(
            "Path to the named-skills directory. When omitted and --graph points "
            "at a mock graph, this is derived from the graph's sibling 'named' dir "
            "so a mock --graph validates its own named skills, not the real "
            "registry/named (#1223). With neither flag, the real registry is used."
        ),
    )
    parser.add_argument(
        "--check-meta-sync", action="store_true",
        help="Verify meta.json is in sync with gaia.json and bundled copies"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help=(
            "Escalate benchmark-result provenance='pending' rows to hard errors. "
            "Auto-enabled when GITHUB_BASE_REF == 'main' (PR run) or GITHUB_REF == "
            "'refs/heads/main' (push run); Sprint D W2a #904."
        ),
    )
    args = parser.parse_args()

    if args.check_meta_sync:
        check_meta_sync()
        return

    # Sprint D W2a (#904): auto-strict on main-touching runs. Covers both
    # PR runs (GITHUB_BASE_REF) and push-to-main (GITHUB_REF).
    strict_mode = (
        args.strict
        or os.environ.get("GITHUB_BASE_REF") == "main"
        or os.environ.get("GITHUB_REF") == "refs/heads/main"
    )

    # Resolve paths
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nodes_dir = os.path.join(repo_root, "registry", "nodes")

    # Default to nodes_dir if it exists, otherwise gaia.json
    if not args.graph and os.path.isdir(nodes_dir):
        graph_path = nodes_dir
    else:
        graph_path = args.graph or os.path.join(repo_root, "registry", "gaia.json")

    schema_dir = args.schema_dir or os.path.join(repo_root, "registry", "schema")

    # Resolve the named-skills directory. Priority:
    #   1. explicit --named-dir
    #   2. derived from a mock --graph (its sibling 'named' dir), so validating a
    #      mock graph checks the mock's named skills — not the real registry/named
    #      (#1223).
    #   3. None → validate_named_skills defaults to the real registry/named.
    # With neither --graph nor --named-dir, named_dir stays None so real-repo
    # behavior is unchanged.
    named_dir = args.named_dir
    if named_dir is None and args.graph:
        graph_arg = os.path.abspath(args.graph)
        base = graph_arg if os.path.isdir(graph_arg) else os.path.dirname(graph_arg)
        # <base>/named if it exists, else <parent>/named (covers --graph pointing
        # at a nodes/ dir whose sibling is named/, or at a mock registry root).
        cand = os.path.join(base, "named")
        if not os.path.isdir(cand):
            cand = os.path.join(os.path.dirname(base), "named")
        named_dir = cand

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

    # Yggdrasil II retired three former steps here, across two commits on this
    # stack: "Named evidence thresholds" (Evidence Floor — TM is the sole gate),
    # "Ultimate constraints" and "Unique skill constraints" (both filtered on
    # retired type literals and validated nothing). See the module docstring and
    # the retirement note above validate_verifier_benchmark_attestations.

    # 6. Named skills validation (includes reviewer gate + catalog cross-refs)
    print("   [6/10] Named skills validation...")
    all_errors.extend(validate_named_skills(graph, named_dir=named_dir))

    # 7. Skill suites validation
    print("   [7/10] Skill suites validation...")
    all_errors.extend(validate_suites(graph))

    # 8. Benchmark source catalog (issue #1419)
    print("   [8/10] Benchmark source catalog...")
    all_errors.extend(validate_benchmark_source_catalog())

    # 9. Benchmark-result provenance (Sprint D W2a, #904)
    strict_label = " [strict]" if strict_mode else ""
    print(f"   [9/10] Benchmark-result provenance{strict_label}...")
    all_errors.extend(validate_benchmark_provenance(graph, strict=strict_mode))

    # 10. Verifier benchmark attestations (Sprint D W2b, #905)
    print("   [10/10] Verifier benchmark attestations...")
    all_errors.extend(validate_verifier_benchmark_attestations())

    # Stats
    compute_stats(graph)

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
