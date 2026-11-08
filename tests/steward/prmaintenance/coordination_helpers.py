"""Explicit administrative genesis fixtures; ONLY disposable local bare remotes."""

from __future__ import annotations

import atexit
import copy
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from gaia_cli.steward import ledger
from gaia_cli.steward.prmaintenance.coordination import (
    Binding, CoordinationError, KEY, Limits, Namespace, PrWriteCoordinator, REF, SCHEMA, TimeBounds, exactRequest,
)

NAMESPACE = Namespace("forge.invalid", "repository-immutable-42", "example/project", "a" * 32)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True, timeout=30)
    return result.stdout.strip()


def isolate(monkeypatch, root: Path) -> None:
    home = root / "home"
    home.mkdir()
    for key in list(os.environ):
        if key.startswith("GIT_") or key in {"SSH_AUTH_SOCK", "GH_TOKEN", "GITHUB_TOKEN"}:
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("GIT_ALLOW_PROTOCOL", "file")


def subject(number: int = 1, action: str = "merge") -> dict:
    return {"number": number, "prId": f"immutable-pr-{number}", "action": action,
            "headSha": "b" * 40, "baseRef": "main", "baseSha": "c" * 40,
            "producerId": "fixture-producer", "reason": "superseded by independently checked replacement" if action == "close" else "",
            "replacement": None}


def proof(candidate: dict | None = None) -> dict:
    candidate = candidate or subject()
    return {"policy": "fixture current policy: merge=2 close=2 hour=10", "producerRegistry": "fixture producer registry bytes",
            "authority": "fixture explicitly decided B authority (not approval inferred by coordinator)",
            "verification": {"builder": "builder", "verifier": "independent-verifier", "result": "PASS",
                             "headSha": candidate["headSha"], "baseSha": candidate["baseSha"],
                             "source": "fixture://durable-independent-verification", "detail": "inspected exact tree and current gate inputs"},
            "justification": "durable justification independent of comment publication"}


def evidence(operation: dict, kind: str, observedState: str) -> dict:
    return {"kind": kind, **{key: operation[key] for key in ("operationId", "attemptId", "requestDigest", "invocationId")},
            "headSha": operation["subject"]["headSha"], "source": "fixture://independently-checked-forge",
            "detail": "sole invocation completed; observation may truthfully record subsequent reopen",
            "observedState": observedState}


class FakeServices:
    """Authoritative test clock is entirely independent of process wall clocks."""

    def __init__(self, *, now: int = 10000, queue=None):
        self.now = TimeBounds(now, now, "fixture-authoritative-clock")
        self.caps = Limits()
        self.response = "effect"
        self.observed = None
        self.invocations = []
        self.effects = []
        self.authorized = True
        self.queue = queue

    def clock(self):
        return self.now

    def limits(self):
        return self.caps

    def authorize(self, namespace, candidate, binding):
        if not self.authorized or namespace != NAMESPACE or binding != proof(candidate):
            raise CoordinationError("fixture current authority/proof unavailable or stale")

    def invoke(self, request, invocationId):
        self.invocations.append((copy.deepcopy(request), invocationId))
        if self.queue is not None:
            self.queue.put(("invocation", invocationId))
        if self.response != "reject":
            self.effects.append(invocationId)
            if self.queue is not None:
                self.queue.put(("effect", invocationId))
        if self.response == "lost":
            raise OSError("fixture lost response after effect")
        return {"id": invocationId, "response": self.response}

    def completion(self, operation, invocationId, response):
        assert response["id"] == invocationId == operation["invocationId"]
        kind = "completed-no-effect" if response["response"] == "reject" else "completed-effect"
        state = "rejected" if kind == "completed-no-effect" else (
            "merged" if operation["subject"]["action"] == "merge" else "reopened" if response["response"] == "reopened" else "closed")
        return evidence(operation, kind, state)

    def observation(self, operation):
        if self.observed is None:
            return None
        return evidence(operation, self.observed[0], self.observed[1])


_GENESIS_CACHE: dict[Namespace, tuple[Path, str]] = {}


def _genesisRemote(namespace: Namespace) -> tuple[Path, str]:
    if namespace in _GENESIS_CACHE:
        return _GENESIS_CACHE[namespace]
    cache_dir = Path(tempfile.mkdtemp(prefix=f"gaia-genesis-bare-{os.getpid()}-"))
    template_remote = cache_dir / "remote.git"
    bootstrap = cache_dir / "administrative-fixture"
    subprocess.run(["git", "init", "--bare", "--quiet", str(template_remote)], check=True, timeout=30)
    subprocess.run(["git", "init", "--quiet", str(bootstrap)], check=True, timeout=30)
    git(bootstrap, "remote", "add", "origin", str(template_remote))
    store = ledger.GitRefLedgerStore(bootstrap, ref=REF)
    document = ledger.empty_ledger()
    document["operations"] = {KEY: {"schemaVersion": SCHEMA, "namespace": asdict(namespace), "events": []}}
    # Administrative fixture provisioning, never a production coordinator path.
    genesis = store.compare_and_swap(None, document, "disposable administrative genesis")
    git(template_remote, "symbolic-ref", "HEAD", f"refs/heads/{REF}")
    shutil.rmtree(bootstrap, ignore_errors=True)
    _GENESIS_CACHE[namespace] = (template_remote, genesis)
    return template_remote, genesis


def seed(root: Path, monkeypatch, namespace: Namespace = NAMESPACE):
    isolate(monkeypatch, root)
    template_remote, genesis = _genesisRemote(namespace)
    remote = root / "remote.git"
    if remote.exists():
        shutil.rmtree(remote)
    shutil.copytree(template_remote, remote, symlinks=True)
    binding = Binding(namespace, genesis, genesis, str(remote))
    first = clone(root, remote, "first")
    second = clone(root, remote, "second")
    assertIndependent(first, second)
    return remote, binding, first, second


def _cleanupGenesis() -> None:
    for template_remote, _ in _GENESIS_CACHE.values():
        shutil.rmtree(template_remote.parent, ignore_errors=True)


atexit.register(_cleanupGenesis)


def clone(root: Path, remote: Path, name: str) -> Path:
    path = root / name
    subprocess.run(["git", "clone", "--no-local", "--quiet", str(remote), str(path)],
                   check=True, capture_output=True, timeout=30)
    assert not (path / ".git/objects/info/alternates").exists()
    return path


def assertIndependent(first: Path, second: Path) -> None:
    firstObjects = (first / git(first, "rev-parse", "--git-path", "objects")).resolve()
    secondObjects = (second / git(second, "rev-parse", "--git-path", "objects")).resolve()
    assert firstObjects != secondObjects
    assert firstObjects.stat().st_ino != secondObjects.stat().st_ino
    assert (first / git(first, "rev-parse", "--git-common-dir")).resolve() != (second / git(second, "rev-parse", "--git-common-dir")).resolve()
    for left in firstObjects.rglob("*"):
        right = secondObjects / left.relative_to(firstObjects)
        if left.is_file() and right.is_file():
            assert left.stat().st_ino != right.stat().st_ino
    assert not (firstObjects / "info/alternates").exists()
    assert not (secondObjects / "info/alternates").exists()


def coordinator(path: Path, binding: Binding, services: FakeServices | None = None) -> PrWriteCoordinator:
    # Explicit historical resource-test profile, not the production default.
    from gaia_cli.steward.prmaintenance.coordination import ResourceProfile
    return PrWriteCoordinator(ledger.GitRefLedgerStore(path, ref=REF), binding, services or FakeServices(), ResourceProfile(512 * 1024))


def prepared(coord: PrWriteCoordinator, number: int = 1, action: str = "merge", run: str = "stable-run"):
    candidate = subject(number, action)
    token = coord.reserve(candidate, proof(candidate), run, f"owner-{number}", f"reserve-{number}").token
    coord.recordIntent(token, exactRequest(NAMESPACE, candidate), f"intent-{number}")
    return token
