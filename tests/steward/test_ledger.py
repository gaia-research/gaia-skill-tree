"""Steward Full S6 - the durable, concurrency-safe shared ledger.

Git-transport tests use real git against local bare repositories created in
tmp_path; two independent clones play the part of two machines. Nothing here
touches a real remote or the real `steward/ledger` ref.
"""

from __future__ import annotations

import copy
import json
import os
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
