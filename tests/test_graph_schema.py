"""Tests for graph.schema.json and the public graph feed contract (Issues #1201, #1202)."""

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "registry" / "schema" / "graph.schema.json"
BUNDLED_SCHEMA_PATH = REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / "graph.schema.json"
DOCS_SCHEMA_PATH = REPO_ROOT / "docs" / "schema" / "graph.schema.json"
DOCS_GRAPH_PATH = REPO_ROOT / "docs" / "graph" / "gaia.json"
REGISTRY_GRAPH_PATH = REPO_ROOT / "registry" / "gaia.json"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate.py"


@pytest.fixture(scope="module")
def graph_schema() -> dict:
    assert SCHEMA_PATH.is_file(), f"Missing {SCHEMA_PATH}"
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_graph_schema_is_valid_draft7(graph_schema):
    """The graph schema must be a valid Draft-07 JSON Schema."""
    jsonschema.Draft7Validator.check_schema(graph_schema)
    assert graph_schema["$id"] == "https://gaiaskilltree.com/schema/graph.schema.json"
    assert graph_schema["$schema"] == "http://json-schema.org/draft-07/schema#"


def test_graph_schema_bundled_and_docs_mirrors_in_sync(graph_schema):
    """The canonical schema must match bundled and docs/schema/ mirrors byte-for-byte."""
    canonical_bytes = SCHEMA_PATH.read_bytes()
    assert BUNDLED_SCHEMA_PATH.is_file(), f"Missing {BUNDLED_SCHEMA_PATH}"
    assert BUNDLED_SCHEMA_PATH.read_bytes() == canonical_bytes, "Bundled schema mirror out of sync"
    assert DOCS_SCHEMA_PATH.is_file(), f"Missing {DOCS_SCHEMA_PATH}"
    assert DOCS_SCHEMA_PATH.read_bytes() == canonical_bytes, "docs/schema mirror out of sync"


def test_docs_graph_gaia_json_declares_truthful_schema():
    """docs/graph/gaia.json must declare the resolvable graph schema URI (Issue #1201)."""
    assert DOCS_GRAPH_PATH.is_file(), f"Missing {DOCS_GRAPH_PATH}"
    with open(DOCS_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("$schema") == "https://gaiaskilltree.com/schema/graph.schema.json"


def test_docs_graph_validates_against_graph_schema(graph_schema):
    """docs/graph/gaia.json must be valid vs its own declared schema (Issue #1202)."""
    with open(DOCS_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(data))
    assert not errors, f"docs/graph/gaia.json schema errors: {[e.message for e in errors]}"


def test_registry_gaia_json_validates_against_graph_schema(graph_schema):
    """registry/gaia.json must be valid vs graph.schema.json."""
    if not REGISTRY_GRAPH_PATH.is_file():
        subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "assemble_gaia.py")], cwd=str(REPO_ROOT), check=True)
    with open(REGISTRY_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(data))
    assert not errors, f"registry/gaia.json schema errors: {[e.message for e in errors]}"


def test_graph_schema_rejects_unexpected_root_properties(graph_schema):
    """graph.schema.json must strictly enforce additionalProperties: false at root."""
    with open(DOCS_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    mutated = copy.deepcopy(data)
    mutated["unexpectedRootProp"] = "invalid"
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(mutated))
    assert any("unexpectedRootProp" in e.message for e in errors)


def test_graph_schema_rejects_unexpected_skill_properties(graph_schema):
    """graph.schema.json must strictly enforce additionalProperties: false on skills."""
    with open(DOCS_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    mutated = copy.deepcopy(data)
    mutated["skills"][0]["unexpectedSkillProp"] = 123
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(mutated))
    assert any("unexpectedSkillProp" in e.message for e in errors)


def test_graph_schema_rejects_unexpected_edge_properties(graph_schema):
    """graph.schema.json must strictly enforce additionalProperties: false on edges."""
    with open(DOCS_GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    mutated = copy.deepcopy(data)
    mutated["edges"][0]["unexpectedEdgeProp"] = True
    validator = jsonschema.Draft7Validator(graph_schema)
    errors = list(validator.iter_errors(mutated))
    assert any("unexpectedEdgeProp" in e.message for e in errors)


def test_graph_and_skill_schema_overlapping_properties_match(graph_schema):
    """Overlapping skill properties in graph.schema.json must match skill.schema.json to prevent drift."""
    skill_schema_path = REPO_ROOT / "registry" / "schema" / "skill.schema.json"
    assert skill_schema_path.is_file(), f"Missing {skill_schema_path}"
    with open(skill_schema_path, "r", encoding="utf-8") as f:
        skill_schema = json.load(f)

    skill_props = skill_schema.get("properties", {})
    graph_skill_props = graph_schema.get("definitions", {}).get("graphSkill", {}).get("properties", {})

    overlapping_keys = sorted(set(skill_props.keys()) & set(graph_skill_props.keys()))
    assert len(overlapping_keys) >= 24, f"Expected at least 24 overlapping properties, got {len(overlapping_keys)}"

    mismatches = []
    for key in overlapping_keys:
        if skill_props[key] != graph_skill_props[key]:
            mismatches.append(key)

    assert not mismatches, f"Overlapping schema properties differ between skill.schema.json and graph.schema.json: {mismatches}"


def test_validate_script_passes_on_docs_graph():
    """scripts/validate.py --graph docs/graph/gaia.json must exit 0."""
    result = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), "--graph", str(DOCS_GRAPH_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"validate.py failed on docs/graph/gaia.json:\n{result.stderr}\n{result.stdout}"
    assert "All validation checks passed." in result.stdout
