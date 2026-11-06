"""Exact persisted-byte boundaries and complete current source proof bindings.

Administrative prefix fixtures use real single-event Git commits and normal
schema/replay validation; they do not modify coordinator/store predicates or
bounds. Only the subsequent public reservation/invocation is the tested action.
"""

from __future__ import annotations

import copy
from dataclasses import asdict
from pathlib import Path

import pytest

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance import coordination as core
from .coordination_helpers import FakeServices, NAMESPACE, coordinator, evidence, proof, seed, subject

SOURCE_BYTES = 64 * 1024
SOURCE_PATHS = {
    "policy": "founder/steward/POLICY.yaml",
    "producerRegistry": "founder/steward/pr-producers.json",
    "authority": "founder/steward/decisions/steward-pr-maintenance-authority.json",
}


class ExactProofServices(FakeServices):
    """Synthetic trusted verifier, configured to match complete source bytes."""

    def __init__(self, expected, namespace=NAMESPACE):
        super().__init__()
        self.expected = copy.deepcopy(expected)
        self.namespace = namespace
        self.authorizations = 0

    def authorize(self, namespace, candidate, binding):
        self.authorizations += 1
        if not self.authorized or namespace != self.namespace or binding != self.expected:
            raise core.CoordinationError("exact fixture source proof/current authority mismatch")


@pytest.mark.parametrize("action", ["merge", "close"])
def test_complete_current_source_text_proof_round_trip(tmp_path, monkeypatch, action):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    root = Path(__file__).resolve().parents[3]
    candidate = subject(action=action)
    bindingProof = proof(candidate)
    for key, path in SOURCE_PATHS.items():
        bindingProof[key] = (root / path).read_bytes().decode("utf-8")
    sizes = {key: len(bindingProof[key].encode("utf-8")) for key in SOURCE_PATHS}
    # Report sizes only, never print or use assertion diffs of the source text.
    print(f"current-source raw-byte-sizes={sizes}")
    services = ExactProofServices(bindingProof)
    coord = coordinator(first, binding, services)
    token = coord.reserve(candidate, bindingProof, "stable-run", "owner", "reserve").token
    reservedBytes = len(ledger.serialize(coord._load()[0]))
    print(f"current-source action={action} proof-json-bytes={len(core.canonical(bindingProof))} "
          f"reserved-bytes={reservedBytes} remaining-bytes={524288 - reservedBytes}")
    coord.recordIntent(token, core.exactRequest(NAMESPACE, candidate), "intent")
    result = coord.invoke(token, "claim")
    assert result.status == core.CommitStatus.NEW and result.state == "completed-effect"
    assert services.authorizations == 2
    assert len(services.invocations) == len(services.effects) == 1
    cold = coordinator(second, binding, ExactProofServices(bindingProof))
    document, tip, state = cold._load()
    operation = state["operations"][token.operationId]
    assert core.digest(operation["proof"]) == core.digest(bindingProof)
    assert operation["state"] == "completed-effect" and state["activeOperationId"] is None
    assert int(cold.store.plumb(["cat-file", "-s", f"{tip}:ledger.json"])) == len(ledger.serialize(document))
    assert len(ledger.serialize(document)) <= 524288 == core.MAX_BYTES
    print(f"current-source action={action} settled-bytes={len(ledger.serialize(document))}")


@pytest.mark.parametrize("key", list(SOURCE_PATHS))
def test_source_limits_are_utf8_bytes_not_characters_and_other_limits_stay_small(key):
    candidate = subject()
    bindingProof = proof(candidate)
    bindingProof[key] = "é" * (SOURCE_BYTES // 2)
    core.validateProof(candidate, bindingProof)
    bindingProof[key] += "x"
    with pytest.raises(core.CoordinationError, match="bounded text"):
        core.validateProof(candidate, bindingProof)
    for other, limit in (("justification", 2048),):
        bindingProof = proof(candidate)
        bindingProof[other] = "x" * (limit + 1)
        with pytest.raises(core.CoordinationError, match="bounded text"):
            core.validateProof(candidate, bindingProof)
    for other, limit in (("source", 256), ("detail", 2048), ("verifier", 256)):
        bindingProof = proof(candidate)
        bindingProof["verification"][other] = "x" * (limit + 1)
        with pytest.raises(core.CoordinationError, match="bounded text"):
            core.validateProof(candidate, bindingProof)


def modeledBoundary(paddingProof, *, admission=False):
    """Full valid history model; final event is the public operation under test."""
    state, events = core.initialState(), []
    now = core.TimeBounds(10000, 10000, "fixture-authoritative-clock")

    def append(kind, operationId, args, transitionId):
        event = {"id": transitionId, "kind": kind, "operationId": operationId,
                 "args": copy.deepcopy(args), "time": asdict(now),
                 "limits": asdict(core.Limits()) if kind in {"reserve", "claim"} else None}
        core.applyEvent(state, event, NAMESPACE)
        events.append(event)

    firstProof = proof(subject(1))
    for key in SOURCE_PATHS:
        firstProof[key] = '"' * SOURCE_BYTES  # byte-bound sources, actual JSON escaping doubles size
    for number, bindingProof in ((1, firstProof), (2, paddingProof)):
        candidate = subject(number)
        operationId = core.logicalId(NAMESPACE, candidate)
        append("reserve", operationId, {"subject": candidate, "proof": bindingProof, "runId": f"run-{number}",
                                       "ownerId": f"owner-{number}"}, f"reserve-{number}")
        token = core.tokenFor(state["operations"][operationId])
        append("cancel", operationId, {"token": asdict(token), "reason": "administrative canceled-unsent fixture"}, f"cancel-{number}")
    candidate = subject(3)
    operationId = core.logicalId(NAMESPACE, candidate)
    append("reserve", operationId, {"subject": candidate, "proof": proof(candidate), "runId": "active-run",
                                   "ownerId": "active-owner"}, "reserve-active")
    token = core.tokenFor(state["operations"][operationId])
    if not admission:
        append("intent", operationId, {"token": asdict(token), "request": core.exactRequest(NAMESPACE, candidate)}, "intent-active")
        now = core.TimeBounds(10121, 10121, "fixture-authoritative-clock")
        append("takeover", operationId, {"token": asdict(token), "newOwnerId": "adopted-owner"}, "takeover-active")
        token = core.tokenFor(state["operations"][operationId])
        append("claim", operationId, {"token": asdict(token)}, "claim-active")
        operation = state["operations"][operationId]
        append("complete", operationId, {"token": asdict(token), "evidence": evidence(operation, "completed-effect", "merged")},
               core.digest(["claim-active", "complete"]))
    document = ledger.empty_ledger()
    document["generation"] = len(events) + 1
    document["operations"] = {core.KEY: {"schemaVersion": core.SCHEMA, "namespace": asdict(NAMESPACE), "events": events}}
    core.fold(events, NAMESPACE)
    return document, token


def boundaryDocument(target, *, admission=False):
    """Tune only canceled-record proof text; no generation/predicate bypass."""
    paddingProof = proof(subject(2))
    for key in SOURCE_PATHS:
        paddingProof[key] = "p"
    document, _ = modeledBoundary(paddingProof, admission=admission)
    remaining = target - len(ledger.serialize(document))
    assert remaining > 0
    for key in SOURCE_PATHS:
        count = min(SOURCE_BYTES - 1, remaining)
        paddingProof[key] += "p" * count
        remaining -= count
    assert remaining == 0
    document, token = modeledBoundary(paddingProof, admission=admission)
    assert len(ledger.serialize(document)) == target
    return document, token


def seedAdministrativePrefix(coord, document, count):
    """Real commits for every validated prefix, within the unchanged byte cap.

    Near-capacity prefix provisioning is administrative fixture authority, not a
    claim that production reserve would admit that artificial history. All
    resulting commits must pass normal cold coordinator validation unchanged.
    """
    current, tip = coord.store.load()
    for event in document["operations"][core.KEY]["events"][:count]:
        current["operations"][core.KEY]["events"].append(copy.deepcopy(event))
        core.fold(current["operations"][core.KEY]["events"], NAMESPACE)
        persisted = ledger.nextGeneration(current)
        assert len(ledger.serialize(persisted)) <= 524288 == core.MAX_BYTES
        tip = coord.store.compare_and_swap(tip, current, "disposable valid administrative event prefix")
        current = persisted
    return tip


@pytest.mark.parametrize("overflow", [0, 1], ids=["exact-fit", "one-byte-overflow"])
def test_real_store_completion_generation_9_to_10_byte_boundary(tmp_path, monkeypatch, overflow):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    modeled, token = boundaryDocument(524288 + overflow)
    services = FakeServices(now=10121)
    coord = coordinator(first, binding, services)
    seedAdministrativePrefix(coord, modeled, 7)  # generation 8; public claim=9, completion=10
    assert coordinator(second, binding).inspect()["operations"][token.operationId]["state"] == "intent"
    calls, beforeCompletion = [], []
    originalCas, originalCompletion = coord.store.compare_and_swap, services.completion

    def observedCas(expected, document, message):
        calls.append(document["generation"])
        return originalCas(expected, document, message)

    def capturedCompletion(operation, invocationId, response):
        actual, tip = coord.store.load()
        beforeCompletion.append((tip, len(ledger.serialize(actual))))
        assert actual["generation"] == 9
        return originalCompletion(operation, invocationId, response)

    monkeypatch.setattr(coord.store, "compare_and_swap", observedCas)
    services.completion = capturedCompletion
    result, uncertain = None, None
    try:
        result = coord.invoke(token, "claim-active")
    except core.InvocationUncertain as exc:
        uncertain = exc
    assert (result is None) != (uncertain is None)  # exactly one post-entry outcome
    if uncertain is not None:
        # Settlement failure is still only uncertainty; the authentic typed
        # capacity refusal is retained as the sanitized cause and __cause__.
        assert uncertain.cause == "capacity"
        assert isinstance(uncertain.__cause__, core.CapacityRefused)
        assert isinstance(uncertain.__cause__, core.Refused)
        assert str(uncertain.__cause__) == "critical record capacity exhausted; settlement headroom retained"
    refusal = uncertain.__cause__ if uncertain is not None else None
    rawDocument, _ = coord.store.load()  # ordinary store read, including a failing old-guard probe
    print(f"completion-probe overflow={overflow} returned-state={None if result is None else result.state} "
          f"refused={refusal is not None} cause={None if uncertain is None else uncertain.cause} "
          f"persisted-bytes={len(ledger.serialize(rawDocument))} "
          f"generation={rawDocument['generation']} invocations={len(services.invocations)}")
    if overflow:
        assert refusal is not None and "capacity" in str(refusal)
        assert result is None  # no false completed-success after the actual adapter effect
    else:
        assert refusal is None
        assert result.status == core.CommitStatus.NEW and result.state == "completed-effect"
    assert len(services.invocations) == len(services.effects) == 1
    assert calls == ([8] if overflow else [8, 9])  # store alone increments; no double increment
    for client in (coord, coordinator(second, binding)):
        actual, tip, state = client._load()
        actualBytes = len(ledger.serialize(actual))
        assert int(client.store.plumb(["cat-file", "-s", f"{tip}:ledger.json"])) == actualBytes <= 524288
        if overflow:
            assert (tip, actualBytes) == beforeCompletion[0]
            assert actual["generation"] == 9
            assert state["activeOperationId"] == token.operationId
            assert state["operations"][token.operationId]["state"] == "possibly-sent"
            assert core.usage(state, services.now, "active-run", "merge") == (1, 1)
        else:
            assert actual["generation"] == 10 and actualBytes == 524288
            assert state["activeOperationId"] is None
    if overflow:
        assert coord.invoke(token, "claim-active").status == core.CommitStatus.ALREADY
        assert len(services.invocations) == 1
    print(f"completion-boundary overflow={overflow} target={524288 + overflow} preincrement={524287 + overflow} "
          f"canonical-bytes={actualBytes} generation={actual['generation']} invocation-count={len(services.invocations)}")


@pytest.mark.parametrize("overflow", [0, 1], ids=["exact-headroom", "headroom-short-one-byte"])
def test_admission_accounts_for_exact_persisted_bytes_and_future_generation_digits(tmp_path, monkeypatch, overflow):
    _, binding, first, second = seed(tmp_path, monkeypatch)
    futureDigits = len(str(core.MAX_HISTORY)) - 1  # admission persists generation 6
    target = 524288 - core.OUTCOME_HEADROOM - futureDigits + overflow
    modeled, _ = boundaryDocument(target, admission=True)
    services = FakeServices()
    coord = coordinator(first, binding, services)
    before = seedAdministrativePrefix(coord, modeled, 4)  # two canceled records; generation 5
    result, refusal = None, None
    try:
        result = coord.reserve(subject(3), proof(subject(3)), "active-run", "active-owner", "reserve-active")
    except core.Refused as exc:
        refusal = exc
    print(f"admission-probe overflow={overflow} refused={refusal is not None} persisted-candidate={target}")
    if overflow:
        assert refusal is not None and "headroom" in str(refusal)
        assert result is None
    else:
        assert refusal is None
        assert coord.inspect()["activeOperationId"] == result.token.operationId
    actual, tip, state = coordinator(second, binding)._load()
    if overflow:
        assert tip == before and actual["generation"] == 5 and state["activeOperationId"] is None
    else:
        assert actual["generation"] == 6 and len(ledger.serialize(actual)) == target
        assert 524288 - len(ledger.serialize(actual)) == core.OUTCOME_HEADROOM + futureDigits
    assert services.invocations == services.effects == []
    print(f"admission-boundary overflow={overflow} persisted-candidate={target} future-generation-bytes={futureDigits} "
          f"canonical-bytes={len(ledger.serialize(actual))}")


@pytest.mark.parametrize("outcome", ["complete", "merge-terminal"])
def test_max_source_escaping_public_paths_fit_outcome_and_generation_headroom(tmp_path, monkeypatch, outcome):
    namespace = core.Namespace("f" * 256, "\t" * 256, "o" * 127 + "/" + "r" * 128, NAMESPACE.epoch)
    _, binding, first, second = seed(tmp_path, monkeypatch, namespace)
    services = ExactProofServices(proof(), namespace)
    coord = coordinator(first, binding, services)
    primer = coord.reserve(subject(), proof(), "primer-run", "primer-owner", "primer-reserve").token
    coord.cancelPrepared(primer, "unsent", "primer-cancel")
    candidate = subject(core.MAX_INTEGER, "close" if outcome == "complete" else "merge")
    for key in ("prId", "baseRef", "producerId"):
        candidate[key] = "\t" * 256
    candidate["reason"] = "\t" * 2048
    candidate["replacement"] = {"repositoryId": "\t" * 256, "prId": "\t" * 256,
                                "number": core.MAX_INTEGER, "headSha": "d" * 40}
    bindingProof = proof(candidate)
    for key, char in zip(SOURCE_PATHS, ('"', "\\", "\t")):
        bindingProof[key] = char * SOURCE_BYTES
    bindingProof["justification"] = "\t" * 2048
    verification = bindingProof["verification"]
    verification.update(builder="\t" * 255 + "b", verifier="\t" * 255 + "v",
                        source="\t" * 256, detail="\t" * 2048)
    services.expected = copy.deepcopy(bindingProof)
    start = core.MAX_INTEGER - 1000
    services.now = core.TimeBounds(start, start + 30, "\t" * 128)
    token = coord.reserve(candidate, bindingProof, "\t" * 128, "\t" * 128, "\t" * 127 + "r").token
    reserved = len(ledger.serialize(coord._load()[0]))
    coord.recordIntent(token, core.exactRequest(namespace, candidate), "\t" * 127 + "i")
    for number in range(3):
        instant = start + (number + 1) * 151
        services.now = core.TimeBounds(instant, instant + 30, "\t" * 128)
        token = coord.takeover(token, "\t" * 127 + str(number), "\t" * 127 + str(number)).token
    claimId = "\t" * 127 + "s"

    def maxEvidence(operation, kind, observedState):
        result = evidence(operation, kind, observedState)
        result.update(source="\t" * 256, detail="\t" * 2048)
        return result

    if outcome == "complete":
        originalInvoke, originalCompletion = services.invoke, services.completion
        services.response = "reopened"
        def pausedReturn(request, invocationId):
            response = originalInvoke(request, invocationId)
            assert coord.recover(token.operationId).state == "quarantined"
            tip = coord.store.remoteTip()
            assert coord.recover(token.operationId).status == core.CommitStatus.ALREADY
            assert coord.store.remoteTip() == tip
            return response
        def authenticatedCompletion(operation, invocationId, response):
            verified = originalCompletion(operation, invocationId, response)
            return maxEvidence(operation, verified["kind"], verified["observedState"])
        services.invoke, services.completion = pausedReturn, authenticatedCompletion
        result = coord.invoke(token, claimId)
        assert result.state == "completed-effect"
    else:
        services.response = "lost"
        assert coord.invoke(token, claimId).state == "unknown"
        assert coord.recover(token.operationId).state == "quarantined"
        tip = coord.store.remoteTip()
        assert coord.recover(token.operationId).status == core.CommitStatus.ALREADY
        assert coord.store.remoteTip() == tip
        services.observation = lambda operation: maxEvidence(operation, "observed-terminal", "merged")
        result = coord.recover(token.operationId)
        assert result.state == "observed-terminal"
    assert len(services.invocations) == len(services.effects) == 1
    actual, _, state = coordinator(second, binding, ExactProofServices(bindingProof, namespace))._load()
    assert state["activeOperationId"] is None
    finalBytes = len(ledger.serialize(actual))
    growth = finalBytes - reserved
    future = actual["operations"][core.KEY]["events"][3:]  # after active reservation at generation 4
    # Structural upper bound for later records at the largest possible fence;
    # this is size arithmetic only, not a claim of a new authorized transition.
    fenceExtra = sum("token" in event["args"] for event in future) * (len(str(core.MAX_OPERATIONS * 4)) - 1)
    generationExtra = len(str(core.MAX_HISTORY)) - len(str(actual["generation"]))
    boundedGrowth = growth + fenceExtra + generationExtra
    assert boundedGrowth <= core.OUTCOME_HEADROOM
    assert finalBytes <= 524288 == core.MAX_BYTES
    assert core.digest(state["operations"][token.operationId]["proof"]) == core.digest(bindingProof)
    print(f"public-max outcome={outcome} raw-source-bytes={sum(len(bindingProof[key].encode('utf-8')) for key in SOURCE_PATHS)} "
          f"source-json-bytes={len(core.canonical({key: bindingProof[key] for key in SOURCE_PATHS}))} "
          f"reserved-bytes={reserved} final-bytes={finalBytes} event-growth={growth} fence-growth-allowance={fenceExtra} "
          f"generation-growth-allowance={generationExtra} bounded-growth={boundedGrowth} "
          f"headroom-slack={core.OUTCOME_HEADROOM - boundedGrowth} final-generation={actual['generation']}")
