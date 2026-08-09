"""Ignored local debt state and immutable Steward receipts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Iterable

from gaia_cli.steward.models import DEBT_SCHEMA, LEDGER_SCHEMA, Debt, Receipt, stable_json


class StateError(RuntimeError):
    """Raised when ignored Steward state is malformed or cannot be persisted."""


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
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"steward-{compact_time}-{digest}"


def write_immutable_receipt(
    receipts_directory: Path,
    receipt: Receipt,
    *,
    repo_root: Path,
    state_root: Path,
) -> tuple[Path, bool]:
    """Stage and atomically publish an immutable receipt.

    The empty exclusive final-file claim prevents ``os.replace`` from
    overwriting an immutable receipt created by an equivalent concurrent run.
    Both the stage and any final claim owned by this call are removed if a
    ``BaseException`` interrupts publication.
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
        claim_fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        _unlink_owned(stage)
        if path.read_bytes() != content:
            raise StateError(f"immutable Steward receipt collision at {path}")
        return path, False

    try:
        os.close(claim_fd)
        os.replace(stage, path)
        return path, True
    except BaseException:
        _unlink_owned(stage)
        _unlink_owned(path)
        raise


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
