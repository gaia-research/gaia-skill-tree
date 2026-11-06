"""Consume independently verified per-finding credential dispositions (#2283).

The founder ruling ``steward-credential-reconciliation-2283`` lets a
credential-shaped finding stop being a Class C desk item, but only through an
individually verified record bound to that exact finding. This module is the
narrow consumer of those records. It authors nothing and exempts nothing by
pattern, path or directory.

A record decides a finding only when every one of these holds, otherwise the
finding stays Class C (fail closed):

- the record is tracked by Git, parses, and passes every shape check below;
- debtId, path, line, pattern, fingerprint and occurrence equal the live finding;
- ``fileSha256`` equals the sha256 of the file bytes the sensor just read, so
  one changed byte forces a fresh review;
- ``policy`` is D1, D2 or D3, and that policy's decision record and the ruling
  record are decided AND accepted by the desk's own decision-record validator;
- ``founderRuling`` names the decided ruling record;
- ``verifiedBy`` is present and differs from ``author`` (independent review);
- exactly one record claims that finding. Every claimant counts, valid or not:
  a second record naming the same finding, even an unusable one, keeps it C.

Finding identity is (debtId, path, line, pattern, fingerprint, occurrence). The
occurrence index orders repeats of one token on one line, so one record can
never resolve two live findings; a record that omits it claims occurrence 0.

Records are written by humans and verifiers, never by this code or the sensor.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from gaia_cli.steward.desk import _check_record as deskCheckRecord
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

LooseKey = tuple[str, str, int, str, str]
Key = tuple[str, str, int, str, str, int]


def fileSha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def occurrences(findings: Iterable[Mapping[str, Any]]) -> list[int]:
    """Index each finding among live findings sharing line, pattern and fingerprint."""

    seen: dict[tuple[int, str, str], int] = {}
    indexes: list[int] = []
    for item in findings:
        key = (int(item["line"]), str(item["pattern"]), str(item["fingerprint"]))
        indexes.append(seen.get(key, 0))
        seen[key] = seen.get(key, 0) + 1
    return indexes


def recordName(debtId: str, line: int, fingerprint: str, occurrence: int = 0) -> str:
    """Conventional file name; the sensor matches on content, never on the name."""

    short = debtId.rsplit(":", 1)[-1]
    suffix = f"-{occurrence}" if occurrence else ""
    return f"{short}-{line}-{fingerprint}{suffix}.json"


def _identity(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _validOccurrence(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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
    if not _validOccurrence(body.get("occurrence", 0)):
        return "occurrence must be a non-negative integer when present"
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
    """True only when the desk's own validator accepts the record and it is decided."""

    rel = f"{DECISIONSDIR}/{identifier}.json"
    if rel not in tracked:
        return False
    full = root / rel
    try:
        if full.is_symlink():
            return False
        record = json.loads(full.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(record, dict):
        return False
    if deskCheckRecord({**record, "_source": rel}) is not None:
        return False
    return record.get("id") == identifier and record.get("status") == "decided"


@dataclass(frozen=True)
class Match:
    record: Mapping[str, Any]
    path: str

    def summary(self) -> dict[str, Any]:
        return {
            "line": self.record["line"],
            "pattern": self.record["pattern"],
            "fingerprint": self.record["fingerprint"],
            "occurrence": self.record.get("occurrence", 0),
            "policy": self.record["policy"],
            "disposition": self.record["disposition"],
            "verifiedBy": self.record["verifiedBy"],
            "verifiedAt": self.record["verifiedAt"],
            "record": self.path,
        }


@dataclass
class Registry:
    """Records keyed by the exact finding they claim; unusable claimants count too."""

    claims: dict[Key, list[Match]] = field(default_factory=dict)
    # Unusable records that still name a finding. A None occurrence claims every one.
    invalidClaims: dict[tuple[LooseKey, int | None], int] = field(default_factory=dict)
    rejected: list[tuple[str, str]] = field(default_factory=list)

    def match(self, debtId: str, path: str, finding: Mapping[str, Any], occurrence: int, sha: str) -> Match | None:
        loose: LooseKey = (debtId, path, int(finding["line"]), str(finding["pattern"]), str(finding["fingerprint"]))
        if self.invalidClaims.get((loose, occurrence), 0) or self.invalidClaims.get((loose, None), 0):
            return None
        found = self.claims.get((*loose, occurrence), [])
        if len(found) != 1 or found[0].record["fileSha256"] != sha:
            return None
        return found[0]


def _claimed(body: Any) -> tuple[LooseKey, int | None] | None:
    """Best-effort identity of the finding an unusable record names, if it names one."""

    if not isinstance(body, dict):
        return None
    debtId, path, line = body.get("debtId"), body.get("path"), body.get("line")
    pattern, fingerprint = body.get("pattern"), body.get("fingerprint")
    if not all(isinstance(item, str) for item in (debtId, path, pattern, fingerprint)):
        return None
    if not isinstance(line, int) or isinstance(line, bool):
        return None
    occurrence = body.get("occurrence", 0)
    return (debtId, path, line, pattern, fingerprint), (occurrence if _validOccurrence(occurrence) else None)


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
            reason = "founder ruling record is not decided or not valid"
        if reason is None and not policies[body["policy"]]:
            reason = f"{body['policy']} policy decision record is not decided or not valid"
        if reason is not None:
            registry.rejected.append((rel, reason))
            claimed = _claimed(body)
            if claimed is not None:
                registry.invalidClaims[claimed] = registry.invalidClaims.get(claimed, 0) + 1
            continue
        key: Key = (
            body["debtId"], body["path"], body["line"], body["pattern"], body["fingerprint"], body.get("occurrence", 0),
        )
        registry.claims.setdefault(key, []).append(Match(body, rel))
    return registry
