"""Consume independently verified per-finding credential dispositions (#2283).

The founder ruling ``steward-credential-reconciliation-2283`` lets a
credential-shaped finding stop being a Class C or B desk item, but only through
an individually verified record bound to that exact finding. This module is the
narrow consumer of those records. It authors nothing and exempts nothing by
pattern, path or directory.

A record decides a finding only when every one of these holds, otherwise the
finding stays undecided (fail closed):

- the record is tracked by Git, parses, and passes every shape check below;
- debtId, path, pattern, fingerprint and occurrence equal the live finding;
- ``contextSha256`` equals the hash of the finding's stable source context: the
  token's line, the two non-blank lines either side, and the chain of enclosing
  block headers (each strictly less indented than the one below, outermost
  first). Only edge ASCII whitespace and CR/LF are ignored: a change inside the
  line (a space, a non-breaking space, any unicode), a move to another function
  or class, or an edit within the surrounding window reopens the finding, while
  an edit elsewhere in the file does not;
- the finding can be rebound UNIQUELY: if two live findings share a pattern,
  fingerprint and context hash (identical occurrences), neither is decided;
- ``policy`` is D1, D2 or D3, and that policy's decision record and the ruling
  record are decided AND accepted by the desk's own decision-record validator;
- ``founderRuling`` names the decided ruling record;
- ``verifiedBy`` is present, differs from ``author``, and is NOT self-asserted:
  the record's ``verificationReceipt`` must name a committed receipt
  (``founder/steward/security-dispositions/receipts/<id>.json``) that records an
  ``agent.verify`` outcome of ``verified`` for this file's credential_review
  dispatch, whose verifier agent id equals ``verifiedBy``, whose builder agent id
  equals ``author`` and differs from the verifier, and which lists the sha256 of
  this record's reviewed content. Only the lead's integrate step writes receipts;
  the dispatch envelope forbids the builder from writing that directory;
- exactly one record claims that finding. Every claimant counts, valid or not:
  a second record naming the same finding, even an unusable one, keeps it open.

A claimant that omits ``occurrence`` is malformed and counts as an ambiguous
claim on EVERY occurrence of that token; it never defaults to 0.

Finding identity is (debtId, path, pattern, fingerprint, occurrence). The
occurrence index orders repeats of one identical token (same pattern and
fingerprint) within the file, so one record can never resolve two live findings.
The line number is deliberately not part of identity: an unrelated insertion
above a reviewed token must not undo a review.

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
from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.primitives import tracked_files

RECORDSCHEMA = "steward-credential-disposition-v3"
RECORDDIR = "founder/steward/security-dispositions"
RECEIPTDIR = f"{RECORDDIR}/receipts"
RECEIPTSCHEMA = "steward-credential-verification-receipt-v1"
DISPATCHRULE = "credential-review-disposition"
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
    "schemaVersion", "debtId", "path", "pattern", "fingerprint", "occurrence", "contextSha256", "policy",
    "disposition", "evidence", "author", "verifiedBy", "verifiedAt", "verificationReceipt", "founderRuling",
)
# Fields stamped after review, by the lead's integrate step; not part of reviewed content.
_STAMPED = ("verifiedBy", "verifiedAt", "verificationReceipt")
_RECEIPT_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
_MAXRECORDS = 2000
_MAXBYTES = 256 * 1024

LooseKey = tuple[str, str, str, str]
Key = tuple[str, str, str, str, int]


def normalizeLine(text: str) -> str:
    """Strip only leading/trailing ASCII whitespace and CR/LF.

    Everything inside the line stays significant, non-breaking spaces and other
    unicode included, so any change within a string literal reopens the finding.
    """

    return text.strip(" \t\r\n\f\v")


def lineSha256(text: str) -> str:
    return hashlib.sha256(normalizeLine(text).encode("utf-8")).hexdigest()


CONTEXTLINES = 2
SCOPEWALKLIMIT = 4000


def _indent(raw: str) -> int:
    expanded = raw.expandtabs(4)
    return len(expanded) - len(expanded.lstrip(" "))


def contextHash(lines: list[str], index: int) -> str:
    """Hash the stable source context of the finding on ``lines[index]``.

    Language-agnostic by construction: the enclosing scope is the chain of
    strictly less indented non-blank lines above the token (the ``def``/``class``/
    block headers in code and YAML, headings-with-indent elsewhere), and the
    window is the two non-blank lines either side. Blank lines never matter.
    """

    raw = lines[index]

    def neighbours(step: int) -> list[str]:
        found: list[str] = []
        cursor = index + step
        while 0 <= cursor < len(lines) and len(found) < CONTEXTLINES:
            candidate = normalizeLine(lines[cursor])
            if candidate:
                found.append(candidate)
            cursor += step
        return found

    scope: list[str] = []
    bound = _indent(raw)
    cursor, walked = index - 1, 0
    while cursor >= 0 and bound > 0 and walked < SCOPEWALKLIMIT:
        if lines[cursor].strip():
            level = _indent(lines[cursor])
            if level < bound:
                scope.append(normalizeLine(lines[cursor]))
                bound = level
        cursor, walked = cursor - 1, walked + 1
    if bound > 0 and cursor >= 0:
        scope.append("<scope walk truncated>")
    payload = json.dumps(
        {"scope": scope[::-1], "before": neighbours(-1)[::-1], "line": normalizeLine(raw), "after": neighbours(1)},
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def occurrences(findings: Iterable[Mapping[str, Any]]) -> list[int]:
    """Index each finding among live findings sharing pattern and fingerprint."""

    seen: dict[tuple[str, str], int] = {}
    indexes: list[int] = []
    for item in findings:
        key = (str(item["pattern"]), str(item["fingerprint"]))
        indexes.append(seen.get(key, 0))
        seen[key] = seen.get(key, 0) + 1
    return indexes


def recordName(debtId: str, fingerprint: str, occurrence: int = 0) -> str:
    """Conventional file name; the sensor matches on content, never on the name."""

    short = debtId.rsplit(":", 1)[-1]
    return f"{short}-{fingerprint}-{occurrence}.json"


def _identity(value: Any) -> str:
    return value.strip().casefold() if isinstance(value, str) else ""


def _nonNegative(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def contentSha256(body: Mapping[str, Any]) -> str:
    """sha256 of a record's reviewed content: canonical JSON without the post-review stamp."""

    reviewed = {key: value for key, value in body.items() if key not in _STAMPED}
    return hashlib.sha256(json.dumps(reviewed, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def reviewDebtId(path: str) -> str:
    """The credential_review debt id the sensor derives for ``path``."""

    return Observation(
        kind="credential_review", subject=Subject(type="source-file", id=path), observed_at="-",
        source="secret-scan", status="drift", current_state={}, observed_state={},
    ).debt_id


def validateReceipt(body: Any, stem: str) -> str | None:
    """Return why a verification receipt is unusable, or None when it is sound."""

    if not isinstance(body, dict):
        return "receipt is not an object"
    if body.get("schemaVersion") != RECEIPTSCHEMA:
        return "unknown receipt schemaVersion"
    if body.get("receiptId") != stem:
        return "receiptId does not match the file name"
    if body.get("action") != "agent.verify" or body.get("outcome") != "verified":
        return "receipt does not record a verified agent.verify outcome"
    if body.get("dispatchRule") != DISPATCHRULE:
        return "receipt is not for the credential-review dispatch rule"
    for key in ("reviewDebtId", "builderAgentId", "verifierAgentId", "recordedAt"):
        if not isinstance(body.get(key), str) or not body[key].strip():
            return f"receipt {key} must be a non-empty string"
    if not body["reviewDebtId"].startswith("debt:credential_review:"):
        return "receipt reviewDebtId is not a credential_review debt"
    if _identity(body["builderAgentId"]) == _identity(body["verifierAgentId"]):
        return "receipt verifier must be a different agent from the builder"
    try:
        datetime.fromisoformat(body["recordedAt"].replace("Z", "+00:00"))
    except ValueError:
        return "receipt recordedAt must be an ISO 8601 timestamp"
    covered = body.get("records")
    if not isinstance(covered, list) or not covered or any(
        not isinstance(item, str) or not _HEX64.fullmatch(item) for item in covered
    ):
        return "receipt records must list sha256 content hashes"
    return None


def _receiptProblem(record: Mapping[str, Any], receipts: Mapping[str, Mapping[str, Any]]) -> str | None:
    """Why a record's verifier identity is not backed by a recorded verification."""

    receipt = receipts.get(record["verificationReceipt"])
    if receipt is None:
        return "verification receipt is missing or invalid"
    if receipt["reviewDebtId"] != reviewDebtId(record["path"]):
        return "receipt is for a different file's dispatch"
    if _identity(record["verifiedBy"]) != _identity(receipt["verifierAgentId"]):
        return "verifiedBy is not the verifier the receipt recorded"
    if _identity(record["author"]) != _identity(receipt["builderAgentId"]):
        return "author is not the builder the receipt recorded"
    if contentSha256(record) not in receipt["records"]:
        return "receipt does not cover this record's reviewed content"
    return None


def validateRecord(body: Any) -> str | None:
    """Return why a record is unusable, or None when its shape is sound."""

    if not isinstance(body, dict):
        return "record is not an object"
    missing = [key for key in _REQUIRED if key not in body]
    if missing:
        return f"missing {', '.join(missing)}"
    if body["schemaVersion"] != RECORDSCHEMA:
        return "unknown schemaVersion"
    for key in (
        "debtId", "path", "pattern", "policy", "disposition", "author", "verifiedBy", "verifiedAt",
        "verificationReceipt", "founderRuling",
    ):
        if not isinstance(body[key], str) or not body[key].strip():
            return f"{key} must be a non-empty string"
    if not _nonNegative(body["occurrence"]):
        return "occurrence must be a non-negative integer"
    if "line" in body and (not isinstance(body["line"], int) or isinstance(body["line"], bool) or body["line"] < 1):
        return "line, when present, must be a positive integer"
    if not _RECEIPT_ID.fullmatch(body["verificationReceipt"]):
        return "verificationReceipt must be a lowercase receipt id"
    if not _HEX12.fullmatch(str(body["fingerprint"])):
        return "fingerprint must be 12 lowercase hex characters"
    if not _HEX64.fullmatch(str(body["contextSha256"])):
        return "contextSha256 must be 64 lowercase hex characters"
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

    def summary(self, line: int) -> dict[str, Any]:
        """The decided finding, as the live scan sees it (``line`` is the live line)."""

        return {
            "line": line,
            "pattern": self.record["pattern"],
            "fingerprint": self.record["fingerprint"],
            "occurrence": self.record["occurrence"],
            "policy": self.record["policy"],
            "disposition": self.record["disposition"],
            "verifiedBy": self.record["verifiedBy"],
            "verifiedAt": self.record["verifiedAt"],
            "verificationReceipt": self.record["verificationReceipt"],
            "record": self.path,
        }


@dataclass
class Registry:
    """Records keyed by the exact finding they claim; unusable claimants count too."""

    claims: dict[Key, list[Match]] = field(default_factory=dict)
    # Unusable records that still name a finding. A None occurrence claims every one.
    invalidClaims: dict[tuple[LooseKey, int | None], int] = field(default_factory=dict)
    rejected: list[tuple[str, str]] = field(default_factory=list)

    def match(
        self, debtId: str, path: str, finding: Mapping[str, Any], occurrence: int, context: str
    ) -> Match | None:
        loose: LooseKey = (debtId, path, str(finding["pattern"]), str(finding["fingerprint"]))
        if self.invalidClaims.get((loose, occurrence), 0) or self.invalidClaims.get((loose, None), 0):
            return None
        found = self.claims.get((*loose, occurrence), [])
        if len(found) != 1 or found[0].record["contextSha256"] != context:
            return None
        return found[0]


def _claimed(body: Any) -> tuple[LooseKey, int | None] | None:
    """Best-effort identity of the finding an unusable record names, if it names one."""

    if not isinstance(body, dict):
        return None
    debtId, path = body.get("debtId"), body.get("path")
    pattern, fingerprint = body.get("pattern"), body.get("fingerprint")
    if not all(isinstance(item, str) for item in (debtId, path, pattern, fingerprint)):
        return None
    # A missing or malformed occurrence is an ambiguous claim on every occurrence.
    occurrence = body.get("occurrence")
    return (debtId, path, pattern, fingerprint), (occurrence if _nonNegative(occurrence) else None)


def _loadReceipts(root: Path, tracked: set[str], registry: Registry) -> dict[str, Mapping[str, Any]]:
    receipts: dict[str, Mapping[str, Any]] = {}
    for rel in sorted(item for item in tracked if item.startswith(RECEIPTDIR + "/")):
        full = root / rel
        try:
            if full.is_symlink() or full.stat().st_size > _MAXBYTES:
                raise ValueError("symlink or oversize receipt")
            body = json.loads(full.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            registry.rejected.append((rel, "unreadable or malformed receipt"))
            continue
        problem = validateReceipt(body, Path(rel).stem)
        if problem is not None:
            registry.rejected.append((rel, problem))
            continue
        receipts[body["receiptId"]] = body
    return receipts


def loadRegistry(root: Path) -> Registry:
    """Load every tracked record; anything unusable is rejected, never trusted."""

    registry = Registry()
    tracked = set(
        tracked_files(root, [RECORDDIR, DECISIONSDIR], suffixes=(".json",), max_files=_MAXRECORDS, require_any=False)
    )
    paths = sorted(
        item for item in tracked if item.startswith(RECORDDIR + "/") and not item.startswith(RECEIPTDIR + "/")
    )
    if not paths:
        return registry
    receipts = _loadReceipts(root, tracked, registry)
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
        if reason is None:
            reason = _receiptProblem(body, receipts)
        if reason is not None:
            registry.rejected.append((rel, reason))
            claimed = _claimed(body)
            if claimed is not None:
                registry.invalidClaims[claimed] = registry.invalidClaims.get(claimed, 0) + 1
            continue
        key: Key = (body["debtId"], body["path"], body["pattern"], body["fingerprint"], body["occurrence"])
        registry.claims.setdefault(key, []).append(Match(body, rel))
    return registry
