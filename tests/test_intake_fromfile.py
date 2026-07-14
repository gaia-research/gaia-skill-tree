import os
import sys
import json
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.validate_intake import validate_schema

def load_schema():
    schema_path = os.path.join(REPO_ROOT, "registry", "schema", "skillBatch.schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_fromfile_valid():
    batch = {
        "fromFile": True,
        "batchId": "test-batch",
        "userId": "tester",
        "sourceRepo": "tester/repo",
        "generatedAt": "2026-07-14T00:00:00Z",
        "knownSkills": [],
        "proposedSkills": [],
        "similarity": []
    }
    schema = load_schema()
    errors = validate_schema(batch, schema, "test-path")
    assert not errors

def test_fromfile_invalid_bogus_key():
    batch = {
        "fromFile": True,
        "bogus": 1,
        "batchId": "test-batch",
        "userId": "tester",
        "sourceRepo": "tester/repo",
        "generatedAt": "2026-07-14T00:00:00Z",
        "knownSkills": [],
        "proposedSkills": [],
        "similarity": []
    }
    schema = load_schema()
    errors = validate_schema(batch, schema, "test-path")
    assert len(errors) > 0
    assert "schema error" in errors[0]
