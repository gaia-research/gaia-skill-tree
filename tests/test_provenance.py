"""Tests for the RFC3 §3.1 provenance sidecar ledger (GAP10 + GAP11)."""

import json
from pathlib import Path

import pytest

from gaia_cli.provenance import (
    STATUS_LADDER,
    VALID_STATUSES,
    buildProvenanceLedger,
    crawlerOriginFromPacket,
    provenanceLedgerPath,
    validateProvenanceLedger,
    writeProvenanceLedger,
)


def _writeSchema(registryRoot):
    """Copy the repo's provenance schema into a temp registry root."""
    repoRoot = Path(__file__).parent.parent
    src = repoRoot / "registry" / "schema" / "provenance.schema.json"
    dst = registryRoot / "registry" / "schema" / "provenance.schema.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def test_ledger_shape_minimal():
    ledger = buildProvenanceLedger("marco/gaia-curate")
    assert ledger["skillId"] == "marco/gaia-curate"
    # status defaults to the ladder terminal reached at ingest
    assert ledger["status"] == "ingested"


def test_status_default_is_ingested():
    ledger = buildProvenanceLedger("contributor/slug")
    assert ledger["status"] == "ingested"
    assert "ingested" in STATUS_LADDER


def test_ledger_full_shape():
    ledger = buildProvenanceLedger(
        "contributor/slug",
        genericSkillRef="research",
        discoveryPacket="registry-for-review/discovery-packets/cand.json",
        intakeBatch="registry-for-review/skill-batches/batch.json",
        intakeIssue="https://github.com/mbtiongson1/gaia-skill-tree/issues/9",
        crawlerOrigin={
            "sourceLane": "source-repository",
            "canonicalUrl": "https://example.com/skill",
            "contentSha256": "a" * 64,
        },
        evidenceSeed="evidence/seeds/contributor/slug/repo-own.jsonl",
        ingestedAt="2026-07-29T00:00:00Z",
    )
    assert ledger["genericSkillRef"] == "research"
    assert ledger["discoveryPacket"].endswith("cand.json")
    assert ledger["intakeBatch"].endswith("batch.json")
    assert ledger["intakeIssue"].startswith("https://")
    assert ledger["evidenceSeed"].endswith("repo-own.jsonl")


def test_crawler_origin_population_closes_gap11():
    packet = {
        "candidateId": "contributor/slug",
        "source": {
            "sourceLane": "marketplace",
            "canonicalUrl": "https://example.com/x",
            "contentSha256": "b" * 64,
            "extra": "ignored",
        },
    }
    origin = crawlerOriginFromPacket(packet)
    assert origin == {
        "sourceLane": "marketplace",
        "canonicalUrl": "https://example.com/x",
        "contentSha256": "b" * 64,
    }
    # extra fields are not smuggled into the ledger
    ledger = buildProvenanceLedger("contributor/slug", crawlerOrigin=origin)
    assert "extra" not in ledger["crawlerOrigin"]


def test_crawler_origin_none_when_no_source():
    assert crawlerOriginFromPacket({"candidateId": "x"}) is None
    assert crawlerOriginFromPacket({"source": "not-a-dict"}) is None
    assert crawlerOriginFromPacket("not-a-packet") is None


def test_build_rejects_empty_skill_id():
    with pytest.raises(ValueError):
        buildProvenanceLedger("")


def test_build_rejects_off_ladder_status():
    with pytest.raises(ValueError):
        buildProvenanceLedger("contributor/slug", status="bogus")


def test_ladder_and_terminals_present():
    for state in ("discovered", "review-ready", "intake-open",
                  "evidence-seeded", "in-appraisal", "ingested",
                  "deferred", "rejected"):
        assert state in VALID_STATUSES


def test_ledger_schema_validates(tmp_path):
    _writeSchema(tmp_path)
    ledger = buildProvenanceLedger(
        "contributor/slug",
        crawlerOrigin={"sourceLane": "github-topic", "canonicalUrl": "https://x.io", "contentSha256": "c" * 64},
    )
    errors = validateProvenanceLedger(ledger, tmp_path)
    assert errors == []


def test_bad_ledger_fails_schema(tmp_path):
    _writeSchema(tmp_path)
    errors = validateProvenanceLedger({"skillId": "x", "status": "not-a-status"}, tmp_path)
    assert errors


def test_write_ledger_roundtrip(tmp_path):
    _writeSchema(tmp_path)
    ledger = buildProvenanceLedger("contributor/slug", status="ingested")
    path = writeProvenanceLedger(ledger, tmp_path)
    assert path == provenanceLedgerPath("contributor/slug", tmp_path)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["skillId"] == "contributor/slug"
    assert loaded["status"] == "ingested"


def test_write_rejects_invalid_ledger(tmp_path):
    _writeSchema(tmp_path)
    with pytest.raises(ValueError):
        writeProvenanceLedger({"skillId": "x", "status": "bogus"}, tmp_path)
