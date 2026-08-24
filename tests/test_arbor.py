"""Focused contract, replay, atomicity, and CLI tests for Arbor ingestion."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from gaia_cli.arbor import (
    HEADER,
    ArborError,
    canonicalJson,
    checkProjection,
    importBundle,
    loadSchemas,
    replayProjection,
)
from gaia_cli.main import main


REPO_ROOT = Path(__file__).resolve().parents[1]
HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64


def decision(skillId: str = "alice/example", skillHash: str = HEX_A) -> dict:
    return {
        "skillId": skillId,
        "skillMdSha256": skillHash,
        "decision": "accepted",
        "stamps": {
            "heaven-native": True,
            "hell-safe": {
                "tier": "high",
                "qualifiers": {
                    "network": "denied",
                    "filesystem": "read-only",
                    "sandbox": "required",
                    "approval": "none",
                    "cost": "metered",
                },
            },
            "ultra-ready": True,
        },
        "primaryStamp": "heaven-native",
        "denyStatus": {"status": "clear"},
        "ledgerRefs": [{"schema": "hh-ledger/v1", "recordSha256": HEX_C}],
    }


def bundle(*decisions: dict, sourceDigest: str = HEX_B) -> dict:
    return {"schema": "hh-stamp/v1", "sourceDigest": sourceDigest, "decisions": list(decisions or [decision()])}


@pytest.fixture
def arborRepo(tmp_path: Path) -> Path:
    schemaRoot = tmp_path / "registry" / "schema"
    schemaRoot.mkdir(parents=True)
    for name in ("hh-stamp.schema.json", "arborStamp.schema.json"):
        shutil.copyfile(REPO_ROOT / "registry" / "schema" / name, schemaRoot / name)
    arborRoot = tmp_path / "registry" / "arbor"
    (arborRoot / "sources").mkdir(parents=True)
    (arborRoot / "stamps.jsonl").write_text(HEADER, encoding="utf-8", newline="")
    return tmp_path


def writeBundle(root: Path, value: object, name: str = "bundle.json", pretty: bool = False) -> Path:
    path = root / name
    path.write_text(json.dumps(value, indent=2 if pretty else None), encoding="utf-8", newline="")
    return path


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def projectionRows(root: Path) -> list[dict]:
    lines = (root / "registry" / "arbor" / "stamps.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[1:]]


def test_schemas_are_valid_and_mirrored_byte_for_byte():
    for name in ("hh-stamp.schema.json", "arborStamp.schema.json"):
        canonical = REPO_ROOT / "registry" / "schema" / name
        bundled = REPO_ROOT / "src" / "gaia_cli" / "data" / "registry" / "schema" / name
        assert canonical.read_bytes() == bundled.read_bytes()
        jsonschema.Draft202012Validator.check_schema(json.loads(canonical.read_text(encoding="utf-8")))


def test_valid_multiplicative_import_preserves_tier_qualifiers_and_exact_hash(arborRepo: Path):
    digest, count, written = importBundle(arborRepo, writeBundle(arborRepo, bundle(decision()), pretty=True))
    assert written is True
    assert count == 1
    assert len(digest) == 64
    retained = arborRepo / "registry" / "arbor" / "sources" / f"{digest}.json"
    assert retained.read_bytes() == canonicalJson(bundle(decision()))
    row = projectionRows(arborRepo)[0]
    assert row["acceptance"]["skillMdSha256"] == HEX_A
    assert set(row["acceptance"]["stamps"]) == {"heaven-native", "hell-safe", "ultra-ready"}
    assert row["acceptance"]["stamps"]["hell-safe"] == decision()["stamps"]["hell-safe"]
    checkProjection(arborRepo)


def test_skill_hash_binds_exact_raw_bytes_without_newline_normalization(arborRepo: Path):
    rawSkill = b"---\nname: Exact bytes\n---\nbody\n"
    exactDigest = hashlib.sha256(rawSkill).hexdigest()
    assert exactDigest != hashlib.sha256(rawSkill.replace(b"\n", b"\r\n")).hexdigest()
    importBundle(
        arborRepo,
        writeBundle(arborRepo, bundle(decision(skillHash=exactDigest))),
    )
    assert projectionRows(arborRepo)[0]["acceptance"]["skillMdSha256"] == exactDigest


@pytest.mark.parametrize(
    "mutate",
    [
        lambda item: item["stamps"]["hell-safe"].update(tier="ceiling"),
        lambda item: item["stamps"]["hell-safe"]["qualifiers"].update(network="sometimes"),
        lambda item: item["stamps"]["hell-safe"].pop("qualifiers"),
        lambda item: item.update(skillMdSha256="sha256:" + HEX_A),
        lambda item: item.update(skillId="Alice/Example"),
    ],
)
def test_closed_tier_qualifiers_sha_and_identity_contract(arborRepo: Path, mutate):
    item = decision()
    mutate(item)
    with pytest.raises(ArborError):
        importBundle(arborRepo, writeBundle(arborRepo, bundle(item)))


def test_primary_deny_and_no_stamp_coherence(arborRepo: Path):
    badPrimary = decision()
    badPrimary["primaryStamp"] = "hell-safe"
    badPrimary["stamps"].pop("hell-safe")
    with pytest.raises(ArborError, match="primary stamp"):
        importBundle(arborRepo, writeBundle(arborRepo, bundle(badPrimary), "primary.json"))

    denied = decision()
    denied["denyStatus"] = {"status": "denied", "reasons": ["safety-endpoint"]}
    with pytest.raises(ArborError, match="cannot be hell-safe"):
        importBundle(arborRepo, writeBundle(arborRepo, bundle(denied), "deny.json"))

    noStamp = decision()
    noStamp["decision"] = "no-stamp"
    noStamp.pop("stamps")
    noStamp.pop("primaryStamp")
    noStamp["denyStatus"] = {"status": "denied", "reasons": ["unbounded-cost"]}
    importBundle(arborRepo, writeBundle(arborRepo, bundle(noStamp), "none.json"))
    accepted = projectionRows(arborRepo)[0]["acceptance"]
    assert accepted["decision"] == "no-stamp"
    assert "primaryStamp" not in accepted and "stamps" not in accepted
    assert accepted["ledgerRefs"]


@pytest.mark.parametrize(
    "change",
    [
        lambda item: item.update(ledgerRefs=[]),
        lambda item: item.update(ledgerRefs=[{"schema": "hh-ledger/v1", "recordSha256": ""}]),
        lambda item: item.update(ledgerRefs=[{"schema": "hh-ledger/v1", "recordSha256": HEX_C, "url": "https://example.test/latest"}]),
        lambda item: item.update(rank="Apex"),
        lambda item: item.update(stars=6),
        lambda item: item.update(trustMagnitude=999),
    ],
)
def test_immutable_nonempty_receipts_and_prestige_fields_rejected(arborRepo: Path, change):
    item = decision()
    change(item)
    with pytest.raises(ArborError):
        importBundle(arborRepo, writeBundle(arborRepo, bundle(item)))


def test_source_digest_must_be_exact_lowercase_sha(arborRepo: Path):
    for digest in ("", "A" * 64, "sha256:" + HEX_B):
        with pytest.raises(ArborError):
            importBundle(arborRepo, writeBundle(arborRepo, bundle(decision(), sourceDigest=digest)))


def test_import_is_canonical_idempotent_and_replay_is_deterministic(arborRepo: Path):
    second = decision("zeta/skill", HEX_D)
    first = decision("alpha/skill", HEX_A)
    path = writeBundle(arborRepo, bundle(second, first), pretty=True)
    digest, count, written = importBundle(arborRepo, path)
    before = snapshot(arborRepo / "registry" / "arbor")
    assert importBundle(arborRepo, path) == (digest, count, False)
    assert snapshot(arborRepo / "registry" / "arbor") == before
    rows = projectionRows(arborRepo)
    assert [row["acceptance"]["skillId"] for row in rows] == ["alpha/skill", "zeta/skill"]
    projectionPath = arborRepo / "registry" / "arbor" / "stamps.jsonl"
    assert projectionPath.read_bytes().endswith(b"\n")
    projectionPath.write_text("drift\n", encoding="utf-8")
    with pytest.raises(ArborError, match="drift"):
        checkProjection(arborRepo)
    assert replayProjection(arborRepo) == 2
    assert projectionPath.read_bytes() == before["stamps.jsonl"]


def test_duplicate_and_conflicting_identity_or_source_claims_rejected(arborRepo: Path):
    duplicate = bundle(decision(), copy.deepcopy(decision()))
    with pytest.raises(ArborError, match="duplicate skill identity"):
        importBundle(arborRepo, writeBundle(arborRepo, duplicate, "duplicate.json"))

    importBundle(arborRepo, writeBundle(arborRepo, bundle(decision()), "first.json"))
    for value, message in (
        (bundle(decision(skillHash=HEX_D), sourceDigest=HEX_D), "conflicting identity/source"),
        (bundle(decision("bob/other"), sourceDigest=HEX_B), "conflicting bundles claim sourceDigest"),
    ):
        with pytest.raises(ArborError, match=message):
            importBundle(arborRepo, writeBundle(arborRepo, value, "conflict.json"))


def test_malformed_or_conflicting_import_leaves_canonical_files_byte_unchanged(arborRepo: Path):
    importBundle(arborRepo, writeBundle(arborRepo, bundle(decision()), "valid.json"))
    before = snapshot(arborRepo / "registry" / "arbor")
    malformed = arborRepo / "malformed.json"
    malformed.write_bytes(b'{"schema":"hh-stamp/v1",')
    with pytest.raises(ArborError):
        importBundle(arborRepo, malformed)
    assert snapshot(arborRepo / "registry" / "arbor") == before

    conflict = bundle(decision(skillHash=HEX_D), sourceDigest=HEX_D)
    with pytest.raises(ArborError):
        importBundle(arborRepo, writeBundle(arborRepo, conflict, "conflict.json"))
    assert snapshot(arborRepo / "registry" / "arbor") == before


def test_invalid_existing_state_blocks_import_without_writes(arborRepo: Path):
    sourceRoot = arborRepo / "registry" / "arbor" / "sources"
    (sourceRoot / "not-a-digest.json").write_text("{}\n", encoding="utf-8")
    before = snapshot(arborRepo / "registry" / "arbor")
    with pytest.raises(ArborError):
        importBundle(arborRepo, writeBundle(arborRepo, bundle(decision())))
    assert snapshot(arborRepo / "registry" / "arbor") == before


def addVerifierIndex(root: Path) -> None:
    (root / "registry" / "named-skills.json").write_text(
        json.dumps({"buckets": {"x": [{"contributor": "alice", "level": "4★"}]}}),
        encoding="utf-8",
    )


def test_cli_check_is_read_only_but_import_and_replay_require_authorization(arborRepo: Path, monkeypatch, capsys):
    addVerifierIndex(arborRepo)
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "bob")
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(arborRepo), "dev", "arbor", "check"])
    main()
    assert "byte-consistent" in capsys.readouterr().out

    source = writeBundle(arborRepo, bundle(decision()))
    for action in (["import", str(source)], ["replay"]):
        monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(arborRepo), "dev", "arbor", *action])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "Verifier" in capsys.readouterr().err


def test_normal_validate_path_detects_arbor_drift(arborRepo: Path, monkeypatch):
    from gaia_cli.impl import validate_command

    monkeypatch.setattr("subprocess.call", lambda *args, **kwargs: 0)
    args = SimpleNamespace(registry=str(arborRepo), intake=False, meta_sync=False)
    with pytest.raises(SystemExit) as clean:
        validate_command(args)
    assert clean.value.code == 0

    (arborRepo / "registry" / "arbor" / "stamps.jsonl").write_text("drift\n", encoding="utf-8")
    with pytest.raises(SystemExit) as drift:
        validate_command(args)
    assert drift.value.code == 1
