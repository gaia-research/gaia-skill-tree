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


# --- round 4: no callable path can write the stamps unauthorized -----------------------------


def test_no_writer_callable_exposes_an_unguarded_inner_function() -> None:
    import inspect

    from gaia_cli import trustRestamp

    for function in (
        calibrate_module.calibrate_trust_magnitude_command,
        calibrate_module._calibrateTrustMagnitudeLocked,
        trustRestamp.restampAfterEvidenceChange,
        trustRestamp._restampLocked,
    ):
        assert not hasattr(function, "__wrapped__"), f"{function.__name__} exposes an unguarded inner writer"
    # The guard is in the body of the function that writes, not in a wrapper around it.
    source = inspect.getsource(calibrate_module._calibrateTrustMagnitudeLocked)
    assert source.index("require_operator(") < source.index("canonicalTransactionLock(") < source.index("buildMergedSkillMap(")
    assert not hasattr(calibrate_module, "_guardedWriter")


def _write_paths(root, registry, before):
    """Every callable that can write stamps, each invoked the way a direct caller would."""
    from gaia_cli.trustRestamp import _restampBody

    verb = _verb(root)
    return {
        "calibrate_trust_magnitude_command": lambda: calibrate_module.calibrate_trust_magnitude_command(verb),
        "_calibrateTrustMagnitudeLocked": lambda: calibrate_module._calibrateTrustMagnitudeLocked(verb),
        "_calibrateTrustMagnitudeLocked.all": lambda: calibrate_module._calibrateTrustMagnitudeLocked(_verb(root, skill=None, all=True)),
        "restampAfterEvidenceChange": lambda: restampAfterEvidenceChange(str(root), before, trigger="direct", targetId="parent"),
        "_restampLocked": lambda: __import__("gaia_cli.trustRestamp", fromlist=["x"])._restampLocked(
            str(root), before, trigger="direct", targetId="parent", dryRun=False),
        "_restampBody": lambda: _restampBody(str(root), before, trigger="direct", targetId="parent", dryRun=False),
    }


@pytest.mark.parametrize("path", [
    "calibrate_trust_magnitude_command",
    "_calibrateTrustMagnitudeLocked",
    "_calibrateTrustMagnitudeLocked.all",
    "restampAfterEvidenceChange",
    "_restampLocked",
    "_restampBody",
])
def test_every_stamp_writing_path_refuses_an_unauthorized_operator_and_writes_nothing(registry, monkeypatch, path) -> None:
    root = registry["root"]
    before = _moved(registry)  # evidence is in place, the stamps are stale
    _set(registry["pure"], trustMagnitude=1.0)
    snapshot = _intruder(registry, monkeypatch)
    snapshot["pure"] = registry["pure"].read_bytes()
    snapshot["parent"] = root.joinpath(*PARENT_NODE).read_bytes()

    with pytest.raises(SystemExit) as raised:
        _write_paths(root, registry, before)[path]()

    assert raised.value.code == 1
    after = {key: p.read_bytes() for key, p in registry.items() if key != "root"}
    after["parent"] = root.joinpath(*PARENT_NODE).read_bytes()
    assert after == snapshot
    assert _read(registry["pure"])["trustMagnitude"] == 1.0


def test_the_former_wrapped_probe_no_longer_writes(registry, monkeypatch) -> None:
    """The round-4 probe: reach for the undecorated function through __wrapped__."""
    root = registry["root"]
    _set(registry["pure"], trustMagnitude=1.0)
    snapshot = _intruder(registry, monkeypatch)
    snapshot["pure"] = registry["pure"].read_bytes()
    inner = getattr(calibrate_module._calibrateTrustMagnitudeLocked, "__wrapped__", calibrate_module._calibrateTrustMagnitudeLocked)

    with pytest.raises(SystemExit):
        inner(_verb(root))

    assert {key: p.read_bytes() for key, p in registry.items() if key != "root"} == snapshot
