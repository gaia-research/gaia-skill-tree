"""Offline read-only canonical repository plan binding proofs (P2 Slice 4A).

All transports are fake and network/GitHub write paths are trapped.
No issue mutations, no settlement, no registry writes, and no rollout changes.
"""

from __future__ import annotations

import copy
import dataclasses
import socket
from pathlib import Path
from typing import Any

import pytest

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


# 9. #1833 preserve-legacy-reference (Ruflo / AgentDB) hold + unaffected repo
def test_legacy_1833_ruflo_agentdb_hold_preserved_and_unrelated_repo_still_usable(tmp_path: Path):
    auth = _authority()
    auth["ruvnet/claude-flow"] = {
        "id": "ruvnet/claude-flow", "suiteRef": "ruvnet/claude-flow", "upstreamComponentRoot": "skills",
        "suiteComponents": ["ruvnet/agentdb-vector-search"],
        "links": {"github": "https://github.com/ruvnet/ruflo"},
        "upstream": {"repo": "ruvnet/ruflo", "version": "v3.0.0"},
    }
    auth["ruvnet/agentdb-vector-search"] = {
        "id": "ruvnet/agentdb-vector-search", "suiteRef": "ruvnet/claude-flow",
        "links": {"github": "https://github.com/ruvnet/ruflo/blob/main/skills/agentdb-vector-search/SKILL.md"},
    }
    legacy_payload = {
        "skillId": "ruvnet/claude-flow", "newVersion": "v3.0.0", "releasedAt": "2026-10-01T00:00:00Z",
        "sourceUrl": "https://github.com/ruvnet/ruflo/releases/tag/v3.0.0", "mode": "components",
        "componentAdds": [], "componentRemoves": [], "linkLiveness": [], "nameDrift": [], "candidates": [],
    }
    legacy_1833 = {
        "number": 1833, "state": "open", "title": "[upstream] ruvnet/ruflo → v3.0.0",
        "body": "## Legacy release\n\n" + batch.payload_block(legacy_payload),
        "labels": ["upstream:release", "upstream:approved"], "updated_at": "2026-10-01T00:00:00Z",
    }

    raw_ruflo = _raw_finding("ruvnet/claude-flow", repo="ruvnet/ruflo", adds=("agentdb-memory",), component_root="skills", version="v3.1.0")
    raw_good = _raw_finding("other/good", repo="other/good", adds=("delta",), component_root="skills", version="v2.0.0")
    commit, poll = _plan_and_commit(
        tmp_path / "named-v3.json", poll_id="poll-1833", observed_at="2026-11-23T10:00:00Z",
        raw_findings=[raw_ruflo, raw_good], gh=NoWriteTrapGh(FakeGh()), authority=auth, allow_bootstrap=True,
    )

    held_raw_gh = FakeGh([legacy_1833])
    held_trap_gh = NoWriteTrapGh(held_raw_gh)
    bound = _bind(
        commit, poll, held_trap_gh, auth,
        policy={"shared_source_model": "repo_envelope", "legacy_transition": "preserve_plan"},
    )
    assert bound.status == wb.RUN_STATUS_BOUND and bound.write_authorized is False and bound.write_readiness is False

    ruflo_bind = bound.repositories["ruvnet/ruflo"]
    assert ruflo_bind.status == wb.STATUS_HELD and ruflo_bind.reason == "legacy-migration-hold"
    assert ruflo_bind.is_candidate_intent is False and ruflo_bind.write_authorized is False
    assert len(ruflo_bind.known_legacy_holds) == 1
    assert ruflo_bind.known_legacy_holds[0]["kind"] == "preserve-legacy-reference"
    assert ruflo_bind.known_legacy_holds[0]["issue"] == 1833
    assert ruflo_bind.known_legacy_holds[0]["writeReadiness"] is False

    assert [b.repository for b in bound.candidate_intents] == ["other/good"]
    assert held_raw_gh.writes == [] and held_trap_gh.write_attempts == []
