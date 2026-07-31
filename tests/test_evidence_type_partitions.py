import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evidence", "scripts"))

from evidence_type_partitions import (  # noqa: E402
    CANONICAL_EVIDENCE_TYPES,
    byTypeDir,
    evidenceTypeFilename,
    iterTypePartitionPaths,
    normalizeEvidenceType,
    typeOutputPath,
)


def test_canonical_order_matches_evidence_seed_vocabulary():
    assert CANONICAL_EVIDENCE_TYPES == (
        "repo-own",
        "github-stars-own",
        "social-signal",
        "benchmark-result",
        "arxiv",
        "peer-review",
        "proxy-containment",
        "verifier-attestation",
        "fusion-recipe",
        "self-attestation",
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("repo-own", "repo-own"),
        ("github-stars-own", "github-stars-own"),
        ("repo", "repo-own"),
        ("github-stars", "github-stars-own"),
    ],
)
def test_normalize_evidence_type_accepts_canonical_and_legacy_aliases(raw, expected):
    assert normalizeEvidenceType(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "not-a-type"])
def test_normalize_evidence_type_rejects_unknown_or_empty(raw):
    with pytest.raises(ValueError):
        normalizeEvidenceType(raw)


def test_evidence_type_paths_are_deterministic(tmp_path):
    evidence_root = tmp_path / "evidence"
    assert byTypeDir(evidence_root) == os.path.join(str(evidence_root), "by-type")
    assert evidenceTypeFilename("repo") == "repo-own.md"
    assert typeOutputPath(evidence_root, "github-stars") == os.path.join(
        str(evidence_root), "by-type", "github-stars-own.md"
    )
    assert typeOutputPath(evidence_root / "by-type", "arxiv") == os.path.join(
        str(evidence_root), "by-type", "arxiv.md"
    )


def test_iter_type_partition_paths_uses_canonical_order(tmp_path):
    by_type = tmp_path / "evidence" / "by-type"
    paths = list(iterTypePartitionPaths(by_type))
    assert paths[0].endswith(os.path.join("by-type", "repo-own.md"))
    assert paths[1].endswith(os.path.join("by-type", "github-stars-own.md"))
    assert paths[-1].endswith(os.path.join("by-type", "self-attestation.md"))
    assert len(paths) == len(CANONICAL_EVIDENCE_TYPES)
