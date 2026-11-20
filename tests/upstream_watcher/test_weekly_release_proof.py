"""Offline-only fixture tests for scripts.upstream_watcher.weekly_release_proof."""
from __future__ import annotations

import dataclasses
import socket
from typing import Any

import pytest

from scripts.upstream_watcher.weekly_release_proof import (
    ReleaseHttpObservation,
    ReleaseProofResult,
    RepoMetadataObservation,
    TRANSPORT_AUTHENTICITY_REQUIREMENTS,
    classify_release_proof,
)


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("weekly_release_proof test attempted network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def _authority(
    *,
    named_id: str = "owner/suite",
    repo: str = "owner/repo",
    version: str | None = "v1.0.0",
) -> dict[str, dict[str, Any]]:
    upstream: dict[str, Any] = {"repo": repo}
    if version is not None:
        upstream["version"] = version
    return {
        named_id: {
            "id": named_id,
            "links": {"github": f"https://github.com/{repo}"},
            "upstream": upstream,
        }
    }


def _latest_obs(
    repo: str = "owner/repo",
    *,
    requested_repo: str | None = None,
    status_code: Any = 200,
    redirected: Any = False,
    body: Any = None,
    headers: dict[str, str] | None = None,
) -> ReleaseHttpObservation:
    return ReleaseHttpObservation(
        requested_url=f"https://api.github.com/repos/{repo}/releases/latest",
        requested_repository=requested_repo if requested_repo is not None else repo,
        status_code=status_code,
        redirected=redirected,
        body=body,
        headers=headers,
    )


def _meta_obs(
    repo: str = "owner/repo",
    *,
    requested_repo: str | None = None,
    status_code: Any = 200,
    redirected: Any = False,
    body: Any = None,
) -> RepoMetadataObservation:
    return RepoMetadataObservation(
        requested_url=f"https://api.github.com/repos/{repo}",
        requested_repository=requested_repo if requested_repo is not None else repo,
        status_code=status_code,
        redirected=redirected,
        body=body,
    )


def test_200_same_version_update_and_bootstrap_relations() -> None:
    auth = _authority(version="v1.0.0")
    same = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            body={
                "tag_name": "v1.0.0",
                "published_at": "2026-11-20T10:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.0.0",
            }
        ),
    )
    assert same.status == "observed"
    assert same.relation == "same-version"
    assert same.release_version == "v1.0.0"
    assert same.release_source == "https://github.com/owner/repo/releases/tag/v1.0.0"
    assert same.release_time == "2026-11-20T10:00:00Z"

    updated = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            body={
                "tag_name": "v1.1.0",
                "published_at": "2026-11-20T11:30:00+02:00",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
            }
        ),
    )
    assert updated.status == "observed"
    assert updated.relation == "update-observed"
    assert updated.release_version == "v1.1.0"
    assert updated.release_time == "2026-11-20T09:30:00Z"

    boot_auth = _authority(version=None)
    boot = classify_release_proof(
        "owner/suite",
        boot_auth,
        expected_repository="owner/repo",
        registered_version=None,
        latest_response=_latest_obs(
            body={
                "tag_name": "v0.1.0",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v0.1.0",
            }
        ),
    )
    assert boot.status == "observed"
    assert boot.relation == "bootstrap-observed"
    assert boot.release_version == "v0.1.0"


def test_agentdb_distinct_locked_source_and_mixed_case_url() -> None:
    auth = _authority(named_id="ruvnet/agentdb", repo="RuvNet/AgentDB", version="v1.0.0")
    ok = classify_release_proof(
        "ruvnet/agentdb",
        auth,
        expected_repository="ruvnet/agentdb",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            "RuvNet/AgentDB",
            body={
                "tag_name": "v1.2.0",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/RuvNet/AgentDB/releases/tag/v1.2.0",
            },
        ),
    )
    assert ok.status == "observed"
    assert ok.repository == "ruvnet/agentdb"
    assert ok.relation == "update-observed"

    # Cross-repo substitution (ruflo pretending to be agentdb) fails closed.
    forged_auth = {
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "links": {"github": "https://github.com/ruvnet/ruflo"},
            "upstream": {"repo": "ruvnet/ruflo", "version": "v1.0.0"},
        }
    }
    locked = classify_release_proof(
        "ruvnet/agentdb",
        forged_auth,
        expected_repository="ruvnet/ruflo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            "ruvnet/ruflo",
            body={
                "tag_name": "v2.0.0",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/ruvnet/ruflo/releases/tag/v2.0.0",
            },
        ),
    )
    assert locked.status == "unknown"
    assert locked.reason == "locked-source-violation"


def test_malformed_url_tag_time_mismatches_and_noninteger_flags_fail_closed() -> None:
    auth = _authority(version="v1.0.0")
    bad_cases = [
        _latest_obs(
            body={
                "tag_name": "v1.1.0",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/other/repo/releases/tag/v1.1.0",
            }
        ),
        _latest_obs(
            body={
                "tag_name": "v1.1.0",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0?evil=1",
            }
        ),
        _latest_obs(
            body={
                "tag_name": "v1.1.0/bad",
                "published_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0%2Fbad",
            }
        ),
        _latest_obs(
            body={
                "tag_name": "v1.1.0",
                "published_at": "2026-11-20 12:00:00",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
            }
        ),
        _latest_obs(status_code=True),
        _latest_obs(redirected=1),
        _latest_obs(redirected=True),
        _latest_obs(requested_repo="other/repo"),
        _latest_obs(status_code=503),
    ]
    for obs in bad_cases:
        res = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=obs,
        )
        assert res.status == "unknown"
        assert res.release_version is None
        assert res.release_source is None
        assert res.release_time is None


def test_permanent_refusals_vs_bare_403_and_rate_limit() -> None:
    auth = _authority(version="v1.0.0")
    gone = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(status_code=410),
    )
    assert gone.status == "unavailable"

    dmca = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            status_code=403,
            body={"message": "Repository access blocked due to DMCA takedown"},
        ),
    )
    assert dmca.status == "unavailable"

    rate_limited = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            status_code=403,
            headers={"X-RateLimit-Remaining": "0"},
            body={"message": "Repository access blocked"},
        ),
    )
    assert rate_limited.status == "unknown"

    bare_403 = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(status_code=403, body={"message": "Forbidden"}),
    )
    assert bare_403.status == "unknown"


def test_404_corroborated_vs_bare_renamed_redirected_wrong_or_missing_metadata() -> None:
    auth = _authority(version="v1.0.0")
    obs_404 = _latest_obs(status_code=404)

    bare = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=obs_404,
    )
    assert bare.status == "unknown"
    assert bare.reason == "bare-404-uncorroborated"

    corroborated = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=obs_404,
        repo_metadata_response=_meta_obs(body={"full_name": "Owner/Repo", "id": 424242}),
        expected_repository_id=424242,
    )
    assert corroborated.status == "no-visible-latest-release"
    assert corroborated.repository == "owner/repo"
    assert corroborated.repository_id == 424242

    bad_meta_cases = [
        _meta_obs(status_code=404),
        _meta_obs(status_code=403),
        _meta_obs(status_code=301, redirected=True),
        _meta_obs(status_code=200, redirected=True, body={"full_name": "owner/repo", "id": 1}),
        _meta_obs(status_code=200, body={"full_name": "owner/renamed-repo", "id": 1}),
        _meta_obs(status_code=200, requested_repo="other/repo", body={"full_name": "owner/repo", "id": 1}),
        _meta_obs(status_code=200, body={"full_name": "owner/repo", "id": True}),
        _meta_obs(status_code=200, body={"full_name": "owner/repo", "id": 999999}),
        _meta_obs(status_code=200, body="not-a-mapping"),
    ]
    for meta in bad_meta_cases:
        res = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=obs_404,
            repo_metadata_response=meta,
            expected_repository_id=424242,
        )
        assert res.status == "unknown"
        assert res.repository_id is None


def test_result_immutability_and_sanitization() -> None:
    auth = _authority(version="v1.0.0")
    res = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=_latest_obs(
            body={
                "tag_name": "v1.1.0",
                "published_at": "2026-11-20T10:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
                "body": "raw release notes must never leak",
                "author": {"login": "secret"},
            }
        ),
    )
    assert isinstance(res, ReleaseProofResult)
    assert res.evidence_scope == "detached-fixture-shape-only"
    assert len(TRANSPORT_AUTHENTICITY_REQUIREMENTS) >= 3
    with pytest.raises(dataclasses.FrozenInstanceError):
        res.status = "unknown"  # type: ignore[misc]
    field_names = {f.name for f in dataclasses.fields(ReleaseProofResult)}
    assert field_names.isdisjoint({"body", "headers", "raw_response", "diagnostics", "write_authorized", "write_readiness"})


def test_invalid_named_id_sanitized_and_never_echoed() -> None:
    auth = _authority(version="v1.0.0")
    for bad_id in ("", "bad\nid", "../etc", "a" * 300, "owner/repo\x1b[31m", 123):
        res = classify_release_proof(
            bad_id,  # type: ignore[arg-type]
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=_latest_obs(
                body={
                    "tag_name": "v1.1.0",
                    "published_at": "2026-11-20T10:00:00Z",
                    "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
                }
            ),
        )
        assert res.status == "unknown"
        assert res.named_id == "?"
        assert res.reason == "invalid-authority-scope"


def test_200_pinned_repository_id_and_supplied_metadata_checks() -> None:
    auth = _authority(version="v1.0.0")
    obs_200 = _latest_obs(
        body={
            "tag_name": "v1.1.0",
            "published_at": "2026-11-20T10:00:00Z",
            "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
        }
    )

    # Positive no-ID control
    no_id = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=obs_200,
    )
    assert no_id.status == "observed"
    assert no_id.relation == "update-observed"
    assert no_id.repository_id is None

    # Positive matching-ID control
    matched_id = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=obs_200,
        repo_metadata_response=_meta_obs(body={"full_name": "Owner/Repo", "id": 424242}),
        expected_repository_id=424242,
    )
    assert matched_id.status == "observed"
    assert matched_id.relation == "update-observed"
    assert matched_id.repository_id == 424242

    # 200 with pin but missing positive metadata fails closed
    missing_meta = classify_release_proof(
        "owner/suite",
        auth,
        expected_repository="owner/repo",
        registered_version="v1.0.0",
        latest_response=obs_200,
        expected_repository_id=424242,
    )
    assert missing_meta.status == "unknown"
    assert missing_meta.reason == "metadata-missing-for-pinned-id"

    # 200 with contradictory/mismatched/failing metadata never returns verified-update
    for bad_meta, expected_pin in (
        (_meta_obs(body={"full_name": "owner/repo", "id": 999999}), 424242),
        (_meta_obs(body={"full_name": "owner/renamed", "id": 424242}), 424242),
        (_meta_obs(body={"full_name": "owner/renamed"}), None),
        (_meta_obs(status_code=404), None),
        (_meta_obs(status_code=301, redirected=True), None),
    ):
        bad_res = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=obs_200,
            repo_metadata_response=bad_meta,
            expected_repository_id=expected_pin,
        )
        assert bad_res.status == "unknown"
        assert bad_res.release_version is None


def test_utc_overflow_and_out_of_bounds_http_status_fail_closed() -> None:
    auth = _authority(version="v1.0.0")
    for boundary_ts in ("0001-01-01T00:00:00+05:00", "9999-12-31T23:59:59-05:00"):
        res = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=_latest_obs(
                body={
                    "tag_name": "v1.1.0",
                    "published_at": boundary_ts,
                    "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
                }
            ),
        )
        assert res.status == "unknown"
        assert res.reason == "malformed-release-time"

    for absurd_code in (0, -1, 99, 600, 999999):
        latest_bad = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=_latest_obs(status_code=absurd_code),
        )
        assert latest_bad.status == "unknown"
        assert latest_bad.reason == "invalid-status-code"

        meta_bad = classify_release_proof(
            "owner/suite",
            auth,
            expected_repository="owner/repo",
            registered_version="v1.0.0",
            latest_response=_latest_obs(status_code=404),
            repo_metadata_response=_meta_obs(status_code=absurd_code),
        )
        assert meta_bad.status == "unknown"
        assert meta_bad.reason == "invalid-metadata-status-code"
