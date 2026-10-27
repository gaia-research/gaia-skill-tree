"""Fail-closed GitHub Actions receipt proposal boundary for Yggdrasil IV.

This module packages complete technical proof for a protected producer workflow
(``.github/workflows/challenge-receipt-issuer.yml``) and resolves a receipt only when an
independently authenticated source adapter can prove every required fact.

Trust model (single operator, founder ruling 2026-10-28). GitHub's REST API does not
keep a durable, attributable environment-approval record, so the producer *seals* the
approvals it observed (``issuer-approval.json``) and attests the sealed file and the
receipt archive with ``actions/attest-build-provenance``. All post-approval work is inline
in the pinned workflow (no repository code runs after the click); the founder approves on
a summary the pinned workflow re-derives from the archive bytes. A verifier then proves,
with ``gh attestation verify`` against a Sigstore trusted root shipped in the package and
pinned by sha256 (a bundle never supplies its own root): (1) a GitHub-hosted runner signed
both files for a tag push in the trusted repository (repository and owner ids pinned);
(2) the workflow file at the signing commit is byte-identical (git blob SHA) to the pinned
``TrustedReceiptConfig.workflow_blob_sha`` and that commit is reachable from the
verifier's ``HEAD``; (3) exactly one ``approved`` review, by a configured reviewer user
id, none rejected, on attempt 1 (``_authenticate_approval``).

Authenticated facts are the approver, tag pusher, run, tag, commit and exact archive
bytes. Builder/contributor independence from the verifier is *declared* in the admission
request and is a convention, not an authenticated GitHub-side fact.
Two adapters share that core: ``GitHubActionsSource`` (online, at admission, additionally
cross-checks the live run, artifact and approvals) and ``CommittedAttestedReceiptSource``
(offline, every docs build, from the committed ``receipt/`` bundle).

Source boundary: the source document carries an ``approvalHistoryVerified`` boolean,
a reviewer name and a roster. Those values are only meaningful when produced by an
``AuthenticatedApprovalSource``, i.e. an adapter that itself authenticated the approver.
A boolean, name, id, URL, hash, ``decisionRef`` or ``eventId`` supplied by any other
party is never approval. The resolver therefore accepts only the exact adapter types in
``GitHubVerificationReceiptResolver.AUTHENTICATED_SOURCES``. Test ports live under
``tests/`` and must opt in explicitly by subclassing the resolver; they are never accepted
by the production class. The allowlist guards against accidental adapters and
misconfiguration, not hostile in-process code.

Steward plug point: ``AuthenticatedApprovalSource._authenticate_approval`` is the single
method that decides who approved. A future automated approver replaces only that method;
admission without the founder's click needs its own founder ruling.

Residual risks (see the issuer PR): credential equivalence (the operator's ``gh`` token can
approve through the API), squash merges break the commit-reachability check (fails closed),
and verification needs the ``gh`` CLI plus FULL git history (any CI that verifies committed
receipts must check out with ``fetch-depth: 0``).

Challenge binding: ``resolve()`` requires the expected challenge id. Callers should
use ``for_challenge()``, which returns a ``BoundReceiptResolver`` exposing the bound
``challenge_id``; ``challengeDomain`` derives the challenge id first and refuses any
resolver that cannot bind to it.

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
import shutil
import subprocess
import tempfile
import threading
import warnings
import zipfile
import zlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Mapping

from gaia_cli.challengeDomain import VerificationReceipt

MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 2 * 1024 * 1024
ARTIFACT_FILE = "verification-receipt.json"
ARTIFACT_COMPRESSION_TYPES = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
RECEIPT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# sha256 digests of bytes (optionally ``sha256:``-prefixed) are exactly 64 lowercase hex.
SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
# Git commit SHAs: 40 hex (SHA-1 object format, what GitHub reports today) or 64 hex
# (SHA-256 object format). Never prefixed.
GIT_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

# Issuer bundle: the three files the producer workflow emits and the repo commits under
# ``evidence/frontier-challenges/<case>/receipt/``.
BUNDLE_ARTIFACT = "artifact.zip"
BUNDLE_APPROVAL = "issuer-approval.json"
BUNDLE_ATTESTATION = "attestation.jsonl"
BUNDLE_LIMITS = {BUNDLE_ARTIFACT: MAX_ARCHIVE_BYTES, BUNDLE_APPROVAL: 1024 * 1024,
                 BUNDLE_ATTESTATION: 2 * 1024 * 1024}
MAX_BUNDLE_ZIP_BYTES = 20 * 1024 * 1024
EVIDENCE_ROOT = "evidence/frontier-challenges"
RECEIPT_SUBDIR = "receipt"
ARTIFACT_NAME_PREFIX = "challenge-receipt-"
SOURCE_LIVE = "github-actions-live"
SOURCE_COMMITTED = "committed-attested"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
SLSA_PREDICATE = "https://slsa.dev/provenance/v1"
TRUST_DIR = Path(__file__).resolve().parents[1] / "data" / "trust"
DEFAULT_CONFIG_PATH = TRUST_DIR / "challenge-receipt-issuer.json"
# Sigstore trusted root (``gh attestation trusted-root``), shipped in the package and pinned
# by ``TrustedReceiptConfig.trusted_root_sha256``. Bundles never carry their own root.
DEFAULT_TRUSTED_ROOT_PATH = TRUST_DIR / "sigstore-trusted-root.jsonl"


class ReceiptUnavailable(RuntimeError):
    """A required trusted source fact is absent, ambiguous, or unprovable."""


class ReceiptMisconfigured(ReceiptUnavailable):
    """Configuration exists but is incomplete, malformed, or inconsistent."""


@dataclass(frozen=True)
class TrustedReceiptConfig:
    """Deployment-owned allowlist; never deserialize this from challenge input.

    ``workflow_blob_sha`` pins the issuer workflow file by git blob SHA; the verified
    signing commit must carry exactly that blob. ``required_reviewer_ids`` are GitHub
    user ids (stable, unlike logins). ``repository_id`` / ``repository_owner_id`` pin the
    repository identity against rename or transfer. ``trusted_root_sha256`` pins the shipped
    Sigstore trusted root. ``prevent_self_review`` may be False: the single
    operator is both pusher and approver; the receipt verifier must still differ from the
    builder and contributor (enforced in the resolver).
    """

    repository: str
    workflow_path: str
    trigger_ref_prefix: str
    workflow_blob_sha: str
    environment: str
    required_reviewer_ids: tuple[int, ...]
    repository_id: int
    repository_owner_id: int
    trusted_root_sha256: str
    prevent_self_review: bool = False
    issuer: str = "github-actions"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise ValueError("trusted repository configuration is invalid")
        if (not self.workflow_path.startswith(".github/workflows/") or ".." in self.workflow_path
                or not self.workflow_path.endswith((".yml", ".yaml"))):
            raise ValueError("trusted workflow path must be a repository workflow path")
        if (not self.trigger_ref_prefix.startswith("refs/tags/") or not self.trigger_ref_prefix.endswith("/")
                or len(self.trigger_ref_prefix) <= len("refs/tags/") + 1):
            raise ValueError("trigger ref prefix must be a non-empty tag namespace such as refs/tags/name/")
        if not GIT_SHA_RE.fullmatch(self.workflow_blob_sha):
            raise ValueError("pinned workflow blob SHA must be a 40- or 64-hex git object id")
        if not self.environment:
            raise ValueError("protected environment is mandatory")
        ids = self.required_reviewer_ids
        if (not isinstance(ids, tuple) or not ids
                or not all(type(item) is int and item > 0 for item in ids)):
            raise ValueError("required reviewer ids must be a non-empty tuple of positive GitHub user ids")
        if (type(self.repository_id) is not int or self.repository_id <= 0
                or type(self.repository_owner_id) is not int or self.repository_owner_id <= 0):
            raise ValueError("repository id and owner id must be positive GitHub numeric ids")
        if not re.fullmatch(r"[0-9a-f]{64}", self.trusted_root_sha256):
            raise ValueError("trusted root sha256 must be 64 lowercase hex")
        if not isinstance(self.prevent_self_review, bool):
            raise ValueError("prevent_self_review must be a boolean")
        if self.issuer != "github-actions":
            raise ValueError("unsupported trusted receipt issuer")


# JSON key -> environment override. Environment values override the committed file per field.
CONFIG_ENV = {
    "repository": "GAIA_RECEIPT_REPOSITORY",
    "workflowPath": "GAIA_RECEIPT_WORKFLOW_PATH",
    "triggerRefPrefix": "GAIA_RECEIPT_TRIGGER_REF_PREFIX",
    "workflowBlobSha": "GAIA_RECEIPT_WORKFLOW_BLOB_SHA",
    "environment": "GAIA_RECEIPT_ENVIRONMENT",
    "requiredReviewerIds": "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS",
    "repositoryId": "GAIA_RECEIPT_REPOSITORY_ID",
    "repositoryOwnerId": "GAIA_RECEIPT_REPOSITORY_OWNER_ID",
    "trustedRootSha256": "GAIA_RECEIPT_TRUSTED_ROOT_SHA256",
    "preventSelfReview": "GAIA_RECEIPT_PREVENT_SELF_REVIEW",
}
CONFIG_KEYS = frozenset(CONFIG_ENV) | {"schemaVersion", "issuer"}


def loadTrustedConfig(env: Mapping[str, str] | None = None,
                      path: Path | str | None = DEFAULT_CONFIG_PATH) -> TrustedReceiptConfig:
    """Load the committed issuer config, overridden per field by ``GAIA_RECEIPT_*`` env.

    Neither a committed file nor any override => ``ReceiptUnavailable`` (not configured).
    A file or override that is incomplete, malformed or invalid => ``ReceiptMisconfigured``.
    Every override is a trust-root change: a ``RuntimeWarning`` names each override that
    alters a field the committed file already pins.
    """
    source = os.environ if env is None else env
    fields: dict[str, Any] = {}
    if path is not None and Path(path).is_file():
        try:
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ReceiptMisconfigured(f"challenge receipt config file is unreadable: {exc}") from exc
        if not isinstance(loaded, dict) or loaded.get("schemaVersion") != 1:
            raise ReceiptMisconfigured("challenge receipt config file must be an object with schemaVersion 1")
        unknown = sorted(set(loaded) - CONFIG_KEYS)
        if unknown:
            raise ReceiptMisconfigured(f"challenge receipt config has unknown keys: {', '.join(unknown)}")
        fields.update(loaded)
    overrides = {key: source[name] for key, name in CONFIG_ENV.items() if source.get(name)}
    if not fields and not overrides:
        raise ReceiptUnavailable(
            "trusted challenge receipt source is not configured; no committed "
            "challenge-receipt-issuer.json and no GAIA_RECEIPT_* deployment overrides")
    try:
        if "requiredReviewerIds" in overrides:
            overrides["requiredReviewerIds"] = [
                int(part) for part in overrides["requiredReviewerIds"].split(",") if part.strip()]
        for key in ("repositoryId", "repositoryOwnerId"):
            if key in overrides:
                overrides[key] = int(overrides[key])
        if "preventSelfReview" in overrides:
            flag = overrides["preventSelfReview"].strip().lower()
            if flag not in {"true", "false"}:
                raise ValueError("GAIA_RECEIPT_PREVENT_SELF_REVIEW must be true or false")
            overrides["preventSelfReview"] = flag == "true"
    except ValueError as exc:
        raise ReceiptMisconfigured(f"challenge receipt override is invalid: {exc}") from exc
    changed = sorted(CONFIG_ENV[key] for key, value in overrides.items()
                     if key in fields and fields[key] != value)
    if changed:
        warnings.warn("challenge receipt trust pins overridden by environment: " + ", ".join(changed)
                      + " (the committed pins are NOT in force)", RuntimeWarning, stacklevel=2)
    fields.update(overrides)
    missing = [key for key in ("repository", "workflowPath", "triggerRefPrefix", "workflowBlobSha",
                               "environment", "requiredReviewerIds", "repositoryId",
                               "repositoryOwnerId", "trustedRootSha256") if key not in fields]
    if missing:
        raise ReceiptMisconfigured(
            f"challenge receipt configuration is incomplete; missing {', '.join(missing)}")
    try:
        ids = fields["requiredReviewerIds"]
        if not isinstance(ids, list):
            raise ValueError("requiredReviewerIds must be a list of user ids")
        return TrustedReceiptConfig(
            fields["repository"], fields["workflowPath"], fields["triggerRefPrefix"],
            fields["workflowBlobSha"], fields["environment"], tuple(ids),
            fields["repositoryId"], fields["repositoryOwnerId"], fields["trustedRootSha256"],
            fields.get("preventSelfReview", False), fields.get("issuer", "github-actions"))
    except (TypeError, ValueError) as exc:
        raise ReceiptMisconfigured(f"trusted challenge receipt configuration is invalid: {exc}") from exc


def trusted_config_from_environment(env: Mapping[str, str] | None = None) -> TrustedReceiptConfig:
    """Environment-only deployment configuration; absence means not configured."""
    return loadTrustedConfig(env, path=None)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_matches(claimed: str, data: bytes) -> bool:
    """True only when ``claimed`` is a well-formed sha256 of exactly ``data``."""
    return (isinstance(claimed, str) and SHA256_RE.fullmatch(claimed) is not None
            and claimed.removeprefix("sha256:") == _sha(data))


def make_receipt_payload(receipt: VerificationReceipt, *, challenge_id: str,
                         context_digest: str, raw_transcript: bytes,
                         notification_ref: str, source_sha: str) -> dict[str, Any]:
    """Create the exact full artifact body; packaging is not authentication."""
    if not challenge_id.strip() or not SHA256_RE.fullmatch(context_digest):
        raise ValueError("challenge binding and SHA-256 context digest are required")
    if not GIT_SHA_RE.fullmatch(source_sha):
        raise ValueError("proof source SHA must be a 40- or 64-hex git commit SHA")
    if len(raw_transcript) > MAX_TRANSCRIPT_BYTES:
        raise ValueError("raw transcript exceeds the 2 MiB safety limit")
    if notification_ref != receipt.notice_ref:
        raise ValueError("notification reference must match the receipt")
    if receipt.context_digest != context_digest:
        raise ValueError("receipt context digest does not match challenge binding")
    if not _digest_matches(receipt.transcript_digest, raw_transcript):
        raise ValueError("receipt transcript digest does not match the packaged transcript")
    if not _digest_matches(receipt.output_digest, receipt.actual_output.encode("utf-8")):
        raise ValueError("receipt output digest does not match the actual output")
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
    if not isinstance(expected_payload_digest, str) or not SHA256_RE.fullmatch(expected_payload_digest):
        raise ReceiptUnavailable("trusted source did not provide an artifact payload digest")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            infos = bundle.infolist()
            if len(infos) != 1 or infos[0].filename != ARTIFACT_FILE:
                raise ValueError("archive must contain exactly the expected regular file")
            info = infos[0]
            if info.is_dir() or info.flag_bits & 0x1 or info.file_size > MAX_PAYLOAD_BYTES:
                raise ValueError("directory, encrypted, or oversized archive member")
            # Only stored/deflate members: bzip2 and lzma can inflate enormous
            # payloads internally before any chunk is returned, so the streaming
            # cap cannot bound them. Checked before the member is ever opened.
            if info.compress_type not in ARTIFACT_COMPRESSION_TYPES:
                raise ValueError("unsupported archive compression method")
            # No compression-ratio bound: the producer legitimately emits highly
            # repetitive transcripts. The bomb defense is a hard cap on bytes
            # actually inflated: zipfile does NOT stop at the (attacker-patchable)
            # header size, so we stream in chunks and refuse past the cap.
            chunks: list[bytes] = []
            total = 0
            with bundle.open(info) as stream:
                while True:
                    chunk = stream.read(min(65536, MAX_PAYLOAD_BYTES + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    chunks.append(chunk)
                    if total > MAX_PAYLOAD_BYTES:
                        raise ValueError("decompressed payload exceeds the 4 MiB cap")
            content = b"".join(chunks)
            if len(content) != info.file_size:
                raise ValueError("decompressed size differs from the declared member size")
    except (ValueError, KeyError, OSError, RuntimeError, EOFError, NotImplementedError,
            zlib.error, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise ReceiptUnavailable(f"invalid receipt artifact archive: {exc}") from exc
    if _sha(content) != expected_payload_digest.removeprefix("sha256:"):
        raise ReceiptUnavailable("receipt artifact complete-payload digest mismatch")
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReceiptUnavailable("receipt artifact payload is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ReceiptUnavailable("receipt artifact payload schema is unsupported")
    return payload


class AuthenticatedApprovalSource(ABC):
    """Marker base for adapters that authenticate approvals independently.

    Subclassing is necessary but not sufficient: the resolver also requires the
    exact type to be in its ``AUTHENTICATED_SOURCES`` allowlist. A source document's
    ``approvalHistoryVerified`` boolean is meaningful only from such an adapter.
    """

    @abstractmethod
    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]: ...

    def _authenticate_approval(self, run: Mapping[str, Any], items: Any,
                               config: TrustedReceiptConfig) -> dict[str, Any]:
        """Decide who approved. THE Steward plug point: override only this method.

        ``run`` is ``{"id", "attempt", "environment"}``; ``items`` is the GitHub
        ``/actions/runs/{id}/approvals`` list (live or sealed). Founder rule: exactly one
        ``approved`` review for ``config.environment``, by a configured reviewer user id,
        no ``rejected`` review, attempt 1. Self-review is permitted (single operator).
        Returns ``{"reviewer": login, "reviewerId": id}`` or raises ``ReceiptUnavailable``.
        """
        if type(run.get("attempt")) is not int or run["attempt"] != 1:
            raise ReceiptUnavailable("workflow run attempt must be 1; re-runs are never trusted")
        if not isinstance(items, list) or not items:
            raise ReceiptUnavailable("no environment approval record is present")
        approved: list[Mapping[str, Any]] = []
        for item in items:
            if not isinstance(item, Mapping):
                raise ReceiptUnavailable("approval record is malformed")
            if item.get("state") == "rejected":
                raise ReceiptUnavailable("a rejected environment review exists for this run")
            if item.get("state") != "approved":
                raise ReceiptUnavailable("approval record has an unrecognized state")
            approved.append(item)
        if len(approved) != 1:
            raise ReceiptUnavailable("exactly one approved environment review is required")
        item = approved[0]
        user = item.get("user")
        environments = item.get("environments")
        if not isinstance(user, Mapping) or type(user.get("id")) is not int or not isinstance(user.get("login"), str):
            raise ReceiptUnavailable("approval record has no authenticated reviewer identity")
        if not isinstance(environments, list) or config.environment not in {
                env.get("name") for env in environments if isinstance(env, Mapping)}:
            raise ReceiptUnavailable("approval was not recorded for the trusted protected environment")
        if user["id"] not in config.required_reviewer_ids or not user["login"].strip():
            raise ReceiptUnavailable("approving user is not in the configured reviewer roster")
        return {"reviewer": user["login"], "reviewerId": user["id"]}


# ---- Injectable collaborators (real defaults shell out to ``gh`` / ``git`` lazily) -----------

def identityFromGhResult(text: str, subjectSha256: str) -> dict[str, Any]:
    """Reduce ``gh attestation verify --format json`` to the signed workflow identity.

    ``gh`` has already checked the signature, trusted root and certificate chain; this
    only extracts the Fulcio certificate claims and requires the statement to name the
    subject digest. All returned attestations must agree.
    """
    try:
        results = json.loads(text)
    except ValueError as exc:
        raise ReceiptUnavailable(f"attestation verification output is not JSON: {exc}") from exc
    if not isinstance(results, list) or not results:
        raise ReceiptUnavailable("attestation verification returned no verified attestation")
    identities: list[dict[str, Any]] = []
    for entry in results:
        try:
            verification = entry["verificationResult"]
            cert = verification["signature"]["certificate"]
            statement = verification["statement"]
            subjects = {subject["digest"]["sha256"] for subject in statement["subject"]}
            if statement["predicateType"] != SLSA_PREDICATE or subjectSha256 not in subjects:
                raise ReceiptUnavailable("attestation statement does not name this exact subject digest")
            if cert["issuer"] != OIDC_ISSUER:
                raise ReceiptUnavailable("attestation certificate was not issued to GitHub Actions OIDC")
            repoUri, signer = cert["sourceRepositoryURI"], cert["buildSignerURI"]
            if not repoUri.startswith("https://github.com/") or not signer.startswith(repoUri + "/"):
                raise ReceiptUnavailable("attestation signer is not a workflow of the source repository")
            repository = repoUri.removeprefix("https://github.com/")
            workflowPath, _, signerRef = signer.removeprefix(repoUri + "/").rpartition("@")
            invocation = re.fullmatch(
                re.escape(repoUri) + r"/actions/runs/([0-9]+)/attempts/([0-9]+)", cert["runInvocationURI"])
            if (not invocation or cert["buildSignerDigest"] != cert["sourceRepositoryDigest"]
                    or signerRef != cert["sourceRepositoryRef"]
                    or cert["buildTrigger"] != cert["githubWorkflowTrigger"]):
                raise ReceiptUnavailable("attestation certificate claims are internally inconsistent")
            identities.append({
                "repository": repository, "workflowPath": workflowPath,
                "ref": cert["sourceRepositoryRef"], "sourceSha": cert["sourceRepositoryDigest"],
                "trigger": cert["buildTrigger"], "runnerEnvironment": cert["runnerEnvironment"],
                "runId": int(invocation.group(1)), "runAttempt": int(invocation.group(2)),
                "repositoryId": int(cert["sourceRepositoryIdentifier"]),
                "ownerId": int(cert["sourceRepositoryOwnerIdentifier"]),
                "subjectSha256": subjectSha256,
            })
        except ReceiptUnavailable:
            raise
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            raise ReceiptUnavailable(f"attestation verification output has an unexpected shape: {exc!r}") from exc
    if any(identity != identities[0] for identity in identities):
        raise ReceiptUnavailable("verified attestations disagree about the signing identity")
    return identities[0]


class GhAttestationVerifier:
    """Verify a subject against a bundle with ``gh attestation verify`` (offline-capable)."""

    def __init__(self, ghPath: str = "gh", *, runner: Callable[..., Any] = subprocess.run,
                 timeout: float = 120.0) -> None:
        self.ghPath, self.runner, self.timeout = ghPath, runner, timeout

    def __call__(self, subject: Path, bundle: Path, trustedRoot: Path | None,
                 config: TrustedReceiptConfig) -> dict[str, Any]:
        command = [self.ghPath, "attestation", "verify", str(subject), "--repo", config.repository,
                   "--bundle", str(bundle), "--signer-workflow", f"{config.repository}/{config.workflow_path}",
                   "--deny-self-hosted-runners", "--format", "json"]
        if trustedRoot is not None:
            command += ["--custom-trusted-root", str(trustedRoot)]
        try:
            done = self.runner(command, capture_output=True, text=True, timeout=self.timeout, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ReceiptUnavailable(f"gh CLI is required to verify attestations: {exc}") from exc
        if done.returncode != 0:
            raise ReceiptUnavailable(f"attestation verification failed: {str(done.stderr).strip()[:300]}")
        digest = hashlib.sha256(Path(subject).read_bytes()).hexdigest()
        return identityFromGhResult(done.stdout, digest)


class LocalGit:
    """Blob and ancestry facts from a local checkout; needs the full history."""

    def __init__(self, repoRoot: Path | str | None = None, *, runner: Callable[..., Any] = subprocess.run) -> None:
        self.repoRoot = Path.cwd() if repoRoot is None else Path(repoRoot)
        self.runner = runner

    def _git(self, *args: str) -> Any:
        try:
            return self.runner(["git", "-C", str(self.repoRoot), *args], capture_output=True, text=True,
                               timeout=60, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ReceiptUnavailable(f"git is required to verify the pinned workflow: {exc}") from exc

    def blobShaAt(self, commit: str, path: str) -> str | None:
        if not GIT_SHA_RE.fullmatch(commit):
            return None
        done = self._git("rev-parse", "--verify", "--quiet", f"{commit}:{path}")
        out = str(done.stdout).strip()
        return out if done.returncode == 0 and GIT_SHA_RE.fullmatch(out) else None

    def isAncestor(self, commit: str, head: str = "HEAD") -> bool:
        return GIT_SHA_RE.fullmatch(commit) is not None and self._git(
            "merge-base", "--is-ancestor", commit, head).returncode == 0


class GhApiTransport:
    """Read-only ``gh api`` transport; ``gh`` handles auth and artifact download redirects.

    Output is read in chunks and the process is killed the moment it exceeds the byte cap,
    so an oversized response is never fully buffered.
    """

    JSON_LIMIT = 4 * 1024 * 1024

    def __init__(self, token: str | None = None, *, timeout: float = 60.0, ghPath: str = "gh",
                 popen: Callable[..., Any] = subprocess.Popen) -> None:
        self.token, self.timeout, self.ghPath, self.popen = token, timeout, ghPath, popen

    def _call(self, path: str, limit: int) -> bytes:
        env = dict(os.environ)
        if self.token:
            env["GH_TOKEN"] = self.token
        with tempfile.TemporaryFile() as errors:
            try:
                proc = self.popen([self.ghPath, "api", path], stdout=subprocess.PIPE, stderr=errors, env=env)
            except OSError as exc:
                raise ReceiptUnavailable(f"gh CLI is required to read GitHub Actions state: {exc}") from exc
            timer = threading.Timer(self.timeout, proc.kill)
            timer.start()
            chunks: list[bytes] = []
            total = 0
            try:
                while True:
                    chunk = proc.stdout.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit:
                        proc.kill()
                        raise ReceiptUnavailable(f"GitHub API response for {path} exceeds the size limit")
                    chunks.append(chunk)
                code = proc.wait()
            finally:
                timer.cancel()
                proc.stdout.close()
            if code != 0:
                errors.seek(0)
                detail = errors.read(400).decode("utf-8", "replace").strip()
                raise ReceiptUnavailable(f"GitHub API read failed for {path}: {detail[:200]}")
        return b"".join(chunks)

    def getJson(self, path: str) -> Any:
        try:
            return json.loads(self._call(path, self.JSON_LIMIT))
        except ValueError as exc:
            raise ReceiptUnavailable(f"GitHub API returned non-JSON for {path}") from exc

    def getBytes(self, path: str) -> bytes:
        return self._call(path, MAX_BUNDLE_ZIP_BYTES)


# ---- Bundle parsing ---------------------------------------------------------------------------

def _readBundleZip(data: bytes) -> dict[str, bytes]:
    """Parse a downloaded Actions artifact: exactly the three bundle files, hard byte caps."""
    if not isinstance(data, bytes) or len(data) > MAX_BUNDLE_ZIP_BYTES:
        raise ReceiptUnavailable("receipt bundle download is absent or too large")
    files: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as bundle:
            infos = bundle.infolist()
            if sorted(info.filename for info in infos) != sorted(BUNDLE_LIMITS):
                raise ValueError("bundle must contain exactly the three issuer files")
            for info in infos:
                cap = BUNDLE_LIMITS[info.filename]
                if (info.is_dir() or info.flag_bits & 0x1 or info.file_size > cap
                        or info.compress_type not in ARTIFACT_COMPRESSION_TYPES):
                    raise ValueError(f"unsafe bundle member {info.filename}")
                with bundle.open(info) as stream:
                    content = stream.read(cap + 1)
                if len(content) > cap or len(content) != info.file_size:
                    raise ValueError(f"bundle member {info.filename} violates its size cap")
                files[info.filename] = content
    except (ValueError, KeyError, OSError, RuntimeError, EOFError, NotImplementedError,
            zlib.error, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise ReceiptUnavailable(f"invalid receipt bundle: {exc}") from exc
    return files


def _readBundleDir(directory: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for name, cap in BUNDLE_LIMITS.items():
        path = directory / name
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
                raise ReceiptUnavailable(f"committed receipt file {name} is missing, linked, or oversized")
            files[name] = path.read_bytes()
        except OSError as exc:
            raise ReceiptUnavailable(f"committed receipt file {name} is unreadable: {exc}") from exc
    return files


def _json(data: bytes, what: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReceiptUnavailable(f"{what} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ReceiptUnavailable(f"{what} must be a JSON object")
    return value


class _BundleSource(AuthenticatedApprovalSource):
    """Shared core: attestation, pinned-workflow and sealed-approval verification."""

    def __init__(self, *, verifier: Callable[..., Mapping[str, Any]] | None = None,
                 git: Any = None, trustedRoot: Path | str = DEFAULT_TRUSTED_ROOT_PATH) -> None:
        self.verifier = GhAttestationVerifier() if verifier is None else verifier
        self.git = git
        self.trustedRoot = Path(trustedRoot)

    def _pinnedRoot(self, config: TrustedReceiptConfig) -> bytes:
        """The packaged Sigstore root, accepted only if it matches the pinned digest."""
        try:
            data = self.trustedRoot.read_bytes()
        except OSError as exc:
            raise ReceiptUnavailable(f"pinned Sigstore trusted root is unreadable: {exc}") from exc
        if _sha(data) != config.trusted_root_sha256:
            raise ReceiptUnavailable("Sigstore trusted root does not match the pinned sha256")
        return data

    def _history(self) -> Any:
        return LocalGit() if self.git is None else self.git

    def _authenticateBundle(self, files: Mapping[str, bytes], receipt_id: str,
                            config: TrustedReceiptConfig) -> dict[str, Any]:
        sealed = _json(files[BUNDLE_APPROVAL], "issuer approval")
        archive = files[BUNDLE_ARTIFACT]
        identities = []
        pinnedRoot = self._pinnedRoot(config)
        with tempfile.TemporaryDirectory(prefix="gaia-receipt-") as tmp:
            root = Path(tmp)
            for name, content in files.items():
                (root / name).write_bytes(content)
            (root / "pinned-trusted-root.jsonl").write_bytes(pinnedRoot)
            for name in (BUNDLE_ARTIFACT, BUNDLE_APPROVAL):
                identity = self.verifier(root / name, root / BUNDLE_ATTESTATION,
                                         root / "pinned-trusted-root.jsonl", config)
                if (not isinstance(identity, Mapping)
                        or identity.get("subjectSha256") != _sha(files[name])):
                    raise ReceiptUnavailable("attestation does not cover the exact bundle file bytes")
                identities.append(dict(identity))
        identity = identities[0]
        if any({k: v for k, v in other.items() if k != "subjectSha256"}
               != {k: v for k, v in identity.items() if k != "subjectSha256"} for other in identities):
            raise ReceiptUnavailable("receipt archive and approval were not signed by the same run")
        if (identity.get("repository") != config.repository
                or identity.get("workflowPath") != config.workflow_path
                or identity.get("repositoryId") != config.repository_id
                or identity.get("ownerId") != config.repository_owner_id):
            raise ReceiptUnavailable("attested workflow is not the trusted issuer workflow")
        ref, sha = identity.get("ref"), identity.get("sourceSha")
        if not isinstance(ref, str) or not ref.startswith(config.trigger_ref_prefix):
            raise ReceiptUnavailable("attested ref is outside the trusted challenge-receipt tag namespace")
        if identity.get("trigger") != "push" or identity.get("runnerEnvironment") != "github-hosted":
            raise ReceiptUnavailable("attestation was not produced by a push-triggered GitHub-hosted run")
        runId, attempt = identity.get("runId"), identity.get("runAttempt")
        if type(runId) is not int or runId <= 0 or type(attempt) is not int or attempt != 1:
            raise ReceiptUnavailable("attested run identity is invalid or not attempt 1")
        if not isinstance(sha, str) or not GIT_SHA_RE.fullmatch(sha):
            raise ReceiptUnavailable("attested source commit is invalid")
        history = self._history()
        blob = history.blobShaAt(sha, config.workflow_path)
        if blob is None:
            raise ReceiptUnavailable(
                "attested source commit is not in local history (full history required; a squash "
                "merge orphans it and fails closed)")
        if blob != config.workflow_blob_sha:
            raise ReceiptUnavailable("issuer workflow at the attested commit does not match the pinned blob SHA")
        if not history.isAncestor(sha):
            raise ReceiptUnavailable("attested source commit is not reachable from HEAD")
        if (sealed.get("schemaVersion") != 1 or sealed.get("kind") != "challenge-receipt-issuer-approval"
                or sealed.get("repository") != config.repository
                or sealed.get("repositoryId") != config.repository_id
                or sealed.get("ownerId") != config.repository_owner_id
                or sealed.get("environment") != config.environment
                or sealed.get("runId") != runId or sealed.get("runAttempt") != attempt
                or sealed.get("ref") != ref or sealed.get("sourceSha") != sha
                or sealed.get("receiptId") != receipt_id
                or sealed.get("artifactSha256") != _sha(archive)):
            raise ReceiptUnavailable("sealed approval does not bind this exact run, ref, receipt and artifact")
        payloadDigest, builder, contributor = (sealed.get("payloadDigest"), sealed.get("builder"),
                                               sealed.get("contributor"))
        if not isinstance(payloadDigest, str) or not SHA256_RE.fullmatch(payloadDigest):
            raise ReceiptUnavailable("sealed approval payload digest is invalid")
        approval = self._authenticate_approval(
            {"id": runId, "attempt": attempt, "environment": config.environment},
            sealed.get("approvals"), config)
        return {
            "repository": config.repository, "workflowPath": config.workflow_path,
            "workflowRef": ref, "workflowSha": sha, "workflowBlobSha": blob,
            "environment": config.environment, "runId": runId, "runAttempt": attempt,
            "builder": builder, "contributor": contributor,
            "reviewer": approval["reviewer"], "reviewerId": approval["reviewerId"],
            "requiredReviewerIds": list(config.required_reviewer_ids),
            "preventSelfReview": config.prevent_self_review, "approvalHistoryVerified": True,
            "payloadDigest": payloadDigest, "archive": archive,
            "sealedChallengeId": sealed.get("challengeId"),
        }


class GitHubActionsSource(_BundleSource):
    """Online adapter, used at admission: live run, artifact and approvals + attestation.

    Everything is read through the injectable ``transport`` (default: ``gh api``); the
    attestation is verified against the same pinned packaged Sigstore root. The
    sealed approval inside the attested bundle must agree with the live approvals.
    """

    def __init__(self, token: str | None = None, *, timeout: float = 60.0, transport: Any = None,
                 verifier: Callable[..., Mapping[str, Any]] | None = None, git: Any = None,
                 trustedRoot: Path | str = DEFAULT_TRUSTED_ROOT_PATH) -> None:
        super().__init__(verifier=verifier, git=git, trustedRoot=trustedRoot)
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.transport = GhApiTransport(self.token, timeout=timeout) if transport is None else transport

    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]:
        repo, name = config.repository, ARTIFACT_NAME_PREFIX + receipt_id
        listing = self.transport.getJson(f"repos/{repo}/actions/artifacts?name={name}&per_page=100")
        artifacts = listing.get("artifacts") if isinstance(listing, Mapping) else None
        if (not isinstance(artifacts, list) or len(artifacts) != 1
                or listing.get("total_count") != 1 or not isinstance(artifacts[0], Mapping)):
            raise ReceiptUnavailable("receipt artifact is absent or ambiguous (exactly one is required)")
        artifact = artifacts[0]
        workflowRun = artifact.get("workflow_run")
        if (artifact.get("name") != name or type(artifact.get("id")) is not int
                or not isinstance(workflowRun, Mapping) or type(workflowRun.get("id")) is not int):
            raise ReceiptUnavailable("receipt artifact listing is malformed")
        runId = workflowRun["id"]
        run = self.transport.getJson(f"repos/{repo}/actions/runs/{runId}")
        approvals = self.transport.getJson(f"repos/{repo}/actions/runs/{runId}/approvals")
        data = self.transport.getBytes(f"repos/{repo}/actions/artifacts/{artifact['id']}/zip")
        document = self._authenticateBundle(_readBundleZip(data), receipt_id, config)
        if not isinstance(run, Mapping):
            raise ReceiptUnavailable("live workflow run is malformed")
        def repoOf(key: str) -> Any:
            value = run.get(key)
            return value.get("full_name") if isinstance(value, Mapping) else None

        if (run.get("id") != runId or run.get("run_attempt") != document["runAttempt"]
                or str(run.get("path", "")).split("@")[0] != config.workflow_path
                or run.get("event") != "push" or run.get("head_sha") != document["workflowSha"]
                or "refs/tags/" + str(run.get("head_branch")) != document["workflowRef"]
                or repoOf("repository") != config.repository
                or repoOf("head_repository") != config.repository):
            raise ReceiptUnavailable("live workflow run does not match the attested run")
        live = self._authenticate_approval(
            {"id": runId, "attempt": run["run_attempt"], "environment": config.environment},
            approvals, config)
        if live != {"reviewer": document["reviewer"], "reviewerId": document["reviewerId"]}:
            raise ReceiptUnavailable("live approvals disagree with the sealed approval")
        document.update({
            "sourceKind": SOURCE_LIVE, "runStatus": run.get("status"), "runConclusion": run.get("conclusion"),
            "artifactId": artifact["id"], "artifactName": artifact["name"],
            "artifactExpired": artifact.get("expired"), "artifactRunId": runId,
            "artifactAttempt": document["runAttempt"], "artifactCount": 1,
        })
        return document


class CommittedAttestedReceiptSource(_BundleSource):
    """Offline adapter, used by every docs build: verifies the committed ``receipt/`` bundle.

    The sealed approval is the durable approval proof (GitHub's own record has unknown
    retention); it is trusted only because the pinned workflow signed it.
    """

    def __init__(self, repo_root: Path | str, *, verifier: Callable[..., Mapping[str, Any]] | None = None,
                 git: Any = None, trustedRoot: Path | str = DEFAULT_TRUSTED_ROOT_PATH) -> None:
        self.repoRoot = Path(repo_root)
        super().__init__(verifier=verifier, git=LocalGit(self.repoRoot) if git is None else git,
                         trustedRoot=trustedRoot)

    def fetch(self, receipt_id: str, config: TrustedReceiptConfig) -> Mapping[str, Any]:
        base = self.repoRoot / EVIDENCE_ROOT
        matches = []
        for candidate in sorted(base.glob(f"*/{RECEIPT_SUBDIR}")) if base.is_dir() else []:
            approval = candidate / BUNDLE_APPROVAL
            if candidate.is_symlink() or not candidate.is_dir() or approval.is_symlink() or not approval.is_file():
                continue
            try:
                if approval.stat().st_size <= BUNDLE_LIMITS[BUNDLE_APPROVAL] and _json(
                        approval.read_bytes(), "issuer approval").get("receiptId") == receipt_id:
                    matches.append(candidate)
            except (OSError, ReceiptUnavailable):
                continue
        if len(matches) > 1:
            raise ReceiptUnavailable(
                "committed receipt bundle is ambiguous: receipt id " + repr(receipt_id) + " is sealed in "
                + ", ".join(sorted(path.parent.name for path in matches)) + " (exactly one is required)")
        if not matches:
            raise ReceiptUnavailable("committed receipt bundle is absent (exactly one is required)")
        document = self._authenticateBundle(_readBundleDir(matches[0]), receipt_id, config)
        document["sourceKind"] = SOURCE_COMMITTED
        return document


class GitHubVerificationReceiptResolver:
    """Resolve immutable receipts only after source provenance and artifact checks."""

    # Exact-type allowlist of adapters trusted to authenticate approval: the online
    # GitHub Actions adapter and the offline committed-attestation adapter. Tests opt in
    # by subclassing and overriding this attribute with their visibly synthetic port.
    AUTHENTICATED_SOURCES: tuple[type, ...] = (GitHubActionsSource, CommittedAttestedReceiptSource)

    def __init__(self, config: TrustedReceiptConfig | None = None,
                 source: AuthenticatedApprovalSource | None = None) -> None:
        self.config = config
        self.source = GitHubActionsSource() if source is None else source

    def for_challenge(self, challenge_id: str, proof_source_sha: str | None = None
                      ) -> "BoundReceiptResolver":
        """Bind expected challenge context so this satisfies the one-argument
        ``VerificationReceiptResolver`` protocol without dropping the binding."""
        return BoundReceiptResolver(self, challenge_id, proof_source_sha)

    def resolve(self, receipt_id: str, *, expected_challenge_id: str,
                expected_proof_source_sha: str | None = None) -> VerificationReceipt:
        try:
            return self._resolve(receipt_id, expected_challenge_id, expected_proof_source_sha)
        except ReceiptUnavailable:
            raise
        except Exception as exc:  # fail closed on any malformed source/artifact shape
            raise ReceiptUnavailable(
                f"receipt resolution failed closed: {type(exc).__name__}: {exc}") from exc

    def _resolve(self, receipt_id: str, expected_challenge_id: str,
                 expected_proof_source_sha: str | None) -> VerificationReceipt:
        if not isinstance(receipt_id, str) or not RECEIPT_ID_RE.fullmatch(receipt_id):
            raise ReceiptUnavailable("receipt id is invalid")
        if not isinstance(expected_challenge_id, str) or not expected_challenge_id.strip():
            raise ReceiptUnavailable("expected challenge id is required")
        if expected_proof_source_sha is not None and not (
                isinstance(expected_proof_source_sha, str)
                and GIT_SHA_RE.fullmatch(expected_proof_source_sha)):
            raise ReceiptUnavailable("expected proof source SHA is invalid")
        config = self.config
        if config is None:
            raise ReceiptUnavailable("trusted challenge receipt source is not configured")
        if (type(self.source) not in self.AUTHENTICATED_SOURCES
                or not isinstance(self.source, AuthenticatedApprovalSource)):
            raise ReceiptUnavailable(
                "receipt source is not an allowlisted authenticated approval source")
        source = self.source.fetch(receipt_id, config)
        if not isinstance(source, Mapping):
            raise ReceiptUnavailable("trusted source returned no provenance document")
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
        if payload["challengeId"] != expected_challenge_id:
            raise ReceiptUnavailable("receipt challenge id does not match the expected challenge")
        if (expected_proof_source_sha is not None
                and payload["proofSourceSha"] != expected_proof_source_sha):
            raise ReceiptUnavailable("receipt proof source SHA does not match the expected source")
        return receipt

    @staticmethod
    def _verify_source(source: Mapping[str, Any], receipt_id: str,
                       config: TrustedReceiptConfig) -> None:
        required = {"sourceKind", "repository", "workflowPath", "workflowRef", "workflowSha",
                    "workflowBlobSha", "environment", "runId", "runAttempt", "builder",
                    "contributor", "reviewer", "reviewerId", "requiredReviewerIds",
                    "preventSelfReview", "approvalHistoryVerified", "payloadDigest", "archive"}
        if not required.issubset(source):
            raise ReceiptUnavailable("trusted Actions provenance is incomplete")
        kind = source["sourceKind"]
        if kind not in (SOURCE_LIVE, SOURCE_COMMITTED):
            raise ReceiptUnavailable("trusted source kind is not recognized")
        workflowRef = source["workflowRef"]
        if (source["repository"] != config.repository or source["workflowPath"] != config.workflow_path
                or source["environment"] != config.environment
                or not isinstance(workflowRef, str) or not workflowRef.startswith(config.trigger_ref_prefix)
                or source["workflowBlobSha"] != config.workflow_blob_sha
                or not isinstance(source["workflowSha"], str) or not GIT_SHA_RE.fullmatch(source["workflowSha"])):
            raise ReceiptUnavailable("workflow source or protected environment does not match trusted configuration")
        run_id, attempt = source["runId"], source["runAttempt"]
        if type(run_id) is not int or run_id <= 0 or type(attempt) is not int or attempt != 1:
            raise ReceiptUnavailable("workflow run/attempt identity is invalid or not attempt 1")
        if kind == SOURCE_LIVE:
            live = {"runStatus", "runConclusion", "artifactId", "artifactName", "artifactExpired",
                    "artifactRunId", "artifactAttempt", "artifactCount"}
            if not live.issubset(source):
                raise ReceiptUnavailable("trusted Actions provenance is incomplete")
            if source["runStatus"] != "completed" or source["runConclusion"] != "success":
                raise ReceiptUnavailable("workflow run did not complete successfully")
            if (source["artifactExpired"] is not False or type(source["artifactCount"]) is not int
                    or source["artifactCount"] != 1):
                raise ReceiptUnavailable("receipt artifact is expired or ambiguous/duplicated")
            if (source["artifactName"] != ARTIFACT_NAME_PREFIX + receipt_id
                    or type(source["artifactRunId"]) is not int or source["artifactRunId"] != run_id
                    or type(source["artifactAttempt"]) is not int or source["artifactAttempt"] != attempt
                    or type(source["artifactId"]) is not int):
                raise ReceiptUnavailable("artifact is not uniquely bound to the exact run and attempt")
        if (source["approvalHistoryVerified"] is not True
                or source["requiredReviewerIds"] != list(config.required_reviewer_ids)
                or source["preventSelfReview"] is not config.prevent_self_review):
            raise ReceiptUnavailable("protected environment approval history/configuration is unavailable or mismatched")
        if type(source["reviewerId"]) is not int or source["reviewerId"] not in config.required_reviewer_ids:
            raise ReceiptUnavailable("authenticated reviewer is not in the configured reviewer roster")
        reviewer, builder, contributor = source["reviewer"], source["builder"], source["contributor"]
        if (not all(isinstance(actor, str) and actor.strip() for actor in (reviewer, builder, contributor))
                or reviewer.lower() in {builder.lower(), contributor.lower()}):
            raise ReceiptUnavailable("independent reviewer must differ from builder and contributor")
        if (not isinstance(source["payloadDigest"], str)
                or not SHA256_RE.fullmatch(source["payloadDigest"])):
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
        sealedChallenge = source.get("sealedChallengeId")
        if sealedChallenge is not None and payload.get("challengeId") != sealedChallenge:
            raise ReceiptUnavailable("sealed approval challenge id differs from the receipt artifact")
        if not isinstance(payload.get("proofSourceSha"), str) or not GIT_SHA_RE.fullmatch(payload["proofSourceSha"]):
            raise ReceiptUnavailable("proof source SHA is absent or invalid")
        if (payload.get("receipt", {}).get("receipt_id") != receipt_id
                or not isinstance(payload.get("challengeId"), str) or not payload["challengeId"].strip()):
            raise ReceiptUnavailable("artifact is not bound to the requested receipt and challenge")
        if (receipt.verifier_id != source["reviewer"] or receipt.builder_id != source["builder"]
                or receipt.contributor_id != source["contributor"]):
            raise ReceiptUnavailable("receipt actor identities differ from authenticated source")
        if not _digest_matches(receipt.transcript_digest, transcript_bytes):
            raise ReceiptUnavailable("receipt transcript digest is not bound to the packaged transcript")
        if not _digest_matches(receipt.output_digest, receipt.actual_output.encode("utf-8")):
            raise ReceiptUnavailable("receipt output digest is not bound to the actual output")
        if receipt.result.lower() not in {"pass", "passed", "verified"}:
            raise ReceiptUnavailable("independent technical verification did not pass")
        if receipt.verifier_id in {receipt.builder_id, receipt.contributor_id}:
            raise ReceiptUnavailable("receipt reviewer is not independent")


class BoundReceiptResolver:
    """One-argument resolver (``VerificationReceiptResolver``) bound to a challenge."""

    def __init__(self, resolver: GitHubVerificationReceiptResolver, challenge_id: str,
                 proof_source_sha: str | None = None) -> None:
        self._resolver = resolver
        self.challenge_id = challenge_id
        self._challenge_id = challenge_id
        self._proof_source_sha = proof_source_sha

    def resolve(self, receipt_id: str) -> VerificationReceipt:
        return self._resolver.resolve(
            receipt_id, expected_challenge_id=self._challenge_id,
            expected_proof_source_sha=self._proof_source_sha)


def probe_trusted_receipt_source(
        config: TrustedReceiptConfig | None = None, *, repoRoot: Path | str | None = None,
        env: Mapping[str, str] | None = None, configPath: Path | str | None = DEFAULT_CONFIG_PATH,
        which: Callable[[str], str | None] = shutil.which,
        runner: Callable[..., Any] = subprocess.run,
        trustedRoot: Path | str = DEFAULT_TRUSTED_ROOT_PATH) -> dict[str, Any]:
    """Return truthful deployment readiness. Never claims that anything was admitted.

    ``not-configured`` (nothing configured) | ``misconfigured`` (config invalid, workflow
    pin drifted from the checkout, or ``gh`` missing) | ``offline-only`` (``gh`` present, no
    GitHub credential: committed bundles verify, live admission cannot) | ``available``
    (live admission and offline verification are both possible). ``available`` means tooling
    only: every report carries ``admitted: False``; admission is decided per challenge by the
    resolver, never by this probe. ``envOverrides`` lists any GAIA_RECEIPT_* trust-pin overrides.
    """
    if config is None:
        try:
            config = loadTrustedConfig(env, configPath)
        except ReceiptMisconfigured as exc:
            return {"status": "misconfigured", "available": False, "admitted": False, "reason": str(exc)}
        except ReceiptUnavailable as exc:
            return {"status": "not-configured", "available": False, "admitted": False, "reason": str(exc)}
    source = os.environ if env is None else env
    report: dict[str, Any] = {
        "available": False, "admitted": False, "admission": "not-evaluated",
        "envOverrides": sorted(name for name in CONFIG_ENV.values() if source.get(name)),
        "configuredIssuer": config.issuer, "repository": config.repository,
        "workflowPath": config.workflow_path, "triggerRefPrefix": config.trigger_ref_prefix,
        "environment": config.environment, "workflowBlobSha": config.workflow_blob_sha,
    }
    try:
        rootOk = _sha(Path(trustedRoot).read_bytes()) == config.trusted_root_sha256
    except OSError:
        rootOk = False
    if not rootOk:
        return {**report, "status": "misconfigured",
                "reason": "packaged Sigstore trusted root is missing or does not match the pinned sha256"}
    if repoRoot is not None:
        workflow = Path(repoRoot) / config.workflow_path
        if not workflow.is_file():
            return {**report, "status": "misconfigured",
                    "reason": f"pinned workflow {config.workflow_path} is missing from the checkout"}
        try:
            done = runner(["git", "-C", str(repoRoot), "hash-object", "--", str(workflow)],
                          capture_output=True, text=True, timeout=30, check=False)
            actual = str(done.stdout).strip() if done.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            actual = None
        if actual != config.workflow_blob_sha:
            return {**report, "status": "misconfigured",
                    "reason": "pinned workflow blob SHA does not match the checked-out workflow file"}
    if not which("gh"):
        return {**report, "status": "misconfigured",
                "reason": "gh CLI not found; attestation verification requires it"}
    authed = bool(source.get("GH_TOKEN") or source.get("GITHUB_TOKEN"))
    if not authed:
        try:
            authed = runner(["gh", "auth", "token"], capture_output=True, text=True, timeout=30,
                            check=False).returncode == 0
        except (OSError, subprocess.SubprocessError):
            authed = False
    if not authed:
        return {**report, "status": "offline-only",
                "reason": "no GitHub credential: committed receipt bundles can be verified, "
                          "live admission cannot"}
    return {**report, "status": "available", "available": True,
            "reason": "tooling and credentials are present; this says nothing about any challenge "
                      "(nothing is admitted until the resolver verifies that challenge's receipt)"}
