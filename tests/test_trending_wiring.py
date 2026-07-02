"""Integration test: verify build pipeline wires trending JSON correctly.

These tests confirm that docs/api/v1/trending/ exists on disk with valid
content after `build_docs.py` has been run. They are marked integration
because they require committed Class S artifacts on disk, not just the
source scripts.
"""
import json
from pathlib import Path

import pytest

TRENDING_DIR = Path(__file__).resolve().parents[1] / "docs" / "api" / "v1" / "trending"


@pytest.mark.integration
def test_7d_json_exists_and_valid():
    path = TRENDING_DIR / "7d.json"
    assert path.exists(), "docs/api/v1/trending/7d.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "7d.json must be a JSON object"


@pytest.mark.integration
def test_30d_json_exists_and_valid():
    path = TRENDING_DIR / "30d.json"
    assert path.exists(), "docs/api/v1/trending/30d.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "30d.json must be a JSON object"


@pytest.mark.integration
def test_ascended_json_exists():
    path = TRENDING_DIR / "ascended.json"
    assert path.exists(), "docs/api/v1/trending/ascended.json must exist"


@pytest.mark.integration
def test_contested_json_exists():
    path = TRENDING_DIR / "contested.json"
    assert path.exists(), "docs/api/v1/trending/contested.json must exist"


@pytest.mark.integration
def test_snapshot_json_exists():
    path = TRENDING_DIR / "snapshot.json"
    assert path.exists(), "docs/api/v1/trending/snapshot.json must exist"


@pytest.mark.integration
def test_7d_json_has_expected_top_level_keys():
    path = TRENDING_DIR / "7d.json"
    assert path.exists(), "docs/api/v1/trending/7d.json must exist"
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("window", "skills", "generatedAt"):
        assert key in data, f"7d.json is missing top-level key '{key}'"
