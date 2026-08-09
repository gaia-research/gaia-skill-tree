"""Ignored local debt state and immutable Steward receipts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

from gaia_cli.steward.models import DEBT_SCHEMA, LEDGER_SCHEMA, Debt, Receipt, stable_json


class StateError(RuntimeError):
    """Raised when ignored Steward state is malformed or cannot be persisted."""


def load_debts(path: Path) -> dict[str, Debt]:
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


def write_current_state(path: Path, debts: Iterable[Debt]) -> bool:
    """Atomically update current debt state, skipping byte-identical writes."""

    content = _pretty_json(ledger_document(debts))
    if path.is_file() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return True


def make_run_id(timestamp: str, payload: object) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "")
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"steward-{compact_time}-{digest}"


def write_immutable_receipt(receipts_directory: Path, receipt: Receipt) -> Path:
    receipts_directory.mkdir(parents=True, exist_ok=True)
    path = receipts_directory / f"{receipt.run_id}.json"
    content = _pretty_json(receipt.to_dict())
    try:
        with path.open("xb") as handle:
            handle.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise StateError(f"immutable Steward receipt collision at {path}")
    return path
