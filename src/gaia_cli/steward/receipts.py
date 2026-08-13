"""Ignored local debt state and immutable Steward receipts."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from gaia_cli.steward.models import DEBT_SCHEMA, LEDGER_SCHEMA, Debt, Receipt, stable_json


class StateError(RuntimeError):
    """Raised when ignored Steward state is malformed or cannot be persisted."""


@contextmanager
def exclusive_scan_lock(
    lock_directory: Path,
    *,
    repo_root: Path,
    state_root: Path,
) -> Iterator[None]:
    """Serialize one checkout's debt transaction with an atomic directory.

    A process crash can leave the directory behind. That state deliberately
    fails closed: a maintainer must remove it only after confirming that no
    Steward scan is active. Normal exceptions and ``BaseException`` paths
    release the lock in ``finally``.
    """

    ensure_local_state_path(repo_root, state_root, lock_directory)
    state_root.mkdir(parents=True, exist_ok=True)
    ensure_local_state_path(repo_root, state_root, lock_directory)
    try:
        lock_directory.mkdir()
    except FileExistsError as exc:
        raise StateError(
            f"Steward scan lock exists at {lock_directory}; another scan is active "
            "or a prior process crashed. Refusing to continue; remove the lock "
            "only after confirming no scan is running."
        ) from exc

    try:
        yield
    finally:
        try:
            lock_directory.rmdir()
        except FileNotFoundError:
            pass


def ensure_local_state_path(repo_root: Path, state_root: Path, path: Path) -> None:
    """Refuse paths that escape the repository or traverse any symlink.

    Steward state is intentionally local to one checkout. Even a symlink whose
    target happens to remain inside the checkout is refused: accepting it would
    make the write boundary depend on mutable filesystem indirection.
    """

    root = repo_root.resolve()
    lexical_state = state_root.absolute()
    lexical_path = path.absolute()
    try:
        lexical_state.relative_to(root)
        lexical_path.relative_to(lexical_state)
    except ValueError as exc:
        raise StateError(f"Steward state path escapes repository-local state: {path}") from exc

    relative = lexical_path.relative_to(root)
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise StateError(f"cannot inspect Steward state path {candidate}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise StateError(f"Steward state path may not traverse symlink: {candidate}")

    resolved_state = lexical_state.resolve(strict=False)
    resolved_path = lexical_path.resolve(strict=False)
    try:
        resolved_state.relative_to(root)
        resolved_path.relative_to(resolved_state)
    except ValueError as exc:
        raise StateError(f"resolved Steward state path escapes repository: {path}") from exc


def load_debts(path: Path, *, repo_root: Path, state_root: Path) -> dict[str, Debt]:
    ensure_local_state_path(repo_root, state_root, path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateError(f"cannot read Steward debt state at {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != LEDGER_SCHEMA:
        raise StateError(f"unsupported Steward debt ledger at {path}")
    raw_debts = data.get("debts")
    if not isinstance(raw_debts, list):
        raise StateError("Steward debt ledger debts must be a list")
    result: dict[str, Debt] = {}
    try:
        for item in raw_debts:
            debt = Debt.from_dict(item)
            if debt.id in result:
                raise StateError(f"duplicate debt id in state: {debt.id}")
            result[debt.id] = debt
    except (KeyError, TypeError, ValueError) as exc:
        raise StateError(f"invalid Steward debt record: {exc}") from exc
    return result


def ledger_document(debts: Iterable[Debt]) -> dict[str, object]:
    return {
        "schemaVersion": LEDGER_SCHEMA,
        "debtSchemaVersion": DEBT_SCHEMA,
        "debts": [debt.to_dict() for debt in sorted(debts, key=lambda item: item.id)],
    }


def _pretty_json(data: object) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_current_state(
    path: Path,
    debts: Iterable[Debt],
    *,
    repo_root: Path,
    state_root: Path,
) -> bool:
    """Atomically update current debt state, skipping byte-identical writes."""

    ensure_local_state_path(repo_root, state_root, path)
    content = _pretty_json(ledger_document(debts))
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_local_state_path(repo_root, state_root, path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    ensure_local_state_path(repo_root, state_root, temporary)
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return True


def make_run_id(timestamp: str, payload: object) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "")
    return f"steward-{compact_time}-{run_id_digest(payload)}"


def run_id_digest(payload: object) -> str:
    """The content half of a run id: a digest of the payload alone."""

    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()[:16]


def run_id_matches(run_id: str, payload: object) -> bool:
    """Return whether a receipt's own id still attests to its contents.

    A receipt is only evidence while it is unedited. The id already commits to
    the payload, so this needs no extra field: a receipt whose body was changed
    after publication no longer hashes to the name it was published under.
    Timestamps are excluded from the digest by construction, so this compares
    content and nothing else.
    """

    _, _, digest = run_id.rpartition("-")
    return bool(digest) and digest == run_id_digest(payload)


def write_immutable_receipt(
    receipts_directory: Path,
    receipt: Receipt,
    *,
    repo_root: Path,
    state_root: Path,
) -> tuple[Path, bool]:
    """Stage and atomically publish an immutable receipt.

    Every publication lane first owns the same per-name claim.  The owner may
    use a hard link or the same-directory rename fallback, but no second lane
    can publish different bytes while that claim is held.
    """

    ensure_local_state_path(repo_root, state_root, receipts_directory)
    receipts_directory.mkdir(parents=True, exist_ok=True)
    path = receipts_directory / f"{receipt.run_id}.json"
    ensure_local_state_path(repo_root, state_root, path)
    content = _pretty_json(receipt.to_dict())

    stage_fd, stage_name = tempfile.mkstemp(
        dir=receipts_directory,
        prefix=f".{receipt.run_id}.",
        suffix=".tmp",
    )
    stage = Path(stage_name)
    try:
        try:
            ensure_local_state_path(repo_root, state_root, stage)
            _write_all(stage_fd, content)
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
    except BaseException:
        _unlink_owned(stage)
        raise

    try:
        _publish_stage(stage, path)
    except FileExistsError:
        try:
            ensure_local_state_path(repo_root, state_root, path)
            if path.read_bytes() != content:
                raise StateError(f"immutable Steward receipt collision at {path}")
            return path, False
        finally:
            _cleanup_stage_best_effort(stage)
    except BaseException:
        _cleanup_stage_best_effort(stage)
        raise
    else:
        # Publication is irrevocable at this layer. A concurrent equivalent
        # run may already have observed and reused the complete final receipt,
        # so stage cleanup must never remove or invalidate it.
        _cleanup_stage_best_effort(stage)
        return path, True


def _publish_stage(stage: Path, final: Path) -> None:
    """Atomically create ``final`` under a shared no-clobber ownership claim.

    The claim is acquired before choosing a publication primitive.  This is
    essential: a hard-link writer and a fallback writer otherwise have no
    common ownership boundary and can race to replace the final name.
    """

    claim = _claim_publication(final)
    try:
        if final.exists():
            raise FileExistsError(final)
        try:
            os.link(stage, final, follow_symlinks=False)
            return
        except FileExistsError:
            raise
        except (AttributeError, NotImplementedError, OSError) as exc:
            if isinstance(exc, OSError) and exc.errno not in {
                errno.EPERM, errno.EOPNOTSUPP, errno.ENOSYS, errno.EXDEV,
            }:
                raise
        # Only the claim owner can use rename.  It has already established
        # final absence, and no other Steward lane can publish until release.
        os.replace(stage, final)
    finally:
        try:
            claim.rmdir()
        except FileNotFoundError:
            pass


def _claim_publication(final: Path) -> Path:
    """Claim one final name or wait only long enough to observe its owner."""

    claim = final.with_name(f".{final.name}.publish-lock")
    try:
        claim.mkdir()
        return claim
    except FileExistsError:
        # A live owner publishes only a complete final file.  A missing final
        # after the bounded wait is a stale claim and remains fail-closed.
        for _ in range(100):
            if final.exists():
                raise FileExistsError(final)
            time.sleep(0.01)
        raise StateError(f"immutable Steward receipt publication is in progress or stale: {claim}")


def _write_chunk(file_descriptor: int, content: memoryview) -> int:
    """One injectable low-level write used by short-write regression tests."""

    return os.write(file_descriptor, content)


def _write_all(file_descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = _write_chunk(file_descriptor, remaining)
        if written <= 0:
            raise OSError("receipt staging write made no progress")
        remaining = remaining[written:]


def _cleanup_stage_best_effort(stage: Path) -> None:
    """Remove a receipt stage without affecting an already-published final."""

    for _attempt in range(2):
        try:
            _unlink_owned(stage)
            return
        except OSError:
            continue


def _unlink_owned(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def remove_uncommitted_receipt(
    path: Path,
    *,
    repo_root: Path,
    state_root: Path,
) -> None:
    """Remove a newly created receipt when its paired ledger commit aborts."""

    ensure_local_state_path(repo_root, state_root, path)
    try:
        path.unlink()
    except FileNotFoundError:
        return
