"""Production resource profile, smaller transport caps and retained real proofs."""
from __future__ import annotations

import copy
from dataclasses import asdict
from pathlib import Path

import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core
from .coordination_helpers import NAMESPACE, FakeServices, evidence, proof, seed, subject


_REAL_PROOF_SOURCES: dict[str, str] | None = None


def realProof(candidate):
    global _REAL_PROOF_SOURCES
    if _REAL_PROOF_SOURCES is None:
        root = Path(__file__).resolve().parents[3]
        _REAL_PROOF_SOURCES = {
            key: (root / path).read_bytes().decode("utf-8")
            for key, path in zip(
                ("policy", "producerRegistry", "authority"),
                (
                    "founder/steward/POLICY.yaml",
                    "founder/steward/pr-producers.json",
                    "founder/steward/decisions/steward-pr-maintenance-authority.json",
                ),
            )
        }
    value = proof(candidate)
    value.update(_REAL_PROOF_SOURCES)
    return value


class Exact(FakeServices):
    def authorize(self, namespace, candidate, binding):
        if namespace != NAMESPACE or binding != self.expected:
            raise core.CoordinationError("fixture exact proof mismatch")


def test_default_eight_mib_real_store_exceeds_old_profile_and_respects_smaller_transport(tmp_path, monkeypatch):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    monkeypatch.delenv("GAIA_STEWARD_LEDGER_MAX_BYTES", raising=False)
    services = Exact()
    coord = core.PrWriteCoordinator(ledger.GitRefLedgerStore(first, ref=core.REF), binding, services)
    assert coord.byteLimit() == 8 * 1024 * 1024
    for number in (1, 2, 3):
        candidate = subject(number)
        bindingProof = realProof(candidate)
        if number < 3:
            for key in ("policy", "producerRegistry", "authority"):
                bindingProof[key] = '"' * core.MAX_SOURCE_BYTES
        services.expected = bindingProof
        token = coord.reserve(candidate, bindingProof, "stable-run", "owner", f"reserve-{number}").token
        coord.cancelPrepared(token, "unsent", f"cancel-{number}")
    document, tip, state = coord._load()
    actual = len(ledger.serialize(document))
    assert 512 * 1024 < actual < 1024 * 1024
    cold = core.PrWriteCoordinator(ledger.GitRefLedgerStore(second, ref=core.REF), binding, services)
    assert len(cold.inspect()["operations"]) == 3 and state["activeOperationId"] is None
    assert int(coord.store.plumb(["cat-file", "-s", f"{tip}:ledger.json"])) == actual
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(1024 * 1024))
    assert coord.byteLimit() == 1024 * 1024
    extra = proof(subject(4))
    for key in ("policy", "producerRegistry", "authority"):
        extra[key] = '"' * core.MAX_SOURCE_BYTES
    services.expected = extra
    with pytest.raises(ledger.LedgerUnavailable):
        coord.reserve(subject(4), extra, "run-4", "owner", "reserve-4")
    assert coord.store.remoteTip() == tip and len(cold.inspect()["operations"]) == 3
    assert services.invocations == services.effects == []
    with pytest.raises(core.CoordinationError):
        core.ResourceProfile(9 * 1024 * 1024).validate()
    print(f"production-profile retained-real-store-bytes={actual} records=3 cap={8 * 1024 * 1024}")


def test_all_128_current_complete_source_records_fit_but_record_129_refuses():
    state, events = core.initialState(), []
    def append(kind, operationId, args, transitionId, now):
        event = {"id": transitionId, "kind": kind, "operationId": operationId, "args": copy.deepcopy(args),
                 "time": asdict(now), "limits": asdict(core.Limits()) if kind in {"reserve", "claim"} else None}
        core.applyEvent(state, event, NAMESPACE)
        events.append(event)
    for index in range(128):
        candidate = subject(index + 1)
        operationId = core.logicalId(NAMESPACE, candidate)
        now = core.TimeBounds(10000 + index * 3601, 10000 + index * 3601, "authoritative-fixture-clock")
        append("reserve", operationId, {"subject": candidate, "proof": realProof(candidate), "runId": f"stable-run-{index}", "ownerId": "owner"}, f"reserve-{index}", now)
        token = core.tokenFor(state["operations"][operationId])
        append("intent", operationId, {"token": asdict(token), "request": core.exactRequest(NAMESPACE, candidate)}, f"intent-{index}", now)
        append("claim", operationId, {"token": asdict(token)}, f"claim-{index}", now)
        append("complete", operationId, {"token": asdict(token), "evidence": evidence(state["operations"][operationId], "completed-effect", "merged")}, f"complete-{index}", now)
    document = ledger.empty_ledger()
    document["generation"] = len(events) + 1
    document["operations"] = {core.KEY: {"schemaVersion": core.SCHEMA, "namespace": asdict(NAMESPACE), "events": events}}
    size = len(ledger.serialize(document))
    assert core.fold(events, NAMESPACE) == state
    assert len(state["operations"]) == 128 and state["activeOperationId"] is None
    assert 512 * 1024 < size < 8 * 1024 * 1024 - core.OUTCOME_HEADROOM
    with pytest.raises(core.Refused, match="anti-replay"):
        append("reserve", core.logicalId(NAMESPACE, subject(129)), {"subject": subject(129), "proof": realProof(subject(129)),
               "runId": "run-129", "ownerId": "owner"}, "reserve-129", now)
    assert len(state["operations"]) == 128
    print(f"complete-current-proof capacity-model records=128 serialized-bytes={size} events={len(events)}")
