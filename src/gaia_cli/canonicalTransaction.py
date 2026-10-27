"""Bounded, approval-gated canonical multi-file transaction foundation.

The guarded CLI and cooperating legacy writers share this lock. Readers that do
not take it can observe intermediate replacements; this is not reader linearizability.
"""
from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

MAX_TARGETS = 32
MAX_PAYLOAD_BYTES = 1_048_576
MAX_JOURNAL_BYTES = MAX_PAYLOAD_BYTES * 2
STATE_DIR = ".gaia/canonical-transactions"
_heldLocks = threading.local()


class TransactionError(RuntimeError):
    pass


class ApprovalUnavailable(TransactionError):
    pass


class ApprovalRejected(TransactionError):
    pass


@dataclass(frozen=True)
class Change:
    path: str
    after: bytes


@dataclass(frozen=True)
class Target:
    path: str
    before: bytes | None
    after: bytes


@dataclass(frozen=True)
class Plan:
    root: str
    purpose: str
    identity: str
    targets: tuple[Target, ...]
    digest: str


@dataclass(frozen=True)
class ApprovalRequest:
    operation: str
    plan_digest: str
    root: str
    context_digest: str


class ApprovalProvider(Protocol):
    """Trusted out-of-band issuer adapter; caller JSON is not an approval."""

    def verify(self, request: ApprovalRequest) -> bool: ...


class UnavailableApprovalProvider:
    def verify(self, request: ApprovalRequest) -> bool:
        raise ApprovalUnavailable("No trusted canonical transaction issuer is configured")


def _hash(data: bytes | None) -> str:
    if data is None:
        return "<absent>"
    return hashlib.sha256(data).hexdigest()


_sha = _hash


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _root(path: str | Path) -> Path:
    root = Path(path).resolve(strict=True)
    if not root.is_dir():
        raise TransactionError("selected root must be an existing directory")
    return root


def _target(root: Path, value: str) -> Path:
    rel = PurePosixPath(value)
    if (not value or rel.is_absolute() or "\\" in value or value != rel.as_posix()
            or any(part in ("", ".", "..") for part in rel.parts)):
        raise TransactionError(f"unsafe relative target: {value!r}")
    if rel.parts[0] not in {"registry", "skill-trees"}:
        raise TransactionError("target is outside the allowed registry and user-tree areas")
    if rel.parts[0] == "registry" and (len(rel.parts) < 3 or rel.parts[1] not in {"nodes", "named"}):
        raise TransactionError("registry target must be under nodes/ or named/")
    if rel.parts[0] == "registry" and ((rel.parts[1] == "nodes" and not value.endswith(".json"))
                                       or (rel.parts[1] == "named" and not value.endswith(".md"))):
        raise TransactionError("node targets must be JSON and named-skill targets must be Markdown")
    if rel.parts[0] == "skill-trees" and (len(rel.parts) != 3 or rel.parts[-1] != "skill-tree.json"):
        raise TransactionError("user-tree target must be a user's skill-tree.json")
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise TransactionError(f"symlink target component refused: {value}")
    try:
        current.resolve(strict=False).relative_to(root)
    except ValueError as exc:
        raise TransactionError("target escapes selected root") from exc
    if current.exists() and not current.is_file():
        raise TransactionError("target must be a regular file")
    if not current.parent.is_dir():
        raise TransactionError("target parent directory must already exist")
    return current


def _plan_digest(root: str, purpose: str, identity: str, targets: tuple[Target, ...]) -> str:
    payload = {"root": root, "purpose": purpose, "identity": identity,
               "targets": [{"path": t.path, "before": _hash(t.before), "after": _hash(t.after),
                            "beforeLength": None if t.before is None else len(t.before), "afterLength": len(t.after)} for t in targets]}
    return hashlib.sha256(_canonical(payload)).hexdigest()


def prepare(root: str | Path, purpose: str, identity: str, changes: tuple[Change, ...] | list[Change]) -> Plan:
    """Create a deterministic plan without writing to canonical or recovery state."""
    selected = _root(root)
    if not purpose.strip() or not identity.strip():
        raise TransactionError("purpose and immutable plan identity are required")
    if not changes or len(changes) > MAX_TARGETS:
        raise TransactionError(f"changeset must contain 1..{MAX_TARGETS} targets")
    paths = [change.path for change in changes]
    if len(set(paths)) != len(paths):
        raise TransactionError("duplicate target paths are forbidden")
    targets = tuple(sorted((Target(c.path, _target(selected, c.path).read_bytes() if _target(selected, c.path).exists() else None, bytes(c.after)) for c in changes), key=lambda t: t.path))
    if sum(len(t.before or b"") + len(t.after) for t in targets) > MAX_PAYLOAD_BYTES:
        raise TransactionError("changeset exceeds bounded payload size")
    return Plan(str(selected), purpose, identity, targets, _plan_digest(str(selected), purpose, identity, targets))


def _context(plan: Plan, operation: str) -> str:
    return hashlib.sha256(_canonical({"operation": operation, "root": plan.root, "purpose": plan.purpose,
                                      "identity": plan.identity, "plan": plan.digest,
                                      "paths": [t.path for t in plan.targets]})).hexdigest()


def _authorize(provider: ApprovalProvider | None, plan: Plan, operation: str) -> None:
    if provider is None:
        raise ApprovalUnavailable("No trusted canonical transaction issuer is configured")
    try:
        accepted = provider.verify(ApprovalRequest(operation, plan.digest, plan.root, _context(plan, operation)))
    except ApprovalUnavailable:
        raise
    except Exception as exc:
        raise ApprovalRejected("trusted approval verification failed") from exc
    if accepted is not True:
        raise ApprovalRejected("approval does not authorize this exact operation and plan")


@contextlib.contextmanager
def _lock(root: Path):
    held = getattr(_heldLocks, "roots", set()) if getattr(_heldLocks, "pid", None) == os.getpid() else set()
    _heldLocks.pid = os.getpid()
    if str(root) in held:
        yield root / STATE_DIR
        return
    metadata_root = root / ".gaia"
    if metadata_root.is_symlink():
        raise TransactionError("transaction metadata parent cannot be a symlink")
    metadata_root.mkdir(exist_ok=True)
    state = metadata_root / "canonical-transactions"
    state.mkdir(exist_ok=True, mode=0o700)
    if state.is_symlink() or not state.is_dir():
        raise TransactionError("transaction state directory must be a real directory")
    lock_path = state / ".lock"
    if lock_path.is_symlink():
        raise TransactionError("transaction lock cannot be a symlink")
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _heldLocks.roots = held | {str(root)}
        yield state
    finally:
        _heldLocks.roots = held
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic(path: Path, data: bytes, mode: int) -> None:
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise


def _journal_data(plan: Plan, mode_map: dict[str, int]) -> bytes:
    value = {"format": 1, "status": "pending", "root": plan.root, "purpose": plan.purpose,
             "identity": plan.identity, "planDigest": plan.digest,
             "targets": [{"path": t.path, "before": None if t.before is None else base64.b64encode(t.before).decode("ascii"),
                          "after": base64.b64encode(t.after).decode("ascii"), "beforeSha256": _hash(t.before),
                          "afterSha256": _hash(t.after), "mode": mode_map[t.path]} for t in plan.targets]}
    value["journalDigest"] = hashlib.sha256(_canonical(value)).hexdigest()
    # Refuse before any journal/target write if our own recovery reader could
    # reject this record. Reserve the exact largest state we may later persist,
    # including interrupted rollback metadata, rather than just the pending form.
    largest_state = dict(value, status="rolled-back", recoveryOperation="rollback")
    if len(_canonical(largest_state)) + 1 > MAX_JOURNAL_BYTES:
        raise TransactionError("journal exceeds bounded recovery size")
    return _canonical(value) + b"\n"


def assertNoPendingTransaction(root: str | Path) -> None:
    selected = _root(root)
    metadata_root = selected / ".gaia"
    state = selected / STATE_DIR
    if metadata_root.is_symlink() or state.is_symlink():
        raise TransactionError("transaction metadata paths cannot be symlinks")
    if state.exists() and any(p.name.endswith(".pending.json") for p in state.iterdir()):
        raise TransactionError("pending canonical transaction requires explicit recovery")


@contextlib.contextmanager
def canonicalTransactionLock(root: str | Path):
    """Cooperative lock/guard hook for legacy writers; callers still own CAS and recovery."""
    selected = _root(root)
    with _lock(selected):
        assertNoPendingTransaction(selected)
        yield


@contextlib.contextmanager
def guardCanonicalPath(path: str | Path):
    """Guard shared file serializers without imposing a Class-C issuer on legacy work."""
    selected = Path(path).absolute()
    for parent in selected.parents:
        # A valid contributor may itself be named registry or skill-trees.
        # Match the namespace's internal path, not just an ancestor basename.
        parts = selected.relative_to(parent).parts
        registry_target = (parent.name == "registry" and len(parts) >= 2
                           and parts[0] in {"nodes", "named"})
        tree_target = (parent.name == "skill-trees" and len(parts) == 2
                       and parts[-1] == "skill-tree.json")
        if registry_target or tree_target:
            with canonicalTransactionLock(parent.parent):
                yield
            return
    yield


def apply(plan: Plan, provider: ApprovalProvider | None = None, *, fail_after: int | None = None) -> str:
    """Apply authorized plan with CAS, durable preimages/stages and recoverable journal."""
    selected = _root(plan.root)
    if str(selected) != plan.root:
        raise TransactionError("plan root identity changed")
    if (not plan.purpose.strip() or not plan.identity.strip() or not plan.targets
            or len(plan.targets) > MAX_TARGETS or tuple(sorted(plan.targets, key=lambda t: t.path)) != plan.targets
            or len({t.path for t in plan.targets}) != len(plan.targets)
            or sum(len(t.before or b"") + len(t.after) for t in plan.targets) > MAX_PAYLOAD_BYTES
            or _plan_digest(plan.root, plan.purpose, plan.identity, plan.targets) != plan.digest):
        raise TransactionError("plan identity, ordering, bounds or digest is invalid")
    _authorize(provider, plan, "apply")
    with _lock(selected) as state:
        assertNoPendingTransaction(selected)
        paths = {t.path: _target(selected, t.path) for t in plan.targets}
        current = {rel: (p.read_bytes() if p.exists() else None) for rel, p in paths.items()}
        if any(_hash(current[t.path]) != _hash(t.before) for t in plan.targets):
            raise TransactionError("CAS conflict: no targets were changed")
        modes = {t.path: (paths[t.path].stat().st_mode & 0o777 if paths[t.path].exists() else 0o644) for t in plan.targets}
        journal = state / f"{plan.digest}.pending.json"
        if any(state.glob(f"{plan.digest}.*.json")):
            raise TransactionError("previously journaled plan cannot be replayed; prepare a new decision")
        journal_bytes = _journal_data(plan, modes)
        _atomic(journal, journal_bytes, 0o600)
        try:
            for index, target in enumerate(plan.targets, 1):
                _atomic(paths[target.path], target.after, modes[target.path])
                if fail_after == index:
                    raise OSError("injected replacement failure")
        except BaseException:
            raise
        done = json.loads(journal_bytes)
        done["status"] = "committed"
        done.pop("journalDigest")
        done["journalDigest"] = hashlib.sha256(_canonical(done)).hexdigest()
        _atomic(journal, _canonical(done) + b"\n", 0o600)
        committed = state / f"{plan.digest}.committed.json"
        os.replace(journal, committed)
        _fsync_dir(state)
        return str(committed)


def _read_journal(path: Path, root: Path) -> tuple[dict, Plan]:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JOURNAL_BYTES:
            raise TransactionError("journal must be a bounded regular file")
        doc = json.loads(path.read_bytes())
        digest = doc.pop("journalDigest")
        if hashlib.sha256(_canonical(doc)).hexdigest() != digest:
            raise TransactionError("journal integrity check failed")
        doc["journalDigest"] = digest
        if doc.get("format") != 1 or doc.get("status") not in {"pending", "committed", "rolled-back"} or doc.get("root") != str(root):
            raise TransactionError("journal state or root invalid")
        targets = []
        for item in doc["targets"]:
            before = None if item["before"] is None else base64.b64decode(item["before"], validate=True)
            after = base64.b64decode(item["after"], validate=True)
            if _hash(before) != item["beforeSha256"] or _hash(after) != item["afterSha256"]:
                raise TransactionError("journal preimage or staged bytes are corrupt")
            _target(root, item["path"])
            targets.append(Target(item["path"], before, after))
        targets.sort(key=lambda t: t.path)
        ordered = tuple(targets)
        plan = Plan(doc["root"], doc["purpose"], doc["identity"], ordered,
                    _plan_digest(doc["root"], doc["purpose"], doc["identity"], ordered))
        if (plan.digest != doc["planDigest"] or not path.name.startswith(plan.digest + ".")
                or not 1 <= len(ordered) <= MAX_TARGETS
                or len({t.path for t in ordered}) != len(ordered)
                or sum(len(t.before or b"") + len(t.after) for t in ordered) > MAX_PAYLOAD_BYTES):
            raise TransactionError("journal plan digest, name or bounds mismatch")
        return doc, plan
    except TransactionError:
        raise
    except Exception as exc:
        raise TransactionError("malformed transaction journal") from exc


def rollback(root: str | Path, journal_path: str | Path, provider: ApprovalProvider | None = None) -> None:
    selected = _root(root)
    path = Path(journal_path)
    with _lock(selected):
        if (path.parent.resolve() != (selected / STATE_DIR).resolve()
                or not (path.name.endswith(".committed.json") or path.name.endswith(".pending.json"))
                or path.is_symlink() or not path.is_file()):
            raise TransactionError("rollback requires a regular pending or committed journal in transaction state")
        doc, plan = _read_journal(path, selected)
        others = [p for p in (selected / STATE_DIR).glob("*.pending.json") if p != path]
        if others:
            raise TransactionError("another pending canonical transaction requires recovery first")
        # Only an explicit rollback approval can reverse a committed receipt.
        _authorize(provider, plan, "rollback")
        paths = {t.path: _target(selected, t.path) for t in plan.targets}
        states = {t.path: (paths[t.path].read_bytes() if paths[t.path].exists() else None) for t in plan.targets}
        if any(_hash(states[t.path]) not in {_hash(t.before), _hash(t.after)} for t in plan.targets):
            raise TransactionError("rollback refused: a target has an unrecognized outside edit")
        if doc["status"] == "rolled-back" and any(states[t.path] != t.before for t in plan.targets):
            raise TransactionError("rollback finalization refused: target differs from restored preimage")
        if doc["status"] == "committed" and any(states[t.path] != t.after for t in plan.targets):
            raise TransactionError("rollback refused: committed target is not its exact after image")
        # Persist rollback intent before restoration so an interrupted reversal also
        # blocks ordinary writers. The journal retains exact preimages and modes.
        if path.name.endswith(".committed.json"):
            pending = path.with_name(path.name.replace(".committed.json", ".pending.json"))
            os.replace(path, pending)
            _fsync_dir(pending.parent)
            path = pending
        doc["status"] = "pending"
        doc["recoveryOperation"] = "rollback"
        doc.pop("journalDigest")
        doc["journalDigest"] = hashlib.sha256(_canonical(doc)).hexdigest()
        _atomic(path, _canonical(doc) + b"\n", 0o600)
        # Preflight all targets before the first restoration.
        for target in plan.targets:
            if _hash(states[target.path]) == _hash(target.before):
                continue
            if target.before is None:
                paths[target.path].unlink()
                _fsync_dir(paths[target.path].parent)
            else:
                _atomic(paths[target.path], target.before, int(next(i["mode"] for i in doc["targets"] if i["path"] == target.path)))
        doc["status"] = "rolled-back"
        doc.pop("journalDigest")
        doc["journalDigest"] = hashlib.sha256(_canonical(doc)).hexdigest()
        rolled = path.with_name(path.name.removesuffix(".pending.json").removesuffix(".committed.json") + ".rolled-back.json")
        _atomic(path, _canonical(doc) + b"\n", 0o600)
        os.replace(path, rolled)
        _fsync_dir(rolled.parent)
