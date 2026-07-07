"""Sprint D W2b (#905) — verifier benchmark-attestation validation tests.

Covers ``scripts/check_verifier_signoffs.py::checkBenchmarkAttestations``:
the CI-enforced invariants on docs/verifier-signoffs/YYYY-MM/*.md.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_verifier_signoffs.py"


def _loadScript():
    spec = importlib.util.spec_from_file_location("_check_verifier_signoffs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["_check_verifier_signoffs"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script():
    return _loadScript()


def _hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _writeAttestation(root: Path, month: str, name: str, frontmatter: dict[str, str], body: str = "Body.") -> Path:
    """Write a docs/verifier-signoffs/<month>/<name>.md-style attestation file."""
    monthDir = root / "docs" / "verifier-signoffs" / month
    monthDir.mkdir(parents=True, exist_ok=True)
    path = monthDir / f"{name}.md"
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_matched_verifier_and_skill_passes(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-code-golf",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "0.83",
            "datasetHash": _hex("dataset"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert errors == []


def test_unknown_verifier_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-bob-fake",
        {
            "verifier": "bob-random",  # not a 4★+
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert len(errors) == 1
    assert "bob-random" in errors[0]
    assert "not in the 4★+" in errors[0] or "not in the 4" in errors[0]


def test_unknown_skill_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-ghost",
        {
            "verifier": "alice",
            "skill": "alice/does-not-exist",
            "benchmark": "humaneval@v1.0",
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/real-skill"},
    )
    assert any("does-not-exist" in e for e in errors)


def test_missing_frontmatter_field_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-partial",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            # benchmark deliberately missing
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert any("benchmark" in e for e in errors)


def test_missing_frontmatter_block_rejected(script, tmp_path):
    monthDir = tmp_path / "docs" / "verifier-signoffs" / "2026-07"
    monthDir.mkdir(parents=True)
    (monthDir / "humaneval-alice-noyaml.md").write_text("no frontmatter here\n", encoding="utf-8")

    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills=set(),
    )
    assert any("frontmatter" in e for e in errors)


def test_bad_dataset_hash_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-shorthash",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "0.5",
            "datasetHash": "not-a-hash",
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert any("datasetHash" in e for e in errors)


def test_unversioned_benchmark_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-unversioned",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval",  # no @version
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert any("versioned" in e for e in errors)


def test_bad_iso_timestamp_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-tzless",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05 18:00:00",  # no T, no timezone
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert any("ISO 8601" in e or "attestedAt" in e for e in errors)


def test_non_numeric_score_rejected(script, tmp_path):
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-nan",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "very-good",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert any("score" in e.lower() for e in errors)


def test_empty_tree_passes(script, tmp_path):
    """No attestation files at all is not an error — the surface is opt-in."""
    (tmp_path / "docs" / "verifier-signoffs").mkdir(parents=True)
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/anything"},
    )
    assert errors == []


def test_readme_is_ignored(script, tmp_path):
    """README.md in the month dir must not be parsed as an attestation file."""
    monthDir = tmp_path / "docs" / "verifier-signoffs" / "2026-07"
    monthDir.mkdir(parents=True)
    (monthDir / "README.md").write_text("just docs\n", encoding="utf-8")
    _writeAttestation(
        tmp_path,
        "2026-07",
        "humaneval-alice-real",
        {
            "verifier": "alice",
            "skill": "alice/code-golf",
            "benchmark": "humaneval@v1.0",
            "score": "0.5",
            "datasetHash": _hex("d"),
            "attestedAt": "2026-07-05T18:00:00Z",
        },
    )
    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/code-golf"},
    )
    assert errors == []


def test_non_month_bucket_ignored(script, tmp_path):
    """Directories that don't match YYYY-MM (e.g. drafts/) are skipped."""
    draftsDir = tmp_path / "docs" / "verifier-signoffs" / "drafts"
    draftsDir.mkdir(parents=True)
    (draftsDir / "malformed.md").write_text("no frontmatter\n", encoding="utf-8")

    errors = script.checkBenchmarkAttestations(
        tmp_path / "docs" / "verifier-signoffs",
        verifiers={"alice"},
        knownSkills={"alice/x"},
    )
    assert errors == []
