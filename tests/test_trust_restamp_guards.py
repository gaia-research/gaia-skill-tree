"""Review blockers on the event-driven restamp (#2323): grade, fingerprint, verification, authorization.

Shares its registry fixture with ``tests/test_trust_restamp.py``.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path

import pytest
import yaml

from gaia_cli.commands.dev import calibrate as calibrate_module
from gaia_cli.commands.dev.evidence import meta_evidence_command
from gaia_cli.trustMagnitude import computeTrustMagnitudeInputHash
from gaia_cli.trustRestamp import (
    RestampVerificationError,
    namedTrustSnapshot,
    protectedState,
    restampAfterEvidenceChange,
    verifyRestamp,
)
from tests.test_trust_restamp import _evidence, _read, _set, _stale, registry  # noqa: F401 (fixture)

pytestmark = [pytest.mark.integration]


def _strip(path: Path, *names: str) -> None:
    skill = _read(path)
    for name in names:
        skill.pop(name, None)
    body = path.read_text(encoding="utf-8").split("---", 2)[2]
    path.write_text("---\n" + yaml.safe_dump(skill, sort_keys=False, allow_unicode=True) + "---" + body, encoding="utf-8")


def _moved(registry: dict, **overrides) -> dict:
    """Snapshot, add evidence to the generic WITHOUT restamping, and return the pre-write snapshot."""
    root = registry["root"]
    before = namedTrustSnapshot(str(root))
    meta_evidence_command(_evidence(root, "parent", no_restamp=True, **overrides))
    return before


def _writer(mutate):
    """A fake writer that reports its targets as written after applying ``mutate``."""

    def write(args):
        mutate(args)
        return {"changed": list(args.skill), "unchanged": [], "held": []}

    return write


def test_a_restamp_that_would_rewrite_the_stored_grade_is_held(registry, capsys) -> None:
    root = registry["root"]
    # Level 3★ agrees with the computed grade B, but the stamp stores grade A (a stale cache).
    _set(registry["pure"], overallTrustGrade="A")
    before_bytes = registry["pure"].read_bytes()

    meta_evidence_command(_evidence(root, "parent"))

    assert registry["pure"].read_bytes() == before_bytes
    assert _read(registry["pure"])["overallTrustGrade"] == "A"
    assert "HELD acme/pure" in capsys.readouterr().out
    stamp = _stale(root)["acme/pure"]
    assert stamp["recomputationOnly"] is False and "overallTrustGrade" in stamp["staleFields"]


def test_a_hash_only_change_with_unchanged_tm_is_affected_and_restamped(registry) -> None:
    root = registry["root"]
    before_tm = _read(registry["pure"])["trustMagnitude"]

    # A star row at 5 stars scores nothing, so TM does not move; the own-input hash does.
    meta_evidence_command(_evidence(
        root, "acme/pure", stars=5, citations=None, evidence_type="github-stars-own",
        source="https://github.com/acme/pure-extra",
    ))

    pure = _read(registry["pure"])
    assert pure["trustMagnitude"] == before_tm
    assert pure["trustMagnitudeInputHash"] == computeTrustMagnitudeInputHash(pure)
    assert any(e["action"] == "recalibrate_trust_magnitude" for e in pure["timeline"])
    assert "acme/pure" not in _stale(root)


def test_the_backstop_sees_grade_only_and_hash_only_staleness(registry) -> None:
    root = registry["root"]
    _set(registry["pure"], overallTrustGrade="C")  # TM and hash are fresh; only the grade is wrong
    _set(registry["governed"], trustMagnitudeInputHash="0" * 64)  # only the hash is wrong

    stale = _stale(root)

    assert stale["acme/pure"]["staleFields"] == ["overallTrustGrade"]
    assert stale["acme/pure"]["recomputationOnly"] is False  # restamping would rewrite the grade
    assert stale["acme/governed"]["staleFields"] == ["trustMagnitudeInputHash"]
    assert stale["acme/governed"]["delta"] == 0.0


def test_an_omitted_writer_result_is_never_assumed_to_be_success(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)
    monkeypatch.setattr(calibrate_module, "calibrate_trust_magnitude_command", lambda args: None)

    with pytest.raises(RestampVerificationError, match="returned no result"):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


def test_a_writer_that_wrote_nothing_fails_verification(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)
    monkeypatch.setattr(calibrate_module, "calibrate_trust_magnitude_command", _writer(lambda args: None))

    with pytest.raises(RestampVerificationError, match="record bytes are unchanged"):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


def test_a_writer_that_reports_a_different_set_of_targets_is_refused(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)
    monkeypatch.setattr(
        calibrate_module,
        "calibrate_trust_magnitude_command",
        lambda args: {"changed": [], "unchanged": list(args.skill), "held": []},
    )

    with pytest.raises(RestampVerificationError, match="were intended"):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


def test_a_missing_stamp_after_the_write_is_a_violation(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)
    strip_all = lambda args: _strip(  # noqa: E731
        registry["pure"], "trustMagnitude", "overallTrustGrade", "trustMagnitudeInputHash"
    )
    monkeypatch.setattr(calibrate_module, "calibrate_trust_magnitude_command", _writer(strip_all))

    with pytest.raises(RestampVerificationError, match="trustMagnitude is missing.*overallTrustGrade is missing"):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


def test_a_partial_stamp_is_a_violation(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)

    def partial(args):
        real(args)
        _strip(registry["pure"], "trustMagnitudeInputHash")

    real = calibrate_module.calibrate_trust_magnitude_command
    monkeypatch.setattr(calibrate_module, "calibrate_trust_magnitude_command", _writer(partial))

    with pytest.raises(RestampVerificationError, match="trustMagnitudeInputHash is missing"):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


@pytest.mark.parametrize(("mutation", "message"), [
    (lambda reg: _set(reg["pure"], level="4★"), "star level moved"),
    (lambda reg: _set(reg["pure"], overallTrustGrade="S"), "stored grade changed"),
    (lambda reg: _set(reg["unaffected"], trustMagnitude=99.0), "non-target record was modified"),
    (lambda reg: _set(reg["frozen"], trustMagnitude=99.0), "non-target record was modified"),
])
def test_independent_verification_rejects_every_unintended_change(registry, monkeypatch, mutation, message) -> None:
    root = registry["root"]
    before = _moved(registry)
    real = calibrate_module.calibrate_trust_magnitude_command

    def write(args):
        result = real(args)
        mutation(registry)
        return result

    monkeypatch.setattr(calibrate_module, "calibrate_trust_magnitude_command", write)

    with pytest.raises(RestampVerificationError, match=message):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")


def test_verifyRestamp_compares_level_and_frozen_records_against_the_pre_write_snapshot(registry) -> None:
    root = registry["root"]
    guarded = protectedState(str(root))
    _set(registry["frozen"], level="4★")  # not a stamp

    with pytest.raises(RestampVerificationError) as raised:
        verifyRestamp(str(root), ["acme/pure"], guarded)

    text = str(raised.value)
    assert "acme/frozen: star level moved" in text
    assert "acme/pure: record bytes are unchanged" in text  # the intended target was never written


def test_an_unauthorized_direct_invocation_is_refused_and_writes_nothing(registry, monkeypatch) -> None:
    root = registry["root"]
    before = _moved(registry)
    (root / "registry" / "named-skills.json").write_text(
        json.dumps({"buckets": {"x": [{"contributor": "boss", "level": "4★"}]}}), encoding="utf-8"
    )
    monkeypatch.setattr("gaia_cli.authz._gaia_user", lambda: "intruder")
    monkeypatch.delenv("GAIA_OPERATOR_OVERRIDE", raising=False)
    snapshot = {key: path.read_bytes() for key, path in registry.items() if key != "root"}
    monkeypatch.setattr(
        calibrate_module,
        "calibrate_trust_magnitude_command",
        lambda args: pytest.fail("the writer must not run for an unauthorized caller"),
    )

    with pytest.raises(SystemExit) as raised:
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")

    assert raised.value.code == 1
    assert {key: path.read_bytes() for key, path in registry.items() if key != "root"} == snapshot


def test_a_direct_invocation_holds_the_canonical_transaction_lock(registry, monkeypatch) -> None:
    from gaia_cli import canonicalTransaction

    root = registry["root"]
    before = _moved(registry)
    taken: list[str] = []
    original = canonicalTransaction.canonicalTransactionLock

    @contextlib.contextmanager
    def spy(path):
        taken.append(str(path))
        with original(path):
            yield

    monkeypatch.setattr(canonicalTransaction, "canonicalTransactionLock", spy)

    report = restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")

    assert str(root) in taken and report.verified and report.restamped == ("acme/pure",)


def test_a_pending_canonical_transaction_blocks_a_direct_restamp(registry) -> None:
    from gaia_cli.canonicalTransaction import TransactionError

    root = registry["root"]
    before = _moved(registry)
    state = root / ".gaia" / "canonical-transactions"
    state.mkdir(parents=True, exist_ok=True)
    (state / "x.pending.json").write_text("{}", encoding="utf-8")
    snapshot = registry["pure"].read_bytes()

    with pytest.raises(TransactionError):
        restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")

    assert registry["pure"].read_bytes() == snapshot
