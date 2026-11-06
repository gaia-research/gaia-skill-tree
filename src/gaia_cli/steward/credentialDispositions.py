"""Consume independently verified per-finding credential dispositions (#2283).

The founder ruling ``steward-credential-reconciliation-2283`` lets a
credential-shaped finding stop being a Class C desk item, but only through an
individually verified record bound to that exact finding. This module is the
narrow consumer of those records. It authors nothing and exempts nothing by
pattern, path or directory.

A record decides a finding only when every one of these holds, otherwise the
finding stays Class C (fail closed):

- the record is tracked by Git, parses, and passes every shape check below;
- debtId, path, line, pattern and fingerprint equal the live finding;
- ``fileSha256`` equals the sha256 of the file bytes the sensor just read, so
  one changed byte forces a fresh review;
- ``policy`` is D1, D2 or D3 and that policy's decision record is decided;
- ``founderRuling`` names the decided ruling record;
- ``verifiedBy`` is present and differs from ``author`` (independent review);
- exactly one record claims that finding (two claimants are ambiguous).

Records are written by humans and verifiers, never by this code or the sensor.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.primitives import tracked_files

RECORDSCHEMA = "steward-credential-disposition-v1"
RECORDDIR = "founder/steward/security-dispositions"
DECISIONSDIR = "founder/steward/decisions"
RULINGID = "steward-credential-reconciliation-2283"
POLICYDECISIONS = {
    "D1": "steward-security-mirrors-2283",
    "D2": "steward-security-fixtures-2283",
    "D3": "steward-security-source-triage-2283",
}
DISPOSITIONS = ("synthetic-fixture", "mirror", "harmless-pattern", "runtime-header-construction")
MINEVIDENCE = 20

_HEX12 = re.compile(r"[0-9a-f]{12}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_REQUIRED = (
    "schemaVersion", "debtId", "path", "line", "pattern", "fingerprint", "fileSha256", "policy",
    "disposition", "evidence", "author", "verifiedBy", "verifiedAt", "founderRuling",
)
_MAXRECORDS = 2000
_MAXBYTES = 256 * 1024


def fileSha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recordName(debtId: str, line: int, fingerprint: str) -> str:
    """Conventional file name; the sensor matches on content, never on the name."""

    short = debtId.rsplit(":", 1)[-1]
    return f"{short}-{line}-{fingerprint}.json"


def _identity(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def validateRecord(body: Any) -> str | None:
    """Return why a record is unusable, or None when its shape is sound."""

    if not isinstance(body, dict):
        return "record is not an object"
    missing = [key for key in _REQUIRED if key not in body]
    if missing:
        return f"missing {', '.join(missing)}"
    if body["schemaVersion"] != RECORDSCHEMA:
        return "unknown schemaVersion"
    for key in ("debtId", "path", "pattern", "policy", "disposition", "author", "verifiedBy", "verifiedAt", "founderRuling"):
        if not isinstance(body[key], str) or not body[key].strip():
            return f"{key} must be a non-empty string"
    if not isinstance(body["line"], int) or isinstance(body["line"], bool) or body["line"] < 1:
        return "line must be a positive integer"
    if not _HEX12.fullmatch(str(body["fingerprint"])):
        return "fingerprint must be 12 lowercase hex characters"
    if not _HEX64.fullmatch(str(body["fileSha256"])):
        return "fileSha256 must be 64 lowercase hex characters"
    if body["policy"] not in POLICYDECISIONS:
        return "unknown policy"
    if body["disposition"] not in DISPOSITIONS:
        return "unknown disposition"
    evidence = body["evidence"]
    items = evidence if isinstance(evidence, list) else [evidence]
    if not items or any(not isinstance(item, str) or len(item.strip()) < MINEVIDENCE for item in items):
        return "evidence must be specific (non-empty text of at least 20 characters)"
    if _identity(body["verifiedBy"]) == _identity(body["author"]):
        return "verifiedBy must be independent of author"
    try:
        datetime.fromisoformat(body["verifiedAt"].replace("Z", "+00:00"))
    except ValueError:
        return "verifiedAt must be an ISO 8601 timestamp"
    if body["founderRuling"] != RULINGID:
        return "founderRuling does not name the 2283 reconciliation ruling"
    return None


def _decided(root: Path, tracked: set[str], identifier: str) -> bool:
    rel = f"{DECISIONSDIR}/{identifier}.json"
    if rel not in tracked:
        return False
    try:
        record = json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("id") == identifier and record.get("status") == "decided"


@dataclass(frozen=True)
class Match:
    record: Mapping[str, Any]
    path: str

    def summary(self) -> dict[str, Any]:
        return {
            "line": self.record["line"],
            "pattern": self.record["pattern"],
            "fingerprint": self.record["fingerprint"],
            "policy": self.record["policy"],
            "disposition": self.record["disposition"],
            "verifiedBy": self.record["verifiedBy"],
            "verifiedAt": self.record["verifiedAt"],
            "record": self.path,
        }


@dataclass
class Registry:
    """Valid records keyed by the exact finding they claim."""

    claims: dict[tuple[str, str, int, str, str], list[Match]] = field(default_factory=dict)
    rejected: list[tuple[str, str]] = field(default_factory=list)

    def match(self, debtId: str, path: str, finding: Mapping[str, Any], sha: str) -> Match | None:
        key = (debtId, path, int(finding["line"]), str(finding["pattern"]), str(finding["fingerprint"]))
        found = self.claims.get(key, [])
        if len(found) != 1:
            return None
        record = found[0].record
        if record["fileSha256"] != sha:
            return None
        return found[0]


def loadRegistry(root: Path) -> Registry:
    """Load every tracked record; anything unusable is rejected, never trusted."""

    registry = Registry()
    tracked = set(
        tracked_files(root, [RECORDDIR, DECISIONSDIR], suffixes=(".json",), max_files=_MAXRECORDS, require_any=False)
    )
    paths = sorted(item for item in tracked if item.startswith(RECORDDIR + "/"))
    if not paths:
        return registry
    ruling = _decided(root, tracked, RULINGID)
    policies = {name: _decided(root, tracked, identifier) for name, identifier in POLICYDECISIONS.items()}
    for rel in paths:
        full = root / rel
        try:
            if full.is_symlink() or full.stat().st_size > _MAXBYTES:
                registry.rejected.append((rel, "symlink or oversize record"))
                continue
            body = json.loads(full.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            registry.rejected.append((rel, "unreadable or malformed JSON"))
            continue
        reason = validateRecord(body)
        if reason is None and not ruling:
            reason = "founder ruling record is not decided"
        if reason is None and not policies[body["policy"]]:
            reason = f"{body['policy']} policy decision record is not decided"
        if reason is not None:
            registry.rejected.append((rel, reason))
            continue
        key = (body["debtId"], body["path"], body["line"], body["pattern"], body["fingerprint"])
        registry.claims.setdefault(key, []).append(Match(body, rel))
    return registry
