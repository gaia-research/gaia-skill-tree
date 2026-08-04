"""Helpers for Gaia's type-first evidence lake partitions (#1148).

The canonical partition key is the evidence type, not star tier/rank. These
helpers deliberately mirror ``src/gaia_cli/evidenceSeed.py::SEED_EVIDENCE_TYPES``
so the seed handoff and the lake compiler agree on path names.
"""

from __future__ import annotations

import os
from typing import Iterator

CANONICAL_EVIDENCE_TYPES = (
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

LEGACY_EVIDENCE_TYPE_ALIASES = {
    "repo": "repo-own",
    "github-stars": "github-stars-own",
}


def normalizeEvidenceType(raw: object) -> str:
    """Return the canonical evidence type for ``raw``.

    Known legacy aliases are mapped forward. Canonical values pass through.
    Unknown/empty values are rejected so callers do not silently route rows into
    a meaningless partition.
    """
    if raw is None:
        raise ValueError("missing evidence type")
    evType = str(raw).strip()
    if not evType:
        raise ValueError("missing evidence type")
    evType = LEGACY_EVIDENCE_TYPE_ALIASES.get(evType, evType)
    if evType not in CANONICAL_EVIDENCE_TYPES:
        raise ValueError(
            f"unknown evidence type {raw!r} "
            f"(valid: {', '.join(CANONICAL_EVIDENCE_TYPES)})"
        )
    return evType


def evidenceTypeFilename(evType: object) -> str:
    """Return the deterministic markdown filename for an evidence type."""
    return f"{normalizeEvidenceType(evType)}.md"


def byTypeDir(evidenceRoot: os.PathLike[str] | str) -> str:
    """Return ``<evidenceRoot>/by-type``."""
    return os.path.join(os.fspath(evidenceRoot), "by-type")


def typeOutputPath(evidenceRootOrByTypeDir: os.PathLike[str] | str, evType: object) -> str:
    """Return the partition path for ``evType``.

    ``evidenceRootOrByTypeDir`` may be either an evidence root (``evidence``) or
    the by-type directory itself (``evidence/by-type``). The latter is detected
    by basename to keep call sites simple.
    """
    root = os.fspath(evidenceRootOrByTypeDir)
    outDir = root if os.path.basename(os.path.normpath(root)) == "by-type" else byTypeDir(root)
    return os.path.join(outDir, evidenceTypeFilename(evType))


def iterTypePartitionPaths(byTypeDirectory: os.PathLike[str] | str) -> Iterator[str]:
    """Yield canonical by-type partition paths in deterministic type order."""
    root = os.fspath(byTypeDirectory)
    for evType in CANONICAL_EVIDENCE_TYPES:
        yield os.path.join(root, evidenceTypeFilename(evType))
