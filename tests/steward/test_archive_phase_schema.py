"""Fail-closed phase portability; synthetic records and disposable remotes only."""
from __future__ import annotations

from copy import deepcopy

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward.ledger import update
from tests.steward.test_archive import hosts, seed, run_record, refs, observation_phases, END


def test_independent_receipt_evidence_counterexample_stays_hot(hosts):
    remote, one, two = hosts
    phases = {"observe": {"receipt": "receipts/proof.bin",
                          "evidence": "evidence/build-output", "payload": "x" * 10000}}
    before = seed(one, {"run-a": run_record(phases=phases)})
    branches = refs(remote)
    assert a.phase_hold(phases) is not None
    assert a.plan(one)["eligible"] == []
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches
    assert a.show(two, "run-a")["run"]["phases"] == phases


@pytest.mark.parametrize("value", [
    "receipts/proof.bin", "evidence/build-output", "/tmp/proof", "./proof",
    "../proof", "proof.bin", "proof.any-extension", "proof", "C:\\proof",
    "https://example.invalid/proof", "file:proof", None, False, 0, [], {},
    ["proof"], {"nested": [{"receipt": "proof"}]},
])
@pytest.mark.parametrize("key", ["receipt", "evidence", "futureReference"])
def test_unknown_reference_fields_fail_closed_even_when_empty(key, value):
    assert a.phase_hold({"observe": {key: value}}) is not None


@pytest.mark.parametrize("value", [
    "receipts/proof.bin", "evidence/build-output", "/tmp/proof", "./proof",
    "../proof", "proof.bin", "proof.any-extension", "C:\\proof", "~proof",
    "https://example.invalid/proof", "file:proof", "prefix proof.bin suffix",
    "unicode-π.未知", None, {}, ["inline"], 10, True,
])
def test_known_inline_slot_does_not_make_paths_portable(value):
    assert a.phase_hold({"observe": {"payload": value}}) is not None


@pytest.mark.parametrize("artifactExists", [False, True])
def test_independent_extensionless_payload_counterexample_stays_hot(hosts, monkeypatch, artifactExists):
    import builtins
    from pathlib import Path

    remote, one, two = hosts
    phases = {"observe": {"payload": "proof"}, "retro": {"detail": "x" * 10000}}
    artifact = one.repo_root / "proof"
    if artifactExists:
        artifact.write_bytes(b"synthetic artifact bytes are not ledger JSON")
    monkeypatch.chdir(one.repo_root)
    before = seed(one, {"run-a": run_record(phases=phases)})
    branches = refs(remote)
    originalOpen, originalPathOpen = builtins.open, Path.open

    def guardedOpen(path, *args, **kwargs):
        if isinstance(path, (str, Path)):
            assert Path(path).resolve() != artifact, "must not open an ambiguous artifact"
        return originalOpen(path, *args, **kwargs)

    def guardedPathOpen(path, *args, **kwargs):
        assert path.resolve() != artifact, "must not open an ambiguous artifact"
        return originalPathOpen(path, *args, **kwargs)

    def noCas(*args, **kwargs):
        pytest.fail("held phases must not attempt canonical CAS")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guardedOpen)
        patch.setattr(Path, "open", guardedPathOpen)
        patch.setattr(one, "compare_and_swap", noCas)
        assert a.phase_hold(phases) is not None
        assert a.plan(one)["eligible"] == []
        assert a.migrate(one)["archived"] == []
        assert two.load() == before
        assert refs(remote) == branches
        assert a.show(two, "run-a")["run"]["phases"] == phases
    if artifactExists:
        assert artifact.read_bytes() == b"synthetic artifact bytes are not ledger JSON"


@pytest.mark.parametrize("value", ["proof", "README", "arbitrary bare words", "", None, False, 0,
                                    "receipts/proof.bin", "evidence/build-output", "π", [], {}])
@pytest.mark.parametrize("slot", ["payload", "detail", "unknownReason", "notEvaluated", "partial",
                                   "sensorReason", "note", "integrationReason", "classBReason", "reused"])
def test_all_unconstrained_prose_slots_hold_even_extensionless_values(slot, value):
    phases = {
        "payload": {"observe": {"payload": value}},
        "detail": {"retro": {"detail": value}},
        "unknownReason": {"observe": {"coverageUnknownReasons": {"sensor": value}}},
        "notEvaluated": {"observe": {"notEvaluated": [{"sensor": "sensor", "reason": value}]}},
        "partial": {"observe": {"partialCoverage": [{"sensor": "sensor", "skippedCount": 1, "reasons": [value]}]}},
        "sensorReason": {"retro": {"sensors": [{"id": "sensor", "state": "unknown", "reason": value}]}},
        "note": {"reobserve": {"notes": [{"debtId": "debt", "note": value}]}},
        "integrationReason": {"reconcile": {"integrationHeadUnknown": value}},
        "classBReason": {"class_b": {"reason": value}},
        "reused": {"reobserve": {"reused": value}},
    }[slot]
    assert a.phase_hold(phases) is not None


def test_reused_text_accepts_only_existing_producer_constrained_literal():
    from gaia_cli.steward.fullrun import FullRunner

    literal = "no state-changing step ran this run; the observe scan is the re-observation"
    assert literal in FullRunner._phaseReobserve.__code__.co_consts
    assert a.phase_hold({"reobserve": {"reused": literal, "notes": []}}) is None
    assert a.phase_hold({"reobserve": {"reused": literal + " proof"}}) is not None


DEBT = "debt:synthetic:subject:0123456789abcdef"


def ambiguous_canonical_phases():
    """Exact old fixture, retained as a hot-only uncertainty regression."""
    return {
        "observe": {
            "scanReceiptId": "scan-original", "observations": 2, "openDebt": 1,
            "openDebtIds": [DEBT], "freshOpenDebt": [DEBT], "resolved": [],
            "created": 1, "debtStatus": {DEBT: "open"},
            "authorityCounts": {"A": 0, "B": 1, "C": 0},
            "coverageUnknown": ["unknown-sensor"],
            "coverageUnknownReasons": {"unknown-sensor": "input unavailable"},
            "notEvaluated": [{"sensor": "optional", "reason": "input absent", "inputAbsent": True}],
            "partialCoverage": [{"sensor": "partial", "skippedCount": 1, "reasons": ["input unavailable"]}],
            "observationsBySensor": {"partial": {"drift": 1, "healthy": 1}},
        },
        "retro": {
            "sensors": [{"id": "partial", "state": "partially-covered", "registered": True,
                         "executed": False, "unknown": False, "notEvaluated": False,
                         "observations": {"drift": 1, "healthy": 1}, "routine_ids": [1],
                         "partial": True, "skippedCount": 1, "reason": "input unavailable"}],
            "routines": [{"routine": 1, "state": "partial",
                          "detectors": [{"sensor": "partial", "state": "partially-covered"}]}],
            "registered": 1, "executed": 0, "unknown": ["unknown-sensor"],
            "notEvaluated": [{"sensor": "optional", "reason": "input absent"}],
            "partiallyCovered": [{"sensor": "partial", "skippedCount": 1, "reasons": ["input unavailable"]}],
        },
        "triage": {"classA": [], "classB": [DEBT], "classC": [], "held": [],
                   "counts": {"A": 0, "B": 1, "B-report-only": 0, "C": 0}},
    }


def canonical_phases():
    """Typed historical summary with no unconstrained prose.

    Unknown sensor states are not work settlement. A partial summary can have
    an empty reasons collection (the existing producer iterates supplied skipped
    records); the original reason-bearing fixture above must instead stay hot.
    """
    phases = observation_phases(coverageUnknown=("unknown-sensor",))
    phases["observe"].update(
        openDebt=1, openDebtIds=[DEBT], freshOpenDebt=[DEBT],
        debtStatus={DEBT: "open"}, authorityCounts={"A": 0, "B": 1, "C": 0},
        partialCoverage=[{"sensor": "partial", "skippedCount": 1, "reasons": []}],
    )
    phases["retro"] = {
        "sensors": [{"id": "unknown-sensor", "state": "unknown", "registered": True,
                     "executed": False, "unknown": True, "notEvaluated": False,
                     "observations": {"drift": 0, "healthy": 0}, "routine_ids": [1]}],
        "routines": [{"routine": 1, "state": "unknown",
                      "detectors": [{"sensor": "unknown-sensor", "state": "unknown"}]}],
        "registered": 1, "executed": 0, "unknown": ["unknown-sensor"],
        "notEvaluated": [], "partiallyCovered": [],
    }
    phases["triage"] = {"classA": [], "classB": [DEBT], "classC": [], "held": [],
                        "counts": {"A": 0, "B": 1, "B-report-only": 0, "C": 0}}
    return phases


def test_original_reason_bearing_uncertainty_stays_hot_exactly(hosts):
    remote, one, two = hosts
    phases = ambiguous_canonical_phases()
    before = seed(one, {"run-a": run_record(phases=phases)})
    update(one, lambda doc: doc["work"].update({DEBT: {"debtId": DEBT, "state": "resolved", "runId": "other"}}))
    before = one.load()
    branches = refs(remote)
    assert a.phase_hold(phases) is not None
    assert a.plan(one)["eligible"] == []
    assert a.migrate(one)["archived"] == []
    assert two.load() == before
    assert refs(remote) == branches
    assert a.show(two, "run-a")["run"]["phases"] == phases


def test_historical_observation_is_not_current_settlement():
    phases = canonical_phases()
    original = deepcopy(phases)
    run = run_record(phases=phases)
    history = [{"from": "escalated", "to": "resolved", "at": END, "reason": "synthetic settlement"}]
    document = {"leases": {}, "work": {
        DEBT: {"debtId": DEBT, "authority": "B", "state": "resolved", "runId": "other", "history": history},
        "debt-c": {"debtId": "debt-c", "authority": "C", "state": "resolved", "runId": "other", "history": history},
    }}
    assert a.phase_hold(phases) is None
    assert a.eligible(document, run)
    assert phases == original  # unknown/partial coverage is preserved, not normalized
    for state in ("queued", "blocked", "escalated", "landed", "building", "proposed", "verified"):
        document["work"][DEBT]["state"] = state
        assert not a.eligible(document, run)
    document["work"].clear()
    assert not a.eligible(document, run)  # absent authoritative work is not settlement


@pytest.mark.parametrize("location", ["phase", "observation", "map", "sensor", "routine", "detector", "partial", "notEvaluated"])
@pytest.mark.parametrize("value", [None, "proof", {"receipt": "receipts/proof.bin"}, ["evidence/build-output"]])
def test_unknown_fields_fail_closed_at_each_supported_nesting(location, value):
    phases = canonical_phases()
    target = {
        "phase": phases, "observation": phases["observe"],
        "map": phases["observe"]["observationsBySensor"]["sensor-000000"],
        "sensor": phases["retro"]["sensors"][0],
        "routine": phases["retro"]["routines"][0],
        "detector": phases["retro"]["routines"][0]["detectors"][0],
        "partial": phases["observe"]["partialCoverage"][0],
        # Every reason-bearing notEvaluated entry is now held, not just its
        # unknown sibling. Preserve that original nested refusal regression.
        "notEvaluated": {},
    }[location]
    assert a.phase_hold(phases) is None
    if location == "notEvaluated":
        target.update(sensor="optional", reason="input absent")
        phases["observe"]["notEvaluated"] = [target]
    target["futureReference"] = value
    assert a.phase_hold(phases) is not None


@pytest.mark.parametrize("phases", [None, [], ["proof"], {"observe": None},
    {"observe": []}, {"observe": {"observations": True}},
    {"observe": {"debtStatus": {"proof.bin": "resolved"}}},
    {"observe": {"coverageUnknown": [None]}},
    {"retro": {"sensors": [{"id": "sensor", "state": "executed", "routine_ids": [True]}]}},
    {"retro": {"routines": [{"routine": 1, "state": "partial", "detectors": [None]}]}},
    {"triage": {"classC": [DEBT]}}, {"reconcile": {"unresolvedWork": 1}},
    {"verify": {"results": [{"receipt": "proof"}]}},
    {"class_a": {"landings": ["proof"]}},
    {"class_b": {"dispatched": "pending"}},
])
def test_wrong_types_and_operational_records_stay_hot(phases):
    assert a.phase_hold(phases) is not None


def test_inline_character_scan_preserves_conservative_token_semantics():
    import itertools
    import re

    # Compare the old intended text predicate only on tiny exhaustive inputs;
    # never execute its pathological large-payload regex in the suite.
    for length in range(5):
        for characters in itertools.product("x._-/π :", repeat=length):
            text = "".join(characters)
            expected = re.search(r"[/\\~:]|[\w.-]+\.[\w.-]+", text) is None
            assert a.phaseText(text) == expected


def test_large_inline_validation_has_bounded_single_pass_work(monkeypatch):
    # No wall-clock threshold, truncation or small-payload substitute. Forbid
    # the old regex scanner and count actual visits over a >2 MiB adversarial
    # dot-free token, then exercise a late filename/path and repeated dots.
    payload = "x" * (3 * 1024 * 1024)
    visits = 0

    def counted(value):
        nonlocal visits
        for index, character in enumerate(value):
            visits += 1
            yield index, character

    def no_regex(*args, **kwargs):
        pytest.fail("inline text must not use an unbounded regex scanner")

    monkeypatch.setattr(a, "enumerate", counted, raising=False)
    with monkeypatch.context() as patch:
        patch.setattr(a.re, "search", no_regex)
        assert a.phaseText(payload)
        assert visits == len(payload)
        visits = 0
        assert a.phaseText(payload + ".")
        assert visits == len(payload) + 1
        visits = 0
        assert not a.phaseText(payload + ".bin")
        assert visits <= len(payload) + 4
        assert not a.phaseText(payload + "/proof")
        assert not a.phaseText("." * len(payload))
    # The bounded lexical diagnostic is NOT a semantic portability gate.
    assert a.phase_hold({"observe": {"payload": payload}}) is not None


def test_canonical_historical_shapes_roundtrip_without_losing_uncertainty(hosts):
    _, one, two = hosts
    phases = canonical_phases()
    seed(one, {"run-a": run_record(phases=phases)})
    update(one, lambda doc: doc["work"].update({DEBT: {
        "debtId": DEBT, "state": "resolved", "runId": "other",
        "history": [{"from": "escalated", "to": "resolved", "at": END, "reason": "synthetic settlement"}],
    }}))
    update(one, lambda doc: doc["work"][DEBT].update(authority="B"))
    before, _ = one.load()
    assert a.migrate(one)["archived"] == ["run-a"]
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]
    after, _ = two.load()
    for key in ("work", "leases", "lane"):
        assert after[key] == before[key]


def test_historical_debt_settlement_is_rechecked_after_cas_conflict(hosts):
    _, one, two = hosts
    phases = canonical_phases()
    seed(one, {"run-a": run_record(phases=phases)})
    update(one, lambda doc: doc["work"].update({DEBT: {
        "debtId": DEBT, "state": "resolved", "runId": "other",
        "history": [{"from": "escalated", "to": "resolved", "at": END, "reason": "synthetic settlement"}],
    }}))
    update(one, lambda doc: doc["work"][DEBT].update(authority="B"))
    raced = False

    def race(stage):
        nonlocal raced
        if stage == "before-cas" and not raced:
            raced = True
            update(two, lambda doc: doc["work"][DEBT].update(state="escalated"))

    assert a.migrate(one, checkpoint=race)["archived"] == []
    assert raced
    hot, _ = two.load()
    assert hot["runs"]["run-a"]["phases"] == phases
    assert a.POINTER not in hot["runs"]["run-a"]
    assert hot["work"][DEBT]["state"] == "escalated"
    assert a.history(two)["entries"] == []
