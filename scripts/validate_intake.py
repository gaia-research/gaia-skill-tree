#!/usr/bin/env python3
"""Validate Gaia skill batch intake records."""

import argparse
import glob
import json
import os
import re
import sys

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
VALID_TYPES = {"basic", "extra", "ultimate"}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_canonical_ids(graph_path):
    graph = load_json(graph_path)
    return {skill["id"] for skill in graph.get("skills", [])}


def batch_files(intake_dir):
    return sorted(glob.glob(os.path.join(intake_dir, "skill-batches", "*.json")))


def validate_required(batch, path):
    errors = []
    for field in (
        "batchId",
        "userId",
        "sourceRepo",
        "generatedAt",
        "knownSkills",
        "proposedSkills",
        "similarity",
    ):
        if field not in batch:
            errors.append(f"{path}: missing required field '{field}'.")
    return errors


def validate_batch_shape(batch, path):
    errors = validate_required(batch, path)
    if errors:
        return errors

    if not isinstance(batch["knownSkills"], list):
        errors.append(f"{path}: knownSkills must be an array.")
    if not isinstance(batch["proposedSkills"], list):
        errors.append(f"{path}: proposedSkills must be an array.")
    if not isinstance(batch["similarity"], list):
        errors.append(f"{path}: similarity must be an array.")

    for known in batch.get("knownSkills", []):
        skill_id = known.get("skillId") if isinstance(known, dict) else None
        if not skill_id or not SKILL_ID_RE.match(skill_id):
            errors.append(f"{path}: knownSkills entries need a valid skillId.")

    for proposed in batch.get("proposedSkills", []):
        if not isinstance(proposed, dict):
            errors.append(f"{path}: proposedSkills entries must be objects.")
            continue
        skill_id = proposed.get("id")
        if not skill_id or not SKILL_ID_RE.match(skill_id):
            errors.append(f"{path}: proposed skill needs a valid id.")
        if proposed.get("type") not in VALID_TYPES:
            errors.append(f"{path}: proposed skill '{skill_id}' has invalid type.")
        if len(proposed.get("description", "")) < 10:
            errors.append(f"{path}: proposed skill '{skill_id}' needs a description.")

    for link in batch.get("similarity", []):
        if not isinstance(link, dict):
            errors.append(f"{path}: similarity entries must be objects.")
            continue
        for field in ("sourceSkillId", "targetSkillId"):
            skill_id = link.get(field)
            if not skill_id or not SKILL_ID_RE.match(skill_id):
                errors.append(f"{path}: similarity entries need a valid {field}.")
        score = link.get("score")
        if not isinstance(score, (int, float)) or score < 0 or score > 1:
            errors.append(f"{path}: similarity score must be between 0 and 1.")

    return errors


def validate_schema(batch, validator, path):
    if not HAS_JSONSCHEMA or not validator:
        return []
    try:
        validator.validate(batch)
        return []
    except jsonschema.ValidationError as exc:
        return [f"{path}: schema error: {exc.message}"]


def canonical_duplicate_warning(path, skill_id):
    return (
        f"{path}: Warning: '{skill_id}' already exists as a generic skill.\n"
        f"  - To add a named implementation: create registry/named/<contributor>/{skill_id}.md\n"
        "  - To reclassify or evolve the generic skill: use PR type [reclassify]\n"
        "Treating this proposal as a named-skill submission. Review required."
    )


def validate_intake(intake_dir, graph_path, schema_path=None, strict=False):
    errors = []
    warnings = []
    canonical_ids = load_canonical_ids(graph_path)
    schema = load_json(schema_path) if schema_path and HAS_JSONSCHEMA else None

    # Performance optimization:
    # Initialize validator once to avoid re-parsing schemas for each batch
    schema_validator = None
    if schema and HAS_JSONSCHEMA:
        validator_cls = jsonschema.validators.validator_for(schema)
        schema_validator = validator_cls(schema)

    proposed_seen = {}
    batches = []

    for path in batch_files(intake_dir):
        try:
            batch = load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
            continue
        if schema_validator:
            errors.extend(validate_schema(batch, schema_validator, path))
        errors.extend(validate_batch_shape(batch, path))
        batches.append((path, batch))

    for path, batch in batches:
        for known in batch.get("knownSkills", []):
            skill_id = known.get("skillId")
            if skill_id and skill_id not in canonical_ids:
                errors.append(f"{path}: known skill '{skill_id}' is not canonical.")

        for proposed in batch.get("proposedSkills", []):
            skill_id = proposed.get("id")
            if not skill_id:
                continue
            if skill_id in canonical_ids:
                message = canonical_duplicate_warning(path, skill_id)
                if strict:
                    errors.append(message)
                else:
                    warnings.append(message)
            if skill_id in proposed_seen:
                errors.append(
                    f"{path}: Duplicate proposed skill '{skill_id}' also appears in {proposed_seen[skill_id]}."
                )
            proposed_seen[skill_id] = path

    known_candidate_ids = canonical_ids.union(proposed_seen.keys())
    for path, batch in batches:
        for link in batch.get("similarity", []):
            source = link.get("sourceSkillId")
            target = link.get("targetSkillId")
            if source and source not in known_candidate_ids:
                errors.append(f"{path}: similarity has unknown sourceSkillId '{source}'.")
            if target and target not in known_candidate_ids:
                errors.append(f"{path}: similarity has unknown targetSkillId '{target}'.")

    return errors, warnings, len(batches)


def main():
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Validate Gaia intake skill batches.")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument("--intake-dir", default=os.path.join(repo_root, "registry-for-review"))
    parser.add_argument("--graph", default=os.path.join(repo_root, "registry", "gaia.json"))
    parser.add_argument("--schema", default=os.path.join(repo_root, "registry", "schema", "skillBatch.schema.json"))
    parser.add_argument("--strict", action="store_true", help="Treat canonical skill ID proposals as errors.")
    args = parser.parse_args()

    if not HAS_JSONSCHEMA:
        print("⚠  jsonschema not installed — skipping intake schema validation.")
        print("   Install with: pip install jsonschema")

    errors, warnings, total = validate_intake(args.intake_dir, args.graph, args.schema, strict=args.strict)
    print(f"Validating intake batches: {args.intake_dir}")
    print(f"Found {total} batch file(s).")

    if warnings:
        print(f"\n{len(warnings)} intake validation warning(s):")
        for idx, warning in enumerate(warnings, 1):
            print(f"   {idx}. {warning}")

    if errors:
        print(f"\n❌ {len(errors)} intake validation error(s):")
        for idx, error in enumerate(errors, 1):
            print(f"   {idx}. {error}")
        sys.exit(1)

    print("\n✅ All intake checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
