"""Bounds for documented named persistence, not new trust/approval policy."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "registry/schema/namedSkill.schema.json").read_text())


def validator():
    return Draft7Validator(SCHEMA, format_checker=FormatChecker())


def record():
    return dict(id="example/tool", name="Tool", contributor="example", origin=False,
                genericSkillRef="tool", status="named", title="The Tool", level="2★",
                description="A concrete implementation.", createdAt="2026-01-01", updatedAt="2026-01-01")


def test_named_persistence_mirrors():
    canonical = (ROOT / "registry/schema/namedSkill.schema.json").read_bytes()
    for path in ("src/gaia_cli/data/registry/schema", "docs/schema"):
        assert (ROOT / path / "namedSkill.schema.json").read_bytes() == canonical


def test_cache_matches_engine_and_does_not_become_evidence():
    from gaia_cli.trustMagnitude import computeTrustMagnitudeInputHash, passesSuiteApexGate
    data = record()
    data.update(trustMagnitude=0, overallTrustGrade="ungraded",
                trustMagnitudeInputHash=computeTrustMagnitudeInputHash(data),
                apexGateStatus=passesSuiteApexGate(data))
    validator().validate(data)
    assert data["apexGateStatus"]["crossOrgVerifier"] is None
    assert data["apexGateStatus"]["systemWideCap"] is None
    evidence = copy.deepcopy(SCHEMA["definitions"]["evidenceEntry"])
    assert "trustMagnitudeInputHash" not in evidence["properties"]


@pytest.mark.parametrize("action", ["note", "suite_ref_set", "installation_updated",
                                    "migrate_trust_magnitude", "recalibrate_trust_magnitude"])
def test_canonical_event_vocabulary(action):
    data = record()
    data["timeline"] = [dict(timestamp="2026-01-01T00:00:00Z", action=action,
                             contributor="github-actions[bot]")]
    validator().validate(data)


def test_existing_provenance_shapes():
    data = record()
    data.update(installable=False, attribution=dict(type="self-made", upstream_author="Example",
                skill_file_url="https://github.com/example/tool/blob/main/SKILL.md"),
                apexGateStatus=dict(apexPromotionPrSignedBy="example", apexPromotionPrSignedAt="2026-01-01"),
                evidence=[dict(type="github-stars-own", source="https://github.com/example/tool",
                               stars=100, evaluator="example", date="2026-01-01", updatedAt="2026-01-01")],
                timeline=[dict(timestamp="2026-01-01T00:00:00Z", action="upstream_deprecated", newValue=None)])
    validator().validate(data)


@pytest.mark.parametrize("patch", [
    {"trustMagnitudeInputHash": "bad"}, {"trustMagnitudeInputHash": 123},
    {"apexGateStatus": {"crossOrgVerifier": "true"}},
    {"apexGateStatus": {"systemWideCap": 1}},
    {"apexGateStatus": {"unknown": None}}, {"unknown": True},
    {"installable": "false"}, {"name": ""},
    {"attribution": {"unknown": "x"}},
    {"apexGateStatus": {"apexPromotionPrSignedAt": "yesterday"}},
    {"evidence": [{"source": "https://example.com", "updatedAt": "yesterday"}]},
])
def test_invalid_new_persistence_rejected(patch):
    data = record()
    data.update(patch)
    assert list(validator().iter_errors(data))


@pytest.mark.parametrize("actor", ["invalid_name", "other[bot]", "github-actions[bot]junk", "bad user", ""])
def test_bot_provenance_is_not_arbitrary_actor_syntax(actor):
    data = record()
    data["timeline"] = [dict(timestamp="2026-01-01T00:00:00Z", action="note", contributor=actor)]
    assert list(validator().iter_errors(data))


def test_bot_not_a_human_owner_and_unknown_action_stays_invalid():
    data = record()
    data["contributor"] = "github-actions[bot]"
    assert list(validator().iter_errors(data))
    data = record()
    data["timeline"] = [dict(timestamp="2026-01-01T00:00:00Z", action="arbitrary", newValue=None)]
    assert list(validator().iter_errors(data))
    data["timeline"][0]["action"] = "upstream_synced"
    assert list(validator().iter_errors(data))
