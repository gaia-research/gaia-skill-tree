from __future__ import annotations

import copy
import hashlib
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

CANONICAL_BYTES = b'{"id":"example-skill","type":"basic"}\n'
SKILL_HASH = hashlib.sha256(CANONICAL_BYTES).hexdigest()
ARTIFACT_HASH = "2" * 64
TASK_SET_HASH = "3" * 64
SEED_HASH = "4" * 64


def makeStore(tmpPath: Path) -> Path:
    contracts = Path(__file__).parents[1] / "registry" / "arbor" / "contracts"
    shutil.copytree(contracts, tmpPath / "registry" / "arbor" / "contracts")
    source = tmpPath / "registry" / "nodes" / "basic" / "example-skill.json"
    source.parent.mkdir(parents=True)
    source.write_bytes(CANONICAL_BYTES)
    return tmpPath


def writeRecord(tmpPath: Path, name: str, record: dict) -> Path:
    path = tmpPath / name
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def declaration(skillId: str = "example-skill", skillHash: str = SKILL_HASH) -> dict:
    return {
        "schema": "gaia.arbor-expert-declaration/v1",
        "skill": {"id": skillId, "contentSha256": skillHash},
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


def environment() -> dict:
    return {
        "model": "fixture-model",
        "harness": "fixture-harness",
        "taskSetSha256": TASK_SET_HASH,
        "seedSha256": SEED_HASH,
    }


def receipt(declarationDigest: str, claimId: str = "human-review") -> dict:
    return {
        "schema": "gaia.arbor-benchmark-receipt/v1",
        "skill": {"id": "example-skill", "contentSha256": SKILL_HASH},
        "target": {"declarationSha256": declarationDigest, "claimId": claimId},
        "benchmark": {"id": "focused-review", "version": "1"},
        "control": {
            "definition": "The same tasks without the declared capability.",
            "environment": environment(),
        },
        "treatment": {
            "definition": "The same tasks with the declared capability.",
            "environment": environment(),
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
                    "confidenceInterval": {
                        "lower": -3.0,
                        "upper": -1.2,
                        "confidence": 0.95,
                    },
                },
            }
        ],
    }


def importDeclaration(root: Path, tmpPath: Path) -> tuple[Path, str, bool]:
    return importSource(writeRecord(tmpPath, "declaration.json", declaration()), root)


def test_dual_human_and_model_facets_are_independent(tmp_path):
    root = makeStore(tmp_path)
    _, digest, created = importDeclaration(root, tmp_path)

    assert created is True
    [profileFile] = replay(root)
    profile = readJson(profileFile)

    assert {claim["facet"] for claim in profile["claims"]} == {"human-led", "model-led"}
    assert {claim["support"] for claim in profile["claims"]} == {"expert-declared"}
    assert profile["sources"]["declarations"] == [digest]
    assert checkStore(root) == 2


def test_profile_recomputes_from_immutable_declaration_and_receipt(tmp_path):
    root = makeStore(tmp_path)
    storedDeclaration, declarationDigest, _ = importDeclaration(root, tmp_path)
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
    record = receipt("5" * 64)
    difference = record["measurements"][0]["difference"]
    difference["estimate"] = estimate
    difference["confidenceInterval"]["lower"] = lower
    difference["confidenceInterval"]["upper"] = upper

    assert interpretReceipt(declaration()["claims"][0], record) == expected


def test_targeted_unresolved_measurement_is_inconclusive_but_untargeted_is_unchanged(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    unresolved = receipt(declarationDigest)
    unresolved["measurements"][0]["metric"] = "another-metric"
    importSource(writeRecord(tmp_path, "receipt.json", unresolved), root)

    [profileFile] = replay(root)
    support = {claim["id"]: claim["support"] for claim in readJson(profileFile)["claims"]}
    assert support == {"human-review": "inconclusive", "model-draft": "expert-declared"}


def test_canonical_exact_bytes_are_verified_for_generic_and_named_skills(tmp_path):
    root = makeStore(tmp_path)
    namedBytes = b"---\nid: expert/named-example\n---\n# Named example\n"
    named = root / "registry" / "named" / "expert" / "named-example.md"
    named.parent.mkdir(parents=True)
    named.write_bytes(namedBytes)
    namedHash = hashlib.sha256(namedBytes).hexdigest()

    validateRecord(declaration("expert/named-example", namedHash), root)
    altered = declaration("expert/named-example", "0" * 64)
    with pytest.raises(ArborError, match="canonical skill hash mismatch"):
        validateRecord(altered, root)
    with pytest.raises(ArborError, match="canonical skill id does not exist"):
        validateRecord(declaration("missing-skill", SKILL_HASH), root)


def test_canonical_source_change_breaks_check_and_replay(tmp_path):
    root = makeStore(tmp_path)
    importDeclaration(root, tmp_path)
    [profile] = replay(root)
    before = profile.read_bytes()
    canonical = root / "registry" / "nodes" / "basic" / "example-skill.json"
    canonical.write_bytes(CANONICAL_BYTES + b" ")

    with pytest.raises(ArborError, match="canonical skill hash mismatch"):
        checkStore(root)
    with pytest.raises(ArborError, match="canonical skill hash mismatch"):
        replay(root)
    assert profile.read_bytes() == before


def test_declaration_preflight_rejects_cross_source_duplicate_without_poison(tmp_path):
    root = makeStore(tmp_path)
    importDeclaration(root, tmp_path)
    second = declaration()
    second["claims"] = [copy.deepcopy(second["claims"][0])]
    second["claims"][0]["rationale"] = "A distinct declaration with a colliding claim id."

    with pytest.raises(ArborError, match="duplicate Arbor claim id"):
        importSource(writeRecord(tmp_path, "duplicate.json", second), root)

    assert len(list((root / "registry" / "arbor" / "sources" / "declarations").glob("*.json"))) == 1


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record["measurements"][0]["difference"].update(estimate=-1.5), "treatment.mean - control.mean"),
        (lambda record: record["measurements"][0]["difference"]["confidenceInterval"].update(lower=-3.0, upper=-2.5), "outside confidence interval"),
        (lambda record: record["treatment"]["environment"].update(model="other-model"), "environments must be equivalent"),
        (lambda record: record["provenance"].update(observedAt="not-a-date"), "not a 'date-time'"),
    ],
)
def test_contradictory_receipts_are_rejected_without_poison(tmp_path, mutate, message):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    record = receipt(declarationDigest)
    mutate(record)

    with pytest.raises(ArborError, match=message):
        importSource(writeRecord(tmp_path, "contradictory.json", record), root)

    receiptRoot = root / "registry" / "arbor" / "sources" / "receipts"
    assert not receiptRoot.exists() or list(receiptRoot.glob("*.json")) == []


def test_immutable_receipt_reuse_and_tamper_detection(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    inputPath = writeRecord(tmp_path, "receipt.json", receipt(declarationDigest))
    stored, _, created = importSource(inputPath, root)
    assert created is True
    sameStored, _, createdAgain = importSource(inputPath, root)
    assert sameStored == stored
    assert createdAgain is False

    stored.write_bytes(stored.read_bytes() + b" ")
    with pytest.raises(ArborError, match="not canonically serialized"):
        checkStore(root)


def test_replay_reconciles_stale_generated_profiles(tmp_path):
    root = makeStore(tmp_path)
    importDeclaration(root, tmp_path)
    [expected] = replay(root)
    stale = expected.parent / ("f" * 64 + ".json")
    stale.write_text("{}\n", encoding="utf-8")

    assert replay(root) == [expected]
    assert expected.is_file()
    assert not stale.exists()


def test_store_lock_blocks_import_check_and_replay(tmp_path):
    root = makeStore(tmp_path)
    lock = root / "registry" / "arbor" / ".store-lock"
    lock.mkdir()
    source = writeRecord(tmp_path, "declaration.json", declaration())

    for operation in (lambda: importSource(source, root), lambda: checkStore(root), lambda: replay(root)):
        with pytest.raises(ArborError, match="store is locked"):
            operation()


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


@pytest.mark.parametrize(
    "field",
    ["stars", "rank", "trustMagnitude", "prestige", "tm", "trust", "grade"],
)
def test_prestige_fields_are_rejected_recursively(tmp_path, field):
    root = makeStore(tmp_path)
    record = declaration()
    record["claims"][0]["authority"][field] = "forbidden"

    with pytest.raises(ArborError, match="prestige field is forbidden"):
        validateRecord(record, root)


@pytest.mark.parametrize(
    "field",
    ["verdict", "result", "interpretation", "assessment", "conclusion", "support"],
)
def test_source_interpretation_fields_are_rejected_recursively(tmp_path, field):
    root = makeStore(tmp_path)
    record = receipt("5" * 64)
    record["provenance"][field] = "confirmed"

    with pytest.raises(ArborError, match="source interpretation field is forbidden"):
        validateRecord(record, root)


@pytest.mark.parametrize("skillId", ["expert//example", "expert/example/extra", "expert/..", "expert/"])
def test_schema_and_profile_path_share_exact_safe_grammar(tmp_path, skillId):
    root = makeStore(tmp_path)
    with pytest.raises(ArborError, match="invalid Arbor record"):
        validateRecord(declaration(skillId, SKILL_HASH), root)
    with pytest.raises(ArborError, match="unsafe Arbor skill id"):
        profilePath(root / "registry" / "arbor", skillId, SKILL_HASH)


def test_profile_path_keeps_skill_identity_and_exact_hash_separate(tmp_path):
    root = makeStore(tmp_path)
    expected = root / "registry" / "arbor" / "profiles" / "example-skill" / f"{SKILL_HASH}.json"
    assert profilePath(root / "registry" / "arbor", "example-skill", SKILL_HASH) == expected
