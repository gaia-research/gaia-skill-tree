"""The durable, concurrency-safe shared Steward ledger (Steward Full, S6).

Manual and scheduled Steward runs on different machines must reconcile through
*one* piece of state, or they duplicate work and fight over the same debt.
`.gaia/steward/` cannot be that state: it is ignored, per-checkout, and by
design invisible to every other machine.

The ledger is one JSON document (`steward-ledger-v1`) holding runs, leases,
work items and the shared Class B lane. Two stores carry it:

- `GitRefLedgerStore` — a dedicated branch (`steward/ledger`) on a git remote
  containing a single `ledger.json`. Writes are compare-and-swap by
  **fast-forward push only**: the new commit's parent is the version that was
  read, so git itself rejects the write if anyone else advanced the ref first.
  There is no force push, no lease option and no lock service; the safety
  property is git's own refusal to move a ref to a non-descendant commit.
  Only plumbing (`hash-object`, `mktree`, `commit-tree`, `fetch`, `push`) is
  used, so the working tree, index and HEAD are never touched.
- `FileLedgerStore` — a local file under an exclusive `flock`. Tests and
  offline use only. It says `shared = False` so no caller can mistake it for
  cross-machine coordination.

`update()` is the only sanctioned write path: load, deep-copy, mutate, CAS, and
on a conflict re-load and re-apply the mutation to the fresh document. The pure
helpers below (`acquire_lease`, `transition_work`, ...) are meant to be called
inside `mutate`.

A ledger that cannot be read or validated is `LedgerUnavailable`. It is never
replaced with an empty one: a silently reset ledger would discard leases and
work history that other machines are relying on.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, TypeVar

try:  # POSIX only; the file store refuses to run without it.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None  # type: ignore[assignment]

from gaia_cli.steward.lane import LANE_SCHEMA


LEDGER_SCHEMA = "steward-ledger-v1"
LEDGER_FILENAME = "ledger.json"
DEFAULT_REF = "steward/ledger"
LOCAL_TRACKING_PREFIX = "refs/steward/remote-ledger"

# A ledger larger than this is refused on load and write. Nothing is pruned
# silently: hitting the bound is a signal that retention needs a decision.
MAX_LEDGER_BYTES = 1024 * 1024

WORK_STATES = (
    "queued",
    "building",
    "proposed",
    "verified",
    "no_change",
    "blocked",
    "escalated",
    "landed",
    "resolved",
)

TOP_LEVEL_KEYS = frozenset(
    {"schemaVersion", "generation", "updatedAt", "runs", "leases", "work", "lane", "operations"}
)

LOCAL_GIT_TIMEOUT = 30.0
REMOTE_GIT_TIMEOUT = 90.0

COMMIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Gaia Steward",
    "GIT_AUTHOR_EMAIL": "steward@gaiaskilltree.invalid",
    "GIT_COMMITTER_NAME": "Gaia Steward",
    "GIT_COMMITTER_EMAIL": "steward@gaiaskilltree.invalid",
}

# `git push --porcelain` status reasons that mean "someone else moved the ref".
# Only these are conflicts. A `[remote rejected]` status is ambiguous (a lost
# ref-lock race and a permanent hook/protection/D-F rejection look alike), so
# it is resolved by asking the remote where the ref now is; see
# `GitRefLedgerStore.classifyPushFailure`. Everything else is unavailability.
PUSH_CONFLICT_REASONS = (
    "[rejected] (non-fast-forward)",
    "[rejected] (fetch first)",
    "[rejected] (stale info)",
)
MAX_LEASE_TTL_SECONDS = 30 * 24 * 3600
REF_PREFIX = "steward/"
FETCH_LOCK_MARKERS = ("cannot lock ref", "unable to update local ref", ".lock")

T = TypeVar("T")


class LedgerConflict(RuntimeError):
    """The ledger moved since it was read; nothing was written."""


class LedgerUnavailable(RuntimeError):
    """The ledger cannot be read, validated or written; nothing was changed."""


class LedgerStore(Protocol):
    transport: str
    shared: bool

    def load(self) -> tuple[dict[str, Any], str | None]: ...

    def compare_and_swap(
        self, expected: str | None, document: dict[str, Any], message: str
    ) -> str: ...


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------


def empty_ledger() -> dict[str, Any]:
    return {
        "schemaVersion": LEDGER_SCHEMA,
        "generation": 0,
        "runs": {},
        "leases": {},
        "work": {},
        "lane": None,
        "operations": {},
    }


def malformed(reason: str) -> LedgerUnavailable:
    return LedgerUnavailable(f"malformed ledger: {reason}")


def isInt(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def parseTime(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp (or pass a datetime) into aware UTC.

    Naive values are taken as UTC. Raises ValueError on anything unparseable;
    callers decide whether that is a refusal or a validation failure.
    """

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"unparseable ledger timestamp: {value!r}") from exc
    else:
        raise ValueError(f"unparseable ledger timestamp: {value!r}")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def formatTime(value: Any) -> str:
    return parseTime(value).isoformat().replace("+00:00", "Z")


def checkTime(value: Any, where: str) -> None:
    try:
        parseTime(value)
    except ValueError:
        raise malformed(f"{where} is not an ISO-8601 timestamp") from None


def validate_ledger(document: Any) -> dict[str, Any]:
    """Return `document` if it is a well-formed `steward-ledger-v1`.

    Raises `LedgerUnavailable` otherwise. Unknown top-level keys are rejected
    rather than carried: a newer writer's fields are not ours to round-trip
    blindly.
    """

    if not isinstance(document, dict):
        raise malformed("document is not an object")
    unknown = sorted(set(document) - TOP_LEVEL_KEYS)
    if unknown:
        raise malformed(f"unknown top-level keys {unknown}")
    if document.get("schemaVersion") != LEDGER_SCHEMA:
        raise malformed(f"schemaVersion is not {LEDGER_SCHEMA}")
    generation = document.get("generation")
    if not isInt(generation) or generation < 0:
        raise malformed("generation must be a non-negative integer")
    updated = document.get("updatedAt")
    if updated is not None:
        if not isinstance(updated, str):
            raise malformed("updatedAt must be a string or absent")
        checkTime(updated, "updatedAt")
    for key in ("runs", "leases", "work"):
        if not isinstance(document.get(key), dict):
            raise malformed(f"{key} must be an object")
    operations = document.get("operations", {})
    if not isinstance(operations, dict):
        raise malformed("operations must be an object")
    lane = document.get("lane")
    if lane is not None:
        if not isinstance(lane, dict):
            raise malformed("lane must be an object or null")
        if lane.get("schemaVersion") != LANE_SCHEMA:
            raise malformed(f"lane schemaVersion is not {LANE_SCHEMA}")

    for run_id, run in document["runs"].items():
        if not isinstance(run, dict):
            raise malformed(f"run {run_id!r} is not an object")
        if run.get("runId") != run_id:
            raise malformed(f"run {run_id!r} runId does not match its key")
    for key, lease in document["leases"].items():
        if not isinstance(lease, dict):
            raise malformed(f"lease {key!r} is not an object")
        if not isinstance(lease.get("holder"), str) or not lease["holder"]:
            raise malformed(f"lease {key!r} has no holder")
        for field in ("acquiredAt", "expiresAt"):
            if not isinstance(lease.get(field), str):
                raise malformed(f"lease {key!r} {field} must be a string")
            checkTime(lease[field], f"lease {key!r} {field}")
    for debt_id, item in document["work"].items():
        if not isinstance(item, dict):
            raise malformed(f"work {debt_id!r} is not an object")
        if item.get("debtId") != debt_id:
            raise malformed(f"work {debt_id!r} debtId does not match its key")
        if item.get("state") not in WORK_STATES:
            raise malformed(f"work {debt_id!r} has unknown state {item.get('state')!r}")
        if not isinstance(item.get("history", []), list):
            raise malformed(f"work {debt_id!r} history must be a list")
    return document


def serialize(document: Mapping[str, Any]) -> bytes:
    """Deterministic, diffable bytes. Raises LedgerUnavailable if oversized."""

    try:
        text = (
            json.dumps(document, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False)
            + "\n"
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise LedgerUnavailable(f"ledger is not JSON-serializable: {exc}") from exc
    data = text.encode("utf-8")
    if len(data) > MAX_LEDGER_BYTES:
        raise LedgerUnavailable(
            f"ledger would be {len(data)} bytes, over the {MAX_LEDGER_BYTES} byte bound; "
            "retention needs a decision, nothing was pruned"
        )
    return data


def deserialize(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_LEDGER_BYTES:
        raise LedgerUnavailable(
            f"ledger is {len(data)} bytes, over the {MAX_LEDGER_BYTES} byte bound"
        )
    try:
        document = json.loads(data.decode("utf-8"), parse_constant=rejectConstant)
    except (UnicodeDecodeError, ValueError) as exc:  # JSONDecodeError is a ValueError
        raise malformed(f"not valid JSON: {exc}") from exc
    except RecursionError:
        raise malformed("nesting is too deep") from None
    return validate_ledger(document)


def rejectConstant(name: str) -> Any:
    raise ValueError(f"non-finite number {name} is not valid in a ledger")


def safeCopy(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except RecursionError:
        raise malformed("nesting is too deep") from None


def nextGeneration(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validated copy of `document` with generation advanced by one."""

    validate_ledger(document)
    result = safeCopy(dict(document))
    result["generation"] = document["generation"] + 1
    return result


# ---------------------------------------------------------------------------
# Git-ref store
# ---------------------------------------------------------------------------


def validateRemote(remote: Any) -> str:
    if not isinstance(remote, str) or not remote.strip():
        raise ValueError("ledger remote must be a non-empty string")
    if remote.startswith("-") or any(ch.isspace() or ord(ch) < 32 for ch in remote):
        raise ValueError(f"unsafe ledger remote name: {remote!r}")
    return remote


def validateRef(ref: Any) -> str:
    """Accept only `steward/...` branch names that git itself considers valid.

    The ledger ref is pushed to and fetched from with a forced tracking
    refspec; it must never be able to name `main`, a release branch, or a
    malformed ref.
    """

    if not isinstance(ref, str) or not ref.startswith(REF_PREFIX) or len(ref) == len(REF_PREFIX):
        raise ValueError(f"ledger ref must be a branch under {REF_PREFIX!r}: {ref!r}")
    try:
        result = subprocess.run(
            ["git", "check-ref-format", f"refs/heads/{ref}"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=LOCAL_GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LedgerUnavailable(f"git could not validate the ledger ref: {exc}") from exc
    if result.returncode != 0:
        raise ValueError(f"invalid ledger ref name: {ref!r}")
    return ref


class GitRefLedgerStore:
    """Ledger on a dedicated branch of a git remote; CAS by fast-forward push."""

    transport = "git-ref"
    shared = True

    def __init__(
        self,
        repo_root: Path | str,
        remote: str = "origin",
        ref: str = DEFAULT_REF,
        *,
        localTimeout: float = LOCAL_GIT_TIMEOUT,
        remoteTimeout: float = REMOTE_GIT_TIMEOUT,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.remote = validateRemote(remote)
        self.ref = validateRef(ref)
        self.localTimeout = localTimeout
        self.remoteTimeout = remoteTimeout
        self.fetchGuard = threading.Lock()
        # One tracking ref per (remote, ref): two stores in one clone must not
        # read each other's fetch results.
        digest = hashlib.sha256(f"{self.remote}\0{self.ref}".encode("utf-8")).hexdigest()[:12]
        self.trackingRef = f"{LOCAL_TRACKING_PREFIX}-{digest}"
        self.ephemeralRemote = f"steward-remote-{digest}"
        self.urls: tuple[str, str] | None = None

    # -- subprocess plumbing ------------------------------------------------

    def git(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float,
        identity: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess:
        sub_env = {
            key: value
            for key, value in os.environ.items()
            if key not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY"}
        }
        sub_env.update(
            {
                "LC_ALL": "C",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_ASKPASS": "true",
                "GCM_INTERACTIVE": "never",
            }
        )
        # An unattended run must fail, never wait on a credential or host-key prompt.
        sub_env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
        if identity:
            sub_env.update(COMMIT_IDENTITY)
        if env:
            sub_env.update(env)
        feed: dict[str, Any] = (
            {"stdin": subprocess.DEVNULL} if stdin is None else {"input": stdin}
        )
        try:
            return subprocess.run(
                [
                    "git", "-C", str(self.repo_root),
                    "-c", "gc.auto=0", "-c", "maintenance.auto=0",
                    *args,
                ],
                **feed,
                capture_output=True,
                timeout=timeout,
                env=sub_env,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LedgerUnavailable(
                f"git {args[0]} timed out after {timeout:.0f}s"
            ) from exc
        except OSError as exc:
            raise LedgerUnavailable(f"git could not run: {exc}") from exc

    @staticmethod
    def outputText(result: subprocess.CompletedProcess) -> str:
        return (result.stderr or b"").decode("utf-8", "replace") + (
            result.stdout or b""
        ).decode("utf-8", "replace")

    def plumb(self, args: list[str], *, stdin: bytes | None = None, identity: bool = False) -> str:
        result = self.git(args, stdin=stdin, timeout=self.localTimeout, identity=identity)
        if result.returncode != 0:
            raise LedgerUnavailable(f"git {args[0]} failed: {self.outputText(result).strip()[:400]}")
        return result.stdout.decode("utf-8", "replace").strip()

    def _remoteEnv(self, url: str) -> dict[str, str]:
        """Subprocess environment mapping an ephemeral remote name to `url`.

        Configuring the remote dynamically via environment variables keeps git
        from:
        1. Updating `refs/remotes/<remote>/<ref>` on push: git's push mechanism
           maps pushed branches against the target remote's fetch refspecs.
           An ephemeral remote has no fetch refspecs, so git leaves no trace
           outside `refs/steward/`.
        2. Leaking raw credential-bearing URLs into process argv or error logs.
        3. Mutating repository or global configuration files.
        """
        return {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"remote.{self.ephemeralRemote}.url",
            "GIT_CONFIG_VALUE_0": url,
        }

    # -- load ---------------------------------------------------------------

    def resolveUrls(self) -> tuple[str, str]:
        """Fetch and push URLs of the configured remote.

        Resolving URLs and binding them to an ephemeral remote via environment
        variables prevents git from matching the caller's configured remote
        fetch refspecs (e.g. `refs/remotes/<remote>/*`) and ensures no raw
        credential-bearing URLs are passed on argv.
        """

        if self.urls is None:
            fetchUrl = self.plumb(["remote", "get-url", self.remote])
            pushUrl = self.plumb(["remote", "get-url", "--push", self.remote])
            if not fetchUrl or not pushUrl:
                raise LedgerUnavailable(f"remote {self.remote!r} has no URL")
            self.urls = (fetchUrl, pushUrl)
        return self.urls

    def remoteTip(self) -> str | None:
        """Current tip of the ledger ref on the remote, or None if it is absent."""

        _, pushUrl = self.resolveUrls()
        result = self.git(
            ["ls-remote", self.ephemeralRemote, f"refs/heads/{self.ref}"],
            timeout=self.remoteTimeout,
            env=self._remoteEnv(pushUrl),
        )
        if result.returncode != 0:
            raise LedgerUnavailable(f"ledger ls-remote failed: {self.outputText(result).strip()[:400]}")
        for line in result.stdout.decode("utf-8", "replace").splitlines():
            sha, _, name = line.partition("\t")
            if name.strip() == f"refs/heads/{self.ref}" and sha:
                return sha
        return None

    def fetchRemote(self) -> str | None:
        """Fetch the remote ledger ref; return its commit sha, or None if absent."""

        fetchUrl, _ = self.resolveUrls()
        refspec = f"+refs/heads/{self.ref}:{self.trackingRef}"
        with self.fetchGuard:
            result = None
            for attempt in range(6):
                result = self.git(
                    ["fetch", "--no-tags", "--quiet", "--refmap=", self.ephemeralRemote, refspec],
                    timeout=self.remoteTimeout,
                    env=self._remoteEnv(fetchUrl),
                )
                if result.returncode == 0:
                    break
                text = self.outputText(result)
                if "couldn't find remote ref" in text:
                    return None
                # Another process in this clone is updating the tracking ref.
                if any(marker in text for marker in FETCH_LOCK_MARKERS) and attempt < 5:
                    time.sleep(0.05 * (attempt + 1) + random.random() * 0.05)
                    continue
                raise LedgerUnavailable(f"ledger fetch failed: {text.strip()[:400]}")
            return self.plumb(["rev-parse", "--verify", f"{self.trackingRef}^{{commit}}"])

    def load(self) -> tuple[dict[str, Any], str | None]:
        commit = self.fetchRemote()
        if commit is None:
            return empty_ledger(), None
        spec = f"{commit}:{LEDGER_FILENAME}"
        size = self.plumb(["cat-file", "-s", spec])
        try:
            if int(size) > MAX_LEDGER_BYTES:
                raise LedgerUnavailable(
                    f"ledger is {size} bytes, over the {MAX_LEDGER_BYTES} byte bound"
                )
        except ValueError as exc:
            raise LedgerUnavailable(f"unreadable ledger size: {size!r}") from exc
        result = self.git(["cat-file", "-p", spec], timeout=self.localTimeout)
        if result.returncode != 0:
            raise LedgerUnavailable(f"ledger read failed: {self.outputText(result).strip()[:400]}")
        return deserialize(result.stdout), commit

    # -- compare-and-swap ---------------------------------------------------

    def compare_and_swap(
        self, expected: str | None, document: dict[str, Any], message: str
    ) -> str:
        data = serialize(nextGeneration(document))
        if expected is not None:
            probe = self.git(
                ["cat-file", "-e", f"{expected}^{{commit}}"], timeout=self.localTimeout
            )
            if probe.returncode != 0:
                raise LedgerUnavailable(
                    f"expected ledger version {expected} is not present locally; load() first"
                )
        blob = self.plumb(["hash-object", "-w", "--stdin"], stdin=data)
        tree = self.plumb(
            ["mktree"], stdin=f"100644 blob {blob}\t{LEDGER_FILENAME}\n".encode("utf-8")
        )
        # The nonce keeps two writers that read the same version and wrote the
        # same bytes from producing the identical commit: the second push must
        # still be a conflict, not a silent no-op.
        full = f"{message.strip() or 'steward ledger update'}\n\nSteward-Nonce: {uuid.uuid4().hex}\n"
        commitArgs = ["-c", "commit.gpgsign=false", "commit-tree", tree]
        if expected is not None:
            commitArgs += ["-p", expected]
        commitArgs += ["-m", full]
        commit = self.plumb(commitArgs, identity=True)

        # A non-root commit pushed to an ABSENT ref is simply accepted, which
        # would resurrect a deleted ledger from a stale parent. So when we
        # expected an existing ref, confirm it is still there. This narrows the
        # window but cannot close it: a deletion landing between this ls-remote
        # and the push below still recreates the ref (git has no atomic
        # "update only if exists" for a fast-forward push). Deleting
        # `steward/ledger` is an operator action, never a Steward one.
        _, pushUrl = self.resolveUrls()
        if expected is not None and self.remoteTip() is None:
            raise LedgerConflict(
                f"ledger ref refs/heads/{self.ref} no longer exists on the remote; "
                f"refusing to resurrect it from version {expected}"
            )

        # No --force, no --force-with-lease. For a non-root commit the remote
        # accepts the push only if its current tip is an ancestor of `commit`,
        # i.e. is `expected`. A root commit (expected None) is a descendant of
        # nothing, so it cannot replace an existing ref.
        result = self.git(
            [
                "push",
                "--no-verify",
                "--porcelain",
                self.ephemeralRemote,
                f"{commit}:refs/heads/{self.ref}",
            ],
            timeout=self.remoteTimeout,
            env=self._remoteEnv(pushUrl),
        )
        if result.returncode == 0:
            return commit
        self.classifyPushFailure(result, expected)
        raise AssertionError("classifyPushFailure always raises")  # pragma: no cover

    def classifyPushFailure(
        self, result: subprocess.CompletedProcess, expected: str | None
    ) -> None:
        """Raise LedgerConflict or LedgerUnavailable for a failed push.

        Only a porcelain status of non-fast-forward / fetch-first / stale-info is
        a conflict outright. A `[remote rejected]` status could be a lost
        ref-lock race (retry will succeed) or a permanent refusal (a hook, branch
        protection, or a `steward` branch blocking `steward/ledger`); it is a
        conflict only if the remote ref has demonstrably moved off `expected`.
        """

        text = self.outputText(result)
        reasons = [
            line.split("\t")[-1].strip()
            for line in result.stdout.decode("utf-8", "replace").splitlines()
            if line.startswith("!")
        ]
        if any(reason.startswith(known) for reason in reasons for known in PUSH_CONFLICT_REASONS):
            raise LedgerConflict(f"ledger moved since version {expected}: {text.strip()[:300]}")
        if any(reason.startswith("[remote rejected]") for reason in reasons):
            try:
                tip = self.remoteTip()
            except LedgerUnavailable:
                tip = None
            if tip is not None and tip != expected:
                raise LedgerConflict(
                    f"ledger moved to {tip} since version {expected}: {text.strip()[:300]}"
                )
        raise LedgerUnavailable(f"ledger push failed: {text.strip()[:400]}")


# ---------------------------------------------------------------------------
# File store (tests / offline)
# ---------------------------------------------------------------------------


class FileLedgerStore:
    """Single-machine ledger file. `shared` is False and callers must say so."""

    transport = "local-file"
    shared = False

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.lockPath = self.path.with_name(self.path.name + ".lock")

    @staticmethod
    def versionOf(document: Mapping[str, Any], data: bytes) -> str:
        return f"{document['generation']}:{hashlib.sha256(data).hexdigest()[:16]}"

    def readFile(self) -> tuple[dict[str, Any], str | None]:
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return empty_ledger(), None
        except OSError as exc:
            raise LedgerUnavailable(f"ledger read failed: {exc}") from exc
        document = deserialize(data)
        return document, self.versionOf(document, data)

    def load(self) -> tuple[dict[str, Any], str | None]:
        return self.readFile()

    def compare_and_swap(
        self, expected: str | None, document: dict[str, Any], message: str
    ) -> str:
        if fcntl is None:  # pragma: no cover
            raise LedgerUnavailable("FileLedgerStore requires a POSIX host (fcntl)")
        newDocument = nextGeneration(document)
        data = serialize(newDocument)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            lockFd = os.open(self.lockPath, os.O_RDWR | os.O_CREAT, 0o644)
        except OSError as exc:
            raise LedgerUnavailable(f"ledger lock failed: {exc}") from exc
        try:
            fcntl.flock(lockFd, fcntl.LOCK_EX)
            _, current = self.readFile()
            if current != expected:
                raise LedgerConflict(f"ledger is at {current}, expected {expected}")
            tmpFd, tmpName = tempfile.mkstemp(
                dir=self.path.parent, prefix=self.path.name + ".", suffix=".tmp"
            )
            try:
                with os.fdopen(tmpFd, "wb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmpName, self.path)
            except OSError as exc:
                try:
                    os.unlink(tmpName)
                except OSError:
                    pass
                raise LedgerUnavailable(f"ledger write failed: {exc}") from exc
            return self.versionOf(newDocument, data)
        finally:
            os.close(lockFd)  # closing the descriptor releases the flock


# ---------------------------------------------------------------------------
# update(): the only sanctioned write path
# ---------------------------------------------------------------------------


def utcNow() -> datetime:
    return datetime.now(timezone.utc)


def update(
    store: LedgerStore,
    mutate: Callable[[dict[str, Any]], T],
    *,
    retries: int = 5,
    clock: Callable[[], datetime] = utcNow,
    sleep: Callable[[float], None] = time.sleep,
    message: str = "steward ledger update",
) -> tuple[T, str]:
    """Load, mutate a deep copy, compare-and-swap; on conflict re-apply.

    `mutate` must be a function of the document it is handed (it is re-run on a
    fresh document after every conflict) and should not carry side effects.
    A mutation that leaves the document unchanged does not write; the current
    version is returned (a write still happens when the ref does not exist yet,
    so a returned version is always a real one). Exhausted retries raise the
    last `LedgerConflict`.
    """

    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise ValueError(f"retries must be a non-negative integer, got {retries!r}")
    lastConflict: LedgerConflict | None = None
    for attempt in range(retries + 1):
        document, version = store.load()
        working = safeCopy(document)
        result = mutate(working)
        if working == document and version is not None:
            return result, version
        working["updatedAt"] = formatTime(clock())
        try:
            return result, store.compare_and_swap(version, working, message)
        except LedgerConflict as exc:
            lastConflict = exc
            if attempt < retries:
                # Jitter breaks lock-step retries between many contenders.
                sleep(random.random() * min(0.02 * (attempt + 1), 0.25))
    raise LedgerConflict(
        f"ledger update gave up after {retries + 1} attempts: {lastConflict}"
    )


# ---------------------------------------------------------------------------
# Pure helpers; call inside `mutate`
# ---------------------------------------------------------------------------


def acquire_lease(
    doc: dict[str, Any], key: str, holder: str, now: Any, ttl_seconds: float
) -> bool:
    """Take or renew lease `key`. True iff `holder` holds it afterwards.

    Succeeds when there is no lease, the lease is expired, or `holder` already
    holds it (renewal keeps `acquiredAt`). A different, unexpired holder wins.
    """

    if not holder:
        raise ValueError("lease holder must be non-empty")
    if (
        isinstance(ttl_seconds, bool)
        or not isinstance(ttl_seconds, (int, float))
        or not math.isfinite(ttl_seconds)
        or ttl_seconds <= 0
        or ttl_seconds > MAX_LEASE_TTL_SECONDS
    ):
        raise ValueError(
            f"lease ttl must be a finite number of seconds in (0, {MAX_LEASE_TTL_SECONDS}], "
            f"got {ttl_seconds!r}"
        )
    current = parseTime(now)
    try:
        expiry = current + timedelta(seconds=ttl_seconds)
    except OverflowError as exc:
        raise ValueError(f"lease expiry overflows for now={now!r}") from exc
    lease = doc["leases"].get(key)
    if lease is not None:
        live = parseTime(lease["expiresAt"]) > current
        if live and lease["holder"] != holder:
            return False
        if live:  # same holder, unexpired: renew
            doc["leases"][key] = {**lease, "expiresAt": formatTime(expiry)}
            return True
    doc["leases"][key] = {
        "holder": holder,
        "acquiredAt": formatTime(current),
        "expiresAt": formatTime(expiry),
    }
    return True


def release_lease(doc: dict[str, Any], key: str, holder: str) -> bool:
    lease = doc["leases"].get(key)
    if lease is None or lease["holder"] != holder:
        return False
    del doc["leases"][key]
    return True


def leaseHolder(doc: Mapping[str, Any], key: str, now: Any) -> str | None:
    """Current live holder of `key`, or None if free or expired."""

    lease = doc["leases"].get(key)
    if lease is None or parseTime(lease["expiresAt"]) <= parseTime(now):
        return None
    return lease["holder"]


def record_run(doc: dict[str, Any], run_record: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run_record.get("runId")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run record needs a non-empty runId")
    doc["runs"][run_id] = copy.deepcopy(dict(run_record))
    return doc["runs"][run_id]


def get_run(doc: Mapping[str, Any], run_id: str) -> dict[str, Any] | None:
    run = doc["runs"].get(run_id)
    return copy.deepcopy(run) if run is not None else None


def upsert_work(doc: dict[str, Any], work_item: Mapping[str, Any]) -> dict[str, Any]:
    """Create a work item or update its non-state fields.

    State and history only ever change through `transition_work`, so the
    history stays an append-only account of every move. Changing `state` here
    on an existing item is refused rather than silently recorded without a
    reason.
    """

    debt_id = work_item.get("debtId")
    if not isinstance(debt_id, str) or not debt_id:
        raise ValueError("work item needs a non-empty debtId")
    state = work_item.get("state", "queued")
    if state not in WORK_STATES:
        raise ValueError(f"unknown work state: {state!r}")
    existing = doc["work"].get(debt_id)
    incoming = copy.deepcopy(dict(work_item))
    if existing is None:
        incoming["state"] = state
        incoming.setdefault("history", [])
        doc["work"][debt_id] = incoming
        return doc["work"][debt_id]
    if state != existing["state"] and "state" in work_item:
        raise ValueError(
            f"work {debt_id!r} is {existing['state']!r}; change state with transition_work"
        )
    incoming.pop("state", None)
    incoming.pop("history", None)
    existing.update(incoming)
    return existing


def transition_work(
    doc: dict[str, Any], debt_id: str, to_state: str, at: Any, reason: str
) -> dict[str, Any]:
    if to_state not in WORK_STATES:
        raise ValueError(f"unknown work state: {to_state!r}")
    item = doc["work"].get(debt_id)
    if item is None:
        raise ValueError(f"unknown work item: {debt_id!r}")
    if not reason:
        raise ValueError("a work transition needs a reason")
    item.setdefault("history", []).append(
        {"at": formatTime(at), "from": item["state"], "to": to_state, "reason": reason}
    )
    item["state"] = to_state
    return item


def set_lane(doc: dict[str, Any], lane_document: Mapping[str, Any] | None) -> None:
    if lane_document is not None:
        if lane_document.get("schemaVersion") != LANE_SCHEMA:
            raise ValueError(f"lane document schemaVersion is not {LANE_SCHEMA}")
        doc["lane"] = copy.deepcopy(dict(lane_document))
    else:
        doc["lane"] = None
