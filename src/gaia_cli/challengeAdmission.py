"""Bind a Frontier case bundle into an admission request and attempt admission honestly.

A case bundle lives at ``evidence/frontier-challenges/<caseId>/``::

    lead.json  request.json  receipts/experiment-receipt.json  meta-verification.json  artifacts/
    [admission-request.json  transcript.json  receipt/  events.jsonl  RUN.md]

Nothing in a bundle is authority. ``inspectBundle`` only re-validates the pieces against
each other and against the committed protocol bytes. Admission happens in exactly one
place, ``attemptAdmission``, by calling ``challengeDomain.open_challenge`` through a
receipt resolver bound to ONE case (``CaseResolver``): it looks only inside that case's own
``receipt/`` directory, pins the pinned-issuer config with no environment overrides, demands
the receipt id ``<caseId>-r<n>``, passes the request's proof source SHA, and afterwards
requires the issuer-attested transcript digest to equal the bytes of ``transcript.json``
(which embeds the recomputed bundle digest). Only then is a case ``admitted``.

``events.jsonl`` is an audit trail, never authority: no reader treats a recorded
``admitted`` event as proof (every docs build re-attempts admission). It is a hash chain
under an exclusive lock, so accidental edits are detected loudly; the append-only guarantee
itself is anchored by git history (an edit to an earlier line is a visible diff on a
meta-guard protected path), not by the chain alone.

No code here touches the Steward package; it only imports the already-landed receipt
adapter and resolver.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

try:  # POSIX advisory locking; Windows falls back to msvcrt, else no lock (single operator)
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None

from . import frontier
from .challengeDomain import (
    Challenge, VerificationReceipt, draft_challenge_id, draft_context_digest, open_challenge,
)
from .steward.challenge_receipts import (
    BUNDLE_APPROVAL, BUNDLE_LIMITS, RECEIPT_SUBDIR, CommittedAttestedReceiptSource, GitHubActionsSource,
    GitHubVerificationReceiptResolver, LocalGit, ReceiptMisconfigured, ReceiptUnavailable, _readBundleZip,
    loadTrustedConfig,
)

NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)  # absent on Windows; assertPlain still checks every component
BINARY = getattr(os, "O_BINARY", 0)
EVIDENCE = "evidence/frontier-challenges"
# Mirrors the Frontier lead id charset (letters of either case, digits) minus its dot/colon/underscore:
# a case id is a single directory name that is also bound in digests and receipt ids, so it can never
# contain a separator, a dot (no traversal, no dot-leading names) or a leading hyphen.
CASEIDRE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,62}$")
LOGINRE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
FIELDRE = re.compile(r"^[A-Za-z0-9._:/@+-]{1,200}$")
GITSHARE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MAXFILE = 4 * 1024 * 1024
EVENTSCHEMA = "frontier-challenge-event-v1"
REQUESTSCHEMA = 1
GENESIS = "0" * 64
METHODS = ("reproducible-test", "benchmark-replay", "cli-replay")
DEFAULTREPO = "gaia-research/gaia-skill-tree"
RECEIPTPATH = "receipts/experiment-receipt.json"  # canonical Frontier layout (frontier.py receipt builder)
LEGACYRECEIPT = "receipt.json"  # pre-Frontier-layout location, still accepted
BUNDLEFILES = ("lead.json", "request.json", RECEIPTPATH, "meta-verification.json")
TRIAGEFILES = ("lead.json", "meta-verification.json", "artifacts/match.json", "artifacts/dedupe.json")
DRAFTKEYS = ("subject_id", "claim_id", "claim", "behavior_id", "contributor_id", "contributor_notice_ref",
             "pinned_version", "pinned_sha", "environment", "test_version", "baseline", "comparator",
             "material_to_origin", "created_at_utc", "linked_challenge_id")
TRANSCRIPTKIND = "gaia-challenge-admission-transcript/v1"


class AdmissionError(ValueError):
    """The bundle or request cannot be processed; nothing was written."""


class BuildEnvironmentError(RuntimeError):
    """A bundle claims admission but this machine cannot verify it (no gh, or shallow history)."""


class HoldReason(str, Enum):
    ISSUER_UNAVAILABLE = "trusted-issuer-unavailable"
    ISSUER_MISCONFIGURED = "trusted-issuer-misconfigured"
    RECEIPT_UNVERIFIABLE = "receipt-unverifiable"
    CHALLENGE_REJECTED = "challenge-rejected"
    BUNDLE_NOT_BOUND = "bundle-not-bound-to-receipt"
    REQUEST_MISSING = "admission-request-missing"
    META_NOT_RECOMMENDED = "meta-not-recommended"
    EVENT_LOG_BROKEN = "event-log-broken"


class Outcome(str, Enum):
    ADMITTED = "admitted"
    HELD = "held"
    LIVE_UNCOMMITTED = "live-verified-uncommitted"


REASONS = tuple(item.value for item in HoldReason)


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def nowUtc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def receiptPattern(caseId: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(caseId)}-r[1-9][0-9]{{0,2}}$")


# --- path safety ---------------------------------------------------------------------

def assertPlain(root: Path, path: Path) -> None:
    """No component of ``path`` below ``root`` may be a symlink."""
    try:
        relative = Path(path).relative_to(root)
    except ValueError:
        raise AdmissionError("path escapes the checkout") from None
    current = Path(root)
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AdmissionError(f"refusing symlinked path component: {current.name}")


def caseDirectory(root: str | Path, caseId: str) -> Path:
    if not isinstance(caseId, str) or not CASEIDRE.fullmatch(caseId):
        raise AdmissionError("case id must be lowercase letters, digits and hyphens (max 63)")
    rootPath = Path(root).resolve()
    path = rootPath / EVIDENCE / caseId
    assertPlain(rootPath, path)
    if not path.is_dir():
        raise AdmissionError(f"no case directory {EVIDENCE}/{caseId}")
    return path


def readBounded(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AdmissionError(f"missing or non-regular file: {path.name}")
    if path.stat().st_size > MAXFILE:
        raise AdmissionError(f"{path.name} exceeds the bounded size")
    return path.read_bytes()


def readJson(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = readBounded(path)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise AdmissionError(f"{path.name} is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise AdmissionError(f"{path.name} must be a JSON object")
    return data, raw


def writeNew(path: Path, data: bytes) -> None:
    """Exclusive, symlink-refusing create; an existing path (even a dangling link) is an error."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | NOFOLLOW | BINARY, 0o644)
    except OSError as exc:
        raise AdmissionError(f"cannot create {path.name} safely: {exc.strerror}") from None
    try:
        os.write(descriptor, data)
    finally:
        os.close(descriptor)


# --- append-only events --------------------------------------------------------------

def parseEvents(raw: bytes) -> tuple[list[dict[str, Any]], list[str], str]:
    """Return ``(events, errors, lastLineDigest)``; a broken chain, gap or edit is an error.

    Reconciled with ``frontier.validate_events``: legacy unchained lines before the first chained entry are
    tolerated (and count toward ``seq``). Two chained forms exist and may follow each other: this module's
    (``schemaVersion``/``seq``/``prev``, hex digest of the previous line) and the Frontier tool's
    (``seq``/``prevHash``, ``sha256:`` digest, null on line 1). Once a chain starts, every later line must be
    chained with a ``seq`` equal to its position and a digest of the previous line; an unchained line after
    that, a gap, or an edit breaks it.

    This is tamper-evidence only. A legacy-only log has no chain, and a truncated tail is invisible in the
    file; both are non-authoritative and git history is the anchor (as in ``frontier.append_event``)."""
    events, errors, prev = [], [], GENESIS
    if raw and not raw.endswith(b"\n"):
        errors.append("events.jsonl does not end with a newline")
    lines = raw.split(b"\n")
    if raw.endswith(b"\n"):
        lines = lines[:-1]
    chained = False
    for index, line in enumerate(lines if raw else [], start=1):
        try:
            event = json.loads(line)
        except ValueError:
            errors.append(f"events.jsonl line {index} is not JSON")
            break
        if not isinstance(event, dict):
            errors.append(f"events.jsonl line {index} breaks the append-only chain")
            break
        own = "schemaVersion" in event or "prev" in event
        tool = "prevHash" in event or ("seq" in event and not own)
        if own:
            valid = event.get("schemaVersion") == EVENTSCHEMA and event.get("seq") == index and event.get("prev") == prev
        elif tool:
            expected = "sha256:" + prev if index > 1 else None
            valid = event.get("seq") == index and event.get("prevHash") == expected
        else:
            valid = not chained  # legacy line: only allowed before the chain starts
        if not valid:
            errors.append(f"events.jsonl line {index} breaks the append-only chain")
            break
        chained = chained or own or tool
        events.append(event)
        prev = hashlib.sha256(line).hexdigest()
    return events, errors, prev


def readEvents(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not os.path.lexists(path):
        return [], []
    try:
        raw = readBounded(path)
    except AdmissionError as exc:
        return [], [str(exc)]
    events, errors, _ = parseEvents(raw)
    return events, errors


def lockFile(descriptor: int) -> None:
    """Exclusive lock released when the descriptor closes."""
    if fcntl is not None:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
    elif msvcrt is not None:  # pragma: no cover
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)


def appendEvent(directory: Path, kind: str, fields: dict[str, Any], *, at: str | None = None) -> dict[str, Any]:
    """Append under an exclusive lock; refuses symlinks and a broken chain."""
    path = directory / "events.jsonl"
    try:
        descriptor = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT | NOFOLLOW | BINARY, 0o644)
    except OSError as exc:
        raise AdmissionError(f"cannot open events.jsonl safely: {exc.strerror}") from None
    try:
        lockFile(descriptor)
        os.lseek(descriptor, 0, os.SEEK_SET)
        raw = os.read(descriptor, MAXFILE + 1)
        if len(raw) > MAXFILE:
            raise AdmissionError("events.jsonl exceeds the bounded size")
        events, errors, prev = parseEvents(raw)
        if errors:
            raise AdmissionError("refusing to append to a broken event log: " + "; ".join(errors))
        event = {"schemaVersion": EVENTSCHEMA, "seq": len(events) + 1, "prev": prev, "at": at or nowUtc(),
                 "type": kind, **fields}
        line = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        os.write(descriptor, line)
        os.fsync(descriptor)
        return event
    finally:
        os.close(descriptor)  # also releases the flock


# --- bundle inspection ---------------------------------------------------------------

@dataclass
class BundleReport:
    caseId: str
    directory: Path
    errors: list[str] = field(default_factory=list)
    eventErrors: list[str] = field(default_factory=list)
    lead: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    receipt: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    admission: dict[str, Any] | None = None
    transcript: dict[str, Any] | None = None
    digests: dict[str, str] = field(default_factory=dict)
    triage: bool = False  # lead + match/dedupe + a stage:"triage" Meta record; no request, receipt or experiment
    receiptFile: str = RECEIPTPATH

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def artifactRoot(self) -> str:
        return f"{EVIDENCE}/{self.caseId}/artifacts"

    @property
    def eligible(self) -> bool:
        recommend = self.meta.get("recommend") if isinstance(self.meta.get("recommend"), dict) else {}
        return self.meta.get("outcome") in frontier.POSITIVE_OUTCOMES and recommend.get("action") == "request-admission-review"

    @property
    def receiptId(self) -> str | None:
        data = (self.admission or {}).get("receipt")
        return data.get("receipt_id") if isinstance(data, dict) else None

    @property
    def challengeId(self) -> str | None:
        value = (self.admission or {}).get("challengeId")
        return value if isinstance(value, str) else None

    @property
    def hasCommittedReceipt(self) -> bool:
        path = self.directory / RECEIPT_SUBDIR
        return os.path.lexists(path)


def receiptLocation(directory: Path) -> str:
    """The receipt file of a case: the canonical Frontier path, else the legacy root path (never both)."""
    for name in (RECEIPTPATH, LEGACYRECEIPT):
        assertPlain(directory, directory / name)  # a symlinked receipts/ or receipt file is refused before any read
    canonicalPath, legacy = os.path.lexists(directory / RECEIPTPATH), os.path.lexists(directory / LEGACYRECEIPT)
    if canonicalPath and legacy:
        raise AdmissionError(f"ambiguous receipt: both {RECEIPTPATH} and {LEGACYRECEIPT} exist")
    return LEGACYRECEIPT if legacy else RECEIPTPATH


def isTriageBundle(directory: Path) -> bool:
    """A triage-only case has no request and no receipt anywhere, and a stage:"triage" Meta record."""
    if any(os.path.lexists(directory / name) for name in ("request.json", "receipts", LEGACYRECEIPT, "admission-request.json")):
        return False
    try:
        meta, _ = readJson(directory / "meta-verification.json")
    except AdmissionError:
        return False
    return meta.get("stage") == "triage"


def bundleDigest(directory: Path, files: tuple[str, ...] | None = None) -> str:
    """Digest of the material an admission binds: the bundle files and artifacts/ (from disk)."""
    names = files if files is not None else tuple(
        receiptLocation(directory) if name == RECEIPTPATH else name for name in BUNDLEFILES)
    entries = {name: sha(readBounded(directory / name)) for name in names}
    artifacts = directory / "artifacts"
    if artifacts.is_symlink():
        raise AdmissionError("artifacts must not be a symlink")
    if artifacts.is_dir():
        for item in sorted(artifacts.rglob("*")):
            if item.is_symlink():
                raise AdmissionError("artifacts must not contain symlinks")
            if item.is_file():
                entries["artifacts/" + item.relative_to(artifacts).as_posix()] = sha(readBounded(item))
    return sha(canonical(entries))


def inspectBundle(root: str | Path, caseId: str) -> BundleReport:
    """Re-validate a committed case bundle; every problem is collected, nothing is trusted."""
    rootPath = Path(root).resolve()
    directory = caseDirectory(rootPath, caseId)
    report = BundleReport(caseId, directory)
    if isTriageBundle(directory):
        return inspectTriage(report, rootPath)
    try:
        report.receiptFile = receiptLocation(directory)
        report.lead, _ = readJson(directory / "lead.json")
        report.request, _ = readJson(directory / "request.json")
        report.receipt, _ = readJson(directory / report.receiptFile)
        report.meta, metaRaw = readJson(directory / "meta-verification.json")
        report.digests = {"lead": sha(canonical(report.lead)), "request": report.request.get("requestId", ""),
                          "receipt": frontier.receipt_digest(report.receipt), "meta": sha(metaRaw),
                          "bundle": bundleDigest(directory)}
    except AdmissionError as exc:
        report.errors.append(str(exc))
        return report
    errors = report.errors
    errors.extend(f"lead: {item}" for item in frontier.validate_lead(report.lead))
    errors.extend(f"request: {item}" for item in frontier.validate_request(report.request))
    if not errors:
        for key, expected in (("leadDigest", report.digests["lead"]), ("leadId", report.lead.get("leadId")),
                              ("campaignId", report.lead.get("campaignId")), ("claimId", report.lead.get("claimId"))):
            if report.request.get(key) != expected:
                errors.append(f"request does not bind the lead: {key}")
        target, bound = report.lead.get("target", {}), report.request.get("target", {})
        if (target.get("skillId"), target.get("revision")) != (bound.get("skillId"), bound.get("revision")):
            errors.append("request target differs from the lead target")
        errors.extend(f"receipt: {item}" for item in frontier.validate_experiment_receipt(
            report.receipt, report.request, repo_root=rootPath, artifact_root=report.artifactRoot))
        errors.extend(f"meta-verification: {item}" for item in frontier.validate_meta_verification(
            report.meta, report.receipt, report.request, repo_root=rootPath, artifact_root=report.artifactRoot))
    # A broken event log does not invalidate the evidence, but it is never silent: it holds admission.
    report.eventErrors = readEvents(directory / "events.jsonl")[1]
    requestPath = directory / "admission-request.json"
    if os.path.lexists(requestPath):
        try:
            report.admission, _ = readJson(requestPath)
            errors.extend(checkAdmissionRequest(report))
        except AdmissionError as exc:
            errors.append(f"admission-request: {exc}")
    report.errors = sorted(set(errors))
    return report


def inspectTriage(report: BundleReport, rootPath: Path) -> BundleReport:
    """Re-validate a triage-only case (lead rejected before any request/receipt). It can only ever be a review."""
    directory = report.directory
    report.triage = True
    try:
        report.lead, _ = readJson(directory / "lead.json")
        report.meta, metaRaw = readJson(directory / "meta-verification.json")
        matchRaw, dedupeRaw = (readBounded(directory / "artifacts" / name) for name in ("match.json", "dedupe.json"))
        report.digests = {"lead": sha(canonical(report.lead)), "meta": sha(metaRaw),
                          "bundle": bundleDigest(directory, TRIAGEFILES)}
    except AdmissionError as exc:
        report.errors.append(str(exc))
        return report
    report.errors.extend(f"meta-verification: {item}" for item in frontier.validate_triage_record(
        report.meta, report.lead, matchRaw, dedupeRaw, repo_root=rootPath))
    # events.jsonl is an audit trail with no authority here and no admission to hold, so it is not checked.
    if os.path.lexists(directory / RECEIPT_SUBDIR):
        report.errors.append("a triage-only case must not carry an issuer receipt")
    report.errors = sorted(set(report.errors))
    return report


def draftOf(request: dict[str, Any]) -> dict[str, Any]:
    draft = request.get("draft")
    if not isinstance(draft, dict) or set(draft) != set(DRAFTKEYS):
        raise AdmissionError("draft must carry exactly the open_challenge context keys")
    return draft


def expectedTranscript(report: BundleReport, draft: dict[str, Any]) -> dict[str, Any]:
    target = report.lead["target"]
    return {
        "kind": TRANSCRIPTKIND, "caseId": report.caseId, "leadId": report.lead["leadId"],
        "leadDigest": report.digests["lead"], "requestId": report.digests["request"],
        "receiptDigest": report.digests["receipt"], "metaVerificationDigest": report.digests["meta"],
        "bundleDigest": report.digests["bundle"], "challengeId": draft_challenge_id(draft),
        "contextDigest": draft_context_digest(draft),
        "subject": {"skillId": target["skillId"], "kind": target["kind"],
                    "genericSkillId": target.get("genericSkillId") or target["skillId"]},
    }


def checkAdmissionRequest(report: BundleReport) -> list[str]:
    """Structural bindings recomputed from the files on disk; none of this is authentication."""
    request, errors = report.admission or {}, []
    if request.get("schemaVersion") != REQUESTSCHEMA or request.get("caseId") != report.caseId:
        return ["schemaVersion must be 1 and name its own case id"]
    try:
        draft = draftOf(request)
        receipt = VerificationReceipt(**request["receipt"])
    except (AdmissionError, TypeError, KeyError, ValueError) as exc:
        return [f"draft or receipt is unusable: {exc}"]
    if not receiptPattern(report.caseId).fullmatch(receipt.receipt_id):
        errors.append(f"receipt id must be {report.caseId}-r<n>")
    expected = {"leadDigest": report.digests["lead"], "requestId": report.digests["request"],
                "receiptDigest": report.digests["receipt"], "metaVerificationDigest": report.digests["meta"],
                "bundleDigest": report.digests["bundle"]}
    if request.get("bundle") != expected:
        errors.append("admission request does not bind this bundle's current bytes")
    if request.get("contextDigest") != draft_context_digest(draft) or request.get("challengeId") != draft_challenge_id(draft):
        errors.append("context digest or challenge id does not derive from the draft")
    if receipt.context_digest != request.get("contextDigest"):
        errors.append("receipt context digest differs from the request")
    if (draft.get("subject_id") != report.lead.get("target", {}).get("skillId")
            or draft.get("claim_id") != report.lead.get("claimId")):
        errors.append("draft subject or claim differs from the lead")
    if receipt.contributor_id != draft.get("contributor_id") or receipt.notice_ref != draft.get("contributor_notice_ref"):
        errors.append("receipt contributor or notice differs from the draft")
    if request.get("verifierId") != receipt.verifier_id:
        errors.append("request verifier differs from the receipt verifier")
    if not GITSHARE.fullmatch(str(request.get("proofSourceSha", ""))):
        errors.append("proofSourceSha must be a git commit id")
    try:
        if request.get("transcriptPath") != "transcript.json":
            raise AdmissionError("transcriptPath must be transcript.json")
        raw = readBounded(report.directory / "transcript.json")
        if sha(raw) != receipt.transcript_digest:
            errors.append("transcript bytes differ from the receipt transcript digest")
        report.transcript, _ = readJson(report.directory / "transcript.json")
        wanted = expectedTranscript(report, draft)
        if any(report.transcript.get(key) != value for key, value in wanted.items()):
            errors.append("transcript does not bind this bundle's current bytes")
    except (AdmissionError, KeyError) as exc:
        errors.append(str(exc))
    return errors


# --- build-request -------------------------------------------------------------------

def buildRequest(root: str | Path, caseId: str, *, verifier: str, builder: str, noticeRef: str,
                 contributor: str | None = None, materialToOrigin: bool = False, revision: int = 1,
                 method: str = "cli-replay", publicReceiptRef: str | None = None,
                 proofSourceSha: str | None = None, verifiedAt: str | None = None,
                 linkedChallengeId: str | None = None, actor: str = "unknown") -> dict[str, Any]:
    """Write ``transcript.json`` and ``admission-request.json`` for a bundle that recommends admission."""
    rootPath = Path(root).resolve()
    report = inspectBundle(rootPath, caseId)
    if (report.admission is not None or os.path.lexists(report.directory / "admission-request.json")
            or os.path.lexists(report.directory / "transcript.json")):
        raise AdmissionError("admission-request.json or transcript.json already exists; a request is pinned by a "
                             "tag once pushed and never overwritten")
    if not report.ok:
        raise AdmissionError("bundle does not re-validate: " + "; ".join(report.errors))
    if not report.eligible:
        raise AdmissionError(f"meta verification outcome {report.meta.get('outcome')!r} does not recommend an admission "
                             "review; there is nothing to bind (use `admit` to record the hold)")
    if method not in METHODS:
        raise AdmissionError("method must be one of " + ", ".join(METHODS))
    lead, request, receipt, meta = report.lead, report.request, report.receipt, report.meta
    target = lead["target"]
    owner = target["skillId"].split("/")[0] if target["kind"] == "named" else None
    contributorId = contributor or owner
    if not contributorId:
        raise AdmissionError("a generic target has no owner; pass --contributor")
    if not LOGINRE.fullmatch(verifier):
        raise AdmissionError("verifier must be the approver's GitHub login")
    for label, value in (("builder", builder), ("contributor", contributorId)):
        if not FIELDRE.fullmatch(value):
            raise AdmissionError(f"{label} is outside the issuer workflow allowlist")
    if verifier.lower() in {builder.lower(), contributorId.lower()}:
        raise AdmissionError("verifier must differ from builder and contributor")
    if not isinstance(revision, int) or not 1 <= revision <= 999:
        raise AdmissionError("revision must be 1-999")
    proof = proofSourceSha or request["protocol"]["revision"]
    if not GITSHARE.fullmatch(proof):
        raise AdmissionError("proof source SHA must be a full git commit id")
    at = verifiedAt or nowUtc()
    declaration = frontier.pinned_declaration(rootPath, request)
    draft = {
        "subject_id": target["skillId"], "claim_id": lead["claimId"], "claim": lead["capability"]["claim"],
        "behavior_id": declaration.get("id") or lead["claimId"], "contributor_id": contributorId,
        "contributor_notice_ref": noticeRef, "pinned_version": f"{target['skillId']}@{target['revision'][:12]}",
        "pinned_sha": target["revision"],
        "environment": f"frontier-protocol {request['protocol']['path']}@{request['protocol']['revision'][:12]}; "
                       f"executed {receipt.get('executedVersion', 'n/a')}",
        "test_version": request["protocol"]["contentDigest"], "baseline": lead["comparison"]["baseline"],
        "comparator": lead["comparison"]["comparator"], "material_to_origin": bool(materialToOrigin),
        "created_at_utc": at, "linked_challenge_id": linkedChallengeId,
    }
    contextDigest, challengeId = draft_context_digest(draft), draft_challenge_id(draft)
    transcript = {
        **expectedTranscript(report, draft),
        "receiptResult": receipt.get("result"), "metaOutcome": meta["outcome"],
        "metaRecommendation": meta["recommend"]["action"], "independence": meta["independence"],
        "outputs": sorted(({"label": o["label"], "path": o["path"], "contentDigest": o["contentDigest"]}
                           for o in receipt.get("outputs", [])), key=lambda item: item["label"]),
        "reexecution": sorted(({"label": a["label"], "path": a["path"], "contentDigest": a["contentDigest"]}
                               for a in meta["reexecution"]["artifacts"]), key=lambda item: item["label"]),
    }
    transcriptBytes = (json.dumps(transcript, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output = (f"meta-verification outcome={meta['outcome']}; receipt result={receipt.get('result')}; "
              f"recommendation={meta['recommend']['action']}; independence={meta['independence']}")
    ref = publicReceiptRef or f"https://github.com/{DEFAULTREPO}/blob/main/{EVIDENCE}/{caseId}/receipt/issuer-approval.json"
    verification = VerificationReceipt(
        receipt_id=f"{caseId}-r{revision}", context_digest=contextDigest, transcript_digest=sha(transcriptBytes),
        verifier_id=verifier, builder_id=builder, contributor_id=contributorId, result="verified", method=method,
        method_version=f"{request['protocol']['path']}@{request['protocol']['revision'][:12]}",
        actual_output=output, output_digest=sha(output.encode("utf-8")), public_receipt_ref=ref,
        notice_ref=noticeRef, verified_at_utc=at)
    document = {
        "schemaVersion": REQUESTSCHEMA, "caseId": caseId, "challengeId": challengeId, "contextDigest": contextDigest,
        "proofSourceSha": proof, "transcriptPath": "transcript.json", "notificationRef": noticeRef,
        "verifierId": verifier, "draft": draft,
        "bundle": {"leadDigest": report.digests["lead"], "requestId": report.digests["request"],
                   "receiptDigest": report.digests["receipt"], "metaVerificationDigest": report.digests["meta"],
                   "bundleDigest": report.digests["bundle"]},
        "receipt": {name: getattr(verification, name) for name in verification.__dataclass_fields__},
    }
    transcriptPath, requestPath = report.directory / "transcript.json", report.directory / "admission-request.json"
    created = []
    try:
        writeNew(transcriptPath, transcriptBytes)
        created.append(transcriptPath)
        writeNew(requestPath, (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        created.append(requestPath)
        after = inspectBundle(rootPath, caseId)
        if not after.ok:
            raise AdmissionError("generated request does not re-validate: " + "; ".join(after.errors))
    except Exception:
        for path in created:  # never leave a half-valid request behind
            path.unlink(missing_ok=True)
        raise
    appendEvent(report.directory, "admission-request-built", {
        "actor": actor, "challengeId": challengeId, "receiptId": verification.receipt_id,
        "requestDigest": sha(requestPath.read_bytes()), "bundleDigest": report.digests["bundle"]})
    return document


# --- case-bound resolution -----------------------------------------------------------

class CaseBound:
    def __init__(self, parent: "CaseResolver", challengeId: str) -> None:
        self.parent, self.challenge_id = parent, challengeId

    def resolve(self, receiptId: str) -> VerificationReceipt:
        parent = self.parent
        if receiptId != parent.receiptId:
            raise ReceiptUnavailable("receipt id is not this case's own receipt")
        inner = parent.inner
        if isinstance(inner, GitHubVerificationReceiptResolver):
            receipt = inner.resolve(receiptId, expected_challenge_id=self.challenge_id,
                                    expected_proof_source_sha=parent.proofSourceSha)
        else:  # injected port (tests only); production resolvers take the branch above
            bound = inner.for_challenge(self.challenge_id)
            if getattr(bound, "challenge_id", None) != self.challenge_id:
                raise ReceiptUnavailable("resolver is not bound to this challenge")
            receipt = bound.resolve(receiptId)
        if parent.approvalPath is not None:
            try:
                sealed = json.loads(parent.approvalPath.read_bytes())
            except (OSError, ValueError):
                raise ReceiptUnavailable("sealed approval is unreadable") from None
            if not isinstance(sealed, dict) or sealed.get("caseId") != parent.caseId:
                raise ReceiptUnavailable("sealed approval names a different case")
        return receipt


class CaseResolver:
    """``VerificationReceiptResolver`` bound to ONE case.

    The committed lookup sees only this case's own ``receipt/`` files (copied to a private
    directory), so a receipt sealed for another case can never satisfy this one.
    """

    def __init__(self, inner: Any, caseId: str, receiptId: str, proofSourceSha: str,
                 approvalPath: Path | None = None, keepalive: Any = None) -> None:
        self.inner, self.caseId, self.receiptId = inner, caseId, receiptId
        self.proofSourceSha, self.approvalPath, self.keepalive = proofSourceSha, approvalPath, keepalive

    def for_challenge(self, challengeId: str) -> CaseBound:
        return CaseBound(self, challengeId)


def scrubbedGit(command, **kwargs):
    """Run git with every GIT_* variable removed so no environment can redirect object lookup
    (GIT_DIR, GIT_OBJECT_DIRECTORY, GIT_ALTERNATE_OBJECT_DIRECTORIES, GIT_CONFIG_*, ...)."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(command, env=env, **kwargs)


def localGit(rootPath: Path) -> LocalGit:
    return LocalGit(rootPath, runner=scrubbedGit)


class IssuerNotConfigured(ReceiptUnavailable):
    """No committed or deployed issuer pins: structurally unavailable, not unverifiable."""


def pinnedConfig():
    """The committed issuer pins ONLY; GAIA_RECEIPT_* overrides never apply to admission."""
    try:
        return loadTrustedConfig(env={})
    except ReceiptMisconfigured:
        raise
    except ReceiptUnavailable as exc:
        raise IssuerNotConfigured(str(exc)) from None


def copyReceiptFiles(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    if source.is_symlink() or not source.is_dir():
        raise ReceiptUnavailable("committed receipt directory is missing or linked")
    for name, cap in BUNDLE_LIMITS.items():
        path = source / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
            raise ReceiptUnavailable(f"committed receipt file {name} is missing, linked, or oversized")
        shutil.copyfile(path, destination / name)


def committedResolver(rootPath: Path, report: BundleReport, receiptDir: Path | None = None) -> CaseResolver:
    """Production offline resolver for one case: pinned config (no env), case-private receipt lookup."""
    config = pinnedConfig()
    scratch = tempfile.TemporaryDirectory(prefix="gaia-case-receipt-")
    destination = Path(scratch.name) / EVIDENCE / report.caseId / RECEIPT_SUBDIR
    copyReceiptFiles(receiptDir or report.directory / RECEIPT_SUBDIR, destination)
    source = CommittedAttestedReceiptSource(scratch.name, git=localGit(rootPath))
    request = report.admission or {}
    return CaseResolver(GitHubVerificationReceiptResolver(config, source), report.caseId, report.receiptId or "",
                        request.get("proofSourceSha", ""), destination / BUNDLE_APPROVAL, scratch)


def liveResolver(rootPath: Path, report: BundleReport) -> CaseResolver:
    config = pinnedConfig()
    request = report.admission or {}
    return CaseResolver(GitHubVerificationReceiptResolver(config, GitHubActionsSource(git=localGit(rootPath))),
                        report.caseId, report.receiptId or "", request.get("proofSourceSha", ""))


# --- admission -----------------------------------------------------------------------

@dataclass(frozen=True)
class AdmissionOutcome:
    outcome: Outcome
    reason: HoldReason | None
    detail: str
    challenge: Challenge | None = None
    genericRef: str | None = None
    resolver: CaseResolver | None = None


def clean(text: Any) -> str:
    """Printable ASCII, bounded, with workflow-command markers (``::``) defused for CI logs."""
    return re.sub(r"[^\x20-\x7e]", " ", str(text))[:240].strip().replace("::", ": :")


def held(reason: HoldReason, detail: str) -> AdmissionOutcome:
    return AdmissionOutcome(Outcome.HELD, reason, clean(detail))


def attemptAdmission(report: BundleReport, root: str | Path, *, resolver: Any = None, online: bool = False) -> AdmissionOutcome:
    """Try a real admission; anything short of a verified, bundle-bound receipt is a hold. Writes nothing.

    ``resolver`` is a test seam standing in for an offline committed lookup. Without it, a case
    with a committed ``receipt/`` uses the offline case-bound source; a case without one is
    held as issuer-unavailable (structurally, no tooling needed) unless ``online`` asks for the
    live adapter, whose success is reported as ``live-verified-uncommitted``, never ``admitted``.
    """
    rootPath = Path(root).resolve()
    if not report.ok:
        raise AdmissionError("bundle does not re-validate: " + "; ".join(report.errors))
    if report.triage:
        raise AdmissionError("a triage-only case has no experiment and can never be admitted")
    if not report.eligible:  # the Meta record's own verdict takes precedence over a missing request or a log problem
        return held(HoldReason.META_NOT_RECOMMENDED, f"meta verification outcome is {report.meta.get('outcome')}")
    if report.eventErrors:
        return held(HoldReason.EVENT_LOG_BROKEN, "; ".join(report.eventErrors))
    if report.admission is None:
        return held(HoldReason.REQUEST_MISSING, "no admission request has been built")
    request = report.admission
    live = False
    try:
        if resolver is not None:
            active = CaseResolver(resolver, report.caseId, report.receiptId or "", request["proofSourceSha"])
        elif report.hasCommittedReceipt:
            active = committedResolver(rootPath, report)
        elif online:
            active, live = liveResolver(rootPath, report), True
        else:
            return held(HoldReason.ISSUER_UNAVAILABLE, "this case has no committed receipt/ directory")
    except ReceiptMisconfigured as exc:
        return held(HoldReason.ISSUER_MISCONFIGURED, exc)
    except IssuerNotConfigured as exc:
        return held(HoldReason.ISSUER_UNAVAILABLE, exc)
    except ReceiptUnavailable as exc:
        return held(HoldReason.RECEIPT_UNVERIFIABLE, exc)
    try:
        draft = dict(draftOf(request))
        values = {key: value for key, value in draft.items() if key != "created_at_utc"}
        challenge = open_challenge(
            receipt_resolver=active, verification_receipt_id=request["receipt"]["receipt_id"],
            verified_at_utc=draft["created_at_utc"], verifier_id=request["verifierId"], **values)
    except ReceiptMisconfigured as exc:
        return held(HoldReason.ISSUER_MISCONFIGURED, exc)
    except ReceiptUnavailable as exc:
        return held(HoldReason.ISSUER_UNAVAILABLE if live else HoldReason.RECEIPT_UNVERIFIABLE, exc)
    except ValueError as exc:
        return held(HoldReason.CHALLENGE_REJECTED, exc)
    except Exception as exc:  # fail closed: an unexpected adapter error is never an admission
        return held(HoldReason.RECEIPT_UNVERIFIABLE, f"{type(exc).__name__}: {exc}")
    opening = challenge.history[0]
    try:
        local = sha(readBounded(report.directory / "transcript.json"))
    except AdmissionError as exc:
        return held(HoldReason.BUNDLE_NOT_BOUND, exc)
    if (challenge.challenge_id != request.get("challengeId") or opening.receipt_id != request["receipt"]["receipt_id"]
            or opening.transcript_digest.removeprefix("sha256:") != local.removeprefix("sha256:")):
        return held(HoldReason.BUNDLE_NOT_BOUND,
                    "the issuer-attested transcript digest does not match this bundle's transcript.json")
    subject = (report.transcript or {}).get("subject", {})
    if not isinstance(subject.get("genericSkillId"), str) or not subject["genericSkillId"].strip():
        return held(HoldReason.BUNDLE_NOT_BOUND, "transcript carries no bound generic skill reference")
    if live:
        return AdmissionOutcome(Outcome.LIVE_UNCOMMITTED, None,
                                "verified live; run `gaia dev challenge fetch-receipt` and commit receipt/ to count")
    return AdmissionOutcome(Outcome.ADMITTED, None, "issuer receipt verified and bound to the bundle",
                            challenge, subject["genericSkillId"], active)


def admit(root: str | Path, caseId: str, *, resolver: Any = None, actor: str = "unknown",
          online: bool = True) -> dict[str, Any]:
    """Attempt admission through the production resolver and append the outcome to events.jsonl."""
    report = inspectBundle(root, caseId)
    if report.eventErrors:
        raise AdmissionError("refusing to record on a broken event log: " + "; ".join(report.eventErrors))
    outcome = attemptAdmission(report, root, resolver=resolver, online=online)
    fields: dict[str, Any] = {"actor": actor, "outcome": outcome.outcome.value,
                              "reason": outcome.reason.value if outcome.reason else "", "detail": outcome.detail,
                              "bundleDigest": report.digests["bundle"], "recordedStateIsNotAuthority": True}
    if report.admission is not None:
        fields["challengeId"] = report.admission.get("challengeId")
    if outcome.challenge is not None:
        fields["historyDigest"] = outcome.challenge.history_digest
    return appendEvent(report.directory, "admission-attempt", fields)


# --- fetch-receipt -------------------------------------------------------------------

def fetchReceipt(root: str | Path, caseId: str, *, source: Any = None, resolver: Any = None,
                 actor: str = "unknown") -> dict[str, Any]:
    """Verify the issuer's run live, then write the committed ``receipt/`` files the offline source reads.

    The three files come from the verified artifact (``artifact.zip``, ``issuer-approval.json``,
    ``attestation.jsonl``); the pinned Sigstore root ships in the package. They are re-verified
    through the case-bound offline resolver before the directory is kept.
    """
    rootPath = Path(root).resolve()
    report = inspectBundle(rootPath, caseId)
    if not report.ok or report.admission is None:
        raise AdmissionError("a valid bundle with an admission request is required")
    if report.hasCommittedReceipt:
        raise AdmissionError("receipt/ already exists; it is never overwritten")
    config = pinnedConfig()
    live = source if source is not None else GitHubActionsSource(git=localGit(rootPath))
    try:
        document = live.fetch(report.receiptId, config)
        data = live.transport.getBytes(f"repos/{config.repository}/actions/artifacts/{document['artifactId']}/zip")
        files = _readBundleZip(data)
    except (ReceiptUnavailable, KeyError, TypeError) as exc:
        raise AdmissionError(f"live issuer receipt is not retrievable: {clean(exc)}") from None
    target = report.directory / RECEIPT_SUBDIR
    assertPlain(rootPath, target)
    target.mkdir()
    try:
        for name, content in files.items():
            writeNew(target / name, content)
        check = inspectBundle(rootPath, caseId)
        outcome = attemptAdmission(check, rootPath, resolver=resolver, online=False)
        if outcome.outcome is not Outcome.ADMITTED:
            raise AdmissionError(f"fetched receipt does not verify offline: {outcome.reason.value if outcome.reason else ''}: {outcome.detail}")
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    return appendEvent(report.directory, "receipt-fetched", {
        "actor": actor, "receiptId": report.receiptId, "files": sorted(files),
        "bundleDigest": report.digests["bundle"], "recordedStateIsNotAuthority": True})
