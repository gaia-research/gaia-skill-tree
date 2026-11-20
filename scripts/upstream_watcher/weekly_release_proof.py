"""Pure offline fixture-only release evidence proof classifier (Hydrogen L2).

This module classifies explicit detached fixture observations from a future
sealed collector without performing any network, transport, subprocess,
filesystem, or import-time I/O. It never wraps default network readers, never
imports ``LiveGh``, and never mutates ``CollectedPoll``, watcher, reducer,
census, or persisted journal schemas.

Future sealed transport authenticity requirements
-------------------------------------------------
Fixtures supplied to this classifier are evidence-shape proof only. Before
any live/hosted collector may feed observations into this classifier, the
transport layer must independently establish:

1. TLS-verified HTTPS connection to ``api.github.com`` (no custom host/port).
2. ``NoRedirect`` enforcement (HTTP ``3xx`` responses are never followed).
3. Unmodified HTTP status code, headers, and bounded JSON body bound to the
   exact requested endpoint URL and repository identity.
4. Strict JSON decoding (no duplicate object keys or non-finite constants).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

from scripts.lib.github_api import (
    PERMANENT_REFUSAL_RE,
    PERMANENT_UNAVAILABLE_STATUSES,
    PERMISSION_PROBLEM_RE,
)
from scripts.upstream_watcher import envelope, weekly_reducer
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.finder import resolve_suite_source
from scripts.upstream_watcher.live import GhError, UnknownEvidenceError
from scripts.upstream_watcher.releaseidentity import validateReleaseSource

_TAG_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}\Z")
_MAX_NAMED_ID_LEN = 256

TRANSPORT_AUTHENTICITY_REQUIREMENTS: tuple[str, ...] = (
    "tls-verified-api.github.com",
    "no-redirect-3xx-never-followed",
    "exact-request-url-and-repository-binding",
    "strict-bounded-json-no-duplicate-keys",
)


@dataclass(frozen=True)
class ReleaseHttpObservation:
    """Detached fixture observation for ``GET /repos/{owner}/{repo}/releases/latest``."""

    requested_url: str
    requested_repository: str
    status_code: int
    redirected: bool = False
    body: Mapping[str, Any] | None = None
    headers: Mapping[str, str] | None = None


@dataclass(frozen=True)
class RepoMetadataObservation:
    """Detached fixture observation for ``GET /repos/{owner}/{repo}``."""

    requested_url: str
    requested_repository: str
    status_code: int
    redirected: bool = False
    body: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ReleaseProofResult:
    """Small sanitized release-evidence classification; never carries raw bodies."""

    named_id: str
    repository: str | None
    status: str  # "observed" | "no-visible-latest-release" | "unavailable" | "unknown"
    reason: str
    relation: str | None = None  # "same-version" | "update-observed" | "bootstrap-observed"
    release_version: str | None = None
    release_source: str | None = None
    release_time: str | None = None
    repository_id: int | None = None
    evidence_scope: str = "detached-fixture-shape-only"


def _is_valid_named_id(named_id: Any) -> bool:
    return (
        isinstance(named_id, str)
        and 0 < len(named_id) <= _MAX_NAMED_ID_LEN
        and envelope.IDENTIFIER.fullmatch(named_id) is not None
    )


def _unknown(named_id: Any, repository: str | None, reason: str) -> ReleaseProofResult:
    safe_id = named_id if _is_valid_named_id(named_id) else "?"
    return ReleaseProofResult(
        named_id=safe_id,
        repository=repository,
        status="unknown",
        reason=reason,
    )


def _has_control_or_space(value: str) -> bool:
    return any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)


def _validate_api_endpoint_url(url: Any, expected_repo: str, *, kind: str) -> bool:
    """Validate an exact ``https://api.github.com/repos/{owner}/{repo}[/releases/latest]`` URL."""
    if not isinstance(url, str) or not url or len(url) > 512 or _has_control_or_space(url):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.query != ""
        or parsed.fragment != ""
    ):
        return False
    segments = parsed.path.split("/")
    if kind == "releases-latest":
        if len(segments) != 6 or segments[0] != "" or segments[1] != "repos" or segments[4:] != ["releases", "latest"]:
            return False
    elif kind == "repo-metadata":
        if len(segments) != 4 or segments[0] != "" or segments[1] != "repos":
            return False
    else:
        return False
    try:
        url_repo = envelope.repository(f"{segments[2]}/{segments[3]}")
    except PayloadError:
        return False
    return url_repo == expected_repo


def _validate_requested_repo(value: Any, expected_repo: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return envelope.repository(value) == expected_repo
    except PayloadError:
        return False


def _is_permanent_refusal_403(obs: ReleaseHttpObservation) -> bool:
    if type(obs.status_code) is not int or obs.status_code != 403:
        return False
    headers = obs.headers or {}
    if not isinstance(headers, Mapping):
        return False
    lowered: dict[str, str] = {}
    for k, v in headers.items():
        if isinstance(k, str) and isinstance(v, str):
            lowered[k.lower()] = v
    if lowered.get("x-ratelimit-remaining") == "0" or "retry-after" in lowered:
        return False
    if not isinstance(obs.body, Mapping):
        return False
    message = obs.body.get("message")
    if not isinstance(message, str) or not message:
        return False
    low = message.lower()
    if "rate limit" in low or "secondary rate" in low or "abuse detection" in low:
        return False
    if PERMISSION_PROBLEM_RE.search(message):
        return False
    return bool(PERMANENT_REFUSAL_RE.search(message))


def _validate_authority_scope(
    named_id: Any,
    authority: Mapping[str, Mapping[str, Any]],
    expected_repository: Any,
    registered_version: Any,
    expected_repository_id: Any,
) -> tuple[str | None, str | None]:
    """Validate named authority, expected repository, locked source, and registered version.

    Returns ``(normalized_repo, None)`` on success or ``(normalized_repo_or_None, reason)`` on failure.
    """
    if not isinstance(authority, Mapping) or not _is_valid_named_id(named_id):
        return None, "invalid-authority-scope"
    try:
        expected_repo = envelope.repository(expected_repository)
    except PayloadError:
        return None, "invalid-expected-repository"

    if expected_repository_id is not None and (type(expected_repository_id) is not int or expected_repository_id < 1):
        return expected_repo, "invalid-expected-repository-id"

    try:
        auth_repo = envelope.authority_repository(named_id, authority)
    except PayloadError:
        return None, "named-not-in-authority"

    if auth_repo != expected_repo:
        return auth_repo, "authority-repository-mismatch"

    meta = authority[named_id]
    if meta.get("watchUpstream") is False:
        return auth_repo, "watch-upstream-disabled"

    try:
        resolved = resolve_suite_source(dict(meta))
    except UnknownEvidenceError:
        return auth_repo, "invalid-authority-source"
    if resolved is None:
        return auth_repo, "missing-authority-source"

    declared = (meta.get("upstream") or {}).get("repo") if isinstance(meta.get("upstream"), Mapping) else None
    if declared is not None:
        try:
            if envelope.repository(declared) != auth_repo:
                return auth_repo, "authority-upstream-repo-contradiction"
        except PayloadError:
            return auth_repo, "invalid-authority-upstream-repo"

    try:
        validateReleaseSource({"skillId": named_id, "sourceUrl": f"https://github.com/{auth_repo}"})
    except GhError:
        return auth_repo, "locked-source-violation"

    upstream_block = meta.get("upstream")
    auth_version = upstream_block.get("version") if isinstance(upstream_block, Mapping) else None
    if registered_version is not None:
        if not isinstance(registered_version, str) or not _TAG_TOKEN_RE.fullmatch(registered_version):
            return auth_repo, "invalid-registered-version"
    if auth_version is not None:
        if not isinstance(auth_version, str) or not _TAG_TOKEN_RE.fullmatch(auth_version):
            return auth_repo, "invalid-authority-version"
        if registered_version != auth_version:
            return auth_repo, "registered-version-mismatch"
    elif registered_version is not None:
        return auth_repo, "registered-version-mismatch"

    return auth_repo, None


def _validate_repo_metadata(
    repo_metadata_response: Any,
    expected_repo: str,
    expected_repository_id: int | None,
) -> tuple[int | None, str | None]:
    """Validate strict corroborating ``GET /repos/{owner}/{repo}`` metadata."""
    if type(repo_metadata_response) is not RepoMetadataObservation:
        return None, "invalid-metadata-observation"
    if type(repo_metadata_response.redirected) is not bool:
        return None, "invalid-metadata-redirect-flag"
    if type(repo_metadata_response.status_code) is not int or not (100 <= repo_metadata_response.status_code <= 599):
        return None, "invalid-metadata-status-code"
    if not _validate_requested_repo(repo_metadata_response.requested_repository, expected_repo):
        return None, "metadata-requested-repository-mismatch"
    if not _validate_api_endpoint_url(repo_metadata_response.requested_url, expected_repo, kind="repo-metadata"):
        return None, "metadata-endpoint-url-mismatch"
    if repo_metadata_response.redirected or 300 <= repo_metadata_response.status_code < 400:
        return None, "metadata-redirect"
    if repo_metadata_response.status_code == 404:
        return None, "metadata-404"
    if repo_metadata_response.status_code == 403:
        return None, "metadata-403"
    if repo_metadata_response.status_code != 200:
        return None, "metadata-non-200"

    meta_body = repo_metadata_response.body
    if not isinstance(meta_body, Mapping):
        return None, "metadata-malformed"
    full_name = meta_body.get("full_name")
    if not isinstance(full_name, str):
        return None, "metadata-malformed"
    try:
        meta_repo = envelope.repository(full_name)
    except PayloadError:
        return None, "metadata-malformed"
    if meta_repo != expected_repo:
        return None, "metadata-repo-mismatch"

    raw_id = meta_body.get("id")
    if raw_id is not None:
        if type(raw_id) is not int or raw_id < 1:
            return None, "metadata-malformed-repo-id"
        if expected_repository_id is not None and raw_id != expected_repository_id:
            return None, "metadata-repo-id-mismatch"
    elif expected_repository_id is not None:
        return None, "metadata-missing-repo-id"

    return raw_id, None


def classify_release_proof(
    named_id: str,
    authority: Mapping[str, Mapping[str, Any]],
    *,
    expected_repository: str,
    registered_version: str | None,
    latest_response: ReleaseHttpObservation,
    repo_metadata_response: RepoMetadataObservation | None = None,
    expected_repository_id: int | None = None,
) -> ReleaseProofResult:
    """Classify detached release-latest (and optional repo-metadata) fixture observations.

    Always fails closed to ``status="unknown"`` on any mismatch, redirect,
    malformed field, non-integer flag, or uncorroborated 404.
    """
    expected_repo, scope_err = _validate_authority_scope(
        named_id,
        authority,
        expected_repository,
        registered_version,
        expected_repository_id,
    )
    if scope_err is not None:
        return _unknown(named_id, expected_repo, scope_err)
    assert expected_repo is not None

    if type(latest_response) is not ReleaseHttpObservation:
        return _unknown(named_id, expected_repo, "invalid-latest-observation")
    if type(latest_response.redirected) is not bool:
        return _unknown(named_id, expected_repo, "invalid-redirect-flag")
    if type(latest_response.status_code) is not int or not (100 <= latest_response.status_code <= 599):
        return _unknown(named_id, expected_repo, "invalid-status-code")
    if not _validate_requested_repo(latest_response.requested_repository, expected_repo):
        return _unknown(named_id, expected_repo, "requested-repository-mismatch")
    if not _validate_api_endpoint_url(latest_response.requested_url, expected_repo, kind="releases-latest"):
        return _unknown(named_id, expected_repo, "endpoint-url-mismatch")
    if latest_response.redirected or 300 <= latest_response.status_code < 400:
        return _unknown(named_id, expected_repo, "redirect-not-allowed")

    status = latest_response.status_code
    if status == 200:
        body = latest_response.body
        if not isinstance(body, Mapping):
            return _unknown(named_id, expected_repo, "malformed-release-body")
        tag_name = body.get("tag_name")
        if not isinstance(tag_name, str) or not _TAG_TOKEN_RE.fullmatch(tag_name):
            return _unknown(named_id, expected_repo, "malformed-release-tag")
        published_at = body.get("published_at")
        if not isinstance(published_at, str) or not published_at:
            return _unknown(named_id, expected_repo, "malformed-release-time")
        try:
            parsed_utc = weekly_reducer.parse_strict_utc(published_at)
            canonical_time = weekly_reducer.format_utc(parsed_utc)
        except (ValueError, OverflowError):
            return _unknown(named_id, expected_repo, "malformed-release-time")

        html_url = body.get("html_url")
        if not isinstance(html_url, str) or len(html_url) > 512:
            return _unknown(named_id, expected_repo, "malformed-release-source")
        try:
            release_repo = envelope.release_repository(html_url, tag_name)
        except PayloadError:
            return _unknown(named_id, expected_repo, "malformed-release-source")
        if release_repo != expected_repo:
            return _unknown(named_id, expected_repo, "release-repo-mismatch")
        try:
            validateReleaseSource({"skillId": named_id, "sourceUrl": html_url})
        except GhError:
            return _unknown(named_id, expected_repo, "locked-source-violation")

        verified_repo_id: int | None = None
        if expected_repository_id is not None and repo_metadata_response is None:
            return _unknown(named_id, expected_repo, "metadata-missing-for-pinned-id")
        if repo_metadata_response is not None:
            verified_repo_id, meta_err = _validate_repo_metadata(
                repo_metadata_response,
                expected_repo,
                expected_repository_id,
            )
            if meta_err is not None:
                return _unknown(named_id, expected_repo, meta_err)

        if registered_version is None:
            relation = "bootstrap-observed"
            reason = "verified-bootstrap"
        elif tag_name == registered_version:
            relation = "same-version"
            reason = "verified-same-version"
        else:
            relation = "update-observed"
            reason = "verified-update"

        return ReleaseProofResult(
            named_id=named_id,
            repository=expected_repo,
            status="observed",
            reason=reason,
            relation=relation,
            release_version=tag_name,
            release_source=html_url,
            release_time=canonical_time,
            repository_id=verified_repo_id,
        )

    if status == 404:
        if repo_metadata_response is None:
            return _unknown(named_id, expected_repo, "bare-404-uncorroborated")
        verified_repo_id, meta_err = _validate_repo_metadata(
            repo_metadata_response,
            expected_repo,
            expected_repository_id,
        )
        if meta_err is not None:
            return _unknown(named_id, expected_repo, meta_err)

        return ReleaseProofResult(
            named_id=named_id,
            repository=expected_repo,
            status="no-visible-latest-release",
            reason="corroborated-404-no-visible-latest-release",
            repository_id=verified_repo_id,
        )

    if status in PERMANENT_UNAVAILABLE_STATUSES:
        return ReleaseProofResult(
            named_id=named_id,
            repository=expected_repo,
            status="unavailable",
            reason=f"permanent-http-{status}",
        )
    if _is_permanent_refusal_403(latest_response):
        return ReleaseProofResult(
            named_id=named_id,
            repository=expected_repo,
            status="unavailable",
            reason="permanent-http-403-refusal",
        )

    return _unknown(named_id, expected_repo, f"unconfirmed-http-{status}")
