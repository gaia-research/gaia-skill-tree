"""Fail-closed GitHub Actions receipt proposal boundary for Yggdrasil IV.

This module packages complete technical proof for a future protected producer and
resolves only when an independently authenticated source adapter can prove every
required fact. The current GitHub REST API does not expose durable historical
environment approval evidence with enough specificity to authenticate the human
approver. Accordingly the live adapter is deliberately unavailable; fixtures test
transport and validation logic only and are not live authorization evidence.

No local field, artifact, workflow input, actor string, comment, or checksum is
itself authorization. This module is not connected to curation authorization and
cannot authorize canonical evidence, score, rank, Origin, or policy changes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from typing import Any, Mapping, Protocol

from gaia_cli.challengeDomain import VerificationReceipt

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024
ARTIFACT_FILE = "verification-receipt.json"
RECEIPT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")


class ReceiptUnavailable(RuntimeError):
    """A required trusted source fact is absent, ambiguous, or unprovable."""


@dataclass(frozen=True)
class TrustedReceiptConfig:
    """Deployment-owned allowlist; never deserialize this from challenge input."""

    repository: str
    workflow_path: str
    workflow_ref: str
    workflow_sha: str
    environment: str
    required_reviewers: tuple[str, ...]
    prevent_self_review: bool = True
    issuer: str = "github-actions"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise ValueError("trusted repository configuration is invalid")
        if not self.workflow_path.startswith(".github/workflows/") or ".." in self.workflow_path:
            raise ValueError("trusted workflow path must be a repository workflow path")
        if not self.workflow_ref or not SHA_RE.fullmatch(self.workflow_sha):
            raise ValueError("trusted workflow ref and pinned source SHA are required")
        if not self.environment or not self.required_reviewers or not self.prevent_self_review:
            raise ValueError("protected environment, required reviewers, and prevent-self-review are mandatory")
        if self.issuer != "github-actions":
            raise ValueError("unsupported trusted receipt issuer")


def trusted_config_from_environment(env: Mapping[str, str] | None = None) -> TrustedReceiptConfig:
    """Load explicit deployment configuration; absence means not configured."""
    source = os.environ if env is None else env
    names = ("GAIA_RECEIPT_REPOSITORY", "GAIA_RECEIPT_WORKFLOW_PATH",
             "GAIA_RECEIPT_WORKFLOW_REF", "GAIA_RECEIPT_WORKFLOW_SHA",
             "GAIA_RECEIPT_ENVIRONMENT", "GAIA_RECEIPT_REQUIRED_REVIEWERS")
    missing = [name for name in names if not source.get(name)]
    reviewers = tuple(sorted({part.strip().lower() for part in source.get(
        "GAIA_RECEIPT_REQUIRED_REVIEWERS", "").split(",") if part.strip()}))
    if missing or not reviewers or source.get("GAIA_RECEIPT_PREVENT_SELF_REVIEW") != "true":
        raise ReceiptUnavailable(
            "trusted challenge receipt source is not configured; missing deployment-owned "
            "repository/workflow/ref/SHA/environment/reviewer roster or prevent-self-review=true"
        )
    try:
        return TrustedReceiptConfig(
            source[names[0]], source[names[1]], source[names[2]], source[names[3]],
            source[names[4]], reviewers, True,
        )
    except ValueError as exc:
        raise ReceiptUnavailable(f"trusted challenge receipt configuration is invalid: {exc}") from exc


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_receipt_payload(receipt: VerificationReceipt, *, challenge_id: str,
                         context_digest: str, raw_transcript: bytes,
                         notification_ref: str, source_sha: str) -> dict[str, Any]:
    """Create the exact full artifact body; packaging is not authentication."""
    if not challenge_id.strip() or not SHA_RE.fullmatch(context_digest):
        raise ValueError("challenge binding and SHA-256 context digest are required")
    if not SHA_RE.fullmatch(source_sha):
        raise ValueError("proof source SHA must be a SHA-256 digest")
    if len(raw_transcript) > MAX_TRANSCRIPT_BYTES:
        raise ValueError("raw transcript exceeds the 2 MiB safety limit")
    if notification_ref != receipt.notice_ref:
        raise ValueError("notification reference must match the receipt")
    if receipt.context_digest != context_digest:
        raise ValueError("receipt context digest does not match challenge binding")
    return {
        "schemaVersion": 1,
        "receipt": asdict(receipt),
        "challengeId": challenge_id,
        "contextDigest": context_digest,
        "transcript": raw_transcript.decode("utf-8", errors="strict"),
        "transcriptBytesSha256": _sha(raw_transcript),
        "notificationRef": notification_ref,
        "proofSourceSha": source_sha,
    }


def make_artifact_archive(payload: Mapping[str, Any]) -> tuple[bytes, str]:
    """Build a single-file, bounded ZIP for upload by a protected producer job."""
    content = _canonical(dict(payload))
    if len(content) > MAX_PAYLOAD_BYTES:
        raise ValueError("receipt payload exceeds the 4 MiB safety limit")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.writestr(ARTIFACT_FILE, content)
    archive = stream.getvalue()
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ValueError("receipt artifact archive exceeds the 8 MiB safety limit")
    return archive, _sha(content)


def _parse_archive(archive: bytes, expected_payload_digest: str) -> dict[str, Any]:
    if not isinstance(archive, bytes) or len(archive) > MAX_ARCHIVE_BYTES:
        raise ReceiptUnavailable("receipt artifact archive is absent or exceeds the 8 MiB limit")
    if not SHA_RE.fullmatch(expected_payload_digest):
        raise ReceiptUnavailable("trusted source did not provide an artifact payload digest")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            infos = bundle.infolist()
            if len(infos) != 1 or infos[0].filename != ARTIFACT_FILE:
                raise ValueError("archive must contain exactly the expected regular file")
            info = infos[0]
            if info.is_dir() or info.flag_bits & 0x1 or info.file_size > MAX_PAYLOAD_BYTES:
                raise ValueError("directory, encrypted, or oversized archive member")
            if info.compress_size == 0 and info.file_size or (
                info.compress_size and info.file_size > info.compress_size * 100
            ):
                raise ValueError("archive compression ratio exceeds safety bound")
            content = bundle.read(info)
    except (ValueError, KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ReceiptUnavailable(f"invalid receipt artifact archive: {exc}") from exc
    if _sha(content) != expected_payload_digest:
        raise ReceiptUnavailable("receipt artifact complete-payload digest mismatch")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptUnavailable("receipt artifact payload is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ReceiptUnavailable("receipt artifact payload schema is unsupported")
    return payload


class SourceAdapter(Protocol):
    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]: ...


class GitHubActionsSource:
    """Authenticated GitHub REST probe. Never infers approval from actor claims."""

    API = "https://api.github.com"

    def __init__(self, token: str | None = None, *, timeout: float = 10.0) -> None:
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout

    def _get(self, path: str, *, binary: bool = False) -> Any:
        if not self.token:
            raise ReceiptUnavailable("GitHub API authentication is unavailable (GH_TOKEN/GITHUB_TOKEN missing)")
        request = urllib.request.Request(
            self.API + path,
            headers={"Accept": "application/vnd.github+json" if not binary else "application/vnd.github+json",
                     "Authorization": f"Bearer {self.token}", "X-GitHub-Api-Version": "2022-11-28"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(MAX_ARCHIVE_BYTES + 1)
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise ReceiptUnavailable(f"authenticated GitHub Actions source unavailable: {exc}") from exc
        if len(raw) > MAX_ARCHIVE_BYTES:
            raise ReceiptUnavailable("GitHub API response exceeds bounded source limit")
        if binary:
            return raw
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ReceiptUnavailable("GitHub API returned invalid JSON") from exc

    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]:
        # GitHub REST exposes run, workflow, artifact and environment protection
        # configuration. It does not expose a durable, independently attributable
        # environment-review history for a completed run via this read-only API.
        # Do not accept actor/reviewer details from artifact JSON as a substitute.
        raise ReceiptUnavailable(
            "GitHub REST cannot currently prove completed protected-environment approval "
            "actor/history bound to this run; no trusted receipt is available"
        )


@dataclass(frozen=True)
class SyntheticSourceFixture:
    """Test-only transport fixture. Never evidence of live GitHub authorization."""
    document: Mapping[str, Any]
    archive: bytes

    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]:
        del receipt_id, config
        return self.document


class GitHubVerificationReceiptResolver:
    """Resolve immutable receipts only after source provenance and artifact checks."""

    def __init__(self, config: TrustedReceiptConfig | None = None,
                 source: SourceAdapter | None = None) -> None:
        self.config = config
        self.source = source or GitHubActionsSource()

    def resolve(self, receipt_id: str) -> VerificationReceipt:
        if not isinstance(receipt_id, str) or not RECEIPT_ID_RE.fullmatch(receipt_id):
            raise ReceiptUnavailable("receipt id is invalid")
        config = self.config
        if config is None:
            raise ReceiptUnavailable("trusted challenge receipt source is not configured")
        try:
            source = self.source.fetch(receipt_id, config)
        except ReceiptUnavailable:
            raise
        except Exception as exc:
            raise ReceiptUnavailable(f"trusted source probe failed closed: {exc}") from exc
        self._verify_source(source, receipt_id, config)
        payload = _parse_archive(source["archive"], source["payloadDigest"])
        receipt_data = payload.get("receipt")
        if not isinstance(receipt_data, dict):
            raise ReceiptUnavailable("receipt artifact has no complete receipt object")
        try:
            receipt = VerificationReceipt(**receipt_data)
        except (TypeError, ValueError) as exc:
            raise ReceiptUnavailable(f"receipt artifact fields are invalid: {exc}") from exc
        self._verify_payload(payload, receipt, receipt_id, source)
        return receipt

    @staticmethod
    def _verify_source(source: Mapping[str, Any], receipt_id: str,
                       config: TrustedReceiptConfig) -> None:
        required = {"repository", "workflowPath", "workflowRef", "workflowSha", "environment",
                    "runId", "runAttempt", "runStatus", "runConclusion", "artifactId",
                    "artifactName", "artifactExpired", "artifactRunId", "artifactAttempt",
                    "artifactCount", "builder", "contributor", "reviewer", "requiredReviewers",
                    "preventSelfReview", "approvalHistoryVerified", "payloadDigest", "archive"}
        if not required.issubset(source):
            raise ReceiptUnavailable("trusted Actions provenance is incomplete")
        if (source["repository"] != config.repository or source["workflowPath"] != config.workflow_path
                or source["workflowRef"] != config.workflow_ref or source["workflowSha"] != config.workflow_sha
                or source["environment"] != config.environment):
            raise ReceiptUnavailable("workflow source or protected environment does not match trusted configuration")
        run_id, attempt = source["runId"], source["runAttempt"]
        if type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt <= 0:
            raise ReceiptUnavailable("workflow run/attempt identity is invalid")
        if source["runStatus"] != "completed" or source["runConclusion"] != "success":
            raise ReceiptUnavailable("workflow run did not complete successfully")
        if (source["artifactExpired"] is not False or type(source["artifactCount"]) is not int
                or source["artifactCount"] != 1):
            raise ReceiptUnavailable("receipt artifact is expired or ambiguous/duplicated")
        expected_name = f"challenge-receipt-{run_id}-{attempt}-{receipt_id}"
        if (source["artifactName"] != expected_name or type(source["artifactRunId"]) is not int
                or source["artifactRunId"] != run_id or type(source["artifactAttempt"]) is not int
                or source["artifactAttempt"] != attempt or type(source["artifactId"]) is not int):
            raise ReceiptUnavailable("artifact is not uniquely bound to the exact run and attempt")
        if (source["approvalHistoryVerified"] is not True
                or source["requiredReviewers"] != list(config.required_reviewers)
                or source["preventSelfReview"] is not True):
            raise ReceiptUnavailable("protected environment approval history/configuration is unavailable or mismatched")
        reviewer, builder, contributor = source["reviewer"], source["builder"], source["contributor"]
        if (not all(isinstance(actor, str) and actor.strip() for actor in (reviewer, builder, contributor))
                or reviewer.lower() in {builder.lower(), contributor.lower()}):
            raise ReceiptUnavailable("independent reviewer must differ from builder and contributor")
        if reviewer.lower() not in {name.lower() for name in config.required_reviewers}:
            raise ReceiptUnavailable("authenticated reviewer is not in the configured reviewer roster")
        if not SHA_RE.fullmatch(source["payloadDigest"]):
            raise ReceiptUnavailable("artifact complete-payload digest is invalid")

    @staticmethod
    def _verify_payload(payload: Mapping[str, Any], receipt: VerificationReceipt,
                        receipt_id: str, source: Mapping[str, Any]) -> None:
        transcript = payload.get("transcript")
        if not isinstance(transcript, str) or len(transcript.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
            raise ReceiptUnavailable("receipt transcript is absent or exceeds the safety limit")
        transcript_bytes = transcript.encode("utf-8")
        if payload.get("transcriptBytesSha256") != _sha(transcript_bytes):
            raise ReceiptUnavailable("raw transcript digest mismatch")
        if payload.get("contextDigest") != receipt.context_digest:
            raise ReceiptUnavailable("challenge context digest differs from immutable receipt")
        if payload.get("notificationRef") != receipt.notice_ref:
            raise ReceiptUnavailable("contributor notification does not match receipt")
        if not isinstance(payload.get("proofSourceSha"), str) or not SHA_RE.fullmatch(payload["proofSourceSha"]):
            raise ReceiptUnavailable("proof source SHA is absent or invalid")
        if (payload.get("receipt", {}).get("receipt_id") != receipt_id
                or not isinstance(payload.get("challengeId"), str) or not payload["challengeId"].strip()):
            raise ReceiptUnavailable("artifact is not bound to the requested receipt and challenge")
        if (receipt.verifier_id != source["reviewer"] or receipt.builder_id != source["builder"]
                or receipt.contributor_id != source["contributor"]):
            raise ReceiptUnavailable("receipt actor identities differ from authenticated source")
        if receipt.result.lower() not in {"pass", "passed", "verified"}:
            raise ReceiptUnavailable("independent technical verification did not pass")
        if receipt.verifier_id in {receipt.builder_id, receipt.contributor_id}:
            raise ReceiptUnavailable("receipt reviewer is not independent")


def probe_trusted_receipt_source(config: TrustedReceiptConfig | None = None) -> dict[str, Any]:
    """Return truthful deployment readiness without claiming live authorization."""
    if config is None:
        try:
            config = trusted_config_from_environment()
        except ReceiptUnavailable as exc:
            return {"status": "not-configured", "available": False, "reason": str(exc)}
    return {
        "status": "unavailable", "available": False,
        "reason": "no dispatch-only protected producer is active and GitHub REST does not expose "
                  "durable completed environment approval actor/history for independent verification",
        "configuredIssuer": config.issuer, "repository": config.repository,
        "workflowPath": config.workflow_path, "workflowRef": config.workflow_ref,
        "environment": config.environment,
    }
