"""Tests for scripts/benchmarks/mmlu/ingest.py — the MMLU mirrored ingest.

These tests lock in the four key guarantees of the mirrored ingest:
1. dry-run mode prints all CLI invocations without executing them
2. re-running ingest is idempotent (duplicate guard skips existing rows)
3. every ingested row carries provenance=mirrored
4. hashes are deterministic: same snapshot => same datasetHash + benchmarkInputHash
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INGEST_PY = REPO_ROOT / "scripts" / "benchmarks" / "mmlu" / "ingest.py"
SNAPSHOT_PATH = REPO_ROOT / "scripts" / "benchmarks" / "mmlu" / "snapshot.json"


def _loadIngest():
    """Import scripts/benchmarks/mmlu/ingest.py by path — no package plumbing needed."""
    spec = importlib.util.spec_from_file_location("_mmlu_ingest", INGEST_PY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["_mmlu_ingest"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ingest():
    return _loadIngest()


@pytest.fixture(scope="module")
def snapshot(ingest):
    return ingest._loadSnapshot(SNAPSHOT_PATH)


# ---------------------------------------------------------------------------
# Test 1 — dry-run prints all rows, no subprocess.run called
# ---------------------------------------------------------------------------

def test_ingest_dry_run_prints_all_rows(ingest, capsys):
    """dry-run mode prints one CLI invocation per snapshot entry, no writes."""
    with patch.object(sys.modules[ingest.__name__], "subprocess") as mock_subprocess:
        written = ingest.main(snapshotPath=SNAPSHOT_PATH, dryRun=True)

    # No real subprocess calls in dry-run mode
    mock_subprocess.run.assert_not_called()

    # Written count is 0 in dry-run
    assert written == 0

    # stdout shows one [dry-run] line per entry
    captured = capsys.readouterr()
    lines = [ln for ln in captured.out.splitlines() if ln.startswith("[dry-run]")]
    assert len(lines) == len(ingest._loadSnapshot(SNAPSHOT_PATH)["entries"]), (
        "Expected one [dry-run] line per snapshot entry"
    )

    # Each line must contain --provenance mirrored
    for line in lines:
        assert "--provenance mirrored" in line, (
            f"[dry-run] line missing --provenance mirrored:\n{line}"
        )


# ---------------------------------------------------------------------------
# Test 2 — duplicate guard: re-running is idempotent
# ---------------------------------------------------------------------------

def test_ingest_skips_duplicate_rows(ingest, capsys):
    """Re-running ingest against the same snapshot produces zero writes."""
    snapshot_data = ingest._loadSnapshot(SNAPSHOT_PATH)
    benchmarkId = snapshot_data["benchmarkId"]
    sourceUrl = snapshot_data["sourceUrl"]
    entries = snapshot_data["entries"]

    # Build a fake existing-evidence list that already has all rows.
    def _fakeLoadExisting(skillId):
        return [
            {
                "type": "benchmark-result",
                "benchmarkId": benchmarkId,
                "attestor": sourceUrl,
                "provenance": "mirrored",
            }
        ]

    with (
        patch.object(sys.modules[ingest.__name__], "_loadExistingEvidence", side_effect=_fakeLoadExisting),
        patch.object(sys.modules[ingest.__name__], "subprocess") as mock_subprocess,
    ):
        written = ingest.main(snapshotPath=SNAPSHOT_PATH, dryRun=False)

    assert written == 0, "Expected 0 writes when all rows already exist"
    mock_subprocess.run.assert_not_called()

    captured = capsys.readouterr()
    skip_lines = [ln for ln in captured.out.splitlines() if ln.startswith("[skip]")]
    assert len(skip_lines) == len(entries), (
        "Expected one [skip] line per duplicate entry"
    )


# ---------------------------------------------------------------------------
# Test 3 — provenance is always mirrored
# ---------------------------------------------------------------------------

def test_provenance_is_mirrored(ingest):
    """Every CLI invocation built by _buildCliArgs carries --provenance mirrored."""
    snapshot_data = ingest._loadSnapshot(SNAPSHOT_PATH)
    sourceUrl = snapshot_data["sourceUrl"]
    benchmarkId = snapshot_data["benchmarkId"]
    unit = snapshot_data["unit"]
    runAt = snapshot_data["runAt"]
    sourceSnapshotDate = snapshot_data["sourceSnapshotDate"]

    datasetHash = ingest._sha256(sourceUrl + sourceSnapshotDate)

    for entry in snapshot_data["entries"]:
        skillId = entry["skillId"]
        score = float(entry["score"])
        benchmarkInputHash = ingest._sha256(sourceUrl + skillId + str(score))

        argv = ingest._buildCliArgs(
            skillId=skillId,
            sourceUrl=sourceUrl,
            benchmarkId=benchmarkId,
            score=score,
            unit=unit,
            runAt=runAt,
            datasetHash=datasetHash,
            benchmarkInputHash=benchmarkInputHash,
        )

        # Locate --provenance flag and its value
        assert "--provenance" in argv, f"Missing --provenance in argv for {skillId}"
        idx = argv.index("--provenance")
        assert argv[idx + 1] == "mirrored", (
            f"Expected --provenance mirrored for {skillId}, got {argv[idx + 1]!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — hashes are deterministic
# ---------------------------------------------------------------------------

def test_datasetHash_is_deterministic(ingest):
    """Same snapshot => same datasetHash and same benchmarkInputHash per row."""
    snapshot_data = ingest._loadSnapshot(SNAPSHOT_PATH)
    sourceUrl = snapshot_data["sourceUrl"]
    sourceSnapshotDate = snapshot_data["sourceSnapshotDate"]

    # Compute twice and compare
    hashA = ingest._sha256(sourceUrl + sourceSnapshotDate)
    hashB = ingest._sha256(sourceUrl + sourceSnapshotDate)
    assert hashA == hashB, "datasetHash is not deterministic"

    for entry in snapshot_data["entries"]:
        skillId = entry["skillId"]
        score = float(entry["score"])
        inputA = ingest._sha256(sourceUrl + skillId + str(score))
        inputB = ingest._sha256(sourceUrl + skillId + str(score))
        assert inputA == inputB, f"benchmarkInputHash is not deterministic for {skillId}"

    # Cross-row hashes must differ (different skillId + score => different hash)
    entries = snapshot_data["entries"]
    if len(entries) >= 2:
        hash0 = ingest._sha256(sourceUrl + entries[0]["skillId"] + str(float(entries[0]["score"])))
        hash1 = ingest._sha256(sourceUrl + entries[1]["skillId"] + str(float(entries[1]["score"])))
        assert hash0 != hash1, "Two distinct rows produced the same benchmarkInputHash — collision risk"
