"""Regression coverage for the curation public error contract.

GitHub Advanced Security reported clear-text sensitive-data findings on the
console surfaces of the curation seam: the two verification scripts and
`gaia dev ratify`. The repair routes every refusal through
`gaia_cli.curation.errors`, so user-facing stderr carries only published
constants — a stable code and a fixed summary — and never upstream text.

These tests pin the security property, not the wording:

  * a verifier that returns secret-bearing text must not reach the console;
  * a refusal must still fail closed, with no packet written;
  * the published fail-closed refusal is still shown, so the operator can
    still see that the protected ceremony is the reason.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.curation.errors import (
    CATEGORY_AUTHORIZATION,
    CATEGORY_UNRECOGNISED,
    DETAIL_WITHHELD,
    REASON_UNRECOGNISED,
    REFUSAL_L4_PENDING,
    classify_refusals,
    public_detail,
    public_reason,
    public_refusal,
    public_refusal_lines,
)

from test_dev_ratify import _makeDeferredMappedPacket, _makeRatifyArgs

#: Stands in for material a real protected verifier could surface.
SECRET = "ghp_EXAMPLETOKENEXAMPLETOKENEXAMPLETOKEN0123456789"


@pytest.fixture(autouse=True)
def unitOnlyAuthorizationAndFreshness(monkeypatch):
    """UNIT-ONLY trust/freshness stubs; real payload reconstruction still runs."""
    monkeypatch.setattr("gaia_cli.commands.dev.ratify.verifyFreshness", lambda *a, **k: [])
    monkeypatch.setattr("gaia_cli.curation.authorization._verifyTrustedEnvelope", lambda *a, **k: [])


def _load_script(name):
    """Import a verification script by path (they are not a package)."""
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        f"_curation_script_{name.replace('.', '_')}", root / "scripts" / name
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the contract itself -------------------------------------------------------


def test_published_refusal_is_echoed():
    """The published fail-closed refusal is this codebase's own contract."""
    lines = public_refusal_lines([REFUSAL_L4_PENDING], CATEGORY_AUTHORIZATION)
    assert len(lines) == 1
    assert REFUSAL_L4_PENDING in lines[0]


def test_unpublished_refusal_is_withheld():
    """Refusal text this codebase does not publish never reaches the console."""
    lines = public_refusal_lines([f"verifier said: {SECRET}"], CATEGORY_AUTHORIZATION)
    rendered = "\n".join(lines)
    assert SECRET not in rendered
    assert CATEGORY_AUTHORIZATION in rendered
    assert "withheld" in rendered


def test_withheld_refusals_are_counted():
    lines = public_refusal_lines(
        [f"a {SECRET}", f"b {SECRET}"], CATEGORY_AUTHORIZATION
    )
    assert len(lines) == 1
    assert "2 withheld" in lines[0]


def test_published_and_withheld_refusals_are_reported_separately():
    lines = public_refusal_lines(
        [REFUSAL_L4_PENDING, f"a {SECRET}"], CATEGORY_AUTHORIZATION
    )
    assert len(lines) == 2
    assert REFUSAL_L4_PENDING in lines[0]
    assert SECRET not in lines[1]


def test_public_refusal_never_echoes_an_unknown_category():
    rendered = public_refusal(f"category {SECRET}")
    assert CATEGORY_UNRECOGNISED in rendered
    assert SECRET not in rendered


def test_public_refusal_lines_never_echo_a_refusal():
    rendered = "\n".join(public_refusal_lines([f"x {SECRET}"], CATEGORY_AUTHORIZATION))
    assert SECRET not in rendered


def test_public_reason_returns_only_published_codes():
    assert public_reason("review accounting must not claim human approval") == (
        "REVIEW_ACCOUNTING_HUMAN_APPROVAL_CLAIM"
    )
    assert public_reason(f"something {SECRET}") == REASON_UNRECOGNISED


def test_public_detail_withholds_anything_that_is_not_a_token():
    assert public_detail("OUTCOME_REVIEW_READY") == "OUTCOME_REVIEW_READY"
    assert public_detail(SECRET) == DETAIL_WITHHELD
    assert public_detail("a lowercase sentence") == DETAIL_WITHHELD


def test_classify_refusals_returns_a_published_token():
    assert classify_refusals([REFUSAL_L4_PENDING]) == "AUTHORIZATION_L4_PENDING"
    assert classify_refusals([f"x {SECRET}"]) == "REFUSAL_UNRECOGNISED"


# --- the production ratify boundary ---------------------------------------------


def _ratify_args(tmp_path):
    packet = _makeDeferredMappedPacket()
    packetPath = tmp_path / "packet.json"
    packetPath.write_text(json.dumps(packet), encoding="utf-8")
    return packetPath, _makeRatifyArgs(tmp_path, packet, packetPath)


def test_ratify_does_not_echo_verifier_text(tmp_path, capsys, monkeypatch):
    """A verifier returning secret-bearing text must not reach stderr."""
    packetPath, args = _ratify_args(tmp_path)
    before = packetPath.read_bytes()
    monkeypatch.setattr(
        "gaia_cli.commands.dev.ratify.verifyPacketAuthorization",
        lambda *a, **k: [f"could not independently build authorization payload: {SECRET}"],
    )
    rc = ratifyCommand(args)
    err = capsys.readouterr().err
    assert rc == 1
    assert SECRET not in err
    # The operator still learns which gate refused.
    assert CATEGORY_AUTHORIZATION in err
    # ... and the refusal still fails closed: nothing was written.
    assert packetPath.read_bytes() == before


def test_ratify_still_publishes_the_fail_closed_refusal(tmp_path, capsys, monkeypatch):
    """The published refusal stays visible; the operator must see the reason."""
    packetPath, args = _ratify_args(tmp_path)
    monkeypatch.setattr(
        "gaia_cli.commands.dev.ratify.verifyPacketAuthorization",
        lambda *a, **k: [REFUSAL_L4_PENDING],
    )
    rc = ratifyCommand(args)
    err = capsys.readouterr().err
    assert rc == 1
    assert REFUSAL_L4_PENDING in err


def test_ratify_does_not_echo_an_invalid_authorization_envelope(tmp_path, capsys, monkeypatch):
    """An unparseable envelope is reported without echoing the document."""
    packetPath, args = _ratify_args(tmp_path)
    envelope = tmp_path / "envelope.json"
    envelope.write_text(f'{{"token": "{SECRET}"', encoding="utf-8")
    args.authorization_envelope = str(envelope)
    monkeypatch.setattr(
        "gaia_cli.commands.dev.ratify.verifyPacketAuthorization",
        lambda *a, **k: [],
    )
    rc = ratifyCommand(args)
    err = capsys.readouterr().err
    assert rc == 1
    assert SECRET not in err
    assert "invalid authorization envelope" in err


# --- the intake / push boundary -------------------------------------------------


def _intake_packet(tmp_path):
    """A packet that clears every gate above the authorization boundary."""
    assessment = tmp_path / "assessment.json"
    assessment.write_text(json.dumps({"proposedDisposition": {"value": "MAP"}}), encoding="utf-8")
    return {
        "candidateId": "candidate-1",
        "name": "Test Skill",
        "description": "A test skill for mapping.",
        "type": "basic",
        "prerequisites": [],
        "decision": {"value": "MAP", "genericId": "generic-a"},
        "l4Resolution": {
            "generic": {"id": "generic-a", "name": "Generic A",
                        "description": "A generic ability for testing.",
                        "type": "basic", "prerequisites": []},
            "named": {"contributor": "owner", "skillName": "test-skill"},
            "skillFileUrl": "https://github.com/owner/test-skill/blob/main/SKILL.md",
            "humanReview": {"assessmentPath": str(assessment)},
        },
    }


@pytest.fixture
def aboveAuthorizationBoundary(monkeypatch):
    """Clear every gate above the authorization boundary (UNIT-ONLY)."""
    monkeypatch.setattr("gaia_cli.intakeAdapter.validateL4Resolution", lambda *a, **k: [])
    monkeypatch.setattr("gaia_cli.prefill.selfValidatePacket", lambda *a, **k: [])
    monkeypatch.setattr("gaia_cli.intakeAdapter.verifyFreshness", lambda *a, **k: [])
    monkeypatch.setattr("gaia_cli.curation.assessment.validateAssessment", lambda *a, **k: [])


def test_intake_boundary_does_not_echo_verifier_text(tmp_path, aboveAuthorizationBoundary, monkeypatch):
    """The push boundary reduces the refusal to the public contract too."""
    from gaia_cli.intakeAdapter import buildIntakeYaml

    monkeypatch.setattr(
        "gaia_cli.intakeAdapter.verifyPacketAuthorization",
        lambda *a, **k: [f"could not independently build authorization payload: {SECRET}"],
    )
    packet = _intake_packet(tmp_path)
    with pytest.raises(ValueError) as excinfo:
        buildIntakeYaml([packet], registryPath=".", requireHumanReview=True, inventory=[packet])
    message = str(excinfo.value)
    assert SECRET not in message
    assert "human authorization failed closed" in message


def test_intake_boundary_still_publishes_the_fail_closed_refusal(tmp_path, aboveAuthorizationBoundary, monkeypatch):
    from gaia_cli.intakeAdapter import buildIntakeYaml

    monkeypatch.setattr(
        "gaia_cli.intakeAdapter.verifyPacketAuthorization",
        lambda *a, **k: [REFUSAL_L4_PENDING],
    )
    packet = _intake_packet(tmp_path)
    with pytest.raises(ValueError) as excinfo:
        buildIntakeYaml([packet], registryPath=".", requireHumanReview=True, inventory=[packet])
    assert REFUSAL_L4_PENDING in str(excinfo.value)


# --- the verification scripts ---------------------------------------------------


@pytest.mark.parametrize("script", ["merge_gate_check.py", "curation_walkthrough.py"])
def test_verification_script_withholds_a_non_token_detail(script, capsys):
    """The scripts print a token, never a payload."""
    module = _load_script(script)
    module.check("a labelled check", True, SECRET)
    out = capsys.readouterr().out
    assert SECRET not in out
    assert DETAIL_WITHHELD in out


@pytest.mark.parametrize("script", ["merge_gate_check.py", "curation_walkthrough.py"])
def test_verification_script_prints_a_published_token(script, capsys):
    module = _load_script(script)
    module.check("a labelled check", True, "OUTCOME_REVIEW_READY")
    out = capsys.readouterr().out
    assert "OUTCOME_REVIEW_READY" in out
