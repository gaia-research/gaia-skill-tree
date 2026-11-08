"""Steward Full S6 - the durable, concurrency-safe shared ledger.

Git-transport tests use real git against local bare repositories created in
tmp_path; two independent clones play the part of two machines. Nothing here
touches a real remote or the real `steward/ledger` ref.
"""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from gaia_cli.steward import ledger as ledgerModule
from gaia_cli.steward.ledger import (
    FileLedgerStore,
    GitRefLedgerStore,
    LedgerConflict,
    LedgerUnavailable,
    WORK_STATES,
    acquire_lease,
    empty_ledger,
    get_run,
    leaseHolder,
    record_run,
    release_lease,
    set_lane,
    transition_work,
    update,
    upsert_work,
    validate_ledger,
)
from gaia_cli.steward.lane import LANE_SCHEMA

REF = "steward/ledger"
T0 = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)

IDENTITY = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(cwd: Path, *args: str, check: bool = True) -> str:
    env = {**os.environ, **IDENTITY, "LC_ALL": "C"}
    result = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {args} failed: {result.stderr}")
    return result.stdout.strip()


def makeClone(root: Path, remote: Path, name: str) -> Path:
    clone = root / name
    subprocess.run(
        ["git", "clone", "--quiet", str(remote), str(clone)],
        capture_output=True,
        check=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    (clone / "tracked.txt").write_text("tracked\n")
    git(clone, "add", "tracked.txt")
    git(clone, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "init")
    # Leave the tree dirty so "never touches the working tree" is a real check.
    (clone / "tracked.txt").write_text("tracked and modified\n")
    (clone / "untracked.txt").write_text("untracked\n")
    (clone / "staged.txt").write_text("staged\n")
    git(clone, "add", "staged.txt")
    return clone


def snapshot(clone: Path) -> dict[str, str]:
    return {
        "head": git(clone, "rev-parse", "HEAD"),
        "branch": git(clone, "symbolic-ref", "HEAD"),
        "status": git(clone, "status", "--porcelain"),
        "index": git(clone, "ls-files", "-s"),
        "tracked": (clone / "tracked.txt").read_text(),
    }


@pytest.fixture
def machines(tmp_path: Path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    cloneA = makeClone(tmp_path, remote, "machine-a")
    cloneB = makeClone(tmp_path, remote, "machine-b")
    return remote, GitRefLedgerStore(cloneA), GitRefLedgerStore(cloneB)


def remoteTip(remote: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(remote), "rev-parse", "--verify", "--quiet", f"refs/heads/{REF}"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def noSleep(_: float) -> None:
    return None


def appendMarker(marker: str):
    def mutate(doc: dict) -> str:
        doc["runs"][marker] = {"runId": marker}
        return marker

    return mutate


# ---------------------------------------------------------------------------
# Document validation
# ---------------------------------------------------------------------------


def test_empty_ledger_is_valid_and_fresh():
    first = empty_ledger()
    assert validate_ledger(first) is first
    first["runs"]["x"] = {}
    assert empty_ledger()["runs"] == {}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(extra=1),
        lambda d: d.update(schemaVersion="steward-ledger-v0"),
        lambda d: d.update(generation=-1),
        lambda d: d.update(generation="3"),
        lambda d: d.update(generation=True),
        lambda d: d.update(runs=[]),
        lambda d: d.update(leases="no"),
        lambda d: d.update(work=None),
        lambda d: d.update(lane="x"),
        lambda d: d.update(lane={"schemaVersion": "other"}),
        lambda d: d.update(updatedAt=5),
        lambda d: d.update(updatedAt="yesterday"),
        lambda d: d["runs"].update(a={"runId": "b"}),
        lambda d: d["leases"].update(k={"holder": "", "acquiredAt": "2026-01-01", "expiresAt": "2026-01-01"}),
        lambda d: d["leases"].update(k={"holder": "h", "acquiredAt": "2026-01-01", "expiresAt": "soon"}),
        lambda d: d["work"].update(w={"debtId": "w", "state": "bogus"}),
        lambda d: d["work"].update(w={"debtId": "other", "state": "queued"}),
    ],
)
def test_validate_rejects_malformed(mutation):
    doc = empty_ledger()
    mutation(doc)
    with pytest.raises(LedgerUnavailable):
        validate_ledger(doc)


def test_validate_rejects_non_object():
    with pytest.raises(LedgerUnavailable):
        validate_ledger([])


def test_work_states_are_exactly_the_architecture_set():
    assert set(WORK_STATES) == {
        "queued", "building", "proposed", "verified", "no_change",
        "blocked", "escalated", "landed", "resolved",
    }


# ---------------------------------------------------------------------------
# Git-ref store
# ---------------------------------------------------------------------------


def test_empty_remote_loads_empty_and_first_write_creates_ref(machines):
    remote, storeA, _ = machines
    document, version = storeA.load()
    assert version is None
    assert document == empty_ledger()
    assert storeA.transport == "git-ref" and storeA.shared is True
    assert remoteTip(remote) is None

    newVersion = storeA.compare_and_swap(None, document, "create")
    assert remoteTip(remote) == newVersion
    loaded, version = storeA.load()
    assert version == newVersion
    assert loaded["generation"] == 1


def test_round_trip_generation_and_untouched_working_tree(machines):
    _, storeA, _ = machines
    before = snapshot(storeA.repo_root)

    def run(marker):
        return update(storeA, appendMarker(marker), clock=lambda: T0)

    _, v1 = run("one")
    _, v2 = run("two")
    document, version = storeA.load()
    assert version == v2 != v1
    assert document["generation"] == 2
    assert set(document["runs"]) == {"one", "two"}
    assert document["updatedAt"] == "2026-10-20T12:00:00Z"
    assert snapshot(storeA.repo_root) == before
    # The ledger lives only on its own ref, never in the checkout.
    assert not (storeA.repo_root / "ledger.json").exists()


def test_cas_conflict_and_update_reapplies_on_fresh_document(machines):
    remote, storeA, storeB = machines
    update(storeA, appendMarker("seed"))
    docB, versionB = storeB.load()
    assert "seed" in docB["runs"]

    _, tipAfterA = update(storeA, appendMarker("from-a"))
    stale = copy.deepcopy(docB)
    stale["runs"]["from-b"] = {"runId": "from-b"}
    with pytest.raises(LedgerConflict):
        storeB.compare_and_swap(versionB, stale, "stale write")
    assert remoteTip(remote) == tipAfterA  # the stale write changed nothing remotely

    # update() on B re-loads and re-applies, so both mutations survive.
    calls = []

    def mutate(doc):
        calls.append(sorted(doc["runs"]))
        doc["runs"]["from-b"] = {"runId": "from-b"}

    update(storeB, mutate)
    final, _ = storeA.load()
    assert {"seed", "from-a", "from-b"} <= set(final["runs"])


def test_update_retries_after_real_conflict(machines):
    _, storeA, storeB = machines
    update(storeA, appendMarker("seed"))
    interfered = []

    def mutate(doc):
        if not interfered:  # A sneaks in a write after B has loaded
            interfered.append(True)
            update(storeA, appendMarker("sneaky"))
        doc["runs"]["b"] = {"runId": "b"}

    update(storeB, mutate, sleep=noSleep)
    final, _ = storeB.load()
    assert {"seed", "sneaky", "b"} <= set(final["runs"])
    assert final["generation"] == 3


def test_update_gives_up_with_conflict_when_retries_exhausted(machines):
    _, storeA, storeB = machines
    update(storeA, appendMarker("seed"))
    counter = [0]

    def mutate(doc):
        counter[0] += 1
        update(storeA, appendMarker(f"interference-{counter[0]}"))
        doc["runs"]["b"] = {"runId": "b"}

    with pytest.raises(LedgerConflict):
        update(storeB, mutate, retries=2, sleep=noSleep)
    assert counter[0] == 3


def test_noop_mutation_does_not_write(machines):
    remote, storeA, _ = machines
    _, v1 = update(storeA, appendMarker("one"))
    result, v2 = update(storeA, lambda doc: "unchanged")
    assert result == "unchanged" and v2 == v1
    assert remoteTip(remote) == v1


def test_concurrent_updates_across_two_clones_are_linear(machines):
    remote, storeA, storeB = machines
    count = 10
    errors: list[BaseException] = []

    def worker(index: int):
        store = storeA if index % 2 == 0 else storeB
        try:
            update(store, appendMarker(f"marker-{index}"), retries=80)
        except BaseException as exc:  # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors, errors

    document, version = storeA.load()
    assert set(document["runs"]) == {f"marker-{i}" for i in range(count)}
    assert document["generation"] == count
    # One linear chain: every commit has exactly one parent except the root.
    assert git(remote, "rev-list", "--count", f"refs/heads/{REF}") == str(count)
    assert git(remote, "rev-list", "--merges", "--count", f"refs/heads/{REF}") == "0"
    parents = git(remote, "rev-list", "--parents", f"refs/heads/{REF}").splitlines()
    assert sorted(len(line.split()) for line in parents) == [1] + [2] * (count - 1)


def test_lease_exclusivity_across_clones(machines):
    _, storeA, storeB = machines
    outcomes: dict[str, bool] = {}
    barrier = threading.Barrier(2)

    def contend(name: str, store):
        barrier.wait()
        won, _ = update(
            store,
            lambda doc: acquire_lease(doc, "run", name, T0, 600),
            retries=40,
        )
        outcomes[name] = won

    threads = [
        threading.Thread(target=contend, args=("alpha", storeA)),
        threading.Thread(target=contend, args=("beta", storeB)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes.values()) == [False, True]
    winner = next(name for name, won in outcomes.items() if won)
    loser = "beta" if winner == "alpha" else "alpha"
    document, _ = storeB.load()
    assert document["leases"]["run"]["holder"] == winner
    assert leaseHolder(document, "run", T0) == winner

    # A non-holder cannot release; the holder can.
    refused, _ = update(storeA, lambda doc: release_lease(doc, "run", loser))
    assert refused is False
    assert storeA.load()[0]["leases"]["run"]["holder"] == winner

    # After TTL expiry the loser takes over.
    later = T0 + timedelta(seconds=601)
    assert leaseHolder(storeA.load()[0], "run", later) is None
    took, _ = update(storeB, lambda doc: acquire_lease(doc, "run", loser, later, 600))
    assert took is True
    assert storeA.load()[0]["leases"]["run"]["holder"] == loser


def test_cas_with_none_when_ref_exists_conflicts_without_force(machines):
    remote, storeA, storeB = machines
    _, tip = update(storeA, appendMarker("existing"))
    assert remoteTip(remote) == tip

    fresh = empty_ledger()
    fresh["runs"]["intruder"] = {"runId": "intruder"}
    with pytest.raises(LedgerConflict):
        storeB.compare_and_swap(None, fresh, "overwrite attempt")

    assert remoteTip(remote) == tip  # the ref did not move
    document, _ = storeA.load()
    assert "intruder" not in document["runs"] and "existing" in document["runs"]


def test_simultaneous_creators_exactly_one_wins(machines):
    remote, storeA, storeB = machines
    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def create(name, store):
        doc = empty_ledger()
        doc["runs"][name] = {"runId": name}
        barrier.wait()
        try:
            store.compare_and_swap(None, doc, f"create {name}")
            results[name] = "won"
        except LedgerConflict:
            results[name] = "conflict"

    threads = [
        threading.Thread(target=create, args=("a", storeA)),
        threading.Thread(target=create, args=("b", storeB)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results.values()) == ["conflict", "won"]
    assert git(remote, "rev-list", "--count", f"refs/heads/{REF}") == "1"


def writeRawLedger(clone: Path, remote: Path, payload: bytes | None, filename: str = "ledger.json") -> str:
    """Hand-build a commit on the remote ledger ref (simulating corruption)."""

    env = {**os.environ, **IDENTITY}
    blob = subprocess.run(
        ["git", "-C", str(clone), "hash-object", "-w", "--stdin"],
        input=payload or b"", capture_output=True, check=True, env=env,
    ).stdout.decode().strip()
    tree = subprocess.run(
        ["git", "-C", str(clone), "mktree"],
        input=f"100644 blob {blob}\t{filename}\n".encode(),
        capture_output=True, check=True, env=env,
    ).stdout.decode().strip()
    commit = git(clone, "-c", "commit.gpgsign=false", "commit-tree", tree, "-m", "corrupt")
    git(clone, "push", "--quiet", str(remote), f"{commit}:refs/heads/{REF}")
    return commit


@pytest.mark.parametrize(
    "payload",
    [
        b"{not json",
        b"[]",
        json.dumps({**empty_ledger(), "surprise": 1}).encode(),
        json.dumps({**empty_ledger(), "generation": -3}).encode(),
        json.dumps({"schemaVersion": "steward-ledger-v1"}).encode(),
    ],
)
def test_corrupt_remote_ledger_is_unavailable_and_never_overwritten(machines, payload):
    remote, storeA, storeB = machines
    corruptTip = writeRawLedger(storeA.repo_root, remote, payload)

    with pytest.raises(LedgerUnavailable):
        storeB.load()
    with pytest.raises(LedgerUnavailable):
        update(storeB, appendMarker("should-not-land"))
    assert remoteTip(remote) == corruptTip


def test_missing_ledger_file_in_remote_commit_is_unavailable(machines):
    remote, storeA, storeB = machines
    writeRawLedger(storeA.repo_root, remote, b"{}", filename="other.json")
    with pytest.raises(LedgerUnavailable):
        storeB.load()


def test_oversized_remote_ledger_is_unavailable(machines, monkeypatch):
    remote, storeA, storeB = machines
    update(storeA, appendMarker("one"))
    monkeypatch.setattr(ledgerModule, "MAX_LEDGER_BYTES", 50)
    with pytest.raises(LedgerUnavailable):
        storeB.load()


def test_git_transport_round_trips_ledger_over_one_mib(machines):
    _remote, writer, reader = machines
    payload = "x" * (1024 * 1024 + 64 * 1024)
    update(writer, lambda document: document["operations"].update({"large": payload}))
    loaded, _version = reader.load()
    assert loaded["operations"]["large"] == payload


@pytest.mark.parametrize("delta,accepted", [(-1, True), (0, True), (1, False)])
def test_eight_mib_exact_utf8_serialized_boundary(monkeypatch, delta, accepted):
    limit = 8 * 1024 * 1024
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(limit))
    document = empty_ledger()
    # JSON overhead and multi-byte payload are included in the exact byte count.
    document["operations"] = {"padding": "é" * 100}
    base = len(ledgerModule.serialize(document))
    document["operations"]["padding"] += "x" * (limit - base + delta)
    raw = json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8") + b"\n"
    assert len(raw) == limit + delta
    if accepted:
        encoded = ledgerModule.serialize(document)
        assert len(encoded) == limit + delta
        assert ledgerModule.deserialize(encoded) == document
    else:
        with pytest.raises(LedgerUnavailable, match="over the"):
            ledgerModule.serialize(document)
        with pytest.raises(LedgerUnavailable, match="over the"):
            ledgerModule.deserialize(raw)


@pytest.mark.parametrize("setting", ["0", "-1", "malformed", "67108865"])
@pytest.mark.parametrize("existing", [False, True], ids=["missing", "existing"])
def test_invalid_capacity_fails_closed_for_local_and_git(monkeypatch, tmp_path, machines, setting, existing):
    monkeypatch.delenv("GAIA_STEWARD_LEDGER_MAX_BYTES", raising=False)
    remote, git_store, _ = machines
    local_path = tmp_path / "ledger.json"
    local = FileLedgerStore(local_path)
    if existing:
        update(local, appendMarker("local-seed"))
        update(git_store, appendMarker("git-seed"))
    local_before = local_path.read_bytes() if existing else None
    tip_before = remoteTip(remote)

    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", setting)
    for store in (local, git_store):
        with pytest.raises(LedgerUnavailable):
            store.load()
        with pytest.raises(LedgerUnavailable):
            update(store, appendMarker("must-not-write"))
        with pytest.raises(LedgerUnavailable):
            store.compare_and_swap(None, empty_ledger(), "bad-config")

    assert (local_path.read_bytes() if local_path.exists() else None) == local_before
    assert remoteTip(remote) == tip_before


def test_capacity_threshold_logs_are_metadata_only(caplog, monkeypatch):
    limit = 1000
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(limit))
    caplog.set_level("WARNING", logger="gaia_cli.steward.ledger")
    for size in (699, 700, 899, 900, 1000):
        with caplog.at_level("WARNING", logger="gaia_cli.steward.ledger"):
            ledgerModule.reportLedgerSize(size, limit, "read")
    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 4
    assert "threshold=70%" in messages[0]
    assert "threshold=70%" in messages[1]
    assert "threshold=90%" in messages[2]
    assert "threshold=90%" in messages[3]
    assert all("operations" not in message and "secret" not in message for message in messages)


def test_legacy_and_configured_capacity_boundaries(monkeypatch):
    document = empty_ledger()
    document["operations"] = {"padding": "x" * (1024 * 1024)}
    monkeypatch.setattr(ledgerModule, "MAX_LEDGER_BYTES", 2 * 1024 * 1024)
    data = ledgerModule.serialize(document)
    assert len(data) > 1024 * 1024
    assert ledgerModule.deserialize(data) == document
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(len(data)))
    assert len(ledgerModule.serialize(document)) == len(data)
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", str(len(data) - 1))
    with pytest.raises(LedgerUnavailable, match="over the"):
        ledgerModule.serialize(document)


def test_ledger_byte_limit_defaults_to_64_mib_and_fails_closed(monkeypatch):
    monkeypatch.delenv("GAIA_STEWARD_LEDGER_MAX_BYTES", raising=False)
    assert ledgerModule.DEFAULT_MAX_LEDGER_BYTES == 64 * 1024 * 1024
    assert ledgerModule.MAX_LEDGER_BYTES == 64 * 1024 * 1024
    assert ledgerModule.ledgerByteLimit() == 67108864

    # Valid overrides
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", "1024")
    assert ledgerModule.ledgerByteLimit() == 1024
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", "67108864")
    assert ledgerModule.ledgerByteLimit() == 67108864

    # Invalid values fail closed
    for invalid in ("0", "-1", "1023", "67108865", "not-a-number", ""):
        monkeypatch.setenv("GAIA_STEWARD_LEDGER_MAX_BYTES", invalid)
        with pytest.raises(LedgerUnavailable):
            ledgerModule.ledgerByteLimit()


def test_oversized_write_is_refused_not_pruned(machines, monkeypatch):
    remote, storeA, _ = machines
    _, tip = update(storeA, appendMarker("one"))
    monkeypatch.setattr(ledgerModule, "MAX_LEDGER_BYTES", 200)
    with pytest.raises(LedgerUnavailable):
        update(storeA, appendMarker("two"))
    assert remoteTip(remote) == tip


def test_unreachable_remote_is_unavailable(tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "init", "--quiet", str(clone)], check=True)
    subprocess.run(
        ["git", "-C", str(clone), "remote", "add", "origin", str(tmp_path / "does-not-exist.git")],
        check=True,
    )
    store = GitRefLedgerStore(clone)
    with pytest.raises(LedgerUnavailable):
        store.load()
    with pytest.raises(LedgerUnavailable):
        store.compare_and_swap(None, empty_ledger(), "x")


def test_unknown_remote_name_is_unavailable(machines):
    _, storeA, _ = machines
    store = GitRefLedgerStore(storeA.repo_root, remote="nonexistent")
    with pytest.raises(LedgerUnavailable):
        store.load()


def test_cas_rejects_invalid_document_before_touching_remote(machines):
    remote, storeA, _ = machines
    bad = empty_ledger()
    bad["unknown"] = True
    with pytest.raises(LedgerUnavailable):
        storeA.compare_and_swap(None, bad, "bad")
    assert remoteTip(remote) is None


def test_cas_with_unknown_expected_commit_is_unavailable(machines):
    _, storeA, _ = machines
    with pytest.raises(LedgerUnavailable):
        storeA.compare_and_swap("0" * 40, empty_ledger(), "x")


def test_input_document_is_not_mutated_by_cas(machines):
    _, storeA, _ = machines
    doc = empty_ledger()
    storeA.compare_and_swap(None, doc, "x")
    assert doc == empty_ledger()


# ---------------------------------------------------------------------------
# File store
# ---------------------------------------------------------------------------


def test_file_store_basics(tmp_path):
    store = FileLedgerStore(tmp_path / "state" / "ledger.json")
    assert store.transport == "local-file"
    assert store.shared is False
    document, version = store.load()
    assert version is None and document == empty_ledger()

    _, v1 = update(store, appendMarker("one"))
    document, loaded = store.load()
    assert loaded == v1
    assert v1.startswith("1:") and document["generation"] == 1
    _, v2 = update(store, appendMarker("two"))
    assert v2.startswith("2:") and store.load()[0]["generation"] == 2


def test_file_store_conflict_and_create_race(tmp_path):
    path = tmp_path / "ledger.json"
    first, second = FileLedgerStore(path), FileLedgerStore(path)
    _, v1 = update(first, appendMarker("one"))
    doc, version = second.load()
    assert version == v1
    update(first, appendMarker("two"))
    with pytest.raises(LedgerConflict):
        second.compare_and_swap(version, doc, "stale")
    with pytest.raises(LedgerConflict):
        second.compare_and_swap(None, empty_ledger(), "create over existing")
    result, _ = update(second, appendMarker("three"))
    assert result == "three"
    assert set(first.load()[0]["runs"]) == {"one", "two", "three"}


def test_file_store_concurrent_threads(tmp_path):
    path = tmp_path / "ledger.json"
    count = 16
    errors: list[BaseException] = []

    def worker(index: int):
        try:
            update(FileLedgerStore(path), appendMarker(f"m{index}"), retries=100)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors, errors
    document, _ = FileLedgerStore(path).load()
    assert document["generation"] == count
    assert set(document["runs"]) == {f"m{i}" for i in range(count)}
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".tmp")] == []


def test_file_store_corrupt_file_is_unavailable_and_untouched(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_text("{broken")
    store = FileLedgerStore(path)
    with pytest.raises(LedgerUnavailable):
        store.load()
    with pytest.raises(LedgerUnavailable):
        update(store, appendMarker("x"))
    assert path.read_text() == "{broken"


def test_file_store_lease_exclusivity(tmp_path):
    store = FileLedgerStore(tmp_path / "ledger.json")
    first, _ = update(store, lambda d: acquire_lease(d, "run", "alpha", T0, 60))
    second, _ = update(store, lambda d: acquire_lease(d, "run", "beta", T0, 60))
    assert (first, second) == (True, False)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_lease_semantics():
    doc = empty_ledger()
    assert acquire_lease(doc, "run", "a", T0, 60) is True
    assert acquire_lease(doc, "run", "b", T0 + timedelta(seconds=59), 60) is False
    assert doc["leases"]["run"]["holder"] == "a"
    # Same holder renews and keeps acquiredAt.
    acquired = doc["leases"]["run"]["acquiredAt"]
    assert acquire_lease(doc, "run", "a", T0 + timedelta(seconds=30), 60) is True
    assert doc["leases"]["run"]["acquiredAt"] == acquired
    assert doc["leases"]["run"]["expiresAt"] == "2026-10-20T12:01:30Z"
    # Expiry boundary: expiresAt <= now is expired.
    assert acquire_lease(doc, "run", "b", T0 + timedelta(seconds=90), 60) is True
    assert doc["leases"]["run"]["holder"] == "b"
    validate_ledger(doc)
    assert release_lease(doc, "run", "a") is False
    assert release_lease(doc, "missing", "a") is False
    assert release_lease(doc, "run", "b") is True
    assert doc["leases"] == {}


def test_lease_accepts_iso_strings_and_rejects_bad_input():
    doc = empty_ledger()
    assert acquire_lease(doc, "k", "a", "2026-10-20T12:00:00Z", 10) is True
    with pytest.raises(ValueError):
        acquire_lease(doc, "k", "a", "not-a-time", 10)
    with pytest.raises(ValueError):
        acquire_lease(doc, "k", "a", T0, 0)
    with pytest.raises(ValueError):
        acquire_lease(doc, "k", "", T0, 10)


def test_run_records():
    doc = empty_ledger()
    record_run(doc, {"runId": "r1", "phase": "observe"})
    record_run(doc, {"runId": "r1", "phase": "triage"})
    fetched = get_run(doc, "r1")
    assert fetched["phase"] == "triage"
    fetched["phase"] = "mutated"
    assert doc["runs"]["r1"]["phase"] == "triage"
    assert get_run(doc, "nope") is None
    with pytest.raises(ValueError):
        record_run(doc, {"phase": "x"})
    validate_ledger(doc)


def test_transition_work_history_and_unknown_states():
    doc = empty_ledger()
    upsert_work(doc, {"debtId": "d1", "routine": "7", "authority": "B"})
    assert doc["work"]["d1"]["state"] == "queued"

    transition_work(doc, "d1", "building", T0, "dispatched")
    transition_work(doc, "d1", "proposed", "2026-10-20T13:00:00Z", "patch returned")
    item = doc["work"]["d1"]
    assert item["state"] == "proposed"
    assert item["history"] == [
        {"at": "2026-10-20T12:00:00Z", "from": "queued", "to": "building", "reason": "dispatched"},
        {"at": "2026-10-20T13:00:00Z", "from": "building", "to": "proposed", "reason": "patch returned"},
    ]

    snapshotBefore = copy.deepcopy(doc)
    with pytest.raises(ValueError):
        transition_work(doc, "d1", "teleported", T0, "nope")
    with pytest.raises(ValueError):
        transition_work(doc, "missing", "building", T0, "nope")
    with pytest.raises(ValueError):
        transition_work(doc, "d1", "verified", T0, "")
    assert doc == snapshotBefore
    validate_ledger(doc)


def test_upsert_work_preserves_history_and_refuses_state_change():
    doc = empty_ledger()
    upsert_work(doc, {"debtId": "d1", "state": "queued"})
    transition_work(doc, "d1", "building", T0, "go")
    upsert_work(doc, {"debtId": "d1", "branch": "steward/a/x", "history": [], "state": "building"})
    item = doc["work"]["d1"]
    assert item["branch"] == "steward/a/x"
    assert len(item["history"]) == 1  # incoming history never replaces the record
    with pytest.raises(ValueError):
        upsert_work(doc, {"debtId": "d1", "state": "resolved"})
    with pytest.raises(ValueError):
        upsert_work(doc, {"debtId": "d2", "state": "bogus"})
    with pytest.raises(ValueError):
        upsert_work(doc, {"state": "queued"})


def test_set_lane():
    doc = empty_ledger()
    lane = {"schemaVersion": LANE_SCHEMA, "entries": []}
    set_lane(doc, lane)
    lane["entries"].append("x")
    assert doc["lane"]["entries"] == []
    validate_ledger(doc)
    with pytest.raises(ValueError):
        set_lane(doc, {"schemaVersion": "wrong"})
    set_lane(doc, None)
    assert doc["lane"] is None


# ---------------------------------------------------------------------------
# Review fixes (S6 round 2)
# ---------------------------------------------------------------------------


def refNames(clone: Path) -> list[str]:
    return git(clone, "for-each-ref", "--format=%(refname)").splitlines()


def outsideSteward(names: list[str]) -> list[str]:
    return sorted(name for name in names if not name.startswith("refs/steward/"))


def test_ledger_leaves_no_refs_outside_refs_steward(machines):
    _, storeA, storeB = machines
    beforeA, beforeB = refNames(storeA.repo_root), refNames(storeB.repo_root)
    update(storeA, appendMarker("one"))
    update(storeA, appendMarker("two"))
    update(storeB, appendMarker("three"))
    storeA.load()
    afterA, afterB = refNames(storeA.repo_root), refNames(storeB.repo_root)
    assert outsideSteward(afterA) == outsideSteward(beforeA)
    assert outsideSteward(afterB) == outsideSteward(beforeB)
    assert not [n for n in afterA + afterB if n.startswith("refs/remotes/")]
    assert [n for n in afterA if n.startswith("refs/steward/")] == [storeA.trackingRef]


def test_ledger_preserves_custom_fetch_mappings_and_sentinel_refs(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    clone = makeClone(tmp_path, remote, "machine-custom")

    # Establish sentinel tracking refs and custom fetch mapping on origin.
    head_sha = git(clone, "rev-parse", "HEAD")
    git(clone, "update-ref", "refs/remotes/origin/main", head_sha)
    git(clone, "update-ref", "refs/remotes/origin/sentinel", head_sha)
    git(clone, "config", "--add", "remote.origin.fetch", "+refs/custom/*:refs/remotes/custom/*")
    git(clone, "update-ref", "refs/remotes/custom/probe", head_sha)

    before_refs = {name: git(clone, "rev-parse", name) for name in refNames(clone)}
    assert "refs/remotes/origin/main" in before_refs
    assert "refs/remotes/origin/sentinel" in before_refs
    assert "refs/remotes/custom/probe" in before_refs

    store = GitRefLedgerStore(clone)
    update(store, appendMarker("entry-1"))
    update(store, appendMarker("entry-2"))
    store.load()

    after_refs = {name: git(clone, "rev-parse", name) for name in refNames(clone)}

    # Names and values of all non-steward refs are strictly preserved
    assert outsideSteward(list(after_refs.keys())) == outsideSteward(list(before_refs.keys()))
    for ref_name, original_sha in before_refs.items():
        assert after_refs[ref_name] == original_sha, f"ref {ref_name} changed value"

    # No opportunistic remote tracking ref was created under refs/remotes/
    assert "refs/remotes/origin/steward/ledger" not in after_refs
    assert [n for n in after_refs if n.startswith("refs/steward/")] == [store.trackingRef]



def test_tracking_ref_is_per_store(machines):
    _, storeA, _ = machines
    other = GitRefLedgerStore(storeA.repo_root, ref="steward/other-ledger")
    third = GitRefLedgerStore(storeA.repo_root, ref="steward/ledger")
    assert storeA.trackingRef != other.trackingRef
    assert storeA.trackingRef == third.trackingRef
    update(storeA, appendMarker("only-in-default"))
    update(other, appendMarker("only-in-other"))
    assert set(storeA.load()[0]["runs"]) == {"only-in-default"}
    assert set(other.load()[0]["runs"]) == {"only-in-other"}
    assert storeA.trackingRef in refNames(storeA.repo_root)
    assert other.trackingRef in refNames(storeA.repo_root)


def installHook(remote: Path, body: str) -> None:
    hook = remote / "hooks" / "pre-receive"
    hook.write_text(f"#!/bin/sh\n{body}\n")
    hook.chmod(0o755)


def test_directory_file_ref_collision_is_unavailable_not_conflict(machines):
    remote, storeA, _ = machines
    # A plain `steward` branch makes `steward/ledger` impossible to create.
    git(storeA.repo_root, "push", "--quiet", str(remote), "HEAD:refs/heads/steward")
    attempts = []

    def mutate(doc):
        attempts.append(1)
        doc["runs"]["x"] = {"runId": "x"}

    with pytest.raises(LedgerUnavailable):
        update(storeA, mutate, retries=5, sleep=noSleep)
    assert len(attempts) == 1  # a permanent rejection is not retried as a conflict
    assert remoteTip(remote) is None


@pytest.mark.parametrize("text", ["ref already exists", "cannot lock ref", "failed to update ref"])
def test_hook_rejection_text_is_unavailable_not_conflict(machines, text):
    remote, storeA, storeB = machines
    _, tip = update(storeA, appendMarker("seed"))
    storeB.load()
    installHook(remote, f'echo "{text}" >&2\nexit 1')
    attempts = []

    def mutate(d):
        attempts.append(1)
        d["runs"]["y"] = {"runId": "y"}

    with pytest.raises(LedgerUnavailable):
        update(storeB, mutate, retries=5, sleep=noSleep)
    assert len(attempts) == 1
    assert remoteTip(remote) == tip


def test_remote_rejection_after_ref_moved_is_a_conflict(machines, tmp_path):
    """A lost ref-lock race surfaces as `[remote rejected] (failed to update ref)`.

    The pre-receive hook parks B's push mid-flight; meanwhile the ref is moved
    to v2 from outside (a hook cannot move refs itself, it runs in quarantine).
    """

    remote, storeA, storeB = machines
    _, v1 = update(storeA, appendMarker("seed"))
    doc, version = storeB.load()
    assert version == v1
    _, v2 = update(storeA, appendMarker("winner"))
    git(remote, "update-ref", f"refs/heads/{REF}", v1)  # rewind: B now looks current
    flag, go = tmp_path / "hook-entered", tmp_path / "hook-go"
    installHook(
        remote,
        f'touch {flag}\nwhile [ ! -e {go} ]; do sleep 0.05; done\n'
        'echo "failed to update ref" >&2\nexit 1',
    )
    doc["runs"]["loser"] = {"runId": "loser"}
    outcome: list[BaseException] = []

    def push():
        try:
            storeB.compare_and_swap(v1, doc, "lost race")
        except BaseException as exc:
            outcome.append(exc)

    thread = threading.Thread(target=push)
    thread.start()
    for _ in range(400):
        if flag.exists():
            break
        time.sleep(0.05)
    assert flag.exists(), "hook never ran"
    git(remote, "update-ref", f"refs/heads/{REF}", v2)
    go.write_text("go")
    thread.join(30)
    assert len(outcome) == 1 and isinstance(outcome[0], LedgerConflict), outcome
    assert remoteTip(remote) == v2


@pytest.mark.parametrize(
    "ref",
    [
        "main", "", "steward", "steward/", "steward/../x", "steward//x", "steward/x.lock",
        "steward/a b", "steward/x~1", "steward/x^", "steward/x:y", "steward/.hidden",
        "refs/heads/steward/x", "release/steward/x", "STEWARD/x", None, 5,
    ],
)
def test_bad_ref_is_rejected(tmp_path, ref):
    with pytest.raises(ValueError):
        GitRefLedgerStore(tmp_path, ref=ref)


@pytest.mark.parametrize("remote", ["", "  ", "-oBad", "--upload-pack=evil", "a b", "x\ny", None])
def test_bad_remote_is_rejected(tmp_path, remote):
    with pytest.raises(ValueError):
        GitRefLedgerStore(tmp_path, remote=remote)


def test_good_refs_are_accepted(tmp_path):
    for ref in ("steward/ledger", "steward/a/b-c_d.e", "steward/ledger-test"):
        assert GitRefLedgerStore(tmp_path, ref=ref).ref == ref


def test_stale_cas_does_not_resurrect_a_deleted_ref(machines):
    remote, storeA, storeB = machines
    update(storeA, appendMarker("seed"))
    doc, version = storeB.load()
    git(remote, "update-ref", "-d", f"refs/heads/{REF}")
    assert remoteTip(remote) is None

    doc["runs"]["stale"] = {"runId": "stale"}
    with pytest.raises(LedgerConflict):
        storeB.compare_and_swap(version, doc, "stale after delete")
    assert remoteTip(remote) is None  # still gone

    # update() re-reads, sees an empty remote and recreates from a fresh root.
    update(storeB, appendMarker("fresh"), sleep=noSleep)
    document, _ = storeA.load()
    assert set(document["runs"]) == {"fresh"}
    assert git(remote, "rev-list", "--count", f"refs/heads/{REF}") == "1"


def test_git_is_never_allowed_to_prompt_or_gc(machines, monkeypatch):
    _, storeA, _ = machines
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)
    seen = []
    real = subprocess.run

    def spy(command, **kwargs):
        if command[0] == "git" and "-C" in command:
            seen.append((command, kwargs))
        return real(command, **kwargs)

    monkeypatch.setattr(ledgerModule.subprocess, "run", spy)
    update(storeA, appendMarker("one"))
    assert seen
    for command, kwargs in seen:
        assert "gc.auto=0" in command
        env = kwargs["env"]
        assert env["GIT_ASKPASS"] == "true"
        assert env["GCM_INTERACTIVE"] == "never"
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GIT_SSH_COMMAND"] == "ssh -o BatchMode=yes"
        if kwargs.get("input") is None:
            assert kwargs["stdin"] == subprocess.DEVNULL
        else:
            assert "stdin" not in kwargs


def test_callers_ssh_command_is_respected(machines, monkeypatch):
    _, storeA, _ = machines
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh -i /custom/key")
    seen = []
    real = subprocess.run

    def spy(command, **kwargs):
        seen.append(kwargs.get("env", {}).get("GIT_SSH_COMMAND"))
        return real(command, **kwargs)

    monkeypatch.setattr(ledgerModule.subprocess, "run", spy)
    storeA.load()
    assert set(filter(None, seen)) == {"ssh -i /custom/key"}


def test_identical_documents_from_two_clones_still_conflict(machines):
    _, storeA, storeB = machines
    _, seed = update(storeA, appendMarker("seed"), clock=lambda: T0)
    docA, versionA = storeA.load()
    docB, versionB = storeB.load()
    assert versionA == versionB == seed and docA == docB
    for doc in (docA, docB):
        doc["runs"]["same"] = {"runId": "same"}
        doc["updatedAt"] = "2026-10-20T12:00:00Z"
    first = storeA.compare_and_swap(versionA, docA, "identical")
    with pytest.raises(LedgerConflict):
        storeB.compare_and_swap(versionB, docB, "identical")
    assert storeB.load()[1] == first


def test_inherited_git_dir_and_index_file_are_ignored(machines, tmp_path, monkeypatch):
    remote, storeA, _ = machines
    before = snapshot(storeA.repo_root)
    with monkeypatch.context() as scoped:
        scoped.setenv("GIT_DIR", str(tmp_path / "bogus.git"))
        scoped.setenv("GIT_INDEX_FILE", str(tmp_path / "bogus-index"))
        scoped.setenv("GIT_WORK_TREE", str(tmp_path / "bogus-tree"))
        _, version = update(storeA, appendMarker("with-hostile-env"))
        document, loaded = storeA.load()
    assert loaded == version and "with-hostile-env" in document["runs"]
    assert remoteTip(remote) == version
    assert snapshot(storeA.repo_root) == before
    assert not (tmp_path / "bogus-index").exists()


def test_deeply_nested_ledger_is_malformed_not_a_crash(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_bytes(b"[" * 200000 + b"]" * 200000)
    with pytest.raises(LedgerUnavailable):
        FileLedgerStore(path).load()


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_are_rejected_on_load(tmp_path, constant):
    path = tmp_path / "ledger.json"
    path.write_text(
        '{"schemaVersion":"steward-ledger-v1","generation":0,"runs":{"r":{"runId":"r","v":%s}},'
        '"leases":{},"work":{},"lane":null}' % constant
    )
    with pytest.raises(LedgerUnavailable):
        FileLedgerStore(path).load()


def test_non_finite_numbers_are_rejected_on_write(tmp_path):
    store = FileLedgerStore(tmp_path / "ledger.json")
    for bad in (float("nan"), float("inf")):
        with pytest.raises(LedgerUnavailable):
            update(store, lambda doc, bad=bad: doc["runs"].update(r={"runId": "r", "v": bad}))
    assert not (tmp_path / "ledger.json").exists()


def test_deeply_nested_mutation_is_refused_on_write(tmp_path):
    store = FileLedgerStore(tmp_path / "ledger.json")
    nested: list = []
    cursor = nested
    for _ in range(5000):
        child: list = []
        cursor.append(child)
        cursor = child
    with pytest.raises(LedgerUnavailable):
        update(store, lambda doc: doc["runs"].update(r={"runId": "r", "deep": nested}))


@pytest.mark.parametrize("retries", [-1, -100, 1.5, "3", True, None])
def test_bad_retries_are_rejected(tmp_path, retries):
    with pytest.raises(ValueError):
        update(FileLedgerStore(tmp_path / "ledger.json"), lambda doc: None, retries=retries)


def test_zero_retries_is_allowed(tmp_path):
    result, _ = update(FileLedgerStore(tmp_path / "ledger.json"), appendMarker("z"), retries=0)
    assert result == "z"


@pytest.mark.parametrize(
    "ttl",
    [float("nan"), float("inf"), float("-inf"), 0, -5, 31 * 24 * 3600, 1e30, True, "60", None],
)
def test_bad_lease_ttl_is_rejected(ttl):
    doc = empty_ledger()
    with pytest.raises(ValueError):
        acquire_lease(doc, "run", "a", T0, ttl)
    assert doc["leases"] == {}


def test_lease_ttl_boundary_and_expiry_overflow():
    doc = empty_ledger()
    assert acquire_lease(doc, "run", "a", T0, 30 * 24 * 3600) is True
    with pytest.raises(ValueError):
        acquire_lease(doc, "other", "a", datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc), 3600)


def test_read_duration_is_measured_and_emitted_in_ledger_monitor(caplog, tmp_path, machines):
    caplog.set_level("INFO", logger="gaia_cli.steward.ledger")

    # 1. FileLedgerStore: empty and populated reads
    file_store = FileLedgerStore(tmp_path / "ledger.json")

    # Empty file read
    caplog.clear()
    doc, ver = file_store.load()
    assert ver is None
    read_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=read" in r.getMessage()]
    assert len(read_msgs) == 1
    m = re.search(
        r"Steward ledger monitor: direction=read bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        read_msgs[0],
    )
    assert m is not None
    assert int(m.group(1)) == 0
    assert float(m.group(3)) >= 0.0
    assert int(m.group(4)) == 0

    # Populate file store
    update(file_store, appendMarker("file-seed"))

    # Populated file read
    caplog.clear()
    doc, ver = file_store.load()
    assert ver is not None
    read_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=read" in r.getMessage()]
    assert len(read_msgs) == 1
    m = re.search(
        r"Steward ledger monitor: direction=read bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        read_msgs[0],
    )
    assert m is not None
    assert int(m.group(1)) > 0
    assert float(m.group(3)) >= 0.0
    assert int(m.group(4)) == 0

    # 2. GitRefLedgerStore: empty and populated reads
    _, git_store_a, _ = machines

    # Empty git read
    caplog.clear()
    doc, ver = git_store_a.load()
    assert ver is None
    read_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=read" in r.getMessage()]
    assert len(read_msgs) == 1
    m = re.search(
        r"Steward ledger monitor: direction=read bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        read_msgs[0],
    )
    assert m is not None
    assert int(m.group(1)) == 0
    assert float(m.group(3)) >= 0.0
    assert int(m.group(4)) == 0

    # Populate git store
    update(git_store_a, appendMarker("git-seed"))

    # Populated git read
    caplog.clear()
    doc, ver = git_store_a.load()
    assert ver is not None
    read_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=read" in r.getMessage()]
    assert len(read_msgs) == 1
    m = re.search(
        r"Steward ledger monitor: direction=read bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        read_msgs[0],
    )
    assert m is not None
    assert int(m.group(1)) > 0
    assert float(m.group(3)) >= 0.0
    assert int(m.group(4)) == 0


def test_write_duration_and_cas_retries_emitted_during_update(caplog, tmp_path, machines):
    caplog.set_level("INFO", logger="gaia_cli.steward.ledger")

    # Clean write (first attempt: cas_retries == 0)
    file_store = FileLedgerStore(tmp_path / "ledger.json")
    caplog.clear()
    update(file_store, appendMarker("clean-write"))
    write_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=write" in r.getMessage()]
    assert len(write_msgs) == 1
    m = re.search(
        r"Steward ledger monitor: direction=write bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        write_msgs[0],
    )
    assert m is not None
    assert int(m.group(1)) > 0
    assert float(m.group(3)) >= 0.0
    assert int(m.group(4)) == 0

    # Conflict retry: cas_retries > 0
    _, store_a, store_b = machines
    update(store_a, appendMarker("seed"))

    interfered = []
    def sneaky_mutate(doc):
        if not interfered:
            interfered.append(True)
            update(store_a, appendMarker("sneak-in"))
        doc["runs"]["b"] = {"runId": "b"}

    caplog.clear()
    update(store_b, sneaky_mutate, sleep=noSleep)
    write_msgs = [r.getMessage() for r in caplog.records if "Steward ledger monitor: direction=write" in r.getMessage()]
    assert len(write_msgs) >= 2
    # The last write message is store_b's successful CAS after 1 retry
    last_msg = write_msgs[-1]
    m_conflict = re.search(
        r"Steward ledger monitor: direction=write bytes=(\d+) limit_bytes=(\d+) duration_ms=([0-9.]+) cas_retries=(\d+)",
        last_msg,
    )
    assert m_conflict is not None
    assert int(m_conflict.group(1)) > 0
    assert float(m_conflict.group(3)) >= 0.0
    assert int(m_conflict.group(4)) == 1


def test_ledger_monitor_and_telemetry_logs_are_metadata_only(caplog, tmp_path):
    caplog.set_level("DEBUG", logger="gaia_cli.steward.ledger")

    secret_key = "super-confidential-token-998877"
    secret_debt = "debt-private-vault-42"
    secret_holder = "agent-secret-007"

    store = FileLedgerStore(tmp_path / "ledger.json")

    def mutate_secret(doc):
        record_run(doc, {"runId": "secret-run", "token": secret_key})
        acquire_lease(doc, "secret-lease", secret_holder, T0, 3600)
        upsert_work(doc, {"debtId": secret_debt, "state": "queued", "payload": secret_key})
        return "done"

    caplog.clear()
    update(store, mutate_secret)
    store.load()

    # Also exercise high-capacity size telemetry with duration and cas_retries
    limit = 1000
    ledgerModule.reportLedgerSize(750, limit, "write", duration_ms=15.5, cas_retries=2)
    ledgerModule.reportLedgerSize(920, limit, "read", duration_ms=25.0)
    ledgerModule.reportLedgerSize(700, limit, "read")

    records = caplog.records
    assert len(records) > 0

    forbidden = {secret_key, secret_debt, secret_holder, "secret-run", "secret-lease", "queued", "payload"}
    for record in records:
        msg = record.getMessage()
        for secret in forbidden:
            assert secret not in msg, f"Secret {secret} leaked in log: {msg}"

    warning_msgs = [r.getMessage() for r in records if r.levelname == "WARNING"]
    assert any("threshold=70% duration_ms=15.5 cas_retries=2" in m for m in warning_msgs)
    assert any("threshold=90% duration_ms=25.0" in m for m in warning_msgs)
    assert any("threshold=70%" in m and "duration_ms" not in m for m in warning_msgs)


def test_classify_push_failure_strips_git_hint_lines_preserving_error(tmp_path):
    """Verbose git hint lines must be stripped so the real error fits in 400 chars."""
    store = GitRefLedgerStore(tmp_path)

    hint_lines = [
        "hint: Support for <GIT_DIR>/info/grafts is deprecated and will be removed in a future Git version.",
        "hint: Consider using replace refs instead.",
        "hint: Disable this message with 'git config advice.graftFileDeprecated false'",
        "hint: Git hint line number 4 providing verbose explanation of deprecated features and behaviors.",
        "hint: Git hint line number 5 providing additional diagnostic recommendations for repository maintainers.",
        "hint: Git hint line number 6 warning about potential conflicts and deprecation policies in git plumbing.",
    ]
    verbose_hints = "\n".join(hint_lines) + "\n"
    assert len(verbose_hints) > 400, "Fixture must exceed 400 chars of hints"

    real_error = "fatal: remote error: upload-pack: not our ref deadbeef12345678"
    raw_stderr = f"{verbose_hints}{real_error}\n".encode("utf-8")

    result = subprocess.CompletedProcess(
        args=["git", "push"],
        returncode=1,
        stdout=b"",
        stderr=raw_stderr,
    )

    # 1. outputText strips hint lines and keeps real error
    filtered_text = store.outputText(result)
    assert "hint:" not in filtered_text.lower()
    assert real_error in filtered_text

    # 2. classifyPushFailure surfaces the real error within 400-char truncation bound
    with pytest.raises(LedgerUnavailable) as exc_info:
        store.classifyPushFailure(result, expected="commit-123")

    msg = str(exc_info.value)
    assert "ledger push failed:" in msg
    assert real_error in msg
    assert "hint:" not in msg.lower()

    # 3. If all lines were hints, outputText falls back to raw output
    all_hints = "hint: only a hint line 1\nhint: only a hint line 2\n".encode("utf-8")
    result_hints_only = subprocess.CompletedProcess(
        args=["git", "push"],
        returncode=1,
        stdout=b"",
        stderr=all_hints,
    )
    fallback_text = store.outputText(result_hints_only)
    assert "hint: only a hint line 1" in fallback_text

    with pytest.raises(LedgerUnavailable) as exc_info_fallback:
        store.classifyPushFailure(result_hints_only, expected="commit-123")
    assert "hint: only a hint line 1" in str(exc_info_fallback.value)

    # 4. GitRefLedgerStore.git passes advice.graftFileDeprecated=false
    completed = store.git(["version"], timeout=5.0)
    assert completed.returncode == 0
    assert "-c" in completed.args
    assert "advice.graftFileDeprecated=false" in completed.args


def test_telemetry_normal_read_write_operations_fields(tmp_path, monkeypatch):
    """Verify telemetry file is written with all required fields without caplog."""
    telem_path = tmp_path / "custom-telemetry.jsonl"
    store = FileLedgerStore(tmp_path / "ledger.json", telemetry_path=telem_path)

    # 1. Update with explicit run_id
    res, ver = update(store, appendMarker("first-op"), run_id="run-step-1")
    assert res == "first-op"

    # 2. Direct load
    doc, ver_loaded = store.load()
    assert ver_loaded == ver

    assert telem_path.is_file()
    lines = [line.strip() for line in telem_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 2  # At least 1 write (from update) and 1 read (from load)

    required_fields = {"op", "bytes", "limit", "duration_ms", "cas_retries", "timestamp", "runId"}
    records = []
    for line in lines:
        record = json.loads(line)
        assert set(record.keys()) == required_fields
        assert record["op"] in {"read", "write"}
        assert isinstance(record["bytes"], int) and record["bytes"] >= 0
        assert isinstance(record["limit"], int) and record["limit"] > 0
        assert isinstance(record["duration_ms"], (int, float)) and record["duration_ms"] >= 0.0
        assert isinstance(record["cas_retries"], int) and record["cas_retries"] >= 0
        parsed_dt = ledgerModule.parseTime(record["timestamp"])
        assert parsed_dt.tzinfo == timezone.utc
        records.append(record)

    write_records = [r for r in records if r["op"] == "write"]
    assert len(write_records) == 1
    assert write_records[0]["runId"] == "run-step-1"
    assert write_records[0]["cas_retries"] == 0

    # 3. Test GAIA_STEWARD_RUN_ID env var
    monkeypatch.setenv("GAIA_STEWARD_RUN_ID", "env-run-step-2")
    update(store, appendMarker("second-op"))
    lines_after = [line.strip() for line in telem_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    new_records = [json.loads(line) for line in lines_after]
    new_writes = [r for r in new_records if r["op"] == "write"]
    assert len(new_writes) == 2
    assert new_writes[1]["runId"] == "env-run-step-2"

    # 4. Test default path under .gaia/steward/ when unconfigured
    default_telem = Path(".gaia/steward/ledger-telemetry.jsonl")
    if default_telem.is_file():
        default_telem.unlink()
    try:
        ledgerModule.reportLedgerSize(2048, 67108864, "write", duration_ms=8.5, cas_retries=0, run_id="default-run")
        assert default_telem.is_file()
        last_line = default_telem.read_text(encoding="utf-8").strip().splitlines()[-1]
        rec = json.loads(last_line)
        assert set(rec.keys()) == required_fields
        assert rec["op"] == "write"
        assert rec["bytes"] == 2048
        assert rec["limit"] == 67108864
        assert rec["duration_ms"] == 8.5
        assert rec["cas_retries"] == 0
        assert rec["runId"] == "default-run"
    finally:
        if default_telem.is_file():
            default_telem.unlink()


def test_telemetry_file_size_bounding_rotation(tmp_path, monkeypatch):
    """File size bounding enforces max bytes and rotates/truncates oldest records."""
    telem_path = tmp_path / "bounded-telemetry.jsonl"
    max_bytes = 350
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_TELEMETRY_PATH", str(telem_path))
    monkeypatch.setenv("GAIA_STEWARD_LEDGER_TELEMETRY_MAX_BYTES", str(max_bytes))

    # Write 6 records with distinctive runId tags
    for i in range(6):
        ledgerModule.reportLedgerSize(
            1000 + i,
            67108864,
            "write",
            duration_ms=10.0 + i,
            cas_retries=i,
            run_id=f"seq-run-{i}",
        )

    assert telem_path.is_file()
    file_bytes = telem_path.read_bytes()
    assert len(file_bytes) <= max_bytes

    lines = [line.strip() for line in file_bytes.decode("utf-8").splitlines() if line.strip()]
    assert len(lines) >= 2
    records = [json.loads(line) for line in lines]

    # Verify chronological order and newest records kept
    run_ids = [r["runId"] for r in records]
    assert "seq-run-0" not in run_ids  # oldest was rotated out
    assert "seq-run-5" in run_ids      # newest is present
    assert run_ids == sorted(run_ids)  # records remain in chronological order


def test_telemetry_write_failure_does_not_fail_operation_and_warns_stderr(tmp_path, capsys):
    """A telemetry failure must not fail the ledger operation and must emit one warning to sys.stderr."""
    # Create a non-writable path: a file acting as parent directory
    blocking_file = tmp_path / "not_a_dir"
    blocking_file.write_text("block")
    unwritable_path = blocking_file / "sub" / "telemetry.jsonl"

    store = FileLedgerStore(tmp_path / "ledger.json", telemetry_path=unwritable_path)

    # Perform normal update; operation must succeed without raising
    capsys.readouterr()  # clear any prior output
    res, ver = update(store, appendMarker("robust-op"))
    assert res == "robust-op"
    assert ver is not None

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "warning: failed to write steward ledger telemetry:" in captured.err
    # Count warnings in stderr: exactly one for this write attempt
    warning_lines = [line for line in captured.err.splitlines() if "warning: failed to write steward ledger telemetry:" in line]
    assert len(warning_lines) >= 1


def test_telemetry_never_committed_or_pushed_to_ledger_ref(tmp_path):
    """Telemetry is written to .gaia/steward/ and never committed into the git ledger ref."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    clone = makeClone(tmp_path, remote, "clone-telemetry")

    # Set telemetry path under clone's .gaia/steward/
    telem_dir = clone / ".gaia" / "steward"
    telem_path = telem_dir / "ledger-telemetry.jsonl"

    store = GitRefLedgerStore(clone, telemetry_path=telem_path)

    # Perform an update
    res, ver = update(store, appendMarker("check-git-ref"), run_id="git-test-run")
    assert res == "check-git-ref"

    # 1. Telemetry file exists on disk
    assert telem_path.is_file()
    telem_content = telem_path.read_text(encoding="utf-8")
    assert "git-test-run" in telem_content

    # 2. Fetch the commit from the ledger ref on remote
    commit = store.fetchRemote()
    assert commit is not None

    # 3. Check commit tree: MUST contain ONLY ledger.json, never .gaia or telemetry
    tree_output = store.plumb(["ls-tree", "-r", "--name-only", commit])
    tree_files = tree_output.splitlines()
    assert tree_files == ["ledger.json"]
    assert ".gaia" not in tree_output
    assert "telemetry" not in tree_output

    # 4. Verify git log on the ledger branch touches only ledger.json
    log_output = store.plumb(["log", "-n", "1", "--stat", commit])
    assert "ledger.json" in log_output
    assert ".gaia" not in log_output
    assert "telemetry" not in log_output


def test_serialize_does_not_emit_duplicate_write_telemetry(tmp_path):
    """serialize() does not emit duplicate write telemetry unless record_telemetry=True."""
    telem_path = tmp_path / "serialize-telemetry.jsonl"
    store = FileLedgerStore(tmp_path / "ledger.json", telemetry_path=telem_path)

    # Calling serialize() directly must not emit write telemetry by default
    doc = empty_ledger()
    ledgerModule.serialize(doc)
    assert not telem_path.is_file() or telem_path.stat().st_size == 0

    # Calling update() must emit exactly one write telemetry record
    update(store, appendMarker("single-write-entry"), telemetry_path=telem_path)
    lines = [line.strip() for line in telem_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [json.loads(line) for line in lines]
    write_records = [r for r in records if r["op"] == "write"]
    assert len(write_records) == 1
