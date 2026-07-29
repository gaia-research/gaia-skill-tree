"""Tests for src/gaia_cli/evidenceSeed.py (RFC2 Gap C / #1148 §2).

Covers partition-by-type correctness, attributionScope propagation, the
suite-wide-not-copied guard, and the no-authoritative-grade/star invariant.
"""

import json
import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "src")
)

from gaia_cli.evidenceSeed import (  # noqa: E402
    appendToCollectors,
    buildSeedRow,
    buildSeedRows,
    emitEvidenceSeed,
    partitionByType,
    writeSeedArtifact,
)


# --------------------------------------------------------------------------- #
# Row / partition basics
# --------------------------------------------------------------------------- #

def test_build_seed_row_shape():
    row = buildSeedRow(
        "alice-skill",
        "https://github.com/alice/skill",
        "repo-own",
        "standalone",
    )
    assert row == {
        "skillId": "alice-skill",
        "sourceUrl": "https://github.com/alice/skill",
        "claimedEvidenceType": "repo-own",
        "attributionScope": "standalone",
    }


def test_build_seed_row_rejects_unknown_type():
    with pytest.raises(ValueError, match="unknown claimedEvidenceType"):
        buildSeedRow("s", "u", "not-a-type", "standalone")


def test_build_seed_row_rejects_unknown_scope():
    with pytest.raises(ValueError, match="unknown attributionScope"):
        buildSeedRow("s", "u", "repo-own", "galaxy-wide")


def test_partition_by_type_groups_rows():
    rows = [
        buildSeedRow("s", "u1", "repo-own", "standalone"),
        buildSeedRow("s", "u2", "benchmark-result", "standalone"),
        buildSeedRow("s", "u3", "repo-own", "standalone"),
    ]
    parts = partitionByType(rows)
    assert set(parts.keys()) == {"repo-own", "benchmark-result"}
    assert len(parts["repo-own"]) == 2
    assert len(parts["benchmark-result"]) == 1


# --------------------------------------------------------------------------- #
# attributionScope propagation
# --------------------------------------------------------------------------- #

def test_attribution_scope_propagates_from_default():
    rows = buildSeedRows(
        "s",
        [{"url": "u1", "type": "repo-own"}, {"url": "u2", "type": "arxiv"}],
        attributionScope="suite-component",
    )
    assert all(r["attributionScope"] == "suite-component" for r in rows)


def test_per_source_scope_overrides_default():
    rows = buildSeedRows(
        "s",
        [
            {"url": "u1", "type": "repo-own"},
            {"url": "u2", "type": "arxiv", "scope": "suite-wide"},
        ],
        attributionScope="standalone",
    )
    scopes = {r["sourceUrl"]: r["attributionScope"] for r in rows}
    assert scopes["u1"] == "standalone"
    assert scopes["u2"] == "suite-wide"


# --------------------------------------------------------------------------- #
# No authoritative grade / star
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("badKey", ["stars", "grade", "tier", "class", "trustNumber"])
def test_rejects_authoritative_strength_keys(badKey):
    with pytest.raises(ValueError, match="forbidden strength key"):
        buildSeedRows("s", [{"url": "u", "type": "repo-own", badKey: 5}])


def test_seed_row_has_no_strength_fields():
    rows = buildSeedRows("s", [{"url": "u", "type": "github-stars-own"}])
    for row in rows:
        assert set(row.keys()) == {
            "skillId", "sourceUrl", "claimedEvidenceType", "attributionScope",
        }


# --------------------------------------------------------------------------- #
# Suite-wide-not-copied guard
# --------------------------------------------------------------------------- #

def test_suite_wide_source_not_copied_full_strength_across_components():
    # Same source declared suite-wide once, then a component tries to claim it.
    rows = buildSeedRows(
        "suite-skill",
        [
            {"url": "https://ex.com/adopt", "type": "social-signal", "scope": "suite-wide"},
            {"url": "https://ex.com/adopt", "type": "social-signal", "scope": "suite-component"},
            {"url": "https://ex.com/adopt", "type": "social-signal", "scope": "suite-component"},
        ],
    )
    matching = [r for r in rows if r["sourceUrl"] == "https://ex.com/adopt"]
    # Exactly one suite-wide full row + at most one collapsed reference row.
    fullStrength = [r for r in matching if not r.get("reference")]
    references = [r for r in matching if r.get("reference")]
    assert len(fullStrength) == 1
    assert fullStrength[0]["attributionScope"] == "suite-wide"
    assert len(references) == 1
    assert references[0]["attributionScope"] == "suite-wide"


def test_standalone_sources_are_not_collapsed():
    rows = buildSeedRows(
        "s",
        [
            {"url": "u1", "type": "repo-own"},
            {"url": "u2", "type": "repo-own"},
        ],
    )
    assert len(rows) == 2


# --------------------------------------------------------------------------- #
# Artifact write + dual write
# --------------------------------------------------------------------------- #

def test_write_seed_artifact_partitioned(tmp_path):
    evidenceRoot = str(tmp_path / "evidence")
    rows = buildSeedRows(
        "alice-skill",
        [
            {"url": "u1", "type": "repo-own"},
            {"url": "u2", "type": "benchmark-result"},
        ],
    )
    paths = writeSeedArtifact("alice-skill", rows, evidenceRoot=evidenceRoot)
    names = {os.path.basename(p) for p in paths}
    assert names == {"repo-own.jsonl", "benchmark-result.jsonl"}
    # Each file is valid JSONL with the correct row.
    seedDir = os.path.join(evidenceRoot, "seeds", "alice-skill")
    with open(os.path.join(seedDir, "repo-own.jsonl"), encoding="utf-8") as f:
        line = f.readline()
        row = json.loads(line)
        assert row["claimedEvidenceType"] == "repo-own"
        assert row["skillId"] == "alice-skill"


def test_append_to_collectors_writes_compiler_blocks(tmp_path):
    evidenceRoot = str(tmp_path / "evidence")
    rows = buildSeedRows(
        "alice-skill",
        [{"url": "https://ex.com/bench", "type": "benchmark-result"}],
    )
    written = appendToCollectors(rows, evidenceRoot=evidenceRoot)
    benchPath = os.path.normpath(os.path.join(
        evidenceRoot, "collectors", "technical", "benchmark_results.md"
    ))
    assert benchPath in written
    content = open(benchPath, encoding="utf-8").read()
    # Block uses the compiler's '### ' marker and embeds the skill id in title.
    assert "### `alice-skill`" in content
    assert "https://ex.com/bench" in content
    # NOT pre-marked injected (the compiler adds that).
    assert "<!-- injected" not in content


def test_emit_evidence_seed_dual_write(tmp_path):
    evidenceRoot = str(tmp_path / "evidence")
    result = emitEvidenceSeed(
        "alice-skill",
        [
            {"url": "https://ex.com/repo", "type": "repo-own"},
            {"url": "https://arxiv.org/abs/1", "type": "arxiv"},
        ],
        evidenceRoot=evidenceRoot,
    )
    assert len(result["rows"]) == 2
    assert len(result["artifactPaths"]) == 2  # partitioned by type
    assert len(result["collectorPaths"]) >= 1


def test_emit_evidence_seed_no_collectors(tmp_path):
    evidenceRoot = str(tmp_path / "evidence")
    result = emitEvidenceSeed(
        "alice-skill",
        [{"url": "u", "type": "repo-own"}],
        evidenceRoot=evidenceRoot,
        appendCollectors=False,
    )
    assert result["collectorPaths"] == set()
    assert len(result["artifactPaths"]) == 1
