"""Offline-only composition tests for P2 Slice 5."""
from __future__ import annotations

import dataclasses
import socket
from typing import Any

import pytest

from scripts.upstream_watcher import liveness, watcher, weekly_census
from scripts.upstream_watcher.approval import PayloadError
from upstream_fakes import FakeGh


@pytest.fixture(autouse=True)
def _forbid_network(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("weekly census test attempted network access")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


class ReadOnlyGh:
    _MUTATORS = {"create_issue", "edit_issue", "edit_labels", "comment", "edit_comment", "delete_comment"}

    def __init__(self, inner: FakeGh):
        self.inner = inner
        self.write_attempts: list[str] = []

    def __getattr__(self, name: str) -> Any:
        if name in self._MUTATORS:
            def blocked(*args: Any, **kwargs: Any) -> None:
                self.write_attempts.append(name)
                raise AssertionError(f"forbidden issue write: {name}")
            return blocked
        return getattr(self.inner, name)


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


def _run(monkeypatch: pytest.MonkeyPatch, *, held_named_ids=frozenset()):
    _install_fake_upstream(monkeypatch)
    auth = _authority()
    gh = ReadOnlyGh(FakeGh())
    result = weekly_census.run_weekly_census(
        [auth["owner/suite"]], auth, gh,
        poll_id="census-2026-11-23", observed_at="2026-11-23T09:00:00Z",
        state_mode="ephemeral-empty", held_named_ids=held_named_ids,
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        historical_loader=lambda _identifier: {},
    )
    assert gh.write_attempts == [] and gh.inner.writes == []
    return result


def test_complete_fake_scoped_census_is_plan_only_and_has_explicit_hold(monkeypatch):
    census = _run(monkeypatch, held_named_ids=frozenset({"owner/suite"}))
    assert census.status == "observed-plan-only"
    assert census.scopes == (weekly_census.CensusScope("owner/suite", "owner/repo", "observed", "verified"),)
    assert census.binding_status == "idle" and census.logical_candidate_count == 0
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


def test_incomplete_collector_tree_never_claims_inventory_clearance(monkeypatch):
    _install_fake_upstream(monkeypatch, tree={"sha": "a" * 40, "truncated": True, "tree": []})
    auth, gh = _authority(), ReadOnlyGh(FakeGh())
    result = weekly_census.run_weekly_census(
        [auth["owner/suite"]], auth, gh, poll_id="census-incomplete",
        observed_at="2026-11-23T09:00:00Z", state_mode="ephemeral-empty",
        index_loader=lambda: {"byId": {}, "bySlug": {}}, policy={},
        historical_loader=lambda _identifier: {},
    )
    assert result.scopes[0].collection_status == "observed"
    assert result.scopes[0].proof_status != "verified"
    assert result.actual_creates == result.actual_updates == 0 and not result.write_readiness
    assert gh.inner.writes == [] and gh.write_attempts == []


def test_duplicate_scope_and_unsupported_supplied_state_fail_closed():
    auth, gh = _authority(), ReadOnlyGh(FakeGh())
    kwargs = dict(poll_id="invalid", observed_at="2026-11-23T09:00:00Z",
                  state_mode="ephemeral-empty", index_loader=lambda: {"byId": {}, "bySlug": {}},
                  policy={}, historical_loader=lambda _identifier: {})
    with pytest.raises(PayloadError):
        weekly_census.run_weekly_census([auth["owner/suite"]] * 2, auth, gh, **kwargs)
    with pytest.raises(PayloadError, match="supplied named-v3 state is deferred"):
        weekly_census.run_weekly_census([], auth, gh, **{**kwargs, "state_mode": "named-v3"})
    assert gh.inner.writes == [] and gh.write_attempts == []


def test_census_api_does_not_accept_a_checkpoint_path_or_implicit_state():
    names = {field.name for field in dataclasses.fields(weekly_census.WeeklyCensus)}
    assert "journal_path" not in names
    with pytest.raises(TypeError):
        weekly_census.run_weekly_census(
            [], _authority(), ReadOnlyGh(FakeGh()), poll_id="x",
            observed_at="2026-11-23T09:00:00Z", journal_path="/tmp/should-not-open",
            state_mode="ephemeral-empty", index_loader=lambda: {"byId": {}, "bySlug": {}},
        )
