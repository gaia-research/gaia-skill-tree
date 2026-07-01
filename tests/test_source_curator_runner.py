from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import jsonschema

from gaia_cli import sourceCuration

REPO_ROOT = Path(__file__).resolve().parents[1]


def makeRoot(tmpPath: Path) -> Path:
    root = tmpPath / "repo"
    schemaDir = root / "registry" / "schema"
    schemaDir.mkdir(parents=True)
    for schemaPath in (REPO_ROOT / "registry" / "schema").glob("*.schema.json"):
        shutil.copy(schemaPath, schemaDir / schemaPath.name)
    return root


def test_dry_run_runner_emits_deterministic_schema_valid_report(tmp_path):
    root = makeRoot(tmp_path)

    report, path = sourceCuration.runDryRun(
        rootDir=root,
        runId="20260702-dry-run-test",
        generatedAt="2026-07-02T14:00:00Z",
    )

    assert path == root / "generated-output" / "source-curation" / "20260702-dry-run-test" / "report.json"
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert report["reportId"] == "20260702-dry-run-test"
    assert report["generatedAt"] == "2026-07-02T14:00:00Z"
    assert report["generatedBy"] == "nova-gaia"
    assert report["dryRun"] is True
    assert report["pipelinePhase"] == "discovery"
    assert len(report["proposals"]) == 2
    assert [proposal["proposalId"] for proposal in report["proposals"]] == [
        "mattpocock-grill-me-90af940b-20260702",
        "karpathy-autoresearch-02e79a9c-20260702",
    ]

    sourceCuration.validateReport(report, root)


def test_dry_run_runner_forces_nova_gaia_and_dry_run_from_seed_file(tmp_path):
    root = makeRoot(tmp_path)
    seedPath = tmp_path / "seed.json"
    seedPath.write_text(
        json.dumps(
            [
                {
                    "skillId": "alice/research-helper",
                    "source": "https://example.com/research-helper",
                    "evidenceType": "social-signal",
                    "crawlerBackend": "fixture-discovery",
                    "confidence": 0.9,
                    "rationale": "Seeded dry-run source that should remain review-only.",
                    "dryRun": False,
                    "discoveredBy": "rogue-bot",
                    "existingEvidenceCheck": {"checked": True, "duplicate": False},
                }
            ]
        ),
        encoding="utf-8",
    )

    report, _ = sourceCuration.runDryRun(
        rootDir=root,
        runId="20260702-seed-test",
        generatedAt="2026-07-02T14:00:00Z",
        inputPath=str(seedPath),
    )

    proposal = report["proposals"][0]
    assert report["generatedBy"] == "nova-gaia"
    assert report["dryRun"] is True
    assert proposal["discoveredBy"] == "nova-gaia"
    assert proposal["dryRun"] is True


def test_dry_run_runner_rejects_report_if_identity_is_changed(tmp_path):
    root = makeRoot(tmp_path)
    report = sourceCuration.buildReport(
        sourceCuration.defaultSeeds(),
        "20260702-invalid-identity",
        "2026-07-02T14:00:00Z",
    )
    report["generatedBy"] = "rogue-bot"

    with pytest.raises(jsonschema.ValidationError):
        sourceCuration.validateReport(report, root)


def test_dry_run_runner_rejects_invalid_generated_at_format(tmp_path):
    root = makeRoot(tmp_path)
    report = sourceCuration.buildReport(
        sourceCuration.defaultSeeds(),
        "20260702-invalid-generated-at",
        "not-a-date-time",
    )

    with pytest.raises(jsonschema.ValidationError):
        sourceCuration.validateReport(report, root)


def test_dry_run_runner_rejects_output_path_outside_source_curation_dir(tmp_path):
    root = makeRoot(tmp_path)
    forbidden = root / "registry" / "named" / "bad.md"

    with pytest.raises(ValueError):
        sourceCuration.runDryRun(
            rootDir=root,
            runId="20260702-bad-output",
            generatedAt="2026-07-02T14:00:00Z",
            outputPath="registry/named/bad.md",
        )

    assert not forbidden.exists()


def test_dry_run_runner_filters_duplicates_and_low_confidence(tmp_path):
    root = makeRoot(tmp_path)
    seeds = [
        {
            "skillId": "alice/research-helper",
            "source": "https://example.com/duplicate",
            "evidenceType": "social-signal",
            "crawlerBackend": "fixture-discovery",
            "confidence": 0.8,
            "rationale": "Duplicate seed should be dropped before the report is written.",
            "existingEvidenceCheck": {"checked": True, "duplicate": True, "existingIndex": 0},
        },
        {
            "skillId": "alice/research-helper",
            "source": "https://example.com/weak",
            "evidenceType": "social-signal",
            "crawlerBackend": "fixture-discovery",
            "confidence": 0.1,
            "rationale": "Low confidence seed should be dropped before the report is written.",
            "existingEvidenceCheck": {"checked": True, "duplicate": False},
        },
    ]
    seedPath = tmp_path / "seed.json"
    seedPath.write_text(json.dumps(seeds), encoding="utf-8")

    report, _ = sourceCuration.runDryRun(
        rootDir=root,
        runId="20260702-filter-test",
        generatedAt="2026-07-02T14:00:00Z",
        inputPath=str(seedPath),
    )

    assert report["proposals"] == []
    assert report["summary"]["duplicatesDropped"] == 1
    assert report["summary"]["belowConfidenceDropped"] == 1
    sourceCuration.validateReport(report, root)


def test_dry_run_runner_does_not_mutate_registry_files(tmp_path):
    root = makeRoot(tmp_path)
    namedDir = root / "registry" / "named" / "alice"
    namedDir.mkdir(parents=True)
    sentinel = namedDir / "skill.md"
    sentinel.write_text("original registry content\n", encoding="utf-8")

    before = sentinel.read_text(encoding="utf-8")
    report, path = sourceCuration.runDryRun(
        rootDir=root,
        runId="20260702-no-mutation",
        generatedAt="2026-07-02T14:00:00Z",
    )

    assert sentinel.read_text(encoding="utf-8") == before
    assert path.is_file()
    assert path.is_relative_to(root / "generated-output" / "source-curation")
    assert report["generatedBy"] == "nova-gaia"
