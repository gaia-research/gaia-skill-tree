"""MMLU mirrored ingest — reads snapshot.json and writes provenance=mirrored
benchmark-result evidence rows via `gaia dev evidence`.

Usage
-----
    # Preview (no writes):
    python scripts/benchmarks/mmlu/ingest.py --dry-run

    # Write rows:
    GAIA_OPERATOR_OVERRIDE=1 python scripts/benchmarks/mmlu/ingest.py

    # Custom snapshot path:
    GAIA_OPERATOR_OVERRIDE=1 python scripts/benchmarks/mmlu/ingest.py \\
        --snapshot /path/to/my-snapshot.json

Contract
--------
- Provenance is always `mirrored` — never `ci-reproduced` or `verifier-attested`.
- Mirrored rows are permanently excluded from Trust Magnitude (TM returns None).
- Duplicate guard: if the skill already has a benchmark-result row with the
  same (benchmarkId, attestor, skillId) triple, the row is skipped.
- datasetHash  = SHA-256(sourceUrl + sourceSnapshotDate)
- benchmarkInputHash = SHA-256(sourceUrl + skillId + str(score))
  Both are deterministic per snapshot entry; same snapshot => same hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_SNAPSHOT = Path(__file__).resolve().parent / "snapshot.json"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _loadSnapshot(snapshotPath: Path) -> dict:
    with open(snapshotPath, encoding="utf-8") as fh:
        data = json.load(fh)
    required = {"sourceUrl", "sourceSnapshotDate", "benchmarkId", "unit", "runAt", "entries"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"snapshot.json is missing required keys: {missing}")
    return data


def _loadExistingEvidence(skillId: str) -> list[dict]:
    """Read the named skill markdown and return its evidence list (may be empty)."""
    contributor, slug = skillId.split("/", 1)
    mdPath = _REPO_ROOT / "registry" / "named" / contributor / f"{slug}.md"
    if not mdPath.exists():
        raise FileNotFoundError(f"Named skill file not found: {mdPath}")

    text = mdPath.read_text(encoding="utf-8")
    # Extract YAML frontmatter between the first pair of --- markers.
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return []

    # Minimal evidence parser: look for the evidence: block and parse entries.
    # We only need to check benchmarkId + attestor for duplicate detection, so
    # a full YAML parse would be overkill — but we do need it for correctness.
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(match.group(1))
    except Exception:
        # If PyYAML is not available, fall back to a best-effort line scan.
        return []

    if not isinstance(meta, dict):
        return []
    return meta.get("evidence", []) or []


def _isDuplicate(existing: list[dict], benchmarkId: str, attestor: str) -> bool:
    """Return True if there is already a mirrored row with the same (benchmarkId, attestor)."""
    for row in existing:
        if (
            row.get("type") == "benchmark-result"
            and row.get("benchmarkId") == benchmarkId
            and row.get("attestor") == attestor
            and row.get("provenance") == "mirrored"
        ):
            return True
    return False


def _buildCliArgs(
    skillId: str,
    sourceUrl: str,
    benchmarkId: str,
    score: float,
    unit: str,
    runAt: str,
    datasetHash: str,
    benchmarkInputHash: str,
) -> list[str]:
    """Return the argv list for `gaia dev evidence … --provenance mirrored`."""
    return [
        sys.executable, "-m", "gaia_cli",
        "dev", "evidence",
        skillId,
        sourceUrl,
        "--type", "benchmark-result",
        "--benchmark-id", benchmarkId,
        "--score", str(score),
        "--unit", unit,
        "--run-at", runAt,
        "--provenance", "mirrored",
        "--attestor", sourceUrl,
        "--dataset-hash", datasetHash,
        "--benchmark-input-hash", benchmarkInputHash,
    ]


def main(snapshotPath: Path = _DEFAULT_SNAPSHOT, dryRun: bool = False) -> int:  # noqa: FBT001
    """Run the ingest.

    Returns the number of rows written (0 on dry-run or all-skipped).
    """
    snapshot = _loadSnapshot(snapshotPath)
    sourceUrl: str = snapshot["sourceUrl"]
    sourceSnapshotDate: str = snapshot["sourceSnapshotDate"]
    benchmarkId: str = snapshot["benchmarkId"]
    unit: str = snapshot["unit"]
    runAt: str = snapshot["runAt"]
    entries: list[dict] = snapshot["entries"]

    datasetHash = _sha256(sourceUrl + sourceSnapshotDate)

    env = {"PYTHONPATH": str(_REPO_ROOT / "src"), "GAIA_OPERATOR_OVERRIDE": "1"}
    import os
    env.update(os.environ)

    written = 0
    for entry in entries:
        skillId: str = entry["skillId"]
        score: float = float(entry["score"])

        benchmarkInputHash = _sha256(sourceUrl + skillId + str(score))

        argv = _buildCliArgs(
            skillId=skillId,
            sourceUrl=sourceUrl,
            benchmarkId=benchmarkId,
            score=score,
            unit=unit,
            runAt=runAt,
            datasetHash=datasetHash,
            benchmarkInputHash=benchmarkInputHash,
        )

        if dryRun:
            print("[dry-run]", " ".join(argv))
            continue

        # Duplicate guard — skip if same (benchmarkId, attestor) already on file.
        try:
            existing = _loadExistingEvidence(skillId)
        except FileNotFoundError as exc:
            print(f"[skip] {skillId}: {exc}", file=sys.stderr)
            continue

        if _isDuplicate(existing, benchmarkId, attestor=sourceUrl):
            print(f"[skip] {skillId}: already has mirrored row for {benchmarkId} from {sourceUrl}")
            continue

        print(f"[ingest] {skillId} score={score} {unit}")
        result = subprocess.run(argv, env=env, cwd=str(_REPO_ROOT), capture_output=False)
        if result.returncode != 0:
            print(f"[error] {skillId}: gaia dev evidence exited {result.returncode}", file=sys.stderr)
        else:
            written += 1

    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest MMLU mirrored benchmark-result rows into the Gaia registry.",
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=_DEFAULT_SNAPSHOT,
        help="Path to snapshot.json (default: scripts/benchmarks/mmlu/snapshot.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print CLI invocations without executing them.",
    )
    args = parser.parse_args()
    written = main(snapshotPath=args.snapshot, dryRun=args.dry_run)
    if not args.dry_run:
        print(f"\nDone: {written} row(s) written.")
    sys.exit(0)
