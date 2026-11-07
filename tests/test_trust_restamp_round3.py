"""Third review of #2323: the actual writer, evidence-command preflight, post-write failure reporting.

Shares its registry fixture and helpers with ``tests/test_trust_restamp.py`` and
``tests/test_trust_restamp_guards.py``.
"""

from __future__ import annotations

import json

import pytest

from gaia_cli import trustMagnitude as trust_magnitude_module
from gaia_cli.commands.dev import calibrate as calibrate_module
from gaia_cli.commands.dev.evidence import meta_evidence_command, meta_rm_evidence_command
from gaia_cli.trustRestamp import RestampVerificationError, namedTrustSnapshot, restampAfterEvidenceChange
from tests.test_trust_restamp import _evidence, _named, _read, _rm, _set, _stale, _stamp, registry  # noqa: F401 (fixture)
from tests.test_trust_restamp_guards import _breakable, _intruder, _moved, _verb

pytestmark = [pytest.mark.integration]

PARENT_NODE = ("registry", "nodes", "basic", "parent.json")


def _parent(root) -> dict:
    return json.loads(root.joinpath(*PARENT_NODE).read_text(encoding="utf-8"))


def _everything(registry: dict) -> dict:
    root = registry["root"]
    files = {key: path.read_bytes() for key, path in registry.items() if key != "root"}
    files["parent"] = root.joinpath(*PARENT_NODE).read_bytes()
    return files


def _breakable_hash(registry: dict, monkeypatch) -> dict:
    """A stamped skill whose own-input hash (not TM) fails on demand, so Origin stays derivable."""
    root = registry["root"]
    path = _named(root, "acme/broken", level="3★", parent="parent")
    _stamp(root, path)
    state = {"fail": False, "path": path}
    real = trust_magnitude_module.computeTrustMagnitudeInputHash

    def flaky(skill, *args, **kwargs):
        if state["fail"] and skill.get("id") == "acme/broken":
            raise ValueError("simulated hash failure")
        return real(skill, *args, **kwargs)

    monkeypatch.setattr(trust_magnitude_module, "computeTrustMagnitudeInputHash", flaky)
    return state


# --- 1. the function that actually writes is guarded ---------------------------------------


@pytest.mark.parametrize("overrides", [
    {},
    {"recomputation_only": False},
    {"skill": None, "all": True},
    {"skill": None, "all": True, "recomputation_only": False},
])
def test_the_actual_writer_function_refuses_an_unauthorized_operator(registry, monkeypatch, overrides) -> None:
    root = registry["root"]
    _set(registry["pure"], trustMagnitude=1.0)  # stale: the writer would change it if it ran
    snapshot = _intruder(registry, monkeypatch)
    snapshot["pure"] = registry["pure"].read_bytes()

    with pytest.raises(SystemExit) as raised:
        calibrate_module._calibrateTrustMagnitudeLocked(_verb(root, **overrides))

    assert raised.value.code == 1
    assert {key: path.read_bytes() for key, path in registry.items() if key != "root"} == snapshot
    assert _read(registry["pure"])["trustMagnitude"] == 1.0


def test_the_actual_writer_keeps_its_preflights_and_still_writes_when_authorized(registry) -> None:
    root = registry["root"]
    with pytest.raises(SystemExit):
        calibrate_module._calibrateTrustMagnitudeLocked(_verb(root, skill=["acme/frozen"]))
    with pytest.raises(SystemExit):
        calibrate_module._calibrateTrustMagnitudeLocked(_verb(root, skill=["acme/missing"]))
    _set(registry["pure"], trustMagnitude=1.0)

    result = calibrate_module._calibrateTrustMagnitudeLocked(_verb(root))

    assert result["changed"] == ["acme/pure"]


# --- 2. the evidence command preflights the restamp before it writes ---------------------


def test_evidence_is_refused_before_any_write_when_origin_cannot_be_derived(registry, monkeypatch, capsys) -> None:
    state = _breakable(registry, monkeypatch)
    state["fail"] = True
    before = _everything(registry)
    before["broken"] = state["path"].read_bytes()

    with pytest.raises(SystemExit) as raised:
        meta_evidence_command(_evidence(registry["root"], "parent"))

    assert raised.value.code == 1
    error = capsys.readouterr().err
    assert "refusing to write evidence" in error and "Nothing was written" in error and "--no-restamp" in error
    assert _parent(registry["root"])["evidence"] == []
    after = _everything(registry)
    assert after == {key: value for key, value in before.items() if key != "broken"}
    assert state["path"].read_bytes() == before["broken"]


def test_evidence_is_refused_before_any_write_when_a_fingerprint_cannot_be_computed(registry, monkeypatch, capsys) -> None:
    state = _breakable_hash(registry, monkeypatch)  # Origin stays derivable; only the fingerprint fails
    state["fail"] = True
    before = _everything(registry)

    with pytest.raises(SystemExit) as raised:
        meta_evidence_command(_evidence(registry["root"], "parent"))

    assert raised.value.code == 1
    error = capsys.readouterr().err
    assert "cannot be fingerprinted" in error and "acme/broken" in error and "--no-restamp" in error
    assert _parent(registry["root"])["evidence"] == []
    assert _everything(registry) == before


def test_rm_evidence_is_refused_before_any_write_when_the_restamp_cannot_be_computed(registry, monkeypatch, capsys) -> None:
    root = registry["root"]
    meta_evidence_command(_evidence(root, "parent", no_restamp=True))
    state = _breakable_hash(registry, monkeypatch)
    state["fail"] = True
    before = _everything(registry)

    with pytest.raises(SystemExit) as raised:
        meta_rm_evidence_command(_rm(root, "parent"))

    assert raised.value.code == 1
    assert "--no-restamp" in capsys.readouterr().err
    assert len(_parent(root)["evidence"]) == 1  # the row is still there
    assert _everything(registry) == before


def test_no_restamp_still_writes_the_evidence_when_the_restamp_cannot_be_computed(registry, monkeypatch) -> None:
    state = _breakable_hash(registry, monkeypatch)
    state["fail"] = True

    meta_evidence_command(_evidence(registry["root"], "parent", no_restamp=True))

    assert len(_parent(registry["root"])["evidence"]) == 1


def test_a_failure_after_the_write_exits_nonzero_and_says_the_evidence_was_written(registry, monkeypatch, capsys) -> None:
    root = registry["root"]

    def boom(*args, **kwargs):
        raise RestampVerificationError("simulated post-write verification failure")

    monkeypatch.setattr("gaia_cli.trustRestamp._restampLocked", boom)

    with pytest.raises(SystemExit) as raised:
        meta_evidence_command(_evidence(root, "parent"))

    assert raised.value.code == 1
    error = capsys.readouterr().err
    assert "Evidence written; stamps not refreshed (sensor backstop will flag)" in error
    assert "do not re-add" in error and "calibrate-trust-magnitude --all --recomputation-only" in error
    # The evidence is on disk exactly once, the stamp is stale, and the sensor backstop reports it.
    assert len(_parent(root)["evidence"]) == 1
    assert "acme/pure" in _stale(root)


def test_the_documented_recovery_clears_the_stamp_the_failed_restamp_left_stale(registry, monkeypatch) -> None:
    root = registry["root"]
    with monkeypatch.context() as patch:
        patch.setattr("gaia_cli.trustRestamp._restampLocked", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
        with pytest.raises(SystemExit):
            meta_evidence_command(_evidence(root, "parent"))
    assert "acme/pure" in _stale(root)

    result = calibrate_module.calibrate_trust_magnitude_command(_verb(root, skill=None, all=True))

    assert "acme/pure" in result["changed"]
    assert "acme/pure" not in _stale(root)
    assert len(_parent(root)["evidence"]) == 1  # recovery did not re-add the evidence


def test_an_unauthorized_restamp_after_the_write_is_also_reported_as_partial(registry, monkeypatch, capsys) -> None:
    def deny(*args, **kwargs):
        raise SystemExit(1)

    monkeypatch.setattr("gaia_cli.trustRestamp._restampLocked", deny)

    with pytest.raises(SystemExit) as raised:
        meta_evidence_command(_evidence(registry["root"], "parent"))

    assert raised.value.code == 1
    assert "Evidence written; stamps not refreshed" in capsys.readouterr().err
    assert len(_parent(registry["root"])["evidence"]) == 1


# --- 3. after-only fingerprint failure where Origin stays derivable ----------------------


def test_an_after_only_fingerprint_failure_is_held_reported_and_not_written(registry, monkeypatch) -> None:
    root = registry["root"]
    state = _breakable_hash(registry, monkeypatch)
    before = namedTrustSnapshot(str(root))
    assert "acme/broken" in before and getattr(before, "unevaluable", ()) == ()
    meta_evidence_command(_evidence(root, "parent", no_restamp=True))
    broken_bytes = state["path"].read_bytes()
    state["fail"] = True  # fails only now, after the evidence write; Origin derivation is unaffected

    report = restampAfterEvidenceChange(str(root), before, trigger="test", targetId="parent")

    held = {item["skillId"]: item for item in report.held}
    assert "acme/broken" in held and "after the evidence write" in held["acme/broken"]["reason"]
    assert "acme/broken" in report.unevaluable
    assert state["path"].read_bytes() == broken_bytes  # the failed skill is not written
    assert report.restamped == ("acme/pure",) and report.verified  # evaluable skills are still handled
    assert "acme/pure" not in _stale(root)
