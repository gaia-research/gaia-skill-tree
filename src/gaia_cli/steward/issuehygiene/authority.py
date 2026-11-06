"""Class A issue-closure authority is the founder's ratification, never a policy switch.

The founder ratified the A1-A5 allowlist (ruling #10, 2026-11-06) in
``steward-issue-closure-authority.json``. POLICY.yaml selects which implemented
rules run and whether writes are on; a writesEnabled edit cannot ratify anything,
and the ratification alone does not turn writes on. A decided question may have
been rejected: only the exact explicit resolution "approved" ratifies it.
Missing, malformed and symlinked records fail closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

DECISION_ID = "steward-issue-closure-authority"
DECISION_PATH = Path("founder/steward/decisions") / f"{DECISION_ID}.json"


def closureAuthorityApproved(root: Path) -> bool:
    path = root / DECISION_PATH
    if any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent):
        return False
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("schemaVersion") == "steward-decision-v1" \
        and record.get("id") == DECISION_ID and record.get("status") == "decided" \
        and record.get("resolution") == "approved"


def authorityReceipt(root: Path) -> dict[str, str] | None:
    """The ratified authority a closure acted under, for its receipt: record id, resolution and the record's sha256.

    None when the record is not currently approved. The caller has already gated on ``closureAuthorityApproved``.
    """
    if not closureAuthorityApproved(root):
        return None
    try:
        digest = hashlib.sha256((root / DECISION_PATH).read_bytes()).hexdigest()
    except OSError:
        return None
    return {"decision": DECISION_ID, "resolution": "approved", "recordSha256": digest}
