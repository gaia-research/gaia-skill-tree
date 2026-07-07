"""Tests for scripts/benchmarks/humaneval/run.py — the reference harness.

The harness is the load-bearing artifact of Sprint D W2b: CI reproduces
against it, and every downstream score row inherits its determinism
guarantees. These tests lock in those guarantees.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HARNESS = REPO_ROOT / "scripts" / "benchmarks" / "humaneval" / "run.py"
FIXTURE = REPO_ROOT / "scripts" / "benchmarks" / "humaneval" / "fixtures" / "mini.jsonl"
PROMPT = REPO_ROOT / "scripts" / "benchmarks" / "humaneval" / "prompts" / "default.md"


def _loadHarness():
    """Import scripts/benchmarks/humaneval/run.py by path — no package plumbing."""
    spec = importlib.util.spec_from_file_location("_humaneval_run", HARNESS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["_humaneval_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def harness():
    return _loadHarness()


def test_deterministic_hashes_across_runs(harness, tmp_path):
    """Same inputs → identical datasetHash + benchmarkInputHash across two runs.

    This is the CI reproduction contract in one assertion. If it flakes, the
    whole benchmark pipeline is unshippable.
    """
    outA = tmp_path / "a.json"
    outB = tmp_path / "b.json"

    resultA = harness.main(
        skillId="test/skill",
        datasetPath=FIXTURE,
        promptTemplate=PROMPT,
        outputFile=outA,
    )
    resultB = harness.main(
        skillId="test/skill",
        datasetPath=FIXTURE,
        promptTemplate=PROMPT,
        outputFile=outB,
    )

    assert resultA["datasetHash"] == resultB["datasetHash"]
    assert resultA["benchmarkInputHash"] == resultB["benchmarkInputHash"]
    # Score must be deterministic too — the stubbed evaluator is seeded by
    # (datasetHash, taskId), so two runs of the same fixture MUST land on
    # the same pass count.
    assert resultA["score"] == resultB["score"]
    assert resultA["pass"] == resultB["pass"]
    assert resultA["total"] == resultB["total"] == 6


def test_output_shape_matches_schema(harness, tmp_path):
    """The emitted JSON must carry every field gaia push --from-result-file consumes."""
    out = tmp_path / "result.json"
    result = harness.main(
        skillId="addy-osmani/code-simplification",
        datasetPath=FIXTURE,
        promptTemplate=PROMPT,
        outputFile=out,
    )

    required = {
        "skillId",
        "benchmarkId",
        "score",
        "unit",
        "pass",
        "total",
        "datasetHash",
        "benchmarkInputHash",
        "runAt",
        "harnessCommit",
    }
    assert required.issubset(result.keys()), f"missing: {required - result.keys()}"

    # Contract shape checks — these mirror _preflight_benchmark_row.
    assert result["benchmarkId"] == "humaneval@v1.0"
    assert result["unit"] == "pass@1"
    assert len(result["datasetHash"]) == 64
    assert len(result["benchmarkInputHash"]) == 64
    assert all(c in "0123456789abcdef" for c in result["datasetHash"])
    assert all(c in "0123456789abcdef" for c in result["benchmarkInputHash"])
    assert result["runAt"].endswith("Z"), "runAt must be UTC-Z ISO 8601"
    assert 0.0 <= result["score"] <= 1.0

    # The file on disk must match the returned dict.
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == result


def test_missing_dataset_raises(harness, tmp_path):
    """Clean error path when the dataset file is missing."""
    with pytest.raises(FileNotFoundError):
        harness.main(
            skillId="test/skill",
            datasetPath=tmp_path / "does-not-exist.jsonl",
            promptTemplate=PROMPT,
            outputFile=tmp_path / "out.json",
        )


def test_missing_prompt_raises(harness, tmp_path):
    """Clean error path when the prompt template is missing."""
    with pytest.raises(FileNotFoundError):
        harness.main(
            skillId="test/skill",
            datasetPath=FIXTURE,
            promptTemplate=tmp_path / "does-not-exist.md",
            outputFile=tmp_path / "out.json",
        )


def test_dry_run_skips_evaluation_but_writes_hashes(harness, tmp_path):
    """--dry-run must still produce a valid fingerprint (for CI plumbing tests)."""
    out = tmp_path / "dry.json"
    result = harness.main(
        skillId="test/skill",
        datasetPath=FIXTURE,
        promptTemplate=PROMPT,
        outputFile=out,
        dryRun=True,
    )
    assert result["pass"] == 0
    assert result["score"] == 0.0
    assert result["dryRun"] is True
    # Hashes still populated — that is the whole point of the dry-run mode.
    assert len(result["datasetHash"]) == 64
    assert len(result["benchmarkInputHash"]) == 64


def test_prompt_template_change_invalidates_input_hash(harness, tmp_path):
    """Changing the prompt template must produce a distinct benchmarkInputHash.

    This is the entire reason benchmarkInputHash is separate from datasetHash —
    a prompt tweak silently changes the eval semantics; the fingerprint must
    reflect it so pending/ci-reproduced rows do not collide across versions.
    """
    altPrompt = tmp_path / "alt.md"
    altPrompt.write_text("DIFFERENT TEMPLATE {prompt}", encoding="utf-8")

    baseline = harness.main(
        skillId="test/skill",
        datasetPath=FIXTURE,
        promptTemplate=PROMPT,
        outputFile=tmp_path / "base.json",
        dryRun=True,
    )
    altered = harness.main(
        skillId="test/skill",
        datasetPath=FIXTURE,
        promptTemplate=altPrompt,
        outputFile=tmp_path / "alt-out.json",
        dryRun=True,
    )

    assert baseline["datasetHash"] == altered["datasetHash"], (
        "datasetHash depends ONLY on dataset bytes; prompt change must not affect it"
    )
    assert baseline["benchmarkInputHash"] != altered["benchmarkInputHash"], (
        "benchmarkInputHash MUST change when prompt template changes"
    )
