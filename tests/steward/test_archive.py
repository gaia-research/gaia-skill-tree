"""Durable memory tests use only synthetic data and temporary bare remotes."""
from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest

from gaia_cli.steward import archive as a
from gaia_cli.steward.ledger import (
    GitRefLedgerStore, FileLedgerStore, LedgerConflict, LedgerUnavailable,
    empty_ledger, update, validate_ledger,
)

IDENTITY = {"GIT_AUTHOR_NAME": "Synthetic", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic", "GIT_COMMITTER_EMAIL": "test@example.invalid"}
START = "2026-01-01T00:00:00Z"
END = "2026-01-02T00:00:00Z"


def git(root, *args, data=None):
    p = subprocess.run(["git", "-C", str(root), *args], input=data, capture_output=True,
                       env={**os.environ, **IDENTITY})
    assert p.returncode == 0, p.stderr.decode()
    return p.stdout.decode().strip()


from copy import deepcopy
import functools
from pathlib import Path


@functools.lru_cache(maxsize=16)
def _cached_observation_phases(sensorCount, coverageUnknown, identityParts):
    from gaia_cli.steward.controller import ScanResult
    from gaia_cli.steward.fullrun import FullRunConfig, FullRunner
    from gaia_cli.steward.models import Observation, Receipt, Subject

    observations = tuple(Observation(
        kind="synthetic", subject=Subject(type="synthetic", id=f"subject-{number}"),
        observed_at=START, source=(f"sensor-{number:06d}" + "".join(
            f"-component-{part:02d}-{number:06d}" for part in range(identityParts))),
        status="healthy",
        current_state={}, observed_state={},
    ) for number in range(sensorCount))
    receipt = Receipt(
        run_id="scan-original", started_at=START, finished_at=END,
        observations_collected=len(observations), coverage_unknown=coverageUnknown,
        debt_created=(), debt_updated=(), debt_resolved=(), open_debt=(),
        authority_counts={"A": 0, "B": 0, "C": 0}, result_status="no_change",
    )
    scan = ScanResult(observations=observations, debts=(), receipt=receipt,
                      debt_state_path=Path("unused-debts"), receipt_path=Path("unused-receipt"),
                      fresh_open_debt_ids=frozenset())
    runner = FullRunner(FullRunConfig(repo_root=Path("."), store=FileLedgerStore(Path("unused-ledger"))))
    return {"observe": runner._observationSummary(scan)}


def observation_phases(sensorCount=16, coverageUnknown=(), identityParts=0):
    """Actual canonical producer output, not an invented padding/text field.

    Synthetic distinct sensor observations exercise the existing unbounded
    sensor-count map. Only typed identities and numeric counts enter phases;
    no observation subjects, artifact references or prose are copied by the
    producer. The large variant tests scale, not today's production fleet size.
    Identity components are synthetic sensor namespaces, within the existing
    source/ID contract, not a new field or serialized reference/prose format.
    """
    return deepcopy(_cached_observation_phases(sensorCount, tuple(coverageUnknown), identityParts))


def run_record(name="run-a", **extra):
    return {"runId": name, "status": "completed", "mode": "full", "phase": "done",
            "startedAt": START, "finishedAt": END, "trigger": "scheduled",
            "steps": [{"stepId": "phase:observe", "status": "done", "idempotencyKey": "once-only"}],
            "actions": [{"stepId": "forge:one", "status": "done", "type": "forge.open_pr",
                         "idempotencyKey": "do-not-repeat", "outcome": {"url": "synthetic://proof"}}],
            "desk": {"decisions": [{"decisionId": "class-c-reference", "debtIds": ["debt-c"]}]},
            "decisions": [], "unresolvedWork": [], "nextAction": "complete",
            "phases": {**observation_phases(), "retro": {"routines": [1, 18]},
                       "triage": {"classC": []}},
            # The desk stays hot; its debt reference still requires explicit
            # CURRENT settlement (supplied by seed for this synthetic fixture).
            "proofArtifacts": ["synthetic://original"], "receipts": [{"id": "scan-original"}],
            **extra}


@pytest.fixture
def hosts(tmp_path):
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare", "--quiet")
    stores = []
    for name in ("one", "two"):
        root = tmp_path / name
        root.mkdir()
        git(root, "init", "--quiet")
        git(root, "remote", "add", "origin", str(remote))
        stores.append(GitRefLedgerStore(root))
    return remote, *stores


def seed(store, runs=None):
    def mutate(doc):
        doc["runs"] = runs or {"run-a": run_record()}
        # A resolved work record is still retained verbatim. Every non-terminal
        # state lives on an unrelated run and must not be touched by migration.
        for state in ("resolved", "queued", "building", "proposed", "verified", "blocked", "escalated", "no_change", "landed"):
            doc["work"][state] = {"debtId": state, "state": state, "runId": "other",
                                   "history": [{"reason": "original", "at": START}]}
        # Explicit synthetic settlement for the default desk reference. The
        # original absent-work shape remains a separate negative regression.
        doc["work"]["debt-c"] = {"debtId": "debt-c", "authority": "C", "state": "resolved",
                                  "runId": "other", "history": [{"from": "escalated", "to": "resolved", "at": END, "reason": "synthetic settlement"}]}
        doc["operations"]["existing-dedup-key"] = {"status": "pending", "nonce": "preserve"}
    update(store, mutate)
    return store.load()


def refs(remote):
    return git(remote, "for-each-ref", "--format=%(refname) %(objectname)")


def raw_source(store, version):
    return store.git(["cat-file", "-p", f"{version}:ledger.json"], timeout=30).stdout


def test_roundtrip_cross_machine_exact_snapshot_and_hot_protection(hosts):
    remote, one, two = hosts
    before, version = seed(one)
    raw = raw_source(one, version)
    result = a.migrate(one)
    assert result["archived"] == ["run-a"]
    assert result["afterBytes"] < result["beforeBytes"]
    after, _ = two.load()
    assert a.POINTER in after["runs"]["run-a"]
    assert after["runs"]["run-a"]["phases"] == {}
    assert validate_ledger(after) is after  # additive, existing schema contract
    for key in ("work", "leases", "lane"):
        assert after[key] == before[key]
    assert after["operations"]["existing-dedup-key"] == before["operations"]["existing-dedup-key"]
    for key in before["runs"]["run-a"]:
        if key != "phases":
            assert after["runs"]["run-a"][key] == before["runs"]["run-a"][key]
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]
    assert a.snapshot(two, "run-a") == raw  # every original source byte, not reserialization
    assert "debt-c" in after["runs"]["run-a"][a.POINTER]["references"]["debtIds"]
    assert a.history(two, debt_id="debt-c", routine="18")["entries"][0]["runId"] == "run-a"
    # The snapshot keeps the source commit reachable on the shared transport.
    store = a.GitArchive(two).store(result["source"])
    tip = store.fetchRemote()
    assert git(remote, "merge-base", "--is-ancestor", version, tip) == ""


@pytest.mark.parametrize("stage", ["snapshot-published", "segments-verified", "index-verified", "before-cas"])
def test_interruption_leaves_hot_source_untouched_and_retry_succeeds(hosts, stage):
    remote, one, two = hosts
    before, version = seed(one)
    def crash(at):
        if at == stage:
            raise RuntimeError("synthetic interruption")
    with pytest.raises(RuntimeError, match="interruption"):
        a.migrate(one, checkpoint=crash)
    assert two.load() == (before, version)
    assert "steward/archive/v1/snapshot/" in refs(remote)
    assert a.migrate(two)["archived"] == ["run-a"]
    assert a.show(one, "run-a")["run"] == before["runs"]["run-a"]


def test_interruption_after_cas_and_duplicate_retry_are_idempotent(hosts):
    remote, one, two = hosts
    before, _ = seed(one)
    def crash(stage):
        if stage == "after-cas":
            raise RuntimeError("lost success response")
    with pytest.raises(RuntimeError):
        a.migrate(one, checkpoint=crash)
    state, version = two.load()
    branches = refs(remote)
    assert a.migrate(two, run_ids=["run-a"])["archived"] == []
    assert two.load() == (state, version)
    assert refs(remote) == branches
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]


def test_stale_cas_recomputes_eligibility_and_keeps_new_work(hosts):
    remote, one, two = hosts
    before, _ = seed(one)
    raced = False
    def race(stage):
        nonlocal raced
        if stage == "before-cas" and not raced:
            raced = True
            def mutate(doc):
                doc["runs"]["run-a"]["status"] = "blocked"
                doc["runs"]["run-a"]["actions"].append({"status": "pending", "stepId": "new"})
                doc["work"]["new"] = {"debtId": "new", "state": "escalated", "history": []}
            update(two, mutate)
    assert a.migrate(one, checkpoint=race)["archived"] == []
    live, _ = two.load()
    assert live["runs"]["run-a"]["phases"] == before["runs"]["run-a"]["phases"]
    assert a.POINTER not in live["runs"]["run-a"]
    assert live["work"]["new"]["state"] == "escalated"
    assert len(a.history(one)["entries"]) == 0  # orphan index isn't canonical history


def test_stale_cas_preserves_unrelated_concurrent_edits_and_retries(hosts):
    _, one, two = hosts
    seed(one)
    raced = False
    def race(stage):
        nonlocal raced
        if stage == "before-cas" and not raced:
            raced = True
            update(two, lambda doc: doc["operations"].update({"concurrent": {"key": "keep"}}))
    assert a.migrate(one, checkpoint=race)["archived"] == ["run-a"]
    live, _ = two.load()
    assert live["operations"]["concurrent"] == {"key": "keep"}
    assert len(a.history(two)["entries"]) == 1


def test_exhausted_cas_never_replaces_canonical_source(hosts, monkeypatch):
    _, one, two = hosts
    before = seed(one)
    def refuse(*args):
        raise LedgerConflict("synthetic race")
    monkeypatch.setattr(one, "compare_and_swap", refuse)
    with pytest.raises(LedgerConflict):
        a.migrate(one, retries=1)
    assert two.load() == before


@pytest.mark.parametrize("status", ["active", "awaiting-action", "blocked", "escalated", "queued", "unknown"])
def test_nonterminal_or_blocked_runs_never_eligible(hosts, status):
    remote, one, _ = hosts
    original = seed(one, {"run-a": run_record(status=status)})
    assert a.migrate(one)["archived"] == []
    assert one.load() == original
    assert "archive/" not in refs(remote)


@pytest.mark.parametrize("protection", ["lease", "pending-action", "unknown-action", "awaiting-step", "decision", "unresolved", "work"])
def test_protected_lifecycles_never_archived(hosts, protection):
    remote, one, _ = hosts
    seed(one)
    def protect(doc):
        r = doc["runs"]["run-a"]
        if protection == "lease":
            doc["leases"]["run"] = {"holder": "run-a", "acquiredAt": START, "expiresAt": END}
        elif protection in {"pending-action", "unknown-action"}:
            r["actions"][0]["status"] = "pending" if protection == "pending-action" else "future-status"
        elif protection == "awaiting-step":
            r["steps"][0]["status"] = "awaiting"
        elif protection == "decision":
            r["decisions"] = [{"decisionId": "c", "status": "pending"}]
        elif protection == "unresolved":
            r["unresolvedWork"] = [{"debtId": "blocked"}]
        else:
            doc["work"]["blocked"]["runId"] = "run-a"
    update(one, protect)
    original = one.load()
    assert a.migrate(one)["archived"] == []
    assert one.load() == original
    assert "archive/" not in refs(remote)


def test_rollback_retains_evidence_and_does_not_reset_other_state(hosts):
    remote, one, two = hosts
    before, _ = seed(one)
    a.migrate(one)
    old_refs = set(refs(remote).splitlines())
    update(two, lambda doc: doc["operations"].update({"later": {"preserve": True}}))
    assert a.rollback(two, "run-a")["restored"] == ["run-a"]
    after, version = one.load()
    assert after["runs"] == before["runs"]
    assert after["work"] == before["work"]
    assert after["operations"]["later"] == {"preserve": True}
    assert old_refs - {line for line in old_refs if "refs/heads/steward/ledger " in line} <= set(refs(remote).splitlines())
    assert [row["event"] for row in a.history(one, pages=2)["entries"]] == ["rollback", "archive"]
    assert a.rollback(two, "run-a")["restored"] == []
    assert one.load()[1] == version


def test_rollback_and_rearchive_keep_history_chain(hosts):
    _, one, two = hosts
    before, _ = seed(one)
    a.migrate(one)
    a.rollback(two, "run-a")
    a.migrate(one)
    assert a.show(two, "run-a")["run"] == before["runs"]["run-a"]
    assert [row["event"] for row in a.history(two, pages=3)["entries"]] == ["archive", "rollback", "archive"]


@pytest.mark.parametrize("kind", ["run", "snapshot", "index", "anchor"])
@pytest.mark.parametrize("damage", ["missing", "corrupt", "oversize"])
def test_missing_corrupt_archives_fail_closed(hosts, kind, damage):
    remote, one, two = hosts
    seed(one)
    migration = a.migrate(one)
    hot, version = one.load()
    pointer = hot["runs"]["run-a"][a.POINTER]
    ref = {"run": pointer["segment"], "snapshot": migration["source"], "index": migration["index"],
           "anchor": migration["sourceAnchor"]}[kind]
    branch = f"refs/heads/{a.PREFIX}/{kind}/{ref['sha256']}"
    if damage == "missing":
        git(remote, "update-ref", "-d", branch)
    else:
        # Operator corruption is simulated directly in the disposable bare repo;
        # production archive code never updates/deletes/forces an existing ref.
        data = b"x" * (a.LIMITS[kind] + 1) if damage == "oversize" else b"{}\n"
        blob = git(remote, "hash-object", "-w", "--stdin", data=data)
        tree = git(remote, "mktree", data=f"100644 blob {blob}\tpayload\n".encode())
        commit = git(remote, "commit-tree", tree, "-m", "synthetic corruption")
        git(remote, "update-ref", branch, commit)
    if kind == "index":
        operations = [lambda: a.history(two), lambda: a.migrate(two), lambda: a.rollback(two, "run-a")]
    else:
        operations = [lambda: a.show(two, "run-a"), lambda: a.snapshot(two, "run-a"),
                      lambda: a.migrate(two, run_ids=["run-a"]), lambda: a.rollback(two, "run-a"),
                      lambda: a.history(two)]
    for operation in operations:
        with pytest.raises(LedgerUnavailable):
            operation()
        assert one.load() == (hot, version)


def test_corruption_during_publish_cannot_commit_hot_pointer(hosts, monkeypatch):
    _, one, two = hosts
    before = seed(one)
    real = a.GitArchive.read
    def corrupt(self, ref):
        if ref["kind"] == "run":
            raise LedgerUnavailable("synthetic checksum mismatch")
        return real(self, ref)
    monkeypatch.setattr(a.GitArchive, "read", corrupt)
    with pytest.raises(LedgerUnavailable):
        a.migrate(one)
    assert two.load() == before


def test_mutated_hot_stub_refuses_hydration_and_rollback(hosts):
    remote, one, two = hosts
    seed(one)
    a.migrate(one)
    with pytest.raises(LedgerUnavailable, match="immutable"):
        update(two, lambda doc: doc["runs"]["run-a"].update({"status": "active"}))
    # Simulate out-of-band operator corruption only in the disposable remote;
    # ordinary writes now refuse this mutation at the CAS boundary.
    damaged, version = one.load()
    damaged["runs"]["run-a"]["status"] = "active"
    blob = git(remote, "hash-object", "-w", "--stdin", data=a.packed(damaged))
    tree = git(remote, "mktree", data=f"100644 blob {blob}\tledger.json\n".encode())
    commit = git(remote, "commit-tree", tree, "-p", version, "-m", "synthetic hot corruption")
    git(remote, "update-ref", "refs/heads/steward/ledger", commit)
    before = one.load()
    with pytest.raises(LedgerUnavailable, match="identity"):
        a.show(two, "run-a")
    with pytest.raises(LedgerUnavailable):
        a.rollback(two, "run-a")
    assert one.load() == before


def test_paged_search_cursor_filters_and_no_model_or_forge_activity(hosts):
    _, one, two = hosts
    runs = {f"r-{n}": run_record(f"r-{n}") for n in range(3)}
    seed(one, runs)
    for n in range(3):
        assert a.migrate(one, run_ids=[f"r-{n}"])["archived"] == [f"r-{n}"]
    first = a.history(two)
    assert [r["runId"] for r in first["entries"]] == ["r-2"]
    second = a.history(one, cursor=first["nextCursor"])
    assert [r["runId"] for r in second["entries"]] == ["r-1"]
    assert len(a.history(two, pages=3, routine="1", debt_id="debt-c", since=START, until=END)["entries"]) == 3
    assert a.history(two, run_id="not-present")["nextCursor"] is not None
    assert a.history(two, pages=3, since="2027-01-01T00:00:00Z")["entries"] == []
    assert a.history(two, pages=3, until="2025-01-01T00:00:00Z")["entries"] == []
    for options in ({"pages": 11}, {"pages": 0}, {"since": END, "until": START}, {"since": "bad"}):
        with pytest.raises(ValueError):
            a.history(two, **options)


def test_content_addressed_publication_duplicate_and_safe_git_surface(hosts):
    remote, one, two = hosts
    before, _ = seed(one)
    a.migrate(one)
    hot, _ = two.load()
    segment = hot["runs"]["run-a"][a.POINTER]["segment"]
    store = a.GitArchive(two)
    data = store.read(segment)
    initial = refs(remote)
    assert store.publish("run", data) == segment
    assert refs(remote) == initial
    assert a.show(one, "run-a")["run"] == before["runs"]["run-a"]
    assert git(one.repo_root, "status", "--porcelain") == ""
    assert git(one.repo_root, "config", "--local", "--get-regexp", "remote.*.url") == f"remote.origin.url {remote}"


def test_preview_is_read_only_unknown_ids_and_bounded_objects(hosts):
    remote, one, _ = hosts
    seed(one)
    before = refs(remote)
    preview = a.plan(one)
    assert preview["eligible"] == ["run-a"] and preview["applyRequired"]
    assert refs(remote) == before
    with pytest.raises(LedgerUnavailable):
        a.plan(one, run_ids=["missing"])
    with pytest.raises(ValueError):
        a.migrate(one, max_runs=33)
    with pytest.raises(LedgerUnavailable):
        a.GitArchive(one).publish("run", b"x" * (a.MAX_SEGMENT_BYTES + 1))
    for ref in ({}, {"kind": "evil", "sha256": "0" * 64, "size": 1},
                {"kind": "run", "sha256": "../main", "size": 1},
                {"kind": "run", "sha256": "0" * 64, "size": True}):
        with pytest.raises(LedgerUnavailable):
            a.GitArchive(one).read(ref)
    assert refs(remote) == before


def test_local_transport_is_not_a_durable_archive(tmp_path):
    with pytest.raises(LedgerUnavailable, match="shared Git"):
        a.migrate(FileLedgerStore(tmp_path / "ledger.json"))


def test_schema_identity_and_index_validation(hosts):
    _, one, _ = hosts
    with pytest.raises(LedgerUnavailable):
        a.GitArchive(one).publish("run", a.packed({"schemaVersion": "future", "kind": "run"}))
    with pytest.raises(LedgerUnavailable):
        a.GitArchive(one).publish("index", a.packed({"schemaVersion": a.SCHEMA, "kind": "index", "entries": []}))
    with pytest.raises(LedgerUnavailable):
        a.GitArchive(one).publish("snapshot", b"{\"schemaVersion\":\"bad\"}")


def test_empty_ledger_and_small_runs_not_pruned(hosts):
    remote, one, _ = hosts
    assert a.migrate(one)["archived"] == []
    assert refs(remote) == ""
    seed(one, {"run-a": run_record(phases={"observe": {"observations": 1}})})
    before = one.load()
    result = a.migrate(one)
    assert result["archived"] == [] and result["reason"] == "no hot size saving"
    assert one.load() == before


def test_rollback_capacity_failure_keeps_archived_evidence(hosts, monkeypatch):
    _, one, two = hosts
    seed(one)
    a.migrate(one)
    before = two.load()
    def refuse(doc):
        raise LedgerUnavailable("synthetic configured bound")
    monkeypatch.setattr(a, "serialize", refuse)
    with pytest.raises(LedgerUnavailable):
        a.rollback(two, "run-a")
    assert one.load() == before
    assert a.show(one, "run-a")["run"]["status"] == "completed"
