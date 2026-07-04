"""tests/test_benchmark_projection.py

Tests for scripts/generateBenchmarkProjection.py.

Run with:
    pytest tests/test_benchmark_projection.py -v
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the scripts package is importable from the repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.generateBenchmarkProjection import (  # noqa: E402
    benchmarkSlug,
    buildBenchmarkFile,
    buildIndexDoc,
    collectBenchmarkRows,
    generate,
    main,
    parseFrontmatter,
)


# ---------------------------------------------------------------------------
# Unit tests — pure helpers
# ---------------------------------------------------------------------------

class TestBenchmarkSlug:
    def test_with_at(self):
        assert benchmarkSlug("humaneval@v1.0") == "humaneval"

    def test_with_at_mmlu(self):
        assert benchmarkSlug("mmlu@2024-03") == "mmlu"

    def test_no_at(self):
        assert benchmarkSlug("custom-bench") == "custom-bench"


class TestParseFrontmatter:
    def test_basic(self):
        md = "---\nid: foo\nname: Foo\n---\nBody"
        fm = parseFrontmatter(md)
        assert fm.get("id") == "foo"

    def test_missing_fence(self):
        assert parseFrontmatter("No frontmatter here") == {}

    def test_evidence_list(self):
        md = (
            "---\n"
            "id: test/skill\n"
            "evidence:\n"
            "- type: benchmark-result\n"
            "  benchmarkId: humaneval@v1.0\n"
            "  score: 0.72\n"
            "---\n"
        )
        fm = parseFrontmatter(md)
        assert isinstance(fm.get("evidence"), list)
        assert fm["evidence"][0]["benchmarkId"] == "humaneval@v1.0"


class TestBuildBenchmarkFile:
    def test_shape(self):
        rows = [{"skillId": "a/b", "score": 0.5, "unit": "pass@1",
                 "provenance": "ci-reproduced", "attestor": None,
                 "datasetHash": None, "benchmarkInputHash": None,
                 "runAt": None, "harnessUrl": None, "percentile": None,
                 "modelRef": None, "notes": None}]
        doc = buildBenchmarkFile("humaneval@v1.0", rows)
        assert doc["benchmarkId"] == "humaneval@v1.0"
        assert doc["schemaVersion"] == "1.0.0"
        assert len(doc["rows"]) == 1
        assert doc["rows"][0]["skillId"] == "a/b"

    def test_unknown_benchmark_falls_back(self):
        doc = buildBenchmarkFile("unknown@v9", [])
        assert doc["benchmarkId"] == "unknown@v9"
        assert doc["name"] == "unknown@v9"


class TestBuildIndexDoc:
    def test_sorted(self):
        doc = buildIndexDoc(["mmlu@2024-03", "humaneval@v1.0"])
        ids = [e["id"] for e in doc["benchmarks"]]
        assert ids == sorted(ids)

    def test_generated_at_null(self):
        doc = buildIndexDoc([])
        assert doc["generatedAt"] is None

    def test_schema_version(self):
        doc = buildIndexDoc(["humaneval@v1.0"])
        assert doc["schemaVersion"] == "1.0.0"


# ---------------------------------------------------------------------------
# Integration tests — actual registry data
# ---------------------------------------------------------------------------

class TestProjectionCreatesHumanevalJson:
    """test_projection_creates_humaneval_json"""

    def test_humaneval_json_exists_after_generate(self, tmp_path):
        out = generate(tmp_path)
        assert "humaneval.json" in out, "humaneval.json not created by generate()"
        doc = json.loads(out["humaneval.json"])
        assert doc["benchmarkId"] == "humaneval@v1.0"
        assert isinstance(doc["rows"], list)

    def test_humaneval_json_matches_committed(self):
        """Running the script should produce output matching the committed file."""
        committed = REPO_ROOT / "docs" / "api" / "v1" / "benchmarks" / "humaneval.json"
        if not committed.exists():
            pytest.skip("humaneval.json not yet committed")
        with tempfile.TemporaryDirectory() as tmp:
            out = generate(Path(tmp))
            if "humaneval.json" not in out:
                pytest.fail("generate() did not produce humaneval.json")
            produced = json.loads(out["humaneval.json"])
            committed_doc = json.loads(committed.read_text(encoding="utf-8"))
            assert produced == committed_doc, (
                "humaneval.json regen does not match committed file — "
                "run `python scripts/generateBenchmarkProjection.py` to refresh"
            )


class TestProjectionIsDeterministic:
    """test_projection_is_deterministic"""

    def test_two_runs_identical(self, tmp_path):
        run1 = generate(tmp_path / "run1")
        run2 = generate(tmp_path / "run2")
        (tmp_path / "run1").mkdir(parents=True, exist_ok=True)
        (tmp_path / "run2").mkdir(parents=True, exist_ok=True)
        assert set(run1.keys()) == set(run2.keys()), "Different file sets"
        for key in run1:
            assert run1[key] == run2[key], f"File {key} differs between runs"


class TestPendingRowsIncluded:
    """test_pending_rows_included — pending provenance rows appear in projection."""

    def test_pending_appears(self, tmp_path, monkeypatch):
        # Inject a synthetic skill file with a pending benchmark row
        fake_named = tmp_path / "named"
        skill_dir = fake_named / "test-contributor"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "test-skill.md"
        skill_md.write_text(
            "---\n"
            "id: test-contributor/test-skill\n"
            "evidence:\n"
            "- type: benchmark-result\n"
            "  benchmarkId: humaneval@v1.0\n"
            "  score: 0.35\n"
            "  unit: pass@1\n"
            "  provenance: pending\n"
            "  attestor: https://example.com/run\n"
            "  datasetHash: abc123\n"
            "  benchmarkInputHash: def456\n"
            "---\n",
            encoding="utf-8",
        )
        import scripts.generateBenchmarkProjection as mod
        orig_dir = mod.NAMED_DIR
        monkeypatch.setattr(mod, "NAMED_DIR", fake_named)
        try:
            rows = collectBenchmarkRows()
        finally:
            monkeypatch.setattr(mod, "NAMED_DIR", orig_dir)

        assert "humaneval@v1.0" in rows
        pending = [r for r in rows["humaneval@v1.0"] if r["provenance"] == "pending"]
        assert len(pending) >= 1
        assert pending[0]["skillId"] == "test-contributor/test-skill"
        assert pending[0]["score"] == 0.35


class TestMirroredRowsFlagged:
    """test_mirrored_rows_flagged — mirrored rows carry provenance field."""

    def test_mirrored_provenance_in_mmlu(self, tmp_path):
        out = generate(tmp_path)
        if "mmlu.json" not in out:
            pytest.skip("No MMLU rows in registry")
        doc = json.loads(out["mmlu.json"])
        for row in doc["rows"]:
            assert row.get("provenance") == "mirrored", (
                f"MMLU row for {row.get('skillId')} is not mirrored: {row.get('provenance')}"
            )

    def test_mirrored_field_preserved_in_projection(self, tmp_path, monkeypatch):
        fake_named = tmp_path / "named"
        skill_dir = fake_named / "mirror-org"
        skill_dir.mkdir(parents=True)
        skill_md = skill_dir / "mirror-skill.md"
        skill_md.write_text(
            "---\n"
            "id: mirror-org/mirror-skill\n"
            "evidence:\n"
            "- type: benchmark-result\n"
            "  benchmarkId: mmlu@2024-03\n"
            "  score: 78.0\n"
            "  unit: pct\n"
            "  provenance: mirrored\n"
            "  attestor: https://huggingface.co/leaderboard\n"
            "---\n",
            encoding="utf-8",
        )
        import scripts.generateBenchmarkProjection as mod
        orig_dir = mod.NAMED_DIR
        monkeypatch.setattr(mod, "NAMED_DIR", fake_named)
        try:
            rows = collectBenchmarkRows()
        finally:
            monkeypatch.setattr(mod, "NAMED_DIR", orig_dir)

        assert "mmlu@2024-03" in rows
        mirrored = [r for r in rows["mmlu@2024-03"] if r["provenance"] == "mirrored"]
        assert len(mirrored) >= 1
        assert mirrored[0]["skillId"] == "mirror-org/mirror-skill"


# ---------------------------------------------------------------------------
# CLI --check flag
# ---------------------------------------------------------------------------

class TestCheckFlag:
    def test_check_exits_zero_when_committed(self):
        """--check should return 0 when committed files match regen."""
        committed = REPO_ROOT / "docs" / "api" / "v1" / "benchmarks" / "humaneval.json"
        if not committed.exists():
            pytest.skip("humaneval.json not yet committed")
        rc = main(["--check"])
        assert rc == 0, "--check returned non-zero on a fresh repo"

    def test_check_exits_one_when_stale(self, tmp_path):
        """--check against an empty dir should detect missing files."""
        rc = main(["--check", "--out-dir", str(tmp_path)])
        assert rc == 1, "--check should return 1 when files are missing"
