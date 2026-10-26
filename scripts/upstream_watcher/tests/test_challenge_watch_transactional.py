"""Offline durability proofs using actual concurrent processes and local git remotes.

No receipt issuer, model, ecosystem crawl, or live GitHub call is involved.
TEST-only admission is imported explicitly; production has no such authority.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gaia_cli.steward.ledger import FileLedgerStore, GitRefLedgerStore, LedgerConflict, update
from scripts.upstream_watcher.challenge_watch import WatchBudget, WatchLedger, _hash, run_challenge_watch
from scripts.upstream_watcher.transport import SimulatedTransport, VirtualClock
from scripts.upstream_watcher.tests.test_challenge_watch import (
    _ExplicitTestResolver, _make_verified_challenge_dict,
)

OP = "upstreamWatcherChallengeWatch"
IDENTITY = {
    "GIT_AUTHOR_NAME": "Watcher Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Watcher Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
}


def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], env={**os.environ, **IDENTITY},
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def make_remote(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    return remote


def clone(remote, path):
    subprocess.run(["git", "clone", "--quiet", str(remote), str(path)],
                   capture_output=True, check=True)
    (path / "base.txt").write_text("fixture\n")
    git(path, "add", "base.txt")
    git(path, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture")
    # Sentinel refs must not be pruned to make namespace isolation pass.
    git(path, "update-ref", "refs/remotes/origin/sentinel", "HEAD")
    return path


def fixture_transport(tag="v2", probe=200):
    transport = SimulatedTransport()
    transport.register_probe("https://github.com/pbakaus/impeccable", status_code=probe)
    transport.register_release("pbakaus", "impeccable", tag=tag)
    transport.register_commit("pbakaus", "impeccable", sha=f"{tag}-sha")
    transport.register_content("pbakaus", "impeccable", "SKILL.md", content=f"{tag} content")
    transport.register_release("competitor", "rival", tag="rival-v1")
    transport.register_commit("competitor", "rival", sha="rival-sha")
    transport.register_content("competitor", "rival", "SKILL.md", content="rival content")
    return transport


def run_fixture(store, directory, *, raw=None, clock="2026-10-26T00:00:00Z", transport=None, budget=None):
    return run_challenge_watch(
        challenges=raw if raw is not None else [_make_verified_challenge_dict()],
        admission_resolver=_ExplicitTestResolver(), shared_store=store,
        ledger_path=directory / "ignored-local-ledger.json", packets_dir=directory / "packets",
        transport=transport or fixture_transport(), clock=VirtualClock(clock), budget=budget,
    )


def wait_for(path):
    deadline = time.monotonic() + 15
    while not path.exists():
        if time.monotonic() > deadline:
            raise AssertionError(f"barrier timed out: {path.name}")
        time.sleep(0.005)


def worker(spec_path):
    """Ordinary Python worker, never an agent; two independently cloned stores."""
    spec = json.loads(Path(spec_path).read_text())
    directory = Path(spec["clone"])
    barrier = Path(spec["barrier"])
    name = spec["name"]
    log = {"pid": os.getpid(), "attempts": [], "conflicts": 0}

    class BarrierStore(GitRefLedgerStore):
        def compare_and_swap(self, expected, document, message):
            log["attempts"].append(expected)
            if len(log["attempts"]) == 1 and spec.get("concurrent"):
                (barrier / f"{name}-ready").write_text(str(expected))
                wait_for(barrier / f"{'b' if name == 'a' else 'a'}-ready")
                if name == "b":
                    wait_for(barrier / "a-committed")
            try:
                result = super().compare_and_swap(expected, document, message)
            except LedgerConflict:
                log["conflicts"] += 1
                raise
            if name == "a" and spec.get("concurrent"):
                (barrier / "a-committed").write_text(result)
            return result

    if spec.get("crash"):
        # Deliberately die AFTER successful shared save, BEFORE any local packet.
        WatchLedger.materialize = lambda self, directory: os._exit(73)
    transport = fixture_transport(spec.get("tag", "v2"))
    result = run_fixture(
        BarrierStore(directory), directory, raw=spec["raw"], clock=spec["clock"],
        transport=transport, budget=WatchBudget(max_requests=spec.get("requests", 7), max_subjects=1),
    )
    log.update({"newIds": [p.packet_id for p in result.packets],
                "requests": len(transport.recorded_requests)})
    (barrier / f"{name}-result.json").write_text(json.dumps(log))


def launch(spec, tmp_path):
    path = tmp_path / f"spec-{spec['name']}.json"
    path.write_text(json.dumps(spec))
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "worker", str(path)],
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def collect(process, expected=0):
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        pytest.fail(f"worker timed out: {stdout}\n{stderr}")
    assert process.returncode == expected, f"{stdout}\n{stderr}"


def concurrent_pair(tmp_path, *, identical=False):
    remote = make_remote(tmp_path)
    a = clone(remote, tmp_path / "a")
    b = clone(remote, tmp_path / "b")
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    # Preserve operations not owned by this watcher across both CAS retries.
    update(GitRefLedgerStore(a), lambda doc: doc["operations"].update({"sentinel": {"keep": 17}}))
    challenge = _make_verified_challenge_dict()
    other = _make_verified_challenge_dict(subject_id="z-other/skill", target_repo="z-other/skill")
    before_refs = {str(path): git(path, "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes")
                   for path in (a, b)}
    procs = []
    try:
        for name, path in (("a", a), ("b", b)):
            procs.append(launch({
                "clone": str(path), "barrier": str(barrier), "name": name, "concurrent": True,
                "raw": [challenge] if name == "a" else [challenge, other],
                "clock": "2026-10-26T02:00:00Z" if name == "a" else "2026-10-26T01:00:00Z",
                "tag": "v3" if name == "a" or identical else "v2",
                "requests": 7 if identical or name == "b" else 2,
            }, tmp_path))
        for process in procs:
            collect(process)
    finally:
        for process in procs:
            if process.poll() is None:
                process.kill()
                process.communicate()
    logs = [json.loads((barrier / f"{name}-result.json").read_text()) for name in ("a", "b")]
    assert logs[0]["pid"] != logs[1]["pid"]
    assert logs[0]["attempts"][0] == logs[1]["attempts"][0]
    assert logs[1]["conflicts"] >= 1
    assert len(logs[1]["attempts"]) >= 2
    for path in (a, b):
        assert git(path, "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes") == before_refs[str(path)]
    fresh = clone(remote, tmp_path / "fresh")
    document, _ = GitRefLedgerStore(fresh).load()
    assert document["operations"]["sentinel"] == {"keep": 17}
    state = WatchLedger(fresh / "no-cache", shared_store=GitRefLedgerStore(fresh))
    assert len(state.inputs) == 2  # B's unevaluated input survives subject budget.
    assert len(state.observations) == 2
    return state, logs, challenge


def test_two_process_two_clone_stale_partial_cas_union(tmp_path):
    state, logs, challenge = concurrent_pair(tmp_path)
    assert [log["requests"] for log in logs] == [2, 7]  # HTTP was NOT replayed on conflict.
    entry = state.challenges[challenge["challenge_id"]]
    assert entry["target"]["last_version"] == "v3"  # Older loser cannot regress winner.
    assert entry["target"]["last_sha"] == "v2-sha"  # Older full observation still contributes.
    assert entry["last_observation"]["target"]["checks"]["commit"] == "not_run_budget"
    assert len(state.packets) == 2
    assert set(logs[0]["newIds"]) <= set(state.packets)
    for packet in state.packets.values():
        assert packet["canonicalMutation"] is None
        assert packet["contextDigest"] == state.contexts[challenge["challenge_id"]]


def test_two_process_two_clone_identical_event_has_one_reserved_intent(tmp_path):
    state, logs, _ = concurrent_pair(tmp_path, identical=True)
    assert len(state.packets) == 1
    assert sum(len(log["newIds"]) for log in logs) == 1
    assert [log["requests"] for log in logs] == [7, 7]


def test_process_crash_after_shared_save_restores_without_original_files(tmp_path):
    remote = make_remote(tmp_path)
    original = clone(remote, tmp_path / "original")
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    process = launch({"clone": str(original), "barrier": str(barrier), "name": "crash",
                      "raw": [_make_verified_challenge_dict()], "clock": "2026-10-26T00:00:00Z",
                      "crash": True}, tmp_path)
    collect(process, expected=73)
    assert not (original / "packets").exists()
    fresh = clone(remote, tmp_path / "fresh")
    # Deliberately corrupt local cache: shared mode must ignore it, never seed it.
    (fresh / "ignored-local-ledger.json").write_text('{"forged": true}')
    transport = SimulatedTransport()
    result = run_challenge_watch(
        challenges=[], shared_store=GitRefLedgerStore(fresh),
        ledger_path=fresh / "ignored-local-ledger.json", packets_dir=fresh / "packets",
        transport=transport, clock=VirtualClock(),  # Default resolver remains unavailable.
    )
    assert result.packets == []
    assert result.unavailable_count == 1
    assert transport.recorded_requests == []
    state = WatchLedger(fresh / "unused", shared_store=GitRefLedgerStore(fresh))
    files = list((fresh / "packets").glob("*.json"))
    assert len(files) == len(state.packets) == 1
    assert json.loads(files[0].read_text()) == next(iter(state.packets.values()))


def reseal(state):
    state["stateSha256"] = _hash({k: v for k, v in state.items() if k != "stateSha256"})


@pytest.mark.parametrize("attack", ["packet-hash", "packet-rehashed", "packet-ref", "packet-id",
                                     "state-projection", "event", "input", "drop-packet"])
def test_shared_tamper_rejected_even_with_resealed_outer_digest(tmp_path, attack):
    store = FileLedgerStore(tmp_path / "operations.json")
    run_fixture(store, tmp_path)

    def corrupt(doc):
        state = doc["operations"][OP]
        packet_id = next(iter(state["packets"]))
        packet = state["packets"][packet_id]
        if attack in {"packet-hash", "packet-rehashed"}:
            packet["targetObservation"]["release"]["latest"] = "forged-version"
            if attack == "packet-rehashed":
                packet["packetSha256"] = _hash({k: v for k, v in packet.items() if k != "packetSha256"})
        elif attack == "packet-ref":
            packet["observationRef"] = "f" * 64
            packet["packetSha256"] = _hash({k: v for k, v in packet.items() if k != "packetSha256"})
        elif attack == "packet-id":
            state["packets"]["f" * 64] = state["packets"].pop(packet_id)
        elif attack == "state-projection":
            next(iter(state["challenges"].values()))["target"]["last_version"] = "forged-version"
        elif attack == "event":
            next(iter(state["observations"].values()))["contextDigest"] = "f" * 64
        elif attack == "input":
            state["inputs"][0]["target_repo"] = "wrong/context"
        elif attack == "drop-packet":
            del state["packets"][packet_id]
        reseal(state)

    update(store, corrupt)
    with pytest.raises(ValueError):
        WatchLedger(tmp_path / "not-authority", shared_store=store)


def test_local_packet_tamper_is_not_silently_overwritten(tmp_path):
    store = FileLedgerStore(tmp_path / "operations.json")
    run_fixture(store, tmp_path)
    path = next((tmp_path / "packets").glob("*.json"))
    path.write_text('{"packetId": "forged"}')
    with pytest.raises(ValueError):
        run_fixture(store, tmp_path)


def test_filtered_manifest_and_zero_budget_cannot_drop_inputs_or_known_state(tmp_path):
    store = FileLedgerStore(tmp_path / "operations.json")
    raw = [_make_verified_challenge_dict(), _make_verified_challenge_dict(
        subject_id="second/skill", target_repo="second/skill")]
    run_fixture(store, tmp_path, raw=raw, budget=WatchBudget(max_requests=7, max_subjects=1))
    before = WatchLedger(tmp_path / "none", shared_store=store)
    run_fixture(store, tmp_path, raw=[raw[0]], budget=WatchBudget(max_requests=0),
                clock="2026-10-27T00:00:00Z")
    after = WatchLedger(tmp_path / "none", shared_store=store)
    assert after.inputs == before.inputs
    assert after.challenges == before.challenges
    assert after.observations == before.observations
    assert after.packets == before.packets
    conflict = deepcopy(raw[0])
    conflict["target_repo"] = "wrong/context"
    with pytest.raises(ValueError, match="immutable challenge input conflict"):
        run_fixture(store, tmp_path, raw=[conflict])


def test_outage_and_unknown_review_episode_dedupe_is_not_daily(tmp_path):
    outage_store = FileLedgerStore(tmp_path / "outage-operations.json")
    counts = []
    for hour in (0, 25, 73, 97, 121, 145):
        clock = VirtualClock("2026-10-26T00:00:00Z")
        clock.advance_hours(hour)
        result = run_fixture(outage_store, tmp_path / "outage", clock=clock.now_utc(),
                             transport=fixture_transport(probe=404))
        counts.append(len(result.packets))
    assert counts == [1, 1, 1, 0, 0, 0]
    run_fixture(outage_store, tmp_path / "outage", clock="2026-11-02T00:00:00Z")
    result = run_fixture(outage_store, tmp_path / "outage", clock="2026-11-03T00:00:00Z",
                         transport=fixture_transport(probe=404))
    assert [p.trigger_type for p in result.packets] == ["availability_probe"]
    state = WatchLedger(tmp_path / "none", shared_store=outage_store)
    episodes = [p["intent"]["episode"] for p in state.packets.values() if p["triggerType"] == "availability_probe"]
    assert sorted(episodes) == [1, 1, 2]

    unknown_store = FileLedgerStore(tmp_path / "unknown-operations.json")
    transport = fixture_transport()
    transport.register_release("pbakaus", "impeccable", tag="unobserved", status_code=500)
    reviews = []
    for hour in (0, 73, 97, 121):
        clock = VirtualClock("2026-10-26T00:00:00Z")
        clock.advance_hours(hour)
        result = run_fixture(unknown_store, tmp_path / "unknown", clock=clock.now_utc(), transport=transport)
        reviews.extend(p for p in result.packets if p.trigger_type == "unknown_review_pending")
    assert len(reviews) == 1
    assert reviews[0].intent["window"] == "72h-review"
    # Virtual timestamps prove policy only, NOT four elapsed operational weeks.


if __name__ == "__main__":
    assert sys.argv[1] == "worker"
    worker(sys.argv[2])
