from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evidence.scripts.verify_benchmark_sources import (  # noqa: E402
    classify_candidate,
    classify_registry_row,
    run,
)


def _catalog(status: str = "verified", *, scores: bool = True) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "benchmarks": [
            {
                "id": "humaneval@v1.0",
                "name": "HumanEval",
                "aliases": ["humaneval"],
                "status": status,
                "mode": "internal-ci" if status == "verified" else status,
                "unit": "pass@1",
                "sourceUrl": "https://example.com/humaneval",
                "methodologyUrl": "/benchmarks/humaneval-v1/",
                "defaultProvenance": "ci-reproduced" if status == "verified" else status,
                "scoring": {
                    "scoresTrustMagnitude": scores,
                    "requiredFields": [
                        "benchmarkId",
                        "score",
                        "unit",
                        "runAt",
                        "provenance",
                        "attestor",
                        "datasetHash",
                        "benchmarkInputHash",
                        "percentile",
                    ],
                },
                "push": {"enabled": False, "aliases": []},
            }
        ],
    }


def _item(row: dict) -> dict:
    return {
        "skillId": "example/skill",
        "path": "registry/named/example/skill.md",
        "evidenceIndex": 0,
        "row": row,
    }


def _scoring_row(**overrides: object) -> dict:
    row = {
        "type": "benchmark-result",
        "benchmarkId": "humaneval@v1.0",
        "score": 0.75,
        "unit": "pass@1",
        "runAt": "2026-07-06T10:44:08Z",
        "provenance": "ci-reproduced",
        "attestor": "https://github.com/gaia-research/gaia-skill-tree/actions/runs/1@abc123",
        "datasetHash": "a" * 64,
        "benchmarkInputHash": "b" * 64,
        "percentile": 92,
    }
    row.update(overrides)
    return row


def test_registry_row_scoring_eligible_when_verified_and_complete() -> None:
    result = classify_registry_row(_item(_scoring_row()), _catalog())

    assert result["status"] == "scoring-eligible"
    assert result["hardBlocker"] is False
    assert result["issues"] == []


def test_registry_row_blocks_incomplete_scoring_payload_without_failing_check() -> None:
    result = classify_registry_row(_item(_scoring_row(percentile=None)), _catalog())

    assert result["status"] == "blocked"
    assert result["hardBlocker"] is False
    assert any("percentile" in issue for issue in result["issues"])


def test_registry_row_hard_blocks_scoring_provenance_on_candidate_source() -> None:
    result = classify_registry_row(_item(_scoring_row()), _catalog(status="candidate", scores=False))

    assert result["status"] == "candidate-only"
    assert result["hardBlocker"] is True
    assert any("candidate" in issue for issue in result["issues"])


def test_legacy_vendor_claim_is_citation_only_not_hard_blocker() -> None:
    result = classify_registry_row(
        _item({"type": "benchmark-result", "source": "https://example.com/vendor", "class": "A"}),
        _catalog(),
    )

    assert result["status"] == "citation-only"
    assert result["hardBlocker"] is False
    assert any("missing benchmarkId" in issue for issue in result["issues"])


def test_candidate_manifest_classification_is_candidate_only() -> None:
    result = classify_candidate(
        {
            "target": "firecrawl/firecrawl-skills",
            "source": "https://github.com/firecrawl/firecrawl/issues/741",
            "benchmarkId": "firecrawl-scrape@2026-05",
            "status": "candidate",
            "missing": ["datasetHash", "benchmarkInputHash", "percentile"],
            "notes": "Motivating candidate only; no scoring row yet.",
        },
        _catalog(),
        1,
    )

    assert result["status"] == "candidate-only"
    assert result["hardBlocker"] is False
    assert any("not in the catalog" in issue for issue in result["issues"])
    assert any("datasetHash" in issue for issue in result["issues"])


def test_run_with_candidate_manifest_writes_report_and_check_ignores_candidates(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    named = root / "registry" / "named" / "example"
    named.mkdir(parents=True)
    (named / "skill.md").write_text(
        "---\n"
        "id: example/skill\n"
        "evidence:\n"
        "- type: benchmark-result\n"
        "  source: https://example.com/vendor\n"
        "  class: A\n"
        "---\n",
        encoding="utf-8",
    )
    catalog_path = root / "registry" / "benchmark-sources.json"
    catalog_path.write_text(json.dumps(_catalog()), encoding="utf-8")
    manifest_path = tmp_path / "candidates.jsonl"
    manifest_path.write_text(
        json.dumps({"target": "example/skill", "source": "https://example.com", "benchmarkId": "new@v1", "status": "candidate"}) + "\n",
        encoding="utf-8",
    )
    report_path = tmp_path / "report.md"

    code, report, results = run(
        argparse.Namespace(
            catalog=str(catalog_path),
            registry_root=str(root),
            candidate_manifest=str(manifest_path),
            report=str(report_path),
            check=True,
        )
    )

    assert code == 0
    assert report_path.exists()
    assert "Candidate manifest entries scanned: 1" in report
    assert {r["kind"] for r in results} == {"registry-row", "candidate-manifest"}
