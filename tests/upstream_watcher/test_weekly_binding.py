"""Offline read-only canonical repository plan binding proofs (P2 Slice 4A).

All transports are fake and network/GitHub write paths are trapped.
No issue mutations, no settlement, no registry writes, and no rollout changes.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import socket
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
from scripts.upstream_watcher import (
    batch,
    envelope as wire,
    liveness,
    repository_batch as rb,
    watcher,
    weekly_binding as wb,
    weekly_collector as wc,
    weekly_journal as wj,
    weekly_reducer as wr,
)
from scripts.upstream_watcher.live import LiveGh
from upstream_fakes import FakeGh, RestGhRunner


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("offline weekly_binding test attempted network access")

    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbidden)


class NoWriteTrapGh:
    """Read-only proxy around a fake GitHub client; fails immediately on any mutator."""

    _MUTATORS = frozenset(
        {"create_issue", "edit_issue", "edit_labels", "comment", "edit_comment", "delete_comment"}
    )

    def __init__(self, inner: Any):
        self._inner = inner
        self.write_attempts: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        if name in self._MUTATORS:
            def _trap(*args: Any, **kwargs: Any) -> None:
                self.write_attempts.append((name, args, kwargs))
                raise AssertionError(f"read-only binding attempted GitHub mutation: {name}")

            return _trap
        return getattr(self._inner, name)


def _authority() -> dict[str, dict[str, Any]]:
    def _suite(sid: str, repo: str, root: str, base_slug: str) -> dict[str, dict[str, Any]]:
        owner = sid.split("/", 1)[0]
        comp = f"{owner}/{base_slug}"
        return {
            sid: {
                "id": sid,
                "suiteRef": sid,
                "upstreamComponentRoot": root,
                "suiteComponents": [comp],
                "links": {"github": f"https://github.com/{repo}"},
                "upstream": {"repo": repo, "version": "v1.0.0"},
            },
            comp: {
                "id": comp,
                "suiteRef": sid,
                "links": {"github": f"https://github.com/{repo}/blob/main/{root}/{base_slug}/SKILL.md"},
            },
        }

    auth: dict[str, dict[str, Any]] = {}
    auth.update(_suite("owner/a", "owner/repo", "skills-a", "a-base"))
    auth.update(_suite("owner/b", "owner/repo", "skills-b", "b-base"))
    auth.update(_suite("owner/c", "owner/repo", "skills-c", "c-base"))
    auth.update(_suite("other/good", "other/good", "skills", "good-base"))
    return auth


def _empty_index() -> dict[str, dict[str, Any]]:
    return {"byId": {}, "bySlug": {}}


def _raw_finding(
    named_id: str = "owner/a",
    *,
    repo: str = "owner/repo",
    version: str = "v1.1.0",
    adds: tuple[str, ...] = ("alpha",),
    removes: tuple[str, ...] = (),
    component_root: str = "skills-a",
    released_at: str = "2026-11-16T08:00:00Z",
) -> dict[str, Any]:
    return {
        "finding_type": "update",
        "skillId": named_id,
        "currentVersion": "v1.0.0",
        "newVersion": version,
        "sourceUrl": f"https://github.com/{repo}/releases/tag/{version}",
        "releasedAt": released_at,
        "mode": "components",
        "upstreamComponentRoot": component_root,
        "componentAdds": list(adds),
        "componentRemoves": list(removes),
        "linkLiveness": [],
        "nameDrift": [],
    }


def _plan_and_commit(
    journal_path: Path,
    *,
    poll_id: str,
    observed_at: str,
    raw_findings: list[dict[str, Any]],
    gh: Any,
    authority: dict[str, dict[str, Any]],
    expected_pin: wj.JournalPin | None = None,
    allow_bootstrap: bool = False,
    initialized: bool = False,
    held_repos: frozenset[str] = frozenset(),
    held_named_ids: frozenset[str] = frozenset(),
    unavailable_named_ids: frozenset[str] = frozenset(),
    complete: bool = True,
) -> tuple[wj.JournalCommitResult, wr.PollInput]:
    report, code = rb.run_repository_batch(
        raw_findings,
        gh,
        apply=False,
        authority=authority,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code == 0, f"planner failed unexpectedly: {report.get('unknownEvidence')}"
    poll = wr.poll_input_from_batch_report(
        poll_id,
        observed_at,
        report,
        complete=complete,
        held_repos=held_repos,
        held_named_ids=held_named_ids,
        unavailable_named_ids=unavailable_named_ids,
    )
    commit = wj.commit_poll(
        journal_path,
        poll,
        authority,
        expected_pin=expected_pin,
        allow_bootstrap=allow_bootstrap,
        initialized=initialized,
    )
    return commit, poll


def _bind(commit: wj.JournalCommitResult, poll: wr.PollInput, gh: Any, authority: dict[str, dict[str, Any]], **kwargs: Any) -> wb.WeeklyBindingResult:
    kwargs.setdefault("index_loader", _empty_index)
    kwargs.setdefault("policy", {})
    kwargs.setdefault("historical_loader", lambda _: {})
    return wb.bind_weekly_plans(commit, poll, gh, authority, **kwargs)


def _envelope_issue(
    raw_findings: list[dict[str, Any]],
    authority: dict[str, dict[str, Any]],
    *,
    number: int = 10,
    state: str = "open",
    updated_at: str = "2026-11-15T12:00:00Z",
) -> tuple[dict[str, Any], dict[str, Any]]:
    report, code = rb.run_repository_batch(
        raw_findings,
        FakeGh(),
        apply=False,
        authority=authority,
        index_loader=_empty_index,
        policy={},
        historical_loader=lambda _: {},
        plan_only=True,
    )
    assert code == 0
    env_payload = report["repositories"][0]["payload"]
    return {
        "number": number,
        "state": state,
        "title": wire.title(env_payload),
        "body": wire.render(env_payload),
        "labels": ["upstream:release", "needs-triage"],
        "updated_at": updated_at,
    }, env_payload


# 1. Full collector -> planner -> reducer -> journal -> binding loop at flush
def test_end_to_end_collector_planner_reducer_journal_binding_flush_and_sibling_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    auth = _authority()
    existing_c_raw = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    existing_issue, existing_env = _envelope_issue([existing_c_raw], auth, number=10)
    existing_c_finding = existing_env["findings"][0]
    existing_c_sha = existing_c_finding["payloadSha256"]

    raw_gh = FakeGh([existing_issue])
    trap_gh = NoWriteTrapGh(raw_gh)

    def _fake_fetch_json(url: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        if url.endswith("/repos/owner/repo/releases/latest"):
            return {
                "tag_name": "v1.2.0",
                "published_at": "2026-11-16T08:00:00Z",
                "html_url": "https://github.com/owner/repo/releases/tag/v1.2.0",
            }
        if "/repos/owner/repo/git/trees/v1.2.0" in url:
            return {
                "sha": "a" * 40,
                "truncated": False,
                "tree": [
                    {"path": "skills-a", "type": "tree", "sha": "0" * 40},
                    {"path": "skills-a/a-base", "type": "tree", "sha": "10" * 20},
                    {"path": "skills-a/a-base/SKILL.md", "type": "blob", "sha": "1" * 40},
                    {"path": "skills-a/alpha", "type": "tree", "sha": "20" * 20},
                    {"path": "skills-a/alpha/SKILL.md", "type": "blob", "sha": "2" * 40},
                    {"path": "skills-b", "type": "tree", "sha": "9" * 40},
                    {"path": "skills-b/b-base", "type": "tree", "sha": "30" * 20},
                    {"path": "skills-b/b-base/SKILL.md", "type": "blob", "sha": "3" * 40},
                    {"path": "skills-b/beta", "type": "tree", "sha": "40" * 20},
                    {"path": "skills-b/beta/SKILL.md", "type": "blob", "sha": "4" * 40},
                ],
            }
        raise AssertionError(f"unexpected fake GitHub URL: {url}")

    monkeypatch.setattr(watcher, "fetch_json", _fake_fetch_json)
    monkeypatch.setattr(liveness, "fetch_json", _fake_fetch_json)
    monkeypatch.setattr(watcher, "check_component_liveness", lambda components, reg: [])
    monkeypatch.setattr(watcher, "check_name_drift", lambda components, reg: [])

    journal_path = tmp_path / "named-v3.json"
    suites = [auth["owner/a"], auth["owner/b"]]

    # Poll 1: Tuesday (non-flush) -> both held; binding is idle.
    collected_1 = wc.collect_suites(suites, auth, poll_id="poll-2026-11-17")
    assert len(collected_1.observed_findings) == 2 and len(collected_1.complete_inventories) == 2
    report_1, code_1 = rb.run_repository_batch(
        list(collected_1.observed_findings), trap_gh, apply=False, authority=auth,
        index_loader=_empty_index, policy={}, historical_loader=lambda _: {}, plan_only=True,
    )
    assert code_1 == 0
    poll_1 = wc.build_poll_input("poll-2026-11-17", "2026-11-17T09:00:00Z", report_1, collected_1, auth)
    commit_1 = wj.commit_poll(journal_path, poll_1, auth, allow_bootstrap=True, initialized=False)
    assert commit_1.persisted is True

    bound_1 = _bind(commit_1, poll_1, trap_gh, auth)
    assert bound_1.status == wb.RUN_STATUS_IDLE and bound_1.candidate_intents == ()
    assert bound_1.non_eligible_scopes == {("owner/repo", "owner/a"): "hold", ("owner/repo", "owner/b"): "hold"}
    assert bound_1.write_authorized is False and bound_1.write_readiness is False

    # Poll 2: Monday (flush day) -> owner/a eligible, owner/b explicitly held_named_ids.
    collected_2 = wc.collect_suites(suites, auth, poll_id="poll-2026-11-23")
    assert len(collected_2.complete_inventories) == 2
    report_2, code_2 = rb.run_repository_batch(
        list(collected_2.observed_findings), trap_gh, apply=False, authority=auth,
        index_loader=_empty_index, policy={}, historical_loader=lambda _: {}, plan_only=True,
    )
    assert code_2 == 0
    poll_2 = wc.build_poll_input(
        "poll-2026-11-23", "2026-11-23T09:00:00Z", report_2, collected_2, auth,
        held_named_ids=frozenset({"owner/b"}),
    )
    commit_2 = wj.commit_poll(journal_path, poll_2, auth, expected_pin=commit_1.handle.pin, initialized=True)
    assert commit_2.persisted is True

    bound_2 = _bind(commit_2, poll_2, trap_gh, auth)
    assert bound_2.status == wb.RUN_STATUS_BOUND
    assert bound_2.write_authorized is False and bound_2.write_readiness is False
    assert bound_2.non_eligible_scopes == {("owner/repo", "owner/b"): "held-scope"}
    assert len(bound_2.candidate_intents) == 1

    repo_bind = bound_2.candidate_intents[0]
    assert repo_bind.repository == "owner/repo" and repo_bind.status == wb.STATUS_CANDIDATE_INTENT
    assert [m.named_id for m in repo_bind.selected_members] == ["owner/a"]
    assert repo_bind.target is not None and repo_bind.target.action == "update" and repo_bind.target.umbrella == 10
    assert dict(repo_bind.target.snapshot) == batch.snapshot_of(existing_issue)
    assert dict(repo_bind.target.preserved_siblings) == {"owner/c": existing_c_sha}

    by_id = {f["skillId"]: f for f in repo_bind.envelope_payload["findings"]}
    assert set(by_id) == {"owner/a", "owner/c"}
    assert by_id["owner/c"] == existing_c_finding
    assert by_id["owner/a"]["payloadSha256"] == repo_bind.selected_members[0].finding_sha256
    assert raw_gh.writes == [] and trap_gh.write_attempts == []


# 2. Same repo, two eligible named scopes with distinct findings & per-named pins/digests
def test_same_repo_two_eligible_named_scopes_preserve_distinct_findings_pins_and_digests(tmp_path: Path):
    auth = _authority()
    raw_gh = FakeGh()
    trap_gh = NoWriteTrapGh(raw_gh)
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_b = _raw_finding("owner/b", adds=("beta",), component_root="skills-b", version="v2.1.0")
    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-flush-1", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_b], gh=trap_gh, authority=auth, allow_bootstrap=True,
    )
    bound = _bind(commit, poll, trap_gh, auth)
    assert bound.status == wb.RUN_STATUS_BOUND and len(bound.candidate_intents) == 1
    repo_bind = bound.candidate_intents[0]
    assert repo_bind.target is not None and repo_bind.target.action == "create" and repo_bind.target.umbrella is None
    assert repo_bind.target.snapshot is None and dict(repo_bind.target.preserved_siblings) == {}
    assert repo_bind.target.inventory_proof["complete"] is True
    assert repo_bind.target.inventory_proof["unambiguousAbsence"] is True
    assert repo_bind.target.inventory_proof["closedAndPrExcluded"] is True

    members = {m.named_id: m for m in repo_bind.selected_members}
    assert set(members) == {"owner/a", "owner/b"}
    assert members["owner/a"].finding_sha256 != members["owner/b"].finding_sha256
    assert members["owner/a"].row_pins["owner/repo:alpha"].first_seen_version == "v2.0.0"
    assert members["owner/b"].row_pins["owner/repo:beta"].first_seen_version == "v2.1.0"
    assert members["owner/a"].row_pins["owner/repo:alpha"].evidence_url.endswith("/blob/v2.0.0/skills-a/alpha/SKILL.md")
    assert members["owner/b"].row_pins["owner/repo:beta"].evidence_url.endswith("/blob/v2.1.0/skills-b/beta/SKILL.md")
    assert raw_gh.writes == [] and trap_gh.write_attempts == []


# 3. Lowest exact OPEN umbrella selected; closed issues & PRs never selected
def test_lowest_exact_open_umbrella_selected_and_closed_and_pr_never_selected(tmp_path: Path):
    auth = _authority()
    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    low_issue, _ = _envelope_issue([existing_c], auth, number=12, updated_at="2026-11-15T10:00:00Z")
    high_issue, _ = _envelope_issue([existing_c], auth, number=25, updated_at="2026-11-15T11:00:00Z")
    gh_dups = NoWriteTrapGh(FakeGh([high_issue, low_issue]))

    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v1.2.0")
    commit_a, poll_a = _plan_and_commit(
        tmp_path / "j-dups.json", poll_id="poll-dups", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a], gh=gh_dups, authority=auth, allow_bootstrap=True,
    )
    bound_dups = _bind(commit_a, poll_a, gh_dups, auth)
    target_dups = bound_dups.candidate_intents[0].target
    assert target_dups is not None and target_dups.action == "update" and target_dups.umbrella == 12
    assert dict(target_dups.snapshot) == batch.snapshot_of(low_issue)
    assert [d["number"] for d in target_dups.duplicates] == [25]

    old_closed_raw = _raw_finding("owner/a", adds=(), component_root="skills-a", version="v1.0.5")
    closed_issue, _ = _envelope_issue([old_closed_raw], auth, number=8, state="closed")
    open_pr = {
        "number": 9, "state": "open", "title": "[upstream] owner/repo → v1.2.0",
        "body": "PR body must never be selected", "labels": ["upstream:release"],
        "updated_at": "2026-11-16T00:00:00Z",
        "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/9"},
    }
    gh_create = NoWriteTrapGh(FakeGh([closed_issue, open_pr]))
    commit_b, poll_b = _plan_and_commit(
        tmp_path / "j-create.json", poll_id="poll-create", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a], gh=gh_create, authority=auth, allow_bootstrap=True,
    )
    bound_create = _bind(commit_b, poll_b, gh_create, auth)
    target_create = bound_create.candidate_intents[0].target
    assert target_create is not None and target_create.action == "create" and target_create.umbrella is None
    assert target_create.inventory_proof["closedAndPrExcluded"] is True
    assert target_create.inventory_proof["unambiguousAbsence"] is True


# 4. Stale revision (both loader-blocked and current-trusted-pin mismatch), replay, wrong/tampered/incomplete poll
def test_stale_journal_revision_replayed_poll_wrong_poll_and_incomplete_poll_refused(tmp_path: Path):
    auth = _authority()
    raw_gh = FakeGh()
    gh = NoWriteTrapGh(raw_gh)
    journal_path = tmp_path / "named-v3.json"
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v1.2.0")

    commit_1, poll_1 = _plan_and_commit(
        journal_path, poll_id="poll-1", observed_at="2026-11-23T09:00:00Z",
        raw_findings=[raw_a], gh=gh, authority=auth, allow_bootstrap=True,
    )

    # (a) Exact replay -> refused.
    replay_commit = wj.commit_poll(journal_path, poll_1, auth, expected_pin=commit_1.handle.pin, initialized=True)
    assert replay_commit.persisted is False and replay_commit.reduction.replayed is True
    bound_replay = _bind(replay_commit, poll_1, gh, auth)
    assert bound_replay.status == wb.RUN_STATUS_REFUSED and bound_replay.candidate_intents == ()
    assert bound_replay.refusal_reason == "replayed-poll-cannot-bind-new-intent"

    # (b) Wrong poll_id and tampered raw poll input -> refused.
    bound_wrong = _bind(commit_1, dataclasses.replace(poll_1, poll_id="poll-other"), gh, auth)
    assert bound_wrong.status == wb.RUN_STATUS_REFUSED and bound_wrong.candidate_intents == ()

    tampered_raw = copy.deepcopy(list(poll_1.observed_findings))
    tampered_raw[0]["componentAdds"] = ["alpha", "injected"]
    bound_tampered = _bind(commit_1, dataclasses.replace(poll_1, observed_findings=tampered_raw), gh, auth)
    assert bound_tampered.status == wb.RUN_STATUS_REFUSED and bound_tampered.candidate_intents == ()
    assert bound_tampered.refusal_reason == "poll-input-disagrees-with-committed-poll-receipt"

    # (c) Incomplete poll -> refused.
    bound_incomplete = _bind(commit_1, dataclasses.replace(poll_1, complete=False), gh, auth)
    assert bound_incomplete.status == wb.RUN_STATUS_REFUSED and bound_incomplete.candidate_intents == ()

    # (d) Advance local journal to rev 2:
    #     - Default call (no external trusted_latest_pin): load_journal blocks stale pin vs on-disk rev 2.
    #     - Caller supplying current on-disk trusted_latest_pin=commit_2.handle.pin: binding catches
    #       live_handle.pin != commit_1.handle.pin.
    commit_2, poll_2 = _plan_and_commit(
        journal_path, poll_id="poll-2", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a], gh=gh, authority=auth, expected_pin=commit_1.handle.pin, initialized=True,
    )
    assert commit_2.handle.pin is not None and commit_2.handle.pin != commit_1.handle.pin

    bound_stale_loader = _bind(commit_1, poll_1, gh, auth)
    assert bound_stale_loader.status == wb.RUN_STATUS_REFUSED and bound_stale_loader.candidate_intents == ()
    assert "stale" in (bound_stale_loader.refusal_reason or "")

    bound_stale_with_current_pin = _bind(commit_1, poll_1, gh, auth, trusted_latest_pin=commit_2.handle.pin)
    assert bound_stale_with_current_pin.status == wb.RUN_STATUS_REFUSED and bound_stale_with_current_pin.candidate_intents == ()
    assert bound_stale_with_current_pin.refusal_reason == "stale-journal-revision-against-local-checkpoint"

    # (e) External trusted_latest_pin newer than on-disk journal -> local-journal-blocked:stale.
    newer_pin = wj.JournalPin(revision=commit_2.handle.pin.revision + 1, digest="f" * 64)
    bound_rollback = _bind(commit_2, poll_2, gh, auth, trusted_latest_pin=newer_pin)
    assert bound_rollback.status == wb.RUN_STATUS_REFUSED and bound_rollback.candidate_intents == ()
    assert "local-journal-blocked:stale" in (bound_rollback.refusal_reason or "")
    assert raw_gh.writes == [] and gh.write_attempts == []


# 5. Fresh plan drift / fabricated decision declined (never re-sealed)
def test_fresh_plan_drift_and_fabricated_decision_declined_without_resealing(tmp_path: Path):
    auth = _authority()
    raw_gh = FakeGh()
    trap_gh = NoWriteTrapGh(raw_gh)
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")

    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-drift", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_good], gh=trap_gh, authority=auth, allow_bootstrap=True,
    )

    older_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v1.5.0")
    drifted_issue, _ = _envelope_issue([older_a], auth, number=30)
    raw_gh.add(drifted_issue)

    bound = _bind(commit, poll, trap_gh, auth)
    assert bound.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert bound.repositories["owner/repo"].reason == "fresh-plan-drift-from-eligible-finding"
    assert [b.repository for b in bound.candidate_intents] == ["other/good"]

    bad_eligible = tuple(
        dataclasses.replace(d, finding_sha256="0" * 64) if d.named_id == "owner/a" else d
        for d in commit.reduction.eligible
    )
    bad_commit = dataclasses.replace(commit, reduction=dataclasses.replace(commit.reduction, eligible=bad_eligible))
    bound_fab = _bind(bad_commit, poll, trap_gh, auth)
    assert bound_fab.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert bound_fab.repositories["owner/repo"].reason == "eligible-scope-provenance-verification-failed"
    assert [b.repository for b in bound_fab.candidate_intents] == ["other/good"]


# 6. Create conservatively declines unselected P1 carried-forward siblings
def test_create_declines_when_p1_carry_forward_would_publish_unselected_sibling(tmp_path: Path):
    auth = _authority()
    closed_b_raw = _raw_finding("owner/b", adds=("beta",), component_root="skills-b", version="v1.1.0")
    closed_issue, _ = _envelope_issue([closed_b_raw], auth, number=55, state="closed")
    gh = NoWriteTrapGh(FakeGh([closed_issue]))

    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")
    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-carry", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_good], gh=gh, authority=auth, allow_bootstrap=True,
    )
    bound = _bind(commit, poll, gh, auth)
    assert bound.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert "create-would-include-unselected-carried-siblings" in (bound.repositories["owner/repo"].reason or "")
    assert "owner/b" in (bound.repositories["owner/repo"].reason or "")
    assert [b.repository for b in bound.candidate_intents] == ["other/good"]


# 7. Ambiguous title, title-only issue, snapshot drift, and partial global read
def test_ambiguous_title_title_only_snapshot_drift_and_partial_global_read(tmp_path: Path):
    auth = _authority()
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")

    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-edge", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )

    ambig_gh = NoWriteTrapGh(FakeGh([{
        "number": 41, "state": "open", "title": "Upstream release for owner/repo v2.0.0",
        "body": "malformed title", "labels": ["upstream:release"], "updated_at": "2026-11-16T00:00:00Z",
    }]))
    bound_ambig = _bind(commit, poll, ambig_gh, auth)
    assert bound_ambig.repositories["owner/repo"].status == wb.STATUS_AMBIGUOUS
    assert [b.repository for b in bound_ambig.candidate_intents] == ["other/good"]

    title_only_gh = NoWriteTrapGh(FakeGh([{
        "number": 42, "state": "open", "title": "[upstream] owner/repo → v2.0.0",
        "body": "Title matches but there is no canonical payload block.",
        "labels": ["upstream:release"], "updated_at": "2026-11-16T00:00:00Z",
    }]))
    bound_title_only = _bind(commit, poll, title_only_gh, auth)
    assert bound_title_only.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert [b.repository for b in bound_title_only.candidate_intents] == ["other/good"]

    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    open_issue, _ = _envelope_issue([existing_c], auth, number=43, updated_at="2026-11-16T00:00:00Z")
    raced_raw_gh = FakeGh([open_issue])
    raced_raw_gh.stale_on_get[43] = {"updated_at": "2026-11-23T10:05:00Z"}
    bound_raced = _bind(commit, poll, NoWriteTrapGh(raced_raw_gh), auth)
    assert bound_raced.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert bound_raced.repositories["owner/repo"].reason == "target-snapshot-or-state-drifted-during-binding"
    assert [b.repository for b in bound_raced.candidate_intents] == ["other/good"]

    failing_gh = NoWriteTrapGh(LiveGh(runner=RestGhRunner([], fail_pages={("open", "", 1)})))
    bound_partial = _bind(commit, poll, failing_gh, auth)
    assert bound_partial.status == wb.RUN_STATUS_REFUSED and bound_partial.candidate_intents == ()
    assert "global-inventory-or-setup-incomplete" in (bound_partial.refusal_reason or "")


# 8. No-op and suppressed-processed distinguished from candidate-intent
def test_noop_and_suppressed_processed_distinguished_from_candidate_intent(tmp_path: Path):
    auth = _authority()
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")

    open_matching, _ = _envelope_issue([raw_a], auth, number=60, state="open")
    gh_noop = NoWriteTrapGh(FakeGh([open_matching]))
    commit_n, poll_n = _plan_and_commit(
        tmp_path / "j-noop.json", poll_id="poll-noop", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a], gh=gh_noop, authority=auth, allow_bootstrap=True,
    )
    bound_noop = _bind(commit_n, poll_n, gh_noop, auth)
    assert bound_noop.repositories["owner/repo"].status == wb.STATUS_NOOP
    assert bound_noop.repositories["owner/repo"].is_candidate_intent is False
    assert bound_noop.repositories["owner/repo"].target is not None
    assert bound_noop.repositories["owner/repo"].target.umbrella == 60
    assert bound_noop.candidate_intents == ()

    commit_s, poll_s = _plan_and_commit(
        tmp_path / "j-sup.json", poll_id="poll-sup", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )
    closed_matching, _ = _envelope_issue([raw_a], auth, number=61, state="closed")
    bound_sup = _bind(commit_s, poll_s, NoWriteTrapGh(FakeGh([closed_matching])), auth)
    assert bound_sup.repositories["owner/repo"].status == wb.STATUS_SUPPRESSED
    assert bound_sup.repositories["owner/repo"].is_candidate_intent is False
    assert bound_sup.candidate_intents == ()


# 9. #1833 preserve-legacy-reference (Ruflo + AgentDB) holds + unaffected repo
def test_legacy_1833_ruflo_agentdb_hold_preserved_and_unrelated_repo_still_usable(tmp_path: Path):
    auth = _authority()
    auth["ruvnet/ruflo"] = {
        "id": "ruvnet/ruflo", "suiteRef": "ruvnet/ruflo", "upstreamComponentRoot": "skills",
        "suiteComponents": ["ruvnet/agentdb"],
        "links": {"github": "https://github.com/ruvnet/ruflo"},
        "upstream": {"repo": "ruvnet/ruflo", "version": "v3.0.0"},
    }
    auth["ruvnet/agentdb"] = {
        "id": "ruvnet/agentdb", "suiteRef": "ruvnet/ruflo", "upstreamComponentRoot": "skills",
        "suiteComponents": ["ruvnet/agentdb-vector-search"],
        "links": {"github": "https://github.com/ruvnet/agentdb/blob/2a8115de9ddbc672df4d725069b77228b43af53d/README.md"},
        "upstream": {"repo": "ruvnet/agentdb", "version": "v3.0.0"},
    }
    auth["ruvnet/agentdb-vector-search"] = {
        "id": "ruvnet/agentdb-vector-search", "suiteRef": "ruvnet/agentdb",
        "links": {"github": "https://github.com/ruvnet/agentdb/blob/main/skills/agentdb-vector-search/SKILL.md"},
    }
    historical_agentdb = {
        "ruvnet/agentdb": {
            "id": "ruvnet/agentdb",
            "suiteRef": "ruvnet/ruflo",
            "links": {"github": "https://github.com/ruvnet/ruflo"},
            "upstream": {"repo": "ruvnet/ruflo", "version": "v3.0.0"},
        }
    }
    legacy_payload = {
        "skillId": "ruvnet/agentdb", "newVersion": "v3.0.0", "releasedAt": "2026-10-01T00:00:00Z",
        "sourceUrl": "https://github.com/ruvnet/ruflo/releases/tag/v3.0.0", "mode": "components",
        "componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": [], "candidates": [],
    }
    legacy_1833 = {
        "number": 1833, "state": "open", "title": "[upstream] ruvnet/ruflo → v3.0.0",
        "body": "## Legacy release\n\n" + batch.payload_block(legacy_payload),
        "labels": ["upstream:release", "upstream:approved"], "updated_at": "2026-10-01T00:00:00Z",
    }

    raw_ruflo = _raw_finding("ruvnet/ruflo", repo="ruvnet/ruflo", adds=("ruflo-new",), component_root="skills", version="v3.1.0")
    raw_agentdb = _raw_finding("ruvnet/agentdb", repo="ruvnet/agentdb", adds=("agentdb-new",), component_root="skills", version="v3.11.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")
    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-1833", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_ruflo, raw_agentdb, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )

    held_raw_gh = FakeGh([legacy_1833])
    held_trap_gh = NoWriteTrapGh(held_raw_gh)
    bound = _bind(
        commit, poll, held_trap_gh, auth,
        policy={"shared_source_model": "repo_envelope", "legacy_transition": "preserve_plan"},
        historical_loader=lambda ident: historical_agentdb if ident == "ruvnet/agentdb" else {},
    )
    assert bound.status == wb.RUN_STATUS_BOUND and bound.write_authorized is False and bound.write_readiness is False

    ruflo_bind = bound.repositories["ruvnet/ruflo"]
    agentdb_bind = bound.repositories["ruvnet/agentdb"]
    for scoped_bind, expected_named in ((ruflo_bind, "ruvnet/ruflo"), (agentdb_bind, "ruvnet/agentdb")):
        assert scoped_bind.status == wb.STATUS_HELD and scoped_bind.reason == "legacy-migration-hold"
        assert scoped_bind.is_candidate_intent is False and scoped_bind.write_authorized is False
        assert [m.named_id for m in scoped_bind.selected_members] == [expected_named]
        assert len(scoped_bind.known_legacy_holds) == 1
        assert scoped_bind.known_legacy_holds[0]["kind"] == "preserve-legacy-reference"
        assert scoped_bind.known_legacy_holds[0]["issue"] == 1833
        assert scoped_bind.known_legacy_holds[0]["legacyNamedId"] == "ruvnet/agentdb"
        assert scoped_bind.known_legacy_holds[0]["currentReleaseRepository"] == "ruvnet/agentdb"
        assert scoped_bind.known_legacy_holds[0]["writeReadiness"] is False

    assert ruflo_bind.selected_members[0].finding_sha256 != agentdb_bind.selected_members[0].finding_sha256
    assert [b.repository for b in bound.candidate_intents] == ["other/good"]
    assert held_raw_gh.writes == [] and held_trap_gh.write_attempts == []


# 10. Fresh get_issue must validate upstream:release label and usable labels without extra read
def test_fresh_get_issue_missing_or_malformed_release_label_declines_without_extra_read(tmp_path: Path):
    auth = _authority()
    existing_c = _raw_finding("owner/c", adds=("gamma",), component_root="skills-c", version="v1.1.0")
    open_issue, _ = _envelope_issue([existing_c], auth, number=44, updated_at="2026-11-16T00:00:00Z")
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")

    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-label-reread", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )

    class _CountingGetGh:
        def __init__(self, inner: FakeGh, override_labels: Any):
            self._inner = inner
            self._override_labels = override_labels
            self.get_calls: list[int] = []

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

        def get_issue(self, number: int) -> dict[str, Any]:
            self.get_calls.append(number)
            row = self._inner.get_issue(number)
            if number == 44:
                row["labels"] = self._override_labels
            return row

    # (a) Identical number/state/title/body/updated_at, only upstream:release removed on get_issue.
    raw_lost = FakeGh([open_issue])
    counting_lost = _CountingGetGh(raw_lost, [{"name": "needs-triage"}])
    trap_lost = NoWriteTrapGh(counting_lost)
    bound_lost = _bind(commit, poll, trap_lost, auth)
    assert bound_lost.status == wb.RUN_STATUS_BOUND
    assert bound_lost.repositories["owner/repo"].status == wb.STATUS_DECLINED
    assert bound_lost.repositories["owner/repo"].reason == "target-snapshot-or-state-drifted-during-binding"
    assert bound_lost.repositories["owner/repo"].is_candidate_intent is False
    assert bound_lost.repositories["owner/repo"].target is None
    assert [b.repository for b in bound_lost.candidate_intents] == ["other/good"]
    assert counting_lost.get_calls == [44]
    assert raw_lost.writes == [] and trap_lost.write_attempts == []

    # (b) Malformed labels on get_issue (labels=None and malformed dict entry) -> declined, single read.
    for bad_labels in (None, [{"name": None}], [123]):
        raw_bad = FakeGh([open_issue])
        counting_bad = _CountingGetGh(raw_bad, bad_labels)
        trap_bad = NoWriteTrapGh(counting_bad)
        bound_bad = _bind(commit, poll, trap_bad, auth)
        assert bound_bad.status == wb.RUN_STATUS_BOUND
        assert bound_bad.repositories["owner/repo"].status == wb.STATUS_DECLINED
        assert bound_bad.repositories["owner/repo"].is_candidate_intent is False
        assert [b.repository for b in bound_bad.candidate_intents] == ["other/good"]
        assert counting_bad.get_calls == [44]
        assert raw_bad.writes == [] and trap_bad.write_attempts == []


# 11. Malformed live inventory fails closed globally without unhandled TypeError or body leak
def test_malformed_live_inventory_fails_closed_globally_without_unhandled_typeerror(tmp_path: Path):
    auth = _authority()
    raw_a = _raw_finding("owner/a", adds=("alpha",), component_root="skills-a", version="v2.0.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")

    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-malformed-inv", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_a, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )

    secret_body_marker = "SENSITIVE_UNTRUSTED_BODY_MARKER_DO_NOT_LEAK"

    class _RawInventoryGh:
        """Fake reader whose list_issues returns unvalidated rows straight to read_repository_live."""

        def __init__(self, open_rows: list[dict[str, Any]]):
            self._open_rows = open_rows
            self.writes: list[Any] = []

        def list_issues(self, state: str, since: str | None = None, labels: str | None = None) -> list[dict[str, Any]]:
            if state == "open" and not labels:
                return copy.deepcopy(self._open_rows)
            return []

        def child_state(self, number: int) -> str:
            return "absent"

    # (a) Exact Terra repro: labels=None passes raw list_issues into read_repository_live -> global refusal.
    malformed_cases = [
        {"number": 71, "state": "open", "title": "[upstream] owner/repo → v1.0.0", "body": secret_body_marker, "labels": None, "updated_at": "2026-11-16T00:00:00Z"},
        {"number": 72, "state": "open", "title": "[upstream] owner/repo → v1.0.0", "body": secret_body_marker, "labels": [{"name": None}], "updated_at": "2026-11-16T00:00:00Z"},
        {"number": 73, "state": "open", "title": 12345, "body": secret_body_marker, "labels": [{"name": "upstream:release"}], "updated_at": "2026-11-16T00:00:00Z"},
    ]
    for bad_row in malformed_cases:
        raw_reader = _RawInventoryGh([bad_row])
        trap_gh = NoWriteTrapGh(raw_reader)
        bound = _bind(commit, poll, trap_gh, auth)
        assert bound.status == wb.RUN_STATUS_REFUSED
        assert bound.candidate_intents == ()
        assert bound.write_authorized is False and bound.write_readiness is False
        assert "global-inventory-or-setup-incomplete" in (bound.refusal_reason or "")
        assert secret_body_marker not in (bound.refusal_reason or "")
        assert raw_reader.writes == [] and trap_gh.write_attempts == []

    # (b) Real LiveGh reader receiving JSON with labels: null on open listing -> global refusal, no TypeError.
    def _raw_rest_runner(args, capture_output=True, text=True, timeout=None):
        if args[1] == "api" and args[-1] == "repos/gaia-research/gaia-skill-tree":
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps({"open_issues_count": 1}), stderr="")
        if args[1] == "api" and "--include" in args:
            row = {
                "number": 74,
                "state": "open",
                "title": "[upstream] owner/repo → v1.0.0",
                "body": secret_body_marker,
                "labels": None,
                "updated_at": "2026-11-16T00:00:00Z",
            }
            payload = [row] if "state=open" in args[-1] else []
            out = "HTTP/2.0 200 OK\nContent-Type: application/json\n\n" + json.dumps(payload)
            return subprocess.CompletedProcess(args, 0, stdout=out, stderr="")
        raise AssertionError(f"unexpected LiveGh subprocess call: {args}")

    live_trap = NoWriteTrapGh(LiveGh(runner=_raw_rest_runner))
    bound_live = _bind(commit, poll, live_trap, auth)
    assert bound_live.status == wb.RUN_STATUS_REFUSED
    assert bound_live.candidate_intents == ()
    assert "global-inventory-or-setup-incomplete" in (bound_live.refusal_reason or "")
    assert secret_body_marker not in (bound_live.refusal_reason or "")
    assert live_trap.write_attempts == []


# 12. Optional offline cached #1833 proof (Ruflo + AgentDB holds, unrelated repo usable)
@pytest.mark.skipif(
    not os.environ.get("P1_LEGACY_CACHE"),
    reason="owner-supplied bounded cache not configured; no network fallback",
)
def test_cached_1833_offline_ruflo_and_agentdb_holds_and_unrelated_usable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def _forbidden_url(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("cached #1833 binding proof attempted network access")

    monkeypatch.setattr(urllib.request, "urlopen", _forbidden_url)

    cache_path = Path(os.environ["P1_LEGACY_CACHE"])
    cache_digest_before = hashlib.sha256(cache_path.read_bytes()).hexdigest()
    cached = json.loads(cache_path.read_text(encoding="utf-8"))
    body = cached["body"]
    raw_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    root = Path(__file__).resolve().parents[2]
    direction = json.loads(
        (root / "founder/reports/upstream-backlog-2026-11/P1_IDENTITY_FOUNDER_DECISIONS.json").read_text(encoding="utf-8")
    )
    # Boolean-only verification; never print, commit, or embed cached issue body or payload.
    assert cached["number"] == 1833
    assert raw_sha == "ae62e163b04c2b24057d629ff1024a19982c8180d88a7ad2c5b64707f3ab8d1a"
    assert hashlib.sha256((body + "\n").encode("utf-8")).hexdigest() == direction["issueBodySha256"]

    # Load exact current checkout authority locks for ruvnet/ruflo and ruvnet/agentdb.
    auth = _authority()
    for rel in ("registry/named/ruvnet/ruflo.md", "registry/named/ruvnet/agentdb.md"):
        _, front, _ = split_frontmatter((root / rel).read_text(encoding="utf-8"))
        meta = load_yaml_simple(front)
        auth[meta["id"]] = meta
    assert wire.authority_repository("ruvnet/ruflo", auth) == "ruvnet/ruflo"
    assert wire.authority_repository("ruvnet/agentdb", auth) == "ruvnet/agentdb"

    actual_run = subprocess.run
    historical_reads: list[str] = []

    def _local_pinned_only(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert args == ["git", "show", "9b4d9b98043140188f00b14d0ac8fa6bc02491b7:registry/named/ruvnet/agentdb.md"]
        historical_reads.append("pinned-local-history")
        return actual_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _local_pinned_only)

    cached_1833 = {
        "number": cached["number"],
        "state": "open",
        "title": cached["title"],
        "body": body,
        "labels": copy.deepcopy(cached["labels"]),
        "updated_at": cached.get("updated_at") or "2026-10-01T00:00:00Z",
    }
    raw_ruflo = _raw_finding("ruvnet/ruflo", repo="ruvnet/ruflo", adds=("ruflo-new",), component_root="skills", version="v99.1.0")
    raw_agentdb = _raw_finding("ruvnet/agentdb", repo="ruvnet/agentdb", adds=("agentdb-new",), component_root="skills", version="v99.2.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")

    # (a) Initial P1 planner already observes cached #1833: both Ruflo & AgentDB are held before binding.
    initial_raw_gh = FakeGh([cached_1833])
    initial_trap_gh = NoWriteTrapGh(initial_raw_gh)
    report_a, code_a = rb.run_repository_batch(
        [raw_ruflo, raw_agentdb, raw_good],
        initial_trap_gh,
        apply=False,
        authority=auth,
        index_loader=_empty_index,
        policy=None,
        historical_loader=rb.historical_authority,
        plan_only=True,
    )
    assert code_a == 0 and report_a["unknownEvidence"] == []
    held_repos_a = frozenset(p["repository"] for p in report_a["repositories"] if p["outcome"] == "held")
    assert held_repos_a == frozenset({"ruvnet/ruflo", "ruvnet/agentdb"})
    poll_a = wr.poll_input_from_batch_report(
        "poll-1833-initial", "2026-11-23T10:00:00Z", report_a, complete=True, held_repos=held_repos_a
    )
    commit_a = wj.commit_poll(tmp_path / "j-1833-initial.json", poll_a, auth, allow_bootstrap=True, initialized=False)
    bound_a = wb.bind_weekly_plans(
        commit_a, poll_a, initial_trap_gh, auth, index_loader=_empty_index, policy=None, historical_loader=rb.historical_authority
    )
    assert bound_a.status == wb.RUN_STATUS_BOUND
    assert bound_a.non_eligible_scopes == {
        ("ruvnet/agentdb", "ruvnet/agentdb"): "held-scope",
        ("ruvnet/ruflo", "ruvnet/ruflo"): "held-scope",
    }
    assert [b.repository for b in bound_a.candidate_intents] == ["other/good"]
    assert initial_raw_gh.writes == [] and initial_trap_gh.write_attempts == []

    # (b) Clean logically eligible initial commit -> fresh target read includes cached #1833:
    #     binding itself holds BOTH ruvnet/ruflo and ruvnet/agentdb independently via pinned historical authority.
    historical_reads.clear()
    commit_b, poll_b = _plan_and_commit(
        tmp_path / "j-1833-bind.json", poll_id="poll-1833-bind", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_ruflo, raw_agentdb, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )
    held_raw_gh = FakeGh([cached_1833])
    held_trap_gh = NoWriteTrapGh(held_raw_gh)
    bound_b = wb.bind_weekly_plans(
        commit_b, poll_b, held_trap_gh, auth, index_loader=_empty_index, policy=None, historical_loader=rb.historical_authority
    )
    assert bound_b.status == wb.RUN_STATUS_BOUND and bound_b.write_authorized is False and bound_b.write_readiness is False

    ruflo_bind = bound_b.repositories["ruvnet/ruflo"]
    agentdb_bind = bound_b.repositories["ruvnet/agentdb"]
    for scoped_bind, expected_named in ((ruflo_bind, "ruvnet/ruflo"), (agentdb_bind, "ruvnet/agentdb")):
        assert scoped_bind.status == wb.STATUS_HELD and scoped_bind.reason == "legacy-migration-hold"
        assert scoped_bind.is_candidate_intent is False
        assert scoped_bind.write_authorized is False and scoped_bind.write_readiness is False
        assert [m.named_id for m in scoped_bind.selected_members] == [expected_named]
        assert len(scoped_bind.known_legacy_holds) == 1
        hold = scoped_bind.known_legacy_holds[0]
        assert hold["kind"] == "preserve-legacy-reference"
        assert hold["issue"] == 1833
        assert hold["repository"] == "ruvnet/ruflo"
        assert hold["legacyNamedId"] == "ruvnet/agentdb"
        assert hold["currentReleaseRepository"] == "ruvnet/agentdb"
        assert hold["bodySha256"] == raw_sha
        assert hold["bodyHashScheme"] == "raw_api_utf8"
        assert hold["writeReadiness"] is False

    assert ruflo_bind.repository != agentdb_bind.repository
    assert ruflo_bind.selected_members[0].finding_sha256 != agentdb_bind.selected_members[0].finding_sha256
    assert [b.repository for b in bound_b.candidate_intents] == ["other/good"]
    assert len(historical_reads) >= 2 and set(historical_reads) == {"pinned-local-history"}
    assert held_raw_gh.writes == [] and held_trap_gh.write_attempts == []
    assert hashlib.sha256(cached_1833["body"].encode("utf-8")).hexdigest() == raw_sha
    assert hashlib.sha256(cache_path.read_bytes()).hexdigest() == cache_digest_before
