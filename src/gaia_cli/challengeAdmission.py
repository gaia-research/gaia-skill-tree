"""Bind a Frontier case bundle into an admission request and attempt admission honestly.

A case bundle lives at ``evidence/frontier-challenges/<caseId>/``::

    lead.json  request.json  receipt.json  meta-verification.json  artifacts/
    [admission-request.json  transcript.json  receipt/  events.jsonl  RUN.md]

Nothing in a bundle is authority. ``inspectBundle`` only re-validates the pieces against
each other and against the committed protocol bytes. Admission happens in exactly one
place, ``attemptAdmission``, by calling ``challengeDomain.open_challenge`` through a
receipt resolver. The production resolver admits only when the issuer's attested receipt
verifies; otherwise the outcome is ``held`` with a reason. The append-only
``events.jsonl`` is an audit trail only: no reader treats a recorded ``admitted`` event
as proof (the docs build re-attempts admission every time).

No code here touches the Steward package; it only imports the already-landed receipt
adapter and resolver.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable

from . import frontier
from .challengeDomain import (
    Challenge, VerificationReceipt, draft_challenge_id, draft_context_digest, open_challenge,
)

EVIDENCE = "evidence/frontier-challenges"
CASEIDRE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
LOGINRE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
FIELDRE = re.compile(r"^[A-Za-z0-9._:/@+-]{1,200}$")
GITSHARE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
MAXFILE = 4 * 1024 * 1024
EVENTSCHEMA = "frontier-challenge-event-v1"
REQUESTSCHEMA = 1
GENESIS = "0" * 64
METHODS = ("reproducible-test", "benchmark-replay", "cli-replay")
DEFAULTREPO = "gaia-research/gaia-skill-tree"
BUNDLEFILES = ("lead.json", "request.json", "receipt.json", "meta-verification.json")
DRAFTKEYS = ("subject_id", "claim_id", "claim", "behavior_id", "contributor_id", "contributor_notice_ref",
             "pinned_version", "pinned_sha", "environment", "test_version", "baseline", "comparator",
             "material_to_origin", "created_at_utc", "linked_challenge_id")
REASONS = ("trusted-issuer-unavailable", "trusted-issuer-misconfigured", "receipt-unverifiable",
           "challenge-rejected", "admission-request-missing", "not-recommended-for-admission")


class AdmissionError(ValueError):
    """The bundle or request cannot be processed; nothing was written."""


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def nowUtc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def caseDirectory(root: str | Path, caseId: str) -> Path:
    if not isinstance(caseId, str) or not CASEIDRE.fullmatch(caseId):
        raise AdmissionError("case id must be lowercase letters, digits and hyphens (max 63)")
    base = Path(root).resolve() / EVIDENCE
    path = base / caseId
    if path.is_symlink() or not path.is_dir() or not path.resolve().is_relative_to(base.resolve()):
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


# --- append-only events -------------------------------------------------------------

def readEvents(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Return ``(events, errors)``; a broken hash chain, gap or edit is an error."""
    if not path.exists():
        return [], []
    try:
        raw = readBounded(path)
    except AdmissionError as exc:
        return [], [str(exc)]
    events, errors, prev = [], [], GENESIS
    if raw and not raw.endswith(b"\n"):
        errors.append("events.jsonl does not end with a newline")
    for index, line in enumerate(raw.split(b"\n")[:-1] if raw.endswith(b"\n") else raw.split(b"\n"), start=1):
        try:
            event = json.loads(line)
        except ValueError:
            errors.append(f"events.jsonl line {index} is not JSON")
            break
        if (not isinstance(event, dict) or event.get("schemaVersion") != EVENTSCHEMA
                or event.get("seq") != index or event.get("prev") != prev):
            errors.append(f"events.jsonl line {index} breaks the append-only chain")
            break
        events.append(event)
        prev = hashlib.sha256(line).hexdigest()
    return events, errors


def appendEvent(directory: Path, kind: str, fields: dict[str, Any], *, at: str | None = None) -> dict[str, Any]:
    path = directory / "events.jsonl"
    events, errors = readEvents(path)
    if errors:
        raise AdmissionError("refusing to append to a broken event log: " + "; ".join(errors))
    prev = GENESIS
    if events:
        prev = hashlib.sha256(path.read_bytes().rstrip(b"\n").split(b"\n")[-1]).hexdigest()
    event = {"schemaVersion": EVENTSCHEMA, "seq": len(events) + 1, "prev": prev, "at": at or nowUtc(),
             "type": kind, **fields}
    line = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(descriptor, line)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return event


# --- bundle inspection --------------------------------------------------------------

@dataclass
class BundleReport:
    caseId: str
    directory: Path
    errors: list[str] = field(default_factory=list)
    lead: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    receipt: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    admission: dict[str, Any] | None = None
    digests: dict[str, str] = field(default_factory=dict)

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


def bundleDigest(directory: Path) -> str:
    """Digest of the material an admission binds: the four bundle files and artifacts/."""
    entries = {name: sha(readBounded(directory / name)) for name in BUNDLEFILES}
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
    try:
        report.lead, leadRaw = readJson(directory / "lead.json")
        report.request, requestRaw = readJson(directory / "request.json")
        report.receipt, receiptRaw = readJson(directory / "receipt.json")
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
    _, eventErrors = readEvents(directory / "events.jsonl")
    errors.extend(eventErrors)
    requestPath = directory / "admission-request.json"
    if requestPath.exists() or requestPath.is_symlink():
        try:
            report.admission, _ = readJson(requestPath)
            errors.extend(checkAdmissionRequest(report))
        except AdmissionError as exc:
            errors.append(f"admission-request: {exc}")
    report.errors = sorted(set(errors))
    return report


def draftOf(request: dict[str, Any]) -> dict[str, Any]:
    draft = request.get("draft")
    if not isinstance(draft, dict) or set(draft) != set(DRAFTKEYS):
        raise AdmissionError("draft must carry exactly the open_challenge context keys")
    return draft


def checkAdmissionRequest(report: BundleReport) -> list[str]:
    """Structural bindings only; none of this is authentication."""
    request, errors = report.admission or {}, []
    if request.get("schemaVersion") != REQUESTSCHEMA or request.get("caseId") != report.caseId:
        return ["schemaVersion must be 1 and name its own case id"]
    try:
        draft = draftOf(request)
        receipt = VerificationReceipt(**request["receipt"])
    except (AdmissionError, TypeError, KeyError, ValueError) as exc:
        return [f"draft or receipt is unusable: {exc}"]
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
    transcript = request.get("transcriptPath")
    try:
        if transcript != "transcript.json":
            raise AdmissionError("transcriptPath must be transcript.json")
        if sha(readBounded(report.directory / transcript)) != receipt.transcript_digest:
            errors.append("transcript bytes differ from the receipt transcript digest")
    except AdmissionError as exc:
        errors.append(str(exc))
    return errors


# --- build-request -----------------------------------------------------------------

def buildRequest(root: str | Path, caseId: str, *, verifier: str, builder: str, noticeRef: str,
                 contributor: str | None = None, materialToOrigin: bool = False, revision: int = 1,
                 method: str = "cli-replay", publicReceiptRef: str | None = None,
                 proofSourceSha: str | None = None, verifiedAt: str | None = None,
                 linkedChallengeId: str | None = None, actor: str = "unknown") -> dict[str, Any]:
    """Write ``transcript.json`` and ``admission-request.json`` for a bundle that recommends admission."""
    report = inspectBundle(root, caseId)
    if report.admission is not None or (report.directory / "admission-request.json").exists():
        raise AdmissionError("admission-request.json already exists; it is pinned by a tag once pushed, never overwritten")
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
    declaration = frontier.pinned_declaration(Path(root).resolve(), request)
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
        "kind": "gaia-challenge-admission-transcript/v1", "caseId": caseId, "leadId": lead["leadId"],
        "leadDigest": report.digests["lead"], "requestId": report.digests["request"],
        "receiptDigest": report.digests["receipt"], "receiptResult": receipt.get("result"),
        "metaVerificationDigest": report.digests["meta"], "metaOutcome": meta["outcome"],
        "metaRecommendation": meta["recommend"]["action"], "independence": meta["independence"],
        "bundleDigest": report.digests["bundle"],
        "outputs": sorted(({"label": o["label"], "path": o["path"], "contentDigest": o["contentDigest"]}
                           for o in receipt.get("outputs", [])), key=lambda item: item["label"]),
        "reexecution": sorted(({"label": a["label"], "path": a["path"], "contentDigest": a["contentDigest"]}
                               for a in meta["reexecution"]["artifacts"]), key=lambda item: item["label"]),
    }
    transcriptBytes = (json.dumps(transcript, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output = (f"meta-verification outcome={meta['outcome']}; receipt result={receipt.get('result')}; "
              f"recommendation={meta['recommend']['action']}; independence={meta['independence']}")
    repo = DEFAULTREPO
    ref = publicReceiptRef or f"https://github.com/{repo}/blob/main/{EVIDENCE}/{caseId}/receipt/issuer-approval.json"
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
    if transcriptPath.exists():
        raise AdmissionError("transcript.json already exists; refusing to overwrite")
    transcriptPath.write_bytes(transcriptBytes)
    requestPath.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    after = inspectBundle(root, caseId)
    if not after.ok:  # never leave a half-valid request behind
        transcriptPath.unlink()
        requestPath.unlink()
        raise AdmissionError("generated request does not re-validate: " + "; ".join(after.errors))
    appendEvent(report.directory, "admission-request-built", {
        "actor": actor, "challengeId": challengeId, "receiptId": verification.receipt_id,
        "requestDigest": sha(requestPath.read_bytes()), "bundleDigest": report.digests["bundle"]})
    return document


# --- admission ---------------------------------------------------------------------

@dataclass(frozen=True)
class AdmissionOutcome:
    outcome: str          # "admitted" | "held"
    reason: str           # "" when admitted, else one of REASONS
    detail: str
    challenge: Challenge | None = None


def clean(text: Any) -> str:
    return re.sub(r"[^\x20-\x7e]", " ", str(text))[:240].strip()


def productionResolver(root: str | Path, *, online: bool):
    """The only resolver that may admit: pinned config + an allowlisted authenticated source.

    ``online`` uses the live GitHub Actions adapter (admission time); otherwise the
    committed attested bundle (every docs build). Raises ``ReceiptUnavailable`` when the
    issuer is not configured.
    """
    from .steward.challenge_receipts import (
        CommittedAttestedReceiptSource, GitHubActionsSource, GitHubVerificationReceiptResolver, loadTrustedConfig,
    )
    config = loadTrustedConfig()
    source = GitHubActionsSource() if online else CommittedAttestedReceiptSource(root)
    return GitHubVerificationReceiptResolver(config, source)


def attemptAdmission(report: BundleReport, root: str | Path, *, resolver: Any = None, online: bool = False) -> AdmissionOutcome:
    """Try a real admission; anything short of a verified receipt is ``held``. Writes nothing."""
    from .steward.challenge_receipts import ReceiptMisconfigured, ReceiptUnavailable
    if not report.ok:
        raise AdmissionError("bundle does not re-validate: " + "; ".join(report.errors))
    if not report.eligible:
        return AdmissionOutcome("held", "not-recommended-for-admission",
                                f"meta verification outcome is {report.meta.get('outcome')}")
    if report.admission is None:
        return AdmissionOutcome("held", "admission-request-missing", "no admission request has been built")
    request = report.admission
    draft = dict(draftOf(request))
    try:
        useLive = online and not (report.directory / "receipt").is_dir()
        active = resolver if resolver is not None else productionResolver(root, online=useLive)
        values = {key: value for key, value in draft.items() if key != "created_at_utc"}
        challenge = open_challenge(
            receipt_resolver=active, verification_receipt_id=request["receipt"]["receipt_id"],
            verified_at_utc=draft["created_at_utc"], verifier_id=request["verifierId"], **values)
    except ReceiptMisconfigured as exc:
        return AdmissionOutcome("held", "trusted-issuer-misconfigured", clean(exc))
    except ReceiptUnavailable as exc:
        message = str(exc)
        absent = ("absent" in message or "not configured" in message or "no committed" in message
                  or "not found" in message or "no GitHub" in message)
        return AdmissionOutcome("held", "trusted-issuer-unavailable" if absent else "receipt-unverifiable", clean(message))
    except ValueError as exc:
        return AdmissionOutcome("held", "challenge-rejected", clean(exc))
    except Exception as exc:  # fail closed: an unexpected adapter error is never an admission
        return AdmissionOutcome("held", "receipt-unverifiable", clean(f"{type(exc).__name__}: {exc}"))
    if challenge.challenge_id != request.get("challengeId"):
        return AdmissionOutcome("held", "challenge-rejected", "opened challenge id differs from the admission request")
    return AdmissionOutcome("admitted", "", "issuer receipt verified", challenge)


def admit(root: str | Path, caseId: str, *, resolver: Any = None, actor: str = "unknown",
          online: bool = True) -> dict[str, Any]:
    """Attempt admission through the production resolver and append the outcome to events.jsonl."""
    report = inspectBundle(root, caseId)
    outcome = attemptAdmission(report, root, resolver=resolver, online=online)
    fields: dict[str, Any] = {"actor": actor, "outcome": outcome.outcome, "reason": outcome.reason,
                              "detail": outcome.detail, "bundleDigest": report.digests["bundle"],
                              "recordedStateIsNotAuthority": True}
    if report.admission is not None:
        fields["challengeId"] = report.admission.get("challengeId")
    if outcome.challenge is not None:
        fields["historyDigest"] = outcome.challenge.history_digest
    return appendEvent(report.directory, "admission-attempt", fields)
