from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from gaia_cli.arbor import (
    ArborError,
    checkStore,
    importSource,
    interpretReceipt,
    profilePath,
    readJson,
    replay,
    validateRecord,
    writeAtomic,
)

SKILL_HASH = "1" * 64
ARTIFACT_HASH = "2" * 64


def makeStore(tmpPath: Path) -> Path:
    contracts = Path(__file__).parents[1] / "registry" / "arbor" / "contracts"
    shutil.copytree(contracts, tmpPath / "registry" / "arbor" / "contracts")
    return tmpPath


def writeRecord(tmpPath: Path, name: str, record: dict) -> Path:
    path = tmpPath / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def declaration() -> dict:
    return {
        "schema": "gaia.arbor-expert-declaration/v1",
        "skill": {"id": "expert/example", "contentSha256": SKILL_HASH},
        "claims": [
            {
                "id": "human-review",
                "facet": "human-led",
                "conditions": "When irreversible publication requires a named reviewer.",
                "rationale": "The person retains the final external decision.",
                "authority": {"actor": "gaia-expert/alex", "basis": "operational use"},
                "expectation": {
                    "metric": "approval-errors",
                    "direction": "decrease",
                    "minimumEffect": 1.0,
                },
            },
            {
                "id": "model-draft",
                "facet": "model-led",
                "conditions": "When drafting is reversible and bounded by review.",
                "rationale": "The model performs the first complete pass.",
                "authority": {"actor": "gaia-expert/alex", "basis": "operational use"},
                "expectation": {
                    "metric": "draft-throughput",
                    "direction": "increase",
                    "minimumEffect": 2.0,
                },
            },
        ],
    }


def receipt(declarationDigest: str, claimId: str = "human-review") -> dict:
    return {
        "schema": "gaia.arbor-benchmark-receipt/v1",
        "skill": {"id": "expert/example", "contentSha256": SKILL_HASH},
        "target": {"declarationSha256": declarationDigest, "claimId": claimId},
        "benchmark": {"id": "focused-review", "version": "1"},
        "control": {
            "definition": "The same tasks without the declared capability.",
            "environment": {"model": "fixture-model", "harness": "fixture-harness"},
        },
        "treatment": {
            "definition": "The same tasks with the declared capability.",
            "environment": {"model": "fixture-model", "harness": "fixture-harness"},
        },
        "provenance": {
            "runner": "fixture-runner",
            "observedAt": "2026-08-24T12:00:00Z",
            "artifacts": [{"uri": "fixture://run/1", "sha256": ARTIFACT_HASH}],
        },
        "measurements": [
            {
                "metric": "approval-errors",
                "unit": "errors/task",
                "control": {"n": 20, "mean": 4.0},
                "treatment": {"n": 20, "mean": 2.0},
                "difference": {
                    "estimate": -2.0,
                    "confidenceInterval": {"lower": -3.0, "upper": -1.2, "confidence": 0.95},
                },
            }
        ],
    }


def test_dual_human_and_model_facets_are_independent(tmp_path):
    root = makeStore(tmp_path)
    source = writeRecord(tmp_path, "declaration.json", declaration())

    _, digest, created = importSource(source, root)
    assert created is True
    [profileFile] = replay(root)
    profile = readJson(profileFile)

    assert {claim["facet"] for claim in profile["claims"]} == {"human-led", "model-led"}
    assert {claim["support"] for claim in profile["claims"]} == {"expert-declared"}
    assert profile["sources"]["declarations"] == [digest]
    assert checkStore(root) == 2


def test_profile_recomputes_from_immutable_declaration_and_receipt(tmp_path):
    root = makeStore(tmp_path)
    declarationPath = writeRecord(tmp_path, "declaration.json", declaration())
    storedDeclaration, declarationDigest, _ = importSource(declarationPath, root)
    [profileFile] = replay(root)
    before = readJson(profileFile)

    receiptPath = writeRecord(tmp_path, "receipt.json", receipt(declarationDigest))
    storedReceipt, receiptDigest, _ = importSource(receiptPath, root)
    [sameProfileFile] = replay(root)
    after = readJson(sameProfileFile)

    assert profileFile == sameProfileFile
    assert readJson(storedDeclaration) == declaration()
    assert readJson(storedReceipt) == receipt(declarationDigest)
    support = {claim["id"]: claim["support"] for claim in after["claims"]}
    assert support == {"human-review": "benchmark-confirmed", "model-draft": "expert-declared"}
    assert before["inputDigest"] != after["inputDigest"]
    assert after["sources"]["benchmarkReceipts"] == [receiptDigest]
    assert checkStore(root) == 3


@pytest.mark.parametrize(
    ("estimate", "lower", "upper", "expected"),
    [
        (-2.0, -3.0, -1.2, "benchmark-confirmed"),
        (-1.2, -2.0, 0.2, "benchmark-qualified"),
        (1.0, 0.2, 1.8, "benchmark-revised"),
        (-0.2, -1.5, 0.8, "inconclusive"),
    ],
)
def test_receipt_interpretation_is_derived_from_measurements(
    estimate, lower, upper, expected
):
    record = receipt("3" * 64)
    difference = record["measurements"][0]["difference"]
    difference["estimate"] = estimate
    difference["confidenceInterval"]["lower"] = lower
    difference["confidenceInterval"]["upper"] = upper

    assert interpretReceipt(declaration()["claims"][0], record) == expected


def test_targeted_unresolved_measurement_is_inconclusive(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importSource(
        writeRecord(tmp_path, "declaration.json", declaration()), root
    )
    unresolved = receipt(declarationDigest)
    unresolved["measurements"][0]["metric"] = "another-metric"
    importSource(writeRecord(tmp_path, "receipt.json", unresolved), root)

    [profileFile] = replay(root)
    support = {claim["id"]: claim["support"] for claim in readJson(profileFile)["claims"]}
    assert support["human-review"] == "inconclusive"


def test_immutable_receipt_reuse_and_tamper_detection(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importSource(
        writeRecord(tmp_path, "declaration.json", declaration()), root
    )
    inputPath = writeRecord(tmp_path, "receipt.json", receipt(declarationDigest))
    stored, _, created = importSource(inputPath, root)
    assert created is True
    sameStored, _, createdAgain = importSource(inputPath, root)
    assert sameStored == stored
    assert createdAgain is False

    altered = readJson(stored)
    altered["measurements"][0]["control"]["mean"] = 99
    stored.write_text(json.dumps(altered), encoding="utf-8")
    with pytest.raises(ArborError, match="filename does not match its digest"):
        checkStore(root)


def test_atomic_generated_write_preserves_old_file_on_replace_failure(tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    path.write_bytes(b"old\n")

    def failReplace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("gaia_cli.arbor.os.replace", failReplace)
    with pytest.raises(OSError, match="simulated"):
        writeAtomic(path, b"new\n")

    assert path.read_bytes() == b"old\n"
    assert list(tmp_path.glob(".*.tmp")) == []


@pytest.mark.parametrize("field", ["stars", "rank", "trustMagnitude", "prestige", "tm"])
def test_prestige_fields_are_rejected_recursively(tmp_path, field):
    root = makeStore(tmp_path)
    record = declaration()
    record["claims"][0]["authority"][field] = "forbidden"

    with pytest.raises(ArborError, match="prestige field is forbidden"):
        validateRecord(record, root)


def test_receipt_rejects_conclusion_labels(tmp_path):
    root = makeStore(tmp_path)
    record = receipt("3" * 64)
    record["measurements"][0]["verdict"] = "confirmed"

    with pytest.raises(ArborError, match="benchmark conclusion field is forbidden"):
        validateRecord(record, root)


def test_profile_path_keeps_skill_identity_and_exact_hash_separate(tmp_path):
    root = makeStore(tmp_path)
    expected = root / "registry" / "arbor" / "profiles" / "expert" / "example" / f"{SKILL_HASH}.json"
    assert profilePath(root / "registry" / "arbor", "expert/example", SKILL_HASH) == expected
