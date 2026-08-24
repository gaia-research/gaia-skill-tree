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
    contentDigest,
    importSource,
    profilePath,
    readJson,
    replay,
    validateRecord,
    writeAtomic,
)

CANONICAL_BYTES = b'{"id":"example-skill","type":"basic"}\n'
SKILL_HASH = hashlib.sha256(CANONICAL_BYTES).hexdigest()
RUN_ARTIFACT_HASH = "2" * 64
TASK_HASH = "3" * 64
FIXTURE_HASH = "4" * 64
EVALUATOR_HASH = "5" * 64


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
        "declarationId": "alex-example-skill-v1",
        "declaredAt": "2026-08-24T10:00:00Z",
        "skill": {"id": skillId, "contentSha256": skillHash},
        "claims": [
            {
                "id": "human-review",
                "facet": "human-led",
                "conditions": "When irreversible publication requires a named reviewer.",
                "rationale": "The person retains the final external decision.",
                "authority": {"actor": "gaia-expert/alex", "basis": "operational use"},
            },
            {
                "id": "model-draft",
                "facet": "model-led",
                "conditions": "When drafting is reversible and bounded by review.",
                "rationale": "The model performs the first complete pass.",
                "authority": {"actor": "gaia-expert/alex", "basis": "operational use"},
            },
        ],
    }


def environment() -> dict:
    return {
        "model": "fixture-model",
        "harness": "fixture-harness",
        "artifacts": {
            "taskSha256": TASK_HASH,
            "fixtureSha256": FIXTURE_HASH,
            "evaluatorSha256": EVALUATOR_HASH,
        },
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
            "artifacts": [
                {"uri": "fixture://run/1", "sha256": RUN_ARTIFACT_HASH}
            ],
        },
        "measurements": [
            {
                "metric": "approval-errors",
                "unit": "errors/task",
                "control": {"value": 4.0, "count": 20},
                "treatment": {"value": 2.0, "count": 20},
                "difference": -2.0,
            }
        ],
    }


def interpretation(
    declarationDigest: str,
    receiptDigest: str,
    support: str = "benchmark-confirmed",
    supersedes: str | None = None,
) -> dict:
    record = {
        "schema": "gaia.arbor-interpretation/v1",
        "interpretationId": "alex-human-review-v1" if supersedes is None else "alex-human-review-v2",
        "interpretedAt": "2026-08-24T13:00:00Z" if supersedes is None else "2026-08-25T13:00:00Z",
        "skill": {"id": "example-skill", "contentSha256": SKILL_HASH},
        "target": {
            "declarationSha256": declarationDigest,
            "claimId": "human-review",
        },
        "authority": {"actor": "gaia-curator/alex", "basis": "governed review"},
        "support": support,
        "rationale": "The curator interpreted the linked focused observation.",
        "receiptSources": [receiptDigest],
    }
    if supersedes is not None:
        record["supersedesSha256"] = supersedes
    return record


def importDeclaration(root: Path, tmpPath: Path) -> tuple[Path, str, bool]:
    return importSource(writeRecord(tmpPath, "declaration.json", declaration()), root)


def test_dual_facets_and_declaration_identity_are_preserved(tmp_path):
    root = makeStore(tmp_path)
    _, digest, created = importDeclaration(root, tmp_path)

    assert created is True
    [profileFile] = replay(root)
    profile = readJson(profileFile)

    assert {claim["facet"] for claim in profile["claims"]} == {"human-led", "model-led"}
    assert {claim["support"] for claim in profile["claims"]} == {"expert-declared"}
    assert {claim["declarationId"] for claim in profile["claims"]} == {
        "alex-example-skill-v1"
    }
    assert {claim["declaredAt"] for claim in profile["claims"]} == {
        "2026-08-24T10:00:00Z"
    }
    assert profile["sources"]["declarations"] == [digest]
    assert checkStore(root) == 2


def test_receipt_is_observation_only_and_does_not_promote_declaration(tmp_path):
    root = makeStore(tmp_path)
    storedDeclaration, declarationDigest, _ = importDeclaration(root, tmp_path)
    [profileFile] = replay(root)
    before = readJson(profileFile)

    receiptRecord = receipt(declarationDigest)
    storedReceipt, receiptDigest, _ = importSource(
        writeRecord(tmp_path, "receipt.json", receiptRecord), root
    )
    [sameProfileFile] = replay(root)
    after = readJson(sameProfileFile)

    assert readJson(storedDeclaration) == declaration()
    assert readJson(storedReceipt) == receiptRecord
    assert {claim["support"] for claim in after["claims"]} == {"expert-declared"}
    assert after["sources"]["benchmarkReceipts"] == [receiptDigest]
    assert after["sources"]["interpretations"] == []
    assert before["inputDigest"] != after["inputDigest"]
    assert checkStore(root) == 3


def test_explicit_immutable_interpretation_controls_support_and_revision(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    _, receiptDigest, _ = importSource(
        writeRecord(tmp_path, "receipt.json", receipt(declarationDigest)), root
    )

    firstRecord = interpretation(declarationDigest, receiptDigest)
    _, firstDigest, _ = importSource(
        writeRecord(tmp_path, "interpretation-1.json", firstRecord), root
    )
    [profileFile] = replay(root)
    firstProfile = readJson(profileFile)
    support = {claim["id"]: claim["support"] for claim in firstProfile["claims"]}
    assert support == {"human-review": "benchmark-confirmed", "model-draft": "expert-declared"}
    humanClaim = next(claim for claim in firstProfile["claims"] if claim["id"] == "human-review")
    assert humanClaim["interpretationSource"] == firstDigest

    revised = interpretation(
        declarationDigest, receiptDigest, "benchmark-revised", supersedes=firstDigest
    )
    _, revisedDigest, _ = importSource(
        writeRecord(tmp_path, "interpretation-2.json", revised), root
    )
    replay(root)
    revisedProfile = readJson(profileFile)
    humanClaim = next(claim for claim in revisedProfile["claims"] if claim["id"] == "human-review")
    assert humanClaim["support"] == "benchmark-revised"
    assert humanClaim["interpretationSource"] == revisedDigest
    assert revisedProfile["sources"]["interpretations"] == sorted(
        [firstDigest, revisedDigest]
    )
    assert checkStore(root) == 5


@pytest.mark.parametrize("support", ["benchmark-qualified", "inconclusive"])
def test_governed_interpretation_persists_qualified_or_inconclusive_support(
    tmp_path, support
):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    _, receiptDigest, _ = importSource(
        writeRecord(tmp_path, "receipt.json", receipt(declarationDigest)), root
    )
    _, interpretationDigest, _ = importSource(
        writeRecord(
            tmp_path,
            "interpretation.json",
            interpretation(declarationDigest, receiptDigest, support),
        ),
        root,
    )

    [profileFile] = replay(root)
    humanClaim = next(
        claim for claim in readJson(profileFile)["claims"] if claim["id"] == "human-review"
    )
    assert humanClaim["support"] == support
    assert humanClaim["interpretationSource"] == interpretationDigest


def test_expert_declared_remains_a_default_not_an_interpretation_outcome(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    _, receiptDigest, _ = importSource(
        writeRecord(tmp_path, "receipt.json", receipt(declarationDigest)), root
    )
    record = interpretation(declarationDigest, receiptDigest, "expert-declared")

    with pytest.raises(ArborError, match="expert-declared.*is not one of"):
        validateRecord(record, root)


def test_parallel_interpretation_requires_explicit_supersession(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    _, receiptDigest, _ = importSource(
        writeRecord(tmp_path, "receipt.json", receipt(declarationDigest)), root
    )
    importSource(
        writeRecord(
            tmp_path,
            "interpretation-1.json",
            interpretation(declarationDigest, receiptDigest),
        ),
        root,
    )
    competing = interpretation(declarationDigest, receiptDigest, "benchmark-revised")
    competing["interpretationId"] = "competing-review"

    with pytest.raises(ArborError, match="must supersede the active source"):
        importSource(writeRecord(tmp_path, "competing.json", competing), root)


def test_receipt_requires_exact_task_fixture_and_evaluator_hashes(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    record = receipt(declarationDigest)
    del record["control"]["environment"]["artifacts"]["fixtureSha256"]

    with pytest.raises(ArborError, match="fixtureSha256.*required"):
        validateRecord(record, root)


def test_measurements_do_not_require_interval_or_automatic_difference(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    record = receipt(declarationDigest)
    del record["measurements"][0]["difference"]

    assert validateRecord(record, root) == "gaia.arbor-benchmark-receipt/v1"


def test_new_declaration_admission_verifies_generic_and_named_exact_bytes(tmp_path):
    root = makeStore(tmp_path)
    namedBytes = b"---\nid: expert/named-example\n---\n# Named example\n"
    named = root / "registry" / "named" / "expert" / "named-example.md"
    named.parent.mkdir(parents=True)
    named.write_bytes(namedBytes)
    namedHash = hashlib.sha256(namedBytes).hexdigest()

    assert checkStore(
        root,
        writeRecord(tmp_path, "named.json", declaration("expert/named-example", namedHash)),
    ) == 1
    with pytest.raises(ArborError, match="canonical skill hash mismatch"):
        checkStore(
            root,
            writeRecord(tmp_path, "altered.json", declaration("expert/named-example", "0" * 64)),
        )
    with pytest.raises(ArborError, match="canonical skill id does not exist"):
        importSource(
            writeRecord(tmp_path, "missing.json", declaration("missing-skill", SKILL_HASH)),
            root,
        )


def test_historical_sources_survive_canonical_evolution(tmp_path):
    root = makeStore(tmp_path)
    declarationInput = writeRecord(tmp_path, "declaration.json", declaration())
    stored, declarationDigest, created = importSource(declarationInput, root)
    assert created is True
    [profile] = replay(root)
    originalProfile = profile.read_bytes()

    canonical = root / "registry" / "nodes" / "basic" / "example-skill.json"
    canonical.write_bytes(b'{"id":"example-skill","type":"fusion","version":2}\n')

    assert checkStore(root) == 2
    assert checkStore(root, declarationInput) == 1
    assert replay(root) == [profile]
    assert profile.read_bytes() == originalProfile
    assert importSource(declarationInput, root) == (stored, declarationDigest, False)

    changed = declaration()
    changed["claims"][0]["rationale"] = "Different source, stale skill pin."
    with pytest.raises(ArborError, match="canonical skill hash mismatch"):
        importSource(writeRecord(tmp_path, "stale-new.json", changed), root)


def test_declaration_preflight_rejects_duplicate_claim_or_declaration_identity(tmp_path):
    root = makeStore(tmp_path)
    importDeclaration(root, tmp_path)
    duplicateClaim = declaration()
    duplicateClaim["declarationId"] = "alex-example-skill-v2"
    duplicateClaim["claims"] = [copy.deepcopy(duplicateClaim["claims"][0])]
    duplicateClaim["claims"][0]["rationale"] = "A colliding claim id."
    with pytest.raises(ArborError, match="duplicate Arbor claim id"):
        importSource(writeRecord(tmp_path, "duplicate-claim.json", duplicateClaim), root)

    duplicateDeclaration = declaration()
    duplicateDeclaration["claims"] = [copy.deepcopy(duplicateDeclaration["claims"][1])]
    duplicateDeclaration["claims"][0]["id"] = "new-model-claim"
    with pytest.raises(ArborError, match="duplicate Arbor declaration id"):
        importSource(
            writeRecord(tmp_path, "duplicate-declaration.json", duplicateDeclaration), root
        )


def test_environment_mismatch_and_bad_time_are_rejected_without_poison(tmp_path):
    root = makeStore(tmp_path)
    _, declarationDigest, _ = importDeclaration(root, tmp_path)
    mismatched = receipt(declarationDigest)
    mismatched["treatment"]["environment"].update(model="other-model")
    with pytest.raises(ArborError, match="environments must be equivalent"):
        importSource(writeRecord(tmp_path, "mismatched.json", mismatched), root)

    badTime = receipt(declarationDigest)
    badTime["provenance"]["observedAt"] = "not-a-date"
    with pytest.raises(ArborError, match="not a 'date-time'"):
        importSource(writeRecord(tmp_path, "bad-time.json", badTime), root)

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

    operations = (
        lambda: importSource(source, root),
        lambda: checkStore(root),
        lambda: replay(root),
    )
    for operation in operations:
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
    ["verdict", "result", "assessment", "conclusion", "support"],
)
def test_receipt_interpretation_fields_are_rejected_recursively(tmp_path, field):
    root = makeStore(tmp_path)
    record = receipt("6" * 64)
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
    expected = (
        root
        / "registry"
        / "arbor"
        / "profiles"
        / "example-skill"
        / f"{SKILL_HASH}.json"
    )
    assert profilePath(
        root / "registry" / "arbor", "example-skill", SKILL_HASH
    ) == expected


def test_digest_is_stable_for_governed_records():
    record = declaration()
    assert contentDigest(record) == contentDigest(json.loads(json.dumps(record)))
