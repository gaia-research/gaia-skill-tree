"""Offline-only composition tests for P2 Slice 5."""
from __future__ import annotations

import dataclasses
import socket
from typing import Any

import pytest

from scripts.upstream_watcher import batch, envelope, liveness, watcher, weekly_census, weekly_collector
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher.weekly_effect import FakeIssueService


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("weekly census test attempted network access")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def _authority() -> dict[str, dict[str, Any]]:
    return {
        "owner/suite": {
            "id": "owner/suite",
            "links": {"github": "https://github.com/owner/repo"},
            "upstream": {"repo": "owner/repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["owner/base"],
        },
        "owner/base": {
            "id": "owner/base",
            "links": {"github": "https://github.com/owner/repo/blob/main/skills/base/SKILL.md"},
        },
    }


def _install_fake_upstream(monkeypatch: pytest.MonkeyPatch, *, tree: Any = None) -> None:
    tree_payload = tree or {
        "sha": "a" * 40, "truncated": False,
        "tree": [
            {"path": "skills", "type": "tree", "sha": "b" * 40},
            {"path": "skills/base", "type": "tree", "sha": "c" * 40},
            {"path": "skills/base/SKILL.md", "type": "blob", "sha": "d" * 40},
            {"path": "skills/alpha", "type": "tree", "sha": "e" * 40},
            {"path": "skills/alpha/SKILL.md", "type": "blob", "sha": "f" * 40},
        ],
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/releases/latest"):
            return {
                "tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0",
            }
        if "/git/trees/v1.1.0" in url:
            return tree_payload
        raise AssertionError("unexpected fake upstream request")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])


def _run(monkeypatch: pytest.MonkeyPatch, *, held_named_ids=frozenset(), held_repos=frozenset(), tree=None, observed_at="2026-11-23T09:00:00Z"):
    _install_fake_upstream(monkeypatch, tree=tree)
    auth = _authority()
    poll_id = "census-2026-11-23"
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id=poll_id)
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    result = weekly_census.run_weekly_census(
        [auth["owner/suite"]], auth, fake, collected,
        poll_id=poll_id, observed_at=observed_at,
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        held_repos=held_repos, held_named_ids=held_named_ids,
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        historical_loader=lambda _identifier: {},
    )
    assert fake.writes == ()
    assert not any(hasattr(fake, name) for name in ("create_issue", "edit_issue", "comment"))
    return result


def test_complete_fake_scoped_census_reports_hold_and_safe_release_proof(monkeypatch):
    census = _run(monkeypatch, held_named_ids=frozenset({"owner/suite"}))
    scope = census.scopes[0]
    assert census.status == "scoped-holds-or-unavailable"
    assert scope.named_id == "owner/suite" and scope.repository == "owner/repo"
    assert scope.collection_status == "observed" and scope.proof_status == "verified"
    assert scope.decision == "held-named-scope"
    assert scope.release_version == "v1.1.0"
    assert scope.release_source == "https://github.com/owner/repo/releases/tag/v1.1.0"
    assert scope.inventory_status == "verified"
    assert ("componentAdds", ("alpha",)) in scope.structural_delta
    assert scope.liveness == () and scope.name_drift_ids == ()
    assert census.actual_creates == census.actual_updates == 0
    assert not census.write_authorized and not census.write_readiness and not census.persisted
    assert census.state_mode == "ephemeral-empty" and census.dispositions == ()


def test_fresh_fake_inventory_binding_remains_logical_only(monkeypatch):
    census = _run(monkeypatch)
    assert census.status == "observed-plan-only"
    assert census.binding_status == "bound"
    assert census.logical_candidate_count == 1
    assert census.actual_creates == census.actual_updates == 0
    assert not census.write_authorized and not census.write_readiness and not census.persisted


def test_tuesday_nonflush_is_hold_not_eligible(monkeypatch):
    census = _run(monkeypatch, observed_at="2026-11-24T09:00:00Z")
    assert census.binding_status == "idle"
    assert census.logical_candidate_count == 0
    assert census.scopes[0].decision == "hold"


def test_repo_hold_is_explicit_and_does_not_become_global_refusal(monkeypatch):
    census = _run(monkeypatch, held_repos=frozenset({"owner/repo"}))
    assert census.status == "scoped-holds-or-unavailable"
    assert census.scopes[0].decision == "held-repository-scope"
    assert census.binding_status != "refused"


def test_incomplete_collector_tree_is_unknown_not_clearance(monkeypatch):
    result = _run(monkeypatch, tree={"sha": "a" * 40, "truncated": True, "tree": []})
    assert result.status == "unknown-incomplete"
    assert result.binding_status == "idle"
    assert result.logical_candidate_count == 0
    assert result.repository_statuses == ()
    assert result.scopes[0].collection_status == "observed"
    assert result.scopes[0].decision == "unknown"
    assert result.scopes[0].hold_reason == "incomplete-tree"
    assert result.scopes[0].proof_status != "verified"
    assert result.scopes[0].inventory_status == "unknown"
    assert result.scopes[0].version_status == "release-observed"
    assert result.scopes[0].release_version == "v1.1.0"
    assert result.scopes[0].canonical_removals == ()
    assert result.actual_creates == result.actual_updates == 0 and not result.write_readiness


def test_unknown_collector_status_is_not_top_level_healthy(monkeypatch):
    auth = _authority()
    collected = weekly_collector.collect_suites([{"id": "owner/missing"}], auth, poll_id="unknown-poll")
    census = weekly_census.run_weekly_census(
        [{"id": "owner/missing"}], auth, FakeIssueService(repo="gaia-research/gaia-skill-tree"), collected,
        poll_id="unknown-poll", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
        config_repo="gaia-research/gaia-skill-tree", index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    assert census.status == "unknown-incomplete"
    assert census.scopes[0].decision == "unknown"


def test_mismatched_poll_and_malformed_collected_object_fail_closed(monkeypatch):
    _install_fake_upstream(monkeypatch)
    auth = _authority()
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id="poll-a")
    kwargs = dict(poll_id="poll-b", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
                  config_repo="gaia-research/gaia-skill-tree", index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={})
    with pytest.raises(PayloadError, match="exact expected poll ID"):
        weekly_census.run_weekly_census([auth["owner/suite"]], auth,
            FakeIssueService(repo="gaia-research/gaia-skill-tree"), collected, **kwargs)
    forged = dataclasses.replace(collected, poll_id="poll-b", complete_inventories=())
    # build_poll_input will not attach a claimed inventory if the real collected proof is absent.
    census = weekly_census.run_weekly_census([auth["owner/suite"]], auth,
        FakeIssueService(repo="gaia-research/gaia-skill-tree"), forged, **kwargs)
    assert census.scopes[0].inventory_status == "unknown"
    assert census.status == "unknown-incomplete"


def test_sealed_reader_refuses_direct_and_wrapped_live_ports():
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    reader = weekly_census._FakeIssueReader(fake, "gaia-research/gaia-skill-tree")
    assert reader.repo == "gaia-research/gaia-skill-tree"
    for name in ("create_issue", "edit_issue", "comment", "request", "session", "transport"):
        with pytest.raises(AttributeError):
            getattr(reader, name)
    with pytest.raises(PayloadError, match="exact FakeIssueService"):
        weekly_census._FakeIssueReader(object(), "gaia-research/gaia-skill-tree")
    with pytest.raises(PayloadError, match="configured repository"):
        weekly_census._FakeIssueReader(fake, "other/repository")


def test_duplicate_scope_and_unsupported_supplied_state_fail_closed(monkeypatch):
    _install_fake_upstream(monkeypatch)
    auth = _authority()
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id="invalid")
    kwargs = dict(poll_id="invalid", observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
                  config_repo="gaia-research/gaia-skill-tree", index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={})
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    with pytest.raises(PayloadError):
        weekly_census.run_weekly_census([auth["owner/suite"]] * 2, auth, fake, collected, **kwargs)
    duplicate = dataclasses.replace(collected, results=collected.results * 2)
    with pytest.raises(PayloadError, match="exactly match collected scopes"):
        weekly_census.run_weekly_census([auth["owner/suite"]], auth, fake, duplicate, **kwargs)
    changed = dataclasses.replace(collected.results[0], finding={**collected.results[0].finding, "newVersion": "v99"})
    mismatched = dataclasses.replace(collected, results=(changed,))
    with pytest.raises(PayloadError, match="observations disagree"):
        weekly_census.run_weekly_census([auth["owner/suite"]], auth, fake, mismatched, **kwargs)
    with pytest.raises(PayloadError, match="supplied named-v3 state is deferred"):
        weekly_census.run_weekly_census([], auth, fake, collected, **{**kwargs, "state_mode": "named-v3"})
    assert fake.writes == ()


def test_census_api_does_not_accept_checkpoint_path_or_implicit_state():
    names = {field.name for field in dataclasses.fields(weekly_census.WeeklyCensus)}
    assert "journal_path" not in names
    with pytest.raises(TypeError):
        weekly_census.run_weekly_census(
            [], _authority(), FakeIssueService(repo="gaia-research/gaia-skill-tree"), None,
            poll_id="x", observed_at="2026-11-23T09:00:00Z", journal_path="/tmp/no-open",
            state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
            index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        )


def test_real_planner_legacy_hold_reports_safe_scopes_and_preserves_unrelated_good_scope(monkeypatch):
    auth = {
        "legacy/suite": {
            "id": "legacy/suite",
            "links": {"github": "https://github.com/current/new-repo"},
            "upstream": {"repo": "current/new-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["legacy/base"],
        },
        "legacy/base": {
            "id": "legacy/base",
            "links": {"github": "https://github.com/current/new-repo/blob/main/skills/base/SKILL.md"},
        },
        "other/good": {
            "id": "other/good",
            "links": {"github": "https://github.com/other/good-repo"},
            "upstream": {"repo": "other/good-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["other/comp"],
        },
        "other/comp": {
            "id": "other/comp",
            "links": {"github": "https://github.com/other/good-repo/blob/main/skills/comp/SKILL.md"},
        },
    }
    legacy_payload = envelope.seal({
        "payloadVersion": 2,
        "skillId": "legacy/suite",
        "newVersion": "v0.9.0",
        "releasedAt": "2026-10-01T00:00:00Z",
        "sourceUrl": "https://github.com/legacy/old-repo/releases/tag/v0.9.0",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
        "candidates": [],
    })
    legacy_issue = {
        "number": 42,
        "state": "open",
        "title": "[upstream] legacy/old-repo → v0.9.0",
        "labels": [{"name": "upstream:release"}],
        "body": batch.payload_block(legacy_payload) + "\n\nSECRET_LEGACY_BODY",
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/repos/current/new-repo/releases/latest"):
            return {"tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/current/new-repo/releases/tag/v1.1.0"}
        if url.endswith("/repos/other/good-repo/releases/latest"):
            return {"tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/other/good-repo/releases/tag/v1.1.0"}
        if "/git/trees/v1.1.0" in url:
            return {
                "sha": "a" * 40, "truncated": False,
                "tree": [
                    {"path": "skills", "type": "tree", "sha": "b" * 40},
                    {"path": "skills/base", "type": "tree", "sha": "c" * 40},
                    {"path": "skills/base/SKILL.md", "type": "blob", "sha": "d" * 40},
                    {"path": "skills/comp", "type": "tree", "sha": "e" * 40},
                    {"path": "skills/comp/SKILL.md", "type": "blob", "sha": "f" * 40},
                    {"path": "skills/newone", "type": "tree", "sha": "1" * 40},
                    {"path": "skills/newone/SKILL.md", "type": "blob", "sha": "2" * 40},
                ],
            }
        raise AssertionError(f"unexpected fake upstream request: {url}")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])

    def historical_loader(identifier: str) -> dict[str, Any]:
        if identifier == "legacy/suite":
            return {
                "legacy/suite": {
                    "id": "legacy/suite",
                    "links": {"github": "https://github.com/legacy/old-repo"},
                    "upstream": {"repo": "legacy/old-repo", "version": "v0.8.0"},
                }
            }
        return {}

    collected = weekly_collector.collect_suites([auth["legacy/suite"], auth["other/good"]], auth, poll_id="legacy-hold-poll")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree", issues=[legacy_issue])
    census = weekly_census.run_weekly_census(
        [auth["legacy/suite"], auth["other/good"]], auth, fake, collected,
        poll_id="legacy-hold-poll", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        historical_loader=historical_loader,
    )
    assert census.status == "scoped-holds-or-unavailable"
    assert census.known_legacy_holds == (
        weekly_census.LegacyHold(
            repository="legacy/old-repo",
            issue=42,
            legacy_named_id="legacy/suite",
            current_release_repository="current/new-repo",
            hold="separate-migration-approval-required",
        ),
    )
    rendered = repr(census)
    assert "SECRET_LEGACY_BODY" not in rendered
    assert "[upstream] legacy/old-repo" not in rendered
    by_id = {scope.named_id: scope for scope in census.scopes}
    assert by_id["legacy/suite"].decision == "held-repository-scope"
    assert by_id["other/good"].decision == "eligible-for-read-only-binding"
    assert census.logical_candidate_count == 1
    assert dict(census.repository_statuses)["other/good-repo"] == "candidate-intent"
    assert census.actual_creates == census.actual_updates == 0
    assert not census.write_authorized and not census.write_readiness


def test_liveness_drift_qualified_removals_and_untrusted_text_suppressed(monkeypatch):
    auth = {
        "owner/suite": {
            "id": "owner/suite",
            "links": {"github": "https://github.com/owner/repo"},
            "upstream": {"repo": "owner/repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["owner/base", "owner/vanished", "owner/neterr"],
        },
        "owner/base": {"id": "owner/base", "links": {"github": "https://github.com/owner/repo/blob/main/skills/base/SKILL.md"}},
        "owner/vanished": {"id": "owner/vanished", "links": {"github": "https://github.com/owner/repo/blob/main/skills/vanished/SKILL.md"}},
        "owner/neterr": {"id": "owner/neterr", "links": {"github": "https://github.com/owner/repo/blob/main/skills/neterr/SKILL.md"}},
    }
    _install_fake_upstream(monkeypatch, tree={
        "sha": "a" * 40, "truncated": False,
        "tree": [
            {"path": "skills", "type": "tree", "sha": "b" * 40},
            {"path": "skills/base", "type": "tree", "sha": "c" * 40},
            {"path": "skills/base/SKILL.md", "type": "blob", "sha": "d" * 40},
            {"path": "skills/neterr", "type": "tree", "sha": "e" * 40},
            {"path": "skills/neterr/SKILL.md", "type": "blob", "sha": "f" * 40},
            {"path": "skills/alpha", "type": "tree", "sha": "1" * 40},
            {"path": "skills/alpha/SKILL.md", "type": "blob", "sha": "2" * 40},
        ],
    })
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [
        {
            "skillId": "owner/base",
            "url": "https://github.com/owner/repo/blob/main/skills/base/SKILL.md",
            "rawUrl": "https://raw.githubusercontent.com/owner/repo/main/skills/base/SKILL.md",
            "status": 404,
        },
        {
            "skillId": "owner/neterr",
            "url": "https://github.com/owner/repo/blob/main/skills/neterr/SKILL.md",
            "rawUrl": "https://raw.githubusercontent.com/owner/repo/main/skills/neterr/SKILL.md",
            "status": "network_error",
        },
    ])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [
        {
            "skillId": "owner/base",
            "registrySlug": "base",
            "sanitizedName": "UNTRUSTED_DRIFT_TEXT",
            "fixCommand": "untrusted-fix-cmd",
        },
    ])
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id="liveness-drift-poll")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    census = weekly_census.run_weekly_census(
        [auth["owner/suite"]], auth, fake, collected,
        poll_id="liveness-drift-poll", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    scope = census.scopes[0]
    assert census.status == "observed-plan-only"
    assert scope.liveness == (("owner/base", "404"), ("owner/neterr", "network_error"))
    assert scope.name_drift_ids == ("owner/base",)
    assert scope.structural_delta == (("componentAdds", ("alpha",)), ("componentRemoves", ("vanished",)))
    assert scope.canonical_removals == ("owner/vanished",)
    assert scope.version_status == "release-observed"
    assert scope.delta_status == "observational-raw"
    assert scope.inventory_status == "verified"
    rendered = repr(census)
    assert "UNTRUSTED_DRIFT_TEXT" not in rendered
    assert "untrusted-fix-cmd" not in rendered


def test_mixed_case_agentdb_release_identity_normalizes_repo(monkeypatch):
    auth = {
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "links": {"github": "https://github.com/RuvNet/AgentDB"},
            "upstream": {"repo": "RuvNet/AgentDB", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["ruvnet/alpha"],
        },
        "ruvnet/alpha": {
            "id": "ruvnet/alpha",
            "links": {"github": "https://github.com/RuvNet/AgentDB/blob/main/skills/alpha/SKILL.md"},
        },
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/repos/RuvNet/AgentDB/releases/latest"):
            return {
                "tag_name": "v2.0.0",
                "published_at": "2026-11-23T08:00:00Z",
                "html_url": "https://github.com/RuvNet/AgentDB/releases/tag/v2.0.0",
            }
        if "/git/trees/v2.0.0" in url:
            return {
                "sha": "a" * 40, "truncated": False,
                "tree": [
                    {"path": "skills", "type": "tree", "sha": "b" * 40},
                    {"path": "skills/alpha", "type": "tree", "sha": "c" * 40},
                    {"path": "skills/alpha/SKILL.md", "type": "blob", "sha": "d" * 40},
                    {"path": "skills/beta", "type": "tree", "sha": "e" * 40},
                    {"path": "skills/beta/SKILL.md", "type": "blob", "sha": "f" * 40},
                ],
            }
        raise AssertionError(f"unexpected fake upstream request: {url}")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])

    collected = weekly_collector.collect_suites([auth["ruvnet/agentdb"]], auth, poll_id="agentdb-mixed-case")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    census = weekly_census.run_weekly_census(
        [auth["ruvnet/agentdb"]], auth, fake, collected,
        poll_id="agentdb-mixed-case", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    scope = census.scopes[0]
    assert census.status == "observed-plan-only"
    assert scope.repository == "ruvnet/agentdb"
    assert scope.release_version == "v2.0.0"
    assert scope.release_source == "https://github.com/RuvNet/AgentDB/releases/tag/v2.0.0"
    assert scope.release_time == "2026-11-23T08:00:00Z"
    assert scope.decision == "eligible-for-read-only-binding"


def test_malformed_projection_fields_are_never_labeled_verified(monkeypatch):
    _install_fake_upstream(monkeypatch)
    auth = _authority()
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id="malformed-proj")
    res = collected.results[0]
    bad_liveness = dataclasses.replace(res, finding={**res.finding, "linkLiveness": [{"skillId": "owner/base", "url": "https://example.com", "status": 200}]})
    assert weekly_census._safe_release_projection(bad_liveness, auth, True) == (None, None, None, None, (), (), (), ())
    bad_drift = dataclasses.replace(res, finding={**res.finding, "nameDrift": [{"skillId": "other/untracked"}]})
    assert weekly_census._safe_release_projection(bad_drift, auth, True) == (None, None, None, None, (), (), (), ())


def test_end_to_end_invalid_liveness_and_unregistered_component_fail_closed(monkeypatch):
    auth = _authority()
    for bad_liveness in (
        [{"skillId": "owner/base", "url": "https://example.invalid/skill", "status": 200}],
        [{"skillId": "owner/missing", "url": "https://example.invalid/skill", "status": 404}],
    ):
        _install_fake_upstream(monkeypatch)
        monkeypatch.setattr(watcher, "check_component_liveness", lambda *_args, rows=bad_liveness: rows)
        collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id="invalid-e2e")
        fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
        census = weekly_census.run_weekly_census(
            [auth["owner/suite"]], auth, fake, collected,
            poll_id="invalid-e2e", observed_at="2026-11-23T09:00:00Z",
            state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
            held_named_ids=frozenset({"owner/suite"}),
            index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        )
        scope = census.scopes[0]
        assert census.status == "unknown-incomplete"
        assert census.logical_candidate_count == 0
        assert scope.decision == "unknown"
        assert scope.inventory_status == "unknown"
        assert scope.proof_status == "unknown"
        assert scope.version_status == "unknown"
        assert scope.delta_status == "unknown"
        assert scope.liveness == ()


def test_invalid_scope_preserves_valid_unrelated_and_held_scopes_without_erasing_uncertainty(monkeypatch):
    auth = {
        "owner/bad": {
            "id": "owner/bad",
            "links": {"github": "https://github.com/owner/bad-repo"},
            "upstream": {"repo": "owner/bad-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["owner/base"],
        },
        "owner/base": {"id": "owner/base", "links": {"github": "https://github.com/owner/bad-repo/blob/main/skills/base/SKILL.md"}},
        "other/good": {
            "id": "other/good",
            "links": {"github": "https://github.com/other/good-repo"},
            "upstream": {"repo": "other/good-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["other/comp"],
        },
        "other/comp": {"id": "other/comp", "links": {"github": "https://github.com/other/good-repo/blob/main/skills/comp/SKILL.md"}},
        "held/suite": {
            "id": "held/suite",
            "links": {"github": "https://github.com/held/held-repo"},
            "upstream": {"repo": "held/held-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["held/comp"],
        },
        "held/comp": {"id": "held/comp", "links": {"github": "https://github.com/held/held-repo/blob/main/skills/comp/SKILL.md"}},
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        for repo_slug in ("owner/bad-repo", "other/good-repo", "held/held-repo"):
            if url.endswith(f"/repos/{repo_slug}/releases/latest"):
                return {
                    "tag_name": "v1.1.0",
                    "published_at": "2026-11-23T08:00:00Z",
                    "html_url": f"https://github.com/{repo_slug}/releases/tag/v1.1.0",
                }
        if "/git/trees/v1.1.0" in url:
            return {
                "sha": "a" * 40, "truncated": False,
                "tree": [
                    {"path": "skills", "type": "tree", "sha": "b" * 40},
                    {"path": "skills/base", "type": "tree", "sha": "c" * 40},
                    {"path": "skills/base/SKILL.md", "type": "blob", "sha": "d" * 40},
                    {"path": "skills/comp", "type": "tree", "sha": "e" * 40},
                    {"path": "skills/comp/SKILL.md", "type": "blob", "sha": "f" * 40},
                    {"path": "skills/newone", "type": "tree", "sha": "1" * 40},
                    {"path": "skills/newone/SKILL.md", "type": "blob", "sha": "2" * 40},
                ],
            }
        raise AssertionError(f"unexpected fake upstream request: {url}")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])
    monkeypatch.setattr(
        watcher,
        "check_component_liveness",
        lambda comps, *_: (
            [{"skillId": "owner/base", "url": "https://example.invalid/skill", "status": 200}]
            if "owner/base" in comps
            else []
        ),
    )

    suites = [auth["owner/bad"], auth["other/good"], auth["held/suite"]]
    collected = weekly_collector.collect_suites(suites, auth, poll_id="mixed-invalid-e2e")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    census = weekly_census.run_weekly_census(
        suites, auth, fake, collected,
        poll_id="mixed-invalid-e2e", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        held_named_ids=frozenset({"held/suite"}),
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    assert census.status == "unknown-incomplete"
    assert census.logical_candidate_count == 1
    by_id = {scope.named_id: scope for scope in census.scopes}
    assert by_id["owner/bad"].decision == "unknown"
    assert by_id["owner/bad"].inventory_status == "unknown"
    assert by_id["owner/bad"].version_status == "unknown"
    assert by_id["other/good"].decision == "eligible-for-read-only-binding"
    assert by_id["other/good"].inventory_status == "verified"
    assert by_id["other/good"].version_status == "release-observed"
    assert by_id["held/suite"].decision == "held-named-scope"
    assert by_id["held/suite"].inventory_status == "verified"
    assert by_id["held/suite"].version_status == "release-observed"


def test_incomplete_tree_with_explicit_hold_tuesday_and_independent_good_scope(monkeypatch):
    trunc = {"sha": "a" * 40, "truncated": True, "tree": []}
    held = _run(monkeypatch, held_named_ids=frozenset({"owner/suite"}), tree=trunc)
    assert held.status == "unknown-incomplete"
    assert held.binding_status == "idle"
    assert held.logical_candidate_count == 0
    assert held.scopes[0].decision == "unknown"
    assert held.scopes[0].hold_reason == "held-named-scope"
    assert held.scopes[0].inventory_status == "unknown"
    assert held.scopes[0].version_status == "release-observed"

    tuesday = _run(monkeypatch, observed_at="2026-11-24T09:00:00Z", tree=trunc)
    assert tuesday.status == "unknown-incomplete"
    assert tuesday.binding_status == "idle"
    assert tuesday.logical_candidate_count == 0
    assert tuesday.scopes[0].decision == "unknown"
    assert tuesday.scopes[0].hold_reason == "incomplete-tree"

    auth = {
        "owner/suite": {
            "id": "owner/suite",
            "links": {"github": "https://github.com/owner/repo"},
            "upstream": {"repo": "owner/repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["owner/base"],
        },
        "owner/base": {"id": "owner/base", "links": {"github": "https://github.com/owner/repo/blob/main/skills/base/SKILL.md"}},
        "other/good": {
            "id": "other/good",
            "links": {"github": "https://github.com/other/good-repo"},
            "upstream": {"repo": "other/good-repo", "version": "v1.0.0"},
            "upstreamComponentRoot": "skills",
            "suiteComponents": ["other/comp"],
        },
        "other/comp": {"id": "other/comp", "links": {"github": "https://github.com/other/good-repo/blob/main/skills/comp/SKILL.md"}},
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/repos/owner/repo/releases/latest"):
            return {"tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/owner/repo/releases/tag/v1.1.0"}
        if url.endswith("/repos/other/good-repo/releases/latest"):
            return {"tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/other/good-repo/releases/tag/v1.1.0"}
        if "/repos/owner/repo/git/trees/v1.1.0" in url:
            return trunc
        if "/repos/other/good-repo/git/trees/v1.1.0" in url:
            return {
                "sha": "a" * 40, "truncated": False,
                "tree": [
                    {"path": "skills", "type": "tree", "sha": "b" * 40},
                    {"path": "skills/comp", "type": "tree", "sha": "c" * 40},
                    {"path": "skills/comp/SKILL.md", "type": "blob", "sha": "d" * 40},
                    {"path": "skills/added", "type": "tree", "sha": "e" * 40},
                    {"path": "skills/added/SKILL.md", "type": "blob", "sha": "f" * 40},
                ],
            }
        raise AssertionError(f"unexpected fake upstream request: {url}")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])

    suites = [auth["owner/suite"], auth["other/good"]]
    collected = weekly_collector.collect_suites(suites, auth, poll_id="partial-trunc-e2e")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    census = weekly_census.run_weekly_census(
        suites, auth, fake, collected,
        poll_id="partial-trunc-e2e", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    assert census.status == "unknown-incomplete"
    assert census.logical_candidate_count == 1
    assert dict(census.repository_statuses) == {"other/good-repo": "candidate-intent"}
    by_id = {scope.named_id: scope for scope in census.scopes}
    assert by_id["owner/suite"].decision == "unknown"
    assert by_id["owner/suite"].hold_reason == "incomplete-tree"
    assert by_id["owner/suite"].inventory_status == "unknown"
    assert by_id["owner/suite"].version_status == "release-observed"
    assert by_id["other/good"].decision == "eligible-for-read-only-binding"
    assert by_id["other/good"].inventory_status == "verified"


def test_bootstrap_and_version_only_preserve_distinct_producer_facts(monkeypatch):
    auth = {
        "boot/suite": {
            "id": "boot/suite",
            "links": {"github": "https://github.com/boot/repo"},
        },
        "ver/suite": {
            "id": "ver/suite",
            "links": {"github": "https://github.com/ver/repo"},
            "upstream": {"repo": "ver/repo", "version": "v1.0.0"},
            "suiteComponents": ["ver/leaf"],
        },
        "ver/leaf": {
            "id": "ver/leaf",
            "links": {"github": "https://github.com/other/leaf-repo/blob/main/SKILL.md"},
        },
    }

    def fetch(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/repos/boot/repo/releases/latest"):
            return {"tag_name": "v1.0.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/boot/repo/releases/tag/v1.0.0"}
        if url.endswith("/repos/ver/repo/releases/latest"):
            return {"tag_name": "v1.1.0", "published_at": "2026-11-23T08:00:00Z", "html_url": "https://github.com/ver/repo/releases/tag/v1.1.0"}
        raise AssertionError(f"unexpected fake upstream request: {url}")

    monkeypatch.setattr(watcher, "fetch_json", fetch)
    monkeypatch.setattr(liveness, "fetch_json", fetch)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda *_: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda *_: [])

    suites = [auth["boot/suite"], auth["ver/suite"]]
    collected = weekly_collector.collect_suites(suites, auth, poll_id="non-comp-facts")
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    census = weekly_census.run_weekly_census(
        suites, auth, fake, collected,
        poll_id="non-comp-facts", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", config_repo="gaia-research/gaia-skill-tree",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
    )
    assert census.status == "observed-plan-only"
    assert census.logical_candidate_count == 2
    by_id = {scope.named_id: scope for scope in census.scopes}
    assert by_id["boot/suite"].proof_status == "bootstrap-finding"
    assert by_id["boot/suite"].inventory_status == "not-applicable"
    assert by_id["boot/suite"].decision == "eligible-for-read-only-binding"
    assert by_id["ver/suite"].proof_status == "non-component-mode"
    assert by_id["ver/suite"].inventory_status == "not-applicable"
    assert by_id["ver/suite"].decision == "eligible-for-read-only-binding"
