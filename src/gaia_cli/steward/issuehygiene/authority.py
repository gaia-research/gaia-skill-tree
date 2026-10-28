"""The issue-write proposal is not authority until the founder decides it.

POLICY.yaml selects implementation rules; a writesEnabled edit cannot ratify a
new Class A capability. Missing, malformed and symlinked records fail closed.
"""

from __future__ import annotations

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
        and record.get("id") == DECISION_ID and record.get("status") == "decided"
