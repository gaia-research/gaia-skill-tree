"""Offline-only composition tests for P2 Slice 5."""
from __future__ import annotations

import dataclasses
import socket
from typing import Any

import pytest

from scripts.upstream_watcher import liveness, watcher, weekly_census, weekly_collector
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


def _run(monkeypatch: pytest.MonkeyPatch, *, held_named_ids=frozenset(), held_repos=frozenset(), tree=None):
    _install_fake_upstream(monkeypatch, tree=tree)
    auth = _authority()
    poll_id = "census-2026-11-23"
    collected = weekly_collector.collect_suites([auth["owner/suite"]], auth, poll_id=poll_id)
    fake = FakeIssueService(repo="gaia-research/gaia-skill-tree")
    result = weekly_census.run_weekly_census(
        [auth["owner/suite"]], auth, fake, collected,
        poll_id=poll_id, observed_at="2026-11-23T09:00:00Z",
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


def test_repo_hold_is_explicit_and_does_not_become_global_refusal(monkeypatch):
    census = _run(monkeypatch, held_repos=frozenset({"owner/repo"}))
    assert census.status == "scoped-holds-or-unavailable"
    assert census.scopes[0].decision == "held-repository-scope"
    assert census.binding_status != "refused"


def test_incomplete_collector_tree_is_unknown_not_clearance(monkeypatch):
    result = _run(monkeypatch, tree={"sha": "a" * 40, "truncated": True, "tree": []})
    assert result.status == "unknown-incomplete"
    assert result.scopes[0].collection_status == "observed"
    assert result.scopes[0].proof_status != "verified"
    assert result.scopes[0].inventory_status == "unknown"
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
